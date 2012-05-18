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
from src.server import serversession, sessionhandler
from src.locks.lockhandler import LockHandler
from src.server.models import ServerConfig
from src.comms.models import Channel, Msg, PlayerChannelConnection, ExternalChannelConnection
from django.contrib.auth.models import User
from src.players.models import PlayerDB
from src.objects.models import ObjectDB

#------------------------------------------------------------
# Command testing
# ------------------------------------------------------------

# print all feedback from test commands (can become very verbose!)
VERBOSE = True
NOMANGLE = True # mangle command input for extra testing

def cleanup():
    User.objects.all().delete()
    PlayerDB.objects.all().delete()
    ObjectDB.objects.all().delete()
    Channel.objects.all().delete()
    Msg.objects.all().delete()
    PlayerChannelConnection.objects.all().delete()
    ExternalChannelConnection.objects.all().delete()
    ServerConfig.objects.all().delete()

class FakeSessionHandler(sessionhandler.ServerSessionHandler):
    """
    Fake sessionhandler, without an amp connection
    """
    def portal_shutdown(self):
        pass
    def disconnect(self, session, reason=""):
        pass
    def login(self, session):
        pass
    def session_sync(self):
        pass
    def data_out(self, session, string="", data=""):
        return string

SESSIONS = FakeSessionHandler()

class FakeSession(serversession.ServerSession):
    """
    A fake session that
    implements dummy versions of the real thing; this is needed to
    mimic a logged-in player.
    """
    protocol_key = "TestProtocol"
    sessdict = {'protocol_key':'telnet', 'address':('0.0.0.0','5000'), 'sessid':2, 'uid':2, 'uname':None,
                'logged_in':False, 'cid':None, 'ndb':{}, 'encoding':'utf-8',
                'conn_time':time.time(), 'cmd_last':time.time(), 'cmd_last_visible':time.time(), 'cmd_total':1}

    def connectionMade(self):
        self.load_sync_data(self.sessdict)
        self.sessionhandler = SESSIONS
    def disconnectClient(self):
        pass
    def lineReceived(self, raw_string):
        pass
    def msg(self, message, data=None):
        global VERBOSE
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
# setting up objects

class CommandTest(TestCase):
    """
    Sets up the basics of testing the default commands and the generic things
    that should always be present in a command.

    Inherit new tests from this.
    """

    def setUp(self):
        "sets up the testing environment"
        #ServerConfig.objects.conf("default_home", 2)
        self.addCleanup(cleanup)
        self.room1 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room1")
        self.room2 = create.create_object(settings.BASE_ROOM_TYPECLASS, key="room2")
        # create a faux player/character for testing.
        self.char1 = create.create_player("TestChar", "testplayer@test.com", "testpassword", character_location=self.room1)
        self.char1.player.user.is_superuser = True
        self.char1.lock_storage = ""
        self.char1.locks = LockHandler(self.char1)
        self.char1.ndb.return_string = None
        self.sess1 = FakeSession()
        self.sess1.connectionMade()
        self.sess1.session_login(self.char1.player)
        # create second player
        self.char2 = create.create_player("TestChar2", "testplayer2@test.com", "testpassword2", character_location=self.room1)
        self.char2.player.user.is_superuser = False
        self.char2.lock_storage = ""
        self.char2.locks = LockHandler(self.char2)
        self.char2.ndb.return_string = None
        self.sess2 = FakeSession()
        self.sess2.connectionMade()
        self.sess2.session_login(self.char2.player)
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

    def execute_cmd(self, raw_string, wanted_return_string=None, nomangle=False):
        """
        Creates the command through faking a normal command call;
        This also mangles the input in various ways to test if the command
        will be fooled.
        """
        if not nomangle and not VERBOSE and not NOMANGLE:
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

class BuildTest(CommandTest):
    """
    We need to turn of mangling for build commands since
    it creates arbitrary objects that mess up tests later.
    """
    NOMANGLE = True


#------------------------------------------------------------
# Default set Command testing
#------------------------------------------------------------

