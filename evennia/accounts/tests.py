# -*- coding: utf-8 -*-

from random import randint
from unittest import TestCase

from django.conf import settings
from django.contrib.auth.hashers import PBKDF2PasswordHasher, ScryptPasswordHasher
from django.test import override_settings
from mock import MagicMock, Mock, patch
from twisted.internet.defer import Deferred

import evennia
from evennia.accounts.accounts import (
    AccountSessionHandler,
    DefaultAccount,
    DefaultGuest,
)
from evennia.accounts.hashers import (
    EvenniaScryptPasswordHasher,
    defer_check_password,
    defer_make_password,
    verify_and_upgrade_password,
)
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.utils.utils import uses_database


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

        s1 = MagicMock()
        s1.logged_in = True
        s1.uid = self.account.uid
        evennia.SESSION_HANDLER[s1.uid] = s1

        s2 = MagicMock()
        s2.logged_in = True
        s2.uid = self.account.uid + 1
        evennia.SESSION_HANDLER[s2.uid] = s2

        s3 = MagicMock()
        s3.logged_in = False
        s3.uid = self.account.uid + 2
        evennia.SESSION_HANDLER[s3.uid] = s3

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
class TestDefaultGuest(BaseEvenniaTest):
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
        with override_settings(GUEST_HOME=self.room1.dbref):
            account, errors = DefaultGuest.create()
        self.assertTrue(account, "Guest account should have been created.")
        self.assertFalse(errors)
        self.assertFalse(
            account.has_usable_password(),
            "Ephemeral guest accounts should use an unusable password.",
        )

    def test_at_post_login(self):
        self.account.db._last_puppet = self.char1
        self.account.at_post_login(self.session)
        self.account.at_post_login()

    def test_at_server_shutdown(self):
        account, errors = DefaultGuest.create(ip=self.ip)
        self.char1.delete = MagicMock()
        account.characters.add(self.char1)
        account.at_server_shutdown()
        self.char1.delete.assert_called()

    def test_at_post_disconnect(self):
        account, errors = DefaultGuest.create(ip=self.ip)
        self.char1.delete = MagicMock()
        account.characters.add(self.char1)
        account.at_post_disconnect()
        self.char1.delete.assert_called()


