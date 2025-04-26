"""
Unit tests for the scripts package

"""

from collections import defaultdict
from unittest import TestCase, mock

from parameterized import parameterized

from evennia import DefaultScript
from evennia.objects.objects import DefaultObject
from evennia.scripts.manager import ScriptDBManager
from evennia.scripts.models import ObjectDoesNotExist, ScriptDB
from evennia.scripts.monitorhandler import MonitorHandler
from evennia.scripts.ondemandhandler import OnDemandHandler, OnDemandTask
from evennia.scripts.scripts import DoNothing, ExtendedLoopingCall
from evennia.scripts.tickerhandler import TickerHandler
from evennia.utils.create import create_script
from evennia.utils.dbserialize import dbserialize
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaTest


class TestScript(BaseEvenniaTest):
    def test_create(self):
        "Check the script can be created via the convenience method."
        with mock.patch("evennia.scripts.scripts.DefaultScript.at_init") as mockinit:
            obj, errors = DefaultScript.create("useless-machine")
            self.assertTrue(obj, errors)
            self.assertFalse(errors, errors)
            mockinit.assert_called()


class TestTickerHandler(TestCase):
    """Test the TickerHandler class"""

    def test_store_key_raises_RunTimeError(self):
        """Test _store_key method raises RuntimeError for interval < 1"""
        with self.assertRaises(RuntimeError):
            th = TickerHandler()
            th._store_key(None, None, 0, None)

    def test_remove_raises_RunTimeError(self):
        """Test remove method raises RuntimeError for catching old ordering of arguments"""
        with self.assertRaises(RuntimeError):
            th = TickerHandler()
            th.remove(callback=1)

    def test_removing_ticker_using_store_key_in_attribute(self):
        """
        Test adding a ticker, storing the store_key in an attribute, and then removing it
        using that same store_key.

        https://github.com/evennia/evennia/pull/3765
        """
        obj = DefaultObject.create("test_object")[0]
        th = TickerHandler()
        obj.db.ticker = th.add(60, obj.msg, idstring="ticker_test", persistent=True)
        self.assertTrue(len(th.all()), 1)
        th.remove(store_key=obj.db.ticker)
        self.assertTrue(len(th.all()), 0)


class TestScriptDBManager(TestCase):
    """Test the ScriptDBManger class"""

    def test_not_obj_return_empty_list(self):
        """Test get_all_scripts_on_obj returns empty list for falsy object"""
        manager_obj = ScriptDBManager()
        returned_list = manager_obj.get_all_scripts_on_obj(False)
        self.assertEqual(returned_list, [])


class TestingListIntervalScript(DefaultScript):
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
        self.obj.scripts.add(TestingListIntervalScript)

    def tearDown(self):
        self.obj.delete()

    def test_start(self):
        "Check that ScriptHandler start function works correctly"
        self.num = self.obj.scripts.start(self.obj.scripts.all()[0].key)
        self.assertEqual(self.num, 1)

    def test_list_script_intervals(self):
        "Checks that Scripthandler __str__ function lists script intervals correctly"
        self.str = str(self.obj.scripts)
        self.assertTrue("None/1" in self.str)
        self.assertTrue("1 repeats" in self.str)

    def test_get_all_scripts(self):
        "Checks that Scripthandler get_all returns correct number of scripts"
        self.assertEqual([script.key for script in self.obj.scripts.all()], ["interval_test"])

    def test_get_script(self):
        "Checks that Scripthandler get function returns correct script"
        script = self.obj.scripts.get("interval_test")
        self.assertTrue(bool(script))

    def test_add_already_existing_script(self):
        "Checks that Scripthandler add function adds script correctly"

        # make a new script with no obj connection
        script = create_script(TestingListIntervalScript, key="interval_test2")
        self.obj.scripts.add(script)
        self.assertEqual([script], list(self.obj.scripts.get("interval_test2")))
        self.assertTrue(bool(self.obj.scripts.get("interval_test")))


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

    def test_start_invalid_interval(self):
        """Test the .start method with interval less than zero"""
        with self.assertRaises(ValueError):
            callback = mock.MagicMock()
            loopcall = ExtendedLoopingCall(callback)
            loopcall.start(-1, now=True, start_delay=None, count_start=1)

    def test__call__when_delay(self):
        """Test __call__ modifies start_delay and starttime if start_delay was previously set"""
        callback = mock.MagicMock()
        loopcall = ExtendedLoopingCall(callback)
        loopcall.clock.seconds = mock.MagicMock(return_value=1)
        loopcall.start_delay = 2
        loopcall.starttime = 0

        loopcall()

        self.assertEqual(loopcall.start_delay, None)
        self.assertEqual(loopcall.starttime, 1)

    def test_force_repeat(self):
        """Test forcing script to run that is scheduled to run in the future"""
        callback = mock.MagicMock()
        loopcall = ExtendedLoopingCall(callback)
        loopcall.clock.seconds = mock.MagicMock(return_value=0)

        loopcall.start(20, now=False, start_delay=5, count_start=0)
        loopcall.force_repeat()
        loopcall.stop()

        callback.assert_called_once()


