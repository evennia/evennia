"""
Tests for M22 -- the widget SDK.

Addendum C.20, and A.28 for the accessibility half (already enforced since A1).

C.20 lists six things: a versioned contract, declared identity, declared
subscriptions, declared accessibility metadata, a clean lifecycle, and failure
isolation. Four shipped at M6 and A1. This milestone adds the version and the
isolation, and the isolation is where the substance is:

    "A widget failure must not destroy the client: catch, disable the widget,
    log, show a recoverable placeholder, preserve the others."

Before M22 none of that was true of `mount`. Widgets are mounted in a `forEach`
at boot, so one game-authored widget throwing aborted the loop and every widget
after it silently never appeared. Demonstrated in the lab before it was fixed.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

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


LAYOUT = _read("layout.js")
WIDGETS = _read("widgets.js")
STORE = _read("store.js")
SHELL = _read("aetos.js")


class TestFailureIsolation(TestCase):
    """
    C.20's five requirements, one test each.

    """

    def test_mount_is_guarded(self):
        """
        The regression that mattered. Unguarded until M22, and widgets are
        mounted in a `forEach` -- so one throwing widget took every widget
        after it with it, silently.

        """
        body = _function_body(LAYOUT, "instance.context = context;", "adapter.setSize")
        self.assertIn('guard(widgetId, "mount"', body)
        self.assertIn("definition.mount(context)", body)

    def test_update_goes_through_the_same_guard(self):
        body = _function_body(LAYOUT, "var deliver = function (section, data)", "unsubscribers[")
        self.assertIn('guard(widgetId, "update"', body)

    def test_destroy_is_guarded(self):
        self.assertIn("instance.definition.destroy(instance.context)", LAYOUT)
        start = LAYOUT.index("instance.definition.destroy(instance.context)")
        window = LAYOUT[max(0, start - 200) : start]
        self.assertIn("try {", window)

    def test_a_failure_is_logged(self):
        body = _function_body(
            LAYOUT, "function guard(widgetId, phase, work)", "function disableWidget"
        )
        self.assertIn("window.console.error", body)

    def test_a_failure_reaches_the_diagnostic_report(self):
        """
        Otherwise the only record is a console line the reporter has usually
        already scrolled past.

        """
        body = _function_body(
            LAYOUT, "function guard(widgetId, phase, work)", "function disableWidget"
        )
        self.assertIn("opts.onWidgetFailure", body)
        self.assertIn('diagnostics.record("widget:"', SHELL)

    def test_a_disabled_widget_shows_a_placeholder(self):
        """
        Not an empty panel. A player looking at a blank inventory needs to know
        whether they are carrying nothing or looking at a broken client.

        """
        body = _function_body(
            LAYOUT, "function disableWidget(widgetId, phase, err)", "function revive"
        )
        self.assertIn("stopped working and has been switched off", body)
        # Split across a line break in the source, so asserted in halves.
        self.assertIn("The rest of the ", body)
        self.assertIn("client is unaffected", body)

    def test_the_placeholder_is_recoverable(self):
        """
        C.20 says "recoverable". A widget broken by one bad payload often works
        on the next, and making somebody reload the whole client to find out is
        a poor trade for a button.

        """
        body = _function_body(
            LAYOUT, "function disableWidget(widgetId, phase, err)", "function revive"
        )
        self.assertIn("Try again", body)
        self.assertIn("revive(widgetId)", body)

    def test_reviving_remounts_from_scratch(self):
        """
        Rather than resuming: whatever state it had when it broke is exactly
        the state that broke it.

        """
        body = _function_body(LAYOUT, "function revive(widgetId)", "function defaultRegionFor")
        self.assertIn("remove(widgetId)", body)
        self.assertIn("add(widgetId, config)", body)

    def test_a_disabled_widget_stops_consuming_events(self):
        """
        Or it keeps failing invisibly.

        """
        body = _function_body(
            LAYOUT, "function disableWidget(widgetId, phase, err)", "function revive"
        )
        self.assertIn("unsubscribers[widgetId]", body)
        self.assertIn("delete unsubscribers[widgetId]", body)

    def test_a_mount_failure_disables_immediately(self):
        """
        A widget that could not build itself has nothing to retry with.

        """
        body = _function_body(
            LAYOUT, "function guard(widgetId, phase, work)", "function disableWidget"
        )
        self.assertIn('phase === "mount"', body)

    def test_repeated_update_failures_eventually_disable(self):
        """
        More than one, because a single bad sync should not permanently cost a
        player a panel. Not many more, because a widget failing every update is
        not going to recover and its errors drown everything else.

        """
        self.assertIn("var MAX_WIDGET_FAILURES = 3;", LAYOUT)
        body = _function_body(
            LAYOUT, "function guard(widgetId, phase, work)", "function disableWidget"
        )
        self.assertIn("failures[widgetId] >= MAX_WIDGET_FAILURES", body)

    def test_the_failure_is_announced(self):
        """
        A panel that quietly turns into a paragraph is a change somebody using
        a screen reader would never notice.

        """
        body = _function_body(
            LAYOUT, "function disableWidget(widgetId, phase, err)", "function revive"
        )
        self.assertIn("opts.announce", body)

    def test_disabled_widgets_are_enumerable(self):
        self.assertIn("function disabledWidgets()", LAYOUT)
        self.assertIn("disabledWidgets: disabledWidgets", LAYOUT)


class TestTheVersionedContract(TestCase):
    """
    C.20's first requirement.

    A game-bundled widget outlives the Aetos release it was written for, and
    the failure it would otherwise produce is a mount error in somebody else's
    game months later with nothing pointing at the cause.

    """

    def test_the_sdk_declares_a_version(self):
        self.assertIn("var SDK_VERSION = 1;", WIDGETS)
        self.assertIn("SDK_VERSION: SDK_VERSION", WIDGETS)

    def test_declaring_a_version_is_optional(self):
        """
        Every widget Aetos ships omits it, and none of them should have to
        change when the number moves.

        """
        body = _function_body(
            WIDGETS, "if (definition.sdkVersion !== undefined)", "if (typeof definition.displayName"
        )
        self.assertIn("!== undefined", body)

    def test_a_newer_version_is_refused_with_advice(self):
        body = _function_body(
            WIDGETS, "if (definition.sdkVersion !== undefined)", "if (typeof definition.displayName"
        )
        self.assertIn("newer than this", body)
        self.assertIn("update Aetos", body)

    def test_an_older_version_is_refused_with_advice(self):
        body = _function_body(
            WIDGETS, "if (definition.sdkVersion !== undefined)", "if (typeof definition.displayName"
        )
        self.assertIn("older than this", body)
        self.assertIn("docs/widget-sdk.md", body)


class TestTheStoreSchedulerFix(TestCase):
    """
    A latent bug M22 surfaced while testing update failures.

    The guard was `if (frameHandle !== null) return;`, which conflates "a flush
    is pending" with "the scheduler returned a cancellable handle".
    `requestAnimationFrame` returns a number so it worked in a browser -- but an
    injected scheduler running synchronously returns `undefined`, and
    `undefined !== null` is true, so every flush after the first was skipped.

    That is a bad failure for the one seam whose purpose is making update
    behaviour testable: it delivered exactly one update and then went quiet.

    """

    def test_the_pending_flag_is_separate_from_the_handle(self):
        self.assertIn("var flushQueued = false;", STORE)
        body = _function_body(STORE, "function markChanged(section)", "function flush()")
        self.assertIn("if (flushQueued)", body)
        self.assertNotIn("frameHandle !== null", body)

    def test_the_flag_is_cleared_on_flush(self):
        body = _function_body(STORE, "function flush()", "function set(section, value)")
        self.assertIn("flushQueued = false", body)

    def test_cancelling_tolerates_an_undefined_handle(self):
        self.assertIn("frameHandle !== null && frameHandle !== undefined", STORE)

    def test_a_synchronous_scheduler_is_a_supported_seam(self):
        """
        The scheduler is injectable precisely so update behaviour can be
        exercised without animation frames -- which a backgrounded browser does
        not run at all.

        """
        self.assertIn("opts.schedule ||", STORE)


class TestNoPluginMarketplace(TestCase):
    """
    C.20: "No arbitrary remote plugin marketplace."

    Downloading and executing third-party JavaScript brings code trust, supply
    chain, signing, update, sandbox and RCE problems the core contrib does not
    need. The SDK targets game-bundled and developer-authored widgets.

    """

    def test_nothing_loads_a_widget_from_a_url(self):
        code = _code_only(WIDGETS) + _code_only(LAYOUT)
        for forbidden in ("import(", 'createElement("script")', "eval(", "new Function", "fetch("):
            self.assertNotIn(forbidden, code, "the widget layer uses %r" % forbidden)

    def test_widgets_are_registered_in_process(self):
        """
        A widget arrives by being registered, which means it was already in the
        page -- shipped by the game or by Aetos.

        """
        self.assertIn("function register(definition)", WIDGETS)


class TestTheContractIsDocumented(TestCase):
    """
    M22's other half: the SDK is a document as much as an API.

    """

    def _doc(self):
        """
        Locate the SDK guide.

        Returns:
            Path: The document.

        """
        return (
            Path(AETOS_STATIC_DIR).parent.parent.parent.parent.parent.parent
            / "docs"
            / "widget-sdk.md"
        )

    def test_the_guide_exists(self):
        doc = self._doc()
        if not doc.is_file():
            self.skipTest("docs/ lives in the published repo, not the contrib")
        self.assertTrue(doc.read_text(encoding="utf-8").strip())

    def test_it_covers_every_c20_requirement(self):
        doc = self._doc()
        if not doc.is_file():
            self.skipTest("docs/ lives in the published repo, not the contrib")
        text = doc.read_text(encoding="utf-8").lower()
        for topic in (
            "sdkversion",
            "subscriptions",
            "accessibility",
            "mount",
            "destroy",
            "failure",
        ):
            self.assertIn(topic, text, "the SDK guide does not cover %r" % topic)

    def test_it_says_there_is_no_marketplace(self):
        doc = self._doc()
        if not doc.is_file():
            self.skipTest("docs/ lives in the published repo, not the contrib")
        self.assertIn("marketplace", doc.read_text(encoding="utf-8").lower())
