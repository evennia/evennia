from datetime import datetime
import json
from dateutil.parser import parse
from django.conf import settings
from evennia.contrib.collab.perms import (
    set_owner, quota_queryset, get_limit_for, quota_check, get_owner,
    is_owner, owner_tag_key, prefix_check, attr_check)
from evennia.contrib.collab.test_base import CollabTest
from evennia.contrib.collab.typeclasses import (
    AdmHiddenAttributeHandler, UserHiddenAttributeHandler, UserAttributeHandler
)
from evennia.typeclasses.models import AttributeHandler
from evennia.utils.create import create_object
from mock import patch

ga = object.__getattribute__


class QuotaTest(CollabTest):
    """
    Test Quotas, their limits and their counts.
    """
    def test_quota_queryset(self):
        """
        Verify we get all objects of a certain type owned by the user.
        """
        set_owner(self.account, self.obj1)
        set_owner(self.account, self.obj2)
        tc_path = settings.COLLAB_TYPES['object']['typeclass']
        self.assertEqual(quota_queryset(self.account, tc_path).count(), 2)
        self.obj2.delete()
        self.assertEqual(quota_queryset(self.account, tc_path).count(), 1)

    def test_quota_bypass(self):
        """
        Verify immortals are no subject to quotas.
        """
        # user1 is an immortal. The default lock should pass for infinite.
        self.assertEqual(quota_check(self.account, 'object'), float('inf'))
        set_owner(self.account, self.obj1)
        self.assertEqual(quota_check(self.account, 'object'), float('inf'))

    def test_quota_limit(self):
        """
        Check to make sure we can consistently set and track limits for
        object types.
        """
        with patch.dict(settings.COLLAB_TYPES['object'], {'quota': 5}):
            settings.COLLAB_TYPES['object']['quota'] = 5
            self.assertEqual(get_limit_for(self.account2, 'object'), 5)
            set_owner(self.account2, self.obj1)
            # This function is not for how many are left, but how many may be
            # made total.
            self.assertEqual(get_limit_for(self.account2, 'object'), 5)
            self.assertEqual(quota_check(self.account, 'object'), float('inf'))

    def test_quota_check(self):
        """
        Verify that quota checks properly tally the number of remaining
        available object creations of each type.
        """
        obj3 = create_object(self.object_typeclass, 'Obj3')
        with patch.dict(settings.COLLAB_TYPES['object'], {'quota': 2}):
            self.assertEqual(quota_check(self.account2, 'object'), 2)
            set_owner(self.account2, self.obj1)
            self.assertEqual(quota_check(self.account2, 'object'), 1)
            set_owner(self.account2, self.obj2)
            self.assertEqual(quota_check(self.account2, 'object'), 0)
            set_owner(self.account2, obj3)
            self.assertEqual(quota_check(self.account2, 'object'), 0)
            obj3.delete()
            self.assertEqual(quota_check(self.account2, 'object'), 0)
            self.obj1.delete()
            self.assertEqual(quota_check(self.account2, 'object'), 1)
            self.obj2.delete()
            self.assertEqual(quota_check(self.account2, 'object'), 2)

    def test_quota_override(self):
        """
        Make sure that a user's quota can be set with an override.
        """
        self.account2.admdb.quota_object = 5
        self.assertEqual(quota_check(self.account2, 'object'), 5)
        self.account2.admdb.quota_object = 3
        self.assertEqual(quota_check(self.account2, 'object'), 3)
        set_owner(self.account2, self.obj1)
        self.assertEqual(quota_check(self.account2, 'object'), 2)


class OwnerTest(CollabTest):
    """
    Test functions dealing with ownership management and checking.
    """
    def test_set_get_owner(self):
        """
        Tests that set and get for owners works. Indirectly tests
        parse_owner as well.
        """
        set_owner(self.account, self.obj1)
        self.assertEqual(self.account, get_owner(self.obj1))
        set_owner(self.account2, self.obj1)
        self.assertEqual(self.account2, get_owner(self.obj1))

    def test_is_owner(self):
        """
        Verify that is_owner returns True or False based on ownership, and
        doesn't falsely report ownership for higher level privileges.
        """
        set_owner(self.account, self.obj1)
        self.assertTrue(is_owner(self.account, self.obj1))
        self.assertFalse(is_owner(self.account2, self.obj1))
        # account1 is an immortal, but not the owner.
        self.assertFalse(is_owner(self.account, self.obj2))

    def test_owner_tag_key(self):
        """
        Verify that the ownership tags contain the proper information and are
        serialized correctly.
        """
        test_date = datetime(
            year=2014, month=5, day=4, hour=6, minute=2, second=45,
            microsecond=83)
        self.account.db_date_created = test_date
        old_id = self.account.id
        self.account.id = 5
        try:
            tag = json.loads(owner_tag_key(self.account))
            self.assertEqual(tag['id'], 5)
            self.assertEqual(
                parse(tag['date']),
                test_date)
            self.assertEqual(tag['cls'], 'account')
        finally:
            self.account.id = old_id


class AttrTest(CollabTest):
    def test_prefix_check(self):
        """
        Verify that the attribute prefix checker returns the right handler
        for properly prefixed attributes.

        Indirectly tests get_handler.
        """
        name, handler = prefix_check(self.account, 'admh_test')
        self.assertEqual(name, 'test')
        self.assertEqual(ga(handler, '__class__'), AdmHiddenAttributeHandler)
        name, handler = prefix_check(self.obj1, 'usrh_stuff')
        self.assertEqual(name, 'stuff')
        self.assertEqual(ga(handler, '__class__'), UserHiddenAttributeHandler)
        # Make sure the default is UserAttributeHandler.
        name, handler = prefix_check(self.account, 'default')
        self.assertEqual(name, 'default')
        self.assertEqual(ga(handler, '__class__'), UserAttributeHandler)
        # If there's nothing before the underscore, it's to be set on .db.
        name, handler = prefix_check(self.account, '_things')
        self.assertEqual(name, 'things')
        self.assertEqual(ga(handler, '__class__'), AttributeHandler)

    def perm_checks(self, account, checks, results, obj):
        """
        Helper method for test_attr_check. Runs a series of tests for
        permissions against attribute handlers on an object given a account.
        """
        for check, result in zip(checks, results):
            access_type, attr_type = check
            self.assertIs(
                attr_check(account, obj, access_type, attr_type),
                result
            )

    def test_attr_check(self):
        """
        Verify that permissions checks on attributes work as expected.

        Indirectly tests controls() lockfunc.
        """
        checks = (
            ('read', 'admh'),
            ('write', 'admh'),
            ('read', ''),
            ('write', ''),
            ('read', 'usr'),
            ('write', 'usr'),
            ('read', 'pub'),
            ('write', 'pub')
        )
        # account1 is a developer. All of these should be True.
        results = [True for _ in checks]
        self.perm_checks(self.account, checks, results, self.obj1)

        # account2 is a normal account who does not own obj1.
        results = [False, False, False, False, True, False, True, True]
        self.perm_checks(self.account2, checks, results, self.obj1)

        # account2 is a normal account who owns obj2.
        set_owner(self.account2, self.obj2)
        results = [False, False, False, False, True, True, True, True]
        self.perm_checks(self.account2, checks, results, self.obj2)
