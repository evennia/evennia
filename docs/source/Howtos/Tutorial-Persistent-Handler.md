# Making a Persistent object Handler

A _handler_ is a convenient way to group functionality on an object. This allows you to logically group all actions related to that thing in one place. This tutorial expemplifies how to make your own handlers and make sure data you store in them survives a reload.

For example, when you do `obj.attributes.get("key")` or `obj.tags.add('tagname')` you are evoking handlers stored as `.attributes` and `tags` on the `obj`. On these handlers are methods (`get()` and `add()` in this example).

## Base Handler example

Here is a base way to set up an on-object handler:

```python

from evennia import DefaultObject, create_object
from evennia.utils.utils import lazy_property

class NameChanger:
    def __init__(self, obj):
        self.obj = obj

    def add_to_key(self, suffix):
        self.obj.key = f"self.obj.key_{suffix}"

# make a test object
class MyObject(DefaultObject):
    @lazy_property:
    def namechange(self):
       return NameChanger(self)


obj = create_object(MyObject, key="test")
print(obj.key)
>>> "test"
obj.namechange.add_to_key("extra")
print(obj.key)
>>> "test_extra"
```

What happens here is that we make a new class `NameChanger`. We use the
`@lazy_property` decorator to set it up - this means the handler will not be
actually created until someone really wants to use it, by accessing
`obj.namechange` later. The decorated `namechange` method returns the handler
and makes sure to initialize it with `self` - this becomes the `obj` inside the
handler!

We then make a silly method `add_to_key` that uses the handler to manipulate the
key of the object. In this example, the handler is pretty pointless, but
grouping functionality this way can both make for an easy-to-remember API and
can also allow you cache data for easy access - this is how the
`AttributeHandler` (`.attributes`) and `TagHandler` (`.tags`) works.

## Persistent storage of data in handler

Let's say we want to track 'quests' in our handler. A 'quest' is a regular class
that represents the quest. Let's make it simple as an example:

```python
# for example in mygame/world/quests.py


class Quest:

    key = "The quest for the red key"

    def __init__(self):
        self.current_step = "start"

    def check_progress(self):
        # uses self.current_step to check
        # progress of this quest
        getattr(self, f"step_{self.current_step}")()

    def step_start(self):
        # check here if quest-step is complete
        self.current_step = "find_the_red_key"
    def step_find_the_red_key(self):
        # check if step is complete
        self.current_step = "hand_in_quest"
    def step_hand_in_quest(self):
        # check if handed in quest to quest giver
        self.current_step = None  # finished

```


We expect the dev to make subclasses of this to implement different quests. Exactly how this works doesn't matter, the key is that we want to track `self.current_step` - a property that _should survive a server reload_. But so far there is no way for `Quest` to accomplish this, it's just a normal Python class with no connection to the database.

### Handler with save/load capability

Let's make a `QuestHandler` that manages a character's quests.

```python
# for example in the same mygame/world/quests.py


class QuestHandler:
    def __init__(self, obj):
        self.obj = obj
        self.do_save = False
        self._load()

    def _load(self):
        self.storage = self.obj.attributes.get(
            "quest_storage", default={}, category="quests")

    def _save(self):
        self.obj.attributes.add(
            "quest_storage", self.storage, category="quests")
        self._load()  # important
        self.do_save = False

    def add(self, questclass):
        self.storage[questclass.key] = questclass(self.obj)
        self._save()

    def check_progress(self):
        for quest in self.storage.values():
            quest.check_progress()
        if self.do_save:
            # .do_save is set on handler by Quest if it wants to save progress
            self._save()

```

The handler is just a normal Python class and has no database-storage on its own. But it has a link to `.obj`, which is assumed to be a full typeclased entity, on which we can create persistent [Attributes](../Components/Attributes.md) to store things however we like!

We make two helper methods `_load` and
`_save` that handles local fetches and saves `storage` to an Attribute on the object.  To avoid saving more than necessary, we have a property `do_save`. This we will set in `Quest` below.

> Note that once we `_save` the data, we need to call `_load` again. This is to make sure the version we store on the handler is properly de-serialized. If you get an error about data being `bytes`, you probably missed this step.


### Make quests storable

The handler will save all `Quest` objects as a `dict` in an Attribute on `obj`. We are not done yet though, the `Quest` object needs access to the `obj` too - not only will this is important to figure out if the quest is complete (the `Quest` must be able to check the quester's inventory to see if they have the red key, for example), it also allows the `Quest` to tell the handler when its state changed and it should be saved.

We change the `Quest` such:

```python
from evennia.utils import dbserialize


class Quest:

    def __init__(self, obj):
        self.obj = obj
        self._current_step = "start"

    def __serialize_dbobjs__(self):
        self.obj = dbserialize.dbserialize(self.obj)

    def __deserialize_dbobjs__(self):
        if isinstance(self.obj, bytes):
            self.obj = dbserialize.dbunserialize(self.obj)

    @property
    def questhandler(self):
        return self.obj.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, value):
        self._current_step = value
        self.questhandler.do_save = True  # this triggers save in handler!

    # [same as before]

```

The `Quest.__init__` now takes `obj` as argument, to match what we pass to it in
`QuestHandler.add`. We want to monitor the changing of `current_step`, so we
make it into a `property`. When we edit that value, we set the `do_save` flag on
the handler, which means it will save the status to database once it has checked
progress on all its quests. The `Quest.questhandler` property allows to easily
get back to the handler (and the object on which it sits).

The `__serialize__dbobjs__` and `__deserialize_dbobjs__` methods are needed
because `Attributes` can't store 'hidden' database objects (the `Quest.obj`
property. The methods help Evennia serialize/deserialize `Quest` propertly when
the handler saves it.  For more information, see [Storing Single
objects](../Components/Attributes.md#storing-single-objects) in the Attributes
documentation.

### Tying it all together

The final thing we need to do is to add the quest-handler to the character:

```python
# in mygame/typeclasses/characters.py

from evennia import DefaultCharacter
from evennia.utils.utils import lazy_property
from .world.quests import QuestHandler  # as an example


class Character(DefaultCharacter):
    # ...
    @lazy_property
    def quests(self):
        return QuestHandler(self)

```


You can now make your Quest classes to describe your quests and add them to
characters with

```python
character.quests.add(FindTheRedKey)
```

and can later do

```python
character.quests.check_progress()
```

and be sure that quest data is not lost between reloads.

You can find a full-fledged quest-handler example as  [EvAdventure
quests](evennia.contribs.tutorials.evadventure.quests) contrib in the Evennia
repository.
