"""
Components - ChrisLR 2022

This file contains the base class to inherit for creating new components.
"""

from evennia.commands.cmdset import CmdSet

from . import exceptions
from .listing import COMPONENT_LISTING


class BaseComponent(type):
    """
    This is the metaclass for components,
    responsible for registering components to the listing.
    """

    def __new__(cls, name, parents, attrs):
        """
        Every class that uses this metaclass will be registered
        as a component in the Component Listing using its name.
        All of them require a unique name.
        """
        attrs_name = attrs.get("name")
        if attrs_name and not COMPONENT_LISTING.get(attrs_name):
            new_fields = {}
            attrs["_fields"] = new_fields
            for parent in parents:
                _parent_fields = getattr(parent, "_fields")
                if _parent_fields:
                    new_fields.update(_parent_fields)

        new_type = super().__new__(cls, name, parents, attrs)
        if new_type.__base__ == object:
            return new_type

        name = getattr(new_type, "name", None)
        if not name:
            raise ValueError(f"Component {new_type} requires a name.")

        if existing_type := COMPONENT_LISTING.get(name):
            if not str(new_type) == str(existing_type):
                raise ValueError(f"Component name {name} is a duplicate, must be unique.")
        else:
            COMPONENT_LISTING[name] = new_type

        return new_type


class Component(metaclass=BaseComponent):
    """
    This is the base class for components.
    Any component must inherit from this class to be considered for usage.

    Each Component must supply the name, it is used as a slot name but also part of the attribute key.
    """

    __slots__ = ("host",)

    name = ""
    slot = None

    _fields: dict | None = None

    def __init__(self, host=None):
        assert self.name, "All Components must have a name"
        self.host = host

    @classmethod
    def default_create(cls, host):
        """
        This is called when the host is created
         and should return the base initialized state of a component.

        Args:
            host (object): The host typeclass instance

        Returns:
            Component: The created instance of the component

        """
        new = cls(host)
        return new

    @classmethod
    def create(cls, host, **kwargs):
        """
        This is the method to call when supplying kwargs to initialize a component.

        Args:
            host (object): The host typeclass instance
            **kwargs: Key-Value of default values to replace.
                      To persist the value, the key must correspond to a DBField.

        Returns:
            Component: The created instance of the component

        """

        new = cls.default_create(host)
        for key, value in kwargs.items():
            setattr(new, key, value)

        return new

    def cleanup(self):
        """
        This deletes all component attributes from the host's db
        """
        for name in self._fields.keys():
            delattr(self, name)

    @classmethod
    def load(cls, host):
        """
        Loads a component instance
         This is called whenever a component is loaded (ex: Server Restart)

        Args:
            host (object): The host typeclass instance

        Returns:
            Component: The loaded instance of the component

        """
        return cls(host)

    def at_added(self, host):
        """
        This is the method called when a component is registered on a host.

        Args:
            host (object): The host typeclass instance

        """
        if self.host and self.host != host:
            raise exceptions.InvalidComponentError("Components must not register twice!")

        self.host = host

    def at_removed(self, host):
        """
        This is the method called when a component is removed from a host.

        Args:
            host (object): The host typeclass instance

        """
        if host != self.host:
            raise ValueError("Component attempted to remove from the wrong host.")

        self.host = None

    @property
    def attributes(self):
        """
        Shortcut property returning the host's AttributeHandler.

        Returns:
            AttributeHandler: The Host's AttributeHandler

        """
        return self.host.attributes

    @property
    def pk(self):
        """
        Shortcut property returning the host's primary key.

        Returns:
            int: The Host's primary key.

        Notes:
            This is requried to allow AttributeProperties to correctly update `_SaverMutable` data
            (like lists) in-place (since the DBField sits on the Component which doesn't itself
            have a primary key, this save operation would otherwise fail).

        """
        return self.host.pk

    @property
    def nattributes(self):
        """
        Shortcut property returning the host's In-Memory AttributeHandler (Non Persisted).

        Returns:
            AttributeHandler: The Host's In-Memory AttributeHandler

        """
        return self.host.nattributes

    @classmethod
    def add_field(cls, name, field):
        cls._fields[name] = field

    @classmethod
    def get_fields(cls):
        return tuple(cls._fields.values())

    @classmethod
    def get_component_slot(cls):
        return cls.slot or cls.name
