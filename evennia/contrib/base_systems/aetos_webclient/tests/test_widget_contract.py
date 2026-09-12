"""
Tests for the A1 widget accessibility contract.

Addendum A.28. The point of the contract is that a widget author cannot ship
without having answered the questions -- so the interesting assertions are about
what registration *refuses*, not what it accepts.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _read(name):
    """
    Read a client module.

    Args:
        name (str): File name under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / name).read_text(encoding="utf-8")


REGISTRY = _read("widgets.js")
LAYOUT = _read("layout.js")

#: Modules that define widgets, and the widgets they define.
WIDGET_MODULES = {
    "builtins.js": ["room", "exits", "people", "items"],
    "character.js": ["inventory", "equipment", "effects", "target"],
    "resources.js": ["resources"],
    "macros.js": ["hotbar"],
    "notes.js": ["notes"],
    "map.js": ["map"],
}


class TestTheContractIsRequired(TestCase):
    """
    A.28, enforced by throwing.

    "We will do accessibility later" is not expressible in this API, which is
    the entire purpose of A1.

    """

    def test_metadata_is_validated(self):
        self.assertIn("function validateAccessibility", REGISTRY)
        self.assertIn("accessibility metadata is required", REGISTRY)

    def test_the_four_required_fields_are_checked(self):
        for field in ("landmarkLabel", "heading", "keyboardOperable", "liveUpdates"):
            self.assertIn("accessibility.%s" % field, REGISTRY, "%s unchecked" % field)

    def test_keyboard_operability_has_no_default(self):
        """
        "Can this be used without a mouse?" has no safe default: assuming true
        hides the widgets that cannot, and assuming false slanders the ones that
        can. It must be stated.

        """
        self.assertIn("there is no safe default for it", REGISTRY)

    def test_a_graphical_widget_must_supply_a_text_alternative(self):
        """
        A canvas with no text form is not a widget with an accessibility gap.
        It is a widget half the audience cannot use at all.

        """
        self.assertIn("graphicalOnly", REGISTRY)
        self.assertIn("textAlternative", REGISTRY)
        self.assertIn("unusable, not merely", REGISTRY)

    def test_the_contract_survives_normalisation(self):
        """
        Validated and then dropped would be worse than not validating: it would
        look enforced while the layout received nothing.

        """
        start = REGISTRY.index("function normalize(")
        end = REGISTRY.index("function createRegistry(")
        block = REGISTRY[start:end]
        for field in ("landmarkLabel", "heading", "keyboardOperable", "liveUpdates"):
            self.assertIn(field, block, "normalize() drops accessibility.%s" % field)


class TestEveryWidgetDeclaresIt(TestCase):
    """
    A1's gate: all twelve, with no exemption for being built in.

    """

    def test_every_widget_module_declares_a_contract_per_widget(self):
        for module, widgets in WIDGET_MODULES.items():
            source = _read(module)
            declared = source.count("accessibility: {")
            self.assertEqual(
                declared,
                len(widgets),
                "%s defines %d widgets but declares %d contracts"
                % (module, len(widgets), declared),
            )

    def test_every_widget_id_is_followed_by_its_contract(self):
        """
        Position matters: the contract must belong to the widget it sits in,
        not to a neighbour.

        """
        for module, widgets in WIDGET_MODULES.items():
            source = _read(module)
            for widget_id in widgets:
                match = re.search(r'id: "%s",\s*\n' % re.escape(widget_id), source)
                self.assertIsNotNone(match, "%s: no id line for %r" % (module, widget_id))
                window = source[match.end() : match.end() + 400]
                self.assertIn(
                    "accessibility: {",
                    window,
                    "%s: %r does not declare a contract next to its id" % (module, widget_id),
                )

    def test_every_declared_contract_names_a_landmark_and_a_heading(self):
        for module in WIDGET_MODULES:
            source = _read(module)
            self.assertEqual(
                source.count("accessibility: {"),
                source.count("landmarkLabel:"),
                "%s has a contract without a landmarkLabel" % module,
            )
            self.assertEqual(
                source.count("accessibility: {"),
                source.count("heading:"),
                "%s has a contract without a heading" % module,
            )


