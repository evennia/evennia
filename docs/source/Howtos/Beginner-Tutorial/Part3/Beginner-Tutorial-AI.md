# NPC and monster AI 

```{sidebar} Artificial Intelligence sounds complex
The term "Artificial Intelligence" can sound daunting. It evokes images of supercomputers, machine learning, neural networks and large language models. For our use case though, you can get something that feels pretty 'intelligent' by just using a few if-statements.
```
Not every entity in the game are controlled by a player. NPCs and enemies need to be controlled by the computer - that is, we need to give them artificial intelligence (AI). 

For our game we will implement a type of AI called a 'state machine'. It means that the entity (like an NPC or mob) is always in a given 'state'. An example of a state could be 'idle', 'roaming' or 'attacking'. 
At regular intervals, the AI entity will be 'ticked' by Evennia. This 'tick' starts with an evaluation which determines if the entity should switch to another state, or stay and perform one (or more) actions inside the current state.

```{sidebar} Mobs and NPC
'Mob' is short for 'Mobile' and is a common MUD term for an entity that can move between rooms. The term is usually used for aggressive enemies. A Mob is also an 'NPC' (Non-Player Character), but the latter term is often used for more peaceful entities, like shopkeeprs and quest givers.
```

For example, if a mob in a 'roaming' state comes upon a player character, it may switch into the 'attack' state. In combat it could move between different combat actions, and if it survives combat it would go back to its 'roaming' state. 

The AI can be 'ticked' on different time scales depending on how your game works. For example, while a mob is moving, they might automatically move from room to room every 20 seconds. But once it enters turn-based combat (if you use that), the AI will 'tick' only on every turn. 

## Our requirements

```{sidebar} Shopkeepers and quest givers
NPC shopkeepers and quest givers will be assumed to always be in the 'idle' state in our game - the functionality of talking to or shopping from them will be explored in a future lesson. 
```

For this tutorial game, we'll need AI entities to be able to be in the following states:

- _Idle_ - don't do anything, just stand around. 
- _Roam_ - move from room to room. It's important that we add the ability to limit where the AI can roam to. For example, if we have non-combat areas we want to be able to [lock](../../../Components/Locks.md) all exits leading into those areas so aggressive mods doesn't walk into them.
- _Combat_ - initiate and perform combat with PCs. This state will make use of the [Combat Tutorial](./Beginner-Tutorial-Combat-Base.md) to randomly select combat actions (turn-based or tick-based as appropriately).
- _Flee_ - this is like _Roam_ except the AI will move so as to avoid entering rooms with PCs, if possible. 

We will organize the AI code like this: 
- `AIHandler` this will be a handler stored as `.ai` on the AI entity. It is responsible for storing the AI's state. To 'tick' the AI, we run `.ai.run()`. How often we crank the wheels of the AI this way we leave up to other game systems. 
- `.ai_<state_name>` methods on the NPC/Mob class - when the `ai.run()` method is called, it is responsible for finding a method named like its current state (e.g. `.ai_combat` if we are in the _combat_ state). Having methods like this makes it easy to add new states - just add a new method named appropriately and the AI now knows how to handle that state! 

## The AIHandler 

```{{sidebar}}
You can find an AIHandler implemented in `evennia/contrib/tutorials`, in [evadventure/tests/test_ai.py](evennia.contrib.tutorials.evadventure.ai)
```
This is the core logic for managing AI states. Create a new file `evadventure/ai.py`.

> Create a new file `evadventure/ai.py`.

```{code-block} python
:linenos: 
:emphasize-lines: 10,11-13,16,23
# in evadventure/ai.py

from evennia.logger import log_trace

class AIHandler:
    attribute_name = "ai_state"
    attribute_category = "ai_state"

    def __init__(self, obj):
        self.obj = obj
        self.ai_state = obj.attributes.get(self.attribute_name,
                                           category=self.attribute_category,
                                           default="idle")
    def set_state(self, state):
        self.ai_state = state
        self.obj.attributes.add(self.attribute_name, state, category=self.attribute_category)

    def get_state(self):
        return self.ai_state

    def run(self):
        try:
            state = self.get_state()
            getattr(self.obj, f"ai_{state}")()
        except Exception:
            log_trace(f"AI error in {self.obj.name} (running state: {state})")


```

