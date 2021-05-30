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
from anything import Anything

from parameterized import parameterized
from django.conf import settings
from unittest.mock import patch, Mock, MagicMock

from evennia import DefaultRoom, DefaultExit, ObjectDB
from evennia.commands.default.cmdset_character import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from evennia.commands.default import (
    help as help_module,
    general,
    system,
    admin,
    account,
    building,
    batchprocess,
    comms,
    unloggedin,
    syscommands,
)
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.command import Command, InterruptCommand
from evennia.commands import cmdparser
from evennia.commands.cmdset import CmdSet
from evennia.utils import ansi, utils, gametime
from evennia.server.sessionhandler import SESSIONS
from evennia import search_object
from evennia import DefaultObject, DefaultCharacter
from evennia.prototypes import prototypes as protlib


# set up signal here since we are not starting the server

_RE_STRIP_EVMENU = re.compile(r"^\+|-+\+|\+-+|--+|\|(?:\s|$)", re.MULTILINE)


# ------------------------------------------------------------
# Command testing
# ------------------------------------------------------------

@patch("evennia.server.portal.portal.LoopingCall", new=MagicMock())
class CommandTest(EvenniaTest):
    """
    Tests a Command by running it and comparing what messages it sends with
    expected values. This tests without actually spinning up the cmdhandler
    for every test, which is more controlled.

    Example:
    ::

        from commands.echo import CmdEcho

        class MyCommandTest(CommandTest):

            def test_echo(self):
                '''
                Test that the echo command really returns
                what you pass into it.
                '''
                self.call(MyCommand(), "hello world!",
                          "You hear your echo: 'Hello world!'")

    """

    # formatting for .call's error message
    _ERROR_FORMAT = """
=========================== Wanted message ===================================
{expected_msg}
=========================== Returned message =================================
{returned_msg}
==============================================================================
""".rstrip()

    def call(
        self,
        cmdobj,
        input_args,
        msg=None,
        cmdset=None,
        noansi=True,
        caller=None,
        receiver=None,
        cmdstring=None,
        obj=None,
        inputs=None,
        raw_string=None,
    ):
        """
        Test a command by assigning all the needed properties to a cmdobj and
        running the sequence. The resulting `.msg` calls will be mocked and
        the text= calls to them compared to a expected output.

        Args:
            cmdobj (Command): The command object to use.
            input_args (str): This should be the full input the Command should
                see, such as 'look here'. This will become `.args` for the Command
                instance to parse.
            msg (str or dict, optional): This is the expected return value(s)
                returned through `caller.msg(text=...)` calls in the command. If a string, the
                receiver is controlled with the `receiver` kwarg (defaults to `caller`).
                If this is a `dict`, it is a mapping
                `{receiver1: "expected1", receiver2: "expected2",...}` and `receiver` is
                ignored. The message(s) are compared with the actual messages returned
                to the receiver(s) as the Command runs. Each check uses `.startswith`,
                so you can choose to only include the first part of the
                returned message if that's enough to verify a correct result. EvMenu
                decorations (like borders) are stripped and should not be included. This
                should also not include color tags unless `noansi=False`.
                If the command returns texts in multiple separate `.msg`-
                calls to a receiver, separate these with `|` if `noansi=True`
                (default) and `||` if `noansi=False`. If no `msg` is given (`None`),
                then no automatic comparison will be done.
            cmdset (str, optional): If given, make `.cmdset` available on the Command
                instance as it runs. While `.cmdset` is normally available on the
                Command instance by default, this is usually only used by
                commands that explicitly operates/displays cmdsets, like
                `examine`.
            noansi (str, optional): By default the color tags of the `msg` is
                ignored, this makes them significant. If unset, `msg` must contain
                the same color tags as the actual return message.
            caller (Object or Account, optional): By default `self.char1` is used as the
                command-caller (the `.caller` property on the Command). This allows to
                execute with another caller, most commonly an Account.
            receiver (Object or Account, optional): This is the object to receive the
                return messages we want to test. By default this is the same as `caller`
                (which in turn defaults to is `self.char1`). Note that if `msg` is
                a `dict`, this is ignored since the receiver is already specified there.
            cmdstring (str, optional): Normally this is the Command's `key`.
                This allows for tweaking the `.cmdname` property of the
                Command`.  This isb used for commands with multiple aliases,
                where the command explicitly checs which alias was used to
                determine its functionality.
            obj (str, optional): This sets the `.obj` property of the Command - the
                object on which the Command 'sits'. By default this is the same as `caller`.
                This can be used for testing on-object Command interactions.
            inputs (list, optional): A list of strings to pass to functions that pause to
                take input from the user (normally using `@interactive` and
                `ret = yield(question)` or `evmenu.get_input`). Each  element of the
                list will be passed into the command as if the user wrote that at the prompt.
            raw_string (str, optional): Normally the `.raw_string` property  is set as
                a combination of your `key/cmdname` and `input_args`. This allows
                direct control of what this is, for example for testing edge cases
                or malformed inputs.

        Returns:
            str or dict: The message sent to `receiver`, or a dict of
                `{receiver: "msg", ...}` if multiple are given. This is usually
                only used with `msg=None` to do the validation externally.

        Raises:
            AssertionError: If the returns of `.msg` calls (tested with `.startswith`) does not
                match `expected_input`.

        Notes:
            As part of the tests, all methods of the Command will be called in
            the proper order:

            - cmdobj.at_pre_cmd()
            - cmdobj.parse()
            - cmdobj.func()
            - cmdobj.at_post_cmd()

        """
        # The `self.char1` is created in the `EvenniaTest` base along with
        # other helper objects like self.room and self.obj
        caller = caller if caller else self.char1
        cmdobj.caller = caller
        cmdobj.cmdname = cmdstring if cmdstring else cmdobj.key
        cmdobj.raw_cmdname = cmdobj.cmdname
        cmdobj.cmdstring = cmdobj.cmdname  # deprecated
        cmdobj.args = input_args
        cmdobj.cmdset = cmdset
        cmdobj.session = SESSIONS.session_from_sessid(1)
        cmdobj.account = self.account
        cmdobj.raw_string = raw_string if raw_string is not None else cmdobj.key + " " + input_args
        cmdobj.obj = obj or (caller if caller else self.char1)
        inputs = inputs or []

        # set up receivers
        receiver_mapping = {}
        if isinstance(msg, dict):
            # a mapping {receiver: msg, ...}
            receiver_mapping = {recv: str(msg).strip() if msg else None
                                for recv, msg in msg.items()}
        else:
            # a single expected string and thus a single receiver (defaults to caller)
            receiver = receiver if receiver else caller
            receiver_mapping[receiver] = str(msg).strip() if msg is not None else None

        unmocked_msg_methods = {}
        for receiver in receiver_mapping:
            # save the old .msg method so we can get it back
            # cleanly  after the test
            unmocked_msg_methods[receiver] = receiver.msg
            # replace normal `.msg` with a mock
            receiver.msg = Mock()

        # Run the methods of the Command. This mimics what happens in the
        # cmdhandler. This will have the mocked .msg be called as part of the
        # execution. Mocks remembers what was sent to them so we will be able
        # to retrieve what was sent later.
        try:
            if cmdobj.at_pre_cmd():
                return
            cmdobj.parse()
            ret = cmdobj.func()

            # handle func's with yield in them (making them generators)
            if isinstance(ret, types.GeneratorType):
                while True:
                    try:
                        inp = inputs.pop() if inputs else None
                        if inp:
                            try:
                                # this mimics a user's reply to a prompt
                                ret.send(inp)
                            except TypeError:
                                next(ret)
                                ret = ret.send(inp)
                        else:
                            # non-input yield, like yield(10). We don't pause
                            # but fire it immediately.
                            next(ret)
                    except StopIteration:
                        break

            cmdobj.at_post_cmd()
        except StopIteration:
            pass
        except InterruptCommand:
            pass

        for inp in inputs:
            # if there are any inputs left, we may have a non-generator
            # input to handle (get_input/ask_yes_no that uses a separate
            # cmdset rather than a yield
            caller.execute_cmd(inp)

        # At this point the mocked .msg methods on each receiver will have
        # stored all calls made to them (that's a basic function of the Mock
        # class). We will not extract them and compare to what we expected to
        # go to each receiver.

        returned_msgs = {}
        for receiver, expected_msg in receiver_mapping.items():
            # get the stored messages from the Mock with Mock.mock_calls.
            stored_msg = [
                args[0] if args and args[0] else kwargs.get("text", utils.to_str(kwargs))
                for name, args, kwargs in receiver.msg.mock_calls
            ]
            # we can return this now, we are done using the mock
            receiver.msg = unmocked_msg_methods[receiver]

            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [str(smsg[0])
                          if isinstance(smsg, tuple) else str(smsg) for smsg in stored_msg]
            if expected_msg is None:
                # no expected_msg; just build the returned_msgs dict

                returned_msg = "\n".join(str(msg) for msg in stored_msg)
                returned_msgs[receiver] = ansi.parse_ansi(returned_msg, strip_ansi=noansi).strip()
            else:
                # compare messages to expected

                # set our separator for returned messages based on parsing ansi or not
                msg_sep = "|" if noansi else "||"

                # We remove Evmenu decorations since that just makes it harder
                # to write the comparison string. We also strip ansi before this
                # comparison since otherwise it would mess with the regex.
                returned_msg = msg_sep.join(
                    _RE_STRIP_EVMENU.sub(
                        "", ansi.parse_ansi(mess, strip_ansi=noansi))
                    for mess in stored_msg).strip()

                # this is the actual test
                if expected_msg == "" and returned_msg or not returned_msg.startswith(expected_msg):
                    # failed the test
                    raise AssertionError(
                        self._ERROR_FORMAT.format(
                            expected_msg=expected_msg, returned_msg=returned_msg)
                    )
                # passed!
                returned_msgs[receiver] = returned_msg

        if len(returned_msgs) == 1:
            return list(returned_msgs.values())[0]
        return returned_msgs


