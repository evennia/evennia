"""
Tests for A12 -- the axis every other gate in this project is blind to.

Gary, looking at the client with all 288 automated accessibility checks passing,
NVDA announcing the mode switch correctly, and axe clean across 144 scans:

    *"this doesnt feel accessible to me, but I dont have this particular
    challenge so its hard for me to tell, but what we have now 'feels' like we
    are way off the mark"*

He was right, and the reason is worth more than the fix. Everything this project
built measures **machine-readable correctness**: does a control have a name, a
role, a state; can a program reach it; will a screen reader say it. Measured
against WCAG 2.5.8 the client passed too -- twelve controls under 24x24, every
one of them inside the spacing exception.

What nothing measured was **legibility, density and effort**: what a sighted
person with low vision, dyslexia, ADHD or a tremor actually meets. One gate
touched that axis (`reflow`) and it only asked whether things fit.

Measured at 1920x1080 with the panel open, before A12:

    one typeface on all 86 text-bearing elements
    eleven controls in one section, in five columns
    242 words of prose, filling 53% of the viewport
    a console line 127 characters long
    `--aetos-target: 0px` on any pointer that is not coarse

And the finding that mattered most: accessible mode and standard mode rendered
**byte-identically**, because the mode masks preferences and every governed
preference defaults to its standard value.

Full write-up, with the sources and with two of my own measurements that turned
out to be wrong: `notes/a12-accessible-ux-research.md`.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

from .test_accessibility_panel import (
    CSS,
    PANEL,
    PREFS,
    _code_only,
    _function,
    _governed_paths,
)

SHELL_CSS = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")


def _block(source, selector):
    """
    One CSS rule body, by its opening selector.

    Args:
        source (str): The stylesheet.
        selector (str): The text that opens the rule, including the brace.

    Returns:
        str: Everything up to the closing brace.

    """
    start = source.index(selector)
    return source[start : source.index("\n}", start)]


def _prefs_function(name, until):
    """
    Slice one function out of `preferences.js`.

    The panel test module's `_function` reads `panel.js`; the preset machinery
    lives in the preferences module, so it needs its own.

    Args:
        name (str): The function's signature line.
        until (str): A later landmark.

    Returns:
        str: JavaScript source.

    """
    start = PREFS.index(name)
    return PREFS[start : PREFS.index(until, start)]


def _without_comments(source):
    """
    A stylesheet with its comments removed.

    Necessary for any test that scans for token *usage*: the comments in this
    project routinely quote the very thing being asserted about, including the
    undefined custom property this file checks for.

    Args:
        source (str): CSS.

    Returns:
        str: The same, minus `/* ... */`.

    """
    return re.sub(r"/\*.*?\*/", "", source, flags=re.S)


def _preset_block():
    """
    The `PRESETS` table's source.

    Returns:
        str: From the declaration to the lookup helper that follows it.

    """
    return PREFS[PREFS.index("var PRESETS = [") : PREFS.index("function presetNamed")]


def _preset_names():
    """
    The starting points, in the order they are offered.

    Returns:
        list: Preset names.

    """
    return re.findall(r'name:\s*"([\w-]+)"', _preset_block())


class TestTheModeDoesSomethingWhenYouTurnItOn(TestCase):
    """
    The sequence before A12, for somebody who needs help: find the switch, flip
    it, watch nothing happen, press Options, read 242 words across five columns,
    and answer eleven technical questions before the client is any easier to use.

    Every step was correct in isolation. The sum put the whole configuration
    burden on the person least able to spend it, in the name of not presuming.

    """

    def test_there_is_a_starting_point_for_each_thing_a_person_would_say(self):
        self.assertEqual(
            _preset_names(),
            ["low-vision", "calm", "screen-reader", "motor", "custom"],
        )

    def test_the_chooser_offers_no_more_than_coga_asks_for(self):
        """
        W3C's COGA guidance asks for no more than about seven options in any one
        section. The panel this replaces opened with eleven.

        """
        self.assertLessEqual(len(_preset_names()), 7)

    def test_setting_it_up_yourself_is_an_answer_rather_than_a_dismissal(self):
        """
        `"custom"` is a recorded preset rather than a way of closing the
        chooser. If it were not, the question would come back every session --
        which is the interruption this whole change exists to remove.

        """
        self.assertIn("custom", _preset_names())

    def test_only_the_preset_that_says_it_changes_nothing_changes_nothing(self):
        for chunk in _preset_block().split('name: "')[1:]:
            name = chunk[: chunk.index('"')]
            values = chunk[chunk.index("values:") :][:400]
            if name == "custom":
                self.assertIn("values: {}", values)
            else:
                self.assertNotIn("values: {}", values)

    def test_the_presets_are_named_in_a_persons_words_not_a_specifications(self):
        """
        Somebody who cannot read small text knows that about themselves. They do
        not necessarily know the phrase "reduced stimulation".

        """
        labels = re.findall(r'label:\s*"([^"]+)"', _preset_block())
        self.assertIn("Hard to see small text", labels)
        self.assertIn("I use a screen reader or braille display", labels)
        for label in labels:
            self.assertNotIn("stimulation", label.lower())
            self.assertNotIn("contrast ratio", label.lower())

    def test_applying_one_is_a_single_write(self):
        """
        One `update`, so subscribers repaint once rather than eleven times, and
        so a preset cannot be left half-applied.

        """
        body = _prefs_function("function applyPreset(name)", "return {")
        self.assertEqual(body.count("update("), 1)
        self.assertIn("patch.shell.preset = preset.name", body)

    def test_an_unknown_preset_changes_nothing(self):
        body = _prefs_function("function applyPreset(name)", "return {")
        self.assertIn("if (!preset)", body)

    def test_a_preset_is_ordinary_preferences_so_the_masking_rule_is_untouched(self):
        """
        `effective()` is the delicate part of A10. A preset is a bulk write of
        the same preferences somebody could set by hand, which is what keeps it
        out of there entirely -- nothing in the masking rule may learn that
        presets exist, or there are two sources of truth for what is in force.

        """
        body = _prefs_function("function effective()", "function activeAccommodations")
        self.assertNotIn("preset", body)
        self.assertNotIn("PRESETS", body)

    def test_the_choice_is_announced_together_with_the_way_back(self):
        """
        Somebody who has just changed the contrast and type size of their whole
        client on one keypress needs to hear that it is undoable before they
        need to hear anything else.

        """
        body = _function("function choose(name)", "function attach(")
        self.assertIn("can be changed", body)


class TestTheOptionsAreGrouped(TestCase):
    """
    Eleven controls in one flat grid measured five columns wide on a 1920px
    screen, so the reading order zig-zagged across the whole display with no
    headings to say where you were.

    """

    def _section_paths(self):
        block = PREFS[PREFS.index("var SECTIONS = [") : PREFS.index("var SCALE_MIN")]
        return re.findall(r'"(\w+\.\w+)"', block)

    def test_every_governed_option_is_in_a_named_group(self):
        """
        The panel renders anything missing under "More" rather than dropping it,
        so this failing costs a heading rather than a control. It should still
        never fail.

        """
        self.assertEqual(sorted(set(_governed_paths())), sorted(set(self._section_paths())))

    def test_no_group_holds_more_than_coga_asks_for(self):
        block = PREFS[PREFS.index("var SECTIONS = [") : PREFS.index("var SCALE_MIN")]
        for chunk in block.split("label:")[1:]:
            self.assertLessEqual(len(re.findall(r'"\w+\.\w+"', chunk)), 7)

    def test_a_group_carries_its_heading_as_its_accessible_name(self):
        """
        A screen reader should get the structure the eye gets, rather than
        eleven undifferentiated controls in a row.

        A13 made the groups `<section>` elements holding tiles rather than
        `<div role="group">` holding controls -- a named `<section>` is a region
        landmark, which is a better fit for something you navigate to than a
        group was.

        """
        body = _function("function buildHub(container)", "function tileFor")
        self.assertIn('createElement("section")', body)
        self.assertIn('group.setAttribute("aria-labelledby", heading.id)', body)


class TestTheClientIsLegibleAndNotOnlyCorrect(TestCase):
    """
    None of axe, the accessibility tree, the keyboard walk, the announcer or
    NVDA has an opinion about whether the result can comfortably be read.

    """

    def test_the_shell_and_the_game_text_are_set_in_different_faces(self):
        self.assertIn("--aetos-font-ui:", SHELL_CSS)
        self.assertIn("--aetos-font-mono:", SHELL_CSS)

    def test_the_ui_face_needs_no_download(self):
        """
        The contrib ships no font files and loads nothing from a CDN, so the
        proportional face has to be a system stack.

        """
        block = SHELL_CSS[SHELL_CSS.index("--aetos-font-ui:") :][:200]
        self.assertIn("system-ui", block)

    def test_game_output_keeps_its_fixed_width_face_regardless(self):
        """
        Not a preference, and this is the one place that is true. The server
        aligned that text by counting characters -- ASCII maps, score tables,
        the rules in Evennia's own connection screen. A proportional face does
        not make that prettier; it makes it wrong.

        """
        self.assertIn("font-family: var(--aetos-font-mono)", _block(SHELL_CSS, ".aetos-console {"))

    def test_what_you_type_is_set_like_what_it_becomes(self):
        """
        The command echoes into the console a moment later, and typing it in a
        different face makes the echo look like somebody else said it.

        """
        self.assertIn("font-family: var(--aetos-font-mono)", _block(SHELL_CSS, ".aetos-input {"))

    def test_the_face_of_the_clients_own_prose_is_a_choice(self):
        """
        Because the evidence splits, and any single answer is wrong for
        somebody. Vision Australia and APA Style say avoid monospace for long
        passages; Rello and Baeza-Yates measured dyslexic readers directly and
        found monospace *improved* reading performance.

        """
        self.assertIn('"visual.typeface"', PREFS)
        self.assertIn('.aetos-root[data-aetos-typeface="monospace"]', SHELL_CSS)

    def test_the_typeface_choice_survives_the_mode_switch(self):
        """
        Like text size, and for the same reason Gary gave about that: the shape
        of the letters is a basic property of a text interface rather than an
        accommodation somebody opts into.

        """
        entry = PREFS[PREFS.index('path: "visual.typeface"') :][:600]
        self.assertIn("revertsInStandardMode: false", entry)

    def test_the_reading_line_is_bounded_in_characters_at_every_size(self):
        """
        There *was* a cap, and measurement found it never fired: `max-width:
        120ch` applied only under `data-aetos-size="wide"`, and a 1920x1080
        monitor computes as `desktop` because at 16px text its effective width
        is 1680 against an 1800 boundary. The console measured 127 characters.

        A breakpoint was the wrong mechanism. "Is this line too long to track
        back from" is a question about characters, so the answer is in `ch`.

        """
        self.assertIn("--aetos-measure: 80ch", SHELL_CSS)
        # A17 moved the cap from the contents to the frame -- see
        # `test_the_frame_hugs_the_column_it_contains` below for why.
        block = _block(SHELL_CSS, "\n.aetos-widget--console {\n    max-width:")
        self.assertIn("max-width: var(--aetos-measure)", block)
        self.assertNotIn('data-aetos-size="wide"', block)

    def test_the_frame_hugs_the_column_it_contains(self):
        """
        A17. Capping `.aetos-console` bounded the reading line correctly and
        looked wrong doing it: the frame is `.aetos-widget--console`, so the
        border went on spanning the whole window while the text sat in an
        80-character column in the middle of it. At 175% text that is a ribbon
        of words floating in a very large empty box, with the Send button
        stranded far from the edge it appears to belong to.

        Measured after the change: a 1285px frame around a 1283px console.

        """
        block = _block(SHELL_CSS, "\n.aetos-widget--console {\n    max-width:")
        self.assertIn("margin-left: auto", block)
        self.assertIn("margin-right: auto", block)

    def test_there_is_a_target_floor_on_every_pointer_and_not_only_touch(self):
        """
        `--aetos-target` was `0px`, raised to 44px only under `pointer: coarse`,
        so a mouse user had no floor at all. Twelve controls measured under
        24x24 -- passing 2.5.8 through the *spacing* exception, which is to say
        by being far from their neighbours rather than by being big enough. A
        20px checkbox is still 20px to somebody with a tremor.

        """
        root = _block(SHELL_CSS, ":root {")
        self.assertIn("--aetos-target: 24px", root)
        self.assertNotIn("--aetos-target: 0px", root)

    def test_the_floor_is_applied_outside_the_coarse_pointer_block(self):
        """
        The token was only half the defect. The rules that used it lived inside
        `@media (pointer: coarse)`, which is how it spent its whole life as a
        no-op on a mouse even before the value was wrong.

        """
        before = SHELL_CSS[: SHELL_CSS.index("@media (pointer: coarse)")]
        self.assertIn("min-height: var(--aetos-target)", before)

    def test_the_panel_controls_use_that_floor(self):
        """
        A13 replaced the checkboxes and dropdowns with tiles and radio cards, so
        the elements that have to clear the floor are those.

        """
        for selector in (
            "\n.aetos-a11y-tile {",
            "\n.aetos-a11y-choice {",
            "\n.aetos-a11y-choice__input {",
            "\n.aetos-a11y-summary__item {",
        ):
            self.assertIn("var(--aetos-target)", _block(CSS, selector))

    def test_every_slider_is_sized_and_not_only_the_panels(self):
        """
        Keyed on the element, not on a class.

        The first version of this styled `.aetos-a11y-panel__range` alone and
        left the six volume sliders in the Sound widget exactly as they were --
        a fix that lands on one instance of a defect and declares the class of
        defect fixed. Measurement caught it because it counted every range on
        the page rather than the one that had just been changed.

        """
        self.assertIn('.aetos-root input[type="range"] {', CSS)
        self.assertNotIn(".aetos-a11y-panel__range::", CSS)

    def test_the_slider_thumb_is_sized_and_not_only_its_box(self):
        """
        The range measured 177x16. Height on the input alone only grows the box;
        the thumb is what gets grabbed, and it needs both vendor pseudo-elements
        or one engine keeps the small one.

        """
        for pseudo in ("::-webkit-slider-thumb", "::-moz-range-thumb"):
            self.assertIn(
                "var(--aetos-target)",
                _block(CSS, '.aetos-root input[type="range"]' + pseudo),
            )

    def test_body_text_has_somewhere_to_get_its_leading_from(self):
        self.assertIn("--aetos-line-height: 1.5", SHELL_CSS)

    def test_a_token_that_is_used_is_a_token_that_is_defined(self):
        """
        `--aetos-text-dim` was used four times and defined nowhere. With no
        fallback the declaration is invalid at computed-value time, so those
        elements rendered at full strength by accident rather than by decision.

        For an explanatory sentence full strength is the right answer, so it is
        now said out loud. The general rule matters more than this instance: a
        custom property with no definition and no fallback is a silent no-op,
        and the contrast validator cannot check a colour that is never applied.

        """
        for name, source in (("accessibility.css", CSS), ("aetos.css", SHELL_CSS)):
            body = _without_comments(source)
            used = set(re.findall(r"var\((--aetos-[\w-]+)\)", body))
            defined = set(re.findall(r"(--aetos-[\w-]+):", body + _without_comments(SHELL_CSS)))
            self.assertEqual(
                used - defined, set(), "%s uses custom properties nothing defines" % name
            )


class TestYouCanAlwaysGetBack(TestCase):
    """
    A13. Gary, on A12's starting-point chooser:

        *"I liked the screen with tiles when you first got to accessibility, but
        theres no way to get back once you pick one."*

    A screen somebody can enter and not leave is the worst thing an
    accessibility panel can be, because the person stuck in it is the person
    least able to guess at a way out. There are now three ways back and each is
    tested here: out of a setting, back to the starting points, and out of the
    panel entirely.

    """

    def test_a_setting_has_a_way_back_to_the_tiles(self):
        body = _function("function buildDetail(container, entry)", "function choiceList")
        self.assertIn("backToHub()", body)

    def test_the_way_back_is_the_first_thing_in_the_detail_screen(self):
        """
        First in the DOM, so it is the first thing Tab reaches and the first
        thing a screen reader meets inside the panel. A back button that is last
        is a back button somebody has to hunt for.

        """
        body = _function("function buildDetail(container, entry)", "function choiceList")
        self.assertLess(
            body.index("aetos-a11y-detail__back"),
            body.index('createElement("fieldset")'),
        )

    def test_the_starting_points_can_be_asked_for_again(self):
        body = _function("function reopenChooser()", "function focusFirstHeading")
        self.assertIn("preset: null", body)

    def test_asking_for_them_again_changes_no_settings(self):
        """
        Clearing the preset shows the tiles; it must not undo what the previous
        preset applied. Somebody looking at the starting points again has not
        asked to lose their text size.

        """
        body = _function("function reopenChooser()", "function focusFirstHeading")
        self.assertIn("Nothing has been changed", body)
        for path in ("visual.", "cognitive.", "screenReader."):
            self.assertNotIn(path, body)

    def test_closing_the_panel_returns_to_the_tiles(self):
        """
        So reopening never drops somebody into a detail screen they have no
        memory of leaving open.

        """
        body = _function("function toggleOptions()", "function attach(")
        self.assertIn('view = "hub"', body)

    def test_moving_between_screens_moves_focus_to_the_new_one(self):
        """
        Leaving focus on a tile that no longer exists drops it to the document,
        which is the thing A0's focus rules exist to prevent. This is the case
        WCAG allows deliberate focus movement: the activation *was* the request
        to go there.

        """
        for name, until in (
            ("function openDetail(path)", "function backToHub"),
            ("function backToHub()", "function reopenChooser"),
        ):
            self.assertIn("focusFirstHeading()", _function(name, until))


class TestTheSliderCanBeDragged(TestCase):
    """
    A13. Gary:

        *"the text size slider is janky I try to slide it smoothly back and
        forth but the slider redraws every time text sizes do so for every
        increment I have to reclick the slider and move in one click, wait one
        click wait."*

    Every `input` event wrote a preference, every write notified subscribers,
    and this panel's subscriber calls `render()`, which begins
    `host.textContent = ""`. So dragging the slider destroyed the element being
    dragged on the first pixel of movement.

    """

    def test_the_panel_does_not_repaint_for_its_own_writes(self):
        self.assertIn("applyingOwnChange = true", PANEL)
        self.assertIn("if (!applyingOwnChange)", PANEL)

    def test_it_still_repaints_for_changes_from_elsewhere(self):
        """
        The subscription must survive. Settings, the command palette and the
        keyboard shortcuts all write the same preferences, and a panel showing
        stale state is worse than no panel.

        """
        self.assertIn("preferences.subscribe(", PANEL)

    def test_the_flag_is_lowered_even_if_a_subscriber_throws(self):
        """
        A stuck flag would leave the panel permanently unable to notice an
        outside change -- a worse bug than the one being fixed, and a silent one.

        """
        body = _function("function set(path, value)", "function rangeControl")
        self.assertIn("} finally {", body)
        self.assertIn("applyingOwnChange = false", body)

    def test_there_is_a_way_to_change_text_size_without_dragging(self):
        """
        Dragging is the hardest gesture the client asks for and the least
        forgiving for a tremor -- and this is the one setting somebody may need
        to change *before* they can comfortably see anything else.

        """
        body = _function("function rangeControl(entry, id)", "function buildHub")
        self.assertIn("Smaller text", body)
        self.assertIn("Larger text", body)


class TestWhatIsOnIsVisibleWithoutOpeningAnything(TestCase):
    """
    A13. Gary: *"once options are selected I dont see them on the main
    screen."*

    Accessible mode masks rather than erases, settings survive a mode switch,
    and one preset can change five things at once -- so "what is in force right
    now" is a real question with a non-obvious answer, and the only way to
    answer it was to open the panel and read four groups.

    """

    def test_the_strip_lives_outside_the_panel(self):
        """
        Otherwise it would hide with it, which is precisely the complaint.

        """
        body = _function("function attach(container, button)", "return {")
        self.assertLess(
            body.index("aetos-accessibility-summary"),
            body.index("host.id = PANEL_ID"),
        )

    def test_it_says_nothing_when_there_is_nothing_to_say(self):
        """
        A permanent strip reading "no accommodations" would spend a line of the
        client's furniture telling people about the absence of a thing.

        """
        body = _function("function renderSummary()", "function buildHub")
        self.assertIn("summaryHost.hidden = !active.length", body)

    def test_standard_mode_lists_only_what_is_still_applying(self):
        """
        The confusing case, and the one worth getting right: somebody who
        switched to standard and kept their text size should see that their text
        size is still theirs and their contrast is not.

        """
        body = _function("function activeSettings()", "function defaultFor")
        self.assertIn("!isAccessible() && entry.revertsInStandardMode", body)

    def test_each_item_opens_the_setting_it_names(self):
        """
        So the strip is also the shortest route to changing one's mind, rather
        than a read-only label.

        """
        body = _function("function renderSummary()", "function buildHub")
        self.assertIn("openDetail(entry.path)", body)

    def test_it_does_not_announce_itself(self):
        """
        Not a live region. It changes as a result of something the player just
        did and was already told about, and announcing it again would say
        everything twice -- which is one of the three failures `announce.js`
        exists to catch.

        """
        body = _function("function attach(container, button)", "return {")
        window = body[: body.index("host.id = PANEL_ID")]
        self.assertNotIn("aria-live", window)


class TestDrillingIntoOneSetting(TestCase):
    """
    A13. Gary: *"I liked the tiles and then opening a box for that specific
    setting so if you are visually impaired, its easy to see choices and drill
    down into those choices."*

    """

    def test_a_tile_says_what_the_setting_is_set_to(self):
        """
        The half that turns a settings screen into an answer to "what is on".

        """
        body = _function("function tileFor(entry)", "function valueText")
        self.assertIn("valueText(entry)", body)

    def test_a_tiles_accessible_name_carries_the_value_too(self):
        """
        A button reading only "Text size" tells a screen reader user nothing
        about the state, and the state is half the reason the tile exists.

        A17 composes that name from the visible text with `aria-labelledby`
        rather than an `aria-label` string. Two reasons, both Heydon
        Pickering's and both previously ignored here: `aria-label` is skipped by
        machine translation, so a player reading the client in another language
        would meet an English accessible name on every tile; and a label
        assembled from ids cannot drift from what is on screen, which matters
        most for voice control, where somebody says what they see.

        Verified against Chrome's own accessibility tree, which computes
        "Text size 175%" for the first tile.

        """
        body = _function("function tileFor(entry)", "function valueText")
        self.assertIn('"aria-labelledby", name.id + " " + value.id', body)
        self.assertNotIn('setAttribute("aria-label"', body)

    def test_the_summary_chips_do_not_say_more_than_they_show(self):
        """
        The chip's visible text already names the setting and its value, and it
        is a button -- the same affordance a sighted person infers from the way
        it is drawn. An `aria-label` reading "Change Contrast, currently High
        contrast" was more words for the same information, untranslated, and a
        parity break rather than an addition.

        """
        body = _function("function renderSummary()", "function buildHub")
        self.assertNotIn('setAttribute(\n                    "aria-label"', body)
        self.assertNotIn('"aria-label"', body)

    def test_the_strip_stands_down_while_the_panel_is_open(self):
        """
        The panel lists every one of these settings and its value a few pixels
        below. Leaving the strip up duplicates the whole thing -- twice the
        reading for somebody going through it with a screen reader. It exists to
        answer "what is on" *without* opening anything.

        """
        body = _function("function renderSummary()", "function buildHub")
        self.assertIn("!active.length || isOpen()", body)

    def test_choices_are_all_visible_rather_than_behind_a_dropdown(self):
        """
        A `<select>` shows one option at a time in small text and hides the rest
        behind an interaction -- the wrong control for somebody who drilled in
        *because* reading small text is hard.

        """
        self.assertNotIn('createElement("select")', PANEL)
        self.assertIn('input.type = "radio"', PANEL)

    def test_the_chosen_choice_is_not_marked_by_colour_alone(self):
        """
        The radio carries the state natively; the border weight is the visual
        emphasis, and weight survives forced colours where an accent does not.

        """
        block = _block(CSS, ".aetos-a11y-choice--chosen {")
        self.assertIn("border-width", block)

    def test_it_does_not_use_a_selector_the_published_floor_lacks(self):
        """
        `:has()` needs Chrome 105 and Firefox 121 against a floor of Chrome 87
        and Firefox 75 -- and the compatibility gate would not have caught it,
        because that gate only knows the features listed in its own table. A
        selector nothing tests is a floor claim nobody is checking.

        """
        self.assertNotIn(":has(", _without_comments(CSS))
        self.assertNotIn(":has(", _without_comments(SHELL_CSS))


class TestQuietIsNotDeaf(TestCase):
    """
    A14b. Gary, with the announcer wired up and a screen reader on:
    *"ok I have the reading turned on but it doesnt read out loud"*.

    Quiet mode dropped `normal` priority as well as `background`, and every line
    of ordinary game text arrives under the category `other`, which is `normal`.
    So "fewer interruptions" silenced the game itself.

    Invisible to a sighted player: the console is right there and nothing appears
    to be lost. Total silence for somebody listening, because the console is
    deliberately `aria-live="off"` and announcements are the only channel they
    have. The setting's own description -- *"Nothing is lost, it is still in the
    log"* -- is true only if you can read the log, which is precisely the
    assumption this client should never make.

    The comment above the rule said "quiet is not deaf" while the rule made it
    deaf. A claim in a comment is not a property of the code, which this project
    has now learned five separate times.

    """

    ANNOUNCER = (
        Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "announcer.js"
    ).read_text(encoding="utf-8")

    def _quiet_rule(self):
        start = self.ANNOUNCER.index('preferenceValue("cognitive.quietMode"')
        return self.ANNOUNCER[start : start + 260]

    def test_quiet_mode_does_not_suppress_ordinary_game_output(self):
        rule = self._quiet_rule()
        self.assertIn('priority === "background"', rule)
        self.assertNotIn('priority === "normal"', rule)

    def test_ordinary_game_text_is_still_normal_priority(self):
        """
        The fix is in the quiet rule, not in reclassifying game text as
        important -- which would have made it outrank a tell.

        """
        block = self.ANNOUNCER[self.ANNOUNCER.index("var CATEGORY_PRIORITY = {") :][:600]
        self.assertIn('other: "normal"', block)
        self.assertIn('tell: "important"', block)

    def test_the_setting_no_longer_promises_speech_the_client_does_not_produce(self):
        """
        The description read "What is spoken aloud or sent to a braille
        display", which reads as a promise that Aetos speaks. It does not: it
        writes to a live region and a screen reader voices it. With no screen
        reader running the setting appears to do nothing, and the person most
        likely to meet that is somebody setting up assistive technology for the
        first time.

        """
        entry = PREFS[PREFS.index('path: "screenReader.announcementMode"') :][:900]
        self.assertIn("Aetos does not speak by itself", entry)


class TestAStartingPointPutsYouAtAKnownPlace(TestCase):
    """
    A14b. Presets were purely additive, so picking "Too much going on" and then
    "I use a screen reader" left `quietMode` on from the first -- and quiet mode
    silenced every line of game output, so the second preset produced a client
    that said nothing at all.

    Nobody chose that combination and nothing on screen explained it.

    """

    def _apply_preset(self):
        return _prefs_function("function applyPreset(name)", "return {")

    def test_applying_one_writes_every_key_any_preset_touches(self):
        body = self._apply_preset()
        self.assertIn("PRESET_KEYS.forEach", body)
        self.assertIn("DEFAULTS[parts[0]][parts[1]]", body)

    def test_the_chosen_presets_values_win_over_those_defaults(self):
        """
        Order matters: defaults first, then the preset's own values on top.

        """
        body = self._apply_preset()
        self.assertLess(
            body.index("PRESET_KEYS.forEach"),
            body.index("Object.keys(preset.values)"),
        )

    def test_the_key_list_is_derived_rather_than_maintained_by_hand(self):
        """
        A list written beside the table is a list somebody forgets to update
        when they add a value to a preset -- which brings back exactly the
        leftover-setting bug it exists to prevent.

        """
        self.assertIn("var PRESET_KEYS = (function ()", PREFS)
        self.assertIn("PRESETS.forEach", PREFS)

    def test_it_does_not_clear_preferences_no_preset_has_an_opinion_about(self):
        """
        A preference somebody set by hand is theirs. Clearing it would make
        picking a starting point a destructive act, which is the opposite of
        what "you can change any of it afterwards" promises.

        """
        keys = re.findall(r'"(\w+\.\w+)"', _preset_block())
        for untouched in ("braille.compactStatus", "keyboard.singleKeyShortcuts"):
            self.assertNotIn(untouched, keys)


class TestTheClientReadsTheGameAloud(TestCase):
    """
    A15. Gary turned on the setting called "How much is announced", played, and
    heard nothing: *"ok I have the reading turned on but it doesnt read out
    loud"*.

    The client was behaving exactly as designed, and the design was wrong. Aetos
    wrote announcements into an ARIA live region and left the speaking to a
    screen reader -- correct for somebody running NVDA, silence for everybody
    else, and the setting's own wording promised speech the client never
    produced.

    The population who want text read to them is far larger than the population
    running a screen reader: dyslexia, low vision without assistive technology,
    tired eyes at the end of a long session, or simply wanting to listen.
    Telling all of them to install NVDA is not an accessibility answer.

    """

    SPEECH = (Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "speech.js").read_text(
        encoding="utf-8"
    )
    ACCESS = (
        Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "accessibility.js"
    ).read_text(encoding="utf-8")

    def test_it_uses_the_platform_rather_than_a_dependency(self):
        """
        `speechSynthesis` is part of every browser at the published floor. The
        contrib ships no audio, downloads nothing, and sends nothing anywhere.

        """
        self.assertIn("speechSynthesis", self.SPEECH)
        for forbidden in ("http://", "https://", "import ", "require("):
            self.assertNotIn(forbidden, self.SPEECH)

    def test_it_is_off_until_somebody_asks(self):
        """
        A client that starts talking is alarming, and for a screen reader user
        it is two voices over the same text.

        """
        block = PREFS[PREFS.index("        speech: {") :][:400]
        self.assertIn("enabled: false", block)

    def test_it_does_not_try_to_detect_a_screen_reader(self):
        """
        A.72 forbids it: detection is fingerprinting, and a player must never
        have to disclose a disability to play. So the overlap with a screen
        reader is handled by saying so in the control's own description rather
        than by guessing.

        """
        for sniff in ("userAgent", "navigator.plugins", "isScreenReader"):
            self.assertNotIn(sniff, self.SPEECH)
        entry = PREFS[PREFS.index('path: "speech.enabled"') :][:800]
        self.assertIn("if you already use a screen reader", entry)

    def test_speech_renders_the_announcers_decisions_rather_than_making_its_own(self):
        """
        Category, priority, per-category preferences, announcement mode, quiet
        mode, review mode and burst aggregation are all decided in the
        announcer. Duplicating any of that here would guarantee the two
        eventually disagreed about what a player asked for.

        """
        for policy in ("category", "quietMode", "announcementMode", "FLOOD", "reviewing"):
            self.assertNotIn(policy, self.SPEECH)

    def test_the_hook_is_where_the_decision_was_already_made(self):
        announcer = (
            Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "announcer.js"
        ).read_text(encoding="utf-8")
        self.assertIn("if (speak) {", announcer)
        self.assertIn("speak(message, { urgent: !!urgent })", announcer)

    def test_urgent_messages_interrupt_and_the_rest_queue(self):
        """
        The same rule as the two live regions, for the same reason: a channel
        that interrupts constantly stops being an interruption.

        """
        body = self.SPEECH[self.SPEECH.index("function speak(message, options)") :][:1400]
        self.assertIn("settings.urgent", body)
        self.assertIn("synth.cancel()", body)

    def test_there_is_a_way_to_stop_it(self):
        """
        Speech that cannot be stopped is worse than no speech.

        """
        self.assertIn("function stop()", self.SPEECH)
        self.assertIn("stop: stop", self.SPEECH)

    def test_turning_it_off_stops_it_mid_sentence(self):
        """
        Otherwise switching it off lets the current utterance run to the end,
        which reads as the control not working -- at exactly the moment somebody
        wants the talking to stop.

        """
        body = self.SPEECH[self.SPEECH.index("function watchPreferences()") :][:700]
        self.assertIn("stop()", body)

    def test_it_waits_for_a_gesture_before_speaking(self):
        """
        Browsers refuse audio until the player has interacted with the page, and
        speaking before that leaves some synthesisers dropping the next
        utterance too.

        """
        self.assertIn("function unlock()", self.SPEECH)
        self.assertIn("!permitted", self.SPEECH)
        self.assertIn("speech.unlock()", self.ACCESS)

    def test_pending_speech_is_discarded_rather_than_queued_before_that(self):
        """
        A queue would empty itself in one burst the moment somebody clicked,
        reading out everything that had happened since the page loaded.

        """
        body = self.SPEECH[self.SPEECH.index("function speak(message, options)") :][:400]
        self.assertIn("return false", body)

    def test_a_failing_synthesiser_does_not_take_the_announcer_with_it(self):
        """
        Degrade, never raise: this runs in a websocket-driven client and the
        speech call sits inside the announcer's write path.

        """
        self.assertIn("catch (err)", self.SPEECH)

    def test_a_missing_voice_falls_back_rather_than_refusing(self):
        """
        Profiles move between machines and language packs get removed. Silence
        is the failure this whole module exists to fix, so it would be a strange
        way to report a missing voice.

        """
        body = self.SPEECH[self.SPEECH.index("function chosenVoice()") :][:1200]
        self.assertIn("return null", body)

    def test_the_voice_is_stored_by_name_rather_than_by_index(self):
        """
        Voice lists differ between machines, so an index would silently select a
        different voice on another one.

        """
        block = PREFS[PREFS.index("        speech: {") :][:600]
        self.assertIn("voice: null", block)

    def test_it_survives_the_mode_switch(self):
        """
        Somebody who asked the client to read to them has not asked for that to
        stop when they look at the standard interface -- which would be the same
        class of defect as quiet mode silencing the game.

        """
        entry = PREFS[PREFS.index('path: "speech.enabled"') :][:900]
        self.assertIn("revertsInStandardMode: false", entry)


class TestABackgroundedTabDoesNotTalk(TestCase):
    """
    A16. From Heydon Pickering's Notifications article, which is the one piece
    of live-region guidance with a concrete remedy rather than a principle.

    A MUD sits in a background tab for hours, and a live region keeps firing
    while it does -- so a screen reader reading somebody's email is interrupted
    by a room description from a game they are not currently playing.

    """

    ACCESS = (
        Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "accessibility.js"
    ).read_text(encoding="utf-8")

    def _block(self):
        """
        The visibility handler, with its comments removed.

        Stripped, because every one of the first three assertions in this class
        failed against its own explanation: the block `push`es the original
        attributes, and the comment inside `restore` uses the word "speech" to
        explain why speech is *not* silenced. Asserting a string is absent from
        source that documents that very string is a trap this project has now
        met often enough to have a helper for it.

        Returns:
            str: JavaScript, no comments.

        """
        start = self.ACCESS.index('document.addEventListener("visibilitychange"')
        block = self.ACCESS[self.ACCESS.rindex("(function () {", 0, start) : start + 400]
        return _code_only(block)

    def test_the_regions_are_silenced_while_the_document_is_hidden(self):
        block = self._block()
        self.assertIn('setAttribute("role", "none")', block)
        self.assertIn('setAttribute("aria-live", "off")', block)

    def test_the_original_attributes_are_captured_rather_than_assumed(self):
        """
        The two regions are not symmetrical: polite is `role="status"
        aria-live="polite"`, urgent is `role="alert"` with no `aria-live` at
        all. Restoring an assumed pair would quietly give the urgent region an
        attribute it never had.

        """
        block = self._block()
        self.assertIn('getAttribute("role")', block)
        self.assertIn('getAttribute("aria-live")', block)

    def test_a_state_it_was_already_in_is_restored_by_removal(self):
        block = self._block()
        self.assertIn('removeAttribute("aria-live")', block)
        self.assertIn('removeAttribute("role")', block)

    def test_it_checks_the_state_at_boot_and_not_only_on_change(self):
        """
        A tab can be in the background from the start -- opened in a new tab, or
        restored by the browser on start-up -- and `visibilitychange` never
        fires for that.

        """
        block = self._block()
        self.assertIn("apply(!!document.hidden)", block)

    def test_nothing_is_queued_for_replay(self):
        """
        Replaying on return would read twenty minutes of combat to somebody who
        just came back to the tab. Nothing is lost either way: the console holds
        the transcript and the history widget can search it, which is the
        condition Heydon puts on dropping notifications at all.

        """
        block = self._block()
        # Not "push(" -- the block legitimately pushes the *original attributes*
        # it has to restore. What must not exist is a store of message text.
        for queueing in ("backlog", "deferred", "queue", "replay", "pending"):
            self.assertNotIn(queueing, block)
        self.assertNotIn("textContent =", block.split("function restore")[0])

    def test_speech_is_deliberately_not_silenced_with_them(self):
        """
        The asymmetry is the point. A screen reader user with the tab in the
        background is reading a *different window* and must not be interrupted.
        Somebody using Aetos's own read-aloud has very likely backgrounded the
        tab in order to listen, and silencing that would break the main reason
        the feature exists.

        Structural rather than incidental: speech is driven from the announcer's
        `write()`, which still runs -- only the region attributes change.

        """
        block = self._block()
        self.assertNotIn("speech", block)
        self.assertIn(
            "speak(message, { urgent: !!urgent })",
            (Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "announcer.js").read_text(
                encoding="utf-8"
            ),
        )

    def test_the_regions_come_back_empty(self):
        """
        Messages arriving while hidden are still *written* -- only the
        attributes are off -- so without clearing, the region returns holding
        the last thing that happened while nobody was looking, and making it
        live again can announce that stale line out of nowhere.

        Measured on the first version of this fix, which had exactly that bug:
        the region came back holding a message sent while the tab was hidden.

        """
        start = self.ACCESS.index("function restore(region, was)")
        window = _code_only(self.ACCESS[start : start + 1400])
        self.assertIn('region.textContent = ""', window)
        # Cleared before the role is restored, so the clearing itself happens
        # while the region is still inert.
        self.assertLess(
            window.index('region.textContent = ""'),
            window.index('setAttribute("role", was.role)'),
        )


class TestTheSettingsDoNotTakeTheWholeScreen(TestCase):
    """
    A17. Gary, with the panel open at 175% text:

    The options filled roughly seventy per cent of the viewport and the console
    was a three-line sliver at the bottom, which defeats the reason the panel is
    inline in the first place. A9's argument still holds -- somebody adjusting
    contrast or text size should be able to watch the game text change while
    they do it, and a modal covering the thing you are adjusting *for* is a
    worse design. But it was pushing rather than sharing.

    """

    def test_the_panel_is_bounded_and_scrolls_its_own_overflow(self):
        block = _block(CSS, ".aetos-a11y-panel {")
        self.assertIn("max-height:", block)
        self.assertIn("overflow-y: auto", block)

    def test_it_is_not_a_dialog(self):
        """
        Still inline. The whole point is watching the client change underneath
        the control you are moving.

        """
        self.assertNotIn('"dialog"', PANEL)
        self.assertNotIn("aria-modal", PANEL)

    def test_a_scrollable_panel_is_focusable_and_a_fitting_one_is_not(self):
        """
        `tabindex="0"` on a scroll container buys native arrow-key, Page Up and
        Page Down scrolling with no key handler, and the panel is already a
        labelled `role="region"` so focusing it announces what it is.

        Only while it overflows: a tab stop that does nothing is, in Heydon
        Pickering's reading, a WCAG 2.4.3 Focus Order failure -- and an
        irritation in anybody's.

        """
        body = _function("function markScrollable()", "function attach(")
        self.assertIn("host.scrollHeight > host.clientHeight", body)
        self.assertIn('host.setAttribute("tabindex", "0")', body)
        self.assertIn('host.removeAttribute("tabindex")', body)

    def test_it_is_recomputed_on_every_render(self):
        """
        Whether it overflows depends on the text size, the viewport and which
        screen the panel is showing -- all of which change without a reload.

        """
        body = _function("function render()", "function markScrollable")
        self.assertIn("markScrollable()", body)


class TestFocusModeActuallyCollapsesTheGrid(TestCase):
    """
    A17, and a specificity bug that was invisible at ordinary text sizes.

    Focus mode hides the side regions and collapses the workspace grid to a
    single column. The collapse rule was `[data-aetos-focus-mode="true"]
    .aetos-workspace` -- specificity (0,2,0) -- against the responsive templates
    at `.aetos-root[data-aetos-size="tablet"] .aetos-workspace`, which is (0,3,0)
    and therefore won.

    So focus mode collapsed the grid only at the sizes that had no template of
    their own. Because the breakpoints are measured in text, a 1600px window at
    175% computes as "tablet" -- the tablet template restored a `--aetos-column`
    sidebar track, focus mode dutifully hid the region *inside* it, and what was
    left was a dead 339px column and a console frame that looked badly
    off-centre for no visible reason.

    Measured before: main region at x=339 with every side region `display:
    none`. After: x=10, and the frame centred with 233px either side.

    """

    def test_the_collapse_rule_outranks_the_responsive_templates(self):
        collapse = SHELL_CSS.index('[data-aetos-focus-mode="true"] .aetos-root .aetos-workspace')
        tablet = SHELL_CSS.index('.aetos-root[data-aetos-size="tablet"] .aetos-workspace')
        # Higher specificity, and later in the file, so it wins either way.
        self.assertGreater(collapse, tablet)

    def test_it_is_scoped_from_the_element_that_carries_the_attribute(self):
        """
        The first attempt at this fix scoped the selector through
        `.aetos-root[data-aetos-focus-mode]`, but the attribute is set on
        `document.documentElement` -- so that selector matched nothing at all
        and changed nothing. Caught by re-measuring rather than by reading it
        back.

        """
        self.assertIn(
            ':root[data-aetos-focus-mode="true"] .aetos-root .aetos-workspace',
            SHELL_CSS,
        )
        self.assertNotIn('.aetos-root[data-aetos-focus-mode="true"]', SHELL_CSS)

    def test_the_attribute_really_is_set_on_the_document_element(self):
        """
        If this ever moves onto `.aetos-root`, the selector above stops matching
        and focus mode silently stops collapsing the grid again.

        """
        access = (
            Path(AETOS_STATIC_DIR) / "aetos" / "js" / "accessibility" / "accessibility.js"
        ).read_text(encoding="utf-8")
        self.assertIn('root.setAttribute("data-aetos-focus-mode"', access)
        self.assertIn("settings.root || document.documentElement", access)
