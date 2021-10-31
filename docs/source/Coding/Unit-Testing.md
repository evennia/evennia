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

## Running tests with custom settings file

If you have implemented your own tests for your game (see below) you can run them from your game dir
with

    evennia test .

The period (`.`) means to run all tests found in the current directory and all subdirectories. You
could also specify, say, `typeclasses` or `world` if you wanted to just run tests in those subdirs.

Those tests will all be run using the default settings. To run the tests with your own settings file
you must use the `--settings` option:

    evennia test --settings settings.py .

The `--settings` option of Evennia takes a file name in the `mygame/server/conf` folder. It is
normally used to swap settings files for testing and development. In combination with `test`, it
forces Evennia to use this settings file over the default one.

## Writing new tests

Evennia's test suite makes use of Django unit test system, which in turn relies on Python's
*unittest* module.

> If you want to help out writing unittests for Evennia, take a look at Evennia's [coveralls.io
page](https://coveralls.io/github/evennia/evennia). There you see which modules have any form of
test coverage and which does not.

To make the test runner find the tests, they must be put in a module named `test*.py` (so `test.py`,
`tests.py` etc). Such a test module will be found wherever it is in the package. It can be a good
idea to look at some of Evennia's `tests.py` modules to see how they look.

Inside a testing file, a `unittest.TestCase` class is used to test a single aspect or component in
various ways. Each test case contains one or more *test methods* - these define the actual tests to
run. You can name the test methods anything you want as long as  the name starts with "`test_`".
Your `TestCase` class can also have a method `setUp()`. This is run before each test, setting up and
storing whatever preparations the test methods need. Conversely, a `tearDown()` method can
optionally do cleanup after each test.

To test the results, you use special methods of the `TestCase` class.  Many of those start with
"`assert`", such as `assertEqual` or `assertTrue`.

Example of a `TestCase` class:

```python
    import unittest

    # the function we want to test
    from mypath import myfunc

    class TestObj(unittest.TestCase):
       "This tests a function myfunc."

       def test_return_value(self):
           "test method. Makes sure return value is as expected."
           expected_return = "This is me being nice."
           actual_return = myfunc()
           # test
           self.assertEqual(expected_return, actual_return)
       def test_alternative_call(self):
           "test method. Calls with a keyword argument."
           expected_return = "This is me being baaaad."
           actual_return = myfunc(bad=True)
           # test
           self.assertEqual(expected_return, actual_return)
```

You might also want to read the [documentation for the unittest
module](https://docs.python.org/library/unittest.html).

### Using the EvenniaTest class

Evennia offers a custom TestCase, the `evennia.utils.test_resources.EvenniaTest` class. This class
initiates a range of useful properties on themselves for testing Evennia systems. Examples are
`.account` and `.session` representing a mock connected Account and its Session and `.char1` and
`char2` representing Characters complete with a location in the test database. These are all useful
when testing Evennia system requiring any of the default Evennia typeclasses as inputs. See the full
definition of the `EvenniaTest` class in
[evennia/utils/test_resources.py](https://github.com/evennia/evennia/blob/master/evennia/utils/test_resources.py).

```python
# in a test module

from evennia.utils.test_resources import EvenniaTest

class TestObject(EvenniaTest):
    def test_object_search(self):
        # char1 and char2 are both created in room1
        self.assertEqual(self.char1.search(self.char2.key), self.char2)
        self.assertEqual(self.char1.search(self.char1.location.key), self.char1.location)
        # ...
```

### Testing in-game Commands

In-game Commands are a special case. Tests for the default commands are put in
`evennia/commands/default/tests.py`. This uses a custom `CommandTest` class that inherits from
`evennia.utils.test_resources.EvenniaTest` described above. `CommandTest` supplies extra convenience
functions for executing commands and check that their return values (calls of `msg()` returns
expected values. It uses Characters and Sessions generated on the `EvenniaTest` class to call each
class).

Each command tested should have its own `TestCase` class. Inherit this class from the `CommandTest`
class in the same module to get access to the command-specific utilities mentioned.

```python
    from evennia.commands.default.tests import CommandTest
    from evennia.commands.default import general
    class TestSet(CommandTest):
        "tests the look command by simple call, using Char2 as a target"
        def test_mycmd_char(self):
            self.call(general.CmdLook(), "Char2", "Char2(#7)")
        "tests the look command by simple call, with target as room"
        def test_mycmd_room(self):
            self.call(general.CmdLook(), "Room",
                      "Room(#1)\nroom_desc\nExits: out(#3)\n"
                      "You see: Obj(#4), Obj2(#5), Char2(#7)")
```

### Unit testing contribs with custom models

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
from evennia.utils.test_resources import EvenniaTest

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

class TestMyModel(EvenniaTest):
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

### A note on adding new tests

Having an extensive tests suite is very important for avoiding code degradation as Evennia is
developed. Only a small fraction of the Evennia codebase is covered by test suites at this point.
Writing new tests is not hard, it's more a matter of finding the time to do so. So adding new tests
is really an area where everyone can contribute, also with only limited Python skills.

### A note on making the test runner faster

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

## Testing for Game development (mini-tutorial)

Unit testing can be of paramount importance to game developers. When starting with a new game, it is
recommended to look into unit testing as soon as possible; an already huge game is much harder to
write tests for.  The benefits of testing a game aren't different from the ones regarding library
testing.  For example it is easy to introduce bugs that affect previously working code. Testing is
there to ensure your project behaves the way it should and continue to do so.

If you have never used unit testing (with Python or another language), you might want to check the
[official Python documentation about unit testing](https://docs.python.org/2/library/unittest.html),
particularly the first section dedicated to a basic example.

### Basic testing using Evennia

Evennia's test runner can be used to launch tests in your game directory (let's call it 'mygame').
Evennia's test runner does a few useful things beyond the normal Python unittest module:

* It creates and sets up an empty database, with some useful objects (accounts, characters and
rooms, among others).
* It provides simple ways to test commands, which can be somewhat tricky at times, if not tested
properly.

Therefore, you should use the command-line to execute the test runner, while specifying your own
game directories (not the one containing evennia).  Go to your game directory (referred as 'mygame'
in this section) and execute the test runner:

    evennia --settings settings.py test commands

This command will execute Evennia's test runner using your own settings file. It will set up a dummy
database of your choice and look into the 'commands' package defined in your game directory
(`mygame/commands` in this example) to find tests. The test module's name should begin with 'test'
and contain one or more `TestCase`.  A full example can be found below.

### A simple example

In your game directory, go to `commands` and create a new file `tests.py` inside (it could be named
anything starting with `test`). We will start by making a test that has nothing to do with Commands,
just to show how unit testing works:

```python
    # mygame/commands/tests.py

    import unittest

    class TestString(unittest.TestCase):

        """Unittest for strings (just a basic example)."""

        def test_upper(self):
            """Test the upper() str method."""
            self.assertEqual('foo'.upper(), 'FOO')
```

This example, inspired from the Python documentation, is used to test the 'upper()' method of the
'str' class.  Not very useful, but it should give you a basic idea of how tests are used.

Let's execute that test to see if it works.

    > evennia --settings settings.py test commands

    TESTING: Using specified settings file 'server.conf.settings'.

    (Obs: Evennia's full test suite may not pass if the settings are very
    different from the default. Use 'test .' as arguments to run only tests
    on the game dir.)

    Creating test database for alias 'default'...
    .
    ----------------------------------------------------------------------
    Ran 1 test in 0.001s

    OK
    Destroying test database for alias 'default'...

We specified the `commands` package to the evennia test command since that's where we put our test
file. In this case we could just as well just said `.` to search all of `mygame` for testing files.
If we have a lot of tests it may be useful to test only a single set at a time though. We get an
information text telling us we are using our custom settings file (instead of Evennia's default
file) and then the test runs. The test passes! Change the "FOO" string to something else in the test
to see how it looks when it fails.

### Testing commands

```{warning} This is not correct anymore.
```

This section will test the proper execution of the 'abilities' command, as described in the DELETED
tutorial to create the 'abilities' command, we will need it to test it.

Testing commands in Evennia is a bit more complex than the simple testing example we have seen.
Luckily, Evennia supplies a special test class to do just that ... we just need to inherit from it
and use it properly. This class is called 'CommandTest' and is defined in the
'evennia.commands.default.tests' package.  To create a test for our 'abilities' command, we just
need to create a class that inherits from 'CommandTest' and add methods.

We could create a new test file for this but for now we just append to the `tests.py` file we
already have in `commands` from before.

```python
    # bottom of mygame/commands/tests.py

    from evennia.commands.default.tests import CommandTest

    from commands.command import CmdAbilities
    from typeclasses.characters import Character

    class TestAbilities(CommandTest):

        character_typeclass = Character

        def test_simple(self):
            self.call(CmdAbilities(), "", "STR: 5, AGI: 4, MAG: 2")
```

* Line 1-4:  we do some importing.  'CommandTest' is going to be our base class for our test, so we
need it.  We also import our command ('CmdAbilities' in this case).  Finally we import the
'Character' typeclass.  We need it, since 'CommandTest' doesn't use 'Character', but
'DefaultCharacter', which means the character calling the command won't have the abilities we have
written in the 'Character' typeclass.
* Line 6-8:  that's the body of our test.  Here, a single command is tested in an entire class.
Default commands are usually grouped by category in a single class.  There is no rule, as long as
you know where you put your tests.  Note that we set the 'character_typeclass' class attribute to
Character.  As explained above, if you didn't do that, the system would create a 'DefaultCharacter'
object, not a 'Character'.  You can try to remove line 4 and 8 to see what happens when running the
test.
* Line 10-11:  our unique testing method.  Note its name:  it should begin by 'test_'.  Apart from
that, the method is quite simple:  it's an instance method (so it takes the 'self' argument) but no
other arguments are needed.  Line 11 uses the 'call' method, which is defined in 'CommandTest'.
It's a useful method that compares a command against an expected result.  It would be like comparing
two strings with 'assertEqual', but the 'call' method does more things, including testing the
command in a realistic way (calling its hooks in the right order, so you don't have to worry about
that).

Line 11 can be understood as:  test the 'abilities' command (first parameter), with no argument
(second parameter), and check that the character using it receives his/her abilities (third
parameter).

Let's run our new test:

    > evennia --settings settings.py test commands
    [...]
    Creating test database for alias 'default'...
    ..
    ----------------------------------------------------------------------
    Ran 2 tests in 0.156s

    OK
    Destroying test database for alias 'default'...

Two tests were executed, since we have kept 'TestString' from last time.  In case of failure, you
will get much more information to help you fix the bug.
