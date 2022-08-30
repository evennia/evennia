# Introduction to Python classes and objects

We have now learned how to run some simple Python code from inside (and outside) your game server.
We have also taken a look at what our game dir looks and what is where. Now we'll start to use it.

## Importing things

No one writes something as big as an online game in one single huge file. Instead one breaks up the
code into separate files (modules). Each module is dedicated to different purposes. Not only does
it make things cleaner, organized and easier to understand. It also makes it easier to re-use code -
you just import the resources you need and know you only get just what you requested. This makes
it much easier to find errors and to know what code is good and which has issues.

> Evennia itself uses your code in the same way - you just tell it where a particular type of code is,
and it will import and use it (often instead of its defaults).

We have already successfully imported things, for example:

    > py import world.test ; world.test.hello_world(me)
    Hello World!

In this example, on your hard drive, the files looks like this:

```
mygame/
    world/
        test.py    <- inside this file is a function hello_world

```
If you followed earlier tutorial lessons, the `mygame/world/test.py` file should look like this (if
not, make it so):

```python
def hello_world(who):
    who.msg("Hello World!")
```

```{eval-rst}

.. sidebar:: Remember:

    - Indentation matters in Python
    - So does capitalization
    - Use 4 `spaces` to indent, not tabs
    - Empty lines are fine
    - Anything on a line after a `#` is a `comment`, ignored by Python
```

The _python_path_ describes the relation between Python resources, both between and inside
Python _modules_ (that is, files ending with .py). A python-path separates each part of the
path `.` and always skips the `.py` file endings. Also, Evennia already knows to start looking
for python resources inside `mygame/` so this should never be specified. Hence

    import world.test

The `import` Python instruction loads `world.test` so you have it available. You can now go "into"
this module to get to the function you want:

    world.test.hello_world(me)

Using `import` like this means that you have to specify the full `world.test` every time you want
to get to your function. Here's a more powerful form of import:

    from world.test import hello_world

The `from ... import ...` is very, very common as long as you want to get something with a longer
python path. It imports `hello_world` directly, so you can use it right away!

     > py from world.test import hello_world ; hello_world(me)
     Hello World!

Let's say your `test.py` module had a bunch of interesting functions. You could then import them
all one by one:

    from world.test import hello_world, my_func, awesome_func

If there were _a lot_ of functions, you could instead just import `test` and get the function
from there when you need (without having to give the full `world.test` every time):

    > from world import test ; test.hello_world(me
    Hello World!

You can also _rename_ stuff you import. Say for example that the module you import to already
has a function `hello_world` but we also want to use the one from `world/test.py`:

    from world.test import hello_world as test_hello_world

The form `from ... import ... as ...` renames the import.

    > from world.test import hello_world as hw ; hw(me)
    Hello World!

> Avoid renaming unless it's to avoid a name-collistion like above - you want to make things as
> easy to read as possible, and renaming adds another layer of potential confusion.

In [the basic intro to Python](./Beginner-Tutorial-Python-basic-introduction.md) we learned how to open the in-game
multi-line interpreter.

    > py
    Evennia Interactive Python mode
    Python 3.7.1 (default, Oct 22 2018, 11:21:55)
    [GCC 8.2.0] on Linux
    [py mode - quit() to exit]

You now only need to import once to use the imported function over and over.

    > from world.test import hello_world
    > hello_world()
    Hello World!
    > hello_world()
    Hello World!
    > hello_world()
    Hello World!
    > quit()
    Closing the Python console.

The same goes when writing code in a module - in most Python modules you will see a bunch of
imports at the top, resources that are then used by all code in that module.

## On classes and objects

Now that we know about imports, let look at a real Evennia module and try to understand it.

Open `mygame/typeclasses/objects.py` in your text editor of choice.

```python
"""
module docstring
"""
from evennia import DefaultObject

class Object(DefaultObject):
    """
    class docstring
    """
    pass
```

```{sidebar} Docstrings vs Comments

    A docstring is not the same as a comment (created by `#`). A
    docstring is not ignored by Python but is an integral part of the thing
    it is documenting (the module and the class in this case).
