"""
EvAdventure Twitch-based combat

This implements a 'twitch' (aka DIKU or other traditional muds) style of MUD combat.

"""
from evennia import AttributeProperty, CmdSet, default_cmds
from evennia.commands.command import Command, InterruptCommand
from evennia.utils.utils import display_len, inherits_from, list_to_string, pad, repeat, unrepeat

from .characters import EvAdventureCharacter
from .combat_base import (
    CombatActionAttack,
    CombatActionHold,
    CombatActionStunt,
    CombatActionUseItem,
    CombatActionWield,
    EvAdventureCombatHandlerBase,
)
from .enums import ABILITY_REVERSE_MAP


class EvAdventureCombatTwitchHandler(EvAdventureCombatHandlerBase):
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

    advantages_against = AttributeProperty(dict)
    disadvantages_against = AttributeProperty(dict)

    action_dict = AttributeProperty(dict)
    fallback_action_dict = AttributeProperty({"key": "hold", "dt": 0})

    # stores the current ticker reference, so we can manipulate it later
    current_ticker_ref = AttributeProperty(None)

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

        if self.obj.location.allow_pvp:
            # in pvp, everyone else is an enemy
            allies = [combatant]
            enemies = [comb for comb in combatants if comb != combatant]
        else:
            # otherwise, enemies/allies depend on who combatant is
            pcs = [comb for comb in combatants if inherits_from(comb, EvAdventureCharacter)]
            npcs = [comb for comb in combatants if comb not in pcs]
            if combatant in pcs:
                # combatant is a PC, so NPCs are all enemies
                allies = [comb for comb in pcs if comb != combatant]
                enemies = npcs
            else:
                # combatant is an NPC, so PCs are all enemies
                allies = [comb for comb in npcs if comb != combatant]
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
        self.advantages_against[target] = True

    def give_disadvantage(self, recipient, target):
        """
        Let an affected party gain disadvantage against a target.

        Args:
            recipient (Character or NPC): The one to get the disadvantage.
            target (Character or NPC): The one against which the target gains disadvantage, usually
                an enemy.

        """
        self.disadvantages_against[target] = True

    def has_advantage(self, combatant, target):
        """
        Check if a given combatant has advantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have advantage
            target (Character or NPC): The target to check advantage against.

        """
        return self.advantages_against.get(target, False)

    def has_disadvantage(self, combatant, target):
        """
        Check if a given combatant has disadvantage against a target.

        Args:
            combatant (Character or NPC): The one to check if they have disadvantage
            target (Character or NPC): The target to check disadvantage against.

        """
        return self.disadvantages_against.get(target, False)

    def queue_action(self, action_dict):
        """
        Schedule the next action to fire.

        Args:
            action_dict (dict): The new action-dict to initialize.

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

    def check_stop_combat(self):
        # check if one side won the battle.

        allies, enemies = self.get_sides()
        allies.append(self.obj)

        # remove all dead combatants
        allies = [comb for comb in allies if comb.hp > 0]
        enemies = [comb for comb in enemies if comb.hp > 0]

        if not allies and not enemies:
            self.msg("Noone stands after the dust settles.")
            self.stop_combat()
            return

        if not allies or not enemies:
            still_standing = list_to_string(
                f"$You({comb.key})" for comb in allies + enemies if comb.hp > 0
            )
            self.msg(f"The combat is over. {still_standing} are still standing.")
            self.stop_combat()

    def stop_combat(self):
        """
        Stop combat immediately.
        """
        self.queue_action({"key": "hold", "dt": 0})  # make sure ticker is killed
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
        Handle parsing of all supported combat syntaxes.

        <action> [<target>|<item>]
        or
        <action> <item> [on] <target>

        Use 'on' to differentiate if names/items have spaces in the name.

        """
        args = self.args.strip()

        if " on " in args:
            lhs, rhs = args.split(" on ", 1)
        else:
            lhs, *rhs = args.split(None, 1)
            rhs = " ".join(rhs)
        self.lhs, self.rhs = lhs.strip(), rhs.strip()

    def get_or_create_combathandler(self, combathandler_name="combathandler"):
        """
        Get or create the combathandler assigned to this combatant.

        """
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
        target = self.search(self.lhs)
        if not target:
            return

        combathandler = self.get_or_create_combathandler()
        # we use a fixed dt of 3 here, to mimic Diku style; one could also picture
        # attacking at a different rate, depending on skills/weapon etc.
        combathandler.queue_action({"key": "attack", "target": target, "dt": 3})
        combathandler.msg("$You() attacks $You(target.key)!", self.caller)


class CmdLook(default_cmds.CmdLook):
    def func(self):
        # get regular look, followed by a combat summary
        super().func()
        if not self.args:
            combathandler = self.get_or_create_combathandler(self.caller.location)
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
        super().parse()
        args = self.args

        if not args or " " not in args:
            self.msg("Usage: <ability> <recipient> <target>")
            raise InterruptCommand()

        advantage = self.cmdname != "foil"

        # extract data from the input

        stunt_type, recipient, target = None, None, None

        stunt_type, *args = args.split(None, 1)
        args = args[0] if args else ""

        recipient, *args = args.split(None, 1)
        target = args[0] if args else None

        # validate input and try to guess if not given

        # ability is requried
        if stunt_type.strip() not in ABILITY_REVERSE_MAP:
            self.msg("That's not a valid ability.")
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
        self.stunt_type = ABILITY_REVERSE_MAP[stunt_type.strip()]
        self.recipient = recipient.strip()
        self.target = target.strip()

    def func(self):
        combathandler = self.get_or_create_combathandler()

        target = self.caller.search(self.target, candidates=combathandler.combatants.keys())
        if not target:
            return
        recipient = self.caller.search(self.recipient, candidates=combathandler.combatants.keys())
        if not recipient:
            return

        combathandler.queue_action(
            self.caller,
            {
                "key": "stunt",
                "recipient": recipient,
                "target": target,
                "advantage": self.advantage,
                "stunt_type": self.stunt_type,
                "defense_type": self.stunt_type,
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
        args = self.args

        if not args:
            self.msg("What do you want to use?")
            raise InterruptCommand()
        elif "on" in args:
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

        combathandler = self.get_or_create_combathandler()
        combathandler.queue_action(self.caller, {"key": "use", "item": item, "target": self.target})
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
        combathandler.queue_action(self.caller, {"key": "wield", "item": item})
        combathandler.msg(
            f"$You() start wielding {item.get_display_name(self.caller)}!", self.caller
        )


class TwitchAttackCmdSet(CmdSet):
    """
    Add to character, to be able to attack others in a twitch-style way.
    """

    def at_cmdset_creation(self):
        self.add(CmdAttack())
        self.add(CmdLook())
        self.add(CmdHold())
        self.add(CmdStunt())
        self.add(CmdUseItem())
        self.add(CmdWield())
