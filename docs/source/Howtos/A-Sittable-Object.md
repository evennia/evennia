[prev lesson](../Unimplemented.md) | [next lesson](../Unimplemented.md)

# Making a sittable object

In this lesson we will go through how to make a chair you can sit on. Sounds easy, right?
Well it is. But in the process of making the chair we will need to consider the various ways
to do it depending on how we want our game to work.

The goals of this lesson are as follows:

- We want a new 'sittable' object, a Chair in particular".
- We want to be able to use a command to sit in the chair.
- Once we are sitting in the chair it should affect us somehow. To demonstrate this we'll
  set a flag "Resting" on the Character sitting in the Chair.
- When you sit down you should not be able to walk to another room without first standing up.
- A character should be able to stand up and move away from the chair.

There are two main ways to design the commands for sitting and standing up.
- You can store the commands on the chair so they are only available when a chair is in the room
- You can store the commands on the Character so they are always available and you must always specify
  which chair to sit on.

Both of these are very useful to know about, so in this lesson we'll try both. But first
we need to handle some basics.


## Don't move us when resting

When you are sitting in a chair you can't just walk off without first standing up.
This requires a change to our Character typeclass. Open `mygame/typeclasses/characters.py`:

```python

# ...

class Character(DefaultCharacter):
    # ...

    def at_pre_move(self, destination):
       """
       Called by self.move_to when trying to move somewhere. If this returns
       False, the move is immediately cancelled.
       """
       if self.db.is_resting:
           self.msg("You can't go anywhere while resting.")
           return False
       return True

```

When moving somewhere, [character.move_to](evennia.objects.objects.DefaultObject.move_to) is called. This in turn
will call `character.at_pre_move`. Here we look for an Attribute `is_resting` (which we will assign below)
to determine if we are stuck on the chair or not.

## Making the Chair itself

Next we need the Chair itself, or rather a whole family of "things you can sit on" that we will call
_sittables_. We can't just use a default Object since we want a sittable to contain some custom code. We need
a new, custom Typeclass. Create a new module `mygame/typeclasses/sittables.py` with the following content:

```python

from evennia import DefaultObject

class Sittable(DefaultObject):

    def at_object_creation(self):
        self.db.sitter = None

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        current = self.db.sitter
        if current:
            if current == sitter:
                sitter.msg("You are already sitting on {self.key}.")
            else:
                sitter.msg(f"You can't sit on {self.key} "
                        f"- {current.key} is already sitting there!")
            return
        self.db.sitting = sitter
        sitter.db.is_resting = True
        sitter.msg(f"You sit on {self.key}")

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
            self.db.sitting = None
            stander.db.is_resting = False
            stander.msg(f"You stand up from {self.key}")
```

Here we have a small Typeclass that handles someone trying to sit on it. It has two methods that we can simply
call from a Command later. We set the `is_resting` Attribute on the one sitting down.

One could imagine that one could have the future `sit` command check if someone is already sitting in the
chair instead. This would work too, but letting the `Sittable` class handle the logic around who can sit on it makes
logical sense.

We let the typeclass handle the logic, and also let it do all the return messaging. This makes it easy to churn out
a bunch of chairs for people to sit on. But it's not perfect. The `Sittable` class is general. What if you want to
make an armchair. You sit "in" an armchair rather than "on" it. We _could_ make a child class of `Sittable` named
`SittableIn` that makes this change, but that feels excessive. Instead we will make it so that Sittables can
modify this per-instance:


```python

from evennia import DefaultObject

class Sittable(DefaultObject):

    def at_object_creation(self):
        self.db.sitter = None
        # do you sit "on" or "in" this object?
        self.db.adjective = "on"

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        adjective = self.db.adjective
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
        sitter.db.is_resting = True
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
            stander.db.is_resting = False
            stander.msg(f"You stand up from {self.key}")
```

We added a new Attribute `adjective` which will probably usually be `in` or `on` but could also be `at` if you
want to be able to sit _at a desk_ for example. A regular builder would use it like this:

    > create/drop armchair : sittables.Sittable
    > set armchair/adjective = in

This is probably enough. But all those strings are hard-coded. What if we want some more dramatic flair when you
sit down?

    You sit down and a whoopie cushion makes a loud fart noise!

