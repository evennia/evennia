"""
Simple turn-based combat system with items and status effects

Contrib - Tim Ashley Jenkins 2017

This is a version of the 'turnbattle' combat system that includes
conditions and usable items, which can instill these conditions, cure
them, or do just about anything else.

Conditions are stored on characters as a dictionary, where the key
is the name of the condition and the value is a list of two items:
an integer representing the number of turns left until the condition
runs out, and the character upon whose turn the condition timer is
ticked down. Unlike most combat-related attributes, conditions aren't
wiped once combat ends - if out of combat, they tick down in real time
instead.

This module includes a number of example conditions:

    Regeneration: Character recovers HP every turn
    Poisoned: Character loses HP every turn
    Accuracy Up: +25 to character's attack rolls
    Accuracy Down: -25 to character's attack rolls
    Damage Up: +5 to character's damage
    Damage Down: -5 to character's damage
    Defense Up: +15 to character's defense
    Defense Down: -15 to character's defense
    Haste: +1 action per turn
    Paralyzed: No actions per turn
    Frightened: Character can't use the 'attack' command

Since conditions can have a wide variety of effects, their code is
scattered throughout the other functions wherever they may apply.

Items aren't given any sort of special typeclass - instead, whether or
not an object counts as an item is determined by its attributes. To make
an object into an item, it must have the attribute 'item_func', with
the value given as a callable - this is the function that will be called
when an item is used. Other properties of the item, such as how many
uses it has, whether it's destroyed when its uses are depleted, and such
can be specified on the item as well, but they are optional.

To install and test, import this module's TBItemsCharacter object into
your game's character.py module:

    from evennia.contrib.game_systems.turnbattle.tb_items import TBItemsCharacter

And change your game's character typeclass to inherit from TBItemsCharacter
instead of the default:

    class Character(TBItemsCharacter):

Next, import this module into your default_cmdsets.py module:

    from evennia.contrib.game_systems.turnbattle import tb_items

And add the battle command set to your default command set:

    #
    # any commands you add below will overload the default ones.
    #
    self.add(tb_items.BattleCmdSet())

This module is meant to be heavily expanded on, so you may want to copy it
to your game's 'world' folder and modify it there rather than importing it
in your game and using it as-is.
"""

from random import randint

from evennia import TICKER_HANDLER as tickerhandler
from evennia import Command, default_cmds
from evennia.commands.default.muxcommand import MuxCommand
from evennia.prototypes.spawner import spawn

from . import tb_basic

"""
----------------------------------------------------------------------------
OPTIONS
----------------------------------------------------------------------------
"""

TURN_TIMEOUT = 30  # Time before turns automatically end, in seconds
ACTIONS_PER_TURN = 1  # Number of actions allowed per turn
NONCOMBAT_TURN_TIME = 30  # Time per turn count out of combat

# Condition options start here.
# If you need to make changes to how your conditions work later,
# it's best to put the easily tweakable values all in one place!

REGEN_RATE = (4, 8)  # Min and max HP regen for Regeneration
POISON_RATE = (4, 8)  # Min and max damage for Poisoned
ACC_UP_MOD = 25  # Accuracy Up attack roll bonus
ACC_DOWN_MOD = -25  # Accuracy Down attack roll penalty
DMG_UP_MOD = 5  # Damage Up damage roll bonus
DMG_DOWN_MOD = -5  # Damage Down damage roll penalty
DEF_UP_MOD = 15  # Defense Up defense bonus
DEF_DOWN_MOD = -15  # Defense Down defense penalty

"""
----------------------------------------------------------------------------
COMBAT FUNCTIONS START HERE
----------------------------------------------------------------------------
"""


