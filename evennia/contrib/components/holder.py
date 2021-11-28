from evennia.contrib import components


class ComponentProperty:
    def __init__(self, component_name, **kwargs):
        self.component_name = component_name
        self.values = kwargs

    def __get__(self, instance, owner):
        component = instance.components.get(self.component_name)
        return component

    def __set__(self, instance, value):
        raise Exception("Cannot set a class property")

    def __set_name__(self, owner, name):
        class_components = getattr(owner, "_class_components", None)
        if not class_components:
            class_components = []
            setattr(owner, "_class_components", class_components)

        class_components.append((self.component_name, self.values))


class ComponentHandler:
    def __init__(self, host):
        self.host = host
        self._loaded_components = {}

    def add(self, component):
        self._set_component(component)
        self.db_names.append(component.name)
        component.on_added(self.host)

    def add_default(self, name):
        component = components.get_component_class(name)
        if not component:
            raise ComponentDoesNotExist(f"Component {name} does not exist.")

        new_component = component.default_create(self.host)
        self._set_component(new_component)
        self.db_names.append(name)
        new_component.on_added(self.host)

    def remove(self, component):
        component_name = component.name
        if component_name in self._loaded_components:
            component.on_removed(self.host)
            self.db_names.remove(component_name)
            del self._loaded_components[component_name]
        else:
            message = f"Cannot remove {component_name} from {self.host.name} as it is not registered."
            raise ComponentIsNotRegistered(message)

    def remove_by_name(self, name):
        instance = self.get(name)
        if not instance:
            message = f"Cannot remove {name} from {self.host.name} as it is not registered."
            raise ComponentIsNotRegistered(message)

        instance.on_removed(self.host)
        self.db_names.remove(name)
        del self._loaded_components[name]

    def get(self, name):
        return self._loaded_components.get(name)

    def has(self, name):
        return name in self._loaded_components

    def initialize(self):
        component_names = self.db_names
        if not component_names:
            return

        for component_name in component_names:
            component = components.get_component_class(component_name)
            if component:
                component_instance = component.load(self.host)
                self._set_component(component_instance)
            else:
                message = f"Could not initialize runtime component {component_name} of {self.host.name}"
                raise ComponentDoesNotExist(message)

    def _set_component(self, component):
        self._loaded_components[component.name] = component

    @property
    def db_names(self):
        return self.host.attributes.get("component_names")

    def __getattr__(self, name):
        return self.get(name)


class ComponentHolderMixin(object):
    """
    Mixin to add component support to a typeclass

    Components are set on objects using the component.name as an object attribute.
    All registered components are initialized on the typeclass.
    They will be of None value if not present in the class components or runtime components.
    """

    def at_init(self):
        super(ComponentHolderMixin, self).at_init()
        setattr(self, "_component_handler", ComponentHandler(self))
        self.components.initialize()

    def at_object_creation(self):
        super().at_object_creation()
        component_names = []
        setattr(self, "_component_handler", ComponentHandler(self))
        class_components = getattr(self, "_class_components", ())
        for component_name, values in class_components:
            component_class = components.get_component_class(component_name)
            component = component_class.create(self, **values)
            component_names.append(component_name)
            self.components._loaded_components[component_name] = component
        self.db.component_names = component_names

    @property
    def components(self) -> ComponentHandler:
        return getattr(self, "_component_handler", None)

    @property
    def cmp(self) -> ComponentHandler:
        return self.components


class ComponentDoesNotExist(Exception):
    pass


class ComponentIsNotRegistered(Exception):
    pass
