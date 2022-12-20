"""
Tests of simpledoor.

"""


from evennia.commands.default.tests import BaseEvenniaCommandTest

from . import simpledoor


class TestSimpleDoor(BaseEvenniaCommandTest):
    def test_cmdopen(self):
        self.call(
            simpledoor.CmdOpen(),
            "newdoor;door:contrib.grid.simpledoor.SimpleDoor,backdoor;door = Room2",
            "Created new Exit 'newdoor' from Room to Room2 (aliases: door).|Note: A door-type exit was "
            "created - ignored eventual custom return-exit type.|Created new Exit 'newdoor' from Room2 to Room (aliases: door).",
        )
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "You close newdoor.", cmdstring="close")
        self.call(
            simpledoor.CmdOpenCloseDoor(),
            "newdoor",
            "newdoor is already closed.",
            cmdstring="close",
        )
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "You open newdoor.", cmdstring="open")
        self.call(
            simpledoor.CmdOpenCloseDoor(), "newdoor", "newdoor is already open.", cmdstring="open"
        )
