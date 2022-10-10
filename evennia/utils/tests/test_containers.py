import unittest

from evennia.utils import containers
from django.conf import settings
from django.test import override_settings
from evennia.utils.utils import class_from_module
from evennia import DefaultScript

_BASE_TYPECLASS = class_from_module(settings.BASE_SCRIPT_TYPECLASS)

class GoodScript(DefaultScript):
    pass

class BrokenScript(DefaultScript):
	"""objects will fail upon call"""
	@property
	def objects(self):
		from evennia import module_that_doesnt_exist

class TestGlobalScriptContainer(unittest.TestCase):

	def test_init_with_no_scripts(self):
		gsc = containers.GlobalScriptContainer()

		self.assertEqual(len(gsc.loaded_data), 0)

	@override_settings(GLOBAL_SCRIPTS={})
	def test_start_with_no_scripts(self):
		gsc = containers.GlobalScriptContainer()

		gsc.start()

		self.assertEqual(len(gsc.typeclass_storage), 0)

	@override_settings(GLOBAL_SCRIPTS={'script_name': {}})
	def test_start_with_typeclassless_script(self):
		"""No specified typeclass should fallback to base"""
		gsc = containers.GlobalScriptContainer()

		gsc.start()

		self.assertEqual(len(gsc.typeclass_storage), 1)
		self.assertIn('script_name', gsc.typeclass_storage)
		self.assertEqual(gsc.typeclass_storage['script_name'], _BASE_TYPECLASS)

	@override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.NoScript'}})
	def test_start_with_nonexistent_script(self):
		"""Missing script class should fall back to base"""
		gsc = containers.GlobalScriptContainer()

		gsc.start()

		self.assertEqual(len(gsc.typeclass_storage), 1)
		self.assertIn('script_name', gsc.typeclass_storage)
		self.assertEqual(gsc.typeclass_storage['script_name'], _BASE_TYPECLASS)

	@override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.GoodScript'}})
	def test_start_with_valid_script(self):
		gsc = containers.GlobalScriptContainer()

		gsc.start()

		self.assertEqual(len(gsc.typeclass_storage), 1)
		self.assertIn('script_name', gsc.typeclass_storage)
		self.assertEqual(gsc.typeclass_storage['script_name'], GoodScript)

	@override_settings(GLOBAL_SCRIPTS={'script_name': {'typeclass': 'evennia.utils.tests.test_containers.BrokenScript'}})
	def test_start_with_broken_script(self):
		"""Broken script module should traceback"""
		gsc = containers.GlobalScriptContainer()

		with self.assertRaises(Exception) as cm:
				gsc.start()
				self.fail("An exception was expected but it didn't occur.")