For this we need to allow some further customization. Let's let the current strings be defaults that
we can replace.

```python

from evennia import DefaultObject

class Sittable(DefaultObject):
    """
    An object one can sit on

    Customizable Attributes:
       adjective: How to sit (on, in, at etc)
    Return messages (set as Attributes):
       msg_already_sitting: Already sitting here
            format tokens {adjective} and {key}
       msg_other_sitting: Someone else is sitting here.
            format tokens {adjective}, {key} and {other}
       msg_sitting_down: Successfully sit down
            format tokens {adjective}, {key}
       msg_standing_fail: Fail to stand because not sitting.
            format tokens {adjective}, {key}
       msg_standing_up: Successfully stand up
            format tokens {adjective}, {key}

    """
    def at_object_creation(self):
        self.db.sitter = None
        # do you sit "on" or "in" this object?
        self.db.adjective = "on"

    def do_sit(self, sitter):
        """
        Called when trying to sit on/in this object.

        Args:
            sitter (Object): The one trying to sit down.

        """
        adjective = self.db.adjective
        current = self.db.sitter
        if current:
            if current == sitter:
                if self.db.msg_already_sitting:
                    sitter.msg(
                        self.db.msg_already_sitting.format(
                            adjective=self.db.adjective, key=self.key))
                else:
                    sitter.msg(f"You are already sitting {adjective} {self.key}.")
            else:
                if self.db.msg_other_sitting:
                    sitter.msg(self.db.msg_already_sitting.format(
                        other=current.key, adjective=self.db.adjective, key=self.key))
                else:
                    sitter.msg(f"You can't sit {adjective} {self.key} "
                               f"- {current.key} is already sitting there!")
            return
        self.db.sitting = sitter
        sitter.db.is_resting = True
        if self.db.msg_sitting_down:
            sitter.msg(self.db.msg_sitting_down.format(adjective=adjective, key=self.key))
        else:
            sitter.msg(f"You sit {adjective} {self.key}")

    def do_stand(self, stander):
        """
        Called when trying to stand from this object.

        Args:
            stander (Object): The one trying to stand up.

        """
        current = self.db.sitter
        if not stander == current:
            if self.db.msg_standing_fail:
                stander.msg(self.db.msg_standing_fail.format(
                    adjective=self.db.adjective, key=self.key))
            else:
                stander.msg(f"You are not sitting {self.db.adjective} {self.key}")
        else:
            self.db.sitting = None
            stander.db.is_resting = False
            if self.db.msg_standing_up:
                stander.msg(self.db.msg_standing_up.format(
                                adjective=self.db.adjective, key=self.key))
            else:
                stander.msg(f"You stand up from {self.key}")
```

Here we really went all out with flexibility. If you need this much is up to you.
We added a bunch of optional Attributes to hold alternative versions of all the messages.
There are some things to note:

- We don't actually initiate those Attributes in `at_object_creation`. This is a simple
optimization. The assumption is that _most_ chairs will probably not be this customized.
So initiating a bunch of Attributes to, say, empty strings would be a lot of useless database calls.
The drawback is that the available Attributes become less visible when reading the code. So we add a long
describing docstring to the end to explain all you can use.
- We use `.format` to inject formatting-tokens in the text. The good thing about such formatting
markers is that they are _optional_. They are there if you want them, but Python will not complain
if you don't include some or any of them. Let's see an example:

    > reload   # if you have new code
    > create/drop armchair : sittables.Sittable
    > set armchair/adjective = in
    > set armchair/msg_sitting_down = As you sit down {adjective} {key}, life feels easier.
    > set armchair/msg_standing_up = You stand up from {key}. Life resumes.

The `{key}` and `{adjective}` are examples of optional formatting markers. Whenever the message is
returned, the format-tokens within will be replaced with `armchair` and `in` respectively. Should we
rename the chair later, this will show in the messages automatically (since `{key}` will change).

We have no Command to use this chair yet. But we can try it out with `py`:

    > py self.search("armchair").do_sit(self)
    As you sit down in armchair, life feels easier.
    > self.db.resting
    True
    > py self.search("armchair").do_stand(self)
    You stand up from armchair. Life resumes
    > self.db.resting
    False

