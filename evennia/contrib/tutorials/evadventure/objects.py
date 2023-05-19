"""
All items in the game inherit from a base object. The properties (what you can do
with an object, such as wear, wield, eat, drink, kill etc) are all controlled by
Tags.

Every object has one of a few `obj_type`-category tags:
- weapon
- armor
- shield
- helmet
- consumable  (potions, torches etc)
- magic (runestones, magic items)
- quest (quest-items)
- treasure  (valuable to sell)

It's possible for an item to have more than one tag, such as a golden helmet (helmet+treasure) or
rune sword (weapon+quest).

"""

from evennia import AttributeProperty, create_object, search_object
from evennia.objects.objects import DefaultObject
from evennia.utils.utils import make_iter

from . import rules
from .enums import Ability, ObjType, WieldLocation
from .utils import get_obj_stats

_BARE_HANDS = None


class EvAdventureObject(DefaultObject):
    """
    Base in-game entity.

    """

    # inventory management
    inventory_use_slot = AttributeProperty(WieldLocation.BACKPACK)
    # how many inventory slots it uses (can be a fraction)
    size = AttributeProperty(1)
    value = AttributeProperty(0)

    # can also be an iterable, for adding multiple obj-type tags
    obj_type = ObjType.GEAR

    def at_object_creation(self):
        for obj_type in make_iter(self.obj_type):
            self.tags.add(obj_type.value, category="obj_type")

    def get_display_header(self, looker, **kwargs):
        return ""  # this is handled by get_obj_stats

    def get_display_desc(self, looker, **kwargs):
        return get_obj_stats(self, owner=looker)

    def has_obj_type(self, objtype):
        """
        Check if object is of a particular type.

        typeobj_enum (enum.ObjType): A type to check, like enums.TypeObj.TREASURE.

        """
        return objtype.value in make_iter(self.obj_type)

    def get_help(self):
        """
        Get help text for the item.

        Returns:
            str: The help text, by default taken from the `.help_text` property.

        """
        return "No help for this item."

    def at_pre_use(self, *args, **kwargs):
        """
        Called before use. If returning False, usage should be aborted.
        """
        return True

    def use(self, *args, **kwargs):
        """
        Use this object, whatever that may mean.

        """
        raise NotImplementedError

    def at_post_use(self, *args, **kwargs):
        """
        Called after use happened.
        """
        pass


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

    obj_type = ObjType.QUEST.value  # can't be sold
    quality = AttributeProperty(0)


class EvAdventureQuestObject(EvAdventureObject):
    """
    A quest object. These cannot be sold and only be used for quest resolution.

    """

    obj_type = ObjType.QUEST
    value = AttributeProperty(0)


class EvAdventureTreasure(EvAdventureObject):
    """
    A 'treasure' is mainly useful to sell for coin.

    """

    obj_type = ObjType.TREASURE
    value = AttributeProperty(100, autocreate=False)


class EvAdventureConsumable(EvAdventureObject):
    """
    Item that can be 'used up', like a potion or food. Weapons, armor etc does not
    have a limited usage in this way.

    """

    obj_type = ObjType.CONSUMABLE
    size = AttributeProperty(0.25, autocreate=False)
    uses = AttributeProperty(1, autocreate=False)

    def at_pre_use(self, user, target=None, *args, **kwargs):
        if target and user.location != target.location:
            user.msg("You are not close enough to the target!")
            return False

        if self.uses <= 0:
            user.msg(f"|w{self.key} is used up.|n")
            return False

        return super().at_pre_use(user, target=target, *args, **kwargs)

    def use(self, user, target=None, *args, **kwargs):
        """
        Use the consumable.

        """

        if user.location:
            user.location.msg_contents(
                f"$You() $conj(use) {self.get_display_name(user)}.", from_obj=user
            )

    def at_post_use(self, user, *args, **kwargs):
        """
        Called after this item was used.

        Args:
            user (Object): The one using the item.
            *args, **kwargs: Optional arguments.

        """
        self.uses -= 1
        if self.uses <= 0:
            user.msg(f"|w{self.key} was used up.|n")
            self.delete()


