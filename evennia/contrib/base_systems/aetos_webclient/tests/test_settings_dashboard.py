"""
Tests for the settings dashboard.

Gary: *"we should have a standard control panel and an accessibility control
panel where we expose more settings"*, then *"consolidate the settings into a
nice settings dashboard and lets expose for admins and deves appropriate
settings and for players only a sub set of settings appropriate for players"*.

**What it replaces is nothing.** Every destination in it already existed; what
did not exist was any way to find them. Privacy, themes, automation groups,
reminders, symbol packs and diagnostics were each a command-palette entry and
nothing else, so reaching any of them meant knowing to press `Ctrl+K` and knowing
what to type. Aetos had no Settings button at all.

**The gate is game-wide and says so.** The developer section appears when the
game has set `AETOS_DIAGNOSTICS`, which reaches the client as a `diagnostics` key
in the manifest. That is a switch a developer sets in `settings.py`, not a
per-account permission, and the panel says as much on screen. Per-account gating
is planned and needs the server to mark the session as staff; when it arrives it
feeds the same function and nothing else changes.

**It grants no authority, and must never look as though it does.** The inspector
shows a player their own session; the diagnostics report names the game's own
provider classes, which is exactly why a game opts into sending it. Hiding a
section is tidiness. Treating it as a security boundary would be the more
dangerous mistake, because somebody would eventually rely on it.

Verified live in both states: with diagnostics off the dashboard shows one group
of eight entries, and with it on, two groups of twelve.

"""

from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
DASH = (JS_DIR / "settings_dashboard.js").read_text(encoding="utf-8")
DIALOG = (JS_DIR / "dialog.js").read_text(encoding="utf-8")
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
TEMPLATE = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
    encoding="utf-8"
)


def _section(heading):
    """
    One section's declaration.

    Args:
        heading (str): The section heading.

    Returns:
        str: Source from the heading to the end of its entries.

    """
    start = DASH.index('heading: "%s"' % heading)
    return DASH[start : DASH.index("\n                }", start)]


class TestThereIsAWayIn(TestCase):
    """
    The whole reason it exists.

    """

    def test_the_status_bar_has_a_settings_button(self):
        self.assertIn('id="aetos-open-settings"', TEMPLATE)
        self.assertIn(">Settings</button>", TEMPLATE)

    def test_the_button_opens_the_dashboard(self):
        self.assertIn("settingsDashboard.open()", SHELL)

    def test_it_falls_back_to_the_palette_rather_than_doing_nothing(self):
        """
        Every destination lived in the palette before this existed, so a client
        without the dashboard module is no worse off than it used to be. A
        button that silently does nothing would be.

        """
        # The id is a *template* string; the shell reaches it by getElementById.
        window = SHELL[SHELL.index('getElementById("aetos-open-settings")') :][:900]
        self.assertIn('palette.open("settings")', window)
        self.assertIn("settingsButton.hidden = true", window)


class TestTheDeveloperGate(TestCase):
    """
    Game-wide, honest about being game-wide, and not a permission.

    """

    def test_it_reads_the_manifest_rather_than_guessing(self):
        body = DASH[DASH.index("function developerToolsAvailable()") :][:400]
        self.assertIn("current.diagnostics", body)

    def test_absent_means_hidden(self):
        """
        The manifest has no `diagnostics` key before the handshake completes
        either, so "not yet known" and "the game declined" both hide the
        section. That is the safe direction to be wrong in.

        """
        body = DASH[DASH.index("function developerToolsAvailable()") :][:400]
        self.assertIn("return !!(current && current.diagnostics)", body)

    def test_the_panel_says_why_the_section_is_there(self):
        """
        Otherwise a player who sees it assumes they have been given something,
        and a developer who does not see it has no idea what to turn on.

        """
        self.assertIn("Shown because this game set AETOS_DIAGNOSTICS", DASH)

    def test_it_does_not_claim_to_be_a_permission(self):
        self.assertIn("grants any authority", DASH)
        self.assertIn("not a per-account permission", DASH)

    def test_the_per_account_plan_is_recorded_where_it_would_be_built(self):
        """
        So the next person changes one function rather than redesigning this.

        """
        self.assertIn("Per-account gating is planned", DASH)
        self.assertIn("developerToolsAvailable()", DASH)


