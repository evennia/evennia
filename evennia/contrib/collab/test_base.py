from copy import deepcopy
from evennia.contrib.collab import collab_settings
from evennia.contrib.collab.typeclasses import CollabCharacter, CollabObject, CollabPlayer
from django.conf import settings
from evennia.commands.default.tests import CommandTest
from evennia.locks.lockhandler import _cache_lockfuncs


class CollabTest(CommandTest):
    character_typeclass = CollabCharacter
    object_typeclass = CollabObject
    player_typeclass = CollabPlayer

    def setUp(self):
        """
        Some tests will involve manipulating quota number settings.
        """
        self.old_settings = dict(settings.__dict__)
        # This may change during the test. Save it for restore.
        self.old_types = deepcopy(collab_settings.COLLAB_TYPES)
        settings.__dict__.update(collab_settings.__dict__)
        settings.LOCK_FUNC_MODULES += ('evennia.contrib.collab.locks',)
        _cache_lockfuncs()
        super(CollabTest, self).setUp()

    def tearDown(self):
        settings.__dict__.update(self.old_settings)
        collab_settings.COLLAB_TYPES = self.old_types
        settings.LOCK_FUNC_MODULES = settings.LOCK_FUNC_MODULES[:-1]
        _cache_lockfuncs()
        super(CollabTest, self).tearDown()
