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
from . import rules


@dataclass
class CombatantStats:
    """
    Represents temporary combat-only data we need to track
    during combat for a single Character.
    """
    weapon = None
    armor = None
    # abstract distance relationship to other combatants
    distance_matrix = {}
    # actions may affect what works better/worse next round
    advantage_actions_next_turn = []
    disadvantage_actions_next_turn = []

    def get_distance(self, target):
        return self.distance_matrix.get(target)

    def change_distance(self, target, change):
        current_dist = self.distance_matrix.get(target)  # will raise error if None, as it should
        self.distance_matrix[target] = max(0, min(4, current_dist + target))


class EvAdventureCombat(DefaultScript):
    """
    This script is created when combat is initialized and stores a queue
    of all active participants. It's also possible to join (or leave) the fray later.

    """
    combatants = AttributeProperty(default=dict())
    queue = AttributeProperty(default=list())
    # turn counter - abstract time
    turn = AttributeProperty(default=1)
    # symmetric distance matrix
    distance_matrix = {}

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

        Distance is tracked to each opponent individually. One can move 1 step and atack
        or 3 steps without attacking. Ranged weapons can't be used in range 0, 1 and
        melee weapons can't be used at ranges 2, 3.

        New combatants will start at a distance averaged between the optimal ranges
        of them and their opponents.

        """
        handled = []
        for combatant1, combatant_stats1 in self.combatants.items():
            for combatant2, combatant_stats2 in self.combatants.items():

                if combatant1 == combatant2:
                    continue

                # only update if data was not available already (or drifted
                # out of sync, which should not happen)
                dist1 = combatant_stats1.get_distance(combatant2)
                dist2 = combatant_stats2.get_distance(combatant1)
                if None in (dist1, dist2) or dist1 != dist2:
                    avg_range = round(0.5 * (combatant1.weapon.range_optimal
                                             + combatant2.weapon.range_optimal))
                    combatant_stats1.distance_matrix[combatant2] = avg_range
                    combatant_stats2.distance_matrix[combatant1] = avg_range

                handled.append(combatant1)
                handled.append(combatant2)

        self.combatants = handled

    def _move_relative_to(self, combatant, target_combatant, change):
        """
        Change the distance to a target.

        Args:
            combatant (Character): The one doing the change.
            target_combatant (Character): The one changing towards.
            change (int): A +/- change value. Result is always in range 0..4.

        """
        self.combatants[combatant].change_distance(target_combatant, change)
        self.combatants[target_combatant].change_distance(combatant, change)

    def add_combatant(self, combatant):
        self.combatants[combatant] = CombatantStats(
            weapon=combatant.equipment.get("weapon"),
            armor=combatant.equipment.armor,
        )
        self._refresh_distance_matrix()

    def remove_combatant(self, combatant):
        self.combatants.pop(combatant, None)
        self._refresh_distance_matrix()
