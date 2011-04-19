# -*- coding: utf-8 -*-
"""
 ** OBS - this is not a normal command module! **
 ** You cannot import anything in this module as a command! **

This is part of the Evennia unittest framework, for testing the
stability and integrity of the codebase during updates. This module
test the default command set. It is instantiated by the
src/objects/tests.py module, which in turn is run by as part of the
main test suite started with
 > python game/manage.py test.

"""

import re, time
try:
    # this is a special optimized Django version, only available in current Django devel
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase
from django.conf import settings
from src.utils import create, ansi
from src.server import session, sessionhandler
from src.locks.lockhandler import LockHandler
from src.server.models import ServerConfig

#------------------------------------------------------------ 
# Command testing 
# ------------------------------------------------------------

# print all feedback from test commands (can become very verbose!)
VERBOSE = False
NOMANGLE = False

class FakeSession(session.Session): 
    """ 
    A fake session that
    implements dummy versions of the real thing; this is needed to
    mimic a logged-in player.  
    """ 
    protocol_key = "TestProtocol"
    def connectionMade(self):
        self.session_connect('0,0,0,0')     
    def disconnectClient(self): 
        pass 
    def lineReceived(self, raw_string): 
        pass 
    def msg(self, message, data=None):             
        if message.startswith("Traceback (most recent call last):"):
            #retval = "Traceback last line: %s" % message.split('\n')[-4:]
            raise AssertionError(message)
        if self.player.character.ndb.return_string != None:
            return_list = self.player.character.ndb.return_string
            if hasattr(return_list, '__iter__'):
                rstring = return_list.pop(0)
                self.player.character.ndb.return_string = return_list
            else:
                rstring = return_list
                self.player.character.ndb.return_string = None
            message_noansi = ansi.parse_ansi(message, strip_ansi=True).strip()
            rstring = rstring.strip()
            if not message_noansi.startswith(rstring):
                sep1 = "\n" + "="*30 + "Wanted message" + "="*34 + "\n"
                sep2 = "\n" + "="*30 + "Returned message" + "="*32 + "\n"                
                sep3 = "\n" + "="*78
                retval = sep1 + rstring + sep2 + message_noansi + sep3
                raise AssertionError(retval)
        if VERBOSE:
            print message

class CommandTest(TestCase):
    """
    Sets up the basics of testing the default commands and the generic things
    that should always be present in a command.

    Inherit new tests from this.
    """
    def setUp(self):
        "sets up the testing environment"                
        ServerConfig.objects.conf("default_home", 2)
        
        self.room1 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room1")
        self.room2 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room2")

        # create a faux player/character for testing.
        self.char1 = create.create_player("TestChar", "testplayer@test.com", "testpassword", location=self.room1)
        self.char1.player.user.is_superuser = True
        self.char1.lock_storage = ""
        self.char1.locks = LockHandler(self.char1)
        self.char1.ndb.return_string = None
        sess = FakeSession()
        sess.connectionMade()
        sess.session_login(self.char1.player)
        # create second player
        self.char2 = create.create_player("TestChar2", "testplayer2@test.com", "testpassword2", location=self.room1)
        self.char2.player.user.is_superuser = False 
        self.char2.lock_storage = ""
        self.char2.locks = LockHandler(self.char2)
        self.char2.ndb.return_string = None
        sess2 = FakeSession()
        sess2.connectionMade()
        sess2.session_login(self.char2.player)
        # A non-player-controlled character 
        self.char3 = create.create_object(settings.BASE_CHARACTER_TYPECLASS, key="TestChar3", location=self.room1) 
        # create some objects  
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
    
    def execute_cmd(self, raw_string, wanted_return_string=None):
        """
        Creates the command through faking a normal command call; 
        This also mangles the input in various ways to test if the command
        will be fooled.
        """ 
        if not VERBOSE and not NOMANGLE:
            # only mangle if not VERBOSE, to make fewer return lines
            test1 = re.sub(r'\s', '', raw_string) # remove all whitespace inside it
            test2 = "%s/åäö öäö;-:$£@*~^' 'test" % raw_string # inserting weird characters in call
            test3 = "%s %s" % (raw_string, raw_string) # multiple calls 
            self.char1.execute_cmd(test1)
            self.char1.execute_cmd(test2)
            self.char1.execute_cmd(test3)
        # actual call, we potentially check so return is ok. 
        self.char1.ndb.return_string = wanted_return_string
        try:
            self.char1.execute_cmd(raw_string)
        except AssertionError, e:
            self.fail(e)
        self.char1.ndb.return_string = None
#------------------------------------------------------------
# Default set Command testing
#------------------------------------------------------------

# general.py tests

class TestLook(CommandTest):
    def test_call(self):
        self.execute_cmd("look here")
class TestHome(CommandTest):
    def test_call(self):
        self.char1.location = self.room1
        self.char1.home = self.room2
        self.execute_cmd("home")
        self.assertEqual(self.char1.location, self.room2)
class TestPassword(CommandTest):
    def test_call(self):
        self.execute_cmd("@password testpassword = newpassword")
