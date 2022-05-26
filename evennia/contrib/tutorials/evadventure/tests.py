"""
Tests for EvAdventure.

"""

from parameterized import parameterized
from unittest.mock import patch, MagicMock, call
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest
from .characters import EvAdventureCharacter
from .objects import EvAdventureObject
from . import enums
from . import combat_turnbased
from . import rules
from . import random_tables


class EvAdventureMixin:
    def setUp(self):
        super().setUp()
        self.character = create.create_object(EvAdventureCharacter, key="testchar")
        self.helmet = create.create_object(EvAdventureObject, key="helmet",
                                          attributes=[("wear_slot", "helmet")])
        self.armor = create.create_object(EvAdventureObject, key="armor",
                                         attributes=[("wear_slot", "armor")])
        self.weapon = create.create_object(EvAdventureObject, key="weapon",
                                          attributes=[("wield_slot", "weapon")])
        self.shield = create.create_object(EvAdventureObject, key="shield",
                                          attributes=[("wield_slot", "shield")])

class EvAdventureEquipmentTest(EvAdventureMixin, BaseEvenniaTest):
    pass


class EvAdventureTurnbasedCombatHandlerTest(EvAdventureMixin, BaseEvenniaTest):
    """
    Test the turn-based combat-handler implementation.

    """
    def setUp(self):
        super().setUp()
        self.combathandler = combat_turnbased.EvAdventureCombatHandler()
        self.combathandler.add_combatant(self.character)

    def test_remove_combatant(self):
        self.combathandler.remove_combatant(self.character)


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
            self.roll_engine.roll('100d6', max_number=10)  # too many die
        with self.assertRaises(TypeError):
            self.roll_engine.roll('100')  # no d
        with self.assertRaises(TypeError):
            self.roll_engine.roll('dummy')  # non-numerical
        with self.assertRaises(TypeError):
            self.roll_engine.roll('Ad4')  # non-numerical
        with self.assertRaises(TypeError):
            self.roll_engine.roll('1d10000')  # limit is d1000

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_with_advantage_disadvantage(self, mock_randint):
        mock_randint.return_value = 9

        # no advantage/disadvantage
        self.assertEqual(self.roll_engine.roll_with_advantage_or_disadvantage(), 9)
        mock_randint.assert_called_once()
        mock_randint.reset_mock()

        # cancel each other out
        self.assertEqual(
            self.roll_engine.roll_with_advantage_or_disadvantage(
                disadvantage=True, advantage=True), 9)
        mock_randint.assert_called_once()
        mock_randint.reset_mock()

        # run with advantage/disadvantage
        self.assertEqual(
            self.roll_engine.roll_with_advantage_or_disadvantage(advantage=True), 9)
        mock_randint.assert_has_calls([call(1, 20), call(1, 20)])
        mock_randint.reset_mock()

        self.assertEqual(
            self.roll_engine.roll_with_advantage_or_disadvantage(disadvantage=True), 9)
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
            (False, None))
        self.assertEqual(
            self.roll_engine.saving_throw(character, bonus_type=enums.Ability.DEX, modifier=1),
            (False, None))
        self.assertEqual(
            self.roll_engine.saving_throw(
                character,
                advantage=True,
                bonus_type=enums.Ability.DEX, modifier=6),
            (False, None))
        self.assertEqual(
            self.roll_engine.saving_throw(
                character,
                disadvantage=True,
                bonus_type=enums.Ability.DEX, modifier=7),
            (True, None))

        mock_randint.return_value = 1
        self.assertEqual(
            self.roll_engine.saving_throw(
                character,
                disadvantage=True,
                bonus_type=enums.Ability.STR, modifier=2),
            (False, enums.Ability.CRITICAL_FAILURE))

        mock_randint.return_value = 20
        self.assertEqual(
            self.roll_engine.saving_throw(
                character,
                disadvantage=True,
                bonus_type=enums.Ability.STR, modifier=2),
            (True, enums.Ability.CRITICAL_SUCCESS))

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_opposed_saving_throw(self, mock_randint):
        mock_randint.return_value = 10

        attacker, defender = MagicMock(), MagicMock()
        attacker.strength = 1
        defender.armor = 2

        self.assertEqual(
            self.roll_engine.opposed_saving_throw(
                attacker, defender,
                attack_type=enums.Ability.STR, defense_type=enums.Ability.ARMOR
            ),
            (False, None)
        )
        self.assertEqual(
            self.roll_engine.opposed_saving_throw(
                attacker, defender,
                attack_type=enums.Ability.STR, defense_type=enums.Ability.ARMOR,
                modifier=2
            ),
            (True, None)
        )

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_random_table(self, mock_randint):
        mock_randint.return_value = 10

        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['physique']),
            "scrawny"
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['vice']),
            "irascible"
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['alignment']),
            "neutrality"
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['helmets and shields']),
            "no helmet or shield"
        )
        # testing faulty rolls outside of the table ranges
        mock_randint.return_value = 25
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['helmets and shields']),
            "helmet and shield"
        )
        mock_randint.return_value = -10
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation['helmets and shields']),
            "no helmet or shield"
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
        character.hp_max = 8
        character.hp = 1
        character.constitution = 1

        mock_randint.return_value = 5
        self.roll_engine.heal_from_rest(character)
        self.assertEqual(character.hp, 7)   # hp + 1d8 + consititution bonus
        mock_randint.assert_called_with(1, 8)  # 1d8

        self.roll_engine.heal_from_rest(character)
        self.assertEqual(character.hp, 8)   # can't have more than max hp

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def test_roll_death(self, mock_randint):
        character = MagicMock()
        character.strength = 13
        character.hp = 0
        character.hp_max = 8

        # death
        mock_randint.return_value = 1
        self.roll_engine.roll_death(character)
        character.handle_death.assert_called()
        # strength loss
        mock_randint.return_value = 3
        self.roll_engine.roll_death(character)
        self.assertEqual(character.strength, 10)


