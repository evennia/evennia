"""
Test the EvAdventure commands.

"""

from unittest.mock import call, patch

from anything import Something

from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaCommandTest

from .. import commands
from ..characters import EvAdventureCharacter
from ..npcs import EvAdventureMob, EvAdventureShopKeeper
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

    @patch("evennia.contrib.tutorials.evadventure.commands.join_combat")
    def test_attack(self, mock_join_combat):
        self.location.allow_combat = True

        target = create_object(EvAdventureMob, key="Ogre", location=self.location)

        self.call(commands.CmdAttackTurnBased(), "ogre", "")

        mock_join_combat.assert_called_with(self.char1, target, session=Something)

        target.delete()

    def test_wield_or_wear(self):
        self.char1.equipment.add(self.helmet)
        self.char1.equipment.add(self.weapon)
        self.shield.location = self.location

        self.call(commands.CmdWieldOrWear(), "shield", "Could not find 'shield'")
        self.call(commands.CmdWieldOrWear(), "helmet", "You put helmet on your head.")
        self.call(
            commands.CmdWieldOrWear(),
            "weapon",
            "You hold weapon in your strongest hand, ready for action.",
        )
        self.call(commands.CmdWieldOrWear(), "helmet", "You are already using helmet.")

    def test_remove(self):
        self.char1.equipment.add(self.helmet)
        self.call(commands.CmdWieldOrWear(), "helmet", "You put helmet on your head.")

        self.call(commands.CmdRemove(), "helmet", "You stash helmet in your backpack.")

    def test_give__coins(self):
        recipient = create_object(EvAdventureCharacter, key="Friend", location=self.location)
        recipient.coins = 0
        self.char1.coins = 100

        self.call(commands.CmdGive(), "40 coins to friend", "You give Friend 40 coins.")
        self.assertEqual(self.char1.coins, 60)
        self.assertEqual(recipient.coins, 40)

        self.call(commands.CmdGive(), "10 to friend", "You give Friend 10 coins.")
        self.assertEqual(self.char1.coins, 50)
        self.assertEqual(recipient.coins, 50)

        self.call(commands.CmdGive(), "60 to friend", "You only have 50 coins to give.")

        recipient.delete()

    @patch("evennia.contrib.tutorials.evadventure.commands.EvMenu")
    def test_give__item(self, mock_EvMenu):

        self.char1.equipment.add(self.helmet)
        recipient = create_object(EvAdventureCharacter, key="Friend", location=self.location)

        self.call(commands.CmdGive(), "helmet to friend", "")

        mock_EvMenu.assert_has_calls(
            (
                call(
                    recipient,
                    {"node_receive": Something, "node_end": Something},
                    item=self.helmet,
                    giver=self.char1,
                ),
                call(
                    self.char1,
                    {"node_give": Something, "node_end": Something},
                    item=self.helmet,
                    receiver=recipient,
                ),
            )
        )

        recipient.delete()

    @patch("evennia.contrib.tutorials.evadventure.npcs.EvMenu")
    def test_talk(self, mock_EvMenu):
        npc = create_object(EvAdventureShopKeeper, key="shopkeep", location=self.location)

        npc.menudata = {"foo": None, "bar": None}

        self.call(commands.CmdTalk(), "shopkeep", "")

        mock_EvMenu.assert_called_with(
            self.char1,
            {"foo": None, "bar": None},
            startnode="node_start",
            session=None,
            npc=npc,
        )
