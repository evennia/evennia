"""
Custom manager for ConfigValue objects.
"""
from traceback import format_exc
from django.db import models
import functions_log

class ConfigValueManager(models.Manager):
    def get_configvalue(self, configname):
        """
        Retrieve a configuration value.
        """
        try:
            return self.get(conf_key__iexact=configname).conf_value
        except self.model.DoesNotExist:
            functions_log.log_errmsg("Unable to get config value for %s (does not exist):\n%s" % (
                configname, (format_exc())))
            
    def set_configvalue(self, configname, newvalue):
        """
        Sets a configuration value with the specified name.
        Returns the new value for the directive.
        """
        try:
            conf = self.get(conf_key=configname)
            conf.conf_value = newvalue
            conf.save()
            # We'll do this instead of conf.conf_value, might save a DB query.
            return newvalue
        except self.model.DoesNotExist:
            functions_log.log_errmsg("Unable to set config value for %s (does not exist):\n%s" % (
                configname, (format_exc())))
