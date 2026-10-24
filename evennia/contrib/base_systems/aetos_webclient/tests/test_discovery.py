"""
Tests for D0, the discovery architecture spike.

D0's job is to settle four things and prove two. The four are the entry point,
the package boundary, the candidate model and the security model; the two proofs
are that source can be read without importing it and that a live Character can be
inspected. These tests are how each of those is stated.

**The entry point was the open question**, recorded as `questions.md` 4:
`evennia aetos discover` is the experience Addendum B.34 asks for, and it was not
known whether Evennia's launcher could be extended to provide it. It can, and
without being extended at all. The launcher handles a fixed list of operations
and passes everything else to Django's management-command dispatch with the
command line intact, so a management command named `aetos` in an installed app
*is* `evennia aetos`. Aetos is already an installed app, because it has to be for
its templates and static files to load.

**The security model is most of what is below**, and that is the right
proportion. Discovery reads a developer's source and their live database from a
command they are trying for the first time, and every plausible way to make it
more capable makes it less safe: import the module and use `dir()`, evaluate the
right-hand side to learn the value, follow the symlink, write the settings block
out for them. Each of those has a test here saying no, and why.

"""

import ast
import os
import tempfile
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR
from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.discovery import (
    candidates as candidates_module,
)
from evennia.contrib.base_systems.aetos_webclient.discovery import (
    report,
    roots,
    runtime_scan,
    static_scan,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    Candidate,
    CandidateSet,
)

CONTRIB = Path(AETOS_STATIC_DIR).parent
DISCOVERY = CONTRIB / "discovery"
COMMAND = CONTRIB / "management" / "commands" / "aetos.py"


def _source(name):
    """
    One discovery module's source.

    Args:
        name (str): File name inside the discovery package.

    Returns:
        str: The file's text.

    """
    return (DISCOVERY / name).read_text(encoding="utf-8")


class TestTheEntryPoint(TestCase):
    """
    `questions.md` 4, answered.

    """

    def test_the_command_is_where_django_looks_for_it(self):
        """
        Django discovers management commands at
        `<app>/management/commands/<name>.py` and nowhere else. The file's
        *location* is the whole registration mechanism, so it is worth an
        assertion of its own.

        """
        self.assertTrue(COMMAND.is_file())
        self.assertTrue((CONTRIB / "management" / "__init__.py").is_file())
        self.assertTrue((CONTRIB / "management" / "commands" / "__init__.py").is_file())

    def test_it_needs_no_settings_entry_to_work(self):
        """
        The alternative route is Evennia's `EXTRA_LAUNCHER_COMMANDS`, which
        would make the command conditional on a game adding a line. This one is
        not: Aetos is already in `INSTALLED_APPS` -- it must be, or no template
        or static file loads -- and that is the only requirement.

        """
        source = COMMAND.read_text(encoding="utf-8")
        self.assertNotIn("EXTRA_LAUNCHER_COMMANDS = ", source)
        self.assertIn("already an installed app", source)

    def test_the_launcher_trap_is_written_down(self):
        """
        `run_custom_commands`'s docstring names `CUSTOM_EVENNIA_LAUNCHER_COMMANDS`
        while its code reads `EXTRA_LAUNCHER_COMMANDS`. Following the
        documentation gets you nothing, silently: the missing attribute is
        caught, the hook returns False, and the command falls through to Django,
        which reports an unrelated "unknown command".

        Not the route taken, and recorded so the next person does not spend an
        hour on it.

        """
        source = COMMAND.read_text(encoding="utf-8")
        self.assertIn("CUSTOM_EVENNIA_LAUNCHER_COMMANDS", source)
        self.assertIn("silently", source)

    def test_there_is_one_command_with_subcommands_under_it(self):
        """
        B.34 asks the documentation to expose exactly one command. Later stages
        add subcommands to this file rather than commands beside it -- D5's
        `setup` is the second.

        """
        source = COMMAND.read_text(encoding="utf-8")
        self.assertIn('SUBCOMMANDS = ("discover", "setup")', source)
        self.assertEqual(source.count("class Command"), 1)

    def test_running_it_with_no_subcommand_does_not_guess(self):
        """
        Defaulting to `discover` would make `evennia aetos` scan a live
        database because somebody pressed return early.

        """
        from evennia.contrib.base_systems.aetos_webclient.management.commands import (
            aetos as command_module,
        )

        command = command_module.Command()
        parser = command.create_parser("evennia", "aetos")
        parsed = parser.parse_args([])
        self.assertEqual(parsed.subcommand, "")

    def test_an_unknown_subcommand_is_an_error_rather_than_silence(self):
        from django.core.management.base import CommandError

        from evennia.contrib.base_systems.aetos_webclient.management.commands import (
            aetos as command_module,
        )

        with self.assertRaises(CommandError):
            command_module.Command().handle(subcommand="wat")


