"""
Tests for M19 -- themes and contrast validation.

Addendum A.55, `A11Y-VIS-003`: themes MUST meet contrast requirements, theme
validation MUST be part of theme acceptance, and a theme that fails MUST produce
a warning.

The most valuable test here is the one that checks Aetos's *own* themes, read
out of the stylesheet that actually ships. A palette chosen by eye passes for
the person who chose it -- that is not a criticism of anyone's judgement, it is
what having particular eyes means. The author of an illegible theme is,
necessarily, somebody who could read it.

It found one immediately: `--aetos-border` had been 1.37:1 against the
background since M4.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, contrast

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
CSS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "css"


def _read(relative):
    """
    Read a client module.

    Args:
        relative (str): Path under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / relative).read_text(encoding="utf-8")


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


THEMES = _read("themes/themes.js")
CONTRAST = _read("themes/contrast.js")
SETTINGS = _read("settings.js")
SHELL = _read("aetos.js")
BASE_CSS = (CSS_DIR / "aetos.css").read_text(encoding="utf-8")
A11Y_CSS = (CSS_DIR / "accessibility.css").read_text(encoding="utf-8")


def _shipped_theme(selector=None):
    """
    Build the token set a shipped theme actually produces.

    Read from the stylesheet rather than from a copy in Python, so the test
    checks what ships instead of something that can drift from it.

    Args:
        selector (str, optional): A theme block to layer over the base tokens.

    Returns:
        dict: Token name mapped to a colour, colours only.

    """
    tokens = contrast.extract_theme_tokens(BASE_CSS, ":root")
    tokens.update(contrast.extract_theme_tokens(A11Y_CSS, ":root"))
    if selector:
        tokens.update(contrast.extract_theme_tokens(A11Y_CSS, selector))
    return {name: value for name, value in tokens.items() if contrast.parse_color(value)}


