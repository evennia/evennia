"""
Unit tests for the utilities of the evennia.utils.gametime module.
"""

import time
import unittest
from unittest.mock import Mock

from django.conf import settings
from django.test import TestCase

from evennia.utils import gametime


class TestGametime(TestCase):
    def setUp(self) -> None:
        self.time = time.time
        self._SERVER_EPOCH = gametime._SERVER_EPOCH
        time.time = Mock(return_value=1555595378.0)
        gametime._SERVER_EPOCH = None
        gametime.SERVER_RUNTIME = 600.0
        gametime.SERVER_START_TIME = time.time() - 300
        gametime.SERVER_RUNTIME_LAST_UPDATED = time.time() - 30
        gametime.TIMEFACTOR = 5.0
        self.timescripts = []

    def tearDown(self) -> None:
        time.time = self.time
        gametime._SERVER_EPOCH = self._SERVER_EPOCH
        gametime.SERVER_RUNTIME_LAST_UPDATED = 0.0
        gametime.SERVER_RUNTIME = 0.0
        gametime.SERVER_START_TIME = 0.0
        gametime.TIMEFACTOR = settings.TIME_FACTOR
        for script in self.timescripts:
            script.stop()

    def test_runtime(self):
        self.assertAlmostEqual(gametime.runtime(), 630.0)

    def test_server_epoch(self):
        self.assertAlmostEqual(gametime.server_epoch(), time.time() - 630.0)

    def test_uptime(self):
        self.assertAlmostEqual(gametime.uptime(), 300.0)

    def test_game_epoch_no_setting(self):
        self.assertAlmostEqual(gametime.game_epoch(), gametime.server_epoch())

    def test_game_epoch_setting(self):
        with self.settings(TIME_GAME_EPOCH=0):
            self.assertEqual(gametime.game_epoch(), 0)

    def test_gametime_simple(self):
        self.assertAlmostEqual(gametime.gametime(), 630.0 * 5)

    def test_gametime_absolute(self):
        self.assertAlmostEqual(gametime.gametime(absolute=True), 1555597898.0)

    def test_gametime_downtimes(self):
        gametime.IGNORE_DOWNTIMES = True
        self.assertAlmostEqual(gametime.gametime(), 630 * 5.0)
        gametime.IGNORE_DOWNTIMES = False

    def test_real_seconds_until(self):
        # using the gametime value above, we are working from the following
        # datetime: datetime.datetime(2019, 4, 18, 14, 31, 38, 245449)
        self.assertAlmostEqual(gametime.real_seconds_until(sec=48), 2)
        self.assertAlmostEqual(gametime.real_seconds_until(min=32), 12)
        self.assertAlmostEqual(gametime.real_seconds_until(hour=15), 720)
        self.assertAlmostEqual(gametime.real_seconds_until(day=19), 17280)
        self.assertAlmostEqual(gametime.real_seconds_until(month=5), 518400)
        self.assertAlmostEqual(gametime.real_seconds_until(year=2020), 6324480)

    def test_real_seconds_until_behind(self):
        self.assertAlmostEqual(gametime.real_seconds_until(sec=28), 10)
        self.assertAlmostEqual(gametime.real_seconds_until(min=30), 708)
        self.assertAlmostEqual(gametime.real_seconds_until(hour=13), 16560)
        self.assertAlmostEqual(gametime.real_seconds_until(day=17), 501120)
        self.assertAlmostEqual(gametime.real_seconds_until(month=1), 4752000)

    def test_real_seconds_until_leap_year(self):
        self.assertAlmostEqual(gametime.real_seconds_until(month=3), 5788800)

    def test_schedule(self):
        callback = Mock()
        script = gametime.schedule(callback, day=19)
        self.timescripts.append(script)
        self.assertIsInstance(script, gametime.TimeScript)
        self.assertAlmostEqual(script.interval, 17280)
        self.assertEqual(script.repeats, 1)

    def test_repeat_schedule(self):
        callback = Mock()
        script = gametime.schedule(callback, repeat=True, min=32)
        self.timescripts.append(script)
        self.assertIsInstance(script, gametime.TimeScript)
        self.assertAlmostEqual(script.interval, 12)
        self.assertEqual(script.repeats, -1)
