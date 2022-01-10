import itertools


class Component:
    name = ""

    def __init__(self, host=None):
        assert self.name, "All Components must have a Name"
        self.host = host

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
        """
        new = cls.default_create(host)
        for key, value in kwargs.items():
            setattr(new, key, value)

        return new

    def cleanup(self):
        """ This cleans all component fields from the host's db """
        for attribute in self._all_db_field_names:
            delattr(self, attribute)

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

    def on_removed(self, host):
        if host != self.host:
            raise ComponentRegisterError("Component attempted to remove from the wrong host.")
        self.host = None

    @property
    def attributes(self):
        return self.host.attributes

    @property
    def nattributes(self):
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


class ComponentRegisterError(Exception):
    pass
