# Game Quests

```{warning}
This tutorial lesson is not yet complete, and has some serious bugs in its implementation. So use this as a reference, but the code is not yet ready to use directly.
```

A _quest_ is a common feature of games. From classic fetch-quests like retrieving 10 flowers to complex quest chains involving drama and intrigue, quests need to be properly tracked in our game. 

A quest follows a specific development:

1. The quest is _started_. This normally involves the player accepting the quest, from a quest-giver, job board or other source. But the quest could also be thrust on the player ("save the family from the burning house before it collapses!")
2. Once a quest has been accepted and assigned to a character, it is either either `Started` (that is, 'in progress'), `Abandoned`, `Failed` or `Complete`. 
3. A quest may consist of one or more 'steps'. Each step has its own set of finish conditions. 
4. At suitable times the quest's _progress_ is checked. This could happen on a timer or when trying to 'hand in' the quest. When checking, the current 'step' is checked against its finish conditions. If ok, that step is closed and the next step is checked until it either hits a step that is not yet complete, or there are no more steps, in which case the entire quest is complete.

```{sidebar} 
An example implementation of quests is found under `evennia/contrib/tutorials`, in [evadventure/quests.py](evennia.contrib.tutorials.evadventure.quests).
```
To represent quests in code, we need 
- A convenient flexible way to code how we check the status and current steps of the quest. We want this scripting to be as flexible as possible. Ideally we want to be able to code the quests's logic in full Python.
- Persistence. The fact that we accepted the quest, as well as its status and other flags must be saved in the database and survive a server reboot.

We'll accomplish this  using two pieces of Python code:
- `EvAdventureQuest`: A Python class with helper methods that we can call to check current quest status, figure if a given quest-step is complete or not. We will create and script new quests by simply inheriting from this base class and implement new methods on it in a standardized way.
- `EvAdventureQuestHandler` will sit 'on' each Character as `character.quests`. It will hold all `EvAdventureQuest`s that the character is or has been involved in. It is also responsible for storing quest state using [Attributes](../../../Components/Attributes.md) on the Character. 

## The Quest Handler

> Create a new module `evadventure/quests.py`.

