#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testing EvString functionality

"""

# TODO: the actual ANSI parser needs to be tested separately now
import re
from unittest import skip
from django.test import TestCase

from evennia.utils.evstring import EvString


class TestEvString(TestCase):
    """
    Verifies that EvString's string-API works as intended.
    """

    def setUp(self):
        self.example_raw = "|relectric |cboogaloo|n"
        self.example = EvString(self.example_raw)
        self.example_clean = "electric boogaloo"
        # self.example_output = "\x1b[1m\x1b[31melectric \x1b[1m\x1b[36mboogaloo\x1b[0m"

    def test_length(self):
        self.assertEqual(len(self.example), 17)

    def test_clean(self):
        self.assertEqual(self.example.clean(), self.example_clean)

    def test_raw(self):
        self.assertEqual(self.example.raw(), self.example_raw)

    def test_format(self):
        self.assertEqual(f"{self.example:0<20}", self.example_raw + "000")

    def test_escapes(self):
        escape_code = EvString("This is ||r not red")
        self.assertIn("|r", escape_code.clean())
        self.assertNotIn("||", escape_code.clean())

    def test_inequality(self):
        """Make sure equality comparison includes codes"""
        self.assertNotEqual(EvString("|g|relectric |cboogaloo|n"), self.example)
        self.assertNotEqual(EvString("|relectric |cboogaloo"), self.example)

    def test_add(self):
        """
        Verify concatenation works correctly.
        """
        a = EvString("|gTest")
        b = EvString("|cString|n")
        c = a + b
        result = EvString("|gTest|cString|n")
        self.assertEqual(c, result)

    def test_strip(self):
        """
        Test the ansi-aware .strip() methods
        """
        a = EvString("   |r   Test of stuff |b with spaces   |n   ")
        self.assertEqual(a.strip(), EvString("|rTest of stuff |b with spaces|n"))
        self.assertEqual(a.strip(" "), EvString("|rTest of stuff |b with spaces|n"))
        self.assertEqual(a.lstrip(), EvString("|rTest of stuff |b with spaces   |n   "))
        self.assertEqual(a.rstrip(), EvString("   |r   Test of stuff |b with spaces|n"))

        b = EvString("|r|b")
        self.assertEqual(b.strip(), b)

        c = EvString("  A normal string with spaces  ")
        self.assertEqual(c.strip(), "A normal string with spaces")

        d = EvString("|rI have no closing tag")
        e = EvString("I have no open tag|n")
        self.assertEqual(d, d.strip())
        self.assertEqual(e, e.strip())

    def test_split(self):
        """
        Verifies that re.split and .split behave similarly and that color
        codes end up where they should.
        """
        target = EvString("|gThis is |nA split string|g")
        re_split = re.split("A", target)
        normal_split = target.split("A")

        self.assertEqual(len(normal_split), 2)
        self.assertEqual(normal_split[0].raw(), "|gThis is |n")
        self.assertEqual(normal_split[1].raw(), " split string|g")

        self.assertEqual(len(re_split), len(normal_split))
        for i in range(len(normal_split)):
            # regex split returns raw strings, so we compare those
            self.assertEqual(re_split[i], normal_split[i].raw())

    def test_slice(self):
        self.assertEqual(self.example[:9].raw(), "|relectric ")
        self.assertEqual(self.example[9:].raw(), "|cboogaloo|n")
        self.assertEqual(self.example[4:].raw(), "|rtric |cboogaloo|n")
        self.assertEqual(self.example[:14].raw(), "|relectric |cbooga|n")

    def test_slice_insert(self):
        """
        Inserting a slice should not remove ansi markup (issue #2205)
        """
        string = EvString("|rTest|n")
        split_string = string[:0] + "Test" + string[4:]
        self.assertEqual(string, split_string)

    def test_slice_insert_longer(self):
        """
        EvString captures the prefixing style codes when splitting a chunk in order to preserve displayed
        color information. This results in some redundancy of codes when splitting and rejoining, but
        with minimal other impact.
        """
        string = EvString("A bigger |rtest of things |bwith more colors|n")
        # from evennia import set_trace;set_trace()
        split_string = string[:17] + "testing " + string[17:]
        self.assertEqual(
            (
                EvString("A bigger |rtest of ")
                + EvString("testing ")
                + EvString("|rthings |bwith more colors|n") # note that the |r is replayed here
            ),
            split_string,
        )

    def test_slice_full(self):
        string = EvString("A bigger |rTest|n of things |bwith more color|n")
        split_string = string[:]
        self.assertEqual(string, split_string)

    def test_join(self):
        """
        Verify that joining a set of EvStrings works.
        """
        # when joining strings, python uses the type of the glue
        # joining with a str will create a string, while joining with an EvString will create an EvString
        l = [EvString("|gTest|r") for _ in range(0, 3)]
        result = "".join(l)
        self.assertEqual(result, "|gTest|r|gTest|r|gTest|r")
        result = EvString("").join(l)
        self.assertEqual(result, EvString("|gTest|r|gTest|r|gTest|r"))

    def test_capitalize(self):
        """
        Make sure that capitalization works. This is the simplest of the
        _transform functions.
        """
        target = EvString("|gtest|n")
        result = EvString("|gTest|n")
        self.assertEqual(target.capitalize(), result)

    def test_title(self):
        """
        Make sure that title case works. Slightly more complex than capitalization.
        """
        result = "|rElectric |cBoogaloo|n"
        self.assertEqual(self.example.title(), result)
        # hard mode: mix color codes into the words
        target = EvString("|rrai|ynbo|gw l|cett|bers|m!|n")
        result = "|rRai|ynbo|gw L|cett|bers|m!|n"
        self.assertEqual(target.title(), result)

    def test_regex_sub(self):
        string = EvString("A |rTest|n string")
        result = re.compile(r"Test").sub("Replacement", string)
        expected = "A |rReplacement|n string"

        self.assertEqual(expected, result)

    # skipping these two regex tests for now as the regex search is currently operating on the raw string
    # it's not clear how best to return indices that are useful to the evstring from the regular string, or
    # if such a reverse-conversion is necessary
    @skip
    def test_regex_search(self):
        """
        Test regex-search in ANSIString - the found position should ignore any ansi-markers
        """
        string = EvString(" |r|[b  Test ")
        match = re.search(r"Test", string)
        self.assertTrue(match)
        self.assertEqual(match.span(), (3, 7))

    @skip
    def test_regex_replace(self):
        """
        Inserting text into an ansistring at an index position should ignore
        the ansi markers but not remove them!

        """
        string = EvString("A |rTest|n string")
        match = re.search(r"Test", string)
        ix1, ix2 = match.span()
        self.assertEqual((ix1, ix2), (2, 6))

        result = string[:ix1] + "Replacement" + string[ix2:]
        expected = EvString("A |rReplacement|n string")

        self.assertEqual(expected, result)

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
    
