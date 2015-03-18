"""
This module describes the unlogged state of the default game.
The setting STATE_UNLOGGED should be set to the python path
of the state instance in this module.
"""
from evennia.commands.cmdset import CmdSet
from evennia.commands.default import unloggedin


class UnloggedinCmdSet(CmdSet):
    """
    Sets up the unlogged cmdset.
    """
    key = "DefaultUnloggedin"
    priority = 0

    def at_cmdset_creation(self):
        "Populate the cmdset"
        self.add(unloggedin.CmdUnconnectedConnect())
        self.add(unloggedin.CmdUnconnectedCreate())
        self.add(unloggedin.CmdUnconnectedQuit())
        self.add(unloggedin.CmdUnconnectedLook())
        self.add(unloggedin.CmdUnconnectedHelp())
        self.add(unloggedin.CmdUnconnectedEncoding())
        self.add(unloggedin.CmdUnconnectedScreenreader())
