"""
Tests for M20 -- the progressive web app shell and touch gestures.

Addendum A.57. Blueprint milestone M20.

A service worker is the one part of a web client that keeps running after the
page is gone, so most of what is asserted here is what it refuses to do: cache
game content, cache a failed response, serve stale code, or reload the client
under somebody mid-sentence.

The gesture tests all reduce to one rule -- a gesture may make something faster
and may never be the only way to do it.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, constants

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


def _code_only(source):
    """
    Strip comments, leaving only what executes.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source without comments.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


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


PWA = _read("pwa.js")
GESTURES = _read("gestures.js")
SHELL = _read("aetos.js")
SETTINGS = _read("settings.js")
WORKER = (Path(AETOS_STATIC_DIR) / "aetos" / "aetos-service-worker.js").read_text(encoding="utf-8")
TEMPLATE = (Path(AETOS_STATIC_DIR).parent / "templates" / "webclient.html").read_text(
    encoding="utf-8"
)


class TestTheWorkerNeverCachesGameContent(TestCase):
    """
    Blueprint 2.3 and section 63. A cache is a data store, and a worker quietly
    holding last night's conversation would be invisible in the privacy panel,
    would survive "clear all Aetos data", and would be readable by anyone who
    picks up the device.

    """

    def test_only_same_origin_static_assets_are_handled(self):
        """
        Structural rather than a filter: there is no branch that could cache a
        response from the game.

        """
        body = _function_body(WORKER, "function isCacheable(request)", "self.addEventListener")
        self.assertIn('request.method !== "GET"', body)
        self.assertIn("url.origin !== self.location.origin", body)
        self.assertIn("CACHEABLE_PREFIXES.some", body)

    def test_the_prefixes_are_an_allowlist_of_client_assets(self):
        block = WORKER[WORKER.index("var CACHEABLE_PREFIXES = [") :]
        block = block[: block.index("];")]
        prefixes = set(re.findall(r'"([^"]+)"', block))
        self.assertEqual(prefixes, {"/static/aetos/", "/static/webclient/"})

    def test_a_request_it_does_not_own_is_left_entirely_alone(self):
        """
        Not "fetched and not cached" -- not handled at all, so the browser
        behaves exactly as if no worker existed.

        """
        body = _function_body(
            WORKER, 'self.addEventListener("fetch"', 'self.addEventListener("message"'
        )
        self.assertIn("if (!isCacheable(event.request)) {", body)
        guard = body[body.index("if (!isCacheable") : body.index("event.respondWith")]
        self.assertIn("return;", guard)

    def test_nothing_reads_the_websocket_or_the_transcript(self):
        code = _code_only(WORKER)
        for forbidden in (
            "WebSocket",
            "aetos_sync",
            "aetos_event",
            "transcript",
            "IndexedDB",
            "indexedDB",
            "localStorage",
        ):
            self.assertNotIn(forbidden, code, "the worker touches %r" % forbidden)


