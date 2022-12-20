"""
Various helper resources for writing unittests.

Classes for testing Evennia core:

- `BaseEvenniaTestCase` - no default objects, only enforced default settings
- `BaseEvenniaTest` - all default objects, enforced default settings
- `BaseEvenniaCommandTest` - for testing Commands, enforced default settings

Classes for testing game folder content:

- `EvenniaTestCase` - no default objects, using gamedir settings (identical to
   standard Python TestCase)
- `EvenniaTest` - all default objects, using gamedir settings
- `EvenniaCommandTest` - for testing game folder commands, using gamedir settings

Other:

- `EvenniaTestMixin` - A class mixin for creating the test environment objects, for
  making custom tests.
- `EvenniaCommandMixin` - A class mixin that adds support for command testing with the .call()
  helper. Used by the command-test classes, but can be used for making a customt test class.

"""
import re
import sys
import types

from django.conf import settings
from django.test import TestCase, override_settings
from mock import MagicMock, Mock, patch
from twisted.internet.defer import Deferred

from evennia import settings_default
from evennia.accounts.accounts import DefaultAccount
from evennia.commands.command import InterruptCommand
from evennia.commands.default.muxcommand import MuxCommand
from evennia.objects.objects import (
    DefaultCharacter,
    DefaultExit,
    DefaultObject,
    DefaultRoom,
)
from evennia.scripts.scripts import DefaultScript
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import ansi, create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.utils import all_from_module, to_str

_RE_STRIP_EVMENU = re.compile(r"^\+|-+\+|\+-+|--+|\|(?:\s|$)", re.MULTILINE)


# set up a 'pristine' setting, unaffected by any changes in mygame
DEFAULT_SETTING_RESETS = dict(
    CONNECTION_SCREEN_MODULE="evennia.game_template.server.conf.connection_screens",
    AT_SERVER_STARTSTOP_MODULE="evennia.game_template.server.conf.at_server_startstop",
    AT_SERVICES_PLUGINS_MODULES=["evennia.game_template.server.conf.server_services_plugins"],
    PORTAL_SERVICES_PLUGIN_MODULES=["evennia.game_template.server.conf.portal_services_plugins"],
    MSSP_META_MODULE="evennia.game_template.server.conf.mssp",
    WEB_PLUGINS_MODULE="server.conf.web_plugins",
    LOCK_FUNC_MODULES=("evennia.locks.lockfuncs", "evennia.game_template.server.conf.lockfuncs"),
    INPUT_FUNC_MODULES=[
        "evennia.server.inputfuncs",
        "evennia.game_template.server.conf.inputfuncs",
    ],
    PROTOTYPE_MODULES=["evennia.game_template.world.prototypes"],
    CMDSET_UNLOGGEDIN="evennia.game_template.commands.default_cmdsets.UnloggedinCmdSet",
    CMDSET_SESSION="evennia.game_template.commands.default_cmdsets.SessionCmdSet",
    CMDSET_CHARACTER="evennia.game_template.commands.default_cmdsets.CharacterCmdSet",
    CMDSET_ACCOUNT="evennia.game_template.commands.default_cmdsets.AccountCmdSet",
    CMDSET_PATHS=["evennia.game_template.commands", "evennia", "evennia.contrib"],
    TYPECLASS_PATHS=[
        "evennia",
        "evennia.contrib",
        "evennia.contrib.game_systems",
        "evennia.contrib.base_systems",
        "evennia.contrib.full_systems",
        "evennia.contrib.tutorials",
        "evennia.contrib.utils",
    ],
    BASE_ACCOUNT_TYPECLASS="evennia.accounts.accounts.DefaultAccount",
    BASE_OBJECT_TYPECLASS="evennia.objects.objects.DefaultObject",
    BASE_CHARACTER_TYPECLASS="evennia.objects.objects.DefaultCharacter",
    BASE_ROOM_TYPECLASS="evennia.objects.objects.DefaultRoom",
    BASE_EXIT_TYPECLASS="evennia.objects.objects.DefaultExit",
    BASE_CHANNEL_TYPECLASS="evennia.comms.comms.DefaultChannel",
    BASE_SCRIPT_TYPECLASS="evennia.scripts.scripts.DefaultScript",
    BASE_BATCHPROCESS_PATHS=[
        "evennia.game_template.world",
        "evennia.contrib",
        "evennia.contrib.tutorials",
    ],
    FILE_HELP_ENTRY_MODULES=["evennia.game_template.world.help_entries"],
    FUNCPARSER_OUTGOING_MESSAGES_MODULES=[
        "evennia.utils.funcparser",
        "evennia.game_template.server.conf.inlinefuncs",
    ],
    FUNCPARSER_PROTOTYPE_PARSING_MODULES=[
        "evennia.prototypes.protfuncs",
        "evennia.game_template.server.conf.prototypefuncs",
    ],
    BASE_GUEST_TYPECLASS="evennia.accounts.accounts.DefaultGuest",
    # a special setting boolean _TEST_ENVIRONMENT is set by the test runner
    # while the test suite is running.
)

