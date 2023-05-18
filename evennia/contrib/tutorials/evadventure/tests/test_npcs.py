"""
Test NPC classes.

"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from .. import npcs


class TestNPCBase(EvenniaTest):
    def test_npc_base(self):
        npc = create_object(
            npcs.EvAdventureNPC,
            key="TestNPC",
            attributes=[("hit_dice", 4), ("armor", 1), ("morale", 9)],
        )

        self.assertEqual(npc.hp_multiplier, 4)
        self.assertEqual(npc.hp_max, 16)
        self.assertEqual(npc.strength, 4)
        self.assertEqual(npc.charisma, 4)