def dummy_func():
    """Dummy function used as callback parameter"""
    return 0


class TestMonitorHandler(TestCase):
    """
    Test the MonitorHandler class.
    """

    def setUp(self):
        self.handler = MonitorHandler()

    def test_add(self):
        """Tests that adding an object to the monitor handler works correctly"""
        obj = mock.Mock()
        fieldname = "db_add"
        callback = dummy_func
        idstring = "test"

        self.handler.add(obj, fieldname, callback, idstring=idstring)

        self.assertIn(fieldname, self.handler.monitors[obj])
        self.assertIn(idstring, self.handler.monitors[obj][fieldname])
        self.assertEqual(self.handler.monitors[obj][fieldname][idstring], (callback, False, {}))

    def test_remove(self):
        """Tests that removing an object from the monitor handler works correctly"""
        obj = mock.Mock()
        fieldname = "db_remove"
        callback = dummy_func
        idstring = "test_remove"

        """Add an object to the monitor handler and then remove it"""
        self.handler.add(obj, fieldname, callback, idstring=idstring)
        self.handler.remove(obj, fieldname, idstring=idstring)
        self.assertEqual(self.handler.monitors[obj][fieldname], {})

    def test_add_with_invalid_function(self):
        obj = mock.Mock()
        """Tests that add method rejects objects where callback is not a function"""
        fieldname = "db_key"
        callback = "not_a_function"

        self.handler.add(obj, fieldname, callback)
        self.assertNotIn(fieldname, self.handler.monitors[obj])

    def test_all(self):
        """Tests that all method correctly returns information about added objects"""
        obj = [mock.Mock(), mock.Mock()]
        fieldname = ["db_all1", "db_all2"]
        callback = dummy_func
        idstring = ["test_all1", "test_all2"]

        self.handler.add(obj[0], fieldname[0], callback, idstring=idstring[0])
        self.handler.add(obj[1], fieldname[1], callback, idstring=idstring[1], persistent=True)

        output = self.handler.all()
        self.assertEqual(
            output,
            [
                (obj[0], fieldname[0], idstring[0], False, {}),
                (obj[1], fieldname[1], idstring[1], True, {}),
            ],
        )

    def test_clear(self):
        """Tests that the clear function correctly clears the monitor handler"""
        obj = mock.Mock()
        fieldname = "db_add"
        callback = dummy_func
        idstring = "test"

        self.handler.add(obj, fieldname, callback, idstring=idstring)
        self.assertIn(obj, self.handler.monitors)

        self.handler.clear()
        self.assertNotIn(obj, self.handler.monitors)
        self.assertEqual(defaultdict(lambda: defaultdict(dict)), self.handler.monitors)

    def test_add_remove_attribute(self):
        """Tests that adding and removing an object attribute to the monitor handler works correctly"""
        obj = mock.Mock()
        obj.name = "testaddattribute"
        fieldname = "name"
        callback = dummy_func
        idstring = "test"
        category = "testattribute"

        """Add attribute to handler and assert that it has been added"""
        self.handler.add(obj, fieldname, callback, idstring=idstring, category=category)

        index = obj.attributes.get(fieldname, return_obj=True)
        name = "db_value[testattribute]"

        self.assertIn(name, self.handler.monitors[index])
        self.assertIn(idstring, self.handler.monitors[index][name])
        self.assertEqual(self.handler.monitors[index][name][idstring], (callback, False, {}))

        """Remove attribute from the handler and assert that it is gone"""
        self.handler.remove(obj, fieldname, idstring=idstring, category=category)
        self.assertEqual(self.handler.monitors[index][name], {})


