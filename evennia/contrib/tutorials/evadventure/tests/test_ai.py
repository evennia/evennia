"""
Test the ai module.

"""

from unittest.mock import Mock, patch

from evennia import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from ..characters import EvAdventureCharacter
from ..npcs import EvAdventureMob


class TestAI(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.npc = create_object(EvAdventureMob, key="Goblin", location=self.room1)
        self.pc = create_object(EvAdventureCharacter, key="Player", location=self.room1)

    def tearDown(self):
        super().tearDown()
        self.npc.delete()

    @patch("evennia.contrib.tutorials.evadventure.ai.random.random")
    @patch("evennia.contrib.tutorials.evadventure.ai.log_trace")
    def test_ai_methods(self, mock_log_trace, mock_random):
        self.assertEqual(self.npc.ai.get_state(), "idle")
        self.npc.ai.set_state("roam")
        self.assertEqual(self.npc.ai.get_state(), "roam")

        self.assertEqual(self.npc.ai.get_targets(), [self.pc])
        self.assertEqual(self.npc.ai.get_traversable_exits(), [self.exit])

        probs = {"hold": 0.1, "combat": 0.5, "flee": 0.4}
        mock_random.return_value = 0.3
        self.assertEqual(self.npc.ai.random_probability(probs), "combat")
        mock_random.return_value = 0.7
        self.assertEqual(self.npc.ai.random_probability(probs), "flee")
        mock_random.return_value = 0.95
        self.assertEqual(self.npc.ai.random_probability(probs), "hold")

    def test_ai_run(self):
        self.npc.ai.set_state("roam")
        self.assertEqual(self.npc.ai.get_state(), "roam")

        self.npc.ai.run()
        self.assertEqual(self.npc.ai.get_state(), "combat")
