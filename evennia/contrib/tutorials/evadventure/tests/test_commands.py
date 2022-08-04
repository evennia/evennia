"""
Test the EvAdventure commands.

"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import BaseEvenniaCommandTest

from .. import commands
from .mixins import EvAdventureMixin


class TestEvAdventureCommands(EvAdventureMixin, BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        # needed for the .call mechanism
        self.char1 = self.character

    def test_inventory(self):
        self.call(
            commands.CmdInventory(),
            "inventory",
            """
You are fighting with your bare fists and have no shield.
You wear no armor and no helmet.
Backpack is empty.
You use 0/11 equipment slots.
""".strip(),
        )
