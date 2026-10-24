"""
Tests for E0 -- the event pipeline contract.

Addendum C.7 (PIPE-001) and C.8 (PIPE-002).

The gate is one sentence: **a presentation filter cannot alter state, canonical
history, or trigger input.** Everything here exists to make that provable rather
than promised, because the failure it prevents is one of the most unpleasant
kinds to diagnose -- an automation that silently stops working because of an
unrelated display setting.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
EVENTS_DIR = JS_DIR / "events"


def _read(path):
    """
    Read a file.

    Args:
        path (Path): File to read.

    Returns:
        str: Contents.

    """
    return path.read_text(encoding="utf-8")


PIPELINE = _read(EVENTS_DIR / "pipeline.js")
LOG = _read(EVENTS_DIR / "canonical_log.js")
SHELL = _read(JS_DIR / "aetos.js")


class TestTheOrderIsDeclared(TestCase):
    """PIPE-001. The order is the contract, so it is written down as data."""

    def test_the_stages_are_a_named_list(self):
        self.assertIn("var STAGES = [", PIPELINE)

    def test_the_order_is_exactly_the_specified_one(self):
        block = PIPELINE[PIPELINE.index("var STAGES = [") : PIPELINE.index("if (Object.freeze)")]
        found = re.findall(r'"(\w+)"', block)
        self.assertEqual(
            found,
            [
                "validate",
                "normalize",
                "state",
                "log",
                "automation",
                "presentation",
                "announce",
            ],
        )

    def test_the_list_is_frozen(self):
        """
        A contract a caller can reorder at runtime is not a contract.

        """
        self.assertIn("Object.freeze(STAGES)", PIPELINE)

    def test_state_precedes_automation(self):
        """
        The ordering rule with teeth. A trigger that fires on stale state acts
        on a world that has already moved on -- it reads the health it had
        before the hit that prompted it.

        """
        self.assertLess(
            PIPELINE.index("/* 3. Authoritative state"),
            PIPELINE.index("/* 5. Automation"),
        )

    def test_the_log_is_written_before_anything_reads(self):
        self.assertLess(PIPELINE.index("/* 4. Canonical log"), PIPELINE.index("/* 5. Automation"))

    def test_automation_precedes_presentation(self):
        """
        The rule this whole milestone exists for. Hiding a line is a display
        decision, not a fact about the game.

        """
        self.assertLess(PIPELINE.index("/* 5. Automation"), PIPELINE.index("/* 6. Presentation"))

    def test_announcements_come_after_presentation_but_independently(self):
        self.assertLess(PIPELINE.index("/* 6. Presentation"), PIPELINE.index("/* 7. Announcement"))


class TestOnlyOneThingWritesState(TestCase):
    """
    PIPE-002 enforced at registration, not by convention.

    """

    def test_the_writing_stages_refuse_observers(self):
        self.assertIn('WRITING_STAGES = ["state", "log"]', PIPELINE)
        self.assertIn("does not take", PIPELINE)

    def test_an_unknown_stage_is_refused(self):
        self.assertIn("unknown stage", PIPELINE)

    def test_reader_stages_receive_a_copy(self):
        """
        The whole enforcement mechanism. A presenter that writes to what it was
        handed writes to a copy, so the record and the automation input -- both
        already past -- are untouched. This is cheaper and far more reliable
        than trusting every downstream author to remember not to.

        """
        self.assertIn("function copyFor", PIPELINE)
        for stage in ("automation", "presentation", "announce"):
            self.assertIn('runStage("%s", copyFor(event))' % stage, PIPELINE)

    def test_no_reader_stage_receives_the_canonical_object(self):
        self.assertNotIn('runStage("presentation", event)', PIPELINE)
        self.assertNotIn('runStage("automation", event)', PIPELINE)


class TestFailureIsContained(TestCase):
    """
    One broken observer must not take the rest with it.

    A third-party widget that throws should cost its own rendering, not the
    player's announcements -- otherwise a defect in a decorative panel silently
    disables an accessibility feature somebody depends on.

    """

    def test_observers_run_inside_a_guard(self):
        start = PIPELINE.index("function runStage")
        window = PIPELINE[start : start + 800]
        self.assertIn("try {", window)
        self.assertIn("catch (err)", window)

    def test_a_failure_is_reported_rather_than_swallowed(self):
        self.assertIn("stats.failures", PIPELINE)
        self.assertIn("onError", PIPELINE)


class TestTheCanonicalLog(TestCase):
    """A.11, A.12, RULE-001."""

    def test_the_original_text_is_kept(self):
        self.assertIn("originalText", LOG)

    def test_readers_get_copies(self):
        """
        A reader that could mutate the record by holding a reference will
        eventually do so, and the bug would be untraceable: the record would
        simply be wrong, with nothing to say when it changed.

        """
        self.assertIn("function copy(event)", LOG)
        self.assertIn("events.map(function (event) { return copy(event); })", LOG)

    def test_the_log_is_bounded(self):
        self.assertIn("MAX_EVENTS", LOG)
        self.assertIn("events.length > limit", LOG)

    def test_dropped_events_are_counted_not_silently_discarded(self):
        """
        A player who scrolls to the top of their history is entitled to know
        the history does not start there.

        """
        self.assertIn("dropped", LOG)
        self.assertIn("droppedCount", LOG)

    def test_ids_are_not_reused_after_a_clear(self):
        """
        Reusing an id would let a stale reference resolve to a different event,
        which is worse than a gap in the numbering.

        """
        start = LOG.index("function clear()")
        window = LOG[start : start + 400]
        self.assertNotIn("nextId = 1", window)

    def test_every_category_in_the_spec_is_supported(self):
        for category in (
            "room",
            "movement",
            "tell",
            "chat",
            "combat",
            "system",
            "resource",
            "effect",
            "inventory",
            "target",
            "command",
            "media",
        ):
            self.assertIn('"%s"' % category, LOG)

    def test_an_unknown_category_is_kept_as_other(self):
        """An unrecognised event is still something that happened."""
        self.assertIn("CATEGORIES.indexOf(entry.category) === -1", LOG)


class TestTheShellUsesThePipeline(TestCase):
    """
    Wiring, not just existence. A pipeline nothing routes through documents an
    order rather than enforcing one.

    """

    def test_text_is_ingested_rather_than_rendered_directly(self):
        start = SHELL.index('emitter.on("text"')
        window = SHELL[start : start + 700]
        self.assertIn("pipeline.ingest(", window)

    def test_sync_is_ingested(self):
        start = SHELL.index("emitter.on(AETOS_MSG.SYNC")
        window = SHELL[start : start + 900]
        self.assertIn("pipeline.ingest(", window)

    def test_triggers_observe_the_automation_stage(self):
        start = SHELL.index('pipeline.observe("automation"')
        window = SHELL[start : start + 900]
        self.assertIn("triggers.onText", window)
        self.assertIn("triggers.onState", window)

    def test_the_console_observes_the_presentation_stage(self):
        """
        Located by its own body rather than by being the first presentation
        observer -- M17 added a second one for the history widget, and an
        index-based assertion silently started testing the wrong thing.

        """
        needle = 'pipeline.observe("presentation", function (event) {'
        self.assertIn(needle, SHELL)
        start = SHELL.index(needle)
        # Bounded by the next observer registration rather than by a character
        # count. A fixed window has now been wrong twice in this file as the
        # body grew -- once when M17 added a second observer, once when E2 added
        # a comment. A landmark cannot drift.
        end = SHELL.index("if (capture) {", start)
        self.assertIn("consoleWidget.append", SHELL[start:end])

    def test_triggers_see_canonical_text(self):
        """
        Not the displayed text. A trigger must not fail because the player
        chose to hide the line it was watching for.

        """
        start = SHELL.index('pipeline.observe("automation"')
        window = SHELL[start : start + 900]
        self.assertIn("event.originalText", window)

    def test_the_console_still_works_without_the_pipeline_module(self):
        """
        Losing the ordering guarantee is bad. Losing the game output is worse.

        """
        start = SHELL.index('emitter.on("text"')
        window = SHELL[start : start + 700]
        self.assertIn("} else {", window)
        self.assertIn("consoleWidget.append(payload)", window)
