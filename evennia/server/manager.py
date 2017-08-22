"""
Custom manager for ServerConfig objects.
"""
from django.db import models


class ServerConfigManager(models.Manager):
    """
    This ServerConfigManager implements methods for searching and
    manipulating ServerConfigs directly from the database.

    These methods will all return database objects (or QuerySets)
    directly.

    ServerConfigs are used to store certain persistent settings for
    the server at run-time.

    """

    def conf(self, key=None, value=None, delete=False, default=None):
        """
        Add, retrieve and manipulate config values.

        Args:
            key (str, optional): Name of config.
            value (str, optional): Data to store in this config value.
            delete (bool, optional): If `True`, delete config with `key`.
            default (str, optional): Use when retrieving a config value
                by a key that does not exist.
        Returns:
            all (list): If `key` was not given - all stored config values.
            value (str): If `key` was given, this is the stored value, or
                `default` if no matching `key` was found.

        """
        if not key:
            return self.all()
        elif delete is True:
            for conf in self.filter(db_key=key):
                conf.delete()
        elif value is not None:
            conf = self.filter(db_key=key)
            if conf:
                conf = conf[0]
            else:
                conf = self.model(db_key=key)
            conf.value = value  # this will pickle
        else:
            conf = self.filter(db_key=key)
            if not conf:
                return default
            return conf[0].value
        return None
