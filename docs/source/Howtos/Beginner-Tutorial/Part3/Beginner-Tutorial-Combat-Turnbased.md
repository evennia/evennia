# Turnbased Combat

In this lesson we will be building on the [combat base](./Beginner-Tutorial-Combat-Base.md) to implement a combat system that works in turns and where you select your actions in a menu, like this:

```shell

> attack Troll
______________________________________________________________________________

 You (Perfect)  vs  Troll (Perfect)
 Your queued action: [attack] (22s until next round,
 or until all combatants have chosen their next action).
______________________________________________________________________________

 1: attack an enemy
 2: Stunt - gain a later advantage against a target
 3: Stunt - give an enemy disadvantage against yourself or an ally
 4: Use an item on yourself or an ally
 5: Use an item on an enemy
 6: Wield/swap with an item from inventory
 7: flee!
 8: hold, doing nothing

> 4
_______________________________________________________________________________

Select the item
_______________________________________________________________________________

 1: Potion of Strength
 2. Potion of Dexterity
 3. Green Apple
 4. Throwing Daggers
 back
 abort

> 1
_______________________________________________________________________________

Choose an ally to target.
_______________________________________________________________________________

 1: Yourself
 back
 abort

> 1
_______________________________________________________________________________

 You (Perfect)  vs Troll (Perfect)
 Your queued action: [use] (6s until next round,
 or until all combatants have chosen their next action).
_______________________________________________________________________________

 1: attack an enemy
 2: Stunt - gain a later advantage against a target
 3: Stunt - give an enemy disadvantage against yourself or an ally
 4: Use an item on yourself or an ally
 5: Use an item on an enemy
 6: Wield/swap with an item from inventory
 7: flee!
 8: hold, doing nothing

Troll attacks You with Claws: Roll vs armor (12):
 rolled 4 on d20 + strength(+3) vs 12 -> Fail
 Troll missed you.

You use Potion of Strength.
 Renewed strength coarses through your body!
 Potion of Strength was used up.
```
> Note that this documentation doesn't show in-game colors. Also, if you interested in an alternative, see the [previous lesson](./Beginner-Tutorial-Combat-Twitch.md) where we implemented a 'twitch'-like combat system based on entering direct commands for every action.

