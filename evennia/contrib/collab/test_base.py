from copy import deepcopy
from contrib.collab import collab_settings
from contrib.collab.typeclasses import CollabCharacter, CollabObject, CollabPlayer
from django.conf import settings
from src.commands.default.tests import CommandTest
from src.locks.lockhandler import _cache_lockfuncs


class CollabTest(CommandTest):
    character_typeclass = CollabCharacter
    object_typeclass = CollabObject
    player_typeclass = CollabPlayer

    def setUp(self):
        """
        Some tests will involve manipulating quota number settings.
        """
        self.old_types = collab_settings.CREATE_TYPES
        collab_settings.CREATE_TYPES = deepcopy(self.old_types)
        self.types = collab_settings.CREATE_TYPES
        settings.LOCK_FUNC_MODULES += ('contrib.collab.locks',)
        _cache_lockfuncs()
        super(CollabTest, self).setUp()

    def tearDown(self):
        collab_settings.CREATE_TYPES = self.old_types
        settings.LOCK_FUNC_MODULES = settings.LOCK_FUNC_MODULES[:-1]
        _cache_lockfuncs()
        super(CollabTest, self).tearDown()