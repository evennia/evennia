# Twitch Combat 

In this lesson we will build upon the basic combat framework we devised [in the previous lesson](./Beginner-Tutorial-Combat-Base.md) to create a 'twitch-like' combat system. 
```shell
> attack troll 
  You attack the Troll! 

The Troll roars!

You attack the Troll with Sword: Roll vs armor(11):
 rolled 3 on d20 + strength(+1) vs 11 -> Fail
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 13 on d20 + strength(+3) vs 12 -> Success
 Troll hits you for 5 damage! 
 
You attack the Troll with Sword: Roll vs armor(11):
 rolled 14 on d20 + strength(+1) vs 11 -> Success
 You hit the Troll for 2 damage!
 
> look 
  A dark cave 
  
  Water is dripping from the ceiling. 
  
  Exits: south and west 
  Enemies: The Troll 
  --------- Combat Status ----------
  You (Wounded)  vs  Troll (Scraped)

> use potion 
  You prepare to use a healing potion! 
  
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 2 on d20 + strength(+3) vs 12 -> Fail
 
You use a healing potion. 
 You heal 4 damage. 
 
Troll attacks you with Terrible claws: Roll vs armor(12): 
 rolled 8 on d20 + strength(+3) vs 12 -> Fail
 
You attack the troll with Sword: Roll vs armor(11):
 rolled 20 on d20 + strength(+1) vs 11 -> Success (critical success)
 You critically hit the Troll for 8 damage! 
 The Troll falls to the ground, dead. 
 
The battle is over. You are still standing. 
```
> Note that this documentation doesn't show in-game colors. If you are interested in an alternative, see  the [next lesson](./Beginner-Tutorial-Combat-Turnbased.md), where we'll make a turnbased, menu-based system instead.

