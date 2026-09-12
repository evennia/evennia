"""
Structural guards on the Aetos scripting sandbox.

Blueprint section 33 forbids a scripting environment from reaching the DOM,
cookies, credentials, arbitrary fetch, WebSocket creation or eval.

Behaviour is exercised in a browser by `browser-qa/qa-scripting.js`, which tries
to escape. These tests assert the *structure* that makes escape impossible
rather than merely blocked: there is no interpreter path to the host runtime, so
there is nothing to block.

That distinction is the whole design. A sandbox built around `eval` must
enumerate and forbid every route out, and every such sandbox broken in the wild
was broken by a route nobody enumerated. A sandbox built as an interpreter can
only do what it implements.

"""

import re
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, manifest

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
SCRIPTING = (JS_DIR / "scripting.js").read_text(encoding="utf-8")


def _strip_comments(source):
    """
    Remove JS comments.

    The commentary names the very constructs being forbidden, so assertions
    about code must not see it.

    Args:
        source (str): JavaScript source.

    Returns:
        str: Source with comments removed.

    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"^\s*//.*$", "", without_block, flags=re.MULTILINE)


CODE = _strip_comments(SCRIPTING)


class TestNoDynamicEvaluation(TestCase):
    """The interpreter never hands anything to the JavaScript runtime."""

    def test_no_eval(self):
        self.assertNotIn("eval(", CODE)

    def test_no_function_constructor(self):
        self.assertNotIn("new Function", CODE)

    def test_no_string_timers(self):
        """setTimeout with a string argument is eval by another name."""
        self.assertNotIn('setTimeout("', CODE)
        self.assertNotIn('setInterval("', CODE)

    def test_no_worker_or_import(self):
        """
        A Worker would isolate the DOM but still grant fetch, WebSocket and
        importScripts -- exactly the network reach section 33 forbids.

        """
        self.assertNotIn("Worker(", CODE)
        self.assertNotIn("importScripts", CODE)


class TestNoNetworkOrStorageReach(TestCase):
    """A script cannot talk to anything."""

    def test_no_network_apis(self):
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "EventSource"):
            self.assertNotIn(forbidden, CODE, "scripting.js references %r" % forbidden)

    def test_no_credential_or_cookie_access(self):
        for forbidden in ("document.cookie", "localStorage", "sessionStorage", "credentials"):
            self.assertNotIn(forbidden, CODE, "scripting.js references %r" % forbidden)

    def test_no_dom_access(self):
        """
        The interpreter builds no DOM and reads none. `echo` reaches the console
        through a host function the shell supplies, not through the language.

        """
        for forbidden in (
            "document.querySelector",
            "document.createElement",
            "document.body",
            "innerHTML",
        ):
            self.assertNotIn(forbidden, CODE, "scripting.js references %r" % forbidden)


class TestTheGrammarCannotExpressDanger(TestCase):
    """
    The strongest guarantee is not a blocklist but an absent feature.

    A script cannot reach a host object because the language has no syntax for
    property access, indexing, or function definition. There is nothing to
    filter.

    """

    def test_calls_resolve_only_against_the_injected_api(self):
        """
        A call names a function in the host-supplied API by string. There is no
        way to obtain a function value, so nothing else is callable.

        """
        self.assertIn("hasOwnProperty.call(api, node.name)", CODE)

    def test_host_objects_cannot_enter_script_space(self):
        """
        An API function returning an object would hand the script a reference it
        could not otherwise obtain, so returns are stringified.

        """
        self.assertIn('typeof result === "object"', CODE)

    def test_the_tokenizer_accepts_no_member_or_index_syntax(self):
        """
        The punctuation the tokenizer recognises does not include `.` or `[`, so
        `window.document` and `a[0]` cannot be tokenised at all.

        """
        match = re.search(r'if \("([^"]+)"\.indexOf\(ch\) !== -1\)', CODE)
        self.assertIsNotNone(match, "punctuation set not found")
        punctuation = match.group(1)
        self.assertNotIn(".", punctuation)
        self.assertNotIn("[", punctuation)


class TestExecutionIsBounded(TestCase):
    """
    A halting oracle is not available, so the interpreter counts.

    Every bound exists because exceeding it would otherwise freeze the player's
    browser with no way back.

    """

    def test_every_bound_is_declared(self):
        for limit in (
            "MAX_STEPS",
            "MAX_LOOP_ITERATIONS",
            "MAX_CALL_DEPTH",
            "MAX_STRING_LENGTH",
            "MAX_RUNTIME_MS",
            "MAX_SOURCE_LENGTH",
        ):
            self.assertIn(limit, CODE, "missing bound %r" % limit)

    def test_wall_clock_is_checked_as_well_as_steps(self):
        """A script can be slow without being long."""
        self.assertIn("MAX_RUNTIME_MS", CODE)

    def test_division_by_zero_is_an_error(self):
        """Infinity propagating through a script is worse than stopping."""
        self.assertIn("Division by zero", SCRIPTING)


class TestScriptingPolicy(TestCase):
    """The game decides whether scripting exists at all."""

    def test_scripting_is_disabled_by_default(self):
        """
        The highest-risk capability defaults off. A game must opt in
        deliberately.

        """
        self.assertFalse(manifest.build_manifest()["automation"]["scripting"])

    @override_settings(AETOS_AUTOMATION={"scripting": True})
    def test_a_game_can_enable_scripting(self):
        self.assertTrue(manifest.build_manifest()["automation"]["scripting"])

    def test_the_client_checks_permission_before_running(self):
        self.assertIn("isAllowed()", CODE)

    def test_a_refusal_is_explained(self):
        self.assertIn("does not allow scripting", SCRIPTING)


class TestTimerPolicy(TestCase):
    """
    Timers act without the player at the keyboard, which is close enough to
    unattended play that many games forbid it.

    """

    def setUp(self):
        self.raw = (JS_DIR / "timers.js").read_text(encoding="utf-8")
        self.timers = _strip_comments(self.raw)

    def test_timers_are_disabled_by_default(self):
        self.assertFalse(manifest.build_manifest()["automation"]["timers"])

    def test_timers_check_permission_before_starting(self):
        self.assertIn("isAllowed", self.timers)

    def test_a_running_timer_notices_policy_being_withdrawn(self):
        """
        A game can reload its settings mid-session. A timer that kept firing
        after being forbidden would be automation the game explicitly refused.

        """
        self.assertIn("no longer allowed", self.raw)

    def test_intervals_are_clamped_not_rejected(self):
        """
        A player asking for 10ms wants "as fast as allowed", not an error -- but
        the game must not be hammered because someone typed a zero too few.

        """
        self.assertIn("Math.max(MIN_INTERVAL", self.timers)

    def test_the_number_of_active_timers_is_capped(self):
        self.assertIn("MAX_ACTIVE", self.timers)


class TestScriptsUseTheSharedQueue(TestCase):
    """
    Section 28: every chained command goes through one queue, so a script gets
    the same caps, ordering and stop-on-failure as anything else.

    """

    def test_the_script_api_sends_through_the_queue(self):
        shell = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))
        self.assertIn("commandQueue.run([String(text)]", shell)

    def test_echo_never_reaches_the_game(self):
        """
        `echo` writes to the player's own console. If it sent a command instead,
        a script author would be broadcasting their debugging to the room.

        """
        shell = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
        self.assertIn("consoleWidget.append(String(text))", shell)
