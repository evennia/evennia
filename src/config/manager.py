"""
Custom manager for ConfigValue objects.
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType

class ConfigValueManager(models.Manager):
    """
    This gives some access methods to search and edit
    the configvalue database. 
    """
    def set_configvalue(self, db_key, db_value):
        "Set new/overwrite old config value"
        db_objs = self.filter(db_key=db_key)
        if db_objs:
            # Overwrite old config value
            db_obj = db_objs[0]
            db_obj.db_value = db_value
            db_obj.save()
        else:
            # No old conf found. Create a new one.
            ConfigValue = ContentType.objects.get(app_label="config", 
                                  model="configvalue").model_class()
            new_conf = ConfigValue()
            new_conf.db_key = db_key
            new_conf.db_value = db_value
            new_conf.save()

    def get_configvalue(self, config_key, default=None):
        """
        Retrieve a configuration value.
        
        config_key - the name of the configuration option
        """
        try:
            return self.get(db_key__iexact=config_key).db_value
        except self.model.DoesNotExist:
            return default

    # a simple wrapper for consistent naming in utils.search
    def config_search(self, ostring):
        """
        Retrieve a configuration value.

        ostring - a (unique) configuration key
        """
        return self.get_configvalue(ostring)

    def conf(self, db_key=None, db_value=None, delete=False, default=None):
        """
        Wrapper to access the Config database.
        This will act as a get/setter, lister or deleter
        depending on how many arguments are supplied.
        Due to its design, you cannot set conf to a value of
        None using this method, use objects.set_configvalue
        instead. 
        """
        if not db_key:
            return self.all()
        elif delete == True:
            conf = self.get_configvalue(db_key)
            if conf:
                conf.delete()
        elif db_value != None:
            self.set_configvalue(db_key, db_value)
        else:
            return self.get_configvalue(db_key, default=default)


class ConnectScreenManager(models.Manager):
    """
    This handles the random initial login screen system. 
    """
    def get_random_connect_screen(self):
        """
        Returns a random active connect screen.
        """
        try:
            return self.filter(db_is_active=True).order_by('?')[0]
        except IndexError:
            ConnectScreen = ContentType.objects.get(app_label="config", 
                                                    model="connectscreen").model_class()            
            text = "This is a placeholder connect screen. "
            text += "Remind your admin to edit it."
            new_screen = ConnectScreen(db_key='Default',
                                       db_text=text,
                                       db_is_active=True)
            new_screen.save()
            return new_screen


