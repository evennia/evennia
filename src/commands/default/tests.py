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

import re
from django.conf import settings
from django.utils.unittest import TestCase
from src.server.serversession import ServerSession
from src.objects.objects import Object, Character
from src.players.player import Player
from src.utils import create, ansi
from src.server.sessionhandler import SESSIONS

from django.db.models.signals import post_save
from src.server.caches import field_post_save
post_save.connect(field_post_save, dispatch_uid="fieldcache")

# set up signal here since we are not starting the server

_RE = re.compile(r"^\+|-+\+|\+-+|--*|\|", re.MULTILINE)

#------------------------------------------------------------
# Command testing
# ------------------------------------------------------------


def dummy(self, *args, **kwargs):
    pass

SESSIONS.data_out = dummy
SESSIONS.disconnect = dummy


class TestObjectClass(Object):
    def msg(self, text="", **kwargs):
        "test message"
        pass


class TestCharacterClass(Character):
    def msg(self, text="", **kwargs):
        "test message"
        if self.player:
            self.player.msg(text=text, **kwargs)
        else:
            if not self.ndb.stored_msg:
                self.ndb.stored_msg = []
            self.ndb.stored_msg.append(text)


class TestPlayerClass(Player):
    def msg(self, text="", **kwargs):
        "test message"
        if not self.ndb.stored_msg:
            self.ndb.stored_msg = []
        self.ndb.stored_msg.append(text)

    def _get_superuser(self):
        "test with superuser flag"
        return self.ndb.is_superuser
    is_superuser = property(_get_superuser)


class CommandTest(TestCase):
    """
    Tests a command
    """
    CID = 0 # we must set a different CID in every test to avoid unique-name collisions creating the objects
    def setUp(self):
        "sets up testing environment"
        #print "creating player %i: %s" % (self.CID, self.__class__.__name__)
        self.player = create.create_player("TestPlayer%i" % self.CID, "test@test.com", "testpassword", typeclass=TestPlayerClass)
        self.player2 = create.create_player("TestPlayer%ib" % self.CID, "test@test.com", "testpassword", typeclass=TestPlayerClass)
        self.room1 = create.create_object("src.objects.objects.Room", key="Room%i"%self.CID, nohome=True)
        self.room1.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room1.id # we must have a default home
        self.room2 = create.create_object("src.objects.objects.Room", key="Room%ib" % self.CID)
        self.obj1 = create.create_object(TestObjectClass, key="Obj%i" % self.CID, location=self.room1, home=self.room1)
        self.obj2 = create.create_object(TestObjectClass, key="Obj%ib" % self.CID, location=self.room1, home=self.room1)
        self.char1 = create.create_object(TestCharacterClass, key="Char%i" % self.CID, location=self.room1, home=self.room1)
        self.char1.permissions.add("Immortals")
        self.char2 = create.create_object(TestCharacterClass, key="Char%ib" % self.CID, location=self.room1, home=self.room1)
        self.char1.player = self.player
        self.char2.player = self.player2
        self.script = create.create_script("src.scripts.scripts.Script", key="Script%i" % self.CID)
        self.player.permissions.add("Immortals")

        # set up a fake session

        global SESSIONS
        session = ServerSession()
        session.init_session("telnet", ("localhost", "testmode"), SESSIONS)
        session.sessid = self.CID
        SESSIONS.portal_connect(session.get_sync_data())
        SESSIONS.login(SESSIONS.session_from_sessid(self.CID), self.player, testmode=True)


    def call(self, cmdobj, args, msg=None, cmdset=None, noansi=True, caller=None):
        """
        Test a command by assigning all the needed
        properties to cmdobj and  running
            cmdobj.at_pre_cmd()
            cmdobj.parse()
            cmdobj.func()
            cmdobj.at_post_cmd()
        The msgreturn value is compared to eventual
        output sent to caller.msg in the game
        """
        cmdobj.caller = caller if caller else self.char1
        #print "call:", cmdobj.key, cmdobj.caller, caller if caller else cmdobj.caller.player
        #print "perms:", cmdobj.caller.permissions.all()
        cmdobj.cmdstring = cmdobj.key
        cmdobj.args = args
        cmdobj.cmdset = cmdset
        cmdobj.sessid = self.CID
        cmdobj.session = SESSIONS.session_from_sessid(self.CID)
        cmdobj.player = self.player
        cmdobj.raw_string = cmdobj.key + " " + args
        cmdobj.obj = caller if caller else self.char1
        # test
        self.char1.player.ndb.stored_msg = []
        cmdobj.at_pre_cmd()
        cmdobj.parse()
        cmdobj.func()
        cmdobj.at_post_cmd()
        # clean out prettytable sugar
        stored_msg = self.char1.player.ndb.stored_msg if self.char1.player else self.char1.ndb.stored_msg
        returned_msg = "|".join(_RE.sub("", mess) for mess in stored_msg)
        #returned_msg = "|".join(self.char1.player.ndb.stored_msg)
        returned_msg = ansi.parse_ansi(returned_msg, strip_ansi=noansi).strip()
        if msg != None:
            if msg == "" and returned_msg or not returned_msg.startswith(msg.strip()):
                sep1 = "\n" + "="*30 + "Wanted message" + "="*34 + "\n"
                sep2 = "\n" + "="*30 + "Returned message" + "="*32 + "\n"
                sep3 = "\n" + "="*78
                retval = sep1 + msg.strip() + sep2 + returned_msg + sep3
                raise AssertionError(retval)