# ------------------------------------------------------------
# Individual module Tests
# ------------------------------------------------------------


class TestGeneral(CommandTest):
    def test_look(self):
        rid = self.room1.id
        self.call(general.CmdLook(), "here", "Room(#{})\nroom_desc".format(rid))

    def test_home(self):
        self.call(general.CmdHome(), "", "You are already home")

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


class TestHelp(CommandTest):

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
            cmdset=CharacterCmdSet()
        )
        self.call(help_module.CmdHelp(), "testhelp", "Help for testhelp", cmdset=CharacterCmdSet())

    @parameterized.expand([
        ("test",  # main help entry
         "Help for test\n\n"
         "Main help text\n\n"
         "Subtopics:\n"
         "  test/creating extra stuff"
         "  test/something else"
         "  test/more"
         ),
        ("test/creating extra stuff",  # subtopic, full match
         "Help for test/creating extra stuff\n\n"
         "Help on creating extra stuff.\n\n"
         "Subtopics:\n"
         "  test/creating extra stuff/subsubtopic\n"
         ),
        ("test/creating",  # startswith-match
         "Help for test/creating extra stuff\n\n"
         "Help on creating extra stuff.\n\n"
         "Subtopics:\n"
         "  test/creating extra stuff/subsubtopic\n"
         ),
        ("test/extra",  # partial match
         "Help for test/creating extra stuff\n\n"
         "Help on creating extra stuff.\n\n"
         "Subtopics:\n"
         "  test/creating extra stuff/subsubtopic\n"
         ),
        ("test/extra/subsubtopic",  # partial subsub-match
         "Help for test/creating extra stuff/subsubtopic\n\n"
         "A subsubtopic text"
         ),
        ("test/creating extra/subsub",  # partial subsub-match
         "Help for test/creating extra stuff/subsubtopic\n\n"
         "A subsubtopic text"
         ),
        ("test/Something else",  # case
         "Help for test/something else\n\n"
         "Something else"
         ),
        ("test/More",  # case
         "Help for test/more\n\n"
         "Another text\n\n"
         "Subtopics:\n"
         "  test/more/second-more"
         ),
        ("test/More/Second-more",
         "Help for test/more/second-more\n\n"
         "The Second More text.\n\n"
         "Subtopics:\n"
         "  test/more/second-more/more again"
         "  test/more/second-more/third more"
         ),
        ("test/More/-more",  # partial match
         "Help for test/more/second-more\n\n"
         "The Second More text.\n\n"
         "Subtopics:\n"
         "  test/more/second-more/more again"
         "  test/more/second-more/third more"
         ),
        ("test/more/second/more again",
         "Help for test/more/second-more/more again\n\n"
         "Even more text.\n"
         ),
        ("test/more/second/third",
         "Help for test/more/second-more/third more\n\n"
         "Third more text\n"
         ),
    ])
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

        self.call(help_module.CmdHelp(),
                  helparg,
                  expected,
                  cmdset=TestCmdSet())


