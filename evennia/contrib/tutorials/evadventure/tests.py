"""
Tests for EvAdventure.

"""

from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest
from .character import EvAdventureCharacter
from .objects import EvAdventureObject

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

