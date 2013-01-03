"""

Server Configuration flags

This holds persistent server configuration flags.

Config values should usually be set through the
manager's conf() method.

"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.db import models
from src.utils.idmapper.models import SharedMemoryModel
from src.utils import logger, utils
from src.server.manager import ServerConfigManager

#------------------------------------------------------------
#
# ServerConfig
#
#------------------------------------------------------------

class ServerConfig(SharedMemoryModel):
    """
    On-the fly storage of global settings.

    Properties defined on ServerConfig:
      key - main identifier
      value - value stored in key. This is a pickled storage.

    """

    #
    # ServerConfig database model setup
    #
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # main name of the database entry
    db_key = models.CharField(max_length=64, unique=True)
    # config value
    db_value = models.TextField(blank=True)

    objects = ServerConfigManager()

    # used by Attributes eventually storing this safely
    _db_model_name = "serverconfig"

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def __key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def __key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def __key_del(self):
        "Deleter. Allows for del self.key. Deletes entry."
        self.delete()
    key = property(__key_get, __key_set, __key_del)

    # value property (wraps db_value)
    #@property
    def __value_get(self):
        "Getter. Allows for value = self.value"
        return pickle.loads(str(self.db_value))
    #@value.setter
    def __value_set(self, value):
        "Setter. Allows for self.value = value"
        if utils.has_parent('django.db.models.base.Model', value):
            # we have to protect against storing db objects.
            logger.log_errmsg("ServerConfig cannot store db objects! (%s)" % value)
            return
        self.db_value = pickle.dumps(value)
        self.save()
    #@value.deleter
    def __value_del(self):
        "Deleter. Allows for del self.value. Deletes entry."
        self.delete()
    value = property(__value_get, __value_set, __value_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Server Config value"
        verbose_name_plural = "Server Config values"

    #
    # ServerConfig other methods
    #

    def __unicode__(self):
        return "%s : %s" % (self.key, self.value)

    def store(self, key, value):
        """
        Wrap the storage (handles pickling)
        """
        self.key = key
        self.value = value
