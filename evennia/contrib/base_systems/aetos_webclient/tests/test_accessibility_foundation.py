"""
Structural tests for the A0 accessibility foundation.

Addendum A treats these as release gates rather than preferences, so they are
asserted structurally: behaviour is exercised in a browser, but a regression in
any of them must fail the ordinary test run, on a machine with no browser and no
screen reader attached.

The recurring theme is that these requirements fail *silently*. A missing skip
link, a stolen focus, a live region nobody coordinates -- none of them throws,
none shows up in a screenshot, and none is noticed by whoever introduced it. So
they are pinned here rather than trusted to review.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    AETOS_TEMPLATE_DIR,
)

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
A11Y_DIR = JS_DIR / "accessibility"
CSS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "css"
TEMPLATE = Path(AETOS_TEMPLATE_DIR) / "webclient.html"


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


def _strip_css_comments(source):
    """
    Remove CSS comments.

    Args:
        source (str): Stylesheet text.

    Returns:
        str: Declarations only.

    """
    return re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)


def _read(path):
    """
    Read a file's text.

    Args:
        path (Path): File to read.

    Returns:
        str: Contents.

    """
    return path.read_text(encoding="utf-8")


PREFERENCES = _strip_comments(_read(A11Y_DIR / "preferences.js"))
ANNOUNCER = _strip_comments(_read(A11Y_DIR / "announcer.js"))
FOCUS = _strip_comments(_read(A11Y_DIR / "focus.js"))
SHORTCUTS = _strip_comments(_read(A11Y_DIR / "shortcuts.js"))
MANAGER = _strip_comments(_read(A11Y_DIR / "accessibility.js"))
SHELL = _strip_comments(_read(JS_DIR / "aetos.js"))
MARKUP = _read(TEMPLATE)
A11Y_CSS = _read(CSS_DIR / "accessibility.css")

#: Every client module, for the sweeps that must hold across all of them.
ALL_JS = sorted(JS_DIR.glob("*.js")) + sorted(A11Y_DIR.glob("*.js"))


class TestTheSubsystemExists(TestCase):
    """A.4: accessibility is a subsystem, not a scattering of helpers."""

    def test_the_four_managers_are_present(self):
        for name in ("preferences.js", "announcer.js", "focus.js", "shortcuts.js"):
            self.assertTrue((A11Y_DIR / name).exists(), "missing accessibility/%s" % name)

    def test_they_are_loaded_before_everything_else(self):
        """
        A module that loads late is one the rest of the client silently did
        without.

        """
        first_a11y = MARKUP.index("accessibility/preferences.js")
        self.assertLess(first_a11y, MARKUP.index("aetos/js/store.js"))
        self.assertLess(MARKUP.index("accessibility/accessibility.js"), MARKUP.index("aetos.js"))

    def test_the_stylesheet_is_loaded(self):
        self.assertIn("aetos/css/accessibility.css", MARKUP)


class TestSemanticShell(TestCase):
    """A.7, A11Y-DOM-002."""

    def test_the_client_is_not_an_aria_application(self):
        """
        The single worst thing a web client can do to a screen-reader user.

        `role="application"` switches NVDA and JAWS out of browse mode, taking
        away single-letter navigation by heading, list and button -- which is
        how those users move around a page at all.

        """
        for source in ALL_JS:
            text = _read(source)
            self.assertNotIn('role", "application"', text, "%s sets role=application" % source.name)
        self.assertNotIn('role="application"', MARKUP)

    def test_the_landmarks_exist(self):
        for landmark in ("<header", "<nav", "<main", "<aside"):
            self.assertIn(landmark, MARKUP, "no %s landmark" % landmark)

    def test_the_navigation_landmark_is_named(self):
        """
        Two <nav> elements without names are two identical entries in a
        landmark list, which is worse than one.

        """
        self.assertIn('aria-label="Aetos navigation"', MARKUP)
        self.assertIn('aria-label="Skip links"', MARKUP)


class TestSkipLinks(TestCase):
    """A11Y-NAV-001."""

    def test_the_required_skip_targets_exist(self):
        for target in ("#aetos-input", "#aetos-console", "#aetos-workspace", "#aetos-toolbar"):
            self.assertIn('href="%s"' % target, MARKUP, "no skip link to %s" % target)

    def test_every_skip_target_is_a_real_element(self):
        """A skip link to a missing id moves focus nowhere at all."""
        for target in re.findall(r'class="aetos-skiplink" href="#([\w-]+)"', MARKUP):
            self.assertIn('id="%s"' % target, MARKUP, "skip link targets missing id %r" % target)

    def test_they_come_before_the_client(self):
        """
        A skip link reached after tabbing through the interface has skipped
        nothing.

        """
        self.assertLess(MARKUP.index("aetos-skiplink"), MARKUP.index('id="aetos-root"'))

    def test_they_become_visible_on_focus(self):
        """
        A skip link that stays invisible when focused is worse than none: it
        sits in the tab order, does something, and tells a sighted keyboard
        user nothing about where they went.

        """
        self.assertIn(".aetos-skiplink:focus", A11Y_CSS)

    def test_they_are_moved_rather_than_display_none(self):
        """`display: none` is not focusable, so it cannot be a skip link."""
        block = A11Y_CSS[A11Y_CSS.index(".aetos-skiplink {") :]
        self.assertNotIn("display: none", block[:400])


class TestAnnouncementsAreCentralised(TestCase):
    """
    A11Y-ANN-001.

    A player has one pair of ears and one braille display. Thirty independent
    live regions do not produce thirty conversations -- they produce one
    conversation with thirty interruptions, arbitrated by render order.

    """

    def test_there_are_exactly_two_live_regions(self):
        self.assertEqual(MARKUP.count('aria-live="polite"'), 1)
        self.assertEqual(MARKUP.count('role="alert"'), 1)

    def test_no_widget_creates_its_own_live_region(self):
        """
        The one permitted use elsewhere is setting `aria-live` to "off", which
        turns a region *down* rather than claiming the channel.

        """
        for source in ALL_JS:
            if source.parent == A11Y_DIR:
                continue
            for match in re.findall(r'"aria-live",\s*"(\w+)"', _read(source)):
                self.assertEqual(
                    match, "off", "%s creates a live region (aria-live=%r)" % (source.name, match)
                )

    def test_the_transcript_is_not_a_live_region(self):
        """
        A11Y-LOG-002. `role="log"` implies a polite live region, which would
        read every line of combat aloud as it arrived.

        """
        self.assertIn('role="log" aria-live="off"', MARKUP)

    def test_every_priority_level_exists(self):
        for level in ("critical", "important", "normal", "background", "silent"):
            self.assertIn('"%s"' % level, ANNOUNCER)

    def test_only_critical_interrupts(self):
        """
        A channel that interrupts constantly stops being an interruption, and
        then the one message that had to interrupt is the one ignored.

        """
        self.assertIn('URGENT_PRIORITIES = ["critical"]', ANNOUNCER)

    def test_gameplay_categories_are_never_critical(self):
        for category in ("chat", "combat", "resource", "inventory", "effect", "target"):
            pattern = r"%s:\s*\"critical\"" % category
            self.assertIsNone(
                re.search(pattern, ANNOUNCER), "%s is routed to the urgent region" % category
            )

    def test_combat_is_off_by_default(self):
        """
        The highest-volume category in most games, and the one most able to
        make speech useless.

        """
        self.assertIn("announceCombat: false", PREFERENCES)

    def test_resources_announce_on_thresholds_not_every_change(self):
        """
        "Health 61, health 60, health 59" is not information.

        """
        self.assertIn('announceResources: "thresholds"', PREFERENCES)

    def test_critical_survives_every_preference(self):
        """
        A player who muted everything still needs to know the connection
        dropped, because everything else on screen just became potentially
        stale.

        """
        self.assertIn('if (priority === "critical") {', ANNOUNCER)

    def test_connection_loss_is_the_thing_that_interrupts(self):
        self.assertIn('category: "connection", priority: "critical"', SHELL)


class TestFocusIsNeverStolen(TestCase):
    """
    A11Y-FOCUS-001.

    Focus moving unexpectedly is a mild annoyance with a mouse, a real problem
    with a keyboard, and disabling with braille -- where the display follows
    focus, so an unrequested move discards the reader's place in a passage they
    were part-way through.

    """

    def test_no_server_driven_module_moves_focus(self):
        """
        These are the modules a server message can reach: the store that applies
        a sync, and every widget rendered from it. None of them may call
        `focus()`, because nothing arriving from the game is a user gesture.

        A poison tick that stole focus every three seconds would make the client
        unusable in a way entirely invisible to a sighted mouse user testing it.

        """
        for name in (
            "store.js",
            "character.js",
            "resources.js",
            "builtins.js",
            "map.js",
            "widgets.js",
        ):
            source = _read(JS_DIR / name)
            self.assertNotIn(".focus()", source, "%s moves focus on server data" % name)

    def test_the_layout_focuses_only_through_a_deliberate_api(self):
        """
        `layout.js` is the exception, and legitimately so: keyboard layout
        editing moves focus *with* the panel it just moved, which is a direct
        response to a keystroke.

        What matters is that this stays reachable only through the explicit
        `focus(id)` entry point, so no render path can acquire the ability by
        accident. Asserted by position rather than by absence.

        """
        source = _strip_comments(_read(JS_DIR / "layout.js"))
        self.assertEqual(source.count(".focus()"), 1, "layout.js focuses in more than one place")

        start = source.index("function focus(id)")
        end = source.index("return true;", start)
        self.assertIn(".focus()", source[start:end], "the focus call escaped focus(id)")

    def test_the_sync_handler_does_not_focus(self):
        start = SHELL.index("emitter.on(AETOS_MSG.SYNC")
        window = SHELL[start : start + 1200]
        self.assertNotIn(".focus()", window, "the sync handler moves focus")

    def test_the_focus_manager_offers_capture_and_restore(self):
        self.assertIn("function capture()", FOCUS)
        self.assertIn("function restore()", FOCUS)

    def test_restore_handles_a_vanished_opener(self):
        """
        Focusing a detached node silently drops focus to <body>, which loses the
        player's place entirely -- so there is a fallback.

        """
        self.assertIn("document.contains(previous)", FOCUS)
        self.assertIn("settings.fallback", FOCUS)

    def test_the_trap_keeps_focus_inside(self):
        self.assertIn("function trapWithin", FOCUS)
        self.assertIn("container.contains(active)", FOCUS)

    def test_the_guard_reports_rather_than_prevents(self):
        """
        Silently refusing a focus call would produce a subtler bug than the one
        it fixed. The guard reports, so a violation is found in QA.

        """
        self.assertIn("onViolation", FOCUS)
        self.assertNotIn("preventFocus", FOCUS)


class TestNoCharacterOnlyShortcuts(TestCase):
    """
    A11Y-KEY-002.

    NVDA and JAWS use single letters for structural navigation. Binding `i` to
    Inventory does not add a shortcut, it removes a letter from someone's
    ability to move around the page -- invisibly to whoever added it.

    """

    def test_a_bare_character_is_refused_not_discouraged(self):
        self.assertIn("isBareCharacter", SHORTCUTS)
        self.assertIn("throw new Error", SHORTCUTS)

    def test_shift_does_not_rescue_a_bare_character(self):
        """
        Screen readers use shifted letters for reverse structural navigation,
        so Shift+H is as unavailable as H.

        """
        self.assertIn('modifiers[0] === "Shift"', SHORTCUTS)

    def test_function_keys_are_allowed(self):
        self.assertIn('"F1"', SHORTCUTS)
        self.assertIn("SAFE_BARE_KEYS", SHORTCUTS)

    def test_the_shipped_defaults_are_not_bare_characters(self):
        bindings = re.findall(r'defaultBinding: "([^"]+)"', SHELL)
        self.assertTrue(bindings, "no shortcuts registered")
        for binding in bindings:
            parts = binding.split("+")
            key = parts[-1]
            modifiers = [p for p in parts[:-1] if p != "Shift"]
            if not modifiers:
                self.assertGreater(len(key), 1, "%r is a bare character shortcut" % binding)

    def test_the_conflict_table_covers_screen_reader_modifiers(self):
        for key in ("Insert", "CapsLock"):
            self.assertIn(key, SHORTCUTS, "%s is not in the conflict table" % key)

    def test_conflicts_warn_but_do_not_block(self):
        """
        The table cannot be authoritative: assistive technology is
        configurable, and a player who remapped their own screen reader knows
        their setup better than a hardcoded list.

        """
        self.assertIn("warnings", SHORTCUTS)
        self.assertIn("ok: true", SHORTCUTS)


class TestNoFeatureHidesBehindAShortcut(TestCase):
    """A.23, enforced rather than encouraged."""

    def test_registration_requires_a_palette_command(self):
        self.assertIn("must name the palette command it", SHORTCUTS)

    def test_every_registered_shortcut_names_one(self):
        """
        Counted against `shortcuts.register` blocks specifically.

        The earlier version compared registrations with every `paletteCommand:`
        anywhere in the shell, which broke at M20 when touch gestures started
        declaring one too -- so it failed while both rules were being honoured.
        The invariant was right; the way it was measured was not.

        """
        source = SHELL
        registrations = source.count("shortcuts.register({")
        self.assertGreater(registrations, 0)

        named = 0
        position = 0
        for _ in range(registrations):
            position = source.index("shortcuts.register({", position) + 1
            block = source[position : source.index("});", position)]
            if "paletteCommand:" in block:
                named += 1
        self.assertEqual(
            registrations,
            named,
            "a shortcut was registered without naming its palette command",
        )

    def test_every_registered_gesture_names_one_too(self):
        """
        M20 applies the same rule to touch gestures (A.57), for the same
        reason: a gesture is invisible, and one with no visible equivalent is a
        feature that does not exist for anyone using a screen reader, a switch
        device or a desktop.

        Every gesture goes through `addGesture`, which refuses to register one
        whose palette command the palette does not actually have.

        """
        self.assertIn("function addGesture(direction", SHELL)
        body = SHELL[SHELL.index("function addGesture(direction") :]
        body = body[: body.index("gestures.listen(document)")]
        self.assertIn("palette.commands().some", body)
        self.assertIn("paletteCommand: command", body)

    def test_shortcuts_can_be_viewed_rebound_disabled_and_restored(self):
        for capability in (
            "function list",
            "function rebind",
            "function disable",
            "function restore",
            "function restoreAll",
        ):
            self.assertIn(capability, SHORTCUTS, "shortcuts cannot %s" % capability)

    def test_only_changes_from_default_are_stored(self):
        """
        So a later change to a default reaches players who never rebound it,
        rather than freezing everyone on whatever default they first loaded.

        """
        self.assertIn("!== commands[id].defaultBinding", SHORTCUTS)


class TestPreferencesAreGranularAndPrivate(TestCase):
    """A.70, A.71, A.72, A.73, A.74."""

    def test_there_is_no_master_switch(self):
        """
        A.71: choosing a screen-reader profile adjusts verbosity. It does not
        "turn accessibility on", because semantic HTML and keyboard operation
        were never off.

        """
        self.assertNotIn("accessibilityEnabled", PREFERENCES)
        self.assertNotIn("screenReaderMode:", PREFERENCES)

    def test_every_required_group_is_present(self):
        for group in ("screenReader", "braille", "keyboard", "cognitive", "visual", "aac"):
            self.assertIn("%s: {" % group, PREFERENCES)

    def test_unknown_values_fall_back_rather_than_being_stored(self):
        """
        A hand-edited import must not be able to put the client in a state no
        code path expects.

        """
        self.assertIn("ENUMS", PREFERENCES)
        self.assertIn("indexOf(value) !== -1", PREFERENCES)

    def test_updates_merge_rather_than_replace(self):
        """
        The same rule the notes store learned the hard way in M11: an omitted
        field means "leave alone", not "clear".

        """
        self.assertIn("function update(patch)", PREFERENCES)
        self.assertIn("var merged = clone(current)", PREFERENCES)

    def test_nothing_is_sent_to_the_server(self):
        for forbidden in ("Evennia.msg", "dispatcher", "fetch(", "XMLHttpRequest", "WebSocket"):
            for name, source in (
                ("preferences", PREFERENCES),
                ("shortcuts", SHORTCUTS),
                ("announcer", ANNOUNCER),
                ("focus", FOCUS),
            ):
                self.assertNotIn(forbidden, source, "%s.js references %r" % (name, forbidden))

    def test_there_is_no_screen_reader_detection(self):
        """
        A.73. Detection would be fingerprinting, and a player must never have
        to disclose a disability to a MUD operator in order to play.

        """
        for probe in (
            "NVDA",
            "JAWS",
            "detectScreenReader",
            "isScreenReader",
            "navigator.userAgent",
        ):
            self.assertNotIn(probe, PREFERENCES)
            self.assertNotIn(probe, MANAGER)

    def test_preferences_live_in_the_players_own_store(self):
        """
        A.75: so they are exported, counted and cleared with everything else,
        rather than being invisible to the privacy panel.

        """
        self.assertIn('"preferences"', PREFERENCES)
        self.assertIn('"keybindings"', SHORTCUTS)


class TestMotionAndContrast(TestCase):
    """A.52, A.53, A11Y-VIS-003."""

    def test_the_system_preference_is_honoured(self):
        self.assertIn("prefers-reduced-motion: reduce", A11Y_CSS)

    def test_an_explicit_choice_overrides_the_system_in_both_directions(self):
        """
        A player may want motion the operating system is suppressing.
        Overriding them "for their own good" is the same paternalism reversed.

        """
        self.assertIn(':root:not([data-aetos-motion="full"])', A11Y_CSS)
        self.assertIn(':root[data-aetos-motion="reduced"]', A11Y_CSS)

    def test_high_contrast_is_a_palette_not_a_filter(self):
        """
        `filter: contrast()` produces unpredictable ratios and can push a
        passing pair into failure -- the opposite of the setting's purpose.

        """
        self.assertIn('[data-aetos-contrast="high"]', A11Y_CSS)
        # Against the declarations only. The prose above explains *why* a filter
        # is wrong, and matching that would fail the file for documenting
        # itself -- the same defect this suite caught in the palette QA.
        self.assertNotIn("filter: contrast", _strip_css_comments(A11Y_CSS))

    def test_forced_colours_mode_is_handled(self):
        self.assertIn("forced-colors: active", A11Y_CSS)

    def test_the_resource_meter_survives_forced_colours(self):
        """
        Otherwise the fill is painted away and the meter reads as empty at
        every value.

        """
        self.assertIn("forced-color-adjust", A11Y_CSS)

    def test_reduced_stimulation_never_hides_content(self):
        """
        Reducing stimulation must not reduce what a player can find out. That
        would make it a worse client rather than a calmer one.

        """
        block = A11Y_CSS[A11Y_CSS.index("Presentation intensity") :]
        self.assertNotIn("display: none", block)
        self.assertNotIn("visibility: hidden", block)


class TestFocusIndicatorAndTargets(TestCase):
    """A11Y-FOCUS-004, A.57."""

    def test_there_is_a_focus_indicator(self):
        self.assertIn(":focus-visible", A11Y_CSS)
        self.assertIn("outline", A11Y_CSS)

    def test_no_stylesheet_removes_an_outline_without_replacing_it(self):
        for sheet in CSS_DIR.glob("*.css"):
            text = _read(sheet)
            for match in re.finditer(r"outline:\s*(none|0)\b", text):
                window = text[match.start() : match.start() + 300]
                self.assertIn(
                    "box-shadow",
                    window,
                    "%s removes an outline without replacing the indicator" % sheet.name,
                )

    def test_pointer_targets_meet_the_minimum(self):
        self.assertIn("min-height: 24px", A11Y_CSS)

    def test_touch_gets_the_enhanced_target(self):
        self.assertIn("pointer: coarse", A11Y_CSS)
        self.assertIn("min-height: 44px", A11Y_CSS)

    def test_visually_hidden_stays_in_the_accessibility_tree(self):
        """
        `display: none` would remove it from the tree as well, which defeats
        the entire purpose of the class.

        """
        block = A11Y_CSS[A11Y_CSS.index(".aetos-visually-hidden {") :]
        self.assertNotIn("display: none", block[:400])
        self.assertIn("clip-path", block[:400])


class TestShortcutReferencesResolve(TestCase):
    """
    A shortcut may not name a palette command that does not exist.

    The original rule (A.23) was checked by asserting a `paletteCommand:` key
    was present, which is spelling rather than substance: `palette.toggle` was
    named by Ctrl+K from A0 onwards and no such command was ever registered. It
    took M20's gesture guard -- which checks against the live palette -- to find
    it, a year later.

    The point of the rule is that a player can find the feature in the palette
    and learn its shortcut there. A dangling reference defeats that completely
    while looking compliant.

    """

    def _registered_command_ids(self):
        """
        Every id passed to `addCommand`.

        Returns:
            set: Command ids the shell registers.

        """
        return set(re.findall(r'addCommand\("([\w.]+)"', SHELL))

    def _referenced_command_ids(self):
        """
        Every id named by a shortcut or a gesture.

        Returns:
            set: Command ids something claims to accelerate.

        """
        return set(re.findall(r'paletteCommand: "([\w.]+)"', SHELL))

    def test_every_shortcut_reference_resolves(self):
        registered = self._registered_command_ids()
        referenced = self._referenced_command_ids()
        self.assertTrue(referenced, "no shortcut names a palette command")
        dangling = referenced - registered
        self.assertEqual(
            dangling,
            set(),
            "shortcut(s) name palette commands that are never registered: %s" % sorted(dangling),
        )

    def test_every_gesture_reference_resolves(self):
        """
        Checked statically here and again at runtime by `addGesture`, which
        refuses to register a gesture whose command the palette lacks.

        """
        registered = self._registered_command_ids()
        gestures = set(re.findall(r'addGesture\("\w+", "[^"]+", "([\w.]+)"', SHELL))
        self.assertTrue(gestures, "no gestures are registered")
        dangling = gestures - registered
        self.assertEqual(
            dangling,
            set(),
            "gesture(s) name palette commands that are never registered: %s" % sorted(dangling),
        )