class ItemCombatRules(tb_basic.BasicCombatRules):
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
            This is where conditions affecting attack rolls are applied, as well.
            Accuracy Up and Accuracy Down are also accounted for in itemfunc_attack(),
            so that attack items' accuracy is affected as well.
        """
        # For this example, just return a random integer up to 100.
        attack_value = randint(1, 100)
        # Add to the roll if the attacker has the "Accuracy Up" condition.
        if "Accuracy Up" in attacker.db.conditions:
            attack_value += ACC_UP_MOD
        # Subtract from the roll if the attack has the "Accuracy Down" condition.
        if "Accuracy Down" in attacker.db.conditions:
            attack_value += ACC_DOWN_MOD
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
            This is where conditions affecting defense are accounted for.
        """
        # For this example, just return 50, for about a 50/50 chance of hit.
        defense_value = 50
        # Add to defense if the defender has the "Defense Up" condition.
        if "Defense Up" in defender.db.conditions:
            defense_value += DEF_UP_MOD
        # Subtract from defense if the defender has the "Defense Down" condition.
        if "Defense Down" in defender.db.conditions:
            defense_value += DEF_DOWN_MOD
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
            This is where conditions affecting damage are accounted for. Since attack items
            roll their own damage in itemfunc_attack(), their damage is unaffected by any
            conditions.
        """
        # For this example, just generate a number between 15 and 25.
        damage_value = randint(15, 25)
        # Add to damage roll if attacker has the "Damage Up" condition.
        if "Damage Up" in attacker.db.conditions:
            damage_value += DMG_UP_MOD
        # Subtract from the roll if the attacker has the "Damage Down" condition.
        if "Damage Down" in attacker.db.conditions:
            damage_value += DMG_DOWN_MOD
        return damage_value

    def resolve_attack(
        self,
        attacker,
        defender,
        attack_value=None,
        defense_value=None,
        damage_value=None,
        inflict_condition=[],
    ):
        """
        Resolves an attack and outputs the result.

        Args:
            attacker (obj): Character doing the attacking
            defender (obj): Character being attacked

        Options:
            attack_value (int): Override for attack roll
            defense_value (int): Override for defense value
            damage_value (int): Override for damage value
            inflict_condition (list): Conditions to inflict upon hit, a
                list of tuples formated as (condition(str), duration(int))

        Notes:
            This function is called by normal attacks as well as attacks
            made with items.
        """
        # Get an attack roll from the attacker.
        if not attack_value:
            attack_value = self.get_attack(attacker, defender)
        # Get a defense value from the defender.
        if not defense_value:
            defense_value = self.get_defense(attacker, defender)
        # If the attack value is lower than the defense value, miss. Otherwise, hit.
        if attack_value < defense_value:
            attacker.location.msg_contents("%s's attack misses %s!" % (attacker, defender))
        else:
            if not damage_value:
                damage_value = self.get_damage(attacker, defender)  # Calculate damage value.
            # Announce damage dealt and apply damage.
            attacker.location.msg_contents(
                "%s hits %s for %i damage!" % (attacker, defender, damage_value)
            )
            self.apply_damage(defender, damage_value)
            # Inflict conditions on hit, if any specified
            for condition in inflict_condition:
                self.add_condition(defender, attacker, condition[0], condition[1])
            # If defender HP is reduced to 0 or less, call at_defeat.
            if defender.db.hp <= 0:
                self.at_defeat(defender)

    def spend_item_use(self, item, user):
        """
        Spends one use on an item with limited uses.

        Args:
            item (obj): Item being used
            user (obj): Character using the item

        Notes:
            If item.db.item_consumable is 'True', the item is destroyed if it
            runs out of uses - if it's a string instead of 'True', it will also
            spawn a new object as residue, using the value of item.db.item_consumable
            as the name of the prototype to spawn.
        """
        item.db.item_uses -= 1  # Spend one use

        if item.db.item_uses > 0:  # Has uses remaining
            # Inform the player
            user.msg("%s has %i uses remaining." % (item.key.capitalize(), item.db.item_uses))

        else:  # All uses spent

            if not item.db.item_consumable:  # Item isn't consumable
                # Just inform the player that the uses are gone
                user.msg("%s has no uses remaining." % item.key.capitalize())

            else:  # If item is consumable
                # If the value is 'True', just destroy the item
                if item.db.item_consumable:
                    user.msg("%s has been consumed." % item.key.capitalize())
                    item.delete()  # Delete the spent item

                else:  # If a string, use value of item_consumable to spawn an object in its place
                    residue = spawn({"prototype": item.db.item_consumable})[0]  # Spawn the residue
                    # Move the residue to the same place as the item
                    residue.location = item.location
                    user.msg("After using %s, you are left with %s." % (item, residue))
                    item.delete()  # Delete the spent item

    def use_item(self, user, item, target):
        """
        Performs the action of using an item.

        Args:
            user (obj): Character using the item
            item (obj): Item being used
            target (obj): Target of the item use
        """
        # If item is self only and no target given, set target to self.
        if item.db.item_selfonly and target is None:
            target = user

        # If item is self only, abort use if used on others.
        if item.db.item_selfonly and user != target:
            user.msg("%s can only be used on yourself." % item)
            return

        # Set kwargs to pass to item_func
        kwargs = {}
        if item.db.item_kwargs:
            kwargs = item.db.item_kwargs

        # Match item_func string to function
        try:
            item_func = ITEMFUNCS[item.db.item_func]
        except KeyError:  # If item_func string doesn't match to a function in ITEMFUNCS
            user.msg("ERROR: %s not defined in ITEMFUNCS" % item.db.item_func)
            return

        # Call the item function - abort if it returns False, indicating an error.
        # This performs the actual action of using the item.
        # Regardless of what the function returns (if anything), it's still executed.
        if not item_func(item, user, target, **kwargs):
            return

        # If we haven't returned yet, we assume the item was used successfully.
        # Spend one use if item has limited uses
        if item.db.item_uses:
            self.spend_item_use(item, user)

        # Spend an action if in combat
        if self.is_in_combat(user):
            self.spend_action(user, 1, action_name="item")

    def condition_tickdown(self, character, turnchar):
        """
        Ticks down the duration of conditions on a character at the start of a given character's
        turn.

        Args:
            character (obj): Character to tick down the conditions of
            turnchar (obj): Character whose turn it currently is

        Notes:
            In combat, this is called on every fighter at the start of every character's turn. Out
            of combat, it's instead called when a character's at_update() hook is called, which is
            every 30 seconds by default.
        """

        for key in character.db.conditions:
            # The first value is the remaining turns - the second value is whose turn to count down
            # on.
            condition_duration = character.db.conditions[key][0]
            condition_turnchar = character.db.conditions[key][1]
            # If the duration is 'True', then the condition doesn't tick down - it lasts
            # indefinitely.
            if condition_duration is not True:
                # Count down if the given turn character matches the condition's turn character.
                if condition_turnchar == turnchar:
                    character.db.conditions[key][0] -= 1
                if character.db.conditions[key][0] <= 0:
                    # If the duration is brought down to 0, remove the condition and inform
                    # everyone.
                    character.location.msg_contents(
                        "%s no longer has the '%s' condition." % (str(character), str(key))
                    )
                    del character.db.conditions[key]

    def add_condition(self, character, turnchar, condition, duration):
        """
        Adds a condition to a fighter.

        Args:
            character (obj): Character to give the condition to
            turnchar (obj): Character whose turn to tick down the condition on in combat
            condition (str): Name of the condition
            duration (int or True): Number of turns the condition lasts, or True for indefinite
        """
        # The first value is the remaining turns - the second value is whose turn to count down on.
        character.db.conditions.update({condition: [duration, turnchar]})
        # Tell everyone!
        character.location.msg_contents("%s gains the '%s' condition." % (character, condition))

    # ----------------------------------------------------------------------------
    # ITEM FUNCTIONS START HERE
    # ----------------------------------------------------------------------------

    # These functions carry out the action of using an item - every item should
    # contain a db entry "item_func", with its value being a string that is
    # matched to one of these functions in the ITEMFUNCS dictionary below.

    # Every item function must take the following arguments:
    #     item (obj): The item being used
    #     user (obj): The character using the item
    #     target (obj): The target of the item use

    # Item functions must also accept **kwargs - these keyword arguments can be
    # used to define how different items that use the same function can have
    # different effects (for example, different attack items doing different
    # amounts of damage).

    # Each function below contains a description of what kwargs the function will
    # take and the effect they have on the result.

    def itemfunc_heal(self, item, user, target, **kwargs):
        """
        Item function that heals HP.

        kwargs:
            min_healing(int): Minimum amount of HP recovered
            max_healing(int): Maximum amount of HP recovered
        """
        if not target:
            target = user  # Target user if none specified

        if not target.attributes.has("max_hp"):  # Has no HP to speak of
            user.msg("You can't use %s on that." % item)
            return False  # Returning false aborts the item use

        if target.db.hp >= target.db.max_hp:
            user.msg("%s is already at full health." % target)
            return False

        min_healing = 20
        max_healing = 40

        # Retrieve healing range from kwargs, if present
        if "healing_range" in kwargs:
            min_healing = kwargs["healing_range"][0]
            max_healing = kwargs["healing_range"][1]

        to_heal = randint(min_healing, max_healing)  # Restore 20 to 40 hp
        if target.db.hp + to_heal > target.db.max_hp:
            to_heal = target.db.max_hp - target.db.hp  # Cap healing to max HP
        target.db.hp += to_heal

        user.location.msg_contents("%s uses %s! %s regains %i HP!" % (user, item, target, to_heal))

    def itemfunc_add_condition(self, item, user, target, **kwargs):
        """
        Item function that gives the target one or more conditions.

        kwargs:
            conditions (list): Conditions added by the item
               formatted as a list of tuples: (condition (str), duration (int or True))

        Notes:
            Should mostly be used for beneficial conditions - use itemfunc_attack
            for an item that can give an enemy a harmful condition.
        """
        conditions = [("Regeneration", 5)]

        if not target:
            target = user  # Target user if none specified

        if not target.attributes.has("max_hp"):  # Is not a fighter
            user.msg("You can't use %s on that." % item)
            return False  # Returning false aborts the item use

        # Retrieve condition / duration from kwargs, if present
        if "conditions" in kwargs:
            conditions = kwargs["conditions"]

        user.location.msg_contents("%s uses %s!" % (user, item))

        # Add conditions to the target
        for condition in conditions:
            self.add_condition(target, user, condition[0], condition[1])

    def itemfunc_cure_condition(self, item, user, target, **kwargs):
        """
        Item function that'll remove given conditions from a target.

        kwargs:
            to_cure(list): List of conditions (str) that the item cures when used
        """
        to_cure = ["Poisoned"]

        if not target:
            target = user  # Target user if none specified

        if not target.attributes.has("max_hp"):  # Is not a fighter
            user.msg("You can't use %s on that." % item)
            return False  # Returning false aborts the item use

        # Retrieve condition(s) to cure from kwargs, if present
        if "to_cure" in kwargs:
            to_cure = kwargs["to_cure"]

        item_msg = "%s uses %s! " % (user, item)

        for key in target.db.conditions:
            if key in to_cure:
                # If condition specified in to_cure, remove it.
                item_msg += "%s no longer has the '%s' condition. " % (str(target), str(key))
                del target.db.conditions[key]

        user.location.msg_contents(item_msg)

    def itemfunc_attack(self, item, user, target, **kwargs):
        """
        Item function that attacks a target.

        kwargs:
            min_damage(int): Minimum damage dealt by the attack
            max_damage(int): Maximum damage dealth by the attack
            accuracy(int): Bonus / penalty to attack accuracy roll
            inflict_condition(list): List of conditions inflicted on hit,
                formatted as a (str, int) tuple containing condition name
                and duration.

        Notes:
            Calls resolve_attack at the end.
        """
        if not self.is_in_combat(user):
            user.msg("You can only use that in combat.")
            return False  # Returning false aborts the item use

        if not target:
            user.msg("You have to specify a target to use %s! (use <item> = <target>)" % item)
            return False

        if target == user:
            user.msg("You can't attack yourself!")
            return False

        if not target.db.hp:  # Has no HP
            user.msg("You can't use %s on that." % item)
            return False

        min_damage = 20
        max_damage = 40
        accuracy = 0
        inflict_condition = []

        # Retrieve values from kwargs, if present
        if "damage_range" in kwargs:
            min_damage = kwargs["damage_range"][0]
            max_damage = kwargs["damage_range"][1]
        if "accuracy" in kwargs:
            accuracy = kwargs["accuracy"]
        if "inflict_condition" in kwargs:
            inflict_condition = kwargs["inflict_condition"]

        # Roll attack and damage
        attack_value = randint(1, 100) + accuracy
        damage_value = randint(min_damage, max_damage)

        # Account for "Accuracy Up" and "Accuracy Down" conditions
        if "Accuracy Up" in user.db.conditions:
            attack_value += 25
        if "Accuracy Down" in user.db.conditions:
            attack_value -= 25

        user.location.msg_contents("%s attacks %s with %s!" % (user, target, item))
        self.resolve_attack(
            user,
            target,
            attack_value=attack_value,
            damage_value=damage_value,
            inflict_condition=inflict_condition,
        )


COMBAT_RULES = ItemCombatRules()


# Match strings to item functions here. We can't store callables on
# prototypes, so we store a string instead, matching that string to
# a callable in this dictionary.
ITEMFUNCS = {
    "heal": COMBAT_RULES.itemfunc_heal,
    "attack": COMBAT_RULES.itemfunc_attack,
    "add_condition": COMBAT_RULES.itemfunc_add_condition,
    "cure_condition": COMBAT_RULES.itemfunc_cure_condition,
}

"""
----------------------------------------------------------------------------
PROTOTYPES START HERE
----------------------------------------------------------------------------