With 'turnbased' combat, we mean combat that 'ticks' along at a slower pace, slow enough to allow the participants to select their options in a menu (the menu is not strictly necessary, but it's a good way to learn how to make menus as well). Their actions are queued and will be executed when the turn timer runs out. To avoid waiting unnecessarily, we will also move on to the next round whenever everyone has made their choices.

The advantage of a turnbased system is that it removes player speed from the equation; your prowess in combat does not depend on how quickly you can enter a command. For RPG-heavy games you could also allow players time to make RP emotes during the rounds of combat to flesh out the action.

The advantage of using a menu is that you have all possible actions directly available to you, making it beginner friendly and easy to know what you can do. It also means a lot less writing which can be an advantage to some players.

## General Principle

```{sidebar}
An example of an implemented Turnbased combat system can be found under `evennia/contrib/tutorials/evadventure/`, in [combat_turnbased.py](evennia.contrib.tutorials.evadventure.combat_turnbased).
```
Here is the general principle of the Turnbased combat handler:

- The turnbased version of the CombatHandler will be stored on the _current location_. That means that there will only be one combat per location. Anyone else starting combat will join the same handler and be assigned a side to fight on.
- The handler will run a central timer of 30s (in this example). When it fires, all queued actions will be executed. If everyone has submitted their actions, this will happen immediately when the last one submits.
- While in combat you will not be able to move around - you are stuck in the room. Fleeing combat is a separate action that takes a few turns to complete (we will need to create this).
- Starting the combat is done via the `attack <target>` command. After that you are in the combat menu and will use the menu for all subsequent actions.

## Turnbased combat handler

> Create a new module `evadventure/combat_turnbased.py`.

```python
# in evadventure/combat_turnbased.py

from .combat_base import (
   CombatActionAttack,
   CombatActionHold,
   CombatActionStunt,
   CombatActionUseItem,
   CombatActionWield,
   EvAdventureCombatBaseHandler,
)

from .combat_base import EvAdventureCombatBaseHandler

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": None # we will add this soon!
    }

    # fallback action if not selecting anything
    fallback_action_dict = AttributeProperty({"key": "hold"}, autocreate=False)

	# track which turn we are on
    turn = AttributeProperty(0)
    # who is involved in combat, and their queued action
    # as {combatant: actiondict, ...}
    combatants = AttributeProperty(dict)

    # who has advantage against whom. This is a structure
    # like {"combatant": {enemy1: True, enemy2: True}}
    advantage_matrix = AttributeProperty(defaultdict(dict))
    # same for disadvantages
    disadvantage_matrix = AttributeProperty(defaultdict(dict))

    # how many turns you must be fleeing before escaping
    flee_timeout = AttributeProperty(1, autocreate=False)

	# track who is fleeing as {combatant: turn_they_started_fleeing}
    fleeing_combatants = AttributeProperty(dict)

    # list of who has been defeated so far
    defeated_combatants = AttributeProperty(list)

```

We leave a placeholder for the `"flee"` action since we haven't created it yet.

Since the turnbased combat handler is shared between all combatants, we need to store references to those combatants on the handler, in the `combatants` [Attribute](Attribute).  In the same way we must store a _matrix_ of who has advantage/disadvantage against whom. We must also track who is _fleeing_, in particular how long they have been fleeing, since they will be leaving combat after that time.

### Getting the sides of combat

The two sides are different depending on if we are in an [PvP room](./Beginner-Tutorial-Rooms.md) or not: In a PvP room everyone else is your enemy. Otherwise only NPCs in combat is your enemy (you are assumed to be teaming up with your fellow players).

```python
# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

	# ...

    def get_sides(self, combatant):
           """
           Get a listing of the two 'sides' of this combat,
           from the perspective of the provided combatant.
           """
           if self.obj.allow_pvp:
               # in pvp, everyone else is an ememy
               allies = [combatant]
               enemies = [comb for comb in self.combatants if comb != combatant]
           else:
               # otherwise, enemies/allies depend on who combatant is
               pcs = [comb for comb in self.combatants if inherits_from(comb, EvAdventureCharacter)]
               npcs = [comb for comb in self.combatants if comb not in pcs]
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

Note that since the `EvadventureCombatBaseHandler` (which our turnbased handler is based on) is a [Script](../../../Components/Scripts.md), it provides many useful features. For example `self.obj` is the entity on which this Script 'sits'. Since we are planning to put this handler on the current location, then `self.obj` will be that Room.

All we do here is check if it's a PvP room or not and use this to figure out who would be an ally or an enemy. Note that the `combatant` is _not_ included in the `allies` return - we'll need to remember this.

### Tracking Advantage/Disadvantage

```python
# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

	# ...

    def give_advantage(self, combatant, target):
        self.advantage_matrix[combatant][target] = True

    def give_disadvantage(self, combatant, target, **kwargs):
        self.disadvantage_matrix[combatant][target] = True

    def has_advantage(self, combatant, target, **kwargs):
        return (
	        target in self.fleeing_combatants
	        or bool(self.advantage_matrix[combatant].pop(target, False))
        )
    def has_disadvantage(self, combatant, target):
        return bool(self.disadvantage_matrix[combatant].pop(target, False))
```

We use the `advantage/disadvantage_matrix` Attributes to track who has advantage against whom.

```{sidebar} .pop()
The Python `.pop()` method removes an element from a list or dict and returns it. For a list, it removes by index (or the last element by default). For a dict (like here), you specify which key to remove. Providing a default value as a second argument prevents an error if the key doesn't exist.
```
In the `has dis/advantage` methods we `pop` the target from the matrix which will result either in the value `True` or `False` (the default value we give to `pop` if the target is not in the matrix). This means that the advantage, once gained, can only be used once.

We also consider everyone to have advantage against fleeing combatants.

### Adding and removing combatants

Since the combat handler is shared we must be able to add- and remove combatants easily.
This is new compared to the base handler.

```python
# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def add_combatant(self, combatant):
        """
        Add a new combatant to the battle. Can be called multiple times safely.
        """
        if combatant not in self.combatants:
            self.combatants[combatant] = self.fallback_action_dict
            return True
        return False

    def remove_combatant(self, combatant):
        """
        Remove a combatant from the battle.
        """
        self.combatants.pop(combatant, None)
        # clean up menu if it exists
		# TODO!
```

We simply add the the combatant with the fallback action-dict to start with. We return a `bool` from `add_combatant` so that the calling function will know if they were actually added anew or not (we may want to do some extra setup if they are new).

For now we just `pop` the combatant, but in the future we'll need to do some extra cleanup of the menu when combat ends (we'll get to that).

### Flee Action

Since you can't just move away from the room to flee turnbased combat, we need to add a new `CombatAction` subclass like the ones we created in the [base combat lesson](./Beginner-Tutorial-Combat-Base.md#actions).


```python
# in evadventure/combat_turnbased.py

from .combat_base import CombatAction

# ...

class CombatActionFlee(CombatAction):
    """
    Start (or continue) fleeing/disengaging from combat.

    action_dict = {
           "key": "flee",
        }
    """

    def execute(self):
        combathandler = self.combathandler

        if self.combatant not in combathandler.fleeing_combatants:
            # we record the turn on which we started fleeing
            combathandler.fleeing_combatants[self.combatant] = self.combathandler.turn

        # show how many turns until successful flight
        current_turn = combathandler.turn
        started_fleeing = combathandler.fleeing_combatants[self.combatant]
        flee_timeout = combathandler.flee_timeout
        time_left = flee_timeout - (current_turn - started_fleeing) - 1

        if time_left > 0:
            self.msg(
                "$You() $conj(retreat), being exposed to attack while doing so (will escape in "
                f"{time_left} $pluralize(turn, {time_left}))."
            )


class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

	action_classes = {
        "hold": CombatActionHold,
        "attack": CombatActionAttack,
        "stunt": CombatActionStunt,
        "use": CombatActionUseItem,
        "wield": CombatActionWield,
        "flee": CombatActionFlee # < ---- added!
    }

	# ...
```

We create the action to make use of the `fleeing_combatants` dict we set up in the combat handler. This dict stores the fleeing combatant along with the  `turn`  its fleeing started. If performing the `flee` action multiple times, we will just display how many turns are remaining.

Finally, we make sure to add our new `CombatActionFlee` to the `action_classes` registry on the combat handler.

### Queue action

```python
# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def queue_action(self, combatant, action_dict):
        self.combatants[combatant] = action_dict

        # track who inserted actions this turn (non-persistent)
        did_action = set(self.ndb.did_action or set())
        did_action.add(combatant)
        if len(did_action) >= len(self.combatants):
            # everyone has inserted an action. Start next turn without waiting!
            self.force_repeat()

```

To queue an action, we simply store its `action_dict` with the combatant in the `combatants` Attribute.

We use a Python `set()` to track who has queued an action this turn. If all combatants have entered a new (or renewed) action this turn, we use the `.force_repeat()` method, which is available on all [Scripts](../../../Components/Scripts.md). When this is called, the next round will fire immediately instead of waiting until it times out.

### Execute an action and tick the round

```{code-block} python
:linenos:
:emphasize-lines: 13,16,17,22,43,49

# in evadventure/combat_turnbased.py

import random

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def execute_next_action(self, combatant):
        # this gets the next dict and rotates the queue
        action_dict = self.combatants.get(combatant, self.fallback_action_dict)

        # use the action-dict to select and create an action from an action class
        action_class = self.action_classes[action_dict["key"]]
        action = action_class(self, combatant, action_dict)

        action.execute()
        action.post_execute()

        if action_dict.get("repeat", False):
            # queue the action again *without updating the
            # *.ndb.did_action list* (otherwise
            # we'd always auto-end the turn if everyone used
            # repeating actions and there'd be
            # no time to change it before the next round)
            self.combatants[combatant] = action_dict
        else:
            # if not a repeat, set the fallback action
            self.combatants[combatant] = self.fallback_action_dict


   def at_repeat(self):
        """
        This method is called every time Script repeats
        (every `interval` seconds). Performs a full turn of
        combat, performing everyone's actions in random order.
        """
        self.turn += 1
        # random turn order
        combatants = list(self.combatants.keys())
        random.shuffle(combatants)  # shuffles in place

        # do everyone's next queued combat action
        for combatant in combatants:
            self.execute_next_action(combatant)

        self.ndb.did_action = set()

        # check if one side won the battle
        self.check_stop_combat()

```

Our action-execution consists of two parts - the `execute_next_action` (which was defined in the parent class for us to implement) and the `at_repeat` method which is a part of the [Script](../../../Components/Scripts.md)

For `execute_next_action` :

- **Line 13**: We get the `action_dict` from the `combatants` Attribute. We return the `fallback_action_dict` if nothing was queued (this defaults to `hold`).
- **Line 16**: We use the `key` of the `action_dict` (which would be something like "attack", "use", "wield" etc) to get the class of the matching Action from the `action_classes` dictionary.
- **Line 17**: Here the action class is instantiated with the combatant and action dict, making it ready to execute. This is then executed on the following lines.
- **Line 22**: We introduce a new optional `action-dict` here, the boolean `repeat` key. This allows us to re-queue the action. If not the fallback action will be used.

The `at_repeat` is called repeatedly every `interval` seconds that the Script fires. This is what we use to track when each round ends.

- **Lines 43**: In this example, we have no internal order between actions. So we simply randomize in which order they fire.
- **Line 49**: This `set` was assigned to in the `queue_action` method to know when everyone submitted a new action. We must make sure to unset it here before the next round.

### Check and stop combat

```{code-block} python
:linenos:
:emphasize-lines: 28,41,49,60

# in evadventure/combat_turnbased.py

import random
from evennia.utils.utils import list_to_string

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

     def stop_combat(self):
        """
        Stop the combat immediately.

        """
        for combatant in self.combatants:
            self.remove_combatant(combatant)
        self.stop()
        self.delete()

    def check_stop_combat(self):
        """Check if it's time to stop combat"""

        # check if anyone is defeated
        for combatant in list(self.combatants.keys()):
            if combatant.hp <= 0:
                # PCs roll on the death table here, NPCs die.
                # Even if PCs survive, they
                # are still out of the fight.
                combatant.at_defeat()
                self.combatants.pop(combatant)
                self.defeated_combatants.append(combatant)
                self.msg("|r$You() $conj(fall) to the ground, defeated.|n", combatant=combatant)
            else:
                self.combatants[combatant] = self.fallback_action_dict

        # check if anyone managed to flee
        flee_timeout = self.flee_timeout
        for combatant, started_fleeing in self.fleeing_combatants.items():
            if self.turn - started_fleeing >= flee_timeout - 1:
                # if they are still alive/fleeing and have been fleeing long enough, escape
                self.msg("|y$You() successfully $conj(flee) from combat.|n", combatant=combatant)
                self.remove_combatant(combatant)

        # check if one side won the battle
        if not self.combatants:
            # noone left in combat - maybe they killed each other or all fled
            surviving_combatant = None
            allies, enemies = (), ()
        else:
            # grab a random survivor and check if they have any living enemies.
            surviving_combatant = random.choice(list(self.combatants.keys()))
            allies, enemies = self.get_sides(surviving_combatant)

        if not enemies:
            # if one way or another, there are no more enemies to fight
            still_standing = list_to_string(f"$You({comb.key})" for comb in allies)
            knocked_out = list_to_string(comb for comb in self.defeated_combatants if comb.hp > 0)
            killed = list_to_string(comb for comb in self.defeated_combatants if comb.hp <= 0)

            if still_standing:
                txt = [f"The combat is over. {still_standing} are still standing."]
            else:
                txt = ["The combat is over. No-one stands as the victor."]
            if knocked_out:
                txt.append(f"{knocked_out} were taken down, but will live.")
            if killed:
                txt.append(f"{killed} were killed.")
            self.msg(txt)
            self.stop_combat()
```

The `check_stop_combat` is called at the end of the round. We want to figure out who is dead and if one of the 'sides' won.

- **Lines 28-38**: We go over all combatants and determine if they are out of HP. If so we fire the relevant hooks and add them to the `defeated_combatants` Attribute.
- **Line 38**: For all surviving combatants, we make sure give them the `fallback_action_dict`.
- **Lines 41-46**: The `fleeing_combatant` Attribute is a dict on the form `{fleeing_combatant: turn_number}`, tracking when they first started fleeing. We compare this with the current turn number and the `flee_timeout` to see if they now flee and should be allowed to be removed from combat.
- **Lines 49-56**: Here on we are determining if one 'side' of the conflict has defeated the other side.
- **Line 60**: The `list_to_string` Evennia utility converts a list of entries, like `["a", "b", "c"` to a nice string `"a, b and c"`. We use this to be able to present some nice ending messages to the combatants.

### Start combat

Since we are using the timer-component of the [Script](../../../Components/Scripts.md) to tick our combat, we also need a helper method to 'start' that.

```python
from evennia.utils.utils import list_to_string

# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...

    def start_combat(self, **kwargs):
        """
        This actually starts the combat. It's safe to run this multiple times
        since it will only start combat if it isn't already running.

        """
        if not self.is_active:
            self.start(**kwargs)

```

The `start(**kwargs)` method is a method on the Script, and will make it start to call `at_repeat` every `interval` seconds. We will pass that `interval` inside `kwargs` (so for example, we'll do `combathandler.start_combat(interval=30)` later).

## Using EvMenu for the combat menu

The _EvMenu_ used to create in-game menues in Evennia. We used a simple EvMenu already in the [Character Generation Lesson](./Beginner-Tutorial-Chargen.md). This time we'll need to be a bit more advanced.  While [The EvMenu documentation](../../../Components/EvMenu.md) describe its functionality in more detail, we will give a quick overview of how it works here.

An EvMenu is made up of _nodes_, which are regular functions on this form (somewhat simplified here, there are more options):

```python
def node_somenodename(caller, raw_string, **kwargs):

    text = "some text to show in the node"
    options = [
        {
           "key": "Option 1", # skip this to get a number
           "desc": "Describing what happens when choosing this option."
           "goto": "name of the node to go to"  # OR (callable, {kwargs}}) returning said name
        },
        # other options here
    ]
    return text, options
```

So basically each node takes the arguments of `caller` (the one using the menu), `raw_string` (the empty string or what the user input on the _previous node_) and `**kwargs` which can be used to pass data from node to node. It returns `text` and `options`.

The `text` is what the user will see when entering this part of the menu, such as "Choose who you want to attack!". The `options` is a list of dicts describing each option. They will appear as a multi-choice list below the node text (see the example at the top of this lesson page).

When we create the EvMenu later, we will create a _node index_ - a mapping between a unique name and these "node functions". So something like this:

```python
# example of a EvMenu node index
    {
      "start": node_combat_main,
      "node1": node_func1,
      "node2": node_func2,
      "some name": node_somenodename,
      "end": node_abort_menu,
    }
```
Each `option` dict has a key `"goto"` that determines which node the player should jump to if they choose that option. Inside the menu, each node needs to be referenced with these names (like `"start"`, `"node1"` etc).

The `"goto"` value of each option can either specify the name directly (like `"node1"`) _or_ it can be given as a tuple `(callable, {keywords})`. This `callable` is _called_ and is expected to in turn return the next node-name to use (like `"node1"`).

The `callable` (often called a "goto callable") looks very similar to a node function:

```python
def _goto_when_choosing_option1(caller, raw_string, **kwargs):
    # do whatever is needed to determine the next node
    return nodename  # also nodename, dict works
```

```{sidebar} Separating node-functions from goto callables
To make node-functions clearly separate from goto-callables, Evennia docs always prefix node-functions with `node_` and menu goto-functions with an underscore `_` (which is also making goto-functions 'private' in Python lingo).
```
Here, `caller` is still the one using the menu and `raw_string` is the actual string you entered to choose this option. `**kwargs` is the keywords you added to the `(callable, {keywords})` tuple.

The goto-callable must return the name of the next node. Optionally, you can return both  `nodename, {kwargs}`. If you do the next node will get those kwargs as ingoing `**kwargs`. This way you can pass information from one node to the next. A special feature is that if `nodename` is returned as `None`, then the _current_ node will be _rerun_ again.

Here's a (somewhat contrived) example of how the goto-callable and node-function hang together:

```
# goto-callable
def _my_goto_callable(caller, raw_string, **kwargs):
    info_number = kwargs["info_number"]
    if info_number > 0:
        return "node1"
    else:
        return "node2", {"info_number": info_number}  # will be **kwargs when "node2" runs next


# node function
def node_somenodename(caller, raw_string, **kwargs):
    text = "Some node text"
    options = [
        {
            "desc": "Option one",
            "goto": (_my_goto_callable, {"info_number", 1})
        },
        {
            "desc": "Option two",
            "goto": (_my_goto_callable, {"info_number", -1})
        },
    ]
```

## Menu for Turnbased combat


Our combat menu will be pretty simple. We will have one central menu node with options indicating all the different actions of combat. When choosing an action in the menu, the player should be asked a series of question, each specifying one piece of information needed for that action. The last step will be the build this information into an `action-dict` we can queue with the combathandler.

To understand the process, here's how the action selection will work (read left to right):

| In base node | step 1 | step 2 | step 3 | step 4 |
| --- | --- | --- | --- | --- |
| select `attack` | select `target` | queue action-dict | - | - |
| select `stunt - give advantage` | select `Ability`| select `allied recipient` | select `enemy target` | queue action-dict |
| select `stunt - give disadvantage` | select `Ability` | select `enemy recipient` | select `allied target` | queue action-dict |
| select `use item on yourself or ally` | select `item` from inventory | select `allied target` | queue action-dict | - |
| select `use item on enemy` | select `item` from inventory | select `enemy target` | queue action-dict | - |
| select `wield/swap item from inventory` | select `item` from inventory` | queue action-dict | - | - |
| select `flee` | queue action-dict | - | - | - |
| select `hold, doing nothing` | queue action-dict | - | - | - |

Looking at the above table we can see that we have _a lot_ of re-use. The selection of allied/enemy/target/recipient/item represent nodes that can be shared by different actions.

Each of these actions also follow a linear sequence, like the step-by step 'wizard' you see in some software. We want to be able to step back and forth in each sequence, and also abort the action if you change your mind along the way.

After queueing the action, we should always go back to the base node where we will wait until the round ends and all actions are executed.

We will create a few helpers to make our particular menu easy to work with.

### The node index

These are the nodes we need for our menu:

```python
# not coded anywhere yet, just noting for reference
node_index = {
    # node names                # callables   # (future callables)
    "node_choose_enemy_target": None, # node_choose_enemy_target,
    "node_choose_allied_target": None, # node_choose_allied_target,
    "node_choose_enemy_recipient": None, # node_choose_enemy_recipient,
    "node_choose_allied_recipient": None, # node_choose_allied_recipient,
    "node_choose_ability": None, # node_choose_ability,
    "node_choose_use_item": None, # node_choose_use_item,
    "node_choose_wield_item": None, # node_choose_wield_item,
    "node_combat": None, # node_combat,
}
```

All callables are left as `None` since we haven't created them yet. But it's good to note down the expected names because we need them in order to jump from node to node. The important one to note is that `node_combat` will be the base node we should get back to over and over.

### Getting or setting the combathandler

```python
# in evadventure/combat_turnbased.py

from evennia import EvMenu

# ...

def _get_combathandler(caller, turn_timeout=30, flee_time=3, combathandler_key="combathandler"):
    return EvAdventureTurnbasedCombatHandler.get_or_create_combathandler(
        caller.location,
        interval=turn_timeout,
        attributes=[("flee_time", flee_time)],
        key=combathandler_key,
    )
```

We only add this to not have to write as much when calling this later. We pass `caller.location`, which is what retrieves/creates the combathandler on the current location. The `interval` is how often the combathandler (which is a [Script](../../../Components/Scripts.md)) will call its `at_repeat` method. We set the `flee_time` Attribute at the same time.

### Queue an action

This is our first "goto function". This will be called to actually queue our finished action-dict with the combat handler. After doing that, it should return us to the base  `node_combat`.

```python
# in evadventure/combat_turnbased.py

# ...

def _queue_action(caller, raw_string, **kwargs):
    action_dict = kwargs["action_dict"]
    _get_combathandler(caller).queue_action(caller, action_dict)
    return "node_combat"
```

We make one assumption here - that `kwargs` contains the `action_dict` key with the action-dict ready to go.

Since this is a goto-callable, we must return the next node to go to. Since this is the last step, we will always go back to the `node_combat` base node, so that's what we return.

### Rerun a node

A special feature of goto callables is the ability to rerun the same node by returning `None`.

```python
# in evadventure/combat_turnbased.py

# ...

def _rerun_current_node(caller, raw_string, **kwargs):
    return None, kwargs
```

Using this in an option will rerun the current node, but will preserve the `kwargs` that were sent in.

### Stepping through the wizard

Our particular menu is very symmetric - you select an option and then you will just select a series of option before you come back. So we will make another goto-function to help us easily do this. To understand, let's first show how we plan to use this:

```python
# in the base combat-node function (just shown as an example)

options = [
    # ...
    "desc": "use an item on an enemy",
    "goto": (
       _step_wizard,
       {
           "steps": ["node_choose_use_item", "node_choose_enemy_target"],
           "action_dict": {"key": "use", "item": None, "target": None},
       }
    )
]
```

When the user chooses to use an item on an enemy, we will call `_step_wizard` with two keywords `steps` and `action_dict`. The first is the _sequence_ of menu nodes we need to guide the player through in order to build up our action-dict.

The latter is the `action_dict` itself. Each node will gradually fill in the `None` places in this dict until we have a complete dict and can send it to the [`_queue_action`](#queue-an-action) goto function we defined earlier.

Furthermore, we want the ability to go "back" to the previous node like this:


```python
# in some other node (shown only as an example)

def some_node(caller, raw_string, **kwargs):

    # ...

    options = [
        # ...
        {
            "key": "back",
            "goto": ( _step_wizard, {**kwargs, **{"step": "back"}})
        },
    ]

    # ...
```

Note the use of `**` here. `{**dict1, **dict2}` is a powerful one-liner syntax to combine two dicts into one. This preserves (and passes on) the incoming `kwargs` and just adds a new key "step" to it. The end effect is similar to if we had done `kwargs["step"] = "back"` on a separate line (except we end up with a _new_ `dict` when using the `**`-approach).

So let's implement a `_step_wizard` goto-function to handle this!

```python
# in evadventure/combat_turnbased.py

# ...

def _step_wizard(caller, raw_string, **kwargs):

    # get the steps and count them
    steps = kwargs.get("steps", [])
    nsteps = len(steps)

    # track which step we are on
    istep = kwargs.get("istep", -1)

    # check if we are going back (forward is default)
    step_direction = kwargs.get("step", "forward")

    if step_direction == "back":
        # step back in wizard
        if istep <= 0:
            # back to the start
            return "node_combat"
        istep = kwargs["istep"] = istep - 1
        return steps[istep], kwargs
    else:
        # step to the next step in wizard
        if istep >= nsteps - 1:
            # we are already at end of wizard - queue action!
            return _queue_action(caller, raw_string, **kwargs)
        else:
            # step forward
            istep = kwargs["istep"] = istep + 1
            return steps[istep], kwargs

```

This depends on passing around `steps`, `step` and `istep` with the `**kwargs`.  If `step` is "back" then we will go back in the sequence of `steps` otherwise forward. We increase/decrease the `istep` key value to track just where we are.

If we reach the end we call our `_queue_action` helper function directly. If we back up to the beginning we return to the base node.

We will make one final helper function, to quickly add the `back` (and `abort`) options to the nodes that need it:

```python
# in evadventure/combat_turnbased.py

# ...

def _get_default_wizard_options(caller, **kwargs):
    return [
        {
            "key": "back",
            "goto": (_step_wizard, {**kwargs, **{"step": "back"}})
        },
        {
            "key": "abort",
            "goto": "node_combat"
        },
        {
            "key": "_default",
            "goto": (_rerun_current_node, kwargs),
        },
    ]
```

This is not a goto-function, it's just a helper that we will call to quickly add these extra options a node's option list and not have to type it out over and over.

As we've seen before, the `back` option will use the `_step_wizard` to step back in the wizard. The `abort` option will simply jump back to the main node, aborting the wizard.

The `_default` option is special. This option key tells EvMenu: "use this option if none of the other match". That is, if they enter an empty input or garbage, we will just re-display the node. We make sure pass along the `kwargs` though, so we don't lose any information of where we were in the wizard.

Finally we are ready to write our menu nodes!

### Choosing targets and recipients

These nodes all work the same: They should present a list of suitable targets/recipients to choose from and then put that result in the action-dict as either `target` or `recipient` key.

```{code-block} python
:linenos:
:emphasize-lines: 11,13,15,18,23

# in evadventure/combat_turnbased.py

# ...

def node_choose_enemy_target(caller, raw_string, **kwargs):

    text = "Choose an enemy to target"

    action_dict = kwargs["action_dict"]
    combathandler = _get_combathandler(caller)
    _, enemies = combathandler.get_sides(caller)

    options = [
        {
            "desc": target.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"target": target}}}},
            )
        }
        for target in enemies
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_enemy_recipient(caller, raw_string, **kwargs):
     # almost the same, except storing "recipient"


def node_choose_allied_target(caller, raw_string, **kwargs):
     # almost the same, except using allies + yourself


def node_choose_allied_recipient(caller, raw_string, **kwargs):
     # almost the same, except using allies + yourself and storing "recipient"

```

- **Line 11**: Here we use `combathandler.get_sides(caller)` to get the 'enemies' from the perspective of `caller` (the one using the menu).
- **Line 13-31**: This is a loop over all enemies we found.
    - **Line 15**:  We use `target.get_display_name(caller)`. This method (a default method on all Evennia `Objects`) allows the target to return a name while being aware of who's asking. It's what makes an admin see `Name (#5)` while a regular user just sees `Name`. If you didn't care about that, you could just do `target.key` here.
    - **Line 18**: This line looks complex, but remember that `{**dict1, **dict2}` is a one-line way to merge two dicts together. What this does is to do this in three steps:
        - First we add `action_dict` together with a dict `{"target": target}`. This has the same effect as doing `action_dict["target"] = target`, except we create a new dict out of the merger.
        - Next we take this new merger and creates a new dict `{"action_dict": new_action_dict}`.
        - Finally we merge this with the existing `kwargs` dict. The result is a new dict that now has the updated `"action_dict"` key pointing to an action-dict where `target` is set.
- **Line 23**: We extend the `options` list with the default wizard options (`back`, `abort`). Since we made a helper function for this, this is only one line.

Creating the three other needed nodes `node_choose_enemy_recipient`, `node_choose_allied_target` and `node_choose_allied_recipient` are following the same pattern; they just use either the `allies` or `enemies` return from `combathandler.get_sides(). It then sets either the `target` or `recipient` field in the `action_dict`. We leave these up to the reader to implement.

### Choose an Ability

For Stunts, we need to be able to select which _Knave_ Ability (STR, DEX etc) you want to boost/foil.

```python
# in evadventure/combat_turnbased.py

from .enums import Ability

# ...

def node_choose_ability(caller, raw_string, **kwargs):
    text = "Choose the ability to apply"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": abi.value,
            "goto": (
                _step_wizard,
                {
                    **kwargs,
                    **{
                        "action_dict": {**action_dict, **{"stunt_type": abi, "defense_type": abi}},
                    },
                },
            ),
        }
        for abi in (
            Ability.STR,
            Ability.DEX,
            Ability.CON,
            Ability.INT,
            Ability.WIS,
            Ability.CHA,
        )
    ]
    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options

```

The principle is the same as for the target/recipient-setter nodes, except that we just provide a list of the abilities to choose from. We update the `stunt_type` and `defense_type` keys in the `action_dict`, as needed by the Stunt action.

### Choose an item to use or wield

```python
# in evadventure/combat_turnbased.py

# ...

def node_choose_use_item(caller, raw_string, **kwargs):
    text = "Select the item"
    action_dict = kwargs["action_dict"]

    options = [
        {
            "desc": item.get_display_name(caller),
            "goto": (
                _step_wizard,
                {**kwargs, **{"action_dict": {**action_dict, **{"item": item}}}},
            ),
        }
        for item in caller.equipment.get_usable_objects_from_backpack()
    ]
    if not options:
        text = "There are no usable items in your inventory!"

    options.extend(_get_default_wizard_options(caller, **kwargs))
    return text, options


def node_choose_wield_item(caller, raw_string, **kwargs):
     # same except using caller.equipment.get_wieldable_objects_from_backpack()

```

Our [equipment handler](./Beginner-Tutorial-Equipment.md) has the very useful help method `.get_usable_objects_from_backpack`. We just call this to get a list of all the items we want to choose. Otherwise this node should look pretty familiar by now.

The `node_choose_wield_item` is very similar, except it uses `caller.equipment.get_wieldable_objects_from_backpack()` instead. We'll leave the implementation of this up to the reader.

### The main menu node

This ties it all together.

```python
# in evadventure/combat_turnbased.py

# ...

def node_combat(caller, raw_string, **kwargs):
    """Base combat menu"""

    combathandler = _get_combathandler(caller)

    text = combathandler.get_combat_summary(caller)
    options = [
        {
            "desc": "attack an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_enemy_target"],
                    "action_dict": {"key": "attack", "target": None, "repeat": True},
                },
            ),
        },
        {
            "desc": "Stunt - gain a later advantage against a target",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_target",
                        "node_choose_allied_recipient",
                    ],
                    "action_dict": {"key": "stunt", "advantage": True},
                },
            ),
        },
        {
            "desc": "Stunt - give an enemy disadvantage against yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": [
                        "node_choose_ability",
                        "node_choose_enemy_recipient",
                        "node_choose_allied_target",
                    ],
                    "action_dict": {"key": "stunt", "advantage": False},
                },
            ),
        },
        {
            "desc": "Use an item on yourself or an ally",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_allied_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Use an item on an enemy",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_use_item", "node_choose_enemy_target"],
                    "action_dict": {"key": "use", "item": None, "target": None},
                },
            ),
        },
        {
            "desc": "Wield/swap with an item from inventory",
            "goto": (
                _step_wizard,
                {
                    "steps": ["node_choose_wield_item"],
                    "action_dict": {"key": "wield", "item": None},
                },
            ),
        },
        {
            "desc": "flee!",
            "goto": (_queue_action, {"action_dict": {"key": "flee", "repeat": True}}),
        },
        {
            "desc": "hold, doing nothing",
            "goto": (_queue_action, {"action_dict": {"key": "hold"}}),
        },
        {
            "key": "_default",
            "goto": "node_combat",
        },
    ]

    return text, options
