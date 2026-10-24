"""
Tests for M26 -- security hardening.

The client was already careful: it rebuilds every piece of server markup from an
allowlist, never uses `innerHTML`, refuses `javascript:` in a symbol source,
strips `__proto__` on import, and interprets its scripting language rather than
handing it to `eval`. M26 is what a review found *around* that.

**The headline change is a Content-Security-Policy**, which turns "an XSS in this
client would be bad" into "an XSS in this client has nothing to execute". Getting
one required removing the last inline script in the page -- one inline script is
all it takes to force a game into `script-src 'unsafe-inline'`, which is the same
as having no script policy at all.

Verified enforced in a real browser rather than only present::

    an injected inline <script>          did not run
    a script from another origin         refused
    eval("1+1")                          refused

Three things a review found and this milestone did not fix, recorded so the next
reader does not assume they were missed:

- **Sync flooding is Evennia's problem and Evennia solves it.** An unauthenticated
  session can call `aetos_request_sync`, and each call runs every provider. That
  looked like unbounded amplification until measured: 2000 requests produced
  exactly 80 syncs and 1920 "You entered commands too fast" refusals. The
  Portal's `MAX_COMMAND_RATE` applies to every inputfunc, not only to `text`.
  Adding a second throttle would have duplicated it and disagreed with it.
- **`style-src` still needs `'unsafe-inline'`**, because theme tokens and layout
  sizes are written as inline styles. It permits no script execution, and the
  sanitiser accepts no `style` attribute or `<style>` element from game content,
  so there is no injection point for it to widen.
- **`frame-ancestors` cannot be expressed in a meta policy**, so clickjacking
  protection still needs a real header from the game.

"""

import re
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, csp, protocol

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
SHELL = (JS_DIR / "aetos.js").read_text(encoding="utf-8")
BOOTSTRAP = (JS_DIR / "transport_bootstrap.js").read_text(encoding="utf-8")
TEMPLATE_DIR = Path(AETOS_STATIC_DIR).parent / "templates"
BASE_TEMPLATE = (TEMPLATE_DIR / "aetos" / "base.html").read_text(encoding="utf-8")
CLIENT_TEMPLATE = (TEMPLATE_DIR / "webclient.html").read_text(encoding="utf-8")