class TestTheStaticScanNeverRunsTheGame(TestCase):
    """
    The proof D0 asks for, stated as what the module may not contain.

    Importing the game's typeclass and calling `dir()` on it is the obvious way
    to make this scan better, and it is a version that cannot be made safe
    afterwards: importing runs module-level code, which can open a connection,
    take ten seconds, or raise on a game that is mid-edit.

    """

    def test_it_does_not_import_the_game(self):
        source = _source("static_scan.py")
        code = ast.parse(source)
        called = {
            node.func.id
            for node in ast.walk(code)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        for forbidden in ("eval", "exec", "compile", "__import__"):
            self.assertNotIn(forbidden, called, "static_scan calls %s" % forbidden)

    def test_it_does_not_reach_for_importlib(self):
        code = ast.parse(_source("static_scan.py"))
        imported = set()
        for node in ast.walk(code):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertNotIn("importlib", imported)

    def test_source_with_a_side_effect_is_read_without_the_side_effect(self):
        """
        The proof itself. This source would raise if executed and would delete a
        file if it got that far; parsing it finds the candidate and does neither.

        """
        source = (
            "import shutil\n"
            "shutil.rmtree('/')\n"
            "raise SystemExit('this module refuses to be imported')\n"
            "\n"
            "class Character:\n"
            "    def at_object_creation(self):\n"
            "        self.db.hp = 100\n"
        )
        found, _, _ = static_scan.scan_source(source, "hostile.py")
        self.assertEqual([c.expression for c in found], ["db.hp"])

    def test_a_file_that_does_not_parse_is_reported_rather_than_swallowed(self):
        """
        A scan that skipped the Character typeclass and printed "no candidates"
        would be read as "your game has nothing", which is a different and much
        worse message.

        """
        with self.assertRaises(SyntaxError):
            static_scan.scan_source("def broken(:\n", "broken.py")


class TestTheStaticScanFindsWhatGamesActuallyWrite(TestCase):
    """
    Both of Evennia's ways to set an attribute, and the receivers that mean the
    character.

    """

    def test_it_finds_a_plain_assignment(self):
        found, _, _ = static_scan.scan_source("self.db.hp = 100\n", "characters.py")
        self.assertEqual(found[0].expression, "db.hp")
        self.assertEqual(found[0].kind, "number")

    def test_the_scan_does_not_decide_confidence(self):
        """
        D3: confidence is decided once, from every scan, by the confidence
        engine. D0's scans each stamped their own guess and the merge kept the
        more optimistic one.

        """
        source = _source("static_scan.py")
        outside_actions = (
            source[: source.index("def _action_from")] + source[source.index("def scan_source") :]
        )
        self.assertNotIn("confidence=", outside_actions)

    def test_it_finds_the_attributes_add_form(self):
        found, _, _ = static_scan.scan_source('self.attributes.add("mana", 50)\n', "characters.py")
        self.assertEqual(found[0].expression, "db.mana")
        self.assertEqual(found[0].kind, "number")

    def test_a_boolean_is_not_reported_as_a_number(self):
        """
        `True` is an `int` in Python. Reporting a flag as a number is the kind of
        small wrongness that makes a generated block need checking line by line.

        """
        found, _, _ = static_scan.scan_source("self.db.is_ghost = True\n", "characters.py")
        self.assertEqual(found[0].kind, "boolean")

    def test_the_evidence_names_a_line_a_developer_can_go_and_look_at(self):
        found, _, _ = static_scan.scan_source("\n\nself.db.hp = 1\n", "typeclasses/characters.py")
        self.assertIn("typeclasses/characters.py:3", found[0].evidence)

    def test_it_ignores_a_receiver_that_is_probably_not_the_character(self):
        """
        `obj.db.x` in a command is usually the thing being acted on. A report
        full of a room's attributes labelled as the character's is worse than a
        shorter report.

        """
        self.assertEqual(static_scan.scan_source("obj.db.hp = 1\n", "cmd.py")[0], [])
        self.assertEqual(static_scan.scan_source("room.db.hp = 1\n", "cmd.py")[0], [])

    def test_it_ignores_a_computed_attribute_key(self):
        """
        `attributes.add(name, value)` in a loop is the case the static scan
        cannot see. Guessing at the variable's contents would produce candidates
        that do not exist.

        """
        self.assertEqual(
            static_scan.scan_source("self.attributes.add(name, 1)\n", "characters.py")[0], []
        )

    def test_it_does_not_claim_three_levels(self):
        """
        `self.db.stats.hp` is an attribute of an attribute. The grammar can say
        it; the scan cannot verify it from source, so it does not claim it.
        Under-reporting costs a line of typing and over-reporting costs an
        afternoon.

        """
        found, _, _ = static_scan.scan_source("self.db.stats.hp = 1\n", "c.py")
        self.assertEqual([c.expression for c in found], ["db.stats"])

    def test_a_broken_file_does_not_stop_the_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            typeclasses = Path(tmp) / "typeclasses"
            typeclasses.mkdir()
            (typeclasses / "characters.py").write_text("self.db.hp = 10\n", encoding="utf-8")
            (typeclasses / "broken.py").write_text("def nope(:\n", encoding="utf-8")

            found, _, problems = static_scan.scan_files(gamedir=tmp)

        self.assertEqual([c.expression for c in found], ["db.hp"])
        self.assertEqual(len(problems), 1)
        self.assertIn("broken.py", problems[0])

    def test_evidence_paths_read_the_same_on_every_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / "world" / "rules"
            world.mkdir(parents=True)
            (world / "combat.py").write_text("self.db.hp = 1\n", encoding="utf-8")
            found, _, _ = static_scan.scan_files(gamedir=tmp)
        self.assertTrue(found)
        self.assertNotIn("\\", found[0].evidence)


class TestTheScanStaysInsideTheGame(TestCase):
    """
    Not a defence against a hostile game author -- somebody who can edit the game
    directory can already run anything -- but against two ordinary accidents: a
    `world/` containing a vendored library, and a `world/` that is a symlink to
    somebody else's checkout.

    """

    def test_containment_is_checked_after_resolving_not_before(self):
        """
        `os.path.join(gamedir, "world")` looks contained no matter where `world`
        leads. Resolving first is the whole check.

        """
        self.assertIn("realpath", _source("roots.py"))

    def test_a_sibling_with_a_shared_prefix_is_not_inside(self):
        """
        `startswith` says `/game-backup` is inside `/game`. `commonpath` does
        not.

        """
        with tempfile.TemporaryDirectory() as tmp:
            game = os.path.join(tmp, "game")
            backup = os.path.join(tmp, "game-backup")
            os.makedirs(game)
            os.makedirs(backup)
            self.assertFalse(roots.is_inside(backup, game))
            self.assertTrue(roots.is_inside(os.path.join(game, "world"), game))

    def test_only_the_named_roots_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("typeclasses", "world", "commands", "server", "web"):
                directory = Path(tmp) / name
                directory.mkdir()
                (directory / "thing.py").write_text("self.db.x = 1\n", encoding="utf-8")

            files = roots.approved_files(gamedir=tmp)

        names = {os.path.basename(os.path.dirname(path)) for path in files}
        self.assertEqual(names, {"typeclasses", "world", "commands"})

    def test_settings_is_never_read(self):
        """
        It is the one file a scan would obviously want, and it stays out.
        Reading it would tell discovery what is already configured, which is the
        beginning of a tool that edits it.

        """
        self.assertNotIn("server", roots.APPROVED_ROOTS)
        self.assertNotIn("settings.py", _source("roots.py").split('"""', 2)[2])

    def test_generated_and_vendored_directories_are_skipped(self):
        for skipped in ("__pycache__", "node_modules", "migrations", ".git"):
            self.assertIn(skipped, roots.SKIP_DIRECTORIES)

    def test_the_walk_is_bounded(self):
        """
        A game's `world/` can contain a package tree. Two levels reaches
        `world/rules/combat.py` and stops before the scan becomes about the
        game's dependencies.

        """
        with tempfile.TemporaryDirectory() as tmp:
            deep = Path(tmp) / "world" / "a" / "b" / "c"
            deep.mkdir(parents=True)
            (deep / "buried.py").write_text("self.db.x = 1\n", encoding="utf-8")
            (Path(tmp) / "world" / "a" / "shallow.py").write_text("", encoding="utf-8")

            files = roots.approved_files(gamedir=tmp)

        self.assertTrue(any(f.endswith("shallow.py") for f in files))
        self.assertFalse(any(f.endswith("buried.py") for f in files))

    def test_the_file_list_is_stable_between_runs(self):
        """
        The report is something a developer reads twice and compares. Output
        that reorders for no reason costs more attention than the ordering
        saves.

        """
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / "world"
            world.mkdir()
            for name in ("c.py", "a.py", "b.py"):
                (world / name).write_text("", encoding="utf-8")
            first = roots.approved_files(gamedir=tmp)
            second = roots.approved_files(gamedir=tmp)
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))