```

This starts off the `_step_wizard` for each action choice. It also lays out the `action_dict` for every action, leaving `None` values for the fields that will be set by the following nodes.

Note how we add the `"repeat"` key to some actions. Having them automatically repeat means the player doesn't have to insert the same action every time.

## Attack Command

We will only need one single command to run the turnbased combat system. This is the `attack` command. Once you use it once, you will be in the menu.


```python
# in evadventure/combat_turnbased.py

from evennia import Command, CmdSet, EvMenu

# ...

class CmdTurnAttack(Command):
    """
    Start or join combat.

    Usage:
      attack [<target>]

    """

    key = "attack"
    aliases = ["hit", "turnbased combat"]

    turn_timeout = 30  # seconds
    flee_time = 3  # rounds

    def parse(self):
        super().parse()
        self.args = self.args.strip()

    def func(self):
        if not self.args:
            self.msg("What are you attacking?")
            return

        target = self.caller.search(self.args)
        if not target:
            return

        if not hasattr(target, "hp"):
            self.msg("You can't attack that.")
            return

        elif target.hp <= 0:
            self.msg(f"{target.get_display_name(self.caller)} is already down.")
            return

        if target.is_pc and not target.location.allow_pvp:
            self.msg("PvP combat is not allowed here!")
            return

        combathandler = _get_combathandler(
            self.caller, self.turn_timeout, self.flee_time)

        # add combatants to combathandler. this can be done safely over and over
        combathandler.add_combatant(self.caller)
        combathandler.queue_action(self.caller, {"key": "attack", "target": target})
        combathandler.add_combatant(target)
        target.msg("|rYou are attacked by {self.caller.get_display_name(self.caller)}!|n")
        combathandler.start_combat()

        # build and start the menu
        EvMenu(
            self.caller,
            {
                "node_choose_enemy_target": node_choose_enemy_target,
                "node_choose_allied_target": node_choose_allied_target,
                "node_choose_enemy_recipient": node_choose_enemy_recipient,
                "node_choose_allied_recipient": node_choose_allied_recipient,
                "node_choose_ability": node_choose_ability,
                "node_choose_use_item": node_choose_use_item,
                "node_choose_wield_item": node_choose_wield_item,
                "node_combat": node_combat,
            },
            startnode="node_combat",
            combathandler=combathandler,
            auto_look=False,
            # cmdset_mergetype="Union",
            persistent=True,
        )


