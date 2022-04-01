"""
Base Character and NPCs.

"""


from evennia.objects.objects import DefaultCharacter, DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import lazy_property, int2str
from .objects import EvAdventureObject
from . import rules


class EquipmentError(TypeError):
    pass


class EquipmentHandler:
    """
    _Knave_ puts a lot of emphasis on the inventory. You have 20 inventory slots,
    Some things, like torches can fit multiple in one slot, other (like
    big weapons) use more than one slot. The items carried and wielded has a big impact
    on character customization - even magic requires carrying a runestone per spell.

    The inventory also doubles as a measure of negative effects. Getting soaked in mud
    or slime could gunk up some of your inventory slots and make the items there unusuable
    until you cleaned them.

    """
    # these are the equipment slots available
    total_slots = 20
    wield_slots = ["shield", "weapon"]
    wear_slots = ["helmet", "armor"]

    def __init__(self, obj):
        self.obj = obj
        self._slots_used = None
        self._wielded = None
        self._worn = None
        self._armor = None

    def _wield_or_wear(self, item, action="wear"):
        """
        Wield or wear a previously carried item in one of the supported wield/wear slots. Items need
        to have the wieldable/wearable tag and will get a wielded/worn tag. The slot to occupy is
        retrieved from the item itself.

        Args:
            item (Object): The object to wield. This will replace any existing
                wieldable item in that spot.
            action (str): One of 'wield' or 'wear'.
        Returns:
            tuple: (slot, old_item - the slot-name this item was
                assigned to (like 'helmet') and any old item that was replaced in that location,.
                (else `old_item` is `None`). This is useful for returning info messages
                to the user.
        Raises:
            EquipmentError: If there is a problem wielding the item.

        Notes:
            Since the action of wielding is so similar to wearing, we use the same code for both,
            just exchanging which slot to use and the wield/wear and wielded/worn texts.

        """
        adjective = 'wearable' if action == 'wear' else 'wieldable'
        verb = "worn" if action == 'wear' else 'wielded'

        if item not in self.obj.contents:
            raise EquipmentError(f"You need to pick it up before you can use it.")
        if item in self.wielded:
            raise EquipmentError(f"Already using {item.key}")
        if not item.tags.has(adjective, category="inventory"):
            # must have wieldable/wearable tag
            raise EquipmentError(f"Cannot {action} {item.key}")

        # see if an existing item already sits in the relevant slot
        if action == 'wear':
            slot = item.wear_slot
            old_item = self.worn.get(slot)
            self.worn[slot] = item
        else:
            slot = item.wield_slot
            old_item = self.wielded.get(slot)
            self.wielded[item]

        # untag old, tag the new and store it in .wielded dict for easy access
        if old_item:
            old_item.tags.remove(verb, category="inventory")
        item.tags.add(verb, category="inventory")

        return slot, old_item

    @property
    def slots_used(self):
        """
        Return how many slots are used up (out of .total_slots). Certain, big items may use more
        than one slot. Also caches the results.

        """
        slots_used = self._slots_used
        if slots_used is None:
            slots_used = self._slots_used = sum(
                item.inventory_slot_usage for item in self.contents
            )
        return slots_used

    @property
    def all(self):
        """
        Get all carried items. Used by an 'inventory' command.

        """
        return self.obj.contents

    @property
    def worn(self):
        """
        Get (and cache) all worn items.

        """
        worn = self._worn
        if worn is None:
            worn = self._worn = list(
                DefaultObject.objects
                .get_by_tag(["wearable", "worn"], category="inventory")
                .filter(db_location=self.obj)
            )
        return worn

    @property
    def wielded(self):
        wielded = self._wielded
        if wielded is None:
            wielded = self._wielded = list(
                DefaultObject.objects
                .get_by_tag(["wieldable", "wielded"], category="inventory")
                .filter(db_location=self.obj)
            )
        return wielded

    @property
    def carried(self):
        wielded_or_worn = self.wielded + self.worn
        return [item for item in self.contents if item not in wielded_or_worn]

    @property
    def armor_defense(self):
        """
        Figure out the total armor defense of the character. This is a combination
        of armor from worn items (helmets, armor) and wielded ones (shields).

        """
        armor = self._armor
        if armor is None:
            # recalculate and refresh cache. Default for unarmored enemy is armor defense of 11.
            armor = self._armor = sum(item.armor for item in self.worn + self.wielded) or 11
        return armor

    def has_space(self, item):
        """
        Check if there's room in equipment for this item.

        Args:
            item (Object): An entity that takes up space.

        Returns:
            bool: If there's room or not.

        Notes:
            Also informs the user of the failure.

        """
        needed_slots = getattr(item, "inventory_slot_usage", 1)
        free = self.slots_used - needed_slots
        if free - needed_slots < 0:
            self.obj.msg(f"No space in inventory - {item} takes up {needed_slots}, "
                         f"but $int2str({free}) $pluralize(is, {free}, are) available.")
            return False
        return True

    def can_drop(self, item):
        """
        Check if the item can be dropped - this is blocked by being worn or wielded.

        Args:
            item (Object): The item to drop.

        Returns:
            bool: If the object can be dropped.

        Notes:
            Informs the user of a failure.

        """
        if item in self.wielded:
            self.msg("You are currently wielding {item.key}. Unwield it first.")
            return False
        if item in self.worn:
            self.msg("You are currently wearing {item.key}. Remove it first.")
            return False
        return True

    def add(self, item):
        """
        Add an item to the inventory. This will be called when picking something up. An item
        must be carried before it can be worn or wielded.

        There is a max number of carry-slots.

        Args:
            item (EvAdventureObject): The item to add (pick up).
        Raises:
            EquipmentError: If the item can't be added (usually because of lack of space).

        """
        slots_needed = item.inventory_slot_usage
        slots_already_used = self.slots_used

        slots_free = self.total_slots - slots_already_used

        if slot_needed > slots_free:
            raise EquipmentError(
                f"This requires {slots_needed} equipment slots - you have "
                f"$int2str({slots_free}) $pluralize(slot, {slots_free}) available.")
        # move to inventory
        item.location = self.obj
        self.slots_used += slots_needed

    def remove(self, item):
        """
        Remove (drop) an item from inventory. This will also un-wear or un-wield it.

        Args:
            item (EvAdventureObject): The item to drop.
        Raises:
            EquipmentError: If the item can't be dropped (usually because we don't have it).

        """
        if item not in self.obj.contents:
            raise EquipmentError("You are not carrying this item.")
        self.slots_used -= item.inventory_slot_usage

    def wear(self, item):
        """
        Wear a previously carried item. The item itelf knows which slot it belongs in (like 'helmet'
        or 'armor').

        Args:
            item (EvAdventureObject): The item to wear. Must already be carried.
        Returns:
            tuple: (slot, old_item - the slot-name this item was
                assigned to (like 'helmet') and any old item that was replaced in that location
                (else `old_item` is `None`). This is useful for returning info messages
                to the user.
        Raises:
            EquipmentError: If there is a problem wearing the item.

        """
        return self._wield_or_wear(item, action="wield")

    def wield(self, item):
        """
        Wield a previously carried item. The item itelf knows which wield-slot it belongs in (like
        'helmet' or 'armor').

        Args:
            item (EvAdventureObject): The item to wield. Must already be carried.

        Returns:
            tuple: (slot, old_item - the wield-slot-name this item was
                assigned to (like 'shield') and any old item that was replaced in that location
                (else `old_item` is `None`). This is useful for returning info messages
                to the user.
        Raises:
            EquipmentError: If there is a problem wielding the item.

        """
        return self._wield_or_wear(item, action="wear")