```
The real file is much longer but we can ignore the multi-line strings (`""" ... """`). These serve
as documentation-strings, or _docstrings_ for the module (at the top) and the `class` below.

Below the module doc string we have the import. In this case we are importing a resource
from the core `evennia` library itself. We will dive into this later, for now we just treat this
as a black box.

Next we have a `class` named `Object`, which _inherits_ from `DefaultObject`. This class doesn't
actually do anything on its own, its only code (except the docstring) is `pass` which means,
well, to pass and don't do anything.

We will get back to this module in the [next lesson](./Beginner-Tutorial-Learning-Typeclasses.md). First we need to do a
little detour to understand what a 'class', an 'object' or 'instance' is. These are fundamental
things to understand before you can use Evennia efficiently.
```{sidebar} OOP

    Classes, objects, instances and inheritance are fundamental to Python. This and some
    other concepts are often clumped together under the term Object-Oriented-Programming (OOP).
```

### Classes and instances

A 'class' can be seen as a 'template' for a 'type' of object. The class describes the basic functionality
of everyone of that class. For example, we could have a class `Monster` which has resources for moving itself
from room to room.

Open a new file `mygame/typeclasses/monsters.py`. Add the following simple class:

```python

class Monster:

    key = "Monster"

    def move_around(self):
        print(f"{self.key} is moving!")

```

Above we have defined a `Monster` class with one variable `key` (that is, the name) and one
_method_ on it. A method is like a function except it sits "on" the class. It also always has
at least one argument (almost always written as `self` although you could in principle use
another name), which is a reference back to itself. So when we print `self.key` we are referring
back to the `key` on the class.

```{eval-rst}
.. sidebar:: Terms

    - A `class` is a code template describing a 'type' of something
    - An `object` is an `instance` of a `class`. Like using a mold to cast tin soldiers, one class can be `instantiated` into any number of object-instances.

```
A class is just a template. Before it can be used, we must create an _instance_ of the class. If
`Monster` is a class, then an instance is Fluffy, the individual red dragon. You instantiate
by _calling_ the class, much like you would a function:

    fluffy = Monster()

Let's try it in-game (we use multi-line mode, it's easier)

    > py
    > from typeclasses.monsters import Monster
    > fluffy = Monster()
    > fluffy.move_around()
    Monster is moving!

We created an _instance_ of `Monster`, which we stored in the variable `fluffy`. We then
called the `move_around` method on fluffy to get the printout.

> Note how we _didn't_ call the method as `fluffy.move_around(self)`. While the `self` has to be
> there when defining the method, we _never_ add it explicitly when we call the method (Python
> will add the correct `self` for us automatically behind the scenes).

Let's create the sibling of Fluffy, Cuddly:

    > cuddly = Monster()
    > cuddly.move_around()
    Monster is moving!

We now have two dragons and they'll hang around until with call `quit()` to exit this Python
instance. We can have them move as many times as we want. But no matter how many dragons we
create, they will all show the same printout since `key` is always fixed as "Monster".

Let's make the class a little more flexible:

```python

class Monster:

    def __init__(self, key):
        self.key = key

    def move_around(self):
        print(f"{self.key} is moving!")

```

The `__init__` is a special method that Python recognizes. If given, this handles extra arguments
when you instantiate a new Monster. We have it add an argument `key` that we store on `self`.

Now, for Evennia to see this code change, we need to reload the server. You can either do it this
way:

    > quit()
    Python Console is closing.
    > reload

Or you can use a separate terminal and restart from outside the game:
```{sidebar} On reloading

    Reloading with the python mode gets a little annoying since you need to redo everything
    after every reload. Just keep in mind that during regular development you will not be
    working this way. The in-game python mode is practical for quick fixes and experiments like
    this, but actual code is normally written externally, in python modules.
```

    $ evennia reload   (or restart)

Either way you'll need to go into `py` again:

    > py
    > from typeclasses.monsters import Monster
    fluffy = Monster("Fluffy")
    fluffy.move_around()
    Fluffy is moving!

Now we passed `"Fluffy"` as an argument to the class. This went into `__init__` and set `self.key`, which we
later used to print with the right name! Again, note that we didn't include `self` when calling.

### What's so good about objects?

So far all we've seen a class do is to behave our first `hello_world` function but more complex. We
could just have made a function:

```python
     def monster_move_around(key):
        print(f"{key} is moving!")