With "Twitch" combat, we refer to a type of combat system that runs without any clear divisions of 'turns' (the opposite of [Turn-based combat](./Beginner-Tutorial-Combat-Turnbased.md)). It is inspired by the way combat worked in the old  [DikuMUD](https://en.wikipedia.org/wiki/DikuMUD) codebase, but is more flexible. 

```{sidebar} Differences to DIKU combat
In DIKU, all actions in combat happen on a _global_ 'tick' of, say 3 seconds. In our system, each combatant have their own 'tick' which is completely independent of each other. Now, in Evadventure, each combatant will tick at the same rate and thus mimic DIKU ... but they don't _have_ to. 
```

Basically, a user enters an action and after a certain time that action will execute (normally an attack). If they don't do anything, the attack will repeat over and over (with a random result) until the enemy or you is defeated. 

You can change up your strategy by performing other actions (like drinking a potion or cast a spell). You can also simply move to another room to 'flee' the combat (but the enemy may of course follow you)

## General principle

```{sidebar}
An example of an implemented Twitch combat system can be found in `evennia/contrib/tutorials`, in [evadventure/combat_twitch.py](evennia.contrib.tutorials.evadventure.combat_twitch).
```
Here is the general design of the Twitch-based combat handler: 

- The twitch-version of the CombatHandler will be stored on each combatant whenever combat starts. When combat is over, or they leave the room with combat, the handler will be deleted. 
- The handler will queue each action independently, starting a timer until they fire.
- All input are handled via Evennia [Commands](../../../Components/Commands.md).

## Twitch combat handler

> Create a new module `evadventure/combat_twitch.py`.

We will make use of the _Combat Actions_, _Action dicts_ and the parent `EvAdventureCombatBaseHandler` [we created previously](./Beginner-Tutorial-Combat-Base.md). 

```python 
# in evadventure/combat_twitch.py

from .combat_base import (
   CombatActionAttack,
   CombatActionHold,
   CombatActionStunt,
   CombatActionUseItem,
   CombatActionWield,
   EvAdventureCombatBaseHandler,
)

from .combat_base import EvAdventureCombatBaseHandler

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):
    """
    This is created on the combatant when combat starts. It tracks only 
    the combatant's side of the combat and handles when the next action 
    will happen.
 
    """
 
    def msg(self, message, broadcast=True):
        """See EvAdventureCombatBaseHandler.msg"""
        super().msg(message, combatant=self.obj, 
                    broadcast=broadcast, location=self.obj.location)
```

We make a child class of `EvAdventureCombatBaseHandler` for our Twitch combat. The parent class is a [Script](../../../Components/Scripts.md), and when a Script sits 'on' an Object, that Object is available on the script as `self.obj`. Since this handler is meant to sit 'on' the combatant, then `self.obj` is thus the combatant and `self.obj.location` is the current room the combatant is in. By using `super()` we can reuse the parent class' `msg()` method with these Twitch-specific details.

### Getting the sides of combat

```python
# in evadventure/combat_twitch.py 

from evennia.utils import inherits_from

# ...

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ... 

    def get_sides(self, combatant):
         """
         Get a listing of the two 'sides' of this combat, from the 
         perspective of the provided combatant. The sides don't need 
         to be balanced.
 
         Args:
             combatant (Character or NPC): The basis for the sides.
             
         Returns:
             tuple: A tuple of lists `(allies, enemies)`, from the 
                 perspective of `combatant`. Note that combatant itself 
                 is not included in either of these.

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

```

Next we add our own implementation of the `get_sides()` method. This presents the sides of combat from the perspective of the provided `combatant`. In Twitch combat, there are a few things that identifies a combatant: 

- That they are in the same location
- That they each have a `EvAdventureCombatTwitchHandler` script running on themselves

```{sidebar} inherits_from 
Since `inherits_from` is True if your class inherits from the parent at _any_ distance, this particular check would not work if you were to change the NPC class to inherit from our Character class as well. In that case we'd have to come up with some other way to compare the two types of entities.
```
In a PvP-open room, it's all for themselves - everyone else is considered an 'enemy'.  Otherwise we separate PCs from NPCs by seeing if they inherit from `EvAdventureCharacter` (our PC class) or not - if you are a PC, then the NPCs are your enemies and vice versa. The [inherits_from](evennia.utils.utils.inherits_from) is very useful for doing these checks - it will pass also if you inherit from `EvAdventureCharacter` at _any_ distance.

Note that `allies` does not include the `combatant` itself, so if you are fighting a lone enemy, the return from this method will be `([], [enemy_obj])`.

### Tracking Advantage / Disadvantage 

```python
# in evadventure/combat_twitch.py 

from evennia import AttributeProperty

# ... 

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    self.advantage_against = AttributeProperty(dict) 
    self.disadvantage_against = AttributeProperty(dict)

    # ... 

    def give_advantage(self, recipient, target):
        """Let a recipient gain advantage against the target."""
        self.advantage_against[target] = True

    def give_disadvantage(self, recipient, target):
        """Let an affected party gain disadvantage against a target."""
        self.disadvantage_against[target] = True

    def has_advantage(self, combatant, target):
        """Check if the combatant has advantage against a target."""
        return self.advantage_against.get(target, False)

    def has_disadvantage(self, combatant, target):
        """Check if the combatant has disadvantage against a target."""
        return self.disadvantage_against.get(target, False)1

```

As seen in the previous lesson, the Actions call these methods to store the fact that 
a given combatant has advantage. 

In this Twitch-combat case, the one getting the advantage is always one on which the combathandler is defined, so we don't actually need to use the `recipient/combatant` argument (it's always going to be `self.obj`) - only `target` is important.

We create two new Attributes to store the relation as dicts. 

### Queue action 

```{code-block} python
:linenos:
:emphasize-lines: 17,26,30,43,44, 48, 49
# in evadventure/combat_twitch.py 

from evennia.utils import repeat, unrepeat
from .combat_base import (
    CombatActionAttack,
    CombatActionHold,
    CombatActionStunt,
    CombatActionUseItem,
    CombatActionWield,
    EvAdventureCombatBaseHandler,
)

# ... 

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    action_classes = {
         "hold": CombatActionHold,
         "attack": CombatActionAttack,
         "stunt": CombatActionStunt,
         "use": CombatActionUseItem,
         "wield": CombatActionWield,
     }

    action_dict = AttributeProperty(dict, autocreate=False)
    current_ticker_ref = AttributeProperty(None, autocreate=False)

    # ... 

    def queue_action(self, action_dict, combatant=None):
        """
        Schedule the next action to fire.

        Args:
            action_dict (dict): The new action-dict to initialize.
            combatant (optional): Unused.

        """
        if action_dict["key"] not in self.action_classes:
            self.obj.msg("This is an unknown action!")
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
                # always schedule the task to be repeating, cancel later
                # otherwise. We store the tickerhandler's ref to make sure 
                # we can remove it later
            self.current_ticker_ref = repeat(
                dt, self.execute_next_action, id_string="combat")

```