We saw the implementation of an on-object handler back in the [lesson about NPC and monster AI](./Beginner-Tutorial-AI.md#the-aihandler) (the `AIHandler`). 

```{code-block} python
:linenos: 
:emphasize-lines: 9,10,13-17,20,23-27
# in evadventure/quests.py

class EvAdventureQuestHandler:
    quest_storage_attribute_key = "_quests"
    quest_storage_attribute_category = "evadventure"

    def __init__(self, obj):
        self.obj = obj
        self.quest_classes = {}
        self.quests = {}
        self._load()

    def _load(self):
        self.quest_classes = self.obj.attributes.get(
            self.quest_storage_attribute_key,
            category=self.quest_storage_attribute_category,
            default={},
        )
        # instantiate all quests
        for quest_key, quest_class in self.quest_classes.items():
            self.quests[quest_key] = quest_class(self.obj, questhandler=self)

    def _save(self):
        self.obj.attributes.add(
            self.quest_storage_attribute_key,
            self.quest_classes,
            category=self.quest_storage_attribute_category,
        )
    
    def get(self, quest_key):
        return self.quests.get(quest_key)

    def all(self):
        return list(self.quests.values())

    def add(self, quest_class):
        self.quest_classes[quest_class.key] = quest_class
        self.quests[quest_class.key] = quest_class(self.obj, questhandler=self)
        self._save()

    def remove(self, quest_key):
        quest = self.quests.pop(quest_key, None)
        self.quest_classes.pop(quest_key, None)
        self.quests.pop(quest_key, None)
        self._save()

```

```{sidebar} Persistent handler pattern
Persistent handlers are commonly used throughout Evennia. You can read more about them in the [Making a Persistent object Handler](../../Tutorial-Persistent-Handler.md) tutorial.
```
- **Line 9**:  We know that the quests themselves will be Python classes inheriting from `EvAdventureQuest` (which we haven't created yet). We will store those classes in `self.quest_classes` on the handler. Note that there is a difference between a class and an _instance_ of a class! The class cannot hold any _state_ on its own, such as the status of that quest is for this particular character. The class only holds python code.
- **Line 10**: We set aside another property on the handler - `self.quest` This is dictionary that will hold `EvAdventureQuest` _instances_. 
- **Line 11**: Note that we call the `self._load()` method here, this loads up data from the database whenever this handler is accessed. 
- **Lines 14-18**: We use `self.obj.attributes.get` to fetch an [Attribute](../../../Components/Attributes.md) on the Character named `_quests` and with a category of `evadventure`. If it doesn't exist yet (because we never started any quests), we just return an empty dict. 
- **Line 21**: Here we loop over all the classes and instantiate them. We haven't defined how these quest-classes look yet, but by instantiating them with `self.obj` (the Character) we should be covered - from the Character class the quest will be able to get to everything else (this handler itself will be accessible as `obj.quests` from that quest instance after all). 
- **Line 24**: Here we do the corresponding save operation.

The rest of the handler are just access methods for getting, adding and removing quests from the handler. We make one assumption in those code, namely that the quest class has a property `.key` being the unique quest-name. 

This is how it would be used in practice: 

```python 
# in some questing code 

from evennia import search_object
from evadventure import quests 

class EvAdventureSuperQuest(quests.EvAdventureQuest):
    key = "superquest"
    # quest implementation here

def start_super_quest(character):
    character.quests.add(EvAdventureSuperQuest)

```
```{sidebar} What can be saved in Attributes?
For more details, see [the Attributes documentation](../../../Components/Attributes.md#what-types-of-data-can-i-save-in-an-attribute) on the matter.
```
We chose to store classes and not instances of classes above. The reason for this has to do with what can be stored in a database `Attribute` - one limitation of an Attribute is that we can't save a class instance _with other database entities baked inside it_. If we saved quest instances as-is, it's highly likely they'd contain database entities 'hidden' inside them - a reference to the Character, maybe to objects required for the quest to be complete etc. Evennia would fail trying to save that data. 
Instead we store only the classes, instantiate those classes with the Character, and let the quest store its state flags separately, like this: 

```python 
# in evadventure/quests.py 

class EvAdventureQuestHandler: 

    # ... 
    quest_data_attribute_template = "_quest_data_{quest_key}"
    quest_data_attribute_category = "evadventure"

    # ... 

    def save_quest_data(self, quest_key):
        quest = self.get(quest_key)
        if quest:
            self.obj.attributes.add(
                self.quest_data_attribute_template.format(quest_key=quest_key),
                quest.data,
                category=self.quest_data_attribute_category,
            )

    def load_quest_data(self, quest_key):
        return self.obj.attributes.get(
            self.quest_data_attribute_template.format(quest_key=quest_key),
            category=self.quest_data_attribute_category,
            default={},
        )

```

This works the same as the `_load` and `_save` methods, except it fetches a property `.data` (this will be a `dict`) on the quest instance and save it. As long as we make sure to call these methods from the quest the quest whenever that `.data` property is changed, all will be well - this is because Attributes know how to properly analyze a `dict` to find and safely serialize any database entities found within. 

Our handler is ready. We created the `EvAdventureCharacter` class back in the [Character lesson](./Beginner-Tutorial-Characters.md) - let's add quest-support to it.

```python
# in evadventure/characters.py

# ...

from evennia.utils import lazy_property
from evadventure.quests import EvAdventureQuestHandler

class EvAdventureCharacter(LivingMixin, DefaultCharacter): 
    # ...

    @lazy_property
    def quests(self): 
        return EvAdventureQuestHandler(self)

    # ...

```

We also need a way to represent the quests themselves though!
## The Quest class


```{code-block} python
:linenos:
:emphasize-lines: 7,10-14,17,24,31
# in evadventure/quests.py

# ...

class EvAdventureQuest:

    key = "base-quest"
    desc = "Base quest"
    start_step = "start"

    def __init__(self, quester, questhandler=None):
        self.quester = quester
        self._questhandler = questhandler
        self.data = self.questhandler.load_quest_data(self.key)
        self._current_step = self.get_data("current_step")

        if not self.current_step:
            self.current_step = self.start_step

    def add_data(self, key, value):
        self.data[key] = value
        self.questhandler.save_quest_data(self.key)

    def get_data(self, key, default=None):
        return self.data.get(key, default)

    def remove_data(self, key):
        self.data.pop(key, None)
        self.questhandler.save_quest_data(self.key)
    
    @property
    def questhandler(self):
        return self._questhandler if self._questhandler else self.quester.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, step_name):
        self._current_step = step_name
        self.add_data("current_step", step_name)

```

- **Line 7**: Each class must have a `.key` property unquely identifying the quest. We depend on this in the quest-handler.
- **Line 12**: `quester` (the Character) is passed into this class when it is initiated inside `EvAdventureQuestHandler._load()`. 
- **Line 13**: The handler is also passed in during loading, so this quest instance can use it directly without triggering recursion during lazy loading.
- **Lines 17, 24 and 31**: `add_data` and `remove_data` call back to `questhandler.save_quest_data` so persistence happens in one place.

The `add/get/remove_data` methods are convenient wrappers for getting data in and out of the database. When we implement a quest we should prefer to use `.get_data`, `add_data` and `remove_data` over manipulating `.data` directly, since the former will make sure to save said that to the database automatically.

The `current_step` tracks the current quest 'step' we are in; what this means is up to each Quest. We set up convenient properties for setting the `current_state` and also make sure to save it in the data dict as "current_step".

The quest can have a few possible statuses: "started", "completed", "abandoned" and "failed". We create a few properties and methods for easily control that, while saving everything under the hood:

```python
# in evadventure/quests.py

# ... 

class EvAdventureQuest:

    # ... 

    @property
    def status(self):
        return self.get_data("status", "started")

    @status.setter
    def status(self, value):
        self.add_data("status", value)

    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def is_abandoned(self):
        return self.status == "abandoned"

    @property
    def is_failed(self):
        return self.status == "failed"

    def complete(self):
        self.status = "completed"

    def abandon(self):
        self.status = "abandoned"

    def fail(self):
        self.status = "failed"


```

So far we have only added convenience functions for checking statuses. How will the actual "quest" aspect of this work? 

What will happen when the system wants to check the progress of the quest, is that it will call a method `.progress()` on this class. Similarly, to get help for the current step, it will call a method `.help()`

```python

    start_step = "start"

    # help entries for quests (could also be methods)
    help_start = "You need to start first"
    help_end = "You need to end the quest"

    def progress(self, *args, **kwargs):
        getattr(self, f"step_{self.current_step}")(*args, **kwargs)

    def help(self, *args, **kwargs):
        if self.status in ("abandoned", "completed", "failed"):
            help_resource = getattr(self, f"help_{self.status}",
                                    f"You have {self.status} this quest.")
        else:
            help_resource = getattr(self, f"help_{self.current_step}", "No help available.")

        if callable(help_resource):
            # the help_* methods can be used to dynamically generate help
            return help_resource(*args, **kwargs)
        else:
            # normally it's just a string
            return str(help_resource)

```

```{sidebar} What's with the *args, **kwargs?
These are optional, but allow you to pass extra information into your quest-check. This could be very powerful if you want to add extra context to determine if a quest-step is currently complete or not.
```
Calling the `.progress(*args, **kwargs)` method will call a method named `step_<current_step>(*args, **kwargs)` on this class. That is, if we are on the _start_ step, the method called will be `self.step_start(*args, **kwargs)`. Where is this method? It has not been implemented yet! In fact, it's up to us to implement methods like this for each quest. By just adding a correctly added method, we will easily be able to add more steps to a quest.  

Similarly, calling `.help(*args, **kwargs)` will try to find a property `help_<current_step>`. If this is a callable, it will be called as  for example `self.help_start(*args, **kwargs)`. If it is given as a string, then the string will be returned as-is and the `*args, **kwargs` will be ignored.

### Example quest 

```python
# in some quest module, like world/myquests.py

from evadventure.quests import EvAdventureQuest 

class ShortQuest(EvAdventureQuest): 

    key = "simple-quest"
    desc = "A very simple quest."

    def step_start(self, *args, **kwargs): 
        """Example step!"""
        self.quester.msg("Quest started!")
        self.current_step = "end"

    def step_end(self, *args, **kwargs): 
        if not self.is_completed:
            self.quester.msg("Quest ended!")
            self.complete()

```

This is a very simple quest that will resolve on its own after two `.progress()` checks. Here's the full life cycle of this quest:

```python 
# in some module somewhere, using evennia shell or in-game using py

from evennia import search_object 
from world.myquests import ShortQuest 

character = search_object("MyCharacterName")[0]
character.quests.add(ShortQuest)

# this will echo "Quest started!" to character
character.quests.get("short-quest").progress()                     
# this will echo "Quest ended!" to character
character.quests.get("short-quest").progress()

```

### A useful Command

The player must know which quests they have and be able to inspect them. Here's a simple `quests` command to handle this:

```python
# in evadventure/quests.py

class CmdQuests(Command):
    """
    List all quests and their statuses as well as get info about the status of
    a specific quest.

    Usage:
        quests
        quest <questname>

    """
    key = "quests"
    aliases = ["quest"]

    def parse(self):
        self.quest_name = self.args.strip()

    def func(self):
        if self.quest_name:
            quest = self.caller.quests.get(self.quest_name)
            if not quest:
                self.msg(f"Quest {self.quest_name} not found.")
                return
            self.msg(f"Quest {quest.key}: {quest.status}\n{quest.help()}")
            return

        quests = self.caller.quests.all()
        if not quests:
            self.msg("No quests.")
            return

        for quest in quests:
            self.msg(f"Quest {quest.key}: {quest.status}")
```

Add this to the `CharacterCmdSet` in `mygame/commands/default_cmdsets.py`. Follow the [Adding a command lesson](../Part1/Beginner-Tutorial-Adding-Commands.md#add-the-echo-command-to-the-default-cmdset) if you are unsure how to do this. Reload and if you are playing as an `EvAdventureCharacter` you should be able to use `quests` to view your quests.

## Testing 

> Create a new folder `evadventure/tests/test_quests.py`.

```{sidebar} 
An example test suite for quests is found in `evennia/contrib/tutorials/evadventure`, as [tests/test_quests.py](evennia.contrib.tutorials.evadventure.tests.test_quests).
```
Testing of the quests means creating a test character, making a dummy quest, add it to the character's quest handler and making sure all methods work correcly. Create the testing quest so that it will automatically step forward when calling `.progress()`, so you can make sure it works as intended. 

## Conclusions 

What we created here is just the framework for questing. The actual complexity will come when creating the quests themselves (that is, implementing the `step_<current_step>(*args, **kwargs)` methods), which is something we'll get to later, in [Part 4](../Part4/Beginner-Tutorial-Part4-Overview.md) of this tutorial.
