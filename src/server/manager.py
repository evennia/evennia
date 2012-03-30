"""
Custom manager for ServerConfig objects.
"""
from django.db import models

class ServerConfigManager(models.Manager):
    """
    This ServerConfigManager implements methods for searching
    and manipulating ServerConfigs directly from the database.

    These methods will all return database objects
    (or QuerySets) directly.

    ServerConfigs are used to store certain persistent settings for the
    server at run-time.

    Evennia-specific:
    conf

    """
    def conf(self, key=None, value=None, delete=False, default=None):
        """
        Access and manipulate config values
        """
        if not key:
            return self.all()
        elif delete == True:
            for conf in self.filter(db_key=key):
                conf.delete()
        elif value != None:
            conf = self.filter(db_key=key)
            if conf:
                conf = conf[0]
            else:
                conf = self.model(db_key=key)
            conf.value = value # this will pickle
        else:
            conf = self.filter(db_key=key)
            if not conf:
                return default
            return conf[0].value
