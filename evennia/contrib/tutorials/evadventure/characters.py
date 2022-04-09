"""
Base Character and NPCs.

"""

from evennia.objects.objects import DefaultCharacter, DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import lazy_property, int2str
from .objects import EvAdventureObject
from . import rules
from .enums import Ability, WieldLocation


class EquipmentError(TypeError):
    pass


class EquipmentHandler:
    """
    _Knave_ puts a lot of emphasis on the inventory. You have CON_DEFENSE inventory
    slots. Some things, like torches can fit multiple in one slot, other (like
    big weapons) use more than one slot. The items carried and wielded has a big impact
    on character customization - even magic requires carrying a runestone per spell.

    The inventory also doubles as a measure of negative effects. Getting soaked in mud
    or slime could gunk up some of your inventory slots and make the items there unusuable
    until you clean them.
    """
    save_attribute = "inventory_slots"

    def __init__(self, obj):
        self.obj = obj
        self._load()

    def _load(self):
        """
        Load or create a new slot storage.

        """
        self.slots = self.obj.attributes.get(
            self.save_attribute,
            category="inventory",
            default={
                WieldLocation.WEAPON_HAND: None,
                WieldLocation.SHIELD_HAND: None,
                WieldLocation.TWO_HANDS: None,
                WieldLocation.BODY: None,
                WieldLocation.HEAD: None,
                WieldLocation.BACKPACK: []
            }
        )

    def _count_slots(self):
        """
        Count slot usage. This is fetched from the .size Attribute of the
        object. The size can also be partial slots.

        """
        slots = self.slots
        wield_usage = sum(
            getattr(slotobj, "size", 0) or 0
            for slot, slotobj in slots.items()
            if slot is not WieldLocation.BACKPACK
        )
        backpack_usage = sum(
            getattr(slotobj, "size", 0) or 0
            for slotobj in slots[WieldLocation.BACKPACK]
        )
        return wield_usage + backpack_usage

    def _save(self):
        """
        Save slot to storage.

        """
        self.obj.attributes.add(self.save_attribute, category="inventory")

    @property
    def max_slots(self):
        """
        The max amount of equipment slots ('carrying capacity') is based on
        the constitution defense.

        """
        return getattr(self.obj, Ability.CON_DEFENSE.value, 11)

    def validate_slot_usage(self, obj):
        """
        Check if obj can fit in equipment, based on its size.

        Args:
            obj (EvAdventureObject): The object to add.

        Raise:
            EquipmentError: If there's not enough room.

        """
        size = getattr(obj, "size", 0)
        max_slots = self.max_slots
        current_slot_usage = self._count_slots()
        if current_slot_usage + size > max_slots:
            slots_left = max_slots - current_slot_usage
            raise EquipmentError(f"Equipment full ({int2str(slots_left)} slots "
                                 f"remaining, {obj.key} needs {int2str(size)} "
                                 f"$pluralize(slot, {size})).")

    @property
    def armor(self):
        """
        Armor provided by actually worn equipment/shield. For body armor
        this is a base value, like 12, for shield/helmet, it's a bonus, like +1.
        We treat values and bonuses equal and just add them up. This value
        can thus be 0, the 'unarmored' default should be handled by the calling
        method.

        Returns:
            int: Armor from equipment.

        """
        slots = self.slots
        return sum((
            getattr(slots[WieldLocation.BODY], "armor", 0),
            getattr(slots[WieldLocation.SHIELD_HAND], "armor", 0),
            getattr(slots[WieldLocation.HEAD], "armor", 0),
        ))

    @property
    def weapon(self):
        """
        Conveniently get the currently active weapon.

        Returns:
            obj or None: The weapon. None if unarmored.

        """
        # first checks two-handed wield, then one-handed; the two
        # should never appear simultaneously anyhow (checked in `use` method).
        slots = self.slots
        weapon = slots[WieldLocation.TWO_HANDS]
        if not weapon:
            weapon = slots[WieldLocation.WEAPON_HAND]
        return weapon

    def use(self, obj):
        """
        Make use of item - this makes use of the object's wield slot to decide where
        it goes. If it doesn't have any, it goes into backpack.

        Args:
            obj (EvAdventureObject): Thing to use.

        Raises:
            EquipmentError: If there's no room in inventory. It will contains the details
                of the error, suitable to echo to user.

        Notes:
            If using an item already in the backpack, it should first be `removed` from the
            backpack, before applying here - otherwise, it will be added a second time!

            this will cleanly move any 'colliding' items to the backpack to
            make the use possible (such as moving sword + shield to backpack when wielding
            a two-handed weapon). If wanting to warn the user about this, it needs to happen
            before this call.

        """
        # first check if we have room for this
        self.validate_slot_usage(obj)

        slots = self.slots
        use_slot = getattr(obj, "inventory_use_slot", WieldLocation.BACKPACK)

        if use_slot is WieldLocation.TWO_HANDS:
            # two-handed weapons can't co-exist with weapon/shield-hand used items
            slots[WieldLocation.WEAPON_HAND] = slots[WieldLocation.SHIELD_HAND] = None
            slots[use_slot] = obj
        elif use_slot in (WieldLocation.WEAPON_HAND, WieldLocation.SHIELD_HAND):
            # can't keep a two-handed weapon if adding a one-handede weapon or shield
            slots[WieldLocation.TWO_HANDS] = None
            slots[use_slot] = obj
        elif use_slot is WieldLocation.BACKPACK:
            # backpack has multiple slots.
            slots[use_slot].append(obj)
        else:
            # for others (body, head), just replace whatever's there
            slots[use_slot] = obj

        # store new state
        self._save()

    def store(self, obj):
        """
        Put something in the backpack specifically (even if it could be wield/worn).

        """
        # check if we have room
        self.validate_slot_usage(obj)
        self.slots[WieldLocation.BACKPACK].append(obj)
        self._save()

    def remove(self, obj_or_slot):
        """
        Remove specific object or objects from a slot.

        Args:
            obj_or_slot (EvAdventureObject or WieldLocation): The specific object or
                location to empty. If this is WieldLocation.BACKPACK, all items
                in the backpack will be emptied and returned!
        Returns:
            list: A list of 0, 1 or more objects emptied from the inventory.

        """
        slots = self.slots
        ret = []
        if isinstance(obj_or_slot, WieldLocation):
            ret = slots[obj_or_slot]
            slots[obj_or_slot] = [] if obj_or_slot is WieldLocation.BACKPACK else None
        elif obj_or_slot in self.obj.contents:
            # object is in inventory, find out which slot and empty it
            for slot, objslot in slots:
                if slot is WieldLocation.BACKPACK:
                    try:
                        ret = objslot.remove(obj_or_slot)
                        break
                    except ValueError:
                        pass
                elif objslot is obj_or_slot:
                    ret = objslot
                    slots[slot] = None
                    break
        if ret:
            self._save()
        return ret