# # general.py tests

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
        self.assertEqual(u"testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEqual(u"testaliasedstring2", self.char1.nicks.get("testalias",nick_type="player"))
        self.assertEqual(u"testaliasedstring3", self.char1.nicks.get("testalias",nick_type="object"))
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
        self.NOMANGLE = True
        sep = "-"*78 + "\n"
        self.execute_cmd("@help/add TestTopic,TestCategory = Test1", )
        self.execute_cmd("help TestTopic",sep + "Help topic for Testtopic\nTest1" + "\n" + sep)
        self.execute_cmd("@help/merge TestTopic = Test2", "Added the new text right after")
        self.execute_cmd("help TestTopic", sep + "Help topic for Testtopic\nTest1 Test2")
        self.execute_cmd("@help/append TestTopic = Test3", "Added the new text as a")
        self.execute_cmd("help TestTopic",sep + "Help topic for Testtopic\nTest1 Test2\n\nTest3")
        self.execute_cmd("@help/delete TestTopic","Deleted the help entry")
        self.execute_cmd("help TestTopic","No help entry found for 'TestTopic'")

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
# cannot test this here; screws up the test suite
#class TestPuppet(CommandTest):
#   def test_call(self):
#       self.execute_cmd("@puppet TestChar3", "You now control TestChar3.")
#       self.execute_cmd("@puppet TestChar", "You now control TestChar.")
class TestWall(CommandTest):
    def test_call(self):
        self.execute_cmd("@wall = This is a test message", "TestChar shouts")


# building.py command tests

class TestObjAlias(BuildTest):
    def test_call(self):
        self.execute_cmd("@alias obj1 = obj1alias, obj1alias2", "Aliases for")
        self.execute_cmd("look obj1alias2", "obj1")
class TestCopy(BuildTest):
    def test_call(self):
        self.execute_cmd("@copy obj1 = obj1_copy;alias1;alias2", "Copied obj1 to 'obj1_copy'")
        self.execute_cmd("look alias2","obj1_copy")
class TestSet(BuildTest):
    def test_call(self):
        self.execute_cmd("@set obj1/test = value", "Created attribute obj1/test = value")
        self.execute_cmd("@set obj1/test", "Attribute obj1/test = value")
        self.assertEqual(self.obj1.db.test, u"value")
class TestCpAttr(BuildTest):
    def test_call(self):
        self.execute_cmd("@set obj1/test = value")
        self.execute_cmd("@set obj2/test2 = value2")
        self.execute_cmd("@cpattr obj1/test = obj2/test")
        self.execute_cmd("@cpattr test2 = obj2")
        self.assertEqual(self.obj2.db.test, u"value")
        self.assertEqual(self.obj2.db.test2, u"value2")
class TestMvAttr(BuildTest):
    def test_call(self):
        self.execute_cmd("@set obj1/test = value")
        self.execute_cmd("@mvattr obj1/test = obj2")
        self.assertEqual(self.obj2.db.test, u"value")
        self.assertEqual(self.obj1.db.test, None)
class TestCreate(BuildTest):
    def test_call(self):
        self.execute_cmd("@create testobj;alias1;alias2")
        self.execute_cmd("look alias1", "testobj")
class TestDebug(BuildTest):
    def test_call(self):
        self.execute_cmd("@debug/obj obj1")
class TestDesc(BuildTest):
    def test_call(self):
        self.execute_cmd("@desc obj1 = Test object", "The description was set on")
        self.assertEqual(self.obj1.db.desc, u"Test object")
class TestDestroy(BuildTest):
    def test_call(self):
        self.execute_cmd("@destroy obj1, obj2", "obj1 was destroyed.\nobj2 was destroyed.")
class TestFind(BuildTest):
    def test_call(self):
        self.execute_cmd("@find obj1", "One Match")
class TestDig(BuildTest):
    def test_call(self):
        self.execute_cmd("@dig room3;roomalias1;roomalias2 = north;n,south;s")
        self.execute_cmd("@find room3", "One Match")
        self.execute_cmd("@find roomalias1", "One Match")
        self.execute_cmd("@find roomalias2", "One Match")
        self.execute_cmd("@find/room roomalias2", "One Match")
        self.execute_cmd("@find/exit south", "One Match")
        self.execute_cmd("@find/exit n", "One Match")
class TestUnLink(BuildTest):
    def test_call(self):
        self.execute_cmd("@dig room3;roomalias1, north, south")
        self.execute_cmd("@unlink north")
class TestLink(BuildTest):
    def test_call(self):
        self.execute_cmd("@dig room3;roomalias1, north, south")
        self.execute_cmd("@unlink north")
        self.execute_cmd("@link north = room3")
class TestHome(BuildTest):
    def test_call(self):
        self.obj1.db_home = self.obj2.dbobj
        self.obj1.save()
        self.execute_cmd("@home obj1")
        self.assertEqual(self.obj1.db_home, self.obj2.dbobj)
class TestCmdSets(BuildTest):
    def test_call(self):
        self.execute_cmd("@cmdsets")
        self.execute_cmd("@cmdsets obj1")
class TestName(BuildTest):
    def test_call(self):
        self.execute_cmd("@name obj1 = Test object", "Object's name changed to 'Test object'.")
        self.assertEqual(self.obj1.key, u"Test object")
class TestOpen(BuildTest):
    def test_call(self):
        self.execute_cmd("@dig room4;roomalias4")
        self.execute_cmd("@open testexit4;aliasexit4 = roomalias4", "Created new Exit")
class TestTypeclass(BuildTest):
    def test_call(self):
        self.execute_cmd("@typeclass obj1 = src.objects.objects.Character", "obj's type is now")
        self.assertEqual(self.obj1.db_typeclass_path, u"src.objects.objects.Character")
class TestSet(BuildTest):
    def test_call(self):
        self.execute_cmd("@set box1/test = value")
        self.execute_cmd("@wipe box1", "Wiped")
        self.assertEqual(self.obj1.db.all, [])
class TestLock(BuildTest):
    # lock functionality itseld is tested separately
    def test_call(self):
        self.char1.permissions = ["TestPerm"]
        self.execute_cmd("@lock obj1 = test:perm(TestPerm)")
        self.assertEqual(True, self.obj1.access(self.char1, u"test"))
class TestExamine(BuildTest):
    def test_call(self):
        self.execute_cmd("examine obj1", "------------")
class TestTeleport(BuildTest):
    def test_call(self):
        self.execute_cmd("@tel obj1 = obj2")
        self.assertEqual(self.obj1.location, self.obj2.dbobj)
class TestScript(BuildTest):
    def test_call(self):
        self.execute_cmd("@script TestChar = examples.bodyfunctions.BodyFunctions", "Script successfully added")

# Comms commands

class TestChannelCreate(CommandTest):
    def test_call(self):
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("testchan1 Hello", "[testchannel1] TestChar: Hello")
class TestAddCom(CommandTest):
    def test_call(self):
        self.execute_cmd("@cdestroy testchannel1", "Channel 'testchannel1'")
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("addcom chan1 = testchannel1")
        self.execute_cmd("addcom chan2 = testchan1")
        self.execute_cmd("delcom testchannel1")
        self.execute_cmd("addcom testchannel1" "You now listen to the channel channel.")
class TestDelCom(CommandTest):
    def test_call(self):
        self.execute_cmd("@cdestroy testchannel1", "Channel 'testchannel1'")
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("addcom chan1 = testchan1")
        self.execute_cmd("addcom chan2 = testchan1b")
        self.execute_cmd("addcom chan3 = testchannel1")
        self.execute_cmd("delcom chan1", "Your alias 'chan1' for ")
        self.execute_cmd("delcom chan2", "Your alias 'chan2' for ")
        self.execute_cmd("delcom testchannel1" "You stop listening to")
class TestAllCom(CommandTest):
    def test_call(self):
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("allcom off")
        self.execute_cmd("allcom on")
        self.execute_cmd("allcom destroy")
class TestChannels(CommandTest):
    def test_call(self):
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("@cdestroy testchannel1", "Channel 'testchannel1'")
class TestCBoot(CommandTest):
    def test_call(self):
        self.execute_cmd("@cdestroy testchannel1", "Channel 'testchannel1'")
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("addcom testchan = testchannel1")
        self.execute_cmd("@cboot testchannel1 = TestChar", "TestChar boots TestChar from channel.")
class TestCemit(CommandTest):
    def test_call(self):
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("@cemit testchan1 = Testing!", "[testchannel1] Testing!")
class TestCwho(CommandTest):
    def test_call(self):
        self.execute_cmd("@ccreate testchannel1;testchan1;testchan1b = This is a test channel")
        self.execute_cmd("@cwho testchan1b", "Channel subscriptions")

# OOC commands

#class TestOOC_and_IC(CommandTest): # can't be tested it seems, causes errors in other commands (?)
#    def test_call(self):
#        self.execute_cmd("@ooc", "\nYou go OOC.")
#        self.execute_cmd("@ic", "\nYou become TestChar")

# Unloggedin commands
# these cannot be tested from here.