class EvAdventureCharacterGenerationTest(BaseEvenniaTest):
    """
    Test the Character generator tracing object in the rule engine.

    """

    @patch("evennia.contrib.tutorials.evadventure.rules.randint")
    def setUp(self, mock_randint):
        super().setUp()
        mock_randint.return_value = 10
        self.chargen = rules.EvAdventureCharacterGeneration()

    def test_base_chargen(self):
        self.assertEqual(self.chargen.strength, 2)
        self.assertEqual(self.chargen.physique, "scrawny")
        self.assertEqual(self.chargen.skin, "pockmarked")
        self.assertEqual(self.chargen.hair, "greased")
        self.assertEqual(self.chargen.clothing, "stained")
        self.assertEqual(self.chargen.misfortune, "exiled")
        self.assertEqual(self.chargen.armor, "gambeson")
        self.assertEqual(self.chargen.shield, "shield")
        self.assertEqual(self.chargen.backpack, ['ration', 'ration', 'waterskin',
                                                 'waterskin', 'drill', 'twine'])

    def test_build_desc(self):
        self.assertEqual(
            self.chargen.build_desc(),
            "Herbalist. Wears stained clothes, and has hoarse speech. Has a scrawny physique, "
            "a broken face, pockmarked skin and greased hair. Is honest, but irascible. "
            "Has been exiled in the past. Favors neutrality."
        )


    @parameterized.expand([
        # source, target, value, new_source_val, new_target_val
        (enums.Ability.CON, enums.Ability.STR, 1, 1, 3),
        (enums.Ability.INT, enums.Ability.DEX, 1, 1, 3),
        (enums.Ability.CHA, enums.Ability.CON, 1, 1, 3),
        (enums.Ability.STR, enums.Ability.WIS, 1, 1, 3),
        (enums.Ability.WIS, enums.Ability.CHA, 1, 1, 3),
        (enums.Ability.DEX, enums.Ability.DEX, 1, 2, 2),
    ])
    def test_adjust_attribute(self, source, target, value, new_source_val, new_target_val):
        self.chargen.adjust_attribute(source, target, value)
        self.assertEqual(
            getattr(self.chargen, source.value), new_source_val, f"{source}->{target}")
        self.assertEqual(
            getattr(self.chargen, target.value), new_target_val, f"{source}->{target}")

    def test_adjust_consecutive(self):
        # gradually shift all to STR (starts at 2)
        self.chargen.adjust_attribute(enums.Ability.CON, enums.Ability.STR, 1)
        self.chargen.adjust_attribute(enums.Ability.CHA, enums.Ability.STR, 1)
        self.chargen.adjust_attribute(enums.Ability.DEX, enums.Ability.STR, 1)
        self.chargen.adjust_attribute(enums.Ability.WIS, enums.Ability.STR, 1)
        self.assertEqual(self.chargen.constitution, 1)
        self.assertEqual(self.chargen.strength, 6)

        # max is 6
        with self.assertRaises(ValueError):
            self.chargen.adjust_attribute(enums.Ability.INT, enums.Ability.STR, 1)
        # minimum is 1
        with self.assertRaises(ValueError):
            self.chargen.adjust_attribute(enums.Ability.DEX, enums.Ability.WIS, 1)

        # move all from str to wis
        self.chargen.adjust_attribute(enums.Ability.STR, enums.Ability.WIS, 5)

        self.assertEqual(self.chargen.strength, 1)
        self.assertEqual(self.chargen.wisdom, 6)

    def test_apply(self):
        character = MagicMock()

        self.chargen.apply(character)

        self.assertTrue(character.db.desc.startswith("Herbalist"))
        self.assertEqual(character.armor, "gambeson")

        character.equipment.store.assert_called()
