from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from evennia.contrib.collab.commands import CmdCreate, CmdBuildNick, CmdDig, CmdOpen, CmdDestroy
from evennia.contrib.collab.perms import quota_queryset, get_owner, set_owner
from evennia.contrib.collab.test_base import CollabTest


class CollabCreateCommandTestMixin(object):
    """
    Test collaborative commands. Verify they have the expected effects.
    """
    command = CmdCreate
    type_key = 'object'

    def create(self, cmd_string='thing', build_nick='this_thing', caller=None):
        caller = caller or self.char1
        self.call(self.command(), cmd_string, caller=caller)
        self.call(CmdBuildNick(), build_nick, caller=caller)
        return caller.search(build_nick)

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
        old_count = quota_queryset(self.player, self.get_typeclass()).count()
        self.create()
        new_count = quota_queryset(self.player, self.get_typeclass()).count()
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
        owner = get_owner(thing, player_check=True)
        self.assertEqual(owner, self.player)

    def test_perm_check(self):
        """
        Verify a character without build permissions can't create.
        """
        thing = self.create(caller=self.char2)
        self.assertIs(thing, None)

    def test_respect_quota(self):
        """
        Verify that an object is not created by the command if the user's quota is already hit.
        """
        settings.COLLAB_TYPES[self.type_key]['quota'] = 1
        self.player2.permissions.add("Builders")
        thing = self.create(caller=self.char2)
        self.assertTrue(thing)
        thing2 = self.create('dingus', caller=self.char2, build_nick='fail_please')
        self.assertFalse(thing2)
        self.assertEqual(quota_queryset(self.player2, self.get_typeclass()).count(), 1)


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
        set_owner(self.player, self.obj1)
        self.call(CmdDestroy(), self.obj1.name)
        self.assertRaises(ObjectDoesNotExist, getattr, self.obj1, 'name')

    def test_perms_failure(self):
        """
        Make sure destroy does not work on objects the user does not own.
        """
        set_owner(self.player, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.player2)
        # Should not raise an exception, because it still exists.
        self.obj1.name
        # Force should not help here.
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.player)
        self.obj1.name

    def test_destroy_override(self):
        """
        Verify an object that a user does not own is not destroyed unless the user really means it.
        """
        set_owner(self.player2, self.obj1)
        self.call(CmdDestroy(), self.obj1.name, caller=self.char1)
        self.obj1.name
        self.call(CmdDestroy(), '/force %s' % self.obj1.name, caller=self.char1)
        self.assertRaises(ObjectDoesNotExist, getattr, self.obj1, 'name')
