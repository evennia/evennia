"""
Simple turn-based combat system

Contrib - Tim Ashley Jenkins 2017

This is a framework for a simple turn-based combat system, similar
to those used in D&D-style tabletop role playing games. It allows
any character to start a fight in a room, at which point initiative
is rolled and a turn order is established. Each participant in combat
has a limited time to decide their action for that turn (30 seconds by
default), and combat progresses through the turn order, looping through
the participants until the fight ends.

Only simple rolls for attacking are implemented here, but this system
is easily extensible and can be used as the foundation for implementing
the rules from your turn-based tabletop game of choice or making your
own battle system.

To install and test, add the following to your settings.py file:

BASE_CHARACTER_TYPECLASS = "evennia.contrib.turnbattle.BattleCharacter"
CMDSET_CHARACTER = "evennia.contrib.turnbattle.CharacterCmdSet"

If you want to expand upon this system, it's recommended you copy the
code over to your game's modules and import from there instead.
"""

from evennia import Command
from evennia import default_cmds
from typeclasses.scripts import Script
from typeclasses.characters import Character
from commands.command import Command
from random import randint

class BattleCharacter(Character):
    
    def at_object_creation(self):
        """
        Adds attributes for a character's current and maximum HP.
        We're just going to set this value at '100' by default.
        
        You may want to expand this to include various 'stats' that
        can be changed at creation and factor into combat calculations.
        """
        self.db.max_hp = 100
        self.db.hp = self.db.max_hp
    pass
    def at_before_move(self, destination):
        """
        This keeps characters from moving when in combat or at 0 HP.
        """
        if is_in_combat(self):
            self.caller.msg("You can't exit a room while in combat!")
            return False # Returning false keeps the character from moving.
        if self.db.HP <= 0:
            self.caller.msg("You can't move, you've been defeated!")
            return False
        return True
    
class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    Adds combat commands to the default command set.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super(CharacterCmdSet, self).at_cmdset_creation()
        self.add(CmdFight())
        self.add(CmdAttack())
        self.add(CmdRest())
        self.add(CmdPass())
        self.add(CmdDisengage())
        
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
        
        if not self.caller.db.hp: # If you don't have any hp
            self.caller.msg("You can't start a fight if you've been defeated!")
            return
        for thing in here.contents: # Test everything in the room to add it to the fight.
            if thing.db.HP: # If the object has HP...
                fighters.append(thing) # ...then add it to the fight.
        if len(fighters) <= 1: # If you're the only able fighter in the room
            self.caller.msg("There's nobody here to fight!")
            return
        if here.db.Combat_TurnHandler: # If there's already a fight going on...
            here.msg_contents("%s joins the fight!" % self.caller)
            here.db.Combat_TurnHandler.join_fight(self.caller) # Join the fight!
            return
        here.msg_contents("%s starts a fight!" % self.caller)
        here.scripts.add("contrib.turnbattle.TurnHandler") # Add a turn handler script to the room, which starts combat.
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
        attacker = self.caller
        defender = self.caller.search(self.args)
        
        if not is_in_combat(self.caller): # If not in combat, can't attack.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return
        
        if not is_turn(self.caller): # If it's not your turn, can't attack.
            self.caller.msg("You can only do that on your turn.")
            return
            
        if not self.caller.db.hp: # Can't attack if you have no HP.
            self.caller.msg("You can't attack, you've been defeated.")
            return
        
        if not defender: # No valid target given.
            return
        
        if not defender.db.hp: # Target object has no HP left or to begin with
            self.caller.msg("You can't fight that!")
            return
        
        if attacker == defender: # Target and attacker are the same
            self.caller.msg("You can't attack yourself!")
            return
        
        "If everything checks out, call the attack resolving function."
        resolve_attack(attacker, defender)
        self.caller.db.Combat_LastAction = "attack"
        self.caller.db.Combat_ActionsLeft -= 1 # Use up one action.
        
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
        if not is_in_combat(self.caller): # Can only pass a turn in combat.
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return
        
        if not is_turn(self.caller): # Can only pass if it's your turn.
            self.caller.msg("You can only do that on your turn.")
            return
        
        self.caller.location.msg_contents("%s takes no further action, passing the turn." % self.caller)
        self.caller.db.Combat_LastAction = "pass"
        self.caller.db.Combat_ActionsLeft = 0

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
        if not is_in_combat(self.caller): # If you're not in combat
            self.caller.msg("You can only do that in combat. (see: help fight)")
            return
        
        if not is_turn(self.caller): # If it's not your turn
            self.caller.msg("You can only do that on your turn.")
            return
        
        self.caller.location.msg_contents("%s disengages, ready to stop fighting." % self.caller)
        self.caller.db.Combat_LastAction = "disengage" # This is checked by the turn handler to end combat if all disengage.
        self.caller.db.Combat_ActionsLeft = 0
        
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
        
        if is_in_combat(self.caller): # If you're in combat
            self.caller.msg("You can't rest while you're in combat.")
            return
        
        self.caller.db.hp = self.caller.db.max_hp # Set current HP to maximum
        self.caller.location.msg_contents("%s rests to recover HP." % self.caller)
        """
        You'll probably want to replace this with your own system for recovering HP.
        """

