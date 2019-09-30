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

from django.conf import settings
from mock import Mock, mock

from evennia import DefaultRoom, DefaultExit
from evennia.commands.default.cmdset_character import CharacterCmdSet
from evennia.utils.test_resources import EvenniaTest
from evennia.commands.default import (
    help,
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
from evennia.commands.cmdparser import build_matches
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

_RE = re.compile(r"^\+|-+\+|\+-+|--+|\|(?:\s|$)", re.MULTILINE)


# ------------------------------------------------------------
# Command testing
# ------------------------------------------------------------


class CommandTest(EvenniaTest):
    """
    Tests a command
    """

    def call(
        self,
        cmdobj,
        args,
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
        cmdobj.raw_string = raw_string if raw_string is not None else cmdobj.key + " " + args
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
        stored_msg = [
            args[0] if args and args[0] else kwargs.get("text", utils.to_str(kwargs))
            for name, args, kwargs in receiver.msg.mock_calls
        ]
        # Get the first element of a tuple if msg received a tuple instead of a string
        stored_msg = [str(smsg[0]) if isinstance(smsg, tuple) else str(smsg) for smsg in stored_msg]
        if msg is not None:
            msg = str(msg)  # to be safe, e.g. `py` command may return ints
            # set our separator for returned messages based on parsing ansi or not
            msg_sep = "|" if noansi else "||"
            # Have to strip ansi for each returned message for the regex to handle it correctly
            returned_msg = msg_sep.join(
                _RE.sub("", ansi.parse_ansi(mess, strip_ansi=noansi)) for mess in stored_msg
            ).strip()
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
    def test_help(self):
        self.call(help.CmdHelp(), "", "Command help entries", cmdset=CharacterCmdSet())

    def test_set_help(self):
        self.call(
            help.CmdSetHelp(),
            "testhelp, General = This is a test",
            "Topic 'testhelp' was successfully created.",
        )
        self.call(help.CmdHelp(), "testhelp", "Help for testhelp", cmdset=CharacterCmdSet())


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
        self.account.unpuppet_object(self.session)
        self.call(
            account.CmdIC(), "Char", "You become Char.", caller=self.account, receiver=self.char1
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
        self.call(building.CmdExamine(), "self/test", "Persistent attributes:\n test = testval")
        self.call(building.CmdExamine(), "NotFound", "Could not find 'NotFound'.")
        self.call(building.CmdExamine(), "out", "Name/key: out")

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

        with mock.patch("evennia.commands.default.building.EvEditor") as mock_ed:
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

        with mock.patch("evennia.commands.default.building.EvEditor") as mock_ed:
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
        self.call(building.CmdListCmdSets(), "", "<DefaultCharacter (Union, prio 0, perm)>:")
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

        self.call(building.CmdFind(), "/char Obj")
        self.call(building.CmdFind(), "/room Obj")
        self.call(building.CmdFind(), "/exit Obj")
        self.call(building.CmdFind(), "/exact Obj", "One Match")

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
        self.call(building.CmdScript(), "Obj = ", "dbref obj")

        self.call(
            building.CmdScript(), "/start Obj", "0 scripts started on Obj"
        )  # because it's already started
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
        def getObject(commandTest, objKeyStr):
            # A helper function to get a spawned object and
            # check that it exists in the process.
            query = search_object(objKeyStr)
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

        self.call(building.CmdSpawn(), "/search ", "Key ")
        self.call(building.CmdSpawn(), "/search test;test2", "")

        self.call(
            building.CmdSpawn(),
            "/save {'key':'Test Char', " "'typeclass':'evennia.objects.objects.DefaultCharacter'}",
            "To save a prototype it must have the 'prototype_key' set.",
        )

        self.call(building.CmdSpawn(), "/list", "Key ")

        self.call(building.CmdSpawn(), "testprot", "Spawned Test Char")
        # Tests that the spawned object's location is the same as the caharacter's location, since
        # we did not specify it.
        testchar = getObject(self, "Test Char")
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
        goblin = getObject(self, "goblin")
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

        ball = getObject(self, "Ball")
        self.assertEqual(ball.location, self.char1.location)
        self.assertIsInstance(ball, DefaultObject)
        ball.delete()

        # Tests "spawn/n ..." without specifying a location.
        # Location should be "None".
        self.call(
            building.CmdSpawn(), "/n 'BALL'", "Spawned Ball"
        )  # /n switch is abbreviated form of /noloc
        ball = getObject(self, "Ball")
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
        ball = getObject(self, "Ball")
        self.assertEqual(ball.location, spawnLoc)
        ball.delete()

        # test calling spawn with an invalid prototype.
        self.call(building.CmdSpawn(), "'NO_EXIST'", "No prototype named 'NO_EXIST'")

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
            building.CmdSpawn(), "/edit NO_EXISTS", "No prototype 'NO_EXISTS' was found."
        )

        # spawn/examine (missing prototype)
        # lists all prototypes that exist
        msg = self.call(building.CmdSpawn(), "/examine")
        assert "testball" in msg and "testprot" in msg

        # spawn/examine with valid prototype
        # prints the prototype
        msg = self.call(building.CmdSpawn(), "/examine BALL")
        assert "Ball" in msg and "testball" in msg

        # spawn/examine with invalid prototype
        # shows error
        self.call(building.CmdSpawn(), "/examine NO_EXISTS", "No prototype 'NO_EXISTS' was found.")


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
            "You are already connected to channel testchan. You can now",
            receiver=self.account,
        )
        self.call(
            comms.CmdDelCom(),
            "tc",
            "Your alias 'tc' for channel testchan was cleared.",
            receiver=self.account,
        )

    def test_channels(self):
        self.call(
            comms.CmdChannels(),
            "",
            "Available channels (use comlist,addcom and delcom to manage",
            receiver=self.account,
        )

    def test_all_com(self):
        self.call(
            comms.CmdAllCom(),
            "",
            "Available channels (use comlist,addcom and delcom to manage",
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

    def test_cemit(self):
        self.call(
            comms.CmdCemit(),
            "testchan = Test Message",
            "[testchan] Test Message|Sent to channel testchan: Test Message",
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


class TestBatchProcess(CommandTest):
    def test_batch_commands(self):
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

    @mock.patch("evennia.commands.default.syscommands.ChannelDB")
    def test_channelcommand(self, mock_channeldb):
        channel = mock.MagicMock()
        channel.msg = mock.MagicMock()
        mock_channeldb.objects.get_channel = mock.MagicMock(return_value=channel)

        self.call(syscommands.SystemSendToChannel(), "public:Hello")
        channel.msg.assert_called()
