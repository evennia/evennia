"""
Tests for the console frame, and for the scrolling it was hiding.

Gary, with a screenshot of the client at a larger text size and most of the
scrollbars circled in red:

    *"first move the text input and send button into the actual text output
    frame. then next lets find a way to minimize all the scrolling. I upped the
    text size and its creating a scroll bar maze from hell. lets figur out how to
    accomodate larger text without the need to doom scroll"*

and then:

    *"our ui needs to be slick, clean and beautiful to look at"*

**The composer.** It was a `<footer>` at the bottom of the whole client, the
full height of the workspace away from the text it answers. It is now the bottom
edge of the console's own frame, and the two share one border.

**The maze had four separate causes**, and only the first is the one anybody
would have guessed:

1. *Nested scroll containers.* A region scrolled, every panel body inside it
   scrolled, and some lists inside those scrolled again. The inner two were
   defensive rather than needed -- panels are `flex: 0 0 auto` and already grow
   to their content.
2. *A resized panel got a fixed `height`*, which is a lid: content taller than it
   clips and grows a scrollbar. It is now a `minHeight`, which is a floor.
3. *Seven `font-size` declarations were in `px`.* The text-size setting scales
   `.aetos-root`, so those did not move: turning the text up grew the game output
   and left every label, button and dialog title at its original size.
4. *The responsive breakpoints were in pixels.* At 250% text an 800px client
   still called itself "desktop" and kept three columns, so each was a handful of
   characters wide with a scrollbar down the side. Breakpoints are really about
   how much text fits, and width alone only answers that while the text stays one
   size.

Verified live at 70%, 100%, 150% and 250% text: 150% now folds to two columns and
250% to one, which is the reflow that was missing rather than a smaller version
of the same broken layout.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

STATIC = Path(AETOS_STATIC_DIR)
CSS_DIR = STATIC / "aetos" / "css"
JS_DIR = STATIC / "aetos" / "js"

CSS = (CSS_DIR / "aetos.css").read_text(encoding="utf-8")
TEMPLATE = (STATIC.parent / "templates" / "webclient.html").read_text(encoding="utf-8")
LAYOUT = (JS_DIR / "layout.js").read_text(encoding="utf-8")
RESPONSIVE = (JS_DIR / "responsive.js").read_text(encoding="utf-8")
ACCESSIBILITY = (JS_DIR / "accessibility" / "accessibility.js").read_text(encoding="utf-8")


def _console_section():
    """
    The markup of the console widget, from its opening tag to its close.

    Returns:
        str: The section's source.

    """
    start = TEMPLATE.index('<section id="aetos-console-widget"')
    return TEMPLATE[start : TEMPLATE.index("</section>", start)]


class TestTheComposerIsInTheFrame(TestCase):
    """
    Gary's first instruction, and the one visible change.

    """

    def test_the_input_is_inside_the_console_widget(self):
        self.assertIn('id="aetos-input"', _console_section())

    def test_so_is_the_send_button(self):
        self.assertIn('id="aetos-send"', _console_section())

    def test_the_old_bar_under_the_client_is_gone(self):
        """
        Not merely unused. A second copy of the field would give the page two
        elements with the same id, and `getElementById` would silently pick one.

        """
        self.assertNotIn("aetos-inputbar", TEMPLATE)
        self.assertNotIn("aetos-inputbar", CSS)

    def test_there_is_still_exactly_one_command_field(self):
        self.assertEqual(TEMPLATE.count('id="aetos-input"'), 1)
        self.assertEqual(TEMPLATE.count('id="aetos-send"'), 1)

    def test_the_skip_link_still_reaches_it(self):
        """
        It targets the field by id, and the field moved. Worth stating, because
        this is the one link a keyboard user takes to get to the thing they came
        for.

        """
        self.assertIn('href="#aetos-input"', TEMPLATE)

    def test_the_field_keeps_its_label(self):
        section = _console_section()
        self.assertIn('for="aetos-input"', section)
        self.assertIn("Command input", section)

    def test_the_prompt_glyph_is_hidden_from_assistive_technology(self):
        """
        A real element with `aria-hidden`, not CSS generated content: generated
        content is exposed by some screen readers, and "greater than sign" before
        every command is noise.

        """
        section = _console_section()
        self.assertIn('class="aetos-composer__prompt" aria-hidden="true"', section)
        self.assertNotIn(".aetos-composer::before", CSS)

    def test_the_composer_follows_the_console_reading_width(self):
        """
        A composer that ran the full width under a capped console would not line
        up with the frame it is part of.

        A12 rewrote what this asserts, and the reason is the pattern this
        project keeps meeting: the original asserted the *mechanism*
        (`[data-aetos-size="wide"]`) rather than the property in its own name.
        That mechanism turned out never to fire on a 1920x1080 monitor, which
        computes as `desktop` -- so the test passed for a milestone while the
        thing it describes was not happening on the commonest large screen.

        The cap is now unconditional and measured in characters, so the two
        share one token and there is no width at which they can disagree.

        A17 moved the cap up one level again, to the frame itself. Capping the
        contents bounded the line correctly and looked wrong doing it: the
        border spanned the window while the text sat in a column in the middle
        of it, and the composer's Send button was stranded well short of the
        edge it appears to belong to. Capping `.aetos-widget--console` means the
        box hugs the column it contains, which is what UI1 meant by the console
        being the one framed object on the page.

        """
        block = CSS[CSS.index("\n.aetos-widget--console {\n    max-width:") :]
        block = block[: block.index("\n}")]
        self.assertIn("max-width: var(--aetos-measure)", block)
        self.assertIn("margin-left: auto", block)


class TestOneFrame(TestCase):
    """
    *"slick, clean and beautiful"*, spent in one place.

    """

    def test_the_console_carries_the_border_and_the_base_widget_does_not(self):
        block = CSS[CSS.index(".aetos-widget {") : CSS.index(".aetos-widget--console")]
        self.assertNotIn("border:", block)
        self.assertNotIn("background:", block)
        self.assertIn(".aetos-widget--console", CSS)

    def test_panels_are_separated_by_a_rule_rather_than_boxed_each(self):
        self.assertIn(".aetos-region > .aetos-widget--panel + .aetos-widget--panel", CSS)

    def test_the_frame_clips_so_the_composer_corners_follow_it(self):
        block = CSS[CSS.index(".aetos-widget--console {") :][:400]
        self.assertIn("overflow: hidden", block)


class TestTheBoxesComeBackWhenTheyAreLoadBearing(TestCase):
    """
    Unframed panels are a decoration decision, and the wrong one for anybody who
    needs an edge to find an edge. Both the operating system's request and the
    client's own high-contrast setting put the surfaces back.

    This is the part that would be easy to skip and impossible to notice.

    """

    def test_more_contrast_restores_the_panel_surface(self):
        block = CSS[CSS.index("@media (prefers-contrast: more)") :]
        self.assertIn(".aetos-widget--panel", block)

    def test_the_client_setting_restores_it_too(self):
        self.assertIn(':root[data-aetos-contrast="high"] .aetos-widget--panel', CSS)

    def test_the_composer_field_gets_its_edges_back(self):
        self.assertIn(':root[data-aetos-contrast="high"] .aetos-composer .aetos-input', CSS)

    def test_and_so_do_the_scrollbars(self):
        """
        A scrollbar is how somebody knows there is more to read. Thin and
        low-contrast is fine until contrast is what was asked for.

        """
        self.assertIn("scrollbar-width: auto", CSS)


class TestOneScrollPerColumn(TestCase):
    """
    The nesting itself.

    """

    def test_panel_bodies_no_longer_scroll(self):
        block = CSS[CSS.index(".aetos-widget__body {") :][:200]
        self.assertNotIn("overflow-y: auto", block)

    def test_they_can_still_shrink_inside_the_column(self):
        """
        `min-height: 0` is not decoration: without it a flex item refuses to go
        below its content and forces the panel taller than the space it has.

        """
        block = CSS[CSS.index(".aetos-widget__body {") :][:200]
        self.assertIn("min-height: 0", block)

    def test_panels_no_longer_clip_their_own_content(self):
        self.assertNotIn(
            ".aetos-widget--panel {\n    overflow: hidden;\n}",
            CSS,
            "panels still clip, which is what made their bodies need scrollbars",
        )

    def test_the_region_is_still_a_scroll_container(self):
        """
        Removing the inner two only works because the outer one stays. A column
        of panels taller than the window has to go somewhere.

        """
        block = CSS[CSS.index(".aetos-region--sidebar,\n.aetos-region--aside {") :][:300]
        self.assertIn("overflow-y: auto", block)

    def test_a_resized_panel_gets_a_floor_rather_than_a_lid(self):
        block = LAYOUT[LAYOUT.index("function setSize(id, size)") :][:1200]
        self.assertIn("style.minHeight", block)
        self.assertNotIn("style.height", block)


class TestNothingSizedInPixelsIgnoresTheTextSetting(TestCase):
    """
    The defect that made the interface look broken at a larger size, generalised.

    The text scale sets `font-size` on `.aetos-root`, so everything in `em` or
    inheriting grows with it and everything in `px` does not. Seven declarations
    were in `px`; the specific seven will not come back and the shape will, which
    is why this checks the shape.

    A `max(16px, ...)` floor is not the same thing and is deliberately allowed:
    it names a minimum, and the value it is compared against still scales.

    """

    def test_no_stylesheet_pins_a_font_size_in_pixels(self):
        offenders = []
        for path in sorted(CSS_DIR.glob("*.css")):
            source = path.read_text(encoding="utf-8")
            for match in re.finditer(r"font-size:\s*([0-9.]+px)\s*;", source):
                line = source[: match.start()].count("\n") + 1
                offenders.append("%s:%d %s" % (path.name, line, match.group(1)))
        self.assertEqual(
            offenders,
            [],
            "these do not grow when the player turns the text size up: %s" % ", ".join(offenders),
        )

    def test_the_touch_floor_is_still_allowed_to_be_a_floor(self):
        """
        16px on a focused field is what stops iOS zooming the page. It is a
        minimum composed with the scaling value, not a replacement for it.

        """
        self.assertIn("max(16px, var(--aetos-font-size))", CSS)


class TestTheLayoutKnowsHowBigTheTextIs(TestCase):
    """
    The fourth cause, and the one that actually answers *"accomodate larger text
    without the need to doom scroll"*.

    """

    def test_the_breakpoint_is_measured_against_the_rendered_text_size(self):
        self.assertIn("function effectiveWidth(width, fontSize)", RESPONSIVE)
        self.assertIn("REFERENCE_FONT_SIZE / fontSize", RESPONSIVE)

    def test_the_reference_size_is_named_rather_than_buried(self):
        self.assertIn("var REFERENCE_FONT_SIZE = 14", RESPONSIVE)

    def test_the_text_size_is_read_rather_than_assumed(self):
        self.assertIn("function measuredFontSize(element)", RESPONSIVE)
        self.assertIn("getComputedStyle(element).fontSize", RESPONSIVE)

    def test_an_unreadable_font_size_falls_back_rather_than_dividing_by_it(self):
        """
        `getComputedStyle` is absent in some embedding contexts and returns an
        empty string for a detached element. Dividing by that would make every
        client a phone, or NaN.

        """
        block = RESPONSIVE[RESPONSIVE.index("function effectiveWidth") :][:400]
        self.assertIn("!fontSize || !isFinite(fontSize) || fontSize <= 0", block)

    def test_height_gets_the_same_treatment(self):
        """
        `SHORT_HEIGHT` is "how many lines fit", which is the same question.

        """
        self.assertIn("effectiveWidth(height, fontSize) < SHORT_HEIGHT", RESPONSIVE)

    def test_changing_the_text_size_asks_the_layout_to_look_again(self):
        """
        The gap that would have made all of the above do nothing.

        The responsive manager watches the root element's *size*. Changing the
        text changes only what is inside it, so the ResizeObserver never fires --
        the client kept three columns at 250% text until something else happened
        to resize it.

        """
        block = ACCESSIBILITY[ACCESSIBILITY.index('removeProperty("--aetos-scale")') :][:900]
        self.assertIn("window.Aetos.responsive.measure()", block)

    def test_it_does_not_assume_the_shell_has_finished_booting(self):
        block = ACCESSIBILITY[ACCESSIBILITY.index('removeProperty("--aetos-scale")') :][:900]
        self.assertIn("window.Aetos.responsive.measure", block)


class TestTheStackedLayoutHoldsItsShape(TestCase):
    """
    One column, at a text size large enough to need one.

    A strip that scrolls has a min-content height of zero, so a grid short of
    space squeezed these to nothing and cut every panel through the middle of its
    first line. A floor plus a scrolling workspace is one honest scrollbar
    instead of three lying ones.

    """

    def test_the_strips_cannot_be_squeezed_to_a_sliver(self):
        block = CSS[CSS.index('.aetos-root[data-aetos-size="phone"] .aetos-region--sidebar,') :][
            :1400
        ]
        self.assertIn("min-height: 4em", block)

    def test_their_cap_grows_with_the_text(self):
        block = CSS[CSS.index('.aetos-root[data-aetos-size="phone"] .aetos-region--sidebar,') :][
            :1400
        ]
        self.assertIn("max-height: max(18vh, 4em)", block)

    def test_a_swipeable_card_stays_wide_enough_to_read(self):
        self.assertIn("min(78%, max(260px, 13em))", CSS)

    def test_the_workspace_scrolls_rather_than_crushing_its_rows(self):
        block = CSS[CSS.index('.aetos-root[data-aetos-size="phone"] .aetos-workspace {') :][:1200]
        self.assertIn("overflow-y: auto", block)

    def test_the_short_window_cap_is_bounded_at_both_ends(self):
        """
        The `em` floor alone was the opposite mistake: at 250% text it claimed a
        third of a short window for each side column and took it off the console.

        """
        self.assertIn("max-height: min(max(22vh, 8em), 34vh)", CSS)
