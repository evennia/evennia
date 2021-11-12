import itertools

from evennia.typeclasses.attributes import AttributeHandler, InMemoryAttributeBackend


class Component:
    name = ""

    def __init__(self, host=None):
        assert self.name, "All Components must have a Name"
        self.host = host
        self._tdb = AttributeHandler(self, InMemoryAttributeBackend) if not host else None
        self._tndb = AttributeHandler(self, InMemoryAttributeBackend) if not host else None

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
        chained = (
            (new.db_field_names, new.attributes),
            (new.ndb_field_names, new.nattributes)
        )
        for fields, handler in chained:
            for field_name in fields:
                provided_value = kwargs.get(field_name)
                if provided_value is None:
                    provided_value = cls.__dict__[field_name].get_default_value()

                setattr(new, field_name, provided_value)

        return new

    @classmethod
    def create(cls, game_object, **kwargs):
        """
        This is the method to call when supplying kwargs to initialize a component.
        Useful with runtime components
        """
        new = cls.default_create(game_object, **kwargs)
        return new

    def cleanup(self):
        """ This cleans all attributes from the host's db """
        for attribute in self._all_db_field_names:
            delattr(self, attribute)

    def duplicate(self, new_host):
        """
        This copies the current values of the component instance
        to a new instance registered to the new host.
        Useful for templates
        """
        new = type(self)(new_host)
        for attribute in self._all_db_field_names:
            value = getattr(self, attribute, None)
            setattr(new, attribute, value)

        return new

    @classmethod
    def load(cls, game_object):
        return cls(game_object)

    def on_register(self, host):
        if not self.host:
            self.host = host
            self._copy_temporary_attributes_to_host()
        else:
            raise ComponentRegisterError("Components should not register twice!")

    def on_unregister(self, host):
        if host != self.host:
            raise ComponentRegisterError("Component attempted to unregister from the wrong host.")
        self.host = None

    def _copy_temporary_attributes_to_host(self):
        host = self.host
        if self._tdb:
            for attribute in self._tdb.all():
                host.attributes.add(attribute.key, attribute.value)
            self._tdb = None

        if self._tndb:
            for attribute in self._tndb.all():
                host.nattributes.add(attribute.key, attribute.value)
            self._tndb = None
            
    @property
    def attributes(self):
        if self.host:
            return self.host.attributes
        else:
            return self._tdb

    @property
    def nattributes(self):
        if self.host:
            return self.host.nattributes
        else:
            return self._tndb

    @property
    def _all_db_field_names(self):
        return itertools.chain(self.db_field_names, self.ndb_field_names)

    @property
    def id(self):
        # This is needed by the AttributeHandler backend but should be unused.
        return id(self)

    @property
    def db_field_names(self):
        db_fields = getattr(self, "_db_fields", {})
        return db_fields.keys()

    @property
    def ndb_field_names(self):
        ndb_fields = getattr(self, "_ndb_fields", {})
        return ndb_fields.keys()


class ComponentRegisterError(Exception):
    pass
