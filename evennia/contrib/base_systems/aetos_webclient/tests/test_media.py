"""
Tests for M18 -- audio, multimedia and captions.

Addendum A.58, A.79, A.84. Absorbs A6.

The gate is `A11Y-MEDIA-001`: no gameplay-essential information may exist only
in audio. Aetos cannot enforce that inside a sound file, so what it enforces is
the structure around one -- that every non-decorative sound is also text, that
the text is emitted whether or not the sound plays, and that a game which omits
a caption is told so rather than allowed to publish audio some of its players
silently never receive.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    media,
    providers,
)
from evennia.contrib.base_systems.aetos_webclient.providers import base

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


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

    Bounded by a following landmark rather than a character count, so the
    window cannot silently grow past the function as the file changes.

    Args:
        source (str): JavaScript source.
        signature (str): The line to start at.
        until (str): A later landmark that ends the window.

    Returns:
        str: The slice between them.

    """
    start = source.index(signature)
    return source[start : source.index(until, start)]


AUDIO = _read("media/audio.js")
CAPTIONS = _read("media/captions.js")
SHELL = _read("aetos.js")


class TestUrlSafety(TestCase):
    """
    A media URL is game-supplied and ends up in an element's `src`.

    Games are trusted with their own content, but a game that interpolates
    player input into a URL is not unusual, and `javascript:` in a `src` runs
    with the client's full privileges.

    """

    def test_relative_and_http_urls_are_allowed(self):
        for url in (
            "/static/sound/rain.ogg",
            "sound/rain.ogg",
            "https://example.test/rain.ogg",
            "http://example.test/rain.ogg",
        ):
            self.assertTrue(media.is_safe_url(url), "%r should be allowed" % url)

    def test_script_urls_are_refused(self):
        for url in (
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "vbscript:msgbox",
            "file:///etc/passwd",
        ):
            self.assertFalse(media.is_safe_url(url), "%r should be refused" % url)

    def test_data_urls_are_refused(self):
        """
        The one form where the payload and the reference are the same string,
        which makes size unbounded and content unreviewable.

        """
        self.assertFalse(media.is_safe_url("data:audio/wav;base64,AAAA"))

    def test_backslashes_are_refused(self):
        """
        Browsers treat a backslash as a forward slash in some positions, which
        is how "https:/\\evil.example" gets past a naive parser. Nothing
        legitimate needs one.

        """
        self.assertFalse(media.is_safe_url("https:/\\evil.example/x.ogg"))

    def test_it_is_an_allowlist_not_a_denylist(self):
        """
        A denylist would have to anticipate every scheme a browser has ever
        supported. An allowlist only needs the three that make sense here.

        """
        source = Path(media.__file__).read_text(encoding="utf-8")
        self.assertIn("ALLOWED_SCHEMES", source)
        self.assertIn("parsed.scheme.lower() in ALLOWED_SCHEMES", source)

    def test_an_unsafe_url_is_dropped_from_a_provider_list(self):
        result = media.normalize_media(
            [
                {"url": "javascript:alert(1)", "category": "effect", "caption": "boom"},
                {"url": "/ok.ogg", "category": "effect", "caption": "boom"},
            ]
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["url"], "/ok.ogg")


class TestCategoriesAreFixed(TestCase):
    """
    A11Y-MEDIA-002. Each category is a volume slider.

    """

    def test_an_unknown_category_is_refused(self):
        """
        A sound in a category the player has no slider for is a sound they
        cannot turn down, so it is refused rather than played uncontrollably.

        """
        result = media.normalize_media([{"url": "/x.ogg", "category": "spooky", "caption": "ooh"}])
        self.assertEqual(result["items"], [])

    def test_every_category_has_a_control(self):
        """
        The set on the server and the sliders in the client must agree, or
        there is a category nobody can adjust.

        """
        block = CAPTIONS[CAPTIONS.index("var SLIDERS = [") :]
        block = block[: block.index("];")]
        keys = set(re.findall(r'key: "(\w+)"', block))
        # "master" is a control without being a category.
        keys.discard("master")
        # "image" is a category without being audible.
        expected = set(media.MEDIA_CATEGORIES) - {"image"}
        self.assertEqual(keys, expected)


