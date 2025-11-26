#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test of the ANSI parsing and ANSIStrings.

"""

from django.test import TestCase

from evennia.utils.ansi import (
    ANSIString as AN,
    ANSI_RED,
    ANSI_CYAN,
    ANSI_YELLOW,
    ANSI_GREEN,
    ANSI_BLUE,
    ANSI_HILITE,
    ANSI_NORMAL,
)


class TestANSIString(TestCase):
    """
    Verifies that ANSIString's string-API works as intended.
    """

    def setUp(self):
        self.example_raw = "|relectric |cboogaloo|n"
        self.example_ansi = AN(self.example_raw)
        self.example_str = "electric boogaloo"
        self.example_output = (
            f"{ANSI_HILITE}{ANSI_RED}electric {ANSI_HILITE}{ANSI_CYAN}boogaloo{ANSI_NORMAL}"
        )

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

    def test_getitem_index_access(self):
        """Test individual character access via indexing"""
        # Test accessing individual characters
        self.assertEqual(self.example_ansi[0].clean(), "e")
        self.assertEqual(self.example_ansi[9].clean(), "b")
        self.assertEqual(self.example_ansi[-1].clean(), "o")
        self.assertEqual(self.example_ansi[-2].clean(), "o")

        # Verify ANSI codes are preserved when accessing characters
        first_char = self.example_ansi[0]
        self.assertTrue(isinstance(first_char, AN))
        # First character should have red color code
        self.assertIn(ANSI_RED, first_char.raw())

        # Test character at color boundary (first character after color change)
        ninth_char = self.example_ansi[9]
        self.assertEqual(ninth_char.clean(), "b")
        # Should have cyan color code
        self.assertIn(ANSI_CYAN, ninth_char.raw())

    def test_getitem_slice_access(self):
        """Test slice access"""
        # Test basic slicing
        substring = self.example_ansi[0:8]
        self.assertEqual(substring.clean(), "electric")
        self.assertTrue(isinstance(substring, AN))

        # Test slicing with step
        substring2 = self.example_ansi[9:17]
        self.assertEqual(substring2.clean(), "boogaloo")

        # Test negative indices
        last_three = self.example_ansi[-3:]
        self.assertEqual(last_three.clean(), "loo")

        # Verify ANSI codes are preserved in slices
        first_word = self.example_ansi[0:8]
        self.assertIn(ANSI_RED, first_word.raw())

    def test_getitem_edge_cases(self):
        """Test edge cases for indexing"""
        # Test with string with no ANSI codes
        plain = AN("plain text")
        self.assertEqual(plain[0].clean(), "p")
        self.assertEqual(plain[6].clean(), "t")

        # Test with single character
        single = AN("|rX|n")
        self.assertEqual(len(single), 1)
        self.assertEqual(single[0].clean(), "X")

        # Test IndexError
        with self.assertRaises(IndexError):
            _ = self.example_ansi[100]

    def test_upper_method(self):
        """Test upper() method"""
        # Test basic upper with ANSI codes
        result = self.example_ansi.upper()
        self.assertEqual(result.clean(), "ELECTRIC BOOGALOO")
        self.assertTrue(isinstance(result, AN))

        # Verify ANSI codes are preserved
        self.assertIn(ANSI_RED, result.raw())
        self.assertIn(ANSI_CYAN, result.raw())

        # Test with mixed case
        mixed = AN("|rHeLLo |cWoRLd|n")
        self.assertEqual(mixed.upper().clean(), "HELLO WORLD")

    def test_lower_method(self):
        """Test lower() method"""
        # Test basic lower with ANSI codes
        upper_ansi = AN("|rELECTRIC |cBOOGALOO|n")
        result = upper_ansi.lower()
        self.assertEqual(result.clean(), "electric boogaloo")
        self.assertTrue(isinstance(result, AN))

        # Verify ANSI codes are preserved
        self.assertIn(ANSI_RED, result.raw())
        self.assertIn(ANSI_CYAN, result.raw())

    def test_capitalize_method(self):
        """Test capitalize() method"""
        # Test basic capitalize with ANSI codes
        lower_ansi = AN("|relectric |cboogaloo|n")
        result = lower_ansi.capitalize()
        self.assertEqual(result.clean(), "Electric boogaloo")
        self.assertTrue(isinstance(result, AN))

        # Verify ANSI codes are preserved
        self.assertIn(ANSI_RED, result.raw())

    def test_swapcase_method(self):
        """Test swapcase() method"""
        # Test basic swapcase with ANSI codes
        mixed = AN("|rElEcTrIc |cBoOgAlOo|n")
        result = mixed.swapcase()
        self.assertEqual(result.clean(), "eLeCtRiC bOoGaLoO")
        self.assertTrue(isinstance(result, AN))

        # Verify ANSI codes are preserved
        self.assertIn(ANSI_RED, result.raw())
        self.assertIn(ANSI_CYAN, result.raw())

    def test_transform_with_dense_ansi(self):
        """Test string transformation with ANSI codes between every character"""
        # Simulate rainbow text with ANSI between each character
        dense = AN("|rh|ce|yl|gl|bo|n")
        self.assertEqual(dense.clean(), "hello")

        # Test upper preserves all ANSI codes
        upper_dense = dense.upper()
        self.assertEqual(upper_dense.clean(), "HELLO")
        self.assertTrue(isinstance(upper_dense, AN))

        # Verify all color codes are still present
        raw = upper_dense.raw()
        self.assertIn(ANSI_RED, raw)
        self.assertIn(ANSI_CYAN, raw)
        self.assertIn(ANSI_YELLOW, raw)
        self.assertIn(ANSI_GREEN, raw)
        self.assertIn(ANSI_BLUE, raw)

    def test_transform_without_ansi(self):
        """Test string transformation on plain strings"""
        plain = AN("hello world")

        self.assertEqual(plain.upper().clean(), "HELLO WORLD")
        self.assertEqual(plain.lower().clean(), "hello world")
        self.assertEqual(plain.capitalize().clean(), "Hello world")

    def test_getitem_no_cancelled_codes_after_reset(self):
        """
        Test that slicing after a reset does NOT inherit cancelled codes.

        This prevents exponential ANSI code accumulation during split/slice
        operations. Text after a reset (|n) should not carry forward the
        color codes that were cancelled by that reset.
        """
        # String with red text, reset, then plain text
        text = AN("|rRed|n plain")

        # Slice starting after the reset - should NOT have red codes
        after_reset = text[4:]  # " plain"
        self.assertEqual(after_reset.clean(), "plain")

        # The raw output should NOT contain red color code since it was reset
        raw = after_reset.raw()
        self.assertNotIn(ANSI_RED, raw, "Cancelled red code should not appear after reset")
        self.assertNotIn(ANSI_HILITE, raw, "Cancelled hilite code should not appear after reset")

        # More complex case: multiple colors with resets
        multi = AN("|rRed|n |gGreen|n |bBlue|n end")

        # Slice after all color codes are reset
        end_slice = multi[-3:]  # "end"
        self.assertEqual(end_slice.clean(), "end")
        # Should have no color codes since all were reset
        end_raw = end_slice.raw()
        self.assertNotIn(ANSI_RED, end_raw)
        self.assertNotIn(ANSI_GREEN, end_raw)
        self.assertNotIn(ANSI_BLUE, end_raw)
