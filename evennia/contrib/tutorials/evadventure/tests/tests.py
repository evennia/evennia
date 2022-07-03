"""
Tests for EvAdventure.

"""

from unittest.mock import patch, MagicMock, call
from parameterized import parameterized
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest
from .characters import EvAdventureCharacter, EquipmentHandler, EquipmentError
from .objects import EvAdventureObject
from . import enums
from . import combat_turnbased
from . import rules
from . import random_tables
