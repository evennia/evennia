"""
Tests for M29 -- the compatibility matrix.

A compatibility claim is a promise, and a promise nobody checks is the same kind
of thing M28 found in the README. So the matrix is not prose here: it is a table
of the platform features Aetos uses, each with the version that first shipped it,
and the floor is *computed* from what the code actually contains.

Add a CSS feature with a later baseline and these tests fail until either the
feature goes or the published floor moves. That is the point: the number in
`docs/compatibility.md` cannot quietly stop being true.

Two findings that came out of building it, both real defects rather than
documentation:

- **A selector list is not a fallback.** `x:focus, x:focus-visible { ... }` looks
  like graceful degradation and is the opposite: one unrecognised selector
  invalidates the *entire* rule, so a browser without `:focus-visible` lost the
  plain `:focus` styling too. The client had one rule written that way and one
  with no `:focus` form at all -- so on such a browser the focus indicator fell
  back to whatever the browser drew by default, which is not what
  A11Y-FOCUS-004 requires and is a WCAG 2.4.7 failure rather than a cosmetic one.
- **A blanket reduced-motion rule from M4 overrode the A0 rule that reads the
  player's choice.** A0's comment says explicitly that an explicit choice must
  win "in BOTH directions" -- somebody may want motion their operating system is
  suppressing. The older rule silently made that impossible.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

CONTRIB_DIR = Path(AETOS_STATIC_DIR).parent
CSS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "css"
JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
A11Y_CSS = (CSS_DIR / "accessibility.css").read_text(encoding="utf-8")
DOCS_DIR = CONTRIB_DIR.parents[4] / "docs"

#: A CSS feature, how to find it, and the first version of each engine to ship it.
#:
#: Sources are the usual public support tables. The numbers are here rather than
#: in prose so that the floor can be recomputed instead of remembered.
CSS_FEATURES = {
    "custom properties": (r"var\(--", (49, 31, 9.1)),
    "grid layout": (r"display:\s*(inline-)?grid", (57, 52, 10.1)),
    "flexbox gap": (None, (84, 63, 14.1)),
    "min() / max() / clamp()": (r"\b(clamp|min|max)\(", (79, 75, 13.1)),
    "inset shorthand": (r"\binset:", (87, 66, 14.1)),
    "object-fit": (r"object-fit", (32, 36, 10)),
}

#: Features Aetos uses as enhancements, with a working fallback.
#:
#: These do not set the floor, and each one's fallback is asserted below --
#: because "it degrades" is a claim, and an unchecked claim is how the focus
#: indicator came to be missing on older browsers in the first place.
CSS_ENHANCEMENTS = {
    ":focus-visible": r":focus-visible",
    "forced-colors": r"forced-colors",
}

#: The published floor. Recomputed by the tests; stated here so a change is
#: visible in a diff rather than only in a failure.
FLOOR = {"chrome": 87, "firefox": 75, "safari": 14.1}


def _all_css():
    """
    Every stylesheet Aetos ships, concatenated.

    Returns:
        str: CSS source.

    """
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(CSS_DIR.glob("*.css")))


def _rules_with_gap_on_flex():
    """
    Rules that set `gap` on a flex container.

    `gap` on grid shipped years before `gap` on flex, so which one is used
    changes the answer by three Safari major versions. Worth measuring rather
    than assuming.

    Returns:
        int: How many such rules exist.

    """
    count = 0
    for match in re.finditer(r"\{([^{}]*)\}", _all_css()):
        body = match.group(1)
        if not re.search(r"(^|;|\s)gap\s*:", body):
            continue
        display = re.search(r"display\s*:\s*([\w-]+)", body)
        if display and display.group(1) in ("flex", "inline-flex"):
            count += 1
    return count


def _code_only(source):
    """
    Strip comments *and* string literals from JavaScript source.

    Both, because a scan for syntax has to look at syntax. The first version of
    this stripped only comments and reported `validator.js` as using template
    literals -- it has a warning message that quotes a regular expression
    containing a backtick, inside an ordinary double-quoted string. A test that
    cannot tell a backtick in a string from a template literal is not testing
    the language level, it is testing the prose.

    Regular expression literals containing quotes could still confuse this. If
    that ever produces a false positive it will name the file, which is enough
    to see it for what it is.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments and string contents removed.

    """
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
    source = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', source)
    return re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", source)


class TestTheFloorIsWhatTheCodeRequires(TestCase):
    """
    Computed, not remembered.

    """

    def test_flexbox_gap_is_what_sets_the_safari_floor(self):
        """
        Named because it is the surprising one: the oldest browser Aetos can run
        on is decided by a layout shorthand, not by any JavaScript it uses.

        """
        self.assertGreater(_rules_with_gap_on_flex(), 0)

    def _required(self, index):
        """
        The highest version any used feature requires, for one engine.

        Args:
            index (int): 0 chrome, 1 firefox, 2 safari.

        Returns:
            float: The required version.

        """
        css = _all_css()
        needed = 0
        for name, (pattern, versions) in CSS_FEATURES.items():
            present = _rules_with_gap_on_flex() > 0 if pattern is None else re.search(pattern, css)
            if present:
                needed = max(needed, versions[index])
        return needed

    def test_the_published_chrome_floor_matches_the_code(self):
        self.assertEqual(self._required(0), FLOOR["chrome"])

    def test_the_published_firefox_floor_matches_the_code(self):
        self.assertEqual(self._required(1), FLOOR["firefox"])

    def test_the_published_safari_floor_matches_the_code(self):
        self.assertEqual(self._required(2), FLOOR["safari"])

    def test_the_documentation_states_the_same_floor(self):
        doc = DOCS_DIR / "compatibility.md"
        if not doc.exists():
            self.skipTest("docs/ is outside a vendored contrib")
        text = doc.read_text(encoding="utf-8")
        for engine, version in FLOOR.items():
            rendered = (
                str(version).rstrip("0").rstrip(".") if isinstance(version, float) else str(version)
            )
            self.assertIn(
                rendered,
                text,
                "compatibility.md does not state the %s floor of %s" % (engine, rendered),
            )


class TestTheEnhancementsActuallyDegrade(TestCase):
    """
    The defect this milestone found. "It degrades gracefully" is a claim, and an
    unchecked one is how a focus indicator goes missing.

    """

    def test_focus_visible_is_never_in_a_selector_list_with_focus(self):
        """
        The whole finding, as one assertion.

        A comma-separated selector list is all-or-nothing: one selector the
        browser does not understand invalidates the entire rule. Pairing
        `:focus` with `:focus-visible` in a single list does not provide a
        fallback -- it removes both.

        """
        for path in sorted(CSS_DIR.glob("*.css")):
            source = re.sub(r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S)
            for rule in re.finditer(r"([^{}]+)\{", source):
                selectors = [part.strip() for part in rule.group(1).split(",")]
                has_plain = any(
                    ":focus" in part and ":focus-visible" not in part for part in selectors
                )
                has_visible = any(":focus-visible" in part for part in selectors)
                self.assertFalse(
                    has_plain and has_visible,
                    "%s pairs :focus with :focus-visible in one list: %s"
                    % (path.name, rule.group(1).strip()[:80]),
                )

    def test_there_is_a_focus_indicator_without_focus_visible(self):
        """
        The rule an older browser is left with has to be a real indicator, not
        just an offset applied to whatever the browser drew by itself.

        """
        match = re.search(
            r"\.aetos-root :focus,[^{]*\{([^}]*)\}",
            A11Y_CSS,
        )
        self.assertIsNotNone(match, "no plain :focus indicator rule")
        self.assertIn("outline: 3px solid", match.group(1))

    def test_pointer_focus_is_quietened_only_where_the_selector_is_understood(self):
        """
        `:focus:not(:focus-visible)` is itself dropped by a browser that lacks
        the selector -- which is exactly right. Such a browser keeps the
        always-on ring rather than losing it, and shows it slightly more often
        than necessary. That is the correct direction to fail in.

        """
        self.assertIn(".aetos-root :focus:not(:focus-visible)", A11Y_CSS)
        block = A11Y_CSS[A11Y_CSS.index(".aetos-root :focus:not(:focus-visible)") :]
        block = block[: block.index("}")]
        self.assertIn("outline: none", block)

    def test_forced_colors_is_an_addition_rather_than_a_requirement(self):
        """
        Safari does not support forced-colors at all. Anything inside that
        query has to be a refinement of something already stated outside it.

        """
        blocks = re.findall(r"@media[^{]*forced-colors[^{]*\{(.*?)\n\}", A11Y_CSS, flags=re.S)
        self.assertTrue(blocks, "no forced-colors block to check")
        for block in blocks:
            self.assertNotIn("display: none", block, "forced-colors hides content")


class TestTheJavaScriptFloorIsLowerThanTheCssFloor(TestCase):
    """
    Aetos is written in ES5 plus promises. That is not nostalgia: it is what
    lets the floor be set by layout features with a clear visual degradation,
    rather than by a syntax error that stops the client dead.

    """

    #: Syntax that would raise the floor, and cannot be feature-detected --
    #: a parse error takes the whole file with it.
    FORBIDDEN_SYNTAX = {
        "arrow functions": r"=>",
        "let bindings": r"(^|[;{}\s])let\s+\w",
        "const bindings": r"(^|[;{}\s])const\s+\w",
        "template literals": r"`",
        "class declarations": r"(^|[;{}\s])class\s+\w+\s*\{",
        "async functions": r"(^|[;{}\s])async\s+function",
        "spread": r"\.\.\.\w",
    }

    def _sources(self):
        """
        Every shipped JavaScript file, comments removed.

        Returns:
            list: Tuples of (name, source).

        """
        paths = sorted(JS_DIR.rglob("*.js"))
        paths.append(Path(AETOS_STATIC_DIR) / "aetos" / "aetos-service-worker.js")
        return [(path.name, _code_only(path.read_text(encoding="utf-8"))) for path in paths]

    def test_there_are_sources_to_check(self):
        self.assertGreater(len(self._sources()), 40)

    def test_no_module_uses_syntax_that_would_fail_to_parse(self):
        for name, source in self._sources():
            for label, pattern in self.FORBIDDEN_SYNTAX.items():
                self.assertIsNone(
                    re.search(pattern, source),
                    "%s uses %s, which raises the floor to a parse error" % (name, label),
                )

    def test_every_optional_api_is_tested_for_before_use(self):
        """
        These are the APIs whose absence must degrade rather than throw. Each is
        checked in the file that uses it -- a guard in a different module is not
        a guard.

        """
        required = {
            "responsive.js": ("ResizeObserver", 'typeof window.ResizeObserver === "function"'),
            "pwa.js": ("serviceWorker", "!window.navigator.serviceWorker"),
            "storage.js": ("indexedDB", "!window.indexedDB"),
        }
        for name, (api, guard) in required.items():
            source = (JS_DIR / name).read_text(encoding="utf-8")
            self.assertIn(api, source, "%s no longer uses %s" % (name, api))
            self.assertIn(guard, source, "%s uses %s without guarding it" % (name, api))

    def test_animation_frames_have_a_timer_fallback(self):
        """
        M25 added the batching that made this matter: a browser or a tab with no
        animation frames must still render output.

        """
        shell = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
        self.assertIn('typeof window.requestAnimationFrame === "function"', shell)
        self.assertIn("window.setTimeout(flush, 100)", shell)


class TestTheMotionPreferenceIsHonouredInBothDirections(TestCase):
    """
    A0's rule says an explicit choice wins over the system setting in both
    directions, because somebody may want motion their operating system is
    suppressing. An M4 rule in the other stylesheet silently made that
    impossible.

    """

    def test_only_one_stylesheet_declares_a_reduced_motion_rule(self):
        declaring = [
            path.name
            for path in sorted(CSS_DIR.glob("*.css"))
            if "@media (prefers-reduced-motion" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(declaring, ["accessibility.css"])

    def test_the_surviving_rule_respects_an_explicit_choice(self):
        self.assertIn(':root:not([data-aetos-motion="full"])', A11Y_CSS)

    def test_choosing_full_motion_is_possible(self):
        """
        The setting has to exist for the rule above to mean anything.

        """
        preferences = (JS_DIR / "accessibility" / "preferences.js").read_text(encoding="utf-8")
        self.assertIn("full", preferences)
        self.assertIn("motion", preferences)