"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""

class TurnHandler(Script):
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
        self.interval = 1 # Once a second
        self.persistent = True
        self.db.fighters = []
        # Add all fighters in the room with at least 1 HP to the combat."
        for object in self.obj.contents:
            if object.db.hp:
                self.db.fighters.append(object)
        # Initialize each fighter for combat
        for fighter in self.db.fighters:
            combat_cleanup(fighter) #Clean up leftover combat attributes beforehand, just in case.
            fighter.db.Combat_ActionsLeft = 1 #Actions remaining - start of turn adds to this, turn ends when it reaches 0
            fighter.db.Combat_TurnHandler = self #Add a reference to this scrip to the character
            fighter.db.Combat_LastAction = "null" #Track last action taken in combat
        # Roll initiative and sort the list of fighters depending on who rolls highest to determine turn order.
        # The initiative roll is determined by the roll_init function and can be customized easily.
        ordered_by_roll = sorted(self.db.fighters, key=roll_init, reverse=True)
        self.db.fighters = ordered_by_roll
        # Announce the turn order.
        self.obj.msg_contents("Turn order is: %s " % ", ".join(obj.key for obj in self.db.fighters))
        "Set up the current turn and turn timeout delay."
        self.db.turn = 0
        self.db.timer = 30 # 30 seconds
        
    def at_stop(self):
        """
        Called at script termination.
        """
        for fighter in self.db.fighters:
            combat_cleanup(fighter) #Clean up the combat attributes for every fighter.
    
    def at_repeat(self):
        """
        Called once every self.interval seconds.
        """
        currentchar = self.db.fighters[self.db.turn] # Note the current character in the turn order.
        self.db.timer -= 1 # Count down the timer by one second.
        
        # If the current character has no actions remaining, go to the next turn.
        if not currentchar.db.Combat_ActionsLeft:
            self.next_turn()
            
        # Warn the current character if they're about to time out.
        if self.db.timer == 10: # 10 seconds left
            currentchar.msg("WARNING: About to time out!")
        
        # Force current character to disengage if timer runs out.
        if self.db.timer <= 0:
            currentchar.db.Combat_LastAction = "disengage" # Set last action to 'disengage'
            currentchar.db.Combat_ActionsLeft = 0 # Set actions remaining to 0
            self.obj.msg_contents("%s's turn timed out!" % currentchar)
            self.next_turn()
            
    def next_turn(self):
        """
        Advances to the next character in the turn order.
        """
        
        # Check to see if every character disengaged as their last action. If so, end combat.
        DisengageCheck = True
        for fighter in self.db.fighters:
            if fighter.db.Combat_LastAction != "disengage": # If a character has done anything but disengage
                DisengageCheck = False
        if DisengageCheck == True: # All characters have disengaged
            self.obj.msg_contents("All fighters have disengaged! Combat is over!")
            self.stop() # Stop this script and end combat.
            return
        
        # Check to see if only one character is left standing. If so, end combat.
        DefeatedCharacters = 0
        for fighter in self.db.fighters:
            if fighter.db.HP == 0:
                DefeatedCharacters += 1 # Add 1 for every fighter with 0 HP left (defeated)
        if DefeatedCharacters == (len(self.db.fighters) - 1): # If only one character isn't defeated
            for fighter in self.db.fighters:
                if fighter.db.HP != 0:
                    LastStanding = fighter # Pick the one fighter left with HP remaining
            self.obj.msg_contents("Only %s remains! Combat is over!" % LastStanding)
            self.stop() # Stop this script and end combat.
            return
            
        # Cycle to the next turn.
        currentchar = self.db.fighters[self.db.turn]
        self.db.turn += 1 # Go to the next in the turn order.
        if self.db.turn > len(self.db.fighters) - 1:
            self.db.turn = 0 # Go back to the first in the turn order once you reach the end.
        newchar = self.db.fighters[self.db.turn]
        self.db.timer = 30 # Reset the timer.
        self.obj.msg_contents("%s's turn ends - %s's turn begins!" % (currentchar, newchar))
        start_turn(newchar) # Start the new character's turn.
        
    def join_fight(self, character):
        """
        Adds a new character to a fight already in progress.
        """
        # Inserts the fighter to the turn order behind whoever's turn it currently is.
        self.db.fighters.insert(self.db.turn, character)
        # Tick the turn counter forward one to compensate.
        self.db.turn += 1
        # Initialize the character like you do at the start.
        combat_cleanup(fighter) # Clean up leftover combat attributes beforehand, just in case.
        fighter.db.Combat_ActionsLeft = 0 # Actions remaining - start of turn adds to this, turn ends when it reaches 0
        fighter.db.Combat_TurnHandler = self # Add a reference to this scrip to the character
        fighter.db.Combat_LastAction = "null" # Track last action taken in combat
        
    
    

