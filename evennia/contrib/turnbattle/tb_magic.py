"""
Simple turn-based combat system with spell casting

Contrib - Tim Ashley Jenkins 2017

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

    from evennia.contrib.turnbattle.tb_magic import TBMagicCharacter

And change your game's character typeclass to inherit from TBMagicCharacter
instead of the default:

    class Character(TBMagicCharacter):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.turnbattle import tb_magic

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
from evennia import DefaultCharacter, Command, default_cmds, DefaultScript, create_object
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.default.help import CmdHelp

"""
----------------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------------
"""

TURN_TIMEOUT = 30  # Time before turns automatically end, in seconds
ACTIONS_PER_TURN = 1  # Number of actions allowed per turn

"""
----------------------------------------------------------------------------
COMBAT FUNCTIONS START HERE
----------------------------------------------------------------------------
"""


def roll_init(character):
    """
    Rolls a number between 1-1000 to determine initiative.

    Args:
        character (obj): The character to determine initiative for

    Returns:
        initiative (int): The character's place in initiative - higher
        numbers go first.

    Notes:
        By default, does not reference the character and simply returns
        a random integer from 1 to 1000.

        Since the character is passed to this function, you can easily reference
        a character's stats to determine an initiative roll - for example, if your
        character has a 'dexterity' attribute, you can use it to give that character
        an advantage in turn order, like so:

        return (randint(1,20)) + character.db.dexterity

        This way, characters with a higher dexterity will go first more often.
    """
    return randint(1, 1000)


def get_attack(attacker, defender):
    """
    Returns a value for an attack roll.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Returns:
        attack_value (int): Attack roll value, compared against a defense value
            to determine whether an attack hits or misses.

    Notes:
        By default, returns a random integer from 1 to 100 without using any
        properties from either the attacker or defender.

        This can easily be expanded to return a value based on characters stats,
        equipment, and abilities. This is why the attacker and defender are passed
        to this function, even though nothing from either one are used in this example.
    """
    # For this example, just return a random integer up to 100.
    attack_value = randint(1, 100)
    return attack_value


def get_defense(attacker, defender):
    """
    Returns a value for defense, which an attack roll must equal or exceed in order
    for an attack to hit.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Returns:
        defense_value (int): Defense value, compared against an attack roll
            to determine whether an attack hits or misses.

    Notes:
        By default, returns 50, not taking any properties of the defender or
        attacker into account.

        As above, this can be expanded upon based on character stats and equipment.
    """
    # For this example, just return 50, for about a 50/50 chance of hit.
    defense_value = 50
    return defense_value


def get_damage(attacker, defender):
    """
    Returns a value for damage to be deducted from the defender's HP after abilities
    successful hit.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being damaged

    Returns:
        damage_value (int): Damage value, which is to be deducted from the defending
            character's HP.

    Notes:
        By default, returns a random integer from 15 to 25 without using any
        properties from either the attacker or defender.

        Again, this can be expanded upon.
    """
    # For this example, just generate a number between 15 and 25.
    damage_value = randint(15, 25)
    return damage_value


def apply_damage(defender, damage):
    """
    Applies damage to a target, reducing their HP by the damage amount to a
    minimum of 0.

    Args:
        defender (obj): Character taking damage
        damage (int): Amount of damage being taken
    """
    defender.db.hp -= damage  # Reduce defender's HP by the damage dealt.
    # If this reduces it to 0 or less, set HP to 0.
    if defender.db.hp <= 0:
        defender.db.hp = 0


def at_defeat(defeated):
    """
    Announces the defeat of a fighter in combat.
    
    Args:
        defeated (obj): Fighter that's been defeated.
    
    Notes:
        All this does is announce a defeat message by default, but if you
        want anything else to happen to defeated fighters (like putting them
        into a dying state or something similar) then this is the place to
        do it.
    """
    defeated.location.msg_contents("%s has been defeated!" % defeated)


def resolve_attack(attacker, defender, attack_value=None, defense_value=None):
    """
    Resolves an attack and outputs the result.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked

    Notes:
        Even though the attack and defense values are calculated
        extremely simply, they are separated out into their own functions
        so that they are easier to expand upon.
    """
    # Get an attack roll from the attacker.
    if not attack_value:
        attack_value = get_attack(attacker, defender)
    # Get a defense value from the defender.
    if not defense_value:
        defense_value = get_defense(attacker, defender)
    # If the attack value is lower than the defense value, miss. Otherwise, hit.
    if attack_value < defense_value:
        attacker.location.msg_contents("%s's attack misses %s!" % (attacker, defender))
    else:
        damage_value = get_damage(attacker, defender)  # Calculate damage value.
        # Announce damage dealt and apply damage.
        attacker.location.msg_contents(
            "%s hits %s for %i damage!" % (attacker, defender, damage_value)
        )
        apply_damage(defender, damage_value)
        # If defender HP is reduced to 0 or less, call at_defeat.
        if defender.db.hp <= 0:
            at_defeat(defender)


def combat_cleanup(character):
    """
    Cleans up all the temporary combat-related attributes on a character.

    Args:
        character (obj): Character to have their combat attributes removed

    Notes:
        Any attribute whose key begins with 'combat_' is temporary and no
        longer needed once a fight ends.
    """
    for attr in character.attributes.all():
        if attr.key[:7] == "combat_":  # If the attribute name starts with 'combat_'...
            character.attributes.remove(key=attr.key)  # ...then delete it!


def is_in_combat(character):
    """
    Returns true if the given character is in combat.

    Args:
        character (obj): Character to determine if is in combat or not

    Returns:
        (bool): True if in combat or False if not in combat
    """
    return bool(character.db.combat_turnhandler)


def is_turn(character):
    """
    Returns true if it's currently the given character's turn in combat.

    Args:
        character (obj): Character to determine if it is their turn or not

    Returns:
        (bool): True if it is their turn or False otherwise
    """
    turnhandler = character.db.combat_turnhandler
    currentchar = turnhandler.db.fighters[turnhandler.db.turn]
    return bool(character == currentchar)


def spend_action(character, actions, action_name=None):
    """
    Spends a character's available combat actions and checks for end of turn.

    Args:
        character (obj): Character spending the action
        actions (int) or 'all': Number of actions to spend, or 'all' to spend all actions

    Kwargs:
        action_name (str or None): If a string is given, sets character's last action in
        combat to provided string
    """
    if not is_in_combat(character):
        return
    if action_name:
        character.db.combat_lastaction = action_name
    if actions == "all":  # If spending all actions
        character.db.combat_actionsleft = 0  # Set actions to 0
    else:
        character.db.combat_actionsleft -= actions  # Use up actions.
        if character.db.combat_actionsleft < 0:
            character.db.combat_actionsleft = 0  # Can't have fewer than 0 actions
    character.db.combat_turnhandler.turn_end_check(character)  # Signal potential end of turn.


"""
----------------------------------------------------------------------------
CHARACTER TYPECLASS
----------------------------------------------------------------------------
"""


class TBMagicCharacter(DefaultCharacter):
    """
    A character able to participate in turn-based combat. Has attributes for current
    and maximum HP, and access to combat commands.
    """

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

    def at_before_move(self, destination):
        """
        Called just before starting to move this object to
        destination.

        Args:
            destination (Object): The object we are moving to

        Returns:
            shouldmove (bool): If we should move or not.

        Notes:
            If this method returns False/None, the move is cancelled
            before it is even started.

        """
        # Keep the character from moving if at 0 HP or in combat.
        if is_in_combat(self):
            self.msg("You can't exit a room while in combat!")
            return False  # Returning false keeps the character from moving.
        if self.db.HP <= 0:
            self.msg("You can't move, you've been defeated!")
            return False
        return True


"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBMagicTurnHandler(DefaultScript):
    """
    This is the script that handles the progression of combat through turns.
    On creation (when a fight is started) it adds all combat-ready characters
    to its roster and then sorts them into a turn order. There can only be one
    fight going on in a single room at a time, so the script is assigned to a
    room as its object.

    Fights persist until only one participant is left with any HP or all
    remaining participants choose to end the combat with the 'disengage' command.
    """

    def at_script_creation(self):
        """
        Called once, when the script is created.
        """
        self.key = "Combat Turn Handler"
        self.interval = 5  # Once every 5 seconds
        self.persistent = True
        self.db.fighters = []

        # Add all fighters in the room with at least 1 HP to the combat."
        for thing in self.obj.contents:
            if thing.db.hp:
                self.db.fighters.append(thing)

        # Initialize each fighter for combat
        for fighter in self.db.fighters:
            self.initialize_for_combat(fighter)

        # Add a reference to this script to the room
        self.obj.db.combat_turnhandler = self

        # Roll initiative and sort the list of fighters depending on who rolls highest to determine turn order.
        # The initiative roll is determined by the roll_init function and can be customized easily.
        ordered_by_roll = sorted(self.db.fighters, key=roll_init, reverse=True)
        self.db.fighters = ordered_by_roll

        # Announce the turn order.
        self.obj.msg_contents("Turn order is: %s " % ", ".join(obj.key for obj in self.db.fighters))

        # Start first fighter's turn.
        self.start_turn(self.db.fighters[0])

        # Set up the current turn and turn timeout delay.
        self.db.turn = 0
        self.db.timer = TURN_TIMEOUT  # Set timer to turn timeout specified in options

    def at_stop(self):
        """
        Called at script termination.
        """
        for fighter in self.db.fighters:
            combat_cleanup(fighter)  # Clean up the combat attributes for every fighter.
        self.obj.db.combat_turnhandler = None  # Remove reference to turn handler in location

    def at_repeat(self):
        """
        Called once every self.interval seconds.
        """
        currentchar = self.db.fighters[
            self.db.turn
        ]  # Note the current character in the turn order.
        self.db.timer -= self.interval  # Count down the timer.

        if self.db.timer <= 0:
            # Force current character to disengage if timer runs out.
            self.obj.msg_contents("%s's turn timed out!" % currentchar)
            spend_action(
                currentchar, "all", action_name="disengage"
            )  # Spend all remaining actions.
            return
        elif self.db.timer <= 10 and not self.db.timeout_warning_given:  # 10 seconds left
            # Warn the current character if they're about to time out.
            currentchar.msg("WARNING: About to time out!")
            self.db.timeout_warning_given = True

    def initialize_for_combat(self, character):
        """
        Prepares a character for combat when starting or entering a fight.

        Args:
            character (obj): Character to initialize for combat.
        """
        combat_cleanup(character)  # Clean up leftover combat attributes beforehand, just in case.
        character.db.combat_actionsleft = (
            0
        )  # Actions remaining - start of turn adds to this, turn ends when it reaches 0
        character.db.combat_turnhandler = (
            self
        )  # Add a reference to this turn handler script to the character
        character.db.combat_lastaction = "null"  # Track last action taken in combat

    def start_turn(self, character):
        """
        Readies a character for the start of their turn by replenishing their
        available actions and notifying them that their turn has come up.

        Args:
            character (obj): Character to be readied.

        Notes:
            Here, you only get one action per turn, but you might want to allow more than
            one per turn, or even grant a number of actions based on a character's
            attributes. You can even add multiple different kinds of actions, I.E. actions
            separated for movement, by adding "character.db.combat_movesleft = 3" or
            something similar.
        """
        character.db.combat_actionsleft = ACTIONS_PER_TURN  # Replenish actions
        # Prompt the character for their turn and give some information.
        character.msg("|wIt's your turn! You have %i HP remaining.|n" % character.db.hp)

    def next_turn(self):
        """
        Advances to the next character in the turn order.
        """

        # Check to see if every character disengaged as their last action. If so, end combat.
        disengage_check = True
        for fighter in self.db.fighters:
            if (
                fighter.db.combat_lastaction != "disengage"
            ):  # If a character has done anything but disengage
                disengage_check = False
        if disengage_check:  # All characters have disengaged
            self.obj.msg_contents("All fighters have disengaged! Combat is over!")
            self.stop()  # Stop this script and end combat.
            return

        # Check to see if only one character is left standing. If so, end combat.
        defeated_characters = 0
        for fighter in self.db.fighters:
            if fighter.db.HP == 0:
                defeated_characters += 1  # Add 1 for every fighter with 0 HP left (defeated)
        if defeated_characters == (
            len(self.db.fighters) - 1
        ):  # If only one character isn't defeated
            for fighter in self.db.fighters:
                if fighter.db.HP != 0:
                    LastStanding = fighter  # Pick the one fighter left with HP remaining
            self.obj.msg_contents("Only %s remains! Combat is over!" % LastStanding)
            self.stop()  # Stop this script and end combat.
            return

        # Cycle to the next turn.
        currentchar = self.db.fighters[self.db.turn]
        self.db.turn += 1  # Go to the next in the turn order.
        if self.db.turn > len(self.db.fighters) - 1:
            self.db.turn = 0  # Go back to the first in the turn order once you reach the end.
        newchar = self.db.fighters[self.db.turn]  # Note the new character
        self.db.timer = TURN_TIMEOUT + self.time_until_next_repeat()  # Reset the timer.
        self.db.timeout_warning_given = False  # Reset the timeout warning.
        self.obj.msg_contents("%s's turn ends - %s's turn begins!" % (currentchar, newchar))
        self.start_turn(newchar)  # Start the new character's turn.

    def turn_end_check(self, character):
        """
        Tests to see if a character's turn is over, and cycles to the next turn if it is.

        Args:
            character (obj): Character to test for end of turn
        """
        if not character.db.combat_actionsleft:  # Character has no actions remaining
            self.next_turn()
            return

    def join_fight(self, character):
        """
        Adds a new character to a fight already in progress.

        Args:
            character (obj): Character to be added to the fight.
        """
        # Inserts the fighter to the turn order, right behind whoever's turn it currently is.
        self.db.fighters.insert(self.db.turn, character)
        # Tick the turn counter forward one to compensate.
        self.db.turn += 1
        # Initialize the character like you do at the start.
        self.initialize_for_combat(character)


"""
----------------------------------------------------------------------------
COMMANDS START HERE
----------------------------------------------------------------------------
"""


class CmdFight(Command):
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

    def func(self):
        """
        This performs the actual command.
        """
        here = self.caller.location
        fighters = []

        if not self.caller.db.hp:  # If you don't have any hp
            self.caller.msg("You can't start a fight if you've been defeated!")
            return
        if is_in_combat(self.caller):  # Already in a fight
            self.caller.msg("You're already in a fight!")
            return
        for thing in here.contents:  # Test everything in the room to add it to the fight.
            if thing.db.HP:  # If the object has HP...
                fighters.append(thing)  # ...then add it to the fight.
        if len(fighters) <= 1:  # If you're the only able fighter in the room
            self.caller.msg("There's nobody here to fight!")
            return
        if here.db.combat_turnhandler:  # If there's already a fight going on...
            here.msg_contents("%s joins the fight!" % self.caller)
            here.db.combat_turnhandler.join_fight(self.caller)  # Join the fight!
            return
        here.msg_contents("%s starts a fight!" % self.caller)
        # Add a turn handler script to the room, which starts combat.
        here.scripts.add("contrib.turnbattle.tb_magic.TBMagicTurnHandler")
        # Remember you'll have to change the path to the script if you copy this code to your own modules!


class CmdAttack(Command):
    """
    Attacks another character.

    Usage:
      attack <target>

    When in a fight, you may attack another character. The attack has
    a chance to hit, and if successful, will deal damage.
    """

    key = "attack"
    help_category = "combat"

    def func(self):
        "This performs the actual command."
        "Set the attacker to the caller and the defender to the target."

        if not is_in_combat(self.caller):  # If not in combat, can't attack.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn, can't attack.
            self.caller.msg("You can only do that on your turn.")
            return

        if not self.caller.db.hp:  # Can't attack if you have no HP.
            self.caller.msg("You can't attack, you've been defeated.")
            return

        attacker = self.caller
        defender = self.caller.search(self.args)

        if not defender:  # No valid target given.
            return

        if not defender.db.hp:  # Target object has no HP left or to begin with
            self.caller.msg("You can't fight that!")
            return

        if attacker == defender:  # Target and attacker are the same
            self.caller.msg("You can't attack yourself!")
            return

        "If everything checks out, call the attack resolving function."
        resolve_attack(attacker, defender)
        spend_action(self.caller, 1, action_name="attack")  # Use up one action.


class CmdPass(Command):
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

    def func(self):
        """
        This performs the actual command.
        """
        if not is_in_combat(self.caller):  # Can only pass a turn in combat.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # Can only pass if it's your turn.
            self.caller.msg("You can only do that on your turn.")
            return

        self.caller.location.msg_contents(
            "%s takes no further action, passing the turn." % self.caller
        )
        spend_action(self.caller, "all", action_name="pass")  # Spend all remaining actions.


class CmdDisengage(Command):
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

    def func(self):
        """
        This performs the actual command.
        """
        if not is_in_combat(self.caller):  # If you're not in combat
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn
            self.caller.msg("You can only do that on your turn.")
            return

        self.caller.location.msg_contents("%s disengages, ready to stop fighting." % self.caller)
        spend_action(self.caller, "all", action_name="disengage")  # Spend all remaining actions.
        """
        The action_name kwarg sets the character's last action to "disengage", which is checked by
        the turn handler script to see if all fighters have disengaged.
        """


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

        spellname = self.lhs.lower()
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
        if spelldata["combat_spell"] == False and is_in_combat(caller):
            caller.msg("You can't use the spell '%s' in combat." % spell_to_cast)
            return

        # If not in combat and the spell isn't a non-combat spell, error ms and return.
        if spelldata["noncombat_spell"] == False and is_in_combat(caller) == False:
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

    def func(self):
        "This performs the actual command."

        if is_in_combat(self.caller):  # If you're in combat
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


class CmdCombatHelp(CmdHelp):
    """
    View help or a list of topics

    Usage:
      help <topic or command>
      help list
      help all

    This will search for help on commands and other
    topics related to the game.
    """

    # Just like the default help command, but will give quick
    # tips on combat when used in a fight with no arguments.

    def func(self):
        if is_in_combat(self.caller) and not self.args:  # In combat and entered 'help' alone
            self.caller.msg(
                "Available combat commands:|/"
                + "|wAttack:|n Attack a target, attempting to deal damage.|/"
                + "|wPass:|n Pass your turn without further action.|/"
                + "|wDisengage:|n End your turn and attempt to end combat.|/"
            )
        else:
            super(CmdCombatHelp, self).func()  # Call the default help command


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


def spell_healing(caster, spell_name, targets, cost, **kwargs):
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

    if is_in_combat(caster):  # Spend action if in combat
        spend_action(caster, 1, action_name="cast")


def spell_attack(caster, spell_name, targets, cost, **kwargs):
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
        defense_value = get_defense(caster, fighter)
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
        apply_damage(fighter, total_damage[fighter])
        # If fighter HP is reduced to 0 or less, call at_defeat.
        if fighter.db.hp <= 0:
            at_defeat(fighter)

    if is_in_combat(caster):  # Spend action if in combat
        spend_action(caster, 1, action_name="cast")


def spell_conjure(caster, spell_name, targets, cost, **kwargs):
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
        "spellfunc": spell_attack,
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
        "spellfunc": spell_attack,
        "target": "otherchar",
        "cost": 3,
        "noncombat_spell": False,
        "attack_name": ("A jet of flame", "jets of flame"),
        "damage_range": (25, 35),
    },
    "cure wounds": {"spellfunc": spell_healing, "target": "anychar", "cost": 5},
    "mass cure wounds": {
        "spellfunc": spell_healing,
        "target": "anychar",
        "cost": 10,
        "max_targets": 5,
    },
    "full heal": {
        "spellfunc": spell_healing,
        "target": "anychar",
        "cost": 12,
        "healing_range": (100, 100),
    },
    "cactus conjuration": {
        "spellfunc": spell_conjure,
        "target": "none",
        "cost": 2,
        "combat_spell": False,
        "obj_key": "a cactus",
        "obj_desc": "An ordinary green cactus with little spines.",
    },
}
