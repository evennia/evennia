"""
EvAdventure turn-based combat

This implements a turn-based combat style, where both sides have a little longer time to
choose their next action. If they don't react before a timer runs out, the previous action
will be repeated. This means that a 'twitch' style combat can be created using the same
mechanism, by just speeding up each 'turn'.

The combat is handled with a `Script` shared between all combatants; this tracks the state
of combat and handles all timing elements.

Unlike in base _Knave_, the MUD version's combat is simultaneous; everyone plans and executes
their turns simultaneously with minimum downtime.

This version is simplified to not worry about things like optimal range etc. So a bow can be used
the same as a sword in battle. One could add a 1D range mechanism to add more strategy by requiring
optimizal positioning.

The combat is controlled through a menu:

------------------- main menu
Combat

You have 30 seconds to choose your next action. If you don't decide, you will hesitate and do
nothing. Available actions:

1. [A]ttack/[C]ast spell at <target> using your equipped weapon/spell
3. Make [S]tunt <target/yourself> (gain/give advantage/disadvantage for future attacks)
4. S[W]ap weapon / spell rune
5. [U]se <item>
6. [F]lee/disengage (takes one turn, during which attacks have advantage against you)
8. [H]esitate/Do nothing

You can also use say/emote between rounds.
As soon as all combatants have made their choice (or time out), the round will be resolved
simultaneusly.

-------------------- attack/cast spell submenu

Choose the target of your attack/spell:
0: Yourself              3: <enemy 3> (wounded)
1: <enemy 1> (hurt)
2: <enemy 2> (unharmed)

------------------- make stunt submenu

Stunts are special actions that don't cause damage but grant advantage for you or
an ally for future attacks - or grant disadvantage to your enemy's future attacks.
The effects of stunts start to apply *next* round. The effect does not stack, can only
be used once and must be taken advantage of within 5 rounds.

Choose stunt:
1: Trip <target> (give disadvantage DEX)
2: Feint <target> (get advantage DEX against target)
3: ...

-------------------- make stunt target submenu

Choose the target of your stunt:
0: Yourself                  3: <combatant 3> (wounded)
1: <combatant 1> (hurt)
2: <combatant 2> (unharmed)

-------------------  swap weapon or spell run

Choose the item to wield.
1: <item1>
2: <item2> (two hands)
3: <item3>
4: ...

------------------- use item

Choose item to use.
1: Healing potion (+1d6 HP)
2: Magic pebble (gain advantage, 1 use)
3: Potion of glue (give disadvantage to target)

------------------- Hesitate/Do nothing

You hang back, passively defending.

------------------- Disengage

You retreat, getting ready to get out of combat. Use two times in a row to
leave combat. You flee last in a round. If anyone Blocks your retreat, this counter resets.

------------------- Block Fleeing

You move to block the escape route of an opponent. If you win a DEX challenge,
you'll negate the target's disengage action(s).

Choose who to block:
1: <enemy 1>
2: <enemy 2>
3: ...


"""

import random
from collections import defaultdict, deque

from evennia import CmdSet, Command, create_script
from evennia.commands.command import InterruptCommand
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import dbserialize, delay, evmenu, evtable, logger
from evennia.utils.utils import inherits_from, list_to_string

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

        for key, val in action_dict.items():
            setattr(self, key, val)

    # advantage / disadvantage
    # These should be read as 'does <recipient> have dis/advantaget against <target>'.
    def give_advantage(self, recipient, target, **kwargs):
        self.combathandler.advantage_matrix[recipient][target] = True

    def give_disadvantage(self, recipient, target, **kwargs):
        self.combathandler.disadvantage_matrix[recipient][target] = True

    def has_advantage(self, recipient, target):
        return bool(self.combathandler.advantage_matrix[recipient].pop(target, False)) or (
            target in self.combathandler.fleeing_combatants
        )

    def has_disadvantage(self, recipient, target):
        return bool(self.combathandler.disadvantage_matrix[recipient].pop(target, False)) or (
            recipient in self.combathandler.fleeing_combatants
        )

    def lose_advantage(self, recipient, target):
        self.combathandler.advantage_matrix[recipient][target] = False

    def lose_disadvantage(self, recipient, target):
        self.combathandler.disadvantage_matrix[recipient][target] = False

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
        # most actions abort ongoing fleeing actions.
        self.combathandler.fleeing_combatants.pop(self.combatant, None)


