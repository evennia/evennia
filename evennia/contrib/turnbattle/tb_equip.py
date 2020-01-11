"""
Simple turn-based combat system with equipment

Contrib - Tim Ashley Jenkins 2017

This is a version of the 'turnbattle' contrib with a basic system for
weapons and armor implemented. Weapons can have unique damage ranges
and accuracy modifiers, while armor can reduce incoming damage and
change one's chance of getting hit. The 'wield' command is used to
equip weapons and the 'don' command is used to equip armor.

Some prototypes are included at the end of this module - feel free to
copy them into your game's prototypes.py module in your 'world' folder
and create them with the @spawn command. (See the tutorial for using
the @spawn command for details.)

For the example equipment given, heavier weapons deal more damage
but are less accurate, while light weapons are more accurate but
deal less damage. Similarly, heavy armor reduces incoming damage by
a lot but increases your chance of getting hit, while light armor is
easier to dodge in but reduces incoming damage less. Light weapons are
more effective against lightly armored opponents and heavy weapons are
more damaging against heavily armored foes, but heavy weapons and armor
are slightly better than light weapons and armor overall.

This is a fairly bare implementation of equipment that is meant to be
expanded to fit your game - weapon and armor slots, damage types and
damage bonuses, etc. should be fairly simple to implement according to
the rules of your preferred system or the needs of your own game.

To install and test, import this module's TBEquipCharacter object into
your game's character.py module:

    from evennia.contrib.turnbattle.tb_equip import TBEquipCharacter

And change your game's character typeclass to inherit from TBEquipCharacter
instead of the default:

    class Character(TBEquipCharacter):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.turnbattle import tb_equip

And add the battle command set to your default command set:

    #
    # any commands you add below will overload the default ones.
    #
    self.add(tb_equip.BattleCmdSet())

This module is meant to be heavily expanded on, so you may want to copy it
to your game's 'world' folder and modify it there rather than importing it
in your game and using it as-is.
"""

from random import randint
from evennia import DefaultCharacter, Command, default_cmds, DefaultScript, DefaultObject
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
        In this example, a weapon's accuracy bonus is factored into the attack
        roll. Lighter weapons are more accurate but less damaging, and heavier
        weapons are less accurate but deal more damage. Of course, you can
        change this paradigm completely in your own game.
    """
    # Start with a roll from 1 to 100.
    attack_value = randint(1, 100)
    accuracy_bonus = 0
    # If armed, add weapon's accuracy bonus.
    if attacker.db.wielded_weapon:
        weapon = attacker.db.wielded_weapon
        accuracy_bonus += weapon.db.accuracy_bonus
    # If unarmed, use character's unarmed accuracy bonus.
    else:
        accuracy_bonus += attacker.db.unarmed_accuracy
    # Add the accuracy bonus to the attack roll.
    attack_value += accuracy_bonus
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
        Characters are given a default defense value of 50 which can be
        modified up or down by armor. In this example, wearing armor actually
        makes you a little easier to hit, but reduces incoming damage.
    """
    # Start with a defense value of 50 for a 50/50 chance to hit.
    defense_value = 50
    # Modify this value based on defender's armor.
    if defender.db.worn_armor:
        armor = defender.db.worn_armor
        defense_value += armor.db.defense_modifier
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
        Damage is determined by the attacker's wielded weapon, or the attacker's
        unarmed damage range if no weapon is wielded. Incoming damage is reduced
        by the defender's armor.
    """
    damage_value = 0
    # Generate a damage value from wielded weapon if armed
    if attacker.db.wielded_weapon:
        weapon = attacker.db.wielded_weapon
        # Roll between minimum and maximum damage
        damage_value = randint(weapon.db.damage_range[0], weapon.db.damage_range[1])
    # Use attacker's unarmed damage otherwise
    else:
        damage_value = randint(
            attacker.db.unarmed_damage_range[0], attacker.db.unarmed_damage_range[1]
        )
    # If defender is armored, reduce incoming damage
    if defender.db.worn_armor:
        armor = defender.db.worn_armor
        damage_value -= armor.db.damage_reduction
    # Make sure minimum damage is 0
    if damage_value < 0:
        damage_value = 0
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
    # Get the attacker's weapon type to reference in combat messages.
    attackers_weapon = "attack"
    if attacker.db.wielded_weapon:
        weapon = attacker.db.wielded_weapon
        attackers_weapon = weapon.db.weapon_type_name
    # Get an attack roll from the attacker.
    if not attack_value:
        attack_value = get_attack(attacker, defender)
    # Get a defense value from the defender.
    if not defense_value:
        defense_value = get_defense(attacker, defender)
    # If the attack value is lower than the defense value, miss. Otherwise, hit.
    if attack_value < defense_value:
        attacker.location.msg_contents(
            "%s's %s misses %s!" % (attacker, attackers_weapon, defender)
        )
    else:
        damage_value = get_damage(attacker, defender)  # Calculate damage value.
        # Announce damage dealt and apply damage.
        if damage_value > 0:
            attacker.location.msg_contents(
                "%s's %s strikes %s for %i damage!"
                % (attacker, attackers_weapon, defender, damage_value)
            )
        else:
            attacker.location.msg_contents(
                "%s's %s bounces harmlessly off %s!" % (attacker, attackers_weapon, defender)
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
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBEquipTurnHandler(DefaultScript):
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
TYPECLASSES START HERE
----------------------------------------------------------------------------
"""


