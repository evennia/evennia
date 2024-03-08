"""
Components - ChrisLR 2022

This file contains the classes that allow a typeclass to use components.
"""

from . import exceptions, signals
from .component import Component
from .listing import get_component_class


class ComponentProperty:
    """
    This allows you to register a component on a typeclass.
    Components registered with this property are automatically added
    to any instance of this typeclass.

    Defaults can be overridden for this typeclass by passing kwargs
    """

    def __init__(self, name, **kwargs):
        """
        Initializes the descriptor

        Args:
            name (str): The name of the component
            **kwargs (any): Key=Values overriding default values of the component
        """
        self.name = name
        self.values = kwargs
        self.component_class = None
        self.slot_name = None

    def __get__(self, instance, owner):
        if not self.component_class:
            component_class = get_component_class(self.name)
            self.component_class = component_class
            self.slot_name = component_class.get_component_slot()

        component = instance.components.get(self.slot_name)
        return component

    def __set__(self, instance, value):
        raise Exception("Cannot set a class property")

    def __set_name__(self, owner, name):
        # Retrieve the class_components set on the direct class only
        class_components = owner.__dict__.get("_class_components", [])
        if not class_components:
            setattr(owner, "_class_components", class_components)

        class_components.append((self.name, self.values))


class ComponentHandler:
    """
    This is the handler that will be added to any typeclass that inherits from ComponentHolder.
    It lets you add or remove components and will load components as needed.
    It stores the list of registered components on the host .db with component_names as key.
    """

    def __init__(self, host):
        self.host = host
        self._loaded_components = {}

    def add(self, component: Component):
        """
        Method to add a Component to a host.
        It caches the loaded component and appends its name to the host's component name list.
        It will also call the component's 'at_added' method, passing its host.

        Args:
            component (object): The 'loaded' component instance to add.

        """
        component_name = component.name
        self.db_names.append(component_name)
        self.host.tags.add(component_name, category="components")
        self._set_component(component)
        for field in component.get_fields():
            field.at_added(component)

        component.at_added(self.host)

    def add_default(self, name):
        """
        Method to add a Component initialized to default values on a host.
        It will retrieve the proper component and instantiate it with 'default_create'.
        It will cache this new component and add it to its list.
        It will also call the component's 'at_added' method, passing its host.

        Args:
            name (str): The name of the component class to add.

        """
        component_class = get_component_class(name)
        component_instance = component_class.default_create(self.host)
        self.add(component_instance)

    def remove(self, component: Component):
        """
        Method to remove a component instance from a host.
        It removes the component from the cache and listing.
        It will call the component's 'at_removed' method.

        Args:
            component (object): The component instance to remove.

        """
        name = component.name
        slot_name = component.get_component_slot()
        if not self.has(slot_name):
            message = f"Cannot remove {name} from {self.host.name} as it is not registered."
            raise exceptions.ComponentIsNotRegistered(message)

        for field in component.get_fields():
            field.at_removed(component)

        component.at_removed(self.host)

        self.host.tags.remove(component.name, category="components")
        self.host.signals.remove_object_listeners_and_responders(component)

        self.db_names.remove(name)
        del self._loaded_components[slot_name]

    def remove_by_name(self, name):
        """
        Method to remove a component instance from a host.
        It removes the component from the cache and listing.
        It will call the component's 'at_removed' method.

        Args:
            name (str): The name of the component to remove or its slot.

        """
        instance = self.get(name)
        if not instance:
            message = f"Cannot remove {name} from {self.host.name} as it is not registered."
            raise exceptions.ComponentIsNotRegistered(message)

        self.remove(instance)

    def get(self, name: str) -> Component | None:
        return self._loaded_components.get(name)

    def has(self, name: str) -> bool:
        """
        Method to check if a component is registered and ready.

        Args:
            name (str): The name of the component or the slot.

        """
        return name in self._loaded_components

    def initialize(self):
        """
        Method that loads and caches each component currently registered on the host.
        It retrieves the names from the registered listing and calls 'load' on each
        prototype class that can be found from this listing.

        """
        component_names = self.db_names
        if not component_names:
            return

        for component_name in component_names:
            component = get_component_class(component_name)
            if component:
                component_instance = component.load(self.host)
                self._set_component(component_instance)
            else:
                message = (
                    f"Could not initialize runtime component {component_name} of {self.host.name}"
                )
                raise exceptions.ComponentDoesNotExist(message)

    def _set_component(self, component):
        """
        Sets the loaded component in this instance.
        """
        slot_name = component.get_component_slot()
        self._loaded_components[slot_name] = component
        self.host.signals.add_object_listeners_and_responders(component)

    @property
    def db_names(self):
        """
        Property shortcut to retrieve the registered component keys

        Returns:
            component_names (iterable): The name of each component that is registered

        """
        names = self.host.attributes.get("component_names")
        if names is None:
            self.host.db.component_names = []
            names = self.host.db.component_names

        return names

    def __getattr__(self, name):
        return self.get(name)


