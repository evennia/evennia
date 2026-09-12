"""
Tests for E5 -- diagnostic reporting.

Addendum C.17.

A report is meant to be pasted into a public issue tracker, so the interesting
assertions are all about what it cannot contain -- and about the fact that it
cannot contain those things *by construction* rather than by filtering.

"""

import re
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, manifest

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
    Strip comments and the user-facing `excludes` list.

    A module that documents what it will not collect necessarily contains those
    words. Only the executable part can say what it actually reads.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments and the excludes literal removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    without_line = re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)
    # The `excludes:` array is text shown to the player, not a data access.
    return re.sub(r"excludes:\s*\[.*?\]", "", without_line, flags=re.DOTALL)


DIAGNOSTICS = _read("developer/diagnostics.js")
SETTINGS = _read("settings.js")
SHELL = _read("aetos.js")


class TestTheReportCannotCarryPrivateData(TestCase):
    """
    C.17. Excluded by construction: the report is assembled from a fixed list of
    sources, none of which is the local data store.

    """

    def test_it_never_reads_a_local_store(self):
        """
        Asserted against the *code*, with comments and the user-facing strings
        stripped.

        The file's own prose necessarily names the things it excludes -- the
        header explains them and the `excludes` list is shown to the player --
        so a naive search matches the file for documenting itself. Sixth time
        this project has written that test; the rule from M17 applies: anchor
        on something that cannot appear in prose.

        """
        code = _code_only(DIAGNOSTICS)
        for forbidden in (
            "notes",
            "relationships",
            "macros",
            "aliases",
            "triggers",
            "scripts",
            "storage",
        ):
            self.assertNotIn(
                "settings." + forbidden,
                code,
                "diagnostics.js reads %s, which is the player's own data" % forbidden,
            )

    def test_it_never_reads_accessibility_preferences(self):
        """
        A.73 and A.74. A report saying `screenReader: true` would disclose a
        disability to whoever reads the issue, and nobody should have to choose
        between reporting a bug and keeping that to themselves.

        """
        code = _code_only(DIAGNOSTICS)
        for probe in (
            "settings.preferences",
            "preferences.value",
            'get("preferences")',
            "screenReader",
            "braille",
        ):
            self.assertNotIn(probe, code, "diagnostics.js reads %r" % probe)

    def test_it_reports_event_types_rather_than_events(self):
        """
        "12 combat, 3 tell" is the shape of what was happening. The text of the
        tells is none of a maintainer's business.

        """
        self.assertIn("function recentEventTypes", DIAGNOSTICS)
        start = DIAGNOSTICS.index("function recentEventTypes")
        window = DIAGNOSTICS[start : start + 500]
        self.assertIn("counts[event.category]", window)
        self.assertNotIn("originalText", window)

    def test_game_text_requires_an_explicit_opt_in(self):
        self.assertIn("opts.includeOutput", DIAGNOSTICS)
        start = DIAGNOSTICS.index("if (opts.includeOutput")
        window = DIAGNOSTICS[start : start + 300]
        self.assertIn("originalText", window)

    def test_the_opt_in_is_named_in_the_summary(self):
        """
        So a reporter can see, in the same panel, that they asked for it.

        """
        self.assertIn("you asked for this", DIAGNOSTICS)

    def test_an_error_keeps_its_message_but_not_its_payload(self):
        """
        The payload that caused a failure may contain game text.

        """
        start = DIAGNOSTICS.index("function record(source, error, detail)")
        window = DIAGNOSTICS[start : start + 600]
        self.assertIn("error.message", window)
        self.assertNotIn("payload", window)