class CombatActionDoNothing(CombatAction):
    """
    Action that does nothing.

    Note:
        Refer to as 'nothing'

    action_dict = {
            "key": "nothing"
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
        attacker = self.combatant
        recipient = self.recipient  # the one to receive the effect of the stunt
        target = self.target  # the affected by the stunt (can be the same as recipient/combatant)
        is_success = False
        txt = ""

        if target == self.combatant:
            # can always grant dis/advantage against yourself
            defender = attacker
            is_success = True
        elif recipient == target:
            # grant another entity dis/advantage against themselves
            defender = recipient
        else:
            # recipient not same as target; who will defend depends on disadvantage or advantage
            # to give.
            defender = target if self.advantage else recipient

        self.stunt_type = ABILITY_REVERSE_MAP.get(self.stunt_type, self.stunt_type)
        self.defense_type = ABILITY_REVERSE_MAP.get(self.defense_type, self.defense_type)

        if not is_success:
            # trying to give advantage to recipient against target. Target defends against caller
            is_success, _, txt = rules.dice.opposed_saving_throw(
                attacker,
                defender,
                attack_type=self.stunt_type,
                defense_type=self.defense_type,
                advantage=self.has_advantage(attacker, defender),
                disadvantage=self.has_disadvantage(attacker, defender),
            )

        # deal with results
        self.msg(f"$You() $conj(attempt) stunt on $You(defender.key). {txt}")
        if is_success:
            if self.advantage:
                self.give_advantage(recipient, target)
            else:
                self.give_disadvantage(recipient, target)
            self.msg(
                f"%You() $conj(cause) $You({recipient.key}) "
                f"to gain {'advantage' if self.advantage else 'disadvantage'} "
                f"against $You({target.key})!"
            )
        else:
            self.msg(f"$You({target.key}) resists! $You() $conj(fail) the stunt.")


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


class CombatActionFlee(CombatAction):
    """
    Start (or continue) fleeing/disengaging from combat.

    action_dict = {
           "key": "flee",
        }

    Note:
        Refer to as 'flee'.

    """

    def execute(self):

        if self.combatant not in self.combathandler.fleeing_combatants:
            # we record the turn on which we started fleeing
            self.combathandler.fleeing_combatants[self.combatant] = self.combathandler.turn

        flee_timeout = self.combathandler.flee_timeout
        self.msg(
            "$You() $conj(retreat), leaving yourself exposed while doing so (will escape in "
            f"{flee_timeout} $pluralize(turn, {flee_timeout}))."
        )

    def post_execute(self):
        """
        We override the default since we don't want to cancel fleeing here.
        """
        pass


class EvAdventureCombatHandler(DefaultScript):
    """
    This script is created when a combat starts. It 'ticks' the combat and tracks
    all sides of it.

    """

    # available actions in combat
    action_classes = {
        "nothing": CombatActionDoNothing,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": CombatActionFlee,
    }

    # how many actions can be queued at a time (per combatant)
    max_action_queue_size = 1

    # fallback action if not selecting anything
    fallback_action_dict = {"key": "nothing"}

    # how many turns you must be fleeing before escaping
    flee_timeout = 1

    # persistent storage

    turn = AttributeProperty(0)

    # who is involved in combat, and their action queue,
    # as {combatant: [actiondict, actiondict,...]}
    combatants = AttributeProperty(dict)

    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    fleeing_combatants = AttributeProperty(dict)
    defeated_combatants = AttributeProperty(list)

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

    def add_combatant(self, combatant):
        """
        Add a new combatant to the battle.

        Args:
            *combatants (EvAdventureCharacter, EvAdventureNPC): Any number of combatants to add to
                the combat.
        """
        if combatant not in self.combatants:
            self.combatants[combatant] = deque((), maxlen=self.max_action_queue_size)
            return True
        return False

    def remove_combatant(self, combatant):
        """
        Remove a combatant from the battle. This removes their queue.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): A combatant to add to
                the combat.

        """
        self.combatants.pop(combatant, None)

    def stop_combat(self):
        """
        Stop the combat immediately.

        """
        for combatant in self.combatants:
            self.remove_combatant(combatant)
        self.stop()
        self.delete()

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
        if self.obj.allow_pvp:
            # in pvp, everyone else is an ememy
            allies = [combatant]
            enemies = [comb for comb in self.combatants if comb != combatant]
        else:
            # otherwise, enemies/allies depend on who combatant is
            pcs = [comb for comb in self.combatants if inherits_from(comb, EvAdventureCharacter)]
            npcs = [comb for comb in self.combatants if comb not in pcs]
            if combatant in pcs:
                # combatant is a PC, so NPCs are all enemies
                allies = [comb for comb in pcs if comb != combatant]
                enemies = npcs
            else:
                # combatant is an NPC, so PCs are all enemies
                allies = [comb for comb in npcs if comb != combatant]
                enemies = pcs
        return allies, enemies

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
        self.combatants[combatant].append(action_dict)

        # track who inserted actions this turn (non-persistent)
        did_action = set(self.nbd.did_action or ())
        did_action.add(combatant)
        if len(did_action) >= len(self.combatants):
            # everyone has inserted an action. Start next turn without waiting!
            self.force_repeat()

    def execute_next_action(self, combatant):
        """
        Perform a combatant's next queued action. Note that there is _always_ an action queued,
        even if this action is 'do nothing'. We don't pop anything from the queue, instead we keep
        rotating the queue. When the queue has a length of one, this means just repeating the
        same action over and over.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant performing and action.

        Example:
            If the combatant's action queue is `[a, b, c]` (where each element is an action-dict),
            then calling this method will lead to action `a` being performed. After this method, the
            queue will be rotated to the left and be `[b, c, a]` (so next time, `b` will be used).

        """
        action_queue = self.combatants[combatant]
        action_dict = action_queue[0] if action_queue else self.fallback_action_dict
        # rotate the queue to the left so that the first element is now the last one
        action_queue.rotate(-1)

        # use the action-dict to select and create an action from an action class
        action_class = self.action_classes[action_dict["key"]]
        action = action_class(self, combatant, action_dict)

        action.execute()
        action.post_execute()

    def execute_full_turn(self):
        """
        Perform a full turn of combat, performing everyone's actions in random order.

        """
        self.turn += 1
        # random turn order
        combatants = list(self.combatants.keys())
        random.shuffle(combatants)  # shuffles in place

        # do everyone's next queued combat action
        for combatant in combatants:
            self.execute_next_action(combatant)

        # check if anyone is defeated
        for combatant in list(self.combatants.keys()):
            if combatant.hp <= 0:
                # PCs roll on the death table here, NPCs die. Even if PCs survive, they
                # are still out of the fight.
                combatant.at_defeat()
                self.combatants.pop(combatant)
                self.defeated_combatants.append(combatant)
                self.msg("|r$You() $conj(fall) to the ground, defeated.|n", combatant=combatant)

        # check if anyone managed to flee
        flee_timeout = self.flee_timeout
        for combatant, started_fleeing in self.fleeing_combatants.items():
            if self.turn - started_fleeing >= flee_timeout:
                # if they are still alive/fleeing and have been fleeing long enough, escape
                self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
                self.remove_combatant(combatant)

        # check if one side won the battle
        if not self.combatants:
            # noone left in combat - maybe they killed each other or all fled
            surviving_combatant = None
            allies, enemies = (), ()
        else:
            # grab a random survivor and check of they have any living enemies.
            surviving_combatant = random.choice(list(self.combatants.keys()))
            allies, enemies = self.get_sides(surviving_combatant)

        if not enemies:
            # if one way or another, there are no more enemies to fight
            still_standing = list_to_string(f"$You({comb.key})" for comb in allies)
            knocked_out = list_to_string(comb for comb in self.defeated_combatants if comb.hp > 0)
            killed = list_to_string(comb for comb in self.defeated_combatants if comb.hp <= 0)

            if still_standing:
                txt = [f"The combat is over. {still_standing} are still standing."]
            else:
                txt = ["The combat is over. No-one stands as the victor."]
            if knocked_out:
                txt.append(f"{knocked_out} were taken down, but will live.")
            if killed:
                txt.append(f"{killed} were killed.")
            self.msg(txt)
            self.stop_combat()

    def get_combat_summary(self, combatant):
        """
        Get a 'battle report' - an overview of the current state of combat.

                                    Goblin shaman
        Ally (hurt)                 Goblin brawler
        Bob               vs        Goblin grunt 1 (hurt)
                                    Goblin grunt 2
                                    Goblin grunt 3

        """
        allies, enemies = self.get_sides(combatant)
        nallies, nenemies = len(allies), len(enemies)

        # make a table with three columns


def get_or_create_combathandler(combatant, combathandler_name="combathandler", combat_tick=5):
    """
    Joins or continues combat. This is a access function that will either get the
    combathandler on the current room or create a new one.

    Args:
        combatant (EvAdventureCharacter, EvAdventureNPC): The one to

    Returns:
        CombatHandler: The new or created combathandler.

    """

    location = combatant.location

    if not location:
        raise CombatFailure("Cannot start combat without a location.")

    combathandler = location.scripts.get(combathandler_name)
    if not combathandler:
        combathandler = create_script(
            EvAdventureCombatHandler,
            key=combathandler_name,
            obj=location,
            interval=combat_tick,
            persistent=True,
        )
    combathandler.add_combatant(combatant)
    return combathandler


# ------------------------------------------------------------
#
# Tick-based fast combat (Diku-style)
#
#   To use, add `CmdCombat` (only) to CharacterCmdset
#
# ------------------------------------------------------------

_COMBAT_HELP = """|rYou are in combat!|n

Examples of commands:

    - |yhit/attack <target>|n   - strike, hit or smite your foe with your current weapon or spell
    - |ywield <item>|n          - wield a weapon, shield or spell rune, swapping old with new

    - |yboost STR of <recipient> vs <target>|n   - give an ally advantage on their next STR action
    - |yboost INT vs <target>|n                  - give yourself advantage on your next INT action
    - |yfoil DEX of <recipient> vs <target>|n    - give an enemy disadvantage on their next DEX action

    - |yuse <item>|n                             - use/consume an item in your inventory
    - |yuse <item> on <target>|n                 - use an item on an enemy or ally

    - |yflee|n                                   - start to flee or disengage from combat

