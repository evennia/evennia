# -*- coding: utf-8 -*-

"""
Unit testing of the 'objects' Evennia component.

Runs as part of the Evennia's test suite with 'manage.py test-evennia'.

Please add new tests to this module as needed.

Guidelines:
 A 'test case' is testing a specific component and is defined as a class inheriting from unittest.TestCase.
 The test case class can have a method setUp() that creates and sets up the testing environment.
 All methods inside the test case class whose names start with 'test' are used as test methods by the runner.
 Inside the test methods, special member methods assert*() are used to test the behaviour.
"""

import re, time
try:
    # this is a special optimized Django version, only available in current Django devel
    from django.utils.unittest import TestCase
except ImportError:
    # if our Django is older we use the normal version
    # TODO: Switch this to django.test.TestCase when the but has been plugged that gives 
    # traceback when using that module over TransactionTestCase.
    from django.test import TestCase
    #from django.test import TransactionTestCase as TestCase
from django.conf import settings
from src.objects import models, objects
from src.utils import create
from src.server import session, sessionhandler

class TestObjAttrs(TestCase):
    """
    Test aspects of ObjAttributes
    """
    def setUp(self):
        "set up the test"
        self.attr = models.ObjAttribute()
        self.obj1 = create.create_object(objects.Object, key="testobj1", location=None)
        self.obj2 = create.create_object(objects.Object, key="testobj2", location=self.obj1)

    # tests
    def test_store_str(self):
        hstring = "sdfv00=97sfjs842 ivfjlQKFos9GF^8dddsöäå-?%"
        self.obj1.db.testattr = hstring
        self.assertEqual(hstring, self.obj1.db.testattr)
    def test_store_obj(self):
        self.obj1.db.testattr = self.obj2
        self.assertEqual(self.obj2 ,self.obj1.db.testattr)
        self.assertEqual(self.obj2.location, self.obj1.db.testattr.location)


#------------------------------------------------------------
# Command testing
#------------------------------------------------------------

# print all feedback from test commands (can become very verbose!)
VERBOSE = False 

class FakeSession(session.SessionProtocol):
    """
    A fake session that implements dummy versions of the real thing; this is needed to mimic
    a logged-in player.
    """
    def connectionMade(self):
        self.prep_session()
        sessionhandler.add_session(self)
    def prep_session(self):
        self.server, self.address = None, "0.0.0.0"
        self.name, self.uid = None, None
        self.logged_in = False
        self.encoding = "utf-8"
        self.cmd_last, self.cmd_last_visible, self.cmd_conn_time = time.time(), time.time(), time.time()
        self.cmd_total = 0
    def disconnectClient(self):
        pass
    def lineReceived(self, raw_string):
        pass
    def msg(self, message, markup=True):
        if VERBOSE:        
            print message

class TestCommand(TestCase):
    """
    Sets up the basics of testing the default commands and the generic things
    that should always be present in a command.

    Inherit new tests from this.
    """
    def setUp(self):
        "sets up the testing environment"                
        self.room1 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room1")
        self.room2 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room2")

        # create a faux player/character for testing.
        self.char1 = create.create_player("TestingPlayer", "testplayer@test.com", "testpassword", location=self.room1)
        self.char1.player.user.is_superuser = True 
        sess = FakeSession()
        sess.connectionMade()
        sess.login(self.char1.player)
        
        self.char2 = create.create_object(settings.BASE_CHARACTER_TYPECLASS, key="char2", location=self.room1)
        self.obj1 = create.create_object(settings.BASE_OBJECT_TYPECLASS, key="obj1", location=self.room1)
        self.obj2 = create.create_object(settings.BASE_OBJECT_TYPECLASS, key="obj2", location=self.room1)
        self.exit1 = create.create_object(settings.BASE_EXIT_TYPECLASS, key="exit1", location=self.room1)
        self.exit2 = create.create_object(settings.BASE_EXIT_TYPECLASS, key="exit2", location=self.room2)        
        
    def get_cmd(self, cmd_class, argument_string=""):
        """
        Obtain a cmd instance from a class and an input string
        Note: This does not make use of the cmdhandler functionality.
        """        
        cmd = cmd_class()
        cmd.caller = self.char1
        cmd.cmdstring = cmd_class.key
        cmd.args = argument_string
        cmd.cmdset = None
        cmd.obj = self.char1
        return cmd
    
    def execute_cmd(self, raw_string):
        """
        Creates the command through faking a normal command call; 
        This also mangles the input in various ways to test if the command
        will be fooled.
        """ 
        test1 = re.sub(r'\s', '', raw_string) # remove all whitespace inside it
        test2 = "%s/åäö öäö;-:$£@*~^' 'test" % raw_string # inserting weird characters in call
        test3 = "%s %s" % (raw_string, raw_string) # multiple calls 
        self.char1.execute_cmd(test1)
        self.char1.execute_cmd(test2)
        self.char1.execute_cmd(test3)
        self.char1.execute_cmd(raw_string)

#------------------------------------------------------------
# Default set Command testing
#------------------------------------------------------------

class TestHome(TestCommand):
    def test_call(self):
        self.char1.home = self.room2
        self.execute_cmd("home")
        self.assertEqual(self.char1.location, self.room2)
class TestLook(TestCommand):
    def test_call(self):
        self.execute_cmd("look here")
class TestPassword(TestCommand):
    def test_call(self):
        self.execute_cmd("@password testpassword = newpassword")
class TestNick(TestCommand):
    def test_call(self):
        self.execute_cmd("nickname testalias = testaliasedstring")        
        self.assertEquals("testaliasedstring", self.char1.nicks.get("testalias", None))