class TestTheStaleCodeTrap(TestCase):
    """
    A worker serving yesterday's JavaScript against an upgraded server presents
    as features mysteriously missing, which nobody diagnoses as caching.

    """

    def test_the_cache_name_carries_the_asset_version(self):
        self.assertIn('var CACHE_NAME = "aetos-shell-" + ASSET_VERSION;', WORKER)

    def test_the_version_is_substituted_at_serve_time(self):
        """
        Read from `constants.ASSET_VERSION` rather than duplicated, so there is
        one version and not two that can disagree.

        """
        from evennia.contrib.base_systems.aetos_webclient import urls

        source = Path(urls.__file__).read_text(encoding="utf-8")
        self.assertIn('"__AETOS_ASSET_VERSION__", constants.ASSET_VERSION', source)
        self.assertIn("__AETOS_ASSET_VERSION__", WORKER)

    def test_activation_deletes_every_older_aetos_cache(self):
        body = _function_body(
            WORKER, 'self.addEventListener("activate"', 'self.addEventListener("fetch"'
        )
        self.assertIn('name.indexOf("aetos-") === 0 && name !== CACHE_NAME', body)

    def test_it_leaves_the_games_own_caches_alone(self):
        body = _function_body(
            WORKER, 'self.addEventListener("activate"', 'self.addEventListener("fetch"'
        )
        # Only Aetos-prefixed caches are deleted; anything else on the origin
        # belongs to the game.
        self.assertNotIn(
            "caches.delete(name);\n            }));",
            body.replace(
                'if (name.indexOf("aetos-") === 0 && name !== CACHE_NAME) {\n                    return caches.delete(name);\n                }',
                "",
            ),
        )

    def test_it_is_network_first_not_cache_first(self):
        """
        The opposite of the usual PWA advice, deliberately. Cache-first suits
        immutable content-addressed assets; Aetos's are neither, and a player on
        a working connection should run the code the server currently has.

        """
        body = _function_body(
            WORKER, 'self.addEventListener("fetch"', 'self.addEventListener("message"'
        )
        self.assertLess(body.index("fetch(event.request)"), body.index("caches.match"))

    def test_a_failed_response_is_never_cached(self):
        """
        A 404 cached as though it were the file is a failure that outlives its
        cause: the server gets fixed and the client keeps serving the error.

        """
        body = _function_body(
            WORKER, 'self.addEventListener("fetch"', 'self.addEventListener("message"'
        )
        self.assertIn('response.ok && response.type === "basic"', body)

    def test_nothing_is_precached(self):
        """
        A precache list is a second copy of the template's script tags, and the
        two drift -- the copy goes stale, the worker caches a file that no
        longer exists, and installation fails for everybody.

        """
        body = _function_body(
            WORKER, 'self.addEventListener("install"', 'self.addEventListener("activate"'
        )
        self.assertNotIn("cache.addAll", body)
        self.assertNotIn("cache.add(", body)

    def test_the_worker_itself_is_served_uncached(self):
        """
        A cached service worker cannot be replaced, which turns any mistake in
        it into a permanent one for everybody who loaded it.

        """
        from evennia.contrib.base_systems.aetos_webclient import urls

        source = Path(urls.__file__).read_text(encoding="utf-8")
        self.assertIn("max_age=0", source)
        self.assertIn("no_cache=True", source)


class TestUpdatesAreNeverAppliedUnderThePlayer(TestCase):
    """
    Reloading the client under somebody mid-fight, or mid-sentence on the
    communication board, is a data-loss bug wearing a feature's clothes.

    """

    def test_the_client_never_calls_skip_waiting_on_its_own(self):
        code = _code_only(PWA)
        # The only `skipWaiting` is the message sent when the player asks.
        self.assertNotIn("registration.skipWaiting", code)
        self.assertIn('postMessage({ type: "aetos-skip-waiting" })', code)

    def test_the_worker_only_skips_waiting_when_told(self):
        body = _function_body(WORKER, 'self.addEventListener("message"', "\n")
        self.assertIn('event.data.type === "aetos-skip-waiting"', WORKER)

    def test_an_available_update_is_announced_not_applied(self):
        body = _function_body(PWA, "function announceUpdate()", "function applyUpdate")
        self.assertIn("nothing has changed yet", body)
        # Anchored on the call, not the word: the message itself says "the next
        # time you reload", so searching for "reload" fails the function for
        # explaining itself. Tenth instance of that mistake in this project.
        self.assertNotIn("window.location.reload", body)

    def test_applying_it_is_a_palette_command(self):
        self.assertIn('"app.update"', SHELL)
        self.assertIn('"app.install"', SHELL)

    def test_the_update_command_hides_when_there_is_none(self):
        body = _function_body(SHELL, 'addCommand("app.update"', "/* Session */")
        self.assertIn("pwa.updateAvailable()", body)


class TestInstallIsOfferedNotPushed(TestCase):
    """
    An unprompted "install this app?" banner over a game somebody is playing is
    an interruption they did not ask for.

    """

    def test_the_browser_prompt_is_captured(self):
        body = _function_body(PWA, "function watchForInstall()", "function canInstall")
        self.assertIn("event.preventDefault()", body)

    def test_it_becomes_a_palette_command(self):
        """
        Which is also the only way a keyboard-only player could reach it, since
        the browser's own banner is not always focusable.

        """
        body = _function_body(SHELL, 'addCommand("app.install"', 'addCommand("app.update"')
        self.assertIn("pwa.install()", body)