class TurnCombatCmdSet(CmdSet):
    """
    CmdSet for the turn-based combat.
    """

    def at_cmdset_creation(self):
        self.add(CmdTurnAttack())
```

The `attack target` Command will determine if the target has health (only things with health can be attacked) and that the room allows fighting. If the target is a pc, it will check so PvP is allowed.

It then proceeds to either start up a new command handler or reuse a new one, while adding  the attacker and target to it. If the target was already in combat, this does nothing (same with the `.start_combat()` call).

As we create the `EvMenu`, we pass it the "menu index" we talked to about earlier, now with the actual node functions in every slot.  We make the menu persistent so it survives a reload.

To make the command available, add the `TurnCombatCmdSet` to the Character's default cmdset.


## Making sure the menu stops

The combat can end for a bunch of reasons. When that happens, we must make sure to clean up the menu so we go back normal operation. We will add this to the `remove_combatant` method on the combat handler (we left a TODO there before):

```python

# in evadventure/combat_turnbased.py

# ...

class EvadventureTurnbasedCombatHandler(EvAdventureCombatBaseHandler):

    # ...
    def remove_combatant(self, combatant):
        """
        Remove a combatant from the battle.
        """
        self.combatants.pop(combatant, None)
        # clean up menu if it exists
        if combatant.ndb._evmenu:                   # <--- new
            combatant.ndb._evmenu.close_menu()      #     ''