```

The difference between the function and an instance of a class (the object), is that the
object retains _state_. Once you called the function it forgets everything about what you called
it with last time. The object, on the other hand, remembers changes:

    > fluffy.key = "Cuddly"
    > fluffy.move_around()
    Cuddly is moving!

The `fluffy` object's `key` was changed to "Cuddly" for as long as it's around. This makes objects
extremely useful for representing and remembering collections of data - some of which can be other
objects in turn:

- A player character with all its stats
- A monster with HP
- A chest with a number of gold coins in it
- A room with other objects inside it
- The current policy positions of a political party
- A rule with methods for resolving challenges or roll dice
- A multi-dimenstional data-point for a complex economic simulation
- And so much more!

### Classes can have children

Classes can _inherit_ from each other. A "child" class will inherit everything from its "parent" class. But if
the child adds something with the same name as its parent, it will _override_ whatever it got from its parent.

Let's expand `mygame/typeclasses/monsters.py` with another class:

```python

class Monster:
    """
    This is a base class for Monster.
    """

    def __init__(self, key):
        self.key = key

    def move_around(self):
        print(f"{self.key} is moving!")


class Dragon(Monster):
    """
    This is a dragon-specific monster.
    """

    def move_around(self):
        print(f"{self.key} flies through the air high above!")

    def firebreath(self):
        """
        Let our dragon breathe fire.
        """
        print(f"{self.key} breathes fire!")

```

We added some docstrings for clarity. It's always a good idea to add doc strings; you can do so also for methods,
as exemplified for the new `firebreath` method.

We created the new class `Dragon` but we also specified that `Monster` is the _parent_ of `Dragon` but adding
the parent in parenthesis. `class Classname(Parent)` is the way to do this.

```{sidebar} Multi-inheritance

    It's possible to add more comma-separated parents to a class. You should usually avoid
    this until you `really` know what you are doing. A single parent will be enough for almost
    every case you'll need.

```

Let's try out our new class. First `reload` the server and the do

    > py
    > from typeclasses.monsters import Dragon
    > smaug = Dragon("Smaug")
    > smaug.move_around()
    Smaug flies through the air high above!
    > smaug.firebreath()
    Smaug breathes fire!

Because we didn't implement `__init__` in `Dragon`, we got the one from `Monster` instead. But since we
implemented our own `move_around` in `Dragon`, it _overrides_ the one in `Monster`. And `firebreath` is only
available for `Dragon`s of course. Having that on `Monster` would not have made much sense, since not every monster
can breathe fire.

One can also force a class to use resources from the parent even if you are overriding some of it. This is done
with the `super()` method. Modify your `Dragon` class as follows:


```python
# ...

class Dragon(Monster):

    def move_around(self):
        super().move_around()
        print("The world trembles.")

    # ...
```
> Keep `Monster` and the `firebreath` method, `# ...` indicates the rest of the code is untouched.
>

The `super().move_around()` line means that we are calling `move_around()` on the parent of the class. So in this
case, we will call `Monster.move_around` first, before doing our own thing.

Now `reload` the server and then:

    > py
    > from typeclasses.monsters import Dragon
    > smaug = Dragon("Smaug")
    > smaug.move_around()
    Smaug is moving!
    The world trembles.

We can see that `Monster.move_around()` is calls first and prints "Smaug is moving!", followed by the extra bit
about the trembling world we added in the `Dragon` class.

Inheritance is very powerful because it allows you to organize and re-use code while only adding the special things
you want to change. Evennia uses this concept a lot.

## Summary

We have created our first dragons from classes. We have learned a little about how you _instantiate_ a class
into an _object_. We have seen some examples of _inheritance_ and we tested to _override_ a method in the parent
with one in the child class. We also used `super()` to good effect.

We have used pretty much raw Python so far. In the coming lessons we'll start to look at the extra bits that Evennia
provides. But first we need to learn just where to find everything.

