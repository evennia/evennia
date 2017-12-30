from django.conf import settings
from django.test import TestCase
from mock import Mock
from evennia.objects.objects import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
from evennia.accounts.accounts import DefaultAccount
from evennia.scripts.scripts import DefaultScript
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache


SESSIONS.data_out = Mock()
SESSIONS.disconnect = Mock()


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

    def setUp(self):
        """
        Sets up testing environment
        """
        self.account = create.create_account("TestAccount", email="test@test.com", password="testpassword", typeclass=self.account_typeclass)
        self.account2 = create.create_account("TestAccount2", email="test@test.com", password="testpassword", typeclass=self.account_typeclass)
        self.room1 = create.create_object(self.room_typeclass, key="Room", nohome=True)
        self.room1.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room1.id  # we must have a default home
        # Set up fake prototype module for allowing tests to use named prototypes.
        settings.PROTOTYPE_MODULES = "evennia.utils.tests.data.prototypes_example"
        self.room2 = create.create_object(self.room_typeclass, key="Room2")
        self.exit = create.create_object(self.exit_typeclass, key='out', location=self.room1, destination=self.room2)
        self.obj1 = create.create_object(self.object_typeclass, key="Obj", location=self.room1, home=self.room1)
        self.obj2 = create.create_object(self.object_typeclass, key="Obj2", location=self.room1, home=self.room1)
        self.char1 = create.create_object(self.character_typeclass, key="Char", location=self.room1, home=self.room1)
        self.char1.permissions.add("Developer")
        self.char2 = create.create_object(self.character_typeclass, key="Char2", location=self.room1, home=self.room1)
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
        SESSIONS.portal_connect(dummysession.get_sync_data())  # note that this creates a new Session!
        session = SESSIONS.session_from_sessid(1)  # the real session
        SESSIONS.login(session, self.account, testmode=True)
        self.session = session

    def tearDown(self):
        flush_cache()
        del SESSIONS[self.session.sessid]
        self.account.delete()
        self.account2.delete()
        super(EvenniaTest, self).tearDown()
