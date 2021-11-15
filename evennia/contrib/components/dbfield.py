from evennia.typeclasses.attributes import AttributeProperty, NAttributeProperty


class DBField(AttributeProperty):
    """
    Similar to AttributeProperty but prefixes the key with the component name
    """

    def __set_name__(self, owner, name):
        key = f"{owner}__{name}"
        self._key = key
        db_fields = getattr(owner, "_db_fields", None)
        if db_fields is None:
            db_fields = {}
            setattr(owner, '_db_fields', db_fields)
        db_fields[name] = self


class NDBField(NAttributeProperty):
    """
    Similar to NAttributeProperty but prefixes the key with the component name
    """

    def __set_name__(self, owner, name):
        key = f"{owner}__{name}"
        self._key = key
        ndb_fields = getattr(owner, "_ndb_fields", None)
        if ndb_fields is None:
            ndb_fields = {}
            setattr(owner, '_ndb_fields', ndb_fields)
        ndb_fields[name] = self