```

When the evmenu is active, it is avaiable on its user as `.ndb._evmenu` (see the EvMenu docs). When we are removed from combat, we use this to get the evmenu and call its `close_menu()` method to shut down the menu.

Our turnbased combat system is complete!


## Testing

```{sidebar}
See an example tests in `evennia/contrib/tutorials`, in  [evadventure/tests/test_combat.py](evennia.contrib.tutorials.evadventure.tests.test_combat) 
```
Unit testing of the Turnbased combat handler is straight forward, you follow the process of earlier lessons to test that each method on the handler returns what you expect with mocked inputs.

Unit-testing the menu is more complex. You will find examples of doing this in [evennia.utils.tests.test_evmenu](github:main/evennia/utils/testss/test_evmenu.py).

## A small combat test

Unit testing the code is not enough to see that combat works. We need to also make a little 'functional' test to see how it works in practice.

​This is what we need for a minimal test:

 - A room with combat enabled.
 - An NPC to attack (it won't do anything back yet since we haven't added any AI)
 - A weapon we can `wield`.
 - An item (like a potion) we can `use`.

```{sidebar}
You can find an example combat batch-code script in `evennia/contrib/tutorials/evadventure/`, in  [batchscripts/turnbased_combat_demo.py](github:evennia/contrib/tutorials/evadventure/batchscripts/turnbased_combat_demo.py)
```

In [The Twitch combat lesson](./Beginner-Tutorial-Combat-Twitch.md) we used a [batch-command script](../../../Components/Batch-Command-Processor.md) to create the testing environment in game. This runs in-game Evennia commands in sequence. For demonstration  purposes we'll instead use a  [batch-code script](../../../Components/Batch-Code-Processor.md), which runs raw Python code in a repeatable way. A batch-code script is much more flexible than a batch-command script.

> Create a new subfolder `evadventure/batchscripts/` (if it doesn't already exist)

> Create a new Python module `evadventure/batchscripts/combat_demo.py`

A batchcode file is a valid Python module. The only difference is that it has a `# HEADER` block and one or more `# CODE` sections. When the processor runs, the `# HEADER` part will be added on top of each `# CODE` part before executing that code block in isolation. Since you can run the file from in-game (including refresh it without reloading the server), this gives the ability to run longer Python codes on-demand.