class TestTheCaptionIsThePrimaryChannel(TestCase):
    """
    A11Y-MEDIA-001, and the reason this milestone is shaped the way it is.

    """

    def test_the_caption_is_emitted_before_any_attempt_to_play(self):
        """
        Tying the text to successful playback would mean the players who most
        need the text are the ones least likely to get it.

        """
        body = _function_body(AUDIO, "function play(item)", "/* --- Ambient media")
        describe_at = body.index("describe(item)")
        play_at = body.index("canPlay()")
        self.assertLess(describe_at, play_at)

    def test_a_muted_category_still_captions(self):
        """
        The caption goes out, then the volume check returns. A player with the
        volume at zero receives everything a player with headphones does.

        """
        body = _function_body(AUDIO, "function play(item)", "/* --- Ambient media")
        self.assertLess(body.index("describe(item)"), body.index("effectiveVolume(item) === 0"))

    def test_uncaptioned_audio_says_so(self):
        """
        Rather than playing silently uncaptioned. A developer who never hears
        about this will never fix it, and a player who is missing something
        deserves to know that they are.

        """
        body = _function_body(AUDIO, "function describe(item)", "function canPlay()")
        self.assertIn('"Uncaptioned "', body)

    def test_no_caption_is_ever_invented(self):
        """
        A.79. Aetos cannot listen to a sound file and describe it, and an
        invented caption is confidently wrong to precisely the player who
        cannot check it.

        """
        body = _function_body(AUDIO, "function describe(item)", "function canPlay()")
        # The only text it will use comes from the game.
        self.assertIn("item.caption || item.description", body)

    def test_the_server_counts_uncaptioned_items(self):
        result = media.normalize_media(
            [
                {"url": "/a.ogg", "category": "effect"},
                {"url": "/b.ogg", "category": "effect", "caption": "A door slams."},
                {"url": "/c.ogg", "category": "ambience", "decorative": True},
            ]
        )
        self.assertEqual(result["uncaptioned"], 1)

    def test_decorative_media_is_not_uncaptioned(self):
        """
        A11Y-MEDIA-003. `decorative: True` is the game asserting the sound
        carries nothing, which is a different thing from forgetting a caption.

        """
        item = media.normalize_media_item(
            {"url": "/wind.ogg", "category": "ambience", "decorative": True}
        )
        self.assertFalse(item["uncaptioned"])

    def test_decorative_media_is_played_without_announcement(self):
        body = _function_body(AUDIO, "function describe(item)", "function canPlay()")
        self.assertIn("if (item.decorative)", body)
        self.assertLess(body.index("item.decorative"), body.index("announce("))


class TestPlayerControl(TestCase):
    """
    A11Y-MEDIA-002 and A.84. Sound the player governs.

    """

    def test_the_player_can_always_reach_zero(self):
        """
        Three multipliers, so a game cannot insist on being heard.

        """
        body = _function_body(AUDIO, "function effectiveVolume(item)", "function describe(item)")
        self.assertIn('preference("audio.muted", false)', body)
        self.assertIn("master * category * own", body)

    def test_a_game_cannot_exceed_full_volume(self):
        item = media.normalize_media_item(
            {"url": "/x.ogg", "category": "effect", "caption": "x", "volume": 40}
        )
        self.assertEqual(item["volume"], 1.0)

    def test_a_negative_volume_is_clamped(self):
        item = media.normalize_media_item(
            {"url": "/x.ogg", "category": "effect", "caption": "x", "volume": -3}
        )
        self.assertEqual(item["volume"], 0.0)

    def test_moving_a_slider_affects_what_is_already_playing(self):
        """
        Without this a slider would only affect the *next* sound, which for
        ambient music means it appears not to work at all.

        """
        self.assertIn("function applyVolumes()", AUDIO)
        body = _function_body(AUDIO, "function applyVolumes()", "return {")
        self.assertIn("entry.audio.volume = level", body)

    def test_stop_all_exists_and_is_immediate(self):
        """
        The control somebody reaches for when sound has become unbearable, so
        it does not require finding the right slider first.

        """
        self.assertIn("function stopAll()", AUDIO)
        body = _function_body(AUDIO, "function stopAll()", "function applyVolumes()")
        self.assertIn("Object.keys(ambient).forEach(stopOne)", body)
        self.assertIn("oneshots.length = 0", body)

    def test_the_controls_are_native_elements(self):
        """
        A custom slider a screen reader cannot operate is a volume control that
        does not exist for the person most likely to need it.

        """
        body = _function_body(CAPTIONS, "function buildControls(container)", "return {")
        self.assertIn('input.type = "range"', body)
        self.assertIn('label.setAttribute("for", id)', body)

    def test_mute_state_is_not_conveyed_by_label_alone(self):
        body = _function_body(CAPTIONS, "function buildControls(container)", "return {")
        self.assertIn('mute.setAttribute("aria-pressed"', body)

    def test_the_master_does_not_start_at_full(self):
        """
        A client that arrives loud is a client somebody closes before they find
        the slider.

        """
        preferences = _read("accessibility/preferences.js")
        block = preferences[preferences.index("audio: {") :]
        block = block[: block.index("}")]
        self.assertIn("master: 0.7", block)


