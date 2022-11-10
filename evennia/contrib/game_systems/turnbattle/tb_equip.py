"""
Simple turn-based combat system with equipment

Contrib - Tim Ashley Jenkins 2017, Refactor by Griatch 2022

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

    from evennia.contrib.game_systems.turnbattle.tb_equip import TBEquipCharacter

And change your game's character typeclass to inherit from TBEquipCharacter
instead of the default:

    class Character(TBEquipCharacter):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.game_systems.turnbattle import tb_equip

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

from evennia import Command, DefaultObject, default_cmds

from . import tb_basic

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


class EquipmentCombatRules(tb_basic.BasicCombatRules):
    """
    Has all the methods of the basic combat, with the addition of equipment.

    """

    def get_attack(self, attacker, defender):
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

    def get_defense(self, attacker, defender):
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

    def get_damage(self, attacker, defender):
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

    def resolve_attack(self, attacker, defender, attack_value=None, defense_value=None):
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
            attack_value = self.get_attack(attacker, defender)
        # Get a defense value from the defender.
        if not defense_value:
            defense_value = self.get_defense(attacker, defender)
        # If the attack value is lower than the defense value, miss. Otherwise, hit.
        if attack_value < defense_value:
            attacker.location.msg_contents(
                "%s's %s misses %s!" % (attacker, attackers_weapon, defender)
            )
        else:
            damage_value = self.get_damage(attacker, defender)  # Calculate damage value.
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
            self.apply_damage(defender, damage_value)
            # If defender HP is reduced to 0 or less, call at_defeat.
            if defender.db.hp <= 0:
                self.at_defeat(defender)


COMBAT_RULES = EquipmentCombatRules()

"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBEquipTurnHandler(tb_basic.TBBasicTurnHandler):
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
TYPECLASSES START HERE
----------------------------------------------------------------------------
"""


class TBEWeapon(DefaultObject):
    """
    A weapon which can be wielded in combat with the 'wield' command.

    """

    rules = COMBAT_RULES

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.damage_range = (15, 25)  # Minimum and maximum damage on hit
        self.db.accuracy_bonus = 0  # Bonus to attack rolls (or penalty if negative)
        self.db.weapon_type_name = (
            "weapon"  # Single word for weapon - I.E. "dagger", "staff", "scimitar"
        )

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

    def at_pre_drop(self, dropper):
        """
        Can't drop in combat.
        """
        if self.rules.is_in_combat(dropper):
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

    def at_pre_give(self, giver, getter):
        """
        Can't give away in combat.
        """
        if self.rules.is_in_combat(giver):
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


class TBEquipCharacter(tb_basic.TBBasicCharacter):
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
    command_handler_class = TBEquipTurnHandler


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


class CmdRest(tb_basic.CmdRest):
    """
    Recovers damage.

    Usage:
      rest

    Resting recovers your HP to its maximum, but you can only
    rest if you're not in a fight.
    """

    key = "rest"
    help_category = "combat"

    rules = COMBAT_RULES


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

    rules = COMBAT_RULES


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

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.
        """
        # If in combat, check to see if it's your turn.
        if self.rules.is_in_combat(self.caller):
            if not self.rules.is_turn(self.caller):
                self.caller.msg("You can only do that on your turn.")
                return
        if not self.args:
            self.caller.msg("Usage: wield <obj>")
            return
        weapon = self.caller.search(self.args, candidates=self.caller.contents)
        if not weapon:
            return
        if not weapon.is_typeclass(
            "evennia.contrib.game_systems.turnbattle.tb_equip.TBEWeapon", exact=True
        ):
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
        if self.rules.is_in_combat(self.caller):
            self.rules.spend_action(self.caller, 1, action_name="wield")  # Use up one action.


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

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.
        """
        # If in combat, check to see if it's your turn.
        if self.rules.is_in_combat(self.caller):
            if not self.rules.is_turn(self.caller):
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

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.
        """
        # Can't do this in combat
        if self.rules.is_in_combat(self.caller):
            self.caller.msg("You can't don armor in a fight!")
            return
        if not self.args:
            self.caller.msg("Usage: don <obj>")
            return
        armor = self.caller.search(self.args, candidates=self.caller.contents)
        if not armor:
            return
        if not armor.is_typeclass(
            "evennia.contrib.game_systems.turnbattle.tb_equip.TBEArmor", exact=True
        ):
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

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.
        """
        # Can't do this in combat
        if self.rules.is_in_combat(self.caller):
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

BASEWEAPON = {"typeclass": "evennia.contrib.game_systems.turnbattle.tb_equip.TBEWeapon"}

BASEARMOR = {"typeclass": "evennia.contrib.game_systems.turnbattle.tb_equip.TBEArmor"}

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
