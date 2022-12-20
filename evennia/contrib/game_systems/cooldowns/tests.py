"""
Cooldowns tests.

"""

from mock import patch

from evennia.utils.test_resources import BaseEvenniaTest

from . import cooldowns


@patch("evennia.contrib.game_systems.cooldowns.cooldowns.time.time", return_value=0.0)
class TestCooldowns(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.handler = cooldowns.CooldownHandler(self.char1)

    def test_empty(self, mock_time):
        self.assertEqual(self.handler.all, [])
        self.assertTrue(self.handler.ready("a", "b", "c"))
        self.assertEqual(self.handler.time_left("a", "b", "c"), 0)

    def test_add(self, mock_time):
        self.assertEqual(self.handler.add, self.handler.set)
        self.handler.add("a", 10)
        self.assertFalse(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 10)
        mock_time.return_value = 9.0
        self.assertFalse(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 1)
        mock_time.return_value = 10.0
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)

    def test_add_float(self, mock_time):
        self.assertEqual(self.handler.time_left("a"), 0)
        self.assertEqual(self.handler.time_left("a", use_int=False), 0)
        self.assertEqual(self.handler.time_left("a", use_int=True), 0)
        self.handler.add("a", 5.5)
        self.assertEqual(self.handler.time_left("a"), 5.5)
        self.assertEqual(self.handler.time_left("a", use_int=False), 5.5)
        self.assertEqual(self.handler.time_left("a", use_int=True), 6)

    def test_add_multi(self, mock_time):
        self.handler.add("a", 10)
        self.handler.add("b", 5)
        self.handler.add("c", 3)
        self.assertFalse(self.handler.ready("a", "b", "c"))
        self.assertEqual(self.handler.time_left("a", "b", "c"), 10)
        self.assertEqual(self.handler.time_left("a", "b"), 10)
        self.assertEqual(self.handler.time_left("a", "c"), 10)
        self.assertEqual(self.handler.time_left("b", "c"), 5)
        self.assertEqual(self.handler.time_left("c", "c"), 3)

    def test_add_none(self, mock_time):
        self.handler.add("a", None)
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)

    def test_add_negative(self, mock_time):
        self.handler.add("a", -5)
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)

    def test_add_overwrite(self, mock_time):
        self.handler.add("a", 5)
        self.handler.add("a", 10)
        self.handler.add("a", 3)
        self.assertFalse(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 3)

    def test_extend(self, mock_time):
        self.assertEqual(self.handler.extend("a", 10), 10)
        self.assertFalse(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 10)
        self.assertEqual(self.handler.extend("a", 10), 20)
        self.assertFalse(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 20)

    def test_extend_none(self, mock_time):
        self.assertEqual(self.handler.extend("a", None), 0)
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)
        self.handler.add("a", 10)
        self.assertEqual(self.handler.extend("a", None), 10)
        self.assertEqual(self.handler.time_left("a"), 10)

    def test_extend_negative(self, mock_time):
        self.assertEqual(self.handler.extend("a", -5), 0)
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)
        self.handler.add("a", 10)
        self.assertEqual(self.handler.extend("a", -5), 5)
        self.assertEqual(self.handler.time_left("a"), 5)

    def test_extend_float(self, mock_time):
        self.assertEqual(self.handler.extend("a", -5.5), 0)
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0.0)
        self.assertEqual(self.handler.time_left("a", use_int=False), 0.0)
        self.assertEqual(self.handler.time_left("a", use_int=True), 0)
        self.handler.add("a", 10.5)
        self.assertEqual(self.handler.extend("a", -5.25), 5.25)
        self.assertEqual(self.handler.time_left("a"), 5.25)
        self.assertEqual(self.handler.time_left("a", use_int=False), 5.25)
        self.assertEqual(self.handler.time_left("a", use_int=True), 6)

    def test_reset_non_existent(self, mock_time):
        self.handler.reset("a")
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)

    def test_reset(self, mock_time):
        self.handler.set("a", 10)
        self.handler.reset("a")
        self.assertTrue(self.handler.ready("a"))
        self.assertEqual(self.handler.time_left("a"), 0)

    def test_clear(self, mock_time):
        self.handler.add("a", 10)
        self.handler.add("b", 10)
        self.handler.add("c", 10)
        self.handler.clear()
        self.assertTrue(self.handler.ready("a", "b", "c"))
        self.assertEqual(self.handler.time_left("a", "b", "c"), 0)

    def test_cleanup(self, mock_time):
        self.handler.add("a", 10)
        self.handler.add("b", 5)
        self.handler.add("c", 5)
        self.handler.add("d", 3.5)
        mock_time.return_value = 6.0
        self.handler.cleanup()
        self.assertEqual(self.handler.time_left("b", "c", "d"), 0)
        self.assertEqual(self.handler.time_left("a"), 4)
        self.assertEqual(list(self.handler.data.keys()), ["a"])

    def test_cleanup_doesnt_delete_anything(self, mock_time):
        self.handler.add("a", 10)
        self.handler.add("b", 5)
        self.handler.add("c", 5)
        self.handler.add("d", 3.5)
        mock_time.return_value = 1.0
        self.handler.cleanup()
        self.assertEqual(self.handler.time_left("d"), 2.5)
        self.assertEqual(self.handler.time_left("b", "c"), 4)
        self.assertEqual(self.handler.time_left("a"), 9)
        self.assertEqual(list(self.handler.data.keys()), ["a", "b", "c", "d"])
