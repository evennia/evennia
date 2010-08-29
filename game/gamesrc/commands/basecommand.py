
"""
This is the parent class for all Commands in Evennia. Inherit from this and 
overload the member functions to define your own commands. 
See commands/default/muxcommand.py for an example. 

"""

from src.commands.command import Command as BaseCommand
from src.permissions import permissions
from src.utils import utils 

class Command(BaseCommand):
    """
    Note that the class's __doc__ string (this text) is
    used by Evennia to create the automatic help entry for
    the command, so make sure to document consistently here. 
    """
    def has_perm(self, srcobj):
        """
        This is called by the cmdhandler to determine
        if srcobj is allowed to execute this command. This
        also determines if the command appears in help etc.

        By default, We use checks of the 'c' type of lock to determine
        if the command should be run. 
        """
        return permissions.has_perm(srcobj, self, 'cmd')

    def parse(self):
        """
        This method is called by the cmdhandler once the command name
        has been identified. It creates a new set of member variables
        that can be later accessed from self.func() (see below)

        The following variables are available for our use when entering this
        method (from the command definition, and assigned on the fly by the
        cmdhandler):
           self.key - the name of this command ('look')
           self.aliases - the aliases of this cmd ('l')
           self.permissions - permission string for this command
           self.help_category - overall category of command
           
           self.caller - the object calling this command
           self.cmdstring - the actual command name used to call this
                            (this allows you to know which alias was used,
                             for example)
           self.args - the raw input; everything following self.cmdstring.
           self.cmdset - the cmdset from which this command was picked. Not
                         often used (useful for commands like 'help' or to 
                         list all available commands etc)
           self.obj - the object on which this command was defined. It is often
                         the same as self.caller. 
        """
        pass


    def func(self):
        """
        This is the hook function that actually does all the work. It is called
         by the cmdhandler right after self.parser() finishes, and so has access
         to all the variables defined therein.         
        """
        # a simple test command to show the available properties
        string = "-" * 50
        string += "\n{w%s{n - Command variables from evennia:\n" % self.key 
        string += "-" * 50
        string += "\nname of cmd (self.key): {w%s{n\n" % self.key 
        string += "cmd aliases (self.aliases): {w%s{n\n" % self.aliases
        string += "cmd perms (self.permissions): {w%s{n\n" % self.permissions
        string += "help category (self.help_category): {w%s{n\n" % self.help_category
        string += "object calling (self.caller): {w%s{n\n" % self.caller
        string += "object storing cmdset (self.obj): {w%s{n\n" % self.obj
        string += "command string given (self.cmdstring): {w%s{n\n" % self.cmdstring        
        # show cmdset.key instead of cmdset to shorten output
        string += utils.fill("current cmdset (self.cmdset): {w%s{n\n" % self.cmdset)
        
        self.caller.msg(string)
