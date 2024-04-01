"""
EvAdventure Turn-based combat

This implements a turn-based (Final Fantasy, etc) style of MUD combat.

In this variation, all combatants are sharing the same combat handler, sitting on the current room.
The user will receive a menu of combat options and each combatat has a certain time time (e.g. 30s)
to select their next action or do nothing. To speed up play, as soon as everyone in combat selected
their next action, the next turn runs immediately, regardless of the timeout.

With this example, all chosen combat actions are considered to happen at the same time (so you are
able to kill and be killed in the same turn).

Unlike in twitch-like combat, there is no movement while in turn-based combat. Fleeing is a select
action that takes several vulnerable turns to complete.

----

"""

import random
from collections import defaultdict

from evennia import AttributeProperty, CmdSet, Command, EvMenu
from evennia.utils import inherits_from, list_to_string

from .characters import EvAdventureCharacter
from .combat_base import (
    CombatAction,
    CombatActionAttack,
    CombatActionHold,
    CombatActionStunt,
    CombatActionUseItem,
    CombatActionWield,
    EvAdventureCombatBaseHandler,
)
from .enums import Ability


# turnbased-combat needs the flee action too
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
        combathandler = self.combathandler

        if self.combatant not in combathandler.fleeing_combatants:
            # we record the turn on which we started fleeing
            combathandler.fleeing_combatants[self.combatant] = self.combathandler.turn

        # show how many turns until successful flight
        current_turn = combathandler.turn
        started_fleeing = combathandler.fleeing_combatants[self.combatant]
        flee_timeout = combathandler.flee_timeout
        time_left = flee_timeout - (current_turn - started_fleeing) - 1

        if time_left > 0:
            self.msg(
                "$You() $conj(retreat), being exposed to attack while doing so (will escape in "
                f"{time_left} $pluralize(turn, {time_left}))."
            )


class EvAdventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):
    """
    A version of the combathandler, handling turn-based combat.

    """

    # available actions in combat
    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": CombatActionFlee,
    }

    # how many turns you must be fleeing before escaping
    flee_timeout = AttributeProperty(1, autocreate=False)

    # fallback action if not selecting anything
    fallback_action_dict = AttributeProperty({"key": "hold"}, autocreate=False)

    # persistent storage

    turn = AttributeProperty(0)
    # who is involved in combat, and their queued action
    # as {combatant: actiondict, ...}
    combatants = AttributeProperty(dict)

    # who has advantage against whom
    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    fleeing_combatants = AttributeProperty(dict)
    defeated_combatants = AttributeProperty(list)

    # usable script properties
    # .is_active - show if timer is running

    def give_advantage(self, combatant, target):
        """
        Let a benefiter gain advantage against the target.

        Args:
            combatant (Character or NPC): The one to gain the advantage. This may or may not
                be the same entity that creates the advantage in the first place.
            target (Character or NPC): The one against which the target gains advantage. This
                could (in principle) be the same as the benefiter (e.g. gaining advantage on
                some future boost)

        """
        self.advantage_matrix[combatant][target] = True

    def give_disadvantage(self, combatant, target, **kwargs):
        """
        Let an affected party gain disadvantage against a target.

        Args:
            recipient (Character or NPC): The one to get the disadvantage.
            target (Character or NPC): The one against which the target gains disadvantage, usually
                an enemy.

        """
        self.disadvantage_matrix[combatant][target] = True

    def has_advantage(self, combatant, target, **kwargs):
        """
        Check if a given combatant has advantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have advantage
            target (Character or NPC): The target to check advantage against.

        """
        return target in self.fleeing_combatants or bool(
            self.advantage_matrix[combatant].pop(target, False)
        )

    def has_disadvantage(self, combatant, target):
        """
        Check if a given combatant has disadvantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have disadvantage
            target (Character or NPC): The target to check disadvantage against.

        """
        return bool(self.disadvantage_matrix[combatant].pop(target, False))

    def add_combatant(self, combatant):
        """
        Add a new combatant to the battle. Can be called multiple times safely.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): Any number of combatants to add to
                the combat.
        Returns:
            bool: If this combatant was newly added or not (it was already in combat).

        """
        if combatant not in self.combatants:
            self.combatants[combatant] = self.fallback_action_dict
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
        # clean up menu if it exists
        if combatant.ndb._evmenu:
            combatant.ndb._evmenu.close_menu()

    def start_combat(self, **kwargs):
        """
        This actually starts the combat. It's safe to run this multiple times
        since it will only start combat if it isn't already running.

        """
        if not self.is_active:
            self.start(**kwargs)

    def stop_combat(self):
        """
        Stop the combat immediately.

        """
        for combatant in self.combatants:
            self.remove_combatant(combatant)
        self.stop()
        self.delete()

    def get_combat_summary(self, combatant):
        """Add your next queued action to summary"""
        summary = super().get_combat_summary(combatant)
        next_action = self.get_next_action_dict(combatant) or {"key": "hold"}
        next_repeat = self.time_until_next_repeat()

        summary = (
            f"{summary}\n Your queued action: [|b{next_action['key']}|n] (|b{next_repeat}s|n until"
            " next round,\n or until all combatants have chosen their next action)."
        )
        return summary

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
                allies = pcs
                enemies = npcs
            else:
                # combatant is an NPC, so PCs are all enemies
                allies = npcs
                enemies = pcs
        return allies, enemies

    def queue_action(self, combatant, action_dict):
        """
        Queue an action by adding the new actiondict.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): A combatant queueing the action.
            action_dict (dict): A dict describing the action class by name along with properties.

        """
        self.combatants[combatant] = action_dict

        # track who inserted actions this turn (non-persistent)
        did_action = set(self.ndb.did_action or set())
        did_action.add(combatant)
        if len(did_action) >= len(self.combatants):
            # everyone has inserted an action. Start next turn without waiting!
            self.force_repeat()

    def get_next_action_dict(self, combatant):
        """
        Give the action_dict for the next action that will be executed.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant to get the action for.

        Returns:
            dict: The next action-dict in the queue.

        """
        return self.combatants.get(combatant, self.fallback_action_dict)

    def execute_next_action(self, combatant):
        """
        Perform a combatant's next queued action. Note that there is _always_ an action queued,
        even if this action is 'hold', which means the combatant will do nothing.

        Args:
            combatant (EvAdventureCharacter, EvAdventureNPC): The combatant performing and action.


        """
        # this gets the next dict and rotates the queue
        action_dict = self.combatants.get(combatant, self.fallback_action_dict)

        # use the action-dict to select and create an action from an action class
        action_class = self.action_classes[action_dict["key"]]
        action = action_class(self, combatant, action_dict)

        action.execute()
        action.post_execute()

        if action_dict.get("repeat", False):
            # queue the action again *without updating the *.ndb.did_action list* (otherwise
            # we'd always auto-end the turn if everyone used repeating actions and there'd be
            # no time to change it before the next round)
            self.combatants[combatant] = action_dict
        else:
            # if not a repeat, set the fallback action
            self.combatants[combatant] = self.fallback_action_dict

    def check_stop_combat(self):
        """Check if it's time to stop combat"""

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
            if self.turn - started_fleeing >= flee_timeout - 1:
                # if they are still alive/fleeing and have been fleeing long enough, escape
                self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
                self.remove_combatant(combatant)

        # check if one side won the battle
        if not self.combatants:
            # noone left in combat - maybe they killed each other or all fled
            surviving_combatant = None
            allies, enemies = (), ()
        else:
            # grab a random survivor and check if they have any living enemies.
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

    def at_repeat(self):
        """
        This method is called every time Script repeats (every `interval` seconds). Performs a full
        turn of combat, performing everyone's actions in random order.

        """
        self.turn += 1
        # random turn order
        combatants = list(self.combatants.keys())
        random.shuffle(combatants)  # shuffles in place

        # do everyone's next queued combat action
        for combatant in combatants:
            self.execute_next_action(combatant)

        self.ndb.did_action = set()

        # check if one side won the battle
        self.check_stop_combat()


# -----------------------------------------------------------------------------------
#
# Turn-based combat (Final Fantasy style), using a menu
#
# Activate by adding the CmdTurnCombat command to Character cmdset, then
# use it to attack a target.
#
# -----------------------------------------------------------------------------------


def _get_combathandler(caller, turn_timeout=30, flee_time=3, combathandler_key="combathandler"):
    """
    Get the combat handler for the caller's location. If it doesn't exist, create it.

    Args:
        caller (EvAdventureCharacter or EvAdventureNPC): The character/NPC to get the
            combat handler for.
        turn_timeout (int): After this time, the turn will roll around.
        flee_time (int): How many turns it takes to flee.

    """
    return EvAdventureTurnbasedCombatHandler.get_or_create_combathandler(
        caller.location,
        interval=turn_timeout,
        attributes=[("flee_time", flee_time)],
        key=combathandler_key,
    )


