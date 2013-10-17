"""
This module stores session-level commands.
"""
from src.commands.cmdset import CmdSet
from src.commands.default import player

class SessionCmdSet(CmdSet):
    """
    Sets up the unlogged cmdset.
    """
    key = "DefaultSession"
    priority = 0

    def at_cmdset_creation(self):
        "Populate the cmdset"
        self.add(player.CmdSessions())