Use |yhelp <command>|n for more info."""


class _CmdCombatBase(Command):
    """
    Base combat class for combat. Change the combat-tick to determine
    how quickly the combat will 'tick'.

    """

    combathandler_name = "combathandler"
    combat_tick = 2
    flee_timeout = 5

    @property
    def combathandler(self):
        combathandler = getattr(self, "combathandler", None)
        if not combathandler:
            self.combathandler = combathandler = get_or_create_combathandler(self.caller)
        return combathandler

    def parse(self):
        super().parse()

        self.args = self.args.strip()

        if not self.caller.location or not self.callerlocation.allow_combat:
            self.msg("Can't fight here!")
            raise InterruptCommand()


class CombatCmdSet(CmdSet):
    """
    Commands to make available while in combat. Note that
    the 'attack' command should also be added to the CharacterCmdSet,
    in order for the user to attack things.

    """

    priority = 1
    mergetype = "Union"  # use Replace to lock down all other commands
    no_exits = True  # don't allow combatants to walk away

    def at_cmdset_creation(self):
        self.add(CmdAttack())
        self.add(CmdStunt())
        self.add(CmdUseItem())
        self.add(CmdWield())
        self.add(CmdUseFlee())


class CmdAttack(_CmdCombatBase):
    """
    Start or join a fight. Your attack will be using the Ability relevent for your current weapon
    (STR for melee, WIS for ranged attacks, INT for magic)

    Usage:
      attack <target>
      hit <target>

    """

    key = "attack"
    aliases = ("hit",)
    help_category = "combat"

    def parse(self):
        super().parse()
        self.args = self.args.strip()

    def func(self):
        if not self.args:
            self.msg("What are you attacking?")
            reuturn

        target = self.search(self.args)
        if not target:
            return

        if not hasattr(target, "hp"):
            self.msg(f"You can't attack that.")
            return
        elif target.hp <= 0:
            self.msg(f"{target.get_display_name(self.caller)} is already down.")
            return

        # this can be done over and over
        is_new = self.combathandler.add_combatant(self)
        if is_new:
            # just joined combat - add the combat cmdset
            self.caller.cmdset.add(CombatCmdSet)
            self.msg(_COMBAT_HELP)
        self.combathandler.queue_action(self.caller, {"key": "attack", "target": target})
        self.msg("You prepare to attack!")


class CmdStunt(_CmdCombatBase):
    """
    Perform a combat stunt, that boosts an ally against a target, or
    foils an enemy, giving them disadvantage against an ally.

    Usage:
        boost [ability] [of] <recipient> vs <target>
        foil [ability] [of] <recipient> vs <target>
        boost [ability] [vs] <target>       (same as boost me vs target)
        foil [ability] [of] <target>        (same as foil <target> vs me)

    Example:
        boost STR of me vs Goblin
        boost DEX vs Goblin
        foil STR Goblin me
        foil INT Goblin
        boost INT Wizard vs Goblin

    """

    key = "stunt"
    aliases = (
        "boost",
        "foil",
    )
    help_category = "combat"

    def parse(self):
        super().parse()
        args = self.args
        if "of" in args:
            self.stunt_type, args = (part.strip() for part in args.split("of", 1))
        else:
            self.stunt_type, args = (part.strip() for part in args.split(None, 1))

        if " vs " in args:
            self.recipient, self.target = (part.strip() for part in args.split(" vs "))
        elif self.cmdname == "foil":
            self.recipient, self.target = "me", args.strip()
        else:
            self.recipient, self.target = args.strip(), "me"
        self.advantage = self.cmdname == "boost"

    def func(self):
        self.combathandler.queue_action(
            self.caller,
            {
                "key": "stunt",
                "recipient": self.recipient,
                "target": self.target,
                "advantage": self.advantage,
                "stunt_type": self.stunt_type,
                "defense_type": self.stunt_type,
            },
        )
        self.msg("You prepare a stunt!")


class CmdUseItem(_CmdCombatBase):
    """
    Use an item in combat. The item must be in your inventory to use.

    Usage:
        use <item>
        use <item> [on] <target>

    Examples:
        use potion
        use throwing knife on goblin
        use bomb goblin

    """

    key = "use"
    help_category = "combat"

    def parse(self):
        super().parse()
        args = self.args

        if "on" in args:
            self.item, self.target = (part.strip() for part in args.split("on", 1))
        else:
            self.item, *target = args.split(None, 1)
            self.target = target[0] if target else "me"

    def func(self):

        item = self.caller.search(
            self.item, candidates=self.caller.equipment.get_usable_objects_from_backpack()
        )
        if not item:
            self.msg("(You must carry the item to use it.)")
            return
        if self.target:
            target = self.caller.search(self.target)
            if not target:
                return

        self.combathandler.queue_action(self.caller, {"key": "use", "item": item, "target": target})
        self.msg(f"You prepare to use {item.get_display_name(self.caller)}!")


class CmdWield(_CmdCombatBase):
    """
    Wield a weapon or spell-rune. You will the wield the item, swapping with any other item(s) you
    were wielded before.

    Usage:
      wield <weapon or spell>

    Examples:
      wield sword
      wield shield
      wield fireball

    Note that wielding a shield will not replace the sword in your hand, while wielding a two-handed
    weapon (or a spell-rune) will take two hands and swap out what you were carrying.

    """

    key = "wield"
    help_category = "combat"

    def func(self):

        item = self.caller.search(
            self.args, candidates=self.caller.equipment.get_wieldable_objects_from_backpack()
        )
        if not item:
            self.msg("(You must carry the item to wield it.)")
            return
        self.combathandler.queue_action(self.caller, {"key": "wield", "item": item})
        self.msg(f"You start wielding {item.get_display_name(self.caller)}!")


class CmdFlee(_CmdCombatBase):
    """
    Flee or disengage from combat. An opponent may attempt a 'hinder' action to stop you
    with a DEX challenge.

    Usage:
      flee

    """

    key = "flee"
    aliases = ["disengage"]
    help_category = "combat"

    def func(self):
        self.combathandler.queue_action(self.caller, {"key": "flee"})
        self.msg("You prepare to flee!")


# -----------------------------------------------------------------------------------
#
# Turn-based combat (Final Fantasy style), using a menu
#
# -----------------------------------------------------------------------------------


def _get_combathandler(caller):
    evmenu = caller.ndb._evmenu
    if not hasattr(evmenu, "combathandler"):
        evmenu.combathandler = get_or_create_combathandler(caller)
    return evmenu.combathandler


def _select_target(caller, raw_string, **kwargs):
    """Helper to set a selection"""
    action_dict = kwargs["action_dict"]
    action_dict["target"] = kwargs["target"]

    _get_combathandler(caller).queue_action(caller, action_dict)


def node_choose_target(caller, raw_string, **kwargs):
    """
    Choose target!

    """
    text = kwargs.get("text", "Choose your target!")
    target_type = kwargs.get("target_type", "enemies")

    combathandler = _get_combathandler(caller)
    allies, enemies = combathandler.get_sides(caller)

    if target_type == "enemies":
        targets = enemies
    else:
        targets = allies

    options = [
        {
            "desc": target.get_display_name(caller),
            "goto": (_select_target, {"target": target, **kwargs}),
        }
        for target in targets
    ]

    return text, options


def node_combat(caller, raw_string, **kwargs):
    """Base combat menu"""
    text = ""


## -----------------------------------------------------------------------------------
##  Combat Actions
## -----------------------------------------------------------------------------------
#
#
# class CombatAction:
#    """
#    This is the base of a combat-action, like 'attack'  Inherit from this to make new actions.
#
#    Note:
#        We want to store initialized version of this objects in the CombatHandler (in order to track
#        usages, time limits etc), so we need to make sure we can serialize it into an Attribute. See
#        `Attribute` documentation for more about `__serialize_dbobjs__` and
#        `__deserialize_dbobjs__`.
#
#    """
#
#    key = "Action"
#    desc = "Option text"
#    aliases = []
#    help_text = "Combat action to perform."
#
#    # the next combat menu node to go to - this ties the combat action into the UI
#    # use None to do nothing (jump directly to registering the action)
#    next_menu_node = "node_select_action"
#
#    max_uses = None  # None for unlimited
#    # in which order (highest first) to perform the action. If identical, use random order
#    priority = 0
#
#    def __init__(self, combathandler, combatant):
#        self.combathandler = combathandler
#        self.combatant = combatant
#        self.uses = 0
#
#    def msg(self, message, broadcast=True):
#        """
#        Convenience route to the combathandler msg-sender mechanism.
#
#        Args:
#            message (str): Message to send; use `$You()` and `$You(other.key)`
#                to refer to the combatant doing the action and other combatants,
#                respectively.
#        """
#        self.combathandler.msg(message, combatant=self.combatant, broadcast=broadcast)
#
#    def __serialize_dbobjs__(self):
#        """
#        This is necessary in order to be able to store this entity in an Attribute.
#        We must make sure to tell Evennia how to serialize internally stored db-objects.
#
#        The `__serialize_dbobjs__` and `__deserialize_dbobjs__` methods form a required pair.
#
#        """
#        self.combathandler = dbserialize.dbserialize(self.combathandler)
#        self.combatant = dbserialize.dbserialize(self.combatant)
#
#    def __deserialize_dbobjs__(self):
#        """
#        This is necessary in order to be able to store this entity in an Attribute.
#        We must make sure to tell Evennia how to deserialize internally stored db-objects.
#
#        The `__serialize_dbobjs__` and `__deserialize_dbobjs__` methods form a required pair.
#
#        """
#        if isinstance(self.combathandler, bytes):
#            self.combathandler = dbserialize.dbunserialize(self.combathandler)
#            self.combatant = dbserialize.dbunserialize(self.combatant)
#
#    def get_help(self, *args, **kwargs):
#        """
#        Allows to customize help message on the fly. By default, just returns `.help_text`.
#
#        """
#        return self.help_text
#
#    def can_use(self, *args, **kwargs):
#        """
#        Determine if combatant can use this action. In this implementation,
#        it fails if already used up all of a usage-limited action.
#
#        Args:
#            *args: Any optional arguments.
#            **kwargs: Any optional keyword arguments.
#
#        Returns:
#            tuple: (bool, motivation) - if not available, will describe why,
#                if available, should describe what the action does.
#
#        """
#        return True if self.max_uses is None else self.uses < (self.max_uses or 0)
#
#    def pre_use(self, *args, **kwargs):
#        """
#        Called just before the main action.
#
#        """
#
#        pass
#
#    def use(self, *args, **kwargs):
#        """
#        Main activation of the action. This happens simultaneously to other actions.
#
#        """
#        pass
#
#    def post_use(self, *args, **kwargs):
#        """
#        Called just after the action has been taken.
#
#        """
#        pass
#
#
# class CombatActionAttack(CombatAction):
#    """
#    A regular attack, using a wielded weapon. Depending on weapon type, this will be a ranged or
#    melee attack.
#
#    """
#
#    key = "Attack or Cast"
#    desc = "[A]ttack/[C]ast spell at <target>"
#    aliases = ("a", "c", "attack", "cast")
#    help_text = "Make an attack using your currently equipped weapon/spell rune"
#    next_menu_node = "node_select_enemy_target"
#
#    priority = 1
#
#    def use(self, defender, *args, **kwargs):
#        """
#        Make an attack against a defender.
#
#        """
#        attacker = self.combatant
#        weapon = self.combatant.weapon
#
#        # figure out advantage (gained by previous stunts)
#        advantage = bool(self.combathandler.advantage_matrix[attacker].pop(defender, False))
#        # figure out disadvantage (gained by enemy stunts/actions)
#        disadvantage = bool(self.combathandler.disadvantage_matrix[attacker].pop(defender, False))
#
#        is_hit, quality, txt = rules.dice.opposed_saving_throw(
#            attacker,
#            defender,
#            attack_type=weapon.attack_type,
#            defense_type=attacker.weapon.defense_type,
#            advantage=advantage,
#            disadvantage=disadvantage,
#        )
#        self.msg(f"$You() $conj(attack) $You({defender.key}) with {weapon.key}: {txt}")
#        if is_hit:
#            # enemy hit, calculate damage
#            weapon_dmg_roll = attacker.weapon.damage_roll
#
#            dmg = rules.dice.roll(weapon_dmg_roll)
#
#            if quality is Ability.CRITICAL_SUCCESS:
#                dmg += rules.dice.roll(weapon_dmg_roll)
#                message = (
#                    f" $You() |ycritically|n $conj(hit) $You({defender.key}) for |r{dmg}|n damage!"
#                )
#            else:
#                message = f" $You() $conj(hit) $You({defender.key}) for |r{dmg}|n damage!"
#            self.msg(message)
#
#            # call hook
#            defender.at_damage(dmg, attacker=attacker)
#
#            # note that we mustn't remove anyone from combat yet, because this is
#            # happening simultaneously. So checking of the final hp
#            # and rolling of death etc happens in the combathandler at the end of the turn.
#
#        else:
#            # a miss
#            message = f" $You() $conj(miss) $You({defender.key})."
#            if quality is Ability.CRITICAL_FAILURE:
#                attacker.weapon.quality -= 1
#                message += ".. it's a |rcritical miss!|n, damaging the weapon."
#            self.msg(message)
#
#
# class CombatActionStunt(CombatAction):
#    """
#    Perform a stunt. A stunt grants an advantage to you or another player for their next
#    action, or a disadvantage to your or an enemy's next action.
#
#    Note that while the check happens between the user and a target, another (the 'beneficiary'
#    could still gain the effect. This allows for boosting allies or making them better
#    defend against an enemy.
#
#    Note: We only count a use if the stunt is successful; they will still spend their turn, but
#    won't spend a use unless they succeed.
#
#    """
#
#    key = "Perform a Stunt"
#    desc = "Make [S]tunt against <target>"
#    aliases = ("s", "stunt")
#    help_text = (
#        "A stunt does not cause damage but grants/gives advantage/disadvantage to future "
#        "actions. The effect needs to be used up within 5 turns."
#    )
#    next_menu_node = "node_select_enemy_target"
#
#    give_advantage = True  # if False, give_disadvantage
#    max_uses = 1
#    priority = -1
#    attack_type = Ability.DEX
#    defense_type = Ability.DEX
#    help_text = (
#        "Perform a stunt against a target. This will give you an advantage or an enemy "
#        "disadvantage on your next action."
#    )
#
#    def use(self, defender, *args, **kwargs):
#        # quality doesn't matter for stunts, they are either successful or not
#
#        attacker = self.combatant
#        advantage, disadvantage = False, False
#
#        is_success, _, txt = rules.dice.opposed_saving_throw(
#            attacker,
#            defender,
#            attack_type=self.attack_type,
#            defense_type=self.defense_type,
#            advantage=advantage,
#            disadvantage=disadvantage,
#        )
#        self.msg(f"$You() $conj(attempt) stunt on $You(defender.key). {txt}")
#        if is_success:
#            stunt_duration = self.combathandler.stunt_duration
#            if self.give_advantage:
#                self.combathandler.gain_advantage(attacker, defender)
#                self.msg(
#                    "%You() $conj(gain) advantage against $You(defender.key! "
#                    f"You must use it within {stunt_duration} turns."
#                )
#            else:
#                self.combathandler.gain_disadvantage(defender, attacker)
#                self.msg(
#                    f"$You({defender.key}) $conj(suffer) disadvantage against $You(). "
#                    "Lasts next attack, or until 3 turns passed."
#                )
#
#            # only spend a use after being successful
#            self.uses += 1
#
#
# class CombatActionUseItem(CombatAction):
#    """
#    Use an item in combat. This is meant for one-off or limited-use items, like potions, scrolls or
#    wands.  We offload the usage checks and usability to the item's own hooks. It's generated
#    dynamically from the items in the character's inventory (you could also consider using items in
#    the room this way).
#
#    Each usable item results in one possible action.
#
#    It relies on the combat_* hooks on the item:
#        combat_get_help
#        combat_can_use
#        combat_pre_use
#        combat_pre
#        combat_post_use
#
#    """
#
#    key = "Use Item"
#    desc = "[U]se item"
#    aliases = ("u", "item", "use item")
#    help_text = "Use an item from your inventory."
#    next_menu_node = "node_select_friendly_target"
#
#    def get_help(self, item, *args):
#        return item.get_help(*args)
#
#    def use(self, item, target, *args, **kwargs):
#        item.at_use(self.combatant, target, *args, **kwargs)
#
#    def post_use(self, item, *args, **kwargs):
#        item.at_post_use(self.combatant, *args, **kwargs)
#        self.msg("$You() $conj(use) an item.")
#
#
# class CombatActionSwapWieldedWeaponOrSpell(CombatAction):
#    """
#    Swap Wielded weapon or spell.
#
#    """
#
#    key = "Swap weapon/rune/shield"
#    desc = "Swap currently wielded weapon, shield or spell-rune."
#    aliases = (
#        "s",
#        "swap",
#        "draw",
#        "swap weapon",
#        "draw weapon",
#        "swap rune",
#        "draw rune",
#        "swap spell",
#        "draw spell",
#    )
#    help_text = (
#        "Draw a new weapon or spell-rune from your inventory, replacing your current loadout"
#    )
#
#    next_menu_node = "node_select_wield_from_inventory"
#
#    def use(self, _, item, *args, **kwargs):
#        # this will make use of the item
#        self.combatant.equipment.move(item)
#
#
# class CombatActionFlee(CombatAction):
#    """
#    Fleeing/disengaging from combat means doing nothing but 'running away' for two turn. Unless
#    someone attempts and succeeds in their 'block' action, you will leave combat by fleeing at the
#    end of the second turn.
#
#    """
#
#    key = "Flee/Disengage"
#    desc = "[F]lee/disengage from combat (takes two turns)"
#    aliases = ("d", "disengage", "flee")
#
#    # this only affects us
#    next_menu_node = "node_confirm_register_action"
#
#    help_text = (
#        "Disengage from combat. Use successfully two times in a row to leave combat at the "
#        "end of the second round. If someone Blocks you successfully, this counter is reset."
#    )
#    priority = -5  # checked last
#
#    def use(self, *args, **kwargs):
#        # it's safe to do this twice
#        self.msg(
#            "$You() $conj(retreat), and will leave combat next round unless someone successfully "
#            "blocks the escape."
#        )
#        self.combathandler.flee(self.combatant)
#
#
# class CombatActionBlock(CombatAction):
#
#    """
#    Blocking is, in this context, a way to counter an enemy's 'Flee/Disengage' action.
#
#    """
#
#    key = "Block"
#    desc = "[B]lock <target> from fleeing"
#    aliases = ("b", "block", "chase")
#    help_text = (
#        "Move to block a target from fleeing combat. If you succeed "
#        "in a DEX vs DEX challenge, they don't get away."
#    )
#    next_menu_node = "node_select_enemy_target"
#
#    priority = -1  # must be checked BEFORE the flee action of the target!
#
#    attack_type = Ability.DEX
#    defense_type = Ability.DEX
#
#    def use(self, fleeing_target, *args, **kwargs):
#
#        advantage = bool(
#            self.combathandler.advantage_matrix[self.combatant].pop(fleeing_target, False)
#        )
#        disadvantage = bool(
#            self.combathandler.disadvantage_matrix[self.combatant].pop(fleeing_target, False)
#        )
#
#        is_success, _, txt = rules.dice.opposed_saving_throw(
#            self.combatant,
#            fleeing_target,
#            attack_type=self.attack_type,
#            defense_type=self.defense_type,
#            advantage=advantage,
#            disadvantage=disadvantage,
#        )
#        self.msg(
#            f"$You() $conj(try) to block the retreat of $You({fleeing_target.key}). {txt}",
#        )
#
#        if is_success:
#            # managed to stop the target from fleeing/disengaging
#            self.combathandler.unflee(fleeing_target)
#            self.msg(f"$You() $conj(block) the retreat of $You({fleeing_target.key})")
#        else:
#            self.msg(f"$You({fleeing_target.key}) $conj(dodge) away from you $You()!")
#
#
# class CombatActionDoNothing(CombatAction):
#    """
#    Do nothing this turn.
#
#    """
#
#    key = "Hesitate"
#    desc = "Do [N]othing/Hesitate"
#    aliases = ("n", "hesitate", "nothing", "do nothing")
#    help_text = "Hold you position, doing nothing."
#
#    # affects noone else
#    next_menu_node = "node_confirm_register_action"
#
#    post_action_text = "{combatant} does nothing this turn."
#
#    def use(self, *args, **kwargs):
#        self.msg("$You() $conj(hesitate), accomplishing nothing.")
#
#
## -----------------------------------------------------------------------------------
##  Combat handler
## -----------------------------------------------------------------------------------
#
#
# class EvAdventureCombatHandler(DefaultScript):
#    """
#    This script is created when combat is initialized and stores a queue
#    of all active participants.
#
#    It's also possible to join (or leave) the fray later.
#
#    """
#
#    # we use the same duration for all stunts
#    stunt_duration = 3
#
#    # Default actions available to everyone
#    default_action_classes = [
#        CombatActionAttack,
#        CombatActionStunt,
#        CombatActionSwapWieldedWeaponOrSpell,
#        CombatActionUseItem,
#        CombatActionFlee,
#        CombatActionBlock,
#        CombatActionDoNothing,
#    ]
#
#    # attributes
#
#    # stores all combatants active in the combat
#    combatants = AttributeProperty(list())
#    # each combatant has its own set of actions that may or may not be available
#    # every round
#    combatant_actions = AttributeProperty(defaultdict(dict))
#
#    action_queue = AttributeProperty(dict())
#
#    turn_stats = AttributeProperty(dict())
#
#    # turn counter - abstract time
#    turn = AttributeProperty(default=0)
#    # advantages or disadvantages gained against different targets
#    advantage_matrix = AttributeProperty(defaultdict(dict))
#    disadvantage_matrix = AttributeProperty(defaultdict(dict))
#
#    fleeing_combatants = AttributeProperty(list())
#    defeated_combatants = AttributeProperty(list())
#
#    _warn_time_task = None
#
#    def at_script_creation(self):
#
#        # how often this script ticks - the max length of each turn (in seconds)
#        self.key = COMBAT_HANDLER_KEY
#        self.interval = COMBAT_HANDLER_INTERVAL
#
#    def at_repeat(self, **kwargs):
#        """
#        Called every self.interval seconds. The main tick of the script.
#
#        """
#        if self._warn_time_task:
#            self._warn_time_task.remove()
#
#        if self.turn == 0:
#            self._start_turn()
#        else:
#            self._end_turn()
#            self._start_turn()
#
#    def _init_menu(self, combatant, session=None):
#        """
#        Make sure combatant is in the menu. This is safe to call on a combatant already in a menu.
#
#        """
#        if not combatant.ndb._evmenu:
#            # re-joining the menu is useful during testing
#            evmenu.EvMenu(
#                combatant,
#                {
#                    "node_wait_start": node_wait_start,
#                    "node_select_enemy_target": node_select_enemy_target,
#                    "node_select_friendly_target": node_select_friendly_target,
#                    "node_select_action": node_select_action,
#                    "node_select_wield_from_inventory": node_select_wield_from_inventory,
#                    "node_wait_turn": node_wait_turn,
#                },
#                startnode="node_wait_turn",
#                auto_quit=True,
#                persistent=True,
#                cmdset_mergetype="Union",
#                session=session,
#                combathandler=self,  # makes this available as combatant.ndb._evmenu.combathandler
#            )
#
#    def _warn_time(self, time_remaining):
#        """
#        Send a warning message when time is about to run out.
#
#        """
#        self.msg(f"{time_remaining} seconds left in round!")
#
#    def _start_turn(self):
#        """
#        New turn events
#
#        """
#        self.turn += 1
#        self.action_queue = {}
#        self.turn_stats = defaultdict(list)
#
#        # start a timer to echo a warning to everyone 15 seconds before end of round
#        if self.interval >= 0:
#            # set -1 for unit tests
#            warning_time = 10
#            self._warn_time_task = delay(
#                self.interval - warning_time, self._warn_time, warning_time
#            )
#
#        self.msg(f"|y_______________________ start turn {self.turn} ___________________________|n")
#
#        for combatant in self.combatants:
#            if hasattr(combatant, "ai_combat_next_action"):
#                # NPC needs to get a decision from the AI
#                next_action_key, args, kwargs = combatant.ai_combat_next_action(self)
#                self.register_action(combatant, next_action_key, *args, **kwargs)
#            else:
#                # cycle combat menu for PC
#                self._init_menu(combatant)
#                combatant.ndb._evmenu.goto("node_select_action", "")
#
#    def _end_turn(self):
#        """
#        End of turn operations.
#
#        1. Do all regular actions
#        2. Check if fleeing combatants got away - remove them from combat
#        3. Check if anyone has hp <= - defeated
#        4. Check if any one side is alone on the battlefield - they loot the defeated
#        5. If combat is still on, update stunt timers
#
#        """
#        self.msg(
#            f"|y__________________ turn resolution (turn {self.turn}) ____________________|n\n"
#        )
#
#        # store those in the process of fleeing
#        already_fleeing = self.fleeing_combatants[:]
#
#        # do all actions
#        for combatant in self.combatants:
#            # read the current action type selected by the player
#            action, args, kwargs = self.action_queue.get(
#                combatant, (CombatActionDoNothing(self, combatant), (), {})
#            )
#            # perform the action on the CombatAction instance
#            try:
#                action.pre_use(*args, **kwargs)
#                action.use(*args, **kwargs)
#                action.post_use(*args, **kwargs)
#            except Exception as err:
#                combatant.msg(
#                    f"An error ({err}) occurred when performing this action.\n"
#                    "Please report the problem to an admin."
#                )
#                logger.log_trace()
#                raise
#
#        # handle disengaging combatants
#
#        to_flee = []
#        to_defeat = []
#
#        for combatant in self.combatants:
#            # see if fleeing characters managed to do two flee actions in a row.
#            if (combatant in self.fleeing_combatants) and (combatant in already_fleeing):
#                self.fleeing_combatants.remove(combatant)
#                to_flee.append(combatant)
#
#            if combatant.hp <= 0:
#                # check characters that are beaten down.
#                # characters roll on the death table here; but even if they survive, they
#                # count as defeated (unconcious) for this combat.
#                combatant.at_defeat()
#                to_defeat.append(combatant)
#
#        for combatant in to_flee:
#            # combatant leaving combat by fleeing
#            self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
#            self.remove_combatant(combatant)
#
#        for combatant in to_defeat:
#            # combatants leaving combat by being defeated
#            self.msg("|r$You() $conj(fall) to the ground, defeated.|n", combatant=combatant)
#            self.combatants.remove(combatant)
#            self.defeated_combatants.append(combatant)
#
#        # check if only one side remains, divide into allies and enemies based on the first
#        # combatant,then check if either team is empty.
#        if not self.combatants:
#            # everyone's defeated at the same time. This is a tie where everyone loses and
#            # no looting happens.
#            self.msg("|yEveryone takes everyone else out. Today, noone wins.|n")
#            self.stop_combat()
#            return
#        else:
#            combatant = self.combatants[0]
#            allies = self.get_friendly_targets(combatant)  # will always contain at least combatant
#            enemies = self.get_enemy_targets(combatant)
#
#            if not enemies:
#                # no enemies left - allies to combatant won!
#                defeated_enemies = self.get_enemy_targets(
#                    combatant, all_combatants=self.defeated_combatants
#                )
#
#                # all surviving allies loot the fallen enemies
#                for ally in allies:
#                    for enemy in defeated_enemies:
#                        try:
#                            if ally.pre_loot(enemy):
#                                enemy.at_looted(ally)
#                                ally.post_loot(enemy)
#                        except Exception:
#                            logger.log_trace()
#                self.stop_combat()
#                return
#
#        # if we get here, combat is still on
#
#        # refresh stunt timeouts (note - self.stunt_duration is the same for
#        # all stunts; # for more complex use we could store the action and let action have a
#        # 'duration' property to use instead.
#        oldest_stunt_age = self.turn - self.stunt_duration
#
#        advantage_matrix = self.advantage_matrix
#        disadvantage_matrix = self.disadvantage_matrix
#        # rebuild advantages with the (possibly cropped) list of combatants
#        # we make new matrices in order to make sure disengaged combatants are
#        # not included.
#        new_advantage_matrix = {}
#        new_disadvantage_matrix = {}
#
#        for combatant in self.combatants:
#            new_advantage_matrix[combatant] = {
#                target: set_at_turn
#                for target, set_at_turn in advantage_matrix[combatant].items()
#                if set_at_turn > oldest_stunt_age
#            }
#            new_disadvantage_matrix[combatant] = {
#                target: set_at_turn
#                for target, set_at_turn in disadvantage_matrix[combatant].items()
#                if set_at_turn > oldest_stunt_age
#            }
#
#        self.advantage_matrix = new_advantage_matrix
#        self.disadvantage_matrix = new_disadvantage_matrix
#
#    def add_combatant(self, combatant, session=None):
#        """
#        Add combatant to battle.
#
#        Args:
#            combatant (Object): The combatant to add.
#            session (Session, optional): Session to use.
#
#        Notes:
#            This adds them to the internal list and initiates
#            all possible actions. If the combatant as an Attribute list
#            `custom_combat_actions` containing `CombatAction` items, this
#            will injected and if the `.key` matches, will replace the
#            default action classes.
#
#        """
#        if combatant not in self.combatants:
#            self.combatants.append(combatant)
#            combatant.db.combathandler = self
#
#            # allow custom character actions (not used by default)
#            custom_action_classes = combatant.db.custom_combat_actions or []
#
#            self.combatant_actions[combatant] = {
#                action_class.key: action_class(self, combatant)
#                for action_class in self.default_action_classes + custom_action_classes
#            }
#            self._init_menu(combatant, session=session)
#
#    def remove_combatant(self, combatant):
#        """
#        Remove combatant from battle.
#
#        Args:
#            combatant (Object): The combatant to remove.
#
#        """
#        if combatant in self.combatants:
#            self.combatants.remove(combatant)
#            self.combatant_actions.pop(combatant, None)
#            if combatant.ndb._evmenu:
#                combatant.ndb._evmenu.close_menu()
#            del combatant.db.combathandler
#
#    def start_combat(self):
#        """
#        Start the combat timer and get everyone going.
#
#        """
#        for combatant in self.combatants:
#            combatant.ndb._evmenu.goto("node_select_action", "")
#        self.start()  # starts the script timer
#        self._start_turn()
#
#    def stop_combat(self):
#        """
#        This is used to stop the combat immediately.
#
#        It can also be called from external systems, for example by
#        monster AI can do this when only allied players remain.
#
#        """
#        for combatant in self.combatants:
#            self.remove_combatant(combatant)
#        self.delete()
#
#    def get_enemy_targets(self, combatant, excluded=None, all_combatants=None):
#        """
#        Get all valid targets the given combatant can target for an attack. This does not apply for
#        'friendly' targeting (like wanting to cast a heal on someone). We assume there are two types
#        of combatants - PCs (player-controlled characters and NPCs (AI-controlled). Here, we assume
#        npcs can never attack one another (or themselves)
#
#        For PCs to be able to target each other, the `allow_pvp`
#        Attribute flag must be set on the current `Room`.
#
#        Args:
#            combatant (Object): The combatant looking for targets.
#            excluded (list, optional): If given, these are not valid targets - this can be used to
#                avoid friendly NPCs.
#            all_combatants (list, optional): If given, use this list to get all combatants, instead
#                of using `self.combatants`.
#
#        """
#        is_pc = not inherits_from(combatant, EvAdventureNPC)
#        allow_pvp = self.obj.allow_pvp
#        targets = []
#        combatants = all_combatants or self.combatants
#
#        if is_pc:
#            if allow_pvp:
#                # PCs may target everyone, including other PCs
#                targets = combatants
#            else:
#                # PCs may only attack NPCs
#                targets = [target for target in combatants if inherits_from(target, EvAdventureNPC)]
#
#        else:
#            # NPCs may only attack PCs, not each other
#            targets = [target for target in combatants if not inherits_from(target, EvAdventureNPC)]
#
#        if excluded:
#            targets = [target for target in targets if target not in excluded]
#
#        return targets
#
#    def get_friendly_targets(self, combatant, extra=None, all_combatants=None):
#        """
#        Get a list of all 'friendly' or neutral targets a combatant may target, including
#        themselves.
#
#        Args:
#            combatant (Object): The combatant looking for targets.
#            extra (list, optional): If given, these are additional targets that can be
#                considered target for allied effects (could be used for a friendly NPC).
#            all_combatants (list, optional): If given, use this list to get all combatants, instead
#                of using `self.combatants`.
#
#        """
#        is_pc = not inherits_from(combatant, EvAdventureNPC)
#        combatants = all_combatants or self.combatants
#        if is_pc:
#            # can target other PCs
#            targets = [target for target in combatants if not inherits_from(target, EvAdventureNPC)]
#        else:
#            # can target other NPCs
#            targets = [target for target in combatants if inherits_from(target, EvAdventureNPC)]
#
#        if extra:
#            targets = list(set(targets + extra))
#
#        return targets
#
#    def get_combat_summary(self, combatant):
#        """
#        Get a summary of the current combat state from the perspective of a
#        given combatant.
#
#        Args:
#            combatant (Object): The combatant to get the summary for
#
#        Returns:
#            str: The summary.
#
#        Example:
#
#            ```
#            You (5/10 health)
#            Foo (Hurt) [Running away - use 'block' to stop them!]
#            Bar (Perfect health)
#
#            ```
#
#        """
#        table = evtable.EvTable(border_width=0)
#
#        # 'You' display
#        fleeing = ""
#        if combatant in self.fleeing_combatants:
#            fleeing = " You are running away! Use 'flee' again next turn."
#
#        table.add_row(f"You ({combatant.hp} / {combatant.hp_max} health){fleeing}")
#
#        for comb in self.combatants:
#
#            if comb is combatant:
#                continue
#
#            name = comb.key
#            health = f"{comb.hurt_level}"
#            fleeing = ""
#            if comb in self.fleeing_combatants:
#                fleeing = " [Running away! Use 'block' to stop them!"
#
#            table.add_row(f"{name} ({health}){fleeing}")
#
#        return str(table)
#
#    def msg(self, message, combatant=None, broadcast=True):
#        """
#        Central place for sending messages to combatants. This allows
#        for adding any combat-specific text-decoration in one place.
#
#        Args:
#            message (str): The message to send.
#            combatant (Object): The 'You' in the message, if any.
#            broadcast (bool): If `False`, `combatant` must be included and
#                will be the only one to see the message. If `True`, send to
#                everyone in the location.
#
#        Notes:
#            If `combatant` is given, use `$You/you()` markup to create
#            a message that looks different depending on who sees it. Use
#            `$You(combatant_key)` to refer to other combatants.
#
#        """
#        location = self.obj
#        location_objs = location.contents
#
#        exclude = []
#        if not broadcast and combatant:
#            exclude = [obj for obj in location_objs if obj is not combatant]
#
#        location.msg_contents(
#            message,
#            exclude=exclude,
#            from_obj=combatant,
#            mapping={locobj.key: locobj for locobj in location_objs},
#        )
#
#    def gain_advantage(self, combatant, target):
#        """
#        Gain advantage against target. Spent by actions.
#
#        """
#        self.advantage_matrix[combatant][target] = self.turn
#
#    def gain_disadvantage(self, combatant, target):
#        """
#        Gain disadvantage against target. Spent by actions.
#
#        """
#        self.disadvantage_matrix[combatant][target] = self.turn
#
#    def flee(self, combatant):
#        if combatant not in self.fleeing_combatants:
#            self.fleeing_combatants.append(combatant)
#
#    def unflee(self, combatant):
#        if combatant in self.fleeing_combatants:
#            self.fleeing_combatants.remove(combatant)
#
#    def register_action(self, combatant, action_key, *args, **kwargs):
#        """
#        Register an action based on its `.key`.
#
#        Args:
#            combatant (Object): The one performing the action.
#            action_key (str): The action to perform, by its `.key`.
#            *args: Arguments to pass to `action.use`.
#            **kwargs: Kwargs to pass to `action.use`.
#
#        """
#        # get the instantiated action for this combatant
#        action = self.combatant_actions[combatant].get(
#            action_key, CombatActionDoNothing(self, combatant)
#        )
#
#        # store the action in the queue
#        self.action_queue[combatant] = (action, args, kwargs)
#
#        if len(self.action_queue) >= len(self.combatants):
#            # all combatants registered actions - force the script
#            # to cycle (will fire at_repeat)
#            self.force_repeat()
#
#    def get_available_actions(self, combatant, *args, **kwargs):
#        """
#        Get only the actions available to a combatant.
#
#        Args:
#            combatant (Object): The combatant to get actions for.
#            *args: Passed to `action.can_use()`
#            **kwargs: Passed to `action.can_use()`
#
#        Returns:
#            list: The initiated CombatAction instances available to the
#                combatant right now.
#
#        Note:
#            We could filter this by `.can_use` return already here, but then it would just
#            be removed from the menu. Instead we return all and use `.can_use` in the menu
#            so we can include the option but gray it out.
#
#        """
#        return list(self.combatant_actions[combatant].values())
#
#
## -----------------------------------------------------------------------------------
##  Combat Menu definitions
## -----------------------------------------------------------------------------------
#
#
# def _register_action(caller, raw_string, **kwargs):
#    """
#    Actually register action with handler.
#
#    """
#    action_key = kwargs.pop("action_key")
#    action_args = kwargs["action_args"]
#    action_kwargs = kwargs["action_kwargs"]
#    action_target = kwargs.pop("action_target", None)
#    combat_handler = caller.ndb._evmenu.combathandler
#    combat_handler.register_action(caller, action_key, action_target, *action_args, **action_kwargs)
#
#    # move into waiting
#    return "node_wait_turn"
#
#
# def node_confirm_register_action(caller, raw_string, **kwargs):
#    """
#    Node where one can confirm registering the action or change one's mind.
#
#    """
#    action_key = kwargs["action_key"]
#    action_target = kwargs.get("action_target", None) or ""
#    if action_target:
#        action_target = f", targeting {action_target.key}"
#
#    text = f"You will {action_key}{action_target}. Confirm? [Y]/n"
#    options = (
#        {
#            "key": "_default",
#            "goto": (_register_action, kwargs),
#        },
#        {"key": ("Abort/Cancel", "abort", "cancel", "a", "no", "n"), "goto": "node_select_action"},
#    )
#    return text, options
#
#
# def _select_target_helper(caller, raw_string, targets, **kwargs):
#    """
#    Helper to select among only friendly or enemy targets (given by the calling node).
#
#    """
#    action_key = kwargs["action_key"]
#    text = f"Select target for |w{action_key}|n."
#
#    # make the apply-self option always the first one, give it key 0
#    if caller in targets:
#        targets.remove(caller)
#        kwargs["action_target"] = caller
#        options = [{"key": "0", "desc": "(yourself)", "goto": (_register_action, kwargs)}]
#    # filter out ourselves and then make options for everyone else
#    for inum, combatant in enumerate(targets):
#        kwargs["action_target"] = combatant
#        options.append(
#            {"key": str(inum + 1), "desc": combatant.key, "goto": (_register_action, kwargs)}
#        )
#
#    # add ability to cancel
#    options.append({"key": "_default", "goto": "node_select_action"})
#
#    return text, options
#
#
# def node_select_enemy_target(caller, raw_string, **kwargs):
#    """
#    Menu node allowing for selecting an enemy target among all combatants. This combines
#    with all other actions.
#
#    """
#    combat = caller.ndb._evmenu.combathandler
#    targets = combat.get_enemy_targets(caller)
#    return _select_target_helper(caller, raw_string, targets, **kwargs)
#
#
# def node_select_friendly_target(caller, raw_string, **kwargs):
#    """
#    Menu node for selecting a friendly target among combatants (including oneself).
#
#    """
#    combat = caller.ndb._evmenu.combathandler
#    targets = combat.get_friendly_targets(caller)
#    return _select_target_helper(caller, raw_string, targets, **kwargs)
#
#
# def _item_broken(caller, raw_string, **kwargs):
#    caller.msg("|rThis item is broken and unusable!|n")
#    return None  # back to previous node
#
#
# def node_select_wield_from_inventory(caller, raw_string, **kwargs):
#    """
#    Menu node allowing for wielding item(s) from inventory.
#
#    """
#    loadout = caller.equipment.display_loadout()
#    text = (
#        f"{loadout}\nSelect weapon, spell or shield to draw. It will swap out "
#        "anything already in the same hand (you can't change armor or helmet in combat)."
#    )
#
#    # get a list of all suitable weapons/spells/shields
#    options = []
#    for obj in caller.equipment.get_wieldable_objects_from_backpack():
#        if obj.quality <= 0:
#            # object is broken
#            options.append(
#                {
#                    "desc": "|Rstr(obj)|n",
#                    "goto": _item_broken,
#                }
#            )
#        else:
#            # normally working item
#            kwargs["action_args"] = (obj,)
#            options.append({"desc": str(obj), "goto": (_register_action, kwargs)})
#
#    # add ability to cancel
#    options.append(
#        {"key": "_default", "desc": "(No input to Abort and go back)", "goto": "node_select_action"}
#    )
#
#    return text, options
#
#
# def node_select_use_item_from_inventory(caller, raw_string, **kwargs):
#    """
#    Menu item allowing for using usable items (like potions) from inventory.
#
#    """
#    text = "Select an item to use."
#
#    # get a list of all suitable weapons/spells/shields
#    options = []
#    for obj in caller.inventory.get_usable_objects_from_backpack():
#        if obj.quality <= 0:
#            # object is broken
#            options.append(
#                {
#                    "desc": "|Rstr(obj)|n",
#                    "goto": _item_broken,
#                }
#            )
#        else:
#            # normally working item
#            kwargs["action_args"] = (obj,)
#            options.append({"desc": str(obj), "goto": (_register_action, kwargs)})
#
#    # add ability to cancel
#    options.append({"key": "_default", "goto": "node_select_action"})
#
#    return text, options
#
#
# def _action_unavailable(caller, raw_string, **kwargs):
#    """
#    Selecting an unavailable action.
#
#    """
#    action_key = kwargs["action_key"]
#    caller.msg(f"|rAction |w{action_key}|r is currently not available.|n")
#    # go back to previous node
#    return
#
#
# def node_select_action(caller, raw_string, **kwargs):
#    """
#    Menu node for selecting a combat action.
#
#    """
#    combat = caller.ndb._evmenu.combathandler
#    text = combat.get_combat_summary(caller)
#
#    options = []
#    for icount, action in enumerate(combat.get_available_actions(caller)):
#        # we handle counts manually so we can grey the entire line if action is unavailable.
#        key = str(icount + 1)
#        desc = action.desc
#
#        if not action.can_use():
#            # action is unavailable. Greyscale the option if not available and route to the
#            # _action_unavailable helper
#            key = f"|x{key}|n"
#            desc = f"|x{desc}|n"
#
#            options.append(
#                {
#                    "key": (key,) + tuple(action.aliases),
#                    "desc": desc,
#                    "goto": (_action_unavailable, {"action_key": action.key}),
#                }
#            )
#        elif action.next_menu_node is None:
#            # action is available, but needs no intermediary step. Redirect to register
#            # the action immediately
#            options.append(
#                {
#                    "key": (key,) + tuple(action.aliases),
#                    "desc": desc,
#                    "goto": (
#                        _register_action,
#                        {
#                            "action_key": action.key,
#                            "action_args": (),
#                            "action_kwargs": {},
#                            "action_target": None,
#                        },
#                    ),
#                }
#            )
#        else:
#            # action is available and next_menu_node is set to point to the next node we want
#            options.append(
#                {
#                    "key": (key,) + tuple(action.aliases),
#                    "desc": desc,
#                    "goto": (
#                        action.next_menu_node,
#                        {
#                            "action_key": action.key,
#                            "action_args": (),
#                            "action_kwargs": {},
#                            "action_target": None,
#                        },
#                    ),
#                }
#            )
#        # add ability to cancel
#        options.append(
#            {
#                "key": "_default",
#                "goto": "node_select_action",
#            }
#        )
#
#    return text, options
#
#
# def node_wait_turn(caller, raw_string, **kwargs):
#    """
#    Menu node routed to waiting for the round to end (for everyone to choose their actions).
#
#    All menu actions route back to the same node. The CombatHandler will handle moving everyone back
#    to the `node_select_action` node when the next round starts.
#
#    """
#    text = "Waiting for other combatants ..."
#
#    options = {
#        "key": "_default",
#        "desc": "(next round will start automatically)",
#        "goto": "node_wait_turn",
#    }
#    return text, options
#
#
# def node_wait_start(caller, raw_string, **kwargs):
#    """
#    Menu node entered when waiting for the combat to start. New players joining an existing
#    combat will end up here until the previous round is over, at which point the combat handler
#    will goto everyone to `node_select_action`.
#
#    """
#    text = "Waiting for combat round to start ..."
#
#    options = {
#        "key": "_default",
#        "desc": "(combat will start automatically)",
#        "goto": "node_wait_start",
#    }
#    return text, options


