# First Steps Coding


This section gives a brief step-by-step introduction on how to set up Evennia for the first time so
you can modify and overload the defaults easily. You should only need to do these steps once. It
also walks through you making your first few tweaks.

Before continuing, make sure you have Evennia installed and running by following the [Getting
Started](./Getting-Started.md) instructions. You should have initialized a new game folder with the
`evennia --init foldername` command.  We will in the following assume this folder is called
"mygame".

It might be a good idea to eye through the brief [Coding Introduction](./Coding-Introduction.md) too
(especially the recommendations in the section about the evennia "flat" API and about using `evennia
shell` will help you here and in the future).

To follow this tutorial you also need to know the basics of operating your computer's
terminal/command line. You also need to have a text editor to edit and create source text files.
There are plenty of online tutorials on how to use the terminal and plenty of good free text
editors. We will assume these things are already familiar to you henceforth.


## Your First Changes

Below are some first things to try with your new custom modules. You can test these to get a feel
for the system. See also [Tutorials](./Tutorials.md) for more step-by-step help and special cases.

### Tweak Default Character

We will add some simple rpg attributes to our default Character. In the next section we will follow
up with a new command to view those attributes.

1. Edit `mygame/typeclasses/characters.py` and modify the `Character` class.  The
`at_object_creation` method also exists on the `DefaultCharacter` parent and will overload it. The
`get_abilities` method is unique to our version of `Character`.

    ```python
    class Character(DefaultCharacter):
        # [...]
        def at_object_creation(self):
            """
            Called only at initial creation. This is a rather silly
            example since ability scores should vary from Character to
            Character and is usually set during some character
            generation step instead.
            """
            #set persistent attributes
            self.db.strength = 5
            self.db.agility = 4
            self.db.magic = 2

        def get_abilities(self):
            """
            Simple access method to return ability
            scores as a tuple (str,agi,mag)
            """
            return self.db.strength, self.db.agility, self.db.magic
    ```

1. [Reload](./Start-Stop-Reload.md) the server (you will still be connected to the game after doing
this). Note that if you examine *yourself* you will *not* see any new Attributes appear yet. Read
the next section to understand why.

#### Updating Yourself

It's important to note that the new [Attributes](./Attributes.md) we added above will only be stored on
*newly* created characters. The reason for this is simple: The `at_object_creation` method, where we
added those Attributes, is per definition only called when the object is *first created*, then never
again. This is usually a good thing since those Attributes may change over time - calling that hook
would reset them back to start values. But it also means that your existing character doesn't have
them yet. You can see this by calling the `get_abilities` hook on yourself at this point:

```
# (you have to be superuser to use @py)
@py self.get_abilities()
<<< (None, None, None)
```

This is easily remedied.

```
@update self
```

This will (only) re-run `at_object_creation` on yourself. You should henceforth be able to get the
abilities successfully:

```
@py self.get_abilities()
<<< (5, 4, 2)
```

This is something to keep in mind if you start building your world before your code is stable -
startup-hooks will not (and should not) automatically run on *existing* objects - you have to update
your existing objects manually. Luckily this is a one-time thing and pretty simple to do. If the
typeclass you want to update is in `typeclasses.myclass.MyClass`, you can do the following (e.g.
from `evennia shell`):

```python
from typeclasses.myclass import MyClass
# loop over all MyClass instances in the database
# and call .swap_typeclass on them
for obj in MyClass.objects.all():
    obj.swap_typeclass(MyClass, run_start_hooks="at_object_creation")
```

Using `swap_typeclass` to the same typeclass we already have will re-run the creation hooks (this is
what the `@update` command does under the hood). From in-game you can do the same with `@py`:

```
@py typeclasses.myclass import MyClass;[obj.swap_typeclass(MyClass) for obj in
MyClass.objects.all()]
```

See the [Object Typeclass tutorial](./Adding-Object-Typeclass-Tutorial.md) for more help and the
[Typeclasses](./Typeclasses.md) and [Attributes](./Attributes.md) page for detailed documentation about
Typeclasses and Attributes.

#### Troubleshooting: Updating Yourself

One may experience errors for a number of reasons. Common beginner errors are spelling mistakes,
wrong indentations or code omissions leading to a `SyntaxError`. Let's say you leave out a colon
from the end of a class function like so: ```def at_object_creation(self)```. The client will reload
without issue. *However*, if you look at the terminal/console (i.e. not in-game), you will see
Evennia complaining (this is called a *traceback*):

```
Traceback (most recent call last):
File "C:\mygame\typeclasses\characters.py", line 33
     def at_object_creation(self)
                                 ^
SyntaxError: invalid syntax
```

Evennia will still be restarting and following the tutorial, doing `@py self.get_abilities()` will
return the right response `(None, None, None)`. But when attempting to `@typeclass/force self` you
will get this response:

```python
    AttributeError: 'DefaultObject' object has no attribute 'get_abilities'
```

