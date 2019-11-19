# -*- coding: utf-8 -*-

import sys
from mock import Mock, MagicMock, patch
from random import randint
from unittest import TestCase

from django.test import override_settings
from evennia.accounts.accounts import AccountSessionHandler
from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create
from evennia.utils.utils import uses_database

from django.conf import settings


class TestAccountSessionHandler(TestCase):
    "Check AccountSessionHandler class"

    def setUp(self):
        self.account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.handler = AccountSessionHandler(self.account)

    def tearDown(self):
        if hasattr(self, "account"):
            self.account.delete()

    def test_get(self):
        "Check get method"
        self.assertEqual(self.handler.get(), [])
        self.assertEqual(self.handler.get(100), [])

        import evennia.server.sessionhandler

        s1 = MagicMock()
        s1.logged_in = True
        s1.uid = self.account.uid
        evennia.server.sessionhandler.SESSIONS[s1.uid] = s1

        s2 = MagicMock()
        s2.logged_in = True
        s2.uid = self.account.uid + 1
        evennia.server.sessionhandler.SESSIONS[s2.uid] = s2

        s3 = MagicMock()
        s3.logged_in = False
        s3.uid = self.account.uid + 2
        evennia.server.sessionhandler.SESSIONS[s3.uid] = s3

        self.assertEqual([s.uid for s in self.handler.get()], [s1.uid])
        self.assertEqual([s.uid for s in [self.handler.get(self.account.uid)]], [s1.uid])
        self.assertEqual([s.uid for s in self.handler.get(self.account.uid + 1)], [])

    def test_all(self):
        "Check all method"
        self.assertEqual(self.handler.get(), self.handler.all())

    def test_count(self):
        "Check count method"
        self.assertEqual(self.handler.count(), len(self.handler.get()))


@override_settings(GUEST_ENABLED=True, GUEST_LIST=["bruce_wayne"])
class TestDefaultGuest(EvenniaTest):
    "Check DefaultGuest class"

    ip = "212.216.134.22"

    @override_settings(GUEST_ENABLED=False)
    def test_create_not_enabled(self):
        # Guest account should not be permitted
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertFalse(account, "Guest account was created despite being disabled.")

    def test_authenticate(self):
        # Create a guest account
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertTrue(account, "Guest account should have been created.")

        # Create a second guest account
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertFalse(
            account, "Two guest accounts were created with a single entry on the guest list!"
        )

    @patch("evennia.accounts.accounts.ChannelDB.objects.get_channel")
    def test_create(self, get_channel):
        get_channel.connect = MagicMock(return_value=True)
        account, errors = DefaultGuest.create()
        self.assertTrue(account, "Guest account should have been created.")
        self.assertFalse(errors)

    def test_at_post_login(self):
        self.account.db._last_puppet = self.char1
        self.account.at_post_login(self.session)
        self.account.at_post_login()

    def test_at_server_shutdown(self):
        account, errors = DefaultGuest.create(ip=self.ip)
        self.char1.delete = MagicMock()
        account.db._playable_characters = [self.char1]
        account.at_server_shutdown()
        self.char1.delete.assert_called()

    def test_at_post_disconnect(self):
        account, errors = DefaultGuest.create(ip=self.ip)
        self.char1.delete = MagicMock()
        account.db._playable_characters = [self.char1]
        account.at_post_disconnect()
        self.char1.delete.assert_called()


