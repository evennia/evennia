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
from . import rules

MIN_RANGE = 0
MAX_RANGE = 4

RANGE_NAMES = {
    0: "close",  # melee, short weapons, fists. long weapons with disadvantage
    1: "near",  # melee, long weapons, short weapons with disadvantage
    2: "medium",  # thrown, ranged with disadvantage
    3: "far",  # ranged, thrown with disadvantage
    4: "disengaging"  # no weapons
}


class AttackFailure(RuntimeError):
    """
    Cannot attack for some reason.
    """


class EvAdventureCombat(DefaultScript):
    """
    This script is created when combat is initialized and stores a queue
    of all active participants. It's also possible to join (or leave) the fray later.

    """
    combatants = AttributeProperty(default=list())
    action_queue = AttributeProperty(default=dict())

    # turn counter - abstract time
    turn = AttributeProperty(default=0)
    # symmetric distance matrix (handled dynamically). Mapping {combatant1: {combatant2: dist}, ...}
    distance_matrix = defaultdict(dict)
    # advantages or disadvantages gained against different targets
    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    stunt_duration = 2

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

    def _start_turn(self):
        """
        New turn events

        """
        self.turn += 1
        self.action_queue = {}

    def _end_turn(self):
        """
        End of turn cleanup.

        """
        # refresh stunt timeouts
        oldest_stunt_age = self.turn - self.stunt_duration

        advantage_matrix = self.advantage_matrix
        disadvantage_matrix = self.disadvantage_matrix

        # to avoid modifying the dict while we iterate over it, we
        # put the results in new dicts. This also avoids us having to
        # delete from the old dicts.
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

    def add_combatant(self, combatant):
        if combatant not in self.combatants:
            self.combatants.append(combatant)
            self._refresh_distance_matrix()

    def remove_combatant(self, combatant):
        if combatant in self.combatants:
            self.combatants.remove(combatant)
            self._refresh_distance_matrix()

    def move_relative_to(self, combatant, target_combatant, change):
        """
        Change the distance to a target.

        Args:
            combatant (Character): The one doing the change.
            target_combatant (Character): The one distance is changed to.
            change (int): A +/- change value. Result is always in range 0..4.

        """
        current_dist = self.distance_matrix[combatant][target_combatant]

        new_dist = max(MIN_RANGE, min(MAX_RANGE, current_dist + change))

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

    def stunt(self, attacker, defender, attack_type="agility",
              defense_type="agility", optimal_distance=0, suboptimal_distance=1,
              advantage=True, beneficiary=None):
        """
        Stunts does not hurt anyone, but are used to give advantage/disadvantage to combatants
        for later turns. The 'attacker' here is the one attemting the stunt against the 'defender'.
        If successful, advantage is given to attacker against defender and disadvantage to
        defender againt attacker. It's also possible to replace the attacker with another combatant
        against the defender - allowing to aid/hinder others on the battlefield.

        Stunt-modifers last a maximum of two turns and are not additive. Advantages and
        disadvantages against the same target cancel each other out.

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
            # fighting at the wrong range is not good
            disadvantage = True
        elif self._get_optimal_distance(attacker) != distance:
            # if we are neither at optimal nor suboptimal distance, we can't do the stunt
            # from here.
            raise AttackFailure(f"You can't perform this stunt "
                                f"from {RANGE_NAMES[distance]} distance (must be "
                                f"{RANGE_NAMES[suboptimal_distance]} or, even better, "
                                f"{RANGE_NAMES[optimal_distance]}).")
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

    def attack(self, attacker, defender):
        """
        Make an attack against a defender. This takes into account distance.

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
            raise AttackFailure(f"You can't attack with {attacker.weapon.key} "
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
