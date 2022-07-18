"""
Test the rules and chargen.

"""

from unittest.mock import MagicMock, call, patch

from anything import Something
from evennia.utils.test_resources import BaseEvenniaTest
from parameterized import parameterized

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
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation["physique"]
            ),
            "scrawny",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table("1d20", random_tables.character_generation["vice"]),
            "irascible",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation["alignment"]
            ),
            "neutrality",
        )
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation["helmets and shields"]
            ),
            "no helmet or shield",
        )
        # testing faulty rolls outside of the table ranges
        mock_randint.return_value = 25
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation["helmets and shields"]
            ),
            "helmet and shield",
        )
        mock_randint.return_value = -10
        self.assertEqual(
            self.roll_engine.roll_random_table(
                "1d20", random_tables.character_generation["helmets and shields"]
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
        character.hp_max = 8
        character.hp = 1
        character.constitution = 1

        mock_randint.return_value = 5
        self.roll_engine.heal_from_rest(character)
        self.assertEqual(character.hp, 7)  # hp + 1d8 + consititution bonus
        mock_randint.assert_called_with(1, 8)  # 1d8

        self.roll_engine.heal_from_rest(character)
        self.assertEqual(character.hp, 8)  # can't have more than max hp

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


class EvAdventureCharacterGenerationTest(BaseEvenniaTest):
    """
    Test the Character generator in the rule engine.

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
        self.assertEqual(
            self.chargen.backpack, ["ration", "ration", "waterskin", "waterskin", "drill", "twine"]
        )

    def test_build_desc(self):
        self.assertEqual(
            self.chargen.build_desc(),
            "Herbalist. Wears stained clothes, and has hoarse speech. Has a scrawny physique, "
            "a broken face, pockmarked skin and greased hair. Is honest, but irascible. "
            "Has been exiled in the past. Favors neutrality.",
        )

    @parameterized.expand(
        [
            # source, target, value, new_source_val, new_target_val
            (enums.Ability.CON, enums.Ability.STR, 1, 1, 3),
            (enums.Ability.INT, enums.Ability.DEX, 1, 1, 3),
            (enums.Ability.CHA, enums.Ability.CON, 1, 1, 3),
            (enums.Ability.STR, enums.Ability.WIS, 1, 1, 3),
            (enums.Ability.WIS, enums.Ability.CHA, 1, 1, 3),
            (enums.Ability.DEX, enums.Ability.DEX, 1, 2, 2),
        ]
    )
    def test_adjust_attribute(self, source, target, value, new_source_val, new_target_val):
        self.chargen.adjust_attribute(source, target, value)
        self.assertEqual(getattr(self.chargen, source.value), new_source_val, f"{source}->{target}")
        self.assertEqual(getattr(self.chargen, target.value), new_target_val, f"{source}->{target}")

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

        character.equipment.add.assert_called()


class EvAdventureEquipmentTest(EvAdventureMixin, BaseEvenniaTest):
    """
    Test the equipment mechanism.

    """

    def _get_empty_slots(self):
        return {
            enums.WieldLocation.BACKPACK: [],
            enums.WieldLocation.WEAPON_HAND: None,
            enums.WieldLocation.SHIELD_HAND: None,
            enums.WieldLocation.TWO_HANDS: None,
            enums.WieldLocation.BODY: None,
            enums.WieldLocation.HEAD: None,
        }

    def test_equipmenthandler_max_slots(self):
        self.assertEqual(self.character.equipment.max_slots, 11)

    @parameterized.expand(
        [
            # size, pass_validation?
            (1, True),
            (2, True),
            (11, True),
            (12, False),
            (20, False),
            (25, False),
        ]
    )
    def test_validate_slot_usage(self, size, is_ok):
        obj = MagicMock()
        obj.size = size

        if is_ok:
            self.assertTrue(self.character.equipment.validate_slot_usage(obj))
        else:
            with self.assertRaises(equipment.EquipmentError):
                self.character.equipment.validate_slot_usage(obj)

    @parameterized.expand(
        [
            # item, where
            ("helmet", enums.WieldLocation.HEAD),
            ("shield", enums.WieldLocation.SHIELD_HAND),
            ("armor", enums.WieldLocation.BODY),
            ("weapon", enums.WieldLocation.WEAPON_HAND),
            ("big_weapon", enums.WieldLocation.TWO_HANDS),
            ("item", enums.WieldLocation.BACKPACK),
        ]
    )
    def test_use(self, itemname, where):
        self.assertEqual(self.character.equipment.slots, self._get_empty_slots())

        obj = getattr(self, itemname)
        self.character.equipment.use(obj)
        # check that item ended up in the right place
        if where is enums.WieldLocation.BACKPACK:
            self.assertTrue(obj in self.character.equipment.slots[where])
        else:
            self.assertEqual(self.character.equipment.slots[where], obj)

    def test_add(self):
        self.character.equipment.add(self.weapon)
        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.WEAPON_HAND], None)
        self.assertTrue(self.weapon in self.character.equipment.slots[enums.WieldLocation.BACKPACK])

    def test_two_handed_exclusive(self):
        """Two-handed weapons can't be used together with weapon+shield"""
        self.character.equipment.use(self.big_weapon)
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.TWO_HANDS], self.big_weapon
        )
        # equipping sword or shield removes two-hander
        self.character.equipment.use(self.shield)
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], self.shield
        )
        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.TWO_HANDS], None)
        self.character.equipment.use(self.weapon)
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.WEAPON_HAND], self.weapon
        )

        # the two-hander removes the two weapons
        self.character.equipment.use(self.big_weapon)
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.TWO_HANDS], self.big_weapon
        )
        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], None)
        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.WEAPON_HAND], None)

    def test_remove__with_obj(self):
        self.character.equipment.use(self.shield)
        self.character.equipment.use(self.item)
        self.character.equipment.add(self.weapon)

        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], self.shield
        )
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.BACKPACK], [self.item, self.weapon]
        )

        self.assertEqual(self.character.equipment.remove(self.shield), [self.shield])
        self.assertEqual(self.character.equipment.remove(self.item), [self.item])

        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], None)
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.BACKPACK], [self.weapon]
        )

    def test_remove__with_slot(self):
        self.character.equipment.use(self.shield)
        self.character.equipment.use(self.item)
        self.character.equipment.add(self.helmet)

        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], self.shield
        )
        self.assertEqual(
            self.character.equipment.slots[enums.WieldLocation.BACKPACK], [self.item, self.helmet]
        )

        self.assertEqual(
            self.character.equipment.remove(enums.WieldLocation.SHIELD_HAND), [self.shield]
        )
        self.assertEqual(
            self.character.equipment.remove(enums.WieldLocation.BACKPACK), [self.item, self.helmet]
        )

        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.SHIELD_HAND], None)
        self.assertEqual(self.character.equipment.slots[enums.WieldLocation.BACKPACK], [])

    def test_properties(self):
        self.character.equipment.use(self.armor)
        self.assertEqual(self.character.equipment.armor, 1)
        self.character.equipment.use(self.shield)
        self.assertEqual(self.character.equipment.armor, 2)
        self.character.equipment.use(self.helmet)
        self.assertEqual(self.character.equipment.armor, 3)

        self.character.equipment.use(self.weapon)
        self.assertEqual(self.character.equipment.weapon, self.weapon)
        self.character.equipment.use(self.big_weapon)
        self.assertEqual(self.character.equipment.weapon, self.big_weapon)
