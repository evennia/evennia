"""
Tests for A5 -- the cognitive and orientation layer.

Addendum A.36 through A.48.

Most of these assert an *absence*. The layer's whole value rests on a player
being able to trust what it tells them, so the interesting properties are the
things it refuses to do: guess at intent, invent a reminder, build a trail out
of commands that failed, or nag somebody who asked for quiet.

Following the M17 rule, every source assertion anchors on something that cannot
appear in prose -- an access, a call or a literal -- because these modules
necessarily *describe* the things they do not do.

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


def _code_only(source):
    """
    Strip comments, leaving only what executes.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source without comments.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


def _function_body(source, signature, until):
    """
    Slice one function out of a module.

    Bounded by a following landmark rather than a character count, so the
    window cannot silently grow past the function as the file changes.

    Args:
        source (str): JavaScript source.
        signature (str): The `function name(` line to start at.
        until (str): A later landmark that ends the window.

    Returns:
        str: The slice between them.

    """
    start = source.index(signature)
    end = source.index(until, start)
    return source[start:end]


ORIENTATION = _read("accessibility/orientation.js")
COGNITIVE = _read("accessibility/cognitive.js")
SHELL = _read("aetos.js")
SETTINGS = _read("settings.js")
TEMPLATE = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
    encoding="utf-8"
)


class TestNoIntentionInference(TestCase):
    """
    A11Y-COG-002. The rule the whole layer rests on.

    A client that guessed at intent would be confidently wrong at exactly the
    moment somebody was relying on it -- and a wrong answer delivered with
    certainty costs the player the time to discover it was wrong plus the trust
    they had in the feature.

    """

    def test_the_summary_never_narrates_a_goal(self):
        """
        "Looked at Captain Renn" is a fact. "You were investigating Captain
        Renn" is a story, and a client that told it would eventually tell the
        wrong one.

        """
        body = _function_body(ORIENTATION, "function reorient()", "function speakReorientation")
        for narration in (
            "you were trying",
            "you wanted",
            "your objective",
            "your goal",
            "looks like you",
        ):
            self.assertNotIn(narration, body.lower(), "reorient() narrates: %r" % narration)

    def test_the_section_titles_are_all_factual(self):
        """
        Every heading names something observable.

        """
        body = _function_body(ORIENTATION, "function reorient()", "function speakReorientation")
        titles = re.findall(r'section\("([^"]+)"', body)
        self.assertIn("Current location", titles)
        self.assertIn("You recently sent", titles)
        for title in titles:
            self.assertNotIn("trying", title.lower())
            self.assertNotIn("goal", title.lower())

    def test_recent_commands_are_reported_verbatim(self):
        """
        Not summarised, not categorised, not interpreted. What you sent.

        """
        body = _function_body(ORIENTATION, "function observeCommand", "function reorient")
        self.assertIn("recentCommands.push(command)", body)


class TestTheTrailFollowsOutcomesNotIntentions(TestCase):
    """
    A11Y-COG-003. A player who typed "north" into a wall has not moved.

    """

    def test_breadcrumbs_come_from_room_changes(self):
        body = _function_body(ORIENTATION, "function observeRoom", "var pendingDirection")
        self.assertIn("breadcrumbs.push(entry)", body)
        self.assertIn("room.id === lastRoomId", body)

    def test_a_command_alone_never_adds_a_breadcrumb(self):
        body = _function_body(ORIENTATION, "function observeCommand", "function reorient")
        self.assertNotIn("breadcrumbs.push", body)

    def test_the_shell_observes_the_store_not_the_payload(self):
        """
        The store is what everything else reads. A breadcrumb taken from
        anywhere else could describe a room the rest of the client does not
        believe in.

        """
        body = _function_body(SHELL, "function observeLocation()", "// The single outbound seam")
        self.assertIn('store.get("room")', body)
        self.assertIn("orientation.observeRoom(room)", body)

    def test_it_is_called_on_both_sync_paths(self):
        """
        With the pipeline and without it. A fallback path that skipped this
        would leave the trail frozen on any install where the pipeline is off.

        """
        self.assertEqual(SHELL.count("observeLocation();"), 2)

    def test_commands_are_recorded_at_the_single_outbound_seam(self):
        """
        C.11. Keyboard, button, macro, route, script and voice alike.

        """
        body = _function_body(SHELL, "function sendCommand(text)", "/* --- Local actions")
        self.assertIn("orientation.observeCommand(text)", body)


