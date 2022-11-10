"""
Testing custom game time

"""

# Testing custom_gametime
from mock import Mock, patch

from evennia.utils.test_resources import BaseEvenniaTest

from .. import custom_gametime


def _testcallback():
    pass


@patch("evennia.utils.gametime.gametime", new=Mock(return_value=2975000898.46))
class TestCustomGameTime(BaseEvenniaTest):
    def tearDown(self):
        if hasattr(self, "timescript"):
            self.timescript.stop()

    def test_time_to_tuple(self):
        self.assertEqual(custom_gametime.time_to_tuple(10000, 34, 2, 4, 6, 1), (294, 2, 0, 0, 0, 0))
        self.assertEqual(custom_gametime.time_to_tuple(10000, 3, 3, 4), (3333, 0, 0, 1))
        self.assertEqual(custom_gametime.time_to_tuple(100000, 239, 24, 3), (418, 4, 0, 2))

    def test_gametime_to_realtime(self):
        self.assertEqual(custom_gametime.gametime_to_realtime(days=2, mins=4), 86520.0)
        self.assertEqual(
            custom_gametime.gametime_to_realtime(format=True, days=2), (0, 0, 0, 1, 0, 0, 0)
        )

    def test_realtime_to_gametime(self):
        self.assertEqual(custom_gametime.realtime_to_gametime(days=3, mins=34), 349680.0)
        self.assertEqual(
            custom_gametime.realtime_to_gametime(days=3, mins=34, format=True),
            (0, 0, 0, 4, 1, 8, 0),
        )
        self.assertEqual(
            custom_gametime.realtime_to_gametime(format=True, days=3, mins=4), (0, 0, 0, 4, 0, 8, 0)
        )

    def test_custom_gametime(self):
        self.assertEqual(custom_gametime.custom_gametime(), (102, 5, 2, 6, 21, 8, 18))
        self.assertEqual(custom_gametime.custom_gametime(absolute=True), (102, 5, 2, 6, 21, 8, 18))

    def test_real_seconds_until(self):
        self.assertEqual(
            custom_gametime.real_seconds_until(year=2300, month=12, day=7), 31911667199.77
        )

    def test_schedule(self):
        self.timescript = custom_gametime.schedule(_testcallback, repeat=True, min=5, sec=0)
        self.assertEqual(self.timescript.interval, 1700.7699999809265)