The AIHandler is an example of an [Object Handler](../../Tutorial-Persistent-Handler.md). This is a design style that groups all functionality together. To look-ahead a little, this handler will be added to the object like this: 
```{sidebar} lazy_property
This is an Evennia [@decorator](https://realpython.com/primer-on-python-decorators/) that makes it so that the handler won't be initialized until someone actually tries to access `obj.ai` for the first time. On subsequent calls, the already initialized handler is returned. This is a very useful performance optimization when you have a lot of objects and also important for the functionality of handlers.
```

```python
# just an example, don't put this anywhere yet

from evennia.utils import lazy_property
from evadventure.ai import AIHandler 

class MyMob(SomeParent): 

    @lazy_property
    class ai(self): 
        return AIHandler(self)
```

So in short, accessing the `.ai` property will initialize an instance of `AIHandler`, to which we pass `self` (the current object). In the `AIHandler.__init__` we take this input and store it as `self.obj` (**lines 10-13**). This way the handler can always operate on the entity it's "sitting on" by accessing `self.obj`.  The `lazy_property` makes sure that this initialization only happens once per server reload. 

More key functionality: 

- **Line 11**: We (re)load the AI state by accessing `self.obj.attributes.get()`. This loads a database [Attribute](../../../Components/Attributes.md) with a given name and category. If one is not (yet) saved, return "idle". Note that we must access `self.obj` (the NPC/mob) since that is the only thing with access to the database. 
- **Line 16**: In the `set_state` method we force the handler to switch to a given state. When we do, we make sure to save it to the database as well, so its state survives a reload. But we also store it in `self.ai_state` so we don't need to hit the database on every fetch.
- **line 23**: The `getattr` function is an in-built Python function for getting a named property on an object. This allows us to, based on the current state, call a method `ai_<statename>` defined on the NPC/mob. We must wrap this call in a `try...except` block to properly handle errors in the AI method. Evennia's `log_trace` will make sure to log the error, including its traceback for debugging.

### More helpers on the AI handler 

It's also convenient to put a few helpers on the AIHandler. This makes them easily available from inside the `ai_<state>` methods, callable as e.g. `self.ai.get_targets()`.

```{code-block} python
:linenos:
:emphasize-lines: 41,42,47,49
# in evadventure/ai.py 

# ... 
import random

class AIHandler:

    # ...

    def get_targets(self):
        """
        Get a list of potential targets for the NPC to combat.

        """
        return [obj for obj in self.obj.location.contents if hasattr(obj, "is_pc") and obj.is_pc]

    def get_traversable_exits(self, exclude_destination=None):
        """
        Get a list of exits that the NPC can traverse. Optionally exclude a destination.
        
        Args:
            exclude_destination (Object, optional): Exclude exits with this destination.

        """
        return [
            exi
            for exi in self.obj.location.exits
            if exi.destination != exclude_destination and exi.access(self, "traverse")
        ]
    
    def random_probability(self, probabilities):
        """
        Given a dictionary of probabilities, return the key of the chosen probability.

        Args:
            probabilities (dict): A dictionary of probabilities, where the key is the action and the
                value is the probability of that action.

        """
        # sort probabilities from higheest to lowest, making sure to normalize them 0..1
        prob_total = sum(probabilities.values())
        sorted_probs = sorted(
            ((key, prob / prob_total) for key, prob in probabilities.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        rand = random.random()
        total = 0
        for key, prob in sorted_probs:
            total += prob
            if rand <= total:
                return key
```

