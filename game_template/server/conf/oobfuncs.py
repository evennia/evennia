"""
OOB configuration.

This module should be included in (or replace) the
default module set in settings.OOB_PLUGIN_MODULES

All functions defined in this module are made available
to be called by the OOB handler.

See src/server/oob_msdp.py for more information.

    function execution - the oob protocol can execute a function directly on
                         the server. The available functions must be defined
                         as global functions via settings.OOB_PLUGIN_MODULES.
    repeat func execution - the oob protocol can request a given function be
                            executed repeatedly at a regular interval. This
                            uses an internal script pool.
    tracking - the oob protocol can request Evennia to track changes to
               fields on objects, as well as changes in Attributes. This is
               done by dynamically adding tracker-objects on entities. The
               behaviour of those objects can be customized via
               settings.OOB_PLUGIN_MODULES.

oob functions have the following call signature:
    function(caller, session, *args, **kwargs)

oob trackers should inherit from the OOBTracker class in src/server.oob_msdp.py
    and implement a minimum of the same functionality.

a global function oob_error will be used as optional error management.

"""

# import the contents of the default msdp module
from src.server.oob_cmds import *

