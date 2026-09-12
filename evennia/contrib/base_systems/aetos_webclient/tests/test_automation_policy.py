"""
Tests for the automation policy contract.

Blueprint section 32: the game decides which automation the client may offer, and
the client must honour that rather than quietly ignoring it. A player's macros
are their own data, but permission to run them is not the player's to grant.

Behaviour is exercised in a browser by `browser-qa/qa-macros-queue.js`. What
Python pins down is the policy surface and the structural limits, so a regression
fails in the Evennia suite even if nobody runs the browser QA.

"""

import re
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, manifest

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


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


class TestAutomationPolicyIsDeclared(TestCase):
    """The manifest carries the game's decision."""

    def test_macros_are_permitted_by_default(self):
        """
        A macro sends ordinary commands the player could type, so the safe
        default is to allow them. Scripting, which is far more powerful, defaults
        the other way.

        """
        automation = manifest.build_manifest()["automation"]
        self.assertTrue(automation["macros"])
        self.assertFalse(automation["scripting"])

    @override_settings(AETOS_AUTOMATION={"macros": False})
    def test_a_game_can_forbid_macros(self):
        self.assertFalse(manifest.build_manifest()["automation"]["macros"])

    @override_settings(AETOS_AUTOMATION={"macros": False})
    def test_forbidding_macros_leaves_other_policy_alone(self):
        automation = manifest.build_manifest()["automation"]
        self.assertTrue(automation["aliases"])
        self.assertTrue(automation["triggers"])


class TestClientHonoursThePolicy(TestCase):
    """
    The client reads the policy rather than assuming.

    A client that ignored the manifest would let a player run macros on a game
    that had explicitly disabled them.

    """

    def setUp(self):
        self.shell = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))
        self.macros = _strip_comments((JS_DIR / "macros.js").read_text(encoding="utf-8"))

    def test_the_shell_reads_the_manifest_policy(self):
        self.assertIn("automation.macros", self.shell)

    def test_macros_check_permission_before_running(self):
        self.assertIn("isAllowed", self.macros)

    def test_a_forbidden_macro_is_refused_audibly(self):
        """
        A button that silently does nothing reads as a broken client. Saying
        the game does not allow macros is information.

        """
        self.assertIn("does not allow macros", self.macros)


class TestQueueLimitsAreStructural(TestCase):
    """
    Blueprint sections 27 and 28.

    These are enforced in code rather than documented, because a macro that
    quietly grew to fifty commands would be a spam vector, and a queue that kept
    firing after a failed step is how a player ends up somewhere they never
    chose.

    """

    def setUp(self):
        self.queue = _strip_comments((JS_DIR / "queue.js").read_text(encoding="utf-8"))
        self.macros = _strip_comments((JS_DIR / "macros.js").read_text(encoding="utf-8"))

    def test_the_five_command_macro_limit_exists(self):
        self.assertIn("MAX_MACRO_COMMANDS = 5", self.queue)
        self.assertIn("MAX_COMMANDS = 5", self.macros)

    def test_the_limit_is_applied_on_save(self):
        """
        Applying the cap when saving means an over-long macro cannot be smuggled
        in by editing an exported profile and importing it.

        """
        self.assertIn("slice(0, MAX_COMMANDS)", self.macros)

    def test_queue_length_is_capped(self):
        self.assertIn("MAX_QUEUE_LENGTH", self.queue)

    def test_queue_stops_on_a_failed_step(self):
        self.assertIn("verify", self.queue)
        self.assertIn("outcome.ok", self.queue)

    def test_queue_pauses_rather_than_discarding_on_disconnect(self):
        self.assertIn("paused = true", self.queue)
        self.assertIn("isConnected", self.queue)

    def test_reconnecting_does_not_auto_resume(self):
        """
        Section 60 forbids dumping accumulated commands on reconnect without an
        explicit policy, so resuming requires someone to ask.

        """
        self.assertIn("function resume()", self.queue)

    def test_a_new_sequence_replaces_rather_than_interleaves(self):
        """Two sequences at once would produce an order neither caller wanted."""
        self.assertIn("if (active) {", self.queue)


class TestOneQueueForEverything(TestCase):
    """
    Section 28 requires all chained commands to go through one queue.

    Click-to-walk originally had its own walker. Keeping two would mean the
    safety properties had to be re-derived -- and eventually forgotten -- in each.

    """

    def setUp(self):
        self.shell = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))

    def test_route_walking_uses_the_shared_queue(self):
        self.assertIn("commandQueue.run(steps", self.shell)

    def test_no_separate_route_timer_remains(self):
        """The old walker drove itself with its own timer; it must be gone."""
        self.assertNotIn("stepRoute", self.shell)

    def test_macros_use_the_shared_queue(self):
        macros = _strip_comments((JS_DIR / "macros.js").read_text(encoding="utf-8"))
        self.assertIn("queue.run(macro.commands", macros)