```{sidebar} Locking exits
The 'traverse' lock is the default lock-type checked by Evennia before allowing something to pass through an exit. Since only PCs have the `is_pc` property, we could lock down exits to _only_ allow entities with the property to pass through.

In game: 

    lock north = traverse:attr(is_pc, True)

Or in code: 

    exit_obj.locks.add(
        "traverse:attr(is_pc, True)")

See [Locks](../../../Components/Locks.md) for a lot more information about Evennia locks.
```
- `get_targets` checks if any of the other objects in the same location as the `is_pc` property set on their typeclass. For simplicity we assume Mobs will only ever attack PCs (no monster in-fighting!).
- `get_traversable_exits` fetches all valid exits from the current location, excluding those with a provided destination _or_ those which doesn't pass the "traverse" access check.
- `get_random_probability` takes a dict `{action: probability, ...}`. This will randomly select an action, but the higher the probability, the more likely it is that it will be picked. We will use this for the combat state later, to allow different combatants to more or less likely to perform different combat actions. This algorithm uses a few useful Python tools: 
    - **Line 41**: Remember `probabilities` is a `dict` `{key: value, ...}`, where the values are the probabilities. So `probabilities.values()` gets us a list of only the probabilities. Running `sum()` on them gets us the total sum of those probabilities. We need that to normalize all probabilities between 0 and 1.0 on the line below.
    - **Lines 42-46**: Here we create a new iterable of tuples `(key, prob/prob_total)`. We sort them using the Python `sorted` helper. The `key=lambda x: x[1]` means that we sort on the second element of each tuple (the probability). The `reverse=True` means that we'll sort from highest probability to lowest.
    - **Line 47**:The `random.random()` call generates a random value between 0 and 1.
    - **Line 49**: Since the probabilities are sorted from highest to lowest, we loop over them until we find the first one fitting in the random value - this is the action/key we are looking for.
    - To give an example, if you have a `probability` input of `{"attack": 0.5, "defend": 0.1, "idle": 0.4}`, this would become a sorted iterable `(("attack", 0.5), ("idle", 0.4), ("defend": 0.1))`, and if `random.random()` returned 0.65, the outcome would be "idle". If `random.random()` returned `0.90`, it would be "defend".  That is, this AI entity would attack 50% of the time, idle 40% and defend 10% of the time.


## Adding AI to an entity 

All we need to add AI-support to a game entity is to add the AI handler and a bunch of `.ai_statename()` methods onto that object's typeclass. 

We already sketched out NPCs and Mob typeclasses back in the [NPC tutorial](Beginner-Tutorial_NPCs). Open `evadventure/npcs.py` and expand the so-far empty `EvAdventureMob` class.

```python
# in evadventure/npcs.py 

# ... 

from evennia.utils import lazy_property 
from .ai import AIHandler

# ... 

class EvAdventureMob(EvAdventureNPC):

    @lazy_property
    def ai(self): 
        return AIHandler(self)

    def ai_idle(self): 
        pass 

    def ai_roam(self): 
        pass 

    def ai_roam(self): 
        pass 

    def ai_combat(self): 
        pass 

    def ai_flee(self):
        pass

```

All the remaining logic will go into each state-method. 

### Idle state 

In the idle state the mob does nothing, so we just leave the `ai_idle` method as it is - with just an empty `pass` in it. This means that it will also not attack PCs in the same room - but if a PC attacks it, we must make sure to force it into a combat state (otherwise it will be defenseless). 

### Roam state 

In this state the mob should move around from room to room until it finds PCs to attack. 

```python
# in evadventure/npcs.py

# ... 

import random

class EvAdventureMob(EvAdventureNPC): 

    # ... 

    def ai_roam(self):
        """
        roam, moving randomly to a new room. If a target is found, switch to combat state.

        """
        if targets := self.ai.get_targets():
            self.ai.set_state("combat")
            self.execute_cmd(f"attack {random.choice(targets).key}")
        else:
            exits = self.ai.get_traversable_exits()
            if exits:
                exi = random.choice(exits)
                self.execute_cmd(f"{exi.key}")
```

Every time the AI is ticked, this method will be called. It will first check if there are any valid targets in the room (using the `get_targets()` helper we made on the `AIHandler`). If so, we switch to the `combat` state and immediately call the `attack` command to initiate/join combat (see the [Combat tutorial](./Beginner-Tutorial-Combat-Base.md)). 

If no target is found, we get a list of traversible exits (exits that fail the `traverse` lock check is already excluded from this list). Using Python's in-bult `random.choice` function we grab a random exit from that list and moves through it by its name.

### Flee state 

Flee is similar to _Roam_ except the the AI never tries to attack anything and will make sure to not return the way it came.

```python
# in evadventure/npcs.py

# ... 

class EvAdventureMob(EvAdventureNPC):

    # ... 

    def ai_flee(self):
        """
        Flee from the current room, avoiding going back to the room from which we came. If no exits
        are found, switch to roam state.

        """
        current_room = self.location
        past_room = self.attributes.get("past_room", category="ai_state", default=None)
        exits = self.ai.get_traversable_exits(exclude_destination=past_room)
        if exits:
            self.attributes.set("past_room", current_room, category="ai_state")
            exi = random.choice(exits)
            self.execute_cmd(f"{exi.key}")
        else:
            # if in a dead end, roam will allow for backing out
            self.ai.set_state("roam")

```

