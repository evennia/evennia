"""
Knave has a system of Slots for its inventory.

"""

from .enums import Ability, WieldLocation
from .objects import WeaponEmptyHand


class EquipmentError(TypeError):
    pass


class EquipmentHandler:
    """
    _Knave_ puts a lot of emphasis on the inventory. You have CON_DEFENSE inventory
    slots. Some things, like torches can fit multiple in one slot, other (like
    big weapons and armor) use more than one slot. The items carried and wielded has a big impact
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
                WieldLocation.BACKPACK: [],
            },
        )

    def _save(self):
        """
        Save slot to storage.

        """
        self.obj.attributes.add(self.save_attribute, self.slots, category="inventory")

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
            getattr(slotobj, "size", 0) or 0 for slotobj in slots[WieldLocation.BACKPACK]
        )
        return wield_usage + backpack_usage

    @property
    def max_slots(self):
        """
        The max amount of equipment slots ('carrying capacity') is based on
        the constitution defense.

        """
        return getattr(self.obj, Ability.CON.value, 1) + 10

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
            raise EquipmentError(
                f"Equipment full ($int2str({slots_left}) slots "
                f"remaining, {obj.key} needs $int2str({size}) "
                f"$pluralize(slot, {size}))."
            )
        return True

    @property
    def armor(self):
        """
        Armor provided by actually worn equipment/shield. For body armor
        this is a base value, like 12, for shield/helmet, it's a bonus, like +1.
        We treat values and bonuses equal and just add them up. This value
        can thus be 0, the 'unarmored' default should be handled by the calling
        method.

        Returns:
            int: Armor from equipment. Note that this is the +bonus of Armor, not the
                'defense' (to get that one adds 10).

        """
        slots = self.slots
        return sum(
            (
                # armor is listed using its defense, so we remove 10 from it
                # (11 is base no-armor value in Knave)
                getattr(slots[WieldLocation.BODY], "armor", 11) - 10,
                # shields and helmets are listed by their bonus to armor
                getattr(slots[WieldLocation.SHIELD_HAND], "armor", 0),
                getattr(slots[WieldLocation.HEAD], "armor", 0),
            )
        )

    @property
    def weapon(self):
        """
        Conveniently get the currently active weapon or rune stone.

        Returns:
            obj or None: The weapon. None if unarmored.

        """
        # first checks two-handed wield, then one-handed; the two
        # should never appear simultaneously anyhow (checked in `use` method).
        slots = self.slots
        weapon = slots[WieldLocation.TWO_HANDS]
        if not weapon:
            weapon = slots[WieldLocation.WEAPON_HAND]
        if not weapon:
            weapon = WeaponEmptyHand()
        return weapon

    def display_loadout(self):
        """
        Get a visual representation of your current loadout.

        Returns:
            str: The current loadout.

        """
        slots = self.slots
        weapon_str = "You are fighting with your bare fists"
        shield_str = " and have no shield."
        armor_str = "You wear no armor"
        helmet_str = " and no helmet."

        two_hands = slots[WieldLocation.TWO_HANDS]
        if two_hands:
            weapon_str = f"You wield {two_hands} with both hands"
            shield_str = " (you can't hold a shield at the same time)."
        else:
            one_hands = slots[WieldLocation.WEAPON_HAND]
            if one_hands:
                weapon_str = f"You are wielding {one_hands} in one hand."
            shield = slots[WieldLocation.SHIELD_HAND]
            if shield:
                shield_str = f"You have {shield} in your off hand."

        armor = slots[WieldLocation.BODY]
        if armor:
            armor_str = f"You are wearing {armor}"

        helmet = slots[WieldLocation.BODY]
        if helmet:
            helmet_str = f" and {helmet} on your head."

        return f"{weapon_str}{shield_str}\n{armor_str}{helmet_str}"

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

    def add(self, obj):
        """
        Put something in the backpack specifically (even if it could be wield/worn).

        """
        # check if we have room
        self.validate_slot_usage(obj)
        self.slots[WieldLocation.BACKPACK].append(obj)
        self._save()

    def can_remove(self, leaving_object):
        """
        Called to check if the object can be removed.

        """
        return True  # TODO - some things may not be so easy, like mud

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
            if obj_or_slot is WieldLocation.BACKPACK:
                # empty entire backpack
                ret.extend(slots[obj_or_slot])
                slots[obj_or_slot] = []
            else:
                ret.append(slots[obj_or_slot])
                slots[obj_or_slot] = None
        elif obj_or_slot in self.slots.values():
            # obj in use/wear slot
            for slot, objslot in slots.items():
                if objslot is obj_or_slot:
                    slots[slot] = None
                    ret.append(objslot)
        elif obj_or_slot in slots[WieldLocation.BACKPACK]:
            # obj in backpack slot
            try:
                slots[WieldLocation.BACKPACK].remove(obj_or_slot)
                ret.append(obj_or_slot)
            except ValueError:
                pass
        if ret:
            self._save()
        return ret

    def get_wieldable_objects_from_backpack(self):
        """
        Get all wieldable weapons (or spell runes) from backpack. This is useful in order to
        have a list to select from when swapping your wielded loadout.

        Returns:
            list: A list of objects with a suitable `inventory_use_slot`. We don't check
            quality, so this may include broken items (we may want to visually show them
            in the list after all).

        """
        return [
            obj
            for obj in self.slots[WieldLocation.BACKPACK]
            if obj.inventory_use_slot
            in (WieldLocation.WEAPON_HAND, WieldLocation.TWO_HANDS, WieldLocation.SHIELD_HAND)
        ]

    def get_wearable_objects_from_backpack(self):
        """
        Get all wearable items (armor or helmets) from backpack. This is useful in order to
        have a list to select from when swapping your worn loadout.

        Returns:
            list: A list of objects with a suitable `inventory_use_slot`. We don't check
            quality, so this may include broken items (we may want to visually show them
            in the list after all).

        """
        return [
            obj
            for obj in self.slots[WieldLocation.BACKPACK]
            if obj.inventory_use_slot in (WieldLocation.BODY, WieldLocation.HEAD)
        ]

    def get_usable_objects_from_backpack(self):
        """
        Get all 'usable' items (like potions) from backpack. This is useful for getting a
        list to select from.

        Returns:
            list: A list of objects that are usable.

        """
        character = self.obj
        return [obj for obj in self.slots[WieldLocation.BACKPACK] if obj.at_pre_use(character)]
