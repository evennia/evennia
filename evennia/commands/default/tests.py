# -*- coding: utf-8 -*-
"""
 ** OBS - this is not a normal command module! **
 ** You cannot import anything in this module as a command! **

This is part of the Evennia unittest framework, for testing the
stability and integrity of the codebase during updates. This module
test the default command set. It is instantiated by the
evennia/objects/tests.py module, which in turn is run by as part of the
main test suite started with
 > python game/manage.py test.

"""

import re
import types
import datetime

from django.conf import settings
from mock import Mock, mock

from evennia.commands.default.cmdset_character import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from evennia.commands.default import help, general, system, admin, account, building, batchprocess, comms, unloggedin
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.command import Command, InterruptCommand
from evennia.utils import ansi, utils, gametime
from evennia.server.sessionhandler import SESSIONS
from evennia import search_object
from evennia import DefaultObject, DefaultCharacter
from evennia.prototypes import prototypes as protlib


# set up signal here since we are not starting the server

_RE = re.compile(r"^\+|-+\+|\+-+|--+|\|(?:\s|$)", re.MULTILINE)


# ------------------------------------------------------------
# Command testing
# ------------------------------------------------------------


class CommandTest(EvenniaTest):
    """
    Tests a command
    """
    def call(self, cmdobj, args, msg=None, cmdset=None, noansi=True, caller=None,
             receiver=None, cmdstring=None, obj=None, inputs=None):
        """
        Test a command by assigning all the needed
        properties to cmdobj and  running
            cmdobj.at_pre_cmd()
            cmdobj.parse()
            cmdobj.func()
            cmdobj.at_post_cmd()
        The msgreturn value is compared to eventual
        output sent to caller.msg in the game

        Returns:
            msg (str): The received message that was sent to the caller.

        """
        caller = caller if caller else self.char1
        receiver = receiver if receiver else caller
        cmdobj.caller = caller
        cmdobj.cmdname = cmdstring if cmdstring else cmdobj.key
        cmdobj.raw_cmdname = cmdobj.cmdname
        cmdobj.cmdstring = cmdobj.cmdname  # deprecated
        cmdobj.args = args
        cmdobj.cmdset = cmdset
        cmdobj.session = SESSIONS.session_from_sessid(1)
        cmdobj.account = self.account
        cmdobj.raw_string = cmdobj.key + " " + args
        cmdobj.obj = obj or (caller if caller else self.char1)
        # test
        old_msg = receiver.msg
        inputs = inputs or []

        try:
            receiver.msg = Mock()
            if cmdobj.at_pre_cmd():
                return
            cmdobj.parse()
            ret = cmdobj.func()

            # handle func's with yield in them (generators)
            if isinstance(ret, types.GeneratorType):
                while True:
                    try:
                        inp = inputs.pop() if inputs else None
                        if inp:
                            try:
                                ret.send(inp)
                            except TypeError:
                                next(ret)
                                ret = ret.send(inp)
                        else:
                            next(ret)
                    except StopIteration:
                        break

            cmdobj.at_post_cmd()
        except StopIteration:
            pass
        except InterruptCommand:
            pass

        # clean out evtable sugar. We only operate on text-type
        stored_msg = [args[0] if args and args[0] else kwargs.get("text", utils.to_str(kwargs, force_string=True))
                      for name, args, kwargs in receiver.msg.mock_calls]
        # Get the first element of a tuple if msg received a tuple instead of a string
        stored_msg = [smsg[0] if isinstance(smsg, tuple) else smsg for smsg in stored_msg]
        if msg is not None:
            # set our separator for returned messages based on parsing ansi or not
            msg_sep = "|" if noansi else "||"
            # Have to strip ansi for each returned message for the regex to handle it correctly
            returned_msg = msg_sep.join(_RE.sub("", ansi.parse_ansi(mess, strip_ansi=noansi))
                                        for mess in stored_msg).strip()
            if msg == "" and returned_msg or not returned_msg.startswith(msg.strip()):
                sep1 = "\n" + "=" * 30 + "Wanted message" + "=" * 34 + "\n"
                sep2 = "\n" + "=" * 30 + "Returned message" + "=" * 32 + "\n"
                sep3 = "\n" + "=" * 78
                retval = sep1 + msg.strip() + sep2 + returned_msg + sep3
                raise AssertionError(retval)
        else:
            returned_msg = "\n".join(str(msg) for msg in stored_msg)
            returned_msg = ansi.parse_ansi(returned_msg, strip_ansi=noansi).strip()
        receiver.msg = old_msg

        return returned_msg

