# -*- coding: utf-8 -*-

from mock import Mock, MagicMock
from random import randint
from unittest import TestCase

from django.test import override_settings
from evennia.accounts.accounts import AccountSessionHandler

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.server.session import Session
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestAccountSessionHandler(TestCase):
    "Check AccountSessionHandler class"

    def setUp(self):
        self.account = create.create_account(
            "TestAccount%s" % randint(0, 999999), email="test@test.com",
            password="testpassword", typeclass=DefaultAccount)
        self.handler = AccountSessionHandler(self.account)

    def tearDown(self):
        if hasattr(self, 'account'):
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
        
class TestDefaultGuest(EvenniaTest):
    "Check DefaultGuest class"
    
    ip = '212.216.134.22'
    
    def test_authenticate(self):
        # Guest account should not be permitted
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertFalse(account, 'Guest account was created despite being disabled.')
        
        settings.GUEST_ENABLED = True
        settings.GUEST_LIST = ['bruce_wayne']
        
        # Create a guest account
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertTrue(account, 'Guest account should have been created.')
        
        # Create a second guest account
        account, errors = DefaultGuest.authenticate(ip=self.ip)
        self.assertFalse(account, 'Two guest accounts were created with a single entry on the guest list!')
        
        settings.GUEST_ENABLED = False
        
