from evennia import CmdSet
from findCode import findCodeCommands

class PlayerCmdSet( CmdSet ):
    """
    Implements the default command set.
    """
    key = "devUtilsCommandSet"
    priority = 0

    def at_cmdset_creation( self ):
        "Populates the cmdset"
        self.add( findCodeCommands.cmdFindCode( ) )
