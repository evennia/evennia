"""
Custom manager for ServerConfig objects.
"""
from django.db import models

class ServerConfigManager(models.Manager):
    """
    This gives some access methods to search and edit
    the configvalue database. 

    If no match is found, return default. 
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
