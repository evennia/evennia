# -*- coding: utf-8 -*-
"""
Tests for the EvMore pager (evennia.utils.evmore).

These focus on the pager re-reading the terminal size when the client is
resized mid-pagination (issue #3916), so that pages rendered after a resize use
the current dimensions rather than the ones cached at construction time.

"""

from unittest.mock import Mock

from evennia.utils.evmore import EvMore
from evennia.utils.test_resources import BaseEvenniaTest


class TestEvMoreResize(BaseEvenniaTest):
    """Terminal-resize handling for the EvMore pager."""

    def setUp(self):
        super().setUp()
        # avoid sending real output while exercising the pager
        self.char1.msg = Mock()
        # deterministic starting screen size
        self.session.protocol_flags["SCREENWIDTH"] = {0: 80}
        self.session.protocol_flags["SCREENHEIGHT"] = {0: 20}

    def _make_pager(self, nlines=50):
        text = "\n".join(f"line {num}" for num in range(nlines))
        return EvMore(self.char1, text, session=self.session)

    def _set_screen(self, height=None, width=None):
        if height is not None:
            self.session.protocol_flags["SCREENHEIGHT"] = {0: height}
        if width is not None:
            self.session.protocol_flags["SCREENWIDTH"] = {0: width}

    def test_calc_size_honors_char_cap(self):
        """_calc_size reads current flags and caps chars-per-page at 10000."""
        self._set_screen(height=10000, width=5)
        pager = self._make_pager()
        # width passes straight through; height is capped by 10000 // width
        self.assertEqual(pager._calc_size(), (5, 10000 // 5))

    def test_no_resize_uses_initial_size(self):
        """Without a resize, the pager keeps its initial size and page count."""
        pager = self._make_pager()
        initial_height = pager.height
        initial_npages = pager._npages
        # a display with no size change must not alter pagination
        pager.display()
        self.assertEqual(pager.height, initial_height)
        self.assertEqual(pager._npages, initial_npages)

    def test_resize_shrink_repaginates(self):
        """Shrinking the terminal mid-pagination adds pages (the bug case)."""
        pager = self._make_pager()
        initial_height = pager.height
        initial_npages = pager._npages

        # user shrinks their terminal after paging started
        self._set_screen(height=8)
        pager.display()

        self.assertLess(pager.height, initial_height)
        self.assertGreater(pager._npages, initial_npages)

    def test_resize_grow_repaginates(self):
        """Growing the terminal mid-pagination removes pages."""
        # start small so there is room to grow
        self._set_screen(height=8)
        pager = self._make_pager()
        initial_height = pager.height
        initial_npages = pager._npages

        self._set_screen(height=40)
        pager.display()

        self.assertGreater(pager.height, initial_height)
        self.assertLess(pager._npages, initial_npages)

    def test_resize_clamps_position(self):
        """A resize that reduces the page count keeps the position valid."""
        # start small -> many pages
        self._set_screen(height=8)
        pager = self._make_pager()
        # jump to the last page
        pager._npos = pager._npages - 1
        last_pos = pager._npos

        # grow the terminal so far fewer pages are needed
        self._set_screen(height=200)
        # this must not raise IndexError and must clamp the position
        pager.display()

        self.assertLess(pager._npages, last_pos + 1)
        self.assertLessEqual(pager._npos, pager._npages - 1)
        self.assertGreaterEqual(pager._npos, 0)
