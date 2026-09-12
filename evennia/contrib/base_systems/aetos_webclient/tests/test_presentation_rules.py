"""
Tests for E2 -- non-destructive presentation rules.

Addendum C.14, RULE-001.

The gate is one sentence: **hidden or substituted output remains fully
recoverable from canonical history.** Everything else here follows from it.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _read(relative):
    """
    Read a client module.

    Args:
        relative (str): Path under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / relative).read_text(encoding="utf-8")


RULES = _read("presentation/rules.js")
SHELL = _read("aetos.js")
STORAGE = _read("storage.js")


class TestRulesArePresentationOnly(TestCase):
    """
    RULE-001. A rule changes how output looks and nothing else.

    """

    def test_the_engine_never_touches_the_store(self):
        for forbidden in ("store.", "applySync", "canonicalLog", "dispatcher"):
            self.assertNotIn(forbidden, RULES, "rules.js reaches %r" % forbidden)

    def test_present_returns_metadata_rather_than_mutating(self):
        """
        The caller receives a separate object, so there is no way to
        accidentally hand the mutated thing onward as though it were the
        record.

        """
        start = RULES.index("function present(event")
        end = RULES.index("return {\n            load: load")
        body = RULES[start:end]
        self.assertIn("var result = {", body)
        self.assertNotIn("event.originalText =", body)
        self.assertNotIn("event.category =", body)

    def test_rules_run_after_state_log_and_automation(self):
        """
        The ordering E0 established, and the reason a filter cannot prevent a
        trigger firing.

        """
        start = SHELL.index('pipeline.observe("presentation", function (event) {')
        end = SHELL.index("if (capture) {", start)
        body = SHELL[start:end]
        # Matched on the call, not on its arguments: E3 wrapped this across
        # lines when it started passing the active group map, and an assertion
        # that included the first argument broke on formatting alone.
        self.assertIn("displayRules.present(", body)

    def test_a_filtered_line_is_not_drawn_but_is_not_deleted(self):
        """
        The distinction the whole milestone rests on.

        """
        self.assertIn("if (display.hiddenInView) {", SHELL)
        start = SHELL.index("if (display.hiddenInView) {")
        window = SHELL[start : start + 200]
        self.assertIn("return null", window)


class TestSubstitutionDoesNotLeaveStaleOffsets(TestCase):
    """
    C.14.

    A highlight pointing at the wrong words asserts something false about which
    part mattered, which is worse than no highlight at all.

    """

    def test_spans_are_dropped_when_the_length_changes(self):
        self.assertIn("replaced.length !== result.displayText.length", RULES)
        start = RULES.index("replaced.length !== result.displayText.length")
        window = RULES[start : start + 500]
        self.assertIn("result.spans = []", window)

    def test_overlapping_spans_are_merged(self):
        """
        Otherwise rendering would produce nested or crossing markup, which is
        invalid and renders unpredictably.

        """
        self.assertIn("span.start < last.end", RULES)

    def test_a_zero_width_match_cannot_loop_forever(self):
        self.assertIn("match[0].length === 0", RULES)


class TestHighlightsCarryMeaningNotJustColour(TestCase):
    """A.56, and the reason a highlight has a label at all."""

    def test_a_rule_has_a_style_token_rather_than_a_colour(self):
        """
        The theme decides what it looks like. A rule that stored `#ff0000`
        would be unreadable in a high-contrast theme and unchangeable by one.

        """
        self.assertIn("style: String(raw.style", RULES)
        self.assertNotIn("color:", RULES)

    def test_every_span_carries_a_label(self):
        self.assertIn('label: rule.label || "highlighted"', RULES)

    def test_the_label_is_rendered_as_text_not_an_aria_label(self):
        """
        `<mark>` carries no implicit role, and `aria-label` on a roleless
        element is not reliably supported -- axe reports it as indeterminate,
        which is a fair description of what a screen reader will do with it.
        Real text is announced by everything.

        """
        start = SHELL.index("function renderHighlighted")
        end = SHELL.index("return fragment;", start)
        body = SHELL[start:end]
        self.assertIn("aetos-visually-hidden", body)
        self.assertNotIn('setAttribute("aria-label"', body)

    def test_the_mark_is_underlined_as_well_as_coloured(self):
        """
        So it survives a high-contrast theme and is visible without colour
        perception.

        """
        css = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")
        start = css.index(".aetos-console__mark {")
        window = css[start : start + 400]
        self.assertIn("text-decoration", window)


class TestRegexIsBounded(TestCase):
    """
    A.16 / E4.

    JavaScript has no universal safe timeout for regex execution, so the only
    real defence is refusing to run anything expensive.

    """

    def test_patterns_and_input_are_both_bounded(self):
        self.assertIn("MAX_PATTERN_LENGTH", RULES)
        self.assertIn("MAX_INPUT_LENGTH", RULES)

    def test_a_rule_matches_one_event_not_the_transcript(self):
        self.assertIn("event.originalText", RULES)
        self.assertNotIn("canonicalLog.all()", RULES)

    def test_dangerous_patterns_warn_rather_than_being_silently_accepted(self):
        self.assertIn("DANGEROUS", RULES)
        self.assertIn("may be slow", RULES)

    def test_plain_text_patterns_are_escaped(self):
        """
        So a player typing "cost: $5 (each)" gets a literal match rather than a
        syntax error about an unbalanced group.

        """
        self.assertIn("replace(/[.*+?^${}()|[\\]\\\\]/g", RULES)

    def test_the_rule_count_is_bounded(self):
        self.assertIn("MAX_RULES", RULES)


class TestTheDatabaseSchemaWasBumped(TestCase):
    """
    E2 added a namespace, which is only half the change.

    """

    def test_display_rules_is_a_namespace(self):
        self.assertIn('"display_rules"', STORAGE)

    def test_the_version_was_bumped_with_it(self):
        """
        IndexedDB creates object stores only during an upgrade. Adding a
        namespace without bumping the version works perfectly on a fresh
        browser and throws on every existing install -- which is exactly what
        happened while building this.

        """
        version = int(re.search(r"var DB_VERSION = (\d+);", STORAGE).group(1))
        self.assertGreaterEqual(version, 2)

    def test_the_privacy_panel_lists_it(self):
        """
        A namespace the privacy panel does not name is data a player cannot see
        they are storing (A.75).

        """
        settings = _read("settings.js")
        self.assertIn("display_rules:", settings)
