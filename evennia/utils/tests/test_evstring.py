#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testing EvString functionality

"""

# TODO: the actual ANSI parser needs to be tested separately now

from django.test import TestCase

from evennia.utils.evstring import EvString


class TestEvString(TestCase):
    """
    Verifies that EvString's string-API works as intended.
    """

    def setUp(self):
        self.example_raw = "|relectric |cboogaloo|n"
        self.example_ansi = EvString(self.example_raw)
        self.example_clean = "electric boogaloo"
        # self.example_output = "\x1b[1m\x1b[31melectric \x1b[1m\x1b[36mboogaloo\x1b[0m"

    def test_length(self):
        self.assertEqual(len(self.example_ansi), 17)

    def test_clean(self):
        self.assertEqual(self.example_ansi.clean(), self.example_clean)

    def test_raw(self):
        self.assertEqual(self.example_ansi.raw(), self.example_raw)

    def test_format(self):
        self.assertEqual(f"{self.example_ansi:0<20}", self.example_raw + "000")

    def test_slice(self):
        # TODO: determine if the trailing tag should be included
        self.assertEqual(self.example_ansi[:9].raw(), "|relectric ")
        self.assertEqual(self.example_ansi[9:].raw(), "|cboogaloo|n")

    def test_inequality(self):
        """Make sure equality comparison includes codes"""
        self.assertNotEqual(EvString("|c|relectric |cboogaloo|n"), self.example_ansi)
        self.assertNotEqual(EvString("|relectric |cboogaloo"), self.example_ansi)

    def test_split_with_mixed_strings(self):
        """This tests the solution of a bug"""

        evstr1 = EvString("Line1\nLine2")
        evstr2 = EvString("\n").join([EvString("Line1"), EvString("Line2")])
        evstr3 = EvString("\n").join([EvString("Line1"), "Line2"])

        self.assertEqual(evstr2, evstr3)
        self.assertEqual(evstr1, evstr2)
        self.assertEqual(evstr1, evstr3)

        split1 = evstr1.split("\n")
        split2 = evstr2.split("\n")
        split3 = evstr3.split("\n")

        self.assertEqual(split2, split3, "Split 2 and 3 differ")
        self.assertEqual(split1, split2, "Split 1 and 2 differ")
        self.assertEqual(split1, split3, "Split 1 and 3 differ")