class TestTheTwoAudiences(TestCase):
    """
    What belongs in each list, and the rule that decides.

    """

    def test_the_player_section_is_about_the_player(self):
        section = _section("Your client")
        for expected in ("Themes", "Privacy and your data", "Export your profile"):
            self.assertIn(expected, section)

    def test_the_developer_section_is_about_the_game(self):
        section = _section("For game developers")
        for expected in ("Developer inspector", "Diagnostics report"):
            self.assertIn(expected, section)

    def test_no_developer_tool_leaks_into_the_player_section(self):
        section = _section("Your client")
        for forbidden in ("inspector", "openDiagnostics", "showContrastReport"):
            self.assertNotIn(forbidden, section, "%s is in the player list" % forbidden)

    def test_the_rule_for_deciding_is_written_down(self):
        """
        A list of destinations is a judgement, and the next person adding one
        needs the judgement rather than the list.

        """
        self.assertIn("WHAT MAKES SOMETHING A PLAYER SETTING", DASH)

    def test_the_player_section_says_nothing_leaves_the_browser(self):
        self.assertIn("None of it is sent to the game", DASH)


class TestRowsThatWouldDoNothingAreNotShown(TestCase):
    """
    A control that appears to work and changes nothing is the defect this
    project keeps finding. Here it would be a button opening a panel a game has
    switched off.

    """

    def test_automation_groups_respect_the_game_policy(self):
        section = _section("Your client")
        self.assertIn("automationAllowed(", section)

    def test_availability_is_asked_at_open_time(self):
        """
        The manifest arrives after boot. Deciding at build time would fix the
        list to whatever was known before the handshake.

        """
        self.assertIn("function sections()", DASH)
        body = DASH[DASH.index("function buildContent()") :]
        self.assertIn("sections().forEach", body)

    def test_an_empty_section_is_omitted_entirely(self):
        body = DASH[DASH.index("function buildContent()") :]
        self.assertIn("if (!available.length)", body)


class TestTheDialogIsRightForAListOfChoices(TestCase):
    """
    It reuses `dialog.js` rather than being a fourth overlay implementation:
    the focus trap, Escape, and returning focus to the opener are all things
    this project has already got right once.

    """

    def test_it_reuses_the_dialog_rather_than_building_another_overlay(self):
        self.assertIn("dialog.open({", DASH)
        self.assertIn("content: buildContent()", DASH)

    def test_there_is_no_save_button_on_something_with_nothing_to_save(self):
        self.assertIn("dismissOnly: true", DASH)
        self.assertIn("if (!options.dismissOnly)", DIALOG)

    def test_the_only_button_says_close_rather_than_cancel(self):
        """
        Its choices act immediately. "Cancel" would suggest what you already
        clicked could be undone by pressing it.

        """
        self.assertIn('options.dismissOnly ? "Close" : "Cancel"', DIALOG)

    def test_choosing_a_destination_closes_the_dashboard_first(self):
        """
        Two stacked modal dialogs is a focus trap inside a focus trap, and the
        way out of the inner one is not obvious from inside it.

        """
        body = DASH[DASH.index('button.addEventListener("click"') :][:600]
        self.assertLess(body.index("dialog.close(null)"), body.index("entry.run()"))

    def test_each_row_is_named_by_its_button_and_described_by_its_sentence(self):
        """
        Folding the sentence into the accessible name makes a screen reader read
        the paragraph before the word, every time focus lands on it.

        """
        self.assertIn('button.setAttribute("aria-describedby", detail.id)', DASH)
