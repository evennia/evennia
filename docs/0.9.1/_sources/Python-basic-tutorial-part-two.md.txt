# Python basic tutorial part two

[In the first part](./Python-basic-introduction) of this Python-for-Evennia basic tutorial we learned how to run some simple Python code from inside the game. We also made our first new *module* containing a *function* that we called. Now we're going to start exploring the very important subject of *objects*.

**Contents:**
- [On the subject of objects](./Python-basic-tutorial-part-two#on-the-subject-of-objects)
- [Exploring the Evennia library](./Python-basic-tutorial-part-two#exploring-the-evennia-library)
- [Tweaking our Character class](./Python-basic-tutorial-part-two#tweaking-our-character-class)
- [The Evennia shell](./Python-basic-tutorial-part-two#the-evennia-shell)
- [Where to go from here](./Python-basic-tutorial-part-two#where-to-go-from-here)

### On the subject of objects

In the first part of the tutorial we did things like

    > py me.msg("Hello World!")

To learn about functions and imports we also passed that `me` on to a function `hello_world` in another module.

Let's learn some more about this `me` thing we are passing around all over the place. In the following we assume that we named our superuser Character "Christine".

    > py me
    Christine
    > py me.key
    Christine

These returns look the same at first glance, but not if we examine them more closely:

    > py type(me)
    <class 'typeclasses.characters.Character'>
    > py type(me.key)
    <type str>

> Note: In some MU clients, such as Mudlet and MUSHclient simply returning `type(me)`, you may not see the proper return from the above commands. This is likely due to the HTML-like tags `<...>`, being swallowed by the client.

The `type` function is, like `print`, another in-built function in Python. It
tells us that we (`me`) are of the *class* `typeclasses.characters.Character`.
Meanwhile `me.key` is a *property* on us, a string. It holds the name of this
object.

> When you do `py me`, the `me` is defined in such a way that it will use its `.key` property to represent itself. That is why the result is the same as when doing `py me.key`. Also, remember that as noted in the first part of the tutorial, the `me` is *not* a reserved Python word; it was just defined by the Evennia developers as a convenient short-hand when creating the `py` command. So don't expect `me` to be available elsewhere.

A *class* is like a "factory" or blueprint. From a class you then create individual *instances*. So if class is`Dog`, an instance of `Dog` might be `fido`. Our in-game persona is of a class `Character`. The superuser `christine` is an *instance* of the `Character` class (an instance is also often referred to as an *object*). This is an important concept in *object oriented programming*. You are wise to [familiarize yourself with it](https://en.wikipedia.org/wiki/Class-based_programming) a little.

> In other terms:
> * class: A description of a thing, all the methods (code) and data (information)
> * object: A thing, defined as an *instance* of a class.
>
> So in "Fido is a Dog", "Fido" is an object--a unique thing--and "Dog" is a class. Coders would also say, "Fido is an instance of Dog". There can be other dogs too, such as Butch and Fifi. They, too, would be instances of Dog.
>
> As another example: "Christine is a Character", or "Christine is an instance of typeclasses.characters.Character". To start, all characters will be instances of typeclass.characters.Character.
>
> You'll be writing your own class soon! The important thing to know here is how classes and objects relate.

The string `'typeclasses.characters.Character'` we got from the `type()` function is not arbitrary. You'll recognize this from when we _imported_ `world.test` in part one. This is a _path_ exactly describing where to find the python code describing this class. Python treats source code files on your hard drive (known as *modules*) as well as folders (known as *packages*) as objects that you access with the `.` operator. It starts looking at a place that Evennia has set up for you - namely the root of your own game directory.

Open and look at your game folder (named `mygame` if you exactly followed the Getting Started instructions) in a file editor or in a new terminal/console. Locate the file `mygame/typeclasses/characters.py`

```
mygame/
    typeclasses
        characters.py
```

This represents the first part of the python path - `typeclasses.characters` (the `.py` file ending is never included in the python path). The last bit, `.Character` is the actual class name inside the `characters.py` module. Open that file in a text editor and you will see something like this:

```python
"""
(Doc string for module)
"""

from evennia import DefaultCharacter

class Character(DefaultCharacter):
    """
    (Doc string for class)
    """
    pass

```

There is `Character`, the last part of the path. Note how empty this file is. At first glance one would think a Character had no functionality at all. But from what we have used already we know it has at least the `key` property and the method `msg`! Where is the code? The answer is that this 'emptiness' is an illusion caused by something called *inheritance*. Read on.

Firstly, in the same way as the little `hello.py` we did in the first part of the tutorial, this is an example of full, multi-line Python code. Those triple-quoted strings are used for strings that have line breaks in them. When they appear on their own like this, at the top of a python module, class or similar they are called *doc strings*. Doc strings are read by Python and is used for producing online help about the function/method/class/module. By contrast, a line starting with `#` is a *comment*. It is ignored completely by Python and is only useful to help guide a human to understand the code.

The line

```python
    class Character(DefaultCharacter):
```

means that the class `Character` is a *child* of the class `DefaultCharacter`. This is called *inheritance* and is another fundamental concept. The answer to the question "where is the code?" is that the code is *inherited* from its parent, `DefaultCharacter`. And that in turn may inherit code from *its* parent(s) and so on. Since our child, `Character` is empty, its functionality is *exactly identical* to that of its parent. The moment we add new things to Character, these will take precedence. And if we add something that already existed in the parent, our child-version will *override* the version in the parent. This is very practical: It means that we can let the parent do the heavy lifting and only tweak the things we want to change. It also means that we could easily have many different Character classes, all inheriting from `DefaultCharacter` but changing different things. And those can in turn also have children ...

Let's go on an expedition up the inheritance tree.

### Exploring the Evennia library

Let's figure out how to tweak `Character`. Right now we don't know much about `DefaultCharacter` though. Without knowing that we won't know what to override. At the top of the file you find

```python
from evennia import DefaultCharacter
```

This is an `import` statement again, but on a different form to what we've seen before. `from ... import ...` is very commonly used and allows you to precisely dip into a module to extract just the component you need to use. In this case we head into the `evennia` package to get `DefaultCharacter`.

Where is `evennia`? To find it you need to go to the `evennia` folder (repository) you originally cloned from us. If you open it, this is how it looks:

```
evennia/
   __init__.py
   bin/
   CHANGELOG.txt etc.
   ...
   evennia/
   ...
```
There are lots of things in there. There are some docs but most of those have to do with the distribution of Evennia and does not concern us right now. The `evennia` subfolder is what we are looking for. *This* is what you are accessing when you do `from evennia import ...`. It's set up by Evennia as a good place to find modules when the server starts. The exact layout of the Evennia library [is covered by our directory overview](./Directory-Overview#evennia-library-layout). You can also explore it [online on github](https://github.com/evennia/evennia/tree/master/evennia).

The structure of the library directly reflects how you import from it.

- To, for example, import [the text justify function](https://github.com/evennia/evennia/blob/master/evennia/utils/utils.py#L201) from `evennia/utils/utils.py` you would do `from evennia.utils.utils import justify`. In your code you could then just call `justify(...)` to access its functionality.
- You could also do `from evennia.utils import utils`. In code you would then have to write `utils.justify(...)`. This is practical if want a lot of stuff from that `utils.py` module and don't want to import each component separately.
- You could also do `import evennia`. You would then have to enter the full `evennia.utils.utils.justify(...)` every time you use it. Using `from` to only import the things you need is usually easier and more readable.
- See [this overview](http://effbot.org/zone/import-confusion.htm) about the different ways to import in Python.

Now, remember that our `characters.py` module did `from evennia import DefaultCharacter`. But if we look at the contents of the `evennia` folder, there is no `DefaultCharacter` anywhere! This is because Evennia gives a large number of optional "shortcuts", known as [the "flat" API](./Evennia-API). The intention is to make it easier to remember where to find stuff. The flat API is defined in that weirdly named `__init__.py` file. This file just basically imports useful things from all over Evennia so you can more easily find them in one place.

We could [just look at the documenation](github:evennia#typeclasses) to find out where we can look at our `DefaultCharacter` parent. But for practice, let's figure it out. Here is where `DefaultCharacter` [is imported from](https://github.com/evennia/evennia/blob/master/evennia/__init__.py#L188) inside `__init__.py`:

```python
from .objects.objects import DefaultCharacter
```

The period at the start means that it imports beginning from the same location this module sits(i.e. the `evennia` folder). The full python-path accessible from the outside is thus `evennia.objects.objects.DefaultCharacter`. So to import this into our game it'd be perfectly valid to do

```python
from evennia.objects.objects import DefaultCharacter
```

Using

```python
from evennia import DefaultCharacter
```

is the same thing, just a little easier to remember.

> To access the shortcuts of the flat API you *must* use `from evennia import
> ...`. Using something like `import evennia.DefaultCharacter` will not work.
> See [more about the Flat API here](./Evennia-API).


### Tweaking our Character class

In the previous section we traced the parent of our `Character` class to be
`DefaultCharacter` in
[evennia/objects/objects.py](https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py).
Open that file and locate the `DefaultCharacter` class. It's quite a bit down
in this module so you might want to search using your editor's (or browser's)
search function. Once you find it, you'll find that the class starts like this:

```python

class DefaultCharacter(DefaultObject):
    """
    This implements an Object puppeted by a Session - that is, a character
    avatar controlled by an account.
    """

    def basetype_setup(self):
        """
        Setup character-specific security.
        You should normally not need to overload this, but if you do,
        make sure to reproduce at least the two last commands in this
        method (unless you want to fundamentally change how a
        Character object works).
        """
        super().basetype_setup()
        self.locks.add(";".join(["get:false()",     # noone can pick up the character
                                 "call:false()"]))  # no commands can be called on character from outside
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, permanent=True)

    def at_after_move(self, source_location, **kwargs):
        """
        We make sure to look around after a move.
        """
        if self.location.access(self, "view"):
            self.msg(self.at_look(self.location))

    def at_pre_puppet(self, account, session=None, **kwargs):
        """
        Return the character from storage in None location in `at_post_unpuppet`.
        """

    # ...

```

... And so on (you can see the full [class online here](https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py#L1915)). Here we have functional code! These methods may not be directly visible in `Character` back in our game dir, but they are still available since `Character` is a child of `DefaultCharacter` above. Here is a brief summary of the methods we find in `DefaultCharacter` (follow in the code to see if you can see roughly where things happen)::

- `basetype_setup` is called by Evennia only once, when a Character is first created. In the `DefaultCharacter` class it sets some particular [Locks](./Locks) so that people can't pick up and puppet Characters just like that. It also adds the [Character Cmdset](./Command-Sets) so that Characters always can accept command-input (this should usually not be modified - the normal hook to override is `at_object_creation`, which is called after `basetype_setup` (it's in the parent)).
- `at_after_move` makes it so that every time the Character moves, the `look` command is automatically fired (this would not make sense for just any regular Object).
- `at_pre_puppet` is called when an Account begins to puppet this Character. When not puppeted, the Character is hidden away to a `None` location. This brings it back to the location it was in before. Without this, "headless" Characters would remain in the game world just standing around.
- `at_post_puppet` is called when puppeting is complete. It echoes a message to the room that his Character has now connected.
- `at_post_unpuppet` is called once stopping puppeting of the Character. This hides away the Character to a `None` location again.
- There are also some utility properties which makes it easier to get some time stamps from the Character.

Reading the class we notice another thing:

```python
class DefaultCharacter(DefaultObject):
    # ...
```

This means that `DefaultCharacter` is in *itself* a child of something called `DefaultObject`! Let's see what this parent class provides. It's in the same module as `DefaultCharacter`, you just need to [scroll up near the top](https://github.com/evennia/evennia/blob/master/evennia/objects/objects.py#L182):

```python
class DefaultObject(with_metaclass(TypeclassBase, ObjectDB)):
   # ...
```

This is a really big class where the bulk of code defining an in-game object resides. It consists of a large number of methods, all of which thus also becomes available on the `DefaultCharacter` class below *and* by extension in your `Character` class over in your game dir. In this class you can for example find the `msg` method we have been using before.

> You should probably not expect to understand all details yet, but as an exercise, find and read the doc string of `msg`.

> As seen, `DefaultObject` actually has multiple parents. In one of those the basic `key` property is defined, but we won't travel further up the inheritance tree in this tutorial. If you are interested to see them, you can find `TypeclassBase` in [evennia/typeclasses/models.py](https://github.com/evennia/evennia/blob/master/evennia/typeclasses/models.py#L93) and `ObjectDB` in [evennia/objects/models.py](https://github.com/evennia/evennia/blob/master/evennia/objects/models.py#L121). We will also not go into the details of [Multiple Inheritance](https://docs.python.org/2/tutorial/classes.html#multiple-inheritance) or [Metaclasses](http://www.onlamp.com/pub/a/python/2003/04/17/metaclasses.html) here. The general rule is that if you realize that you need these features, you already know enough to use them.

Remember the `at_pre_puppet` method we looked at in `DefaultCharacter`? If you look at the `at_pre_puppet` hook as defined in `DefaultObject` you'll find it to be completely empty (just a `pass`). So if you puppet a regular object it won't be hiding/retrieving the object when you unpuppet it. The `DefaultCharacter` class *overrides* its parent's functionality with a version of its own. And since it's `DefaultCharacter` that our `Character` class inherits back in our game dir, it's *that* version of `at_pre_puppet` we'll get. Anything not explicitly overridden will be passed down as-is.

While it's useful to read the code, we should never actually modify anything inside the `evennia` folder. Only time you would want that is if you are planning to release a bug fix or new feature for Evennia itself. Instead you *override* the default functionality inside your game dir.

So to conclude our little foray into classes, objects and inheritance, locate the simple little `at_before_say` method in the `DefaultObject` class:

```python
    def at_before_say(self, message, **kwargs):
        """
        (doc string here)
        """
        return message
```

If you read the doc string you'll find that this can be used to modify the output of `say` before it goes out. You can think of it like this: Evennia knows the name of this method, and when someone speaks, Evennia will make sure to redirect the outgoing message through this method. It makes it ripe for us to replace with a version of our own.

> In the Evennia documentation you may sometimes see the term *hook* used for a method explicitly meant to be overridden like this.

As you can see, the first argument to `at_before_say` is `self`. In Python, the first argument of a method is *always a back-reference to the object instance on which the method is defined*. By convention this argument is always called `self` but it could in principle be named anything. The `self` is very useful. If you wanted to, say, send a message to the same object from inside `at_before_say`, you would do `self.msg(...)`.

What can trip up newcomers is that you *don't* include `self` when you *call* the method. Try:

    > @py me.at_before_say("Hello World!")
    Hello World!

Note that we don't send `self` but only the `message` argument. Python will automatically add `self` for us. In this case, `self` will become equal to the Character instance `me`.

By default the `at_before_say` method doesn't do anything. It just takes the `message` input and `return`s it just the way it was (the `return` is another reserved Python word).

> We won't go into `**kwargs` here, but it (and its sibling `*args`) is also important to understand, extra reading is [here for `**kwargs`](https://stackoverflow.com/questions/1769403/understanding-kwargs-in-python).

Now, open your game folder and edit `mygame/typeclasses/characters.py`. Locate your `Character` class and modify it as such:

```python
class Character(DefaultCharacter):
    """
    (docstring here)
    """
    def at_before_say(self, message, **kwargs):
        "Called before say, allows for tweaking message"
        return f"{message} ..."
```

So we add our own version of `at_before_say`, duplicating the `def` line from the parent but putting new code in it. All we do in this tutorial is to add an ellipsis (`...`) to the message as it passes through the method.

Note that `f` in front of the string, it means we turned the string into a 'formatted string'. We can now easily inject stuff directly into the string by wrapping them in curly brackets `{ }`. In this example, we put the incoming `message` into the string, followed by an ellipsis. This is only one way to format a string. Python has very powerful [string formatting](https://docs.python.org/2/library/string.html#format-specification-mini-language) and you are wise to learn it well, considering your game will be mainly text-based.

> You could also copy & paste the relevant method from `DefaultObject` here to get the full doc string. For more complex methods, or if you only want to change some small part of the default behavior, copy & pasting will eliminate the need to constantly look up the original method and keep you sane.

In-game, now try

    > @reload
    > say Hello
    You say, "Hello ..."

An ellipsis `...` is added to what you said! This is a silly example but you have just made your first code change to core functionality - without touching any of Evennia's original code! We just plugged in our own version of the `at_before_say` method and it replaced the default one. Evennia happily redirected the message through our version and we got a different output.

> For sane overriding of parent methods you should also be aware of Python's [super](https://docs.python.org/3/library/functions.html#super), which allows you to call the methods defined on a parent in your child class.

### The Evennia shell

Now on to some generally useful tools as you continue learning Python and Evennia. We have so far explored using `py` and have inserted Python code directly in-game. We have also modified Evennia's behavior by overriding default functionality with our own. There is a third way to conveniently explore Evennia and Python - the Evennia shell.

Outside of your game, `cd` to your mygame folder and make sure any needed virtualenv is running. Next:

    > pip install ipython      # only needed once

The [`IPython`](https://en.wikipedia.org/wiki/IPython) program is just a nicer interface to the Python interpreter - you only need to install it once, after which Evennia will use it automatically.

    > evennia shell

If you did this call from your game dir you will now be in a Python prompt managed by the IPython program.

    IPython ...
    ...
    In [1]: 
IPython has some very nice ways to explore what Evennia has to offer.

    > import evennia
    > evennia.<TAB>

That is, write `evennia.` and press the Tab key. You will be presented with a list of all available resources in the Evennia Flat API. We looked at the `__init__.py` file in the `evennia` folder earlier, so some of what you see should be familiar. From the IPython prompt, do:

    > from evennia import DefaultCharacter
    > DefaultCharacter.at_before_say?

Don't forget that you can use `<TAB>` to auto-complete code as you write. Appending a single `?` to the end will show you the doc-string for `at_before_say` we looked at earlier. Use `??` to get the whole source code.

Let's look at our over-ridden version instead. Since we started the `evennia shell` from our game dir we can easily get to our code too:

    > from typeclasses.characters import Character
    > Character.at_before_say??

This will show us the changed code we just did. Having a window with IPython running is very convenient for quickly exploring code without having to go digging through the file structure!

### Where to go from here

This should give you a running start using Python with Evennia. If you are completely new to programming or Python you might want to look at a more formal Python tutorial. You can find links and resources [on our link page](./Links).

We have touched upon many of the concepts here but to use Evennia and to be able to follow along in the code, you will need basic understanding of Python [modules](http://docs.python.org/2/tutorial/modules.html), [variables](http://www.tutorialspoint.com/python/python_variable_types.htm), [conditional statements](http://docs.python.org/tutorial/controlflow.html#if-statements), [loops](http://docs.python.org/tutorial/controlflow.html#for-statements), [functions](http://docs.python.org/tutorial/controlflow.html#defining-functions), [lists, dictionaries, list comprehensions](http://docs.python.org/tutorial/datastructures.html) and [string formatting](http://docs.python.org/tutorial/introduction.html#strings). You should also have a basic understanding of [object-oriented programming](http://www.tutorialspoint.com/python/python_classes_objects.htm) and what Python [Classes](http://docs.python.org/tutorial/classes.html) are.

Once you have familiarized yourself, or if you prefer to pick Python up as you go, continue to one of the beginning-level [Evennia tutorials](./Tutorials) to gradually build up your understanding.

Good luck!
