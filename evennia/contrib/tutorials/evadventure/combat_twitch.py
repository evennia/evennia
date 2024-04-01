"""
EvAdventure Twitch-based combat

This implements a 'twitch' (aka DIKU or other traditional muds) style of MUD combat.

----

"""

from evennia import AttributeProperty, CmdSet, default_cmds
from evennia.commands.command import Command, InterruptCommand
from evennia.utils.utils import (
    display_len,
    inherits_from,
    list_to_string,
    pad,
    repeat,
    unrepeat,
)

from .characters import EvAdventureCharacter
from .combat_base import (
    CombatActionAttack,
    CombatActionHold,
    CombatActionStunt,
    CombatActionUseItem,
    CombatActionWield,
    EvAdventureCombatBaseHandler,
)
from .enums import ABILITY_REVERSE_MAP


class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):
    """
    This is created on the combatant when combat starts. It tracks only the combatants
    side of the combat and handles when the next action will happen.


    """

    # fixed properties
    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
    }

    # dynamic properties

    advantage_against = AttributeProperty(dict)
    disadvantage_against = AttributeProperty(dict)

    action_dict = AttributeProperty(dict)
    fallback_action_dict = AttributeProperty({"key": "hold", "dt": 0})

    # stores the current ticker reference, so we can manipulate it later
    current_ticker_ref = AttributeProperty(None)

    def msg(self, message, broadcast=True, **kwargs):
        """
        Central place for sending messages to combatants. This allows
        for adding any combat-specific text-decoration in one place.

        Args:
            message (str): The message to send.
            combatant (Object): The 'You' in the message, if any.
            broadcast (bool): If `False`, `combatant` must be included and
                will be the only one to see the message. If `True`, send to
                everyone in the location.
            location (Object, optional): If given, use this as the location to
                send broadcast messages to. If not, use `self.obj` as that
                location.

        Notes:
            If `combatant` is given, use `$You/you()` markup to create
            a message that looks different depending on who sees it. Use
            `$You(combatant_key)` to refer to other combatants.
        """
        super().msg(message, combatant=self.obj, broadcast=broadcast, location=self.obj.location)

    def at_init(self):
        self.obj.cmdset.add(TwitchLookCmdSet, persistent=False)

    def get_sides(self, combatant):
        """
        Get a listing of the two 'sides' of this combat, from the perspective of the provided
        combatant. The sides don't need to be balanced.

        Args:
            combatant (Character or NPC): The one whose sides are to determined.

        Returns:
            tuple: A tuple of lists `(allies, enemies)`, from the perspective of `combatant`.
                Note that combatant itself is not included in either of these.

        """
        # get all entities involved in combat by looking up their combathandlers
        combatants = [
            comb
            for comb in self.obj.location.contents
            if hasattr(comb, "scripts") and comb.scripts.has(self.key)
        ]
        location = self.obj.location

        if hasattr(location, "allow_pvp") and location.allow_pvp:
            # in pvp, everyone else is an enemy
            allies = [combatant]
            enemies = [comb for comb in combatants if comb != combatant]
        else:
            # otherwise, enemies/allies depend on who combatant is
            pcs = [comb for comb in combatants if inherits_from(comb, EvAdventureCharacter)]
            npcs = [comb for comb in combatants if comb not in pcs]
            if combatant in pcs:
                # combatant is a PC, so NPCs are all enemies
                allies = pcs
                enemies = npcs
            else:
                # combatant is an NPC, so PCs are all enemies
                allies = npcs
                enemies = pcs
        return allies, enemies

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
        self.advantage_against[target] = True

    def give_disadvantage(self, recipient, target):
        """
        Let an affected party gain disadvantage against a target.

        Args:
            recipient (Character or NPC): The one to get the disadvantage.
            target (Character or NPC): The one against which the target gains disadvantage, usually
                an enemy.

        """
        self.disadvantage_against[target] = True

    def has_advantage(self, combatant, target):
        """
        Check if a given combatant has advantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have advantage
            target (Character or NPC): The target to check advantage against.

        """
        return self.advantage_against.get(target, False)

    def has_disadvantage(self, combatant, target):
        """
        Check if a given combatant has disadvantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have disadvantage
            target (Character or NPC): The target to check disadvantage against.

        """
        return self.disadvantage_against.get(target, False)

    def queue_action(self, action_dict, combatant=None):
        """
        Schedule the next action to fire.

        Args:
            action_dict (dict): The new action-dict to initialize.
            combatant: Unused.

        """
        if action_dict["key"] not in self.action_classes:
            self.obj.msg("This is an unkown action!")
            return

        # store action dict and schedule it to run in dt time
        self.action_dict = action_dict
        dt = action_dict.get("dt", 0)

        if self.current_ticker_ref:
            # we already have a current ticker going - abort it
            unrepeat(self.current_ticker_ref)
        if dt <= 0:
            # no repeat
            self.current_ticker_ref = None
        else:
            # always schedule the task to be repeating, cancel later otherwise. We store
            # the tickerhandler's ref to make sure we can remove it later
            self.current_ticker_ref = repeat(dt, self.execute_next_action, id_string="combat")

    def execute_next_action(self):
        """
        Triggered after a delay by the command
        """
        combatant = self.obj
        action_dict = self.action_dict
        action_class = self.action_classes[action_dict["key"]]
        action = action_class(self, combatant, action_dict)

        if action.can_use():
            action.execute()
            action.post_execute()

        if not action_dict.get("repeat", True):
            # not a repeating action, use the fallback (normally the original attack)
            self.action_dict = self.fallback_action_dict
            self.queue_action(self.fallback_action_dict)

        self.check_stop_combat()

    def check_stop_combat(self):
        """
        Check if the combat is over.
        """

        allies, enemies = self.get_sides(self.obj)

        location = self.obj.location

        # only keep combatants that are alive and still in the same room
        allies = [comb for comb in allies if comb.hp > 0 and comb.location == location]
        enemies = [comb for comb in enemies if comb.hp > 0 and comb.location == location]

        if not allies and not enemies:
            self.msg("Noone stands after the dust settles.", broadcast=False)
            self.stop_combat()
            return

        if not allies or not enemies:
            if allies + enemies == [self.obj]:
                self.msg("The combat is over.")
            else:
                still_standing = list_to_string(f"$You({comb.key})" for comb in allies + enemies)
                self.msg(
                    f"The combat is over. Still standing: {still_standing}.",
                    broadcast=False,
                )
            self.stop_combat()

    def stop_combat(self):
        """
        Stop combat immediately.
        """
        self.queue_action({"key": "hold", "dt": 0})  # make sure ticker is killed
        del self.obj.ndb.combathandler
        self.obj.cmdset.remove(TwitchLookCmdSet)
        self.delete()


