"""
D6 -- hardening, documentation and validation.

The D-track's last stage, and the one with the least new code in it. What is
here is the set of tests that say the whole thing is a supported developer API
rather than five stages that each passed their own gate:

- **Fresh Evennia (B.64)**, the critical genre-neutrality test. Point discovery
  at a game with nothing in it and it must find nothing. A tool that
  manufactures a health bar for a game with no health has failed in exactly the
  way this project exists to avoid.
- **A game that is not fantasy (B.65)**, end to end this time: a ship with
  `hull_integrity`, `oxygen` and `reactor_output` gets the same treatment
  `hp` does, and no list of stat names is consulted to do it.
- **A large project (B.63)**: a tree with more files than the ceiling allows
  finishes, stays bounded, and says what it left out.
- **Error messages (B.11)**: `AETOS_BINDINGS` is the setting for somebody who
  did not want to write Python, so an error that quotes a regular expression is
  an error that sends them to find somebody who does.
- **Generated code (B.43)**: what the wizard writes has to survive being pasted
  into a project whose CI runs `black`.
- **The docs cannot drift from the commands.** D6 found the in-client help
  showing the wizard under the wrong command name, which is the kind of thing
  only a test notices after the second time.

"""

import ast
import os
import re
import tempfile
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR
from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.discovery import (
    generate,
    report,
    roots,
    runtime_scan,
    static_scan,
    structure,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    CandidateSet,
)

CONTRIB = Path(AETOS_STATIC_DIR).parent
COMMAND = CONTRIB / "management" / "commands" / "aetos.py"
HELP = Path(AETOS_STATIC_DIR) / "aetos" / "js" / "help.js"


def _game(files):
    """
    A throwaway game directory.

    Args:
        files (dict): Relative path -> contents.

    Returns:
        str: The directory.

    """
    directory = tempfile.mkdtemp()
    for relative, text in files.items():
        path = Path(directory) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return directory


def _discover(gamedir, characters=()):
    """
    Everything `evennia aetos discover` would find, without the command.

    Args:
        gamedir (str): The game directory.
        characters (iterable, optional): Characters for the runtime pass.

    Returns:
        tuple: `(CandidateSet, problems)`.

    """
    found = CandidateSet()
    candidates, actions, problems = static_scan.scan_files(gamedir)
    for candidate in candidates:
        found.add(candidate)
    for action in actions:
        found.add_action(action)

    characters = list(characters)
    if characters:
        more, issues = runtime_scan.scan_characters(characters)
        for candidate in more:
            found.add(candidate)
        problems.extend(issues)
        described = structure.inspect(characters)
        for candidate in described["candidates"]:
            found.add(candidate)
        problems.extend(described["problems"])

    found.pair_maximums()
    found.assess(sampled=len(characters))
    return found, problems


# ------------------------------------------------------------------- B.64


class TestFreshEvennia(TestCase):
    """
    The test that matters most. A pristine game must yield nothing, while the
    zero-configuration integration it already has keeps working.

    """

    def setUp(self):
        from evennia.utils import create

        self.character = create.create_object(
            "evennia.objects.objects.DefaultCharacter", key="Pristine"
        )
        self.addCleanup(self.character.delete)

    def test_a_game_with_nothing_in_it_yields_nothing(self):
        gamedir = _game(
            {"typeclasses/characters.py": "class Character(DefaultCharacter):\n    pass\n"}
        )
        found, _ = _discover(gamedir, [self.character])
        for slot in schema.BINDING_SLOTS:
            self.assertEqual(found.by_slot(slot), [], slot)

    def test_and_the_report_says_so_in_words(self):
        gamedir = _game({"world/empty.py": "x = 1\n"})
        found, problems = _discover(gamedir)
        text = report.render(found, problems)
        self.assertIn("No candidates found", text)
        self.assertNotIn("AETOS_BINDINGS = {", text)

    def test_the_zero_configuration_integration_is_untouched(self):
        """
        Discovery adds nothing to what a stock game already shows: the entity,
        inventory, map and action providers keep working with no bindings at
        all. Asserted here because "found nothing" and "broke everything" look
        the same from inside a discovery test.

        """
        from evennia.contrib.base_systems.aetos_webclient.providers import get_providers

        providers = get_providers()
        for slot in ("entities", "inventory", "map", "actions"):
            self.assertIsNotNone(providers.get(slot), slot)


# ------------------------------------------------------------------- B.65