class TestTheRuntimeScanOnlyReads(TestCase):
    """
    This runs against a live game's database, possibly a production one, from a
    command a developer is trying for the first time.

    """

    def test_it_does_not_write(self):
        source = _source("runtime_scan.py")
        for forbidden in (".save(", ".delete(", "attributes.add(", "create_object"):
            self.assertNotIn(forbidden, source, "runtime_scan uses %s" % forbidden)

    def test_it_does_not_create_a_character_to_inspect(self):
        """
        The tempting fix for "no characters exist yet". It would leave an object
        in the game.

        """
        self.assertNotIn("create", _source("runtime_scan.py").split('"""', 2)[2])

    def test_the_sample_is_bounded(self):
        """
        A game with fifty thousand characters is not fifty thousand times more
        informative: attribute names repeat, and the names are what discovery is
        after.

        """
        self.assertIn("[:limit]", _source("runtime_scan.py"))
        self.assertLessEqual(runtime_scan.SAMPLE_SIZE, 100)


class _FakeAttribute:
    """A stand-in for an Evennia Attribute row."""

    def __init__(self, key, value, category=None):
        self.key = key
        self.value = value
        self.category = category


class _FakeCharacter:
    """A stand-in for a Character, with only what the scan reads."""

    def __init__(self, identifier, attributes):
        self.id = identifier
        self.attributes = type("Handler", (), {"all": lambda _self: attributes})()


