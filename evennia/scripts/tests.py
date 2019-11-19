# this is an optimized version only available in later Django versions
from unittest import TestCase
from evennia import DefaultScript
from evennia.scripts.models import ScriptDB, ObjectDoesNotExist
from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest
from evennia.scripts.scripts import DoNothing


class TestScript(EvenniaTest):
    def test_create(self):
        "Check the script can be created via the convenience method."
        obj, errors = DefaultScript.create("useless-machine")
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)


class TestScriptDB(TestCase):
    "Check the singleton/static ScriptDB object works correctly"

    def setUp(self):
        self.scr = create_script(DoNothing)

    def tearDown(self):
        try:
            self.scr.delete()
        except ObjectDoesNotExist:
            pass
        del self.scr

    def test_delete(self):
        "Check the script is removed from the database"
        self.scr.delete()
        self.assertFalse(self.scr in ScriptDB.objects.get_all_scripts())

    def test_double_delete(self):
        "What should happen? Isn't it already deleted?"
        with self.assertRaises(ObjectDoesNotExist):
            self.scr.delete()
            self.scr.delete()

    def test_deleted_script_fails_start(self):
        "Would it ever be necessary to start a deleted script?"
        self.scr.delete()
        with self.assertRaises(ObjectDoesNotExist):  # See issue #509
            self.scr.start()
        # Check the script is not recreated as a side-effect
        self.assertFalse(self.scr in ScriptDB.objects.get_all_scripts())

    def test_deleted_script_is_invalid(self):
        "Can deleted scripts be said to be valid?"
        self.scr.delete()
        self.assertFalse(self.scr.is_valid())  # assertRaises? See issue #509
