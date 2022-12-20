"""
Test Color markup.

"""

import re

from evennia.utils.test_resources import BaseEvenniaTest

from . import color_markups


class TestColorMarkup(BaseEvenniaTest):
    """
    Note: Normally this would be tested by importing the ansi parser and run
    the mappings through it. This is not possible since the ansi module creates
    its mapping at the module/class level; since the ansi module is used by so
    many other modules it appears that trying to overload
    settings to test it causes issues with unrelated tests.
    """

    def test_curly_markup(self):
        ansi_map = color_markups.CURLY_COLOR_ANSI_EXTRA_MAP
        self.assertIsNotNone(re.match(re.escape(ansi_map[7][0]), "{r"))
        self.assertIsNotNone(re.match(re.escape(ansi_map[-1][0]), "{[X"))
        xterm_fg = color_markups.CURLY_COLOR_XTERM256_EXTRA_FG
        self.assertIsNotNone(re.match(xterm_fg[0], "{001"))
        self.assertIsNotNone(re.match(xterm_fg[0], "{123"))
        self.assertIsNotNone(re.match(xterm_fg[0], "{455"))
        xterm_bg = color_markups.CURLY_COLOR_XTERM256_EXTRA_BG
        self.assertIsNotNone(re.match(xterm_bg[0], "{[001"))
        self.assertIsNotNone(re.match(xterm_bg[0], "{[123"))
        self.assertIsNotNone(re.match(xterm_bg[0], "{[455"))
        xterm_gfg = color_markups.CURLY_COLOR_XTERM256_EXTRA_GFG
        self.assertIsNotNone(re.match(xterm_gfg[0], "{=h"))
        self.assertIsNotNone(re.match(xterm_gfg[0], "{=e"))
        self.assertIsNotNone(re.match(xterm_gfg[0], "{=w"))
        xterm_gbg = color_markups.CURLY_COLOR_XTERM256_EXTRA_GBG
        self.assertIsNotNone(re.match(xterm_gbg[0], "{[=a"))
        self.assertIsNotNone(re.match(xterm_gbg[0], "{[=k"))
        self.assertIsNotNone(re.match(xterm_gbg[0], "{[=z"))
        bright_map = color_markups.CURLY_COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP
        self.assertEqual(bright_map[0][1], "{[500")
        self.assertEqual(bright_map[-1][1], "{[222")

    def test_mux_markup(self):
        ansi_map = color_markups.MUX_COLOR_ANSI_EXTRA_MAP
        self.assertIsNotNone(re.match(re.escape(ansi_map[10][0]), "%cr"))
        self.assertIsNotNone(re.match(re.escape(ansi_map[-1][0]), "%cX"))
        xterm_fg = color_markups.MUX_COLOR_XTERM256_EXTRA_FG
        self.assertIsNotNone(re.match(xterm_fg[0], "%c001"))
        self.assertIsNotNone(re.match(xterm_fg[0], "%c123"))
        self.assertIsNotNone(re.match(xterm_fg[0], "%c455"))
        xterm_bg = color_markups.MUX_COLOR_XTERM256_EXTRA_BG
        self.assertIsNotNone(re.match(xterm_bg[0], "%c[001"))
        self.assertIsNotNone(re.match(xterm_bg[0], "%c[123"))
        self.assertIsNotNone(re.match(xterm_bg[0], "%c[455"))
        xterm_gfg = color_markups.MUX_COLOR_XTERM256_EXTRA_GFG
        self.assertIsNotNone(re.match(xterm_gfg[0], "%c=h"))
        self.assertIsNotNone(re.match(xterm_gfg[0], "%c=e"))
        self.assertIsNotNone(re.match(xterm_gfg[0], "%c=w"))
        xterm_gbg = color_markups.MUX_COLOR_XTERM256_EXTRA_GBG
        self.assertIsNotNone(re.match(xterm_gbg[0], "%c[=a"))
        self.assertIsNotNone(re.match(xterm_gbg[0], "%c[=k"))
        self.assertIsNotNone(re.match(xterm_gbg[0], "%c[=z"))
        bright_map = color_markups.MUX_COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP
        self.assertEqual(bright_map[0][1], "%c[500")
        self.assertEqual(bright_map[-1][1], "%c[222")