class TestWalkBackCannotInvent(TestCase):
    """
    The ambiguity rule (C.6) applied to movement.

    """

    def test_only_unambiguous_directions_reverse(self):
        """
        "enter the portal" has no reliable inverse -- a game may have put you
        somewhere with three exits.

        """
        block = ORIENTATION[ORIENTATION.index("var INVERSE = {") :]
        block = block[: block.index("};")]
        self.assertIn('north: "south"', block)
        self.assertNotIn("enter", block)
        self.assertNotIn("portal", block)

    def test_backtracking_stops_at_the_first_ambiguous_step(self):
        body = _function_body(ORIENTATION, "function backtrack()", "function walkBack")
        self.assertIn("break;", body)

    def test_walking_back_uses_the_ordinary_queue(self):
        """
        Server authority (blueprint 2.4). Aetos is not authoritative about
        movement, and a locked door ends the walk exactly where it should.

        """
        body = _function_body(ORIENTATION, "function walkBack()", "function clear()")
        self.assertIn("settings.queueRoute(steps)", body)
        for bypass in ("Evennia.msg", "fetch(", "dispatcher"):
            self.assertNotIn(bypass, body)

    def test_the_shell_hands_it_the_route_walker(self):
        self.assertIn("queueRoute: function (steps) { return walkRoute(steps); }", SHELL)


class TestRemindersAreOnlyEverCreatedOnRequest(TestCase):
    """
    A11Y-COG-005. Aetos never invents one.

    A client that generated its own reminders would be inferring intent, which
    A11Y-COG-002 forbids, and nagging -- which for somebody who reached for a
    memory aid is actively counterproductive.

    """

    def test_every_trigger_is_a_condition_the_player_stated(self):
        block = COGNITIVE[COGNITIVE.index("var TRIGGERS = [") :]
        block = block[: block.index("];")]
        self.assertIn('"pinned"', block)
        self.assertIn('"here"', block)
        self.assertIn('"next-session"', block)

    def test_nothing_creates_an_item_except_save(self):
        """
        `save` is reachable only from the editor, which is reachable only from
        the palette. There is no other writer.

        """
        code = _code_only(COGNITIVE)
        self.assertEqual(code.count("storage.put("), 1)

    def test_completion_is_never_automatic(self):
        """
        A memory aid that marks its own items done is a memory aid you cannot
        trust.

        """
        body = _function_body(COGNITIVE, "function complete(id, done)", "/* --- Surfacing")
        self.assertIn("found.completed = done !== false", body)
        # No inspection of game state anywhere in the decision.
        self.assertNotIn("store.get", body)

    def test_a_location_reminder_surfaces_once_per_visit(self):
        """
        A reminder that repeats on every sync while the player stands in a room
        stops being a reminder and becomes an obstacle -- and the player who
        most needs the feature is the least able to tolerate that.

        """
        body = _function_body(COGNITIVE, "function observeRoom(room)", "function nextSession")
        self.assertIn("surfacedThisVisit[item.id] = true", body)
        self.assertIn("!surfacedThisVisit[item.id]", body)

    def test_leaving_the_room_clears_the_mark(self):
        """
        So returning later surfaces it again, which is what "remind me when I
        am back here" means.

        """
        body = _function_body(COGNITIVE, "function observeRoom(room)", "function nextSession")
        self.assertIn("delete surfacedThisVisit[id]", body)

    def test_next_session_reminders_are_not_fired_at_connect(self):
        """
        Arriving to a queue of announcements is exactly the kind of start that
        makes somebody close the tab. They are surfaced on request.

        """
        body = _function_body(COGNITIVE, "function nextSession()", "function resumeCard")
        self.assertNotIn("announce(", body)


