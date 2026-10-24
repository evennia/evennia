"""
Tests for A9 and A10 -- the mode switch and the two control panels.

Gary's direction came in four parts, and each one corrected the version before
it:

1. *"the accessibility ui and the standard ui should be a toggle and if its
   toggled on you can choose the accessibility features you want"* (A9). Shipped
   as a disclosure: the panel hid and every accommodation stayed applied.
2. *"lets make the default mode and the accessable mode a toggle so we dont have
   to try to be everything to everybody"* (A10). Two real modes.
3. *"the button in the upper right only presents layout options that has
   accessibility options, I want a toggle that switches between default mode and
   accessibility mode"* -- because the switch also opened a panel of options, so
   it read as an options button. The mode and the options are now two controls.
4. *"we need to make sure we give text size options... having to zoom the browser
   is janky"*, and *"that option should be in both modes"*. Text size is not an
   accommodation somebody opts into; it is a basic property of a text interface.
   It survives the switch and appears in both panels.

Which leaves: a switch at the top right that changes the mode and nothing else, a
standard control panel, and an accessibility control panel that exposes more.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
PANEL = (JS_DIR / "accessibility" / "panel.js").read_text(encoding="utf-8")
PREFS = (JS_DIR / "accessibility" / "preferences.js").read_text(encoding="utf-8")
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
TEMPLATE = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
    encoding="utf-8"
)
CSS = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "accessibility.css").read_text(encoding="utf-8")


def _governed_paths():
    """
    The preference paths the panels offer.

    Returns:
        list: Dotted paths, in declaration order.

    """
    block = PREFS[PREFS.index("var GOVERNED = [") : PREFS.index("var UNCONDITIONAL = [")]
    return re.findall(r'path:\s*"([\w.]+)"', block)


def _entry(path):
    """
    One governed entry's declaration.

    Args:
        path (str): The preference path.

    Returns:
        str: The declaration block.

    """
    start = PREFS.index('path: "%s"' % path)
    return PREFS[start : PREFS.index("}", start)]


def _code_only(source):
    """
    Source with its comments removed.

    A guard that greps for a forbidden construct cannot tell an explanation from
    an instruction, and the explanation is usually right next to it -- the
    comment saying "`!!wanted` was removed because..." contains `!!wanted`.

    That has now happened twice in one day, in two different files, so it is a
    shape rather than an accident: any assertion of the form "this string must
    not appear in the source" needs the comments gone first, or it fails the
    moment somebody documents the fix.

    Args:
        source (str): JavaScript source.

    Returns:
        str: The same source with block and line comments stripped.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


def _function(name, until):
    """
    Slice one function out of `panel.js`.

    Args:
        name (str): The function's signature line.
        until (str): A later landmark.

    Returns:
        str: JavaScript source.

    """
    start = PANEL.index(name)
    return PANEL[start : PANEL.index(until, start)]