def _queue_action(caller, raw_string, **kwargs):
    """
    Goto-function that queue the action with the CombatHandler. This always returns
    to the top-level combat menu "node_combat"
    """
    action_dict = kwargs["action_dict"]
    _get_combathandler(caller).queue_action(caller, action_dict)
    return "node_combat"


def _rerun_current_node(caller, raw_string, **kwargs):
    return None, kwargs


def _get_default_wizard_options(caller, **kwargs):
    """
    Get the standard wizard options for moving back/forward/abort. This can be appended to
    the end of other options.

    """

    return [
        {"key": ("back", "b"), "goto": (_step_wizard, {**kwargs, **{"step": "back"}})},
        {"key": ("abort", "a"), "goto": "node_combat"},
        {
            "key": "_default",
            "goto": (_rerun_current_node, kwargs),
        },
    ]


def _step_wizard(caller, raw_string, **kwargs):
    """
    Many options requires stepping through several steps, wizard style. This
    will redirect back/forth in the sequence.

    E.g. Stunt boost -> Choose ability to boost -> Choose recipient -> Choose target -> queue

    """
    steps = kwargs.get("steps", [])
    nsteps = len(steps)
    istep = kwargs.get("istep", -1)
    # one of abort, back, forward
    step_direction = kwargs.get("step", "forward")

    if step_direction == "back":
        # step back in wizard
        if istep <= 0:
            return "node_combat"
        istep = kwargs["istep"] = istep - 1
        return steps[istep], kwargs
    else:
        # step to the next step in wizard
        if istep >= nsteps - 1:
            # we are already at end of wizard - queue action!
            return _queue_action(caller, raw_string, **kwargs)
        else:
            # step forward
            istep = kwargs["istep"] = istep + 1
            return steps[istep], kwargs


def node_choose_enemy_target(caller, raw_string, **kwargs):
    """
    Choose an enemy as a target for an action
    """
    text = "Choose an enemy to target."
    action_dict = kwargs["action_dict"]

    combathandler = _get_combathandler(caller)

    _, enemies = combathandler.get_sides(caller)

    options = [
        {
            "desc": target.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"target": target}}}},
            ),
        }
        for target in enemies
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_enemy_recipient(caller, raw_string, **kwargs):
    """
    Choose an enemy as a 'recipient' for an action.
    """
    text = "Choose an enemy as a recipient."
    action_dict = kwargs["action_dict"]

    combathandler = _get_combathandler(caller)
    _, enemies = combathandler.get_sides(caller)

    options = [
        {
            "desc": target.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"recipient": target}}}},
            ),
        }
        for target in enemies
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_allied_target(caller, raw_string, **kwargs):
    """
    Choose an enemy as a target for an action
    """
    text = "Choose an ally to target."
    action_dict = kwargs["action_dict"]

    combathandler = _get_combathandler(caller)
    allies, _ = combathandler.get_sides(caller)

    options.extend(
        [
            {
                "desc": target.get_display_name(caller),
                "goto": (
                    _step_wizard,
                    {
                        **kwargs,
                        **{"action_dict": {**action_dict, **{"target": target}}},
                    },
                ),
            }
            for target in allies
        ]
    )
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_allied_recipient(caller, raw_string, **kwargs):
    """
    Choose an allied recipient for an action
    """
    text = "Choose an ally as a recipient."
    action_dict = kwargs["action_dict"]

    combathandler = _get_combathandler(caller)
    allies, _ = combathandler.get_sides(caller)

    options.extend(
        [
            {
                "desc": target.get_display_name(caller),
                "goto": (
                    _step_wizard,
                    {
                        **kwargs,
                        **{
                            "action_dict": {
                                **action_dict,
                                **{"recipient": target},
                            }
                        },
                    },
                ),
            }
            for target in allies
        ]
    )
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_ability(caller, raw_string, **kwargs):
    """
    Select an ability to use/boost etc.
    """
    text = "Choose the ability to apply"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": abi.value,
            "goto": (
                _step_wizard,
                {
                    **kwargs,
                    **{
                        "action_dict": {**action_dict, **{"stunt_type": abi, "defense_type": abi}},
                    },
                },
            ),
        }
        for abi in (
            Ability.STR,
            Ability.DEX,
            Ability.CON,
            Ability.INT,
            Ability.INT,
            Ability.WIS,
            Ability.CHA,
        )
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_use_item(caller, raw_string, **kwargs):
    """
    Choose item to use.

    """
    text = "Select the item"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": item.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"item": item}}}},
            ),
        }
        for item in caller.equipment.get_usable_objects_from_backpack()
    ]
    if not options:
        text = "There are no usable items in your inventory!"

    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_wield_item(caller, raw_string, **kwargs):
    """
    Choose item to use.

    """
    text = "Select the item"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": item.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"item": item}}}},
            ),
        }
        for item in caller.equipment.get_wieldable_objects_from_backpack()
    ]
    if not options:
        text = "There are no items in your inventory that you can wield!"

    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_combat(caller, raw_string, **kwargs):
    """Base combat menu"""

    combathandler = _get_combathandler(caller)

    text = combathandler.get_combat_summary(caller)
    options = [
        {
            "desc": "attack an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_enemy_target"],
                    "action_dict": {"key": "attack", "target": None, "repeat": True},
                },
            ),
        },
        {
            "desc": "Stunt - gain a later advantage against a target",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_target",
                        "node_choose_allied_recipient",
                    ],
                    "action_dict": {"key": "stunt", "advantage": True},
                },
            ),
        },
        {
            "desc": "Stunt - give an enemy disadvantage against yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_recipient",
                        "node_choose_allied_target",
                    ],
                    "action_dict": {"key": "stunt", "advantage": False},
                },
            ),
        },
        {
            "desc": "Use an item on yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_allied_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Use an item on an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_enemy_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Wield/swap with an item from inventory",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_wield_item"],
                    "action_dict": {"key": "wield", "item": None},
                },
            ),
        },
        {
            "desc": "flee!",
            "goto": (_queue_action, {"action_dict": {"key": "flee", "repeat": True}}),
        },
        {
            "desc": "hold, doing nothing",
            "goto": (_queue_action, {"action_dict": {"key": "hold"}}),
        },
        {
            "key": "_default",
            "goto": "node_combat",
        },
    ]

    return text, options