class TestResumeDoesNotPresentStaleStateAsCurrent(TestCase):
    """
    A11Y-COG-004. Presenting cached state as current is how a player acts on a
    world that has moved on.

    """

    def test_unsynced_state_is_labelled(self):
        body = _function_body(COGNITIVE, "function resumeCard(synced)", "return {")
        self.assertIn('"Last known: "', body)

    def test_the_label_depends_on_a_real_sync(self):
        self.assertIn("cognitive.resumeCard(", SHELL)
        body = _function_body(SHELL, 'addCommand("session.resume"', "/* Session */")
        self.assertIn('store.get("room").name', body)


class TestNothingLeavesTheBrowser(TestCase):
    """
    Blueprint 2.3. None of this is a server-side player profile.

    """

    def test_neither_module_talks_to_the_server(self):
        for name, source in (("orientation.js", ORIENTATION), ("cognitive.js", COGNITIVE)):
            for forbidden in (
                "fetch(",
                "XMLHttpRequest",
                "sendBeacon",
                "WebSocket",
                "Evennia.msg",
                "dispatcher",
            ):
                self.assertNotIn(forbidden, source, "%s uses %r" % (name, forbidden))

    def test_reminders_are_stored_locally(self):
        self.assertIn('var NAMESPACE = "reminders"', COGNITIVE)
        storage = _read("storage.js")
        self.assertIn('"reminders"', storage)

    def test_the_privacy_panel_names_them(self):
        """
        A.75. A namespace the panel does not name is data a player cannot see
        they are storing.

        """
        self.assertIn("reminders:", SETTINGS)

    def test_the_diagnostic_report_still_cannot_carry_them(self):
        """
        C.17 lists reminders among the things a bug report must never contain,
        and A5 is the milestone that made them exist.

        """
        diagnostics = _code_only(_read("developer/diagnostics.js"))
        # Anchored on accesses, not words. "reminders" appears in the
        # user-facing `excludes` list -- the sentence promising the report does
        # not contain them -- so a bare search fails the file for documenting
        # itself. Seventh time this project has written that test.
        for probe in (
            "settings.cognitive",
            "settings.orientation",
            "settings.reminders",
            'get("reminders")',
        ):
            self.assertNotIn(probe, diagnostics, "diagnostics.js reads %r" % probe)


class TestReachability(TestCase):
    """
    A.97. A feature nobody can find is a feature that does not exist.

    """

    def test_both_modules_are_loaded(self):
        self.assertIn("accessibility/orientation.js", TEMPLATE)
        self.assertIn("accessibility/cognitive.js", TEMPLATE)

    def test_every_action_has_a_palette_entry(self):
        for command in (
            '"orientation.reorient"',
            '"orientation.trail"',
            '"orientation.walkback"',
            '"reminder.new"',
            '"reminder.list"',
            '"session.resume"',
        ):
            self.assertIn(command, SHELL, "no palette entry for %s" % command)

    def test_the_shortcut_names_its_palette_command(self):
        """
        Enforced by the shortcut manager, and asserted here because a feature
        reachable only by keystroke does not exist for anyone who does not
        already know the keystroke.

        """
        body = _function_body(SHELL, 'id: "orientation.reorient"', "});")
        self.assertIn('paletteCommand: "orientation.reorient"', body)
        self.assertIn('defaultBinding: "Ctrl+Shift+W"', body)

    def test_the_shortcut_and_the_palette_do_the_same_thing(self):
        """
        An earlier draft had the shortcut speak only, so a sighted player who
        pressed it saw nothing happen at all.

        """
        # Three callers now: the palette entry, the keyboard shortcut and the
        # swipe. All three going through one function is the point -- an
        # earlier draft had the shortcut speak without showing anything.
        self.assertEqual(SHELL.count("reorientNow();"), 3)
        self.assertIn("function reorientNow()", SHELL)

    def test_the_summary_is_shown_as_well_as_spoken(self):
        """
        "Where am I" is not only a screen reader question.

        """
        body = _function_body(SETTINGS, "function openOrientation()", "return {")
        self.assertIn('createElement("h3")', body)

    def test_the_summary_is_announced_as_important(self):
        """
        So it is heard in Quiet Mode. Somebody who asked where they are has
        asked a direct question, and quiet is about unsolicited interruption
        rather than about refusing to answer.

        """
        body = _function_body(ORIENTATION, "function speakReorientation()", "/* --- How I Got Here")
        self.assertIn('priority: "important"', body)

    def test_reminder_rows_are_individually_labelled(self):
        """
        "Delete" repeated down a list is indistinguishable when tabbed through
        out of context.

        """
        body = _function_body(SETTINGS, "function openReminders()", "function editReminder")
        self.assertIn('"aria-label", "Delete: " + item.text', body)

    def test_done_state_is_not_conveyed_by_styling_alone(self):
        body = _function_body(SETTINGS, "function openReminders()", "function editReminder")
        self.assertIn('"aria-pressed"', body)


