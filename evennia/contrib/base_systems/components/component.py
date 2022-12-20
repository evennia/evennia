"""
Components - ChrisLR 2022

This file contains the base class to inherit for creating new components.
"""
import itertools


class Component:
    """
    This is the base class for components.
    Any component must inherit from this class to be considered for usage.

    Each Component must supply the name, it is used as a slot name but also part of the attribute key.
    """

    name = ""

    def __init__(self, host=None):
        assert self.name, "All Components must have a Name"
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
        for attribute in self._all_db_field_names:
            delattr(self, attribute)

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

        if self.host:
            if self.host == host:
                return
            else:
                raise ComponentRegisterError("Components must not register twice!")

        self.host = host

    def at_removed(self, host):
        """
        This is the method called when a component is removed from a host.

        Args:
            host (object): The host typeclass instance

        """
        if host != self.host:
            raise ComponentRegisterError("Component attempted to remove from the wrong host.")
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
    def nattributes(self):
        """
        Shortcut property returning the host's In-Memory AttributeHandler (Non Persisted).

        Returns:
            AttributeHandler: The Host's In-Memory AttributeHandler

        """
        return self.host.nattributes

    @property
    def _all_db_field_names(self):
        return itertools.chain(self.db_field_names, self.ndb_field_names)

    @property
    def db_field_names(self):
        db_fields = getattr(self, "_db_fields", {})
        return db_fields.keys()

    @property
    def ndb_field_names(self):
        ndb_fields = getattr(self, "_ndb_fields", {})
        return ndb_fields.keys()

    @property
    def tag_field_names(self):
        tag_fields = getattr(self, "_tag_fields", {})
        return tag_fields.keys()


class ComponentRegisterError(Exception):
    pass
