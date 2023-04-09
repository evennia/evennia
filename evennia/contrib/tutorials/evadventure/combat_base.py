"""
EvAdventure Base combat utilities.

This establishes the basic building blocks for combat:

    - `CombatAction` - classes encompassing all the working around an action. They are initialized
      from 'action-dicts` - dictionaries with all the relevant data for the particular invocation
    - `CombatHandler` - base class for running a combat. Exactly how this is used depends on the
      type of combat intended (twitch- or turn-based) so many details of this will be implemented
      in child classes.


"""

import random
from collections import defaultdict, deque

from evennia import CmdSet, Command, create_script, default_cmds
from evennia.commands.command import InterruptCommand
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import dbserialize, delay, evmenu, evtable, logger
from evennia.utils.utils import display_len, inherits_from, list_to_string, pad

from . import rules
from .characters import EvAdventureCharacter
from .enums import ABILITY_REVERSE_MAP, Ability, ObjType
from .npcs import EvAdventureNPC
from .objects import EvAdventureObject

COMBAT_HANDLER_KEY = "evadventure_turnbased_combathandler"
COMBAT_HANDLER_INTERVAL = 30


class CombatFailure(RuntimeError):
    """
    Some failure during actions.

    """


# Combat action classes


class CombatAction:
    """
    Parent class for all actions.

    This represents the executable code to run to perform an action. It is initialized from an
    'action-dict', a set of properties stored in the action queue by each combatant.

    """

    def __init__(self, combathandler, combatant, action_dict):
        """
        Each key-value pair in the action-dict is stored as a property on this class
        for later access.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant performing
                the action.
            action_dict (dict): A dict containing all properties to initialize on this
                class. This should not be any keys with `_` prefix, since these are
                used internally by the class.

        """
        self.combathandler = combathandler
        self.combatant = combatant

        # store the action dicts' keys as properties accessible as e.g. action.target etc
        for key, val in action_dict.items():
            if not key.startswith("_"):
                setattr(self, key, val)

    def msg(self, message, broadcast=True):
        """
        Convenience route to the combathandler msg-sender mechanism.

        Args:
            message (str): Message to send; use `$You()` and `$You(other.key)` to refer to
                the combatant doing the action and other combatants, respectively.

        """
        self.combathandler.msg(message, combatant=self.combatant, broadcast=broadcast)

    def can_use(self):
        """
        Called to determine if the action is usable with the current settings. This does not
        actually perform the action.

        Returns:
            bool: If this action can be used at this time.

        """
        return True

    def execute(self):
        """
        Perform the action as the combatant. Should normally make use of the properties
        stored on the class during initialization.

        """
        pass

    def post_execute(self):
        """
        Called after execution.
        """
        pass


class CombatActionHold(CombatAction):
    """
    Action that does nothing.

    Note:
        Refer to as 'hold'

    action_dict = {
            "key": "hold"
        }
    """


class CombatActionAttack(CombatAction):
    """
    A regular attack, using a wielded weapon.

    action-dict = {
            "key": "attack",
            "target": Character/Object
        }

    Note:
        Refer to as 'attack'

    """

    def execute(self):
        attacker = self.combatant
        weapon = attacker.weapon
        target = self.target

        if weapon.at_pre_use(attacker, target):
            weapon.use(attacker, target, advantage=self.has_advantage(attacker, target))
            weapon.at_post_use(attacker, target)


