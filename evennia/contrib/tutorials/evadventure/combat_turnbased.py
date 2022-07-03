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

"""

from collections import defaultdict
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import make_iter
from evennia.utils import evmenu, evtable, dbserialize
from .enums import Ability
from . import rules

# for simplicity, we have a default duration for advantages/disadvantages


class CombatFailure(RuntimeError):
    """
    Some failure during actions.
    """


class CombatAction:
    """
    This is the base of a combat-action, like 'attack' or defend.
    Inherit from this to make new actions.

    """

    key = "action"
    help_text = "Combat action to perform."
    # action to echo to everyone.
    post_action_text = "{combatant} performed an action."
    max_uses = None  # None for unlimited
    # in which order (highest first) to perform the action. If identical, use random order
    priority = 0

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

    def __serialize_dbobjs__(self):
        self.combathandler = dbserialize.dbserialize(self.combathandler)
        self.combatant = dbserialize.dbserialize(self.combatant)

    def __deserialize_dbobjs__(self):
        self.combathandler = dbserialize.dbunserialize(self.combathandler)
        self.combatant = dbserialize.dbunserialize(self.combatant)

    def get_help(self, *args, **kwargs):
        return self.help_text

    def can_use(self, combatant, *args, **kwargs):
        """
        Determine if combatant can use this action. In this implementation,
        it fails if already use all of a usage-limited action.

        Args:
            combatant (Object): The one performing the action.
            *args: Any optional arguments.
            **kwargs: Any optional keyword arguments.

        Returns:
            tuple: (bool, motivation) - if not available, will describe why,
                if available, should describe what the action does.

        """
        return True if self.uses is None else self.uses < self.max_uses

    def pre_use(self, *args, **kwargs):
        pass

    def use(self, *args, **kwargs):
        pass

    def post_use(self, *args, **kwargs):
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
    Perform a stunt. A stunt grants an advantage to yours or another player for their next
    action, or a disadvantage to yours or an enemy's next action.

    Note that while the check happens between the user and a target, another (the 'beneficiary'
    could still gain the effect. This allows for boosting allies or making them better
    defend against an enemy.

    Note: We only count a use if the stunt is successful; they will still spend their turn, but won't
    spend a use unless they succeed.

    """

    give_advantage = True
    give_disadvantage = False
    max_uses = 1
    priority = -1
    attack_type = Ability.DEX
    defense_type = Ability.DEX
    help_text = (
        "Perform a stunt against a target. This will give you or an ally advantage "
        "on your next action against the same target [range 0-1, one use per combat. "
        "Bonus lasts for two turns]."
    )

    def use(self, attacker, defender, *args, beneficiary=None, **kwargs):
        # quality doesn't matter for stunts, they are either successful or not

        is_success, _ = rules.EvAdventureRollEngine.opposed_saving_throw(
            attacker,
            defender,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=False,
            disadvantage=disadvantage,
        )
        if is_success:
            beneficiary = beneficiary if beneficiary else attacker
            if advantage:
                self.combathandler.gain_advantage(beneficiary, defender)
            else:
                self.combathandler.gain_disadvantage(defender, beneficiary)

            self.msg
            # only spend a use after being successful
            uses += 1