class EvAdventureWeapon(EvAdventureObject):
    """
    Base weapon class for all EvAdventure weapons.

    """

    obj_type = ObjType.WEAPON
    inventory_use_slot = AttributeProperty(WieldLocation.WEAPON_HAND)
    quality = AttributeProperty(3)

    # what ability used to attack with this weapon
    attack_type = AttributeProperty(Ability.STR)
    # what defense stat of the enemy it must defeat
    defense_type = AttributeProperty(Ability.ARMOR)
    damage_roll = AttributeProperty("1d6")

    def get_display_name(self, looker=None, **kwargs):
        quality = self.quality

        quality_txt = ""
        if quality <= 0:
            quality_txt = "|r(broken!)|n"
        elif quality < 2:
            quality_txt = "|y(damaged)|n"
        elif quality < 3:
            quality_txt = "|Y(chipped)|n"

        return super().get_display_name(looker=looker, **kwargs) + quality_txt

    def at_pre_use(self, user, target=None, *args, **kwargs):
        if target and user.location != target.location:
            # we assume weapons can only be used in the same location
            user.msg("You are not close enough to the target!")
            return False

        if self.quality is not None and self.quality <= 0:
            user.msg(f"{self.get_display_name(user)} is broken and can't be used!")
            return False
        return super().at_pre_use(user, target=target, *args, **kwargs)

    def use(self, attacker, target, *args, advantage=False, disadvantage=False, **kwargs):
        """When a weapon is used, it attacks an opponent"""

        location = attacker.location

        is_hit, quality, txt = rules.dice.opposed_saving_throw(
            attacker,
            target,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        location.msg_contents(
            f"$You() $conj(attack) $You({target.key}) with {self.key}: {txt}",
            from_obj=attacker,
            mapping={target.key: target},
        )
        if is_hit:
            # enemy hit, calculate damage
            dmg = rules.dice.roll(self.damage_roll)

            if quality is Ability.CRITICAL_SUCCESS:
                # doble damage roll for critical success
                dmg += rules.dice.roll(self.damage_roll)
                message = (
                    f" $You() |ycritically|n $conj(hit) $You({target.key}) for |r{dmg}|n damage!"
                )
            else:
                message = f" $You() $conj(hit) $You({target.key}) for |r{dmg}|n damage!"

            location.msg_contents(message, from_obj=attacker, mapping={target.key: target})
            # call hook
            target.at_damage(dmg, attacker=attacker)

        else:
            # a miss
            message = f" $You() $conj(miss) $You({target.key})."
            if quality is Ability.CRITICAL_FAILURE:
                message += ".. it's a |rcritical miss!|n, damaging the weapon."
                if self.quality is not None:
                    self.quality -= 1
                location.msg_contents(message, from_obj=attacker, mapping={target.key: target})

    def at_post_use(self, user, *args, **kwargs):
        if self.quality is not None and self.quality <= 0:
            user.msg(f"|r{self.get_display_name(user)} breaks and can no longer be used!")


class EvAdventureThrowable(EvAdventureWeapon, EvAdventureConsumable):
    """
    Something you can throw at an enemy to harm them once, like a knife or exploding potion/grenade.

    Note: In Knave, ranged attacks are done with WIS (representing the stillness of your mind?)

    """

    obj_type = (ObjType.THROWABLE, ObjType.WEAPON, ObjType.CONSUMABLE)

    attack_type = AttributeProperty(Ability.WIS)
    defense_type = AttributeProperty(Ability.DEX)
    damage_roll = AttributeProperty("1d6")


class EvAdventureRunestone(EvAdventureWeapon, EvAdventureConsumable):
    """
    Base class for magic runestones. In _Knave_, every spell is represented by a rune stone
    that takes up an inventory slot. It is wielded as a weapon in order to create the specific
    magical effect provided by the stone. Normally each stone can only be used once per day but
    they are quite powerful (and scales with caster level).

    """

    obj_type = (ObjType.WEAPON, ObjType.MAGIC)
    inventory_use_slot = WieldLocation.TWO_HANDS
    quality = AttributeProperty(3)

    attack_type = AttributeProperty(Ability.INT)
    defense_type = AttributeProperty(Ability.DEX)
    damage_roll = AttributeProperty("1d8")

    def at_post_use(self, user, *args, **kwargs):
        """Called after the spell was cast"""
        self.uses -= 1
        # the rune stone is not deleted after use, but
        # it needs to be refreshed after resting.

    def refresh(self):
        self.uses = 1


class EvAdventureArmor(EvAdventureObject):
    """
    Base class for all wearable Armors.

    """

    obj_type = ObjType.ARMOR
    inventory_use_slot = WieldLocation.BODY

    armor = AttributeProperty(1)
    quality = AttributeProperty(3)


class EvAdventureShield(EvAdventureArmor):
    """
    Base class for all Shields.

    """

    obj_type = ObjType.SHIELD
    inventory_use_slot = WieldLocation.SHIELD_HAND


class EvAdventureHelmet(EvAdventureArmor):
    """
    Base class for all Helmets.

    """

    obj_type = ObjType.HELMET
    inventory_use_slot = WieldLocation.HEAD


class WeaponBareHands(EvAdventureWeapon):
    """
    This is a dummy-class loaded when you wield no weapons. We won't create any db-object for it.

    """

    obj_type = ObjType.WEAPON
    key = "Bare hands"
    inventory_use_slot = WieldLocation.WEAPON_HAND
    attack_type = Ability.STR
    defense_type = Ability.ARMOR
    damage_roll = "1d4"
    quality = None  # let's assume fists are always available ...


def get_bare_hands():
    """
    Get the bare-hands singleton object.

    Returns:
        WeaponBareHands
    """
    global _BARE_HANDS

    if not _BARE_HANDS:
        _BARE_HANDS = search_object("Bare hands", typeclass=WeaponBareHands).first()
    if not _BARE_HANDS:
        _BARE_HANDS = create_object(WeaponBareHands, key="Bare hands")
    return _BARE_HANDS