We store the `past_room` in an Attribute "past_room" on ourselves and make sure to exclude it when trying to find random exits to traverse to.

If we end up in a dead end we switch to _Roam_ mode so that it can get back out (and also start attacking things again). So the effect of this is that the mob will flee in terror as far as it can before 'calming down'. 

### Combat state

While in the combat state, the mob will use one of the combat systems we've designed (either [twitch-based combat](./Beginner-Tutorial-Combat-Twitch.md) or [turn-based combat](./Beginner-Tutorial-Combat-Turnbased.md)). This means that every time the AI ticks, and we are in the combat state, the entity needs to perform one of the available combat actions, _hold_, _attack_, _do a stunt_, _use an item_ or _flee_.

```{code-block} python
:linenos: 
:emphasize-lines: 7,22,24,25
# in evadventure/npcs.py 

# ... 

class EvAdventureMob(EvAdventureNPC): 

    combat_probabilities = {
        "hold": 0.0,
        "attack": 0.85,
        "stunt": 0.05,
        "item": 0.0,
        "flee": 0.05,
    }

    # ... 

    def ai_combat(self):
        """
        Manage the combat/combat state of the mob.

        """
        if combathandler := self.nbd.combathandler:
            # already in combat
            allies, enemies = combathandler.get_sides(self)
            action = self.ai.random_probability(self.combat_probabilities)

            match action:
                case "hold":
                    combathandler.queue_action({"key": "hold"})
                case "combat":
                    combathandler.queue_action({"key": "attack", "target": random.choice(enemies)})
                case "stunt":
                    # choose a random ally to help
                    combathandler.queue_action(
                        {
                            "key": "stunt",
                            "recipient": random.choice(allies),
                            "advantage": True,
                            "stunt": Ability.STR,
                            "defense": Ability.DEX,
                        }
                    )
                case "item":
                    # use a random item on a random ally
                    target = random.choice(allies)
                    valid_items = [item for item in self.contents if item.at_pre_use(self, target)]
                    combathandler.queue_action(
                        {"key": "item", "item": random.choice(valid_items), "target": target}
                    )
                case "flee":
                    self.ai.set_state("flee")

        elif not (targets := self.ai.get_targets()):
            self.ai.set_state("roam")
        else:
            target = random.choice(targets)
            self.execute_cmd(f"attack {target.key}")

```

- **Lines 7-13**: This dict describe how likely the mob is to perform a given combat action. By just modifying this dictionary we can easily creating mobs that behave very differently, like using items more or being more prone to fleeing. You can also turn off certain action entirely - by default his mob never "holds" or "uses items".
- **Line 22**: If we are in combat, a `CombadHandler` should be initialized on us, available as as `self.ndb.combathandler` (see the [base combat tutorial](./Beginner-Tutorial-Combat-Base.md)).
- **Line 24**: The `combathandler.get_sides()` produces the allies and enemies for the one passed to it. 
- **Line 25**: Now that `random_probability` method we created earlier in this lesson becomes handy! 

The rest of this method just takes the randomly chosen action and performs the required operations to queue it as a new action with the `CombatHandler`.  For simplicity, we only use stunts to boost our allies, not to hamper our enemies.

Finally, if we are not currently in combat and there are no enemies nearby, we switch to  roaming - otherwise we start another fight! 

## Unit Testing 

```{{sidebar}}
Find an example of AI tests in [evennia/contrib/tutorials/tests/test_ai.py](evennia.contrib.tutorials.evadventure.tests.test_ai).
```
> Create a new file `evadventure/tests/test_ai.py`.

Testing the AI handler and mob is straightforward if you have followed along with previous lessons. Create an `EvAdventureMob` and test that calling the various ai-related methods and handlers on it works as expected. A complexity is to mock the output from `random` so that you always get the same random result to compare against. We leave the implementation of AI tests as an extra exercise for the reader. 

## Conclusions

You can easily expand this simple system to make Mobs more 'clever'. For example, instead of just randomly decide which action to take in combat, the mob could consider more factors - maybe some support mobs could use stunts to pave the way for their heavy hitters or use health potions when badly hurt. 

It's also simple to add a 'hunt' state, where mobs check adjoining rooms for targets before moving there. 

And while implementing a functional game AI system requires no advanced math or machine learning techniques, there's of course no limit to what kind of advanced things you could add if you really wanted to!

