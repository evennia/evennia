"""
D4 -- static AST discovery.

D0 proved a game's source could be read without importing it, and built the
allowlist, the depth limit and the symlink containment that keep the walk inside
the game. D4 is the rest of Addendum B's static pass: the patterns B.23 lists,
the ceilings B.53 and B.56 require, and the proof B.60 asks for that hostile
source is parsed and never run.

WHY STATIC AT ALL, when D3 can read live characters: a brand-new game has source
and no characters, and a game mid-edit has source that will not import. The two
passes fail in opposite conditions, which is why neither is offered alone.

The hostile fixtures here are the substance of the module, not decoration.
Discovery reads files a developer may have downloaded from anywhere, so
`os.system(...)`, `open(...).write(...)` and a module-level `raise` are parsed in
tests that fail if any of them takes effect.

"""

import ast
import os
import tempfile
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR
from evennia.contrib.base_systems.aetos_webclient.discovery import (
    confidence,
    report,
    roots,
    static_scan,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    CandidateSet,
)

DISCOVERY = Path(AETOS_STATIC_DIR).parent / "discovery"


def _scan(source, label="typeclasses/characters.py"):
    """
    Scan one piece of source.

    Args:
        source (str): Python source text.
        label (str, optional): How evidence names it.

    Returns:
        tuple: `(candidates by name, actions by key, problems)`.

    """
    found, actions, problems = static_scan.scan_source(source, label)
    return (
        {candidate.name: candidate for candidate in found},
        {action.key: action for action in actions},
        problems,
    )


class _Game:
    """A throwaway game directory with files in it."""

    def __init__(self, files):
        self.directory = tempfile.mkdtemp()
        for relative, text in files.items():
            path = Path(self.directory) / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def files(self, **kwargs):
        """
        The files discovery would read here.

        Args:
            **kwargs: Passed to `select_files`.

        Returns:
            tuple: `(paths, problems)`.

        """
        return roots.select_files(self.directory, **kwargs)

    def names(self, **kwargs):
        """
        Just the file names, relative and with forward slashes.

        Args:
            **kwargs: Passed to `select_files`.

        Returns:
            list: Relative paths.

        """
        paths, _ = self.files(**kwargs)
        return sorted(os.path.relpath(p, self.directory).replace(os.sep, "/") for p in paths)


# ------------------------------------------------------------------ B.23


class TestTheDeclarationFormsGamesActuallyUse(TestCase):
    """
    B.23's patterns. D0 read two of them -- `self.db.x = 1` and
    `attributes.add("x", 1)`. These are the rest.

    """

    def test_an_attribute_property_is_a_declaration(self):
        candidates, _, _ = _scan(
            "class Character(DefaultCharacter):\n    hp = AttributeProperty(100)\n"
        )
        self.assertIn("hp", candidates)
        self.assertEqual(candidates["hp"].kind, "number")
        self.assertEqual(candidates["hp"].origin, "typeclass")
        self.assertIn("AttributeProperty", candidates["hp"].evidence)

    def test_an_attribute_property_with_no_default_says_unknown(self):
        candidates, _, _ = _scan("class C(X):\n    mood = AttributeProperty()\n")
        self.assertEqual(candidates["mood"].kind, "unknown")

    def test_a_categorised_attribute_property_is_reported_not_suggested(self):
        """The grammar cannot reach a category, so suggesting it would not work."""
        candidates, _, problems = _scan(
            'class C(X):\n    rank = AttributeProperty(0, category="factions")\n'
        )
        self.assertNotIn("rank", candidates)
        self.assertIn("rank", " ".join(problems))
        self.assertIn("category", " ".join(problems))

    def test_a_read_is_weaker_evidence_than_an_assignment(self):
        """
        B.23 lists `character.db.mana` -- a read -- as a pattern of interest. It
        says the attribute is expected to exist, but not what it holds.

        """
        candidates, _, _ = _scan("def f(character):\n    return character.db.mana > 0\n")
        self.assertIn("mana", candidates)
        self.assertEqual(candidates["mana"].kind, "unknown")
        self.assertIn("read", candidates["mana"].evidence)

    def test_an_assignment_is_not_also_counted_as_a_read(self):
        candidates, _, _ = _scan("def f(caller):\n    caller.db.hp = 5\n")
        self.assertEqual(candidates["hp"].evidence.count(";"), 0)
        self.assertNotIn("read", candidates["hp"].evidence)

    def test_a_read_on_something_that_is_not_the_character_is_ignored(self):
        candidates, _, _ = _scan("def f(obj):\n    return obj.db.value\n")
        self.assertEqual(candidates, {})