class TestDefaultAccountAuth(BaseEvenniaTest):
    def setUp(self):
        super().setUp()

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
            result, error = DefaultAccount.validate_username(r"¯\_(ツ)_/¯")
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

    def test_password_hasher_default(self):
        """Confirm default password hashing uses EvenniaScryptPasswordHasher."""
        self.assertEqual(
            settings.PASSWORD_HASHERS[0],
            "evennia.accounts.hashers.EvenniaScryptPasswordHasher",
        )
        self.assertTrue(
            self.account.password.startswith("scrypt$32768$"),
            f"Expected scrypt$32768$ hash, got: {self.account.password[:20]}",
        )

    def test_password_hasher_pbkdf2_upgrade(self):
        """Confirm legacy PBKDF2 passwords authenticate and upgrade to EvenniaScrypt."""
        legacy_hash = PBKDF2PasswordHasher().encode(self.password, salt="testsalt", iterations=100)
        self.account.password = legacy_hash
        self.account.save(update_fields=["password"])

        account, errors = DefaultAccount.authenticate(self.account.name, self.password)
        self.assertEqual(account, self.account)
        self.assertFalse(errors)

        self.account.refresh_from_db()
        self.assertTrue(
            self.account.password.startswith("scrypt$32768$"),
            "Legacy PBKDF2 password should transparently upgrade to EvenniaScrypt on login.",
        )

        # Verify subsequent authentication with upgraded hash succeeds
        account, errors = DefaultAccount.authenticate(self.account.name, self.password)
        self.assertEqual(account, self.account)
        self.assertFalse(errors)

    def test_authenticate_async(self):
        """Confirm authenticate_async verifies credentials and upgrades legacy hashes."""
        d = DefaultAccount.authenticate_async(self.account.name, self.password)
        self.assertIsInstance(d, Deferred)
        self.assertTrue(d.called)
        account, errors = d.result
        self.assertEqual(account, self.account)
        self.assertEqual(account.backend, "evennia.web.utils.backends.CaseInsensitiveModelBackend")
        self.assertFalse(errors)

        # Invalid password fails cleanly
        d = DefaultAccount.authenticate_async(self.account.name, "wrongpassword")
        account, errors = d.result
        self.assertIsNone(account)
        self.assertTrue(errors)

        # Legacy PBKDF2 password authenticates and upgrades in DB
        legacy_hash = PBKDF2PasswordHasher().encode(self.password, salt="testsalt", iterations=100)
        self.account.password = legacy_hash
        self.account.save(update_fields=["password"])

        d = DefaultAccount.authenticate_async(self.account.name, self.password)
        account, errors = d.result
        self.assertEqual(account, self.account)
        self.assertFalse(errors)
        self.account.refresh_from_db()
        self.assertTrue(self.account.password.startswith("scrypt$32768$"))

    def test_authenticate_async_respects_subclass_override(self):
        """Confirm authenticate_async delegates when a subclass overrides authenticate()."""

        class CustomAccount(DefaultAccount):
            """Subclass with custom synchronous authenticate."""

            called_sync = False

            @classmethod
            def authenticate(cls, username, password, ip="", **kwargs):
                cls.called_sync = True
                return None, ["custom error"]

        d = CustomAccount.authenticate_async("someone", "secret")
        account, errors = d.result
        self.assertTrue(CustomAccount.called_sync)
        self.assertIsNone(account)
        self.assertEqual(errors, ["custom error"])

    @override_settings(AUTHENTICATION_BACKENDS=["django.contrib.auth.backends.ModelBackend"])
    def test_authenticate_async_custom_backend_fallback(self):
        """Confirm authenticate_async falls back to Django authenticate for custom backends."""
        with patch(
            "evennia.accounts.accounts.authenticate", return_value=self.account
        ) as mock_auth:
            d = DefaultAccount.authenticate_async(self.account.name, self.password)
            account, errors = d.result
        mock_auth.assert_called_once_with(username=self.account.name, password=self.password)
        self.assertEqual(account, self.account)
        self.assertFalse(errors)

    def test_create_async(self):
        """Confirm create_async hashes via defer_make_password and creates valid account."""
        d = DefaultAccount.create_async(username="asyncziggy", password="stardust11")
        self.assertIsInstance(d, Deferred)
        self.assertTrue(d.called)
        account, errors = d.result
        self.assertTrue(account)
        self.assertFalse(errors)
        self.assertTrue(account.password.startswith("scrypt$32768$"))
        self.assertTrue(account.check_password("stardust11"))
        account.delete()

    def test_create_async_skips_hashing_on_validation_error(self):
        """Confirm create_async does not invoke password hashing when validation fails."""
        with patch("evennia.accounts.accounts.defer_make_password") as mock_defer:
            d = DefaultAccount.create_async(username="xx", password="bad")
            account, errors = d.result
        self.assertIsNone(account)
        self.assertTrue(errors)
        mock_defer.assert_not_called()


