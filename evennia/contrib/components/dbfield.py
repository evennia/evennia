UNSET = object()


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
                self.handler(instance).add(key, default_value)

        return default_value

    def _get_default_value(self):
        default_value = self.default_value
        if callable(default_value):
            default_value = default_value()

        return default_value

    def __get__(self, instance, owner):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be retrieved from instances.")

        host = instance.host
        key = f"{instance.name}_{self.name}"
        if host:
            value = self.handler(instance).get(key, UNSET)
            if value is UNSET or (value is None and self.default_value is not None):
                return self._get_default_value()
            return value
        else:
            return self._cache.get(instance)

    def __set__(self, instance, value):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be set on instances.")

        host = instance.host
        key = f"{instance.name}_{self.name}"
        self._cache[instance] = value
        if host:
            if not value or value == self._get_default_value():
                current_value = self.handler(instance).get(key, UNSET)
                if current_value is not UNSET:
                    self.handler(instance).remove(key)
            elif value:
                self.handler(instance).add(key, value)

        # TODO This could be taken from a constructor parameter or just erased
        # TODO Since using setters would remove the need of such a thing
        # TODO Also, the attribute handler already has something similar?
        # signal = f'on_change_{self.name}'
        # signal_func = getattr(instance, signal, None)
        # if signal_func:
        #     signal_func()

    def __delete__(self, instance):
        if not instance:
            raise NoInstanceError(f"{self.name} can only be deleted from instances.")

        host = instance.host
        if host:
            key = f"{instance.name}_{self.name}"
            self.handler(instance).remove(key)

        del self._cache[instance]

    @classmethod
    def handler(cls, instance):
        return instance.attributes


class NDBField(DBField):
    """ Similar in usage to DBField except in-memory via the NDB attributes """
    @classmethod
    def handler(cls, instance):
        return instance.nattributes



class NoInstanceError(Exception):
    pass