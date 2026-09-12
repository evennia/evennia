"""
Tests for M21 -- the developer inspector.

Addendum C.18.

The hard rule is one sentence: *"It MUST NOT become a general-purpose arbitrary
server-object browser."* Most of what is asserted here is that boundary, because
the rest of the milestone is assembly -- capture, replay, validation and the
diagnostic report all shipped earlier, and what M21 adds is somewhere to find
them.

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

    Args:
        source (str): JavaScript source.
        signature (str): The line to start at.
        until (str): A later landmark that ends the window.

    Returns:
        str: The slice between them.

    """
    start = source.index(signature)
    return source[start : source.index(until, start)]


INSPECTOR = _read("developer/inspector.js")
SHELL = _read("aetos.js")


class TestItIsNotAnObjectBrowser(TestCase):
    """
    C.18's one prohibition.

    An inspector that could fetch arbitrary objects would be a
    privilege-escalation surface shipped to every player, in a client whose whole
    security posture is that it asks for nothing the game did not offer.

    """

    def test_it_never_sends_anything_to_the_server(self):
        code = _code_only(INSPECTOR)
        for forbidden in (
            "Evennia.msg",
            "dispatcher",
            "sendCommand",
            "fetch(",
            "XMLHttpRequest",
            "WebSocket",
            "sendBeacon",
        ):
            self.assertNotIn(forbidden, code, "inspector.js uses %r" % forbidden)

    def test_it_offers_no_query_or_lookup(self):
        """
        No text field, no dbref box, no path that turns curiosity into a request
        the game did not expect.

        """
        code = _code_only(INSPECTOR)
        for forbidden in ("dbref", "search(", "query"):
            self.assertNotIn(forbidden, code, "inspector.js offers %r" % forbidden)

        # The one input is the replay file picker, which reads a local file the
        # developer chose. The rule is about fields that *interrogate the game*,
        # and a first draft of this test forbade `createElement("input")`
        # outright -- which would have failed a control that asks the game
        # nothing at all. Assert the type instead.
        inputs = re.findall(r"picker\.type = \"(\w+)\"", code)
        self.assertEqual(inputs, ["file"])
        self.assertNotIn('type = "text"', code)

    def test_it_reads_only_what_the_client_already_has(self):
        """
        Store, registry, canonical log, diagnostics. Every one of them is
        client-side state that arrived because the game chose to send it.

        """
        code = _code_only(INSPECTOR)
        accessors = set(re.findall(r"settings\.(\w+)", code))
        allowed = {
            "store",
            "registry",
            "layout",
            "canonicalLog",
            "diagnostics",
            "capture",
            "replay",
            "dialog",
            "announce",
            "openDiagnostics",
            "validateAll",
        }
        self.assertEqual(
            accessors - allowed,
            set(),
            "the inspector reads services it should not: %s" % sorted(accessors - allowed),
        )

    def test_it_cannot_reach_the_players_private_data(self):
        """
        Notes, macros, relationship tags and accessibility preferences live in
        IndexedDB, not the store -- so there is no path, and nothing to filter.
        The same "excluded by construction" property the diagnostic report has
        (E5).

        """
        code = _code_only(INSPECTOR)
        for forbidden in (
            "notes",
            "macros",
            "aliases",
            "relationships",
            "preferences",
            "storage",
            "reminders",
        ):
            self.assertNotIn("settings." + forbidden, code, "the inspector reads %r" % forbidden)


class TestItSaysWhatIsMissingAndWhy(TestCase):
    """
    The difference between "your game exposes none" and "Aetos cannot do that
    yet" sends a developer to completely different places.

    """

    def test_absent_bindings_are_explained_not_shown_empty(self):
        body = _function_body(INSPECTOR, "function bindingsSection()", "function widgetsSection")
        self.assertIn("Not implemented", body)
        self.assertIn("D-track", body)

    def test_ungated_providers_name_the_setting(self):
        body = _function_body(INSPECTOR, "function providersSection()", "function bindingsSection")
        self.assertIn("AETOS_DIAGNOSTICS = True", body)

    def test_a_provider_that_cannot_describe_itself_is_surfaced(self):
        """
        Precisely what an inspector exists for.

        """
        body = _function_body(INSPECTOR, "function providersSection()", "function bindingsSection")
        self.assertIn("diagnostics.error", body)

    def test_withheld_widgets_name_what_they_needed(self):
        """
        A widget that never appeared did not fail -- it was withheld because the
        game does not expose what it needs. Those look identical from outside,
        and this is the line that tells them apart.

        """
        body = _function_body(INSPECTOR, "function widgetsSection()", "function stateSection")
        self.assertIn("Withheld", body)
        self.assertIn("requiredCapabilities", body)

    def test_switched_off_widgets_are_listed(self):
        """
        A failed widget's own panel says so, but only if you happen to be
        looking at that panel. M22 made widgets fail in isolation; this is
        where you find out that one did.

        """
        body = _function_body(INSPECTOR, "function widgetsSection()", "function stateSection")
        self.assertIn("disabledWidgets()", body)
        self.assertIn("Switched off after failing", body)

    def test_a_missing_handshake_is_called_out(self):
        body = _function_body(INSPECTOR, "function connectionSection()", "function manifestSection")
        self.assertIn("may not have Aetos installed", body)

    def test_dropped_events_are_reported(self):
        """
        A developer wondering why an old event is missing has usually hit the
        cap rather than a bug, and nothing else says so.

        """
        body = _function_body(INSPECTOR, "function eventsSection()", "function errorsSection")
        self.assertIn("droppedCount()", body)
        self.assertIn("over the cap", body)


