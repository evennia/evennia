"""
D5 -- the setup wizard and what it generates.

The wizard's reason to exist is the **test** step (Addendum B.40). A binding
that resolves to nothing looks exactly like a correct one until a browser is
open and a bar is missing, and the developer is the wrong person to find that
out last. Everything else here -- review, edit, accept, ignore -- exists to put
that test in front of a decision.

Driven by a script rather than a terminal: the wizard is handed `ask` and `say`,
so a list of answers walks it end to end and the transcript is a string the
tests read. Nothing here needs a tty, and neither does anything the wizard does.

The other half is what is *not* written. `settings.py` is never touched, a
credential never reaches a generated file, quitting writes nothing, and end of
input is a quit rather than a default -- a wizard that read EOF as "yes" would
accept everything the moment it ran without a terminal.

"""

import ast
import os
import tempfile
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient.discovery import (
    generate,
    roots,
    wizard,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    ActionCandidate,
    Candidate,
    CandidateSet,
)


class _Answers:
    """A scripted developer."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if not self.answers:
            raise EOFError("the script ran out")
        return self.answers.pop(0)


class _Resolver:
    """A stand-in resolver with fixed readings."""

    def __init__(self, values=None):
        self.values = values or {}

    def resolve(self, character, expression):
        return self.values.get(expression)

    def resolve_number(self, character, expression):
        return self.values.get(expression)


def _found(*candidates):
    """
    A candidate set holding exactly these, assessed.

    Args:
        *candidates: `Candidate` objects.

    Returns:
        CandidateSet: The set.

    """
    found = CandidateSet()
    for candidate in candidates:
        found.add(candidate)
    found.pair_maximums()
    found.assess(sampled=1)
    return found


def _health():
    """
    The addendum's own example: `db.hp` 82 with `db.hp_max` 100.

    Returns:
        CandidateSet: Holding the pair.

    """
    return _found(
        Candidate("db.hp", "hp", "runtime", "on 1 of 1", "number", observed=((1, 82),), count=1),
        Candidate(
            "db.hp_max", "hp_max", "runtime", "on 1 of 1", "number", observed=((1, 100),), count=1
        ),
    )


def _walk(found, answers, character=object(), values=None, context=None):
    """
    Run a wizard over a script and collect everything it said.

    Args:
        found (CandidateSet): What to offer.
        answers (list): The developer's answers, in order.
        character: Anything not None means a character was selected.
        values (dict, optional): What the resolver reads back.
        context (dict, optional): Wizard context.

    Returns:
        tuple: `(result, transcript, the _Answers object)`.

    """
    said = []
    script = _Answers(answers)
    walk = wizard.Wizard(
        found,
        context=context or {},
        character=character,
        ask=script,
        say=said.append,
        # `values if values is not None`, never `values or ...`: an empty dict
        # is how a test says "nothing resolves", and `or` would quietly hand it
        # working values instead -- which is the test defeating its own point.
        resolver=_Resolver({"db.hp": 82, "db.hp_max": 100} if values is None else values),
    )
    return walk.run(), "\n".join(said), script


# ----------------------------------------------------------------- B.35-B.40


class TestTheWalkthrough(TestCase):
    """B.35's screen, and the four answers it offers."""

    def test_a_candidate_is_presented_the_way_the_addendum_lays_it_out(self):
        _, transcript, _ = _walk(_health(), ["y"])
        for line in ("Possible resource found", "Suggested name:", "Test values:", "Confidence:"):
            self.assertIn(line, transcript)

    def test_the_test_step_shows_live_values(self):
        """B.40: the step that catches a mistake before a browser is open."""
        _, transcript, _ = _walk(_health(), ["y"])
        self.assertIn("82 / 100", transcript)

    def test_yes_accepts_it_in_the_shape_settings_takes(self):
        result, _, _ = _walk(_health(), ["y"])
        self.assertEqual(
            result["accepted"]["resources"]["hp"],
            {"label": "Hp", "value": "db.hp", "maximum": "db.hp_max"},
        )

    def test_no_ignores_it_and_records_that(self):
        result, transcript, _ = _walk(_health(), ["n"])
        self.assertEqual(result["accepted"], {})
        self.assertTrue(result["ignored_lines"])
        self.assertIn("Ignored", transcript)

    def test_explain_answers_and_asks_again(self):
        result, transcript, script = _walk(_health(), ["?", "y"])
        self.assertIn("Found:", transcript)
        self.assertIn("Accepting it generates:", transcript)
        self.assertEqual(len(script.prompts), 2)
        self.assertIn("hp", result["accepted"]["resources"])

    def test_quit_stops_and_keeps_nothing(self):
        result, transcript, _ = _walk(_health(), ["q"])
        self.assertTrue(result["quit"])
        self.assertEqual(result["accepted"], {})
        self.assertIn("Nothing has been written", transcript)

    def test_an_answer_that_is_not_offered_is_refused_rather_than_guessed(self):
        result, transcript, _ = _walk(_health(), ["maybe", "y"])
        self.assertIn("Please answer one of", transcript)
        self.assertIn("hp", result["accepted"]["resources"])

    def test_the_end_of_input_is_a_quit_not_a_yes(self):
        """
        Run without a terminal, `input()` raises immediately. A wizard that
        treated that as the default answer would accept everything it found.

        """
        result, _, _ = _walk(_health(), [])
        self.assertTrue(result["quit"])
        self.assertEqual(result["accepted"], {})


