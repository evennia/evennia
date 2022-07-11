"""
All items in the game inherit from a base object. The properties (what you can do
with an object, such as wear, wield, eat, drink, kill etc) are all controlled by
Tags.



"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty

from .enums import WieldLocation, Ability


class EvAdventureObject(DefaultObject):
    """
    Base in-game entity.

    """

    # inventory management
    inventory_use_slot = AttributeProperty(WieldLocation.BACKPACK)
    # how many inventory slots it uses (can be a fraction)
    size = AttributeProperty(1)
    armor = AttributeProperty(0)
    # items that are usable (like potions) have a value larger than 0. Wieldable items
    # like weapons, armor etc are not 'usable' in this respect.
    uses = AttributeProperty(0)
    # when 0, item is destroyed and is unusable
    quality = AttributeProperty(1)
    value = AttributeProperty(0)


class EvAdventureObjectFiller(EvAdventureObject):
    """
    In _Knave_, the inventory slots act as an extra measure of how you are affected by
    various averse effects. For example, mud or water could fill up some of your inventory
    slots and make the equipment there unusable until you cleaned it. Inventory is also
    used to track how long you can stay under water etc - the fewer empty slots you have,
    the less time you can stay under water due to carrying so much stuff with you.

    This class represents such an effect filling up an empty slot. It has a quality of 0,
    meaning it's unusable.

    """
    quality = AttributeProperty(0)


class EvAdventureConsumable(EvAdventureObject):
    """
    Item that can be 'used up', like a potion or food. Weapons, armor etc does not
    have a limited usage in this way.

    """
    inventory_use_slot = AttributeProperty(WieldLocation.BACKPACK)
    size = AttributeProperty(0.25)
    uses = AttributeProperty(1)

    def use(self, user, *args, **kwargs):
        """
        Consume a 'use' of this item. Once it reaches 0 uses, it should normally
        not be usable anymore and probably be deleted.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Extra arguments depending on the usage and item.

        """
        pass


class EvAdventureWeapon(EvAdventureObject):
    """
    Base weapon class for all EvAdventure weapons.

    """

    inventory_use_slot = AttributeProperty(WieldLocation.WEAPON_HAND)

    attack_type = AttributeProperty(Ability.STR)
    defense_type = AttributeProperty(Ability.ARMOR)
    damage_roll = AttributeProperty("1d6")


class EvAdventureRunestone(EvAdventureWeapon):
    """
    Base class for magic runestones. In _Knave_, every spell is represented by a rune stone
    that takes up an inventory slot. It is wielded as a weapon in order to create the specific
    magical effect provided by the stone. Normally each stone can only be used once per day but
    they are quite powerful (and scales with caster level).

    """
    inventory_use_slot = AttributeProperty(WieldLocation.TWO_HANDS)

    attack_type = AttributeProperty(Ability.INT)
    defense_type = AttributeProperty(Ability.CON)
    damage_roll = AttributeProperty("1d8")
