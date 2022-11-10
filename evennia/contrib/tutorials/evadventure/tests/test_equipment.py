"""
Test the EvAdventure equipment handler.

"""


from unittest.mock import MagicMock, patch

from parameterized import parameterized

from evennia.utils.test_resources import BaseEvenniaTest

from ..enums import Ability, WieldLocation
from ..equipment import EquipmentError
from .mixins import EvAdventureMixin


class TestEquipment(EvAdventureMixin, BaseEvenniaTest):
    def test_count_slots(self):
        self.assertEqual(self.character.equipment.count_slots(), 0)

    def test_max_slots(self):
        self.assertEqual(self.character.equipment.max_slots, 11)
        setattr(self.character, Ability.CON.value, 3)
        self.assertEqual(self.character.equipment.max_slots, 13)

    def test_add__remove(self):
        self.character.equipment.add(self.helmet)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], [self.helmet])
        self.character.equipment.remove(self.helmet)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], [])

    def test_move__get_current_slot(self):
        self.character.equipment.add(self.helmet)
        self.assertEqual(
            self.character.equipment.get_current_slot(self.helmet), WieldLocation.BACKPACK
        )
        self.character.equipment.move(self.helmet)
        self.assertEqual(self.character.equipment.get_current_slot(self.helmet), WieldLocation.HEAD)

    def test_get_wearable_or_wieldable_objects_from_backpack(self):
        self.character.equipment.add(self.helmet)
        self.character.equipment.add(self.weapon)

        self.assertEqual(
            self.character.equipment.get_wieldable_objects_from_backpack(), [self.weapon]
        )
        self.assertEqual(
            self.character.equipment.get_wearable_objects_from_backpack(), [self.helmet]
        )

        self.assertEqual(
            self.character.equipment.all(),
            [
                (None, WieldLocation.WEAPON_HAND),
                (None, WieldLocation.SHIELD_HAND),
                (None, WieldLocation.TWO_HANDS),
                (None, WieldLocation.BODY),
                (None, WieldLocation.HEAD),
                (self.helmet, WieldLocation.BACKPACK),
                (self.weapon, WieldLocation.BACKPACK),
            ],
        )

    def _get_empty_slots(self):
        return {
            WieldLocation.BACKPACK: [],
            WieldLocation.WEAPON_HAND: None,
            WieldLocation.SHIELD_HAND: None,
            WieldLocation.TWO_HANDS: None,
            WieldLocation.BODY: None,
            WieldLocation.HEAD: None,
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

        with patch("evennia.contrib.tutorials.evadventure.equipment.inherits_from") as mock_inherit:
            mock_inherit.return_value = True
            if is_ok:
                self.assertTrue(self.character.equipment.validate_slot_usage(obj))
            else:
                with self.assertRaises(EquipmentError):
                    self.character.equipment.validate_slot_usage(obj)

    @parameterized.expand(
        [
            # item, where
            ("helmet", WieldLocation.HEAD),
            ("shield", WieldLocation.SHIELD_HAND),
            ("armor", WieldLocation.BODY),
            ("weapon", WieldLocation.WEAPON_HAND),
            ("big_weapon", WieldLocation.TWO_HANDS),
            ("item", WieldLocation.BACKPACK),
        ]
    )
    def test_move(self, itemname, where):
        self.assertEqual(self.character.equipment.slots, self._get_empty_slots())

        obj = getattr(self, itemname)
        self.character.equipment.move(obj)
        # check that item ended up in the right place
        if where is WieldLocation.BACKPACK:
            self.assertTrue(obj in self.character.equipment.slots[where])
        else:
            self.assertEqual(self.character.equipment.slots[where], obj)

    def test_add(self):
        self.character.equipment.add(self.weapon)
        self.assertEqual(self.character.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertTrue(self.weapon in self.character.equipment.slots[WieldLocation.BACKPACK])

    def test_two_handed_exclusive(self):
        """Two-handed weapons can't be used together with weapon+shield"""
        self.character.equipment.move(self.big_weapon)
        self.assertEqual(self.character.equipment.slots[WieldLocation.TWO_HANDS], self.big_weapon)
        # equipping sword or shield removes two-hander
        self.character.equipment.move(self.shield)
        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], self.shield)
        self.assertEqual(self.character.equipment.slots[WieldLocation.TWO_HANDS], None)
        self.character.equipment.move(self.weapon)
        self.assertEqual(self.character.equipment.slots[WieldLocation.WEAPON_HAND], self.weapon)

        # the two-hander removes the two weapons
        self.character.equipment.move(self.big_weapon)
        self.assertEqual(self.character.equipment.slots[WieldLocation.TWO_HANDS], self.big_weapon)
        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], None)
        self.assertEqual(self.character.equipment.slots[WieldLocation.WEAPON_HAND], None)

    def test_remove__with_obj(self):
        self.character.equipment.move(self.shield)
        self.character.equipment.move(self.item)
        self.character.equipment.add(self.weapon)

        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], self.shield)
        self.assertEqual(
            self.character.equipment.slots[WieldLocation.BACKPACK], [self.item, self.weapon]
        )

        self.assertEqual(self.character.equipment.remove(self.shield), [self.shield])
        self.assertEqual(self.character.equipment.remove(self.item), [self.item])

        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], None)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], [self.weapon])

    def test_remove__with_slot(self):
        self.character.equipment.move(self.shield)
        self.character.equipment.move(self.item)
        self.character.equipment.add(self.helmet)

        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], self.shield)
        self.assertEqual(
            self.character.equipment.slots[WieldLocation.BACKPACK], [self.item, self.helmet]
        )

        self.assertEqual(self.character.equipment.remove(WieldLocation.SHIELD_HAND), [self.shield])
        self.assertEqual(
            self.character.equipment.remove(WieldLocation.BACKPACK), [self.item, self.helmet]
        )

        self.assertEqual(self.character.equipment.slots[WieldLocation.SHIELD_HAND], None)
        self.assertEqual(self.character.equipment.slots[WieldLocation.BACKPACK], [])

    def test_properties(self):
        self.character.equipment.move(self.armor)
        self.assertEqual(self.character.equipment.armor, 1)
        self.character.equipment.move(self.shield)
        self.assertEqual(self.character.equipment.armor, 2)
        self.character.equipment.move(self.helmet)
        self.assertEqual(self.character.equipment.armor, 3)

        self.character.equipment.move(self.weapon)
        self.assertEqual(self.character.equipment.weapon, self.weapon)
        self.character.equipment.move(self.big_weapon)
        self.assertEqual(self.character.equipment.weapon, self.big_weapon)