class TestTheSwitchIsASwitch(TestCase):
    """
    Gary's third correction. It used to be a button that opened a panel of
    options, which is what it looked like, because it was.

    """

    def test_it_is_a_switch_rather_than_a_button_or_a_disclosure(self):
        """
        `role="switch"` with `aria-checked` announces "on" and "off", which is
        what this does. `aria-pressed` would say "pressed" -- the act rather
        than the state -- and `aria-expanded` would claim it merely reveals a
        panel, while it is in fact changing the whole client.

        """
        window = TEMPLATE[TEMPLATE.index('id="aetos-accessibility-toggle"') :][:400]
        self.assertIn('role="switch"', window)
        self.assertIn('aria-checked="false"', window)
        self.assertNotIn("aria-pressed", window)
        self.assertNotIn("aria-expanded", window)

    def test_it_has_a_visible_track_and_thumb(self):
        self.assertIn("aetos-modeswitch__track", TEMPLATE)
        self.assertIn("aetos-modeswitch__thumb", TEMPLATE)

    def test_the_state_is_carried_by_position_and_not_only_colour(self):
        """
        Measured moving 16px. Somebody who cannot tell the two colours apart can
        still see which end the thumb is at.

        """
        block = CSS[CSS.index('[aria-checked="true"] .aetos-modeswitch__thumb') :]
        block = block[: block.index("}")]
        self.assertIn("margin-left: auto", block)

    def test_the_thumb_does_not_rely_on_absolute_positioning(self):
        """
        It did, and it never moved -- not from the rule and not from an inline
        `left: 18px !important` either, so `left` was being ignored outright
        rather than losing a cascade. Flex layout has nothing to override and
        nothing to position against.

        """
        block = CSS[CSS.index(".aetos-modeswitch__thumb {") :]
        block = block[: block.index("}")]
        self.assertNotIn("position: absolute", block)

    def test_it_reports_the_mode_rather_than_the_panel(self):
        """
        Found by reading the code back after splitting the two: this line still
        used `isOpen()`, which had quietly come to mean "the options are
        showing". The switch would have reported the wrong thing whenever the
        two disagreed, which is the only time it matters.

        """
        self.assertIn('toggleButton.setAttribute("aria-checked", isAccessible()', PANEL)

    def test_the_track_stays_visible_without_colour(self):
        """
        Windows High Contrast discards background and border colours, and the
        thumb's position is then the only thing left.

        """
        blocks = re.findall(r"@media \(forced-colors: active\)[^{]*\{(.*?)\n\}", CSS, flags=re.S)
        self.assertTrue(blocks, "no forced-colors block at all")
        # The file has more than one, so find the one that mentions the thumb
        # rather than trusting the first -- the first version of this assertion
        # searched the wrong block and failed for the wrong reason.
        relevant = [b for b in blocks if "modeswitch__thumb" in b]
        self.assertTrue(relevant, "the switch has no forced-colors handling")
        self.assertIn("currentColor", relevant[0])


class TestTheSwitchAndTheOptionsAreSeparate(TestCase):
    """
    The correction itself. A control that does two things is read as whichever
    one you notice first.

    """

    def test_switching_the_mode_does_not_open_the_options(self):
        """
        A12 narrowed this rule, and the test says exactly how far.

        It used to be absolute: `setMode` never sets `optionsShown`. That was
        right when the only thing behind the switch was a panel of eleven
        technical choices, and wrong once measurement showed the alternative --
        turning accessible mode on with no preset changes nothing whatsoever on
        screen, because every governed preference already sits at its standard
        value.

        So the rule is now conditional, and the condition is the whole
        protection: the panel may open **only** when the starting-point question
        is owed, which happens at most once per profile. Asserting on the guard
        rather than on its absence is what stops this quietly becoming "the
        switch opens the panel again".

        """
        body = _function("function setMode(wanted)", "function adjustTextSize")
        opens = [line for line in body.splitlines() if "optionsShown = true" in line]
        self.assertEqual(len(opens), 1, "setMode should open the panel in exactly one place")
        # ...and that one place is guarded by the chooser being owed.
        self.assertIn("if (next && needsChooser()) {", body)
        # Still never steals focus. Moving focus on a mode switch was the
        # original complaint and no part of A12 needs it.
        self.assertNotIn("focusFirst", body)

    def test_the_chooser_is_owed_only_once_and_only_in_accessible_mode(self):
        """
        `null` is "never asked"; every other value is an answer.

        Including `"custom"`, which is why choosing to set things up by hand has
        to be a preset rather than a way of dismissing the question. A chooser
        that reappears every session is an interruption, and interruptions are
        the thing this panel exists to reduce.

        """
        body = _function("function needsChooser()", "function set(")
        self.assertIn("isAccessible()", body)
        self.assertIn('preferences.value("shell.preset") === null', body)

    def test_opening_the_options_does_not_change_the_mode(self):
        body = _function("function toggleOptions()", "function attach(")
        self.assertNotIn("setMode(", body)

    def test_they_are_two_controls(self):
        self.assertIn('id="aetos-accessibility-toggle"', TEMPLATE)
        self.assertIn('id="aetos-accessibility-options"', TEMPLATE)

    def test_they_are_two_palette_commands(self):
        self.assertIn('addCommand("accessibility.mode"', SHELL)
        self.assertIn('addCommand("accessibility.options"', SHELL)

    def test_the_shortcut_belongs_to_the_mode(self):
        """
        `Ctrl+Shift+A` is the way back for somebody who can no longer read the
        screen, so it switches the mode rather than opening a settings panel
        they would then have to read.

        """
        window = SHELL[SHELL.index('addCommand("accessibility.mode"') :][:400]
        self.assertIn("Ctrl+Shift+A", window)
        self.assertIn("accessibilityPanel.setMode()", window)

    def test_the_options_panel_state_is_not_persisted(self):
        """
        The mode is a lasting choice about which interface you are in; having
        the settings open is something you are doing this minute. Persisting it
        would bring the panel back every session for somebody who opened it
        once.

        """
        self.assertIn("var optionsShown = false;", PANEL)
        self.assertNotIn('"shell.optionsShown"', PANEL)


