"""
Helpers for testing evadventure modules.

"""

from evennia.utils import create

from .. import enums
from ..characters import EvAdventureCharacter
from ..objects import (
    EvAdventureArmor,
    EvAdventureHelmet,
    EvAdventureObject,
    EvAdventureShield,
    EvAdventureWeapon,
)
from ..rooms import EvAdventureRoom


class EvAdventureMixin:
    """
    Provides a set of pre-made characters.

    """

    def setUp(self):
        super().setUp()
        self.location = create.create_object(EvAdventureRoom, key="testroom")
        self.character = create.create_object(
            EvAdventureCharacter, key="testchar", location=self.location
        )
        self.helmet = create.create_object(
            EvAdventureHelmet,
            key="helmet",
            attributes=[("inventory_use_slot", enums.WieldLocation.HEAD), ("armor", 1)],
        )
        self.shield = create.create_object(
            EvAdventureShield,
            key="shield",
            attributes=[("inventory_use_slot", enums.WieldLocation.SHIELD_HAND), ("armor", 1)],
        )
        self.armor = create.create_object(
            EvAdventureArmor,
            key="armor",
            attributes=[("inventory_use_slot", enums.WieldLocation.BODY), ("armor", 11)],
        )
        self.weapon = create.create_object(
            EvAdventureWeapon,
            key="weapon",
            attributes=[("inventory_use_slot", enums.WieldLocation.WEAPON_HAND)],
        )
        self.big_weapon = create.create_object(
            EvAdventureWeapon,
            key="big_weapon",
            attributes=[("inventory_use_slot", enums.WieldLocation.TWO_HANDS)],
        )
        self.item = create.create_object(EvAdventureObject, key="backpack item")
