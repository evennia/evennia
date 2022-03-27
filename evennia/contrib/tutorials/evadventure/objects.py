"""
All items in the game inherit from a base object. The properties (what you can do
with an object, such as wear, wield, eat, drink, kill etc) are all controlled by
Tags.

"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty


class EvAdventureObject(DefaultObject):
    """
    Base in-game entity.

    """
    # inventory management
    wield_slot = AttributeProperty(default=None)
    wear_slot = AttributeProperty(default=None)
    inventory_slot_usage = AttributeProperty(default=1)
    armor = AttributeProperty(default=0)
    # when 0, item is destroyed and is unusable
    quality = AttributeProperty(default=1)


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
    quality = AttributeProperty(default=0)


class EvAdventureWeapon(EvAdventureObject):
    """
    Base weapon class for all EvAdventure weapons.

    """
    wield_slot = AttributeProperty(default="weapon")

    attack_type = AttributeProperty(default="strength")
    defense_type = AttributeProperty(default="armor")
    damage_roll = AttributeProperty(default="1d6")

    # at which ranges this weapon can be used. If not listed, unable to use
    distance_optimal = AttributeProperty(default=0)  # normal usage (fists)
    distance_suboptimal = AttributeProperty(default=None)  # disadvantage (fists)


class EvAdventureRunestone(EvAdventureWeapon):
    """
    Base class for magic runestones. In _Knave_, every spell is represented by a rune stone
    that takes up an inventory slot. It is wielded as a weapon in order to create the specific
    magical effect provided by the stone. Normally each stone can only be used once per day but
    they are quite powerful (and scales with caster level).

    """