class TestTwoControlPanels(TestCase):
    """
    Gary: *"we should have a standard control panel and an accessibility control
    panel where we expose more settings"*.

    Same host, two lists. Standard mode shows what standard mode can actually
    apply; accessible mode adds the rest.

    """

    def _standard_paths(self):
        """
        The options a standard-mode panel offers.

        Returns:
            list: Dotted paths.

        """
        return [
            path for path in _governed_paths() if "revertsInStandardMode: false" in _entry(path)
        ]

    def test_the_list_depends_on_the_mode(self):
        body = _function("function entriesForMode()", "function set(")
        self.assertIn("if (isAccessible())", body)
        self.assertIn("!entry.revertsInStandardMode", body)

    def test_the_standard_panel_is_not_empty(self):
        """
        Four options apply in standard mode. Hiding the panel there -- which an
        earlier version did -- would have taken text size away from the people
        most likely to need it.

        """
        standard = self._standard_paths()
        self.assertGreaterEqual(len(standard), 4)
        self.assertIn("visual.scale", standard)

    def test_the_accessible_panel_exposes_more(self):
        self.assertGreater(len(_governed_paths()), len(self._standard_paths()))

    def test_the_headings_say_which_list_you_are_looking_at(self):
        self.assertIn('"Accessible mode options"', PANEL)
        self.assertIn('"Display options"', PANEL)

    def test_the_options_button_is_offered_in_both_modes(self):
        self.assertIn("optionsButton.hidden = false;", PANEL)


class TestTextSizeIsAvailableInBothModes(TestCase):
    """
    Gary: *"one of the worst things is having to read tiny text with no way to
    just adjust the text size. having to zoom the browser is janky"* -- and
    *"that option should be in both modes"*.

    """

    def test_it_survives_the_mode_switch(self):
        self.assertIn("revertsInStandardMode: false", _entry("visual.scale"))

    def test_the_reason_is_recorded(self):
        """
        It is the one entry marked `false` for a different reason from the other
        three, and the difference matters: theirs is that reverting would impose
        an accommodation's opposite, and this one's is that it was never an
        accommodation to begin with.

        """
        entry = _entry("visual.scale")
        self.assertIn("not an accommodation", entry)
        self.assertIn("zoom", entry)

    def test_it_can_be_changed_without_opening_anything(self):
        """
        Somebody who cannot read the screen should not have to read a settings
        panel first.

        """
        for command in ("text.larger", "text.smaller", "text.reset"):
            self.assertIn('addCommand("%s"' % command, SHELL)

    def test_the_step_is_clamped_to_the_schema_range(self):
        """
        A repeated keystroke must not walk the interface somewhere unreadable
        in either direction.

        """
        body = _function("function adjustTextSize(delta)", "Show or hide")
        self.assertIn('schema.RANGES && schema.RANGES["visual.scale"]', body)
        self.assertIn("Math.min(bounds[1], Math.max(bounds[0], next))", body)

    def test_the_result_is_announced_as_a_number(self):
        """
        "Larger" tells somebody adjusting this nothing they can act on; they
        cannot necessarily see the result.

        """
        body = _function("function adjustTextSize(delta)", "Show or hide")
        self.assertIn('"Text size " + Math.round(next * 100) + " percent."', body)


