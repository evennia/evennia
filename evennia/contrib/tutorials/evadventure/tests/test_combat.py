"""
Test EvAdventure combat.

"""

from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.utils import create
from .mixins import EvAdventureMixin
from .. import combat_turnbased
from ..charactersd import EvAdventureCharacter


class EvAdventureTurnbasedCombatHandlerTest(EvAdventureMixin, BaseEvenniaTest):
    """
    Test the turn-based combat-handler implementation.

    """

    @patch(
        "evennia.contrib.tutorials.evadventure.combat_turnbased"
        ".EvAdventureCombatHandler.interval",
        new=-1,
    )
    def setUp(self):
        super().setUp()
        self.combathandler = combat_turnbased.EvAdventureCombatHandler.objects.create()
        self.combatant = self.character
        self.target = create.create_object(EvAdventureCharacter, key="testchar2")
        self.combathandler.add_combatant(self.combatant)
        self.combathandler.add_combatant(self.target)

    def test_remove_combatant(self):
        self.combathandler.remove_combatant(self.character)

    def test_start_turn(self):
        self.combathandler._start_turn()
        self.assertEqual(self.combathandler.turn, 1)
        self.combathandler._start_turn()
        self.assertEqual(self.combathandler.turn, 2)

    def test_end_of_turn__empty(self):
        self.combathandler._end_turn()

    def test_register_and_run_action(self):
        action = combat_turnbased.CombatActionAttack
        action.use = MagicMock()

        self.combathandler.register_action(action, self.combatant)
        self.combathandler._end_turn()
        action.use.assert_called_once()

    @patch("evennia.contrib.tutorials.evadventure.combat_turnbased.rules.randint")
    def test_attack(self, mock_randint):
        mock_randint = 8
        self.combathandler.register_action(
            combat_turnbased.CombatActionAttack, self.combatant, self.target
        )
        self.combathandler._end_turn()
