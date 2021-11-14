UNSET = object()


class DBField(object):
    """
    This is the class to use in components for attributes that bind to their owner's db.
    Allows using a simpler syntax, similar to component.attribute
    Values are stored on the host's db using a prefixed key made of
    the component's name and the attribute name, similar to component__attribute.
    """

    def __init__(self, default_value=None):
        self.default_value = default_value

    def assign_default_value(self, instance):
        default_value = self.get_default_value()
        key = f"{instance.name}__{self.name}"
        self.handler(instance).add(key, default_value)

    def get_default_value(self):
        default_value = self.default_value
        if callable(default_value):
            default_value = default_value()

        return default_value

    def __get__(self, instance, owner):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be retrieved from instances.")

        key = f"{instance.name}__{self.name}"
        value = self.handler(instance).get(key, UNSET)
        if value is UNSET or (value is None and self.default_value is not None):
            return self.get_default_value()

        return value

    def __set__(self, instance, value):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be set on instances.")

        key = f"{instance.name}__{self.name}"
        if not value or value == self.get_default_value():
            current_value = self.handler(instance).get(key, UNSET)
            if current_value is not UNSET:
                self.handler(instance).remove(key)
        elif value:
            self.handler(instance).add(key, value)

    def __set_name__(self, owner, name):
        """ This ensures Components are aware of their db fields """
        self.name = name
        db_fields = getattr(owner, "_db_fields", None)
        if db_fields is None:
            db_fields = {}
            setattr(owner, '_db_fields', db_fields)
        db_fields[name] = self

    def __delete__(self, instance):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be deleted from instances.")

        key = f"{instance.name}__{self.name}"
        self.handler(instance).remove(key)

    @classmethod
    def handler(cls, instance):
        return instance.attributes


class NDBField(DBField):
    """ Similar in usage to DBField except in-memory via the NDB attributes """
    @classmethod
    def handler(cls, instance):
        return instance.nattributes

    def __set_name__(self, owner, name):
        self.name = name
        db_fields = getattr(owner, "_ndb_fields", None)
        if db_fields is None:
            db_fields = {}
            setattr(owner, '_ndb_fields', db_fields)
        db_fields[name] = self


class NoInstanceError(Exception):
    pass