You can paste these prototypes into your game's prototypes.py module in your
/world/ folder, and use the spawner to create them - they serve as examples
of items you can make and a handy way to demonstrate the system for
conditions as well.

Items don't have any particular typeclass - any object with a db entry
"item_func" that references one of the functions given above can be used as
an item with the 'use' command.

Only "item_func" is required, but item behavior can be further modified by
specifying any of the following:

    item_uses (int): If defined, item has a limited number of uses

    item_selfonly (bool): If True, user can only use the item on themself

    item_consumable(True or str): If True, item is destroyed when it runs
        out of uses. If a string is given, the item will spawn a new
        object as it's destroyed, with the string specifying what prototype
        to spawn.

    item_kwargs (dict): Keyword arguments to pass to the function defined in
        item_func. Unique to each function, and can be used to make multiple
        items using the same function work differently.
"""

MEDKIT = {
    "key": "a medical kit",
    "aliases": ["medkit"],
    "desc": "A standard medical kit. It can be used a few times to heal wounds.",
    "item_func": "heal",
    "item_uses": 3,
    "item_consumable": True,
    "item_kwargs": {"healing_range": (15, 25)},
}

GLASS_BOTTLE = {"key": "a glass bottle", "desc": "An empty glass bottle."}

HEALTH_POTION = {
    "key": "a health potion",
    "desc": "A glass bottle full of a mystical potion that heals wounds when used.",
    "item_func": "heal",
    "item_uses": 1,
    "item_consumable": "GLASS_BOTTLE",
    "item_kwargs": {"healing_range": (35, 50)},
}

REGEN_POTION = {
    "key": "a regeneration potion",
    "desc": "A glass bottle full of a mystical potion that regenerates wounds over time.",
    "item_func": "add_condition",
    "item_uses": 1,
    "item_consumable": "GLASS_BOTTLE",
    "item_kwargs": {"conditions": [("Regeneration", 10)]},
}

HASTE_POTION = {
    "key": "a haste potion",
    "desc": "A glass bottle full of a mystical potion that hastens its user.",
    "item_func": "add_condition",
    "item_uses": 1,
    "item_consumable": "GLASS_BOTTLE",
    "item_kwargs": {"conditions": [("Haste", 10)]},
}

BOMB = {
    "key": "a rotund bomb",
    "desc": "A large black sphere with a fuse at the end. Can be used on enemies in combat.",
    "item_func": "attack",
    "item_uses": 1,
    "item_consumable": True,
    "item_kwargs": {"damage_range": (25, 40), "accuracy": 25},
}

POISON_DART = {
    "key": "a poison dart",
    "desc": "A thin dart coated in deadly poison. Can be used on enemies in combat",
    "item_func": "attack",
    "item_uses": 1,
    "item_consumable": True,
    "item_kwargs": {
        "damage_range": (5, 10),
        "accuracy": 25,
        "inflict_condition": [("Poisoned", 10)],
    },
}

TASER = {
    "key": "a taser",
    "desc": "A device that can be used to paralyze enemies in combat.",
    "item_func": "attack",
    "item_kwargs": {
        "damage_range": (10, 20),
        "accuracy": 0,
        "inflict_condition": [("Paralyzed", 1)],
    },
}

GHOST_GUN = {
    "key": "a ghost gun",
    "desc": "A gun that fires scary ghosts at people. Anyone hit by a ghost becomes frightened.",
    "item_func": "attack",
    "item_uses": 6,
    "item_kwargs": {
        "damage_range": (5, 10),
        "accuracy": 15,
        "inflict_condition": [("Frightened", 1)],
    },
}

ANTIDOTE_POTION = {
    "key": "an antidote potion",
    "desc": "A glass bottle full of a mystical potion that cures poison when used.",
    "item_func": "cure_condition",
    "item_uses": 1,
    "item_consumable": "GLASS_BOTTLE",
    "item_kwargs": {"to_cure": ["Poisoned"]},
}

AMULET_OF_MIGHT = {
    "key": "The Amulet of Might",
    "desc": "The one who holds this amulet can call upon its power to gain great strength.",
    "item_func": "add_condition",
    "item_selfonly": True,
    "item_kwargs": {"conditions": [("Damage Up", 3), ("Accuracy Up", 3), ("Defense Up", 3)]},
}

AMULET_OF_WEAKNESS = {
    "key": "The Amulet of Weakness",
    "desc": "The one who holds this amulet can call upon its power to gain great weakness. "
    "It's not a terribly useful artifact.",
    "item_func": "add_condition",
    "item_selfonly": True,
    "item_kwargs": {"conditions": [("Damage Down", 3), ("Accuracy Down", 3), ("Defense Down", 3)]},
}


"""
----------------------------------------------------------------------------
CHARACTER TYPECLASS
----------------------------------------------------------------------------
"""


class TBItemsCharacter(tb_basic.TBBasicCharacter):
    """
    A character able to participate in turn-based combat. Has attributes for current
    and maximum HP, and access to combat commands.
    """

    rules = ItemCombatRules()

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.
        """
        self.db.max_hp = 100  # Set maximum HP to 100
        self.db.hp = self.db.max_hp  # Set current HP to maximum
        self.db.conditions = {}  # Set empty dict for conditions
        # Subscribe character to the ticker handler
        tickerhandler.add(NONCOMBAT_TURN_TIME, self.at_update, idstring="update")
        """
        Adds attributes for a character's current and maximum HP.
        We're just going to set this value at '100' by default.

        An empty dictionary is created to store conditions later,
        and the character is subscribed to the Ticker Handler, which
        will call at_update() on the character, with the interval
        specified by NONCOMBAT_TURN_TIME above. This is used to tick
        down conditions out of combat.

        You may want to expand this to include various 'stats' that
        can be changed at creation and factor into combat calculations.
        """

    def at_turn_start(self):
        """
        Hook called at the beginning of this character's turn in combat.
        """
        # Prompt the character for their turn and give some information.
        self.msg("|wIt's your turn! You have %i HP remaining.|n" % self.db.hp)

        # Apply conditions that fire at the start of each turn.
        self.apply_turn_conditions()

    def apply_turn_conditions(self):
        """
        Applies the effect of conditions that occur at the start of each
        turn in combat, or every 30 seconds out of combat.
        """
        # Regeneration: restores 4 to 8 HP at the start of character's turn
        if "Regeneration" in self.db.conditions:
            to_heal = randint(REGEN_RATE[0], REGEN_RATE[1])  # Restore HP
            if self.db.hp + to_heal > self.db.max_hp:
                to_heal = self.db.max_hp - self.db.hp  # Cap healing to max HP
            self.db.hp += to_heal
            self.location.msg_contents("%s regains %i HP from Regeneration." % (self, to_heal))

        # Poisoned: does 4 to 8 damage at the start of character's turn
        if "Poisoned" in self.db.conditions:
            to_hurt = randint(POISON_RATE[0], POISON_RATE[1])  # Deal damage
            self.rules.apply_damage(self, to_hurt)
            self.location.msg_contents("%s takes %i damage from being Poisoned." % (self, to_hurt))
            if self.db.hp <= 0:
                # Call at_defeat if poison defeats the character
                self.rules.at_defeat(self)

        # Haste: Gain an extra action in combat.
        if self.rules.is_in_combat(self) and "Haste" in self.db.conditions:
            self.db.combat_actionsleft += 1
            self.msg("You gain an extra action this turn from Haste!")

        # Paralyzed: Have no actions in combat.
        if self.rules.is_in_combat(self) and "Paralyzed" in self.db.conditions:
            self.db.combat_actionsleft = 0
            self.location.msg_contents("%s is Paralyzed, and can't act this turn!" % self)
            self.db.combat_turnhandler.turn_end_check(self)

    def at_update(self):
        """
        Fires every 30 seconds.
        """
        if not self.rules.is_in_combat(self):  # Not in combat
            # Change all conditions to update on character's turn.
            for key in self.db.conditions:
                self.db.conditions[key][1] = self
            # Apply conditions that fire every turn
            self.apply_turn_conditions()
            # Tick down condition durations
            self.rules.condition_tickdown(self, self)


