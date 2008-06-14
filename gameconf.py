import os
from traceback import format_exc

from apps.config.models import ConfigValue, ConnectScreen
import functions_general
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
    try:
        return ConfigValue.objects.get(conf_key__iexact=configname).conf_value
    except:
        functions_general.log_errmsg("Unable to get config value for %s:\n%s" % (configname, (format_exc())))

def set_configvalue(configname, newvalue):
    """
    Sets a configuration value with the specified name.
    """
    conf = ConfigValue.objects.get(conf_key=configname)
    conf.conf_value = newvalue
    conf.save()
    
