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
import datetime
from unittest.mock import MagicMock, Mock, patch

from anything import Anything
from django.conf import settings
from django.test import override_settings
from parameterized import parameterized
from twisted.internet import task

from evennia import (
    DefaultCharacter,
    DefaultExit,
    DefaultObject,
    DefaultRoom,
    ObjectDB,
    search_object,
)
from evennia.commands import cmdparser
from evennia.commands.cmdset import CmdSet
from evennia.commands.command import Command, InterruptCommand
from evennia.commands.default import (
    account,
    admin,
    batchprocess,
    building,
    comms,
    general,
)
from evennia.commands.default import help as help_module
from evennia.commands.default import syscommands, system, unloggedin
from evennia.commands.default.cmdset_character import CharacterCmdSet
from evennia.commands.default.muxcommand import MuxCommand
from evennia.prototypes import prototypes as protlib
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create, gametime, utils
from evennia.utils.test_resources import BaseEvenniaCommandTest  # noqa
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaCommandTest

# ------------------------------------------------------------
# Command testing
# ------------------------------------------------------------


class TestGeneral(BaseEvenniaCommandTest):
    def test_look(self):
        rid = self.room1.id
        self.call(general.CmdLook(), "here", "Room(#{})\nroom_desc".format(rid))

    def test_look_no_location(self):
        self.char1.location = None
        self.call(general.CmdLook(), "", "You have no location to look at!")

    def test_look_nonexisting(self):
        self.call(general.CmdLook(), "yellow sign", "Could not find 'yellow sign'.")

    def test_home(self):
        self.call(general.CmdHome(), "", "You are already home")

    def test_go_home(self):
        self.call(building.CmdTeleport(), "/quiet Room2")
        self.call(general.CmdHome(), "", "There's no place like home")

    def test_no_home(self):
        self.char1.home = None
        self.call(general.CmdHome(), "", "You have no home")

    def test_inventory(self):
        self.call(general.CmdInventory(), "", "You are not carrying anything.")

    def test_pose(self):
        self.call(general.CmdPose(), "looks around", "Char looks around")

    def test_nick(self):
        self.call(
            general.CmdNick(),
            "testalias = testaliasedstring1",
            "Inputline-nick 'testalias' mapped to 'testaliasedstring1'.",
        )
        self.call(
            general.CmdNick(),
            "/account testalias = testaliasedstring2",
            "Account-nick 'testalias' mapped to 'testaliasedstring2'.",
        )
        self.call(
            general.CmdNick(),
            "/object testalias = testaliasedstring3",
            "Object-nick 'testalias' mapped to 'testaliasedstring3'.",
        )
        self.assertEqual("testaliasedstring1", self.char1.nicks.get("testalias"))
        self.assertEqual(
            "testaliasedstring2", self.char1.nicks.get("testalias", category="account")
        )
        self.assertEqual(None, self.char1.account.nicks.get("testalias", category="account"))
        self.assertEqual("testaliasedstring3", self.char1.nicks.get("testalias", category="object"))

    def test_nick_list(self):
        self.call(general.CmdNick(), "/list", "No nicks defined.")
        self.call(general.CmdNick(), "test1 = Hello", "Inputline-nick 'test1' mapped to 'Hello'.")
        self.call(general.CmdNick(), "/list", "Defined Nicks:")

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
            key = "test"
            switch_options = ("test", "testswitch", "testswitch2")

            def func(self):
                self.msg("Switches matched: {}".format(self.switches))

        self.call(
            CmdTest(),
            "/test/testswitch/testswitch2",
            "Switches matched: ['test', 'testswitch', 'testswitch2']",
        )
        self.call(CmdTest(), "/test", "Switches matched: ['test']")
        self.call(CmdTest(), "/test/testswitch", "Switches matched: ['test', 'testswitch']")
        self.call(
            CmdTest(), "/testswitch/testswitch2", "Switches matched: ['testswitch', 'testswitch2']"
        )
        self.call(CmdTest(), "/testswitch", "Switches matched: ['testswitch']")
        self.call(CmdTest(), "/testswitch2", "Switches matched: ['testswitch2']")
        self.call(
            CmdTest(),
            "/t",
            "test: Ambiguous switch supplied: "
            "Did you mean /test or /testswitch or /testswitch2?|Switches matched: []",
        )
        self.call(
            CmdTest(),
            "/tests",
            "test: Ambiguous switch supplied: "
            "Did you mean /testswitch or /testswitch2?|Switches matched: []",
        )

    def test_say(self):
        self.call(general.CmdSay(), "Testing", 'You say, "Testing"')

    def test_whisper(self):
        self.call(
            general.CmdWhisper(),
            "Obj = Testing",
            'You whisper to Obj, "Testing"',
            caller=self.char2,
        )

    def test_access(self):
        self.call(general.CmdAccess(), "", "Permission Hierarchy (climbing):")


class TestHelp(BaseEvenniaCommandTest):

    maxDiff = None

    def setUp(self):
        super().setUp()
        # we need to set up a logger here since lunr takes over the logger otherwise
        import logging

        logging.basicConfig(level=logging.ERROR)

    def tearDown(self):
        super().tearDown()
        import logging

        logging.disable(level=logging.ERROR)

    def test_help(self):
        self.call(help_module.CmdHelp(), "", "Commands", cmdset=CharacterCmdSet())

    def test_set_help(self):
        self.call(
            help_module.CmdSetHelp(),
            "testhelp, General = This is a test",
            "Topic 'testhelp' was successfully created.",
            cmdset=CharacterCmdSet(),
        )
        self.call(help_module.CmdHelp(), "testhelp", "Help for testhelp", cmdset=CharacterCmdSet())

    @parameterized.expand(
        [
            (
                "test",  # main help entry
                "Help for test\n\n"
                "Main help text\n\n"
                "Subtopics:\n"
                "  test/creating extra stuff"
                "  test/something else"
                "  test/more",
            ),
            (
                "test/creating extra stuff",  # subtopic, full match
                "Help for test/creating extra stuff\n\n"
                "Help on creating extra stuff.\n\n"
                "Subtopics:\n"
                "  test/creating extra stuff/subsubtopic\n",
            ),
            (
                "test/creating",  # startswith-match
                "Help for test/creating extra stuff\n\n"
                "Help on creating extra stuff.\n\n"
                "Subtopics:\n"
                "  test/creating extra stuff/subsubtopic\n",
            ),
            (
                "test/extra",  # partial match
                "Help for test/creating extra stuff\n\n"
                "Help on creating extra stuff.\n\n"
                "Subtopics:\n"
                "  test/creating extra stuff/subsubtopic\n",
            ),
            (
                "test/extra/subsubtopic",  # partial subsub-match
                "Help for test/creating extra stuff/subsubtopic\n\nA subsubtopic text",
            ),
            (
                "test/creating extra/subsub",  # partial subsub-match
                "Help for test/creating extra stuff/subsubtopic\n\nA subsubtopic text",
            ),
            ("test/Something else", "Help for test/something else\n\nSomething else"),  # case
            (
                "test/More",  # case
                "Help for test/more\n\nAnother text\n\nSubtopics:\n  test/more/second-more",
            ),
            (
                "test/More/Second-more",
                "Help for test/more/second-more\n\n"
                "The Second More text.\n\n"
                "Subtopics:\n"
                "  test/more/second-more/more again"
                "  test/more/second-more/third more",
            ),
            (
                "test/More/-more",  # partial match
                "Help for test/more/second-more\n\n"
                "The Second More text.\n\n"
                "Subtopics:\n"
                "  test/more/second-more/more again"
                "  test/more/second-more/third more",
            ),
            (
                "test/more/second/more again",
                "Help for test/more/second-more/more again\n\nEven more text.\n",
            ),
            (
                "test/more/second/third",
                "Help for test/more/second-more/third more\n\nThird more text\n",
            ),
        ]
    )
    def test_subtopic_fetch(self, helparg, expected):
        """
        Check retrieval of subtopics.

        """

        class TestCmd(Command):
            """
            Main help text

            # SUBTOPICS

                ## creating extra stuff

                Help on creating extra stuff.

                    ### subsubtopic

                    A subsubtopic text

                ## Something else

                Something else

                ## More

                Another text

                    ### Second-More

                    The Second More text.

                            #### More again

                            Even more text.

                            #### Third more

                            Third more text

            """

            key = "test"

        class TestCmdSet(CmdSet):
            def at_cmdset_creation(self):
                self.add(TestCmd())
                self.add(help_module.CmdHelp())

        self.call(help_module.CmdHelp(), helparg, expected, cmdset=TestCmdSet())