class TestOnDemandTask(EvenniaTest):
    """
    Test the OnDemandTask class.

    """

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_no_stages__no_autostart(self, mock_runtime):
        mock_runtime.return_value = 1000
        task = OnDemandTask("rose", "flower", autostart=False)

        self.assertEqual(task.key, "rose")
        self.assertEqual(task.category, "flower")
        self.assertEqual(task.start_time, None)

        self.assertEqual(str(task), "OnDemandTask(rose[flower] (dt=0s), stage=None)")
        self.assertEqual(task.get_dt(), 0)
        self.assertEqual(task.start_time, 1000)

        mock_runtime.return_value = 3000

        self.assertEqual(task.get_dt(), 2000)
        self.assertEqual(task.get_stage(), None)
        self.assertEqual(task.start_time, 1000)

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_stages_autostart(self, mock_runtime):
        START_TIME = 1000
        mock_runtime.return_value = START_TIME
        task = OnDemandTask(
            "rose",
            "flower",
            stages={0: "seedling", 100: "bud", 200: "flower", 300: "wilted", 400: "dead"},
        )
        self.assertEqual(task.start_time, 1000)
        self.assertEqual(
            task.stages,
            {
                0: ("seedling", None),
                100: ("bud", None),
                200: ("flower", None),
                300: ("wilted", None),
                400: ("dead", None),
            },
        )

        # step through the stages
        self.assertEqual(task.get_dt(), 0)

        self.assertEqual(task.get_stage(), "seedling")

        mock_runtime.return_value = START_TIME + 20
        self.assertEqual(task.get_stage(), "seedling")

        mock_runtime.return_value = START_TIME + 99.99
        self.assertEqual(task.get_stage(), "seedling")

        mock_runtime.return_value = START_TIME + 100
        self.assertEqual(task.get_stage(), "bud")

        mock_runtime.return_value = START_TIME + 250.14
        self.assertEqual(task.get_stage(), "flower")

        mock_runtime.return_value = START_TIME + 300
        self.assertEqual(task.get_stage(), "wilted")

        mock_runtime.return_value = START_TIME + 400.0
        self.assertEqual(task.get_stage(), "dead")

        mock_runtime.return_value = START_TIME + 10000
        self.assertEqual(task.get_stage(), "dead")

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_stagefuncs(self, mock_runtime):
        START_TIME = 0
        mock_runtime.return_value = START_TIME

        def statefunc(task):
            task.start_time = 2000

        task = OnDemandTask(
            "rose",
            "flower",
            stages={
                0: "seedling",
                100: "bud",
                200: "flower",
                300: "wilted",
                400: ("dead", statefunc),
            },
        )

        self.assertEqual(task.get_stage(), "seedling")
        mock_runtime.return_value = START_TIME + 400
        self.assertEqual(task.get_stage(), "dead")
        self.assertEqual(task.start_time, 2000)

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_stagefunc_loop(self, mock_runtime):
        START_TIME = 0
        mock_runtime.return_value = START_TIME

        task = OnDemandTask(
            "rose",
            "flower",
            stages={
                0: "seedling",
                50: "bud",
                150: "flower",
                300: "wilted",
                400: "dead",
                500: ("_loop", OnDemandTask.stagefunc_loop),
            },
        )

        self.assertAlmostEqual(task.get_dt(), 0)
        self.assertEqual(task.get_stage(), "seedling")

        mock_runtime.return_value = START_TIME + 500
        self.assertEqual(task.get_dt(), 0)
        self.assertEqual(task.get_stage(), "seedling")

        mock_runtime.return_value = START_TIME + 600
        self.assertEqual(task.get_dt(), 100)
        self.assertEqual(task.iterations, 1)
        self.assertEqual(task.get_stage(), "bud")

        # wait a long time, should loop back indefinitely, counting iterations
        mock_runtime.return_value = START_TIME + 10250
        self.assertEqual(task.get_dt(), 250)
        self.assertEqual(task.iterations, 20)
        self.assertEqual(task.get_stage(), "flower")

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_stagefunc_bounce(self, mock_runtime):
        START_TIME = 0
        mock_runtime.return_value = START_TIME

        task = OnDemandTask(
            "reactor",
            "nuclear",
            stages={
                0: ("cold", OnDemandTask.stagefunc_bounce),
                50: "lukewarm",
                150: "warm",
                300: "hot",
                400: ("HOT!", OnDemandTask.stagefunc_bounce),
            },
        )

        self.assertAlmostEqual(task.get_dt(), 0)
        self.assertEqual(task.get_stage(), "cold")

        mock_runtime.return_value = START_TIME + 400
        self.assertEqual(task.get_dt(), 0)
        self.assertEqual(task.get_stage(), "HOT!")
        self.assertEqual(task.iterations, 1)

        # we should be going back down the sequence
        mock_runtime.return_value = START_TIME + 450
        self.assertEqual(task.get_dt(), 50)
        self.assertEqual(task.get_stage(), "HOT!")

        mock_runtime.return_value = START_TIME + 500
        self.assertEqual(task.get_dt(), 100)
        self.assertEqual(task.get_stage(), "hot")

        mock_runtime.return_value = START_TIME + 650
        self.assertEqual(task.get_dt(), 250)
        self.assertEqual(task.get_stage(), "warm")

        mock_runtime.return_value = START_TIME + 750
        self.assertEqual(task.get_dt(), 350)
        self.assertEqual(task.get_stage(), "lukewarm")

        mock_runtime.return_value = START_TIME + 800
        self.assertEqual(task.get_dt(), 0)
        self.assertEqual(task.iterations, 2)
        self.assertEqual(task.get_stage(), "cold")

        # back up again
        mock_runtime.return_value = START_TIME + 950
        self.assertEqual(task.get_dt(), 150)
        self.assertEqual(task.iterations, 2)
        self.assertEqual(task.get_stage(), "warm")

        # Waiting a long time
        mock_runtime.return_value = START_TIME + 10250
        self.assertEqual(task.get_dt(), 250)
        self.assertEqual(task.iterations, 25)
        self.assertEqual(task.get_stage(), "warm")