# -----------------------------------------------------------------------------------
#  Access function
# -----------------------------------------------------------------------------------


# def join_combat(caller, *targets, session=None):
#    """
#    Join or create a new combat involving caller and at least one target. The combat
#    is started on the current room location - this means there can only be one combat
#    in each room (this is not hardcoded in the combat per-se, but it makes sense for
#    this implementation).
#
#    Args:
#        caller (Object): The one starting the combat.
#        *targets (Objects): Any other targets to pull into combat. At least one target
#            is required if `combathandler` is not given (a new combat must have at least
#            one opponent!).
#
#    Keyword Args:
#        session (Session, optional): A player session to use. This is useful for multisession modes.
#
#    Returns:
#        EvAdventureCombatHandler: A created or existing combat handler.
#
#    """
#    created = False
#    location = caller.location
#    if not location:
#        raise CombatFailure("Must have a location to start combat.")
#
#    if caller.hp <= 0:
#        raise CombatFailure("You can't start a fight in your current condition!")
#
#    if not getattr(location, "allow_combat", False):
#        raise CombatFailure("This is not the time and place for picking a fight.")
#
#    if not targets:
#        raise CombatFailure("Must have an opponent to start combat.")
#
#    combathandler = location.scripts.get(COMBAT_HANDLER_KEY).first()
#    if not combathandler:
#        combathandler = location.scripts.add(EvAdventureCombatHandler, autostart=False)
#        created = True
#
#    if not hasattr(caller, "hp"):
#        raise CombatFailure("You have no hp and so can't attack anyone.")
#
#    # it's safe to add a combatant to the same combat more than once
#    combathandler.add_combatant(caller, session=session)
#    for target in targets:
#        if target.hp <= 0:
#            caller.msg(f"{target.get_display_name(caller)} is already out of it.")
#            continue
#        combathandler.add_combatant(target)
#
#    if created:
#        combathandler.start_combat()
#
#    return combathandler

