"""
Various helper resources for writing unittests.

"""
import sys
from twisted.internet.defer import Deferred
from django.conf import settings
from django.test import TestCase, override_settings
from mock import Mock, patch
from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.scripts import DefaultScript
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.utils import all_from_module
from evennia import settings_default


# set up a 'pristine' setting, unaffected by any changes in mygame
DEFAULT_SETTING_RESETS = dict(
    CONNECTION_SCREEN_MODULE="evennia.game_template.server.conf.connection_screens",
    AT_SERVER_STARTSTOP_MODULE="evennia.game_template.server.conf.at_server_startstop",
    AT_SERVICES_PLUGINS_MODULES=["evennia.game_template.server.conf.server_services_plugins"],
    PORTAL_SERVICES_PLUGIN_MODULES=["evennia.game_template.server.conf.portal_services_plugins"],
    MSSP_META_MODULE="evennia.game_template.server.conf.mssp",
    WEB_PLUGINS_MODULE="server.conf.web_plugins",
    LOCK_FUNC_MODULES=("evennia.locks.lockfuncs", "evennia.game_template.server.conf.lockfuncs"),
    INPUT_FUNC_MODULES=["evennia.server.inputfuncs",
                        "evennia.game_template.server.conf.inputfuncs"],
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
        "evennia.contrib.utils"],
    BASE_ACCOUNT_TYPECLASS="evennia.accounts.accounts.DefaultAccount",
    BASE_OBJECT_TYPECLASS="evennia.objects.objects.DefaultObject",
    BASE_CHARACTER_TYPECLASS="evennia.objects.objects.DefaultCharacter",
    BASE_ROOM_TYPECLASS="evennia.objects.objects.DefaultRoom",
    BASE_EXIT_TYPECLASS="evennia.objects.objects.DefaultExit",
    BASE_CHANNEL_TYPECLASS="evennia.comms.comms.DefaultChannel",
    BASE_SCRIPT_TYPECLASS="evennia.scripts.scripts.DefaultScript",
    BASE_BATCHPROCESS_PATHS=["evennia.game_template.world",
                             "evennia.contrib", "evennia.contrib.tutorials"],
    FILE_HELP_ENTRY_MODULES=["evennia.game_template.world.help_entries"],
    FUNCPARSER_OUTGOING_MESSAGES_MODULES=["evennia.utils.funcparser",
                                          "evennia.game_template.server.conf.inlinefuncs"],
    FUNCPARSER_PROTOTYPE_PARSING_MODULES=["evennia.prototypes.protfuncs",
                                          "evennia.game_template.server.conf.prototypefuncs"],
    BASE_GUEST_TYPECLASS="evennia.accounts.accounts.DefaultGuest",
)

DEFAULT_SETTINGS = {
    **all_from_module(settings_default),
    **DEFAULT_SETTING_RESETS
}
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

    def save_backups(self):
        self.backups = (
            SESSIONS.data_out,
            SESSIONS.disconnect,
            settings.DEFAULT_HOME,
            settings.PROTOTYPE_MODULES,
        )

    def restore_backups(self):
        flush_cache()
        SESSIONS.data_out = self.backups[0]
        SESSIONS.disconnect = self.backups[1]
        settings.DEFAULT_HOME = self.backups[2]
        settings.PROTOTYPE_MODULES = self.backups[3]

    def mock_sessions(self):
        SESSIONS.data_out = Mock()
        SESSIONS.disconnect = Mock()
        self.mocked_SESSIONS = SESSIONS

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
        self.account.delete()
        self.account2.delete()

    def create_rooms(self):
        self.room1 = create.create_object(self.room_typeclass, key="Room", nohome=True)
        self.room1.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room1.id  # we must have a default home

        # Set up fake prototype module for allowing tests to use named prototypes.
        settings.PROTOTYPE_MODULES = "evennia.utils.tests.data.prototypes_example"
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
        del SESSIONS[self.session.sessid]

    @patch("evennia.scripts.taskhandler.deferLater", _mock_deferlater)
    def setUp(self):
        """
        Sets up testing environment
        """
        self.save_backups()
        self.mock_sessions()
        self.create_accounts()
        self.create_rooms()
        self.create_objs()
        self.create_chars()
        self.create_script()
        self.setup_session()

    def tearDown(self):
        self.restore_backups()
        self.teardown_session()
        self.teardown_accounts()
        super().tearDown()


@override_settings(**DEFAULT_SETTINGS)
class BaseEvenniaTestCase(TestCase):
    """
    Base test (with no default objects) but with
    enforced default settings.

    """


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
