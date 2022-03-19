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


class TagField:
    """
    Component Descriptor to add a tag to the host.
    """
    def __init__(self, default=None, enforce_single=False):
        self._category_key = None
        self._default = default
        self._enforce_single = enforce_single

    def __set_name__(self, owner, name):
        """
        Called when descriptor is first assigned to the class. It is called with
        the name of the field.

        """
        self._category_key = f"{owner.name}__{name}"
        tag_fields = getattr(owner, "_tag_fields", None)
        if tag_fields is None:
            tag_fields = {}
            setattr(owner, '_tag_fields', tag_fields)
        tag_fields[name] = self

    def __get__(self, instance, owner):
        tag_value = instance.host.tags.get(
            default=self._default,
            category=self._category_key,
        )
        return tag_value

    def __set__(self, instance, value):
        tag_handler = instance.host.tags
        if self._enforce_single:
            tag_handler.clear(category=self._category_key)

        tag_handler.add(
            key=self._key,
            category=self._category_key,
        )

    def __delete__(self, instance):
        instance.host.tags.clear(category=self._category_key)
