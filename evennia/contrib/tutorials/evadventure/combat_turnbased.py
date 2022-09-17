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
6. [F]lee/disengage (takes two turns)
7. [B]lock <target> from fleeing
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

from collections import defaultdict

from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import dbserialize, delay, evmenu, evtable, logger
from evennia.utils.utils import inherits_from

from . import rules
from .enums import Ability
from .npcs import EvAdventureNPC

COMBAT_HANDLER_KEY = "evadventure_turnbased_combathandler"
COMBAT_HANDLER_INTERVAL = 30


class CombatFailure(RuntimeError):
    """
    Some failure during actions.

    """


# -----------------------------------------------------------------------------------
#  Combat Actions
# -----------------------------------------------------------------------------------


class CombatAction:
    """
    This is the base of a combat-action, like 'attack'  Inherit from this to make new actions.

    Note:
        We want to store initialized version of this objects in the CombatHandler (in order to track
        usages, time limits etc), so we need to make sure we can serialize it into an Attribute. See
        `Attribute` documentation for more about `__serialize_dbobjs__` and
        `__deserialize_dbobjs__`.

    """

    key = "Action"
    desc = "Option text"
    aliases = []
    help_text = "Combat action to perform."

    # the next combat menu node to go to - this ties the combat action into the UI
    # use None to do nothing (jump directly to registering the action)
    next_menu_node = "node_select_action"

    max_uses = None  # None for unlimited
    # in which order (highest first) to perform the action. If identical, use random order
    priority = 0

    def __init__(self, combathandler, combatant):
        self.combathandler = combathandler
        self.combatant = combatant
        self.uses = 0

    def msg(self, message, broadcast=True):
        """
        Convenience route to the combathandler msg-sender mechanism.

        Args:
            message (str): Message to send; use `$You()` and `$You(other.key)`
                to refer to the combatant doing the action and other combatants,
                respectively.
        """
        self.combathandler.msg(message, combatant=self.combatant, broadcast=broadcast)

    def __serialize_dbobjs__(self):
        """
        This is necessary in order to be able to store this entity in an Attribute.
        We must make sure to tell Evennia how to serialize internally stored db-objects.

        The `__serialize_dbobjs__` and `__deserialize_dbobjs__` methods form a required pair.

        """
        self.combathandler = dbserialize.dbserialize(self.combathandler)
        self.combatant = dbserialize.dbserialize(self.combatant)

    def __deserialize_dbobjs__(self):
        """
        This is necessary in order to be able to store this entity in an Attribute.
        We must make sure to tell Evennia how to deserialize internally stored db-objects.

        The `__serialize_dbobjs__` and `__deserialize_dbobjs__` methods form a required pair.

        """
        if isinstance(self.combathandler, bytes):
            self.combathandler = dbserialize.dbunserialize(self.combathandler)
            self.combatant = dbserialize.dbunserialize(self.combatant)

    def get_help(self, *args, **kwargs):
        """
        Allows to customize help message on the fly. By default, just returns `.help_text`.

        """
        return self.help_text

    def can_use(self, *args, **kwargs):
        """
        Determine if combatant can use this action. In this implementation,
        it fails if already used up all of a usage-limited action.

        Args:
            *args: Any optional arguments.
            **kwargs: Any optional keyword arguments.

        Returns:
            tuple: (bool, motivation) - if not available, will describe why,
                if available, should describe what the action does.

        """
        return True if self.max_uses is None else self.uses < (self.max_uses or 0)

    def pre_use(self, *args, **kwargs):
        """
        Called just before the main action.

        """

        pass

    def use(self, *args, **kwargs):
        """
        Main activation of the action. This happens simultaneously to other actions.

        """
        pass

    def post_use(self, *args, **kwargs):
        """
        Called just after the action has been taken.

        """
        pass


