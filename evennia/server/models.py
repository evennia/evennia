"""

Server Configuration flags

This holds persistent server configuration flags.

Config values should usually be set through the
manager's conf() method.

"""
import pickle

from django.db import models
from evennia.utils.idmapper.models import WeakSharedMemoryModel
from evennia.utils import logger, utils
from evennia.utils.dbserialize import to_pickle, from_pickle
from evennia.server.manager import ServerConfigManager
from evennia.utils import picklefield


# ------------------------------------------------------------
#
# ServerConfig
#
# ------------------------------------------------------------


class ServerConfig(WeakSharedMemoryModel):
    """
    On-the fly storage of global settings.

    Properties defined on ServerConfig:

      - key: Main identifier
      - value: Value stored in key. This is a pickled storage.

    """

    #
    # ServerConfig database model setup
    #
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but without the db_* prefix.

    # main name of the database entry
    db_key = models.CharField(max_length=64, unique=True)
    # config value
    # db_value = models.BinaryField(blank=True)

    db_value = picklefield.PickledObjectField(
        "value",
        null=True,
        help_text="The data returned when the config value is accessed. Must be "
        "written as a Python literal if editing through the admin "
        "interface. Attribute values which are not Python literals "
        "cannot be edited through the admin interface.",
    )

    objects = ServerConfigManager()
    _is_deleted = False

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # key property (wraps db_key)
    # @property
    def __key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key

    # @key.setter
    def __key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()

    # @key.deleter
    def __key_del(self):
        "Deleter. Allows for del self.key. Deletes entry."
        self.delete()

    key = property(__key_get, __key_set, __key_del)

    # value property (wraps db_value)
    # @property
    def __value_get(self):
        "Getter. Allows for value = self.value"
        return from_pickle(self.db_value, db_obj=self)

    # @value.setter
    def __value_set(self, value):
        "Setter. Allows for self.value = value"
        if utils.has_parent("django.db.models.base.Model", value):
            # we have to protect against storing db objects.
            logger.log_err("ServerConfig cannot store db objects! (%s)" % value)
            return
        self.db_value = to_pickle(value)
        self.save()

    # @value.deleter
    def __value_del(self):
        "Deleter. Allows for del self.value. Deletes entry."
        self.delete()

    value = property(__value_get, __value_set, __value_del)

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Server Config value"
        verbose_name_plural = "Server Config values"

    #
    # ServerConfig other methods
    #

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__, self.key, self.value)

    def store(self, key, value):
        """
        Wrap the storage.

        Args:
            key (str): The name of this store.
            value (str): The data to store with this `key`.

        """
        self.key = key
        self.value = value
