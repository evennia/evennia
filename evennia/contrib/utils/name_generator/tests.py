"""
Tests for the Random Name Generator
"""

from evennia.contrib.utils.name_generator import namegen
from evennia.utils.test_resources import BaseEvenniaTest

_INVALID_STYLES = {
    "missing_keys": {
        "consonants": ["c", "d"],
        "length": (1, 2),
    },
    "invalid_vowels": {
        "syllable": "CVC",
        "consonants": ["c", "d"],
        "vowels": "aeiou",
        "length": (1, 2),
    },
    "invalid_length": {
        "syllable": "CVC",
        "consonants": ["c", "d"],
        "vowels": ["a", "e"],
        "length": 2,
    },
}

namegen._FANTASY_NAME_STRUCTURES |= _INVALID_STYLES


class TestNameGenerator(BaseEvenniaTest):
    def test_fantasy_name(self):
        """
        Verify output types and lengths.

        fantasy_name()       - str
        fantasy_name(style="fluid") - str
        fantasy_name(num=3)  - list of length 3
        fantasy_name(return_list=True) - list of length 1

        raises KeyError on missing style or ValueError on num
        """
        single_name = namegen.fantasy_name()
        self.assertEqual(type(single_name), str)

        fluid_name = namegen.fantasy_name(style="fluid")
        self.assertEqual(type(fluid_name), str)

        three_names = namegen.fantasy_name(num=3)
        self.assertEqual(type(three_names), list)
        self.assertEqual(len(three_names), 3)

        single_list = namegen.fantasy_name(return_list=True)
        self.assertEqual(type(single_list), list)
        self.assertEqual(len(single_list), 1)

        with self.assertRaises(ValueError):
            namegen.fantasy_name(num=-1)

        with self.assertRaises(ValueError):
            namegen.fantasy_name(style="dummy")

    def test_structure_validation(self):
        """
        Verify that validation raises the correct errors for invalid inputs.
        """
        with self.assertRaises(KeyError):
            namegen.fantasy_name(style="missing_keys")

        with self.assertRaises(TypeError):
            namegen.fantasy_name(style="invalid_vowels")

        with self.assertRaises(ValueError):
            namegen.fantasy_name(style="invalid_length")

    def test_first_name(self):
        """
        Verify output types and lengths.

        first_name()       - str
        first_name(num=3)  - list of length 3
        first_name(gender='f') - str
        first_name(return_list=True) - list of length 1
        """
        single_name = namegen.first_name()
        self.assertEqual(type(single_name), str)

        three_names = namegen.first_name(num=3)
        self.assertEqual(type(three_names), list)
        self.assertEqual(len(three_names), 3)

        gendered_name = namegen.first_name(gender="f")
        self.assertEqual(type(gendered_name), str)

        single_list = namegen.first_name(return_list=True)
        self.assertEqual(type(single_list), list)
        self.assertEqual(len(single_list), 1)

        with self.assertRaises(ValueError):
            namegen.first_name(gender="x")

        with self.assertRaises(ValueError):
            namegen.first_name(num=-1)

    def test_last_name(self):
        """
        Verify output types and lengths.

        last_name()       - str
        last_name(num=3)  - list of length 3
        last_name(return_list=True) - list of length 1
        """
        single_name = namegen.last_name()
        self.assertEqual(type(single_name), str)

        three_names = namegen.last_name(num=3)
        self.assertEqual(type(three_names), list)
        self.assertEqual(len(three_names), 3)

        single_list = namegen.last_name(return_list=True)
        self.assertEqual(type(single_list), list)
        self.assertEqual(len(single_list), 1)

        with self.assertRaises(ValueError):
            namegen.last_name(num=-1)

    def test_full_name(self):
        """
        Verify output types and lengths.

        full_name()       - str
        full_name(num=3)  - list of length 3
        full_name(gender='f') - str
        full_name(return_list=True) - list of length 1
        """
        single_name = namegen.full_name()
        self.assertEqual(type(single_name), str)

        three_names = namegen.full_name(num=3)
        self.assertEqual(type(three_names), list)
        self.assertEqual(len(three_names), 3)

        gendered_name = namegen.full_name(gender="f")
        self.assertEqual(type(gendered_name), str)

        single_list = namegen.full_name(return_list=True)
        self.assertEqual(type(single_list), list)
        self.assertEqual(len(single_list), 1)

        parts_name = namegen.full_name(parts=4)
        # a name made of 4 parts must have at least 3 spaces, but may have more
        parts = parts_name.split(" ")
        self.assertGreaterEqual(len(parts), 3)

        with self.assertRaises(ValueError):
            namegen.full_name(parts=1)

        with self.assertRaises(ValueError):
            namegen.full_name(num=-1)
