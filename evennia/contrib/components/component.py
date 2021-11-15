import itertools

from evennia.typeclasses.attributes import AttributeHandler, InMemoryAttributeBackend


class Component:
    name = ""

    def __init__(self, host=None):
        assert self.name, "All Components must have a Name"
        self.host = host
        self._tdb = None
        self._tndb = None

    @classmethod
    def as_template(cls, **kwargs):
        """
        This allows you to create a stand alone Component that will
        store its own values in memory.
        You can then duplicate it or add it to a host later.
        """
        new = cls.default_create(None)
        new._tdb = AttributeHandler(new, InMemoryAttributeBackend)
        new._tndb = AttributeHandler(new, InMemoryAttributeBackend)
        for key, value in kwargs.items():
            setattr(new, key, value)

        return new

    @classmethod
    def default_create(cls, host):
        """
        This is called when the host is created
         and should return the base initialized state of a component.
        """
        new = cls(host)
        return new

    @classmethod
    def create(cls, host, **kwargs):
        """
        This is the method to call when supplying kwargs to initialize a component.
        Useful with runtime components
        """
        new = cls.default_create(host)
        for key, value in kwargs.items():
            setattr(new, key, value)

        return new

    def cleanup(self):
        """ This cleans all component fields from the host's db """
        for attribute in self._all_db_field_names:
            delattr(self, attribute)

    def duplicate(self, new_host=None):
        """
        This copies the current values of the component instance
        to a new instance.

        When passing a host, the values will be written directly to it.
        """
        new = type(self).default_create(new_host)
        for attribute in self._all_db_field_names:
            value = getattr(self, attribute, None)
            setattr(new, attribute, value)

        return new

    @classmethod
    def load(cls, host):
        """ This is called whenever a component is loaded (ex: Server Restart) """
        return cls(host)

    def on_added(self, host):
        if self.host:
            if self.host == host:
                return
            else:
                raise ComponentRegisterError("Components must not register twice!")

        self.host = host
        if self._tdb or self._tndb:
            self._copy_temporary_attributes_to_host()

    def on_removed(self, host):
        if host != self.host:
            raise ComponentRegisterError("Component attempted to remove from the wrong host.")
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