"""
----------------------------------------------------------------------------
COMBAT FUNCTIONS START HERE
----------------------------------------------------------------------------
"""
def roll_init(character):
    """
    Rolls a number between 1-1000 to determine initiative.
    """
    return randint(1,1000)
    """
    Since the character is passed to this function, you can easily reference
    a character's stats to determine an initiative roll - for example, if your
    character has a 'dexterity' attribute, you can use it to give that character
    an advantage in turn order, like so:
    
    return (randint(1,20)) + character.db.dexterity
    
    This way, characters with a higher dexterity will go first more often.
    """
    
def start_turn(character):
    """
    Readies a character for the start of their turn.
    """
    character.db.Combat_ActionsLeft = 1 # 1 action per turn.
    """
    Here, you only get one action per turn, but you might want to allow more than
    one per turn, or even grant a number of actions based on a character's
    attributes. You can even add multiple different kinds of actions, I.E. actions
    separated for movement, by adding "character.db.Combat_MovesLeft = 3" or
    something similar.
    """
    # Prompt the character for their turn and give some information.
    character.msg("|wIt's your turn! You have %i HP remaining.|n" % character.db.hp)
    
    
    
def resolve_attack(attacker, defender):
    """
    Resolves an attack and outputs the result.
    """
    # Get an attack roll from the attacker.
    attack_value = get_attack(attacker, defender)
    # Get a defense value from the defender.
    defense_value = get_defense(attacker, defender)
    """
    Even though these functions are very simple, separating them out
    makes it much easier to make the calculations more involved later.
    """
    # If the attack value is lower than the defense value, miss. Otherwise, hit.
    if attack_value < defense_value:
        attacker.location.msg_contents("%s's attack misses %s!" % (attacker, defender))
    else:
        damage_value = get_damage(attacker, defender) # Calculate damage value.
        # Announce damage dealt and apply damage.
        attacker.location.msg_contents("%s hits %s for %i damage!" % (attacker, defender, damage_value))
        apply_damage (defender, damage_value)
        # If defender HP is reduced to 0 or less, announce defeat.
        if defender.db.hp <= 0:
            attacker.location.msg_contents("%s has been defeated!" % defender)
        
def get_attack(attacker, defender):
    """
    Returns a value for an attack roll.
    """
    # For this example, just return a random integer up to 100.
    attack_value = randint(1, 100)
    """
    This can easily be expanded to return a value based on characters stats,
    equipment, and abilities. This is why the attacker and defender are passed
    to this function, even though nothing from either one are used in this example.
    """
    return attack_value
    
def get_defense(attacker, defender):
    """
    Returns a value for defense for an attack roll to beat.
    """
    # For this example, just return 50, for about a 50/50 chance of hit.
    defense_value = 50
    """
    As above, this can be expanded upon based on character stats and equipment.
    """
    return defense_value
    
def get_damage(attacker, defender):
    """
    Returns a value for damage.
    """
    # For this example, just generate a number between 15 and 25.
    damage_value = randint(15, 25)
    """
    Again, this can be expanded upon.
    """
    return damage_value
    
def apply_damage(defender, damage):
    """
    Applies damage to a target, reducing their HP.
    """
    defender.db.hp -= damage # Reduce defender's HP by the damage dealt.
    # If this reduces it to 0 or less, set HP to 0.
    if defender.db.hp <= 0:
        defender.db.hp = 0
    
def combat_cleanup(character):
    """
    Cleans up all the temporary combat-related attributes on a character.
    """
    for attr in character.attributes.all():
        if attr.key[:7] == "combat_": # If the attribute name starts with 'combat_'...
            character.attributes.remove(key=attr.key) # ...then delete it!
            
def is_in_combat(character):
    """
    Returns true if the given character is in combat.
    """
    if character.db.Combat_TurnHandler:
        return True
    return False
        
def is_turn(character):
    """
    Returns true if it's the given character's turn in combat.
    """
    turnhandler = character.db.Combat_TurnHandler
    currentchar = turnhandler.db.fighters[turnhandler.db.turn]
    if character == currentchar:
        return True
    return False
    
