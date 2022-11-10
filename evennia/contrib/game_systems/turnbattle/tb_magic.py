"""
Simple turn-based combat system with spell casting

Contrib - Tim Ashley Jenkins 2017, Refactor by Griatch, 2022

This is a version of the 'turnbattle' contrib that includes a basic,
expandable framework for a 'magic system', whereby players can spend
a limited resource (MP) to achieve a wide variety of effects, both in
and out of combat. This does not have to strictly be a system for
magic - it can easily be re-flavored to any other sort of resource
based mechanic, like psionic powers, special moves and stamina, and
so forth.

In this system, spells are learned by name with the 'learnspell'
command, and then used with the 'cast' command. Spells can be cast in or
out of combat - some spells can only be cast in combat, some can only be
cast outside of combat, and some can be cast any time. However, if you
are in combat, you can only cast a spell on your turn, and doing so will
typically use an action (as specified in the spell's funciton).

Spells are defined at the end of the module in a database that's a
dictionary of dictionaries - each spell is matched by name to a function,
along with various parameters that restrict when the spell can be used and
what the spell can be cast on. Included is a small variety of spells that
damage opponents and heal HP, as well as one that creates an object.

Because a spell can call any function, a spell can be made to do just
about anything at all. The SPELLS dictionary at the bottom of the module
even allows kwargs to be passed to the spell function, so that the same
function can be re-used for multiple similar spells.

Spells in this system work on a very basic resource: MP, which is spent
when casting spells and restored by resting. It shouldn't be too difficult
to modify this system to use spell slots, some physical fuel or resource,
or whatever else your game requires.

To install and test, import this module's TBMagicCharacter object into
your game's character.py module:

    from evennia.contrib.game_systems.turnbattle.tb_magic import TBMagicCharacter

And change your game's character typeclass to inherit from TBMagicCharacter
instead of the default:

    class Character(TBMagicCharacter):

Note: If your character already existed you need to also make sure
to re-run the creation hooks on it to set the needed Attributes.
Use `update self` to try on yourself or use py to call `at_object_creation()`
on all existing Characters.


Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.game_systems.turnbattle import tb_magic

And add the battle command set to your default command set:

    #
    # any commands you add below will overload the default ones.
    #
    self.add(tb_magic.BattleCmdSet())

This module is meant to be heavily expanded on, so you may want to copy it
to your game's 'world' folder and modify it there rather than importing it
in your game and using it as-is.
"""

from random import randint

from evennia import Command, DefaultScript, create_object, default_cmds
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.logger import log_trace

from . import tb_basic

"""
----------------------------------------------------------------------------
SPELL FUNCTIONS START HERE
----------------------------------------------------------------------------

These are the functions that are called by the 'cast' command to perform the
effects of various spells. Which spells execute which functions and what
parameters are passed to them are specified at the bottom of the module, in
the 'SPELLS' dictionary.

All of these functions take the same arguments:
    caster (obj): Character casting the spell
    spell_name (str): Name of the spell being cast
    targets (list): List of objects targeted by the spell
    cost (int): MP cost of casting the spell

These functions also all accept **kwargs, and how these are used is specified
in the docstring for each function.
"""


