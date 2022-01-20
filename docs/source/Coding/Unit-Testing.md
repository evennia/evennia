# Unit Testing

*Unit testing* means testing components of a program in isolation from each other to make sure every
part works on its own before using it with others. Extensive testing helps avoid new updates causing
unexpected side effects as well as alleviates general code rot (a more comprehensive wikipedia
article on unit testing can be found [here](https://en.wikipedia.org/wiki/Unit_test)).

A typical unit test set calls some function or method with a given input, looks at the result and
makes sure that this result looks as expected. Rather than having lots of stand-alone test programs,
Evennia makes use of a central *test runner*. This is a program that gathers all available tests all
over the Evennia source code (called *test suites*) and runs them all in one go. Errors and
tracebacks are reported.

By default Evennia only tests itself. But you can also add your own tests to your game code and have
Evennia run those for you.

## Running the Evennia test suite

To run the full Evennia test suite, go to your game folder and issue the command

    evennia test evennia

This will run all the evennia tests using the default settings. You could also run only a subset of
all tests by specifying a subpackage of the library:

    evennia test evennia.commands.default

A temporary database will be instantiated to manage the tests. If everything works out you will see
how many tests were run and how long it took. If something went wrong you will get error messages.
If you contribute to Evennia, this is a useful sanity check to see you haven't introduced an
unexpected bug.

## Running tests for your game dir

If you have implemented your own tests for your game you can run them from your game dir
with

    evennia test .

The period (`.`) means to run all tests found in the current directory and all subdirectories. You
could also specify, say, `typeclasses` or `world` if you wanted to just run tests in those subdirs.

An important thing to note is that those tests will all be run using the _default Evennia settings_. 
To run the tests with your own settings file you must use the `--settings` option:

    evennia test --settings settings.py .

The `--settings` option of Evennia takes a file name in the `mygame/server/conf` folder. It is
normally used to swap settings files for testing and development. In combination with `test`, it
forces Evennia to use this settings file over the default one.

You can also test specific things by giving their path

    evennia test --settings settings.py .world.tests.YourTest


## Writing new tests

Evennia's test suite makes use of Django unit test system, which in turn relies on Python's
*unittest* module.

To make the test runner find the tests, they must be put in a module named `test*.py` (so `test.py`,
`tests.py` etc). Such a test module will be found wherever it is in the package. It can be a good
idea to look at some of Evennia's `tests.py` modules to see how they look.

Inside the module you need to put a class inheriting (at any distance) from `unittest.TestCase`. Each
method on that class that starts with `test_` will be run separately as a unit test. There 
are two special, optional methods `setUp` and `tearDown` that will (if you define them) run before 
_every_ test. This can be useful for setting up and deleting things.

To actually test things, you use special `assert...` methods on the class. Most common on is 
`assertEqual`, which makes sure a result is what you expect it to be.

Here's an example of the principle. Let's assume you put this in `mygame/world/tests.py` 
and want to test a function in `mygame/world/myfunctions.py`

```python
    # in a module tests.py somewhere i your game dir
    import unittest

    from evennia import create_object
    # the function we want to test
    from .myfunctions import myfunc

    
    class TestObj(unittest.TestCase):
       "This tests a function myfunc."

       def setUp(self):
           """done before every of the test_ * methods below"""
           self.obj = create_object("mytestobject")
           
       def tearDown(self):
           """done after every test_* method below """
           self.obj.delete()
       
       def test_return_value(self):
           """test method. Makes sure return value is as expected."""
           actual_return = myfunc(self.obj)
           expected_return = "This is the good object 'mytestobject'."
           # test
           self.assertEqual(expected_return, actual_return)
       def test_alternative_call(self):
           """test method. Calls with a keyword argument."""
           actual_return = myfunc(self.obj, bad=True)
           expected_return = "This is the baaad object 'mytestobject'."
           # test
           self.assertEqual(expected_return, actual_return)
```

To test this, run 

    evennia test --settings settings.py .

to run the entire test module

    evennia test --settings setings.py .world.tests

or a specific class:

    evennia test --settings settings.py .world.tests.TestObj 

You can also run a specific test: 

    evennia test --settings settings.py .world.tests.TestObj.test_alternative_call

You might also want to read the [Python documentation for the unittest module](https://docs.python.org/library/unittest.html).

## Using the Evennia testing classes

Evennia offers many custom testing classes that helps with testing Evennia features. 
They are all found in [evennia.utils.test_resources](evennia.utils.test_resources). Note that 
these classes implement the `setUp` and `tearDown` already, so if you want to add stuff in them 
yourself you should remember to use e.g. `super().setUp()` in your code.

### Classes for testing your game dir

These all use whatever setting you pass to them and works well for testing code in your game dir.

- `EvenniaTest` - this sets up a full object environment for your test. All the created entities 
   can be accesses as properties on the class:
  - `.account` - A fake [Account](evennia.accounts.accounts.DefaultAccount) named "TestAccount".
  - `.account2` - Another account named "TestAccount2"
  - `char1` - A [Character](evennia.objects.objects.DefaultCharacter) linked to `.account`, named `Char`. 
    This has 'Developer' permissions but is not a superuser.
  - `.char2` - Another character linked to `account`, named `Char2`. This has base permissions (player).
  - `.obj1` - A regular [Object](evennia.objects.objects.DefaultObject) named "Obj". 
  - `.obj2` - Another object named "Obj2".
  - `.room1` - A [Room](evennia.objects.objects.DefaultRoom) named "Room". Both characters and both 
    objects are located inside this room. It has a description of "room_desc".
  - `.room2` - Another room named "Room2". It is empty and has no set description.
  - `.exit` - An exit named "out" that leads from `.room1` to `.room2`.
  - `.script` - A [Script](evennia.scripts.scripts.DefaultScript) named "Script". It's an inert script 
    without a timing component.
  - `.session` - A fake [Session](evennia.server.serversession.ServerSession) that mimics a player 
    connecting to the game. It is used by `.account1` and has a sessid of 1.
- `EvenniaCommandTest` - has the same environment like `EvenniaTest` but also adds a special
   [.call()](evennia.utils.test_resources.EvenniaCommandTestMixin.call) method specifically for 
   testing Evennia [Commands](../Components/Commands.md). It allows you to compare what the command _actually_ 
   returns to the player with what you expect. Read the `call` api doc for more info.
- `EvenniaTestCase` - This is identical to the regular Python `TestCase` class, it's
  just there for naming symmetry with `BaseEvenniaTestCase` below.

Here's an example of using `EvenniaTest`

```python
# in a test module

from evennia.utils.test_resources import EvenniaTest

class TestObject(EvenniaTest):
    """Remember that the testing class creates char1 and char2 inside room1 ..."""
    def test_object_search_character(self):
        """Check that char1 can search for char2 by name"""
        self.assertEqual(self.char1.search(self.char2.key), self.char2)
        
    def test_location_search(self):
        """Check so that char1 can find the current location by name"""
        self.assertEqual(self.char1.search(self.char1.location.key), self.char1.location)
        # ...
```

This example tests a custom command.

```python
    from evennia.commands.default.tests import EvenniaCommandTest
from commands import command as mycommand


class TestSet(EvenniaCommandTest):
    "tests the look command by simple call, using Char2 as a target"

    def test_mycmd_char(self):
        self.call(mycommand.CmdMyLook(), "Char2", "Char2(#7)")

    def test_mycmd_room(self):
        "tests the look command by simple call, with target as room"
        self.call(mycommand.CmdMyLook(), "Room",
                  "Room(#1)\nroom_desc\nExits: out(#3)\n"
                  "You see: Obj(#4), Obj2(#5), Char2(#7)")
```

When using `.call`, you don't need to specify the entire string; you can just give the beginning
of it and if it matches, that's enough. Use `\n` to denote line breaks and (this is a special for 
the `.call` helper), `||` to indicate multiple uses of `.msg()` in the Command. The `.call` helper
has a lot of arguments for mimicing different ways of calling a Command, so make sure to 
[read the API docs for .call()](evennia.utils.test_resources.EvenniaCommandTestMixin.call).

### Classes for testing Evennia core

These are used for testing Evennia itself. They provide the same resources as the classes 
above but enforce Evennias default settings found in `evennia/settings_default.py`, ignoring
any settings changes in your game dir.

- `BaseEvenniaTest` - all the default objects above but with enforced default settings
- `BaseEvenniaCommandTest` - for testing Commands, but with enforced default settings
- `BaseEvenniaTestCase` - no default objects, only enforced default settings

There are also two special 'mixin' classes. These are uses in the classes above, but may also 
be useful if you want to mix your own testing classes: 

- `EvenniaTestMixin` - A class mixin that creates all test environment objects.
- `EvenniaCommandMixin` - A class mixin that adds the `.call()` Command-tester helper.
 
If you want to help out writing unittests for Evennia, take a look at Evennia's [coveralls.io
page](https://coveralls.io/github/evennia/evennia). There you see which modules have any form of
test coverage and which does not. All help is appreciated!

## Unit testing contribs with custom models

A special case is if you were to create a contribution to go to the `evennia/contrib` folder that
uses its [own database models](../Concepts/New-Models.md). The problem with this is that Evennia (and Django) will
only recognize models in `settings.INSTALLED_APPS`. If a user wants to use your contrib, they will
be required to add your models to their settings file. But since contribs are optional you cannot
add the model to Evennia's central `settings_default.py` file - this would always create your
optional models regardless of if the user wants them. But at the same time a contribution is a part
of the Evennia distribution and its unit tests should be run with all other Evennia tests using
`evennia test evennia`.

The way to do this is to only temporarily add your models to the `INSTALLED_APPS` directory when the
test runs. here is an example of how to do it.

> Note that this solution, derived from this [stackexchange
answer](http://stackoverflow.com/questions/502916/django-how-to-create-a-model-dynamically-just-for-
testing#503435) is currently untested! Please report your findings.

```python
# a file contrib/mycontrib/tests.py

from django.conf import settings
import django
from evennia.utils.test_resources import BaseEvenniaTest

OLD_DEFAULT_SETTINGS = settings.INSTALLED_APPS
DEFAULT_SETTINGS = dict(
    INSTALLED_APPS=(
        'contrib.mycontrib.tests',
    ),
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3"
        }
    },
    SILENCED_SYSTEM_CHECKS=["1_7.W001"],
)


class TestMyModel(BaseEvenniaTest):
    def setUp(self):
        if not settings.configured:
            settings.configure(**DEFAULT_SETTINGS)
        django.setup()

        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    def tearDown(self):
        settings.configure(**OLD_DEFAULT_SETTINGS)
        django.setup()

        from django.core.management import call_command
        from django.db.models import loading
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    # test cases below ...

    def test_case(self):
# test case here
```


## A note on making the test runner faster

If you have custom models with a large number of migrations, creating the test database can take a
very long time. If you don't require migrations to run for your tests, you can disable them with the
django-test-without-migrations package. To install it, simply:

```
$ pip install django-test-without-migrations
```

Then add it to your `INSTALLED_APPS` in your `server.conf.settings.py`:

```python
INSTALLED_APPS = (
    # ...
    'test_without_migrations',
)
```

After doing so, you can then run tests without migrations by adding the `--nomigrations` argument:

```
evennia test --settings settings.py --nomigrations .
```