class TestPasswordHashers(TestCase):
    """No-DB unit tests for EvenniaScryptPasswordHasher and thread-offload helpers."""

    def test_scrypt_hasher_parameters_and_verify(self):
        """Confirm EvenniaScryptPasswordHasher uses OWASP N=2**15, r=8, p=1 settings."""
        hasher = EvenniaScryptPasswordHasher()
        self.assertEqual(hasher.work_factor, 2**15)
        self.assertEqual(hasher.block_size, 8)
        self.assertEqual(hasher.parallelism, 1)
        self.assertEqual(hasher.maxmem, 64 * 1024 * 1024)

        encoded = hasher.encode("SuperSecret123!", hasher.salt())
        self.assertTrue(encoded.startswith("scrypt$32768$"))
        self.assertTrue(hasher.verify("SuperSecret123!", encoded))
        self.assertFalse(hasher.verify("WrongPassword!", encoded))
        self.assertFalse(hasher.must_update(encoded))

    def test_scrypt_hasher_verifies_stock_django_scrypt(self):
        """Confirm stock Django Scrypt hashes verify and flag must_update."""
        stock_hasher = ScryptPasswordHasher()
        stock_encoded = stock_hasher.encode("SuperSecret123!", stock_hasher.salt())

        evennia_hasher = EvenniaScryptPasswordHasher()
        self.assertTrue(evennia_hasher.verify("SuperSecret123!", stock_encoded))
        self.assertTrue(evennia_hasher.must_update(stock_encoded))

    def test_verify_and_upgrade_password(self):
        """Confirm pure verify_and_upgrade_password upgrades legacy hashes without DB."""
        legacy = PBKDF2PasswordHasher().encode("SuperSecret123!", salt="testsalt", iterations=100)
        is_valid, upgraded = verify_and_upgrade_password("SuperSecret123!", legacy)
        self.assertTrue(is_valid)
        self.assertIsNotNone(upgraded)
        self.assertTrue(upgraded.startswith("scrypt$32768$"))

        # Already-current hash produces no upgrade
        is_valid2, upgraded2 = verify_and_upgrade_password("SuperSecret123!", upgraded)
        self.assertTrue(is_valid2)
        self.assertIsNone(upgraded2)

        # Wrong password fails with no upgrade
        is_valid3, upgraded3 = verify_and_upgrade_password("WrongPass!", legacy)
        self.assertFalse(is_valid3)
        self.assertIsNone(upgraded3)

    def test_defer_helpers_use_thread_when_reactor_running(self):
        """Confirm defer_check_password and defer_make_password offload when reactor runs."""
        sentinel_deferred = Deferred()
        with (
            patch("evennia.accounts.hashers.reactor") as mock_reactor,
            patch(
                "evennia.accounts.hashers.threads.deferToThread", return_value=sentinel_deferred
            ) as mock_dtt,
        ):
            mock_reactor.running = True
            res = defer_check_password("pw", "encoded")
            self.assertIs(res, sentinel_deferred)
            mock_dtt.assert_called_once_with(verify_and_upgrade_password, "pw", "encoded")

            mock_dtt.reset_mock()
            res2 = defer_make_password("pw")
            self.assertIs(res2, sentinel_deferred)
            self.assertEqual(mock_dtt.call_count, 1)
            self.assertEqual(mock_dtt.call_args[0][1:], ("pw",))

    def test_defer_helpers_sync_when_reactor_stopped(self):
        """Confirm defer helpers return fired Deferreds when reactor is not running."""
        d_make = defer_make_password("SuperSecret123!")
        self.assertTrue(d_make.called)
        encoded = d_make.result
        self.assertTrue(encoded.startswith("scrypt$32768$"))

        d_check = defer_check_password("SuperSecret123!", encoded)
        self.assertTrue(d_check.called)
        self.assertEqual(d_check.result, (True, None))


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

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.SESSION_HANDLER[self.s1.uid] = self.s1

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

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.SESSION_HANDLER[self.s1.uid] = self.s1

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

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.s1.uid = account.uid
        evennia.SESSION_HANDLER[self.s1.uid] = self.s1

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

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.account = account
        self.s1.uid = account.uid
        evennia.SESSION_HANDLER[self.s1.uid] = self.s1

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

    @override_settings(MAX_NR_CHARACTERS=5)
    def test_get_character_slots(self):
        "Check get_character_slots method"

        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )

        self.assertEqual(account.get_character_slots(), 5)
        account.delete()

    @override_settings(MAX_NR_CHARACTERS=5)
    def test_get_available_character_slots(self):
        "Check get_available_character_slots method"
        account = create.create_account(
            f"TestAccount{randint(0, 999999)}",
            email="test@test.com",
            password="testpassword",
            typeclass=DefaultAccount,
        )
        self.assertEqual(account.get_available_character_slots(), 5)
        account.delete()