class TestAmbientMediaIsStateNotEvents(TestCase):
    """
    A sync arriving every few seconds must not restart the music -- which would
    be unpleasant, and for anyone relying on a sound to know where they are,
    actively confusing.

    """

    def test_the_engine_diffs_rather_than_restarting(self):
        body = _function_body(AUDIO, "function sync(section)", "function stopOne(id)")
        self.assertIn("if (ambient[item.id])", body)
        self.assertIn("adjust volume only", body)

    def test_media_that_is_no_longer_wanted_stops(self):
        body = _function_body(AUDIO, "function sync(section)", "function stopOne(id)")
        self.assertIn("if (!wanted[id])", body)

    def test_an_item_keeps_a_stable_id(self):
        """
        Falling back to the URL is right: the same file in the same category
        *is* the same media as far as playback is concerned.

        """
        item = media.normalize_media_item(
            {"url": "/rain.ogg", "category": "ambience", "caption": "Rain."}
        )
        self.assertEqual(item["id"], "/rain.ogg")

    def test_the_shell_tells_the_two_kinds_apart(self):
        """
        `{items: [...]}` is state and is diffed. `{play: [...]}` is an event
        and is not -- a door slamming twice is two sounds.

        """
        body = _function_body(SHELL, 'emitter.on("aetos_media"', "/* --- Command queue")
        self.assertIn("if (payload.play)", body)
        self.assertIn("audio.sync(payload)", body)


class TestFailureIsReportedNotSwallowed(TestCase):
    """
    Browsers refuse autoplay, and rightly. Aetos does not fight it, and above
    all does not fail silently.

    """

    def test_blocked_autoplay_is_explained_once(self):
        """
        Once, because a blocked policy blocks every sound and a message per
        sound would be its own kind of noise.

        """
        self.assertIn("function reportBlocked()", AUDIO)
        body = _function_body(AUDIO, "function reportBlocked()", "function element(item)")
        self.assertIn("if (blockedReported)", body)
        self.assertIn("Captions appear either way", body)

    def test_a_browser_without_audio_still_captions(self):
        body = _function_body(AUDIO, "function canPlay()", "/*")
        self.assertIn("Captions will still appear", body)

    def test_a_burst_is_dropped_rather_than_layered(self):
        """
        Forty overlapping effects are not louder information. On a screen
        reader they are forty interruptions.

        """
        self.assertIn("MAX_CONCURRENT", AUDIO)
        body = _function_body(AUDIO, "function play(item)", "/* --- Ambient media")
        self.assertIn("oneshots.length >= MAX_CONCURRENT", body)


