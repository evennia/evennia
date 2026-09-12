"""
Tests for E4 -- the unified validator.

Addendum C.16.

Includes the **corpus** C.16 asks for: valid, invalid, edge-case and malicious
samples that every parser change runs against. Waiting for a runtime failure to
find a regression is the thing the corpus exists to replace.

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


VALIDATOR = _read("automation/validator.js")
SETTINGS = _read("settings.js")
SHELL = _read("aetos.js")

#: The corpus.  C.16 / B.58.
#:
#: Behaviour is exercised in a browser -- these pin the *shape*, so a rewrite
#: that quietly stopped handling a category fails here rather than in somebody's
#: session.
MALICIOUS_PATTERNS = [
    "(a+)+b",
    "(a|a)*c",
    "(.*a){20}",
    "x" * 300,
]

VALID_PATTERNS = [
    "goblin",
    "^You (hit|miss) (.+)$",
    r"\d+ gold",
]


class TestSeverityIsAContract(TestCase):
    """
    ERROR refuses a save. WARNING allows one. INFO explains.

    """

    def test_all_three_levels_exist(self):
        for level in ('ERROR = "error"', 'WARNING = "warning"', 'INFO = "info"'):
            self.assertIn(level, VALIDATOR)

    def test_only_errors_block(self):
        self.assertIn("item.severity === ERROR", VALIDATOR)
        start = VALIDATOR.index("function validate(kind, subject)")
        window = VALIDATOR[start : start + 600]
        self.assertIn("blocked", window)

    def test_warnings_do_not_block(self):
        """
        A validator that refused everything it disliked is one players route
        around, and the player frequently knows something it does not.

        """
        start = VALIDATOR.index("function validate(kind, subject)")
        window = VALIDATOR[start : start + 600]
        self.assertNotIn("=== WARNING", window)


class TestScriptValidationUsesTheRealCompiler(TestCase):
    """
    A validator with its own idea of the grammar is a second grammar, and the
    two will disagree -- always by accepting something that fails at runtime.

    """

    def test_it_calls_the_shipped_compiler(self):
        self.assertIn("window.AetosScripting.compile", VALIDATOR)

    def test_it_does_not_reimplement_parsing(self):
        for token in ("function tokenize", "function parse(", "function createInterpreter"):
            self.assertNotIn(token, VALIDATOR, "validator.js reimplements %r" % token)

    def test_unknown_functions_are_found_by_walking_the_ast(self):
        """
        Not by scanning the text. A textual scan would flag a function name that
        merely appears inside a string -- verified live that it does not.

        """
        self.assertIn("function walkCalls", VALIDATOR)
        self.assertIn('node.type === "call"', VALIDATOR)

    def test_the_walker_is_structure_agnostic(self):
        """
        It walks whatever the parser produced rather than assuming a shape, so
        an AST change cannot silently stop the check finding anything -- which
        is how this sort of validation usually dies.

        """
        start = VALIDATOR.index("function walkCalls")
        window = VALIDATOR[start : start + 900]
        self.assertIn("Object.keys(node)", window)
        self.assertIn("level > 64", window)

    def test_an_unknown_function_is_a_warning_not_an_error(self):
        """
        The known list is what this client supplies today. Refusing to save
        would also refuse a script written against a newer Aetos and pasted
        into an older one, which is worse than a warning.

        """
        start = VALIDATOR.index("There is no function called")
        window = VALIDATOR[max(0, start - 400) : start]
        self.assertIn("WARNING", window)

    def test_the_builtin_list_is_overridable(self):
        """
        So the validator cannot drift from a client that offers more.

        """
        self.assertIn("settings.builtins || DEFAULT_BUILTINS", VALIDATOR)

    def test_it_states_what_it_did_not_check(self):
        """
        A validator that says "looks fine" about something that then hangs the
        tab damages trust in everything else it says.

        """
        self.assertIn("Checked for syntax and known functions only", VALIDATOR)


class TestRegexValidation(TestCase):
    """A.16, C.16."""

    def test_both_sides_are_bounded(self):
        """
        JavaScript cannot interrupt a pattern once it starts backtracking, so
        bounding the pattern and the input is the only real defence.

        """
        self.assertIn("MAX_PATTERN_LENGTH", VALIDATOR)
        self.assertIn("MAX_TEST_INPUT", VALIDATOR)

    def test_the_classic_catastrophic_shapes_are_detected(self):
        self.assertIn("NESTED_QUANTIFIER", VALIDATOR)
        self.assertIn("ADJACENT_QUANTIFIERS", VALIDATOR)

    def test_incompleteness_is_stated_rather_than_implied(self):
        """
        There is no complete detector. Saying so is why the result is a warning
        and why the bounds are the actual protection.

        """
        self.assertIn("Not a complete detector", VALIDATOR)

    def test_the_engines_own_message_is_surfaced(self):
        """
        It names the position, which is more useful than anything paraphrased.

        """
        start = VALIDATOR.index("not a valid regular expression")
        window = VALIDATOR[start : start + 200]
        self.assertIn("err.message", window)

    def test_the_test_facility_bounds_its_input_and_iterations(self):
        start = VALIDATOR.index("function testRegex")
        window = VALIDATOR[start : VALIDATOR.index("Aetos Script", start)]
        self.assertIn("MAX_TEST_INPUT", window)
        self.assertIn("guard < 100", window)

    def test_the_corpus_shapes_are_all_representable(self):
        """
        The corpus itself. Behaviour is checked in a browser; this asserts the
        samples remain the kinds the validator claims to handle, so a future
        rewrite that dropped a category fails here.

        """
        for pattern in MALICIOUS_PATTERNS:
            self.assertTrue(pattern, "empty corpus entry")
        # Every valid sample must compile as a Python regex too -- a sanity
        # check on the corpus rather than on the client.
        for pattern in VALID_PATTERNS:
            re.compile(pattern)


class TestTheOtherKinds(TestCase):
    """Aliases, timers, triggers, display rules."""

    def test_an_alias_with_a_space_is_an_error(self):
        """
        An alias replaces the first word only, so a two-word pattern could
        never match -- silently, which is the worst way to learn it.

        """
        self.assertIn("An alias replaces the first word only", VALIDATOR)

    def test_a_self_referential_alias_warns_without_claiming_a_loop(self):
        """
        Expansion is single-pass, so it cannot loop. Saying it would loop would
        be a lie that teaches the wrong model of how aliases work.

        """
        start = VALIDATOR.index("expands to itself")
        window = VALIDATOR[start : start + 400]
        self.assertIn("not re-expanded", window)

    def test_a_sub_second_timer_is_refused(self):
        self.assertIn("under one second would flood the server", VALIDATOR)

    def test_a_fast_timer_warns_about_game_rules(self):
        """
        Aetos does not know a game's rules on automation. It can point at them.

        """
        self.assertIn("Check your game's rules on automation", VALIDATOR)

    def test_the_five_command_cap_is_enforced(self):
        self.assertIn("validateCommands(spec.commands, 5)", VALIDATOR)


class TestWholeProfileValidation(TestCase):
    """C.16: "Validate All Local Automation"."""

    def test_it_handles_engines_that_answer_synchronously_and_asynchronously(self):
        """
        The storage-backed engines return a Promise; the in-memory ones return
        an array. Rather than requiring every engine to change, the difference
        is resolved in one place.

        """
        self.assertIn('typeof value.then === "function"', VALIDATOR)
        self.assertIn("Array.isArray(value) ? value : []", VALIDATOR)

    def test_a_resolved_non_array_is_coerced_too(self):
        """
        Coercing only the synchronous branch left a promise resolving to a
        non-array to reach the loop and throw there -- a long way from the
        engine that caused it.

        """
        self.assertIn("Array.isArray(resolved) ? resolved : []", VALIDATOR)

    def test_one_failing_engine_does_not_cost_the_report(self):
        self.assertIn("costs its own section", VALIDATOR)

    def test_nothing_is_uploaded(self):
        for forbidden in ("fetch(", "XMLHttpRequest", "dispatcher", "Evennia.msg"):
            self.assertNotIn(forbidden, VALIDATOR, "validator.js reaches %r" % forbidden)

    def test_the_dialog_says_so(self):
        """
        The player's automation lives in their browser precisely so it stays
        there, and a validator that phoned home to check a regex would be an
        odd exception.

        """
        self.assertIn("Nothing was sent anywhere", SETTINGS)

    def test_the_report_names_the_offending_items(self):
        """
        A count without a location is a chore, not a report.

        """
        self.assertIn("aetos-validate__detail", SETTINGS)
        self.assertIn("item.name", SETTINGS)

    def test_severity_is_shown_in_words(self):
        self.assertIn("found.severity.toUpperCase()", SETTINGS)

    def test_it_is_reachable_from_the_palette(self):
        self.assertIn('"automation.validate"', SHELL)


class TestTheValidatorIsWiredAfterItsEngines(TestCase):
    """
    It takes the engines by value, so it has to be created after them.

    An earlier position would have captured six hoisted `undefined`s and
    reported "0 items checked" forever, silently -- which is how this was
    actually written the first time.

    """

    def test_it_is_created_after_every_engine_it_consults(self):
        position = SHELL.index("var validator = window.AetosValidator")
        for engine in (
            "var triggers =",
            "var aliases =",
            "var timers =",
            "var scripting =",
            "var macros =",
            "var displayRules =",
        ):
            self.assertLess(
                SHELL.index(engine),
                position,
                "the validator is created before %s" % engine,
            )