class TestDefaultAccountAuth(EvenniaTest):
    
    def setUp(self):
        super(TestDefaultAccountAuth, self).setUp()
        
        self.password = "testpassword"
        self.account.delete()
        self.account = create.create_account("TestAccount%s" % randint(100000, 999999), email="test@test.com", password=self.password, typeclass=DefaultAccount)
        
    def test_authentication(self):
        "Confirm Account authentication method is authenticating/denying users."
        # Valid credentials
        obj, errors = DefaultAccount.authenticate(self.account.name, self.password)
        self.assertTrue(obj, 'Account did not authenticate given valid credentials.')
        
        # Invalid credentials
        obj, errors = DefaultAccount.authenticate(self.account.name, 'xyzzy')
        self.assertFalse(obj, 'Account authenticated using invalid credentials.')
        
    def test_create(self):
        "Confirm Account creation is working as expected."
        # Create a normal account
        account, errors = DefaultAccount.create(username='ziggy', password='stardust11')
        self.assertTrue(account, 'New account should have been created.')
        
        # Try creating a duplicate account
        account, errors = DefaultAccount.create(username='Ziggy', password='starman11')
        self.assertFalse(account, 'Duplicate account name should not have been allowed.')
        
    def test_throttle(self):
        "Confirm throttle activates on too many failures."
        for x in xrange(20):
            obj, errors = DefaultAccount.authenticate(self.account.name, 'xyzzy', ip='12.24.36.48')
            self.assertFalse(obj, 'Authentication was provided a bogus password; this should NOT have returned an account!')
        
        self.assertTrue('too many login failures' in errors[-1].lower(), 'Failed logins should have been throttled.')
        
    def test_username_validation(self):
        "Check username validators deny relevant usernames"
        # Should not accept Unicode by default, lest users pick names like this
        result, error = DefaultAccount.validate_username('¯\_(ツ)_/¯')
        self.assertFalse(result, "Validator allowed kanji in username.")
        
        # Should not allow duplicate username
        result, error = DefaultAccount.validate_username(self.account.name)
        self.assertFalse(result, "Duplicate username should not have passed validation.")
        
        # Should not allow username too short
        result, error = DefaultAccount.validate_username('xx')
        self.assertFalse(result, "2-character username passed validation.")

    def test_absolute_url(self):
        "Get URL for account detail page on website"
        self.account = create.create_account("TestAccount%s" % randint(100000, 999999),
                email="test@test.com", password="testpassword", typeclass=DefaultAccount)
        self.assertTrue(self.account.web_get_detail_url())

    def test_admin_url(self):
        "Get object's URL for access via Admin pane"
        self.account = create.create_account("TestAccount%s" % randint(100000, 999999),
                email="test@test.com", password="testpassword", typeclass=DefaultAccount)
        self.assertTrue(self.account.web_get_admin_url())
        self.assertTrue(self.account.web_get_admin_url() != '#')

    def test_password_validation(self):
        "Check password validators deny bad passwords"

        self.account = create.create_account("TestAccount%s" % randint(100000, 999999),
                email="test@test.com", password="testpassword", typeclass=DefaultAccount)
        for bad in ('', '123', 'password', 'TestAccount', '#', 'xyzzy'):
            self.assertFalse(self.account.validate_password(bad, account=self.account)[0])

        "Check validators allow sufficiently complex passwords"
        for better in ('Mxyzptlk', "j0hn, i'M 0n1y d4nc1nG"):
            self.assertTrue(self.account.validate_password(better, account=self.account)[0])

    def test_password_change(self):
        "Check password setting and validation is working as expected"
        self.account = create.create_account("TestAccount%s" % randint(0, 9),
                email="test@test.com", password="testpassword", typeclass=DefaultAccount)

        from django.core.exceptions import ValidationError
        # Try setting some bad passwords
        for bad in ('', '#', 'TestAccount', 'password'):
            self.assertRaises(ValidationError, self.account.set_password, bad)

        # Try setting a better password (test for False; returns None on success)
        self.assertFalse(self.account.set_password('Mxyzptlk'))

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
            "TestAccount%s" % randint(0, 999999), email="test@test.com",
            password="testpassword", typeclass=DefaultAccount)
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.logged_in = True
        self.s1.data_out = Mock(return_value=None)

        obj = Mock()
        self.s1.puppet = obj
        account.puppet_object(self.s1, obj)
        self.s1.data_out.assert_called_with(options=None, text="You are already puppeting this object.")
        self.assertIsNone(obj.at_post_puppet.call_args)

    def test_puppet_object_no_permission(self):
        "Check puppet_object method called, no permission"

        import evennia.server.sessionhandler

        account = create.create_account("TestAccount%s" % randint(0, 999999), email="test@test.com", password="testpassword", typeclass=DefaultAccount)
        self.s1.uid = account.uid
        evennia.server.sessionhandler.SESSIONS[self.s1.uid] = self.s1

        self.s1.data_out = MagicMock()
        obj = Mock()
        obj.access = Mock(return_value=False)

        account.puppet_object(self.s1, obj)

        self.assertTrue(self.s1.data_out.call_args[1]['text'].startswith("You don't have permission to puppet"))
        self.assertIsNone(obj.at_post_puppet.call_args)

    @override_settings(MULTISESSION_MODE=0)
    def test_puppet_object_joining_other_session(self):
        "Check puppet_object method called, joining other session"

        import evennia.server.sessionhandler

        account = create.create_account("TestAccount%s" % randint(0, 999999), email="test@test.com", password="testpassword", typeclass=DefaultAccount)
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
        self.assertTrue(self.s1.data_out.call_args[1]['text'].endswith("from another of your sessions.|n"))
        self.assertTrue(obj.at_post_puppet.call_args[1] == {})

    def test_puppet_object_already_puppeted(self):
        "Check puppet_object method called, already puppeted"

        import evennia.server.sessionhandler

        account = create.create_account("TestAccount%s" % randint(0, 999999), email="test@test.com", password="testpassword", typeclass=DefaultAccount)
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
        self.assertTrue(self.s1.data_out.call_args[1]['text'].endswith("is already puppeted by another Account."))
        self.assertIsNone(obj.at_post_puppet.call_args)


class TestAccountPuppetDeletion(EvenniaTest):

    @override_settings(MULTISESSION_MODE=2)
    def test_puppet_deletion(self):
        # Check for existing chars
        self.assertFalse(self.account.db._playable_characters, 'Account should not have any chars by default.')

        # Add char1 to account's playable characters
        self.account.db._playable_characters.append(self.char1)
        self.assertTrue(self.account.db._playable_characters, 'Char was not added to account.')

        # See what happens when we delete char1.
        self.char1.delete()
        # Playable char list should be empty.
        self.assertFalse(self.account.db._playable_characters,
                         'Playable character list is not empty! %s' % self.account.db._playable_characters)
