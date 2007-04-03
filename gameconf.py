from apps.config.models import ConfigValue
"""
Handle the setting/retrieving of server config directives.
"""

def get_configvalue(configname):
   """
   Retrieve a configuration value.
   """
   return ConfigValue.objects.get(conf_key=configname).conf_value
