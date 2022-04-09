"""
EvAdventure turn-based combat

This implements a turn-based combat style, where both sides have a little longer time to
choose their next action. If they don't react before a timer runs out, the previous action
will be repeated. This means that a 'twitch' style combat can be created using the same
mechanism, by just speeding up each 'turn'.

The combat is handled with a `Script` shared between all combatants; this tracks the state
of combat and handles all timing elements.

Unlike in base _Knave_, the MUD version's combat is simultaneous; everyone plans and executes
their turns simultaneously with minimum downtime. This version also includes a stricter
handling of optimal distances than base _Knave_ (this would be handled by the GM normally).

"""

from dataclasses import dataclass
from collections import defaultdict
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import make_iter
from evennia.utils import evmenu, evtable
from . import rules

MIN_RANGE = 0
MAX_RANGE = 4
MAX_MOVE_RATE = 2
STUNT_DURATION = 2

RANGE_NAMES = {
    0: "close",  # melee, short weapons, fists. long weapons with disadvantage
    1: "near",  # melee, long weapons, short weapons with disadvantage
    2: "medium",  # thrown, ranged with disadvantage
    3: "far",  # ranged, thrown with disadvantage
    4: "disengaging"  # no weapons
}


class CombatFailure(RuntimeError):
    """
    Some failure during actions.
    """

class CombatAction:
    """
    This describes a combat-action, like 'attack'.

    """
    key = 'action'
    help_text = "Combat action to perform."
    # action to echo to everyone.
    post_action_text = "{combatant} performed an action."
    optimal_range = 0
    # None for unlimited
    max_uses = None
    suboptimal_range = 1
    # move actions can be combined with other actions
    is_move_action = False

    def __init__(self, combathandler, combatant):
        self.combathandler = combathandler
        self.combatant = combatant
        self.uses = 0

    def msg(self, message, broadcast=False):
        if broadcast:
            # send to everyone in combat.
            self.combathandler.msg(message)
        else:
            # send only to the combatant.
            self.combatant.msg(message)

    def get_help(self):
        return ""

    def check_distance(self, distance, optimal_range=None, suboptimal_range=None):
        """Call to easily check and warn for out-of-bound distance"""

        if optimal_range is None:
            optimal_range = self.optimal_range
        if suboptimal_range is None:
            suboptimal_range = self.suboptimal_range

        if distance not in (self.suboptimal_distance, self.optimal_distance):
            # if we are neither at optimal nor suboptimal distance, we can't do the stunt
            # from here.
            self.msg(f"|rYou can't perform {self.key} from {range_names[distance]} distance "
                     "(must be {range_names[suboptimal_distance]} or, even better, "
                     "{range_names[optimal_distance]}).|n")
            return False
        elif self.distance == self.suboptimal_distance:
            self.msg(f"|yNote: Performing {self.key} from {range_names[distance]} works, but "
                     f"the optimal range is {range_names[optimal_range]} (you'll "
                     "act with disadvantage).")
        return True

    def can_use(self, combatant, *args, **kwargs):
        """
        Determine if combatant can use this action.

        Args:
            combatant (Object): The one performing the action.
            *args: Any optional arguments.
            **kwargs: Any optional keyword arguments.

        Returns:
            tuple: (bool, motivation) - if not available, will describe why,
                if available, should describe what the action does.

        """
        return True if self.uses is None else self.uses < self.max_uses

    def pre_perform(self, *args, **kwargs):
        pass

    def perform(self, *args, **kwargs):
        pass

    def post_perform(self, *args, **kwargs):
        self.uses += 1
        self.combathandler.msg(self.post_action_text.format(combatant=combatant))


class CombatActionDoNothing(CombatAction):
    """
    Do nothing this turn.

    """
    help_text = "Hold you position, doing nothing."
    post_action_text = "{combatant} does nothing this turn."



class CombatActionStunt(CombatAction):
    """
    Perform a stunt.

    """
    optimal_distance = 0
    suboptimal_distance = 1
    give_advantage = True
    give_disadvantage = False
    uses = 1
    attack_type = "dexterity"
    defense_type = "dexterity"
    help_text = ("Perform a stunt against a target. This will give you or an ally advantage "
                 "on your next action against the same target [range 0-1, one use per combat. "
                 "Bonus lasts for two turns].")

    def perform(self, attacker, defender, *args, beneficiary=None, **kwargs):
        # quality doesn't matter for stunts, they are either successful or not

        is_success, _  = rules.EvAdventureRollEngine.opposed_saving_throw(
            attacker, defender,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=False, disadvantage=disadvantage,
        )
        if is_success:
            beneficiary = beneficiary if beneficiary else attacker
            if advantage:
                self.gain_advantage(beneficiary, defender)
            else:
                self.gain_disadvantage(defender, beneficiary)

            self.msg


