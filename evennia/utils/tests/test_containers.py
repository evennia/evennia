import unittest

from evennia.utils import containers
from django.conf import settings
from django.test import override_settings
from evennia.utils.utils import class_from_module
from evennia.scripts.scripts import DefaultScript

_BASE_SCRIPT_TYPECLASS = class_from_module(settings.BASE_SCRIPT_TYPECLASS)

class GoodScript(_BASE_SCRIPT_TYPECLASS):
  pass

class BadScript:
  """Not subclass of _BASE_SCRIPT_TYPECLASS,"""
  pass

class WorseScript(_BASE_SCRIPT_TYPECLASS):
  """objects will fail upon call"""
  @property
  def objects(self):
    from evennia import module_that_doesnt_exist

class QuestionableScript(DefaultScript):
  """Does NOT derive from settings.BASE_SCRIPT_TYPECLASS so it would fail."""
  pass

class TestGlobalScriptContainer(unittest.TestCase):

  def test_init_with_no_scripts(self):
    gsc = containers.GlobalScriptContainer()

    self.assertEqual(len(gsc.loaded_data), 0)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {}})
  def test_init_with_typeclassless_script(self):

    gsc = containers.GlobalScriptContainer()

    self.assertEqual(len(gsc.loaded_data), 1)
    self.assertIn('script_name', gsc.loaded_data)

  def test_start_with_no_scripts(self):
    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 0)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {}})
  def test_start_with_typeclassless_script_defaults_to_base(self):
    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 1)
    self.assertIn('script_name', gsc.typeclass_storage)
    self.assertEqual(gsc.typeclass_storage['script_name'], _BASE_SCRIPT_TYPECLASS)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.GoodScript'}})
  def test_start_with_typeclassed_script_loads_it(self):
    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 1)
    self.assertIn('script_name', gsc.typeclass_storage)
    self.assertEqual(gsc.typeclass_storage['script_name'], GoodScript)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.BadScript'}})
  def test_start_with_bad_typeclassed_script_skips_it(self):
    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 0)
    self.assertNotIn('script_name', gsc.typeclass_storage)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.QuestionableScript'}})
  def test_start_with_questionably_subclassed_script_skips_it(self):
    # Make sure _BASE_SCRIPT_TYPECLASS is NOT DefaultScript but it's a subclass
    assert issubclass(_BASE_SCRIPT_TYPECLASS, DefaultScript) and _BASE_SCRIPT_TYPECLASS != DefaultScript

    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 0)
    self.assertNotIn('script_name', gsc.typeclass_storage)

  @override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.WorstScript'}})
  def test_start_with_worst_typeclassed_script_skips_it(self):
    gsc = containers.GlobalScriptContainer()

    gsc.start()

    self.assertEqual(len(gsc.typeclass_storage), 0)
    self.assertNotIn('script_name', gsc.typeclass_storage)