class MagicCombatRules(tb_basic.BasicCombatRules):
    def spell_healing(self, caster, spell_name, targets, cost, **kwargs):
        """
        Spell that restores HP to a target or targets.

        kwargs:
            healing_range (tuple): Minimum and maximum amount healed to
                each target. (20, 40) by default.
        """
        spell_msg = "%s casts %s!" % (caster, spell_name)

        min_healing = 20
        max_healing = 40

        # Retrieve healing range from kwargs, if present
        if "healing_range" in kwargs:
            min_healing = kwargs["healing_range"][0]
            max_healing = kwargs["healing_range"][1]

        for character in targets:
            to_heal = randint(min_healing, max_healing)  # Restore 20 to 40 hp
            if character.db.hp + to_heal > character.db.max_hp:
                to_heal = character.db.max_hp - character.db.hp  # Cap healing to max HP
            character.db.hp += to_heal
            spell_msg += " %s regains %i HP!" % (character, to_heal)

        caster.db.mp -= cost  # Deduct MP cost

        caster.location.msg_contents(spell_msg)  # Message the room with spell results

        if self.is_in_combat(caster):  # Spend action if in combat
            self.spend_action(caster, 1, action_name="cast")

    def spell_attack(self, caster, spell_name, targets, cost, **kwargs):
        """
        Spell that deals damage in combat. Similar to resolve_attack.

        kwargs:
            attack_name (tuple): Single and plural describing the sort of
                attack or projectile that strikes each enemy.
            damage_range (tuple): Minimum and maximum damage dealt by the
                spell. (10, 20) by default.
            accuracy (int): Modifier to the spell's attack roll, determining
                an increased or decreased chance to hit. 0 by default.
            attack_count (int): How many individual attacks are made as part
                of the spell. If the number of attacks exceeds the number of
                targets, the first target specified will be attacked more
                than once. Just 1 by default - if the attack_count is less
                than the number targets given, each target will only be
                attacked once.
        """
        spell_msg = "%s casts %s!" % (caster, spell_name)

        atkname_single = "The spell"
        atkname_plural = "spells"
        min_damage = 10
        max_damage = 20
        accuracy = 0
        attack_count = 1

        # Retrieve some variables from kwargs, if present
        if "attack_name" in kwargs:
            atkname_single = kwargs["attack_name"][0]
            atkname_plural = kwargs["attack_name"][1]
        if "damage_range" in kwargs:
            min_damage = kwargs["damage_range"][0]
            max_damage = kwargs["damage_range"][1]
        if "accuracy" in kwargs:
            accuracy = kwargs["accuracy"]
        if "attack_count" in kwargs:
            attack_count = kwargs["attack_count"]

        to_attack = []
        # If there are more attacks than targets given, attack first target multiple times
        if len(targets) < attack_count:
            to_attack = to_attack + targets
            extra_attacks = attack_count - len(targets)
            for n in range(extra_attacks):
                to_attack.insert(0, targets[0])
        else:
            to_attack = to_attack + targets

        # Set up dictionaries to track number of hits and total damage
        total_hits = {}
        total_damage = {}
        for fighter in targets:
            total_hits.update({fighter: 0})
            total_damage.update({fighter: 0})

        # Resolve attack for each target
        for fighter in to_attack:
            attack_value = randint(1, 100) + accuracy  # Spell attack roll
            defense_value = self.get_defense(caster, fighter)
            if attack_value >= defense_value:
                spell_dmg = randint(min_damage, max_damage)  # Get spell damage
                total_hits[fighter] += 1
                total_damage[fighter] += spell_dmg

        for fighter in targets:
            # Construct combat message
            if total_hits[fighter] == 0:
                spell_msg += " The spell misses %s!" % fighter
            elif total_hits[fighter] > 0:
                attack_count_str = atkname_single + " hits"
                if total_hits[fighter] > 1:
                    attack_count_str = "%i %s hit" % (total_hits[fighter], atkname_plural)
                spell_msg += " %s %s for %i damage!" % (
                    attack_count_str,
                    fighter,
                    total_damage[fighter],
                )

        caster.db.mp -= cost  # Deduct MP cost

        caster.location.msg_contents(spell_msg)  # Message the room with spell results

        for fighter in targets:
            # Apply damage
            self.apply_damage(fighter, total_damage[fighter])
            # If fighter HP is reduced to 0 or less, call at_defeat.
            if fighter.db.hp <= 0:
                self.at_defeat(fighter)

        if self.is_in_combat(caster):  # Spend action if in combat
            self.spend_action(caster, 1, action_name="cast")

    def spell_conjure(self, caster, spell_name, targets, cost, **kwargs):
        """
        Spell that creates an object.

        kwargs:
            obj_key (str): Key of the created object.
            obj_desc (str): Desc of the created object.
            obj_typeclass (str): Typeclass path of the object.

        If you want to make more use of this particular spell funciton,
        you may want to modify it to use the spawner (in evennia.utils.spawner)
        instead of creating objects directly.
        """

        obj_key = "a nondescript object"
        obj_desc = "A perfectly generic object."
        obj_typeclass = "evennia.objects.objects.DefaultObject"

        # Retrieve some variables from kwargs, if present
        if "obj_key" in kwargs:
            obj_key = kwargs["obj_key"]
        if "obj_desc" in kwargs:
            obj_desc = kwargs["obj_desc"]
        if "obj_typeclass" in kwargs:
            obj_typeclass = kwargs["obj_typeclass"]

        conjured_obj = create_object(
            obj_typeclass, key=obj_key, location=caster.location
        )  # Create object
        conjured_obj.db.desc = obj_desc  # Add object desc

        caster.db.mp -= cost  # Deduct MP cost

        # Message the room to announce the creation of the object
        caster.location.msg_contents(
            "%s casts %s, and %s appears!" % (caster, spell_name, conjured_obj)
        )