class TestNothingIsSent(TestCase):
    """
    The report is built locally and shown in full first.

    """

    def test_the_module_makes_no_requests(self):
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "sendBeacon",
            "WebSocket",
            "dispatcher",
            "Evennia.msg",
        ):
            self.assertNotIn(forbidden, DIAGNOSTICS, "diagnostics.js uses %r" % forbidden)

    def test_the_github_helper_returns_a_url_and_does_not_open_it(self):
        """
        A tool that filed an issue on somebody's behalf, with a payload they had
        not read, would be indefensible however convenient.

        """
        start = DIAGNOSTICS.index("function issueUrl")
        window = DIAGNOSTICS[start : start + 700]
        self.assertIn('return "https://github.com/"', window)
        self.assertNotIn("window.open", window)
        self.assertNotIn("location", window)

    def test_the_dialog_says_nothing_has_been_sent(self):
        start = SETTINGS.index("function openDiagnostics")
        window = SETTINGS[start : start + 1200]
        self.assertIn("nothing has been sent", window)

    def test_the_report_is_shown_before_any_action(self):
        """
        In a textarea rather than a `<pre>`: selectable, scrollable,
        keyboard-reachable and copyable with the keys everybody already knows,
        without Aetos reimplementing any of that.

        """
        start = SETTINGS.index("function openDiagnostics")
        window = SETTINGS[start : start + 3000]
        self.assertIn('createElement("textarea")', window)
        self.assertIn("area.readOnly = true", window)

    def test_the_textarea_has_a_label(self):
        start = SETTINGS.index("function openDiagnostics")
        window = SETTINGS[start : start + 3000]
        self.assertIn('"for", "aetos-diagnostics-text"', window)


class TestProviderNamesAreOptIn(TestCase):
    """
    C.17 permits provider class names. They are still a game's own internals,
    so a game decides whether to send them.

    """

    def test_diagnostics_are_absent_by_default(self):
        payload = manifest.build_manifest()
        self.assertNotIn("diagnostics", payload)

    @override_settings(AETOS_DIAGNOSTICS=True)
    def test_a_game_can_opt_in(self):
        payload = manifest.build_manifest()
        self.assertIn("diagnostics", payload)
        self.assertIn("providers", payload["diagnostics"])

    @override_settings(AETOS_DIAGNOSTICS=True)
    def test_the_opt_in_payload_carries_names_not_values(self):
        """
        Class names and slot names only. Never a value, never source.

        """
        payload = manifest.build_manifest()
        for slot, description in payload["diagnostics"]["providers"].items():
            self.assertIn("class", description)
            self.assertNotIn("value", description)

    def test_the_client_explains_the_absence(self):
        """
        Rather than showing an empty section, which reads as a bug in Aetos
        rather than a setting in the game.

        """
        self.assertIn("set AETOS_DIAGNOSTICS = True", DIAGNOSTICS)

    @override_settings(AETOS_DIAGNOSTICS=True)
    def test_a_provider_that_cannot_describe_itself_is_reported(self):
        """
        Precisely the situation a diagnostic report exists to explain, so the
        failure is surfaced rather than swallowed.

        """
        source = Path(manifest.__file__).read_text(encoding="utf-8")
        self.assertIn('payload["diagnostics"] = {"providers": {}, "error"', source)


class TestWiring(TestCase):
    """The report is only useful if something records into it."""

    def test_pipeline_failures_are_recorded(self):
        self.assertIn("diagnostics.record(", SHELL)
        self.assertIn('"pipeline:" + failure.stage', SHELL)

    def test_the_widget_list_is_an_accessor_not_an_array(self):
        """
        The registry does not exist when diagnostics is created. An array
        captured then would still be empty at report time -- which is exactly
        what the first version did.

        """
        start = SHELL.index("window.AetosDiagnostics.create({")
        window = SHELL[start : start + 800]
        self.assertIn("widgets: function ()", window)
        self.assertIn("modules: function ()", window)

    def test_the_module_accepts_either(self):
        self.assertIn("function resolve(source)", DIAGNOSTICS)
        self.assertIn('typeof source === "function"', DIAGNOSTICS)

    def test_it_is_reachable_from_the_palette(self):
        self.assertIn('"diagnostics.report"', SHELL)

    def test_errors_are_bounded(self):
        """
        A game with a broken provider produces one error per sync, and a report
        nobody can read is a report nobody reads.

        """
        self.assertIn("MAX_ERRORS", DIAGNOSTICS)
        self.assertIn("errors.length >= MAX_ERRORS", DIAGNOSTICS)
