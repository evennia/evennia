"""
Components - ChrisLR 2021

This is a basic Component System.
It allows you to use components on typeclasses using a simple syntax.
This helps writing isolated code and reusing it over multiple objects.

## Installation

- To enable component support for a typeclass,
   import and inherit the ComponentHolderMixin, similar to this
  ```
  from evennia.contrib.components import ComponentHolderMixin
  class Character(ComponentHolderMixin, DefaultCharacter):
  ```

- Components need to inherit the Component class and must be registered to the listing
    Example:
    ```
    from evennia.contrib.components import Component, listing
    @listing.register
    class Health(Component):
        name = "health"
    ```

- Components may define DBFields at the class level
    Example:
    ```
    from evennia.contrib.components import Component, listing, DBField
    @listing.register
    class Health(Component):
        health = DBField('health', default_value=1)
    ```

    Note that default_value is optional and may be a callable such as `dict`

- Keep in mind that all components must be imported to be visible in the listing
  As such, I recommend regrouping them in a package
  You can then import all your components in that package's __init__
  The plug the import of that package early, for example in your typeclasses's __init__

"""
import abc
import inspect
import itertools

from evennia.contrib.components import listing
from evennia.utils import logger

UNSET = object()


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
        self.db.runtime_components = []
        super(ComponentHolderMixin, self).at_object_creation()
        for component_class in self.class_components:
            if inspect.isclass(component_class):
                component_instance = component_class.default_create(self)
            else:
                component_instance = component_class.duplicate(self)
            setattr(self, component_class.name, component_instance)

    def at_post_puppet(self, *args, **kwargs):
        """
        This allows a component to react to a player logging in.
        For example, Hunger could start ticking down.
        """
        super().at_post_puppet(*args, **kwargs)
        # TODO Should we only call components who register to this host signal?
        for component in self.component_instances:
            component.at_post_puppet(*args, **kwargs)

    def at_post_unpuppet(self, *args, **kwargs):
        """
        This allows a component to react to a player logging out.
        For example, Hunger could stop ticking down.
        """
        super().at_post_unpuppet(*args, **kwargs)
        # TODO Should we only call components who register to this host signal?
        for component in self.component_instances:
            component.at_post_unpuppet(*args, **kwargs)

    def initialize_components(self):
        """
        Loads components from DB values and sets them as usable attributes on the object
        """
        for component_class in self.class_components:
            component_name = component_class.name
            component_instance = component_class.load(self)
            setattr(self, component_name, component_instance)
            self.component_instances[component_name] = component_instance

        runtime_component_names = self.runtime_component_names
        if not runtime_component_names:
            return

        for component_name in runtime_component_names:
            component = listing.get(component_name)
            if component:
                component_instance = component.load(self)
                setattr(self, component_name, component_instance)
                self.component_instances[component_name] = component_instance
            else:
                logger.log_err(f"Could not initialize runtime component {component_name} from {self.name}")

    def register_component(self, component):
        """
        Registers new components as runtime or replaces an existing component.
        """
        if component.name in self.class_component_names or component.name in self.runtime_component_names:
            existing_component = getattr(self, component.name, None)
            if existing_component:
                existing_component.unregister_component()
        else:
            self.db.runtime_components.append(component.name)

        setattr(self, component.name, component)
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

    @property
    def runtime_components(self):
        runtime_component_names = self.db.runtime_components
        component_instances = [
            getattr(self, name, None) for name in runtime_component_names
        ]

        return component_instances

    @property
    def runtime_component_names(self):
        return self.db.runtime_components

    @property
    def class_component_names(self):
        # TODO Improve
        return (c.name for c in self.class_components)

    @property
    def component_instances(self):
        # TODO Maybe this should be stored in a permanent list
        runtime_component_names = self.db.runtime_components
        class_component_names = self.class_component_names
        instances = []
        for component_name in itertools.chain(runtime_component_names, class_component_names):
            instance = getattr(self, component_name, None)
            if instance:
                instances.append(instance)

        return instances