class EvAdventureCombatHandler(DefaultScript):
    """
    This script is created when combat is initialized and stores a queue
    of all active participants. It's also possible to join (or leave) the fray later.

    """
    combatants = AttributeProperty(list())
    action_queue = AttributeProperty(dict())

    turn_stats = AttributeProperty(defaultdict(list))

    # turn counter - abstract time
    turn = AttributeProperty(default=0)
    # symmetric distance matrix (handled dynamically). Mapping {combatant1: {combatant2: dist}, ...}
    distance_matrix = defaultdict(dict)
    # advantages or disadvantages gained against different targets
    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    disengaging_combatants = AttributeProperty(default=list())

    # actions that will be performed before a normal action
    move_actions = ("approach", "withdraw")

    def at_init(self):
        self.ndb.actions = {
            "do_nothing": CombatActionDoNothing,
        }


    def _refresh_distance_matrix(self):
        """
        Refresh the distance matrix, either after movement or when a
        new combatant enters combat - everyone must have a symmetric
        distance to every other combatant (that is, if you are 'near' an opponent,
        they are also 'near' to you).

        Distances are abstract and divided into four steps:

        0. Close (melee, short weapons, fists, long weapons with disadvantage)
        1. Near (melee, long weapons, short weapons with disadvantage)
        2. Medium (thrown, ranged with disadvantage)
        3. Far (ranged, thrown with disadvantage)
        4. Disengaging/fleeing (no weapons can be used)

        Distance is tracked to each opponent individually. One can move 1 step and attack
        or up to 2 steps (closer or further away) without attacking.

        New combatants will start at a distance averaged between the optimal ranges
        of them and their opponents.

        """
        combatants = self.combatants
        distance_matrix = self.distance_matrix

        for combatant1 in combatants:
            for combatant2 in combatants:

                if combatant1 == combatant2:
                    continue

                combatant1_distances = distance_matrix[combatant1]
                combatant2_distances = distance_matrix[combatant2]

                if combatant2 not in combatant1_distances or combatant1 not in combatant2_distances:
                    # this happens on initialization or when a new combatant is added.
                    # we make sure to update both sides to the distance of the longest
                    # optimal weapon range. So ranged weapons have advantage going in.
                    start_optimal = max(combatant1.weapon.distance_optimal,
                                        combatant2.weapon.distance_optimal)

                    combatant1_distances[combatant2] = start_optimal
                    combatant2_distances[combatant1] = start_optimal

    def _update_turn_stats(self, combatant, message):
        """
        Store combat messages to display at the end of turn.

        """
        self.turn_stats[combatant].append(message)

    def _start_turn(self):
        """
        New turn events

        """
        self.turn += 1
        self.action_queue = {}
        self.turn_stats = defaultdict(list)

    def _end_turn(self):
        """
        End of turn operations.

        1. Do all moves
        2. Do all regular actions
        3. Remove combatants that disengaged successfully
        4. Timeout advantages/disadvantages set for longer than STUNT_DURATION

        """
        # first do all moves
        for combatant in self.combatants:
            action, args, kwargs = self.action_queue[combatant].get(
                "move", ("do_nothing", (), {}))
            getattr(self, f"action_{action}")(combatant, *args, **kwargs)
        # next do all regular actions
        for combatant in self.combatants:
            action, args, kwargs = self.action_qeueue[combatant].get(
                "action", ("do_nothing", (), {}))
            getattr(self, f"action_{action}")(combatant, *args, **kwargs)

        # handle disengaging combatants

        to_remove = []

        for combatant in self.combatants:
            # check disengaging combatants (these are combatants that managed
            # to stay at disengaging distance for a turn)
            if combatant in self.disengaging_combatants:
                self.disengaging_combatants.remove(combatant)
                to_remove.append(combatant)
            elif all(1 for distance in self.distance_matrix[combatant].values()
                     if distance == MAX_RANGE):
                # if at max distance (disengaging) from everyone, they are disengaging
                self.disengaging_combatants.append(combatant)

        for combatant in to_remove:
            # for clarity, we remove here rather than modifying the combatant list
            # inside the previous loop
            self.msg(f"{combatant.key} disengaged and left combat.")
            self.remove_combatant(combatant)

        # refresh stunt timeouts

        oldest_stunt_age = self.turn - STUNT_DURATION

        advantage_matrix = self.advantage_matrix
        disadvantage_matrix = self.disadvantage_matrix
        # rebuild advantages with the (possibly cropped) list of combatants
        # we make new matrices in order to make sure disengaged combatants are
        # not included.
        new_advantage_matrix = {}
        new_disadvantage_matrix = {}

        for combatant in self.combatants:
            new_advantage_matrix[combatant] = {
                target: set_at_turn for target, turn in advantage_matrix.items()
                if set_at_turn > oldest_stunt_age
            }
            new_disadvantage_matrix[combatant] = {
                target: set_at_turn for target, turn in disadvantage_matrix.items()
                if set_at_turn > oldest_stunt_age
            }

        self.advantage_matrix = new_advantage_matrix
        self.disadvantage_matrix = new_disadvantage_matrix

    def add_combatant(self, combatant):
        if combatant not in self.combatants:
            self.combatants.append(combatant)
            self._refresh_distance_matrix()

    def remove_combatant(self, combatant):
        if combatant in self.combatants:
            self.combatants.remove(combatant)
            self._refresh_distance_matrix()

    def get_combat_summary(self, combatant):
        """
        Get a summary of the current combat state.

        You (5/10 health)
        Foo (Hurt) distance:   You__0__1___X____3_____4 (medium)
        Bar (Perfect health):  You__X__1___2____3_____4 (close)

        """
        table = evtable.EvTable(border_width=0)

        table.add_row(f"You ({combatant.hp} / {combatant.hp_max} health)")

        dist_template = "|x(You)__{0}|x__{1}|x___{2}|x____{3}|x_____|R{4} |x({distname})"

        for comb in self.combatants:

            if comb is combatant:
                continue

            name = combatant.key
            distance = self.distance_matrix[combatant][comb]
            dist_map = {i: '|wX' if i == distance else i for i in range(MAX_RANGE)}
            dist_map["distname"] = RANGE_NAMES[distance]
            health = f"{comb.hurt_level}"
            distance_string = dist_template.format(**dist_map)

            table.add_row(f"{name} ({health})", distance_string)

        return str(table)

    def msg(self, message, targets=None):
        """
        Central place for sending messages to combatants. This allows
        for decorating the output in one place if needed.

        Args:
            message (str): The message to send.
            targets (Object or list, optional): Sends message only to
                one or more particular combatants. If unset, send to
                everyone in the combat.

        """
        if targets:
            for target in make_iter(targets):
                target.msg(message)
        else:
            for target in self.combatants:
                target.msg(message)

    def move_relative_to(self, combatant, target_combatant, change,
                         min_dist=MIN_RANGE, max_dist=MAX_RANGE):
        """
        Change the distance to a target.

        Args:
            combatant (Character): The one doing the change.
            target_combatant (Character): The one distance is changed to.
            change (int): A +/- change value. Result is always in range 0..4.

        """
        current_dist = self.distance_matrix[combatant][target_combatant]

        change = max(0, min(MAX_MOVE_RATE, change))

        new_dist = max(min_dist, min(max_dist, current_dist + change))

        self.distance_matrix[combatant][target_combatant] = new_dist
        self.distance_matrix[target_combatant][combatant] = new_dist

    def gain_advantage(self, combatant, target):
        """
        Gain advantage against target. Spent by actions.

        """
        self.advantage_matrix[combatant][target] = self.turn

    def gain_disadvantage(self, combatant, target):
        """
        Gain disadvantage against target. Spent by actions.

        """
        self.disadvantage_matrix[combatant][target] = self.turn

    def resolve_damage(self, attacker, defender, critical=False):
        """
        Apply damage to defender. On a critical hit, the damage die
        is rolled twice.

        """
        weapon_dmg_roll = attacker.weapon.damage_roll

        dmg = rules.EvAdventureRollEngine.roll(weapon_dmg_roll)
        if critical:
            dmg += rules.EvAdventureRollEngine.roll(weapon_dmg_roll)

        defender.hp -= dmg

        # call hook
        defender.at_damage(dmg, attacker=attacker)

        if defender.hp <= 0:
            # roll on death table. This may or may not kill you
            rules.EvAdventureRollEngine.roll_death(self)

            # tell everyone
            self.msg(defender.defeat_message(attacker, dmg))

            if defender.hp > 0:
                # they are weakened, but with hp
                self.msg("You are alive, but out of the fight. If you want to press your luck, "
                         "you need to rejoin the combat.", targets=defender)
                defender.at_defeat()  # note - NPC monsters may still 'die' here
            else:
                # outright killed
                defender.at_death()

            # no matter the result, the combatant is out
            self.remove_combatant(defender)
        else:
            # defender still alive
            self.msg(defender)

    def register_action(self, combatant, action="do_nothing", *args, **kwargs):
        """
        Register an action by-name.

        Args:
            combatant (Object): The one performing the action.
            action (str): An available action, will be prepended with `action_` and
                used to call the relevant handler on this script.
            *args: Will be passed to the action method `action_<action>`.
            **kwargs: Will be passed into the action method `action_<action>`.

        """
        if action in self.move_actions:
            self.action_queue[combatant]["move"] = (action, args, kwargs)
        else:
            self.action_queue[combatant]["action"] = (action, args, kwargs)

    # action verbs. All of these start with action_* and should also accept
    # *args, **kwargs so that we can make the call-mechanism generic.

    def action_do_nothing(self, combatant, *args, **kwargs):
        """Do nothing for a turn."""

    def action_stunt(self, attacker, defender, attack_type="agility",
              defense_type="agility", optimal_distance=0, suboptimal_distance=1,
              advantage=True, beneficiary=None, *args, **kwargs):
        """
        Stunts does not cause damage but are used to give advantage/disadvantage to combatants
        for later turns. The 'attacker' here is the one attemting the stunt against the 'defender'.
        If successful, advantage is given to attacker against defender and disadvantage to
        defender againt attacker. It's also possible to replace the attacker with another combatant
        against the defender - allowing to aid/hinder others on the battlefield.

        Stunt-modifers last a maximum of two turns and are not additive. Advantages and
        disadvantages relative to the same target cancel each other out.

        Args:
            attacker (Object): The one attempting the stunt.
            defender (Object): The one affected by the stunt.
            attack_type (str): The ability tested to do the stunt.
            defense_type (str): The ability used to defend against the stunt.
            optimal_distance (int): At which distance the stunt works normally.
            suboptimal_distance (int): At this distance, the stunt is performed at disadvantage.
            advantage (bool): If False, try to apply disadvantage to defender
                rather than advantage to attacker.
            beneficiary (bool): If stunt succeeds, it may benefit another
                combatant than the `attacker` doing the stunt. This allows for helping
                allies.

        """
        # check if stunt-attacker is at optimal distance
        distance = self.distance_matrix[attacker][defender]
        disadvantage = False
        if suboptimal_distance == distance:
            # stunts need to be within range
            disadvantage = True
        elif self._get_optimal_distance(attacker) != distance:
            # if we are neither at optimal nor suboptimal distance, we can't do the stunt
            # from here.
            raise combatfailure(f"you can't perform this stunt "
                                f"from {range_names[distance]} distance (must be "
                                f"{range_names[suboptimal_distance]} or, even better, "
                                f"{range_names[optimal_distance]}).")
        # quality doesn't matter for stunts, they are either successful or not
        is_success, _  = rules.EvAdventureRollEngine.opposed_saving_throw(
            attacker, defender,
            attack_type=attack_type,
            defense_type=defense_type,
            advantage=False, disadvantage=disadvantage,
        )
        if is_success:
            beneficiary = beneficiary if beneficiary else attacker
            if advantage:
                self.gain_advantage(beneficiary, defender)
            else:
                self.gain_disadvantage(defender, beneficiary)

        return is_success

    def action_attack(self, attacker, defender, *args, **kwargs):
        """
        Make an attack against a defender. This takes into account distance. The
        attack type/defense depends on the weapon/spell/whatever used.

        """
        # check if attacker is at optimal distance
        distance = self.distance_matrix[attacker][defender]

        # figure out advantage (gained by previous stunts)
        advantage = bool(self.advantage_matrix[attacker].pop(defender, False))

        # figure out disadvantage (by distance or by previous action)
        disadvantage = bool(self.disadvantage_matrix[attacker].pop(defender, False))
        if self._get_suboptimal_distance(attacker) == distance:
            # fighting at the wrong range is not good
            disadvantage = True
        elif self._get_optimal_distance(attacker) != distance:
            # if we are neither at optimal nor suboptimal distance, we can't
            # attack from this range
            raise CombatFailure(f"You can't attack with {attacker.weapon.key} "
                                f"from {RANGE_NAMES[distance]} distance.")

        is_hit, quality = rules.EvAdventureRollEngine.opposed_saving_throw(
            attacker, defender,
            attack_type=attacker.weapon.attack_type,
            defense_type=attacker.weapon.defense_type,
            advantage=advantage, disadvantage=disadvantage
        )
        if is_hit:
            self.resolve_damage(attacker, defender, critical=quality == "critical success")

        return is_hit

    def action_heal(self, combatant, target, max_distance=1, healing_roll="1d6", *args, **kwargs):
        """
        Heal a target. Target can be the combatant itself.

        Args:
            combatant (Object): The one performing the heal.
            target (Object): The one to be healed (can be the same as combatant).
            max_distance (int): Distances *up to* this range allow for healing.
            healing_roll (str): The die roll for how many HP to heal.

        Raises:
            CombatFailure: If too far away to heal target.

        """
        if target is not combatant:
            distance = self.distance_matrix[attacker][defender]
            if distance > max_distance:
                raise CombatFailure(f"Too far away to heal {target.key}.")

        target.heal(rules.EvAdventureRollEngine.roll(healing_roll), healer=combatant)

    def action_approach(self, combatant, other_combatant, change, *args, **kwargs):
        """
        Approach target. Closest is 0. This can be combined with another action.

        """
        self.move_relative_to(combatant, other_combatant, -abs(change), min_dist=MIN_RANGE)

    def action_withdraw(self, combatant, other_combatant, change):
        """
        Withdraw from target. Most distant is range 3 - further and you'll be disengaging.
        This can be combined with another action.

        """
        self.move_relative_to(combatant, other_combatant, abs(change), max_dist=3)

    def action_flee(self, combatant, *args, **kwargs):
        """
        Fleeing/disengaging from combat means moving towards 'disengaging' range from
        everyone else and staying there for one turn.

        """
        for other_combatant in self.combatants:
            self.move_relative_to(combatant, other_combatant, MAX_MOVE_RATE, max_dist=MAX_RANGE)

    def action_chase(self, combatant, fleeing_target, *args, **kwargs):
        """
        Chasing is a way to counter a 'flee' action. It is a maximum movement towards the target
        and will mean a DEX contest, if the fleeing target loses, they are moved back from
        'disengaging' range and remain in combat at the new distance (likely 2 if max movement
        is 2). Advantage/disadvantage are considered.

        """
        ability = "dexterity"

        advantage = bool(self.advantage_matrix[attacker].pop(fleeing_target, False))
        disadvantage = bool(self.disadvantage_matrix[attacker].pop(fleeing_target, False))

        is_success, _ = rules.EvAdventureRollEngine.opposed_saving_throw(
            combatant, fleeing_target,
            attack_type=ability, defense_type=ability,
            advantage=advantage, disadvantage=disadvantage
        )

        if is_success:
            # managed to stop the target from fleeing/disengaging - move closer
            if fleeing_target in self.disengaging_combatants:
                self.disengaging_combatants.remove(fleeing_target)
            self.approach(combatant, fleeing_target, change=MAX_MOVE_RATE)

        return is_success