- **Line 30**: The `queue_action` method takes an "Action dict" representing an action the combatant wants to perform next. It must be one of the keyed Actions added to the handler in the `action_classes` property (**Line 17**). We make no use of the `combatant` keyword argument since we already know that the combatant is `self.obj`. 
- **Line 43**: We simply store the given action dict in the Attribute `action_dict` on the handler. Simple and effective!
- **Line 44**: When you enter e.g. `attack`, you expect in this type of combat to see the `attack` command repeat automatically even if you don't enter anything more. To this end we are looking for a new key in action dicts, indicating that this action should _repeat_ with a certain rate (`dt`, given in seconds).  We make this compatible with all action dicts by simply assuming it's zero if not specified. 

 [evennia.utils.utils.repeat](evennia.utils.utils.repeat) and [evennia.utils.utils.unrepeat](evennia.utils.utils.unrepeat) are convenient shortcuts to the [TickerHandler](../../../Components/TickerHandler.md). You tell `repeat` to call a given method/function at a certain rate. What you get back is a reference that you can then later use to 'un-repeat' (stop the repeating) later.  We make sure to store this reference (we don't care exactly how it looks, just that we need to store it) in the `current_ticker_ref` Attribute (**Line 26**).
 
- **Line 48**: Whenever we queue a new action (it may replace an existing one) we must make sure to kill (un-repeat) any old repeats that are ongoing. Otherwise we would get old actions firing over and over and new ones starting alongside them.
- **Line 49**: If `dt` is set, we call `repeat` to set up a new repeat action at the given rate. We store this new reference. After `dt` seconds, the `.execute_next_action` method will fire (we'll create that in the next section).

### Execute an action 

```{code-block} python
:linenos:
:emphasize-lines: 5,15,16,18,22,27

# in evadventure/combat_twitch.py

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    fallback_action_dict = AttributeProperty({"key": "hold", "dt": 0})

    # ... 

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
```

This is the method called after `dt` seconds in `queue_action`. 

- **Line 5**: We defined a 'fallback action'. This is used after a one-time action (one that should not repeat) has completed.
- **Line 15**: We take the `'key'` from the `action_dict` and use the `action_classes` mapping to get an action class (e.g. `ActionAttack` we defined [here](./Beginner-Tutorial-Combat-Base.md#attack-action)). 
- **Line 16**: Here we initialize the action class with the actual current data - the combatant and the `action_dict`. This calls the `__init__` method on the class and makes the action ready to use.
```{sidebar} New action-dict keys 
To summarize, for twitch-combat use we have now introduced two new keys to action-dicts:
- `dt`: How long to wait (in seconds) from queueing the action until it fires. 
- `repeat`: Boolean determining if action should automatically be queued again after it fires.
```
- **Line 18**: Here we run through the usage methods of the action - where we perform the action. We let the action itself handle all the logics.
- **Line 22**: We check for another optional flag on the action-dict: `repeat`. Unless it's set, we use the fallback-action defined on **Line 5**. Many actions should not repeat - for example, it would not make sense to do `wield` for the same weapon over and over.
- **Line 27**: It's important that we know how to stop combat. We will write this method next.

### Checking and stopping combat

```{code-block} python 
:linenos: 
:emphasize-lines: 12,18,19

# in evadventure/combat_twitch.py 

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ... 

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
            self.msg("The combat is over. No one stands.", broadcast=False)
            self.stop_combat()
            return
        if not allies: 
            self.msg("The combat is over. You lost.", broadcast=False)
            self.stop_combat()
        if not enemies:
            self.msg("The combat is over. You won!", broadcast=False)
            self.stop_combat()

    def stop_combat(self):
        pass  # We'll finish this last
```

We must make sure to check if combat is over. 

- **Line 12**: With our `.get_sides()` method we can easily get the two sides of the conflict.
- **Lines 18, 19**: We get everyone still alive _and still in the same room_. The latter condition is important in case we move away from the battle - you can't hit your enemy from another room. 

In the `stop_combat` method we'll need to do a bunch of cleanup. We'll hold off on implementing this until we have the Commands written out. Read on.

## Commands 

We want each action to map to a [Command](../../../Components/Commands.md) - an actual input the player can pass to the game.  

### Base Combat class 

We should try to find the similarities between the commands we'll need and group them into one parent class. When a Command fires, it will fire the following methods on itself, in sequence: 

1. `cmd.at_pre_command()`
2. `cmd.parse()`
3. `cmd.func()`
4. `cmd.at_post_command()`

We'll override the first two for our parent. 

```{code-block} python
:linenos: 
:emphasize-lines: 23,49

# in evadventure/combat_twitch.py

from evennia import Command
from evennia import InterruptCommand 

# ... 

# after the combat handler class

class _BaseTwitchCombatCommand(Command):
    """
    Parent class for all twitch-combat commands.

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

    def get_or_create_combathandler(self, target=None, combathandler_name="combathandler"):
        """
        Get or create the combathandler assigned to this combatant.

        """
        if target:
            # add/check combathandler to the target
            if target.hp_max is None:
                self.msg("You can't attack that!")
                raise InterruptCommand()

            EvAdventureCombatTwitchHandler.get_or_create_combathandler(target)
        return EvAdventureCombatTwitchHandler.get_or_create_combathandler(self.caller)
```

- **Line 23**: If the current location doesn't allow combat, all combat commands should exit immediately. To stop the command before it reaches the `.func()`, we must raise the `InterruptCommand()`. 
- **Line 49**: It's convenient to add a helper method for getting the command handler because all our commands will be using it. It in turn calls the class method `get_or_create_combathandler` we inherit from the parent of `EvAdventureCombatTwitchHandler`. 

### In-combat look command

```python
# in evadventure/combat_twitch.py 

from evennia import default_cmds
from evennia.utils import pad

# ...

class CmdLook(default_cmds.CmdLook, _BaseTwitchCombatCommand):
    def func(self):
        # get regular look, followed by a combat summary
        super().func()
        if not self.args:
            combathandler = self.get_or_create_combathandler()
            txt = str(combathandler.get_combat_summary(self.caller))
            maxwidth = max(display_len(line) for line in txt.strip().split("\n"))
            self.msg(f"|r{pad(' Combat Status ', width=maxwidth, fillchar='-')}|n\n{txt}")
```

When in combat we want to be able to do `look` and get the normal look but with the extra `combat summary` at the end (on the form `Me (Hurt)  vs  Troll (Perfect)`). So 

The last line uses Evennia's `utils.pad` function to put the text "Combat Status" surrounded by a line on both sides.

The result will be the look command output followed directly by 

```shell
--------- Combat Status ----------
You (Wounded)  vs  Troll (Scraped)
```

### Hold command 

```python
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
```

The 'do nothing' command showcases the basic principle of how all following commands work: 

1. Get the combathandler (will be created or loaded if it already existed). 
2. Queue the action by passing its action-dict to the `combathandler.queue_action` method.
3. Confirm to the caller that they now queued this action. 

### Attack command 

```python
# in evadventure/combat_twitch.py 

# ... 

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
        combathandler.queue_action(
            {"key": "attack", 
             "target": target, 
             "dt": 3, 
             "repeat": True}
        )
        combathandler.msg(f"$You() $conj(attack) $You({target.key})!", self.caller)
```

The `attack` command becomes quite simple because we do all the heavy lifting in the combathandler and in the `ActionAttack` class. Note that we set `dt` to a fixed `3` here, but in a more complex system one could imagine your skills, weapon and circumstance affecting how long your attack will take.

```python
# in evadventure/combat_twitch.py 

from .enums import ABILITY_REVERSE_MAP

# ... 

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
        # if any values are still None at this point, we can't continue
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

```

This looks much longer, but that is only because the stunt command should understand many different input structures depending on if you are trying to create an advantage or disadvantage, and if an ally or enemy should receive the effect of the stunt. 

Note the `enums.ABILITY_REVERSE_MAP` (created in the [Utilities lesson](./Beginner-Tutorial-Utilities.md)) being useful to convert your input of 'str' into `Ability.STR` needed by the action dict.

Once we've sorted out the string parsing, the `func` is simple - we find the target and recipient and use them to build the needed action-dict to queue. 

### Using items 

```python
# in evadventure/combat_twitch.py 

# ... 

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
            self.item,
            candidates=self.caller.equipment.get_usable_objects_from_backpack()
        )
        if not item:
            self.msg("(You must carry the item to use it.)")
            return
        if self.target:
            target = self.caller.search(self.target)
            if not target:
                return

        combathandler = self.get_or_create_combathandler(self.target)
        combathandler.queue_action(
            {"key": "use", 
             "item": item, 
             "target": target, 
             "dt": 3}
        )
        combathandler.msg(
            f"$You() prepare to use {item.get_display_name(self.caller)}!", self.caller
        )
```

To use an item, we need to make sure we are carrying it. Luckily our work in the [Equipment lesson](./Beginner-Tutorial-Equipment.md) gives us easy methods we can use to search for suitable objects.

### Wielding new weapons and equipment

```python
# in evadventure/combat_twitch.py 

# ... 

class CmdWield(_BaseTwitchCombatCommand):
    """
    Wield a weapon or spell-rune. You wield the item,
        swapping with any other item(s) you were wielding before.

    Usage:
      wield <weapon or spell>

    Examples:
      wield sword
      wield shield
      wield fireball

    Note that wielding a shield will not replace the sword in your hand, 
        while wielding a two-handed weapon (or a spell-rune) will take 
        two hands and swap out what you were carrying.

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

```

The Wield command follows the same pattern as other commands.

## Grouping Commands for use 

To make these commands available to use we must add them to a [Command Set](../../../Components/Command-Sets.md). 

```python 
# in evadventure/combat_twitch.py 

from evennia import CmdSet

# ... 

# after the commands 

class TwitchCombatCmdSet(CmdSet):
    """
    Add to character, to be able to attack others in a twitch-style way.
    """

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

    def at_cmdset_creation(self):
        self.add(CmdLook())


```

The first cmdset, `TwitchCombatCmdSet` is intended to be added to the Character. We can do so permanently by adding the cmdset to the default character cmdset (as outlined in the [Beginner Command lesson](../Part1/Beginner-Tutorial-Adding-Commands.md)). In the testing section below, we'll do this in another way.

What about that `TwitchLookCmdSet`? We can't add it to our character permanently, because we only want this particular version of `look` to operate while we are in combat. 

We must make sure to add and clean this up when combat starts and ends.

### Combat startup and cleanup

```{code-block} python 
:linenos: 
:emphasize-lines: 9,13,14,15,16

# in evadventure/combat_twitch.py

# ... 

class EvAdventureCombatTwitchHandler(EvAdventureCombatBaseHandler):

    # ... 

    def at_init(self): 
        self.obj.cmdset.add(TwitchLookCmdSet, persistent=False)

    def stop_combat(self): 
        self.queue_action({"key": "hold", "dt": 0})  # make sure ticker is killed
        del self.obj.ndb.combathandler
        self.obj.cmdset.remove(TwitchLookCmdSet)
        self.delete()
```

Now that we have the Look command set, we can finish the Twitch combat handler. 

- **Line 9**: The `at_init` method is a standard Evennia method available on all typeclassed entities (including `Scripts`, which is what our combat handler is). Unlike `at_object_creation` (which only fires once, when the object is first created), `at_init` will be called every time the object is loaded into memory (normally after you do a server `reload`). So we add the `TwitchLookCmdSet` here. We do so non-persistently, since we don't want to get an ever growing number of cmdsets added every time we reload. 
- **Line 13**: By queuing a hold action with `dt` of `0`, we make sure to kill the `repeat` action that is going on. If not, it would still fire later - and find that the combat handler is gone. 
- **Line 14**: If looking at how we defined the `get_or_create_combathandler` classmethod (the one we have been using to get/create the combathandler during the combat), you'll see that it caches the handler as `.ndb.combathandler` on the object we send to it. So we delete that cached reference here to make sure it's gone. 
- **Line 15**: We remove the look-cmdset from ourselves (remember `self.obj` is you, the combatant that now just finished combat).
- **Line 16**: We delete the combat handler itself. 


## Unit Testing 

```{sidebar} 
For examples of unit tests, see `evennia/contrib/tutorials`, in [evadventure/tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat) for an example of a full suite of combat tests.
```

> Create `evadventure/tests/test_combat.py` (if you don't already have it).

Both the Twitch command handler and commands can and should be unit tested.  Testing of commands are made easier by Evennia's special `EvenniaCommandTestMixin` class. This makes the `.call` method available and makes it easy to check if a command returns what you expect. 

Here's an example: 

```python 
# in evadventure/tests/test_combat.py 

from unittest.mock import Mock, patch
from evennia.utils.test_resources import EvenniaCommandTestMixin

from .. import combat_twitch

# ...

class TestEvAdventureTwitchCombat(EvenniaCommandTestMixin):

    def setUp(self): 
        self.combathandler = (
                combat_twitch.EvAdventureCombatTwitchHandler.get_or_create_combathandler(
            self.char1, key="combathandler") 
        )
   
    @patch("evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evadventure.combat_twitch.repeat", new=Mock())
    def test_hold_command(self): 
        self.call(combat_twitch, CmdHold(), "", "You hold back, doing nothing.")
        self.assertEqual(self.combathandler.action_dict, {"key": "hold"})
            
```

The `EvenniaCommandTestMixin` has a few default objects, including `self.char1`, which we make use of here. 

The two `@patch` lines are Python [decorators](https://realpython.com/primer-on-python-decorators/) that 'patch' the `test_hold_command` method. What they do is basically saying "in the following method, whenever any code tries to access `evadventure.combat_twitch.un/repeat`, just return a Mocked object instead".

We do this patching as an easy way to avoid creating timers in the unit test - these timers would finish after the test finished (which includes deleting its objects) and thus fail. 

Inside the test, we use the `self.call()` method to explicitly fire the Command (with no argument) and check that the output is what we expect.  Lastly we check that the combathandler is set up correctly, having stored the action-dict on itself. 

## A small combat test

```{sidebar}
You can find an example batch-command script at `evennia/contrib/tutorials/evadventure`, in [batchscripts/twitch_combat_demo.ev](github:evennia/contrib/tutorials/evadventure/batchscripts/twitch_combat_demo.ev)
```
Showing that the individual pieces of code works (unit testing) is not enough to be sure that your combat system is actually working. We need to test all the pieces _together_. This is often called _functional testing_. While functional testing can also be automated, wouldn't it be fun to be able to actually see our code in action? 

This is what we need for a minimal test: 

 - A room with combat enabled. 
 - An NPC to attack (it won't do anything back yet since we haven't added any AI)
 - A weapon we can `wield` 
 - An item (like a potion) we can `use`. 

While you can create these manually in-game, it can be convenient to create a [batch-command script](../../../Components/Batch-Command-Processor.md) to set up your testing environment. 

> create a new subfolder `evadventure/batchscripts/`  (if it doesn't already exist)


> create a new file `evadventure/combat_demo.ev`  (note, it's `.ev` not `.py`!) 

A batch-command file is a text file with normal in-game commands, one per line, separated by lines starting with `#` (these are required between all command lines). Here's how it looks: 

```
# Evadventure combat demo 

# start from limbo

tel #2

# turn ourselves into a evadventure-character

type self = evadventure.characters.EvAdventureCharacter

# assign us the twitch combat cmdset (requires superuser/developer perms)

py self.cmdset.add("evadventure.combat_twitch.TwitchCombatCmdSet", persistent=True)

# Create a weapon in our inventory (using all defaults)

create sword:evadventure.objects.EvAdventureWeapon

# create a consumable to use

create potion:evadventure.objects.EvAdventureConsumable

# dig a combat arena

dig arena:evadventure.rooms.EvAdventureRoom = arena,back

# go to arena

arena

# allow combat in this room

set here/allow_combat = True

# create a dummy enemy to hit on

create/drop dummy puppet;dummy:evadventure.npcs.EvAdventureNPC

# describe the dummy

desc dummy = This is is an ugly training dummy made out of hay and wood.

# make the dummy crazy tough

set dummy/hp_max = 1000

# 

set dummy/hp = 1000
```

Log into the game with a developer/superuser account and run

    > batchcmd evadventure.batchscripts.twitch_combat_demo 
    
This should place you in the arena with the dummy (if not, check for errors in the output! Use `objects` and `delete` commands to list and delete objects if you need to start over. )

You can now try `attack dummy` and should be able to pound away at the dummy (lower its health to test destroying it). Use `back` to 'flee' the combat. 

## Conclusions 

This was a big lesson! Even though our combat system is not very complex, there are still many moving parts to keep in mind. 

Also, while pretty simple, there is also a lot of growth possible with this system. You could easily expand from this or use it as inspiration for your own game.

Next we'll try to achieve the same thing within a turn-based framework! 