DEFAULT_SETTINGS = {**all_from_module(settings_default), **DEFAULT_SETTING_RESETS}
DEFAULT_SETTINGS.pop("DATABASES")  # we want different dbs tested in CI


# mocking of evennia.utils.utils.delay
def mockdelay(timedelay, callback, *args, **kwargs):
    callback(*args, **kwargs)
    return Deferred()


# mocking of twisted's deferLater
def mockdeferLater(reactor, timedelay, callback, *args, **kwargs):
    callback(*args, **kwargs)
    return Deferred()


def unload_module(module):
    """
    Reset import so one can mock global constants.

    Args:
        module (module, object or str): The module will
            be removed so it will have to be imported again. If given
            an object, the module in which that object sits will be unloaded. A string
            should directly give the module pathname to unload.

    Example:

        ```python
        # (in a test method)
        unload_module(foo)
        with mock.patch("foo.GLOBALTHING", "mockval"):
            import foo
            ... # test code using foo.GLOBALTHING, now set to 'mockval'
        ```

    This allows for mocking constants global to the module, since
    otherwise those would not be mocked (since a module is only
    loaded once).

    """
    if isinstance(module, str):
        modulename = module
    elif hasattr(module, "__module__"):
        modulename = module.__module__
    else:
        modulename = module.__name__

    if modulename in sys.modules:
        del sys.modules[modulename]


def _mock_deferlater(reactor, timedelay, callback, *args, **kwargs):
    callback(*args, **kwargs)
    return Deferred()


class EvenniaTestMixin:
    """
    Evennia test environment mixin
    """

    account_typeclass = DefaultAccount
    object_typeclass = DefaultObject
    character_typeclass = DefaultCharacter
    exit_typeclass = DefaultExit
    room_typeclass = DefaultRoom
    script_typeclass = DefaultScript

    def create_accounts(self):
        self.account = create.create_account(
            "TestAccount",
            email="test@test.com",
            password="testpassword",
            typeclass=self.account_typeclass,
        )
        self.account2 = create.create_account(
            "TestAccount2",
            email="test@test.com",
            password="testpassword",
            typeclass=self.account_typeclass,
        )
        self.account.permissions.add("Developer")

    def teardown_accounts(self):
        if hasattr(self, "account"):
            self.account.delete()
        if hasattr(self, "account2"):
            self.account2.delete()

    # Set up fake prototype module for allowing tests to use named prototypes.
    @override_settings(
        PROTOTYPE_MODULES=["evennia.utils.tests.data.prototypes_example"], DEFAULT_HOME="#1"
    )
    def create_rooms(self):
        self.room1 = create.create_object(self.room_typeclass, key="Room", nohome=True)
        self.room1.db.desc = "room_desc"

        self.room2 = create.create_object(self.room_typeclass, key="Room2")
        self.exit = create.create_object(
            self.exit_typeclass, key="out", location=self.room1, destination=self.room2
        )

    def create_objs(self):
        self.obj1 = create.create_object(
            self.object_typeclass, key="Obj", location=self.room1, home=self.room1
        )
        self.obj2 = create.create_object(
            self.object_typeclass, key="Obj2", location=self.room1, home=self.room1
        )

    def create_chars(self):
        self.char1 = create.create_object(
            self.character_typeclass, key="Char", location=self.room1, home=self.room1
        )
        self.char1.permissions.add("Developer")
        self.char2 = create.create_object(
            self.character_typeclass, key="Char2", location=self.room1, home=self.room1
        )
        self.char1.account = self.account
        self.account.db._last_puppet = self.char1
        self.char2.account = self.account2
        self.account2.db._last_puppet = self.char2

    def create_script(self):
        self.script = create.create_script(self.script_typeclass, key="Script")

    def setup_session(self):
        dummysession = ServerSession()
        dummysession.init_session("telnet", ("localhost", "testmode"), SESSIONS)
        dummysession.sessid = 1
        SESSIONS.portal_connect(
            dummysession.get_sync_data()
        )  # note that this creates a new Session!
        session = SESSIONS.session_from_sessid(1)  # the real session
        SESSIONS.login(session, self.account, testmode=True)
        self.session = session

    def teardown_session(self):
        if hasattr(self, "sessions"):
            del SESSIONS[self.session.sessid]

    @patch("evennia.scripts.taskhandler.deferLater", _mock_deferlater)
    def setUp(self):
        """
        Sets up testing environment
        """
        self.backups = (
            SESSIONS.data_out,
            SESSIONS.disconnect,
            settings.DEFAULT_HOME,
            settings.PROTOTYPE_MODULES,
        )
        SESSIONS.data_out = Mock()
        SESSIONS.disconnect = Mock()

        self.create_accounts()
        self.create_rooms()
        self.create_objs()
        self.create_chars()
        self.create_script()
        self.setup_session()

    def tearDown(self):
        flush_cache()
        try:
            SESSIONS.data_out = self.backups[0]
            SESSIONS.disconnect = self.backups[1]
            settings.DEFAULT_HOME = self.backups[2]
            settings.PROTOTYPE_MODULES = self.backups[3]
        except AttributeError as err:
            raise AttributeError(
                f"{err}: Teardown error. If you overrode the `setUp()` method "
                "in your test, make sure you also added `super().setUp()`!"
            )

        del SESSIONS[self.session.sessid]
        self.teardown_accounts()
        super().tearDown()