If you follow along and get a result like this, all seems to be working well!

## Command variant 1: Commands on the chair

This way to implement `sit` and `stand` puts new cmdsets on the Sittable itself.
As we've learned before, commands on objects are made available to others in the room.
This makes the command easy but instead adds some complexity in the management of the CmdSet.

This is how it will look if `armchair` is in the room:

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

    You can organize these things as you like. If you wanted you could put the sit-command + cmdset
    together with the `Sittable` typeclass in `mygame/typeclasses/sittables.py`. That has the advantage of
    keeping everything related to sitting in one place. But there is also some organizational merit to
    keeping all Commands in one place as we do here.

```

```python
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

As seen, the commands are nearly trivial. `self.obj` is the object to which we added the cmdset with this
Command (so for example a chair). We just call the `do_sit/stand` on that object and the `Sittable` will
do the rest.

Why that `priority = 1` on `CmdSetSit`? This makes same-named Commands from this cmdset merge with a bit higher
priority than Commands from the Character-cmdset. Why this is a good idea will become clear shortly.

We also need to make a change to our `Sittable` typeclass. Open `mygame/typeclasses/sittables.py`:

```python
from evennia import DefaultObject
from commands.sittables import CmdSetSit  # <- new

class Sittable(DefaultObject):
    """
    (docstring)
    """
    def at_object_creation(self):

        self.db.sitter = None
        # do you sit "on" or "in" this object?
        self.db.adjective = "on"
        self.cmdset.add_default(CmdSetSit)  # <- new
```

Any _new_ Sittables will now have your `sit` Command. Your existing `armchair` will not,
since `at_object_creation` will not re-run for already existing objects. We can update it manually:

    > reload
    > update armchair

We could also update all existing sittables (all on one line):

    > py from typeclasses.sittables import Sittable ;
           [sittable.at_object_creation() for sittable in Sittable.objects.all()]

> The above shows an example of a _list comprehension_. Think of it as an efficient way to construct a new list
all in one line. You can read more about list comprehensions
[here in the Python docs](https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions).

We should now be able to use `sit` while in the room with the armchair.

    > sit
    As you sit down in armchair, life feels easier.
    > stand
    You stand up from armchair.

One issue with placing the `sit` (or `stand`) Command "on" the chair is that it will not be available when in a
room without a Sittable object:

    > sit
    Command 'sit' is not available. ...

This is practical but not so good-looking; it makes it harder for the user to know a `sit` action is at all
possible. Here is a trick for fixing this. Let's add _another_ Command to the bottom
of `mygame/commands/sittables.py`:

```python
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

Here we have a Command that is actually two - it will answer to both `sit` and `stand` since we
added `stand` to its `aliases`. In the command we look at `self.cmdname`, which is the string
_actually used_ to call this command. We use this to return different messages.

We don't need a separate CmdSet for this, instead we will add this
to the default Character cmdset. Open `mygame/commands/default_cmdsets.py`:

```python
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

To test we'll build a new location without any comfy armchairs and go there:

    > reload
    > tunnel n = kitchen
    north
    > sit
    You have nothing to sit on.
    > south
    sit
    As you sit down in armchair, life feels easier.

We now have a fully functioning `sit` action that is contained with the chair itself. When no chair is around, a
default error message is shown.

How does this work? There are two cmdsets at play, both of which have a `sit` Command. As you may remember we
set the chair's cmdset to `priority = 1`. This is where that matters. The default Character cmdset has a
priority of 0. This means that whenever we enter a room with a Sittable thing, the `sit` command
from _its_ cmdset will take _precedence_ over the Character cmdset's version. So we are actually picking
_different_ `sit` commands depending on circumstance! The user will never be the wiser.

So this handles `sit`. What about `stand`? That will work just fine:

    > stand
    You stand up from armchair.
    > north
    > stand
    You are not sitting down.

We have one remaining problem with `stand` though - what happens when you are sitting down and try to
`stand` in a room with more than one chair:

    > stand
    More than one match for 'stand' (please narrow target):
     stand-1 (armchair)
     stand-2 (sofa)
     stand-3 (barstool)

