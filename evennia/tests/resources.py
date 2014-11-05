from django.conf import settings
from django.test import TestCase
from evennia.objects import DefaultObject, DefaultCharacter, DefaultRoom
from evennia.players import DefaultPlayer
from evennia.scripts import DefaultScript
from evennia.server.serversession import ServerSession
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import create
from evennia.utils.idmapper.base import flush_cache


def dummy(self, *args, **kwargs):
    pass

SESSIONS.data_out = dummy
SESSIONS.disconnect = dummy


class TestObjectClass(DefaultObject):
    def msg(self, text="", **kwargs):
        "test message"
        pass


class TestCharacterClass(DefaultCharacter):
    def msg(self, text="", **kwargs):
        "test message"
        if self.player:
            self.player.msg(text=text, **kwargs)
        else:
            if not self.ndb.stored_msg:
                self.ndb.stored_msg = []
            self.ndb.stored_msg.append(text)


class TestPlayerClass(DefaultPlayer):
    def msg(self, text="", **kwargs):
        "test message"
        if not self.ndb.stored_msg:
            self.ndb.stored_msg = []
        self.ndb.stored_msg.append(text)


class EvenniaTest(TestCase):
    """
    Base test for Evennia, sets up a basic environment.
    """
    player_typeclass = TestPlayerClass
    object_typeclass = TestObjectClass
    character_typeclass = TestCharacterClass
    room_typeclass = DefaultRoom
    script_typeclass = DefaultScript

    def setUp(self):
        """
        Sets up testing environment
        """
        self.player = create.create_player("TestPlayer", email="test@test.com", password="testpassword", typeclass=self.player_typeclass)
        self.player2 = create.create_player("TestPlayer2", email="test@test.com", password="testpassword", typeclass=self.player_typeclass)
        self.room1 = create.create_object(self.room_typeclass, key="Room", nohome=True)
        self.room1.db.desc = "room_desc"
        settings.DEFAULT_HOME = "#%i" % self.room1.id  # we must have a default home
        self.room2 = create.create_object(self.room_typeclass, key="Room2")
        self.obj1 = create.create_object(self.object_typeclass, key="Obj", location=self.room1, home=self.room1)
        self.obj2 = create.create_object(self.object_typeclass, key="Obj2", location=self.room1, home=self.room1)
        self.char1 = create.create_object(self.character_typeclass, key="Char", location=self.room1, home=self.room1)
        self.char1.permissions.add("Immortals")
        self.char2 = create.create_object(self.character_typeclass, key="Char2", location=self.room1, home=self.room1)
        self.char1.player = self.player
        self.char2.player = self.player2
        self.script = create.create_script(self.script_typeclass, key="Script")
        self.player.permissions.add("Immortals")

        # set up a fake session

        session = ServerSession()
        session.init_session("telnet", ("localhost", "testmode"), SESSIONS)
        session.sessid = 1
        SESSIONS.portal_connect(session.get_sync_data())
        SESSIONS.login(SESSIONS.session_from_sessid(1), self.player, testmode=True)
        self.session = session

    def tearDown(self):
        flush_cache()
        del SESSIONS.sessions[self.session.sessid]