class CombatActionAttack(CombatAction):
    """
    A regular attack, using a wielded weapon. Depending on weapon type, this will be a ranged or
    melee attack.

    """

    key = "attack"
    priority = 1

    def use(self, attacker, defender, *args, **kwargs):
        """
        Make an attack against a defender.

        """
        # figure out advantage (gained by previous stunts)
        advantage = bool(self.combathandler.advantage_matrix[attacker].pop(defender, False))

        # figure out disadvantage (gained by enemy stunts/actions)
        disadvantage = bool(self.combathandler.disadvantage_matrix[attacker].pop(defender, False))

        is_hit, quality = rules.EvAdventureRollEngine.opposed_saving_throw(
            attacker,
            defender,
            attack_type=attacker.weapon.attack_type,
            defense_type=attacker.weapon.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        if is_hit:
            self.combathandler.resolve_damage(
                attacker, defender, critical=quality == "critical success"
            )

            # TODO messaging here


class CombatActionUseItem(CombatAction):
    """
    Use an item in combat. This is meant for one-off or limited-use items, like potions, scrolls or
    wands.  We offload the usage checks and usability to the item's own hooks. It's generated dynamically
    from the items in the character's inventory (you could also consider using items in the room this way).

    Each usable item results in one possible action.

    It relies on the combat_* hooks on the item:
        combat_get_help
        combat_can_use
        combat_pre_use
        combat_pre
        combat_post_use

    """

    def get_help(self, item, *args):
        return item.combat_get_help(*args)

    def can_use(self, item, combatant, *args, **kwargs):
        return item.combat_can_use(combatant, self.combathandler, *args, **kwargs)

    def pre_use(self, item, *args, **kwargs):
        item.combat_pre_use(*args, **kwargs)

    def use(self, item, combatant, target, *args, **kwargs):
        item.combat_use(combatant, target, *args, **kwargs)

    def post_use(self, item, *args, **kwargs):
        item.combat_post_use(*args, **kwargs)


class CombatActionFlee(CombatAction):
    """
    Fleeing/disengaging from combat means doing nothing but 'running away' for two turn. Unless
    someone attempts and succeeds in their 'chase' action, you will leave combat by fleeing at the
    end of the second turn.

    """

    key = "flee"
    priority = -1

    def use(self, combatant, target, *args, **kwargs):
        # it's safe to do this twice
        self.combathandler.flee(combatant)


class CombatActionChase(CombatAction):

    """
    Chasing is a way to counter a 'flee' action. It is a maximum movement towards the target
    and will mean a DEX contest, if the fleeing target loses, they are moved back from
    'disengaging' range and remain in combat at the new distance (likely 2 if max movement
    is 2). Advantage/disadvantage are considered.

    """

    key = "chase"
    priority = -5  # checked last

    attack_type = Ability.DEX  # or is it CON?
    defense_type = Ability.DEX

    def use(self, combatant, fleeing_target, *args, **kwargs):

        advantage = bool(self.advantage_matrix[attacker].pop(fleeing_target, False))
        disadvantage = bool(self.disadvantage_matrix[attacker].pop(fleeing_target, False))

        is_success, _ = rules.EvAdventureRollEngine.opposed_saving_throw(
            combatant,
            fleeing_target,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )

        if is_success:
            # managed to stop the target from fleeing/disengaging
            self.combatant.unflee(fleeing_target)
        else:
            pass  # they are getting away!


class EvAdventureCombatHandler(DefaultScript):
    """
    This script is created when combat is initialized and stores a queue
    of all active participants. It's also possible to join (or leave) the fray later.

    """

    # we use the same duration for all stunts
    stunt_duration = 3

    # these will all be checked if they are available at a given time.
    all_action_classes = [
        CombatActionDoNothing,
        CombatActionChase,
        CombatActionUseItem,
        CombatActionStunt,
        CombatActionAttack,
    ]

    # attributes

    # stores all combatants active in the combat
    combatants = AttributeProperty(list())
    action_queue = AttributeProperty(dict())

    turn_stats = AttributeProperty(defaultdict(list))

    # turn counter - abstract time
    turn = AttributeProperty(default=0)
    # advantages or disadvantages gained against different targets
    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    fleeing_combatants = AttributeProperty(default=list())

    # how often this script ticks - the length of each turn (in seconds)
    interval = 60

    def at_repeat(self, **kwargs):
        """
        Called every self.interval seconds. The main tick of the script.

        """
        if self.turn == 0:
            self._start_turn()
        else:
            self._end_turn()
            self._start_turn()

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

        1. Do all regular actions
        2. Remove combatants that disengaged successfully
        3. Timeout advantages/disadvantages

        """
        # do all actions
        for combatant in self.combatants:
            # read the current action type selected by the player
            action, args, kwargs = self.action_queue.get(
                combatant, (CombatActionDoNothing(self, combatant), (), {})
            )
            # perform the action on the CombatAction instance
            action.use(combatant, *args, **kwargs)

        # handle disengaging combatants

        to_remove = []

        for combatant in self.combatants:
            # check disengaging combatants (these are combatants that managed
            # to stay at disengaging distance for a turn)
            if combatant in self.fleeing_combatants:
                self.disengaging_combatants.remove(combatant)

        for combatant in to_remove:
            # for clarity, we remove here rather than modifying the combatant list
            # inside the previous loop
            self.msg(f"{combatant.key} disengaged and left combat.")
            self.remove_combatant(combatant)

        # refresh stunt timeouts (note - self.stunt_duration is the same for
        # all stunts; # for more complex use we could store the action and let action have a
        # 'duration' property to use instead.
        oldest_stunt_age = self.turn - self.stunt_duration

        advantage_matrix = self.advantage_matrix
        disadvantage_matrix = self.disadvantage_matrix
        # rebuild advantages with the (possibly cropped) list of combatants
        # we make new matrices in order to make sure disengaged combatants are
        # not included.
        new_advantage_matrix = {}
        new_disadvantage_matrix = {}

        for combatant in self.combatants:
            new_advantage_matrix[combatant] = {
                target: set_at_turn
                for target, turn in advantage_matrix.items()
                if set_at_turn > oldest_stunt_age
            }
            new_disadvantage_matrix[combatant] = {
                target: set_at_turn
                for target, turn in disadvantage_matrix.items()
                if set_at_turn > oldest_stunt_age
            }

        self.advantage_matrix = new_advantage_matrix
        self.disadvantage_matrix = new_disadvantage_matrix

    def add_combatant(self, combatant):
        if combatant not in self.combatants:
            self.combatants.append(combatant)

    def remove_combatant(self, combatant):
        if combatant in self.combatants:
            self.combatants.remove(combatant)

    def get_combat_summary(self, combatant):
        """
        Get a summary of the current combat state from the perspective of a
        given combatant.

        You (5/10 health)
        Foo (Hurt) [Running away - use 'chase' to stop them!]
        Bar (Perfect health)

        """
        table = evtable.EvTable(border_width=0)

        # 'You' display
        fleeing = ""
        if combatant in self.fleeing_combatants:
            fleeing = " You are running away! Use 'flee' again next turn."

        table.add_row(f"You ({combatant.hp} / {combatant.hp_max} health){fleeing}")

        for comb in self.combatants:

            if comb is combatant:
                continue

            name = combatant.key
            health = f"{comb.hurt_level}"
            fleeing = ""
            if comb in self.fleeing_combatants:
                fleeing = " [Running away! Use 'chase' to stop them!"

            table.add_row(f"{name} ({health}){fleeing}")

        return str(table)

    def msg(self, message, targets=None):
        """
        Central place for sending messages to combatants. This allows
        for adding any combat-specific text-decoration in one place.

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

    def flee(self, combatant):
        if combatant not in self.fleeing_combatants:
            self.fleeing_combatants.append(combatant)

    def unflee(self, combatant):
        if combatant in self.fleeing_combatants:
            self.fleeing_combatants.remove(combatant)

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
                self.msg(
                    "You are alive, but out of the fight. If you want to press your luck, "
                    "you need to rejoin the combat.",
                    targets=defender,
                )
                defender.at_defeat()  # note - NPC monsters may still 'die' here
            else:
                # outright killed
                defender.at_death()

            # no matter the result, the combatant is out
            self.remove_combatant(defender)
        else:
            # defender still alive
            self.msg(defender)

    def register_action(self, action, combatant, *args, **kwargs):
        """
        Register an action by-name.

        Args:
            combatant (Object): The one performing the action.
            action (CombatAction): An available action class to use.

        """
        if not action:
            action = CombatActionDoNothing
        self.action_queue[combatant] = (action(self, combatant), args, kwargs)


# combat menu

combat_script = """




"""


def _register_action(caller, raw_string, **kwargs):
    """
    Register action with handler.

    """
    action = kwargs.get["action"]
    action_args = kwargs["action_args"]
    action_kwargs = kwargs["action_kwargs"]
    combat = caller.scripts.get("combathandler")
    combat.register_action(caller, action=action, *action_args, **action_kwargs)


def node_select_target(caller, raw_string, **kwargs):
    """
    Menu node allowing for selecting a target among all combatants. This combines
    with all other actions.

    """
    action = kwargs.get("action")
    action_args = kwargs.get("action_args")
    action_kwargs = kwargs.get("action_kwargs")
    combat = caller.scripts.get("combathandler")
    text = "Select target for |w{action}|n."

    combatants = [combatant for combatant in combat.combatants if combatant is not caller]
    options = [
        {
            "desc": combatant.key,
            "goto": (
                _register_action,
                {"action": action, "args": action_args, "kwargs": action_kwargs},
            ),
        }
        for combatant in combat.combatants
    ]
    # make the apply-self option always the last one
    options.append(
        {
            "desc": "(yourself)",
            "goto": (
                _register_action,
                {"action": action, "args": action_args, "kwargs": action_kwargs},
            ),
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
        "goto": (
            "node_select_target",
            {
                "action": action,
            },
        ),
    }

    return text, options