class TestTheRuntimeScanReadsWhatIsThere(TestCase):
    """
    Proved against stand-ins rather than the database.

    The scan reads exactly two things off a character -- `id` and
    `attributes.all()` -- so a fake that provides those exercises every decision
    in it, and the test runs without a database.

    """

    def test_it_finds_an_attribute_and_says_how_many_carried_it(self):
        characters = [
            _FakeCharacter(1, [_FakeAttribute("hp", 50)]),
            _FakeCharacter(2, [_FakeAttribute("hp", 40), _FakeAttribute("gold", 3)]),
        ]
        found, problems = runtime_scan.scan_characters(characters)
        by_name = {c.name: c for c in found}
        self.assertEqual(by_name["hp"].kind, "number")
        self.assertIn("on 2 of 2 characters", by_name["hp"].evidence)
        self.assertIn("on 1 of 2 characters", by_name["gold"].evidence)
        self.assertEqual(problems, [])

    def test_a_flag_is_not_reported_as_a_number(self):
        found, _ = runtime_scan.scan_characters(
            [_FakeCharacter(1, [_FakeAttribute("dead", False)])]
        )
        self.assertEqual(found[0].kind, "boolean")

    def test_a_key_the_grammar_cannot_express_is_skipped(self):
        """
        Evennia allows attribute keys that are not identifiers. Suggesting one
        would produce a line that does not work when pasted.

        """
        character = _FakeCharacter(1, [_FakeAttribute("not an identifier", 1)])
        found, _ = runtime_scan.scan_characters([character])
        self.assertEqual(found, [])

    def test_a_categorised_attribute_is_skipped(self):
        character = _FakeCharacter(1, [_FakeAttribute("hp", 1, category="combat")])
        found, _ = runtime_scan.scan_characters([character])
        self.assertEqual(found, [])

    def test_no_characters_says_so_rather_than_reporting_nothing(self):
        """
        "No candidates" on a new game reads as "your game has nothing". The
        reason is on the same screen instead.

        """
        found, problems = runtime_scan.scan_characters([])
        self.assertEqual(found, [])
        self.assertTrue(any("no characters exist yet" in p for p in problems))


