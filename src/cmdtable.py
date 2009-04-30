"""
Command Table Module
---------------------
Each command entry consists of a key and a tuple containing a reference to the
command's function, and a tuple of the permissions to match against. The user
only need have one of the permissions in the permissions tuple to gain
access to the command. Obviously, super users don't have to worry about this
stuff. If the command is open to all (or you want to implement your own
privilege checking in the command function), use None in place of the
permissions tuple.

Commands are located under evennia/src/commands. server.py imports these
based on the value of settings.COMMAND_MODULES and 
settings.CUSTOM_COMMAND_MODULES. Each module imports cmdtable.py and runs
add_command on the command table each command belongs to.
"""

from src.helpsys.management.commands.edit_helpfiles import add_help

class CommandTable(object):
    """
    Stores command tables and performs lookups.
    """
    ctable = None
    
    def __init__(self):
        # This ensures there are no leftovers when the class is instantiated.
        self.ctable = {}
    
    def add_command(self, command_string, function, priv_tuple=None,
                    extra_vals=None, auto_help=False, staff_only=False):
        """
        Adds a command to the command table.
        
        command_string: (string) Command string (IE: WHO, QUIT, look).
        function: (reference) The command's function.
        priv_tuple: (tuple) String tuple of permissions required for command.
        extra_vals: (dict) Dictionary to add to the Command object.

        Auto-help system:
        auto_help (bool): If true, automatically creates/replaces a help topic with the
                    same name as the command_string, using the functions's __doc__ property
                    for help text. 
        staff_help (bool): Only relevant if help_auto is activated; It True, makes the
                     help topic (and all eventual subtopics) only visible to staff.

        Note: the auto_help system also supports limited markup. If you divide your __doc__
              with markers of the form <<TOPIC:MyTopic>>, the system will automatically create
              separate help topics for each topic. Your initial text (if you define no TOPIC)
              will still default to the name of your command.
              You can also custon-set the staff_only flag for individual subtopics by
              using the markup <<TOPIC:STAFF:MyTopic>> and <<TOPIC:NOSTAFF:MyTopic>>. 
        """
        self.ctable[command_string] = (function, priv_tuple, extra_vals)

        if auto_help:            
            #add automatic help text from the command's doc string            
            topicstr = command_string
            entrytext = function.__doc__
            add_help(topicstr, entrytext, staff_only=staff_only,
                     force_create=True, auto_help=True)
                        
    def get_command_tuple(self, func_name):
        """
        Returns a reference to the command's tuple. If there are no matches,
        returns false.
        """
        return self.ctable.get(func_name, False)

"""
Command tables
"""
# Global command table, for authenticated users.
GLOBAL_CMD_TABLE = CommandTable()
# Global unconnected command table, for unauthenticated users.
GLOBAL_UNCON_CMD_TABLE = CommandTable()