class TestTheServerSide(TestCase):
    """The provider slot and the convenience helper."""

    def test_media_is_a_provider_slot(self):
        self.assertIn("media", providers.PROVIDER_SLOTS)
        self.assertIs(providers.PROVIDER_SLOTS["media"], base.AetosMediaProvider)

    def test_the_default_provider_is_inert(self):
        """
        Evennia models no media, and a client that invented some would be
        guessing at a game's art direction.

        """
        self.assertEqual(base.AetosMediaProvider().get_media(None), [])

    def test_the_helper_refuses_an_unsafe_url(self):
        """
        A caption obligation cannot be dodged by using the convenience helper,
        and an unsafe URL is refused on both paths.

        """
        source = Path(Path(media.__file__).parent / "state.py").read_text(encoding="utf-8")
        body = source[source.index("def push_media(") : source.index("#: Categories a game may")]
        self.assertIn("media.normalize_media_item(", body)
        self.assertIn("if item is None:", body)
        self.assertIn("return False", body)

    def test_one_bad_descriptor_does_not_cost_the_rest(self):
        """
        A provider is game code, and a single bad entry must not cost the
        player every other one -- the rule the resource and effect normalisers
        already follow.

        """
        result = media.normalize_media(
            [
                "not a dict",
                {"url": "/good.ogg", "category": "music", "caption": "Theme."},
                {"category": "music"},
            ]
        )
        self.assertEqual(len(result["items"]), 1)

    def test_the_list_is_bounded(self):
        result = media.normalize_media(
            [
                {"url": "/n%d.ogg" % index, "category": "effect", "caption": "x"}
                for index in range(200)
            ]
        )
        self.assertLessEqual(len(result["items"]), media.MAX_MEDIA_ITEMS)

    def test_duplicate_ids_are_collapsed(self):
        result = media.normalize_media(
            [
                {"url": "/rain.ogg", "category": "ambience", "caption": "Rain."},
                {"url": "/rain.ogg", "category": "ambience", "caption": "Rain."},
            ]
        )
        self.assertEqual(len(result["items"]), 1)


class TestReachabilityAndAccessibility(TestCase):
    """A.97."""

    def test_both_modules_are_loaded(self):
        template = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("media/audio.js", template)
        self.assertIn("media/captions.js", template)

    def test_the_widget_declares_a_contract(self):
        """
        A1's registry throws without one, and it did -- the first version of
        this widget invented its own shape and was refused at boot. Which is
        exactly what A1 exists for: "we'll do accessibility later" is not
        expressible in the API.

        """
        for field in (
            'landmarkLabel: "Sound and captions"',
            "heading:",
            "keyboardOperable: true",
            "liveUpdates: true",
            "graphicalOnly: false",
        ):
            self.assertIn(field, CAPTIONS, "the widget contract is missing %r" % field)

    def test_the_caption_list_is_keyboard_reachable(self):
        body = _function_body(CAPTIONS, "mount: function (context)", "destroy: function ()")
        self.assertIn('listEl.setAttribute("tabindex", "0")', body)
        self.assertIn('"aria-label", "Captions"', body)

    def test_the_caption_list_keeps_its_list_semantics(self):
        """
        No `role="region"` on the <ul>.

        A role on a list replaces its semantics and orphans every <li> inside
        it: axe reports `listitem`, and a screen reader stops announcing "list,
        12 items". A0 made exactly this mistake once already while *fixing* a
        scrollable region, and it is worth guarding because the wrong version
        looks more accessible than the right one.

        """
        body = _function_body(CAPTIONS, "mount: function (context)", "destroy: function ()")
        code = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
        self.assertNotIn('listEl.setAttribute("role"', code)

    def test_captions_do_not_get_their_own_live_region(self):
        """
        The client has exactly two live regions, so nothing competes for
        speech. Media announces through the shared announcer instead.

        """
        # Comments stripped: the file necessarily explains why it has no live
        # region, and a bare search fails it for documenting itself. Eighth
        # instance of that mistake in this project; the M17 rule stands.
        code = re.sub(r"/\*.*?\*/", "", CAPTIONS, flags=re.DOTALL)
        code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)
        # Explicitly off, not merely absent. The console is the live surface;
        # captions are spoken by the shared announcer, so a second live region
        # here would compete with the transcript for speech.
        self.assertIn('setAttribute("aria-live", "off")', code)
        self.assertNotIn('"aria-live", "polite"', code)
        self.assertNotIn('"aria-live", "assertive"', code)

    def test_an_undescribed_image_is_not_read_as_a_filename(self):
        """
        "seven underscore dungeon underscore two dot png" is worse than
        silence.

        """
        body = _function_body(CAPTIONS, "function showImage(item)", "/* --- Controls")
        self.assertIn('picture.alt = item.description || item.caption || ""', body)

    def test_an_image_is_never_dismissed_automatically(self):
        """
        A.84. An image that disappears on a timer cannot be examined.

        """
        body = _function_body(CAPTIONS, "function showImage(item)", "/* --- Controls")
        self.assertNotIn("setTimeout", body)
        self.assertIn("Hide image", body)

    def test_stop_and_mute_are_in_the_palette(self):
        for command in ('"audio.stop"', '"audio.mute"'):
            self.assertIn(command, SHELL)

    def test_the_engine_is_given_to_the_widget_through_a_setter(self):
        """
        The widget's controls close over their own `audio` variable. Setting a
        field on the returned object would leave every one of them inert while
        looking entirely correct -- the fifth instance of that trap in this
        client, and the first anticipated rather than discovered.

        """
        self.assertIn("captionsWidget.setAudio(audio)", SHELL)
        self.assertIn("setAudio: function (engine) { audio = engine; return true; }", CAPTIONS)