class TestMergingAndPairing(TestCase):
    """
    The part of discovery with a decision in it.

    """

    def _pair(self):
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "characters.py:1", "number"))
        found.add(Candidate("db.hp_max", "hp_max", "static", "characters.py:2", "number"))
        found.pair_maximums()
        return found

    def test_the_same_attribute_from_both_scans_is_one_candidate(self):
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "characters.py:1", "number"))
        found.add(Candidate("db.hp", "hp", "runtime", "on 3 of 3", "unknown"))
        self.assertEqual(len(found), 1)
        merged = found.candidates["db.hp"]
        self.assertEqual(merged.origin, "static and runtime")
        self.assertIn("characters.py:1", merged.evidence)
        self.assertIn("on 3 of 3", merged.evidence)

    def test_the_merge_keeps_the_stronger_claim_whichever_order_it_arrived_in(self):
        """
        Taking the last write would make the result depend on scan order, which
        is not something a developer should have to know about.

        """
        forwards = CandidateSet()
        forwards.add(Candidate("db.hp", "hp", "static", "a", "number"))
        forwards.add(Candidate("db.hp", "hp", "runtime", "b", "unknown"))

        backwards = CandidateSet()
        backwards.add(Candidate("db.hp", "hp", "runtime", "b", "unknown"))
        backwards.add(Candidate("db.hp", "hp", "static", "a", "number"))

        self.assertEqual(forwards.candidates["db.hp"].kind, "number")
        self.assertEqual(backwards.candidates["db.hp"].kind, "number")

    def test_a_maximum_is_paired_with_the_value_it_bounds(self):
        found = self._pair()
        self.assertEqual(found.candidates["db.hp"].maximum, "db.hp_max")
        self.assertEqual(found.candidates["db.hp"].pairing, "name")

    def test_a_paired_maximum_is_not_also_listed_on_its_own(self):
        """
        Or every health bar appears in the report twice and the developer
        deletes one at random.

        """
        names = [c.name for c in self._pair().suggestions()]
        self.assertEqual(names, ["hp"])

    def test_the_longest_suffix_wins(self):
        """
        `hp_maximum` matched as `hp_max` plus a stray `imum` would pair `hp`
        with an attribute that does not exist.

        """
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "a"))
        found.add(Candidate("db.hp_maximum", "hp_maximum", "static", "b"))
        found.pair_maximums()
        self.assertEqual(found.candidates["db.hp"].maximum, "db.hp_maximum")

    def test_pairing_works_across_the_two_scans(self):
        """
        `hp` written in the typeclass and `hp_max` set from a command is an
        ordinary way for a game to end up, which is why pairing runs after both
        scans rather than during either.

        """
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "characters.py:1"))
        found.add(Candidate("db.hp_max", "hp_max", "runtime", "on 2 of 2"))
        self.assertEqual(found.pair_maximums(), 1)

    def test_a_pair_is_not_claimed_from_a_name_list(self):
        """
        `looks_like_a_resource` is true when there is a paired maximum and never
        because the attribute is called `hp`. A name list is a guess about
        somebody else's game and is wrong in every language but English.

        """
        source = (DISCOVERY / "candidates.py").read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]
        for name in ("mana", "stamina", "vitality"):
            self.assertNotIn('"%s"' % name, body)

    def test_bookkeeping_is_filtered_but_reachable(self):
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "runtime", "a"))
        found.add(Candidate("db.creator_ip", "creator_ip", "runtime", "b"))
        found.add(Candidate("db._sessid", "_sessid", "runtime", "c"))

        self.assertEqual([c.name for c in found.suggestions()], ["hp"])
        self.assertEqual(len(found.suggestions(include_all=True)), 3)

    def test_a_candidate_is_a_record_and_cannot_be_edited_in_place(self):
        """
        Frozen, so anything deriving a new observation does so visibly rather
        than letting one scan quietly edit another's findings.

        """
        candidate = Candidate("db.hp", "hp", "static", "a")
        with self.assertRaises(Exception):
            candidate.kind = "number"


