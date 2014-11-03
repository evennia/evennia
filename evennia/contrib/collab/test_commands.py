from uuid import uuid4
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from mock import patch
from evennia.contrib.collab.commands import CmdCreate, CmdBuildNick, CmdDig, CmdOpen, CmdDestroy, CmdChown, CmdLink, \
    CmdCollabCopy
from evennia.contrib.collab.perms import quota_queryset, get_owner, set_owner, quota_check
from evennia.contrib.collab.test_base import CollabTest


class CollabCommandTestMixin(object):
    """
    Helpful mixin for
    """
    def retrieve(self, caller):
        """
        Retrieve the last object created by the caller.
        """
        build_nick = str(uuid4())
        self.call(CmdBuildNick(), build_nick, caller=caller)
        return caller.search(build_nick)


class CollabCreateCommandTestMixin(CollabCommandTestMixin):
    """
    Test collaborative commands. Verify they have the expected effects.
    """
    command = CmdCreate
    type_key = 'object'

    def create(self, cmd_string='thing', caller=None):
        caller = caller or self.char1
        self.call(self.command(), cmd_string, caller=caller)
        return self.retrieve(caller)

    def get_typeclass(self):
        return settings.COLLAB_TYPES[self.type_key]['typeclass']

    def test_create_typeclass(self):
        """
        Test creating an object.
        """
        thing = self.create()
        self.assertEqual(thing.typename, self.get_typeclass().split('.')[-1])

    def test_set_destination(self):
        """
        Test that setting a destination for an object works.
        """
        thing = self.create('thing=here')
        self.assertTrue(thing.destination)
        self.assertEqual(thing.destination, self.char1.location)

    def test_set_aliases(self):
        """
        Test that aliases can be set for created objects.
        """
        thing = self.create('thing;thingus;thingectomy')
        self.assertEqual(set(thing.aliases.all()), {'thingus', 'thingectomy'})

    def test_affects_quota(self):
        """
        Make sure creating objects of a specific type affects the quota for that type.
        """
        old_count = quota_queryset(self.account, self.get_typeclass()).count()
        self.create()
        new_count = quota_queryset(self.account, self.get_typeclass()).count()
        self.assertEquals(new_count, old_count + 1)

    def test_sets_display_owner(self):
        """
        Ensure the 'display owner' of an object is set upon creation.
        """
        thing = self.create()
        owner = get_owner(thing)
        self.assertEqual(owner, self.char1)

    def test_sets_owner(self):
        """
        Ensure the 'true owner' of an object is set upon creation.
        """
        thing = self.create()
        owner = get_owner(thing, account_check=True)
        self.assertEqual(owner, self.account)

    def test_perm_check(self):
        """
        Verify a character without build permissions can't create.
        """
        self.account2.permissions.clear()
        self.account2.permissions.add("account")
        thing = self.create(caller=self.char2)
        self.assertIs(thing, None)

    def test_respect_quota(self):
        """
        Verify that an object is not created by the command if the user's quota is already hit.
        """
        with patch.dict(settings.COLLAB_TYPES[self.type_key], {'quota': 1}):
            settings.COLLAB_TYPES[self.type_key]['quota'] = 1
            thing = self.create(caller=self.char2)
            self.assertTrue(thing)
            thing2 = self.create('dingus', caller=self.char2)
            self.assertFalse(thing2)
            self.assertEqual(quota_queryset(self.account2, self.get_typeclass()).count(), 1)


class CreateCmdTest(CollabCreateCommandTestMixin, CollabTest):
    pass


class CmdDigTest(CollabCreateCommandTestMixin, CollabTest):
    command = CmdDig
    type_key = 'room'


class OpenCmdTest(CollabCreateCommandTestMixin, CollabTest):
    command = CmdOpen
    type_key = 'exit'