class TestSystem(CommandTest):
    def test_py(self):
        # we are not testing CmdReload, CmdReset and CmdShutdown, CmdService or CmdTime
        # since the server is not running during these tests.
        self.call(system.CmdPy(), "1+2", ">>> 1+2|3")
        self.call(system.CmdPy(), "/clientraw 1+2", ">>> 1+2|3")

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
        self.call(admin.CmdBan(), "Char", "Name-Ban char was added.")

    def test_force(self):
        cid = self.char2.id
        self.call(
            admin.CmdForce(),
            "Char2=say test",
            'Char2(#{}) says, "test"|You have forced Char2 to: say test'.format(cid),
        )


class TestAccount(CommandTest):
    def test_ooc_look(self):
        if settings.MULTISESSION_MODE < 2:
            self.call(
                account.CmdOOCLook(), "", "You are out-of-character (OOC).", caller=self.account
            )
        if settings.MULTISESSION_MODE == 2:
            self.call(
                account.CmdOOCLook(),
                "",
                "Account TestAccount (you are OutofCharacter)",
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


class TestBuilding(CommandTest):
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
        self.call(building.CmdExamine(), "self/test", "Persistent attribute(s):\n  test = testval")
        self.call(building.CmdExamine(), "NotFound", "Could not find 'NotFound'.")
        self.call(building.CmdExamine(), "out", "Name/key: out")

        # escape inlinefuncs
        self.char1.db.test2 = "this is a $random() value."
        self.call(
            building.CmdExamine(),
            "self/test2",
            "Persistent attribute(s):\n  test2 = this is a \$random() value.",
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
            "Created attribute Obj/test1 = 'value1'",
        )
        self.call(
            building.CmdSetAttribute(),
            'Obj2/test2="value2"',
            "Created attribute Obj2/test2 = 'value2'",
        )
        self.call(building.CmdSetAttribute(), "Obj2/test2", "Attribute Obj2/test2 = value2")
        self.call(building.CmdSetAttribute(), "Obj2/NotFound", "Obj2 has no attribute 'notfound'.")

        with patch("evennia.commands.default.building.EvEditor") as mock_ed:
            self.call(building.CmdSetAttribute(), "/edit Obj2/test3")
            mock_ed.assert_called_with(self.char1, Anything, Anything, key="Obj2/test3")

        self.call(
            building.CmdSetAttribute(),
            'Obj2/test3="value3"',
            "Created attribute Obj2/test3 = 'value3'",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj2/test3 = ",
            "Deleted attribute 'test3' (= True) from Obj2.",
        )

        self.call(
            building.CmdCpAttr(),
            "/copy Obj2/test2 = Obj2/test3",
            'cpattr: Extra switch "/copy" ignored.|\nCopied Obj2.test2 -> Obj2.test3. '
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
            building.CmdSetAttribute(), "Obj/test1=[1,2]", "Created attribute Obj/test1 = [1, 2]"
        )
        self.call(building.CmdSetAttribute(), "Obj/test1", "Attribute Obj/test1 = [1, 2]")
        self.call(building.CmdSetAttribute(), "Obj/test1[0]", "Attribute Obj/test1[0] = 1")
        self.call(building.CmdSetAttribute(), "Obj/test1[1]", "Attribute Obj/test1[1] = 2")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[0] = 99",
            "Modified attribute Obj/test1 = [99, 2]",
        )
        self.call(building.CmdSetAttribute(), "Obj/test1[0]", "Attribute Obj/test1[0] = 99")
        # list delete
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[0] =",
            "Deleted attribute 'test1[0]' (= nested) from Obj.",
        )
        self.call(building.CmdSetAttribute(), "Obj/test1[0]", "Attribute Obj/test1[0] = 2")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[1]",
            "Obj has no attribute 'test1[1]'. (Nested lookups attempted)",
        )
        # Delete non-existent
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[5] =",
            "Obj has no attribute 'test1[5]'. (Nested lookups attempted)",
        )
        # Append
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[+] = 42",
            "Modified attribute Obj/test1 = [2, 42]",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test1[+0] = -1",
            "Modified attribute Obj/test1 = [-1, 2, 42]",
        )

        # dict - removing white space proves real parsing
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2={ 'one': 1, 'two': 2 }",
            "Created attribute Obj/test2 = {'one': 1, 'two': 2}",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test2", "Attribute Obj/test2 = {'one': 1, 'two': 2}"
        )
        self.call(building.CmdSetAttribute(), "Obj/test2['one']", "Attribute Obj/test2['one'] = 1")
        self.call(building.CmdSetAttribute(), "Obj/test2['one]", "Attribute Obj/test2['one] = 1")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['one']=99",
            "Modified attribute Obj/test2 = {'one': 99, 'two': 2}",
        )
        self.call(building.CmdSetAttribute(), "Obj/test2['one']", "Attribute Obj/test2['one'] = 99")
        self.call(building.CmdSetAttribute(), "Obj/test2['two']", "Attribute Obj/test2['two'] = 2")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three']",
            "Obj has no attribute 'test2[+'three']'. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three'] = 3",
            "Modified attribute Obj/test2 = {'one': 99, 'two': 2, \"+'three'\": 3}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+'three'] =",
            "Deleted attribute 'test2[+'three']' (= nested) from Obj.",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['three']=3",
            "Modified attribute Obj/test2 = {'one': 99, 'two': 2, 'three': 3}",
        )
        # Dict delete
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['two'] =",
            "Deleted attribute 'test2['two']' (= nested) from Obj.",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['two']",
            "Obj has no attribute 'test2['two']'. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test2", "Attribute Obj/test2 = {'one': 99, 'three': 3}"
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[0]",
            "Obj has no attribute 'test2[0]'. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2['five'] =",
            "Obj has no attribute 'test2['five']'. (Nested lookups attempted)",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+]=42",
            "Modified attribute Obj/test2 = {'one': 99, 'three': 3, '+': 42}",
        )
        self.call(
            building.CmdSetAttribute(),
            "Obj/test2[+1]=33",
            "Modified attribute Obj/test2 = {'one': 99, 'three': 3, '+': 42, '+1': 33}",
        )

        # tuple
        self.call(
            building.CmdSetAttribute(), "Obj/tup = (1,2)", "Created attribute Obj/tup = (1, 2)"
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
            "Obj has no attribute 'tup[1]'. (Nested lookups attempted)",
        )

        # Deaper nesting
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3=[{'one': 1}]",
            "Created attribute Obj/test3 = [{'one': 1}]",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test3[0]['one']", "Attribute Obj/test3[0]['one'] = 1"
        )
        self.call(building.CmdSetAttribute(), "Obj/test3[0]", "Attribute Obj/test3[0] = {'one': 1}")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test3[0]['one'] =",
            "Deleted attribute 'test3[0]['one']' (= nested) from Obj.",
        )
        self.call(building.CmdSetAttribute(), "Obj/test3[0]", "Attribute Obj/test3[0] = {}")
        self.call(building.CmdSetAttribute(), "Obj/test3", "Attribute Obj/test3 = [{}]")

        # Naughty keys
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]='foo'",
            "Created attribute Obj/test4[0] = 'foo'",
        )
        self.call(building.CmdSetAttribute(), "Obj/test4[0]", "Attribute Obj/test4[0] = foo")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4=[{'one': 1}]",
            "Created attribute Obj/test4 = [{'one': 1}]",
        )
        self.call(
            building.CmdSetAttribute(), "Obj/test4[0]['one']", "Attribute Obj/test4[0]['one'] = 1"
        )
        # Prefer nested items
        self.call(building.CmdSetAttribute(), "Obj/test4[0]", "Attribute Obj/test4[0] = {'one': 1}")
        self.call(
            building.CmdSetAttribute(), "Obj/test4[0]['one']", "Attribute Obj/test4[0]['one'] = 1"
        )
        # Restored access
        self.call(building.CmdWipe(), "Obj/test4", "Wiped attributes test4 on Obj.")
        self.call(building.CmdSetAttribute(), "Obj/test4[0]", "Attribute Obj/test4[0] = foo")
        self.call(
            building.CmdSetAttribute(),
            "Obj/test4[0]['one']",
            "Obj has no attribute 'test4[0]['one']'.",
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
        self.call(building.CmdListCmdSets(), "",
                  "<CmdSetHandler> stack:\n <CmdSet DefaultCharacter, Union, perm, prio 0>:")
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
            "Obj already has the typeclass 'evennia.objects.objects.DefaultExit'. Use /force to override.",
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
            "Obj updated its existing typeclass (evennia.objects.objects.DefaultObject).\n"
            "Only the at_object_creation hook was run (update mode). Attributes set before swap were not removed.",
            cmdstring="update",
        )
        self.call(
            building.CmdTypeclass(),
            "/reset/force Obj=evennia.objects.objects.DefaultObject",
            "Obj updated its existing typeclass (evennia.objects.objects.DefaultObject).\n"
            "All object creation hooks were run. All old attributes where deleted before the swap.",
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
                "replaced_obj changed typeclass from "
                "evennia.objects.objects.DefaultObject to "
                "typeclasses.objects.Object.\nAll object creation hooks were "
                "run. Attributes set before swap were not removed. Prototype "
                "'replaced_obj' was successfully applied over the object type.",
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
        self.call(building.CmdScript(), "Obj = ", "No scripts defined on Obj")
        self.call(
            building.CmdScript(), "Obj = scripts.Script", "Script scripts.Script successfully added"
        )
        self.call(building.CmdScript(), "", "Usage: ")
        self.call(
            building.CmdScript(),
            "= Obj",
            "To create a global script you need scripts/add <typeclass>.",
        )
        self.call(building.CmdScript(), "Obj ", "dbref ")

        self.call(
            building.CmdScript(), "/start Obj", "1 scripts started on Obj"
        )  # we allow running start again; this should still happen
        self.call(building.CmdScript(), "/stop Obj", "Stopping script")

        self.call(
            building.CmdScript(), "Obj = scripts.Script", "Script scripts.Script successfully added"
        )
        self.call(
            building.CmdScript(),
            "/start Obj = scripts.Script",
            "Script scripts.Script could not be (re)started.",
        )
        self.call(
            building.CmdScript(),
            "/stop Obj = scripts.Script",
            "Script stopped and removed from object.",
        )

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
            "Tags on Obj: 'testtag', 'testtag2', " "'testtag2' (category: category1), 'testtag3'",
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
            "/save {'key':'Test Char', " "'typeclass':'evennia.objects.objects.DefaultCharacter'}",
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
            "/noloc {'prototype_parent':'TESTBALL', 'key': 'Ball', 'prototype_key': 'foo', 'location':'%s'}"
            % spawnLoc.dbref,
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


class TestComms(CommandTest):
    def setUp(self):
        super(CommandTest, self).setUp()
        self.call(
            comms.CmdChannelCreate(),
            "testchan;test=Test Channel",
            "Created channel testchan and connected to it.",
            receiver=self.account,
        )

    def test_toggle_com(self):
        self.call(
            comms.CmdAddCom(),
            "tc = testchan",
            "You are already connected to channel testchan.| You can now",
            receiver=self.account,
        )
        self.call(
            comms.CmdDelCom(),
            "tc",
            "Any alias 'tc' for channel testchan was cleared.",
            receiver=self.account,
        )

    def test_all_com(self):
        self.call(
            comms.CmdAllCom(),
            "",
            "Available channels:",
            receiver=self.account,
        )

    def test_clock(self):
        self.call(
            comms.CmdClock(),
            "testchan=send:all()",
            "Lock(s) applied. Current locks on testchan:",
            receiver=self.account,
        )

    def test_cdesc(self):
        self.call(
            comms.CmdCdesc(),
            "testchan = Test Channel",
            "Description of channel 'testchan' set to 'Test Channel'.",
            receiver=self.account,
        )

    def test_cwho(self):
        self.call(
            comms.CmdCWho(),
            "testchan",
            "Channel subscriptions\ntestchan:\n  TestAccount",
            receiver=self.account,
        )

    def test_page(self):
        self.call(
            comms.CmdPage(),
            "TestAccount2 = Test",
            "TestAccount2 is offline. They will see your message if they list their pages later."
            "|You paged TestAccount2 with: 'Test'.",
            receiver=self.account,
        )

    def test_cboot(self):
        # No one else connected to boot
        self.call(
            comms.CmdCBoot(),
            "",
            "Usage: cboot[/quiet] <channel> = <account> [:reason]",
            receiver=self.account,
        )

    def test_cdestroy(self):
        self.call(
            comms.CmdCdestroy(),
            "testchan",
            "[testchan] TestAccount: testchan is being destroyed. Make sure to change your aliases."
            "|Channel 'testchan' was destroyed.",
            receiver=self.account,
        )


from evennia.utils.create import create_channel  # noqa

class TestCommsChannel(CommandTest):
    """
    Test the central `channel` command.

    """
    def setUp(self):
        super(CommandTest, self).setUp()
        self.channel = create_channel(
            key="testchannel",
            desc="A test channel")
        self.channel.connect(self.char1)
        self.cmdchannel = comms.CmdChannel
        self.cmdchannel.account_caller = False

    def tearDown(self):
        if self.channel.pk:
            self.channel.delete()

    # test channel command
    def test_channel__noarg(self):
        self.call(
            self.cmdchannel(),
            "",
            "Channel subscriptions"
        )

    def test_channel__msg(self):
        self.channel.msg = Mock()
        self.call(
            self.cmdchannel(),
            "testchannel = Test message",
            ""
        )
        self.channel.msg.assert_called_with("Test message", senders=self.char1)

    def test_channel__list(self):
        self.call(
            self.cmdchannel(),
            "/list",
            "Channel subscriptions"
        )

    def test_channel__all(self):
        self.call(
            self.cmdchannel(),
            "/all",
            "Available channels"
        )

    def test_channel__history(self):
        with patch("evennia.commands.default.comms.tail_log_file") as mock_tail:
            self.call(
                self.cmdchannel(),
                "/history testchannel",
                ""
            )
            mock_tail.assert_called()

    def test_channel__sub(self):
        self.channel.disconnect(self.char1)

        self.call(
            self.cmdchannel(),
            "/sub testchannel",
            "You are now subscribed"
        )
        self.assertTrue(self.char1 in self.channel.subscriptions.all())
        self.assertEqual(self.char1.nicks.nickreplace("testchannel Hello"), "channel testchannel = Hello")

    def test_channel__unsub(self):
        self.call(
            self.cmdchannel(),
            "/unsub testchannel",
            "You un-subscribed"
        )
        self.assertFalse(self.char1 in self.channel.subscriptions.all())

    def test_channel__alias__unalias(self):
        """Add and then remove a channel alias"""
        # add alias
        self.call(
            self.cmdchannel(),
            "/alias testchannel = foo",
            "Added/updated your alias 'foo' for channel testchannel."
        )
        self.assertEqual(
            self.char1.nicks.nickreplace('foo Hello'), "channel testchannel = Hello")

        # use alias
        self.channel.msg = Mock()
        self.call(
            self.cmdchannel(),
            "foo = test message",
            "")
        self.channel.msg.assert_called_with("test message", senders=self.char1)

        # remove alias
        self.call(
            self.cmdchannel(),
            "/unalias foo",
            "Removed your channel alias 'foo'"
        )
        self.assertEqual(self.char1.nicks.get('foo $1', category="channel"), None)

    def test_channel__mute(self):
        self.call(
            self.cmdchannel(),
            "/mute testchannel",
            "Muted channel testchannel"
        )
        self.assertTrue(self.char1 in self.channel.mutelist)

    def test_channel__unmute(self):
        self.channel.mute(self.char1)

        self.call(
            self.cmdchannel(),
            "/unmute testchannel = Char1",
            "Un-muted channel testchannel"
        )
        self.assertFalse(self.char1 in self.channel.mutelist)

    def test_channel__create(self):
        self.call(
            self.cmdchannel(),
            "/create testchannel2",
            "Created (and joined) new channel"
        )

    def test_channel__destroy(self):
        self.channel.msg = Mock()
        self.call(
            self.cmdchannel(),
            "/destroy testchannel = delete reason",
            "Are you sure you want to delete channel ",
            inputs=['Yes']
        )
        self.channel.msg.assert_called_with(
            "delete reason", bypass_mute=True, senders=self.char1)

    def test_channel__desc(self):
        self.call(
            self.cmdchannel(),
            "/desc testchannel = Another description",
            "Updated channel description."
        )

    def test_channel__lock(self):
        self.call(
            self.cmdchannel(),
            "/lock testchannel = foo:false()",
            "Added/updated lock on channel"
        )
        self.assertEqual(self.channel.locks.get('foo'), 'foo:false()')

    def test_channel__unlock(self):
        self.channel.locks.add("foo:true()")
        self.call(
            self.cmdchannel(),
            "/unlock testchannel = foo",
            "Removed lock from channel"
        )
        self.assertEqual(self.channel.locks.get('foo'), '')

    def test_channel__boot(self):
        self.channel.connect(self.char2)
        self.assertTrue(self.char2 in self.channel.subscriptions.all())
        self.channel.msg = Mock()
        self.char2.msg = Mock()

        self.call(
            self.cmdchannel(),
            "/boot testchannel = Char2 : Booting from channel!",
            "Are you sure ",
            inputs=["Yes"]
        )
        self.channel.msg.assert_called_with(
            "Char2 was booted from channel by Char. Reason: Booting from channel!")
        self.char2.msg.assert_called_with(
            "You were booted from channel testchannel by Char. Reason: Booting from channel!")

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
            inputs=["Yes"]
        )
        self.channel.msg.assert_called_with(
            "Char2 was booted from channel by Char. Reason: Banning from channel!")
        self.char2.msg.assert_called_with(
            "You were booted from channel testchannel by Char. Reason: Banning from channel!")
        self.assertTrue(self.char2 in self.channel.banlist)

        # unban

        self.call(
            self.cmdchannel(),
            "/unban testchannel = Char2",
            "Un-banned Char2 from channel testchannel"
        )
        self.assertFalse(self.char2 in self.channel.banlist)

    def test_channel__who(self):
        self.call(
            self.cmdchannel(),
            "/who testchannel",
            "Subscribed to testchannel:\nChar"
        )


class TestBatchProcess(CommandTest):

    @patch("evennia.contrib.tutorial_examples.red_button.repeat")
    @patch("evennia.contrib.tutorial_examples.red_button.delay")
    def test_batch_commands(self, mock_delay, mock_repeat):
        # cannot test batchcode here, it must run inside the server process
        self.call(
            batchprocess.CmdBatchCommands(),
            "example_batch_cmds",
            "Running Batch-command processor - Automatic mode for example_batch_cmds",
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


class TestInterruptCommand(CommandTest):
    def test_interrupt_command(self):
        ret = self.call(CmdInterrupt(), "")
        self.assertEqual(ret, "")


class TestUnconnectedCommand(CommandTest):
    def test_info_command(self):
        # instead of using SERVER_START_TIME (0), we use 86400 because Windows won't let us use anything lower
        gametime.SERVER_START_TIME = 86400
        expected = (
            "## BEGIN INFO 1.1\nName: %s\nUptime: %s\nConnected: %d\nVersion: Evennia %s\n## END INFO"
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


class TestSystemCommands(CommandTest):
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
