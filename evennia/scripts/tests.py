from unittest import TestCase, mock

from parameterized import parameterized

from evennia import DefaultScript
from evennia.scripts.models import ObjectDoesNotExist, ScriptDB
from evennia.scripts.scripts import DoNothing, ExtendedLoopingCall
from evennia.utils.create import create_script
from evennia.utils.test_resources import BaseEvenniaTest


class TestScript(BaseEvenniaTest):
    def test_create(self):
        "Check the script can be created via the convenience method."
        with mock.patch("evennia.scripts.scripts.DefaultScript.at_init") as mockinit:
            obj, errors = DefaultScript.create("useless-machine")
            self.assertTrue(obj, errors)
            self.assertFalse(errors, errors)
            mockinit.assert_called()


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
        with self.assertRaises(ScriptDB.DoesNotExist):  # See issue #509
            self.scr.start()
        # Check the script is not recreated as a side-effect
        self.assertFalse(self.scr in ScriptDB.objects.get_all_scripts())


class TestExtendedLoopingCall(TestCase):
    """
    Test the ExtendedLoopingCall class.

    """

    @mock.patch("evennia.scripts.scripts.LoopingCall")
    def test_start__nodelay(self, MockClass):
        """Test the .start method with no delay"""

        callback = mock.MagicMock()
        loopcall = ExtendedLoopingCall(callback)
        loopcall.__call__ = mock.MagicMock()
        loopcall._scheduleFrom = mock.MagicMock()
        loopcall.clock.seconds = mock.MagicMock(return_value=0)

        loopcall.start(20, now=True, start_delay=None, count_start=1)
        loopcall._scheduleFrom.assert_not_called()

    @mock.patch("evennia.scripts.scripts.LoopingCall")
    def test_start__delay(self, MockLoopingCall):
        """Test the .start method with delay"""

        callback = mock.MagicMock()
        MockLoopingCall.clock.seconds = mock.MagicMock(return_value=0)

        loopcall = ExtendedLoopingCall(callback)
        loopcall.__call__ = mock.MagicMock()
        loopcall.clock.seconds = mock.MagicMock(return_value=121)
        loopcall._scheduleFrom = mock.MagicMock()

        loopcall.start(20, now=False, start_delay=10, count_start=1)

        loopcall.__call__.assert_not_called()
        self.assertEqual(loopcall.interval, 20)
        loopcall._scheduleFrom.assert_called_with(121)