Since all the sittables have the `stand` Command on them, you'll get a multi-match error. This _works_  ... but
you could pick _any_ of those sittables to "stand up from". That's really weird and non-intuitive. With `sit` it
was okay to get a choice - Evennia can't know which chair we intended to sit on. But we know which chair we
sit on so we should only get _its_ `stand` command.

We will fix this with a `lock` and a custom `lock function`. We want a lock on the `stand` Command that only
makes it available when the caller is actually sitting on the chair the `stand` command is on.

First let's add the lock so we see what we want. Open `mygame/commands/sittables.py`:

```python
# ...

class CmdStand(Command):
     """
     Stand up.
     """
     key = "stand"
     lock = "cmd:sitsonthis()"  # < this is new

     def func(self):
         self.obj.do_stand(self.caller)
# ...
```

We define a [Lock](../Components/Locks.md) on the command. The `cmd:` is in what situation Evennia will check
the lock. The `cmd` means that it will check the lock when determining if a user has access to this command or not.
What will be checked is the `sitsonthis` _lock function_ which doesn't exist yet.

Open `mygame/server/conf/lockfuncs.py` to add it!

```python
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

Evennia knows that all functions in `mygame/server/conf/lockfuncs` should be possible to use in a lock definition.
The arguments are required and Evennia will pass all relevant objects to them:

```{sidebar} Lockfuncs

    Evennia provides a large number of default lockfuncs, such as checking permission-levels,
    if you are carrying or are inside the accessed object etc. There is no concept of 'sitting'
    in default Evennia however, so this we need to specify ourselves.

```

- `accessing_obj` is the one trying to access the lock. So us, in this case.
- `accessed_obj` is the entity we are trying to gain a particular type of access to. So the chair.
- `args` is a tuple holding any arguments passed to the lockfunc. Since we use `sitsondthis()` this will
   be empty (and if we add anything, it will be ignored).
- `kwargs` is a tuple of keyword arguments passed to the lockfuncs. This will be empty as well in our example.

If you are superuser, it's important that you `quell` yourself before trying this out. This is because the superuser
bypasses all locks - it can never get locked out, but it means it will also not see the effects of a lock like this.

    > reload
    > quell
    > stand
    You stand up from armchair

None of the other sittables' `stand` commands passed the lock and only the one we are actually sitting on did.

Adding a Command to the chair object like this is powerful and a good technique to know. It does come with some
caveats though that one needs to keep in mind.

We'll now try another way to add the `sit/stand` commands.

## Command variant 2: Command on Character

Before we start with this, delete the chairs you've created (`del armchair` etc) and then do the following
changes:

- In `mygame/typeclasses/sittables.py`, comment out the line `self.cmdset.add_default(CmdSetSit)`.
- In `mygame/commands/default_cmdsets.py`, comment out the line `self.add(sittables.CmdNoSitStand)`.

This disables the on-object command solution so we can try an alternative. Make sure to `reload` so the
changes are known to Evennia.

In this variation we will put the `sit` and `stand` commands on the `Character` instead of on the chair. This
makes some things easier, but makes the Commands themselves more complex because they will not know which
chair to sit on. We can't just do `sit` anymore. This is how it will work.

    > sit <chair>
    You sit on chair.
    > stand
    You stand up from chair.

Open `mygame/commands.sittables.py` again. We'll add a new sit-command. We name the class `CmdSit2` since
we already have `CmdSit` from the previous example. We put everything at the end of the module to
keep it separate.

```python
from evennia import Command, CmdSet
from evennia import InterruptCommand  # <- this is new

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

With this Command-variation we need to search for the sittable. A series of methods on the Command
are run in sequence:

1. `Command.at_pre_command` - this is not used by default
2. `Command.parse` - this should parse the input
3. `Command.func` - this should implement the actual Command functionality
4. `Command.at_post_func` - this is not used by default

So if we just `return` in `.parse`, `.func` will still run, which is not what we want. To immediately
abort this sequence we need to `raise InterruptCommand`.

```{sidebar} Raising exceptions

    Raising an exception allows for immediately interrupting the current program flow. Python
    automatically raises error-exceptions when detecting problems with the code. It will be
    raised up through the sequence of called code (the 'stack') until it's either `caught` with
    a `try ... except` or reaches the outermost scope where it'll be logged or displayed.

```

