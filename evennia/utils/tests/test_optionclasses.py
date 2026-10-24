"""Tests for the option classes in evennia.utils.optionclasses."""

import datetime

import mock
from django.test import TestCase

from evennia.utils import optionclasses


def _option(option_class, default=None):
    return option_class(mock.Mock(), "test_option", "a test option", default)


class TestOptionDeserialize(TestCase):
    def test_text_ok(self):
        self.assertEqual("hello", _option(optionclasses.Text).deserialize("hello"))

    def test_text_empty_raises_ValueError(self):
        with self.assertRaises(ValueError):
            _option(optionclasses.Text).deserialize("")

    def test_boolean_ok(self):
        self.assertEqual(True, _option(optionclasses.Boolean).deserialize(True))
        self.assertEqual(False, _option(optionclasses.Boolean).deserialize(False))

    def test_boolean_non_bool_raises_ValueError(self):
        for value in [1, 0, "true", None]:
            with self.assertRaises(ValueError):
                _option(optionclasses.Boolean).deserialize(value)

    def test_unsigned_integer_ok(self):
        for value in [0, 1, 500]:
            self.assertEqual(value, _option(optionclasses.UnsignedInteger).deserialize(value))

    def test_unsigned_integer_bad_raises_ValueError(self):
        for value in [-1, "5", 1.5]:
            with self.assertRaises(ValueError):
                _option(optionclasses.UnsignedInteger).deserialize(value)

    def test_signed_integer_ok(self):
        for value in [-3, 0, 7]:
            self.assertEqual(value, _option(optionclasses.SignedInteger).deserialize(value))

    def test_signed_integer_bad_raises_ValueError(self):
        for value in ["3", 2.0, None]:
            with self.assertRaises(ValueError):
                _option(optionclasses.SignedInteger).deserialize(value)

    def test_positive_integer_ok(self):
        for value in [1, 42]:
            self.assertEqual(value, _option(optionclasses.PositiveInteger).deserialize(value))

    def test_positive_integer_bad_raises_ValueError(self):
        for value in [0, -5, "1"]:
            with self.assertRaises(ValueError):
                _option(optionclasses.PositiveInteger).deserialize(value)

    def test_duration_ok(self):
        self.assertEqual(
            datetime.timedelta(seconds=90),
            _option(optionclasses.Duration).deserialize(90),
        )

    def test_duration_non_int_raises_ValueError(self):
        for value in ["90", 1.5, None]:
            with self.assertRaises(ValueError):
                _option(optionclasses.Duration).deserialize(value)