class TestTheModeMasksAndNeverErases(TestCase):
    """
    The decision that makes a real mode switch safe to try.

    """

    def test_the_mode_is_the_stored_state(self):
        self.assertIn("shell: {", PREFS)
        self.assertIn('mode: "standard"', PREFS)
        self.assertIn('"shell.mode": ["standard", "accessible"]', PREFS)

    def test_the_default_is_the_standard_interface(self):
        block = PREFS[PREFS.index("shell: {") :][:120]
        self.assertIn('mode: "standard"', block)

    def test_switching_writes_only_the_mode(self):
        body = _function("function setMode(wanted)", "function adjustTextSize")
        self.assertIn('set("shell.mode", next ? "accessible" : "standard")', body)
        self.assertEqual(body.count("set("), 1)

    def test_standard_mode_masks_rather_than_clearing(self):
        body = PREFS[
            PREFS.index("function effective()") : PREFS.index("function activeAccommodations()")
        ]
        self.assertIn("var view = clone(current);", body)
        self.assertIn("entry.revertsInStandardMode", body)
        self.assertNotIn("current[", body.split("clone(current)")[1])

    def test_consumers_are_given_the_effective_view(self):
        self.assertIn("listener(effective());", PREFS)
        self.assertNotIn("listener(clone(current));", PREFS)

    def test_the_priming_call_uses_it_too(self):
        """
        Priming with `get()` would apply the accommodations once at boot and
        mask them from the next change onward, so a client started in standard
        mode would look accessible until somebody touched something.

        """
        body = PREFS[PREFS.index("function subscribe(listener)") :][:1200]
        self.assertIn("listener(effective());", body)

    def test_the_editors_still_see_what_the_player_chose(self):
        body = PREFS[PREFS.index("function get() {") :][:120]
        self.assertIn("return clone(current);", body)


class TestSomeThingsMustNotRevert(TestCase):
    """
    A preference may only be reverted if its **default is the standard
    experience**, so that reverting removes an accommodation rather than
    imposing one. Getting this backwards would have made standard mode hostile
    to exactly the people it is meant to leave alone.

    """

    def test_gestures_do_not_come_back_on(self):
        """
        They default to ON, so somebody with a tremor turns them OFF.

        """
        self.assertIn("revertsInStandardMode: false", _entry("pointer.gestures"))

    def test_mute_is_not_undone(self):
        """
        Muting is the accommodation; the default is unmuted.

        """
        self.assertIn("revertsInStandardMode: false", _entry("audio.muted"))

    def test_orientation_help_is_not_switched_on(self):
        """
        It defaults to ON, so reverting would add a feature rather than remove
        one.

        """
        self.assertIn("revertsInStandardMode: false", _entry("cognitive.reorientEnabled"))

    def test_the_visual_accommodations_do_revert(self):
        for path in (
            "visual.contrast",
            "visual.stimulation",
            "cognitive.quietMode",
            "cognitive.focusMode",
            "aac.enabled",
        ):
            self.assertIn(
                "revertsInStandardMode: true",
                _entry(path),
                "%s should revert in standard mode" % path,
            )

    def test_motion_reverts_to_following_the_system(self):
        """
        Its default is `"system"`, so reverting hands the decision back to
        `prefers-reduced-motion`. Somebody whose operating system asks for less
        still gets less in standard mode.

        """
        self.assertIn("revertsInStandardMode: true", _entry("visual.motion"))
        self.assertIn('motion: "system"', PREFS)

    def test_the_reasoning_is_recorded_next_to_the_flag(self):
        block = PREFS[: PREFS.index("var GOVERNED = [")]
        self.assertIn("default is the standard experience", block[-3000:])
        self.assertIn("tremor", block[-3000:])


