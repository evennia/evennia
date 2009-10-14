"""
Command Table Module

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
from django.conf import settings
from src.helpsys import helpsystem

class CommandTable(object):
    """
    Stores commands and performs lookups.
    """
    ctable = None
    
    def __init__(self):
        # This ensures there are no leftovers when the class is instantiated.
        self.ctable = {}
    
    def add_command(self, command_string, function, priv_tuple=None,
                    extra_vals=None, help_category="", priv_help_tuple=None,
                    auto_help_override=None):
        """
        Adds a command to the command table.
        
        command_string: (string) Command string (IE: WHO, QUIT, look).
        function: (reference) The command's function.
        priv_tuple: (tuple) String tuple of permissions required for command.
        extra_vals: (dict) Dictionary to add to the Command object.
        
        Auto-help system: (this is only used if settings.HELP_AUTO_ENABLED is active)
        help_category (str): An overall help category where auto-help will place 
                             the help entry. If not given, 'General' is assumed.
        priv_help_tuple (tuple) String tuple of permissions required to view this
                                help entry. If nothing is given, priv_tuple is used. 
        auto_help_override (bool): Override the value in settings.AUTO_HELP_ENABLED with the
                                value given. Use None to not override.  
                                This can be useful when developing a new routine and
                                has made manual changes to help entries of other
                                commands in the database (and so do not want to use global
                                auto-help). It is also used by e.g. the state system
                                to selectively deactive auto-help.
        
        Note: the auto_help system also supports limited markup. You can divide your __doc__
              with markers of any combinations of the forms
                [[Title]]
                [[Title, category]]
                [[Title, (priv_tuple)]]
                [[Title, category, (priv_tuple)]],
             If such markers are found, the system will automatically create 
             separate help topics for each topic. Your main help entry will
             default to the name of your command.
        """
        self.ctable[command_string] = (function, priv_tuple, extra_vals)

        if auto_help_override == None:
            auto_help_override = settings.HELP_AUTO_ENABLED

        if auto_help_override:
            #add automatic help text from the command's doc string            
            topicstr = command_string
            entrytext = function.__doc__
            if not help_category:
                help_category = "General"
            if not priv_help_tuple:
                priv_help_tuple = priv_tuple
            helpsystem.edithelp.add_help_auto(topicstr, help_category,
                                              entrytext, priv_help_tuple)
                        
    def get_command_tuple(self, func_name):
        """
        Returns a reference to the command's tuple. If there are no matches,
        returns false.
        """
        return self.ctable.get(func_name, False)

# Global command table, for authenticated users.
GLOBAL_CMD_TABLE = CommandTable()
# Global unconnected command table, for unauthenticated users.
GLOBAL_UNCON_CMD_TABLE = CommandTable()
