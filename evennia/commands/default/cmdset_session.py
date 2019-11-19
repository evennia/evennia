"""
This module stores session-level commands.
"""
from evennia.commands.cmdset import CmdSet
from evennia.commands.default import account


class SessionCmdSet(CmdSet):
    """
    Sets up the unlogged cmdset.
    """

    key = "DefaultSession"
    priority = -20

    def at_cmdset_creation(self):
        "Populate the cmdset"
        self.add(account.CmdSessions())