class TestDefaultAccountAuth(EvenniaTest):
    def setUp(self):
        super(TestDefaultAccountAuth, self).setUp()

        self.password = "testpassword"
        self.account.delete()
        self.account = create.create_account(
            f"TestAccount{randint(100000, 999999)}",
            email="test@test.com",
            password=self.password,
            typeclass=DefaultAccount,
        )

    def test_authentication(self):
        "Confirm Account authentication method is authenticating/denying users."
        # Valid credentials
        obj, errors = DefaultAccount.authenticate(self.account.name, self.password)
        self.assertTrue(obj, "Account did not authenticate given valid credentials.")

        # Invalid credentials
        obj, errors = DefaultAccount.authenticate(self.account.name, "xyzzy")
        self.assertFalse(obj, "Account authenticated using invalid credentials.")

    def test_create(self):
        "Confirm Account creation is working as expected."
        # Create a normal account
        account, errors = DefaultAccount.create(username="ziggy", password="stardust11")
        self.assertTrue(account, "New account should have been created.")

        # Try creating a duplicate account
        account2, errors = DefaultAccount.create(username="Ziggy", password="starman11")
        self.assertFalse(account2, "Duplicate account name should not have been allowed.")
        account.delete()

    def test_throttle(self):
        "Confirm throttle activates on too many failures."
        for x in range(20):
            obj, errors = DefaultAccount.authenticate(self.account.name, "xyzzy", ip="12.24.36.48")
            self.assertFalse(
                obj,
                "Authentication was provided a bogus password; this should NOT have returned an account!",
            )

        self.assertTrue(
            "too many login failures" in errors[-1].lower(),
            "Failed logins should have been throttled.",
        )

    def test_username_validation(self):
        "Check username validators deny relevant usernames"
        # Should not accept Unicode by default, lest users pick names like this

        if not uses_database("mysql"):
            # TODO As of Mar 2019, mysql does not pass this test due to collation problems
            # that has not been possible to resolve
            result, error = DefaultAccount.validate_username("¯\_(ツ)_/¯")
            self.assertFalse(result, "Validator allowed kanji in username.")

        # Should not allow duplicate username
        result, error = DefaultAccount.validate_username(self.account.name)
        self.assertFalse(result, "Duplicate username should not have passed validation.")

        # Should not allow username too short
        result, error = DefaultAccount.validate_username("xx")
        self.assertFalse(result, "2-character username passed validation.")

    def test_password_validation(self):
        "Check password validators deny bad passwords"

        account = create.create_account(
            f"TestAccount{randint(100000, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        for bad in ("", "123", "password", "TestAccount", "#", "xyzzy"):
            self.assertFalse(account.validate_password(bad, account=self.account)[0])

        "Check validators allow sufficiently complex passwords"
        for better in ("Mxyzptlk", "j0hn, i'M 0n1y d4nc1nG"):
            self.assertTrue(account.validate_password(better, account=self.account)[0])
        account.delete()

    def test_password_change(self):
        "Check password setting and validation is working as expected"
        account = create.create_account(
            f"TestAccount{randint(100000, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )

        from django.core.exceptions import ValidationError

        # Try setting some bad passwords
        for bad in ("", "#", "TestAccount", "password"):
            valid, error = account.validate_password(bad, account)
            self.assertFalse(valid)

        # Try setting a better password (test for False; returns None on success)
        self.assertFalse(account.set_password("Mxyzptlk"))
        account.delete()


class TestDefaultAccount(TestCase):
    "Check DefaultAccount class"

    def setUp(self):
        self.s1 = MagicMock()
        self.s1.puppet = None
        self.s1.sessid = 0

    def test_puppet_object_no_object(self):
        "Check puppet_object method called with no object param"

        try:
            DefaultAccount().puppet_object(self.s1, None)
            self.fail("Expected error: 'Object not found'")
        except RuntimeError as re:
            self.assertEqual("Object not found", str(re))

    def test_puppet_object_no_session(self):
        "Check puppet_object method called with no session param"

        try:
            DefaultAccount().puppet_object(None, Mock())
            self.fail("Expected error: 'Session not found'")
        except RuntimeError as re:
            self.assertEqual("Session not found", str(re))

    def test_puppet_object_already_puppeting(self):
        "Check puppet_object method called, already puppeting this"

        import evennia.server.sessionhandler

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.logged_in = True
        self.s1.data_out = Mock(return_value=None)

        obj = Mock()
        self.s1.puppet = obj
        account.puppet_object(self.s1, obj)
        self.s1.data_out.assert_called_with(
            options=None, text="You are already puppeting this object."
        )
        self.assertIsNone(obj.at_post_puppet.call_args)

    def test_puppet_object_no_permission(self):
        "Check puppet_object method called, no permission"

        import evennia.server.sessionhandler

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.data_out = MagicMock()
        obj = Mock()
        obj.access = Mock(return_value=False)

        account.puppet_object(self.s1, obj)

        self.assertTrue(
            self.s1.data_out.call_args[1]["text"].startswith("You don't have permission to puppet")
        )
        self.assertIsNone(obj.at_post_puppet.call_args)

    @override_settings(MULTISESSION_MODE=0)
    def test_puppet_object_joining_other_session(self):
        "Check puppet_object method called, joining other session"

        import evennia.server.sessionhandler

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.puppet = None
        self.s1.logged_in = True
        self.s1.data_out = MagicMock()

        obj = Mock()
        obj.access = Mock(return_value=True)
        obj.account = account
        obj.sessions.all = MagicMock(return_value=[self.s1])

        account.puppet_object(self.s1, obj)
        # works because django.conf.settings.MULTISESSION_MODE is not in (1, 3)
        self.assertTrue(
            self.s1.data_out.call_args[1]["text"].endswith("from another of your sessions.|n")
        )
        self.assertTrue(obj.at_post_puppet.call_args[1] == {})

    def test_puppet_object_already_puppeted(self):
        "Check puppet_object method called, already puppeted"

        import evennia.server.sessionhandler

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.account = account
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.puppet = None
        self.s1.logged_in = True
        self.s1.data_out = Mock(return_value=None)

        obj = Mock()
        obj.access = Mock(return_value=True)
        obj.account = Mock()
        obj.at_post_puppet = Mock()

        account.puppet_object(self.s1, obj)
        self.assertTrue(
            self.s1.data_out.call_args[1]["text"].endswith(
                "is already puppeted by another Account."
            )
        )
        self.assertIsNone(obj.at_post_puppet.call_args)


class TestAccountPuppetDeletion(EvenniaTest):
    @override_settings(MULTISESSION_MODE=2)
    def test_puppet_deletion(self):
        # Check for existing chars
        self.assertFalse(
            self.account.db._playable_characters, "Account should not have any chars by default."
        )

        # Add char1 to account's playable characters
        self.account.db._playable_characters.append(self.char1)
        self.assertTrue(self.account.db._playable_characters, "Char was not added to account.")

        # See what happens when we delete char1.
        self.char1.delete()
        # Playable char list should be empty.
        self.assertFalse(
            self.account.db._playable_characters,
            f"Playable character list is not empty! {self.account.db._playable_characters}",
        )


class TestDefaultAccountEv(EvenniaTest):
    """
    Testing using the EvenniaTest parent

    """

    def test_characters_property(self):
        "test existence of None in _playable_characters Attr"
        self.account.db._playable_characters = [self.char1, None]
        chars = self.account.characters
        self.assertEqual(chars, [self.char1])
        self.assertEqual(self.account.db._playable_characters, [self.char1])

    def test_puppet_success(self):
        self.account.msg = MagicMock()
        with patch("evennia.accounts.accounts._MULTISESSION_MODE", 2):
            self.account.puppet_object(self.session, self.char1)
            self.account.msg.assert_called_with("You are already puppeting this object.")

    @patch("evennia.accounts.accounts.time.time", return_value=10000)
    def test_idle_time(self, mock_time):
        self.session.cmd_last_visible = 10000 - 10
        idle = self.account.idle_time
        self.assertEqual(idle, 10)

        # test no sessions
        with patch(
            "evennia.accounts.accounts._SESSIONS.sessions_from_account", return_value=[]
        ) as mock_sessh:
            idle = self.account.idle_time
            self.assertEqual(idle, None)

    @patch("evennia.accounts.accounts.time.time", return_value=10000)
    def test_connection_time(self, mock_time):
        self.session.conn_time = 10000 - 10
        conn = self.account.connection_time
        self.assertEqual(conn, 10)

        # test no sessions
        with patch(
            "evennia.accounts.accounts._SESSIONS.sessions_from_account", return_value=[]
        ) as mock_sessh:
            idle = self.account.connection_time
            self.assertEqual(idle, None)

    def test_create_account(self):
        acct = create.account(
            "TestAccount3",
            "test@test.com",
            "testpassword123",
            locks="test:all()",
            tags=[("tag1", "category1"), ("tag2", "category2", "data1"), ("tag3", None)],
            attributes=[("key1", "value1", "category1", "edit:false()", True), ("key2", "value2")],
        )
        acct.save()
        self.assertTrue(acct.pk)

    def test_at_look(self):
        ret = self.account.at_look()
        self.assertTrue("Out-of-Character" in ret)
        ret = self.account.at_look(target=self.obj1)
        self.assertTrue("Obj" in ret)
        ret = self.account.at_look(session=self.session)
        self.assertTrue("*" in ret)  #  * marks session is active in list
        ret = self.account.at_look(target=self.obj1, session=self.session)
        self.assertTrue("Obj" in ret)
        ret = self.account.at_look(target="Invalid", session=self.session)
        self.assertEqual(ret, "Invalid has no in-game appearance.")

    def test_msg(self):
        self.account.msg