class TestTheRatioCalculation(TestCase):
    """
    WCAG 2.x, a published and fixed calculation. Pinned to known values so the
    two implementations -- Python here, JavaScript in the editor -- cannot
    quietly disagree.

    """

    def test_black_on_white_is_the_maximum(self):
        self.assertAlmostEqual(contrast.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_identical_colours_are_the_minimum(self):
        self.assertAlmostEqual(contrast.contrast_ratio("#5aa9e6", "#5aa9e6"), 1.0, places=4)

    def test_the_order_of_the_arguments_does_not_matter(self):
        forward = contrast.contrast_ratio("#14171c", "#d7dce3")
        backward = contrast.contrast_ratio("#d7dce3", "#14171c")
        self.assertAlmostEqual(forward, backward, places=6)

    def test_known_values(self):
        """
        Fixtures both implementations are held to.

        """
        cases = (
            ("#767676", "#ffffff", 4.54),
            ("#ffffff", "#0000ff", 8.59),
            ("#5aa9e6", "#14171c", 7.06),
        )
        for foreground, background, expected in cases:
            self.assertAlmostEqual(
                contrast.contrast_ratio(foreground, background), expected, places=2
            )

    def test_short_hex_is_expanded(self):
        self.assertAlmostEqual(
            contrast.contrast_ratio("#fff", "#000"),
            contrast.contrast_ratio("#ffffff", "#000000"),
            places=6,
        )

    def test_unparseable_colours_return_none(self):
        """
        Hex only. Supporting `rgb()`, `hsl()` and `color-mix()` would mean
        reimplementing a CSS colour parser in order to reject one of them, and
        every format that cannot be checked is a format a failing theme can
        hide in.

        """
        for value in ("rgb(0,0,0)", "hsl(0 0% 0%)", "red", "", None, "#12345"):
            self.assertIsNone(contrast.contrast_ratio(value, "#ffffff"))


class TestTheShippedThemesPass(TestCase):
    """
    A11Y-VIS-003 turned on Aetos itself.

    This is the whole point of the milestone. A high-contrast theme that fails
    contrast is the exact failure the requirement exists to prevent, and it is
    not hypothetical -- it is the most common way accessibility themes go wrong,
    because the muted colour is chosen to recede and then recedes past
    legibility.

    """

    def test_the_default_theme_passes_every_pair(self):
        result = contrast.validate_theme(_shipped_theme())
        self.assertEqual(
            result["failures"],
            [],
            "the default theme fails contrast: "
            + "; ".join(contrast.describe_failures(result["failures"])),
        )

    def test_the_high_contrast_preset_passes_every_pair(self):
        result = contrast.validate_theme(_shipped_theme(':root[data-aetos-contrast="high"]'))
        self.assertEqual(
            result["failures"],
            [],
            "the high-contrast preset fails contrast: "
            + "; ".join(contrast.describe_failures(result["failures"])),
        )

    def test_the_light_theme_passes_every_pair(self):
        """
        Light themes fail contrast just as readily as dark ones, usually on the
        muted text.

        """
        block = THEMES[THEMES.index('id: "paper"') :]
        block = block[: block.index("}")]
        tokens = dict(re.findall(r'"(--aetos-[a-z-]+)": "(#[0-9a-f]+)"', block))
        self.assertTrue(tokens, "could not read the Paper theme's tokens")
        result = contrast.validate_theme(tokens)
        self.assertEqual(
            result["failures"],
            [],
            "; ".join(contrast.describe_failures(result["failures"])),
        )

    def test_every_required_pair_is_actually_checked(self):
        """
        A pair whose tokens are absent is skipped, so a theme missing a token
        could pass by having nothing to check. The shipped themes must declare
        all of them.

        """
        result = contrast.validate_theme(_shipped_theme())
        self.assertEqual(result["checked"], len(contrast.REQUIRED_PAIRS))

    def test_the_border_regression(self):
        """
        The defect this milestone found, pinned.

        `--aetos-border` was 1.37:1 against the background. Since a panel
        differs from the page by only about 1.09:1, that border is the *only*
        thing separating one region from another -- so there were effectively
        no panel edges for anyone with reduced contrast sensitivity. Wrong
        since M4, and invisible to everyone who looked at it.

        """
        tokens = _shipped_theme()
        ratio = contrast.contrast_ratio(tokens["--aetos-border"], tokens["--aetos-bg"])
        self.assertGreaterEqual(ratio, contrast.AA_NON_TEXT)


class TestTheValidatorItself(TestCase):
    """What it reports, and what it declines to report."""

    def test_a_failing_pair_is_named_with_its_ratio_and_reason(self):
        """
        A ratio alone tells an author they are wrong without telling them what
        to change.

        """
        result = contrast.validate_theme({"--aetos-text": "#777777", "--aetos-bg": "#808080"})
        self.assertEqual(len(result["failures"]), 1)
        failure = result["failures"][0]
        self.assertEqual(failure["foreground"], "--aetos-text")
        self.assertEqual(failure["required"], contrast.AA_NORMAL_TEXT)
        self.assertIn("body text", failure["reason"])

        sentence = contrast.describe_failures(result["failures"])[0]
        self.assertIn("--aetos-text", sentence)
        self.assertIn("body text", sentence)
        self.assertIn("4.5", sentence)

    def test_a_missing_token_is_skipped_not_failed(self):
        """
        A partial theme inherits the rest, and reporting an inherited pair as
        this theme's failure would send an author looking in the wrong place.

        """
        result = contrast.validate_theme({"--aetos-text": "#ffffff"})
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["checked"], 0)

    def test_text_and_non_text_have_different_thresholds(self):
        """
        AA, not AAA. Committing to 7:1 would rule out most legible palettes and
        push games towards ignoring the system entirely, which helps nobody.

        """
        thresholds = {pair[2] for pair in contrast.REQUIRED_PAIRS}
        self.assertEqual(thresholds, {contrast.AA_NORMAL_TEXT, contrast.AA_NON_TEXT})

    def test_borders_and_the_focus_ring_are_checked(self):
        """
        Borders carry structure: they are what separates one region from
        another for somebody who cannot rely on a subtle background shift.

        """
        checked = {pair[0] for pair in contrast.REQUIRED_PAIRS}
        self.assertIn("--aetos-border", checked)
        self.assertIn("--aetos-focus", checked)

    def test_the_muted_colour_is_checked_against_both_surfaces(self):
        """
        Where contrast themes usually fail.

        """
        pairs = {(pair[0], pair[1]) for pair in contrast.REQUIRED_PAIRS}
        self.assertIn(("--aetos-text-muted", "--aetos-bg"), pairs)
        self.assertIn(("--aetos-text-muted", "--aetos-panel"), pairs)