class TestEditing(TestCase):
    """B.38: change a candidate without editing Python."""

    def test_a_label_can_be_changed(self):
        result, _, _ = _walk(_health(), ["e", "Vitality", "", "", "y"])
        self.assertEqual(result["accepted"]["resources"]["hp"]["label"], "Vitality")

    def test_an_empty_answer_keeps_what_was_there(self):
        result, _, _ = _walk(_health(), ["e", "", "", "", "y"])
        self.assertEqual(result["accepted"]["resources"]["hp"]["value"], "db.hp")

    def test_an_expression_the_grammar_refuses_is_explained_and_not_taken(self):
        result, transcript, _ = _walk(_health(), ["e", "", "db.hp()", "", "y"])
        self.assertIn("method call", transcript)
        self.assertEqual(result["accepted"]["resources"]["hp"]["value"], "db.hp")

    def test_an_edited_expression_is_retested_before_it_is_offered(self):
        result, transcript, _ = _walk(
            _health(),
            ["e", "", "db.mana", "", "y", "y"],
            values={"db.hp": 82, "db.hp_max": 100, "db.mana": None},
        )
        self.assertIn("does not read as anything", transcript)


class TestTheTestStepGuardsAcceptance(TestCase):
    """A binding that reads nothing is the mistake this whole step exists for."""

    def test_a_failing_binding_is_not_accepted_on_a_plain_yes(self):
        result, transcript, _ = _walk(_health(), ["y", "n", "n"], values={})
        self.assertIn("does not read as anything", transcript)
        self.assertEqual(result["accepted"], {})

    def test_it_can_be_accepted_deliberately_and_is_marked(self):
        result, _, _ = _walk(_health(), ["y", "y"], values={})
        self.assertIn("hp", result["accepted"]["resources"])
        self.assertIn("test failed", " ".join(result["accepted_lines"]))

    def test_without_a_character_it_says_so_rather_than_pretending(self):
        result, transcript, _ = _walk(_health(), ["y"], character=None)
        self.assertIn("cannot be tested", transcript)
        self.assertIn("hp", result["accepted"]["resources"])


class TestTheProviderOffer(TestCase):
    """B.42: a starter provider, only where a provider is the honest answer."""

    CONTEXT = {
        "problems": [
            "characters.py reads values through character.stats, a handler... "
            "A provider class in AETOS_PROVIDERS is the supported route."
        ]
    }

    def test_it_is_offered_when_something_cannot_be_bound(self):
        result, transcript, _ = _walk(_health(), ["n", "y"], context=self.CONTEXT)
        self.assertIn("cannot be reached by a binding", transcript)
        self.assertTrue(result["provider_findings"])

    def test_it_is_not_offered_to_a_game_that_does_not_need_one(self):
        """
        Asserted on the *prompts*, not the transcript. The question goes to
        `ask` and never to `say`, so a transcript check cannot see the wizard
        asking it -- which a mutation check caught: offering the skeleton to
        every game passed a test that was only reading what was printed.

        """
        result, transcript, script = _walk(_health(), ["n"], context={"problems": []})
        self.assertEqual(len(script.prompts), 1)
        self.assertFalse(result["quit"])
        self.assertNotIn("cannot be reached by a binding", transcript)
        self.assertEqual(result["provider_findings"], [])

    def test_declining_it_writes_none(self):
        result, _, _ = _walk(_health(), ["n", "n"], context=self.CONTEXT)
        self.assertEqual(result["provider_findings"], [])


# -------------------------------------------------------------- B.41-B.44