class TestCommandsFoundInSource(TestCase):
    """
    B.22 and B.23: `class CmdAttack(Command): key = "attack"`. D3 reads commands
    off a live character's command sets; this finds them in a game that has no
    characters yet.

    """

    SOURCE = (
        "class CmdAttack(Command):\n"
        '    """\n'
        "    Hit something.\n\n"
        "    Usage:\n"
        "      attack <target>\n\n"
        '    """\n'
        '    key = "attack"\n'
        '    locks = "cmd:all()"\n'
    )

    def test_a_command_class_becomes_an_action(self):
        _, actions, _ = _scan(self.SOURCE, "commands/combat.py")
        self.assertIn("attack", actions)
        self.assertEqual(actions["attack"].command, "attack {target}")
        self.assertIn("commands/combat.py", actions["attack"].evidence)

    def test_it_is_low_because_source_is_all_there_is(self):
        """
        B.28: a name that appears only in source is LOW. Nothing here says the
        command is actually in a character's command set.

        """
        _, actions, _ = _scan(self.SOURCE, "commands/combat.py")
        self.assertEqual(actions["attack"].confidence, confidence.LOW)

    def test_a_staff_locked_command_is_not_a_player_action(self):
        source = self.SOURCE.replace('locks = "cmd:all()"', 'locks = "cmd:perm(Builder)"')
        _, actions, problems = _scan(source, "commands/build.py")
        self.assertEqual(actions, {})

    def test_a_class_with_no_key_is_not_a_command_worth_offering(self):
        _, actions, _ = _scan("class CmdBase(Command):\n    pass\n", "commands/base.py")
        self.assertEqual(actions, {})

    def test_a_class_that_is_not_a_command_is_ignored(self):
        _, actions, _ = _scan('class Character(DefaultCharacter):\n    key = "bob"\n')
        self.assertEqual(actions, {})

    def test_a_merged_action_drops_the_caveat_the_other_half_disproves(self):
        """
        Found by running the wizard against the lab: `setres` was presented as
        "not seen in a live command set" directly under evidence that it was in
        one. A reason that contradicts the evidence beside it costs the report
        its credibility.

        """
        from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
            SOURCE_ONLY_REASON,
            ActionCandidate,
        )

        found = CandidateSet()
        found.add_action(
            ActionCandidate(
                "setres",
                "setres {target}",
                "world/demo_cmds.py:14",
                confidence.LOW,
                reasons=("declared in the game's source", SOURCE_ONLY_REASON),
            )
        )
        found.add_action(
            ActionCandidate(
                "setres",
                "setres {target}",
                "setres in DefaultCharacter",
                confidence.LOW,
                reasons=("a command the game added, not one of Evennia's own",),
            )
        )
        merged = found.actions["setres"]
        self.assertNotIn(SOURCE_ONLY_REASON, merged.reasons)
        self.assertIn("DefaultCharacter", merged.evidence)

    def test_the_caveat_survives_when_source_is_all_there_is(self):
        from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
            SOURCE_ONLY_REASON,
        )

        _, actions, _ = _scan(self.SOURCE, "commands/combat.py")
        self.assertIn(SOURCE_ONLY_REASON, actions["attack"].reasons)

    def test_a_runtime_action_outranks_the_same_one_found_in_source(self):
        """
        The live command set is the stronger evidence, and the merge must not
        depend on which scan ran first.

        """
        from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
            ActionCandidate,
        )

        static = ActionCandidate(
            "attack", "attack {target}", "commands/combat.py:1", confidence.LOW
        )
        live = ActionCandidate(
            "attack", "attack {target}", "attack in CharacterCmdSet", confidence.MEDIUM
        )
        for order in ((static, live), (live, static)):
            found = CandidateSet()
            for action in order:
                found.add_action(action)
            merged = found.actions["attack"]
            self.assertEqual(merged.confidence, confidence.MEDIUM)
            self.assertIn("commands/combat.py:1", merged.evidence)
            self.assertIn("CharacterCmdSet", merged.evidence)