class TBItemsCharacterTest(TBItemsCharacter):
    """
    Just like the TBItemsCharacter, but doesn't subscribe to the TickerHandler.
    This makes it easier to run unit tests on.
    """

    def at_object_creation(self):
        self.db.max_hp = 100  # Set maximum HP to 100
        self.db.hp = self.db.max_hp  # Set current HP to maximum
        self.db.conditions = {}  # Set empty dict for conditions


"""
----------------------------------------------------------------------------
SCRIPTS START HERE
----------------------------------------------------------------------------
"""


class TBItemsTurnHandler(tb_basic.TBBasicTurnHandler):
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

    def next_turn(self):
        """
        Advances to the next character in the turn order.
        """
        super().next_turn()

        # Count down condition timers.
        next_fighter = self.db.fighters[self.db.turn]
        for fighter in self.db.fighters:
            self.rules.condition_tickdown(fighter, next_fighter)


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
    combat_handler_class = TBItemsTurnHandler


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
    combat_help_text = (
        "Available combat commands:|/"
        "|wAttack:|n Attack a target, attempting to deal damage.|/"
        "|wPass:|n Pass your turn without further action.|/"
        "|wDisengage:|n End your turn and attempt to end combat.|/"
        "|wUse:|n Use an item you're carrying."
    )