def _markup_only(template):
    """
    Strip `{% comment %}` blocks from a template.

    Both templates explain themselves at length, and that prose says things like
    "these were an inline `<script>` until M26" -- which a scan for markup would
    otherwise find and report as the very thing it was written to describe. The
    same rule the rest of this suite follows: anchor on something that cannot
    appear in prose.

    Args:
        template (str): Template source.

    Returns:
        str: The source with comment blocks removed.

    """
    return re.sub(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", "", template, flags=re.S)


BASE_MARKUP = _markup_only(BASE_TEMPLATE)
CLIENT_MARKUP = _markup_only(CLIENT_TEMPLATE)

#: Every JavaScript file the client ships.
ALL_JS = sorted(JS_DIR.rglob("*.js")) + [
    Path(AETOS_STATIC_DIR) / "aetos" / "aetos-service-worker.js"
]


class TestTheClientHasNoInlineScript(TestCase):
    """
    The change that made a policy possible.

    """

    def test_neither_template_carries_an_inline_script(self):
        for name, template in (("base.html", BASE_MARKUP), ("webclient.html", CLIENT_MARKUP)):
            for tag in re.findall(r"<script\b[^>]*>", template):
                self.assertIn("src=", tag, "%s has an inline script: %s" % (name, tag))

    def test_neither_template_carries_an_inline_event_handler(self):
        """
        `onclick` and friends are inline script by another name, and CSP blocks
        them under the same directive.

        """
        for name, template in (("base.html", BASE_MARKUP), ("webclient.html", CLIENT_MARKUP)):
            found = re.findall(r"\son(?:click|load|error|submit|change|input|key\w+)\s*=", template)
            self.assertEqual(found, [], "%s has inline handlers: %s" % (name, found))

    def test_the_transport_values_moved_to_meta_tags(self):
        for name in (
            "aetos-websocket-active",
            "aetos-browser-sessid",
            "aetos-websocket-url",
            "aetos-websocket-port",
        ):
            self.assertIn('name="%s"' % name, BASE_TEMPLATE)

    def test_the_bootstrap_defines_what_evennia_reads(self):
        """
        These four names are Evennia's, not Aetos's. Getting one wrong produces
        a client that loads perfectly and never connects.

        """
        for global_name in ("window.wsactive", "window.csessid", "window.wsurl", "window.cuid"):
            self.assertIn(global_name + " =", BOOTSTRAP)

    def test_the_bootstrap_loads_before_evennia(self):
        """
        Deferred scripts run in document order, so position is the ordering
        guarantee. `evennia.js` reads the globals as it initialises.

        """
        self.assertLess(
            BASE_TEMPLATE.index("transport_bootstrap.js"),
            BASE_TEMPLATE.index("webclient/js/evennia.js"),
        )

    def test_an_absent_session_id_is_false_rather_than_empty(self):
        """
        `evennia.js` tests `csessid` for truthiness, and the stock template
        supplies `false`. An empty string is a different kind of absent.

        """
        self.assertIn("sessid === null ? false : sessid", BOOTSTRAP)


class TestNothingEvaluatesSource(TestCase):
    """
    `script-src 'self'` without `'unsafe-eval'` makes this a runtime guarantee
    as well as a rule. The scripting language (blueprint section 33) is
    interpreted from an AST for exactly this reason.

    """

    def test_no_module_reaches_the_javascript_evaluator(self):
        for path in ALL_JS:
            source = path.read_text(encoding="utf-8")
            # Comments in `scripting.js` discuss `eval` at length, so match the
            # call rather than the word.
            for sink in ("eval(", "new Function(", 'setTimeout("', 'setInterval("'):
                stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
                stripped = re.sub(r"^\s*//.*$", "", stripped, flags=re.M)
                self.assertNotIn(sink, stripped, "%s uses %r" % (path.name, sink))

    def test_no_module_writes_markup_as_a_string(self):
        for path in ALL_JS:
            source = path.read_text(encoding="utf-8")
            stripped = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
            stripped = re.sub(r"^\s*//.*$", "", stripped, flags=re.M)
            for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
                self.assertNotIn(sink, stripped, "%s uses %r" % (path.name, sink))


class TestTheSanitiserCannotBeMadeToRecurseForever(TestCase):
    """
    The rebuild is recursive and its input is markup a builder or another player
    was able to produce.

    """

    def test_there_is_a_depth_bound(self):
        self.assertIn("var MAX_NESTING = 64;", SHELL)
        self.assertIn("if (level > MAX_NESTING) {", SHELL)

    def test_content_past_the_bound_is_kept_as_text(self):
        """
        Not discarded. Flattening is what already happens to any tag not on the
        allowlist, so nothing a game says is lost -- which is the rule the
        sanitiser has followed since M4.

        """
        window = SHELL[SHELL.index("if (level > MAX_NESTING) {") :][:300]
        self.assertIn("createTextNode(sourceNode.textContent", window)

    def test_every_recursion_carries_the_depth(self):
        """
        A recursive call that forgot to increment would leave the bound in place
        and unreachable, which is worse than not having it: it reads as
        protection.

        """
        calls = re.findall(r"sanitizeInto\((?!sourceNode)[^)]*\)", SHELL)
        self.assertTrue(calls)
        for call in calls:
            self.assertTrue(
                "level + 1" in call or call.endswith(", 0)"),
                "sanitizeInto call does not carry depth: %s" % call,
            )


class TestTheDefaultPolicy(TestCase):
    """What a game gets without configuring anything."""

    def test_scripts_are_same_origin_with_no_inline_and_no_eval(self):
        policy = csp.build_policy()
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("'unsafe-inline'", policy.split("script-src")[1].split(";")[0])
        self.assertNotIn("'unsafe-eval'", policy)

    def test_the_websocket_is_permitted_by_scheme(self):
        """
        The websocket is usually on a different port from the page, which makes
        it a different origin -- so `'self'` does not cover it, and a game behind
        a proxy or a tunnel reaches it at a host this module cannot predict.

        """
        policy = csp.build_policy()
        connect = policy.split("connect-src")[1].split(";")[0]
        self.assertIn("ws:", connect)
        self.assertIn("wss:", connect)

    def test_the_things_aetos_never_does_are_closed_off(self):
        policy = csp.build_policy()
        for directive in ("object-src 'none'", "frame-src 'none'", "form-action 'none'"):
            self.assertIn(directive, policy)

    def test_base_uri_is_locked(self):
        """
        An injected `<base>` retargets every relative URL on the page, which
        turns one injection into control of every asset the client loads.

        """
        self.assertIn("base-uri 'none'", csp.build_policy())

    def test_media_may_come_from_elsewhere(self):
        """
        Game-declared media is commonly on a CDN. The scheme allowlist in
        `media.py` is what stops it being `javascript:`; the policy's job here
        is to not break a working game.

        """
        policy = csp.build_policy()
        self.assertIn("https:", policy.split("img-src")[1].split(";")[0])
        self.assertIn("https:", policy.split("media-src")[1].split(";")[0])


class TestGamesCanExtendThePolicy(TestCase):
    """`AETOS_CSP`, with the same strictness the other settings get."""

    def test_a_declared_source_is_added_to_the_defaults(self):
        with override_settings(AETOS_CSP={"img-src": ["https://cdn.example.com"]}):
            policy = csp.build_policy()
        images = policy.split("img-src")[1].split(";")[0]
        self.assertIn("https://cdn.example.com", images)
        # And the defaults survive: extension, not replacement.
        self.assertIn("'self'", images)
        self.assertIn("data:", images)

    def test_the_other_directives_are_untouched(self):
        with override_settings(AETOS_CSP={"img-src": ["https://cdn.example.com"]}):
            policy = csp.build_policy()
        self.assertIn("script-src 'self'", policy)

    def test_a_game_can_decline_the_policy_entirely(self):
        """
        For a game that sends its own header. Two policies both apply and the
        result is their intersection, which is the failure mode nobody debugs
        successfully.

        """
        with override_settings(AETOS_CSP=False):
            self.assertEqual(csp.build_policy(), "")

    def test_an_unknown_directive_is_refused(self):
        with override_settings(AETOS_CSP={"scrpt-src": ["'self'"]}):
            with self.assertRaises(csp.AetosCspError) as caught:
                csp.build_policy()
        self.assertIn("Valid directives", str(caught.exception))

    def test_a_directive_a_meta_policy_cannot_express_is_refused(self):
        """
        An error rather than a silent drop. A game setting `frame-ancestors`
        here believes it is protected from framing and is not, and deploy time
        is a much better moment to learn that than an incident is.

        """
        with override_settings(AETOS_CSP={"frame-ancestors": ["'none'"]}):
            with self.assertRaises(csp.AetosCspError) as caught:
                csp.build_policy()
        self.assertIn("X-Frame-Options", str(caught.exception))

    def test_a_bare_string_is_refused(self):
        """
        `{"img-src": "https://cdn"}` would otherwise iterate as characters and
        produce a policy of single letters.

        """
        with override_settings(AETOS_CSP={"img-src": "https://cdn.example.com"}):
            with self.assertRaises(csp.AetosCspError):
                csp.build_policy()

    def test_a_source_cannot_smuggle_a_separator(self):
        with override_settings(AETOS_CSP={"img-src": ["https://a.example; script-src *"]}):
            with self.assertRaises(csp.AetosCspError):
                csp.build_policy()

    def test_a_non_dict_setting_is_refused(self):
        with override_settings(AETOS_CSP=["script-src 'self'"]):
            with self.assertRaises(csp.AetosCspError):
                csp.build_policy()


class TestThePolicyIsInThePage(TestCase):
    """Declared in the document, because a contrib does not own the view."""

    def test_it_is_emitted_as_a_meta_policy(self):
        self.assertIn('http-equiv="Content-Security-Policy"', BASE_TEMPLATE)

    def test_it_comes_before_anything_it_governs(self):
        """
        A meta policy governs only what the parser has not already reached, so
        a policy after the first script tag protects nothing.

        """
        self.assertLess(
            BASE_TEMPLATE.index("Content-Security-Policy"),
            BASE_TEMPLATE.index("<script"),
        )

    def test_a_referrer_policy_is_declared(self):
        self.assertIn('name="referrer"', BASE_TEMPLATE)
        self.assertIn("strict-origin-when-cross-origin", BASE_TEMPLATE)


class TestTheHandshakeCannotBeUsedToFillTheLog(TestCase):
    """
    Evennia's Portal throttles every inputfunc to `MAX_COMMAND_RATE`, which is
    still 80 handshakes a second -- each one able to write up to 4KB of
    attacker-chosen capability names into the game's log.

    """

    def test_capability_names_and_counts_are_bounded(self):
        self.assertEqual(protocol.MAX_CAPABILITIES, 64)
        self.assertEqual(protocol.MAX_CAPABILITY_LENGTH, 64)

    def test_an_overlong_capability_list_is_refused(self):
        payload = protocol.build_hello(capabilities=["c%d" % i for i in range(200)])
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello(payload)

    def test_a_long_capability_name_is_truncated_rather_than_stored(self):
        hello = protocol.parse_hello(protocol.build_hello(capabilities=["x" * 5000]))
        for capability in hello.capabilities:
            self.assertLessEqual(len(capability), protocol.MAX_CAPABILITY_LENGTH)

    def test_unknown_capabilities_are_logged_once_per_session(self):
        source = Path(Path(AETOS_STATIC_DIR).parent / "inputfuncs.py").read_text(encoding="utf-8")
        self.assertIn('getattr(session, "aetos_logged_unknown", None)', source)
        self.assertIn("session.aetos_logged_unknown = unknown", source)

    def test_a_changed_capability_set_is_still_reported(self):
        """
        Compared against the last set logged rather than a "have logged" flag,
        so a client that genuinely changes what it advertises is not silenced
        by the first one.

        """
        source = Path(Path(AETOS_STATIC_DIR).parent / "inputfuncs.py").read_text(encoding="utf-8")
        self.assertIn("unknown != getattr(session", source)