```python
# Evadventure (Turnbased) combat demo - using a batch-code file.
#
# Sets up a combat area for testing turnbased combat.
#
# First add mygame/server/conf/settings.py:
#
#    BASE_BATCHPROCESS_PATHS += ["evadventure.batchscripts"]
#
# Run from in-game as `batchcode turnbased_combat_demo`
#

# HEADER

from evennia import DefaultExit, create_object, search_object
from evennia.contrib.tutorials.evadventure.characters import EvAdventureCharacter
from evennia.contrib.tutorials.evadventure.combat_turnbased import TurnCombatCmdSet
from evennia.contrib.tutorials.evadventure.npcs import EvAdventureNPC
from evennia.contrib.tutorials.evadventure.rooms import EvAdventureRoom

# CODE

# Make the player an EvAdventureCharacter
player = caller  # caller is injected by the batchcode runner, it's the one running this script # E: undefined name 'caller'
player.swap_typeclass(EvAdventureCharacter)

# add the Turnbased cmdset
player.cmdset.add(TurnCombatCmdSet, persistent=True)

# create a weapon and an item to use
create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureWeapon",
    key="Sword",
    location=player,
    attributes=[("desc", "A sword.")],
)

create_object(
    "contrib.tutorials.evadventure.objects.EvAdventureConsumable",
    key="Potion",
    location=player,
    attributes=[("desc", "A potion.")],
)

# start from limbo
limbo = search_object("#2")[0]

arena = create_object(EvAdventureRoom, key="Arena", attributes=[("desc", "A large arena.")])

# Create the exits
arena_exit = create_object(DefaultExit, key="Arena", location=limbo, destination=arena)
back_exit = create_object(DefaultExit, key="Back", location=arena, destination=limbo)

# create the NPC dummy
create_object(
    EvAdventureNPC,
    key="Dummy",
    location=arena,
    attributes=[("desc", "A training dummy."), ("hp", 1000), ("hp_max", 1000)],
)

```

If editing this in an IDE, you may get errors on the `player = caller` line. This is because `caller` is not defined anywhere in this file. Instead `caller` (the one running the script) is injected by the `batchcode` runner.

But apart from the `# HEADER` and `# CODE` specials, this just a series of normal Evennia api calls.

Log into the game with a developer/superuser account and run

    > batchcode evadventure.batchscripts.turnbased_combat_demo

This should place you in the arena with the dummy (if not, check for errors in the output! Use `objects` and `delete` commands to list and delete objects if you need to start over.)

You can now try `attack dummy` and should be able to pound away at the dummy (lower its health to test destroying it). If you need to fix something, use `q` to exit the menu and get access to the `reload` command (for the final combat, you can disable this ability by passing `auto_quit=False` when you create the `EvMenu`).

## Conclusions

At this point we have covered some ideas on how to implement both twitch- and turnbased combat systems. Along the way you have been exposed to many concepts such as classes, scripts and handlers, Commands, EvMenus and more.

Before our combat system is actually usable, we need our enemies to actually fight back. We'll get to that next.