The full error will show in the terminal/console but this is confusing since you did add
`get_abilities` before. Note however what the error says - you (`self`) should be a `Character` but
the error talks about `DefaultObject`. What has happened is that due to your unhandled `SyntaxError`
earlier, Evennia could not load the `character.py` module at all (it's not valid Python). Rather
than crashing, Evennia handles this by temporarily falling back to a safe default -  `DefaultObject`
- in order to keep your MUD running. Fix the original `SyntaxError` and reload the server. Evennia
will then be able to use your modified `Character` class again and things should work.

> Note: Learning how to interpret an error traceback is a critical skill for anyone learning Python.
Full tracebacks will appear in the terminal/Console you started Evennia from. The traceback text can
sometimes be quite long, but you are usually just looking for the last few lines: The description of
the error and the filename + line number for where the error occurred. In the example above, we see
it's a `SyntaxError` happening at `line 33` of `mygame\typeclasses\characters.py`. In this case it
even points out *where* on the line it encountered the error (the missing colon). Learn to read
tracebacks and you'll be able to resolve the vast majority of common errors easily.

### Add a New Default Command

The `@py` command used above is only available to privileged users. We want any player to be able to
see their stats.  Let's add a new [command](./Commands.md) to list the abilities we added in the previous
section.

1. Open `mygame/commands/command.py`. You could in principle put your command anywhere but this
module has all the imports already set up along with some useful documentation. Make a new class at
the bottom of this file:

    ```python
        class CmdAbilities(BaseCommand):
            """
            List abilities

            Usage:
              abilities

            Displays a list of your current ability values.
            """
            key = "abilities"
            aliases = ["abi"]
            lock = "cmd:all()"
            help_category = "General"

            def func(self):
                """implements the actual functionality"""

                 str, agi, mag = self.caller.get_abilities()
                 string = "STR: %s, AGI: %s, MAG: %s" % (str, agi, mag)
                 self.caller.msg(string)
    ```

1. Next you edit `mygame/commands/default_cmdsets.py` and add a new import to it near the top:

    ```python
        from commands.command import CmdAbilities
    ```

1. In the `CharacterCmdSet` class, add the following near the bottom (it says where):

    ```python
        self.add(CmdAbilities())
    ```

1. [Reload](./Start-Stop-Reload.md) the server (noone will be disconnected by doing this).

You (and anyone else) should now be able to use `abilities` (or its alias `abi`) as part of your
normal commands in-game:

```
abilities
STR: 5, AGI: 4, MAG: 2
```

See the [Adding a Command tutorial](./Adding-Command-Tutorial.md) for more examples and the
[Commands](./Commands.md) section for detailed documentation about the Command system.

### Make a New Type of Object

Let's test to make a new type of object. This example is an "wise stone" object that returns some
random comment when you look at it, like this:

    > look stone

    A very wise stone

    This is a very wise old stone.
    It grumbles and says: 'The world is like a rock of chocolate.'

1. Create a new module in `mygame/typeclasses/`. Name it `wiseobject.py` for this example.
1. In the module import the base `Object` (`typeclasses.objects.Object`). This is empty by default,
meaning it is just a proxy for the default `evennia.DefaultObject`.
1. Make a new class in your module inheriting from `Object`. Overload hooks on it to add new
functionality. Here is an example of how the file could look:

    ```python
    from random import choice
    from typeclasses.objects import Object

    class WiseObject(Object):
        """
        An object speaking when someone looks at it. We
        assume it looks like a stone in this example.
        """
        def at_object_creation(self):
            """Called when object is first created"""
            self.db.wise_texts = \
                   ["Stones have feelings too.",
                    "To live like a stone is to not have lived at all.",
                    "The world is like a rock of chocolate."]

        def return_appearance(self, looker):
            """
            Called by the look command. We want to return
            a wisdom when we get looked at.
            """
            # first get the base string from the
            # parent's return_appearance.
            string = super().return_appearance(looker)
            wisewords = "\n\nIt grumbles and says: '%s'"
            wisewords = wisewords % choice(self.db.wise_texts)
            return string + wisewords
    ```

1. Check your code for bugs. Tracebacks will appear on your command line or log. If you have a grave
Syntax Error in your code, the source file itself will fail to load which can cause issues with the
entire cmdset. If so, fix your bug and [reload the server from the command line](./Start-Stop-Reload.md)
(noone will be disconnected by doing this).
1. Use `@create/drop stone:wiseobject.WiseObject` to create a talkative stone. If the `@create`
command spits out a warning or cannot find the typeclass (it will tell you which paths it searched),
re-check your code for bugs and that you gave the correct path. The `@create` command starts looking
for Typeclasses in `mygame/typeclasses/`.
1. Use `look stone` to test. You will see the default description ("You see nothing special")
followed by a random message of stony wisdom. Use `@desc stone = This is a wise old stone.` to make
it look nicer. See the [Builder Docs](./Builder-Docs.md) for more information.

Note that `at_object_creation` is only called once, when the stone is first created. If you make
changes to this method later, already existing stones will not see those changes. As with the
`Character` example above you can use `@typeclass/force` to tell the stone to re-run its
initialization.

The `at_object_creation` is a special case though. Changing most other aspects of the typeclass does
*not* require manual updating like this - you just need to `@reload` to have all changes applied
automatically to all existing objects.

## Where to Go From Here?

There are more [Tutorials](./Tutorials.md), including one for building a [whole little MUSH-like
game](./Tutorial-for-basic-MUSH-like-game.md) - that is instructive also if you have no interest in
MUSHes per se. A good idea is to also get onto the [IRC
chat](http://webchat.freenode.net/?channels=evennia) and the [mailing
list](https://groups.google.com/forum/#!forum/evennia) to get in touch with the community and other
developers.