class TestAGameThatIsNotFantasy(TestCase):
    """
    B.65, end to end. The scan reads a ship's source and the report offers its
    bars, with no fantasy vocabulary anywhere in the path.

    """

    SOURCE = (
        "class Ship(DefaultCharacter):\n"
        "    def at_object_creation(self):\n"
        "        self.db.hull_integrity = 800\n"
        "        self.db.hull_capacity = 1000\n"
        "        self.db.oxygen = 40\n"
        "        self.db.oxygen_capacity = 100\n"
        "        self.db.reactor_output = 12\n"
        "        self.db.reactor_capacity = 20\n"
    )

    def test_every_pair_is_found_and_offered(self):
        gamedir = _game({"typeclasses/ships.py": self.SOURCE})
        found, problems = _discover(gamedir)
        for value, ceiling in (
            ("hull_integrity", "hull_capacity"),
            ("oxygen", "oxygen_capacity"),
            ("reactor_output", "reactor_capacity"),
        ):
            candidate = found.candidates["db.%s" % value]
            self.assertEqual(candidate.maximum, "db.%s" % ceiling, value)

    def test_nothing_in_the_path_consults_a_list_of_stat_names(self):
        """
        The pairing rule is structural. A name list is a guess about somebody
        else's game and is wrong in every language but English.

        """
        for name in ("discovery/candidates.py", "discovery/confidence.py"):
            body = (CONTRIB / name).read_text(encoding="utf-8").split('"""', 2)[2]
            for fantasy in ('"mana"', '"stamina"', '"vitality"', '"health"', '"hp"'):
                self.assertNotIn(fantasy, body, "%s mentions %s" % (name, fantasy))


# ------------------------------------------------------------------- B.63