class TestSystem(BaseEvenniaCommandTest):
    def test_py(self):
        # we are not testing CmdReload, CmdReset and CmdShutdown, CmdService or CmdTime
        # since the server is not running during these tests.
        self.call(system.CmdPy(), "1+2", ">>> 1+2|3")
        self.call(system.CmdPy(), "/clientraw 1+2", ">>> 1+2|3")

    def test_scripts(self):
        self.call(building.CmdScripts(), "", "dbref ")

    def test_objects(self):
        self.call(building.CmdObjects(), "", "Object subtype totals")

    def test_about(self):
        self.call(system.CmdAbout(), "", None)

    def test_server_load(self):
        self.call(system.CmdServerLoad(), "", "Server CPU and Memory load:")


_TASK_HANDLER = None


def func_test_cmd_tasks():
    return "success"


class TestCmdTasks(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        # get a reference of TASK_HANDLER
        self.timedelay = 5
        global _TASK_HANDLER
        if _TASK_HANDLER is None:
            from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER
        _TASK_HANDLER.clock = task.Clock()
        self.task_handler = _TASK_HANDLER
        self.task_handler.clear()
        self.task = self.task_handler.add(self.timedelay, func_test_cmd_tasks)
        task_args = self.task_handler.tasks.get(self.task.get_id(), False)

    def tearDown(self):
        super().tearDown()
        self.task_handler.clear()

    def test_no_tasks(self):
        self.task_handler.clear()
        self.call(system.CmdTasks(), "", "There are no active tasks.")

    def test_active_task(self):
        cmd_result = self.call(system.CmdTasks(), "")
        for ptrn in (
            "Task ID",
            "Completion",
            "Date",
            "Function",
            "KWARGS",
            "persisten",
            "1",
            r"\d+/\d+/\d+",
            r"\d+\:",
            r"\d+\:\d+",
            r"\:\d+",
            "func_test",
            "{}",
            "False",
        ):
            self.assertRegex(cmd_result, ptrn)

    def test_persistent_task(self):
        self.task_handler.clear()
        self.task_handler.add(self.timedelay, func_test_cmd_tasks, persistent=True)
        cmd_result = self.call(system.CmdTasks(), "")
        self.assertRegex(cmd_result, "True")

    def test_pause_unpause(self):
        # test pause
        args = f"/pause {self.task.get_id()}"
        wanted_msg = "Pause task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        self.assertTrue(self.task.paused)
        self.task_handler.clock.advance(self.timedelay + 1)
        # test unpause
        args = f"/unpause {self.task.get_id()}"
        self.assertTrue(self.task.exists())
        wanted_msg = "Unpause task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        # verify task continues after unpause
        self.task_handler.clock.advance(1)
        self.assertFalse(self.task.exists())

    def test_do_task(self):
        args = f"/do_task {self.task.get_id()}"
        wanted_msg = "Do_task task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        self.assertFalse(self.task.exists())

    def test_remove(self):
        args = f"/remove {self.task.get_id()}"
        wanted_msg = "Remove task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        self.assertFalse(self.task.exists())

    def test_call(self):
        args = f"/call {self.task.get_id()}"
        wanted_msg = "Call task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        # make certain the task is still active
        self.assertTrue(self.task.active())
        # go past delay time, the task should call do_task and remove itself after calling.
        self.task_handler.clock.advance(self.timedelay + 1)
        self.assertFalse(self.task.exists())

    def test_cancel(self):
        args = f"/cancel {self.task.get_id()}"
        wanted_msg = "Cancel task 1 with completion date"
        cmd_result = self.call(system.CmdTasks(), args, wanted_msg)
        self.assertRegex(cmd_result, " \(func_test_cmd_tasks\) ")
        self.char1.execute_cmd("y")
        self.assertTrue(self.task.exists())
        self.assertFalse(self.task.active())

    def test_func_name_manipulation(self):
        self.task_handler.add(self.timedelay, func_test_cmd_tasks)  # add an extra task
        args = f"/remove func_test_cmd_tasks"
        wanted_msg = (
            "Task action remove completed on task ID 1.|The task function remove returned: True|"
            "Task action remove completed on task ID 2.|The task function remove returned: True"
        )
        self.call(system.CmdTasks(), args, wanted_msg)
        self.assertFalse(self.task_handler.tasks)  # no tasks should exist.

    def test_wrong_func_name(self):
        args = f"/remove intentional_fail"
        wanted_msg = "No tasks deferring function name intentional_fail found."
        self.call(system.CmdTasks(), args, wanted_msg)
        self.assertTrue(self.task.active())

    def test_no_input(self):
        args = f"/cancel {self.task.get_id()}"
        self.call(system.CmdTasks(), args)
        # task should complete since no input was received
        self.task_handler.clock.advance(self.timedelay + 1)
        self.assertFalse(self.task.exists())

    def test_responce_of_yes(self):
        self.call(system.CmdTasks(), f"/cancel {self.task.get_id()}")
        self.char1.msg = Mock()
        self.char1.execute_cmd("y")
        text = ""
        for _, _, kwargs in self.char1.msg.mock_calls:
            text += kwargs.get("text", "")
        self.assertEqual(text, "cancel request completed.The task function cancel returned: True")
        self.assertTrue(self.task.exists())

    def test_task_complete_waiting_input(self):
        """Test for task completing while waiting for input."""
        self.call(system.CmdTasks(), f"/cancel {self.task.get_id()}")
        self.task_handler.clock.advance(self.timedelay + 1)
        self.char1.msg = Mock()
        self.char1.execute_cmd("y")
        text = ""
        for _, _, kwargs in self.char1.msg.mock_calls:
            text += kwargs.get("text", "")
        self.assertEqual(text, "Task completed while waiting for input.")
        self.assertFalse(self.task.exists())

    def test_new_task_waiting_input(self):
        """
        Test task completing than a new task with the same ID being made while waitinf for input.
        """
        self.assertTrue(self.task.get_id(), 1)
        self.call(system.CmdTasks(), f"/cancel {self.task.get_id()}")
        self.task_handler.clock.advance(self.timedelay + 1)
        self.assertFalse(self.task.exists())
        self.task = self.task_handler.add(self.timedelay, func_test_cmd_tasks)
        self.assertTrue(self.task.get_id(), 1)
        self.char1.msg = Mock()
        self.char1.execute_cmd("y")
        text = ""
        for _, _, kwargs in self.char1.msg.mock_calls:
            text += kwargs.get("text", "")
        self.assertEqual(text, "Task completed while waiting for input.")

    def test_misformed_command(self):
        wanted_msg = (
            "Task command misformed.|Proper format tasks[/switch] [function name or task id]"
        )
        self.call(system.CmdTasks(), f"/cancel", wanted_msg)


class TestAdmin(BaseEvenniaCommandTest):
    def test_emit(self):
        self.call(admin.CmdEmit(), "Char2 = Test", "Emitted to Char2:\nTest")

    def test_perm(self):
        self.call(
            admin.CmdPerm(),
            "Obj = Builder",
            "Permission 'Builder' given to Obj (the Object/Character).",
        )
        self.call(
            admin.CmdPerm(),
            "Char2 = Builder",
            "Permission 'Builder' given to Char2 (the Object/Character).",
        )

    def test_wall(self):
        self.call(admin.CmdWall(), "Test", "Announcing to all connected sessions ...")

    def test_ban(self):
        self.call(admin.CmdBan(), "Char", "Name-ban 'char' was added. Use unban to reinstate.")

    def test_force(self):
        cid = self.char2.id
        self.call(
            admin.CmdForce(),
            "Char2=say test",
            'Char2(#{}) says, "test"|You have forced Char2 to: say test'.format(cid),
        )


class TestAccount(BaseEvenniaCommandTest):
    """
    Test different account-specific modes

    """

    @parameterized.expand(
        # multisession-mode, auto-puppet, max_nr_characters
        [
            (0, True, 1, "You are out-of-character"),
            (1, True, 1, "You are out-of-character"),
            (2, True, 1, "You are out-of-character"),
            (3, True, 1, "You are out-of-character"),
            (0, False, 1, "Account TestAccount"),
            (1, False, 1, "Account TestAccount"),
            (2, False, 1, "Account TestAccount"),
            (3, False, 1, "Account TestAccount"),
            (0, True, 2, "Account TestAccount"),
            (1, True, 2, "Account TestAccount"),
            (2, True, 2, "Account TestAccount"),
            (3, True, 2, "Account TestAccount"),
            (0, False, 2, "Account TestAccount"),
            (1, False, 2, "Account TestAccount"),
            (2, False, 2, "Account TestAccount"),
            (3, False, 2, "Account TestAccount"),
        ]
    )
    def test_ooc_look(self, multisession_mode, auto_puppet, max_nr_chars, expected_result):

        self.account.db._playable_characters = [self.char1]
        self.account.unpuppet_all()

        with self.settings(MULTISESSION=multisession_mode):
            # we need to patch the module header instead of settings
            with patch("evennia.commands.default.account._MAX_NR_CHARACTERS", new=max_nr_chars):
                with patch(
                    "evennia.commands.default.account._AUTO_PUPPET_ON_LOGIN", new=auto_puppet
                ):
                    self.call(
                        account.CmdOOCLook(),
                        "",
                        expected_result,
                        caller=self.account,
                    )

    def test_ooc(self):
        self.call(account.CmdOOC(), "", "You go OOC.", caller=self.account)

    def test_ic(self):
        self.account.db._playable_characters = [self.char1]
        self.account.unpuppet_object(self.session)
        self.call(
            account.CmdIC(), "Char", "You become Char.", caller=self.account, receiver=self.char1
        )

    def test_ic__other_object(self):
        self.account.db._playable_characters = [self.obj1]
        self.account.unpuppet_object(self.session)
        self.call(
            account.CmdIC(), "Obj", "You become Obj.", caller=self.account, receiver=self.obj1
        )

    def test_ic__nonaccess(self):
        self.account.unpuppet_object(self.session)
        self.call(
            account.CmdIC(),
            "Nonexistent",
            "That is not a valid character choice.",
            caller=self.account,
            receiver=self.account,
        )

    def test_password(self):
        self.call(
            account.CmdPassword(),
            "testpassword = testpassword",
            "Password changed.",
            caller=self.account,
        )

    def test_option(self):
        self.call(account.CmdOption(), "", "Client settings", caller=self.account)

    def test_who(self):
        self.call(account.CmdWho(), "", "Accounts:", caller=self.account)

    def test_quit(self):
        self.call(
            account.CmdQuit(), "", "Quitting. Hope to see you again, soon.", caller=self.account
        )

    def test_sessions(self):
        self.call(account.CmdSessions(), "", "Your current session(s):", caller=self.account)

    def test_color_test(self):
        self.call(account.CmdColorTest(), "ansi", "ANSI colors:", caller=self.account)

    def test_char_create(self):
        self.call(
            account.CmdCharCreate(),
            "Test1=Test char",
            "Created new character Test1. Use ic Test1 to enter the game",
            caller=self.account,
        )

    def test_char_delete(self):
        # Chardelete requires user input; this test is mainly to confirm
        # whether permissions are being checked

        # Add char to account playable characters
        self.account.db._playable_characters.append(self.char1)

        # Try deleting as Developer
        self.call(
            account.CmdCharDelete(),
            "Char",
            "This will permanently destroy 'Char'. This cannot be undone. Continue yes/[no]?",
            caller=self.account,
        )

        # Downgrade permissions on account
        self.account.permissions.add("Player")
        self.account.permissions.remove("Developer")

        # Set lock on character object to prevent deletion
        self.char1.locks.add("delete:none()")

        # Try deleting as Player
        self.call(
            account.CmdCharDelete(),
            "Char",
            "You do not have permission to delete this character.",
            caller=self.account,
        )

        # Set lock on character object to allow self-delete
        self.char1.locks.add("delete:pid(%i)" % self.account.id)

        # Try deleting as Player again
        self.call(
            account.CmdCharDelete(),
            "Char",
            "This will permanently destroy 'Char'. This cannot be undone. Continue yes/[no]?",
            caller=self.account,
        )

    def test_quell(self):
        self.call(
            account.CmdQuell(),
            "",
            "Quelling to current puppet's permissions (developer).",
            caller=self.account,
        )


class TestBuilding(BaseEvenniaCommandTest):
    def test_create(self):
        name = settings.BASE_OBJECT_TYPECLASS.rsplit(".", 1)[1]
        self.call(
            building.CmdCreate(),
            "/d TestObj1",  # /d switch is abbreviated form of /drop
            "You create a new %s: TestObj1." % name,
        )
        self.call(building.CmdCreate(), "", "Usage: ")
        self.call(
            building.CmdCreate(),
            "TestObj1;foo;bar",
            "You create a new %s: TestObj1 (aliases: foo, bar)." % name,
        )

    def test_examine(self):
        self.call(building.CmdExamine(), "", "Name/key: Room")
        self.call(building.CmdExamine(), "Obj", "Name/key: Obj")
        self.call(building.CmdExamine(), "Obj", "Name/key: Obj")
        self.call(building.CmdExamine(), "*TestAccount", "Name/key: TestAccount")

        self.char1.db.test = "testval"
        self.call(
            building.CmdExamine(), "self/test", "Attribute Char/test [category=None]:\n\ntestval"
        )
        self.call(building.CmdExamine(), "NotFound", "Could not find 'NotFound'.")
        self.call(building.CmdExamine(), "out", "Name/key: out")

        # escape inlinefuncs
        self.char1.db.test2 = "this is a $random() value."
        self.call(
            building.CmdExamine(),
            "self/test2",
            "Attribute Char/test2 [category=None]:\n\nthis is a \$random() value.",
        )

        self.room1.scripts.add(self.script.__class__)
        self.call(building.CmdExamine(), "")
        self.account.scripts.add(self.script.__class__)
        self.call(building.CmdExamine(), "*TestAccount")

    def test_set_obj_alias(self):
        oid = self.obj1.id
        self.call(building.CmdSetObjAlias(), "Obj =", "Cleared aliases from Obj")
        self.call(
            building.CmdSetObjAlias(),
            "Obj = TestObj1b",
            "Alias(es) for 'Obj(#{})' set to 'testobj1b'.".format(oid),
        )
        self.call(building.CmdSetObjAlias(), "", "Usage: ")
        self.call(building.CmdSetObjAlias(), "NotFound =", "Could not find 'NotFound'.")

        self.call(building.CmdSetObjAlias(), "Obj", "Aliases for Obj(#{}): 'testobj1b'".format(oid))
        self.call(building.CmdSetObjAlias(), "Obj2 =", "Cleared aliases from Obj2")
        self.call(building.CmdSetObjAlias(), "Obj2 =", "No aliases to clear.")

    def test_copy(self):
        self.call(
            building.CmdCopy(),
            "Obj = TestObj2;TestObj2b, TestObj3;TestObj3b",
            "Copied Obj to 'TestObj3' (aliases: ['TestObj3b']",
        )
        self.call(building.CmdCopy(), "", "Usage: ")
        self.call(building.CmdCopy(), "Obj", "Identical copy of Obj, named 'Obj_copy' was created.")
        self.call(building.CmdCopy(), "NotFound = Foo", "Could not find 'NotFound'.")

    def test_attribute_commands(self):
        self.call(building.CmdSetAttribute(), "", "Usage: ")
        self.call(
            building.CmdSetAttribute(),
            'Obj/test1="value1"',
            "Created attribute Obj/test1 [category:None] = value1",
        )
        self.call(
            building.CmdSetAttribute(),
            'Obj2/test2="value2"',
            "Created attribute Obj2/test2 [category:None] = value2",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj2/test2",
            "Attribute Obj2/test2 [category:None] = value2",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj2/NotFound",
            "Attribute Obj2/notfound [category:None] does not exist.",
        )

        with patch("evennia.commands.default.building.EvEditor") as mock_ed:
            self.call(building.CmdSetAttribute(), "/edit Obj2/test3")
            mock_ed.assert_called_with(self.char1, Anything, Anything, key="Obj2/test3")

        self.call(
            building.CmdSetAttribute(),
            'Obj2/test3="value3"',
            "Created attribute Obj2/test3 [category:None] = value3",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj2/test3 = ",
            "Deleted attribute Obj2/test3 [category:None].",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj2/test4:Foo = 'Bar'",
            "Created attribute Obj2/test4 [category:Foo] = Bar",
        )
        self.call(
            building.CmdCpAttr(),
            "/copy Obj2/test2 = Obj2/test3",
            '@cpattr: Extra switch "/copy" ignored.|\nCopied Obj2.test2 -> Obj2.test3. '
            "(value: 'value2')",
        )
        self.call(building.CmdMvAttr(), "", "Usage: ")
        self.call(building.CmdMvAttr(), "Obj2/test2 = Obj/test3", "Moved Obj2.test2 -> Obj.test3")
        self.call(building.CmdCpAttr(), "", "Usage: ")
        self.call(building.CmdCpAttr(), "Obj/test1 = Obj2/test3", "Copied Obj.test1 -> Obj2.test3")

        self.call(building.CmdWipe(), "", "Usage: ")
        self.call(building.CmdWipe(), "Obj2/test2/test3", "Wiped attributes test2,test3 on Obj2.")
        self.call(building.CmdWipe(), "Obj2", "Wiped all attributes on Obj2.")

    def test_nested_attribute_commands(self):
        # list - adding white space proves real parsing
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1=[1,2]",
            "Created attribute Obj/test1 [category:None] = [1, 2]",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test1", "Attribute Obj/test1 [category:None] = [1, 2]"
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test1[0]", "Attribute Obj/test1[0] [category:None] = 1"
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test1[1]", "Attribute Obj/test1[1] [category:None] = 2"
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[0] = 99",
            "Modified attribute Obj/test1 [category:None] = [99, 2]",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[0]",
            "Attribute Obj/test1[0] [category:None] = 99",
        )
        # list delete
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[0] =",
            "Deleted attribute Obj/test1[0] [category:None].",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test1[0]", "Attribute Obj/test1[0] [category:None] = 2"
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[1]",
            "Attribute Obj/test1[1] [category:None] does not exist. (Nested lookups attempted)",
        )
        # Delete non-existent
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[5] =",
            "No attribute Obj/test1[5] [category: None] was found to "
            "delete. (Nested lookups attempted)",
        )
        # Append
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[+] = 42",
            "Modified attribute Obj/test1 [category:None] = [2, 42]",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[+0] = -1",
            "Modified attribute Obj/test1 [category:None] = [-1, 2, 42]",
        )

        # dict - removing white space proves real parsing
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2={ 'one': 1, 'two': 2 }",
            "Created attribute Obj/test2 [category:None] = {'one': 1, 'two': 2}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2",
            "Attribute Obj/test2 [category:None] = {'one': 1, 'two': 2}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['one']",
            "Attribute Obj/test2['one'] [category:None] = 1",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['one]",
            "Attribute Obj/test2['one] [category:None] = 1",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['one']=99",
            "Modified attribute Obj/test2 [category:None] = {'one': 99, 'two': 2}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['one']",
            "Attribute Obj/test2['one'] [category:None] = 99",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['two']",
            "Attribute Obj/test2['two'] [category:None] = 2",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three']",
            "Attribute Obj/test2[+'three'] [category:None] does not exist. (Nested lookups"
            " attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three'] = 3",
            "Modified attribute Obj/test2 [category:None] = {'one': 99, 'two': 2, \"+'three'\": 3}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three'] =",
            "Deleted attribute Obj/test2[+'three'] [category:None].",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['three']=3",
            "Modified attribute Obj/test2 [category:None] = {'one': 99, 'two': 2, 'three': 3}",
        )
        # Dict delete
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['two'] =",
            "Deleted attribute Obj/test2['two'] [category:None].",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['two']",
            "Attribute Obj/test2['two'] [category:None] does not exist. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2",
            "Attribute Obj/test2 [category:None] = {'one': 99, 'three': 3}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[0]",
            "Attribute Obj/test2[0] [category:None] does not exist. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['five'] =",
            "No attribute Obj/test2['five'] [category: None] "
            "was found to delete. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+]=42",
            "Modified attribute Obj/test2 [category:None] = {'one': 99, 'three': 3, '+': 42}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+1]=33",
            "Modified attribute Obj/test2 [category:None] = "
            "{'one': 99, 'three': 3, '+': 42, '+1': 33}",
        )

        # dict - case sensitive keys

        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case = {'FooBar': 1}",
            "Created attribute Obj/test_case [category:None] = {'FooBar': 1}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case['FooBar'] = 2",
            "Modified attribute Obj/test_case [category:None] = {'FooBar': 2}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case",
            "Attribute Obj/test_case [category:None] = {'FooBar': 2}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case['FooBar'] = {'BarBaz': 1}",
            "Modified attribute Obj/test_case [category:None] = {'FooBar': {'BarBaz': 1}}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case['FooBar']['BarBaz'] = 2",
            "Modified attribute Obj/test_case [category:None] = {'FooBar': {'BarBaz': 2}}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test_case",
            "Attribute Obj/test_case [category:None] = {'FooBar': {'BarBaz': 2}}",
        )

        # tuple
        self.call(
            building.CmdSetAttribute(),
            "Obj/tup = (1,2)",
            "Created attribute Obj/tup [category:None] = (1, 2)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/tup[1] = 99",
            "'tuple' object does not support item assignment - (1, 2)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/tup[+] = 99",
            "'tuple' object does not support item assignment - (1, 2)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/tup[+1] = 99",
            "'tuple' object does not support item assignment - (1, 2)",
        )
        self.call(
            building.CmdSetAttribute(),
            # Special case for tuple, could have a better message
            "Obj/tup[1] = ",
            "No attribute Obj/tup[1] [category: None] "
            "was found to delete. (Nested lookups attempted)",
        )

        # Deaper nesting
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3=[{'one': 1}]",
            "Created attribute Obj/test3 [category:None] = [{'one': 1}]",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3[0]['one']",
            "Attribute Obj/test3[0]['one'] [category:None] = 1",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3[0]",
            "Attribute Obj/test3[0] [category:None] = {'one': 1}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3[0]['one'] =",
            "Deleted attribute Obj/test3[0]['one'] [category:None].",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3[0]",
            "Attribute Obj/test3[0] [category:None] = {}",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test3", "Attribute Obj/test3 [category:None] = [{}]"
        )

        # Naughty keys
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]='foo'",
            "Created attribute Obj/test4[0] [category:None] = foo",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]",
            "Attribute Obj/test4[0] [category:None] = foo",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4=[{'one': 1}]",
            "Created attribute Obj/test4 [category:None] = [{'one': 1}]",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]['one']",
            "Attribute Obj/test4[0]['one'] [category:None] = 1",
        )
        # Prefer nested items
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]",
            "Attribute Obj/test4[0] [category:None] = {'one': 1}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]['one']",
            "Attribute Obj/test4[0]['one'] [category:None] = 1",
        )
        # Restored access
        self.call(building.CmdWipe(), "Obj/test4", "Wiped attributes test4 on Obj.")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]",
            "Attribute Obj/test4[0] [category:None] = foo",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]['one']",
            "Attribute Obj/test4[0]['one'] [category:None] does not exist. (Nested lookups"
            " attempted)",
        )

    def test_split_nested_attr(self):
        split_nested_attr = building.CmdSetAttribute().split_nested_attr
        test_cases = {
            "test1": [("test1", [])],
            'test2["dict"]': [("test2", ["dict"]), ('test2["dict"]', [])],
            # Quotes not actually required
            "test3[dict]": [("test3", ["dict"]), ("test3[dict]", [])],
            'test4["dict]': [("test4", ["dict"]), ('test4["dict]', [])],
            # duplicate keys don't cause issues
            "test5[0][0]": [("test5", [0, 0]), ("test5[0]", [0]), ("test5[0][0]", [])],
            # String ints preserved
            'test6["0"][0]': [("test6", ["0", 0]), ('test6["0"]', [0]), ('test6["0"][0]', [])],
            # Unmatched []
            "test7[dict": [("test7[dict", [])],
        }

        for attr, result in test_cases.items():
            self.assertEqual(list(split_nested_attr(attr)), result)

    def test_do_nested_lookup(self):
        do_nested_lookup = building.CmdSetAttribute().do_nested_lookup
        not_found = building.CmdSetAttribute.not_found

        def do_test_single(value, key, result):
            self.assertEqual(do_nested_lookup(value, key), result)

        def do_test_multi(value, keys, result):
            self.assertEqual(do_nested_lookup(value, *keys), result)

        do_test_single([], "test1", not_found)
        do_test_single([1], "test2", not_found)
        do_test_single([], 0, not_found)
        do_test_single([], "0", not_found)
        do_test_single([1], 2, not_found)
        do_test_single([1], 0, 1)
        do_test_single([1], "0", not_found)  # str key is str not int
        do_test_single({}, "test3", not_found)
        do_test_single({}, 0, not_found)
        do_test_single({"foo": "bar"}, "foo", "bar")

        do_test_multi({"one": [1, 2, 3]}, ("one", 0), 1)
        do_test_multi([{}, {"two": 2}, 3], (1, "two"), 2)

    def test_name(self):
        self.call(building.CmdName(), "", "Usage: ")
        self.call(building.CmdName(), "Obj2=Obj3", "Object's name changed to 'Obj3'.")
        self.call(
            building.CmdName(),
            "*TestAccount=TestAccountRenamed",
            "Account's name changed to 'TestAccountRenamed'.",
        )
        self.call(building.CmdName(), "*NotFound=TestAccountRenamed", "Could not find '*NotFound'")
        self.call(
            building.CmdName(), "Obj3=Obj4;foo;bar", "Object's name changed to 'Obj4' (foo, bar)."
        )
        self.call(building.CmdName(), "Obj4=", "No names or aliases defined!")

    def test_desc(self):
        oid = self.obj2.id
        self.call(
            building.CmdDesc(), "Obj2=TestDesc", "The description was set on Obj2(#{}).".format(oid)
        )
        self.call(building.CmdDesc(), "", "Usage: ")

        with patch("evennia.commands.default.building.EvEditor") as mock_ed:
            self.call(building.CmdDesc(), "/edit")
            mock_ed.assert_called_with(
                self.char1,
                key="desc",
                loadfunc=building._desc_load,
                quitfunc=building._desc_quit,
                savefunc=building._desc_save,
                persistent=True,
            )

    def test_empty_desc(self):
        """
        empty desc sets desc as ''
        """
        oid = self.obj2.id
        o2d = self.obj2.db.desc
        r1d = self.room1.db.desc
        self.call(building.CmdDesc(), "Obj2=", "The description was set on Obj2(#{}).".format(oid))
        assert self.obj2.db.desc == "" and self.obj2.db.desc != o2d
        assert self.room1.db.desc == r1d

    def test_desc_default_to_room(self):
        """no rhs changes room's desc"""
        rid = self.room1.id
        o2d = self.obj2.db.desc
        r1d = self.room1.db.desc
        self.call(building.CmdDesc(), "Obj2", "The description was set on Room(#{}).".format(rid))
        assert self.obj2.db.desc == o2d
        assert self.room1.db.desc == "Obj2" and self.room1.db.desc != r1d

    def test_destroy(self):
        confirm = building.CmdDestroy.confirm
        building.CmdDestroy.confirm = False
        self.call(building.CmdDestroy(), "", "Usage: ")
        self.call(building.CmdDestroy(), "Obj", "Obj was destroyed.")
        self.call(building.CmdDestroy(), "Obj", "Obj2 was destroyed.")
        self.call(
            building.CmdDestroy(),
            "Obj",
            "Could not find 'Obj'.| (Objects to destroy "
            "must either be local or specified with a unique #dbref.)",
        )
        settings.DEFAULT_HOME = f"#{self.room1.dbid}"
        self.call(
            building.CmdDestroy(), settings.DEFAULT_HOME, "You are trying to delete"
        )  # DEFAULT_HOME should not be deleted
        self.char2.location = self.room2
        charid = self.char2.id
        room1id = self.room1.id
        room2id = self.room2.id
        self.call(
            building.CmdDestroy(),
            self.room2.dbref,
            "Char2(#{}) arrives to Room(#{}) from Room2(#{}).|Room2 was destroyed.".format(
                charid, room1id, room2id
            ),
        )
        building.CmdDestroy.confirm = confirm

    def test_destroy_sequence(self):
        confirm = building.CmdDestroy.confirm
        building.CmdDestroy.confirm = False
        self.call(
            building.CmdDestroy(),
            "{}-{}".format(self.obj1.dbref, self.obj2.dbref),
            "Obj was destroyed.\nObj2 was destroyed.",
        )

    def test_dig(self):
        self.call(building.CmdDig(), "TestRoom1=testroom;tr,back;b", "Created room TestRoom1")
        self.call(building.CmdDig(), "", "Usage: ")

    def test_tunnel(self):
        self.call(building.CmdTunnel(), "n = TestRoom2;test2", "Created room TestRoom2")
        self.call(building.CmdTunnel(), "", "Usage: ")
        self.call(building.CmdTunnel(), "foo = TestRoom2;test2", "tunnel can only understand the")
        self.call(building.CmdTunnel(), "/tel e = TestRoom3;test3", "Created room TestRoom3")
        DefaultRoom.objects.get_family(db_key="TestRoom3")
        exits = DefaultExit.objects.filter_family(db_key__in=("east", "west"))
        self.assertEqual(len(exits), 2)

    def test_tunnel_exit_typeclass(self):
        self.call(
            building.CmdTunnel(),
            "n:evennia.objects.objects.DefaultExit = TestRoom3",
            "Created room TestRoom3",
        )

    def test_exit_commands(self):
        self.call(
            building.CmdOpen(), "TestExit1=Room2", "Created new Exit 'TestExit1' from Room to Room2"
        )
        self.call(building.CmdLink(), "TestExit1=Room", "Link created TestExit1 -> Room (one way).")
        self.call(building.CmdUnLink(), "", "Usage: ")
        self.call(building.CmdLink(), "NotFound", "Could not find 'NotFound'.")
        self.call(building.CmdLink(), "TestExit", "TestExit1 is an exit to Room.")
        self.call(building.CmdLink(), "Obj", "Obj is not an exit. Its home location is Room.")
        self.call(
            building.CmdUnLink(), "TestExit1", "Former exit TestExit1 no longer links anywhere."
        )

        self.char1.location = self.room2
        self.call(
            building.CmdOpen(), "TestExit2=Room", "Created new Exit 'TestExit2' from Room2 to Room."
        )
        self.call(
            building.CmdOpen(),
            "TestExit2=Room",
            "Exit TestExit2 already exists. It already points to the correct place.",
        )

        # ensure it matches locally first
        self.call(
            building.CmdLink(), "TestExit=Room2", "Link created TestExit2 -> Room2 (one way)."
        )
        self.call(
            building.CmdLink(),
            "/twoway TestExit={}".format(self.exit.dbref),
            "Link created TestExit2 (in Room2) <-> out (in Room) (two-way).",
        )
        self.call(
            building.CmdLink(),
            "/twoway TestExit={}".format(self.room1.dbref),
            "To create a two-way link, TestExit2 and Room must both have a location ",
        )
        self.call(
            building.CmdLink(),
            "/twoway {}={}".format(self.exit.dbref, self.exit.dbref),
            "Cannot link an object to itself.",
        )
        self.call(building.CmdLink(), "", "Usage: ")
        # ensure can still match globally when not a local name
        self.call(building.CmdLink(), "TestExit1=Room2", "Note: TestExit1")
        self.call(
            building.CmdLink(), "TestExit1=", "Former exit TestExit1 no longer links anywhere."
        )

    def test_set_home(self):
        self.call(
            building.CmdSetHome(), "Obj = Room2", "Home location of Obj was changed from Room"
        )
        self.call(building.CmdSetHome(), "", "Usage: ")
        self.call(building.CmdSetHome(), "self", "Char's current home is Room")
        self.call(building.CmdSetHome(), "Obj", "Obj's current home is Room2")
        self.obj1.home = None
        self.call(building.CmdSetHome(), "Obj = Room2", "Home location of Obj was set to Room")

    def test_list_cmdsets(self):
        self.call(
            building.CmdListCmdSets(),
            "",
            "<CmdSetHandler> stack:\n <CmdSet DefaultCharacter, Union, perm, prio 0>:",
        )
        self.call(building.CmdListCmdSets(), "NotFound", "Could not find 'NotFound'")

    def test_typeclass(self):
        self.call(building.CmdTypeclass(), "", "Usage: ")
        self.call(
            building.CmdTypeclass(),
            "Obj = evennia.objects.objects.DefaultExit",
            "Obj changed typeclass from evennia.objects.objects.DefaultObject "
            "to evennia.objects.objects.DefaultExit.",
        )
        self.call(
            building.CmdTypeclass(),
            "Obj2 = evennia.objects.objects.DefaultExit",
            "Obj2 changed typeclass from evennia.objects.objects.DefaultObject "
            "to evennia.objects.objects.DefaultExit.",
            cmdstring="swap",
            inputs=["yes"],
        )
        self.call(building.CmdTypeclass(), "/list Obj", "Core typeclasses")
        self.call(
            building.CmdTypeclass(),
            "/show Obj",
            "Obj's current typeclass is 'evennia.objects.objects.DefaultExit'",
        )
        self.call(
            building.CmdTypeclass(),
            "Obj = evennia.objects.objects.DefaultExit",
            "Obj already has the typeclass 'evennia.objects.objects.DefaultExit'. Use /force to"
            " override.",
        )
        self.call(
            building.CmdTypeclass(),
            "/force Obj = evennia.objects.objects.DefaultExit",
            "Obj updated its existing typeclass ",
        )
        self.call(building.CmdTypeclass(), "Obj = evennia.objects.objects.DefaultObject")
        self.call(
            building.CmdTypeclass(),
            "/show Obj",
            "Obj's current typeclass is 'evennia.objects.objects.DefaultObject'",
        )
        self.call(
            building.CmdTypeclass(),
            "Obj",
            "Obj updated its existing typeclass (evennia.objects.objects.DefaultObject).\nOnly the"
            " at_object_creation hook was run (update mode). Attributes set before swap were not"
            " removed\n(use `swap` or `type/reset` to clear all).",
            cmdstring="update",
        )
        self.call(
            building.CmdTypeclass(),
            "/reset/force Obj=evennia.objects.objects.DefaultObject",
            "Obj updated its existing typeclass (evennia.objects.objects.DefaultObject).\n"
            "All object creation hooks were run. All old attributes where deleted before the swap.",
            inputs=["yes"],
        )

        from evennia.prototypes.prototypes import homogenize_prototype

        test_prototype = [
            homogenize_prototype(
                {
                    "prototype_key": "testkey",
                    "prototype_tags": [],
                    "typeclass": "typeclasses.objects.Object",
                    "key": "replaced_obj",
                    "attrs": [("foo", "bar", None, ""), ("desc", "protdesc", None, "")],
                }
            )
        ]
        with patch(
            "evennia.commands.default.building.protlib.search_prototype",
            new=MagicMock(return_value=test_prototype),
        ) as mprot:
            self.call(
                building.CmdTypeclass(),
                "/prototype Obj=testkey",
                "replaced_obj changed typeclass from evennia.objects.objects.DefaultObject to "
                "typeclasses.objects.Object.\nOnly the at_object_creation hook was run "
                "(update mode). Attributes set before swap were not removed\n"
                "(use `swap` or `type/reset` to clear all). Prototype 'replaced_obj' was "
                "successfully applied over the object type.",
            )
            assert self.obj1.db.desc == "protdesc"

    def test_lock(self):
        self.call(building.CmdLock(), "", "Usage: ")
        self.call(building.CmdLock(), "Obj = test:all()", "Added lock 'test:all()' to Obj.")
        self.call(
            building.CmdLock(),
            "*TestAccount = test:all()",
            "Added lock 'test:all()' to TestAccount",
        )
        self.call(building.CmdLock(), "Obj/notfound", "Obj has no lock of access type 'notfound'.")
        self.call(building.CmdLock(), "Obj/test", "test:all()")
        self.call(
            building.CmdLock(),
            "/view Obj = edit:false()",
            "Switch(es) view can not be used with a lock assignment. "
            "Use e.g. lock/del objname/locktype instead.",
        )
        self.call(building.CmdLock(), "Obj = control:false()")
        self.call(building.CmdLock(), "Obj = edit:false()")
        self.call(building.CmdLock(), "Obj/test", "You are not allowed to do that.")
        self.obj1.locks.add("control:true()")
        self.call(building.CmdLock(), "Obj", "call:true()")  # etc
        self.call(building.CmdLock(), "*TestAccount", "boot:perm(Admin)")  # etc

    def test_find(self):
        rid2 = self.room2.id
        rmax = rid2 + 100
        self.call(building.CmdFind(), "", "Usage: ")
        self.call(building.CmdFind(), "oom2", "One Match")
        self.call(building.CmdFind(), "oom2 = 1-{}".format(rmax), "One Match")
        self.call(building.CmdFind(), "oom2 = 1 {}".format(rmax), "One Match")  # space works too
        self.call(building.CmdFind(), "Char2", "One Match", cmdstring="locate")
        self.call(
            building.CmdFind(),
            "/ex Char2",  # /ex is an ambiguous switch
            "locate: Ambiguous switch supplied: Did you mean /exit or /exact?|",
            cmdstring="locate",
        )
        self.call(building.CmdFind(), "Char2", "One Match", cmdstring="locate")
        self.call(
            building.CmdFind(), "/l Char2", "One Match", cmdstring="find"
        )  # /l switch is abbreviated form of /loc
        self.call(building.CmdFind(), "Char2", "One Match", cmdstring="find")
        self.call(building.CmdFind(), "/startswith Room2", "One Match")

        self.call(building.CmdFind(), self.char1.dbref, "Exact dbref match")
        self.call(building.CmdFind(), "*TestAccount", "Match")

        self.call(building.CmdFind(), "/char Obj", "No Matches")
        self.call(building.CmdFind(), "/room Obj", "No Matches")
        self.call(building.CmdFind(), "/exit Obj", "No Matches")
        self.call(building.CmdFind(), "/exact Obj", "One Match")

        # Test multitype filtering
        with patch(
            "evennia.commands.default.building.CHAR_TYPECLASS",
            "evennia.objects.objects.DefaultCharacter",
        ):
            self.call(building.CmdFind(), "/char/room Obj", "No Matches")
            self.call(building.CmdFind(), "/char/room/exit Char", "2 Matches")
            self.call(building.CmdFind(), "/char/room/exit/startswith Cha", "2 Matches")

        # Test null search
        self.call(building.CmdFind(), "=", "Usage: ")

        # Test bogus dbref range with no search term
        self.call(building.CmdFind(), "= obj", "Invalid dbref range provided (not a number).")
        self.call(building.CmdFind(), "= #1a", "Invalid dbref range provided (not a number).")

        # Test valid dbref ranges with no search term
        id1 = self.obj1.id
        id2 = self.obj2.id
        maxid = ObjectDB.objects.latest("id").id
        maxdiff = maxid - id1 + 1
        mdiff = id2 - id1 + 1

        self.call(building.CmdFind(), f"=#{id1}", f"{maxdiff} Matches(#{id1}-#{maxid}")
        self.call(building.CmdFind(), f"={id1}-{id2}", f"{mdiff} Matches(#{id1}-#{id2}):")
        self.call(building.CmdFind(), f"={id1} - {id2}", f"{mdiff} Matches(#{id1}-#{id2}):")
        self.call(building.CmdFind(), f"={id1}- #{id2}", f"{mdiff} Matches(#{id1}-#{id2}):")
        self.call(building.CmdFind(), f"={id1}-#{id2}", f"{mdiff} Matches(#{id1}-#{id2}):")
        self.call(building.CmdFind(), f"=#{id1}-{id2}", f"{mdiff} Matches(#{id1}-#{id2}):")

    def test_script(self):
        self.call(building.CmdScripts(), "Obj", "No scripts defined on Obj")
        self.call(
            building.CmdScripts(),
            "Obj = scripts.scripts.DefaultScript",
            "Script scripts.scripts.DefaultScript successfully added",
        )
        self.call(building.CmdScripts(), "evennia.Dummy", "Global Script NOT Created ")
        self.call(
            building.CmdScripts(),
            "evennia.scripts.scripts.DoNothing",
            "Global Script Created - sys_do_nothing ",
        )
        self.call(building.CmdScripts(), "Obj ", "dbref ")

        self.call(
            building.CmdScripts(), "/start Obj", "Script on Obj Started "
        )  # we allow running start again; this should still happen
        self.call(building.CmdScripts(), "/stop Obj", "Script on Obj Stopped - ")

        self.call(
            building.CmdScripts(),
            "Obj = scripts.scripts.DefaultScript",
            "Script scripts.scripts.DefaultScript successfully added",
            inputs=["Y"],
        )
        self.call(
            building.CmdScripts(),
            "/start Obj = scripts.scripts.DefaultScript",
            "Script on Obj Started ",
            inputs=["Y"],
        )
        self.call(
            building.CmdScripts(),
            "/stop Obj = scripts.scripts.DefaultScript",
            "Script on Obj Stopped ",
            inputs=["Y"],
        )
        self.call(
            building.CmdScripts(),
            "/delete Obj = scripts.scripts.DefaultScript",
            "Script on Obj Deleted ",
            inputs=["Y"],
        )
        self.call(
            building.CmdScripts(),
            "/delete evennia.scripts.scripts.DoNothing",
            "Global Script Deleted -",
        )

    def test_script_multi_delete(self):

        script1 = create.create_script()
        script2 = create.create_script()
        script3 = create.create_script()

        self.call(
            building.CmdScripts(),
            "/delete #{}-#{}".format(script1.id, script3.id),
            f"Global Script Deleted - #{script1.id} (evennia.scripts.scripts.DefaultScript)|"
            f"Global Script Deleted - #{script2.id} (evennia.scripts.scripts.DefaultScript)|"
            f"Global Script Deleted - #{script3.id} (evennia.scripts.scripts.DefaultScript)",
            inputs=["y"],
        )
        self.assertFalse(script1.pk)
        self.assertFalse(script2.pk)
        self.assertFalse(script3.pk)

    def test_teleport(self):
        oid = self.obj1.id
        rid = self.room1.id
        rid2 = self.room2.id
        self.call(building.CmdTeleport(), "", "Usage: ")
        self.call(building.CmdTeleport(), "Obj = Room", "Obj is already at Room.")
        self.call(
            building.CmdTeleport(),
            "Obj = NotFound",
            "Could not find 'NotFound'.|Destination not found.",
        )
        self.call(
            building.CmdTeleport(),
            "Obj = Room2",
            "Obj(#{}) is leaving Room(#{}), heading for Room2(#{}).|Teleported Obj -> Room2.".format(
                oid, rid, rid2
            ),
        )
        self.call(building.CmdTeleport(), "NotFound = Room", "Could not find 'NotFound'.")
        self.call(
            building.CmdTeleport(), "Obj = Obj", "You can't teleport an object inside of itself!"
        )

        self.call(building.CmdTeleport(), "/tonone Obj2", "Teleported Obj2 -> None-location.")
        self.call(building.CmdTeleport(), "/quiet Room2", "Room2(#{})".format(rid2))
        self.call(
            building.CmdTeleport(),
            "/t",  # /t switch is abbreviated form of /tonone
            "Cannot teleport a puppeted object (Char, puppeted by TestAccount",
        )
        self.call(
            building.CmdTeleport(),
            "/l Room2",  # /l switch is abbreviated form of /loc
            "Destination has no location.",
        )
        self.call(
            building.CmdTeleport(),
            "/q me to Room2",  # /q switch is abbreviated form of /quiet
            "Char is already at Room2.",
        )

    def test_tag(self):
        self.call(building.CmdTag(), "", "Usage: ")

        self.call(building.CmdTag(), "Obj = testtag")
        self.call(building.CmdTag(), "Obj = testtag2")
        self.call(building.CmdTag(), "Obj = testtag2:category1")
        self.call(building.CmdTag(), "Obj = testtag3")

        self.call(
            building.CmdTag(),
            "Obj",
            "Tags on Obj: 'testtag', 'testtag2', 'testtag2' (category: category1), 'testtag3'",
        )

        self.call(building.CmdTag(), "/search NotFound", "No objects found with tag 'NotFound'.")
        self.call(building.CmdTag(), "/search testtag", "Found 1 object with tag 'testtag':")
        self.call(building.CmdTag(), "/search testtag2", "Found 1 object with tag 'testtag2':")
        self.call(
            building.CmdTag(),
            "/search testtag2:category1",
            "Found 1 object with tag 'testtag2' (category: 'category1'):",
        )

        self.call(building.CmdTag(), "/del Obj = testtag3", "Removed tag 'testtag3' from Obj.")
        self.call(
            building.CmdTag(),
            "/del Obj",
            "Cleared all tags from Obj: testtag, testtag2, testtag2 (category: category1)",
        )

    def test_spawn(self):
        def get_object(commandTest, obj_key):
            # A helper function to get a spawned object and
            # check that it exists in the process.
            query = search_object(obj_key)
            commandTest.assertIsNotNone(query)
            commandTest.assertTrue(bool(query))
            obj = query[0]
            commandTest.assertIsNotNone(obj)
            return obj

        # Tests "spawn" without any arguments.
        self.call(building.CmdSpawn(), " ", "Usage: spawn")

        # Tests "spawn <prototype_dictionary>" without specifying location.

        self.call(
            building.CmdSpawn(),
            "/save {'prototype_key': 'testprot', 'key':'Test Char', "
            "'typeclass':'evennia.objects.objects.DefaultCharacter'}",
            "Saved prototype: testprot",
            inputs=["y"],
        )

        self.call(
            building.CmdSpawn(),
            "/save testprot2 = {'key':'Test Char', "
            "'typeclass':'evennia.objects.objects.DefaultCharacter'}",
            "(Replacing `prototype_key` in prototype with given key.)|Saved prototype: testprot2",
            inputs=["y"],
        )

        self.call(building.CmdSpawn(), "/search ", "Key ")
        self.call(building.CmdSpawn(), "/search test;test2", "No prototypes found.")

        self.call(
            building.CmdSpawn(),
            "/save {'key':'Test Char', 'typeclass':'evennia.objects.objects.DefaultCharacter'}",
            "A prototype_key must be given, either as `prototype_key = <prototype>` or as "
            "a key 'prototype_key' inside the prototype structure.",
        )

        self.call(building.CmdSpawn(), "/list", "Key ")
        self.call(building.CmdSpawn(), "testprot", "Spawned Test Char")

        # Tests that the spawned object's location is the same as the character's location, since
        # we did not specify it.
        testchar = get_object(self, "Test Char")
        self.assertEqual(testchar.location, self.char1.location)
        testchar.delete()

        # Test "spawn <prototype_dictionary>" with a location other than the character's.
        spawnLoc = self.room2
        if spawnLoc == self.char1.location:
            # Just to make sure we use a different location, in case someone changes
            # char1's default location in the future...
            spawnLoc = self.room1

        self.call(
            building.CmdSpawn(),
            "{'prototype_key':'GOBLIN', 'typeclass':'evennia.objects.objects.DefaultCharacter', "
            "'key':'goblin', 'location':'%s'}" % spawnLoc.dbref,
            "Spawned goblin",
        )
        goblin = get_object(self, "goblin")
        # Tests that the spawned object's type is a DefaultCharacter.
        self.assertIsInstance(goblin, DefaultCharacter)
        self.assertEqual(goblin.location, spawnLoc)

        goblin.delete()

        # create prototype
        protlib.create_prototype(
            {
                "key": "Ball",
                "typeclass": "evennia.objects.objects.DefaultCharacter",
                "prototype_key": "testball",
            }
        )

        # Tests "spawn <prototype_name>"
        self.call(building.CmdSpawn(), "testball", "Spawned Ball")

        ball = get_object(self, "Ball")
        self.assertEqual(ball.location, self.char1.location)
        self.assertIsInstance(ball, DefaultObject)
        ball.delete()

        # Tests "spawn/n ..." without specifying a location.
        # Location should be "None".
        self.call(
            building.CmdSpawn(), "/n 'BALL'", "Spawned Ball"
        )  # /n switch is abbreviated form of /noloc
        ball = get_object(self, "Ball")
        self.assertIsNone(ball.location)
        ball.delete()

        self.call(
            building.CmdSpawn(),
            "/noloc {'prototype_parent':'TESTBALL', 'prototype_key': 'testball', 'location':'%s'}"
            % spawnLoc.dbref,
            "Error: Prototype testball tries to parent itself.",
        )

        # Tests "spawn/noloc ...", but DO specify a location.
        # Location should be the specified location.
        self.call(
            building.CmdSpawn(),
            "/noloc {'prototype_parent':'TESTBALL', 'key': 'Ball', 'prototype_key': 'foo',"
            " 'location':'%s'}" % spawnLoc.dbref,
            "Spawned Ball",
        )
        ball = get_object(self, "Ball")
        self.assertEqual(ball.location, spawnLoc)
        ball.delete()

        # test calling spawn with an invalid prototype.
        self.call(building.CmdSpawn(), "'NO_EXIST'", "No prototype named 'NO_EXIST' was found.")

        # Test listing commands
        self.call(building.CmdSpawn(), "/list", "Key ")

        # spawn/edit (missing prototype)
        # brings up olc menu
        msg = self.call(building.CmdSpawn(), "/edit")
        assert "Prototype wizard" in msg

        # spawn/edit with valid prototype
        # brings up olc menu loaded with prototype
        msg = self.call(building.CmdSpawn(), "/edit testball")
        assert "Prototype wizard" in msg
        assert hasattr(self.char1.ndb._menutree, "olc_prototype")
        assert (
            dict == type(self.char1.ndb._menutree.olc_prototype)
            and "prototype_key" in self.char1.ndb._menutree.olc_prototype
            and "key" in self.char1.ndb._menutree.olc_prototype
            and "testball" == self.char1.ndb._menutree.olc_prototype["prototype_key"]
            and "Ball" == self.char1.ndb._menutree.olc_prototype["key"]
        )
        assert "Ball" in msg and "testball" in msg

        # spawn/edit with valid prototype (synomym)
        msg = self.call(building.CmdSpawn(), "/edit BALL")
        assert "Prototype wizard" in msg
        assert "Ball" in msg and "testball" in msg

        # spawn/edit with invalid prototype
        msg = self.call(
            building.CmdSpawn(), "/edit NO_EXISTS", "No prototype named 'NO_EXISTS' was found."
        )

        # spawn/examine (missing prototype)
        # lists all prototypes that exist
        self.call(building.CmdSpawn(), "/examine", "You need to specify a prototype-key to show.")

        # spawn/examine with valid prototype
        # prints the prototype
        msg = self.call(building.CmdSpawn(), "/examine BALL")
        assert "Ball" in msg and "testball" in msg

        # spawn/examine with invalid prototype
        # shows error
        self.call(
            building.CmdSpawn(), "/examine NO_EXISTS", "No prototype named 'NO_EXISTS' was found."
        )


