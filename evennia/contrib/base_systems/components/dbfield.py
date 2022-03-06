"""
Components - ChrisLR 2022

This file contains the Descriptors used to set Fields in Components
"""
from evennia.typeclasses.attributes import AttributeProperty, NAttributeProperty


class DBField(AttributeProperty):
    """
    Component Attribute Descriptor.
    Allows you to set attributes related to a component on the class.
    It uses AttributeProperty under the hood but prefixes the key with the component name.
    """

    def __set_name__(self, owner, name):
        """
        Called when descriptor is first assigned to the class.

        Args:
            owner (object): The component classF on which this is set
            name (str): The name that was used to set the DBField.
        """
        key = f"{owner.name}__{name}"
        self._key = key
        db_fields = getattr(owner, "_db_fields", None)
        if db_fields is None:
            db_fields = {}
            setattr(owner, '_db_fields', db_fields)
        db_fields[name] = self


class NDBField(NAttributeProperty):
    """
    Component In-Memory Attribute Descriptor.
    Allows you to set in-memory attributes related to a component on the class.
    It uses NAttributeProperty under the hood but prefixes the key with the component name.
    """

    def __set_name__(self, owner, name):
        """
        Called when descriptor is first assigned to the class.

        Args:
            owner (object): The component class on which this is set
            name (str): The name that was used to set the DBField.
        """
        key = f"{owner.name}__{name}"
        self._key = key
        ndb_fields = getattr(owner, "_ndb_fields", None)
        if ndb_fields is None:
            ndb_fields = {}
            setattr(owner, '_ndb_fields', ndb_fields)
        ndb_fields[name] = self
