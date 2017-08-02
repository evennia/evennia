from evennia import CmdSet
from tekmunkey.adaptiveDisplay import adaptiveDisplayCommands

class PlayerCmdSet(CmdSet):
    """
    Implements the default command set.
    """
    key = "adaptiveDisplayCommandSet"
    priority = 0

    def at_cmdset_creation(self):
        "Populates the cmdset"
        self.add( adaptiveDisplayCommands.cmdSetScreenWidth() )
        self.add( adaptiveDisplayCommands.cmdTestDisplay() )