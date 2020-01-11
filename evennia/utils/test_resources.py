"""
Various helper resources for writing unittests.

"""
import sys
from twisted.internet.defer import Deferred
from django.conf import settings
from django.test import TestCase
from mock import Mock, patch
from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.scripts import DefaultScript
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache


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
        # (in a test method)
        unload_module(foo)
        with mock.patch("foo.GLOBALTHING", "mockval"):
            import foo
            ... # test code using foo.GLOBALTHING, now set to 'mockval'


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


class EvenniaTest(TestCase):
    """
    Base test for Evennia, sets up a basic environment.
    """

    account_typeclass = DefaultAccount
    object_typeclass = DefaultObject
    character_typeclass = DefaultCharacter
    exit_typeclass = DefaultExit
    room_typeclass = DefaultRoom
    script_typeclass = DefaultScript

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
        self.room1 = create.create_object(self.room_typeclass, key="Room", nohome=True)
        self.room1.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room1.id  # we must have a default home
        # Set up fake prototype module for allowing tests to use named prototypes.
        settings.PROTOTYPE_MODULES = "evennia.utils.tests.data.prototypes_example"
        self.room2 = create.create_object(self.room_typeclass, key="Room2")
        self.exit = create.create_object(
            self.exit_typeclass, key="out", location=self.room1, destination=self.room2
        )
        self.obj1 = create.create_object(
            self.object_typeclass, key="Obj", location=self.room1, home=self.room1
        )
        self.obj2 = create.create_object(
            self.object_typeclass, key="Obj2", location=self.room1, home=self.room1
        )
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
        self.script = create.create_script(self.script_typeclass, key="Script")
        self.account.permissions.add("Developer")

        # set up a fake session

        dummysession = ServerSession()
        dummysession.init_session("telnet", ("localhost", "testmode"), SESSIONS)
        dummysession.sessid = 1
        SESSIONS.portal_connect(
            dummysession.get_sync_data()
        )  # note that this creates a new Session!
        session = SESSIONS.session_from_sessid(1)  # the real session
        SESSIONS.login(session, self.account, testmode=True)
        self.session = session

    def tearDown(self):
        flush_cache()
        SESSIONS.data_out = self.backups[0]
        SESSIONS.disconnect = self.backups[1]
        settings.DEFAULT_HOME = self.backups[2]
        settings.PROTOTYPE_MODULES = self.backups[3]

        del SESSIONS[self.session.sessid]
        self.account.delete()
        self.account2.delete()
        super().tearDown()