import evennia.commands.default.comms as cmd_comms  # noqa
from evennia.comms.comms import DefaultChannel  # noqa
from evennia.utils.create import create_channel  # noqa


@patch("evennia.commands.default.comms.CHANNEL_DEFAULT_TYPECLASS", DefaultChannel)
class TestCommsChannel(BaseEvenniaCommandTest):
    """
    Test the central `channel` command.

    """

    def setUp(self):
        super().setUp()
        self.channel = create_channel(key="testchannel", desc="A test channel")
        self.channel.connect(self.char1)
        self.cmdchannel = cmd_comms.CmdChannel
        self.cmdchannel.account_caller = False

    def tearDown(self):
        if self.channel.pk:
            self.channel.delete()

    # test channel command
    def test_channel__noarg(self):
        self.call(self.cmdchannel(), "", "Channel subscriptions")

    def test_channel__msg(self):
        self.channel.msg = Mock()
        self.call(self.cmdchannel(), "testchannel = Test message", "")
        self.channel.msg.assert_called_with("Test message", senders=self.char1)

    def test_channel__list(self):
        self.call(self.cmdchannel(), "/list", "Channel subscriptions")

    def test_channel__all(self):
        self.call(self.cmdchannel(), "/all", "Available channels")

    def test_channel__history(self):
        with patch("evennia.commands.default.comms.tail_log_file") as mock_tail:
            self.call(self.cmdchannel(), "/history testchannel", "")
            mock_tail.assert_called()

    def test_channel__sub(self):
        self.channel.disconnect(self.char1)

        self.call(self.cmdchannel(), "/sub testchannel", "You are now subscribed")
        self.assertTrue(self.char1 in self.channel.subscriptions.all())
        self.assertEqual(
            self.char1.nicks.nickreplace("testchannel Hello"), "channel testchannel = Hello"
        )

    def test_channel__unsub(self):
        self.call(self.cmdchannel(), "/unsub testchannel", "You un-subscribed")
        self.assertFalse(self.char1 in self.channel.subscriptions.all())

    def test_channel__alias__unalias(self):
        """Add and then remove a channel alias"""

        # add alias
        self.call(
            self.cmdchannel(),
            "/alias testchannel = foo",
            "Added/updated your alias 'foo' for channel testchannel.",
        )
        self.assertEqual(self.char1.nicks.nickreplace("foo Hello"), "channel testchannel = Hello")

        # use alias
        self.channel.msg = Mock()
        self.call(self.cmdchannel(), "foo = test message", "")
        self.channel.msg.assert_called_with("test message", senders=self.char1)

        # remove alias
        self.call(self.cmdchannel(), "/unalias foo", "Removed your channel alias 'foo'")
        self.assertEqual(self.char1.nicks.get("foo $1", category="channel"), None)

    def test_channel__mute(self):
        self.call(self.cmdchannel(), "/mute testchannel", "Muted channel testchannel")
        self.assertTrue(self.char1 in self.channel.mutelist)

    def test_channel__unmute(self):
        self.channel.mute(self.char1)

        self.call(self.cmdchannel(), "/unmute testchannel = Char1", "Un-muted channel testchannel")
        self.assertFalse(self.char1 in self.channel.mutelist)

    def test_channel__create(self):
        self.call(self.cmdchannel(), "/create testchannel2", "Created (and joined) new channel")

    def test_channel__destroy(self):
        self.channel.msg = Mock()
        self.call(
            self.cmdchannel(),
            "/destroy testchannel = delete reason",
            "Are you sure you want to delete channel ",
            inputs=["Yes"],
        )
        self.channel.msg.assert_called_with("delete reason", bypass_mute=True, senders=self.char1)

    def test_channel__desc(self):
        self.call(
            self.cmdchannel(),
            "/desc testchannel = Another description",
            "Updated channel description.",
        )

    def test_channel__lock(self):
        self.call(
            self.cmdchannel(), "/lock testchannel = foo:false()", "Added/updated lock on channel"
        )
        self.assertEqual(self.channel.locks.get("foo"), "foo:false()")

    def test_channel__unlock(self):
        self.channel.locks.add("foo:true()")
        self.call(self.cmdchannel(), "/unlock testchannel = foo", "Removed lock from channel")
        self.assertEqual(self.channel.locks.get("foo"), "")

    def test_channel__boot(self):
        self.channel.connect(self.char2)
        self.assertTrue(self.char2 in self.channel.subscriptions.all())
        self.channel.msg = Mock()
        self.char2.msg = Mock()

        self.call(
            self.cmdchannel(),
            "/boot testchannel = Char2 : Booting from channel!",
            "Are you sure ",
            inputs=["Yes"],
        )
        self.channel.msg.assert_called_with(
            "Char2 was booted from channel by Char. Reason: Booting from channel!"
        )
        self.char2.msg.assert_called_with(
            "You were booted from channel testchannel by Char. Reason: Booting from channel!"
        )

    def test_channel__ban__unban(self):
        """Test first ban and then unban"""

        # ban
        self.channel.connect(self.char2)
        self.assertTrue(self.char2 in self.channel.subscriptions.all())
        self.channel.msg = Mock()
        self.char2.msg = Mock()

        self.call(
            self.cmdchannel(),
            "/ban testchannel = Char2 : Banning from channel!",
            "Are you sure ",
            inputs=["Yes"],
        )
        self.channel.msg.assert_called_with(
            "Char2 was booted from channel by Char. Reason: Banning from channel!"
        )
        self.char2.msg.assert_called_with(
            "You were booted from channel testchannel by Char. Reason: Banning from channel!"
        )
        self.assertTrue(self.char2 in self.channel.banlist)

        # unban

        self.call(
            self.cmdchannel(),
            "/unban testchannel = Char2",
            "Un-banned Char2 from channel testchannel",
        )
        self.assertFalse(self.char2 in self.channel.banlist)

    def test_channel__who(self):
        self.call(self.cmdchannel(), "/who testchannel", "Subscribed to testchannel:\nChar")


