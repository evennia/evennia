try:
    # this is an optimized version only available in later Django versions
    from django.utils.unittest import TestCase
except ImportError:
    # if the first fails, we use the old version
    from django.test import TestCase

from src.scripts.models import ScriptDB, ObjectDoesNotExist
from src.utils.create import create_script
from src.scripts import DoNothing
import unittest
from django.conf import settings


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

    #@unittest.skip("not implemented")
    #def test___init__fails(self):  # Users should be told not to do this
    #                                  - No they should not; ScriptDB() is required internally. /Griatch
    #    with self.assertRaises(Exception):
    #        ScriptDB()

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


if __name__ == '__main__':
    unittest.main()