class TestTheTwoImplementationsAgree(TestCase):
    """
    One published formula, implemented twice: Python for the shipped themes,
    JavaScript for a player's own. They are pinned to the same pairs and
    thresholds, because a validator that passes in one place and fails in the
    other is worse than either alone.

    """

    def test_the_same_pairs_are_required(self):
        block = CONTRAST[CONTRAST.index("var REQUIRED_PAIRS = [") :]
        block = block[: block.index("\n    ];")]
        js_pairs = set(re.findall(r'\["(--aetos-[a-z-]+)", "(--aetos-[a-z-]+)"', block))
        py_pairs = {(pair[0], pair[1]) for pair in contrast.REQUIRED_PAIRS}
        self.assertEqual(js_pairs, py_pairs)

    def test_the_same_thresholds(self):
        self.assertIn("var AA_NORMAL_TEXT = 4.5;", CONTRAST)
        self.assertIn("var AA_NON_TEXT = 3.0;", CONTRAST)
        self.assertEqual(contrast.AA_NORMAL_TEXT, 4.5)
        self.assertEqual(contrast.AA_NON_TEXT, 3.0)

    def test_both_accept_hex_only(self):
        self.assertIn("/^#([0-9a-f]{3}|[0-9a-f]{6})$/", CONTRAST)

    def test_both_use_the_wcag_luminance_coefficients(self):
        self.assertIn("0.2126", CONTRAST)
        self.assertIn("0.7152", CONTRAST)
        self.assertIn("0.0722", CONTRAST)
        self.assertIn("0.03928", CONTRAST)


class TestThemesCannotBreakThings(TestCase):
    """
    A theme changes colours. That is the entire permitted surface.

    """

    def test_only_colour_tokens_may_be_set(self):
        """
        A theme that could ship CSS could hide content, override a focus ring,
        animate something the player asked not to be animated, or reintroduce
        every accessibility defect the client spent a year removing.

        """
        block = THEMES[THEMES.index("var TOKENS = [") :]
        block = block[: block.index("\n    ];")]
        tokens = set(re.findall(r'"(--aetos-[a-z-]+)"', block))
        for structural in (
            "--aetos-space",
            "--aetos-font-size",
            "--aetos-column",
            "--aetos-radius",
            "--aetos-target",
            "--aetos-scale",
        ):
            self.assertNotIn(structural, tokens, "a theme must not be able to set %s" % structural)

    def test_a_theme_never_injects_style_or_markup(self):
        for forbidden in ("innerHTML", 'createElement("style")', "insertRule", "cssText", "<style"):
            self.assertNotIn(forbidden, THEMES, "themes.js uses %r" % forbidden)

    def test_unparseable_colours_are_dropped_at_normalisation(self):
        """
        Rather than passed to the browser, which would silently ignore them and
        leave the author wondering which of their ten colours did not take.

        """
        body = _function_body(THEMES, "function normalize(raw)", "function createThemes")
        self.assertIn("window.AetosContrast.parseColor(value)", body)

    def test_switching_themes_removes_what_the_new_one_does_not_set(self):
        """
        Otherwise one colour from the previous theme is stranded in the new
        one -- a combination neither author ever looked at, and therefore one
        nobody validated.

        """
        body = _function_body(THEMES, "function apply(id, options)", "function effectiveTokens")
        self.assertIn("root.style.removeProperty(token)", body)

    def test_a_partial_theme_is_validated_on_what_it_results_in(self):
        """
        A theme setting six of ten tokens inherits the other four, so
        validating only what it declares would miss exactly the failures that
        partial themes cause.

        """
        body = _function_body(THEMES, "function effectiveTokens(theme)", "function validate(theme)")
        self.assertIn("getComputedStyle(root)", body)

    def test_built_in_themes_cannot_be_deleted(self):
        """
        A player who deleted the only theme they could read would have no way
        back.

        """
        body = _function_body(THEMES, "function remove(id)", "return {")
        self.assertIn("theme.builtin", body)

    def test_the_default_theme_sets_nothing(self):
        """
        "Default" means "whatever the stylesheet says", so removing a theme
        restores the shipped look exactly rather than a copy that can drift
        from it.

        """
        block = THEMES[THEMES.index('id: "default"') :]
        block = block[: block.index("},")]
        self.assertIn("tokens: {}", block)

    def test_the_theme_list_is_bounded(self):
        self.assertIn("MAX_THEMES", THEMES)
        self.assertIn("custom.length >= MAX_THEMES", THEMES)