class TestInventory(CommandTest):
    def test_call(self):
        self.execute_cmd("inv")
class TestQuit(CommandTest):
    def test_call(self):
        self.execute_cmd("@quit")
class TestPose(CommandTest):
    def test_call(self):
        self.execute_cmd("pose is testing","TestChar is testing")
class TestNick(CommandTest):
    def test_call(self):
        self.char1.player.user.is_superuser = False 
        self.execute_cmd("nickname testalias = testaliasedstring1")        
        self.execute_cmd("nickname/player testalias = testaliasedstring2")        
        self.execute_cmd("nickname/object testalias = testaliasedstring3")        
        self.assertEquals(u"testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEquals(u"testaliasedstring2", self.char1.nicks.get("testalias",nick_type="player"))
        self.assertEquals(u"testaliasedstring3", self.char1.nicks.get("testalias",nick_type="object"))
class TestGet(CommandTest):
    def test_call(self):        
        self.obj1.location = self.room1
        self.execute_cmd("get obj1", "You pick up obj1.")
class TestDrop(CommandTest):
    def test_call(self):        
        self.obj1.location = self.char1
        self.execute_cmd("drop obj1", "You drop obj1.")
class TestWho(CommandTest):
    def test_call(self):                
        self.execute_cmd("who")
class TestSay(CommandTest):
    def test_call(self):                
        self.execute_cmd("say Hello", 'You say, "Hello')
class TestAccess(CommandTest):
    def test_call(self):                
        self.execute_cmd("access")
class TestEncoding(CommandTest):
    def test_call(self):        
        global NOMANGLE
        NOMANGLE = True 
        self.char1.db.encoding="utf-8"
        self.execute_cmd("@encoding", "Default encoding:")
        NOMANGLE = False 

# help.py command tests

class TestHelpSystem(CommandTest):
    def test_call(self):                
        global NOMANGLE
        NOMANGLE = True 
        sep = "-"*78 + "\n"
        self.execute_cmd("@help/add TestTopic,TestCategory = Test1", )
        self.execute_cmd("help TestTopic",sep + "Help topic for Testtopic\nTest1" + "\n" + sep)
        self.execute_cmd("@help/merge TestTopic = Test2", "Added the new text right after")
        self.execute_cmd("help TestTopic", sep + "Help topic for Testtopic\nTest1 Test2")
        self.execute_cmd("@help/append TestTopic = Test3", "Added the new text as a")
        self.execute_cmd("help TestTopic",sep + "Help topic for Testtopic\nTest1 Test2\n\nTest3")
        self.execute_cmd("@help/delete TestTopic","Deleted the help entry")
        self.execute_cmd("help TestTopic","No help entry found for 'TestTopic'")
        NOMANGLE = False 

# system.py command tests
class TestPy(CommandTest):
    def test_call(self):
        self.execute_cmd("@py 1+2", [">>> 1+2", "<<< 3"])
class TestScripts(CommandTest):
    def test_call(self):
        script = create.create_script(None, "test")
        self.execute_cmd("@scripts", "id")
class TestObjects(CommandTest):
    def test_call(self):
        self.execute_cmd("@objects", "Database totals")
# Cannot be tested since we don't have an active server running at this point.
# class TestListService(CommandTest):
#     def test_call(self):
#         self.execute_cmd("@service/list", "---")
class TestVersion(CommandTest):
    def test_call(self):
        self.execute_cmd("@version", '---')
class TestTime(CommandTest):
    def test_call(self):
        self.execute_cmd("@time", "Current server uptime")
class TestServerLoad(CommandTest):
    def test_call(self):
        self.execute_cmd("@serverload", "Server load")
class TestPs(CommandTest):
    def test_call(self):
        self.execute_cmd("@ps","Non-timed scripts")

# admin.py command tests

class TestBoot(CommandTest):
   def test_call(self):
       self.execute_cmd("@boot TestChar2","You booted TestChar2.")
class TestDelPlayer(CommandTest):
   def test_call(self):
       self.execute_cmd("@delplayer TestChar2","Booting and informing player ...")
class TestEmit(CommandTest):
    def test_call(self):
        self.execute_cmd("@emit Test message", "Emitted to room1.")
class TestUserPassword(CommandTest):
    def test_call(self):
        self.execute_cmd("@userpassword TestChar2 = newpass", "TestChar2 - new password set to 'newpass'.")
class TestPerm(CommandTest):
    def test_call(self):
        self.execute_cmd("@perm TestChar2 = Builders", "Permission 'Builders' given to")
# cannot test this at the moment, screws up the test suite
#class TestPuppet(CommandTest):
#   def test_call(self):
#       self.execute_cmd("@puppet TestChar3", "You now control TestChar3.")       
#       self.execute_cmd("@puppet TestChar", "You now control TestChar.")       
class TestWall(CommandTest):
    def test_call(self):
        self.execute_cmd("@wall = This is a test message", "TestChar shouts")
        
# building.py command tests

class TestScript(CommandTest):
    def test_call(self):
        self.execute_cmd("@script TestChar = examples.bodyfunctions.BodyFunctions", "Script successfully added")

#TODO
