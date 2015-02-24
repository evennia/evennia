from django.test import override_settings
from evennia.contrib.collab import collab_settings
from evennia.contrib.collab.typeclasses import CollabCharacter, CollabObject, CollabAccount, CollabExit
from evennia.commands.default.tests import CommandTest
from evennia.locks.lockhandler import _cache_lockfuncs
from evennia import settings_default


collab_overrides = {key: value for key, value in collab_settings.__dict__.items() if key.isupper()}
collab_overrides['LOCK_FUNC_MODULES'] = settings_default.LOCK_FUNC_MODULES + ('evennia.contrib.collab.locks',)


@override_settings(**collab_overrides)
class CollabTest(CommandTest):
    character_typeclass = CollabCharacter
    object_typeclass = CollabObject
    account_typeclass = CollabAccount
    exit_typeclass = CollabExit

    def setUp(self):
        """
        The lock functions will be overwritten, so we'll need to recache them.
        """
        _cache_lockfuncs()
        super(CollabTest, self).setUp()

    def tearDown(self):
        _cache_lockfuncs()
        super(CollabTest, self).tearDown()
