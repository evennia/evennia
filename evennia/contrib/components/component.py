import abc

from evennia.contrib.components import DBField


class Component(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def name(self):
        pass

    def __init__(self, host=None):
        # TODO Passing a host here is to prevent TDB TNDB from creating
        # TODO Without host, this should instantiate this component's TDB and TNDB
        self.host = host
        self._db_fields = self._get_db_field_names()

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
        for field_name in new._db_fields:
            # TODO AttributeHandler has a batch_add that might give better performance
            provided_value = kwargs.get(field_name)
            if provided_value is not None:
                setattr(new, field_name, provided_value)
            else:
                cls.__dict__[field_name].assign_default_value(new)

        return new

    @classmethod
    def create(cls, game_object, **kwargs):
        """
        This is the method to call when supplying kwargs to initialize a component.
        Useful with runtime components
        """
        new = cls.default_create(game_object)
        return new

    def cleanup(self):
        """ This cleans all attributes from the host's db """
        for attribute in self._db_fields:
            delattr(self, attribute)

    def duplicate(self, new_host):
        """
        This copies the current values of the component instance
        to a new instance registered to the new host.
        Useful for templates
        """
        new = type(self)(new_host)
        for attribute, value in self._get_db_field_values():
            setattr(new, attribute, value)

        return new

    @classmethod
    def load(cls, game_object):
        return cls(game_object)

    def _get_db_field_names(self):
        # TODO This does not include inherited DB Fields, to investigate
        return tuple(name for name, attribute in type(self).__dict__.items()
                     if isinstance(attribute, DBField))

    def _get_db_field_values(self):
        return ((name, getattr(self, name, None)) for name in self._db_fields)

    def on_register(self, host):
        # TODO This here should fetch the host's db, ndb or use its own ndb
        # TODO using its own ndb shud copyover
        if not self.host:
            self.host = host
        else:
            raise ValueError("Components should not register twice!")

    def on_unregister(self, host):
        if host != self.host:
            raise ValueError("Component attempted to unregister from the wrong host.")
        self.host = None

    def at_post_puppet(self, *args, **kwargs):
        pass

    def at_post_unpuppet(self, *args, **kwargs):
        pass