COMBAT_RULES = MagicCombatRules()


"""
----------------------------------------------------------------------------
SPELL DEFINITIONS START HERE
----------------------------------------------------------------------------
In this section, each spell is matched to a function, and given parameters
that determine its MP cost, valid type and number of targets, and what
function casting the spell executes.

This data is given as a dictionary of dictionaries - the key of each entry
is the spell's name, and the value is a dictionary of various options and
parameters, some of which are required and others which are optional.

Required values for spells:

    cost (int): MP cost of casting the spell
    target (str): Valid targets for the spell. Can be any of:
        "none" - No target needed
        "self" - Self only
        "any" - Any object
        "anyobj" - Any object that isn't a character
        "anychar" - Any character
        "other" - Any object excluding the caster
        "otherchar" - Any character excluding the caster
    spellfunc (callable): Function that performs the action of the spell.
        Must take the following arguments: caster (obj), spell_name (str),
        targets (list), and cost (int), as well as **kwargs.

Optional values for spells:

    combat_spell (bool): If the spell can be cast in combat. True by default.
    noncombat_spell (bool): If the spell can be cast out of combat. True by default.
    max_targets (int): Maximum number of objects that can be targeted by the spell.
        1 by default - unused if target is "none" or "self"

Any other values specified besides the above will be passed as kwargs to 'spellfunc'.
You can use kwargs to effectively re-use the same function for different but similar
spells - for example, 'magic missile' and 'flame shot' use the same function, but
behave differently, as they have different damage ranges, accuracy, amount of attacks
made as part of the spell, and so forth. If you make your spell functions flexible
enough, you can make a wide variety of spells just by adding more entries to this
dictionary.
"""

SPELLS = {
    "magic missile": {
        "spellfunc": COMBAT_RULES.spell_attack,
        "target": "otherchar",
        "cost": 3,
        "noncombat_spell": False,
        "max_targets": 3,
        "attack_name": ("A bolt", "bolts"),
        "damage_range": (4, 7),
        "accuracy": 999,
        "attack_count": 3,
    },
    "flame shot": {
        "spellfunc": COMBAT_RULES.spell_attack,
        "target": "otherchar",
        "cost": 3,
        "noncombat_spell": False,
        "attack_name": ("A jet of flame", "jets of flame"),
        "damage_range": (25, 35),
    },
    "cure wounds": {"spellfunc": COMBAT_RULES.spell_healing, "target": "anychar", "cost": 5},
    "mass cure wounds": {
        "spellfunc": COMBAT_RULES.spell_healing,
        "target": "anychar",
        "cost": 10,
        "max_targets": 5,
    },
    "full heal": {
        "spellfunc": COMBAT_RULES.spell_healing,
        "target": "anychar",
        "cost": 12,
        "healing_range": (100, 100),
    },
    "cactus conjuration": {
        "spellfunc": COMBAT_RULES.spell_conjure,
        "target": "none",
        "cost": 2,
        "combat_spell": False,
        "obj_key": "a cactus",
        "obj_desc": "An ordinary green cactus with little spines.",
    },
}


"""
----------------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------------
"""

TURN_TIMEOUT = 30  # Time before turns automatically end, in seconds
ACTIONS_PER_TURN = 1  # Number of actions allowed per turn


"""
----------------------------------------------------------------------------
CHARACTER TYPECLASS
----------------------------------------------------------------------------
"""


