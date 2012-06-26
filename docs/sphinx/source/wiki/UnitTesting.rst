Unit Testing
============

*This topic is mainly of interest to people interested in helping to
develop Evennia itself.*

Unit testing means testing components of a program in isolation from
each other to make sure every part works on its own before using it with
others. Extensive testing helps avoid new updates causing unexpected
side effects as well as alleviates general code rot (a more
comprehensive wikipedia article on unit testing can be found
`here <http://en.wikipedia.org/wiki/Unit_test>`_).

A typical unit test calls some component of Evennia with a given input,
looks at the result and makes sure that this result looks as expected.
Rather than having lots of stand-alone test programs, Evennia makes use
of a central *test runner*. This is a program that gathers all available
tests all over the Evennia source code (called *test suites*) and runs
them all in one go. Errors and tracebacks are reported.

Running the test suite
----------------------

To run the Evennia test suite, go to the ``game/`` folder and issue the
command

    ``python manage.py test``

A temporary database will be instantiated to manage the tests. If
everything works out you will see how many tests were run and how long
it took. If something went wrong you will get error messages.

Writing new tests
-----------------

Evennia's test suite makes use of Django unit test system, which in turn
relies on Python's *unittest* module. Evennia's test modules are always
named ``tests.py`` and should be located in different sub folders of
``src/`` depending on which system they are testing. You can find an
example of a testing module in ``src/objects/tests.py``.

Inside the ``tests.py`` module you create classes inheriting from
``django.test.TestCase`` (later versions of Django will use
``django.utils.unittest.TestCase`` instead). A ``TestCase`` class is
used to test a single aspect or component in various ways. Each test
case contains one ore more *test methods* - these define the actual
tests to run. You can name the test methods anything you want as long as
the name starts with "``test_``\ ". Your ``TestCase`` class can also
have a method SetUp(). This is run before each test, setting up whatever
preparations the test methods need.

To test the results, you use special methods of the ``TestCase`` class.
Many of those start with "``assert``\ ", such as ``assertEqual`` or
``assertTrue``.

Example of a ``TestCase`` class (inside a file ``tests.py``):

::


    # testing a simple funcion

    try:
       # this is an optimized version only available in later Django versions
       from django.utils.unittest import TestCase
    except ImportError:
       # if the first fail, we use the old version
       from django.test import TestCase

    # the function we want to test
    from mypath import myfunc

    TestObj(unittest.TestCase):
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

The above example is very simplistic, but you should get the idea. Look
at ``src/objects/tests.py`` for more realistic examples of tests. You
might also want to read the `documentation for the unittest
module <http://docs.python.org/library/unittest.html>`_.

Testing in-game Commands
------------------------

In-game Commands are a special case. Tests for the default commands are
put in ``src/commands/default/tests.py``. This test suite is executed as
part of running the ``objects`` test suite (since it lies outside
Django's normal "app" structure). It also supplies a few convenience
functions for executing commands (notably creating a "fake" player
session so as to mimic an actual command call). It also makes several
test characters and objects available. For example ``char1`` is a
"logged in" Character object that acts as the one calling the command.

Each command tested should have its own ``TestCase`` class. Inherit this
class from the ``CommandTest`` class in the same module to get access to
the command-specific utilities mentioned.

::

    class TestSet(CommandTest):
        "tests the @set command by simple call"
        def test_call(self):
            self.execute_command("@set self/testval = mytestvalue")
            # knowing what @set does, our test character (char1) should
            # by now have a new attribute 'testval' with the value 'mytestvalue'.
            self.assertEqual("mytestvalue", self.char1.db.testval)

A note on adding new tests
--------------------------

Having an extensive tests suite is very important for avoiding code
degradation as Evennia is developed. Only a small fraction of the
Evennia codebase is covered by test suites at this point. Writing new
tests is not hard, it's more a matter of finding the time to do so. So
adding new tests is really an area where everyone can contribute, also
with only limited Python skills.
