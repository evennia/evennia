"""
Accessibility contract tests for the Aetos shell.

Blueprint revision 2 makes accessibility a completion gate rather than a late
review: no core Aetos widget is finished until it is usable without vision and
usable without a mouse. These tests encode the parts of that rule which can be
asserted statically, so a regression fails here rather than in a screen reader.

"""

from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_TEMPLATE_DIR, constants

TEMPLATE_PATH = Path(AETOS_TEMPLATE_DIR) / constants.WEBCLIENT_TEMPLATE_NAME
STATIC_DIR = Path(AETOS_TEMPLATE_DIR).parent / "static" / "aetos"


class TestShellSemantics(TestCase):
    """Landmarks, headings and labels a non-visual user navigates by."""

    def setUp(self):
        self.markup = TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_has_a_main_landmark(self):
        """Screen reader users jump between landmarks to skip chrome."""
        self.assertIn("<main", self.markup)

    def test_console_region_is_labelled(self):
        """An unlabelled region is announced only as "region"."""
        self.assertIn('aria-labelledby="aetos-console-heading"', self.markup)
        self.assertIn('id="aetos-console-heading"', self.markup)

    def test_command_input_has_a_label(self):
        """A bare textarea is announced with no indication of its purpose."""
        self.assertIn('<label for="aetos-input"', self.markup)

    def test_console_is_keyboard_reachable(self):
        """
        Scrollback must be reachable without a mouse. tabindex="0" puts the log
        in the tab order so it can be scrolled with the keyboard.

        """
        self.assertIn('tabindex="0"', self.markup)


class TestOutputIsNotALiveRegion(TestCase):
    """
    The output console must not announce every line.

    `role="log"` carries an *implicit* aria-live="polite". Left implicit, a screen
    reader would announce every line of game output -- unusable during combat spam
    or a long room listing. Aetos therefore sets aria-live="off" explicitly and
    routes deliberate announcements through a separate announcer region.
    Blueprint sections 48 and 100.

    """

    def setUp(self):
        self.markup = TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_console_disables_the_implicit_live_region(self):
        """Without this, role="log" would announce all game output."""
        self.assertIn('aria-live="off"', self.markup)

    def test_a_dedicated_announcer_region_exists(self):
        """Deliberate announcements need a channel that is not the output log."""
        self.assertIn('id="aetos-announcer"', self.markup)
        self.assertIn('aria-live="polite"', self.markup)

    def test_announcer_is_available_to_widgets(self):
        """Later widgets announce through this shared seam, not their own."""
        script = (STATIC_DIR / "js" / "aetos.js").read_text(encoding="utf-8")
        self.assertIn("announcer: announcer", script)


class TestGameOutputIsActuallyAnnounced(TestCase):
    """
    A14, and the other half of the class above.

    Gary: *"when I turn screen reader on and then go back to the game and type
    look nothing is read to me."*

    He was right, and it was the most serious defect this project has shipped.
    The console is deliberately `aria-live="off"` -- `role="log"` carries an
    implicit polite region that would speak every line including combat spam --
    and the stated design is that deliberate announcements go through the
    announcer instead.

    **Nothing went through the announcer.** The pipeline has had an `announce`
    stage since E0, the announcer has had categories, per-category preferences,
    priorities, flood control and review mode since A0, and
    `screenReader.announceRoom` has defaulted to `True` throughout. The only
    observer of that stage was the capture recorder, so no game text was ever
    handed to the announcer at all. A screen reader user heard silence.

    Every test in the class above passed, because each asserts one end of a wire
    that was never joined: the console is not a live region (true), an announcer
    region exists (true), widgets can reach it (true). Nobody asserted that game
    output arrives at it.

    The browser suite made the same mistake in a sharper form. Its `announce`
    check ingested five lines of game text and asserted only that none reached
    the *urgent* region -- which was true, because none reached anywhere. **A
    negative assertion is satisfied by nothing happening**, and needs a positive
    one beside it or it is measuring an empty room.

    """

    def setUp(self):
        self.script = (STATIC_DIR / "js" / "aetos.js").read_text(encoding="utf-8")

    def _announce_stage(self):
        """
        The block that observes the pipeline's announce stage.

        Returns:
            str: JavaScript source from the first announce observer onward.

        """
        start = self.script.index('pipeline.observe("announce"')
        return self.script[start : start + 2000]

    def test_something_observes_the_announce_stage_besides_the_recorder(self):
        """
        The stage existed and ran; it simply had no listener that spoke.

        """
        self.assertGreaterEqual(self.script.count('pipeline.observe("announce"'), 2)

    def test_game_output_is_handed_to_the_announcer(self):
        self.assertIn("announcer.announce(", self._announce_stage())

    def test_it_announces_the_plain_text_rather_than_the_markup(self):
        """
        Server markup legitimately reaches the client, and a screen reader must
        not read span tags aloud.

        """
        self.assertIn("event.plainText", self._announce_stage())

    def test_it_carries_the_category_so_the_announcer_can_decide(self):
        """
        Category is how `announceCombat: False` and the rest take effect. An
        announcement with no category is one the player's preferences cannot
        reach.

        """
        self.assertIn("category: event.category", self._announce_stage())

    def test_it_does_not_second_guess_the_announcer(self):
        """
        Priorities, per-category preferences, quiet mode, review mode and burst
        aggregation are the announcer's job. A second opinion in the shell is
        how two places come to disagree about what a player asked for.

        """
        stage = self._announce_stage()
        for policy in ("quietMode", "announceCombat", "announcementMode", "FLOOD"):
            self.assertNotIn(policy, stage)

    def test_empty_events_are_not_announced(self):
        """
        A structured event with no text would otherwise announce an empty
        string, which a screen reader reports as a change with nothing in it.

        """
        self.assertIn("if (!spoken", self._announce_stage())

    def test_the_console_is_still_not_a_live_region(self):
        """
        The fix must not be "turn the console on".

        `role="log"`'s implicit polite region would speak every line, with no
        categories, no thresholds and no flood control -- which is the thing the
        announcer exists to avoid and the reason `aria-live="off"` is there.

        """
        markup = TEMPLATE_PATH.read_text(encoding="utf-8")
        console = markup[markup.index('id="aetos-console"') :][:200]
        self.assertIn('aria-live="off"', console)


