"""
This is an example command module for showing the pluggable command system
in action. 

You'll need to make sure that this or any new modules you create are added to
game/settings.py under CUSTOM_COMMAND_MODULES or CUSTOM_UNLOGGED_COMMAND_MODULES,
which are tuples of module import path strings. See src/config_defaults.py for more details.

E.g. to add this example command for testing, your entry in game/settings.py would
look like this:

CUSTOM_COMMAND_MODULES = ('game.gamesrc.commands.examples.example',)

(note the extra comma at the end to make this into a Python tuple. It's only
needed if you have only one entry.) You need to restart the Evennia server before new
files are recognized. 

"""

# This is the common global CommandTable object which we'll be adding the
# example command to. We can add any number of commands this way in the
# same file.
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_example(command):
    """    
    This is the help text for the 'example' command, a command to
    show how the pluggable command system works.

    For testing, you can try calling this with different switches and
    arguments, like
       > example/test/test2 Hello
    and see what is returned.

    <<TOPIC:example_auto_help>>

    This is a subtopic to the main example command help entry.
    
    Note that this text is auto-added since auto_help=True
    was set in the call to add_function. Any number of subtopics like
    this one can be added on the fly using the auto-help system. See
    help topics on 'help' and 'help_staff' for more information and
    options.
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

# Add the command to the common global command table. Note that
# since auto_help=True, help entries named "example" and
# "example_auto_help" (as defined in the __doc__ string) will
# automatically be created for us.
GLOBAL_CMD_TABLE.add_command("example", cmd_example, auto_help=True),

#another simple example

def cmd_emote_smile(command):
    """
    Simplistic 'smile' emote. 
    """
    #get the source object (that is, the player using the command)
    caller = command.source_object
    #find name of caller
    name = caller.get_name(show_dbref=False)
    #get the location caller is at
    location = caller.get_location()
    #build the emote
    text = "%s smiles." % name
    #emit the emote to everyone at the current location
    location.emit_to_contents(text)

#add to global command table (no auto_help activated)
GLOBAL_CMD_TABLE.add_command('smile', cmd_emote_smile)