# -----------------------------------------------------------------------------------
#  Access function
# -----------------------------------------------------------------------------------
#
#
# def join_combat(caller, *targets, session=None):
#     """
#     Join or create a new combat involving caller and at least one target. The combat
#     is started on the current room location - this means there can only be one combat
#     in each room (this is not hardcoded in the combat per-se, but it makes sense for
#     this implementation).
#
#     Args:
#         caller (Object): The one starting the combat.
#         *targets (Objects): Any other targets to pull into combat. At least one target
#             is required if `combathandler` is not given (a new combat must have at least
#             one opponent!).
#
#     Keyword Args:
#         session (Session, optional): A player session to use. This is useful for multisession modes.
#
#     Returns:
#         EvAdventureCombatHandler: A created or existing combat handler.
#
#     """
#     created = False
#     location = caller.location
#     if not location:
#         raise CombatFailure("Must have a location to start combat.")
#
#     if caller.hp <= 0:
#         raise CombatFailure("You can't start a fight in your current condition!")
#
#     if not getattr(location, "allow_combat", False):
#         raise CombatFailure("This is not the time and place for picking a fight.")
#
#     if not targets:
#         raise CombatFailure("Must have an opponent to start combat.")
#
#     combathandler = location.scripts.get(COMBAT_HANDLER_KEY).first()
#     if not combathandler:
#         combathandler = location.scripts.add(EvAdventureCombatHandler, autostart=False)
#         created = True
#
#     if not hasattr(caller, "hp"):
#         raise CombatFailure("You have no hp and so can't attack anyone.")
#
#     # it's safe to add a combatant to the same combat more than once
#     combathandler.add_combatant(caller, session=session)
#     for target in targets:
#         if target.hp <= 0:
#             caller.msg(f"{target.get_display_name(caller)} is already out of it.")
#             continue
#         combathandler.add_combatant(target)
#
#     if created:
#         combathandler.start_combat()
#
#     return combathandler
