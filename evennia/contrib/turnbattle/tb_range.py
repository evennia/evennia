"""
Simple turn-based combat system with range and movement

Contrib - Tim Ashley Jenkins 2017

This is a version of the 'turnbattle' contrib that includes a system
for abstract movement and positioning in combat, including distinction
between melee and ranged attacks. In this system, a fighter or object's
exact position is not recorded - only their relative distance to other
actors in combat.

In this example, the distance between two objects in combat is expressed
as an integer value: 0 for "engaged" objects that are right next to each
other, 1 for "reach" which is for objects that are near each other but
not directly adjacent, and 2 for "range" for objects that are far apart.

When combat starts, all fighters are at reach with each other and other
objects, and at range from any exits. On a fighter's turn, they can use
the "approach" command to move closer to an object, or the "withdraw"
command to move further away from an object, either of which takes an
action in combat. In this example, fighters are given two actions per
turn, allowing them to move and attack in the same round, or to attack
twice or move twice.

When you move toward an object, you will also move toward anything else
that's close to your target - the same goes for moving away from a target,
which will also move you away from anything close to your target. Moving
toward one target may also move you away from anything you're already
close to, but withdrawing from a target will never inadvertently bring
you closer to anything else.

In this example, there are two attack commands. 'Attack' can only hit
targets that are 'engaged' (range 0) with you. 'Shoot' can hit any target
on the field, but cannot be used if you are engaged with any other fighters.
In addition, strikes made with the 'attack' command are more accurate than
'shoot' attacks. This is only to provide an example of how melee and ranged
attacks can be made to work differently - you can, of course, modify this
to fit your rules system.

When in combat, the ranges of objects are also accounted for - you can't
pick up an object unless you're engaged with it, and can't give an object
to another fighter without being engaged with them either. Dropped objects
are automatically assigned a range of 'engaged' with the fighter who dropped
them. Additionally, giving or getting an object will take an action in combat.
Dropping an object does not take an action, but can only be done on your turn.

When combat ends, all range values are erased and all restrictions on getting
or getting objects are lifted - distances are no longer tracked and objects in
the same room can be considered to be in the same space, as is the default
behavior of Evennia and most MUDs.

This system allows for strategies in combat involving movement and
positioning to be implemented in your battle system without the use of
a 'grid' of coordinates, which can be difficult and clunky to navigate
in text and disadvantageous to players who use screen readers. This loose,
narrative method of tracking position is based around how the matter is
handled in tabletop RPGs played without a grid - typically, a character's
exact position in a room isn't important, only their relative distance to
other actors.

You may wish to expand this system with a method of distinguishing allies
from enemies (to prevent allied characters from blocking your ranged attacks)
as well as some method by which melee-focused characters can prevent enemies
from withdrawing or punish them from doing so, such as by granting "attacks of
opportunity" or something similar. If you wish, you can also expand the breadth
of values allowed for range - rather than just 0, 1, and 2, you can allow ranges
to go up to much higher values, and give attacks and movements more varying
values for distance for a more granular system. You may also want to implement
a system for fleeing or changing rooms in combat by approaching exits, which
are objects placed in the range field like any other.

To install and test, import this module's TBRangeCharacter object into
your game's character.py module:

    from evennia.contrib.turnbattle.tb_range import TBRangeCharacter

And change your game's character typeclass to inherit from TBRangeCharacter
instead of the default:

    class Character(TBRangeCharacter):
        
Do the same thing in your game's objects.py module for TBRangeObject:

    from evennia.contrib.turnbattle.tb_range import TBRangeObject
    class Object(TBRangeObject):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.turnbattle import tb_range

And add the battle command set to your default command set:

    #
    # any commands you add below will overload the default ones.
    #
    self.add(tb_range.BattleCmdSet())

This module is meant to be heavily expanded on, so you may want to copy it
to your game's 'world' folder and modify it there rather than importing it
in your game and using it as-is.
"""

from random import randint
from evennia import DefaultCharacter, DefaultObject, Command, default_cmds, DefaultScript
from evennia.commands.default.help import CmdHelp

"""
----------------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------------
"""