class LivingMixin:
    """
    Helpers shared between all living things.

    """

    @property
    def hurt_level(self):
        """
        String describing how hurt this character is.
        """
        percent = max(0, min(100, 100 * (self.hp / self.hp_max)))
        if 95 < percent <= 100:
            return "|gPerfect|n"
        elif 80 < percent <= 95:
            return "|gScraped|n"
        elif 60 < percent <= 80:
            return "|GBruised|n"
        elif 45 < percent <= 60:
            return "|yHurt|n"
        elif 30 < percent <= 45:
            return "|yWounded|n"
        elif 15 < percent <= 30:
            return "|rBadly wounded|n"
        elif 1 < percent <= 15:
            return "|rBarely hanging on|n"
        elif percent == 0:
            return "|RCollapsed!|n"

    def heal(self, hp, healer=None):
        """
        Heal by a certain amount of HP.

        """
        damage = self.hp_max - self.hp
        healed = min(damage, hp)
        self.hp += healed

        if healer is self:
            self.msg(f"|gYou heal yourself for {healed} health.|n")
        else:
            self.msg(f"|g{healer.key} heals you for {healed} health.|n")


class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    """
    A Character for use with EvAdventure. This also works fine for
    monsters and NPCS.

    """

    # these are the ability bonuses. Defense is always 10 higher
    strength = AttributeProperty(default=1)
    dexterity = AttributeProperty(default=1)
    constitution = AttributeProperty(default=1)
    intelligence = AttributeProperty(default=1)
    wisdom = AttributeProperty(default=1)
    charisma = AttributeProperty(default=1)

    exploration_speed = AttributeProperty(default=120)
    combat_speed = AttributeProperty(default=40)

    hp = AttributeProperty(default=4)
    hp_max = AttributeProperty(default=4)
    level = AttributeProperty(default=1)
    xp = AttributeProperty(default=0)

    morale = AttributeProperty(default=9)  # only used for NPC/monster morale checks

    @lazy_property
    def equipment(self):
        """Allows to access equipment like char.equipment.worn"""
        return EquipmentHandler(self)

    @property
    def weapon(self):
        """
        Quick access to the character's currently wielded weapon.

        """
        self.equipment.weapon

    @property
    def armor(self):
        """
        Quick access to the character's current armor.
        Will return the "Unarmored" armor level (11) if none other are found.

        """
        self.equipment.armor or 11

    def at_pre_object_receive(self, moved_object, source_location, **kwargs):
        """
        Hook called by Evennia before moving an object here. Return False to abort move.

        Args:
            moved_object (Object): Object to move into this one (that is, into inventory).
            source_location (Object): Source location moved from.
            **kwargs: Passed from move operation; unused here.

        Returns:
            bool: If move should be allowed or not.

        """
        return self.equipment.has_space(moved_object)

    def at_object_receive(self, moved_object, source_location, **kwargs):
        """
        Hook called by Evennia as an object is moved here. We make sure it's added
        to the equipment handler.

        Args:
            moved_object (Object): Object to move into this one (that is, into inventory).
            source_location (Object): Source location moved from.
            **kwargs: Passed from move operation; unused here.

        """
        self.equipment.add(moved_object)

    def at_pre_object_leave(self, leaving_object, destination, **kwargs):
        """
        Hook called when dropping an item. We don't allow to drop weilded/worn items
        (need to unwield/remove them first).

        """
        self.equipment.can_drop(leaving_object)

    def at_object_leave(self, moved_object, destination, **kwargs):
        """
        Called just before an object leaves from inside this object

        Args:
            moved_obj (Object): The object leaving
            destination (Object): Where `moved_obj` is going.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        self.equipment.remove(moved_object)

    def at_damage(self, dmg, attacker=None):
        """
        Called when receiving damage for whatever reason. This
        is called *before* hp is evaluated for defeat/death.

        """

    def defeat_message(self, attacker, dmg):
        return f"After {attacker.key}'s attack, {self.key} collapses in a heap."

    def at_defeat(self, attacker, dmg):
        """
        At this point, character has been defeated but is not killed (their
        hp >= 0 but they lost ability bonuses). Called after being defeated in combat or
        other situation where health is lost below or equal to 0.

        """

    def handle_death(self):
        """
        Called when character dies.

        """


class EvAdventureNPC(LivingMixin, DefaultCharacter):
    """
    This is the base class for all non-player entities, including monsters. These
    generally don't advance in level but uses a simplified, abstract measure of how
    dangerous or competent they are - the 'hit dice' (HD).

    HD indicates how much health they have and how hard they hit. In _Knave_, HD also
    defaults to being the bonus for all abilities. HP is 4 x Hit die (this can then be
    customized per-entity of course).

    Morale is set explicitly per-NPC, usually between 7 and 9.

    Monsters don't use equipment in the way PCs do, instead they have a fixed armor
    value, and their Abilities are dynamically generated from the HD (hit_dice).

    If wanting monsters or NPCs that can level and work the same as PCs, base them off the
    EvAdventureCharacter class instead.

    """
    hit_dice = AttributeProperty(default=1)
    armor = AttributeProperty(default=11)
    morale = AttributeProperty(default=9)
    hp = AttributeProperty(default=8)

    @property
    def strength(self):
        return self.hit_dice

    @property
    def dexterity(self):
        return self.hit_dice

    @property
    def constitution(self):
        return self.hit_dice

    @property
    def intelligence(self):
        return self.hit_dice

    @property
    def wisdom(self):
        return self.hit_dice

    @property
    def charisma(self):
        return self.hit_dice

    @property
    def hp_max(self):
        return self.hit_dice * 4

    def at_object_creation(self):
        """
        Start with max health.

        """
        self.hp = self.hp_max