`InterruptCommand` is an _exception_ that the Command-system catches with the understanding that we want
to do a clean abort. In the `.parse` method we strip any whitespaces from the argument and
sure there actuall _is_ an argument. We abort immediately if there isn't.

We we get to `.func` at all, we know that we have an argument. We search for this and abort if we there was
a problem finding the target.

> We could have done `raise InterruptCommand` in `.func` as well, but `return` is a little shorter to write
> and there is no harm done if `at_post_func` runs since it's empty.

Next we call the found sittable's `do_sit` method. Note that we wrap this call like this:

```python

try:
    # code
except AttributeError:
    # stuff to do if AttributeError exception was raised
```

The reason is that `caller.search` has no idea we are looking for a Sittable. The user could have tried
`sit wall` or `sit sword`. These don't have a `do_sit` method _but we call it anyway and handle the error_.
This is a very "Pythonic" thing to do. The concept is often called "leap before you look" or "it's easier to
ask for forgiveness than for permission". If `sittable.do_sit` does not exist, Python will raise an `AttributeError`.
We catch this with `try ... except AttributeError` and convert it to a proper error message.

While it's useful to learn about `try ... except`, there is also a way to leverage Evennia to do this without
`try ... except`:

```python

    # ...

    def func(self):

        # self.search handles all error messages etc.
        sittable = self.caller.search(
                         self.args,
                         typeclass="typeclasses.sittables.Sittable")
        if not sittable:
            return
        sittable.do_sit(self.caller)
```

```{sidebar} Continuing across multiple lines

    Note how the `.search()` method's arguments are spread out over multiple
    lines. This works for all lists, tuples and other listings and is
    a good way to avoid very long and hard-to-read lines.

```

The `caller.search` method has an keyword argument `typeclass` that can take either a python-path to a
typeclass, the typeclass itself, or a list of either to widen the allowed options. In this case we know
for sure that the `sittable` we get is actually a `Sittable` class and we can call `sittable.do_sit` without
needing to worry about catching errors.

Let's do the `stand` command while we are at it. Again, since the Command is external to the chair we don't
know which object we are sitting in and have to search for it.

```python

class CmdStand2(Command):
    """
    Stand up.

    Usage:
        stand

    """
    key = "stand"

    def func(self):

        caller = self.caller
        # find the thing we are sitting on/in, by finding the object
        # in the current location that as an Attribute "sitter" set
        # to the caller
        sittable = caller.search(
                         caller,
                         candidates=caller.location.contents,
                         attribute_name="sitter",
                         typeclass="typeclasses.sittables.Sittable")
        # if this is None, the error was already reported to user
        if not sittable:
            return

        sittable.do_stand(caller)

```

This forced us to to use the full power of the `caller.search` method. If we wanted to search for something
more complex we would likely need to break out a [Django query](Beginner-Tutorial/Part1/Beginner-Tutorial-Django-queries.md) to do it. The key here is that
we know that the object we are looking for is a `Sittable` and that it must have an Attribute named `sitter`
which should be set to us, the one sitting on/in the thing. Once we have that we just call `.do_stand` on it
and let the Typeclass handle the rest.

All that is left now is to make this available to us. This type of Command should be available to us all the time
so we can put it in the default Cmdset` on the Character. Open `mygame/default_cmdsets.py`


```python
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

Now let's try it out:

    > reload
    > create/drop sofa : sittables.Sittable
    > sit sofa
    You sit down on sofa.
    > stand
    You stand up from sofa.


## Conclusions

In this lesson we accomplished quite a bit:

- We modified our `Character` class to avoid moving when sitting down.
- We made a new `Sittable` typeclass
- We tried two ways to allow a user to interact with sittables using `sit` and `stand` commands.

Eagle-eyed readers will notice that the `stand` command sitting "on" the chair (variant 1) would work just fine
together with the `sit` command sitting "on" the Character (variant 2). There is nothing stopping you from
mixing them, or even try a third solution that better fits what you have in mind.

[prev lesson](../Unimplemented.md) | [next lesson](../Unimplemented.md)