# combat menu

def _register_action(caller, raw_string, **kwargs):
    """
    Register action with handler.

    """
    action = kwargs.get['action']
    action_args = kwargs['action_args']
    action_kwargs = kwargs['action_kwargs']
    combat = caller.scripts.get("combathandler")
    combat.register_action(
        caller, action=action, *action_args, **action_kwargs
    )


def node_select_target(caller, raw_string, **kwargs):
    """
    Menu node allowing for selecting a target among all combatants. This combines
    with all other actions.

    """
    action = kwargs.get('action')
    action_args = kwargs.get('action_args')
    action_kwargs = kwargs.get('action_kwargs')
    combat = caller.scripts.get("combathandler")
    text = "Select target for |w{action}|n."

    combatants = [combatant for combatant in combat.combatants if combatant is not caller]
    options = [
        {
            "desc": combatant.key,
            "goto": (_register_action, {"action": action,
                                        "args": action_args,
                                        "kwargs": action_kwargs})
        }
    for combatant in combat.combatants]
    # make the apply-self option always the last one
    options.append(
        {
            "desc": "(yourself)",
            "goto": (_register_action, {"action": action,
                                       "args": action_args,
                                       "kwargs": action_kwargs})
        }
    )
    return text, options

def node_select_action(caller, raw_string, **kwargs):
    """
    Menu node for selecting a combat action.

    """
    combat = caller.scripts.get("combathandler")
    text = combat.get_previous_turn_status(caller)
    options = combat.get_available_options(caller)


    options = {
        "desc": action,
        "goto": ("node_select_target", {"action": action,
                                        })

    }


    return text, options