#------------------------------------------------------------
# Individual module Tests
#------------------------------------------------------------

from src.commands.default import general
class TestGeneral(CommandTest):
    CID = 1

    def test_cmds(self):
        self.call(general.CmdLook(), "here", "Room1\n room_desc")
        self.call(general.CmdHome(), "", "You are already home")
        self.call(general.CmdInventory(), "", "You are not carrying anything.")
        self.call(general.CmdPose(), "looks around", "Char1 looks around")
        self.call(general.CmdHome(), "", "You are already home")
        self.call(general.CmdNick(), "testalias = testaliasedstring1", "Nick set:")
        self.call(general.CmdNick(), "/player testalias = testaliasedstring2", "Nick set:")
        self.call(general.CmdNick(), "/object testalias = testaliasedstring3", "Nick set:")
        self.assertEqual(u"testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEqual(u"testaliasedstring2", self.char1.nicks.get("testalias", category="player"))
        self.assertEqual(u"testaliasedstring3", self.char1.nicks.get("testalias", category="object"))
        self.call(general.CmdGet(), "Obj1", "You pick up Obj1.")
        self.call(general.CmdDrop(), "Obj1", "You drop Obj1.")
        self.call(general.CmdSay(), "Testing", "You say, \"Testing\"")
        self.call(general.CmdAccess(), "", "Permission Hierarchy (climbing):")


from src.commands.default import help
from src.commands.default.cmdset_character import CharacterCmdSet
class TestHelp(CommandTest):
    CID = 2
    def test_cmds(self):
        self.call(help.CmdHelp(), "", "Command help entries", cmdset=CharacterCmdSet())
        self.call(help.CmdSetHelp(), "testhelp, General = This is a test", "Topic 'testhelp' was successfully created.")
        self.call(help.CmdHelp(), "testhelp", "Help topic for testhelp", cmdset=CharacterCmdSet())


from src.commands.default import system
class TestSystem(CommandTest):
    CID = 3
    def test_cmds(self):
        # we are not testing CmdReload, CmdReset and CmdShutdown, CmdService or CmdTime
        # since the server is not running during these tests.
        self.call(system.CmdPy(), "1+2", ">>> 1+2|<<< 3")
        self.call(system.CmdScripts(), "", "dbref ")
        self.call(system.CmdObjects(), "", "Object subtype totals")
        self.call(system.CmdAbout(), "", None)
        self.call(system.CmdServerLoad(), "", "Server CPU and Memory load:")


from src.commands.default import admin
class TestAdmin(CommandTest):
    CID = 4
    def test_cmds(self):
        # not testing CmdBoot, CmdDelPlayer, CmdNewPassword
        self.call(admin.CmdEmit(), "Char4b = Test", "Emitted to Char4b:\nTest")
        self.call(admin.CmdPerm(), "Obj4 = Builders", "Permission 'Builders' given to Obj4 (the Object/Character).")
        self.call(admin.CmdWall(), "Test", "Announcing to all connected players ...")
        self.call(admin.CmdPerm(), "Char4b = Builders","Permission 'Builders' given to Char4b (the Object/Character).")
        self.call(admin.CmdBan(), "Char4", "NameBan char4 was added.")


from src.commands.default import player
class TestPlayer(CommandTest):
   CID = 5
   def test_cmds(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(player.CmdOOCLook(), "", "You are outofcharacter (OOC).", caller=self.player)
        if settings.MULTISESSION_MODE == 2:
            self.call(player.CmdOOCLook(), "", "Account TestPlayer5 (you are OutofCharacter)", caller=self.player)
        self.call(player.CmdOOC(), "", "You are already", caller=self.player)
        self.call(player.CmdIC(), "Char5","You become Char5.", caller=self.player)
        self.call(player.CmdPassword(), "testpassword = testpassword", "Password changed.", caller=self.player)
        self.call(player.CmdEncoding(), "", "Default encoding:", caller=self.player)
        self.call(player.CmdWho(), "", "Players:", caller=self.player)
        self.call(player.CmdQuit(), "", "Quitting. Hope to see you soon again.", caller=self.player)
        self.call(player.CmdSessions(), "", "Your current session(s):", caller=self.player)
        self.call(player.CmdColorTest(), "ansi", "ANSI colors:", caller=self.player)
        self.call(player.CmdCharCreate(), "Test1=Test char","Created new character Test1. Use @ic Test1 to enter the game", caller=self.player)
        self.call(player.CmdQuell(), "", "Quelling to current puppet's permissions (immortals).", caller=self.player)


from src.commands.default import building
class TestBuilding(CommandTest):
    CID = 6
    def test_cmds(self):
        self.call(building.CmdCreate(), "/drop TestObj1", "You create a new Object: TestObj1.")
        self.call(building.CmdExamine(), "TestObj1", "Name/key: TestObj1")
        self.call(building.CmdSetObjAlias(), "TestObj1 = TestObj1b","Alias(es) for 'TestObj1' set to testobj1b.")
        self.call(building.CmdCopy(), "TestObj1 = TestObj2;TestObj2b, TestObj3;TestObj3b", "Copied TestObj1 to 'TestObj3' (aliases: ['TestObj3b']")
        self.call(building.CmdSetAttribute(), "Obj6/test1=\"value1\"", "Created attribute Obj6/test1 = \"value1\"")
        self.call(building.CmdSetAttribute(), "Obj6b/test2=\"value2\"", "Created attribute Obj6b/test2 = \"value2\"")
        self.call(building.CmdMvAttr(), "Obj6b/test2 = Obj6/test3", "Moving Obj6b/test2 (with value value2) ...\nMoved Obj6b.test2")
        self.call(building.CmdCpAttr(), "Obj6/test1 = Obj6b/test3", "Copying Obj6/test1 (with value value1) ...\nCopied Obj6.test1")
        self.call(building.CmdName(), "Obj6b=Obj6c", "Object's name changed to 'Obj6c'.")
        self.call(building.CmdDesc(), "Obj6c=TestDesc", "The description was set on Obj6c.")
        self.call(building.CmdWipe(), "Obj6c/test2/test3", "Wiped attributes test2,test3 on Obj6c.")
        self.call(building.CmdDestroy(), "TestObj1","TestObj1 was destroyed.")
        self.call(building.CmdDig(), "TestRoom1=testroom;tr,back;b", "Created room TestRoom1")
        self.call(building.CmdTunnel(), "n = TestRoom2;test2", "Created room TestRoom2")
        self.call(building.CmdOpen(), "TestExit1=Room6b", "Created new Exit 'TestExit1' from Room6 to Room6b")
        self.call(building.CmdLink(),"TestExit1 = TestRoom1","Link created TestExit1 > TestRoom1 (one way).")
        self.call(building.CmdUnLink(), "TestExit1", "Former exit TestExit1 no longer links anywhere.")
        self.call(building.CmdSetHome(), "Obj6 = Room6b", "Obj6's home location was changed from Room6")
        self.call(building.CmdListCmdSets(), "", "<DefaultCharacter (Union, prio 0, perm)>:")
        self.call(building.CmdTypeclass(), "Obj6 = src.objects.objects.Exit",
                "Obj6 changed typeclass from src.commands.default.tests.TestObjectClass to src.objects.objects.Exit")
        self.call(building.CmdLock(), "Obj6 = test:perm(Immortals)", "Added lock 'test:perm(Immortals)' to Obj6.")
        self.call(building.CmdFind(), "TestRoom1", "One Match")
        self.call(building.CmdScript(), "Obj6 = src.scripts.scripts.Script", "Script src.scripts.scripts.Script successfully added")
        self.call(building.CmdTeleport(), "TestRoom1", "TestRoom1\nExits: back|Teleported to TestRoom1.")


from src.commands.default import comms
class TestComms(CommandTest):
    CID = 7
    def test_cmds(self):
        # not testing the irc/imc2/rss commands here since testing happens offline
        self.call(comms.CmdChannelCreate(), "testchan;test=Test Channel", "Created channel testchan and connected to it.")
        self.call(comms.CmdAddCom(), "tc = testchan", "You are already connected to channel testchan. You can now")
        self.call(comms.CmdDelCom(), "tc",  "Your alias 'tc' for channel testchan was cleared.")
        self.call(comms.CmdChannels(), "" ,"Available channels (use comlist,addcom and delcom to manage")
        self.call(comms.CmdAllCom(), "", "Available channels (use comlist,addcom and delcom to manage")
        self.call(comms.CmdClock(), "testchan=send:all()", "Lock(s) applied. Current locks on testchan:")
        self.call(comms.CmdCdesc(), "testchan = Test Channel", "Description of channel 'testchan' set to 'Test Channel'.")
        self.call(comms.CmdCemit(), "testchan = Test Message", "[testchan] Test Message|Sent to channel testchan: Test Message")
        self.call(comms.CmdCWho(), "testchan", "Channel subscriptions\ntestchan:\n  TestPlayer7")
        self.call(comms.CmdPage(), "TestPlayer7b = Test", "TestPlayer7b is offline. They will see your message if they list their pages later.|You paged TestPlayer7b with: 'Test'.")
        self.call(comms.CmdCBoot(), "", "Usage: @cboot[/quiet] <channel> = <player> [:reason]") # noone else connected to boot
        self.call(comms.CmdCdestroy(), "testchan" ,"[testchan] TestPlayer7: testchan is being destroyed. Make sure to change your aliases.|Channel 'testchan' was destroyed.")


from src.commands.default import batchprocess
class TestBatchProcess(CommandTest):
    CID = 8
    def test_cmds(self):
        # cannot test batchcode here, it must run inside the server process
        self.call(batchprocess.CmdBatchCommands(), "examples.batch_cmds", "Running Batchcommand processor  Automatic mode for examples.batch_cmds")
        #self.call(batchprocess.CmdBatchCode(), "examples.batch_code", "")
