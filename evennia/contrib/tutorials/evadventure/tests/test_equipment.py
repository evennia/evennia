"""
Test the EvAdventure equipment handler.

"""


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

    def test_validate_slot_usage(self):
        helmet = self.helmet
        self.assertTrue(self.character.equipment.validate_slot_usage(helmet))
        helmet.size = 20  # a very large helmet
        with self.assertRaises(EquipmentError):
            self.assertFalse(self.character.equipment.validate_slot_usage(helmet))

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
            self.character.equipment.get_all(),
            [(self.helmet, WieldLocation.BACKPACK), (self.weapon, WieldLocation.BACKPACK)],
        )