class TBEWeapon(DefaultObject):
    """
    A weapon which can be wielded in combat with the 'wield' command.
    """

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.damage_range = (15, 25)  # Minimum and maximum damage on hit
        self.db.accuracy_bonus = 0  # Bonus to attack rolls (or penalty if negative)
        self.db.weapon_type_name = (
            "weapon"
        )  # Single word for weapon - I.E. "dagger", "staff", "scimitar"

    def at_drop(self, dropper):
        """
        Stop being wielded if dropped.
        """
        if dropper.db.wielded_weapon == self:
            dropper.db.wielded_weapon = None
            dropper.location.msg_contents("%s stops wielding %s." % (dropper, self))

    def at_give(self, giver, getter):
        """
        Stop being wielded if given.
        """
        if giver.db.wielded_weapon == self:
            giver.db.wielded_weapon = None
            giver.location.msg_contents("%s stops wielding %s." % (giver, self))


class TBEArmor(DefaultObject):
    """
    A set of armor which can be worn with the 'don' command.
    """

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.damage_reduction = 4  # Amount of incoming damage reduced by armor
        self.db.defense_modifier = (
            -4
        )  # Amount to modify defense value (pos = harder to hit, neg = easier)

    def at_before_drop(self, dropper):
        """
        Can't drop in combat.
        """
        if is_in_combat(dropper):
            dropper.msg("You can't doff armor in a fight!")
            return False
        return True

    def at_drop(self, dropper):
        """
        Stop being wielded if dropped.
        """
        if dropper.db.worn_armor == self:
            dropper.db.worn_armor = None
            dropper.location.msg_contents("%s removes %s." % (dropper, self))

    def at_before_give(self, giver, getter):
        """
        Can't give away in combat.
        """
        if is_in_combat(giver):
            dropper.msg("You can't doff armor in a fight!")
            return False
        return True

    def at_give(self, giver, getter):
        """
        Stop being wielded if given.
        """
        if giver.db.worn_armor == self:
            giver.db.worn_armor = None
            giver.location.msg_contents("%s removes %s." % (giver, self))


class TBEquipCharacter(DefaultCharacter):
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
        self.db.wielded_weapon = None  # Currently used weapon
        self.db.worn_armor = None  # Currently worn armor
        self.db.unarmed_damage_range = (5, 15)  # Minimum and maximum unarmed damage
        self.db.unarmed_accuracy = 30  # Accuracy bonus for unarmed attacks

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
        here.scripts.add("contrib.turnbattle.tb_equip.TBEquipTurnHandler")
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
            super().func()  # Call the default help command


class CmdWield(Command):
    """
    Wield a weapon you are carrying
    
    Usage:
      wield <weapon>
      
    Select a weapon you are carrying to wield in combat. If
    you are already wielding another weapon, you will switch
    to the weapon you specify instead. Using this command in
    combat will spend your action for your turn. Use the
    "unwield" command to stop wielding any weapon you are
    currently wielding.
    """

    key = "wield"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        # If in combat, check to see if it's your turn.
        if is_in_combat(self.caller):
            if not is_turn(self.caller):
                self.caller.msg("You can only do that on your turn.")
                return
        if not self.args:
            self.caller.msg("Usage: wield <obj>")
            return
        weapon = self.caller.search(self.args, candidates=self.caller.contents)
        if not weapon:
            return
        if not weapon.is_typeclass("evennia.contrib.turnbattle.tb_equip.TBEWeapon"):
            self.caller.msg("That's not a weapon!")
            # Remember to update the path to the weapon typeclass if you move this module!
            return

        if not self.caller.db.wielded_weapon:
            self.caller.db.wielded_weapon = weapon
            self.caller.location.msg_contents("%s wields %s." % (self.caller, weapon))
        else:
            old_weapon = self.caller.db.wielded_weapon
            self.caller.db.wielded_weapon = weapon
            self.caller.location.msg_contents(
                "%s lowers %s and wields %s." % (self.caller, old_weapon, weapon)
            )
        # Spend an action if in combat.
        if is_in_combat(self.caller):
            spend_action(self.caller, 1, action_name="wield")  # Use up one action.