class TestOnDemandHandler(EvenniaTest):
    """
    Test the OnDemandHandler class.

    """

    def setUp(self):
        super(TestOnDemandHandler, self).setUp()
        self.handler = OnDemandHandler()
        self.task1 = OnDemandTask(
            "rose",
            "flower",
            stages={0: "seedling", 100: "bud", 200: "flower", 300: "wilted", 400: "dead"},
        )
        self.task2 = OnDemandTask(
            "daffodil",
            "flower",
            stages={0: "seedling", 50: "bud", 100: "flower", 150: "wilted", 200: "dead"},
        )
        self.task3 = OnDemandTask("test", None)

    def test_add_get(self):
        self.handler.add("rose", category="flower", stages={0: "seedling"})
        task = self.handler.get("rose", "flower")
        self.assertEqual(
            (task.key, task.category, task.stages), ("rose", "flower", {0: ("seedling", None)})
        )
        self.assertEqual(self.handler.get("rose"), None)  # no category

    def test_batch_add(self):
        self.handler.batch_add(self.task1, self.task2, self.task3)
        task1 = self.handler.get("rose", "flower")
        task2 = self.handler.get("daffodil", "flower")
        task3 = self.handler.get("test")
        self.assertEqual((task1.key, task1.category), ("rose", "flower"))
        self.assertEqual((task2.key, task2.category), ("daffodil", "flower"))
        self.assertEqual((task3.key, task3.category), ("test", None))

    def test_remove(self):
        self.handler.add(self.task1)
        self.handler.add(self.task2)
        self.handler.remove(self.task1)
        self.assertEqual(self.handler.get("rose", "flower"), None)
        self.assertEqual(self.handler.get("daffodil", "flower"), self.task2)

    def test_batch_remove(self):
        self.handler.batch_add(self.task1, self.task2, self.task3)
        self.handler.batch_remove(self.task1, self.task2)
        self.assertEqual(self.handler.get("rose", "flower"), None)
        self.assertEqual(self.handler.get("daffodil", "flower"), None)
        self.assertEqual(self.handler.get("test"), self.task3)

    def test_all(self):
        self.handler.batch_add(self.task1, self.task2, self.task3)
        self.assertEqual(
            self.handler.all(),
            {
                (self.task1.key, self.task1.category): self.task1,
                (self.task2.key, self.task2.category): self.task2,
                (self.task3.key, self.task3.category): self.task3,
            },
        )

    def test_clear(self):
        self.handler.batch_add(self.task1, self.task2, self.task3)
        self.handler.clear(all_on_none=False)  # only task3 gone (None
        self.assertEqual(
            self.handler.all(),
            {
                (self.task1.key, self.task1.category): self.task1,
                (self.task2.key, self.task2.category): self.task2,
            },
        )
        self.handler.clear()  # all gone
        self.assertEqual(self.handler.all(), {})

    def test_save_and_load(self):
        self.handler.add(self.task1)
        self.handler.add(self.task2)
        self.handler.save()
        self.handler.load()
        task1 = self.handler.get("rose", "flower")
        task2 = self.handler.get(self.task2)
        self.assertEqual((task1.key, task1.category), ("rose", "flower"))
        self.assertEqual((task2.key, task2.category), ("daffodil", "flower"))

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_get_dt_and_stage(self, mock_runtime):
        START_TIME = 0

        mock_runtime.return_value = START_TIME
        self.handler.batch_add(self.task1, self.task2)

        for task in self.handler.tasks.values():
            task.start_time = START_TIME

        self.assertEqual(self.handler.get_dt("rose", "flower"), 0)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 0)

        mock_runtime.return_value = START_TIME + 50
        self.assertEqual(self.handler.get_dt("rose", "flower"), 50)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 50)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "seedling")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "bud")

        mock_runtime.return_value = START_TIME + 150
        self.assertEqual(self.handler.get_dt("rose", "flower"), 150)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 150)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "bud")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "wilted")

        mock_runtime.return_value = START_TIME + 250
        self.assertEqual(self.handler.get_dt("rose", "flower"), 250)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 250)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "flower")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "dead")

        mock_runtime.return_value = START_TIME + 10000
        self.assertEqual(self.handler.get_dt("rose", "flower"), 10000)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 10000)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "dead")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "dead")

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_set_dt(self, mock_runtime):
        START_TIME = 0

        mock_runtime.return_value = START_TIME
        self.handler.batch_add(self.task1, self.task2)

        for task in self.handler.tasks.values():
            task.start_time = START_TIME

        self.assertEqual(self.handler.get_stage("rose", "flower"), "seedling")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "seedling")

        self.handler.set_dt("rose", "flower", 100)
        self.handler.set_dt("daffodil", "flower", 150)
        self.assertEqual(
            [task.start_time for task in self.handler.tasks.values()],
            [START_TIME - 100, START_TIME - 150],
        )
        self.assertEqual(self.handler.get_dt("rose", "flower"), 100)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 150)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "bud")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "wilted")

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_set_stage(self, mock_runtime):
        START_TIME = 0

        mock_runtime.return_value = START_TIME
        self.handler.batch_add(self.task1, self.task2)

        for task in self.handler.tasks.values():
            task.start_time = START_TIME

        self.assertEqual(self.handler.get_stage("rose", "flower"), "seedling")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "seedling")

        self.handler.set_stage("rose", "flower", "bud")
        self.handler.set_stage("daffodil", "flower", "wilted")
        self.assertEqual(
            [task.start_time for task in self.handler.tasks.values()],
            [START_TIME - 100, START_TIME - 150],
        )
        self.assertEqual(self.handler.get_dt("rose", "flower"), 100)
        self.assertEqual(self.handler.get_dt("daffodil", "flower"), 150)
        self.assertEqual(self.handler.get_stage("rose", "flower"), "bud")
        self.assertEqual(self.handler.get_stage("daffodil", "flower"), "wilted")

    @staticmethod
    def _do_decay(task, **kwargs):
        task.stored_kwargs = kwargs

    def test_handler_save(self):
        """
        Testing the save method of the OnDemandHandler class for reported pickling issue

        """

        self.handler.add(
            key="foo",
            category="decay",
            stages={
                0: "new",
                10: ("old", self._do_decay),
            },
        )
        self.handler.save()
        self.handler.clear()
        self.handler.save()

    @mock.patch("evennia.scripts.ondemandhandler.OnDemandTask.runtime")
    def test_call_staging_function_with_kwargs(self, mock_runtime):
        """ """

        mock_runtime.return_value = 0

        self.handler.add(
            key="foo",
            category="decay",
            stages={
                0: "new",
                10: ("old", self._do_decay),
            },
        )
        self.handler.set_dt("foo", "decay", 10)

        self.handler.get_stage("foo", "decay", foo="bar", bar="foo")

        self.assertEqual(
            self.handler.get("foo", "decay").stored_kwargs, {"foo": "bar", "bar": "foo"}
        )