class TestWhatIsGenerated(TestCase):
    """The three files, and the promises each of them keeps."""

    ACCEPTED = {"resources": {"hp": {"label": "Hp", "value": "db.hp", "maximum": "db.hp_max"}}}

    def test_the_bindings_file_parses_and_says_what_it_claims(self):
        source = generate.bindings_source(self.ACCEPTED)
        tree = ast.parse(source)
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        self.assertEqual(assignment.targets[0].id, "AETOS_BINDINGS")
        self.assertEqual(ast.literal_eval(assignment.value), self.ACCEPTED)

    def test_it_is_quoted_the_way_evennias_own_code_is(self):
        """
        B.41 asks for Evennia's project conventions. `repr` gives single quotes,
        and `black` -- which Evennia's CI runs -- would rewrite every line of
        this file the moment it was pasted into settings.py.

        """
        source = generate.bindings_source(self.ACCEPTED)
        self.assertIn('"db.hp"', source)
        self.assertNotIn("'db.hp'", source)

    def test_a_label_with_a_quote_in_it_cannot_break_the_file(self):
        source = generate.bindings_source(
            {"resources": {"hp": {"label": 'The "Big" One\\', "value": "db.hp"}}}
        )
        ast.parse(source)

    def test_the_provider_is_labelled_starter_code_in_capitals(self):
        source = generate.provider_source(["character.stats is a handler"])
        ast.parse(source)
        self.assertIn("STARTER CODE", source)
        self.assertIn("character.stats", source)
        self.assertIn("REPLACE", source)

    def test_the_generated_provider_marker_is_not_one_the_release_gate_bans(self):
        """
        The contrib's own "nothing left marked unfinished" release gate scans
        every Python file here for the four usual unfinished-work markers. A
        template living in this source carries its marker into that scan, so the
        generated file says REPLACE instead -- the gate keeps its teeth, and the
        developer still sees plainly what they have to finish.

        """
        # Spelled with separators that are stripped back out, so this file does
        # not itself trip the gate it is describing -- the gate scans every
        # Python file in the contrib, tests included, and it is right to.
        banned = tuple(word.replace("-", "") for word in ("TO-DO", "FIX-ME", "X-XX:", "HA-CK"))
        source = generate.provider_source(["x"])
        for marker in banned:
            self.assertNotIn(marker, source, marker)

    def test_the_report_says_what_was_read_accepted_and_ignored(self):
        text = generate.report_source(
            {"gamedir": "/game", "characters": ["#1 Ada"]},
            ["resources hp (db.hp)"],
            ["effects poisoned (db.poisoned)"],
            ["world/broken.py could not be parsed"],
            ["report.txt"],
        )
        for line in ("Accepted", "Ignored", "#1 Ada", "db.hp", "poisoned", "broken.py"):
            self.assertIn(line, text)

    def test_the_report_says_nothing_was_applied(self):
        text = generate.report_source({}, [], [], [], [])
        self.assertIn("does not edit settings.py", text)


class TestWhereItIsWritten(TestCase):
    """B.44, and the refusal underneath it."""

    def setUp(self):
        self.game = tempfile.mkdtemp()

    def test_the_three_files_land_in_aetos_discovery(self):
        written = generate.write(self.game, "report", bindings="X = 1\n", provider="Y = 2\n")
        names = sorted(os.path.basename(path) for path in written)
        self.assertEqual(names, ["report.txt", "suggested_bindings.py", "suggested_provider.py"])
        for path in written:
            self.assertTrue(os.path.dirname(path).endswith("aetos-discovery"))

    def test_only_the_report_is_written_when_nothing_was_accepted(self):
        written = generate.write(self.game, "report")
        self.assertEqual([os.path.basename(p) for p in written], ["report.txt"])

    def test_generated_python_is_parsed_before_it_is_written(self):
        """
        A generator whose output will not parse has failed at the one thing it
        is for, and the developer's editor is a late place to find that out.

        """
        with self.assertRaises(SyntaxError):
            generate.write(self.game, "report", bindings="def (:\n")
        self.assertFalse(os.path.exists(generate.output_directory(self.game)))

    def test_it_refuses_to_write_outside_the_game(self):
        outside = tempfile.mkdtemp()
        link = os.path.join(self.game, generate.OUTPUT_DIRECTORY)
        try:
            os.symlink(outside, link, target_is_directory=True)
        except (OSError, NotImplementedError, AttributeError) as error:
            self.skipTest("symlinks not permitted here (%s)" % error)
        with self.assertRaises(roots.ScanRootError):
            generate.write(self.game, "report")

    def test_settings_is_never_written(self):
        settings_file = Path(self.game) / "server" / "conf" / "settings.py"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text("ORIGINAL = True\n", encoding="utf-8")
        generate.write(self.game, "report", bindings="AETOS_BINDINGS = {}\n")
        self.assertEqual(settings_file.read_text(encoding="utf-8"), "ORIGINAL = True\n")

    def test_nothing_generated_is_importable_by_accident(self):
        """B.44: nothing generated is imported automatically."""
        generate.write(self.game, "report", bindings="AETOS_BINDINGS = {}\n")
        directory = generate.output_directory(self.game)
        self.assertFalse(os.path.exists(os.path.join(directory, "__init__.py")))

    def test_a_withheld_name_never_reaches_a_generated_file(self):
        text = generate.bindings_source({"resources": {"hp": {"label": "Hp", "value": "db.hp"}}})
        self.assertFalse(generate.contains_secret(text, {"api_token"}))
        self.assertTrue(generate.contains_secret("db.api_token", {"api_token"}))