class TestAccountPuppetDeletion(BaseEvenniaTest):
    @override_settings(MULTISESSION_MODE=2)
    def test_puppet_deletion(self):
        # Check for existing chars
        self.assertFalse(self.account.characters, "Account should not have any chars by default.")

        # Add char1 to account's playable characters
        self.account.characters.add(self.char1)
        self.assertTrue(self.account.characters, "Char was not added to account.")

        # See what happens when we delete char1.
        self.char1.delete()
        # Playable char list should be empty.
        self.assertFalse(
            self.account.characters,
            f"Playable character list is not empty! {self.account.characters}",
        )


class TestDefaultAccountEv(BaseEvenniaTest):
    """
    Testing using the EvenniaTest parent

    """

    def test_characters_property(self):
        "test existence of None in _playable_characters Attr"
        self.account.db._playable_characters = [self.char1, None]
        self.assertEqual(self.account.characters.all(), [self.char1])
        self.assertEqual(self.account.db._playable_characters, [self.char1])

    def test_add_character_to_playable_list(self):
        self.assertEqual(self.account.characters.all(), [])
        self.account.characters.add(self.char1)
        self.assertEqual(self.account.characters.all(), [self.char1])

    def test_remove_character_from_playable_list(self):
        self.account.characters.add(self.char1)
        self.assertEqual(self.account.characters.all(), [self.char1])
        self.account.characters.remove(self.char1)
        self.assertEqual(self.account.characters.all(), [])

    def test_puppet_success(self):
        self.account.msg = MagicMock()
        with patch("evennia.accounts.accounts._MULTISESSION_MODE", 2):
            self.account.puppet_object(self.session, self.char1)
            self.account.msg.assert_called_with("You are already puppeting this object.")

    def test_puppet_limit(self):
        "Test that PERMISSION_MULTIPLE_PUPPETS controls who can bypass the puppet limit."
        self.account.msg = MagicMock()
        self.char2.locks.add("puppet:all()")
        with (
            patch.object(self.account, "get_all_puppets", return_value=[MagicMock()]),
            patch("evennia.accounts.accounts._MULTISESSION_MODE", 2),
            patch("evennia.accounts.accounts._MAX_NR_SIMULTANEOUS_PUPPETS", 1),
            patch("evennia.accounts.accounts._PERMISSION_MULTIPLE_PUPPETS", "Developer"),
        ):
            self.account.is_superuser = False
            self.account.permissions.remove("Developer")
            self.account.puppet_object(self.session, self.char2)
            self.account.msg.assert_called_with("You cannot control any more puppets (max 1)")

            self.account.msg.reset_mock()
            self.account.permissions.add("Developer")
            self.account.puppet_object(self.session, self.char2)
            self.account.msg.assert_not_called()

    @patch("evennia.accounts.accounts.time.time", return_value=10000)
    def test_idle_time(self, mock_time):
        self.session.cmd_last_visible = 10000 - 10
        idle = self.account.idle_time
        self.assertEqual(idle, 10)

        # test no sessions
        with patch("evennia.SESSION_HANDLER.sessions_from_account", return_value=[]) as mock_sessh:
            idle = self.account.idle_time
            self.assertEqual(idle, None)

    @patch("evennia.accounts.accounts.time.time", return_value=10000)
    def test_connection_time(self, mock_time):
        self.session.conn_time = 10000 - 10
        conn = self.account.connection_time
        self.assertEqual(conn, 10)

        # test no sessions
        with patch("evennia.SESSION_HANDLER.sessions_from_account", return_value=[]) as mock_sessh:
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