@patch("evennia.server.portal.portal.LoopingCall", new=MagicMock())
class EvenniaCommandTestMixin:
    """
    Mixin to add to a test in order to provide the `.call` helper for
    testing the execution and returns of a command.

    Tests a Command by running it and comparing what messages it sends with
    expected values. This tests without actually spinning up the cmdhandler
    for every test, which is more controlled.

    Example:
    ::

        from commands.echo import CmdEcho

        class MyCommandTest(EvenniaTest, CommandTestMixin):

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
                list will be passed into the command as if the user answered each prompt
                in that order.
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
            receiver_mapping = {
                recv: str(msg).strip() if msg else None for recv, msg in msg.items()
            }
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
                args[0] if args and args[0] else kwargs.get("text", to_str(kwargs))
                for name, args, kwargs in receiver.msg.mock_calls
            ]
            # we can return this now, we are done using the mock
            receiver.msg = unmocked_msg_methods[receiver]

            # Get the first element of a tuple if msg received a tuple instead of a string
            stored_msg = [
                str(smsg[0]) if isinstance(smsg, tuple) else str(smsg) for smsg in stored_msg
            ]
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
                    _RE_STRIP_EVMENU.sub("", ansi.parse_ansi(mess, strip_ansi=noansi))
                    for mess in stored_msg
                ).strip()

                # this is the actual test
                if expected_msg == "" and returned_msg or not returned_msg.startswith(expected_msg):
                    # failed the test
                    raise AssertionError(
                        self._ERROR_FORMAT.format(
                            expected_msg=expected_msg, returned_msg=returned_msg
                        )
                    )
                # passed!
                returned_msgs[receiver] = returned_msg

        if len(returned_msgs) == 1:
            return list(returned_msgs.values())[0]
        return returned_msgs


# Base testing classes


@override_settings(**DEFAULT_SETTINGS)
class BaseEvenniaTestCase(TestCase):
    """
    Base test (with no default objects) but with enforced default settings.

    """


class EvenniaTestCase(TestCase):
    """
    For use with gamedir settings; Just like the normal test case, only for naming consistency.

    """

    pass


@override_settings(**DEFAULT_SETTINGS)
class BaseEvenniaTest(EvenniaTestMixin, TestCase):
    """
    This class parent has all default objects and uses only default settings.

    """


class EvenniaTest(EvenniaTestMixin, TestCase):
    """
    This test class is intended for inheriting in mygame tests.
    It helps ensure your tests are run with your own objects
    and settings from your game folder.

    """

    account_typeclass = settings.BASE_ACCOUNT_TYPECLASS
    object_typeclass = settings.BASE_OBJECT_TYPECLASS
    character_typeclass = settings.BASE_CHARACTER_TYPECLASS
    exit_typeclass = settings.BASE_EXIT_TYPECLASS
    room_typeclass = settings.BASE_ROOM_TYPECLASS
    script_typeclass = settings.BASE_SCRIPT_TYPECLASS


@patch("evennia.commands.account.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.admin.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.batchprocess.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.building.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.comms.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.general.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.help.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.syscommands.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.system.COMMAND_DEFAULT_CLASS", MuxCommand)
@patch("evennia.commands.unloggedin.COMMAND_DEFAULT_CLASS", MuxCommand)
class BaseEvenniaCommandTest(BaseEvenniaTest, EvenniaCommandTestMixin):
    """
    Commands only using the default settings.

    """


class EvenniaCommandTest(EvenniaTest, EvenniaCommandTestMixin):
    """
    Parent class to inherit from - makes tests use your own
    classes and settings in mygame.

    """