class TestThereIsAlwaysAWayBack(TestCase):
    """
    The hazard that made A9 ship the softer version first.

    """

    def _set_mode(self):
        """
        The body of the mode switch.

        Returns:
            str: JavaScript source.

        """
        return _function("function setMode(wanted)", "function adjustTextSize")

    def test_setmode_understands_the_names_of_the_modes_it_sets(self):
        """
        `setMode("standard")` used to turn accessible mode ON.

        The argument was coerced with `!!wanted`, so any non-empty string was
        true -- and the two strings anybody would reach for are the names of the
        two modes. A function called `setMode` that accepts "standard" and does
        the opposite is this project's recurring defect wearing an API's
        clothes.

        **No player could hit it.** Every call site inside the client passes
        nothing and toggles, which is why it survived A9, A10 and four
        milestones after them. It was found by the A8 readiness probe -- the
        first caller from outside the client -- falling into it on its first
        run, which is what an outside caller would do.

        """
        body = _code_only(self._set_mode())
        self.assertIn('wanted === "accessible" || wanted === "standard"', body)
        self.assertNotIn("!!wanted", body, "the argument is still coerced")

    def test_a_bare_call_still_toggles(self):
        """
        The behaviour every shipped call site depends on, so the fix must not
        have moved it.

        """
        self.assertIn("wanted === undefined", self._set_mode())

    def test_an_unrecognised_argument_is_refused_rather_than_guessed_at(self):
        """
        And refused with `null`, not `false`: a successful switch to standard
        mode already returns `false`, and a caller cannot be asked to tell those
        two apart.

        """
        body = self._set_mode()
        self.assertIn("return null", body)

    def test_leaving_says_how_to_return(self):
        self.assertIn("Press Control Shift A", self._set_mode())

    def test_leaving_says_nothing_was_erased(self):
        self.assertIn("nothing was erased", self._set_mode())

    def test_it_names_what_stopped_applying(self):
        self.assertIn("activeAccommodations", PANEL)
        self.assertIn("function activeAccommodations()", PREFS)

    def test_that_message_is_not_announced_at_the_quietest_level(self):
        self.assertIn('priority: "important"', self._set_mode())

    def test_the_shell_forwards_announcement_options(self):
        """
        Found by writing the test: the shell passed a fixed
        `{ priority: "normal" }` and dropped anything the panel asked for.

        """
        self.assertIn("accessibility.announce(message, options || ", SHELL)

    def test_the_switch_keeps_its_size_in_both_modes(self):
        """
        Measured at 32px in both. It is the control somebody reaches for when
        they can no longer read the screen.

        """
        block = CSS[CSS.index(".aetos-root .aetos-statusbar__button--mode {") :]
        self.assertIn("min-height: 32px", block[: block.index("}")])

    def test_the_floor_wins_on_specificity_rather_than_on_order(self):
        """
        Three earlier versions of this floor did nothing at all.
        `var(--aetos-target)` is `0px` on a fine pointer; `28px` in `aetos.css`
        lost to a rule in this file, which loads later; and dropping the
        `.aetos-root` prefix lost to `.aetos-root button` on specificity. All
        three were found by measuring the rendered button, which read 24px while
        the stylesheet said otherwise.

        The prefix is what makes it win: two classes (0,2,0) against one class
        and one element (0,1,1). This asserts the prefix rather than the
        position, because the position is not what decides it -- an earlier
        version of this very test asserted the ordering and failed while the
        button measured a correct 32px.

        """
        self.assertIn(".aetos-root .aetos-statusbar__button--mode {", CSS)
        self.assertIn(".aetos-root button,", CSS)