# ------------------------------------------------------------
# Individual module Tests
# ------------------------------------------------------------


class TestGeneral(CommandTest):
    def test_look(self):
        self.call(general.CmdLook(), "here", "Room(#1)\nroom_desc")

    def test_home(self):
        self.call(general.CmdHome(), "", "You are already home")

    def test_inventory(self):
        self.call(general.CmdInventory(), "", "You are not carrying anything.")

    def test_pose(self):
        self.call(general.CmdPose(), "looks around", "Char looks around")

    def test_nick(self):
        self.call(general.CmdNick(), "testalias = testaliasedstring1",
                "Inputline-nick 'testalias' mapped to 'testaliasedstring1'.")
        self.call(general.CmdNick(), "/account testalias = testaliasedstring2",
                "Account-nick 'testalias' mapped to 'testaliasedstring2'.")
        self.call(general.CmdNick(), "/object testalias = testaliasedstring3",
                "Object-nick 'testalias' mapped to 'testaliasedstring3'.")
        self.assertEqual("testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEqual("testaliasedstring2", self.char1.nicks.get("testalias", category="account"))
        self.assertEqual(None, self.char1.account.nicks.get("testalias", category="account"))
        self.assertEqual("testaliasedstring3", self.char1.nicks.get("testalias", category="object"))

    def test_get_and_drop(self):
        self.call(general.CmdGet(), "Obj", "You pick up Obj.")
        self.call(general.CmdDrop(), "Obj", "You drop Obj.")

    def test_give(self):
        self.call(general.CmdGive(), "Obj to Char2", "You aren't carrying Obj.")
        self.call(general.CmdGive(), "Obj = Char2", "You aren't carrying Obj.")
        self.call(general.CmdGet(), "Obj", "You pick up Obj.")
        self.call(general.CmdGive(), "Obj to Char2", "You give")
        self.call(general.CmdGive(), "Obj = Char", "You give", caller=self.char2)

    def test_mux_command(self):

        class CmdTest(MuxCommand):
            key = 'test'
            switch_options = ('test', 'testswitch', 'testswitch2')

            def func(self):
                self.msg("Switches matched: {}".format(self.switches))

        self.call(CmdTest(), "/test/testswitch/testswitch2", "Switches matched: ['test', 'testswitch', 'testswitch2']")
        self.call(CmdTest(), "/test", "Switches matched: ['test']")
        self.call(CmdTest(), "/test/testswitch", "Switches matched: ['test', 'testswitch']")
        self.call(CmdTest(), "/testswitch/testswitch2", "Switches matched: ['testswitch', 'testswitch2']")
        self.call(CmdTest(), "/testswitch", "Switches matched: ['testswitch']")
        self.call(CmdTest(), "/testswitch2", "Switches matched: ['testswitch2']")
        self.call(CmdTest(), "/t", "test: Ambiguous switch supplied: "
                                   "Did you mean /test or /testswitch or /testswitch2?|Switches matched: []")
        self.call(CmdTest(), "/tests", "test: Ambiguous switch supplied: "
                                       "Did you mean /testswitch or /testswitch2?|Switches matched: []")

    def test_say(self):
        self.call(general.CmdSay(), "Testing", "You say, \"Testing\"")

    def test_whisper(self):
        self.call(general.CmdWhisper(), "Obj = Testing", "You whisper to Obj, \"Testing\"", caller=self.char2)

    def test_access(self):
        self.call(general.CmdAccess(), "", "Permission Hierarchy (climbing):")


class TestHelp(CommandTest):
    def test_help(self):
        self.call(help.CmdHelp(), "", "Command help entries", cmdset=CharacterCmdSet())

    def test_set_help(self):
        self.call(help.CmdSetHelp(), "testhelp, General = This is a test", "Topic 'testhelp' was successfully created.")
        self.call(help.CmdHelp(), "testhelp", "Help for testhelp", cmdset=CharacterCmdSet())


class TestSystem(CommandTest):
    def test_py(self):
        # we are not testing CmdReload, CmdReset and CmdShutdown, CmdService or CmdTime
        # since the server is not running during these tests.
        self.call(system.CmdPy(), "1+2", ">>> 1+2|3")

    def test_scripts(self):
        self.call(system.CmdScripts(), "", "dbref ")

    def test_objects(self):
        self.call(system.CmdObjects(), "", "Object subtype totals")

    def test_about(self):
        self.call(system.CmdAbout(), "", None)

    def test_server_load(self):
        self.call(system.CmdServerLoad(), "", "Server CPU and Memory load:")


class TestAdmin(CommandTest):
    def test_emit(self):
        self.call(admin.CmdEmit(), "Char2 = Test", "Emitted to Char2:\nTest")

    def test_perm(self):
        self.call(admin.CmdPerm(), "Obj = Builder", "Permission 'Builder' given to Obj (the Object/Character).")
        self.call(admin.CmdPerm(), "Char2 = Builder", "Permission 'Builder' given to Char2 (the Object/Character).")

    def test_wall(self):
        self.call(admin.CmdWall(), "Test", "Announcing to all connected sessions ...")

    def test_ban(self):
        self.call(admin.CmdBan(), "Char", "Name-Ban char was added.")


class TestAccount(CommandTest):

    def test_ooc_look(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(account.CmdOOCLook(), "", "You are out-of-character (OOC).", caller=self.account)
        if settings.MULTISESSION_MODE == 2:
            self.call(account.CmdOOCLook(), "", "Account TestAccount (you are OutofCharacter)", caller=self.account)

    def test_ooc(self):
        self.call(account.CmdOOC(), "", "You go OOC.", caller=self.account)

    def test_ic(self):
        self.account.unpuppet_object(self.session)
        self.call(account.CmdIC(), "Char", "You become Char.", caller=self.account, receiver=self.char1)

    def test_password(self):
        self.call(account.CmdPassword(), "testpassword = testpassword", "Password changed.", caller=self.account)

    def test_option(self):
        self.call(account.CmdOption(), "", "Client settings", caller=self.account)

    def test_who(self):
        self.call(account.CmdWho(), "", "Accounts:", caller=self.account)

    def test_quit(self):
        self.call(account.CmdQuit(), "", "Quitting. Hope to see you again, soon.", caller=self.account)

    def test_sessions(self):
        self.call(account.CmdSessions(), "", "Your current session(s):", caller=self.account)

    def test_color_test(self):
        self.call(account.CmdColorTest(), "ansi", "ANSI colors:", caller=self.account)

    def test_char_create(self):
        self.call(account.CmdCharCreate(), "Test1=Test char",
                  "Created new character Test1. Use @ic Test1 to enter the game", caller=self.account)

    def test_quell(self):
        self.call(account.CmdQuell(), "", "Quelling to current puppet's permissions (developer).", caller=self.account)


class TestBuilding(CommandTest):
    def test_create(self):
        name = settings.BASE_OBJECT_TYPECLASS.rsplit('.', 1)[1]
        self.call(building.CmdCreate(), "/d TestObj1",   # /d switch is abbreviated form of /drop
                  "You create a new %s: TestObj1." % name)

    def test_examine(self):
        self.call(building.CmdExamine(), "Obj", "Name/key: Obj")

    def test_set_obj_alias(self):
        self.call(building.CmdSetObjAlias(), "Obj =", "Cleared aliases from Obj(#4)")
        self.call(building.CmdSetObjAlias(), "Obj = TestObj1b", "Alias(es) for 'Obj(#4)' set to 'testobj1b'.")

    def test_copy(self):
        self.call(building.CmdCopy(), "Obj = TestObj2;TestObj2b, TestObj3;TestObj3b",
                  "Copied Obj to 'TestObj3' (aliases: ['TestObj3b']")

    def test_attribute_commands(self):
        self.call(building.CmdSetAttribute(), "Obj/test1=\"value1\"", "Created attribute Obj/test1 = 'value1'")
        self.call(building.CmdSetAttribute(), "Obj2/test2=\"value2\"", "Created attribute Obj2/test2 = 'value2'")
        self.call(building.CmdMvAttr(), "Obj2/test2 = Obj/test3", "Moved Obj2.test2 -> Obj.test3")
        self.call(building.CmdCpAttr(), "Obj/test1 = Obj2/test3", "Copied Obj.test1 -> Obj2.test3")
        self.call(building.CmdWipe(), "Obj2/test2/test3", "Wiped attributes test2,test3 on Obj2.")

    def test_name(self):
        self.call(building.CmdName(), "Obj2=Obj3", "Object's name changed to 'Obj3'.")

    def test_desc(self):
        self.call(building.CmdDesc(), "Obj2=TestDesc", "The description was set on Obj2(#5).")

    def test_wipe(self):
        confirm = building.CmdDestroy.confirm
        building.CmdDestroy.confirm = False
        self.call(building.CmdDestroy(), "Obj", "Obj was destroyed.")
        building.CmdDestroy.confirm = confirm

    def test_dig(self):
        self.call(building.CmdDig(), "TestRoom1=testroom;tr,back;b", "Created room TestRoom1")

    def test_tunnel(self):
        self.call(building.CmdTunnel(), "n = TestRoom2;test2", "Created room TestRoom2")

    def test_tunnel_exit_typeclass(self):
        self.call(building.CmdTunnel(), "n:evennia.objects.objects.DefaultExit = TestRoom3", "Created room TestRoom3")

    def test_exit_commands(self):
        self.call(building.CmdOpen(), "TestExit1=Room2", "Created new Exit 'TestExit1' from Room to Room2")
        self.call(building.CmdLink(), "TestExit1=Room", "Link created TestExit1 -> Room (one way).")
        self.call(building.CmdUnLink(), "TestExit1", "Former exit TestExit1 no longer links anywhere.")

    def test_set_home(self):
        self.call(building.CmdSetHome(), "Obj = Room2", "Obj's home location was changed from Room")

    def test_list_cmdsets(self):
        self.call(building.CmdListCmdSets(), "", "<DefaultCharacter (Union, prio 0, perm)>:")

    def test_typeclass(self):
        self.call(building.CmdTypeclass(), "Obj = evennia.objects.objects.DefaultExit",
                  "Obj changed typeclass from evennia.objects.objects.DefaultObject "
                  "to evennia.objects.objects.DefaultExit.")

    def test_lock(self):
        self.call(building.CmdLock(), "Obj = test:perm(Developer)", "Added lock 'test:perm(Developer)' to Obj.")

    def test_find(self):
        self.call(building.CmdFind(), "oom2", "One Match")
        expect = "One Match(#1-#7, loc):\n   " +\
                 "Char2(#7) - evennia.objects.objects.DefaultCharacter (location: Room(#1))"
        self.call(building.CmdFind(), "Char2", expect, cmdstring="locate")
        self.call(building.CmdFind(), "/ex Char2",  # /ex is an ambiguous switch
                  "locate: Ambiguous switch supplied: Did you mean /exit or /exact?|" + expect,
                  cmdstring="locate")
        self.call(building.CmdFind(), "Char2", expect, cmdstring="@locate")
        self.call(building.CmdFind(), "/l Char2", expect, cmdstring="find")  # /l switch is abbreviated form of /loc
        self.call(building.CmdFind(), "Char2", "One Match", cmdstring="@find")
        self.call(building.CmdFind(), "/startswith Room2", "One Match")

    def test_script(self):
        self.call(building.CmdScript(), "Obj = scripts.Script", "Script scripts.Script successfully added")

    def test_teleport(self):
        self.call(building.CmdTeleport(), "/quiet Room2", "Room2(#2)\n|Teleported to Room2.")
        self.call(building.CmdTeleport(), "/t",  # /t switch is abbreviated form of /tonone
                  "Cannot teleport a puppeted object (Char, puppeted by TestAccount(account 1)) to a None-location.")
        self.call(building.CmdTeleport(), "/l Room2",  # /l switch is abbreviated form of /loc
                  "Destination has no location.")
        self.call(building.CmdTeleport(), "/q me to Room2",  # /q switch is abbreviated form of /quiet
                  "Char is already at Room2.")

    def test_spawn(self):
        def getObject(commandTest, objKeyStr):
            # A helper function to get a spawned object and
            # check that it exists in the process.
            query = search_object(objKeyStr)
            commandTest.assertIsNotNone(query)
            commandTest.assertTrue(bool(query))
            obj = query[0]
            commandTest.assertIsNotNone(obj)
            return obj

        # Tests "@spawn" without any arguments.
        self.call(building.CmdSpawn(), " ", "Usage: @spawn")

        # Tests "@spawn <prototype_dictionary>" without specifying location.

        self.call(building.CmdSpawn(),
                  "/save {'prototype_key': 'testprot', 'key':'Test Char', "
                  "'typeclass':'evennia.objects.objects.DefaultCharacter'}",
                  "Saved prototype: testprot", inputs=['y'])

        self.call(building.CmdSpawn(), "/list", "Key ")

        self.call(building.CmdSpawn(), 'testprot', "Spawned Test Char")
        # Tests that the spawned object's location is the same as the caharacter's location, since
        # we did not specify it.
        testchar = getObject(self, "Test Char")
        self.assertEqual(testchar.location, self.char1.location)
        testchar.delete()

        # Test "@spawn <prototype_dictionary>" with a location other than the character's.
        spawnLoc = self.room2
        if spawnLoc == self.char1.location:
            # Just to make sure we use a different location, in case someone changes
            # char1's default location in the future...
            spawnLoc = self.room1

        self.call(building.CmdSpawn(),
                "{'prototype_key':'GOBLIN', 'typeclass':'evennia.objects.objects.DefaultCharacter', "
                "'key':'goblin', 'location':'%s'}" % spawnLoc.dbref, "Spawned goblin")
        goblin = getObject(self, "goblin")
        # Tests that the spawned object's type is a DefaultCharacter.
        self.assertIsInstance(goblin, DefaultCharacter)
        self.assertEqual(goblin.location, spawnLoc)

        goblin.delete()

        # create prototype
        protlib.create_prototype(**{'key': 'Ball',
                                    'typeclass': 'evennia.objects.objects.DefaultCharacter',
                                    'prototype_key': 'testball'})

        # Tests "@spawn <prototype_name>"
        self.call(building.CmdSpawn(), "testball", "Spawned Ball")

        ball = getObject(self, "Ball")
        self.assertEqual(ball.location, self.char1.location)
        self.assertIsInstance(ball, DefaultObject)
        ball.delete()

        # Tests "@spawn/n ..." without specifying a location.
        # Location should be "None".
        self.call(building.CmdSpawn(), "/n 'BALL'", "Spawned Ball")   # /n switch is abbreviated form of /noloc
        ball = getObject(self, "Ball")
        self.assertIsNone(ball.location)
        ball.delete()

        self.call(building.CmdSpawn(),
                "/noloc {'prototype_parent':'TESTBALL', 'prototype_key': 'testball', 'location':'%s'}"
                % spawnLoc.dbref, "Error: Prototype testball tries to parent itself.")

        # Tests "@spawn/noloc ...", but DO specify a location.
        # Location should be the specified location.
        self.call(building.CmdSpawn(),
                "/noloc {'prototype_parent':'TESTBALL', 'key': 'Ball', 'prototype_key': 'foo', 'location':'%s'}"
                  % spawnLoc.dbref, "Spawned Ball")
        ball = getObject(self, "Ball")
        self.assertEqual(ball.location, spawnLoc)
        ball.delete()

        # test calling spawn with an invalid prototype.
        self.call(building.CmdSpawn(), "'NO_EXIST'", "No prototype named 'NO_EXIST'")

        # Test listing commands
        self.call(building.CmdSpawn(), "/list", "Key ")


class TestComms(CommandTest):

    def setUp(self):
        super(CommandTest, self).setUp()
        self.call(comms.CmdChannelCreate(), "testchan;test=Test Channel",
                  "Created channel testchan and connected to it.", receiver=self.account)

    def test_toggle_com(self):
        self.call(comms.CmdAddCom(), "tc = testchan",
                  "You are already connected to channel testchan. You can now", receiver=self.account)
        self.call(comms.CmdDelCom(), "tc", "Your alias 'tc' for channel testchan was cleared.", receiver=self.account)

    def test_channels(self):
        self.call(comms.CmdChannels(), "",
                  "Available channels (use comlist,addcom and delcom to manage", receiver=self.account)

    def test_all_com(self):
        self.call(comms.CmdAllCom(), "",
                  "Available channels (use comlist,addcom and delcom to manage", receiver=self.account)

    def test_clock(self):
        self.call(comms.CmdClock(),
                  "testchan=send:all()", "Lock(s) applied. Current locks on testchan:", receiver=self.account)

    def test_cdesc(self):
        self.call(comms.CmdCdesc(), "testchan = Test Channel",
                  "Description of channel 'testchan' set to 'Test Channel'.", receiver=self.account)

    def test_cemit(self):
        self.call(comms.CmdCemit(), "testchan = Test Message",
                  "[testchan] Test Message|Sent to channel testchan: Test Message", receiver=self.account)

    def test_cwho(self):
        self.call(comms.CmdCWho(), "testchan", "Channel subscriptions\ntestchan:\n  TestAccount", receiver=self.account)

    def test_page(self):
        self.call(comms.CmdPage(), "TestAccount2 = Test",
                  "TestAccount2 is offline. They will see your message if they list their pages later."
                  "|You paged TestAccount2 with: 'Test'.", receiver=self.account)

    def test_cboot(self):
        # No one else connected to boot
        self.call(comms.CmdCBoot(), "", "Usage: @cboot[/quiet] <channel> = <account> [:reason]", receiver=self.account)

    def test_cdestroy(self):
        self.call(comms.CmdCdestroy(), "testchan",
                  "[testchan] TestAccount: testchan is being destroyed. Make sure to change your aliases."
                  "|Channel 'testchan' was destroyed.", receiver=self.account)


class TestBatchProcess(CommandTest):
    def test_batch_commands(self):
        # cannot test batchcode here, it must run inside the server process
        self.call(batchprocess.CmdBatchCommands(), "example_batch_cmds",
                "Running Batch-command processor - Automatic mode for example_batch_cmds")
        # we make sure to delete the button again here to stop the running reactor
        confirm = building.CmdDestroy.confirm
        building.CmdDestroy.confirm = False
        self.call(building.CmdDestroy(), "button", "button was destroyed.")
        building.CmdDestroy.confirm = confirm


class CmdInterrupt(Command):

    key = "interrupt"

    def parse(self):
        raise InterruptCommand

    def func(self):
        self.msg("in func")


class TestInterruptCommand(CommandTest):
    def test_interrupt_command(self):
        ret = self.call(CmdInterrupt(), "")
        self.assertEqual(ret, "")


class TestUnconnectedCommand(CommandTest):
    def test_info_command(self):
        # instead of using SERVER_START_TIME (0), we use 86400 because Windows won't let us use anything lower
        gametime.SERVER_START_TIME = 86400
        expected = "## BEGIN INFO 1.1\nName: %s\nUptime: %s\nConnected: %d\nVersion: Evennia %s\n## END INFO" % (
                        settings.SERVERNAME,
                        datetime.datetime.fromtimestamp(gametime.SERVER_START_TIME).ctime(),
                        SESSIONS.account_count(), utils.get_evennia_version())
        self.call(unloggedin.CmdUnconnectedInfo(), "", expected)
        del gametime.SERVER_START_TIME