class TBMagicCharacter(tb_basic.TBBasicCharacter):
    """
    A character able to participate in turn-based combat. Has attributes for current
    and maximum HP, access to combat commands and magic.

    """

    rules = COMBAT_RULES

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.

        Adds attributes for a character's current and maximum HP.
        We're just going to set this value at '100' by default.

        You may want to expand this to include various 'stats' that
        can be changed at creation and factor into combat calculations.
        """
        self.db.max_hp = 100  # Set maximum HP to 100
        self.db.hp = self.db.max_hp  # Set current HP to maximum
        self.db.spells_known = []  # Set empty spells known list
        self.db.max_mp = 20  # Set maximum MP to 20
        self.db.mp = self.db.max_mp  # Set current MP to maximum


"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBMagicTurnHandler(tb_basic.TBBasicTurnHandler):
    """
    This is the script that handles the progression of combat through turns.
    On creation (when a fight is started) it adds all combat-ready characters
    to its roster and then sorts them into a turn order. There can only be one
    fight going on in a single room at a time, so the script is assigned to a
    room as its object.

    Fights persist until only one participant is left with any HP or all
    remaining participants choose to end the combat with the 'disengage' command.
    """

    rules = COMBAT_RULES


"""
----------------------------------------------------------------------------
COMMANDS START HERE
----------------------------------------------------------------------------
"""


class CmdFight(tb_basic.CmdFight):
    """
    Starts a fight with everyone in the same room as you.

    Usage:
      fight

    When you start a fight, everyone in the room who is able to
    fight is added to combat, and a turn order is randomly rolled.
    When it's your turn, you can attack other characters.
    """

    key = "fight"
    help_category = "combat"

    rules = COMBAT_RULES
    combat_handler_class = TBMagicTurnHandler


class CmdAttack(tb_basic.CmdAttack):
    """
    Attacks another character.

    Usage:
      attack <target>

    When in a fight, you may attack another character. The attack has
    a chance to hit, and if successful, will deal damage.
    """

    key = "attack"
    help_category = "combat"

    rules = COMBAT_RULES


class CmdPass(tb_basic.CmdPass):
    """
    Passes on your turn.

    Usage:
      pass

    When in a fight, you can use this command to end your turn early, even
    if there are still any actions you can take.
    """

    key = "pass"
    aliases = ["wait", "hold"]
    help_category = "combat"

    rules = COMBAT_RULES


class CmdDisengage(tb_basic.CmdDisengage):
    """
    Passes your turn and attempts to end combat.

    Usage:
      disengage

    Ends your turn early and signals that you're trying to end
    the fight. If all participants in a fight disengage, the
    fight ends.
    """

    key = "disengage"
    aliases = ["spare"]
    help_category = "combat"

    rules = COMBAT_RULES


class CmdLearnSpell(Command):
    """
    Learn a magic spell.

    Usage:
        learnspell <spell name>

    Adds a spell by name to your list of spells known.

    The following spells are provided as examples:

        |wmagic missile|n (3 MP): Fires three missiles that never miss. Can target
            up to three different enemies.

        |wflame shot|n (3 MP): Shoots a high-damage jet of flame at one target.

        |wcure wounds|n (5 MP): Heals damage on one target.

        |wmass cure wounds|n (10 MP): Like 'cure wounds', but can heal up to 5
            targets at once.

        |wfull heal|n (12 MP): Heals one target back to full HP.

        |wcactus conjuration|n (2 MP): Creates a cactus.
    """

    key = "learnspell"
    help_category = "magic"

    def func(self):
        """
        This performs the actual command.
        """
        spell_list = sorted(SPELLS.keys())
        args = self.args.lower()
        args = args.strip(" ")
        caller = self.caller
        spell_to_learn = []

        if not args or len(args) < 3:  # No spell given
            caller.msg("Usage: learnspell <spell name>")
            return

        for spell in spell_list:  # Match inputs to spells
            if args in spell.lower():
                spell_to_learn.append(spell)

        if spell_to_learn == []:  # No spells matched
            caller.msg("There is no spell with that name.")
            return
        if len(spell_to_learn) > 1:  # More than one match
            matched_spells = ", ".join(spell_to_learn)
            caller.msg("Which spell do you mean: %s?" % matched_spells)
            return

        if len(spell_to_learn) == 1:  # If one match, extract the string
            spell_to_learn = spell_to_learn[0]

        if spell_to_learn not in self.caller.db.spells_known:  # If the spell isn't known...
            caller.db.spells_known.append(spell_to_learn)  # ...then add the spell to the character
            caller.msg("You learn the spell '%s'!" % spell_to_learn)
            return
        if spell_to_learn in self.caller.db.spells_known:  # Already has the spell specified
            caller.msg("You already know the spell '%s'!" % spell_to_learn)
        """
        You will almost definitely want to replace this with your own system
        for learning spells, perhaps tied to character advancement or finding
        items in the game world that spells can be learned from.
        """


class CmdCast(MuxCommand):
    """
    Cast a magic spell that you know, provided you have the MP
    to spend on its casting.

    Usage:
        cast <spellname> [= <target1>, <target2>, etc...]

    Some spells can be cast on multiple targets, some can be cast
    on only yourself, and some don't need a target specified at all.
    Typing 'cast' by itself will give you a list of spells you know.
    """

    key = "cast"
    help_category = "magic"

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.

        Note: This is a quite long command, since it has to cope with all
        the different circumstances in which you may or may not be able
        to cast a spell. None of the spell's effects are handled by the
        command - all the command does is verify that the player's input
        is valid for the spell being cast and then call the spell's
        function.
        """
        caller = self.caller

        if not self.lhs or len(self.lhs) < 3:  # No spell name given
            caller.msg("Usage: cast <spell name> = <target>, <target2>, ...")
            if not caller.db.spells_known:
                caller.msg("You don't know any spells.")
                return
            else:
                caller.db.spells_known = sorted(caller.db.spells_known)
                spells_known_msg = "You know the following spells:|/" + "|/".join(
                    caller.db.spells_known
                )
                caller.msg(spells_known_msg)  # List the spells the player knows
                return

        spellname = self.lhs.lower()  # noqa  - not used but potentially useful
        spell_to_cast = []
        spell_targets = []

        if not self.rhs:
            spell_targets = []
        elif self.rhs.lower() in ["me", "self", "myself"]:
            spell_targets = [caller]
        elif len(self.rhs) > 2:
            spell_targets = self.rhslist

        for spell in caller.db.spells_known:  # Match inputs to spells
            if self.lhs in spell.lower():
                spell_to_cast.append(spell)

        if spell_to_cast == []:  # No spells matched
            caller.msg("You don't know a spell of that name.")
            return
        if len(spell_to_cast) > 1:  # More than one match
            matched_spells = ", ".join(spell_to_cast)
            caller.msg("Which spell do you mean: %s?" % matched_spells)
            return

        if len(spell_to_cast) == 1:  # If one match, extract the string
            spell_to_cast = spell_to_cast[0]

        if spell_to_cast not in SPELLS:  # Spell isn't defined
            caller.msg("ERROR: Spell %s is undefined" % spell_to_cast)
            return

        # Time to extract some info from the chosen spell!
        spelldata = SPELLS[spell_to_cast]

        # Add in some default data if optional parameters aren't specified
        if "combat_spell" not in spelldata:
            spelldata.update({"combat_spell": True})
        if "noncombat_spell" not in spelldata:
            spelldata.update({"noncombat_spell": True})
        if "max_targets" not in spelldata:
            spelldata.update({"max_targets": 1})

        # Store any superfluous options as kwargs to pass to the spell function
        kwargs = {}
        spelldata_opts = [
            "spellfunc",
            "target",
            "cost",
            "combat_spell",
            "noncombat_spell",
            "max_targets",
        ]
        for key in spelldata:
            if key not in spelldata_opts:
                kwargs.update({key: spelldata[key]})

        # If caster doesn't have enough MP to cover the spell's cost, give error and return
        if spelldata["cost"] > caller.db.mp:
            caller.msg("You don't have enough MP to cast '%s'." % spell_to_cast)
            return

        # If in combat and the spell isn't a combat spell, give error message and return
        if spelldata["combat_spell"] is False and self.rules.is_in_combat(caller):
            caller.msg("You can't use the spell '%s' in combat." % spell_to_cast)
            return

        # If not in combat and the spell isn't a non-combat spell, error ms and return.
        if spelldata["noncombat_spell"] is False and self.rules.is_in_combat(caller) is False:
            caller.msg("You can't use the spell '%s' outside of combat." % spell_to_cast)
            return

        # If spell takes no targets and one is given, give error message and return
        if len(spell_targets) > 0 and spelldata["target"] == "none":
            caller.msg("The spell '%s' isn't cast on a target." % spell_to_cast)
            return

        # If no target is given and spell requires a target, give error message
        if spelldata["target"] not in ["self", "none"]:
            if len(spell_targets) == 0:
                caller.msg("The spell '%s' requires a target." % spell_to_cast)
                return

        # If more targets given than maximum, give error message
        if len(spell_targets) > spelldata["max_targets"]:
            targplural = "target"
            if spelldata["max_targets"] > 1:
                targplural = "targets"
            caller.msg(
                "The spell '%s' can only be cast on %i %s."
                % (spell_to_cast, spelldata["max_targets"], targplural)
            )
            return

        # Set up our candidates for targets
        target_candidates = []

        # If spell targets 'any' or 'other', any object in caster's inventory or location
        # can be targeted by the spell.
        if spelldata["target"] in ["any", "other"]:
            target_candidates = caller.location.contents + caller.contents

        # If spell targets 'anyobj', only non-character objects can be targeted.
        if spelldata["target"] == "anyobj":
            prefilter_candidates = caller.location.contents + caller.contents
            for thing in prefilter_candidates:
                if not thing.attributes.has("max_hp"):  # Has no max HP, isn't a fighter
                    target_candidates.append(thing)

        # If spell targets 'anychar' or 'otherchar', only characters can be targeted.
        if spelldata["target"] in ["anychar", "otherchar"]:
            prefilter_candidates = caller.location.contents
            for thing in prefilter_candidates:
                if thing.attributes.has("max_hp"):  # Has max HP, is a fighter
                    target_candidates.append(thing)

        # Now, match each entry in spell_targets to an object in the search candidates
        matched_targets = []
        for target in spell_targets:
            match = caller.search(target, candidates=target_candidates)
            matched_targets.append(match)
        spell_targets = matched_targets

        # If no target is given and the spell's target is 'self', set target to self
        if len(spell_targets) == 0 and spelldata["target"] == "self":
            spell_targets = [caller]

        # Give error message if trying to cast an "other" target spell on yourself
        if spelldata["target"] in ["other", "otherchar"]:
            if caller in spell_targets:
                caller.msg("You can't cast '%s' on yourself." % spell_to_cast)
                return

        # Return if "None" in target list, indicating failed match
        if None in spell_targets:
            # No need to give an error message, as 'search' gives one by default.
            return

        # Give error message if repeats in target list
        if len(spell_targets) != len(set(spell_targets)):
            caller.msg("You can't specify the same target more than once!")
            return

        # Finally, we can cast the spell itself. Note that MP is not deducted here!
        try:
            spelldata["spellfunc"](
                caller, spell_to_cast, spell_targets, spelldata["cost"], **kwargs
            )
        except Exception:
            log_trace("Error in callback for spell: %s." % spell_to_cast)