class CmdDestroyTest(CollabTest):
    """
    Tests the destroy command.
    """
    def test_destroy_object(self):
        """
        Verify destroy's base functionality.
        """
        set_owner(self.account, self.obj1)
        self.call(CmdDestroy(), self.obj1.name)
        self.assertRaises(ObjectDoesNotExist, self.obj1.delete)

    def test_perms_failure(self):
        """
        Make sure destroy does not work on objects the user does not own.
        """
        set_owner(self.account, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.account2)
        self.assertFalse(self.obj1._is_deleted)
        # Force should not help here.
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.account)
        self.assertFalse(self.obj1._is_deleted)

    def test_destroy_override(self):
        """
        Verify an object that a user does not own is not destroyed unless the user really means it.
        """
        set_owner(self.account2, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.char1)
        self.assertFalse(self.obj1._is_deleted)
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.char1)
        self.assertTrue(self.obj1._is_deleted)


class TestCmdChown(CollabTest):
    """
    Tests that CmdChown works.
    """
    def test_good_chown(self):
        """
        Verify that a user who should be able to chown an object can.
        """
        self.assertNotEqual(get_owner(self.obj2), self.char1)
        self.assertNotEqual(get_owner(self.obj2, account_check=True), self.account)
        # account is an immortal, so should always be able to chown.
        self.call(CmdChown(), self.obj2.name, caller=self.char1)
        self.assertEqual(get_owner(self.obj2), self.char1)
        self.assertEqual(get_owner(self.obj2, account_check=True), self.account)

    def test_bad_chown(self):
        """
        Verify that a user who should not be able to chown cannot.
        """
        self.assertNotEqual(get_owner(self.obj1), self.char2)
        self.assertNotEqual(get_owner(self.obj1, account_check=True), self.account2)
        self.call(CmdChown(), self.obj1.name, caller=self.char2)
        self.assertNotEqual(get_owner(self.obj1), self.char2)
        self.assertNotEqual(get_owner(self.obj1, account_check=True), self.account2)


class TestCmdLink(CollabTest, CollabCommandTestMixin):
    """
    Verify linking works sanely.
    """

    def test_can_link(self):
        """
        Make sure that a user can link an exit they own to a room they own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.room2)
        set_owner(self.char2, self.exit)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertEqual(self.exit.destination, self.room2)

    def test_no_link_to_unowned(self):
        """
        Make sure that a user cannot link to a place they do not own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.exit)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertFalse(self.exit.destination)

    def test_no_link_unowned_exit(self):
        """
        Make sure that a user cannot link up an exit they do not own.
        """
        set_owner(self.char2, self.room1)
        set_owner(self.char2, self.room2)
        self.exit.destination = None
        self.call(CmdLink(), '%s=#%s' % (self.exit.name, self.room2.id), caller=self.char2)
        self.assertFalse(self.exit.destination)


class TestCmdCopy(CollabTest, CollabCommandTestMixin):
    """
    Test the copy command with collab enhancements.
    """

    def test_copy(self):
        """
        Test basic copying works.
        """
        self.char2.account = self.account2
        set_owner(self.char2, self.obj1)
        original_quota = quota_check(self.char2, settings.COLLAB_DEFAULT_TYPE)
        self.call(CmdCollabCopy(), self.obj1.name, caller=self.char2, msg='Identical')
        copied = self.retrieve(self.char2)
        self.assertEqual(self.obj1.name + '_copy', copied.name)
        self.assertEqual(self.obj1.typeclass_path, copied.typeclass_path)
        self.assertLess(quota_check(self.char2, settings.COLLAB_DEFAULT_TYPE), original_quota)

    def test_no_quota_circumvention(self):
        """
        Make sure a user can't skirt quotas by copying.
        """
        self.account2.admdb.quota_object = 2
        set_owner(self.account2, self.obj1)
        set_owner(self.account2, self.obj2)
        self.call(CmdCollabCopy(), self.obj1.name, caller=self.account2)
        self.assertIsNone(self.retrieve(self.account2))