class _BaseTwitchCombatCommand(Command):
    """
    Parent class for all twitch-combat commnads.

    """

    def at_pre_command(self):
        """
        Called before parsing.

        """
        if not self.caller.location or not self.caller.location.allow_combat:
            self.msg("Can't fight here!")
            raise InterruptCommand()

    def parse(self):
        """
        Handle parsing of most supported combat syntaxes (except stunts).

        <action> [<target>|<item>]
        or
        <action> <item> [on] <target>

        Use 'on' to differentiate if names/items have spaces in the name.

        """
        self.args = args = self.args.strip()
        self.lhs, self.rhs = "", ""

        if not args:
            return

        if " on " in args:
            lhs, rhs = args.split(" on ", 1)
        else:
            lhs, *rhs = args.split(None, 1)
            rhs = " ".join(rhs)
        self.lhs, self.rhs = lhs.strip(), rhs.strip()

    def get_or_create_combathandler(self, target=None, combathandler_key="combathandler"):
        """
        Get or create the combathandler assigned to this combatant.

        """
        if target:
            # add/check combathandler to the target
            if target.hp_max is None:
                self.msg("You can't attack that!")
                raise InterruptCommand()

            EvAdventureCombatTwitchHandler.get_or_create_combathandler(
                target, key=combathandler_key
            )
        return EvAdventureCombatTwitchHandler.get_or_create_combathandler(self.caller)


class CmdAttack(_BaseTwitchCombatCommand):
    """
    Attack a target. Will keep attacking the target until
    combat ends or another combat action is taken.

    Usage:
        attack/hit <target>

    """

    key = "attack"
    aliases = ["hit"]
    help_category = "combat"

    def func(self):
        target = self.caller.search(self.lhs)
        if not target:
            return

        combathandler = self.get_or_create_combathandler(target)
        # we use a fixed dt of 3 here, to mimic Diku style; one could also picture
        # attacking at a different rate, depending on skills/weapon etc.
        combathandler.queue_action({"key": "attack", "target": target, "dt": 3, "repeat": True})
        combathandler.msg(f"$You() $conj(attack) $You({target.key})!", self.caller)


class CmdLook(default_cmds.CmdLook, _BaseTwitchCombatCommand):
    def func(self):
        # get regular look, followed by a combat summary
        super().func()
        if not self.args:
            combathandler = self.get_or_create_combathandler()
            txt = str(combathandler.get_combat_summary(self.caller))
            maxwidth = max(display_len(line) for line in txt.strip().split("\n"))
            self.msg(f"|r{pad(' Combat Status ', width=maxwidth, fillchar='-')}|n\n{txt}")