TURN_TIMEOUT = 30  # Time before turns automatically end, in seconds
ACTIONS_PER_TURN = 2  # Number of actions allowed per turn

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


def get_attack(attacker, defender, attack_type):
    """
    Returns a value for an attack roll.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked
        attack_type (str): Type of attack ('melee' or 'ranged')

    Returns:
        attack_value (int): Attack roll value, compared against a defense value
            to determine whether an attack hits or misses.

    Notes:
        By default, generates a random integer from 1 to 100 without using any
        properties from either the attacker or defender, and modifies the result
        based on whether it's for a melee or ranged attack.

        This can easily be expanded to return a value based on characters stats,
        equipment, and abilities. This is why the attacker and defender are passed
        to this function, even though nothing from either one are used in this example.
    """
    # For this example, just return a random integer up to 100.
    attack_value = randint(1, 100)
    # Make melee attacks more accurate, ranged attacks less accurate
    if attack_type == "melee":
        attack_value += 15
    if attack_type == "ranged":
        attack_value -= 15
    return attack_value


def get_defense(attacker, defender, attack_type):
    """
    Returns a value for defense, which an attack roll must equal or exceed in order
    for an attack to hit.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked
        attack_type (str): Type of attack ('melee' or 'ranged')

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


def resolve_attack(attacker, defender, attack_type, attack_value=None, defense_value=None):
    """
    Resolves an attack and outputs the result.

    Args:
        attacker (obj): Character doing the attacking
        defender (obj): Character being attacked
        attack_type (str): Type of attack (melee or ranged)

    Notes:
        Even though the attack and defense values are calculated
        extremely simply, they are separated out into their own functions
        so that they are easier to expand upon.
    """
    # Get an attack roll from the attacker.
    if not attack_value:
        attack_value = get_attack(attacker, defender, attack_type)
    # Get a defense value from the defender.
    if not defense_value:
        defense_value = get_defense(attacker, defender, attack_type)
    # If the attack value is lower than the defense value, miss. Otherwise, hit.
    if attack_value < defense_value:
        attacker.location.msg_contents(
            "%s's %s attack misses %s!" % (attacker, attack_type, defender)
        )
    else:
        damage_value = get_damage(attacker, defender)  # Calculate damage value.
        # Announce damage dealt and apply damage.
        attacker.location.msg_contents(
            "%s hits %s with a %s attack for %i damage!"
            % (attacker, defender, attack_type, damage_value)
        )
        apply_damage(defender, damage_value)
        # If defender HP is reduced to 0 or less, call at_defeat.
        if defender.db.hp <= 0:
            at_defeat(defender)


def get_range(obj1, obj2):
    """
    Gets the combat range between two objects.
    
    Args:
        obj1 (obj): First object
        obj2 (obj): Second object
        
    Returns:
        range (int or None): Distance between two objects or None if not applicable
    """
    # Return None if not applicable.
    if not obj1.db.combat_range:
        return None
    if not obj2.db.combat_range:
        return None
    if obj1 not in obj2.db.combat_range:
        return None
    if obj2 not in obj1.db.combat_range:
        return None
    # Return the range between the two objects.
    return obj1.db.combat_range[obj2]


def distance_inc(mover, target):
    """
    Function that increases distance in range field between mover and target.
    
    Args:
        mover (obj): The object moving
        target (obj): The object to be moved away from
    """
    mover.db.combat_range[target] += 1
    target.db.combat_range[mover] = mover.db.combat_range[target]
    # Set a cap of 2:
    if get_range(mover, target) > 2:
        target.db.combat_range[mover] = 2
        mover.db.combat_range[target] = 2


def approach(mover, target):
    """
    Manages a character's whole approach, including changes in ranges to other characters.
    
    Args:
        mover (obj): The object moving
        target (obj): The object to be moved toward
        
    Notes:
        The mover will also automatically move toward any objects that are closer to the
        target than the mover is. The mover will also move away from anything they started
        out close to.
    """

    def distance_dec(mover, target):
        """
        Helper function that decreases distance in range field between mover and target.
        
        Args:
            mover (obj): The object moving
            target (obj): The object to be moved toward
        """
        mover.db.combat_range[target] -= 1
        target.db.combat_range[mover] = mover.db.combat_range[target]
        # If this brings mover to range 0 (Engaged):
        if get_range(mover, target) <= 0:
            # Reset range to each other to 0 and copy target's ranges to mover.
            target.db.combat_range[mover] = 0
            mover.db.combat_range = target.db.combat_range
            # Assure everything else has the same distance from the mover and target, now that they're together
            for thing in mover.location.contents:
                if thing != mover and thing != target:
                    thing.db.combat_range[mover] = thing.db.combat_range[target]

    contents = mover.location.contents

    for thing in contents:
        if thing != mover and thing != target:
            # Move closer to each object closer to the target than you.
            if get_range(mover, thing) > get_range(target, thing):
                distance_dec(mover, thing)
            # Move further from each object that's further from you than from the target.
            if get_range(mover, thing) < get_range(target, thing):
                distance_inc(mover, thing)
    # Lastly, move closer to your target.
    distance_dec(mover, target)


def withdraw(mover, target):
    """
    Manages a character's whole withdrawal, including changes in ranges to other characters.
    
    Args:
        mover (obj): The object moving
        target (obj): The object to be moved away from
        
    Notes:
        The mover will also automatically move away from objects that are close to the target
        of their withdrawl. The mover will never inadvertently move toward anything else while
        withdrawing - they can be considered to be moving to open space.
    """

    contents = mover.location.contents

    for thing in contents:
        if thing != mover and thing != target:
            # Move away from each object closer to the target than you, if it's also closer to you than you are to the target.
            if get_range(mover, thing) >= get_range(target, thing) and get_range(
                mover, thing
            ) < get_range(mover, target):
                distance_inc(mover, thing)
            # Move away from anything your target is engaged with
            if get_range(target, thing) == 0:
                distance_inc(mover, thing)
            # Move away from anything you're engaged with.
            if get_range(mover, thing) == 0:
                distance_inc(mover, thing)
    # Then, move away from your target.
    distance_inc(mover, target)


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
    if action_name:
        character.db.combat_lastaction = action_name
    if actions == "all":  # If spending all actions
        character.db.combat_actionsleft = 0  # Set actions to 0
    else:
        character.db.combat_actionsleft -= actions  # Use up actions.
        if character.db.combat_actionsleft < 0:
            character.db.combat_actionsleft = 0  # Can't have fewer than 0 actions
    character.db.combat_turnhandler.turn_end_check(character)  # Signal potential end of turn.


def combat_status_message(fighter):
    """
    Sends a message to a player with their current HP and
    distances to other fighters and objects. Called at turn
    start and by the 'status' command.
    """
    if not fighter.db.max_hp:
        fighter.db.hp = 100
        fighter.db.max_hp = 100

    status_msg = "HP Remaining: %i / %i" % (fighter.db.hp, fighter.db.max_hp)

    if not is_in_combat(fighter):
        fighter.msg(status_msg)
        return

    engaged_obj = []
    reach_obj = []
    range_obj = []

    for thing in fighter.db.combat_range:
        if thing != fighter:
            if fighter.db.combat_range[thing] == 0:
                engaged_obj.append(thing)
            if fighter.db.combat_range[thing] == 1:
                reach_obj.append(thing)
            if fighter.db.combat_range[thing] > 1:
                range_obj.append(thing)

    if engaged_obj:
        status_msg += "|/Engaged targets: %s" % ", ".join(obj.key for obj in engaged_obj)
    if reach_obj:
        status_msg += "|/Reach targets: %s" % ", ".join(obj.key for obj in reach_obj)
    if range_obj:
        status_msg += "|/Ranged targets: %s" % ", ".join(obj.key for obj in range_obj)

    fighter.msg(status_msg)


"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBRangeTurnHandler(DefaultScript):
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

        # Initialize range field for all objects in the room
        for thing in self.obj.contents:
            self.init_range(thing)

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
        for thing in self.obj.contents:
            combat_cleanup(thing)  # Clean up the combat attributes for every object in the room.
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

    def init_range(self, to_init):
        """
        Initializes range values for an object at the start of a fight.
        
        Args:
            to_init (object): Object to initialize range field for.
        """
        rangedict = {}
        # Get a list of objects in the room.
        objectlist = self.obj.contents
        for thing in objectlist:
            # Object always at distance 0 from itself
            if thing == to_init:
                rangedict.update({thing: 0})
            else:
                if thing.destination or to_init.destination:
                    # Start exits at range 2 to put them at the 'edges'
                    rangedict.update({thing: 2})
                else:
                    # Start objects at range 1 from other objects
                    rangedict.update({thing: 1})
        to_init.db.combat_range = rangedict

    def join_rangefield(self, to_init, anchor_obj=None, add_distance=0):
        """
        Adds a new object to the range field of a fight in progress.
        
        Args:
            to_init (object): Object to initialize range field for.
        
        Kwargs:
            anchor_obj (object): Object to copy range values from, or None for a random object.
            add_distance (int): Distance to put between to_init object and anchor object.
            
        """
        # Get a list of room's contents without to_init object.
        contents = self.obj.contents
        contents.remove(to_init)
        # If no anchor object given, pick one in the room at random.
        if not anchor_obj:
            anchor_obj = contents[randint(0, (len(contents) - 1))]
        # Copy the range values from the anchor object.
        to_init.db.combat_range = anchor_obj.db.combat_range
        # Add the new object to everyone else's ranges.
        for thing in contents:
            new_objects_range = thing.db.combat_range[anchor_obj]
            thing.db.combat_range.update({to_init: new_objects_range})
        # Set the new object's range to itself to 0.
        to_init.db.combat_range.update({to_init: 0})
        # Add additional distance from anchor object, if any.
        for n in range(add_distance):
            withdraw(to_init, anchor_obj)

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
            In this example, characters are given two actions per turn. This allows
            characters to both move and attack in the same turn (or, alternately,
            move twice or attack twice).
        """
        character.db.combat_actionsleft = ACTIONS_PER_TURN  # Replenish actions
        # Prompt the character for their turn and give some information.
        character.msg("|wIt's your turn!|n")
        combat_status_message(character)

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
        # Add the character to the rangefield, at range from everyone, if they're not on it already.
        if not character.db.combat_range:
            self.join_rangefield(character, add_distance=2)