class CombatActionStunt(CombatAction):
    """
    Perform a stunt the grants a beneficiary (can be self) advantage on their next action against a
    target. Whenever performing a stunt that would affect another negatively (giving them disadvantage
    against an ally, or granting an advantage against them, we need to make a check first. We don't
    do a check if giving an advantage to an ally or ourselves.

    action_dict = {
           "key": "stunt",
           "recipient": Character/NPC,
           "target": Character/NPC,
           "advantage": bool,  # if False, it's a disadvantage
           "stunt_type": Ability,  # what ability (like STR, DEX etc) to use to perform this stunt.
           "defense_type": Ability, # what ability to use to defend against (negative) effects of this
               stunt.
        }

    Note:
        refer to as 'stunt'.

    """

    def execute(self):
        combathandler = self.combathandler
        attacker = self.combatant
        recipient = self.recipient  # the one to receive the effect of the stunt
        target = self.target  # the affected by the stunt (can be the same as recipient/combatant)
        txt = ""

        if recipient == target:
            # grant another entity dis/advantage against themselves
            defender = recipient
        else:
            # recipient not same as target; who will defend depends on disadvantage or advantage
            # to give.
            defender = target if self.advantage else recipient

        # trying to give advantage to recipient against target. Target defends against caller
        is_success, _, txt = rules.dice.opposed_saving_throw(
            attacker,
            defender,
            attack_type=self.stunt_type,
            defense_type=self.defense_type,
            advantage=combathandler.has_advantage(attacker, defender),
            disadvantage=combathandler.has_disadvantage(attacker, defender),
        )

        self.msg(f"$You() $conj(attempt) stunt on $You({defender.key}). {txt}")

        # deal with results
        if is_success:
            if self.advantage:
                combathandler.give_advantage(recipient, target)
            else:
                combathandler.give_disadvantage(recipient, target)
            if recipient == self.combatant:
                self.msg(
                    f"$You() $conj(gain) {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            else:
                self.msg(
                    f"$You() $conj(cause) $You({recipient.key}) "
                    f"to gain {'advantage' if self.advantage else 'disadvantage'} "
                    f"against $You({target.key})!"
                )
            self.msg(
                "|yHaving succeeded, you hold back to plan your next move.|n [hold]",
                broadcast=False,
            )
            combathandler.queue_action(attacker, combathandler.default_action_dict)
        else:
            self.msg(f"$You({defender.key}) $conj(resist)! $You() $conj(fail) the stunt.")


class CombatActionUseItem(CombatAction):
    """
    Use an item in combat. This is meant for one-off or limited-use items (so things like
    scrolls and potions, not swords and shields). If this is some sort of weapon or spell rune,
    we refer to the item to determine what to use for attack/defense rolls.

    action_dict = {
            "key": "use",
            "item": Object
            "target": Character/NPC/Object/None
        }

    Note:
        Refer to as 'use'

    """

    def execute(self):
        item = self.item
        user = self.combatant
        target = self.target

        if item.at_pre_use(user, target):
            item.use(
                user,
                target,
                advantage=self.has_advantage(user, target),
                disadvantage=self.has_disadvantage(user, target),
            )
            item.at_post_use(user, target)
        # to back to idle after this
        self.combathandler.queue_action(self.combatant, self.combathandler.fallback_action_dict)


class CombatActionWield(CombatAction):
    """
    Wield a new weapon (or spell) from your inventory. This will swap out the one you are currently
    wielding, if any.

    action_dict = {
            "key": "wield",
            "item": Object
        }

    Note:
        Refer to as 'wield'.

    """

    def execute(self):
        self.combatant.equipment.move(self.item)
        self.combathandler.queue_action(self.combatant, self.combathandler.fallback_action_dict)


# main combathandler


class EvAdventureCombatHandlerBase(DefaultScript):
    """
    This script is created when a combat starts. It 'ticks' the combat and tracks
    all sides of it.

    """

    # available actions in combat
    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
    }

    # fallback action if not selecting anything
    fallback_action_dict = AttributeProperty({"key": "hold"}, autocreate=False)

    @classmethod
    def get_or_create_combathandler(cls, obj, combathandler_key="combathandler", **kwargs):
        """
        Get or create a combathandler on `obj`.

        Args:
            obj (any): The Typeclassed entity to store the CombatHandler Script on. This could be
                a location (for turn-based combat) or a Character (for twitch-based combat).
        Keyword Args:
            combathandler_key (str): They key name for the script. Will be 'combathandler' by default.
            **kwargs: Arguments to the Script, if it is created.

        """
        if not obj:
            raise CombatFailure("Cannot start combat without a place to do it!")

        combathandler = obj.ndb.combathandler
        if not combathandler:
            combathandler = obj.scripts.get(combathandler_name).first()
            if not combathandler:
                # have to create from scratch
                persistent = kwargs.pop("persistent", True)
                combathandler = create_script(
                    cls, key=combathandler_key, obj=obj, persistent=persistent, **kwargs
                )
            self.caller.ndb.combathandler = combathandler
        return combathandler

    def msg(self, message, combatant=None, broadcast=True):
        """
        Central place for sending messages to combatants. This allows
        for adding any combat-specific text-decoration in one place.

        Args:
            message (str): The message to send.
            combatant (Object): The 'You' in the message, if any.
            broadcast (bool): If `False`, `combatant` must be included and
                will be the only one to see the message. If `True`, send to
                everyone in the location.

        Notes:
            If `combatant` is given, use `$You/you()` markup to create
            a message that looks different depending on who sees it. Use
            `$You(combatant_key)` to refer to other combatants.

        """
        location = self.obj
        location_objs = location.contents

        exclude = []
        if not broadcast and combatant:
            exclude = [obj for obj in location_objs if obj is not combatant]

        location.msg_contents(
            message,
            exclude=exclude,
            from_obj=combatant,
            mapping={locobj.key: locobj for locobj in location_objs},
        )

    def get_combat_summary(self, combatant):
        """
        Get a 'battle report' - an overview of the current state of combat from the perspective
        of one of the sides.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant to get.

        Returns:
            EvTable: A table representing the current state of combat.

        Example:
        ::

                                        Goblin shaman (Perfect)[attack]
        Gregor (Hurt)[attack]           Goblin brawler(Hurt)[attack]
        Bob (Perfect)[stunt]     vs     Goblin grunt 1 (Hurt)[attack]
                                        Goblin grunt 2 (Perfect)[hold]
                                        Goblin grunt 3 (Wounded)[flee]

        """
        allies, enemies = self.get_sides(combatant)
        # we must include outselves at the top of the list (we are not returned from get_sides)
        allies.insert(0, combatant)
        nallies, nenemies = len(allies), len(enemies)

        # prepare colors and hurt-levels
        allies = [
            f"{ally} ({ally.hurt_level})[{self.get_next_action_dict(ally)['key']}]"
            for ally in allies
        ]
        enemies = [
            f"{enemy} ({enemy.hurt_level})[{self.get_next_action_dict(enemy)['key']}]"
            for enemy in enemies
        ]

        # the center column with the 'vs'
        vs_column = ["" for _ in range(max(nallies, nenemies))]
        vs_column[len(vs_column) // 2] = "|wvs|n"

        # the two allies / enemies columns should be centered vertically
        diff = abs(nallies - nenemies)
        top_empty = diff // 2
        bot_empty = diff - top_empty
        topfill = ["" for _ in range(top_empty)]
        botfill = ["" for _ in range(bot_empty)]

        if nallies >= nenemies:
            enemies = topfill + enemies + botfill
        else:
            allies = topfill + allies + botfill

        # make a table with three columns
        return evtable.EvTable(
            table=[
                evtable.EvColumn(*allies, align="l"),
                evtable.EvColumn(*vs_column, align="c"),
                evtable.EvColumn(*enemies, align="r"),
            ],
            border=None,
            maxwidth=78,
        )

    def get_sides(self, combatant):
        """
        Get a listing of the two 'sides' of this combat, from the perspective of the provided
        combatant. The sides don't need to be balanced.

        Args:
            combatant (Character or NPC): The one whose sides are to determined.

        Returns:
            tuple: A tuple of lists `(allies, enemies)`, from the perspective of `combatant`.

        Note:
            The sides are found by checking PCs vs NPCs. PCs can normally not attack other PCs, so
            are naturally allies. If the current room has the `allow_pvp` Attribute set, then _all_
            other combatants (PCs and NPCs alike) are considered valid enemies (one could expand
            this with group mechanics).

        """
        raise NotImplemented

    def give_advantage(self, recipient, target):
        """
        Let a benefiter gain advantage against the target.

        Args:
            recipient (Character or NPC): The one to gain the advantage. This may or may not
                be the same entity that creates the advantage in the first place.
            target (Character or NPC): The one against which the target gains advantage. This
                could (in principle) be the same as the benefiter (e.g. gaining advantage on
                some future boost)

        """
        raise NotImplemented

    def give_disadvantage(self, recipient, target):
        """
        Let an affected party gain disadvantage against a target.

        Args:
            recipient (Character or NPC): The one to get the disadvantage.
            target (Character or NPC): The one against which the target gains disadvantage, usually an enemy.

        """
        raise NotImplemented

    def has_advantage(self, combatant, target):
        """
        Check if a given combatant has advantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have advantage
            target (Character or NPC): The target to check advantage against.

        """
        raise NotImplemented

    def has_disadvantage(self, combatant, target):
        """
        Check if a given combatant has disadvantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have disadvantage
            target (Character or NPC): The target to check disadvantage against.

        """
        raise NotImplemented

    def queue_action(self, combatant, action_dict):
        """
        Queue an action by adding the new actiondict to the back of the queue. If the
        queue was alrady at max-size, the front of the queue will be discarded.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): A combatant queueing the action.
            action_dict (dict): A dict describing the action class by name along with properties.

        Example:
            If the queue max-size is 3 and was `[a, b, c]` (where each element is an action-dict),
            then using this method to add the new action-dict `d` will lead to a queue `[b, c, d]` -
            that is, adding the new action will discard the one currently at the front of the queue
            to make room.

        """
        raise NotImplemented

    def execute_next_action(self, combatant):
        """
        Perform a combatant's next action.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant performing and action.


        """
        raise NotImplemented

    def start_combat(self):
        """
        Start combat.

        """
        raise NotImplemented

    def check_stop_combat(self):
        """
        Check if this combat should be aborted, whatever this means for the particular
        the particular combat type.

        Stop the combat immediately. This should also do all needed  cleanup.

        Keyword Args:
            kwargs: Any extra keyword args used.

        Returns:
            bool: If `True`, the `stop_combat` method sho

        """
        raise NotImplemented

    def stop_combat(self):
        """
        Stop combat. This should also do all cleanup.
        """
        raise NotImplemented