class TestTheReportIsPastable(TestCase):
    """
    Discovery's whole value is that the developer does not have to look anything
    up, so what is printed has to be correct if pasted unchanged.

    """

    def _report(self):
        """
        A pair written in source *and* carried by live characters.

        D0's version had the pair in source only. Under B.28 that is LOW --
        "name appears only in source" -- and LOW is printed commented out, so it
        would no longer be in the evaluated block. The live readings are what
        make it selectable, which is the point of the runtime pass.

        """
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "typeclasses/characters.py:12", "number"))
        found.add(
            Candidate("db.hp_max", "hp_max", "static", "typeclasses/characters.py:13", "number")
        )
        live = tuple((who, 80) for who in range(1, 5))
        ceiling = tuple((who, 100) for who in range(1, 5))
        found.add(
            Candidate("db.hp", "hp", "runtime", "on 4 of 4", "number", observed=live, count=4)
        )
        found.add(
            Candidate(
                "db.hp_max", "hp_max", "runtime", "on 4 of 4", "number", observed=ceiling, count=4
            )
        )
        found.add(
            Candidate(
                "db.gold", "gold", "runtime", "on 4 of 4 characters sampled", "number", count=4
            )
        )
        found.pair_maximums()
        found.assess(sampled=4)
        return report.render(found)

    def test_the_output_is_valid_python(self):
        ast.parse(self._report())

    def test_it_evaluates_to_the_bindings_it_claims(self):
        """
        Parsed rather than executed, and read with `literal_eval`: a test that
        `exec`s generated output would pass on output that also did something
        else.

        """
        tree = ast.parse(self._report())
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        self.assertEqual(assignment.targets[0].id, "AETOS_BINDINGS")

        bindings = ast.literal_eval(assignment.value)
        self.assertEqual(
            bindings["resources"]["hp"],
            {"label": "Hp", "value": "db.hp", "maximum": "db.hp_max"},
        )
        self.assertEqual(bindings["resources"]["gold"], {"label": "Gold", "value": "db.gold"})

    def test_every_expression_in_it_passes_the_grammar(self):
        tree = ast.parse(self._report())
        assignment = next(node for node in tree.body if isinstance(node, ast.Assign))
        bindings = ast.literal_eval(assignment.value)
        for entry in bindings["resources"].values():
            self.assertTrue(schema.is_valid_expression(entry["value"]))
            if "maximum" in entry:
                self.assertTrue(schema.is_valid_expression(entry["maximum"]))

    def test_the_evidence_travels_with_the_suggestion(self):
        """
        The first thing anybody does with a generated settings block is check one
        line of it, and a suggestion with no provenance cannot be checked.

        """
        text = self._report()
        self.assertIn("typeclasses/characters.py:12", text)
        self.assertIn("on 4 of 4 characters sampled", text)

    def test_the_guessed_field_is_named_once(self):
        """
        The label is the only field discovery invents. Saying so on every line
        would be noise, and noise is what gets pasted without reading.

        """
        text = self._report()
        self.assertEqual(text.count("is a guess"), 1)

    def test_nothing_found_explains_itself(self):
        text = report.render(CandidateSet())
        self.assertIn("No candidates found", text)
        self.assertIn("AETOS_PROVIDERS", text)
        self.assertNotIn("AETOS_BINDINGS = {", text)

    def test_problems_are_shown_beside_the_result(self):
        """
        "I got fewer results than I expected" needs its answer on the same
        screen.

        """
        text = report.render(CandidateSet(), problems=["world/broken.py could not be parsed"])
        self.assertIn("world/broken.py", text)

    def test_it_never_writes_anything(self):
        """
        A tool that edits a developer's settings file has to be trusted before it
        is understood, which is the wrong way round for the first thing somebody
        runs.

        """
        for name in ("report.py", "static_scan.py", "runtime_scan.py", "roots.py"):
            source = _source(name)
            self.assertNotIn('"w"', source, "%s opens a file for writing" % name)
            self.assertNotIn("'w'", source, "%s opens a file for writing" % name)


