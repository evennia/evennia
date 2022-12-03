# Building a chair you can sit on

In this lesson we will make use of what we have learned to create a new game object: a chair you can sit on. 

Out goals are:

- We want a new 'sittable' object, a `Chair` in particular.
- We want to be able to use a command to sit in the chair.
- Once we are sitting in the chair it should affect us somehow. To demonstrate this store 
the current chair in an attribute `is_sitting`. Other systems could check this to affect us in different ways.
- A character should be able to stand up and move away from the chair.
- When you sit down you should not be able to walk to another room without first standing up.

## Make us not able to move while resting

When you are sitting in a chair you can't just walk off without first standing up.
This requires a change to our Character typeclass. Open `mygame/typeclasses/characters.py`:

```python
# in mygame/typeclasses/characters.py

# ...

class Character(DefaultCharacter):
    # ...

    def at_pre_move(self, destination):
       """
       Called by self.move_to when trying to move somewhere. If this returns
       False, the move is immediately cancelled.
       """
       if self.db.is_resting:
           self.msg("You need to stand up first.")
           return False
       return True

```

When moving somewhere, [character.move_to](evennia.objects.objects.DefaultObject.move_to) is called. This in turn
will call `character.at_pre_move`.  If this returns `False`, the move is aborted. 

Here we look for an Attribute `is_resting` (which we will assign below) to determine if we are stuck on the chair or not.

## Making the Chair itself

Next we need the Chair itself, or rather a whole family of "things you can sit on" that we will call _sittables_. We can't just use a default Object since we want a sittable to contain some custom code. We need a new, custom Typeclass. Create a new module `mygame/typeclasses/sittables.py` with the following content:

```{code-block} python
:linenos:
:emphasize-lines: 3,7,15,16,23,24,25

# in mygame/typeclasses/sittables.py

from typeclasses.objects import Object

class Sittable(Object):

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        current = self.db.sitter
        if current:
            if current == sitter:
                sitter.msg(f"You are already sitting on {self.key}.")
            else:
                sitter.msg(f"You can't sit on {self.key} "
                        f"- {current.key} is already sitting there!")
            return
        self.db.sitting = sitter
        sitter.db.is_sitting = self.obj
        sitter.msg(f"You sit on {self.key}")
```

This handles the logic of someone sitting down on the chair.  

- **Line 3**: We inherit from the empty `Object` class in `mygame/typeclasses/objects.py`. This means we can theoretically modify that in the future and have those changes affect sittables too.
- **Line 7**: The `do_sit` method expects to be called with the argument `sitter`, which is to be an `Object` (most likely a `Character`). This is the one wanting to sit down.
-  **Line 15**: Note that, if the [Attribute](../../../Components/Attributes.md) `sitter` is not defined on the chair (because this is the first time someone sits in it), this will simply return `None`, which is fine. 
- **Lines 16-22** We check if someone is already sitting on the chair and returns appropriate error messages depending on if it's you or someone else. We use `return` to abort the sit-action.
- **Line 23**: If we get to this point, `sitter` gets to, well, sit down. We store them in the `sitter` Attribute on the chair.
- **Line 24**: `self.obj` is the chair this command is attachd to. We store that in the  `is_sitting` Attribute on the `sitter` itself.
- **Line 25**: Finally we tell the sitter that they could sit down.

Let's continue: 

```{code-block} python 
:linenos: 
:emphasize-lines: 12,15,16,17

# add this right after the `do_sit method` in the same class 

    def do_stand(self, stander):
        """
        Called when trying to stand from this object.

        Args:
            stander (Object): The one trying to stand up.

        """
        current = self.db.sitter
        if not stander == current:
            stander.msg(f"You are not sitting on {self.key}.")
        else:
            self.db.sitter = None
            del stander.db.is_sitting
            stander.msg(f"You stand up from {self.key}")
```

This is the inverse of sitting down; we need to do some cleanup. 

- **Line 12**: If we are not sitting on the chair, it makes no sense to stand up from it.
- **Line 15**: If we get here, we could stand up. We make sure to un-set the `sitter` Attribute so someone else could use the chair later. 
- **Line 16**: The character is no longer sitting, so we delete their `is_sitting` Attribute. We could also have done `stander.db.is_sitting = None` here, but deleting the Attribute feels cleaner.
- **Line 17**: Finally, we inform them that they stood up successfully.