class TestALargeProject(TestCase):
    """A tree bigger than the ceilings, which must finish and say what it left."""

    def test_it_stops_at_the_ceiling_and_names_what_was_missed(self):
        files = {
            "world/pack%03d/mod%02d.py" % (n // 20, n % 20): "x = %d\n" % n for n in range(300)
        }
        gamedir = _game(files)
        paths, problems = roots.select_files(gamedir, max_files=50)
        self.assertEqual(len(paths), 50)
        self.assertIn("were not scanned", " ".join(problems))

    def test_a_deep_tree_is_not_followed_forever(self):
        deep = "world/" + "/".join("level%d" % n for n in range(8)) + "/deep.py"
        gamedir = _game({deep: "self.db.buried = 1\n", "world/top.py": "self.db.seen = 1\n"})
        found, _ = _discover(gamedir)
        self.assertIn("db.seen", found.candidates)
        self.assertNotIn("db.buried", found.candidates)

    def test_the_file_order_is_stable_between_runs(self):
        gamedir = _game(
            {"world/b.py": "x = 1\n", "world/a.py": "y = 2\n", "commands/c.py": "z = 3\n"}
        )
        first, _ = roots.select_files(gamedir)
        second, _ = roots.select_files(gamedir)
        self.assertEqual(first, second)


# ------------------------------------------------------------------- B.11


class TestErrorsAreWrittenForABeginner(TestCase):
    """
    `AETOS_BINDINGS` is the setting for somebody who did not want to write
    Python. An error that quotes a regular expression is an error that tells
    them to go and find somebody who does.

    """

    REFUSED = ("db.hp()", "db.stats[0]", "db.__class__", "hp", "db.hp + 1", "")

    def test_every_refusal_is_a_sentence_with_no_machinery_in_it(self):
        for expression in self.REFUSED:
            message = schema.explain_expression(expression)
            self.assertGreater(len(message.split()), 4, expression)
            for machinery in ("^db", "regex", "regular expression", "Traceback", "\\w", "[A-Za-z"):
                self.assertNotIn(machinery, message, "%s -> %s" % (expression, message))

    def test_a_refusal_says_what_to_do_instead(self):
        for expression, expected in (
            ("db.hp()", "provider"),
            ("db.stats[0]", "db.stats.hp"),
            ("hp", "db."),
        ):
            self.assertIn(expected, schema.explain_expression(expression), expression)

    def test_selection_errors_name_the_fix(self):
        with self.assertRaises(runtime_scan.SelectionError) as caught:
            runtime_scan.select_characters(character="Nobody Called This")
        self.assertIn("Nobody Called This", str(caught.exception))

    def test_a_scan_root_error_explains_itself(self):
        message = str(
            roots.ScanRootError(
                "world resolves outside the game directory. Discovery reads the game's "
                "own source and nothing else; if this is deliberate, copy the files in."
            )
        )
        self.assertIn("copy the files in", message)


# ------------------------------------------------------------------- B.43


class TestGeneratedCodeSurvivesAProjectsFormatter(TestCase):
    """
    Generated `suggested_bindings.py` is pasted into a project whose CI runs
    `black`. It cannot be checked with `black` here -- the contrib depends on
    Evennia and the standard library only -- so the properties `black` would
    enforce are asserted directly.

    """

    ACCEPTED = {
        "resources": {"hp": {"label": "Hp", "value": "db.hp", "maximum": "db.hp_max"}},
        "actions": {"attack": {"label": "Attack", "command": "attack {target}"}},
    }

    def setUp(self):
        self.source = generate.bindings_source(self.ACCEPTED)

    def test_it_parses(self):
        ast.parse(self.source)

    def test_double_quotes_four_space_indents_and_trailing_commas(self):
        for line in self.source.splitlines():
            if line.strip().startswith('"') and ":" in line and line.rstrip().endswith(","):
                self.assertTrue(line.rstrip().endswith(","), line)
            indent = len(line) - len(line.lstrip(" "))
            self.assertEqual(indent % 4, 0, line)
        self.assertNotIn("'", self.source)

    def test_no_line_is_longer_than_the_project_allows(self):
        for line in self.source.splitlines():
            self.assertLessEqual(len(line), 99, line)

    def test_it_ends_with_exactly_one_newline(self):
        self.assertTrue(self.source.endswith("\n"))
        self.assertFalse(self.source.endswith("\n\n"))


# ------------------------------------------------------- documentation gate


class TestTheDocumentationCannotDriftFromTheCommands(TestCase):
    """
    D6 found the in-client help showing the wizard's screen under
    `evennia aetos discover`, which is the one-shot report. The walkthrough is
    `evennia aetos setup`. Documentation that names a command is documentation
    that can go stale, so it is checked rather than trusted.

    """

    def _subcommands(self):
        from evennia.contrib.base_systems.aetos_webclient.management.commands import (
            aetos,
        )

        return aetos.SUBCOMMANDS

    def test_every_aetos_command_named_in_the_readme_exists(self):
        text = (CONTRIB / "README.md").read_text(encoding="utf-8")
        for named in set(re.findall(r"evennia aetos ([a-z]+)", text)):
            self.assertIn(named, self._subcommands(), named)

    def test_every_aetos_command_named_in_the_in_client_help_exists(self):
        text = HELP.read_text(encoding="utf-8")
        for named in set(re.findall(r"evennia aetos ([a-z]+)", text)):
            self.assertIn(named, self._subcommands(), named)

    def test_the_help_shows_the_walkthrough_under_the_command_that_walks(self):
        text = HELP.read_text(encoding="utf-8")
        walkthrough = text[text.index("Possible resource found") - 400 : text.index("[Q]uit")]
        self.assertIn("evennia aetos setup", walkthrough)

    def test_the_readme_teaches_the_levels_in_the_order_the_addendum_asks(self):
        """
        B.50: zero config -> discovery -> bindings -> a provider only when
        needed. The provider example used to be the first thing offered.

        """
        text = (CONTRIB / "README.md").read_text(encoding="utf-8")
        teaching = text.index("## Teaching Aetos about your game")
        bindings = text.index("### Bindings", teaching)
        providers = text.index("### Providers", teaching)
        self.assertLess(bindings, providers)
        self.assertIn("advanced", text[providers : providers + 200].lower())

    def test_the_readme_separates_runtime_from_development_tooling(self):
        """B.51's replacement wording, which distinguishes the two."""
        text = (CONTRIB / "README.md").read_text(encoding="utf-8")
        self.assertIn("during gameplay", text)
        self.assertIn("during development", text)


# ------------------------------------------------------------------- B.52


class TestDiscoveryChangesNoPlayerPrivacy(TestCase):
    """
    B.52. Discovery analyses developer-owned implementation data. It creates no
    player tracking, no server-side profile, and no storage of any kind.

    """

    def test_it_adds_no_models_and_no_migrations(self):
        self.assertEqual(list((CONTRIB / "discovery").glob("models.py")), [])
        self.assertEqual(list((CONTRIB / "discovery").glob("migrations")), [])

    WRITERS = ("save", "delete", "add", "create", "create_object", "update", "set")

    def test_nothing_in_it_writes_to_the_database(self):
        """
        Asked of the syntax tree, not of the text. `static_scan` documents the
        `attributes.add("hp", 100)` form it recognises, and a substring search
        cannot tell a sentence about a call from a call.

        """
        for path in sorted((CONTRIB / "discovery").glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called = getattr(node.func, "attr", None)
                if called in self.WRITERS:
                    receiver = getattr(node.func.value, "id", "") or getattr(
                        node.func.value, "attr", ""
                    )
                    # `set()` and `dict.update()` on local data are not writes to
                    # anything; a write goes through a model, a handler or a
                    # queryset, which is what these receivers name.
                    self.assertNotIn(
                        receiver,
                        ("objects", "attributes", "db", "character", "obj"),
                        "%s line %d calls %s.%s()" % (path.name, node.lineno, receiver, called),
                    )

    def test_the_only_thing_it_writes_is_the_generated_directory(self):
        opens = 0
        for path in sorted((CONTRIB / "discovery").glob("*.py")):
            body = path.read_text(encoding="utf-8")
            opens += len(re.findall(r'open\([^)]*"w"', body))
        self.assertEqual(opens, 1, "something besides generate.py opens a file for writing")

    def test_generated_files_land_only_under_the_game_directory(self):
        gamedir = tempfile.mkdtemp()
        generate.write(gamedir, "report")
        written = generate.output_directory(gamedir)
        self.assertTrue(os.path.realpath(written).startswith(os.path.realpath(gamedir)))
