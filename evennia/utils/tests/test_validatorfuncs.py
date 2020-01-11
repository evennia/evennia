"""Tests for validatorfuncs """

from django.test import TestCase
from evennia.utils import validatorfuncs
import mock
import datetime
import pytz


class TestValidatorFuncs(TestCase):
    def test_text_ok(self):
        for val in [None, -123, "abc", 1.234, {1: True, 2: False}, ["a", 1]]:
            self.assertEqual(str(val), validatorfuncs.text(val))

    @mock.patch("builtins.str")
    def test_text_raises_ValueError(self, mocked_str):
        mocked_str.side_effect = Exception
        with self.assertRaises(ValueError):
            validatorfuncs.text(None)

    def test_color_ok(self):
        for color in ["r", "g", "b", "H", "R", "M", "^"]:
            self.assertEqual(color, validatorfuncs.color(color))

    def test_color_falsy_raises_ValueError(self):
        for color in [None, (), [], False, True, {}]:
            with self.assertRaises(ValueError):
                validatorfuncs.color(color)

    def test_datetime_ok(self):
        for dt in ["Oct 12 1:00 1492", "Jan 2 12:00 2020", "Dec 31 00:00 2018"]:
            self.assertTrue(
                isinstance(validatorfuncs.datetime(dt, from_tz=pytz.UTC), datetime.datetime)
            )

    def test_datetime_raises_ValueError(self):
        for dt in ["", "January 1, 2019", "1/1/2019", "Jan 1 2019"]:
            with self.assertRaises(ValueError):
                validatorfuncs.datetime(dt)

    def test_duration_ok(self):
        for d in ["1d", "2w", "3h", "4s", "5m", "6y"]:
            self.assertTrue(isinstance(validatorfuncs.duration(d), datetime.timedelta))

        self.assertEqual(
            datetime.timedelta(1 + 6 * 365, 2, 0, 0, 3, 4, 5),
            validatorfuncs.duration("1d 2s 3m 4h 5w 6y"),
        )
        # values may be duplicated
        self.assertEqual(
            datetime.timedelta((1 + 7) + (6 + 12) * 365, 2 + 8, 0, 0, 3 + 9, 4 + 10, 5 + 11),
            validatorfuncs.duration("1d 2s 3m 4h 5w 6y 7d 8s 9m 10h 11w 12y"),
        )

    def test_duration_raises_ValueError(self):
        for d in ["", "1", "5days", "1Week"]:
            with self.assertRaises(ValueError):
                validatorfuncs.duration(d)

    def test_future_ok(self):
        year = int(datetime.datetime.utcnow().strftime("%Y"))
        for f in [f"Jan 2 12:00 {year+1}", f"Dec 31 00:00 {year+1}"]:
            self.assertTrue(
                isinstance(validatorfuncs.future(f, from_tz=pytz.UTC), datetime.datetime)
            )

    def test_future_raises_ValueError(self):
        year = int(datetime.datetime.utcnow().strftime("%Y"))
        for f in [f"Jan 2 12:00 {year-1}", f"Dec 31 00:00 {year-1}"]:
            with self.assertRaises(ValueError):
                validatorfuncs.future(f, from_tz=pytz.UTC)

    def test_signed_integer_ok(self):
        for si in ["123", "4567890", "001", "-123", "-45", "0"]:
            self.assertEqual(int(si), validatorfuncs.signed_integer(si))

    @mock.patch("builtins.int")
    def test_signed_integer_raises_ValueError(self, mocked_int):
        for si in ["", "000", "abc"]:
            mocked_int.side_effect = ValueError
            with self.assertRaises(ValueError):
                validatorfuncs.signed_integer(si)

    def test_positive_integer_ok(self):
        for pi in ["123", "4567890", "001"]:
            self.assertEqual(int(pi), validatorfuncs.positive_integer(pi))

    @mock.patch("builtins.int")
    def test_positive_integer_raises_ValueError(self, mocked_int):
        mocked_int.return_value = -1
        with self.assertRaises(ValueError):
            validatorfuncs.positive_integer(str(-1))
        for pi in ["", "000", "abc", "-1"]:
            mocked_int.side_effect = ValueError
            with self.assertRaises(ValueError):
                validatorfuncs.positive_integer(pi)

    def test_unsigned_integer_ok(self):
        for ui in ["123", "4567890", "001", "0"]:
            self.assertEqual(int(ui), validatorfuncs.unsigned_integer(ui))

    @mock.patch("builtins.int")
    def test_unsigned_integer_raises_ValueError(self, mocked_int):
        mocked_int.return_value = -1
        with self.assertRaises(ValueError):
            validatorfuncs.unsigned_integer(str(-1))
        for ui in ["", "000", "abc", "-1", "0"]:
            mocked_int.side_effect = ValueError
            with self.assertRaises(ValueError):
                validatorfuncs.unsigned_integer(ui)

    def test_boolean(self):
        for b in ["true", "1", "on", "ENABLED"]:
            self.assertTrue(validatorfuncs.boolean(b))
        for b in ["FalSe", "0", "oFF", "disabled"]:
            self.assertFalse(validatorfuncs.boolean(b))

    def test_boolean_raises_ValueError(self):
        for b in ["", None, 1, 0, True, False, [None], {True: True}]:
            with self.assertRaises(ValueError):
                validatorfuncs.boolean(b)

    def test_timezone_ok(self):
        for tz in ["America/Chicago", "GMT", "UTC"]:
            self.assertEqual(tz, validatorfuncs.timezone(tz).zone)

    def test_timezone_raises_ValueError(self):
        for tz in ["America", None, "", "Mars", "DT"]:
            with self.assertRaises(ValueError):
                validatorfuncs.timezone(tz)

    def test_email_ok(self):
        for e in ["a@a.aa", "zeus@olympus.net"]:
            self.assertEqual(e, validatorfuncs.email(e))

    def test_email_raises_ValueError(self):
        for e in ["", None, ["abc@abc.com"], 123]:
            with self.assertRaises(ValueError):
                validatorfuncs.email(e)

    def test_lock_ok(self):
        for l in ["do:true;look:no", "a:t"]:
            self.assertEqual(l, validatorfuncs.lock(l))

    def test_lock_raises_ValueError(self):
        for l in [";;;", "", ":", ":::", ";:;:", "x:", ":y"]:
            with self.assertRaises(ValueError):
                validatorfuncs.lock(l)
        with self.assertRaises(ValueError):
            validatorfuncs.lock("view:", access_options=())
        with self.assertRaises(ValueError):
            validatorfuncs.lock("view:", access_options=("look"))