class CmdUnwield(Command):
    """
    Stop wielding a weapon.
    
    Usage:
      unwield
      
    After using this command, you will stop wielding any
    weapon you are currently wielding and become unarmed.
    """

    key = "unwield"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        # If in combat, check to see if it's your turn.
        if is_in_combat(self.caller):
            if not is_turn(self.caller):
                self.caller.msg("You can only do that on your turn.")
                return
        if not self.caller.db.wielded_weapon:
            self.caller.msg("You aren't wielding a weapon!")
        else:
            old_weapon = self.caller.db.wielded_weapon
            self.caller.db.wielded_weapon = None
            self.caller.location.msg_contents("%s lowers %s." % (self.caller, old_weapon))


class CmdDon(Command):
    """
    Don armor that you are carrying
    
    Usage:
      don <armor>
      
    Select armor to wear in combat. You can't use this
    command in the middle of a fight. Use the "doff" 
    command to remove any armor you are wearing.
    """

    key = "don"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        # Can't do this in combat
        if is_in_combat(self.caller):
            self.caller.msg("You can't don armor in a fight!")
            return
        if not self.args:
            self.caller.msg("Usage: don <obj>")
            return
        armor = self.caller.search(self.args, candidates=self.caller.contents)
        if not armor:
            return
        if not armor.is_typeclass("evennia.contrib.turnbattle.tb_equip.TBEArmor"):
            self.caller.msg("That's not armor!")
            # Remember to update the path to the armor typeclass if you move this module!
            return

        if not self.caller.db.worn_armor:
            self.caller.db.worn_armor = armor
            self.caller.location.msg_contents("%s dons %s." % (self.caller, armor))
        else:
            old_armor = self.caller.db.worn_armor
            self.caller.db.worn_armor = armor
            self.caller.location.msg_contents(
                "%s removes %s and dons %s." % (self.caller, old_armor, armor)
            )


class CmdDoff(Command):
    """
    Stop wearing armor.
    
    Usage:
      doff
      
    After using this command, you will stop wearing any
    armor you are currently using and become unarmored.
    You can't use this command in combat.
    """

    key = "doff"
    help_category = "combat"

    def func(self):
        """
        This performs the actual command.
        """
        # Can't do this in combat
        if is_in_combat(self.caller):
            self.caller.msg("You can't doff armor in a fight!")
            return
        if not self.caller.db.worn_armor:
            self.caller.msg("You aren't wearing any armor!")
        else:
            old_armor = self.caller.db.worn_armor
            self.caller.db.worn_armor = None
            self.caller.location.msg_contents("%s removes %s." % (self.caller, old_armor))


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
        self.add(CmdWield())
        self.add(CmdUnwield())
        self.add(CmdDon())
        self.add(CmdDoff())


"""
----------------------------------------------------------------------------
PROTOTYPES START HERE
----------------------------------------------------------------------------
"""

BASEWEAPON = {"typeclass": "evennia.contrib.turnbattle.tb_equip.TBEWeapon"}

BASEARMOR = {"typeclass": "evennia.contrib.turnbattle.tb_equip.TBEArmor"}

DAGGER = {
    "prototype": "BASEWEAPON",
    "damage_range": (10, 20),
    "accuracy_bonus": 30,
    "key": "a thin steel dagger",
    "weapon_type_name": "dagger",
}

BROADSWORD = {
    "prototype": "BASEWEAPON",
    "damage_range": (15, 30),
    "accuracy_bonus": 15,
    "key": "an iron broadsword",
    "weapon_type_name": "broadsword",
}

GREATSWORD = {
    "prototype": "BASEWEAPON",
    "damage_range": (20, 40),
    "accuracy_bonus": 0,
    "key": "a rune-etched greatsword",
    "weapon_type_name": "greatsword",
}

LEATHERARMOR = {
    "prototype": "BASEARMOR",
    "damage_reduction": 2,
    "defense_modifier": -2,
    "key": "a suit of leather armor",
}

SCALEMAIL = {
    "prototype": "BASEARMOR",
    "damage_reduction": 4,
    "defense_modifier": -4,
    "key": "a suit of scale mail",
}

PLATEMAIL = {
    "prototype": "BASEARMOR",
    "damage_reduction": 6,
    "defense_modifier": -6,
    "key": "a suit of plate mail",
}