class TestTheCacheIsPlayerData(TestCase):
    """Section 63: local data is enumerable and clearable."""

    def test_clearing_all_data_clears_the_cache_too(self):
        """
        A cache the panel does not clear is data a player was told they had
        deleted -- a worse failure than not offering to delete it.

        """
        self.assertIn("services.pwa\n", SETTINGS.replace("services.pwa ", "services.pwa\n"))
        self.assertIn("pwa.clearCaches()", SETTINGS)

    def test_the_confirmation_says_the_cache_goes_too(self):
        self.assertIn("cached", SETTINGS[SETTINGS.index("Clear all Aetos data?") :][:900])

    def test_only_aetos_caches_are_deleted(self):
        body = _function_body(PWA, "function clearCaches()", "function cacheSummary")
        self.assertIn('name.indexOf("aetos-") === 0', body)

    def test_the_reported_version_comes_from_the_cache_itself(self):
        """
        Not from a copy passed in, which could disagree with what is actually
        cached -- the one thing a cache report must not do.

        """
        body = _function_body(PWA, "function cacheSummary()", "function start()")
        self.assertIn('replace("aetos-shell-", "")', body)


class TestGesturesAreNeverTheOnlyWay(TestCase):
    """
    A.57, read as a design rule: a gesture may make something faster and may
    never be the only way to do it.

    A gesture is invisible. It cannot be discovered, listed, rebound or
    announced -- so a feature reachable only by swipe does not exist for anyone
    using a screen reader, a switch device, or a desktop.

    """

    def test_registration_requires_the_palette_command_it_duplicates(self):
        body = _function_body(GESTURES, "function register(gesture)", "function shouldIgnore")
        self.assertIn("!gesture.paletteCommand", body)
        self.assertIn("throw new Error", body)

    def test_a_gesture_is_not_registered_without_its_command(self):
        """
        Checked against the live palette, not merely declared. A shortcut for
        something that does not exist is worse than no shortcut.

        """
        body = _function_body(SHELL, "function addGesture(direction", "gestures.listen(document)")
        self.assertIn("palette.commands().some", body)
        self.assertIn("return false;", body)

    def test_every_registered_gesture_names_a_real_command(self):
        body = _function_body(SHELL, "if (gestures && palette) {", "gestures.listen(document)")
        named = set(re.findall(r'addGesture\("\w+", "[^"]+", "([\w.]+)"', body))
        self.assertTrue(named)
        for command in named:
            self.assertIn(
                '"%s"' % command,
                SHELL,
                "gesture names %r, which no palette command registers" % command,
            )

    def test_gestures_are_listable(self):
        """
        A gesture nobody can list is folklore rather than a feature.

        """
        self.assertIn("function all()", GESTURES)