class TestTheGovernanceLine(TestCase):
    """
    The deliverable of A9, still true after A10: what the mode governs, and what
    it must never reach.

    """

    def test_every_offered_path_exists_in_the_schema(self):
        defaults = PREFS[PREFS.index("var DEFAULTS = {") : PREFS.index("var GOVERNED = [")]
        for path in _governed_paths():
            group, key = path.split(".")
            self.assertIn(group + ": {", defaults, "no such group: %s" % group)
            self.assertIn(key + ":", defaults, "no such preference: %s" % path)

    def test_the_baseline_is_not_offered_as_an_option(self):
        offered = set(_governed_paths())
        for forbidden in (
            "keyboard.singleKeyShortcuts",
            "screenReader.reviewModeBehavior",
            "braille.compactStatus",
        ):
            self.assertNotIn(forbidden, offered)

    def test_the_panel_lists_what_was_never_optional(self):
        """
        Shown, not merely excluded. Otherwise a mode called "accessible" implies
        the other one is not.

        """
        self.assertIn("var UNCONDITIONAL = [", PREFS)
        block = PREFS[PREFS.index("var UNCONDITIONAL = [") : PREFS.index("var SCALE_MIN")]
        for expected in ("keyboard", "Focus", "Colour", "announcement"):
            self.assertIn(expected, block)
        self.assertIn("buildUnconditional", PANEL)
        self.assertIn('textContent = "Always on"', PANEL)

    def test_the_picker_is_granular_rather_than_a_preset(self):
        self.assertGreaterEqual(len(_governed_paths()), 8)
        self.assertIn("bundle to accept or refuse", PANEL)


