"""
This is an example command module for showing the pluggable command
system in action.

You'll need to make sure that this or any new modules you create are
added to game/settings.py under CUSTOM_COMMAND_MODULES or
CUSTOM_UNLOGGED_COMMAND_MODULES, which are tuples of module import
path strings. See src/config_defaults.py for more details.

E.g. to add this example command for testing, your entry in
game/settings.py would look like this:

CUSTOM_COMMAND_MODULES = ('game.gamesrc.commands.examples.example',)

(note the extra comma at the end to make this into a Python
tuple. It's only needed if you have only one entry.) You need to
restart the Evennia server before new files are recognized. Once this
is done once, you don't have to restart again, just use
@reload/commands to use the changes you make to your modules.
"""

# This is the common global CommandTable object which we'll be adding the
# example command(s) to. 
from src.cmdtable import GLOBAL_CMD_TABLE

# The main command definition. We can add any number of commands this way in the
# same file.
def cmd_example(command):
    """    
    example - example command

    Usage:
      @testcommand[/switches] <text>

    switches:
      (can be any string, e.g. /test1 or /tom/sarah/peter)

    This is the help text for the 'example' command, a command to
    show how the pluggable command system works.

    For testing, you can try calling this with different switches and
    arguments, like
       > example/test/test2 Hello
    and see what is returned.

    [[example_auto_help]]

    This is a subtopic to the main example command help entry. It is
    done by the help system splitting the text by markup of the
    form [ [title ] ] (with no spaces between the square brackets)
    
    Note that this help entry is auto-added as long as HELP_AUTO
    is not set to False in your game/settings.py file. 
    Any number of subtopics like this one can be added on the fly
    using the auto-help system. See help topics on 'help' and
    'help_markup' for more information and options.
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

    # Some more info for more advanced commands.
    if not command.command_switches and \
           command.command_argument:
        retval += "\n Obs: When no switches, also multi-word\n"
        retval += " command names are possible. Max allowed\n"
        retval += " length is set in game/settings.py.\n"
        retval += " So if there exist a matching command in the\n"
        retval += " command table, Evennia would also allow\n"
        retval += " the following as valid commands (and the\n"
        retval += " argument list would shrink accordingly):\n"
        multi = ""
        for arg in command.command_argument.split():
            multi += " %s" % arg
            retval += "   %s%s\n" % (command.command_string, multi)

    # send string to player
    command.source_object.emit_to(retval)

# Add the command to the common global command table. Note that
# this will auto-create help entries 'example' and
# "example_auto_help" for us.
GLOBAL_CMD_TABLE.add_command("@testcommand", cmd_example)

#
# another simple example
#
def cmd_emote_smile(command):
    """
    smile - break a smile

    Usage:
      smile

    A 'smile' emote. 
    """
    #get the source object (that is, the player using the command)
    source_object = command.source_object
    #find name of caller
    name = source_object.get_name(show_dbref=False)
    #get the location caller is at
    location = source_object.get_location()
    #build the emote
    text = "%s smiles." % name
    #emit the emote to everyone at the current location
    location.emit_to_contents(text)

# add to global command table (we probably want an auto-help entry
# for this, but we are turning auto-help off anyway, to show
# how it works)
GLOBAL_CMD_TABLE.add_command('smile', cmd_emote_smile,
                             auto_help_override=False)
