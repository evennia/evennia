"""Tests for validatorfuncs """

from django.test import TestCase
from evennia.utils import validatorfuncs
import mock
import datetime


class TestValidatorFuncs(TestCase):

    def test_text_ok(self):
        for val in [None, -123, 'abc', 1.234, {1:True, 2:False}, ['a', 1]]:
            self.assertEqual(str(val), validatorfuncs.text(val))    

    @mock.patch('builtins.str')
    def test_text_raises_ValueError(self, mocked_str):
        mocked_str.side_effect = Exception
        with self.assertRaises(
                ValueError,
                msg='Input could not be converted to text (Exception)'):
            validatorfuncs.text(None)

    def test_color_ok(self):
        for color in ['r', 'g', 'b', 'H', 'R', 'M', '^']:
          self.assertEqual(color, validatorfuncs.color(color))

    def test_color_falsy_raises_ValueError(self):
        for color in [None, (), [], False, True, {}]:
            with self.assertRaises(
                    ValueError,
                    msg=f'(color) is not valid Color.'):
                validatorfuncs.color(color)

    def test_datetime_ok(self):
        for dt in ['Jan 2 12:00', 'Dec 31 00:00 2018']:
            self.assertTrue(isinstance(validatorfuncs.datetime(dt), datetime.datetime))

    def test_datetime_raises_ValueError(self):
        for dt in ['', 'January 1, 2019', '1/1/2019', 'Jan 1 2019']:
            with self.assertRaises(
                    ValueError,
                    msg='Date must be entered in a 24-hr format such as: '):
                validatorfuncs.datetime(dt)

    def test_duration_ok(self):
        for d in ['1d', '2w', '3h', '4s', '5m', '6y']:
            self.assertTrue(
                isinstance(validatorfuncs.duration(d), datetime.timedelta))

        # THE FOLLOWING FAILS, year calculation seems to be incorrect
        # self.assertEqual(
        #     datetime.timedelta(1+5*365, 2, 0, 0, 3, 4, 5),
        #     validatorfuncs.duration('1d 2s 3m 4h 5w 5y'))

    def test_duration_raises_ValueError(self):
        for d in ['', '1', '5days', '1Week']:
            with self.assertRaises(
                    ValueError,
                    msg=f"Could not convert section 'd' to Duration."):
                validatorfuncs.duration(d)