"""
----------------------------------------------------------------------------
TYPECLASSES START HERE
----------------------------------------------------------------------------
"""


class TBRangeCharacter(DefaultCharacter):
    """
    A character able to participate in turn-based combat. Has attributes for current
    and maximum HP, and access to combat commands.
    """

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.max_hp = 100  # Set maximum HP to 100
        self.db.hp = self.db.max_hp  # Set current HP to maximum
        """
        Adds attributes for a character's current and maximum HP.
        We're just going to set this value at '100' by default.

        You may want to expand this to include various 'stats' that
        can be changed at creation and factor into combat calculations.
        """

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


class TBRangeObject(DefaultObject):
    """
    An object that is assigned range values in combat. Getting, giving, and dropping
    the object has restrictions in combat - you must be next to an object to get it,
    must be next to your target to give them something, and can only interact with
    objects on your own turn.
    """

    def at_before_drop(self, dropper):
        """
        Called by the default `drop` command before this object has been
        dropped.

        Args:
            dropper (Object): The object which will drop this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            shoulddrop (bool): If the object should be dropped or not.

        Notes:
            If this method returns False/None, the dropping is cancelled
            before it is even started.

        """
        # Can't drop something if in combat and it's not your turn
        if is_in_combat(dropper) and not is_turn(dropper):
            dropper.msg("You can only drop things on your turn!")
            return False
        return True

    def at_drop(self, dropper):
        """
        Called by the default `drop` command when this object has been
        dropped.

        Args:
            dropper (Object): The object which just dropped this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the drop from happening. Use
            permissions or the at_before_drop() hook for that.

        """
        # If dropper is currently in combat
        if dropper.location.db.combat_turnhandler:
            # Object joins the range field
            self.db.combat_range = {}
            dropper.location.db.combat_turnhandler.join_rangefield(self, anchor_obj=dropper)

    def at_before_get(self, getter):
        """
        Called by the default `get` command before this object has been
        picked up.

        Args:
            getter (Object): The object about to get this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            shouldget (bool): If the object should be gotten or not.

        Notes:
            If this method returns False/None, the getting is cancelled
            before it is even started.
        """
        # Restrictions for getting in combat
        if is_in_combat(getter):
            if not is_turn(getter):  # Not your turn
                getter.msg("You can only get things on your turn!")
                return False
            if get_range(self, getter) > 0:  # Too far away
                getter.msg("You aren't close enough to get that! (see: help approach)")
                return False
        return True

    def at_get(self, getter):
        """
        Called by the default `get` command when this object has been
        picked up.

        Args:
            getter (Object): The object getting this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the pickup from happening. Use
            permissions or the at_before_get() hook for that.

        """
        # If gotten, erase range values
        if self.db.combat_range:
            del self.db.combat_range
        # Remove this object from everyone's range fields
        for thing in getter.location.contents:
            if thing.db.combat_range:
                if self in thing.db.combat_range:
                    thing.db.combat_range.pop(self, None)
        # If in combat, getter spends an action
        if is_in_combat(getter):
            spend_action(getter, 1, action_name="get")  # Use up one action.

    def at_before_give(self, giver, getter):
        """
        Called by the default `give` command before this object has been
        given.

        Args:
            giver (Object): The object about to give this object.
            getter (Object): The object about to get this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            shouldgive (bool): If the object should be given or not.

        Notes:
            If this method returns False/None, the giving is cancelled
            before it is even started.

        """
        # Restrictions for giving in combat
        if is_in_combat(giver):
            if not is_turn(giver):  # Not your turn
                giver.msg("You can only give things on your turn!")
                return False
            if get_range(giver, getter) > 0:  # Too far away from target
                giver.msg(
                    "You aren't close enough to give things to %s! (see: help approach)" % getter
                )
                return False
        return True

    def at_give(self, giver, getter):
        """
        Called by the default `give` command when this object has been
        given.

        Args:
            giver (Object): The object giving this object.
            getter (Object): The object getting this object.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:
            This hook cannot stop the give from happening. Use
            permissions or the at_before_give() hook for that.

        """
        # Spend an action if in combat
        if is_in_combat(giver):
            spend_action(giver, 1, action_name="give")  # Use up one action.


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
        here.scripts.add("contrib.turnbattle.tb_range.TBRangeTurnHandler")
        # Remember you'll have to change the path to the script if you copy this code to your own modules!


