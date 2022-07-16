"""
All items in the game inherit from a base object. The properties (what you can do
with an object, such as wear, wield, eat, drink, kill etc) are all controlled by
Tags.



"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty

from .enums import Ability, WieldLocation


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

    help_text = AttributeProperty("")

    def get_help(self):
        """
        Get help text for the item.

        Returns:
            str: The help text, by default taken from the `.help_text` property.

        """
        return self.help_text

    def at_pre_use(self, user, *args, **kwargs):
        """
        Called before this item is used.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Optional arguments.

        Return:
            bool: False to stop usage.

        """
        return self.uses > 0

    def at_use(self, user, *args, **kwargs):
        """
        Called when this item is used.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Optional arguments.

        """
        pass

    def at_post_use(self, user, *args, **kwargs):
        """
        Called after this item was used.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Optional arguments.

        """
        self.uses -= 1


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

    def at_use(self, user, *args, **kwargs):
        """
        Consume a 'use' of this item. Once it reaches 0 uses, it should normally
        not be usable anymore and probably be deleted.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Extra arguments depending on the usage and item.

        """
        pass

    def at_post_use(self, user, *args, **kwargs):
        """
        Called after this item was used.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Optional arguments.

        """
        self.uses -= 1
        if self.uses <= 0:
            user.msg(f"{self.key} was used up.")
            self.delete()


class EvAdventureWeapon(EvAdventureObject):
    """
    Base weapon class for all EvAdventure weapons.

    """

    inventory_use_slot = AttributeProperty(WieldLocation.WEAPON_HAND)

    attack_type = AttributeProperty(Ability.STR)
    defense_type = AttributeProperty(Ability.ARMOR)
    damage_roll = AttributeProperty("1d6")


class WeaponEmptyHand:
    """
    This is used when you wield no weapons. We won't create any db-object for it.

    """

    key = "Empty Fists"
    inventory_use_slot = WieldLocation.WEAPON_HAND
    attack_type = Ability.STR
    defense_type = Ability.ARMOR
    damage_roll = "1d4"
    quality = 100000  # let's assume fists are always available ...

    def __repr__(self):
        return "<WeaponEmptyHand>"


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
