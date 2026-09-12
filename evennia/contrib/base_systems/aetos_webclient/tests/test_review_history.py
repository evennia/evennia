"""
Tests for M17 -- flood control, Review Mode and event history.

Addendum A.16, A.17, A.18, A.76.

The theme is that a client which speaks everything is as unusable as one that
speaks nothing, and that the fix is never to silently drop things. Every
suppression here is counted and reported.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    protocol,
    state,
)

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


ANNOUNCER = _read("accessibility/announcer.js")
REVIEW = _read("events/review.js")
HISTORY = _read("history.js")
SHELL = _read("aetos.js")


class TestCategoriesComeFromTheGame(TestCase):
    """
    A.76, and the C.6 ambiguity rule applied to text.

    Aetos cannot tell a tell from a shout by reading the words, and a client
    that guessed would be wrong on every game that phrases things its own way.
    So the game says, or the event is "other".

    """

    def test_there_is_a_message_for_it(self):
        self.assertTrue(hasattr(protocol, "MSG_EVENT"))
        self.assertEqual(protocol.MSG_EVENT, "aetos_event")

    def test_the_helper_exists(self):
        self.assertTrue(callable(state.push_event))

    def test_an_unknown_category_becomes_other_rather_than_failing(self):
        """A typo should cost the categorisation, not the message."""
        source = Path(state.__file__).read_text(encoding="utf-8")
        self.assertIn("category not in EVENT_CATEGORIES", source)
        self.assertIn('category = "other"', source)

    def test_importance_is_advisory(self):
        source = Path(state.__file__).read_text(encoding="utf-8")
        self.assertIn("importance_hint", source)
        self.assertIn("Advisory", source)

    def test_both_plain_and_markup_forms_travel(self):
        """
        Automation matches on what the player reads, not on the markup they
        never see.

        """
        source = Path(state.__file__).read_text(encoding="utf-8")
        self.assertIn('"plain"', source)

    def test_the_client_knows_the_message(self):
        self.assertIn('EVENT: "aetos_event"', SHELL)
        self.assertIn("AETOS_MSG.EVENT", SHELL)

    def test_the_client_never_infers_a_category_from_text(self):
        """
        The rule that keeps this genre-neutral. No regex over game output
        deciding what channel it belongs to.

        """
        for module in ("aetos.js", "events/review.js", "history.js"):
            source = _read(module)
            for guess in ("/tell/", "/says/", "/whispers/", '"shout"'):
                self.assertNotIn(guess, source, "%s guesses at categories" % module)


class TestFloodControl(TestCase):
    """
    A.16.

    A browser cannot know when a screen reader has finished speaking, so Aetos
    counts instead of synchronising. What is dropped during a burst is the
    reading aloud of each line -- never the line itself.

    """

    def test_the_constants_are_in_one_place(self):
        """
        Starting values, not findings. They should be tunable from user testing
        rather than hunted for across the file.

        """
        self.assertIn("var FLOOD = {", ANNOUNCER)
        for key in ("threshold", "sustainMs", "summaryMs", "windowMs"):
            self.assertIn(key, ANNOUNCER)

    def test_a_burst_must_be_sustained_before_aggregating(self):
        """
        Without this, one busy moment would trigger summarising.

        """
        self.assertIn("sustainMs", ANNOUNCER)
        self.assertIn("(moment - burstStartedAt) >= FLOOD.sustainMs", ANNOUNCER)

    def test_tells_are_never_aggregated(self):
        """
        Someone speaking to you directly is the thing you most need to hear
        during a fight, and exactly what a naive rate limiter would bury.

        """
        self.assertIn('NEVER_AGGREGATE = ["tell", "connection", "session"]', ANNOUNCER)

    def test_critical_and_important_are_never_aggregated(self):
        self.assertIn('priority !== "critical" && priority !== "important"', ANNOUNCER)

    def test_suppressed_events_are_counted_not_discarded(self):
        self.assertIn("suppressedTotal", ANNOUNCER)
        self.assertIn("suppressed[category]", ANNOUNCER)

    def test_the_first_summary_waits_for_a_real_count(self):
        """
        An earlier version tripped the summary interval on the very first
        suppressed event and announced "Heavy activity. 1 chat event.", which
        is both useless and faintly absurd.

        """
        self.assertIn("if (!aggregating) {", ANNOUNCER)
        self.assertIn("lastSummaryAt = moment;", ANNOUNCER)

    def test_the_window_is_pruned_before_it_is_counted(self):
        """
        An earlier version pushed the current event first and then tested for
        an empty window, which could never be true -- so a burst never formally
        ended, and a message minutes later was still reported as heavy
        activity.

        """
        self.assertIn("var quiet = recent.length === 0;", ANNOUNCER)
        index_prune = ANNOUNCER.index("while (recent.length && recent[0]")
        index_push = ANNOUNCER.index("recent.push(moment);")
        self.assertLess(index_prune, index_push)

    def test_the_end_of_burst_summary_is_not_overwritten(self):
        """
        A live region only announces its latest text. Writing the summary and
        then the message that ended the burst would silently lose the summary,
        so it is carried and prefixed onto that message instead.

        """
        self.assertIn("var settledSummary = null;", ANNOUNCER)
        self.assertIn('settledSummary + " " + message', ANNOUNCER)


class TestReviewMode(TestCase):
    """A11Y-REV-001, A.17, A.18."""

    def test_entering_pauses_announcements(self):
        self.assertIn("announcer.beginReview", REVIEW)

    def test_leaving_summarises_rather_than_replaying(self):
        """
        Reading seventeen held announcements in a row is worse than the
        interruption they were held to avoid.

        """
        self.assertIn("occurred while reviewing", REVIEW)
        # Asserted from what `exit` does, not by searching for the word
        # "replay". The prose above the code legitimately says "summarise
        # rather than replay", and a test that fails on a file describing
        # itself is a bad test -- the third time this project has written one.
        start = REVIEW.index("function exit()")
        end = REVIEW.index("function toggle()")
        body = REVIEW[start:end]
        self.assertIn("byCategory", body)
        self.assertIn("missed.length", body)
        # Exactly one announcement leaves `exit`: the summary. The held events
        # are counted and returned, never spoken one by one.
        self.assertEqual(body.count("announce("), 2, "exit() announces per event")

    def test_the_summary_counts_what_happened_not_what_would_be_spoken(self):
        """
        Taken from the canonical log rather than the announcement queue, so a
        player who muted combat still learns a fight occurred.

        """
        self.assertIn("event.sequence > enteredAtSequence", REVIEW)

    def test_critical_still_gets_through(self):
        """
        Review is not a mute. Someone reading their combat log should still be
        told the connection dropped, because everything they are reading just
        became potentially stale.

        """
        self.assertIn('priority !== "critical"', ANNOUNCER)

    def test_navigation_is_by_channel(self):
        for channel in ("tell", "chat", "combat", "system"):
            self.assertIn('"%s"' % channel, REVIEW)
        self.assertIn("function previous", REVIEW)
        self.assertIn("function next", REVIEW)

    def test_running_out_of_events_says_so(self):
        """
        A key that appears not to work is worse than one that explains itself.

        """
        self.assertIn("Start of history.", REVIEW)
        self.assertIn("No ", REVIEW)

    def test_search_reads_canonical_text(self):
        """
        A player searching for something they saw must find it even if a
        display rule has since hidden it -- which is exactly when searching
        matters.

        It reads the plain rendering of the canonical event rather than the
        markup. Searching the markup meant a query for "span" matched every
        coloured line while a word split by a colour change matched nothing --
        and the announcement read the tags aloud.

        """
        self.assertIn("readable(event).toLowerCase()", REVIEW)
        self.assertIn("event.plainText === undefined ? event.originalText", REVIEW)

    def test_it_has_a_shortcut_and_palette_entries(self):
        self.assertIn('id: "review.toggle"', SHELL)
        self.assertIn('defaultBinding: "Ctrl+Shift+R"', SHELL)
        self.assertIn('"review.prev.tell"', SHELL)

    def test_the_shortcut_avoids_the_browser_reload_key(self):
        """
        Ctrl+R reloads the page, which would lose the very session being
        reviewed.

        """
        self.assertNotIn('defaultBinding: "Ctrl+R"', SHELL)


class TestHistoryWidget(TestCase):
    """A.10, A.12, A.18."""

    def test_it_reads_the_canonical_log_not_the_console(self):
        self.assertIn("log.all()", HISTORY)
        self.assertNotIn("consoleWidget", HISTORY)

    def test_it_does_not_announce(self):
        self.assertIn('"aria-live", "off"', HISTORY)
        self.assertIn("liveUpdates: true", HISTORY)

    def test_it_is_paged_rather_than_virtualised(self):
        """
        A.12 forbids virtualisation that evicts a focused or reviewed node. The
        simplest way to honour that is not to virtualise at all.

        """
        self.assertIn("PAGE_SIZE", HISTORY)
        self.assertNotIn("IntersectionObserver", HISTORY)

    def test_paging_states_where_you_are(self):
        """
        So a player knows there is more before they go looking for it.

        """
        self.assertIn('"Page " + (page + 1) + " of "', HISTORY)

    def test_the_channel_is_a_word_not_a_colour(self):
        """
        The player most likely to be reading history rather than the console is
        the one least able to rely on a tint.

        """
        self.assertIn("channel.textContent = event.category", HISTORY)

    def test_the_search_field_has_a_label(self):
        self.assertIn("aetos-visually-hidden", HISTORY)
        self.assertIn('"for", "aetos-history-search"', HISTORY)

    def test_typing_does_not_rebuild_the_search_field(self):
        """
        A11Y-FOCUS-005, and the lesson A3 learned the hard way.

        """
        start = HISTORY.index('input.addEventListener("input"')
        end = HISTORY.index("FILTERS.forEach", start)
        handler = HISTORY[start:end]
        self.assertIn("refresh()", handler)
        self.assertNotIn("createElement", handler)

    def test_refresh_is_throttled(self):
        """
        During a flood the log grows faster than a browser can usefully redraw
        a hundred rows, and a history that stutters during a fight is one
        nobody reads during a fight.

        """
        self.assertIn("throttledRefresh", HISTORY)
        self.assertIn("250", HISTORY)

    def test_it_is_driven_by_events_not_by_state(self):
        """
        Subscribing to a store section would redraw when *state* changed rather
        than when an *event* arrived. Correlated, but not the same thing.

        """
        self.assertIn("registerRefresh", HISTORY)
        self.assertIn("historyRefreshers", SHELL)
        start = SHELL.index('pipeline.observe("presentation", function () {')
        window = SHELL[start : start + 300]
        self.assertIn("historyRefreshers", window)

    def test_the_scrolling_rows_region_is_keyboard_reachable(self):
        """
        Arrow keys scroll whatever has focus, so a scrolling region outside the
        tab order cannot be scrolled by keyboard at all: the player can see
        there is more and has no way to reach it.

        Third instance of this defect in the client, and the third caught by
        axe rather than by anyone reading the code -- it is invisible to
        whoever tests with a mouse wheel. A focusable region also needs a name,
        or it is announced as an unlabelled group.

        """
        start = HISTORY.index('rows.className = "aetos-history__rows"')
        end = HISTORY.index("aetos-history__pager", start)
        window = HISTORY[start:end]
        self.assertIn('rows.setAttribute("tabindex", "0")', window)
        self.assertIn('"aria-label", "Event history"', window)
