"""
Contract tests for the command palette and settings surface.

Behaviour is exercised in a browser by `browser-qa/qa-palette-settings.js`.
These pin the structural decisions: that the palette acts on the client rather
than the game, and that an editor is never offered for automation a game forbids.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _strip_comments(source):
    """
    Remove JS comments.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


PALETTE = _strip_comments((JS_DIR / "palette.js").read_text(encoding="utf-8"))
SETTINGS = _strip_comments((JS_DIR / "settings.js").read_text(encoding="utf-8"))
SHELL = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))


class TestThePaletteActsOnTheClient(TestCase):
    """
    The palette never sends game commands.

    Most palettes in other software do run arbitrary things. The player already
    has a command line for the game; a second one that looked similar but
    behaved differently would be a trap.

    """

    def test_the_palette_never_touches_the_transport(self):
        for forbidden in ("Evennia.msg", "evennia.msg", "dispatcher.send", "WebSocket"):
            self.assertNotIn(forbidden, PALETTE, "palette.js references %r" % forbidden)

    def test_commands_are_plain_functions(self):
        """
        A palette entry runs a function the client registered. There is no
        command string that could be mistaken for game input.

        """
        self.assertIn("command.run()", PALETTE)


class TestNoEditorForForbiddenAutomation(TestCase):
    """
    Blueprint section 32: if scripting is disabled, no scripting editor appears.

    Not a disabled button, not a form that refuses on save -- absent. Offering a
    form that cannot work wastes the player's time and misrepresents the game.

    """

    def test_commands_can_declare_when_they_apply(self):
        self.assertIn("when:", PALETTE)
        self.assertIn("command.when()", PALETTE)

    def test_a_condition_that_throws_hides_rather_than_breaks(self):
        """One bad condition must not empty the whole palette."""
        self.assertIn("catch (err)", PALETTE)

    def test_automation_entries_are_gated_on_policy(self):
        for capability in ("macros", "aliases", "triggers", "timers", "scripting"):
            self.assertIn(
                'automationAllowed("%s")' % capability,
                SHELL,
                "%r editor is not gated on policy" % capability,
            )


class TestPaletteAccessibility(TestCase):
    """
    The ARIA combobox pattern.

    Focus stays in the input and `aria-activedescendant` moves the selection, so
    a screen reader announces each option without the player losing the field
    they are typing in.

    """

    def test_uses_the_combobox_pattern(self):
        self.assertIn('"role", "combobox"', PALETTE)
        self.assertIn('"role", "listbox"', PALETTE)
        self.assertIn('"role", "option"', PALETTE)

    def test_selection_moves_by_activedescendant(self):
        self.assertIn("aria-activedescendant", PALETTE)

    def test_focus_returns_to_the_opener_on_close(self):
        self.assertIn("opener.focus()", PALETTE)

    def test_options_are_chosen_on_mousedown(self):
        """
        A click would blur the input first and close the palette before the
        choice registered.

        """
        self.assertIn('"mousedown"', PALETTE)


class TestDiscoverability(TestCase):
    """
    A keyboard shortcut nobody can find is not a feature.

    Commands carry their shortcut so the palette teaches it, rather than the
    shortcut being something you had to read the docs to know.

    """

    def test_commands_carry_their_shortcut(self):
        self.assertIn("shortcut", PALETTE)

    def test_at_least_one_registered_command_advertises_a_shortcut(self):
        self.assertIn('"Ctrl+Shift+L"', SHELL)

    def test_ctrl_k_is_registered_with_the_shortcut_manager(self):
        """
        Not bound inside palette.js.

        A0 moved every global binding to `AetosShortcutManager` so it can be
        viewed, rebound and disabled (Addendum A.23).

        """
        self.assertIn('id: "palette.toggle"', SHELL)
        self.assertIn('defaultBinding: "Ctrl+K"', SHELL)

    def test_the_palette_no_longer_binds_its_own_global_key(self):
        self.assertNotIn("bindKeys", PALETTE, "palette.js still binds Ctrl+K itself")

    def test_the_palette_still_owns_its_internal_keys(self):
        """
        Arrows, Home, End and Escape stay in palette.js. They apply only while
        the palette has focus, so they belong to the combobox pattern rather
        than being global shortcuts -- exactly the case A11Y-KEY-002 permits.

        """
        for key in ("ArrowDown", "ArrowUp", "Home", "End", "Escape"):
            self.assertIn(key, PALETTE)


class TestPrivacyPanelReportsReality(TestCase):
    """
    Section 63.

    Counts are read from storage rather than assumed. A privacy screen that
    under-reports is worse than none, because it is actively reassuring about
    something it has not checked.

    """

    def test_counts_come_from_storage(self):
        self.assertIn("storage.counts()", SETTINGS)

    def test_every_namespace_is_listed(self):
        self.assertIn("storage.namespaces.forEach", SETTINGS)

    def test_it_reports_whether_storage_is_even_persistent(self):
        """
        In private browsing nothing survives the session, and saying so is more
        honest than listing counts that will vanish.

        """
        self.assertIn("isPersistent()", SETTINGS)

    def test_clearing_is_confirmed_with_specifics(self):
        """
        "Are you sure?" without specifics is not informed consent. The
        confirmation names what will go and what will not.

        """
        self.assertIn("Clear all Aetos data?", SETTINGS)
        self.assertIn("cannot be undone", SETTINGS)
        self.assertIn("game account is not affected", SETTINGS)

    def test_import_reports_what_it_refused(self):
        """
        An import that silently drops half a file is worse than one that says
        so.

        """
        self.assertIn("rejected", SETTINGS)
        self.assertIn("unknownNamespaces", SETTINGS)


class TestEditorsExistForEveryEngine(TestCase):
    """
    M12-M14 deferred these; they land here.

    An engine with no editor is a feature only reachable from a console, which
    is not a feature a player has.

    """

    def test_every_automation_kind_has_an_editor(self):
        for editor in ("editAlias", "editTrigger", "editTimer", "editScript"):
            self.assertIn(editor, SETTINGS, "missing %r" % editor)

    def test_the_script_editor_explains_the_sandbox(self):
        """
        A player should know what a script can and cannot reach before writing
        one, rather than discovering it from an error.

        """
        self.assertIn("cannot reach the web", SETTINGS)

    def test_the_timer_editor_warns_about_unattended_play(self):
        """
        Timers act with nobody at the keyboard. Many games have rules about
        that, and the client should say so rather than let a player find out
        from a moderator.

        """
        self.assertIn("unattended play", SETTINGS)
