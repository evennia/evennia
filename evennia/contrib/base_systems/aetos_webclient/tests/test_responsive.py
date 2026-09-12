"""
Contract tests for the responsive layout.

Behaviour is verified in a browser by `browser-qa/qa-responsive.js`, run at
several viewport sizes. What Python pins down are the structural decisions --
that the layout measures rather than assumes, that no widget is dropped on a
small screen, and that touch sizing asks about the pointer rather than the
screen.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
CSS = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")


def _strip_comments(source):
    """
    Remove JS comments.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


class TestLayoutMeasuresRatherThanAssumes(TestCase):
    """
    Breakpoints come from the client element's own size.

    `window.innerWidth` is not the space the client has. A browser side panel, a
    devtools dock, a scrollbar or an embedding frame all make the element
    narrower than the window, and a layout that trusts the window lays out for
    space it does not have -- which is exactly the class of fault that produces
    a client not filling its container.

    """

    def setUp(self):
        self.source = _strip_comments((JS_DIR / "responsive.js").read_text(encoding="utf-8"))

    def test_uses_a_resize_observer_on_the_element(self):
        self.assertIn("ResizeObserver", self.source)
        self.assertIn("observer.observe(root)", self.source)

    def test_measures_the_elements_own_box(self):
        self.assertIn("contentRect", self.source)

    def test_falls_back_when_resize_observer_is_missing(self):
        """Older browsers must still get some responsiveness."""
        self.assertIn('addEventListener("resize"', self.source)
        self.assertIn("orientationchange", self.source)

    def test_publishes_the_breakpoint_for_css(self):
        """
        The decision lives in one place and the styling in the stylesheet, so
        JavaScript never sets pixel values that later fight a media query.

        """
        self.assertIn('setAttribute("data-aetos-size"', self.source)

    def test_flags_short_viewports_separately(self):
        """A phone in landscape is short, not narrow; they need different rules."""
        self.assertIn("data-aetos-short", self.source)


class TestBreakpointsCoverEverySize(TestCase):
    """No width may fall between breakpoints."""

    def setUp(self):
        self.source = (JS_DIR / "responsive.js").read_text(encoding="utf-8")

    def test_the_largest_breakpoint_is_unbounded(self):
        """Otherwise a very large monitor matches nothing."""
        self.assertIn("Infinity", self.source)

    def test_all_four_sizes_have_css_rules(self):
        for size in ("phone", "tablet", "wide"):
            self.assertIn('data-aetos-size="%s"' % size, CSS, "no rules for %r" % size)


class TestNothingIsLostOnASmallScreen(TestCase):
    """
    Blueprint sections 46 and 53.

    On a phone the side panels are the only non-visual route to exits and room
    contents, so hiding them to save space would remove a screen-reader user's
    only way to know where they are.

    """

    def test_no_region_is_display_none_at_any_breakpoint(self):
        offenders = []
        for match in re.finditer(
            r'\[data-aetos-size="(\w+)"\][^{]*\.aetos-region[^{]*\{([^}]*)\}', CSS
        ):
            if "display: none" in match.group(2):
                offenders.append(match.group(1))
        self.assertEqual(offenders, [], "regions hidden at: %s" % offenders)

    def test_phone_strips_scroll_rather_than_truncate(self):
        """
        A capped strip that does not scroll silently loses whatever does not
        fit. Scrolling keeps every widget reachable.

        """
        self.assertIn("overflow-x: auto", CSS)

    def test_the_console_has_a_floor_on_phone(self):
        """
        Without one, several stacked panels squeeze the game text -- the thing
        the player is actually reading -- down to a few lines.

        """
        self.assertIn("minmax(45vh, 1fr)", CSS)


class TestTouchSizingAsksAboutThePointer(TestCase):
    """
    A touchscreen laptop needs large targets at desktop width, and a phone
    driven by a mouse does not. Screen size is the wrong question.

    """

    def test_uses_a_pointer_query_not_a_width_query(self):
        self.assertIn("pointer: coarse", CSS)

    def test_targets_meet_the_minimum_size(self):
        self.assertIn("--aetos-target: 44px", CSS)

    def test_input_font_size_prevents_ios_zoom(self):
        """
        A font smaller than 16px makes iOS zoom the page on focus, leaving the
        player zoomed in with no obvious way back.

        """
        self.assertIn("max(16px, var(--aetos-font-size))", CSS)


class TestFluidSizing(TestCase):
    """Spacing and type scale continuously rather than stepping."""

    def test_spacing_and_type_are_clamped(self):
        self.assertIn("--aetos-space: clamp(", CSS)
        self.assertIn("--aetos-font-size: clamp(", CSS)

    def test_side_columns_are_proportional_and_bounded(self):
        self.assertIn("--aetos-column: clamp(", CSS)

    def test_the_reading_line_is_capped_on_wide_screens(self):
        """
        Extra width on a large monitor goes to the sides, not into an
        unreadably long line of game text.

        """
        self.assertIn("max-width: 120ch", CSS)
