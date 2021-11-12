import inspect

from evennia.contrib.components import listing
from evennia.utils import logger


class ComponentHolderMixin(object):
    """
    Mixin to add component support to a typeclass

    Components are set on objects using the component.name as an object attribute.
    All registered components are initialized on the typeclass.
    They will be of None value if not present in the class components or runtime components.
    """
    class_components = []

    def at_init(self):
        self.component_instances = {}
        for component in listing.all_components:
            setattr(self, component.name, None)

        super(ComponentHolderMixin, self).at_init()
        self.initialize_components()

    def at_object_creation(self):
        """
        This initializes a newly created object to hold components.
        Class components will be instanced via default_create.
        If a class component is already instanced it will be duplicated instead.
        """
        self.component_instances = {}
        self.db.runtime_components = []
        super(ComponentHolderMixin, self).at_object_creation()
        for component_class in self.class_components:
            if inspect.isclass(component_class):
                component_instance = component_class.default_create(self)
            else:
                component_instance = component_class.duplicate(self)

            self._set_component(component_instance)

    def at_post_puppet(self, *args, **kwargs):
        """
        This allows a component to react to a player logging in.
        For example, Hunger could start ticking down.
        """
        super().at_post_puppet(*args, **kwargs)
        # TODO Should we only call components who register to this host signal?
        for component in self.component_instances.values():
            component.at_post_puppet(*args, **kwargs)

    def at_post_unpuppet(self, *args, **kwargs):
        """
        This allows a component to react to a player logging out.
        For example, Hunger could stop ticking down.
        """
        super().at_post_unpuppet(*args, **kwargs)
        # TODO Should we only call components who register to this host signal?
        for component in self.component_instances.values():
            component.at_post_unpuppet(*args, **kwargs)

    def initialize_components(self):
        """
        Loads components from DB values and sets them as usable attributes on the object
        """
        for component_class in self.class_components:
            component_name = component_class.name
            component_instance = component_class.load(self)
            self._set_component(component_instance)

        runtime_component_names = self.runtime_component_names
        if not runtime_component_names:
            return

        for component_name in runtime_component_names:
            component = listing.get(component_name)
            if component:
                component_instance = component.load(self)
                self._set_component(component_instance)
            else:
                logger.log_err(f"Could not initialize runtime component {component_name} from {self.name}")

    def register_component(self, component):
        """
        Registers new components as runtime or replaces an existing component.
        """
        existing_component = self.component_instances.get(component.name)
        if existing_component:
            self.unregister_component(existing_component)
        else:
            self.db.runtime_components.append(component.name)

        self._set_component(component)
        component.on_register(self)

    def unregister_component(self, component):
        """
        Unregisters a component, only works for runtime components
        """
        if component.name in self.class_components_names:
            raise ValueError("Cannot unregister class components.")

        component.on_unregister(self)
        if component.name in self.runtime_component_names:
            self.db.runtime_components.remove(component.name)

        setattr(self, component.name, None)
        del self.component_instances[component.name]

    @property
    def runtime_components(self):
        runtime_component_names = self.db.runtime_components
        component_instances = [
            self.component_instances.get(name)
            for name in runtime_component_names
        ]
        return component_instances

    @property
    def runtime_component_names(self):
        return self.db.runtime_components

    @property
    def class_component_names(self):
        return [c.name for c in self.class_components]

    def _set_component(self, component):
        self.component_instances[component.name] = component
        setattr(self, component.name, component)