class TestNothingIsInferred(TestCase):
    """
    Aetos assigns no meaning to media, exactly as it assigns none to resources.

    """

    def test_the_client_never_guesses_a_category(self):
        for guess in ('indexOf(".mp3")', 'endsWith(".ogg")', "guessCategory"):
            self.assertNotIn(guess, AUDIO)

    def test_media_defaults_to_absent(self):
        from evennia.contrib.base_systems.aetos_webclient import manifest

        self.assertFalse(manifest.DEFAULT_FEATURES["media"])


class TestNumericPreferencesPersist(TestCase):
    """
    Regression guard for a bug M18 exposed in the A0 preferences layer.

    `normalize()` handled enums, one special-cased number, booleans and
    strings. A number with no special case fell through to the string branch
    and was **silently discarded** -- so every volume slider appeared to work
    while nothing it set survived a reload.

    That is the worst shape a settings bug can take. Nothing errors, the
    control moves, and the value is gone. A player would conclude the client
    was broken, and they would be right.

    """

    def test_every_numeric_preference_has_a_range(self):
        """
        The tripwire. A numeric default with no range is dropped by
        `normalize`, and the only symptom is a setting that will not stick.

        """
        source = _read("accessibility/preferences.js")
        ranges = set(re.findall(r'"([a-z]+\.[a-zA-Z]+)": \[', source))

        defaults = source[source.index("var DEFAULTS = {") :]
        defaults = defaults[: defaults.index("\n    };")]
        numeric = set()
        group = None
        for line in defaults.split("\n"):
            group_match = re.match(r"\s{8}(\w+): \{", line)
            if group_match:
                group = group_match.group(1)
                continue
            value_match = re.match(r"\s{12}(\w+): (-?\d+\.?\d*),?\s*$", line)
            if value_match and group:
                numeric.add(group + "." + value_match.group(1))

        self.assertTrue(numeric, "found no numeric preferences to check")
        self.assertEqual(
            numeric - ranges,
            set(),
            "numeric preferences with no RANGES entry are silently discarded",
        )

    def test_the_range_table_replaced_the_special_case(self):
        """
        One table rather than a branch per key, so the next number added is
        handled by construction rather than by remembering.

        """
        source = _read("accessibility/preferences.js")
        self.assertIn("if (RANGES[path])", source)
        self.assertNotIn('if (path === "visual.scale")', source)

    def test_the_scale_bounds_are_not_repeated(self):
        """
        An earlier draft of the table wrote 2.0 and silently narrowed a range
        that had been 2.5 since A0.

        """
        source = _read("accessibility/preferences.js")
        self.assertIn('"visual.scale": [SCALE_MIN, SCALE_MAX]', source)
