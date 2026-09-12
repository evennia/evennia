"""
Contract tests for the Aetos widget registry, layout manager and workspaces.

Behaviour is verified in a real browser by `browser-qa/qa-layout-workspaces.js`,
which drives the keyboard path directly. What Python pins down here are the
structural contracts that must not drift, so the Evennia suite catches a
regression even if nobody runs the browser suite.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _strip_comments(source):
    """
    Remove JS comments.

    Assertions here are about executable code, not the commentary that explains
    the design decisions behind it.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


class TestWidgetsAreDecoupledFromTheLayoutEngine(TestCase):
    """
    Blueprint section 15: widgets must not depend on the layout engine.

    The whole point of the adapter boundary is that the engine can be replaced
    without touching a widget. A widget that reached for the engine, or for the
    DOM outside its own element, would silently break that.

    """

    def setUp(self):
        self.builtins = _strip_comments((JS_DIR / "builtins.js").read_text(encoding="utf-8"))

    def test_builtin_widgets_do_not_reference_the_adapter(self):
        self.assertNotIn("Adapter", self.builtins)

    def test_builtin_widgets_do_not_reference_goldenlayout(self):
        """
        Named explicitly: GoldenLayout is the engine the blueprint anticipated,
        and a widget reaching for it would defeat the abstraction.

        """
        self.assertNotIn("GoldenLayout", self.builtins)

    def test_builtin_widgets_do_not_reach_into_the_store_directly(self):
        """
        The layout manager wires subscriptions on a widget's behalf. A widget
        subscribing for itself would leak listeners when it is removed.

        """
        self.assertNotIn("store.subscribe", self.builtins)

    def test_builtin_widgets_do_not_touch_the_transport(self):
        """Commands go through the injected sendCommand, never the websocket."""
        for forbidden in ("Evennia.msg", "evennia.msg", "WebSocket"):
            self.assertNotIn(forbidden, self.builtins)


class TestLayoutIsKeyboardOperable(TestCase):
    """
    Blueprint revision 2 section 16: every drag operation needs a keyboard
    equivalent, and section 72: no widget is finished until it is usable without
    a mouse.

    The manager's primitives are discrete operations rather than pointer events,
    so the keyboard path cannot fall behind a drag-first implementation.

    """

    def setUp(self):
        self.layout = _strip_comments((JS_DIR / "layout.js").read_text(encoding="utf-8"))
        self.workspaces = _strip_comments((JS_DIR / "workspaces.js").read_text(encoding="utf-8"))

    def test_manager_exposes_discrete_move_and_resize(self):
        self.assertIn("moveWidget", self.layout)
        self.assertIn("resizeWidget", self.layout)

    def test_every_layout_operation_has_a_key_binding(self):
        """Selection, movement, resize, hide and reset are all reachable."""
        for binding in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Escape"):
            self.assertIn(binding, self.workspaces, "missing binding %r" % binding)

    def test_layout_keys_are_scoped_to_edit_mode(self):
        """
        A player typing "n" to go north must never move a panel. The handler
        returns early unless edit mode is on and focus is outside the input.

        """
        self.assertIn("if (!editing || inInput)", self.workspaces)

    def test_typing_in_an_input_never_triggers_layout_keys(self):
        self.assertIn("TEXTAREA", self.workspaces)
        self.assertIn("INPUT", self.workspaces)


class TestLayoutChangesAreAnnounced(TestCase):
    """
    A player who cannot see a panel move has no other way to know it did, so
    every layout operation announces its result (blueprint section 48).

    """

    def setUp(self):
        self.workspaces = _strip_comments((JS_DIR / "workspaces.js").read_text(encoding="utf-8"))

    def test_operations_announce(self):
        self.assertGreaterEqual(self.workspaces.count("announce("), 8)

    def test_refusal_is_announced_not_silent(self):
        """
        Moving a panel that cannot move must say so. Silence is indistinguishable
        from a broken control when you cannot see the screen.

        """
        self.assertIn("cannot move", self.workspaces)


class TestHidingAWidgetIsReversible(TestCase):
    """
    Hiding must not be a one-way door.

    Without a palette the only route back would be a full layout reset, which
    discards everything else the player arranged.

    """

    def setUp(self):
        self.workspaces = _strip_comments((JS_DIR / "workspaces.js").read_text(encoding="utf-8"))
        self.template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )

    def test_a_palette_exists(self):
        self.assertIn("renderPalette", self.workspaces)
        self.assertIn("aetos-palette-list", self.template)

    def test_palette_state_is_exposed_to_assistive_technology(self):
        """Shown/hidden must not be conveyed by styling alone."""
        self.assertIn("aria-pressed", self.workspaces)

    def test_unavailable_widgets_explain_themselves(self):
        """
        A widget missing because the game does not expose a capability should
        say so, rather than being silently absent and looking like a bug.

        """
        self.assertIn("requiredCapabilities.join", self.workspaces)


class TestRestoreIsDefensive(TestCase):
    """
    A saved layout is local data that may predate a change in the game's
    manifest or in Aetos itself, so it is re-checked rather than trusted.

    """

    def setUp(self):
        self.layout = _strip_comments((JS_DIR / "layout.js").read_text(encoding="utf-8"))

    def test_restore_reports_what_it_skipped(self):
        self.assertIn("skipped", self.layout)

    def test_add_refuses_unsupported_widgets(self):
        """
        Restoring blindly would resurrect widgets for capabilities the game no
        longer exposes.

        """
        self.assertIn("isSupported", self.layout)