class TestGesturesRespectMotorLimits(TestCase):
    """A.57's specific prohibitions."""

    def test_multi_point_gestures_are_refused(self):
        """
        Explicitly named in A.57. They exclude anyone operating a touchscreen
        one-handed, with a stylus, a head pointer or a single switch.

        """
        body = _function_body(GESTURES, "function onStart(event)", "function onEnd")
        self.assertIn("event.touches.length !== 1", body)

    def test_a_second_finger_cancels_rather_than_completes(self):
        body = _function_body(GESTURES, "function onEnd(event)", "function listen")
        self.assertIn("event.changedTouches.length !== 1", body)

    def test_nothing_requires_dragging(self):
        code = _code_only(GESTURES)
        for dragging in ("dragstart", "dragover", "ondrop", "draggable", "mousemove"):
            self.assertNotIn(dragging, code)

    def test_the_thresholds_are_set_for_a_tremor(self):
        """
        A gesture that only works when performed neatly is a gesture that fails
        for the people who most needed it to be easy.

        """
        self.assertGreaterEqual(int(re.search(r"var MIN_DISTANCE = (\d+);", GESTURES).group(1)), 40)
        self.assertGreaterEqual(
            float(re.search(r"var MAX_DRIFT_RATIO = ([\d.]+);", GESTURES).group(1)), 0.5
        )

    def test_gestures_never_block_scrolling(self):
        """
        A handler that fights the browser's own scrolling makes a page feel
        broken.

        """
        body = _function_body(GESTURES, "function listen(root)", "function all()")
        self.assertIn("{ passive: true }", body)
        self.assertNotIn("preventDefault", _code_only(GESTURES))

    def test_text_fields_and_scrolling_regions_are_left_alone(self):
        """
        A swipe that stole a scroll would make the transcript unreadable on the
        device where it is already hardest to read.

        """
        body = _function_body(GESTURES, "function shouldIgnore(target)", "function classify")
        self.assertIn("input, textarea, select, [contenteditable]", body)
        self.assertIn("#aetos-console", body)

    def test_a_gesture_announces_what_it_did(self):
        """
        A gesture is invisible and its result may be too. Somebody who swiped
        by accident needs to know what happened in order to undo it.

        """
        body = _function_body(GESTURES, "function fire(direction)", "function onStart")
        self.assertIn("announce(", body)

    def test_gestures_can_be_switched_off(self):
        body = _function_body(GESTURES, "function enabled()", "function register")
        self.assertIn('preferences.value("pointer.gestures", true)', body)


class TestOptionalByConstruction(TestCase):
    """
    The PWA is progressive enhancement on top of progressive enhancement. A game
    that has not added Aetos's URLs should get no part of it rather than a
    broken part.

    """

    def test_the_urls_are_a_separate_optional_module(self):
        from evennia.contrib.base_systems.aetos_webclient import urls

        self.assertTrue(hasattr(urls, "urlpatterns"))
        self.assertEqual(len(urls.urlpatterns), 2)

    def test_a_missing_worker_is_silent(self):
        """
        An unavailable service worker costs a player nothing they would notice,
        and a warning about a technology they did not ask for would be noise.

        """
        body = _function_body(PWA, "function register()", "function watchForUpdates")
        self.assertIn(".catch(function () {", body)
        self.assertNotIn("announce(", body)

    def test_an_insecure_origin_is_not_treated_as_an_error(self):
        body = _function_body(PWA, "function register()", "function watchForUpdates")
        self.assertIn('window.location.protocol !== "https:"', body)
        self.assertIn('"localhost"', body)

    def test_the_manifest_is_linked_relatively(self):
        """
        So it resolves under whatever path the game serves the client at.

        """
        self.assertIn('<link rel="manifest" href="aetos-manifest.json" />', TEMPLATE)

    def test_the_theme_colour_matches_the_stylesheet(self):
        """
        It is consumed before any CSS runs, so it cannot be a variable -- which
        means it can drift from the real background unless something checks.

        """
        meta = re.search(r'<meta name="theme-color" content="(#[0-9a-f]{6})"', TEMPLATE)
        self.assertIsNotNone(meta)
        css = (Path(AETOS_STATIC_DIR) / "aetos" / "css" / "aetos.css").read_text(encoding="utf-8")
        background = re.search(r"--aetos-bg:\s*(#[0-9a-f]{6});", css)
        self.assertEqual(meta.group(1), background.group(1))

    def test_the_manifest_declares_no_icons_it_does_not_have(self):
        """
        Aetos ships no artwork, and declaring icons it lacks would produce a
        broken install prompt.

        """
        from evennia.contrib.base_systems.aetos_webclient import urls

        source = Path(urls.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"icons"', source)

    def test_the_manifest_does_not_hide_the_way_out(self):
        """
        `fullscreen` hides the system back gesture and status bar, and a client
        that swallows the way out of itself is one somebody has to force-quit.

        """
        from evennia.contrib.base_systems.aetos_webclient import urls

        source = Path(urls.__file__).read_text(encoding="utf-8")
        self.assertIn('"display": "standalone"', source)
        # The word appears in the comment explaining why it is not used, so the
        # assertion is on the JSON value rather than the word. Eleventh time.
        self.assertNotIn('"display": "fullscreen"', source)