class TestBounds(TestCase):
    """Anything that grows for the length of a session needs a ceiling."""

    def test_the_trail_is_bounded(self):
        self.assertIn("MAX_BREADCRUMBS", ORIENTATION)
        self.assertIn("breadcrumbs.length > MAX_BREADCRUMBS", ORIENTATION)

    def test_recent_commands_are_bounded(self):
        """
        Four is roughly "what I was just doing". Twenty is a transcript, which
        the player already has.

        """
        self.assertIn("recentCommands.length > RECENT_COMMANDS", ORIENTATION)

    def test_reminders_are_bounded(self):
        self.assertIn("MAX_ITEMS", COGNITIVE)
        self.assertIn("MAX_TEXT", COGNITIVE)


class TestUniversalSearch(TestCase):
    """
    A11Y-COG-006. One place to look for anything.

    Somebody who half-remembers "that thing about the manifest" should not have
    to work out *which panel* they wrote it in before they can search for it --
    reconstructing that is exactly the recall the feature exists to replace.

    """

    def test_the_palette_accepts_search_sources(self):
        palette = _read("palette.js")
        self.assertIn("function registerSource(source)", palette)
        self.assertIn("function fromSources(query)", palette)

    def test_sources_are_scored_alongside_commands(self):
        """
        Appending them would bury an exact-title match under a command that
        matched three scattered letters.

        """
        palette = _read("palette.js")
        self.assertIn("available().concat(fromSources(query))", palette)

    def test_an_empty_query_searches_no_sources(self):
        """
        An empty palette lists what the client can *do*. Dumping every note
        into it would bury the commands under the player's own data.

        """
        palette = _read("palette.js")
        body = _function_body(palette, "function fromSources(query)", "function available()")
        self.assertIn("if (!query)", body)
        self.assertIn("return [];", body)

    def test_a_broken_source_hides_itself(self):
        """
        Search that returns nothing looks identical to search that found
        nothing, so a throwing source must not empty the palette.

        """
        palette = _read("palette.js")
        body = _function_body(palette, "function fromSources(query)", "function available()")
        self.assertIn("catch (err)", body)

    def test_notes_reminders_and_history_are_all_searchable(self):
        for group in ('"Your notes"', '"Your tasks"', '"What happened"'):
            self.assertIn(group, SHELL, "no search source produces %s" % group)

    def test_the_note_snapshot_is_refreshed_when_the_palette_opens(self):
        """
        Notes live in IndexedDB and search must stay synchronous, so the shell
        keeps a snapshot. A cache that only filled at boot would be a search
        that quietly cannot see the player's most recent thought.

        """
        self.assertIn("onOpen: refreshNoteSnapshot", SHELL)
        palette = _read("palette.js")
        self.assertIn('typeof services.onOpen === "function"', palette)

    def test_a_history_hit_jumps_in_review_mode(self):
        """
        Rather than scrolling the console, so the line is reachable even when a
        display rule has since hidden it (E2).

        """
        body = _function_body(SHELL, '"What happened"', "/*\n         * Global shortcuts")
        self.assertIn("review.jumpTo(event.id)", body)