class CmdUse(MuxCommand):
    """
    Use an item.

    Usage:
      use <item> [= target]

    An item can have various function - looking at the item may
    provide information as to its effects. Some items can be used
    to attack others, and as such can only be used in combat.
    """

    key = "use"
    help_category = "combat"

    rules = COMBAT_RULES

    def func(self):
        """
        This performs the actual command.
        """
        # Search for item
        item = self.caller.search(self.lhs, candidates=self.caller.contents)
        if not item:
            return

        # Search for target, if any is given
        target = None
        if self.rhs:
            target = self.caller.search(self.rhs)
            if not target:
                return

        # If in combat, can only use items on your turn
        if self.rules.is_in_combat(self.caller):
            if not self.rules.is_turn(self.caller):
                self.caller.msg("You can only use items on your turn.")
                return

        if not item.db.item_func:  # Object has no item_func, not usable
            self.caller.msg("'%s' is not a usable item." % item.key.capitalize())
            return

        if item.attributes.has("item_uses"):  # Item has limited uses
            if item.db.item_uses <= 0:  # Limited uses are spent
                self.caller.msg("'%s' has no uses remaining." % item.key.capitalize())
                return

        # If everything checks out, call the use_item function
        self.rules.use_item(self.caller, item, target)


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
        self.add(CmdUse())