class Component(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def name(self):
        pass

    def __init__(self, host=None):
        # TODO Passing a host here is to prevent TDB TNDB from creating
        # TODO Without host, this should instantiate this component's TDB and TNDB
        # TODO Should this be the default create?
        self.host = host
        self._db_fields = self._get_db_field_names()

    @classmethod
    def as_template(cls, **kwargs):
        new = cls.default_create(None, **kwargs)
        return new


    @classmethod
    def default_create(cls, game_object, **kwargs):
        """
        This is called when the game_object is created
         and should return the base initialized state of a component.
        """
        new = cls(game_object)
        for field_name in new._db_fields:
            # TODO AttributeHandler has a batch_add that might give better performance
            provided_value = kwargs.get(field_name)
            if provided_value is not None:
                setattr(new, field_name, provided_value)
            else:
                cls.__dict__[field_name].assign_default_value(new)

        return new

    @classmethod
    def create(cls, game_object, **kwargs):
        """
        This is the method to call when supplying kwargs to initialize a component.
        Useful with runtime components
        """
        new = cls.default_create(game_object)
        return new

    def cleanup(self):
        """ This cleans all attributes from the host's db """
        for attribute in self._db_fields:
            delattr(self, attribute)

    def duplicate(self, new_host):
        """
        This copies the current values of the component instance
        to a new instance registered to the new host.
        Useful for templates
        """
        new = type(self)(new_host)
        for attribute, value in self._get_db_field_values():
            setattr(new, attribute, value)

        return new

    @classmethod
    def load(cls, game_object):
        return cls(game_object)

    def _get_db_field_names(self):
        # TODO This does not include inherited DB Fields, to investigate
        return tuple(name for name, attribute in type(self).__dict__.items()
                     if isinstance(attribute, DBField))

    def _get_db_field_values(self):
        return ((name, getattr(self, name, None)) for name in self._db_fields)

    def on_register(self, host):
        # TODO This here should fetch the host's db, ndb or use its own ndb
        # TODO using its own ndb shud copyover
        if not self.host:
            self.host = host
        else:
            raise ValueError("Components should not register twice!")

    def on_unregister(self, host):
        if host != self.host:
            raise ValueError("Component attempted to unregister from the wrong host.")
        self.host = None

    def at_post_puppet(self, *args, **kwargs):
        pass

    def at_post_unpuppet(self, *args, **kwargs):
        pass

class DBField(object):
    """
    This is the class to use in components for attributes that bind to their host's db.
    Allows using a simpler syntax, similar to component.attribute
    Values are stored on the host's db using a prefixed key made of
    the component's name and the attribute name, similar to component__attribute.

    If the parent component's host is not set, values are stored in a local cache.
    This allows you to create Templates that you can then duplicate to valid hosts.
    """
    def __init__(self, name, default_value=None):
        self.name = name
        self.default_value = default_value
        self._cache = {}

    def assign_default_value(self, instance):
        default_value = self._get_default_value()
        self._cache[instance] = default_value

        # Lists and dicts have to be set from the start to avoid mutable objects related mistakes
        if self.default_value is list or self.default_value is dict:
            host = instance.host
            key = f"{instance.name}_{self.name}"
            if host:
                setattr(host.db, key, default_value)

        return default_value

    def _get_default_value(self):
        default_value = self.default_value
        if callable(default_value):
            default_value = default_value()

        return default_value

    def __get__(self, instance, owner):
        if not instance:
            raise ValueError(f"{self.name} can only be retrieved from instances.")

        host = instance.host
        key = f"{instance.name}_{self.name}"
        if host:
            value = getattr(host.db, key, UNSET)
            if value is UNSET or (value is None and self.default_value is not None):
                return self._get_default_value()
            return value
        else:
            return self._cache.get(instance)

    def __set__(self, instance, value):
        if not instance:
            raise ValueError(f"{self.name} can only be set on instances.")

        host = instance.host
        key = f"{instance.name}_{self.name}"
        self._cache[instance] = value
        if host:
            if not value or value == self._get_default_value():
                current_value = getattr(host.db, key, UNSET)
                if current_value is not UNSET:
                    delattr(host.db, key)
            elif value:
                setattr(host.db, key, value)

        # TODO This could be taken from a constructor parameter or just erased
        # TODO Since using setters would remove the need of such a thing
        # TODO Also, the attribute handler already has something similar?
        signal = f'on_change_{self.name}'
        signal_func = getattr(instance, signal, None)
        if signal_func:
            signal_func()

    def __delete__(self, instance):
        if not instance:
            raise ValueError(f"{self.name} can only be deleted from instances.")

        host = instance.host
        if host:
            key = f"{instance.name}_{self.name}"
            delattr(host.db, key)
        del self._cache[instance]
