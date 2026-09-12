"""
Tests for E1 -- developer capture and replay.

Addendum C.12 and C.13.

Two properties matter more than the rest. A capture must never carry the
player's own data, because a capture is *meant to be shared* and a bug report
that discloses somebody's private notes is worse than the bug. And replay must
use the live seam, because a harness that exercises different code from
production tests the harness.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
DEV_DIR = JS_DIR / "developer"


def _read(path):
    """
    Read a file.

    Args:
        path (Path): File to read.

    Returns:
        str: Contents.

    """
    return path.read_text(encoding="utf-8")


CAPTURE = _read(DEV_DIR / "capture.js")
REPLAY = _read(DEV_DIR / "replay.js")
SHELL = _read(JS_DIR / "aetos.js")


class TestCaptureNeverCarriesPlayerData(TestCase):
    """
    C.12. The exclusion is structural, not a filter applied at the end.

    Capture observes the pipeline and the dispatcher, and neither of those ever
    carries browser-local data -- so there is no path by which a note could
    reach a capture file even if somebody wanted one.

    """

    def test_it_does_not_reach_into_local_stores(self):
        for forbidden in (
            "notes",
            "relationships",
            "macros",
            "aliases",
            "scripts",
            "storage",
            "preferences",
        ):
            self.assertNotIn(
                forbidden + ".",
                CAPTURE,
                "capture.js touches %s, which is browser-local data" % forbidden,
            )

    def test_credential_shaped_keys_are_redacted(self):
        """
        Belt and braces. The pipeline should never carry these, and if a game's
        provider puts one in a payload anyway it is redacted rather than
        recorded -- a developer capturing their own game should not have to
        audit their own provider before sharing a bug report.

        """
        for key in ("password", "token", "api_key", "private_key", "session_key"):
            self.assertIn(key, CAPTURE)
        self.assertIn('"<redacted>"', CAPTURE)

    def test_redaction_is_depth_limited(self):
        """
        A provider can hand back a recursive structure, and a capture that hangs
        the tab is worse than one that says it gave up.

        """
        self.assertIn("level > 8", CAPTURE)

    def test_nothing_is_recorded_until_a_developer_starts_it(self):
        """
        A client that quietly accumulated a session log would be storing game
        text nobody asked it to keep.

        """
        self.assertIn("var recording = false", CAPTURE)
        self.assertIn("if (!recording)", CAPTURE)

    def test_the_capture_says_what_it_contains(self):
        """
        A capture is meant to be handed to somebody else, and "trust me" is not
        a privacy model.

        """
        self.assertIn("function describe", CAPTURE)
        self.assertIn("excludes:", CAPTURE)
        self.assertIn("contains:", CAPTURE)


class TestCaptureFormat(TestCase):
    """C.12: versioned JSON Lines, relative milliseconds."""

    def test_the_format_is_versioned(self):
        self.assertIn("FORMAT_VERSION", CAPTURE)

    def test_the_header_is_the_first_record_not_a_wrapper(self):
        """
        Append-only, so a capture interrupted by a crashed tab is still a valid
        readable prefix rather than an unparseable half-object.

        """
        self.assertIn('kind: "meta"', CAPTURE)

    def test_times_are_relative_to_the_start(self):
        self.assertIn("function stamp", CAPTURE)
        self.assertIn("now() - startedAt", CAPTURE)

    def test_the_three_levels_exist(self):
        self.assertIn('"state", "state+text", "full"', CAPTURE)

    def test_the_default_level_is_not_full(self):
        """
        Recording everything by default means every casual capture carries game
        text the developer then has to read before sharing.

        """
        self.assertIn('DEFAULT_LEVEL = "state+text"', CAPTURE)

    def test_state_level_omits_game_text(self):
        self.assertIn('level !== "state"', CAPTURE)

    def test_the_record_count_is_bounded(self):
        self.assertIn("MAX_RECORDS", CAPTURE)

    def test_truncation_is_counted_rather_than_silent(self):
        self.assertIn("truncated", CAPTURE)


class TestReplayUsesTheLiveSeam(TestCase):
    """
    C.13, and the rule that makes replay worth having.

    """

    def test_records_go_through_the_pipeline(self):
        self.assertIn("pipeline.ingest(", REPLAY)

    def test_replay_does_not_touch_the_store_directly(self):
        """
        A second path into state would mean replay testing a code path that
        does not exist in production.

        """
        self.assertNotIn("store.applySync", REPLAY)
        self.assertNotIn("store.set", REPLAY)

    def test_replay_never_sends_a_command(self):
        """
        A capture records what a player did. Re-issuing it would act on their
        behalf against a game that has moved on.

        """
        self.assertNotIn("dispatcher", REPLAY)
        self.assertNotIn("sendCommand", REPLAY)
        self.assertIn("Surfaced, not enacted", REPLAY)

    def test_an_unknown_format_is_refused_not_guessed(self):
        """
        A misread capture produces a convincing wrong answer, and a convincing
        wrong answer during a bug hunt costs more than an honest refusal.

        """
        self.assertIn("cannot be replayed by this client", REPLAY)

    def test_a_file_without_a_header_is_refused(self):
        self.assertIn("no meta record", REPLAY)

    def test_a_malformed_line_does_not_lose_the_whole_capture(self):
        """
        A truncated file is what a crashed tab produces, and it is still worth
        replaying up to the point it stops.

        """
        start = REPLAY.index("function parseJsonl")
        window = REPLAY[start : start + 800]
        self.assertIn("catch (err)", window)
        self.assertIn("problems.push", window)

    def test_every_playback_mode_exists(self):
        """
        Asserted against the speed table rather than by searching for quoted
        strings: `instant` is a plain identifier and so appears unquoted, which
        an earlier version of this test missed while the mode worked fine.

        """
        block = REPLAY[REPLAY.index("var SPEEDS = {") : REPLAY.index("function parseJsonl")]
        for mode in ("1x", "2x", "4x", "instant"):
            self.assertIn(mode, block, "no %r playback speed" % mode)
        self.assertIn("function step", REPLAY)

    def test_step_mode_advances_exactly_one_record(self):
        """
        Step matters more than it looks: watching one event at a time is how
        you find that two announcements collapsed into one, or that a widget
        updated before the state it was reading. Neither is visible at speed.

        """
        start = REPLAY.index("function step()")
        window = REPLAY[start : start + 400]
        self.assertIn("index += 1", window)

    def test_the_clock_is_injectable(self):
        """
        A test that depends on Date.now() is a test that fails on a slow
        morning.

        """
        self.assertIn("settings.now ||", REPLAY)
        self.assertIn("settings.schedule ||", REPLAY)


class TestTheShellWiresThem(TestCase):
    """Wiring, not just existence."""

    def test_capture_observes_the_announce_stage(self):
        """
        Last in the pipeline, so a capture records what the client decided
        rather than what arrived. The bugs worth reproducing live in the second
        thing.

        A14 gave that stage a second observer -- the one that hands game output
        to the announcer, which had been missing since E0 -- so this can now
        assert what it always meant: capture is registered **last**, after
        everything else that stage does. Anchoring on the first observer was
        only ever right while there was exactly one.

        """
        observers = [
            index
            for index in range(len(SHELL))
            if SHELL.startswith('pipeline.observe("announce"', index)
        ]
        self.assertGreaterEqual(len(observers), 2, "the announcer observer is missing")

        window = SHELL[observers[-1] : observers[-1] + 300]
        self.assertIn("capture.recordInbound", window)

        # And nothing else is registered after it.
        self.assertNotIn('pipeline.observe("announce"', SHELL[observers[-1] + 30 :])

    def test_outbound_is_recorded_at_the_single_convergence_point(self):
        """
        C.11: keyboard, button, macro, route, script, voice and AAC all
        converge on `sendCommand`. Recording at each call site instead would
        eventually miss one, and a capture missing one command cannot reproduce
        the session.

        Bounded by the end of the function rather than by a character count.
        The count version broke at M24, when a "not connected" guard was added
        above the recording and pushed it past the window -- failing while the
        property it checks was still true. The M17 rule applies: anchor on a
        landmark, never on a length.

        """
        start = SHELL.index("function sendCommand(text)")
        window = SHELL[start : SHELL.index("/* --- Local actions", start)]
        self.assertIn("capture.recordOutbound(text)", window)

    def test_connection_changes_are_recorded(self):
        self.assertIn("capture.recordConnection(state)", SHELL)

    def test_replay_is_given_the_pipeline(self):
        self.assertIn("window.AetosReplay.create({ pipeline: pipeline })", SHELL)