class TestAccessibilityPresetsWin(TestCase):
    """
    High contrast, reduced motion and minimal stimulation are the player's
    *needs*. A theme is their taste, and taste does not get to overrule a need.

    """

    def test_the_guarantee_does_not_depend_on_load_order(self):
        """
        An earlier version of this test asserted that themes are created before
        the accessibility layer, which was both false and beside the point.

        The two write to different things -- accessibility sets attributes on
        the root, themes set inline custom properties -- so JavaScript ordering
        decides nothing. What decides it is the cascade, and the cascade is
        settled by `!important` in the stylesheet rather than by whichever
        module happened to run first. A guarantee that rests on initialisation
        order is a guarantee that breaks the next time somebody reorders a
        file.

        """
        self.assertIn("window.AetosThemes.create({", SHELL)
        block = A11Y_CSS[A11Y_CSS.index(':root[data-aetos-contrast="high"] {') :]
        block = block[: block.index("}")]
        self.assertIn("!important", block)

    def test_the_preset_selectors_are_more_specific_than_inline_tokens(self):
        """
        A theme sets its tokens inline on the root element, which beats a
        `:root` rule -- so the high-contrast preset needs `!important` or it
        loses to whatever theme is active.

        """
        block = A11Y_CSS[A11Y_CSS.index(':root[data-aetos-contrast="high"] {') :]
        block = block[: block.index("}")]
        for line in block.split("\n"):
            if "--aetos-" in line and ":" in line:
                self.assertIn(
                    "!important",
                    line,
                    "high-contrast token %r loses to an active theme" % line.strip(),
                )


class TestReachability(TestCase):
    """A.97."""

    def test_both_modules_are_loaded(self):
        template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("themes/contrast.js", template)
        self.assertIn("themes/themes.js", template)

    def test_contrast_loads_before_themes(self):
        """
        `themes.js` uses it to reject unparseable colours at normalisation.

        """
        template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )
        self.assertLess(template.index("themes/contrast.js"), template.index("themes/themes.js"))

    def test_themes_are_in_the_palette(self):
        for command in ('"theme.choose"', '"theme.new"'):
            self.assertIn(command, SHELL)

    def test_the_current_theme_is_not_shown_by_colour_alone(self):
        """
        A themes dialog is the one place a colour cue is least trustworthy.

        """
        body = _function_body(SETTINGS, "function openThemes()", "function editTheme")
        self.assertIn('choose.setAttribute("aria-pressed"', body)

    def test_the_editor_uses_labels_not_variable_names(self):
        """
        An editor that reads "--aetos-text-muted" is an editor for whoever
        wrote it.

        """
        body = _function_body(
            SETTINGS, "function editTheme(existing)", "function showContrastReport"
        )
        self.assertIn("labels[token]", body)

    def test_the_report_names_the_pair_and_its_purpose(self):
        body = _function_body(SETTINGS, "function showContrastReport", "return {")
        self.assertIn("window.AetosContrast.describe(report.failures)", body)

    def test_a_failing_theme_warns_and_still_saves(self):
        """
        A11Y-VIS-003 requires a warning, not a refusal. A player who wants a
        theme Aetos considers unwise is entitled to have it -- overruling
        somebody about their own eyes would be the worse failure. What they are
        not entitled to is not being told.

        """
        body = _function_body(
            SETTINGS, "function editTheme(existing)", "function showContrastReport"
        )
        self.assertIn("contrast problem", body)
        self.assertIn("showContrastReport(result.theme, result.contrast)", body)

        report = _function_body(SETTINGS, "function showContrastReport", "return {")
        self.assertIn("The theme has been saved.", report)
        self.assertIn("Keep it anyway", report)

    def test_the_warning_mentions_who_else_is_affected(self):
        """
        An exported theme reaches other people, and they did not choose it.

        """
        body = _function_body(SETTINGS, "function showContrastReport", "return {")
        self.assertIn("share it", body)

    def test_the_privacy_panel_names_the_namespace(self):
        self.assertIn('themes: "Themes"', SETTINGS)