class CmdHold(_BaseTwitchCombatCommand):
    """
    Hold back your blows, doing nothing.

    Usage:
        hold

    """

    key = "hold"

    def func(self):
        combathandler = self.get_or_create_combathandler()
        combathandler.queue_action({"key": "hold"})
        combathandler.msg("$You() $conj(hold) back, doing nothing.", self.caller)


class CmdStunt(_BaseTwitchCombatCommand):
    """
    Perform a combat stunt, that boosts an ally against a target, or
    foils an enemy, giving them disadvantage against an ally.

    Usage:
        boost [ability] <recipient> <target>
        foil [ability] <recipient> <target>
        boost [ability] <target>       (same as boost me <target>)
        foil [ability] <target>        (same as foil <target> me)

    Example:
        boost STR me Goblin
        boost DEX Goblin
        foil STR Goblin me
        foil INT Goblin
        boost INT Wizard Goblin

    """

    key = "stunt"
    aliases = (
        "boost",
        "foil",
    )
    help_category = "combat"

    def parse(self):
        args = self.args

        if not args or " " not in args:
            self.msg("Usage: <ability> <recipient> <target>")
            raise InterruptCommand()

        advantage = self.cmdname != "foil"

        # extract data from the input

        stunt_type, recipient, target = None, None, None

        stunt_type, *args = args.split(None, 1)
        if stunt_type:
            stunt_type = stunt_type.strip().lower()

        args = args[0] if args else ""

        recipient, *args = args.split(None, 1)
        target = args[0] if args else None

        # validate input and try to guess if not given

        # ability is requried
        if not stunt_type or stunt_type not in ABILITY_REVERSE_MAP:
            self.msg(
                f"'{stunt_type}' is not a valid ability. Pick one of"
                f" {', '.join(ABILITY_REVERSE_MAP.keys())}."
            )
            raise InterruptCommand()

        if not recipient:
            self.msg("Must give at least a recipient or target.")
            raise InterruptCommand()

        if not target:
            # something like `boost str target`
            target = recipient if advantage else "me"
            recipient = "me" if advantage else recipient

        # if we still have None:s at this point, we can't continue
        if None in (stunt_type, recipient, target):
            self.msg("Both ability, recipient and  target of stunt must be given.")
            raise InterruptCommand()

        # save what we found so it can be accessed from func()
        self.advantage = advantage
        self.stunt_type = ABILITY_REVERSE_MAP[stunt_type]
        self.recipient = recipient.strip()
        self.target = target.strip()

    def func(self):
        target = self.caller.search(self.target)
        if not target:
            return
        recipient = self.caller.search(self.recipient)
        if not recipient:
            return

        combathandler = self.get_or_create_combathandler(target)

        combathandler.queue_action(
            {
                "key": "stunt",
                "recipient": recipient,
                "target": target,
                "advantage": self.advantage,
                "stunt_type": self.stunt_type,
                "defense_type": self.stunt_type,
                "dt": 3,
            },
        )
        combathandler.msg("$You() prepare a stunt!", self.caller)


class CmdUseItem(_BaseTwitchCombatCommand):
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

        if not self.args:
            self.msg("What do you want to use?")
            raise InterruptCommand()

        self.item = self.lhs
        self.target = self.rhs or "me"

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

        combathandler = self.get_or_create_combathandler(target)
        combathandler.queue_action({"key": "use", "item": item, "target": target, "dt": 3})
        combathandler.msg(
            f"$You() prepare to use {item.get_display_name(self.caller)}!", self.caller
        )


class CmdWield(_BaseTwitchCombatCommand):
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

    def parse(self):
        if not self.args:
            self.msg("What do you want to wield?")
            raise InterruptCommand()
        super().parse()

    def func(self):
        item = self.caller.search(
            self.args, candidates=self.caller.equipment.get_wieldable_objects_from_backpack()
        )
        if not item:
            self.msg("(You must carry the item to wield it.)")
            return
        combathandler = self.get_or_create_combathandler()
        combathandler.queue_action({"key": "wield", "item": item, "dt": 3})
        combathandler.msg(f"$You() reach for {item.get_display_name(self.caller)}!", self.caller)


class TwitchCombatCmdSet(CmdSet):
    """
    Add to character, to be able to attack others in a twitch-style way.
    """

    key = "twitch_combat_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdAttack())
        self.add(CmdHold())
        self.add(CmdStunt())
        self.add(CmdUseItem())
        self.add(CmdWield())


class TwitchLookCmdSet(CmdSet):
    """
    This will be added/removed dynamically when in combat.
    """

    key = "twitch_look_cmdset"

    def at_cmdset_creation(self):
        self.add(CmdLook())
