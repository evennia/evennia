from anything import Something
from django.test import TestCase
from mock import Mock, mock_open, patch

from .dummyrunner_settings import (
    c_creates_button,
    c_creates_obj,
    c_digs,
    c_examines,
    c_help,
    c_idles,
    c_login,
    c_login_nodig,
    c_logout,
    c_looks,
    c_moves,
    c_moves_n,
    c_moves_s,
    c_socialize,
)

try:
    import memplot
except ImportError:
    memplot = Mock()


class TestDummyrunnerSettings(TestCase):
    def setUp(self):
        self.client = Mock()
        self.client.cid = 1
        self.client.counter = Mock(return_value=1)
        self.client.gid = "20171025161153-1"
        self.client.name = "Dummy_%s" % self.client.gid
        self.client.password = (Something,)
        self.client.start_room = "testing_room_start_%s" % self.client.gid
        self.client.objs = []
        self.client.exits = []

    def clear_client_lists(self):
        self.client.objs = []
        self.client.exits = []

    def test_c_login(self):
        self.assertEqual(
            c_login(self.client),
            (
                Something,  # create
                "yes",  # confirm creation
                Something,  # connect
                "dig %s" % self.client.start_room,
                "teleport %s" % self.client.start_room,
                "py from evennia.server.profiling.dummyrunner import DummyRunnerCmdSet;"
                "self.cmdset.add(DummyRunnerCmdSet, persistent=False)",
            ),
        )

    def test_c_login_no_dig(self):
        cmd1, cmd2 = c_login_nodig(self.client)
        self.assertTrue(cmd1.startswith("create " + self.client.name + " "))
        self.assertTrue(cmd2.startswith("connect " + self.client.name + " "))

    def test_c_logout(self):
        self.assertEqual(c_logout(self.client), ("quit",))

    def perception_method_tests(self, func, verb, alone_suffix=""):
        self.assertEqual(func(self.client), ("%s%s" % (verb, alone_suffix),))
        self.client.exits = ["exit1", "exit2"]
        self.assertEqual(func(self.client), ["%s exit1" % verb, "%s exit2" % verb])
        self.client.objs = ["foo", "bar"]
        self.assertEqual(func(self.client), ["%s foo" % verb, "%s bar" % verb])
        self.clear_client_lists()

    def test_c_looks(self):
        self.perception_method_tests(c_looks, "look")

    def test_c_examines(self):
        self.perception_method_tests(c_examines, "examine", " me")

    def test_idles(self):
        self.assertEqual(c_idles(self.client), ("idle", "idle"))

    def test_c_help(self):
        self.assertEqual(
            c_help(self.client),
            ("help", "dummyrunner_echo_response"),
        )

    def test_c_digs(self):
        self.assertEqual(c_digs(self.client), ("dig/tel testing_room_1 = exit_1, exit_1",))
        self.assertEqual(self.client.exits, ["exit_1", "exit_1"])
        self.clear_client_lists()

    def test_c_creates_obj(self):
        objname = "testing_obj_1"
        self.assertEqual(
            c_creates_obj(self.client),
            (
                "create %s" % objname,
                'desc %s = "this is a test object' % objname,
                "set %s/testattr = this is a test attribute value." % objname,
                "set %s/testattr2 = this is a second test attribute." % objname,
            ),
        )
        self.assertEqual(self.client.objs, [objname])
        self.clear_client_lists()

    def test_c_creates_button(self):
        objname = "testing_button_1"
        typeclass_name = "contrib.tutorial_examples.red_button.RedButton"
        self.assertEqual(
            c_creates_button(self.client),
            ("create %s:%s" % (objname, typeclass_name), "desc %s = test red button!" % objname),
        )
        self.assertEqual(self.client.objs, [objname])
        self.clear_client_lists()

    def test_c_socialize(self):
        self.assertEqual(
            c_socialize(self.client),
            (
                "pub Hello!",
                "say Yo!",
                "emote stands looking around.",
            ),
        )

    def test_c_moves(self):
        self.assertEqual(c_moves(self.client), ("look",))
        self.client.exits = ["south", "north"]
        self.assertEqual(c_moves(self.client), ["south", "north"])
        self.clear_client_lists()

    def test_c_move_n(self):
        self.assertEqual(c_moves_n(self.client), ("north",))

    def test_c_move_s(self):
        self.assertEqual(c_moves_s(self.client), ("south",))


class TestMemPlot(TestCase):
    @patch.object(memplot, "_idmapper")
    @patch.object(memplot, "os")
    @patch.object(memplot, "open", new_callable=mock_open, create=True)
    @patch.object(memplot, "time")
    @patch("evennia.utils.idmapper.models.SharedMemoryModel.flush_from_cache", new=Mock())
    def test_memplot(self, mock_time, mocked_open, mocked_os, mocked_idmapper):
        if isinstance(memplot, Mock):
            return
        from evennia.utils.create import create_script

        mocked_idmapper.cache_size.return_value = (9, 5000)
        mock_time.time = Mock(return_value=6000.0)
        script = create_script(memplot.Memplot)
        script.db.starttime = 0.0
        mocked_os.popen.read.return_value = 5000.0
        script.at_repeat()
        handle = mocked_open()
        handle.write.assert_called_with("100.0, 0.001, 0.001, 9\n")
        script.stop()
