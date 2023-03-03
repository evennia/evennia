from unittest import TestCase, mock

from parameterized import parameterized

from evennia import DefaultScript
from evennia.objects.objects import DefaultObject
from evennia.scripts.models import ObjectDoesNotExist, ScriptDB
from evennia.scripts.scripts import DoNothing, ExtendedLoopingCall
from evennia.utils.create import create_script
from evennia.utils.test_resources import BaseEvenniaTest
from evennia.scripts.tickerhandler import TickerHandler
from evennia.scripts.monitorhandler import MonitorHandler
import inspect
from evennia.scripts.manager import ScriptDBManager

class TestScript(BaseEvenniaTest):
    def test_create(self):
        "Check the script can be created via the convenience method."
        with mock.patch("evennia.scripts.scripts.DefaultScript.at_init") as mockinit:
            obj, errors = DefaultScript.create("useless-machine")
            self.assertTrue(obj, errors)
            self.assertFalse(errors, errors)
            mockinit.assert_called()

class Test_improve_coverage(TestCase):
    def test_store_key_raises_RunTimeError(self):
        with self.assertRaises(RuntimeError):
            th=TickerHandler()
            th._store_key(None, None, 0, None)

    def test_remove_raises_RunTimeError(self):
       with self.assertRaises(RuntimeError):
            th=TickerHandler()
            th.remove(callback=1)
            
    def test_not_obj_return_empty_list(self):
        manager_obj = ScriptDBManager()
        returned_list = manager_obj.get_all_scripts_on_obj(False)
        self.assertEqual(returned_list, [])

class ListIntervalsScript(DefaultScript):
    """
    A script that does nothing. Used to test listing of script with nonzero intervals.
    """
    def at_script_creation(self):
        """
        Setup the script
        """
        self.key = "interval_test"
        self.desc = "This is an empty placeholder script."
        self.interval = 1
        self.repeats = 1

class TestScriptHandler(BaseEvenniaTest):
    """
    Test the ScriptHandler class.

    """
    def setUp(self):
        self.obj, self.errors = DefaultObject.create("test_object")

    def tearDown(self):
        self.obj.delete()

    def test_start(self):
        "Check that ScriptHandler start function works correctly"
        self.obj.scripts.add(ListIntervalsScript)
        self.num = self.obj.scripts.start(self.obj.scripts.all()[0].key)
        self.assertTrue(self.num == 1)
    
    def test_list_script_intervals(self):
        "Checks that Scripthandler __str__ function lists script intervals correctly"
        self.obj.scripts.add(ListIntervalsScript)
        self.str = str(self.obj.scripts)
        self.assertTrue("None/1" in self.str)
        self.assertTrue("1 repeats" in self.str)

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
        
def dummy_func():
    return 0
class TestMonitorHandler(TestCase):
    def setUp(self):
        self.handler = MonitorHandler()
    
    def test_add(self):
        obj = mock.Mock()
        fieldname = "db_add"
        callback = dummy_func
        idstring = "test"
        self.assertEquals(inspect.isfunction(callback),True)

        self.handler.add(obj, fieldname, callback, idstring=idstring)

        self.assertIn(fieldname, self.handler.monitors[obj])
        self.assertIn(idstring, self.handler.monitors[obj][fieldname])
        self.assertEqual(self.handler.monitors[obj][fieldname][idstring], (callback, False, {}))

    def test_remove(self):
        obj = mock.Mock()
        fieldname = 'db_remove'
        callback = dummy_func
        idstring = 'test_remove'

        self.handler.add(obj,fieldname,callback,idstring=idstring)
        self.assertIn(fieldname,self.handler.monitors[obj])
        self.assertEqual(self.handler.monitors[obj][fieldname][idstring], (callback, False, {}))

        self.handler.remove(obj,fieldname,idstring=idstring)
        self.assertEquals(self.handler.monitors[obj][fieldname], {})

    def test_add_with_invalid_callback_does_not_work(self):
        obj = mock.Mock()
        fieldname = "db_key"
        callback = "not_a_function"
        
        self.handler.add(obj, fieldname, callback)
        self.assertNotIn(fieldname, self.handler.monitors[obj])

       




