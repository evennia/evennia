"""
EvAdventure NPCs. This includes both friends and enemies, only separated by their AI.

"""
from random import choice

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

from .characters import LivingMixin
from .enums import Ability, WieldLocation
from .objects import WeaponEmptyHand
from .rules import dice


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

    The weapon of the npc is stored as an Attribute instead of implementing a full
    inventory/equipment system. This means that the normal inventory can be used for
    non-combat purposes (or for loot to get when killing an enemy).

    """

    is_pc = False

    hit_dice = AttributeProperty(default=1, autocreate=False)
    armor = AttributeProperty(default=1, autocreate=False)  # +10 to get armor defense
    morale = AttributeProperty(default=9, autocreate=False)
    hp_multiplier = AttributeProperty(default=4, autocreate=False)  # 4 default in Knave
    hp = AttributeProperty(default=None, autocreate=False)  # internal tracking, use .hp property
    allegiance = AttributeProperty(default=Ability.ALLEGIANCE_HOSTILE, autocreate=False)

    is_idle = AttributeProperty(default=False, autocreate=False)

    weapon = AttributeProperty(default=WeaponEmptyHand, autocreate=False)  # instead of inventory
    coins = AttributeProperty(default=1, autocreate=False)  # coin loot

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
        return self.hit_dice * self.hp_multiplier

    def at_object_creation(self):
        """
        Start with max health.

        """
        self.hp = self.hp_max

    def ai_combat_next_action(self):
        """
        The combat engine should ask this method in order to
        get the next action the npc should perform in combat.

        """
        pass


class EvAdventureShopKeeper(EvAdventureNPC):
    """
    ShopKeeper NPC.

    """


class EvAdventureQuestGiver(EvAdventureNPC):
    """
    An NPC that acts as a dispenser of quests.

    """


class EvAdventureMob(EvAdventureNPC):
    """
    Mob (mobile) NPC; this is usually an enemy.

    """

    # chance (%) that this enemy will loot you when defeating you
    loot_chance = AttributeProperty(75)

    def ai_combat_next_action(self, combathandler):
        """
        Called to get the next action in combat.

        Args:
            combathandler (EvAdventureCombatHandler): The currently active combathandler.

        Returns:
            tuple: A tuple `(str, tuple, dict)`, being the `action_key`, and the `*args` and
            `**kwargs` for that action. The action-key is that of a CombatAction available to the
            combatant in the current combat handler.

        """
        from .combat_turnbased import CombatActionAttack, CombatActionDoNothing

        if self.is_idle:
            # mob just stands around
            return CombatActionDoNothing.key, (), {}

        target = choice(combathandler.get_enemy_targets(self))

        # simply randomly decide what action to take
        action = choice(
            (
                CombatActionAttack,
                CombatActionDoNothing,
            )
        )
        return action.key, (target,), {}

    def at_defeat(self):
        """
        Mobs die right away when defeated, no death-table rolls.

        """
        self.at_death()

    def at_loot(self, looted):
        """
        Called when mob gets to loot a PC.

        """
        if dice.roll("1d100") > self.loot_chance:
            # don't loot
            return

        if looted.coins:
            # looter prefer coins
            loot = dice.roll("1d20")
            if looted.coins < loot:
                self.location.msg_location(
                    "$You(looter) loots $You() for all coin!",
                    from_obj=looted,
                    mapping={"looter": self},
                )
            else:
                self.location.msg_location(
                    "$You(looter) loots $You() for |y{loot}|n coins!",
                    from_obj=looted,
                    mapping={"looter": self},
                )
        elif hasattr(looted, "equipment"):
            # go through backpack, first usable, then wieldable, wearable items
            # and finally stuff wielded
            stealable = looted.equipment.get_usable_objects_from_backpack()
            if not stealable:
                stealable = looted.equipment.get_wieldable_objects_from_backpack()
            if not stealable:
                stealable = looted.equipment.get_wearable_objects_from_backpack()
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.SHIELD_HAND]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.HEAD]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.ARMOR]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.WEAPON_HAND]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.TWO_HANDS]]

            stolen = looted.equipment.remove(choice(stealable))
            stolen.location = self

            self.location.msg_location(
                "$You(looter) steals {stolen.key} from $You()!",
                from_obj=looted,
                mapping={"looter": self},
            )