class TestItSummarisesRatherThanDumps(TestCase):
    """
    "resources: 3 items" answers the question a developer has. Forty lines of
    JSON does not.

    """

    def test_state_is_reported_by_shape(self):
        body = _function_body(INSPECTOR, "function stateSection()", "function eventsSection")
        self.assertIn("items.length", body)
        self.assertIn("slots", body)

    def test_errors_are_counted_not_pasted(self):
        """
        Repeating stack traces here would make the panel a wall of them on
        exactly the games that most need reading.

        """
        body = _code_only(
            _function_body(INSPECTOR, "function errorsSection()", "function validationSection")
        )
        self.assertIn("errorCount()", body)
        # Comments stripped: the function explains that it does not paste stack
        # traces, so a bare search fails it for saying so. Twelfth instance.
        self.assertNotIn("error.stack", body)
        self.assertNotIn(".stack", body)

    def test_recent_events_are_counted_by_category(self):
        body = _function_body(INSPECTOR, "function eventsSection()", "function errorsSection")
        self.assertIn("counts[event.category]", body)
        self.assertNotIn("originalText", body)


class TestOneBrokenSectionCostsOnlyItself(TestCase):
    """
    An inspector that fails entirely because the map is malformed is useless at
    precisely the moment somebody is inspecting a malformed map.

    """

    def test_each_section_is_built_inside_a_guard(self):
        body = _function_body(INSPECTOR, "function inspect()", "function toText")
        self.assertIn("try {", body)
        self.assertIn("Could not read", body)

    def test_the_report_is_data_before_it_is_a_panel(self):
        """
        Separated so it can be tested, read from the console, and -- the reason
        that matters -- so the panel cannot show something the data does not
        contain.

        """
        self.assertIn("function inspect()", INSPECTOR)
        self.assertIn("function toText()", INSPECTOR)
        body = _function_body(INSPECTOR, "function open()", "function toggleCapture")
        self.assertIn("var report = inspect();", body)


class TestTheRegistryTrap(TestCase):
    """
    The registry is built inside a branch that runs after the inspector is
    created, so a value captured at creation would be null forever.

    Fifth instance of this family in the client; E5 documented it after losing
    an afternoon to `diagnostics.widgets = [...]` doing nothing.

    """

    def test_the_registry_is_populated_before_the_inspector_is_created(self):
        """
        The ordering that makes passing it directly correct.

        The first version handed it over later through a setter, assuming the
        inspector came first. It did not -- the call sat six hundred lines
        *above* the creation, `var` hoisting made `inspector` undefined there,
        and my own defensive guard skipped it in silence. The panel reported
        "Registry: not available" forever and nothing errored.

        """
        self.assertLess(
            SHELL.index("registry = window.AetosWidgets.createRegistry()"),
            SHELL.index("window.AetosInspector.create({"),
            "the inspector is created before the registry is built",
        )

    def test_the_registry_is_passed_directly(self):
        body = _function_body(SHELL, "window.AetosInspector.create({", "var palette =")
        self.assertIn("registry: registry", body)
        self.assertNotIn("registry: null", body)

    def test_there_is_no_late_handover_to_get_wrong(self):
        self.assertNotIn("setRegistry", SHELL)
        self.assertNotIn("setRegistry", INSPECTOR)