class ComponentHolderMixin:
    """
    Mixin to add component support to a typeclass

    Components are set on objects using the component.name as an object attribute.
    All registered components are initialized on the typeclass.
    They will be of None value if not present in the class components or runtime components.
    """

    def at_init(self):
        """
        Method that initializes the ComponentHandler.
        """
        super(ComponentHolderMixin, self).at_init()
        setattr(self, "_component_handler", ComponentHandler(self))
        setattr(self, "_signal_handler", signals.SignalsHandler(self))
        self.components.initialize()
        self.signals.trigger("at_after_init")

    def at_post_puppet(self, *args, **kwargs):
        super().at_post_puppet(*args, **kwargs)
        self.signals.trigger("at_post_puppet", *args, **kwargs)

    def at_post_unpuppet(self, *args, **kwargs):
        super().at_post_unpuppet(*args, **kwargs)
        self.signals.trigger("at_post_unpuppet", *args, **kwargs)

    def basetype_setup(self):
        """
        Method that initializes the ComponentHandler, creates and registers all
        components that were set on the typeclass using ComponentProperty.
        """
        super().basetype_setup()
        setattr(self, "_component_handler", ComponentHandler(self))
        setattr(self, "_signal_handler", signals.SignalsHandler(self))
        class_components = self._get_class_components()
        for component_name, values in class_components:
            component_class = get_component_class(component_name)
            component = component_class.create(self, **values)
            self.components.add(component)

        self.signals.trigger("at_basetype_setup")

    @property
    def components(self) -> ComponentHandler:
        """
        Property getter to retrieve the component_handler.
        Returns:
            ComponentHandler: This Host's ComponentHandler
        """
        return getattr(self, "_component_handler", None)

    @property
    def cmp(self) -> ComponentHandler:
        """
        Shortcut Property getter to retrieve the component_handler.
        Returns:
            ComponentHandler: This Host's ComponentHandler
        """
        return self.components

    @property
    def signals(self) -> signals.SignalsHandler:
        return getattr(self, "_signal_handler", None)

    def _get_class_components(self):
        class_components = {}

        def base_type_iterator():
            base_stack = [type(self)]
            while base_stack:
                _base_type = base_stack.pop()
                yield _base_type
                base_stack.extend(_base_type.__bases__)

        for base_type in base_type_iterator():
            base_class_components = getattr(base_type, "_class_components", ())
            for cmp_name, cmp_values in base_class_components:
                cmp_class = get_component_class(cmp_name)
                cmp_slot = cmp_class.get_component_slot()
                class_components[cmp_slot] = (cmp_name, cmp_values)

        instance_components = getattr(self, "_class_components", ())
        for cmp_name, cmp_values in instance_components:
            cmp_class = get_component_class(cmp_name)
            cmp_slot = cmp_class.get_component_slot()
            class_components[cmp_slot] = (cmp_name, cmp_values)

        return tuple(class_components.values())