class TestTheCommandOffersIt(TestCase):
    """One canonical command, subcommands underneath (B.34)."""

    def test_setup_is_a_subcommand(self):
        from evennia.contrib.base_systems.aetos_webclient.management.commands import (
            aetos,
        )

        self.assertIn("setup", aetos.SUBCOMMANDS)

    def test_the_wizard_owns_no_input_or_output_of_its_own(self):
        """
        A prompt loop that calls `input()` cannot be driven by anything else --
        not a test, not a future `evennia aetos apply`.

        """
        source = Path(wizard.__file__).read_text(encoding="utf-8").split('"""', 2)[2]
        for forbidden in ("input(", "print("):
            self.assertNotIn(forbidden, source, forbidden)


class TestTheGate(TestCase):
    """
    D5's gate, from the roadmap: *an inexperienced Evennia developer can go from
    a custom `db.hp`/`db.hp_max` Character to a working resource meter without
    writing a provider.*

    Asserted end to end rather than in pieces, because every piece passing is
    exactly the state the D-track could be in while the thing a developer
    actually does still fails. A character is made, discovery reads it, the
    wizard is walked, the generated file is evaluated the way a paste into
    settings.py would evaluate it, and the bar is read back out of the provider
    the client actually uses.

    """

    def setUp(self):
        from evennia.utils import create

        self.character = create.create_object(
            "evennia.objects.objects.DefaultCharacter", key="Newcomer"
        )
        self.character.db.hp = 82
        self.character.db.hp_max = 100
        self.addCleanup(self.character.delete)

    def test_from_a_bare_character_to_a_bar_with_no_python_written(self):
        import ast

        from django.test import override_settings

        from evennia.contrib.base_systems.aetos_webclient.bindings.bound_providers import (
            BoundResourceProvider,
        )
        from evennia.contrib.base_systems.aetos_webclient.discovery import (
            runtime_scan,
            wizard,
        )
        from evennia.contrib.base_systems.aetos_webclient.resources import (
            normalize_resources,
        )

        # 1. Discovery reads the character somebody actually made.
        found = CandidateSet()
        candidates, _ = runtime_scan.scan_characters([self.character])
        for candidate in candidates:
            found.add(candidate)
        found.pair_maximums()
        found.assess(sampled=1)

        # 2. The developer walks the wizard and says yes once.
        said = []
        walk = wizard.Wizard(
            found,
            character=self.character,
            ask=_Answers(["y"] * 6),
            say=said.append,
        )
        result = walk.run()
        self.assertIn("82 / 100", "\n".join(said))

        # 3. What it writes is what they would paste.
        source = generate.bindings_source(result["accepted"])
        tree = ast.parse(source)
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        declared = ast.literal_eval(assignment.value)

        # 4. Pasted, it produces the bar -- through the provider the client uses.
        with override_settings(AETOS_BINDINGS=declared):
            resources = normalize_resources(BoundResourceProvider().get_resources(self.character))

        bar = next(entry for entry in resources if entry["id"] == "hp")
        self.assertEqual(bar["value"], 82)
        self.assertEqual(bar["maximum"], 100)
        self.assertEqual(bar["label"], "Hp")


class TestActionsAreOfferedToo(TestCase):
    """A command is a candidate like any other, with nothing to test."""

    def test_an_action_can_be_accepted(self):
        found = CandidateSet()
        found.add_action(
            ActionCandidate("attack", "attack {target}", "commands/combat.py:1", "MEDIUM")
        )
        result, transcript, _ = _walk(found, ["y"])
        self.assertEqual(
            result["accepted"]["actions"]["attack"],
            {"label": "Attack", "command": "attack {target}"},
        )
        self.assertNotIn("Test values:", transcript)