class EvAdventureCharacter(DefaultCharacter):
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

    armor = AttributeProperty(default=1)

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
        Will return the "Unarmed" weapon if none other are found.

        """
        # TODO

    @property
    def armor(self):
        """
        Quick access to the character's current armor.
        Will return the "Unarmored" armor if none other are found.

        """
        # TODO

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
        Heal the character by a certain amount of HP.

        """
        damage = self.hp_max - self.hp
        healed = min(damage, hp)
        self.hp += healed

        if healer is self:
            self.msg(f"|gYou heal yourself for {healed} health.|n")
        else:
            self.msg(f"|g{healer.key} heals you for {healed} health.|n")

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


class EvAdventureNPC(DefaultCharacter):
    """
    This is the base class for all non-player entities, including monsters. These
    generally don't advance in level but uses a simplified, abstract measure of how
    dangerous or competent they are - the 'hit dice' (HD).

    HD indicates how much health they have and how hard they hit. In _Knave_, HD also
    defaults to being the bonus for all abilities. HP is 4 x Hit die (this can then be
    customized per-entity of course).

    Morale is set explicitly per-NPC, usually between 7 and 9.

    Monsters don't use equipment in the way PCs do, instead their weapons and equipment
    are baked into their HD (and/or dropped as loot when they go down). If you want monsters
    or NPCs that can level and work the same as PCs, base them off the EvAdventureCharacter
    class instead.

    Unlike for a Character, we generate all the abilities dynamically based on HD.

    """
    hit_dice = AttributeProperty(default=1)
    # note: this is the armor bonus, 10 lower than the armor defence (what is usually
    # referred to as ascending AC for many older D&D versions). So if AC is 14, this value
    # should be 4.
    armor = AttributeProperty(default=1)
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