class TestAliasSafety(TestCase):
    """
    Blueprint section 29: alias expansion must be bounded.

    A player who defines `a -> b` and later `b -> a` has built an infinite loop
    without noticing, because each definition is reasonable on its own. The next
    time they type `a`, an unbounded expander would hang their browser.

    """

    def setUp(self):
        self.source = _strip_comments((JS_DIR / "aliases.js").read_text(encoding="utf-8"))

    def test_expansion_depth_is_bounded(self):
        self.assertIn("MAX_DEPTH", self.source)

    def test_cycles_are_detected_separately_from_depth(self):
        """
        A depth limit alone would grind through ten pointless expansions on
        every use and never tell the player why. Detecting the cycle reports the
        actual problem.

        """
        self.assertIn("report.cycle", self.source)

    def test_cycle_detection_is_by_identity_not_by_text(self):
        """
        `a -> b a` produces different text each pass while still looping
        forever, so comparing output text would not catch it.

        """
        self.assertIn("seen[alias.id]", self.source)

    def test_aliases_honour_the_game_policy(self):
        self.assertIn("isAllowed", self.source)


class TestTriggerSafety(TestCase):
    """
    Blueprint sections 30 and 62.

    A trigger sends commands in response to game output, and commands produce
    output. That is a feedback loop with a player's account on one end.

    """

    def setUp(self):
        self.source = _strip_comments((JS_DIR / "triggers.js").read_text(encoding="utf-8"))

    def test_each_trigger_has_a_cooldown(self):
        self.assertIn("cooldown", self.source)

    def test_a_global_rate_limit_exists(self):
        """
        The per-trigger cooldown cannot catch two triggers firing each other,
        so a global limiter backs it up.

        """
        self.assertIn("RATE_LIMIT", self.source)
        self.assertIn("withinRateLimit", self.source)

    def test_a_runaway_trigger_is_disabled_not_throttled(self):
        """
        Silently throttling forever leaves a player wondering why their client
        feels broken. Disabling it and saying so is actionable.

        """
        self.assertIn("trigger.enabled = false", self.source)
        self.assertIn("has been disabled", self.source)

    def test_regex_patterns_are_validated_at_save_time(self):
        """
        An invalid pattern must fail once, when saved -- not throw on every line
        of game output for the rest of the session.

        """
        self.assertIn("new RegExp(record.pattern)", self.source)

    def test_structured_triggers_are_edge_triggered(self):
        """
        A health trigger must fire when health drops below the threshold, not
        once per sync for as long as the player is hurt.

        """
        self.assertIn("previouslyTrue", self.source)

    def test_trigger_command_count_is_capped(self):
        self.assertIn("MAX_COMMANDS", self.source)

    def test_triggers_honour_the_game_policy(self):
        self.assertIn("isAllowed", self.source)


class TestAliasesApplyOnlyToTypedInput(TestCase):
    """
    Aliases expand what the player types, and nothing else.

    Expanding macro, menu, map or trigger commands would let an alias change
    silently alter what a saved macro does, and would compound with the
    recursion limit in ways nobody could reason about.

    """

    def setUp(self):
        self.shell = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))

    def test_expansion_happens_in_the_input_submit_path(self):
        self.assertIn("aliases.expandInput(raw)", self.shell)

    def test_the_queue_does_not_expand_aliases(self):
        """
        The queue sends commands verbatim; anything reaching it has already been
        resolved by whoever queued it.

        """
        queue = _strip_comments((JS_DIR / "queue.js").read_text(encoding="utf-8"))
        self.assertNotIn("alias", queue.lower())

    def test_macros_do_not_expand_aliases(self):
        macros = _strip_comments((JS_DIR / "macros.js").read_text(encoding="utf-8"))
        self.assertNotIn("alias", macros.lower())


class TestTextTriggersSeePlainText(TestCase):
    """
    Trigger patterns match the text a player sees, not the markup.

    Evennia renders colour to HTML server-side. Matching against that would make
    a pattern depend on colour codes the player never sees, so a trigger would
    mysteriously stop working when a game recoloured a message.

    """

    def test_the_shell_strips_markup_before_matching(self):
        """
        The stripping moved into `normalize` when a defect showed that the
        display rules were matching the markup the triggers had already learned
        to strip. Derived once, for everything that matches text, so the two
        agree by construction rather than by two implementations happening to.

        """
        shell = _strip_comments((JS_DIR / "aetos.js").read_text(encoding="utf-8"))
        self.assertIn("holder.textContent", shell)
        self.assertIn("plainText: plain", shell)
        self.assertIn("triggers.onText(event.plainText", shell)
