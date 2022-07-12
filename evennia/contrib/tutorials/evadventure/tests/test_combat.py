"""
Test EvAdventure combat.

"""

from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.utils import create
from .mixins import EvAdventureMixin
from .. import combat_turnbased
from ..characters import EvAdventureCharacter


class EvAdventureTurnbasedCombatHandlerTest(EvAdventureMixin, BaseEvenniaTest):
    """
    Test the turn-based combat-handler implementation.

    """

    maxDiff = None

    @patch(
        "evennia.contrib.tutorials.evadventure.combat_turnbased"
        ".EvAdventureCombatHandler.interval",
        new=-1,
    )
    def setUp(self):
        super().setUp()
        self.combatant = self.character
        self.target = create.create_object(EvAdventureCharacter, key="testchar2")

        # this already starts turn 1
        self.combathandler = combat_turnbased.join_combat(self.combatant, self.target)

    def tearDown(self):
        self.combathandler.delete()

    def test_remove_combatant(self):
        self.combathandler.remove_combatant(self.character)

    def test_start_turn(self):
        self.combathandler._start_turn()
        self.assertEqual(self.combathandler.turn, 2)
        self.combathandler._start_turn()
        self.assertEqual(self.combathandler.turn, 3)

    def test_end_of_turn__empty(self):
        self.combathandler._end_turn()

    def test_register_and_run_action(self):
        action_class = combat_turnbased.CombatActionAttack
        action = self.combathandler.combatant_actions[self.combatant][action_class.key]

        self.combathandler.register_action(self.combatant, action.key)

        self.assertEqual(self.combathandler.action_queue[self.combatant], (action, (), {}))

        action.use = MagicMock()

        self.combathandler._end_turn()
        action.use.assert_called_once()

    @patch("evennia.contrib.tutorials.evadventure.combat_turnbased.rules.randint")
    def test_attack(self, mock_randint):
        mock_randint.return_value = 8
        self.combathandler.register_action(
            combat_turnbased.CombatActionAttack.key, self.combatant, self.target
        )
        self.combathandler._end_turn()