class CmdRest(Command):
    """
    Recovers damage and restores MP.

    Usage:
      rest

    Resting recovers your HP and MP to their maximum, but you can
    only rest if you're not in a fight.
    """

    key = "rest"
    help_category = "combat"

    rules = COMBAT_RULES

    def func(self):
        "This performs the actual command."

        if self.rules.is_in_combat(self.caller):  # If you're in combat
            self.caller.msg("You can't rest while you're in combat.")
            return

        self.caller.db.hp = self.caller.db.max_hp  # Set current HP to maximum
        self.caller.db.mp = self.caller.db.max_mp  # Set current MP to maximum
        self.caller.location.msg_contents("%s rests to recover HP and MP." % self.caller)
        # You'll probably want to replace this with your own system for recovering HP and MP.


class CmdStatus(Command):
    """
    Gives combat information.

    Usage:
      status

    Shows your current and maximum HP and your distance from
    other targets in combat.
    """

    key = "status"
    help_category = "combat"

    def func(self):
        "This performs the actual command."
        char = self.caller

        if not char.db.max_hp:  # Character not initialized, IE in unit tests
            char.db.hp = 100
            char.db.max_hp = 100
            char.db.spells_known = []
            char.db.max_mp = 20
            char.db.mp = char.db.max_mp

        char.msg(
            "You have %i / %i HP and %i / %i MP."
            % (char.db.hp, char.db.max_hp, char.db.mp, char.db.max_mp)
        )


class CmdCombatHelp(tb_basic.CmdCombatHelp):
    """
    View help or a list of topics

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game.
    """


class BattleCmdSet(default_cmds.CharacterCmdSet):
    """
    This command set includes all the commmands used in the battle system.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        self.add(CmdFight())
        self.add(CmdAttack())
        self.add(CmdRest())
        self.add(CmdPass())
        self.add(CmdDisengage())
        self.add(CmdCombatHelp())
        self.add(CmdLearnSpell())
        self.add(CmdCast())
        self.add(CmdStatus())
