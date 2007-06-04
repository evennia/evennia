from apps.config.models import ConfigValue
import os
"""
Handle the setting/retrieving of server config directives.
"""

def host_os_is(osname):
   """
   Check to see if the host OS matches the query.
   """
   if os.name == osname:
      return True
   return False

def get_configvalue(configname):
   """
   Retrieve a configuration value.
   """
   return ConfigValue.objects.get(conf_key=configname).conf_value

def set_configvalue(configname, newvalue):
   """
   Sets a configuration value with the specified name.
   """
   conf = ConfigValue.objects.get(conf_key=configname)
   conf.conf_value = newvalue
   conf.save()
