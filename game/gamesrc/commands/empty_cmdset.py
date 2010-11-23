"""
This is the second component of using a Command in your game - a
command set.  A cmdset groups any number of commands together. CmdSets
are stored on character and objects and all available cmdsets are
searched when Evennia tries to determine if a command is
available. Sets can be merged and combined in many different ways (see
the docs).

You can use the classes below as templates for extending the game with
new command sets; you can also import the default Evennia cmdset and
extend/overload that.

To change default cmdset (the one all character start the game with), 
Create your custom commands in other modules 
(inheriting from game.gamesrc.commands.basecommand), add them to a 
cmdset class, then set your settings.CMDSET_DEFAULT to point to this
new cmdset class. 

"""

from src.commands.cmdset import CmdSet
from src.commands.default import cmdset_default

from game.gamesrc.commands.basecommands import Command

class ExampleCmdSet(CmdSet):
    """
    Implements an example cmdset.
    """
    
    key = "ExampleSet"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during 
        its creation. It should populate the set with command instances.

        Here we just add the base Command object.
        """
        self.add(Command())


class ExtendedDefaultSet(cmdset_default.DefaultCmdSet):
    """
    This is an example of how to overload the default command 
    set defined in src/commands/default/cmdset_default.py.

    Here we copy everything by calling the parent, but you can
    copy&paste any combination of the default command to customize
    your default set. Next you change settings.CMDSET_DEFAULT to point
    to this class.
    """
    key = "DefaultMUX"
    
    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(ExtendedDefaultSet, self).at_cmdset_creation()
        
        #
        # any commands you add below will overload the default ones.
        #
        
        