class TestValuesBehindAHandler(TestCase):
    """
    B.66's complex game: `character.stats.get("health").current` must not
    generate an unsafe binding. D3 sees this on a loaded class; D4 sees it in
    source, which is where a game with no characters shows it.

    """

    def test_a_handler_call_recommends_a_provider(self):
        _, _, problems = _scan(
            'def f(character):\n    return character.stats.get("health").current\n',
            "world/rules.py",
        )
        note = " ".join(problems)
        self.assertIn("stats", note)
        self.assertIn("AETOS_PROVIDERS", note)

    def test_it_generates_no_binding_for_it(self):
        candidates, _, _ = _scan('def f(character):\n    return character.stats.get("health")\n')
        self.assertEqual(candidates, {})

    def test_inside_a_command_self_is_the_command(self):
        """
        Found by running this against the lab game: it reported
        `character.args` and `character.caller` as handlers of the game's own
        and advised writing a provider for them. In a Command, `self` is the
        command object.

        """
        source = (
            "class CmdSetResource(Command):\n"
            '    key = "setres"\n'
            "    def func(self):\n"
            "        name = self.args.split()[0]\n"
            "        self.caller.msg(name)\n"
        )
        _, _, problems = _scan(source, "world/demo_cmds.py")
        self.assertEqual(problems, [])

    def test_a_handler_in_a_typeclass_is_still_found_through_self(self):
        source = (
            "class Character(DefaultCharacter):\n"
            "    def hurt(self):\n"
            '        self.traits.get("health").current -= 1\n'
        )
        _, _, problems = _scan(source)
        self.assertIn("traits", " ".join(problems))

    def test_evennias_own_members_are_never_a_game_handler(self):
        for member in ("location", "sessions", "cmdset", "ndb"):
            _, _, problems = _scan("def f(character):\n    character.%s.get(1)\n" % member)
            self.assertEqual(problems, [], member)

    def test_the_attribute_handlers_are_not_handlers_in_this_sense(self):
        """`db` and `attributes` are how a binding reads -- not a reason for advice."""
        _, _, problems = _scan(
            'def f(caller):\n    caller.db.hp = 1\n    caller.attributes.add("mp", 2)\n'
        )
        self.assertEqual(problems, [])


# ------------------------------------------------------------ B.53, B.56


