"""
Contract tests for the in-client help.

Documentation that drifts from the software is worse than none, so these pin the
things that would silently rot: a feature gaining an editor but no topic, or a
topic surviving after the feature it describes was removed.

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


HELP = _strip_comments((JS_DIR / "help.js").read_text(encoding="utf-8"))
SHELL = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))


class TestEveryFeatureIsDocumented(TestCase):
    """
    A feature with no topic is a feature players have to be told about by
    someone else.

    """

    def test_every_automation_engine_has_a_topic(self):
        for topic in ("macros", "aliases", "triggers", "timers", "scripting"):
            self.assertIn('id: "%s"' % topic, HELP, "no help topic for %r" % topic)

    def test_the_other_surfaces_have_topics(self):
        for topic in ("layout", "palette", "map", "entities", "character", "notes"):
            self.assertIn('id: "%s"' % topic, HELP, "no help topic for %r" % topic)

    def test_privacy_and_accessibility_are_documented(self):
        self.assertIn('id: "privacy"', HELP)
        self.assertIn('id: "accessibility"', HELP)

    def test_developers_get_a_topic_with_real_code(self):
        self.assertIn('id: "developers"', HELP)
        self.assertIn("AETOS_PROVIDERS", HELP)
        self.assertIn("AETOS_FEATURES", HELP)
        self.assertIn("AetosResourceProvider", HELP)

    def test_every_provider_slot_is_listed_for_developers(self):
        """
        A slot nobody documented is a slot nobody uses.

        """
        for slot in (
            "resources",
            "entities",
            "actions",
            "map",
            "inventory",
            "equipment",
            "target",
            "effects",
        ):
            self.assertIn(slot, HELP, "provider slot %r is undocumented" % slot)


class TestTopicsAreGatedOnPolicy(TestCase):
    """
    Blueprint section 32, applied to documentation.

    Documenting scripting on a game that forbids it sends the player looking for
    a button that is not there, which is worse than saying nothing.

    """

    def test_gated_topics_declare_what_they_require(self):
        for capability in ("macros", "aliases", "triggers", "timers", "scripting"):
            self.assertIn('requires: "%s"' % capability, HELP)

    def test_the_filter_honours_the_declaration(self):
        self.assertIn("topic.requires", HELP)
        self.assertIn("isAllowed(topic.requires)", HELP)

    def test_help_is_given_the_real_policy_check(self):
        """
        The same predicate that gates the editors, not a second copy that could
        disagree with it.

        """
        self.assertIn("isAllowed: automationAllowed", SHELL)


class TestHelpIsReachable(TestCase):
    """
    Documentation nobody can find has not been written.

    """

    def test_f1_is_registered_with_the_shortcut_manager(self):
        """
        Not bound inside help.js.

        A0 moved every global binding to `AetosShortcutManager`, because a key a
        module binds for itself cannot be listed, rebound or disabled -- and a
        binding that collides with someone's screen reader with no recourse is
        not a shortcut, it is an obstacle (Addendum A.23).

        """
        self.assertIn('id: "help.toggle"', SHELL)
        self.assertIn('defaultBinding: "F1"', SHELL)

    def test_help_no_longer_binds_its_own_global_key(self):
        self.assertNotIn('=== "F1"', HELP, "help.js still binds F1 itself")
        self.assertNotIn("bindKeys", HELP)

    def test_the_shortcut_names_the_command_it_accelerates(self):
        """
        A.23: no feature may exist only behind a shortcut. Registration is
        refused without a palette command, so disabling the key never removes
        the feature.

        """
        self.assertIn('paletteCommand: "help.open"', SHELL)

    def test_it_is_in_the_palette(self):
        self.assertIn('"help.open"', SHELL)

    def test_every_topic_is_individually_searchable_from_the_palette(self):
        """
        So searching the palette for "privacy" reaches the privacy topic, not
        just a generic "Help" entry the player then has to search again.

        """
        self.assertIn("help.topics().forEach", SHELL)

    def test_the_palette_entry_teaches_the_shortcut(self):
        self.assertIn('"F1"', SHELL)


class TestHelpAccessibility(TestCase):
    """The overlay follows the modal dialog pattern."""

    def test_it_is_a_modal_dialog_with_a_name(self):
        self.assertIn('"role", "dialog"', HELP)
        self.assertIn('"aria-modal", "true"', HELP)
        self.assertIn('"aria-label", "Aetos help"', HELP)

    def test_focus_is_trapped_while_open(self):
        self.assertIn('event.key !== "Tab"', HELP)

    def test_focus_returns_to_the_opener_on_close(self):
        self.assertIn("opener.focus()", HELP)

    def test_choosing_a_topic_moves_focus_to_the_content(self):
        """
        Otherwise a screen-reader user has to hunt for where the article
        appeared.

        """
        self.assertIn("article.focus()", HELP)

    def test_the_current_topic_is_exposed(self):
        self.assertIn("aria-current", HELP)

    def test_the_search_field_has_a_label(self):
        self.assertIn("aetos-visually-hidden", HELP)
        self.assertIn('"for", "aetos-help-search"', HELP)

    def test_escape_closes(self):
        self.assertIn('event.key === "Escape"', HELP)


class TestExamplesCanBeScrolledWithoutAMouse(TestCase):
    """
    Found by running the axe gate at 800x600 rather than at 1280x800, which is
    the only viewport it had ever been run at.

    An example is `white-space: pre` and scrolls sideways instead of wrapping,
    and that is right for this content: several of them are column-aligned
    tables, and wrapping "resources   what your game measures" would destroy the
    alignment that makes it readable. WCAG 1.4.10 allows exactly that -- content
    requiring a two-dimensional layout. What it does not allow is a region only a
    mouse can scroll, which is what `scrollable-region-focusable` reported.

    """

    def test_an_example_is_focusable(self):
        self.assertIn("pre.tabIndex = 0", HELP)

    def test_every_example_is_focusable_rather_than_the_overflowing_ones(self):
        """
        Whether an example overflows depends on the window width and the
        player's text size, and changes under both. A `tabindex` set from a
        measurement is a control that is sometimes there -- which is the shape of
        defect this project keeps finding, and it would be invisible at the
        width whoever wrote it happened to be using.

        """
        block = HELP[HELP.index("if (section.example)") :][:900]
        self.assertNotIn("scrollWidth", block)
        self.assertNotIn("clientWidth", block)

    def test_it_is_named_so_the_focus_stop_means_something(self):
        self.assertIn('"aria-label"', HELP)
        self.assertIn('"Example: " + section.heading', HELP)

    def test_the_name_is_carried_by_a_role_that_may_be_named(self):
        """
        ARIA prohibits naming an element with the generic role, so `aria-label`
        on a plain `<pre>` is dropped by some screen readers and flagged by axe
        as a prohibited attribute -- one violation traded for another.

        `group` rather than `region` because `region` is a landmark, and an
        article with eight examples would add eight landmarks that mean nothing.

        """
        self.assertIn('pre.setAttribute("role", "group")', HELP)

    def test_a_focus_stop_is_visible_when_it_is_focused(self):
        css = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")
        self.assertIn(".aetos-help__example:focus-visible", css)


class TestTheFocusTrapKnowsWhatIsFocusable(TestCase):
    """
    The defect the change above would otherwise have introduced.

    The trap listed the three kinds of focusable element help happened to
    contain -- `button, input, [tabindex='-1']` -- which is a list that goes
    stale the moment anything is added, and something just was. An example
    sitting after the last button would have been skipped entirely: Tab from that
    button matched `last` and wrapped straight back to `first`, past the thing it
    should have reached next.

    A focus trap whose idea of "focusable" is narrower than the browser's does
    not trap focus, it loses it.

    """

    def test_elements_made_focusable_with_tabindex_are_included(self):
        self.assertIn("[tabindex='0']", HELP)

    def test_the_trap_still_covers_what_it_covered_before(self):
        block = HELP[HELP.index("var focusable = Array.prototype.slice.call") :][:400]
        for expected in ("button", "input", "[tabindex='-1']"):
            self.assertIn(expected, block)


class TestHelpRendersAsText(TestCase):
    """
    Help content is authored in this file rather than supplied by a game, but it
    is still rendered as text -- so the day someone makes it configurable there
    is no hole waiting.

    """

    def test_paragraphs_use_textcontent(self):
        self.assertIn("paragraph.textContent = line", HELP)

    def test_examples_use_textcontent(self):
        self.assertIn("pre.textContent = section.example", HELP)

    def test_nothing_is_injected_as_markup(self):
        for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            self.assertNotIn(forbidden, HELP, "help.js uses %r" % forbidden)


class TestHelpNeverTalksToTheGame(TestCase):
    """
    Opening documentation must not send anything. It is reading, not acting.

    """

    def test_no_transport_references(self):
        for forbidden in ("Evennia.msg", "dispatcher.send", "sendCommand", "WebSocket"):
            self.assertNotIn(forbidden, HELP, "help.js references %r" % forbidden)


class TestServicesAreWiredOnce(TestCase):
    """
    Regression guard for a fault this project has now hit three times.

    A patch that replaced every occurrence of a common line -- `queue:
    commandQueue,` -- injected a block of service properties into two unrelated
    factory calls. The result was syntactically valid, passed every test, and
    booted with no console error, because the extra properties were simply
    ignored. The only visible symptom was that `Aetos.help` was null.

    So each service is asserted to appear exactly once. A duplicate means a
    global replace has landed somewhere it was not meant to.

    """

    #: How many times each service line may legitimately appear, and where.
    #:
    #: A declared number rather than "exactly once", because a service can be
    #: wired into a module *and* exported -- `settings` now goes to the settings
    #: dashboard as well as onto `window.Aetos`. Keeping it a number that has to
    #: be edited deliberately preserves what the guard is for: a global replace
    #: raises the count without anybody deciding to.
    EXPECTED = {
        "settings: settings": (2, "the settings dashboard, and the Aetos export"),
        "palette: palette": (1, "the Aetos export"),
        "help: help": (1, "the Aetos export"),
    }

    def test_each_service_is_wired_the_number_of_times_it_should_be(self):
        for service, (expected, where) in self.EXPECTED.items():
            self.assertEqual(
                SHELL.count(service),
                expected,
                "%r appears %d times in aetos.js, expected %d (%s). Either a "
                "global replace has injected it somewhere it does not belong, "
                "or a new consumer was added and this table needs to say so."
                % (service, SHELL.count(service), expected, where),
            )

    def test_help_is_defined_before_it_is_exported(self):
        """
        `var` hoisting means an export above the definition captures `undefined`
        silently -- no error, no clue, just a null service.

        """
        self.assertLess(
            SHELL.index("var help = window.AetosHelp"),
            SHELL.index("help: help"),
            "help is exported before it is defined",
        )
