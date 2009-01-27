"""
This is an example command module that may be copied and used to serve as the
basis to newly created modules. You'll need to make sure that this or any new
modules are added to settings.py under CUSTOM_COMMAND_MODULES or
CUSTOM_UNLOGGED_COMMAND_MODULES, which are tuples of module import path strings.
See src/config_defaults.py for more details.
"""
# This is the common global CommandTable object which we'll be adding the
# example command to.
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_example(command):
    """
    An example command to show how the pluggable command system works.
    """
    # By building one big string and passing it at once, we cut down on a lot
    # of emit_to() calls, which is generally a good idea.
    retval = "----- Example Command -----\n\r"
    # source_object is the object executing the command
    retval += " Source object: %s\n\r" % command.source_object
    # session points to a user Session (session.py) object (if applicable)
    retval += " Session: %s\n\r" % command.session
    # The raw, un-parsed input
    retval += " Raw input: %s\n\r" % command.raw_input
    # The command name being executed
    retval += " Command: %s\n\r" % command.command_string
    # A list of switches provided (if any)
    retval += " Switches: %s\n\r" % command.command_switches
    # A string with any arguments provided with the command
    retval += " Arguments: %s\n\r" % command.command_argument
    # The function that was looked up via cmdtable.py
    retval += " Function: %s\n\r" % command.command_function
    # Extra variables passed with cmdtable.py's add_command().
    retval += " Extra vars: %s\n\r" % command.extra_vars
    command.source_object.emit_to(retval)
# Add the command to the common global command table.
GLOBAL_CMD_TABLE.add_command("example", cmd_example),