class TestThePanelIsItselfAccessible(TestCase):
    """
    A panel about accessibility that is not accessible would be a special kind
    of failure.

    """

    def test_it_is_a_landmark_rather_than_a_dialog(self):
        self.assertIn('host.setAttribute("role", "region")', PANEL)
        self.assertIn('host.setAttribute("aria-label", "Accessibility options")', PANEL)
        self.assertNotIn('"dialog"', PANEL)

    def test_every_control_is_a_native_element(self):
        """
        The rule is unchanged; A13 changed which native elements.

        A0 chose native controls because they arrive already keyboard-operable,
        already announced with their value, and already understood by every
        assistive technology -- and a hand-built one starts at none of that.
        That reasoning has nothing to do with `<select>` specifically.

        A13 replaced the dropdowns and checkboxes with radio groups, because a
        dropdown shows one option at a time in small text and hides the rest
        behind an interaction -- which is the wrong control for somebody who
        drilled in *because* reading small text is hard. A radio is not a step
        away from the native-control rule; it is the same rule.

        """
        for native in (
            'input.type = "radio"',
            'input.type = "range"',
            'createElement("fieldset")',
        ):
            self.assertIn(native, PANEL)
        self.assertNotIn('role="slider"', PANEL)
        self.assertNotIn('role="radio"', PANEL)

    def test_the_explanation_describes_rather_than_names(self):
        """
        The sentence explains the setting; it is not part of its name.

        A13 moved this up a level: the explanation now describes the whole
        `<fieldset>` rather than one control, because the detail screen has one
        setting and several choices, and hanging the description off each choice
        would repeat it once per radio.

        """
        self.assertIn('fieldset.setAttribute("aria-describedby", note.id)', PANEL)

    def test_changes_are_announced(self):
        self.assertIn('announce(entry.label + ": " + choice[1] + ".")', PANEL)

    def test_it_re_renders_for_changes_from_elsewhere_but_not_its_own(self):
        """
        A13, and this is the slider fix stated as a rule.

        Gary: *"the text size slider is janky... for every increment I have to
        reclick the slider and move in one click, wait one click wait."*

        Every `input` event wrote a preference, every write notified
        subscribers, and this panel's subscriber calls `render()`, which begins
        `host.textContent = ""`. Dragging the slider destroyed the element being
        dragged on the first pixel of movement, so the browser had nothing left
        to send pointer events to.

        The subscription still exists, and must: Settings, the command palette
        and the keyboard shortcuts all change the same values, and a panel
        showing stale state is worse than no panel. What it must not do is
        repaint for a change it made itself.

        """
        self.assertIn("if (!applyingOwnChange)", PANEL)
        self.assertIn("applyingOwnChange = true", PANEL)
        # The guard is worthless if the flag is never lowered again, and a
        # `finally` is what survives a throwing subscriber.
        self.assertIn("} finally {", PANEL)
        self.assertNotIn("preferences.subscribe(function () { render(); })", PANEL)

    def test_the_layout_reflows_for_scaled_text_and_not_only_narrow_windows(self):
        """
        The same requirement, one level up.

        A12 split the flat option grid into named groups, so the container that
        has to reflow is now `__groups`. The rule it is protecting is unchanged
        and is the one UI1 established: a `minmax` floor rather than a width
        breakpoint, because scaling the text up is a different layout and a
        breakpoint measured in pixels gets it wrong.

        """
        block = CSS[CSS.index(".aetos-a11y-panel__groups {") :]
        block = block[: block.index("}")]
        self.assertIn("auto-fit", block)
        self.assertIn("minmax(", block)

    def test_the_controls_in_a_group_stack_rather_than_forming_a_second_grid(self):
        """
        Groups sit side by side; their contents do not.

        Measured before A12, the flat grid came out five columns wide on a
        1920px screen, so the reading order zig-zagged across the whole display.
        A group holds at most four short rows and a column of four is read in
        one movement.

        """
        block = CSS[CSS.index(".aetos-a11y-panel__options {") :]
        block = block[: block.index("}")]
        self.assertIn("flex-direction: column", block)


class TestTheSwitchIsFindable(TestCase):
    """
    Top right, outside the navigation landmark, in words.

    """

    def test_it_is_not_inside_the_navigation_landmark(self):
        """
        It does not take you anywhere; it changes which interface you are in.
        Grouped with Edit Layout and Help it read as a third button.

        """
        nav = TEMPLATE[TEMPLATE.index('id="aetos-toolbar"') :]
        nav = nav[: nav.index("</nav>")]
        self.assertNotIn('id="aetos-accessibility-toggle"', nav)

    def test_it_is_the_last_thing_in_the_status_bar(self):
        header = TEMPLATE[TEMPLATE.index('class="aetos-statusbar"') : TEMPLATE.index("</header>")]
        self.assertLess(header.index("</nav>"), header.index('id="aetos-accessibility-toggle"'))

    def test_it_says_words_rather_than_showing_an_icon(self):
        """
        An icon here would be a symbol somebody has to recognise before they can
        ask for help reading symbols.

        """
        self.assertIn(">Accessible mode</span>", TEMPLATE)

    def test_it_is_an_ordinary_button_in_the_tab_order(self):
        window = TEMPLATE[TEMPLATE.index('id="aetos-accessibility-toggle"') :][:400]
        self.assertIn('type="button"', window)
        self.assertNotIn("tabindex", window)

    def test_a_control_that_would_do_nothing_is_hidden(self):
        self.assertIn("orphanToggle.hidden = true", SHELL)

    def test_it_does_not_depend_on_the_command_palette(self):
        """
        The panel was created inside `if (palette)` at first, so a client
        without the palette module would have had no accessibility panel
        either.

        """
        creation = SHELL.index("var accessibilityPanel = window.AetosAccessibilityPanel")
        palette_block = SHELL.index("        if (palette) {")
        self.assertLess(creation, palette_block)