class TestStatusIsNotColourAlone(TestCase):
    """
    No information may depend on colour alone (blueprint sections 45, 49).

    Connection state is carried by a text label; the coloured dot is decorative
    and hidden from assistive technology.

    """

    def setUp(self):
        self.markup = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.script = (STATIC_DIR / "js" / "aetos.js").read_text(encoding="utf-8")

    def test_decorative_dot_is_hidden_from_assistive_tech(self):
        """Announcing a bare dot adds noise and no information."""
        self.assertIn('class="aetos-connection__dot" aria-hidden="true"', self.markup)

    def test_connection_state_has_a_text_label(self):
        """The state must be readable, not merely visible."""
        self.assertIn('id="aetos-connection-label"', self.markup)
        for word in ("Connecting", "Connected", "Disconnected"):
            self.assertIn(word, self.script)


class TestKeyboardOperation(TestCase):
    """Everything must be operable without a mouse (blueprint section 50)."""

    def setUp(self):
        self.script = (STATIC_DIR / "js" / "aetos.js").read_text(encoding="utf-8")

    def test_enter_submits_a_command(self):
        """The primary action must not require clicking the Send button."""
        self.assertIn('event.key === "Enter"', self.script)

    def test_shift_enter_is_reserved_for_newlines(self):
        """Multi-line input must remain possible without submitting."""
        self.assertIn("!event.shiftKey", self.script)


class TestVisualComfortPreferences(TestCase):
    """Respect for user-level display preferences."""

    def setUp(self):
        self.css = (STATIC_DIR / "css" / "aetos.css").read_text(encoding="utf-8")

    def test_reduced_motion_is_respected(self):
        """
        Motion can cause nausea and migraine; the OS preference is honoured.

        Asserted against `accessibility.css`, not this file's stylesheet. M4 put
        a blanket rule here that matched every element unconditionally; A0 later
        added one that honours an explicit player choice in both directions, and
        the two disagreed -- a player who deliberately chose full motion still
        had it removed by the older rule. The blanket rule was deleted at M29,
        and this test follows the rule that actually reads the preference.

        """
        a11y = (STATIC_DIR / "css" / "accessibility.css").read_text(encoding="utf-8")
        self.assertIn("@media (prefers-reduced-motion: reduce)", a11y)
        # And an explicit choice still wins, which is the part that was broken.
        self.assertIn(':root:not([data-aetos-motion="full"])', a11y)

    def test_focus_is_always_visible(self):
        """A keyboard user who cannot see focus cannot navigate."""
        self.assertIn(":focus-visible", self.css)

    def test_focus_outline_is_not_suppressed(self):
        """`outline: none` without a replacement is a common accessibility bug."""
        self.assertNotIn("outline: none", self.css)
        self.assertNotIn("outline:none", self.css)