One could imagine that one could have the future `sit` command (which we haven't created yet) check if someone is already sitting in the chair instead. This would work too, but letting the `Sittable` class handle the logic around who can sit on it makes sense.

We let the typeclass handle the logic, and also let it do all the return messaging. This makes it easy to churn out a bunch of chairs for people to sit on. 

### Sitting on or in? 

It's fine to sit 'on' a chair. But what if our Sittable is an armchair? 

```
> armchair = evennia.create_object("typeclasses.sittables.Sittable", key="armchair", location=here)
> armchair.do_sit(me)
> You sit on armchair.
```

This is not grammatically correct, you actually sit "in" an armchair rather than "on" it. It's also possible to both sit 'in' or 'on' a chair depending on the type of chair (English is weird). We want to be able to control this.

We _could_ make a child class of `Sittable` named `SittableIn` that makes this change, but that feels excessive. Instead we will modify what we have: 

```{code-block} python 
:linenos:
:emphasize-lines: 15,22,43

# in mygame/typeclasses/sittables.py

from evennia import DefaultObject

class Sittable(DefaultObject):

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        adjective = self.db.adjective or "on"
        current = self.db.sitter
        if current:
            if current == sitter:
                sitter.msg(f"You are already sitting {adjective} {self.key}.")
            else:
                sitter.msg(
                    f"You can't sit {adjective} {self.key} "
                    f"- {current.key} is already sitting there!")
            return
        self.db.sitting = sitter
        sitter.db.is_sitting = self.obj
        sitter.msg(f"You sit {adjective} {self.key}")

    def do_stand(self, stander):
        """
        Called when trying to stand from this object.

        Args:
            stander (Object): The one trying to stand up.

        """
        current = self.db.sitter
        if not stander == current:
            stander.msg(f"You are not sitting {self.db.adjective} {self.key}.")
        else:
            self.db.sitting = None
            del stander.db.is_sitting
            stander.msg(f"You stand up from {self.key}")
```

- **Line 15**: We grab the `adjective` Attribute. Using `seld.db.adjective or "on"` here means that if the Attribute is not set (is `None`/falsy) the default "on" string will be assumed.
- **Lines 22 and 43**: We use this adjective to modify the return text we see.  

`reload`  the server. An advantage of using Attributes like this is that they can be modified on the fly, in-game. Let's look at a builder could use this by normal building commands (no need for `py`): 

```
> set armchair/adjective = in 
```

Since we haven't added the `sit` command yet, we must still use `py` to test: 

```
> py armchair = evennia.search_object("armchair")[0];armchair.do_sit(me)
You sit in armchair.
```

### Extra credits 

What if we want some more dramatic flair when you sit down in certain chairs? 

    You sit down and a whoopie cushion makes a loud fart noise!

You can make this happen by tweaking your `Sittable` class having the return messages be replaceable by `Attributes` that you can set on the object you create. You want something like this: 

```
> chair = evennia.create_object("typeclasses.sittables.Sittable", key="pallet")
> chair.do_sit(me)
You sit down on pallet.
> chair.do_stand(me)
You stand up from pallet.
> chair.db.msg_sitting_down = "You sit down and a whoopie cushion makes a loud fart noise!"
> chair.do_sit(me)
You sit down and a whoopie cushion makes a loud fart noise!
```

That is, if you are not setting the Attribute, you should get a default value. We leave this implementation up to the reader.

## Adding commands

As we discussed in the [lesson about adding Commands](./Beginner-Tutorial-More-on-Commands.md), there are two main ways to design the commands for sitting and standing up:
- You can store the commands on the chair so they are only available when a chair is in the room
- You can store the commands on the Character so they are always available and you must always specify which chair to sit on.

Both of these are very useful to know about, so in this lesson we'll try both.

### Command variant 1: Commands on the chair

This way to implement `sit` and `stand` puts new cmdsets on the Sittable itself.
As we've learned before, commands on objects are made available to others in the room.
This makes the command easy but instead adds some complexity in the management of the CmdSet.

This is how it could look if `armchair` is in the room (if you overrode the sit message):

    > sit
    As you sit down in armchair, life feels easier.

What happens if there are sittables `sofa` and `barstool` also in the room? Evennia will automatically
handle this for us and allow us to specify which one we want:

    > sit
    More than one match for 'sit' (please narrow target):
     sit-1 (armchair)
     sit-2 (sofa)
     sit-3 (barstool)
    > sit-1
    As you sit down in armchair, life feels easier.

To keep things separate we'll make a new module `mygame/commands/sittables.py`:

```{sidebar} Separate Commands and Typeclasses?

You can organize these things as you like. If you wanted you could put the sit-command + cmdset together with the `Sittable` typeclass in `mygame/typeclasses/sittables.py`. That has the advantage of keeping everything related to sitting in one place. But there is also some organizational merit to keeping all Commands in one place as we do here.
```

```{code-block} python
:linenos: 
:emphasize-lines: 11,19,23

# in mygame/commands/sittables.py 

from evennia import Command, CmdSet

class CmdSit(Command):
    """
    Sit down.
    """
    key = "sit"
    def func(self):
        self.obj.do_sit(self.caller)

class CmdStand(Command):
     """
     Stand up.
     """
     key = "stand"
     def func(self):
         self.obj.do_stand(self.caller)


class CmdSetSit(CmdSet):
    priority = 1
    def at_cmdset_creation(self):
        self.add(CmdSit)
        self.add(CmdStand)

```

As seen, the commands are nearly trivial. 

- **Lines 11 and 19**: The `self.obj` is the object to which we added the cmdset with this Command (so the chair). We just call the `do_sit/stand` on that object and pass the `caller` (the person sitting down). The `Sittable` will do the rest.
- **Line 23**: The   `priority = 1` on `CmdSetSit` means that same-named Commands from this cmdset merge with a bit higher priority than Commands from the on-Character-cmdset (which has `priority = 0`). This means that if you have a `sit` command on your Character and comes into a room with a chair, the `sit` command on the chair will take precedence. 

We also need to make a change to our `Sittable` typeclass. Open `mygame/typeclasses/sittables.py`:

```{code-block} python 
:linenos: 
:emphasize-lines: 4,10,11

# in mygame/typeclasses/sittables.py

from evennia import DefaultObject
from commands.sittables import CmdSetSit 

class Sittable(DefaultObject):
    """
    (docstring)
    """
    def at_object_creation(self):
        self.cmdset.add_default(CmdSetSit)A
    # ... 
```

- **Line 4**: We must install the `CmdSetSit` . 
- **Line 10**: The `at_object_creation` method will only be called once, when the object is first created. 
- **Line 11**: We add the command-set as a 'default' cmdset with `add_default`. This makes it persistent also protects it from being deleted should another cmdset be added. See [Command Sets](../../../Components/Command-Sets.md) for more info. 

Make sure to `reload` to make the code changes available.
	
All _new_ Sittables will now have your `sit` Command. Your existing `armchair` will not though. This is because  `at_object_creation` will not re-run for already existing objects. We can update it manually:

    > update armchair

We could also update all existing sittables (all on one line):

```{sidebar} List comprehensions 
`[obj for obj in iterator]` is an example of a _list comprehension_. Think of it as an efficient way to construct a new list all in one line. You can read more about list comprehensions [here in the Python docs](https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions).
```

    > py from typeclasses.sittables import Sittable ;
           [sittable.at_object_creation() for sittable in Sittable.objects.all()]

We should now be able to use `sit` while in the room with the armchair.

    > sit
    As you sit down in armchair, life feels easier.
    > stand
    You stand up from armchair.

One issue with placing the `sit` (or `stand`) Command "on" the chair is that it will not be available when in a room without a Sittable object:

    > sit
    Command 'sit' is not available. ...

This is practical but not so good-looking; it makes it harder for the user to know a `sit` action is at all possible. Here is a trick for fixing this. Let's add _another_ Command to the bottom
of `mygame/commands/sittables.py`:

```{code-block} python 
:linenos: 
:emphasize-lines: 9,12

# after the other commands in mygame/commands/sittables.py
# ...

class CmdNoSitStand(Command):
    """
    Sit down or Stand up
    """
    key = "sit"
    aliases = ["stand"]

    def func(self):
        if self.cmdname == "sit":
            self.msg("You have nothing to sit on.")
        else:
            self.msg("You are not sitting down.")

```

- **Line 9**: This command responds both to `sit` and `stand` because we added `stand` to its `aliases` list. Command aliases have the same 'weight' as the `key` of the  command, both equally identify the Command.
- **Line 12**: The `.cmdname` of a `Command` holds the name actually used to call it. This will be one of `"sit"` or `"stand"`.  This leads to different return messages. 

We don't need a new CmdSet for this, instead we will add this to the default Character cmdset. Open `mygame/commands/default_cmdsets.py`:

```python
# in mygame/commands/default_cmdsets.py

# ...
from commands import sittables

class CharacterCmdSet(CmdSet):
    """
    (docstring)
    """
    def at_cmdset_creation(self):
        # ...
        self.add(sittables.CmdNoSitStand)

```

As usual, make sure to `reload` the server to have the new code recognized.

To test we'll build a new location without any comfy armchairs and go there:

    > tunnel n = kitchen
    north
    > sit
    You have nothing to sit on.
    > south
    sit
    As you sit down in armchair, life feels easier.

We now have a fully functioning `sit` action that is contained with the chair itself. When no chair is around, a default error message is shown.

How does this work? There are two cmdsets at play, both of which have a `sit/stand` Command - one on the `Sittable` (armchair) and the other on us (via the `CharacterCmdSet`). Since we set a `priority=1` on the chair's cmdset (and `CharacterCmdSet` has `priority=0`), there will be no command-collision: the chair's `sit` takes precedence over the `sit` defined on us ... until there is no chair around. 

So this handles `sit`. What about `stand`? That will work just fine:

    > stand
    You stand up from armchair.
    > north
    > stand
    You are not sitting down.

We have one remaining problem with `stand` though - what happens when you are sitting down and try to `stand` in a room with more than one `Sittable`:

    > stand
    More than one match for 'stand' (please narrow target):
     stand-1 (armchair)
     stand-2 (sofa)
     stand-3 (barstool)

Since all the sittables have the `stand` Command on them, you'll get a multi-match error. This _works_  ... but you could pick _any_ of those sittables to "stand up from". That's really weird. 

With `sit` it was okay to get a choice - Evennia can't know which chair we intended to sit on. But once we sit we sure know from which chair we should stand up from! We must make sure that we only get the command from the chair we are actually sitting on.

We will fix this with a [Lock](../../../Components/Locks.md) and a custom `lock function`. We want a lock on the `stand` Command that only makes it available when the caller is actually sitting on the chair that particular `stand` command is attached to.

First let's add the lock so we see what we want. Open `mygame/commands/sittables.py`:

```{code-block} python 
:linenos:
:emphasize-lines: 10

# in mygame/commands/sittables.py

# ...

class CmdStand(Command):
     """
     Stand up.
     """
     key = "stand"
     lock = "cmd:sitsonthis()"

     def func(self):
         self.obj.do_stand(self.caller)
# ...
```

- **Line 10**: This is the lock definition. It's on the form `condition:lockfunc`. The `cmd:` type lock is checked by Evennia when determining if a user has access to a Command at all. We want the lock-function to only return `True` if this command is on a chair which the caller is sitting on.
  What will be checked is the `sitsonthis` _lock function_ which doesn't exist yet.

Open `mygame/server/conf/lockfuncs.py` to add it!

```python
# mygame/server/conf/lockfuncs.py

"""
(module lockstring)
"""
# ...

def sitsonthis(accessing_obj, accessed_obj, *args, **kwargs):
    """
    True if accessing_obj is sitting on/in the accessed_obj.
    """
    return accessed_obj.db.sitting == accessing_obj

# ...
```

Evennia knows that _all_ functions in `mygame/server/conf/lockfuncs` should be possible to use in a lock definition. 

All lock functions must acccept the same arguments. The arguments are required and Evennia will pass all relevant objects as needed. 

```{sidebar} Lockfuncs

Evennia provides a large number of default lockfuncs, such as checking permission-levels, if you are carrying or are inside the accessed object etc. There is no concept of 'sitting' in default Evennia however, so this we need to specify ourselves.
```

- `accessing_obj` is the one trying to access the lock. So us, in this case.
- `accessed_obj` is the entity we are trying to gain a particular type of access to. So the chair.
- `args` is a tuple holding any arguments passed to the lockfunc. Since we use `sitsondthis()` this will be empty (and if we add anything, it will be ignored).
- `kwargs` is a tuple of keyword arguments passed to the lockfuncs. This will be empty as well in our example.

Make sure you `reload`.

If you are superuser, it's important that you `quell` yourself before trying this out. This is because the superuser bypasses all locks - it can never get locked out, but it means it will also not see the effects of a lock like this.

    > quell
    > stand
    You stand up from armchair

None of the other sittables' `stand` commands passed the lock and only the one we are actually sitting on did! This is a fully functional chair now!

Adding a Command to the chair object like this is powerful and is a good technique to know. It does come with some caveats though, as we've seen.

We'll now try another way to add the `sit/stand` commands.

### Command variant 2: Command on Character

Before we start with this, delete the chairs you've created: 

	> del armchair 
	> del sofa 
	> (etc)

The make the following changes:

- In `mygame/typeclasses/sittables.py`, comment out the entire `at_object_creation` method.
- In `mygame/commands/default_cmdsets.py`, comment out the line `self.add(sittables.CmdNoSitStand)`.

This disables the on-object command solution so we can try an alternative. Make sure to `reload` so the changes are known to Evennia.

In this variation we will put the `sit` and `stand` commands on the `Character` instead of on the chair. This makes some things easier, but makes the Commands themselves more complex because they will not know which chair to sit on. We can't just do `sit` anymore. This is how it will work.

    > sit <chair>
    You sit on chair.
    > stand
    You stand up from chair.

Open `mygame/commands/sittables.py` again. We'll add a new sit-command. We name the class `CmdSit2` since we already have `CmdSit` from the previous example. We put everything at the end of the module to keep it separate.

```{code-block} python 
:linenos:
:emphasize-lines: 4,27,32,35

# in mygame/commands/sittables.py

from evennia import Command, CmdSet
from evennia import InterruptCommand

class CmdSit(Command):
    # ...

# ...

# new from here

class CmdSit2(Command):
    """
    Sit down.

    Usage:
        sit <sittable>

    """
    key = "sit"

    def parse(self):
        self.args = self.args.strip()
        if not self.args:
            self.caller.msg("Sit on what?")
            raise InterruptCommand

    def func(self):

        # self.search handles all error messages etc.
        sittable = self.caller.search(self.args)
        if not sittable:
            return
        try:
            sittable.do_sit(self.caller)
        except AttributeError:
            self.caller.msg("You can't sit on that!")

```

```{sidebar} Raising exceptions

Raising an exception allows for immediately interrupting the current program flow. Python automatically raises error-exceptions when detecting problems with the code. It will be raised up through the sequence of called code (the 'stack') until it's either `caught` with a `try ... except` or reaches the outermost scope where it'll be logged or displayed. In this case Evennia knows to catch the `InterruptCommand` exception and stop the command execution early.
```

- **Line 4**: We need the `InterruptCommand` to be able to abort command parsing early (see below).
- **Line 27**: The `parse` method runs before the `func` method on a `Command`. If no argument is provided to the command, we want to fail early, already in `parse`, so `func` never fires. Just `return` is not enough to do that, we need to `raise InterruptCommand`. Evennia will see a raised `InterruptCommand` as a sign it should immediately abort the command execution.
- **Line 32**: We use the parsed command arguments as the target-chair to search for. As discussed in the [search tutorial](./Beginner-Tutorial-Searching-Things.md), `self.caller.search()` will handle error messages itself. So if it returns `None`, we can just `return`. 
- **Line 35-38**: The `try...except` block 'catches' and exception and handles it. In this case we try to run `do_sit` on the object. If the object we found is _not_ a `Sittable`, it will likely not have a `do_sit` method and an `AttributeError` will be raised. We should handle that case gracefully.

Let's do the `stand` command while we are at it. Since the Command is external to the chair we don't know which object we are sitting on and have to search for it. In this case we really want to find _only_ things we are sitting on.

```{code-block} python 
:linenos:
:emphasize-lines: 17,21

# end of mygame/commands/sittables.py

class CmdStand2(Command):
    """
    Stand up.

    Usage:
        stand

    """
    key = "stand"

    def func(self):

    caller = self.caller
    # if we are sitting, this should be set on us
    sittable = caller.db.is_sitting
    if not sittable:
        caller.msg("You are not sitting down.")
    else:
        sittable.do_stand(caller)

```

- **Line 17**: We didn't need the `is_sitting` Attribute for the first version of these Commands, but we do need it now. Since we have this, we don't need to search and know just which chair we sit on. If we don't have this set, we are not sitting anywhere. 
- **Line 21**: We stand up using the sittable we found.



All that is left now is to make this available to us. This type of Command should be available to us all the time so we can put it in the default Cmdset on the Character. Open `mygame/commands/default_cmdsets.py`.


```python
# in mygame/commands/default_cmdsets.py

# ...
from commands import sittables

class CharacterCmdSet(CmdSet):
    """
    (docstring)
    """
    def at_cmdset_creation(self):
        # ...
        self.add(sittables.CmdSit2)
        self.add(sittables.CmdStand2)

```

Make sure to `reload`. 

Now let's try it out:

    > create/drop sofa : sittables.Sittable
    > sit sofa
    You sit down on sofa.
    > stand
    You stand up from sofa.
    > north 
    > sit sofa 
    > You can't find 'sofa'.

Storing commands on the Character centralizes them, but you must instead search or store any external objects you want that command to interact on.

## Conclusions

In this lesson we built ourselves a chair and even a sofa! 

- We modified our `Character` class to avoid moving when sitting down.
- We made a new `Sittable` typeclass
- We tried two ways to allow a user to interact with sittables using `sit` and `stand` commands.

Eagle-eyed readers will notice that the `stand` command sitting "on" the chair (variant 1) would work just fine together with the `sit` command sitting "on" the Character (variant 2). There is nothing stopping you from mixing them, or even try a third solution that better fits what you have in mind.

This concludes the first part of the Beginner tutorial!