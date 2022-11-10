"""
Test the rules and chargen.

"""

from unittest.mock import MagicMock, call, patch

from anything import Something
from parameterized import parameterized

from evennia.utils.test_resources import BaseEvenniaTest

from .. import characters, enums, equipment, random_tables, rules
from .mixins import EvAdventureMixin


class EvAdventureRollEngineTest(BaseEvenniaTest):
    """
    Test the roll engine in the rules module. This is the core of any RPG.

    """

    def setUp(self):
        super().setUp()
        self.roll_engine = rules.EvAdventureRollEngine()

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll(self, mock_randint):
        mock_randint.return_value = 8
        self.assertEqual(self.roll_engine.roll("1d6"), 8)
        mock_randint.assert_called_with(1, 6)

        self.assertEqual(self.roll_engine.roll("2d8"), 2 * 8)
        mock_randint.assert_called_with(1, 8)

        self.assertEqual(self.roll_engine.roll("4d12"), 4 * 8)
        mock_randint.assert_called_with(1, 12)

        self.assertEqual(self.roll_engine.roll("8d100"), 8 * 8)
        mock_randint.assert_called_with(1, 100)

    def test_roll_limits(self):
        with self.assertRaises(TypeError):
            self.roll_engine.roll("100d6", max_number=10)  # too many die
        with self.assertRaises(TypeError):
            self.roll_engine.roll("100")  # no d
        with self.assertRaises(TypeError):
            self.roll_engine.roll("dummy")  # non-numerical
        with self.assertRaises(TypeError):
            self.roll_engine.roll("Ad4")  # non-numerical
        with self.assertRaises(TypeError):
            self.roll_engine.roll("1d10000")  # limit is d1000

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_with_advantage_disadvantage(self, mock_randint):
        mock_randint.return_value = 9

        # no advantage/disadvantage
        self.assertEqual(self.roll_engine.roll_with_advantage_or_disadvantage(), 9)
        mock_randint.assert_called_once()
        mock_randint.reset_mock()

        # cancel each other out
        self.assertEqual(
            self.roll_engine.roll_with_advantage_or_disadvantage(disadvantage=True, advantage=True),
            9,
        )
        mock_randint.assert_called_once()
        mock_randint.reset_mock()

        # run with advantage/disadvantage
        self.assertEqual(self.roll_engine.roll_with_advantage_or_disadvantage(advantage=True), 9)
        mock_randint.assert_has_calls([call(1, 20), call(1, 20)])
        mock_randint.reset_mock()

        self.assertEqual(self.roll_engine.roll_with_advantage_or_disadvantage(disadvantage=True), 9)
        mock_randint.assert_has_calls([call(1, 20), call(1, 20)])
        mock_randint.reset_mock()

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_saving_throw(self, mock_randint):
        mock_randint.return_value = 8

        character = MagicMock()
        character.strength = 2
        character.dexterity = 1

        self.assertEqual(
            self.roll_engine.saving_throw(character, bonus_type=enums.Ability.STR),
            (False, None, Something),
        )
        self.assertEqual(
            self.roll_engine.saving_throw(character, bonus_type=enums.Ability.DEX, modifier=1),
            (False, None, Something),
        )
        self.assertEqual(
            self.roll_engine.saving_throw(
                character, advantage=True, bonus_type=enums.Ability.DEX, modifier=6
            ),
            (False, None, Something),
        )
        self.assertEqual(
            self.roll_engine.saving_throw(
                character, disadvantage=True, bonus_type=enums.Ability.DEX, modifier=7
            ),
            (True, None, Something),
        )

        mock_randint.return_value = 1
        self.assertEqual(
            self.roll_engine.saving_throw(
                character, disadvantage=True, bonus_type=enums.Ability.STR, modifier=2
            ),
            (False, enums.Ability.CRITICAL_FAILURE, Something),
        )

        mock_randint.return_value = 20
        self.assertEqual(
            self.roll_engine.saving_throw(
                character, disadvantage=True, bonus_type=enums.Ability.STR, modifier=2
            ),
            (True, enums.Ability.CRITICAL_SUCCESS, Something),
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_opposed_saving_throw(self, mock_randint):
        mock_randint.return_value = 10

        attacker, defender = MagicMock(), MagicMock()
        attacker.strength = 1
        defender.armor = 2

        self.assertEqual(
            self.roll_engine.opposed_saving_throw(
                attacker, defender, attack_type=enums.Ability.STR, defense_type=enums.Ability.ARMOR
            ),
            (False, None, Something),
        )
        self.assertEqual(
            self.roll_engine.opposed_saving_throw(
                attacker,
                defender,
                attack_type=enums.Ability.STR,
                defense_type=enums.Ability.ARMOR,
                modifier=2,
            ),
            (True, None, Something),
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_random_table(self, mock_randint):
        mock_randint.return_value = 10

        self.assertEqual(
            self.roll_engine.roll_random_table("1d20", random_tables.chargen_tables["physique"]),
            "scrawny",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table("1d20", random_tables.chargen_tables["vice"]),
            "irascible",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table("1d20", random_tables.chargen_tables["alignment"]),
            "neutrality",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.chargen_tables["helmets and shields"]
            ),
            "no helmet or shield",
        )
        # testing faulty rolls outside of the table ranges
        mock_randint.return_value = 25
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.chargen_tables["helmets and shields"]
            ),
            "helmet and shield",
        )
        mock_randint.return_value = -10
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.chargen_tables["helmets and shields"]
            ),
            "no helmet or shield",
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_morale_check(self, mock_randint):
        defender = MagicMock()
        defender.morale = 12

        mock_randint.return_value = 7  # 2d6 is rolled, so this will become 14
        self.assertEqual(self.roll_engine.morale_check(defender), False)

        mock_randint.return_value = 3  # 2d6 is rolled, so this will become 6
        self.assertEqual(self.roll_engine.morale_check(defender), True)

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_heal_from_rest(self, mock_randint):
        character = MagicMock()
        character.heal = MagicMock()
        character.hp_max = 8
        character.hp = 1
        character.constitution = 1

        mock_randint.return_value = 5
        self.roll_engine.heal_from_rest(character)
        mock_randint.assert_called_with(1, 8)  # 1d8
        character.heal.assert_called_with(6)  # roll + constitution bonus

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_death(self, mock_randint):
        character = MagicMock()
        character.strength = 13
        character.hp = 0
        character.hp_max = 8

        # death
        mock_randint.return_value = 1
        self.roll_engine.roll_death(character)
        character.at_death.assert_called()
        # strength loss
        mock_randint.return_value = 3
        self.roll_engine.roll_death(character)
        self.assertEqual(character.strength, 10)
