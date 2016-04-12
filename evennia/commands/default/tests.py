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

from django.conf import settings
from mock import Mock

from evennia.commands.default.cmdset_character import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from evennia.commands.default import help, general, system, admin, player, building, batchprocess, comms
from evennia.utils import ansi
from evennia.server.sessionhandler import SESSIONS


# set up signal here since we are not starting the server

_RE = re.compile(r"^\+|-+\+|\+-+|--*|\|", re.MULTILINE)


# ------------------------------------------------------------
# Command testing
# ------------------------------------------------------------

class CommandTest(EvenniaTest):
    """
    Tests a command
    """

    def call(self, cmdobj, args, msg=None, cmdset=None, noansi=True, caller=None, receiver=None):
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
        caller = caller if caller else self.char1
        receiver = receiver if receiver else caller
        cmdobj.caller = caller
        cmdobj.cmdstring = cmdobj.key
        cmdobj.args = args
        cmdobj.cmdset = cmdset
        cmdobj.session = SESSIONS.session_from_sessid(1)
        cmdobj.player = self.player
        cmdobj.raw_string = cmdobj.key + " " + args
        cmdobj.obj = caller if caller else self.char1
        # test
        old_msg = receiver.msg
        try:
            receiver.msg = Mock()
            cmdobj.at_pre_cmd()
            cmdobj.parse()
            cmdobj.func()
            cmdobj.at_post_cmd()
            # clean out prettytable sugar
            stored_msg = [args[0] for name, args, kwargs in receiver.msg.mock_calls]
            returned_msg = "||".join(_RE.sub("", mess) for mess in stored_msg)
            returned_msg = ansi.parse_ansi(returned_msg, strip_ansi=noansi).strip()
            if msg is not None:
                if msg == "" and returned_msg or not returned_msg.startswith(msg.strip()):
                    sep1 = "\n" + "="*30 + "Wanted message" + "="*34 + "\n"
                    sep2 = "\n" + "="*30 + "Returned message" + "="*32 + "\n"
                    sep3 = "\n" + "="*78
                    retval = sep1 + msg.strip() + sep2 + returned_msg + sep3
                    raise AssertionError(retval)
        finally:
            receiver.msg = old_msg

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
        self.call(general.CmdNick(), "testalias = testaliasedstring1", "Nick set:")
        self.call(general.CmdNick(), "/player testalias = testaliasedstring2", "Nick set:")
        self.call(general.CmdNick(), "/object testalias = testaliasedstring3", "Nick set:")
        self.assertEqual(u"testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEqual(u"testaliasedstring2", self.char1.nicks.get("testalias", category="player"))
        self.assertEqual(u"testaliasedstring3", self.char1.nicks.get("testalias", category="object"))

    def test_get_and_drop(self):
        self.call(general.CmdGet(), "Obj", "You pick up Obj.")
        self.call(general.CmdDrop(), "Obj", "You drop Obj.")

    def test_say(self):
        self.call(general.CmdSay(), "Testing", "You say, \"Testing\"")

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
        self.call(admin.CmdPerm(), "Obj = Builders", "Permission 'Builders' given to Obj (the Object/Character).")
        self.call(admin.CmdPerm(), "Char2 = Builders", "Permission 'Builders' given to Char2 (the Object/Character).")

    def test_wall(self):
        self.call(admin.CmdWall(), "Test", "Announcing to all connected players ...")

    def test_ban(self):
        self.call(admin.CmdBan(), "Char", "NameBan char was added.")


class TestPlayer(CommandTest):

    def test_ooc_look(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(player.CmdOOCLook(), "", "You are outofcharacter (OOC).", caller=self.player)
        if settings.MULTISESSION_MODE == 2:
            self.call(player.CmdOOCLook(), "", "Account TestPlayer (you are OutofCharacter)", caller=self.player)

    def test_ooc(self):
        self.call(player.CmdOOC(), "", "You go OOC.", caller=self.player)

    def test_ic(self):
        self.player.unpuppet_object(self.session)
        self.call(player.CmdIC(), "Char", "You become Char.", caller=self.player, receiver=self.char1)

    def test_password(self):
        self.call(player.CmdPassword(), "testpassword = testpassword", "Password changed.", caller=self.player)

    def test_option(self):
        self.call(player.CmdOption(), "", "Encoding:", caller=self.player)

    def test_who(self):
        self.call(player.CmdWho(), "", "Players:", caller=self.player)

    def test_quit(self):
        self.call(player.CmdQuit(), "", "Quitting. Hope to see you again, soon.", caller=self.player)

    def test_sessions(self):
        self.call(player.CmdSessions(), "", "Your current session(s):", caller=self.player)

    def test_color_test(self):
        self.call(player.CmdColorTest(), "ansi", "ANSI colors:", caller=self.player)

    def test_char_create(self):
        self.call(player.CmdCharCreate(), "Test1=Test char", "Created new character Test1. Use @ic Test1 to enter the game", caller=self.player)

    def test_quell(self):
        self.call(player.CmdQuell(), "", "Quelling to current puppet's permissions (immortals).", caller=self.player)


class TestBuilding(CommandTest):
    def test_create(self):
        name = settings.BASE_OBJECT_TYPECLASS.rsplit('.', 1)[1]
        self.call(building.CmdCreate(), "/drop TestObj1", "You create a new %s: TestObj1." % name)

    def test_examine(self):
        self.call(building.CmdExamine(), "Obj", "Name/key: Obj")

    def test_set_obj_alias(self):
        self.call(building.CmdSetObjAlias(), "Obj = TestObj1b", "Alias(es) for 'Obj(#4)' set to testobj1b.")

    def test_copy(self):
        self.call(building.CmdCopy(), "Obj = TestObj2;TestObj2b, TestObj3;TestObj3b", "Copied Obj to 'TestObj3' (aliases: ['TestObj3b']")

    def test_attribute_commands(self):
        self.call(building.CmdSetAttribute(), "Obj/test1=\"value1\"", "Created attribute Obj/test1 = 'value1'")
        self.call(building.CmdSetAttribute(), "Obj2/test2=\"value2\"", "Created attribute Obj2/test2 = 'value2'")
        self.call(building.CmdMvAttr(), "Obj2/test2 = Obj/test3", "Moved Obj2.test2 > Obj.test3")
        self.call(building.CmdCpAttr(), "Obj/test1 = Obj2/test3", "Copied Obj.test1 > Obj2.test3")
        self.call(building.CmdWipe(), "Obj2/test2/test3", "Wiped attributes test2,test3 on Obj2.")

    def test_name(self):
        self.call(building.CmdName(), "Obj2=Obj3", "Object's name changed to 'Obj3'.")

    def test_desc(self):
        self.call(building.CmdDesc(), "Obj2=TestDesc", "The description was set on Obj2(#5).")

    def test_wipe(self):
        self.call(building.CmdDestroy(), "Obj", "Obj was destroyed.")

    def test_dig(self):
        self.call(building.CmdDig(), "TestRoom1=testroom;tr,back;b", "Created room TestRoom1")

    def test_tunnel(self):
        self.call(building.CmdTunnel(), "n = TestRoom2;test2", "Created room TestRoom2")

    def test_exit_commands(self):
        self.call(building.CmdOpen(), "TestExit1=Room2", "Created new Exit 'TestExit1' from Room to Room2")
        self.call(building.CmdLink(), "TestExit1=Room", "Link created TestExit1 > Room (one way).")
        self.call(building.CmdUnLink(), "TestExit1", "Former exit TestExit1 no longer links anywhere.")

    def test_set_home(self):
        self.call(building.CmdSetHome(), "Obj = Room2", "Obj's home location was changed from Room")

    def test_list_cmdsets(self):
        self.call(building.CmdListCmdSets(), "", "<DefaultCharacter (Union, prio 0, perm)>:")

    def test_typeclass(self):
        self.call(building.CmdTypeclass(), "Obj = evennia.objects.objects.DefaultExit",
                "Obj changed typeclass from evennia.objects.objects.DefaultObject to evennia.objects.objects.DefaultExit.")

    def test_lock(self):
        self.call(building.CmdLock(), "Obj = test:perm(Immortals)", "Added lock 'test:perm(Immortals)' to Obj.")

    def test_find(self):
        self.call(building.CmdFind(), "Room2", "One Match")

    def test_script(self):
        self.call(building.CmdScript(), "Obj = scripts.Script", "Script scripts.Script successfully added")

    def test_teleport(self):
        self.call(building.CmdTeleport(), "Room2", "Room2(#2)\n|Teleported to Room2.")


class TestComms(CommandTest):

    def setUp(self):
        super(CommandTest, self).setUp()
        self.call(comms.CmdChannelCreate(), "testchan;test=Test Channel", "Created channel testchan and connected to it.", receiver=self.player)

    def test_toggle_com(self):
        self.call(comms.CmdAddCom(), "tc = testchan", "You are already connected to channel testchan. You can now", receiver=self.player)
        self.call(comms.CmdDelCom(), "tc",  "Your alias 'tc' for channel testchan was cleared.", receiver=self.player)

    def test_channels(self):
        self.call(comms.CmdChannels(), "" ,"Available channels (use comlist,addcom and delcom to manage", receiver=self.player)

    def test_all_com(self):
        self.call(comms.CmdAllCom(), "", "Available channels (use comlist,addcom and delcom to manage", receiver=self.player)

    def test_clock(self):
        self.call(comms.CmdClock(), "testchan=send:all()", "Lock(s) applied. Current locks on testchan:", receiver=self.player)

    def test_cdesc(self):
        self.call(comms.CmdCdesc(), "testchan = Test Channel", "Description of channel 'testchan' set to 'Test Channel'.", receiver=self.player)

    def test_cemit(self):
        self.call(comms.CmdCemit(), "testchan = Test Message", "[testchan] Test Message|Sent to channel testchan: Test Message", receiver=self.player)

    def test_cwho(self):
        self.call(comms.CmdCWho(), "testchan", "Channel subscriptions\ntestchan:\n  TestPlayer", receiver=self.player)

    def test_page(self):
        self.call(comms.CmdPage(), "TestPlayer2 = Test", "TestPlayer2 is offline. They will see your message if they list their pages later.|You paged TestPlayer2 with: 'Test'.", receiver=self.player)

    def test_cboot(self):
        # No one else connected to boot
        self.call(comms.CmdCBoot(), "", "Usage: @cboot[/quiet] <channel> = <player> [:reason]", receiver=self.player)

    def test_cdestroy(self):
        self.call(comms.CmdCdestroy(), "testchan" ,"[testchan] TestPlayer: testchan is being destroyed. Make sure to change your aliases.|Channel 'testchan' was destroyed.", receiver=self.player)


class TestBatchProcess(CommandTest):
    def test_batch_commands(self):
        # cannot test batchcode here, it must run inside the server process
        self.call(batchprocess.CmdBatchCommands(), "example_batch_cmds", "Running Batchcommand processor  Automatic mode for example_batch_cmds")
        #self.call(batchprocess.CmdBatchCode(), "examples.batch_code", "")