class TestComfortModes(TestCase):
    """
    A.47 and A.48. Two separate toggles, both owned by the player.

    """

    def test_focus_mode_and_quiet_mode_are_separate_preferences(self):
        """
        Wanting a calmer screen and wanting fewer interruptions are different
        needs, and somebody may want either without the other.

        """
        preferences = _read("accessibility/preferences.js")
        self.assertIn("quietMode: false", preferences)
        self.assertIn("focusMode: false", preferences)

    def test_focus_mode_follows_one_preference(self):
        """
        So it survives a reload without the shell restoring anything, and there
        is exactly one thing to read when asking whether it is on.

        """
        body = _function_body(SHELL, "function setFocusMode(on)", "function focusModeIsOn")
        self.assertIn("cognitive: { focusMode: on !== false }", body)
        self.assertNotIn("classList", body)

    def test_the_attribute_is_written_by_the_accessibility_layer(self):
        accessibility = _read("accessibility/accessibility.js")
        self.assertIn(
            'root.setAttribute("data-aetos-focus-mode", cognitive.focusMode ? "true" : "false")',
            accessibility,
        )

    def test_hidden_panels_are_removed_from_the_tab_order(self):
        """
        `display: none`, not visual hiding. A panel that is merely invisible is
        still tabbable and still read aloud, which would make Focus Mode a trap
        -- the clutter a sighted player wanted gone would remain in full for
        everyone else.

        """
        css = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")
        start = css.index('[data-aetos-focus-mode="true"] .aetos-region--sidebar')
        window = css[start : css.index("}", start)]
        self.assertIn("display: none", window)

    def test_quiet_mode_still_lets_important_announcements_through(self):
        """
        A.48. Quiet is about interruption, not information. Somebody who asked
        a direct question still gets an answer.

        A14b tightened this, and the old assertion was working against the
        docstring above it. It required `priority === "normal"` to appear in the
        quiet rule -- that is, it pinned the behaviour where quiet mode
        suppressed ordinary game output, which is information rather than
        interruption.

        That was not academic. Every line of game text arrives under the
        category `other`, which is `normal`, so quiet mode silenced the game. A
        sighted player never noticed, because the console is right there; for
        somebody listening it was total silence, because the console is
        deliberately `aria-live="off"`. Gary found it by turning a screen reader
        on and hearing nothing.

        Quiet now drops `background` -- resource ticks, inventory, media -- and
        nothing else. Combat has its own control, which is a choice a player
        makes rather than a side effect of asking for fewer interruptions.

        """
        announcer = _read("accessibility/announcer.js")
        start = announcer.index('preferenceValue("cognitive.quietMode", false)')
        window = announcer[start : announcer.index("return priority;", start)]
        self.assertIn('priority === "background"', window)
        self.assertNotIn('priority === "normal"', window)
        self.assertNotIn('priority === "important"', window)

    def test_nothing_the_game_sends_can_set_a_comfort_mode(self):
        """
        A11Y-COG-007 makes this explicit for workspace switching; the same
        reasoning applies to both comfort modes. A layout that rearranges
        itself under somebody is disorienting for everyone and disabling for
        some.

        Asserted by counting call sites: the definition and the one palette
        command. A third would mean something else is deciding.

        """
        self.assertEqual(SHELL.count("setFocusMode("), 2)
        self.assertIn("function setFocusMode(on)", SHELL)
        self.assertIn(
            'automaticWorkspaceSwitching: "never"',
            _read("accessibility/preferences.js"),
        )

    def test_both_are_reachable_from_the_palette(self):
        for command in ('"focus.toggle"', '"quiet.toggle"'):
            self.assertIn(command, SHELL)