class TestReachability(TestCase):
    """
    A.97, and the reason this milestone exists at all: a developer debugging
    "why is my health bar empty" was expected to know `Aetos.diagnostics.build()`
    exists.

    """

    def test_the_module_is_loaded(self):
        template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("developer/inspector.js", template)

    def test_it_is_in_the_palette(self):
        self.assertIn('"developer.inspect"', SHELL)

    def test_it_gathers_the_actions_that_already_existed(self):
        body = _function_body(INSPECTOR, "var actions = [];", "dialog.open({")
        self.assertIn("Diagnostic report", body)
        self.assertIn("Validate automation", body)
        self.assertIn("Capture this session", body)

    def test_each_action_hides_when_its_subsystem_is_absent(self):
        """
        Rather than offering a button that then explains it cannot work.

        """
        body = _function_body(INSPECTOR, "var actions = [];", "dialog.open({")
        self.assertIn("if (settings.openDiagnostics)", body)
        self.assertIn("if (settings.validateAll)", body)
        self.assertIn("if (settings.capture)", body)

    def test_capture_warns_that_it_includes_game_text(self):
        """
        Capture records what was said. A developer about to share a capture
        should know that before they start, not after.

        """
        body = _function_body(INSPECTOR, "function toggleCapture()", "return {")
        self.assertIn("review it before sharing", body)

    def test_the_panel_uses_real_headings(self):
        """
        So a screen reader can jump between sections rather than reading nine
        lists in sequence.

        """
        body = _function_body(INSPECTOR, "function open()", "function toggleCapture")
        self.assertIn('createElement("h3")', body)

    def test_it_states_its_own_limits_to_the_reader(self):
        body = _function_body(INSPECTOR, "function open()", "function toggleCapture")
        self.assertIn("cannot ask your game for anything", body)


class TestC18Coverage(TestCase):
    """
    C.18 enumerates what the inspector exposes. Each is either a section or an
    action, and this is the checklist.

    """

    def test_every_named_subject_is_present(self):
        block = INSPECTOR[INSPECTOR.index("var SECTIONS = [") :]
        block = block[: block.index("];")]
        sections = set(re.findall(r'"(\w+)"', block))
        for required in (
            "manifest",
            "providers",
            "bindings",
            "widgets",
            "state",
            "events",
            "errors",
            "validation",
        ):
            self.assertIn(required, sections, "C.18 names %r" % required)

    def test_the_three_actions_are_reachable(self):
        """
        Generate a diagnostic report, capture a session, replay a session.

        Replay is reached from the diagnostic tooling rather than duplicated
        here; the other two are buttons on the panel.

        """
        self.assertIn("openDiagnostics", INSPECTOR)
        self.assertIn("function toggleCapture()", INSPECTOR)
        self.assertIn("function loadReplay()", INSPECTOR)

    def test_capture_and_replay_finally_have_palette_entries(self):
        """
        They were built at E1 and reachable only as `Aetos.capture` from the
        console, which is to say reachable by their author. C.18 lists both as
        things the inspector exposes, and writing that test is what found it.

        """
        for command in (
            '"developer.capture"',
            '"developer.capture.save"',
            '"developer.replay"',
            '"developer.inspect"',
        ):
            self.assertIn(command, SHELL, "no palette entry for %s" % command)

    def test_saving_a_capture_warns_about_its_contents(self):
        """
        A capture holds what was said. That warning belongs at the moment of
        saving, not buried in a note somewhere.

        """
        body = _function_body(INSPECTOR, "function downloadCapture()", "function loadReplay")
        self.assertIn("read it before sending it", body)

    def test_replaying_warns_that_it_replaces_the_session(self):
        body = _function_body(INSPECTOR, "function loadReplay()", "return {")
        self.assertIn("will be replaced", body)

    def test_a_capture_is_loaded_from_a_local_file(self):
        body = _function_body(INSPECTOR, "function loadReplay()", "return {")
        self.assertIn('picker.type = "file"', body)
        for forbidden in ("fetch(", "XMLHttpRequest"):
            self.assertNotIn(forbidden, body)

    def test_every_section_list_is_keyboard_scrollable(self):
        """
        Any of these can grow tall enough to scroll, and a scrolling region
        outside the tab order cannot be scrolled by keyboard at all.

        Fourth instance of this defect in the client, and the fourth found by
        axe rather than by reading the code.

        """
        body = _function_body(INSPECTOR, "function open()", "function toggleCapture")
        self.assertIn('list.setAttribute("tabindex", "0")', body)
        self.assertIn('list.setAttribute("aria-label", section.title)', body)

    def test_the_section_lists_keep_their_list_semantics(self):
        """
        A role on the <ul> would orphan every row. A7 made that mistake.

        """
        body = _code_only(_function_body(INSPECTOR, "function open()", "function toggleCapture"))
        self.assertNotIn('list.setAttribute("role"', body)