class TestTheLayoutUsesIt(TestCase):
    """
    Metadata nothing consumes is metadata that rots.

    """

    def test_the_heading_comes_from_the_contract(self):
        self.assertIn("meta.heading || instance.displayName", LAYOUT)

    def test_the_landmark_name_is_only_set_when_it_differs(self):
        """
        `aria-label` overrides `aria-labelledby`, so setting it unconditionally
        would silently detach every panel from its own heading for no benefit.

        """
        self.assertIn("meta.landmarkLabel !== heading.textContent", LAYOUT)

    def test_live_updates_are_declared_on_the_panel(self):
        """
        So QA can assert that a widget claiming live updates routes them through
        the announcement manager rather than inventing a live region.

        """
        self.assertIn('"data-aetos-live"', LAYOUT)

    def test_display_only_widgets_are_marked(self):
        self.assertIn("data-aetos-display-only", LAYOUT)

    def test_the_contract_reaches_the_adapter(self):
        """
        The adapter's contract is the *instance*. An adapter reaching back
        through `instance.definition` would break the moment a second adapter
        was written -- which is the whole reason the adapter boundary exists.

        """
        start = LAYOUT.index("var instance = {")
        end = LAYOUT.index("adapter.mount(instance)")
        self.assertIn("accessibility: definition.accessibility", LAYOUT[start:end])


class TestConditionalRequirementsAreRecorded(TestCase):
    """
    A.26 (keyboard splitter) and A.27 (tabs) are conditional: they apply *where
    such a control is used*. Aetos uses neither.

    Resizing is discrete keyboard commands on a selected panel, not a draggable
    splitter, so there is no `separator` to give value semantics to. Nothing in
    the client is a tab set.

    Asserted rather than assumed, so that the day someone adds a splitter or a
    tab strip, this test fails and points at the requirement they now owe.

    """

    def test_there_is_no_splitter_to_give_separator_semantics_to(self):
        """
        A splitter is a separator that is *also* focusable or valued.

        Three things in this client wear roles that look like a splitter and
        are not one, so the detector has to be precise:

        - `menu.js` uses `role="separator"` for a static menu divider.
        - `resources.js` uses `role="meter"` with `aria-valuenow` for a
          read-only gauge.
        - `workspaces.js` resizes panels by keystroke, with no draggable
          boundary at all.

        Only a separator carrying a value or a tab stop is a window splitter,
        and only that owes A.26 arrow-key resizing and value semantics.

        """
        for source in JS_DIR.glob("*.js"):
            text = source.read_text(encoding="utf-8")
            for match in re.finditer(r'"role",\s*"separator"', text):
                window = text[max(0, match.start() - 400) : match.start() + 400]
                self.assertNotIn(
                    "aria-valuenow",
                    window,
                    "%s has a valued separator -- that is a splitter, and A.26 "
                    "now applies" % source.name,
                )
                self.assertNotIn(
                    "tabindex",
                    window,
                    "%s has a focusable separator -- that is a splitter, and "
                    "A.26 now applies" % source.name,
                )

    def test_the_menu_separator_is_static(self):
        """
        Confirming the distinction rather than assuming it: a menu separator
        must not be focusable, or Tab would stop on a divider.

        """
        menu = _read("menu.js")
        start = menu.index('divider.setAttribute("role", "separator")')
        window = menu[start - 300 : start + 300]
        self.assertNotIn("tabindex", window)
        self.assertNotIn("aria-valuenow", window)

    def test_there_is_no_tab_set(self):
        for source in JS_DIR.glob("*.js"):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn(
                'role", "tablist"',
                text,
                "%s introduces tabs -- A.27 now applies: the APG Tabs pattern "
                "is required" % source.name,
            )

    def test_resizing_is_keyboard_operable_anyway(self):
        """
        The requirement behind A.26 is met even though its specific mechanism is
        absent: a panel can be resized without a pointer.

        """
        workspaces = _read("workspaces.js")
        self.assertIn("function resize(", workspaces)
        self.assertIn("resize(1)", workspaces)
        self.assertIn("resize(-1)", workspaces)
