import unittest

from django.conf import settings
from django.test import override_settings
from evennia import DefaultScript
from evennia.utils import containers
from evennia.utils.utils import class_from_module

_BASE_TYPECLASS = class_from_module(settings.BASE_SCRIPT_TYPECLASS)


class UnittestGoodScript(DefaultScript):
    pass


class UnittestInvalidScript:
    pass


class TestGlobalScriptContainer(unittest.TestCase):

    def test_init_with_no_scripts(self):
        gsc = containers.GlobalScriptContainer()

        self.assertEqual(len(gsc.loaded_data), 0)

    @override_settings(GLOBAL_SCRIPTS={})
    def test_start_with_no_scripts(self):
        gsc = containers.GlobalScriptContainer()

        gsc.start()

        self.assertEqual(len(gsc.typeclass_storage), 0)

    @override_settings(GLOBAL_SCRIPTS={"script_name": {}})
    def test_start_with_typeclassless_script(self):
        """No specified typeclass should fallback to base"""
        gsc = containers.GlobalScriptContainer()

        gsc.start()

        self.assertEqual(len(gsc.typeclass_storage), 1)
        self.assertIn("script_name", gsc.typeclass_storage)
        self.assertEqual(gsc.typeclass_storage["script_name"], _BASE_TYPECLASS)

    @override_settings(
        GLOBAL_SCRIPTS={
            "script_name": {"typeclass": "evennia.utils.tests.test_containers.NoScript"}
        }
    )
    def test_start_with_nonexistent_script(self):
        """Missing script class should fall back to base"""
        gsc = containers.GlobalScriptContainer()

        gsc.start()

        self.assertEqual(len(gsc.typeclass_storage), 1)
        self.assertIn("script_name", gsc.typeclass_storage)
        self.assertEqual(gsc.typeclass_storage["script_name"], _BASE_TYPECLASS)

    @override_settings(
        GLOBAL_SCRIPTS={
            "script_name": {"typeclass": "evennia.utils.tests.test_containers.UnittestGoodScript"}
        }
    )
    def test_start_with_valid_script(self):
        gsc = containers.GlobalScriptContainer()

        gsc.start()

        self.assertEqual(len(gsc.typeclass_storage), 1)
        self.assertIn("script_name", gsc.typeclass_storage)
        self.assertEqual(gsc.typeclass_storage["script_name"], UnittestGoodScript)

    @override_settings(
        GLOBAL_SCRIPTS={
            "script_name": {
                "typeclass": "evennia.utils.tests.test_containers.UnittestInvalidScript"
            }
        }
    )
    def test_start_with_invalid_script(self):
        """Script class doesn't implement required methods methods"""
        gsc = containers.GlobalScriptContainer()

        with self.assertRaises(AttributeError) as err:
            gsc.start()
        # check for general attribute failure on the invalid class to preserve against future code-rder changes
        self.assertTrue(
            str(err.exception).startswith("type object 'UnittestInvalidScript' has no attribute"),
            err.exception,
        )

    @override_settings(
        GLOBAL_SCRIPTS={
            "script_name": {"typeclass": "evennia.utils.tests.data.broken_script.BrokenScript"}
        }
    )
    def test_start_with_broken_script(self):
        """Un-importable script should traceback"""
        gsc = containers.GlobalScriptContainer()

        with self.assertRaises(Exception) as err:
            gsc.start()
        # exception raised by imported module
        self.assertTrue(
            str(err.exception).startswith("cannot import name 'nonexistent_module' from 'evennia'"),
            err.exception,
        )

    @override_settings(
        GLOBAL_SCRIPTS={
            "script_name": {"typeclass": "evennia.utils.tests.test_containers.UnittestGoodScript"}
        }
    )
    def test_using_global_script__all(self):
        """
        Using the GlobalScriptContainer.all() to get all scripts

        Tests https://github.com/evennia/evennia/issues/3788

        """
        from evennia.scripts.models import ScriptDB

        ScriptDB.objects.all().delete()  # clean up any old scripts

        gsc = containers.GlobalScriptContainer()
        script = gsc.get("script_name")
        result = gsc.all()
        self.assertEqual(result, [script])