class TestTheScanHasCeilings(TestCase):
    """
    B.56: configurable ceilings, and **say so when one is hit**. A scan that
    silently truncates teaches a developer that their attribute is not there.

    """

    def test_a_file_larger_than_the_ceiling_is_skipped_and_named(self):
        game = _Game({"world/huge.py": "x = 1\n" * 200000, "world/small.py": "y = 2\n"})
        names = game.names()
        problems = game.files()[1]
        self.assertEqual(names, ["world/small.py"])
        self.assertIn("world/huge.py", " ".join(problems))

    def test_too_many_files_stops_and_says_how_many_were_not_scanned(self):
        game = _Game({"world/f%03d.py" % index: "x = 1\n" for index in range(12)})
        paths, problems = game.files(max_files=5)
        self.assertEqual(len(paths), 5)
        note = " ".join(problems)
        self.assertIn("5", note)
        self.assertIn("7", note)

    def test_a_total_byte_ceiling_stops_the_walk(self):
        game = _Game({"world/a.py": "x = 1\n" * 500, "world/b.py": "y = 2\n" * 500})
        paths, problems = game.files(max_total_bytes=1000)
        self.assertEqual(len(paths), 1)
        self.assertTrue(problems)

    def test_a_file_whose_tree_is_enormous_is_reported_rather_than_parsed_twice(self):
        source = "x = [%s]\n" % ", ".join(str(n) for n in range(5000))
        found, actions, problems = static_scan.scan_source(source, "world/data.py", max_nodes=100)
        self.assertEqual(found, [])
        self.assertIn("world/data.py", " ".join(problems))

    def test_the_ceilings_are_constants_that_can_be_changed(self):
        for name in ("MAX_FILES", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES"):
            self.assertTrue(hasattr(roots, name), name)
        self.assertTrue(hasattr(static_scan, "MAX_NODES"))


# ------------------------------------------------------------------ B.25


class TestWhatIsNeverRead(TestCase):
    """B.25's denylist, and the one addition D4 makes to it."""

    def test_secrets_and_checkouts_and_environments_are_not_read(self):
        game = _Game(
            {
                "world/rules.py": "x = 1\n",
                ".env": "SECRET=1\n",
                "server/conf/secret_settings.py": "PASSWORD = 'x'\n",
                "world/private.pem": "-----BEGIN KEY-----\n",
                "world/.git/config": "[core]\n",
                "world/venv/lib.py": "import os\n",
                "world/node_modules/thing.py": "import os\n",
                "world/__pycache__/cached.py": "x = 1\n",
                "logs/server.log": "text\n",
            }
        )
        self.assertEqual(game.names(), ["world/rules.py"])

    def test_settings_is_never_read_even_though_it_is_the_obvious_file(self):
        game = _Game({"server/conf/settings.py": "AETOS_BINDINGS = {}\n", "world/a.py": "x = 1\n"})
        self.assertEqual(game.names(), ["world/a.py"])

    def test_a_source_file_whose_name_looks_like_a_credential_is_skipped_and_said(self):
        """
        `world/api_keys.py` is ordinary Python inside an approved root, so the
        walk would read it. Its name is the only warning available before
        reading, and B.46's reasoning applies to a file as much as an attribute.

        """
        game = _Game({"world/api_keys.py": "KEY = 'sk-live'\n", "world/rules.py": "x = 1\n"})
        names = game.names()
        problems = game.files()[1]
        self.assertEqual(names, ["world/rules.py"])
        self.assertIn("api_keys.py", " ".join(problems))

    def test_nothing_from_a_skipped_file_reaches_the_report(self):
        game = _Game({"world/api_keys.py": "SECRET_TOKEN = 'sk-live-42'\n"})
        candidates, _, problems = static_scan.scan_files(game.directory)
        found = CandidateSet()
        for candidate in candidates:
            found.add(candidate)
        self.assertNotIn("sk-live-42", report.render(found, problems))


# ------------------------------------------------------------ B.26, B.60


class TestHostileSourceIsParsedAndNeverRun(TestCase):
    """
    B.60. Discovery reads files a developer may have downloaded from anywhere.
    Each fixture below would leave a trace if it ran, and the tests fail if the
    trace appears.

    """

    HOSTILE = (
        "import os\n"
        "\n"
        'open("danger.txt", "w").write("pwned")\n'
        'os.system("echo pwned > pwned_by_system.txt")\n'
        'os.environ["PWNED"] = "1"\n'
        "raise RuntimeError('boom')\n"
        "\n"
        "class Character(DefaultCharacter):\n"
        "    hp = AttributeProperty(100)\n"
    )

    def test_it_is_read_without_any_of_it_happening(self):
        game = _Game({"world/hostile.py": self.HOSTILE})
        here = os.getcwd()
        os.chdir(game.directory)
        try:
            candidates, _, problems = static_scan.scan_files(game.directory)
        finally:
            os.chdir(here)

        # The candidate is found, so the scan really did read the file.
        self.assertIn("hp", [candidate.name for candidate in candidates])
        for trace in ("danger.txt", "pwned_by_system.txt"):
            self.assertFalse(os.path.exists(os.path.join(game.directory, trace)), trace)
            self.assertFalse(os.path.exists(os.path.join(here, trace)), trace)
        self.assertNotIn("PWNED", os.environ)

    def test_a_module_level_raise_does_not_reach_the_caller(self):
        candidates, _, problems = _scan("raise SystemExit(1)\n", "world/rude.py")
        self.assertEqual(candidates, {})

    def test_the_module_names_none_of_the_ways_to_execute(self):
        """
        The natural way to make this scan "better" is to import the module and
        use `dir()`, and that version cannot be made safe afterwards.

        """
        source = static_scan.__doc__ and (DISCOVERY / "static_scan.py").read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]
        for forbidden in ("importlib", "__import__", "exec(", "eval(", "compile("):
            self.assertNotIn(forbidden, body, forbidden)

    def test_one_unparseable_file_does_not_stop_the_others(self):
        """B.57. A tool that dies on the first legacy file is one nobody finishes."""
        game = _Game({"world/broken.py": "def (:\n", "world/fine.py": "x = 1\n"})
        candidates, _, problems = static_scan.scan_files(game.directory)
        self.assertIn("world/broken.py", " ".join(problems).replace(os.sep, "/"))
        self.assertIn("could not be parsed", " ".join(problems))


class TestTheWalkStaysInsideTheGame(TestCase):
    """
    B.55. Developers symlink `world/` at a shared checkout more often than
    anyone expects, and following one means reporting another project's source
    as this game's.

    """

    def test_a_symlinked_file_pointing_outside_is_not_read(self):
        outside = tempfile.mkdtemp()
        Path(outside, "elsewhere.py").write_text("secret = 1\n", encoding="utf-8")
        game = _Game({"world/rules.py": "x = 1\n"})
        link = Path(game.directory) / "world" / "linked.py"
        try:
            os.symlink(os.path.join(outside, "elsewhere.py"), link)
        except (OSError, NotImplementedError, AttributeError) as error:
            self.skipTest("symlinks not permitted here (%s)" % error)
        self.assertEqual(game.names(), ["world/rules.py"])
