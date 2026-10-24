"""
Tests for A8 (automated half) -- reflow at 320px.

WCAG 1.4.10 requires content to reflow to a 320 CSS pixel width without
two-dimensional scrolling. WCAG 2.4.11 requires a focused control not to be
hidden. The client failed both, in the same place, from M4 until this was found.

**What was wrong.** The status bar is a flex row that never wrapped. At 320px
its contents -- the connection indicator, the game name, Edit Layout, Help and
the Accessibility toggle -- measured 589px. `body` carries `overflow-x: hidden`,
so they were not merely off the right-hand edge: there was no scrollbar,
`window.scrollTo(500, 0)` left the page at 0, and the controls were unreachable
by pointer or touch at all. Tabbing to one put focus on something nobody could
see.

**How it survived.** M20 shipped responsive layout with `data-aetos-size` rules
for the workspace and the widgets, and none for the header. Every axe run passed,
because axe does not test reflow. Every one of my own runs had been at the pane's
default width.

**And the first check I wrote for it passed too.** It looked for elements *wider
than the viewport*; these elements were narrow and *positioned outside* it. Two
different failures, and I checked the wrong one first. The second version had the
opposite fault -- it flagged nine controls inside horizontally scrollable widget
bodies, which are reachable and fine. The distinction that matters is not
"off-screen" but "off-screen with no ancestor that scrolls", and that is what
`browser-qa/qa-reflow.js` now measures.

These tests pin the fix. The measurement itself lives in the browser harness,
because reflow is a question about layout and only a browser can answer it.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

CSS = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")


def _rule(selector):
    """
    The declarations of one CSS rule.

    Args:
        selector (str): The selector introducing the rule.

    Returns:
        str: The rule body.

    """
    marker = selector + " {"
    start = CSS.index(marker) + len(marker)
    return CSS[start : CSS.index("}", start)]


class TestTheStatusBarWraps(TestCase):
    """
    The row that took a whole set of controls off the side of a phone screen.

    """

    def test_it_is_allowed_to_wrap(self):
        self.assertIn("flex-wrap: wrap", _rule(".aetos-statusbar"))

    def test_it_wraps_unconditionally_rather_than_at_a_breakpoint(self):
        """
        Wrapping changes nothing when the row fits -- verified at 1280px, where
        the bar stays one 40px line. A media query here would only be another
        width to be wrong about, and being wrong about it is what this cost.

        """
        media_blocks = re.findall(r"@media[^{]*\{(.*?)\n\}", CSS, flags=re.S)
        for block in media_blocks:
            self.assertNotIn(
                ".aetos-statusbar {",
                block,
                "the status bar's layout is being set inside a media query",
            )

    def test_the_reason_is_recorded_where_somebody_would_undo_it(self):
        """
        `flex-wrap: wrap` on a bar that visibly never wraps is exactly the
        declaration somebody tidies away.

        """
        window = CSS[: CSS.index(".aetos-statusbar {")]
        self.assertIn("320px", window[-1400:])
        self.assertIn("overflow-x: hidden", window[-1400:])


class TestTheHarnessMeasuresReachabilityRatherThanPosition(TestCase):
    """
    The distinction the first two versions of the check got wrong.

    """

    def _harness(self):
        """
        The reflow QA script.

        Returns:
            str: JavaScript source, or "" when running outside a checkout.

        """
        # parents[5], not [4]: [4] is the Evennia checkout and [5] is the
        # project root that holds `browser-qa/`. The first version used [4],
        # which made all three of these tests skip silently -- a check that
        # passes by not running is the defect this suite keeps finding.
        path = Path(AETOS_STATIC_DIR).parents[5] / "browser-qa" / "qa-reflow.js"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def test_it_exists(self):
        if not self._harness():
            self.skipTest("browser-qa/ is outside a vendored contrib")
        self.assertIn("320", self._harness())

    def test_it_treats_a_scrollable_ancestor_as_reachable(self):
        source = self._harness()
        if not source:
            self.skipTest("browser-qa/ is outside a vendored contrib")
        self.assertIn("overflowX", source)
        self.assertIn("scrollWidth > node.clientWidth", source)

    def test_it_checks_scaled_text_as_well_as_a_narrow_window(self):
        """
        A width breakpoint gets scaled text wrong: the window is wide and the
        content is not. Both have to be measured.

        """
        source = self._harness()
        if not source:
            self.skipTest("browser-qa/ is outside a vendored contrib")
        self.assertIn("2.5", source)
        self.assertIn("visual: { scale", source)