class TestTheBoundary(TestCase):
    """
    D0's gate: no browser dependency, no player protocol surface.

    The easiest version of this feature to build by accident is one where a
    player can ask the server to enumerate its own internals, so the import
    graph is asserted rather than assumed.

    """

    FORBIDDEN = (
        "protocol",
        "manifest",
        "inputfuncs",
        "ui_manifest",
        "media",
        "csp",
        "contrast",
        "map_layout",
    )

    def test_discovery_does_not_import_the_client(self):
        for path in sorted(DISCOVERY.glob("*.py")):
            code = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(code):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                for module in modules:
                    tail = module.rsplit(".", 1)[-1]
                    self.assertNotIn(
                        tail,
                        self.FORBIDDEN,
                        "%s imports the client module %s" % (path.name, module),
                    )

    def test_no_inputfunc_exposes_discovery(self):
        """
        An inputfunc is the player-facing surface. Discovery must have none.

        """
        source = (CONTRIB / "inputfuncs.py").read_text(encoding="utf-8")
        self.assertNotIn("discovery", source)

    def test_discovery_is_not_in_the_manifest(self):
        """
        The manifest is what the client is told about the game. A `discovery`
        key would be a feature flag for something with no client half at all.

        """
        source = (CONTRIB / "manifest.py").read_text(encoding="utf-8")
        self.assertNotIn("discovery", source)

    def test_the_command_defers_its_imports(self):
        """
        Django imports every management-command module it finds, in every
        process, to build its own help. Importing the scans at module level
        would put a source walk and a database query behind `evennia --help`.

        """
        source = COMMAND.read_text(encoding="utf-8")
        header = source[: source.index("class Command")]
        self.assertNotIn("discovery", header.split('"""', 2)[2])


class TestTheModelSaysWhatItIs(TestCase):
    """
    D0 is a spike, so the writing is part of the deliverable: the next person
    builds D1 against these decisions and needs the reasoning, not the list.

    """

    def test_the_two_scans_say_why_neither_is_enough_alone(self):
        self.assertIn("brand-new game", _source("__init__.py"))
        self.assertIn("database rows", _source("runtime_scan.py"))

    def test_confidence_is_words_rather_than_a_number(self):
        """
        A number invites arithmetic on evidence that does not support it.

        D0 had two words, `likely` and `possible`. D3 adopts Addendum B.28's
        three, because B.28 attaches a rule to the lowest -- not selected by
        default -- and two levels cannot say "shown but not selected".

        """
        self.assertEqual(candidates_module.CONFIDENCE, ("HIGH", "MEDIUM", "LOW"))