class CombatActionAttack(CombatAction):
    """
    A regular attack, using a wielded weapon. Depending on weapon type, this will be a ranged or
    melee attack.

    """

    key = "Attack or Cast"
    desc = "[A]ttack/[C]ast spell at <target>"
    aliases = ("a", "c", "attack", "cast")
    help_text = "Make an attack using your currently equipped weapon/spell rune"
    next_menu_node = "node_select_enemy_target"

    priority = 1

    def use(self, defender, *args, **kwargs):
        """
        Make an attack against a defender.

        """
        attacker = self.combatant
        weapon = self.combatant.weapon

        # figure out advantage (gained by previous stunts)
        advantage = bool(self.combathandler.advantage_matrix[attacker].pop(defender, False))
        # figure out disadvantage (gained by enemy stunts/actions)
        disadvantage = bool(self.combathandler.disadvantage_matrix[attacker].pop(defender, False))

        is_hit, quality, txt = rules.dice.opposed_saving_throw(
            attacker,
            defender,
            attack_type=weapon.attack_type,
            defense_type=attacker.weapon.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        self.msg(f"$You() $conj(attack) $You({defender.key}) with {weapon.key}: {txt}")
        if is_hit:
            # enemy hit, calculate damage
            weapon_dmg_roll = attacker.weapon.damage_roll

            dmg = rules.dice.roll(weapon_dmg_roll)

            if quality is Ability.CRITICAL_SUCCESS:
                dmg += rules.dice.roll(weapon_dmg_roll)
                message = (
                    f" $You() |ycritically|n $conj(hit) $You({defender.key}) for |r{dmg}|n damage!"
                )
            else:
                message = f" $You() $conj(hit) $You({defender.key}) for |r{dmg}|n damage!"
            self.msg(message)

            # call hook
            defender.at_damage(dmg, attacker=attacker)

            # note that we mustn't remove anyone from combat yet, because this is
            # happening simultaneously. So checking of the final hp
            # and rolling of death etc happens in the combathandler at the end of the turn.

        else:
            # a miss
            message = f" $You() $conj(miss) $You({defender.key})."
            if quality is Ability.CRITICAL_FAILURE:
                attacker.weapon.quality -= 1
                message += ".. it's a |rcritical miss!|n, damaging the weapon."
            self.msg(message)


class CombatActionStunt(CombatAction):
    """
    Perform a stunt. A stunt grants an advantage to yours or another player for their next
    action, or a disadvantage to yours or an enemy's next action.

    Note that while the check happens between the user and a target, another (the 'beneficiary'
    could still gain the effect. This allows for boosting allies or making them better
    defend against an enemy.

    Note: We only count a use if the stunt is successful; they will still spend their turn, but
    won't spend a use unless they succeed.

    """

    key = "Perform a Stunt"
    desc = "Make [S]tunt against <target>"
    aliases = ("s", "stunt")
    help_text = (
        "A stunt does not cause damage but grants/gives advantage/disadvantage to future "
        "actions. The effect needs to be used up within 5 turns."
    )
    next_menu_node = "node_select_enemy_target"

    give_advantage = True  # if False, give_disadvantage
    max_uses = 1
    priority = -1
    attack_type = Ability.DEX
    defense_type = Ability.DEX
    help_text = (
        "Perform a stunt against a target. This will give you an advantage or an enemy "
        "disadvantage on your next action."
    )

    def use(self, defender, *args, **kwargs):
        # quality doesn't matter for stunts, they are either successful or not

        attacker = self.combatant
        advantage, disadvantage = False, False

        is_success, _, txt = rules.dice.opposed_saving_throw(
            attacker,
            defender,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        self.msg(f"$You() $conj(attempt) stunt on $You(defender.key). {txt}")
        if is_success:
            stunt_duration = self.combathandler.stunt_duration
            if self.give_advantage:
                self.combathandler.gain_advantage(attacker, defender)
                self.msg(
                    "%You() $conj(gain) advantage against $You(defender.key! "
                    f"You must use it within {stunt_duration} turns."
                )
            else:
                self.combathandler.gain_disadvantage(defender, attacker)
                self.msg(
                    f"$You({defender.key}) $conj(suffer) disadvantage against $You(). "
                    "Lasts next attack, or until 3 turns passed."
                )

            # only spend a use after being successful
            self.uses += 1


class CombatActionUseItem(CombatAction):
    """
    Use an item in combat. This is meant for one-off or limited-use items, like potions, scrolls or
    wands.  We offload the usage checks and usability to the item's own hooks. It's generated
    dynamically from the items in the character's inventory (you could also consider using items in
    the room this way).

    Each usable item results in one possible action.

    It relies on the combat_* hooks on the item:
        combat_get_help
        combat_can_use
        combat_pre_use
        combat_pre
        combat_post_use

    """

    key = "Use Item"
    desc = "[U]se item"
    aliases = ("u", "item", "use item")
    help_text = "Use an item from your inventory."
    next_menu_node = "node_select_friendly_target"

    def get_help(self, item, *args):
        return item.get_help(*args)

    def use(self, item, target, *args, **kwargs):
        item.at_use(self.combatant, target, *args, **kwargs)

    def post_use(self, item, *args, **kwargs):
        item.at_post_use(self.combatant, *args, **kwargs)
        self.msg("$You() $conj(use) an item.")


class CombatActionSwapWieldedWeaponOrSpell(CombatAction):
    """
    Swap Wielded weapon or spell.

    """

    key = "Swap weapon/rune/shield"
    desc = "Swap currently wielded weapon, shield or spell-rune."
    aliases = (
        "s",
        "swap",
        "draw",
        "swap weapon",
        "draw weapon",
        "swap rune",
        "draw rune",
        "swap spell",
        "draw spell",
    )
    help_text = (
        "Draw a new weapon or spell-rune from your inventory, replacing your current loadout"
    )

    next_menu_node = "node_select_wield_from_inventory"

    def use(self, _, item, *args, **kwargs):
        # this will make use of the item
        self.combatant.equipment.move(item)


class CombatActionFlee(CombatAction):
    """
    Fleeing/disengaging from combat means doing nothing but 'running away' for two turn. Unless
    someone attempts and succeeds in their 'block' action, you will leave combat by fleeing at the
    end of the second turn.

    """

    key = "Flee/Disengage"
    desc = "[F]lee/disengage from combat (takes two turns)"
    aliases = ("d", "disengage", "flee")

    # this only affects us
    next_menu_node = "node_confirm_register_action"

    help_text = (
        "Disengage from combat. Use successfully two times in a row to leave combat at the "
        "end of the second round. If someone Blocks you successfully, this counter is reset."
    )
    priority = -5  # checked last

    def use(self, *args, **kwargs):
        # it's safe to do this twice
        self.msg(
            "$You() $conj(retreat), and will leave combat next round unless someone successfully "
            "blocks the escape."
        )
        self.combathandler.flee(self.combatant)


class CombatActionBlock(CombatAction):

    """
    Blocking is, in this context, a way to counter an enemy's 'Flee/Disengage' action.

    """

    key = "Block"
    desc = "[B]lock <target> from fleeing"
    aliases = ("b", "block", "chase")
    help_text = (
        "Move to block a target from fleeing combat. If you succeed "
        "in a DEX vs DEX challenge, they don't get away."
    )
    next_menu_node = "node_select_enemy_target"

    priority = -1  # must be checked BEFORE the flee action of the target!

    attack_type = Ability.DEX
    defense_type = Ability.DEX

    def use(self, fleeing_target, *args, **kwargs):

        advantage = bool(
            self.combathandler.advantage_matrix[self.combatant].pop(fleeing_target, False)
        )
        disadvantage = bool(
            self.combathandler.disadvantage_matrix[self.combatant].pop(fleeing_target, False)
        )

        is_success, _, txt = rules.dice.opposed_saving_throw(
            self.combatant,
            fleeing_target,
            attack_type=self.attack_type,
            defense_type=self.defense_type,
            advantage=advantage,
            disadvantage=disadvantage,
        )
        self.msg(
            f"$You() $conj(try) to block the retreat of $You({fleeing_target.key}). {txt}",
        )

        if is_success:
            # managed to stop the target from fleeing/disengaging
            self.combathandler.unflee(fleeing_target)
            self.msg(f"$You() $conj(block) the retreat of $You({fleeing_target.key})")
        else:
            self.msg(f"$You({fleeing_target.key}) $conj(dodge) away from you $You()!")


class CombatActionDoNothing(CombatAction):
    """
    Do nothing this turn.

    """

    key = "Hesitate"
    desc = "Do [N]othing/Hesitate"
    aliases = ("n", "hesitate", "nothing", "do nothing")
    help_text = "Hold you position, doing nothing."

    # affects noone else
    next_menu_node = "node_confirm_register_action"

    post_action_text = "{combatant} does nothing this turn."

    def use(self, *args, **kwargs):
        self.msg("$You() $conj(hesitate), accomplishing nothing.")


# -----------------------------------------------------------------------------------
#  Combat handler
# -----------------------------------------------------------------------------------


class EvAdventureCombatHandler(DefaultScript):
    """
    This script is created when combat is initialized and stores a queue
    of all active participants.

    It's also possible to join (or leave) the fray later.

    """

    # we use the same duration for all stunts
    stunt_duration = 3

    # Default actions available to everyone
    default_action_classes = [
        CombatActionAttack,
        CombatActionStunt,
        CombatActionSwapWieldedWeaponOrSpell,
        CombatActionUseItem,
        CombatActionFlee,
        CombatActionBlock,
        CombatActionDoNothing,
    ]

    # attributes

    # stores all combatants active in the combat
    combatants = AttributeProperty(list())
    # each combatant has its own set of actions that may or may not be available
    # every round
    combatant_actions = AttributeProperty(defaultdict(dict))

    action_queue = AttributeProperty(dict())

    turn_stats = AttributeProperty(dict())

    # turn counter - abstract time
    turn = AttributeProperty(default=0)
    # advantages or disadvantages gained against different targets
    advantage_matrix = AttributeProperty(defaultdict(dict))
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    fleeing_combatants = AttributeProperty(list())
    defeated_combatants = AttributeProperty(list())

    _warn_time_task = None

    def at_script_creation(self):

        # how often this script ticks - the max length of each turn (in seconds)
        self.key = COMBAT_HANDLER_KEY
        self.interval = COMBAT_HANDLER_INTERVAL

    def at_repeat(self, **kwargs):
        """
        Called every self.interval seconds. The main tick of the script.

        """
        if self._warn_time_task:
            self._warn_time_task.remove()

        if self.turn == 0:
            self._start_turn()
        else:
            self._end_turn()
            self._start_turn()

    def _init_menu(self, combatant, session=None):
        """
        Make sure combatant is in the menu. This is safe to call on a combatant already in a menu.

        """
        if not combatant.ndb._evmenu:
            # re-joining the menu is useful during testing
            evmenu.EvMenu(
                combatant,
                {
                    "node_wait_start": node_wait_start,
                    "node_select_enemy_target": node_select_enemy_target,
                    "node_select_friendly_target": node_select_friendly_target,
                    "node_select_action": node_select_action,
                    "node_select_wield_from_inventory": node_select_wield_from_inventory,
                    "node_wait_turn": node_wait_turn,
                },
                startnode="node_wait_turn",
                auto_quit=True,
                persistent=True,
                cmdset_mergetype="Union",
                session=session,
                combathandler=self,  # makes this available as combatant.ndb._evmenu.combathandler
            )

    def _warn_time(self, time_remaining):
        """
        Send a warning message when time is about to run out.

        """
        self.msg(f"{time_remaining} seconds left in round!")

    def _start_turn(self):
        """
        New turn events

        """
        self.turn += 1
        self.action_queue = {}
        self.turn_stats = defaultdict(list)

        # start a timer to echo a warning to everyone 15 seconds before end of round
        if self.interval >= 0:
            # set -1 for unit tests
            warning_time = 10
            self._warn_time_task = delay(
                self.interval - warning_time, self._warn_time, warning_time
            )

        self.msg(f"|y_______________________ start turn {self.turn} ___________________________|n")

        for combatant in self.combatants:
            if hasattr(combatant, "ai_combat_next_action"):
                # NPC needs to get a decision from the AI
                next_action_key, args, kwargs = combatant.ai_combat_next_action(self)
                self.register_action(combatant, next_action_key, *args, **kwargs)
            else:
                # cycle combat menu for PC
                self._init_menu(combatant)
                combatant.ndb._evmenu.goto("node_select_action", "")

    def _end_turn(self):
        """
        End of turn operations.

        1. Do all regular actions
        2. Check if fleeing combatants got away - remove them from combat
        3. Check if anyone has hp <= - defeated
        4. Check if any one side is alone on the battlefield - they loot the defeated
        5. If combat is still on, update stunt timers

        """
        self.msg(
            f"|y__________________ turn resolution (turn {self.turn}) ____________________|n\n"
        )

        # store those in the process of fleeing
        already_fleeing = self.fleeing_combatants[:]

        # do all actions
        for combatant in self.combatants:
            # read the current action type selected by the player
            action, args, kwargs = self.action_queue.get(
                combatant, (CombatActionDoNothing(self, combatant), (), {})
            )
            # perform the action on the CombatAction instance
            try:
                action.pre_use(*args, **kwargs)
                action.use(*args, **kwargs)
                action.post_use(*args, **kwargs)
            except Exception as err:
                combatant.msg(
                    f"An error ({err}) occurred when performing this action.\n"
                    "Please report the problem to an admin."
                )
                logger.log_trace()
                raise

        # handle disengaging combatants

        to_flee = []
        to_defeat = []

        for combatant in self.combatants:
            # see if fleeing characters managed to do two flee actions in a row.
            if (combatant in self.fleeing_combatants) and (combatant in already_fleeing):
                self.fleeing_combatants.remove(combatant)
                to_flee.append(combatant)

            if combatant.hp <= 0:
                # check characters that are beaten down.
                # characters roll on the death table here; but even if they survive, they
                # count as defeated (unconcious) for this combat.
                combatant.at_defeat()
                to_defeat.append(combatant)

        for combatant in to_flee:
            # combatant leaving combat by fleeing
            self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
            self.remove_combatant(combatant)

        for combatant in to_defeat:
            # combatants leaving combat by being defeated
            self.msg("|r$You() $conj(fall) to the ground, defeated.|n", combatant=combatant)
            self.combatants.remove(combatant)
            self.defeated_combatants.append(combatant)

        # check if only one side remains, divide into allies and enemies based on the first
        # combatant,then check if either team is empty.
        if not self.combatants:
            # everyone's defeated at the same time. This is a tie where everyone loses and
            # no looting happens.
            self.msg("|yEveryone takes everyone else out. Today, noone wins.|n")
            self.stop_combat()
            return
        else:
            combatant = self.combatants[0]
            allies = self.get_friendly_targets(combatant)  # will always contain at least combatant
            enemies = self.get_enemy_targets(combatant)

            if not enemies:
                # no enemies left - allies to combatant won!
                defeated_enemies = self.get_enemy_targets(
                    combatant, all_combatants=self.defeated_combatants
                )

                # all surviving allies loot the fallen enemies
                for ally in allies:
                    for enemy in defeated_enemies:
                        try:
                            if ally.pre_loot(enemy):
                                enemy.at_looted(ally)
                                ally.post_loot(enemy)
                        except Exception:
                            logger.log_trace()
                self.stop_combat()
                return

        # if we get here, combat is still on

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
                for target, set_at_turn in advantage_matrix[combatant].items()
                if set_at_turn > oldest_stunt_age
            }
            new_disadvantage_matrix[combatant] = {
                target: set_at_turn
                for target, set_at_turn in disadvantage_matrix[combatant].items()
                if set_at_turn > oldest_stunt_age
            }

        self.advantage_matrix = new_advantage_matrix
        self.disadvantage_matrix = new_disadvantage_matrix

    def add_combatant(self, combatant, session=None):
        """
        Add combatant to battle.

        Args:
            combatant (Object): The combatant to add.
            session (Session, optional): Session to use.

        Notes:
            This adds them to the internal list and initiates
            all possible actions. If the combatant as an Attribute list
            `custom_combat_actions` containing `CombatAction` items, this
            will injected and if the `.key` matches, will replace the
            default action classes.

        """
        if combatant not in self.combatants:
            self.combatants.append(combatant)
            combatant.db.combathandler = self

            # allow custom character actions (not used by default)
            custom_action_classes = combatant.db.custom_combat_actions or []

            self.combatant_actions[combatant] = {
                action_class.key: action_class(self, combatant)
                for action_class in self.default_action_classes + custom_action_classes
            }
            self._init_menu(combatant, session=session)

    def remove_combatant(self, combatant):
        """
        Remove combatant from battle.

        Args:
            combatant (Object): The combatant to remove.

        """
        if combatant in self.combatants:
            self.combatants.remove(combatant)
            self.combatant_actions.pop(combatant, None)
            if combatant.ndb._evmenu:
                combatant.ndb._evmenu.close_menu()
            del combatant.db.combathandler

    def start_combat(self):
        """
        Start the combat timer and get everyone going.

        """
        for combatant in self.combatants:
            combatant.ndb._evmenu.goto("node_select_action", "")
        self.start()  # starts the script timer
        self._start_turn()

    def stop_combat(self):
        """
        This is used to stop the combat immediately.

        It can also be called from external systems, for example by
        monster AI can do this when only allied players remain.

        """
        for combatant in self.combatants:
            self.remove_combatant(combatant)
        self.delete()

    def get_enemy_targets(self, combatant, excluded=None, all_combatants=None):
        """
        Get all valid targets the given combatant can target for an attack. This does not apply for
        'friendly' targeting (like wanting to cast a heal on someone). We assume there are two types
        of combatants - PCs (player-controlled characters and NPCs (AI-controlled). Here, we assume
        npcs can never attack one another (or themselves)

        For PCs to be able to target each other, the `allow_pvp`
        Attribute flag must be set on the current `Room`.

        Args:
            combatant (Object): The combatant looking for targets.
            excluded (list, optional): If given, these are not valid targets - this can be used to
                avoid friendly NPCs.
            all_combatants (list, optional): If given, use this list to get all combatants, instead
                of using `self.combatants`.

        """
        is_pc = not inherits_from(combatant, EvAdventureNPC)
        allow_pvp = self.obj.allow_pvp
        targets = []
        combatants = all_combatants or self.combatants

        if is_pc:
            if allow_pvp:
                # PCs may target everyone, including other PCs
                targets = combatants
            else:
                # PCs may only attack NPCs
                targets = [target for target in combatants if inherits_from(target, EvAdventureNPC)]

        else:
            # NPCs may only attack PCs, not each other
            targets = [target for target in combatants if not inherits_from(target, EvAdventureNPC)]

        if excluded:
            targets = [target for target in targets if target not in excluded]

        return targets

    def get_friendly_targets(self, combatant, extra=None, all_combatants=None):
        """
        Get a list of all 'friendly' or neutral targets a combatant may target, including
        themselves.

        Args:
            combatant (Object): The combatant looking for targets.
            extra (list, optional): If given, these are additional targets that can be
                considered target for allied effects (could be used for a friendly NPC).
            all_combatants (list, optional): If given, use this list to get all combatants, instead
                of using `self.combatants`.

        """
        is_pc = not inherits_from(combatant, EvAdventureNPC)
        combatants = all_combatants or self.combatants
        if is_pc:
            # can target other PCs
            targets = [target for target in combatants if not inherits_from(target, EvAdventureNPC)]
        else:
            # can target other NPCs
            targets = [target for target in combatants if inherits_from(target, EvAdventureNPC)]

        if extra:
            targets = list(set(targets + extra))

        return targets

    def get_combat_summary(self, combatant):
        """
        Get a summary of the current combat state from the perspective of a
        given combatant.

        Args:
            combatant (Object): The combatant to get the summary for

        Returns:
            str: The summary.

        Example:

            ```
            You (5/10 health)
            Foo (Hurt) [Running away - use 'block' to stop them!]
            Bar (Perfect health)

            ```

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

            name = comb.key
            health = f"{comb.hurt_level}"
            fleeing = ""
            if comb in self.fleeing_combatants:
                fleeing = " [Running away! Use 'block' to stop them!"

            table.add_row(f"{name} ({health}){fleeing}")

        return str(table)

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

    def register_action(self, combatant, action_key, *args, **kwargs):
        """
        Register an action based on its `.key`.

        Args:
            combatant (Object): The one performing the action.
            action_key (str): The action to perform, by its `.key`.
            *args: Arguments to pass to `action.use`.
            **kwargs: Kwargs to pass to `action.use`.

        """
        # get the instantiated action for this combatant
        action = self.combatant_actions[combatant].get(
            action_key, CombatActionDoNothing(self, combatant)
        )

        # store the action in the queue
        self.action_queue[combatant] = (action, args, kwargs)

        if len(self.action_queue) >= len(self.combatants):
            # all combatants registered actions - force the script
            # to cycle (will fire at_repeat)
            self.force_repeat()

    def get_available_actions(self, combatant, *args, **kwargs):
        """
        Get only the actions available to a combatant.

        Args:
            combatant (Object): The combatant to get actions for.
            *args: Passed to `action.can_use()`
            **kwargs: Passed to `action.can_use()`

        Returns:
            list: The initiated CombatAction instances available to the
                combatant right now.

        Note:
            We could filter this by `.can_use` return already here, but then it would just
            be removed from the menu. Instead we return all and use `.can_use` in the menu
            so we can include the option but gray it out.

        """
        return list(self.combatant_actions[combatant].values())


# -----------------------------------------------------------------------------------
#  Combat Menu definitions
# -----------------------------------------------------------------------------------


def _register_action(caller, raw_string, **kwargs):
    """
    Actually register action with handler.

    """
    action_key = kwargs.pop("action_key")
    action_args = kwargs["action_args"]
    action_kwargs = kwargs["action_kwargs"]
    action_target = kwargs.pop("action_target", None)
    combat_handler = caller.ndb._evmenu.combathandler
    combat_handler.register_action(caller, action_key, action_target, *action_args, **action_kwargs)

    # move into waiting
    return "node_wait_turn"


def node_confirm_register_action(caller, raw_string, **kwargs):
    """
    Node where one can confirm registering the action or change one's mind.

    """
    action_key = kwargs["action_key"]
    action_target = kwargs.get("action_target", None) or ""
    if action_target:
        action_target = f", targeting {action_target.key}"

    text = f"You will {action_key}{action_target}. Confirm? [Y]/n"
    options = (
        {
            "key": "_default",
            "goto": (_register_action, kwargs),
        },
        {"key": ("Abort/Cancel", "abort", "cancel", "a", "no", "n"), "goto": "node_select_action"},
    )
    return text, options


def _select_target_helper(caller, raw_string, targets, **kwargs):
    """
    Helper to select among only friendly or enemy targets (given by the calling node).

    """
    action_key = kwargs["action_key"]
    text = f"Select target for |w{action_key}|n."

    # make the apply-self option always the first one, give it key 0
    if caller in targets:
        targets.remove(caller)
        kwargs["action_target"] = caller
        options = [{"key": "0", "desc": "(yourself)", "goto": (_register_action, kwargs)}]
    # filter out ourselves and then make options for everyone else
    for inum, combatant in enumerate(targets):
        kwargs["action_target"] = combatant
        options.append(
            {"key": str(inum + 1), "desc": combatant.key, "goto": (_register_action, kwargs)}
        )

    # add ability to cancel
    options.append({"key": "_default", "goto": "node_select_action"})

    return text, options


def node_select_enemy_target(caller, raw_string, **kwargs):
    """
    Menu node allowing for selecting an enemy target among all combatants. This combines
    with all other actions.

    """
    combat = caller.ndb._evmenu.combathandler
    targets = combat.get_enemy_targets(caller)
    return _select_target_helper(caller, raw_string, targets, **kwargs)


def node_select_friendly_target(caller, raw_string, **kwargs):
    """
    Menu node for selecting a friendly target among combatants (including oneself).

    """
    combat = caller.ndb._evmenu.combathandler
    targets = combat.get_friendly_targets(caller)
    return _select_target_helper(caller, raw_string, targets, **kwargs)


def _item_broken(caller, raw_string, **kwargs):
    caller.msg("|rThis item is broken and unusable!|n")
    return None  # back to previous node


def node_select_wield_from_inventory(caller, raw_string, **kwargs):
    """
    Menu node allowing for wielding item(s) from inventory.

    """
    loadout = caller.equipment.display_loadout()
    text = (
        f"{loadout}\nSelect weapon, spell or shield to draw. It will swap out "
        "anything already in the same hand (you can't change armor or helmet in combat)."
    )

    # get a list of all suitable weapons/spells/shields
    options = []
    for obj in caller.equipment.get_wieldable_objects_from_backpack():
        if obj.quality <= 0:
            # object is broken
            options.append(
                {
                    "desc": "|Rstr(obj)|n",
                    "goto": _item_broken,
                }
            )
        else:
            # normally working item
            kwargs["action_args"] = (obj,)
            options.append({"desc": str(obj), "goto": (_register_action, kwargs)})

    # add ability to cancel
    options.append(
        {"key": "_default", "desc": "(No input to Abort and go back)", "goto": "node_select_action"}
    )

    return text, options


def node_select_use_item_from_inventory(caller, raw_string, **kwargs):
    """
    Menu item allowing for using usable items (like potions) from inventory.

    """
    text = "Select an item to use."

    # get a list of all suitable weapons/spells/shields
    options = []
    for obj in caller.inventory.get_usable_objects_from_backpack():
        if obj.quality <= 0:
            # object is broken
            options.append(
                {
                    "desc": "|Rstr(obj)|n",
                    "goto": _item_broken,
                }
            )
        else:
            # normally working item
            kwargs["action_args"] = (obj,)
            options.append({"desc": str(obj), "goto": (_register_action, kwargs)})

    # add ability to cancel
    options.append({"key": "_default", "goto": "node_select_action"})

    return text, options


def _action_unavailable(caller, raw_string, **kwargs):
    """
    Selecting an unavailable action.

    """
    action_key = kwargs["action_key"]
    caller.msg(f"|rAction |w{action_key}|r is currently not available.|n")
    # go back to previous node
    return


def node_select_action(caller, raw_string, **kwargs):
    """
    Menu node for selecting a combat action.

    """
    combat = caller.ndb._evmenu.combathandler
    text = combat.get_combat_summary(caller)

    options = []
    for icount, action in enumerate(combat.get_available_actions(caller)):
        # we handle counts manually so we can grey the entire line if action is unavailable.
        key = str(icount + 1)
        desc = action.desc

        if not action.can_use():
            # action is unavailable. Greyscale the option if not available and route to the
            # _action_unavailable helper
            key = f"|x{key}|n"
            desc = f"|x{desc}|n"

            options.append(
                {
                    "key": (key,) + tuple(action.aliases),
                    "desc": desc,
                    "goto": (_action_unavailable, {"action_key": action.key}),
                }
            )
        elif action.next_menu_node is None:
            # action is available, but needs no intermediary step. Redirect to register
            # the action immediately
            options.append(
                {
                    "key": (key,) + tuple(action.aliases),
                    "desc": desc,
                    "goto": (
                        _register_action,
                        {
                            "action_key": action.key,
                            "action_args": (),
                            "action_kwargs": {},
                            "action_target": None,
                        },
                    ),
                }
            )
        else:
            # action is available and next_menu_node is set to point to the next node we want
            options.append(
                {
                    "key": (key,) + tuple(action.aliases),
                    "desc": desc,
                    "goto": (
                        action.next_menu_node,
                        {
                            "action_key": action.key,
                            "action_args": (),
                            "action_kwargs": {},
                            "action_target": None,
                        },
                    ),
                }
            )
        # add ability to cancel
        options.append(
            {
                "key": "_default",
                "goto": "node_select_action",
            }
        )

    return text, options


def node_wait_turn(caller, raw_string, **kwargs):
    """
    Menu node routed to waiting for the round to end (for everyone to choose their actions).

    All menu actions route back to the same node. The CombatHandler will handle moving everyone back
    to the `node_select_action` node when the next round starts.

    """
    text = "Waiting for other combatants ..."

    options = {
        "key": "_default",
        "desc": "(next round will start automatically)",
        "goto": "node_wait_turn",
    }
    return text, options


def node_wait_start(caller, raw_string, **kwargs):
    """
    Menu node entered when waiting for the combat to start. New players joining an existing
    combat will end up here until the previous round is over, at which point the combat handler
    will goto everyone to `node_select_action`.

    """
    text = "Waiting for combat round to start ..."

    options = {
        "key": "_default",
        "desc": "(combat will start automatically)",
        "goto": "node_wait_start",
    }
    return text, options


# -----------------------------------------------------------------------------------
#  Access function
# -----------------------------------------------------------------------------------


def join_combat(caller, *targets, session=None):
    """
    Join or create a new combat involving caller and at least one target. The combat
    is started on the current room location - this means there can only be one combat
    in each room (this is not hardcoded in the combat per-se, but it makes sense for
    this implementation).

    Args:
        caller (Object): The one starting the combat.
        *targets (Objects): Any other targets to pull into combat. At least one target
            is required if `combathandler` is not given (a new combat must have at least
            one opponent!).

    Keyword Args:
        session (Session, optional): A player session to use. This is useful for multisession modes.

    Returns:
        EvAdventureCombatHandler: A created or existing combat handler.

    """
    created = False
    location = caller.location
    if not location:
        raise CombatFailure("Must have a location to start combat.")

    if caller.hp <= 0:
        raise CombatFailure("You can't start a fight in your current condition!")

    if not getattr(location, "allow_combat", False):
        raise CombatFailure("This is not the time and place for picking a fight.")

    if not targets:
        raise CombatFailure("Must have an opponent to start combat.")

    combathandler = location.scripts.get(COMBAT_HANDLER_KEY).first()
    if not combathandler:
        combathandler = location.scripts.add(EvAdventureCombatHandler, autostart=False)
        created = True

    if not hasattr(caller, "hp"):
        raise CombatFailure("You have no hp and so can't attack anyone.")

    # it's safe to add a combatant to the same combat more than once
    combathandler.add_combatant(caller, session=session)
    for target in targets:
        if target.hp <= 0:
            caller.msg(f"{target.get_display_name(caller)} is already out of it.")
            continue
        combathandler.add_combatant(target)

    if created:
        combathandler.start_combat()

    return combathandler