# Add this command to the Character cmdset to make turn-based combat available.


class CmdTurnAttack(Command):
    """
    Start or join combat.

    Usage:
      attack [<target>]

    """

    key = "attack"
    aliases = ["hit", "turnbased combat"]

    turn_timeout = 30  # seconds
    flee_time = 3  # rounds

    def parse(self):
        super().parse()
        self.args = self.args.strip()

    def func(self):
        if not self.args:
            self.msg("What are you attacking?")
            return

        target = self.caller.search(self.args)
        if not target:
            return

        if not hasattr(target, "hp"):
            self.msg("You can't attack that.")
            return
        elif target.hp <= 0:
            self.msg(f"{target.get_display_name(self.caller)} is already down.")
            return

        if target.is_pc and not target.location.allow_pvp:
            self.msg("PvP combat is not allowed here!")
            return

        combathandler = _get_combathandler(self.caller, self.turn_timeout, self.flee_time)

        # add combatants to combathandler. this can be done safely over and over
        combathandler.add_combatant(self.caller)
        combathandler.queue_action(self.caller, {"key": "attack", "target": target})
        combathandler.add_combatant(target)
        target.msg("|rYou are attacked by {self.caller.get_display_name(self.caller)}!|n")
        combathandler.start_combat()

        # build and start the menu
        EvMenu(
            self.caller,
            {
                "node_choose_enemy_target": node_choose_enemy_target,
                "node_choose_allied_target": node_choose_allied_target,
                "node_choose_enemy_recipient": node_choose_enemy_recipient,
                "node_choose_allied_recipient": node_choose_allied_recipient,
                "node_choose_ability": node_choose_ability,
                "node_choose_use_item": node_choose_use_item,
                "node_choose_wield_item": node_choose_wield_item,
                "node_combat": node_combat,
            },
            startnode="node_combat",
            combathandler=combathandler,
            auto_look=False,
            # cmdset_mergetype="Union",
            persistent=True,
        )


class TurnCombatCmdSet(CmdSet):
    """
    CmdSet for the turn-based combat.
    """

    key = "turncombat_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdTurnAttack())
