#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test of the ANSI parsing and ANSIStrings.

"""

from django.test import TestCase

from evennia.utils.ansi import ANSIString as AN


class TestANSIString(TestCase):
    """
    Verifies that ANSIString's string-API works as intended.
    """

    def setUp(self):
        self.example_raw = "|relectric |cboogaloo|n"
        self.example_ansi = AN(self.example_raw)
        self.example_str = "electric boogaloo"
        self.example_output = "\x1b[1m\x1b[31melectric \x1b[1m\x1b[36mboogaloo\x1b[0m"

    def test_length(self):
        self.assertEqual(len(self.example_ansi), 17)

    def test_clean(self):
        self.assertEqual(self.example_ansi.clean(), self.example_str)

    def test_raw(self):
        self.assertEqual(self.example_ansi.raw(), self.example_output)

    def test_format(self):
        self.assertEqual(f"{self.example_ansi:0<20}", self.example_output + "000")

    def test_split_with_mixed_strings(self):
        """This tests the solution of a bug"""

        anstr1 = AN("Line1\nLine2")
        anstr2 = AN("\n").join([AN("Line1"), AN("Line2")])
        anstr3 = AN("\n").join([AN("Line1"), "Line2"])

        self.assertEqual(anstr2, anstr3)
        self.assertEqual(anstr1, anstr2)
        self.assertEqual(anstr1, anstr3)

        split1 = anstr1.split("\n")
        split2 = anstr2.split("\n")
        split3 = anstr3.split("\n")

        self.assertEqual(split2, split3, "Split 2 and 3 differ")
        self.assertEqual(split1, split2, "Split 1 and 2 differ")
        self.assertEqual(split1, split3, "Split 1 and 3 differ")
