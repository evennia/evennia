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

    def get_mysql_db_version(self):
        """
        This is a helper method for getting the version string
        of a mysql database.
        """
        from django.db import connection
        conn = connection.cursor()
        conn.execute("SELECT VERSION()")
        version = conn.fetchone()
        return version and str(version[0]) or ""