class CmdAttack(Command):
    """
    Attacks another character in melee.

    Usage:
      attack <target>

    When in a fight, you may attack another character. The attack has
    a chance to hit, and if successful, will deal damage. You can only
    attack engaged targets - that is, targets that are right next to
    you. Use the 'approach' command to get closer to a target.
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

        if not get_range(attacker, defender) == 0:  # Target isn't in melee
            self.caller.msg(
                "%s is too far away to attack - you need to get closer! (see: help approach)"
                % defender
            )
            return

        "If everything checks out, call the attack resolving function."
        resolve_attack(attacker, defender, "melee")
        spend_action(self.caller, 1, action_name="attack")  # Use up one action.


class CmdShoot(Command):
    """
    Attacks another character from range.

    Usage:
      shoot <target>

    When in a fight, you may shoot another character. The attack has
    a chance to hit, and if successful, will deal damage. You can attack
    any target in combat by shooting, but can't shoot if there are any
    targets engaged with you. Use the 'withdraw' command to retreat from
    nearby enemies.
    """

    key = "shoot"
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

        # Test to see if there are any nearby enemy targets.
        in_melee = []
        for target in attacker.db.combat_range:
            # Object is engaged and has HP
            if get_range(attacker, defender) == 0 and target.db.hp and target != self.caller:
                in_melee.append(target)  # Add to list of targets in melee

        if len(in_melee) > 0:
            self.caller.msg(
                "You can't shoot because there are fighters engaged with you (%s) - you need to retreat! (see: help withdraw)"
                % ", ".join(obj.key for obj in in_melee)
            )
            return

        "If everything checks out, call the attack resolving function."
        resolve_attack(attacker, defender, "ranged")
        spend_action(self.caller, 1, action_name="attack")  # Use up one action.


class CmdApproach(Command):
    """
    Approaches an object.

    Usage:
      approach <target>

    Move one space toward a character or object. You can only attack
    characters you are 0 spaces away from.
    """

    key = "approach"
    help_category = "combat"

    def func(self):
        "This performs the actual command."

        if not is_in_combat(self.caller):  # If not in combat, can't approach.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn, can't approach.
            self.caller.msg("You can only do that on your turn.")
            return

        if not self.caller.db.hp:  # Can't approach if you have no HP.
            self.caller.msg("You can't move, you've been defeated.")
            return

        mover = self.caller
        target = self.caller.search(self.args)

        if not target:  # No valid target given.
            return

        if not target.db.combat_range:  # Target object is not on the range field
            self.caller.msg("You can't move toward that!")
            return

        if mover == target:  # Target and mover are the same
            self.caller.msg("You can't move toward yourself!")
            return

        if get_range(mover, target) <= 0:  # Already engaged with target
            self.caller.msg("You're already next to that target!")
            return

        # If everything checks out, call the approach resolving function.
        approach(mover, target)
        mover.location.msg_contents("%s moves toward %s." % (mover, target))
        spend_action(self.caller, 1, action_name="move")  # Use up one action.


class CmdWithdraw(Command):
    """
    Moves away from an object.

    Usage:
      withdraw <target>

    Move one space away from a character or object.
    """

    key = "withdraw"
    help_category = "combat"

    def func(self):
        "This performs the actual command."

        if not is_in_combat(self.caller):  # If not in combat, can't withdraw.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return

        if not is_turn(self.caller):  # If it's not your turn, can't withdraw.
            self.caller.msg("You can only do that on your turn.")
            return

        if not self.caller.db.hp:  # Can't withdraw if you have no HP.
            self.caller.msg("You can't move, you've been defeated.")
            return

        mover = self.caller
        target = self.caller.search(self.args)

        if not target:  # No valid target given.
            return

        if not target.db.combat_range:  # Target object is not on the range field
            self.caller.msg("You can't move away from that!")
            return

        if mover == target:  # Target and mover are the same
            self.caller.msg("You can't move away from yourself!")
            return

        if mover.db.combat_range[target] >= 3:  # Already at maximum distance
            self.caller.msg("You're as far as you can get from that target!")
            return

        # If everything checks out, call the approach resolving function.
        withdraw(mover, target)
        mover.location.msg_contents("%s moves away from %s." % (mover, target))
        spend_action(self.caller, 1, action_name="move")  # Use up one action.


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


class CmdRest(Command):
    """
    Recovers damage.

    Usage:
      rest

    Resting recovers your HP to its maximum, but you can only
    rest if you're not in a fight.
    """

    key = "rest"
    help_category = "combat"

    def func(self):
        "This performs the actual command."

        if is_in_combat(self.caller):  # If you're in combat
            self.caller.msg("You can't rest while you're in combat.")
            return

        self.caller.db.hp = self.caller.db.max_hp  # Set current HP to maximum
        self.caller.location.msg_contents("%s rests to recover HP." % self.caller)
        """
        You'll probably want to replace this with your own system for recovering HP.
        """


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
        combat_status_message(self.caller)


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
                + "|wAttack:|n Attack an engaged target, attempting to deal damage.|/"
                + "|wShoot:|n Attack from a distance, if not engaged with other fighters.|/"
                + "|wApproach:|n Move one step cloer to a target.|/"
                + "|wWithdraw:|n Move one step away from a target.|/"
                + "|wPass:|n Pass your turn without further action.|/"
                + "|wStatus:|n View current HP and ranges to other targets.|/"
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
        self.add(CmdShoot())
        self.add(CmdRest())
        self.add(CmdPass())
        self.add(CmdDisengage())
        self.add(CmdApproach())
        self.add(CmdWithdraw())
        self.add(CmdStatus())
        self.add(CmdCombatHelp())