from evennia.commands.default import comms  # noqa


class TestComms(BaseEvenniaCommandTest):
    def test_page(self):
        self.call(
            comms.CmdPage(),
            "TestAccount2 = Test",
            "TestAccount2 is offline. They will see your message if they list their pages later."
            "|You paged TestAccount2 with: 'Test'.",
            receiver=self.account,
        )


@override_settings(DISCORD_BOT_TOKEN="notarealtoken", DISCORD_ENABLED=True)
class TestDiscord(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.channel = create.create_channel(key="testchannel", desc="A test channel")
        self.cmddiscord = cmd_comms.CmdDiscord2Chan
        self.cmddiscord.account_caller = False
        # create bot manually so it doesn't get started
        self.discordbot = create.create_account(
            "DiscordBot", None, None, typeclass="evennia.accounts.bots.DiscordBot"
        )

    def tearDown(self):
        if self.channel.pk:
            self.channel.delete()

    @parameterized.expand(
        [
            ("", "No Discord connections found."),
            ("/list", "No Discord connections found."),
            ("/guild", "Messages to Evennia will include the Discord server."),
            ("/channel", "Relayed messages will include the originating channel."),
        ]
    )
    def test_discord__switches(self, cmd_args, expected):
        self.call(self.cmddiscord(), cmd_args, expected)

    def test_discord__linking(self):
        self.call(
            self.cmddiscord(), "nosuchchannel = 5555555", "There is no channel 'nosuchchannel'"
        )
        self.call(
            self.cmddiscord(),
            "testchannel = 5555555",
            "Discord connection created: testchannel <-> #5555555",
        )
        self.assertTrue(self.discordbot in self.channel.subscriptions.all())
        self.assertTrue(("testchannel", "5555555") in self.discordbot.db.channels)
        self.call(self.cmddiscord(), "testchannel = 5555555", "Those channels are already linked.")

    def test_discord__list(self):
        self.discordbot.db.channels = [("testchannel", "5555555")]
        cmdobj = self.cmddiscord()
        cmdobj.msg = lambda text, **kwargs: setattr(self, "out", str(text))
        self.call(cmdobj, "", None)
        self.assertIn("testchannel", self.out)
        self.assertIn("5555555", self.out)
        self.call(cmdobj, "testchannel", None)
        self.assertIn("testchannel", self.out)
        self.assertIn("5555555", self.out)


class TestBatchProcess(BaseEvenniaCommandTest):
    """
    Test the batch processor.

    """

    # there is some sort of issue with the mock; it needs to loaded once to work
    from evennia.contrib.tutorials.red_button import red_button  # noqa

    @patch("evennia.contrib.tutorials.red_button.red_button.repeat")
    @patch("evennia.contrib.tutorials.red_button.red_button.delay")
    def test_batch_commands(self, mock_tutorials, mock_repeat):
        # cannot test batchcode here, it must run inside the server process
        self.call(
            batchprocess.CmdBatchCommands(),
            "batchprocessor.example_batch_cmds",
            "Running Batch-command processor - Automatic mode for"
            " batchprocessor.example_batch_cmds",
        )
        # we make sure to delete the button again here to stop the running reactor
        confirm = building.CmdDestroy.confirm
        building.CmdDestroy.confirm = False
        self.call(building.CmdDestroy(), "button", "button was destroyed.")
        building.CmdDestroy.confirm = confirm
        mock_repeat.assert_called()


class CmdInterrupt(Command):

    key = "interrupt"

    def parse(self):
        raise InterruptCommand

    def func(self):
        self.msg("in func")


class TestInterruptCommand(BaseEvenniaCommandTest):
    def test_interrupt_command(self):
        ret = self.call(CmdInterrupt(), "")
        self.assertEqual(ret, "")


class TestUnconnectedCommand(BaseEvenniaCommandTest):
    def test_info_command(self):
        # instead of using SERVER_START_TIME (0), we use 86400 because Windows won't let us use anything lower
        gametime.SERVER_START_TIME = 86400
        expected = (
            "## BEGIN INFO 1.1\nName: %s\nUptime: %s\nConnected: %d\nVersion: Evennia %s\n## END"
            " INFO"
            % (
                settings.SERVERNAME,
                datetime.datetime.fromtimestamp(gametime.SERVER_START_TIME).ctime(),
                SESSIONS.account_count(),
                utils.get_evennia_version(),
            )
        )
        self.call(unloggedin.CmdUnconnectedInfo(), "", expected)
        del gametime.SERVER_START_TIME


# Test syscommands


class TestSystemCommands(BaseEvenniaCommandTest):
    def test_simple_defaults(self):
        self.call(syscommands.SystemNoInput(), "")
        self.call(syscommands.SystemNoMatch(), "Huh?")

    def test_multimatch(self):
        # set up fake matches and store on command instance
        cmdset = CmdSet()
        cmdset.add(general.CmdLook())
        cmdset.add(general.CmdLook())
        matches = cmdparser.build_matches("look", cmdset)

        multimatch = syscommands.SystemMultimatch()
        multimatch.matches = matches

        self.call(multimatch, "look", "")
