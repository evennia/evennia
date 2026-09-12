"""
D3 -- runtime and structural discovery.

D0 proved a live Character could be read. D3 is what makes the reading worth
trusting: a developer chooses which character is representative (B.20), sees the
values and not only the names, gets three confidence levels that each say *why*
(B.28, B.33), and never sees a credential (B.46). The structural pass (B.22)
reads the typeclass and the command sets, which is where the two things the
attribute scan cannot see live -- declared `AttributeProperty` fields and a
game's own handlers.

The tests are organised around Addendum B's own examples, because those are the
cases a reviewer will check first:

- B.64, **fresh Evennia**: nothing invented. The critical genre-neutrality test.
- B.65, **a nontraditional game**: `hull_integrity` / `hull_capacity` pair by
  structure, not because somebody added them to a list.
- B.66, **a complex game**: values behind a handler produce a recommendation to
  write a provider, never an unsafe binding.
- B.28's two confidence cases, `hp` 82/100 and `energy` 40 with no maximum.

"""

import ast
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR
from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.discovery import (
    confidence,
    redaction,
    report,
    runtime_scan,
    structure,
    values,
)
from evennia.contrib.base_systems.aetos_webclient.discovery.candidates import (
    Candidate,
    CandidateSet,
)
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import lazy_property

DISCOVERY = Path(AETOS_STATIC_DIR).parent / "discovery"


class _Attribute:
    """A stand-in for an Evennia Attribute row."""

    def __init__(self, key, value, category=None):
        self.key = key
        self._value = value
        self.category = category

    @property
    def value(self):
        return self._value


class _Untouchable(_Attribute):
    """
    An attribute whose value must never be loaded.

    It *records* a read rather than raising. The scan wraps every value read in
    `except Exception`, so a raising fake would be swallowed and the test would
    pass whether or not the value was read -- a negative assertion satisfied by
    nothing happening, which this project has met before.

    """

    reads = []

    @property
    def value(self):
        _Untouchable.reads.append(self.key)
        return self._value


class _Character:
    """A stand-in for a Character: `id`, `db_key` and `attributes.all()`."""

    def __init__(self, identifier, attributes, key=None):
        self.id = identifier
        self.db_key = key or "Char%d" % identifier
        self.attributes = type("Handler", (), {"all": lambda _self: attributes})()


def _scan(*characters):
    """
    Run the runtime scan and every later stage over stand-in characters.

    Args:
        *characters: Lists of `_Attribute`, one list per character.

    Returns:
        tuple: `(CandidateSet, problems)`.

    """
    people = [_Character(index + 1, attributes) for index, attributes in enumerate(characters)]
    found = CandidateSet()
    candidates, problems = runtime_scan.scan_characters(people)
    for candidate in candidates:
        found.add(candidate)
    found.pair_maximums()
    found.assess(sampled=len(people))
    return found, problems


def _bindings(text):
    """
    The `AETOS_BINDINGS` dictionary a report would produce if pasted.

    Args:
        text (str): A rendered report.

    Returns:
        dict: The literal, evaluated without executing anything.

    """
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id == "AETOS_BINDINGS":
            return ast.literal_eval(node.value)
    return None


# ---------------------------------------------------------------------- B.46


class TestCredentialsAreNeverPrintedOrSuggested(TestCase):
    """
    B.46. A credential on a character is an attribute like any other, and by
    the time a value has been read it is too late to decide not to have read
    it -- so the decision is made on the name.

    """

    def test_every_marker_in_the_addendum_is_caught(self):
        for name in (
            "password",
            "passwd",
            "client_secret",
            "session_token",
            "api_key",
            "API-KEY",
            "apikey",
            "private_key",
            "credentials",
        ):
            self.assertTrue(redaction.is_sensitive(name), name)

    def test_ordinary_names_are_not(self):
        for name in ("hp", "key", "room_key", "keys_held", "oxygen", "hull_capacity"):
            self.assertFalse(redaction.is_sensitive(name), name)

    def test_the_false_positive_is_the_documented_one(self):
        """
        `tokens` as a currency is withheld. The module says so and why: a miss
        prints a secret, a false positive costs one hand-written line.

        """
        self.assertTrue(redaction.is_sensitive("tokens"))
        self.assertIn("db.tokens", _source("redaction.py"))

    def test_the_value_of_a_sensitive_attribute_is_never_loaded(self):
        _Untouchable.reads.clear()
        found, problems = _scan([_Untouchable("api_token", "sk-live"), _Attribute("hp", 5)])
        self.assertEqual(_Untouchable.reads, [])
        self.assertNotIn("db.api_token", found.candidates)
        self.assertIn("db.hp", found.candidates)

    def test_the_fake_would_notice_a_read(self):
        """The counterfactual: an ordinary name *is* read, and the fake records it."""
        _Untouchable.reads.clear()
        _scan([_Untouchable("hp", 5)])
        self.assertEqual(_Untouchable.reads, ["hp"])

    def test_what_was_withheld_is_said_rather_than_silently_dropped(self):
        found, problems = _scan([_Untouchable("password", "x")])
        note = " ".join(problems)
        self.assertIn("password", note)
        self.assertIn(redaction.REDACTED, note)

    def test_a_sensitive_key_inside_a_dict_is_withheld(self):
        found, _ = _scan([_Attribute("auth", {"token": "sk-live", "level": 3})])
        self.assertNotIn("db.auth.token", found.candidates)
        self.assertIn("db.auth.level", found.candidates)

    def test_a_dict_with_a_sensitive_name_withholds_everything_in_it(self):
        found, _ = _scan([_Attribute("secrets", {"level": 3})])
        self.assertEqual([c for c in found.candidates if c.startswith("db.secrets")], [])

    def test_the_static_scan_cannot_smuggle_one_in_either(self):
        """
        The set refuses a sensitive name whichever scan offered it, so a future
        scan cannot forget.

        """
        found = CandidateSet()
        found.add(Candidate("db.password", "password", "static", "x.py:1", "text"))
        self.assertEqual(len(found), 0)
        self.assertIn("password", found.withheld)

    def test_no_secret_reaches_the_report(self):
        found, problems = _scan(
            [_Attribute("hp", 5), _Attribute("hp_max", 9), _Attribute("gm_password", "hunter2")]
        )
        text = report.render(found, problems)
        self.assertNotIn("hunter2", text)


# --------------------------------------------------------------- values, B.20


class _Hostile:
    """An object whose every display method is a trap."""

    def __repr__(self):
        raise AssertionError("repr was called")

    def __str__(self):
        raise AssertionError("str was called")

    def __getattr__(self, name):
        raise AssertionError("getattr(%r) was called" % name)


class TestValuesAreShownWithoutRunningTheirCode(TestCase):
    """
    B.20 wants `db.hp 82 int`. The obvious way to show a value is `repr`, which
    is a method call on an object of the game's choosing.

    """

    def test_numbers_and_flags_and_text(self):
        self.assertEqual(values.shown(82), "82")
        self.assertEqual(values.shown(2.5), "2.5")
        self.assertEqual(values.shown(False), "False")
        self.assertEqual(values.shown("the Brave"), "'the Brave'")

    def test_long_text_is_cut(self):
        self.assertLess(len(values.shown("x" * 500)), 60)

    def test_an_unknown_object_is_named_by_its_type_and_nothing_runs(self):
        self.assertEqual(values.kind_of(_Hostile()), "unknown")
        self.assertEqual(values.shown(_Hostile()), "a _Hostile")

    def test_a_collection_is_shown_by_size_not_contents(self):
        self.assertEqual(values.shown({"password": "hunter2"}), "1 item")
        self.assertEqual(values.shown([1, 2, 3]), "3 items")

    def test_a_structure_that_contains_itself_does_not_hang(self):
        loop = []
        loop.append(loop)
        self.assertEqual(values.shown(loop), "1 item")

    def test_the_value_appears_beside_the_attribute(self):
        found, _ = _scan([_Attribute("hp", 82)])
        self.assertIn("82", found.candidates["db.hp"].evidence)


class TestAGameObjectIsATargetCandidate(TestCase):
    """
    B.20's `db.current_target Goblin Object`. Needs a real object, because
    "is this a game object" is an isinstance check against Evennia's model.

    """

    def setUp(self):
        from evennia.utils import create

        self.goblin = create.create_object("evennia.objects.objects.DefaultObject", key="Goblin")

    def tearDown(self):
        self.goblin.delete()

    def test_it_is_shown_by_its_row_not_its_methods(self):
        self.assertEqual(values.kind_of(self.goblin), "object")
        self.assertEqual(values.shown(self.goblin), "Goblin (#%d)" % self.goblin.id)

    def test_it_is_suggested_as_the_target_name(self):
        found, _ = _scan([_Attribute("current_target", self.goblin)])
        text = report.render(found)
        bindings = _bindings(text)
        self.assertEqual(bindings["target"]["name"]["value"], "db.current_target")

    def test_the_suggestion_actually_names_the_target(self):
        """
        Not assumed: D2's target provider resolves the attribute to the object,
        and the normaliser turns it into its name. Checked end to end, because a
        suggestion that fails when pasted is worse than none.

        """
        from evennia.contrib.base_systems.aetos_webclient.bindings.bound_providers import (
            BoundTargetProvider,
        )
        from evennia.contrib.base_systems.aetos_webclient.character_state import (
            normalize_target,
        )
        from evennia.utils import create

        holder = create.create_object("evennia.objects.objects.DefaultCharacter", key="Hunter")
        self.addCleanup(holder.delete)
        holder.db.current_target = self.goblin
        declared = {"target": {"name": {"label": "Target", "value": "db.current_target"}}}
        with override_settings(AETOS_BINDINGS=declared):
            target = normalize_target(BoundTargetProvider().get_target(holder))
        self.assertEqual(target["name"], "Goblin")


# -------------------------------------------------------------- selection, B.21


class TestTheDeveloperChoosesWhoIsRepresentative(TestCase):
    """
    B.20 and B.21: a developer-selected representative, and never the whole
    database.

    """

    def setUp(self):
        from evennia.utils import create

        self.made = [
            create.create_object("evennia.objects.objects.DefaultCharacter", key="Ada"),
            create.create_object("evennia.objects.objects.DefaultCharacter", key="Twin"),
            create.create_object("evennia.objects.objects.DefaultCharacter", key="Twin"),
        ]

    def tearDown(self):
        for thing in self.made:
            thing.delete()

    def test_by_number(self):
        chosen = runtime_scan.select_characters(character="#%d" % self.made[0].id)
        self.assertEqual([c.id for c in chosen], [self.made[0].id])

    def test_by_name(self):
        chosen = runtime_scan.select_characters(character="ada")
        self.assertEqual([c.id for c in chosen], [self.made[0].id])

    def test_an_ambiguous_name_is_refused_and_says_how_to_choose(self):
        with self.assertRaises(runtime_scan.SelectionError) as caught:
            runtime_scan.select_characters(character="Twin")
        message = str(caught.exception)
        self.assertIn("#%d" % self.made[1].id, message)
        self.assertIn("--character #", message)

    def test_nothing_by_that_name_is_an_error_not_an_empty_report(self):
        with self.assertRaises(runtime_scan.SelectionError):
            runtime_scan.select_characters(character="Nobody At All")

    def test_a_typeclass_path_that_does_not_import_is_explained(self):
        with self.assertRaises(runtime_scan.SelectionError):
            runtime_scan.select_characters(typeclass="no.such.Typeclass")

    @override_settings(BASE_CHARACTER_TYPECLASS="evennia.objects.objects.DefaultObject")
    def test_the_default_sample_includes_subclasses(self):
        """
        D0 filtered on the exact path, so a game whose characters all use a
        subclass -- the ordinary case -- read nobody.

        The setting names a *parent* of the characters made here. The first
        version of this test named their exact class, so an exact-path filter
        passed it too; a mutation check found that.

        """
        chosen = runtime_scan.select_characters()
        ids = {c.id for c in chosen}
        self.assertTrue({thing.id for thing in self.made} <= ids)

    def test_the_sample_is_still_bounded(self):
        self.assertIn("[:limit]", _source("runtime_scan.py"))


# ------------------------------------------------------------ runtime, B.20


class TestTheRuntimeScanReadsDeeper(TestCase):
    def test_numeric_keys_inside_a_dict_become_two_level_bindings(self):
        """
        `db.stats = {"hp": 5, "hp_max": 9}` is common, and `db.name.child` is
        exactly what the grammar allows for it.

        """
        found, _ = _scan([_Attribute("stats", {"hp": 5, "hp_max": 9, "__class__": 1})])
        self.assertIn("db.stats.hp", found.candidates)
        self.assertEqual(found.candidates["db.stats.hp"].maximum, "db.stats.hp_max")
        self.assertNotIn("db.stats.__class__", found.candidates)
        for expression in found.candidates:
            self.assertTrue(schema.is_valid_expression(expression), expression)

    def test_a_categorised_attribute_is_reported_rather_than_silently_skipped(self):
        """
        Evennia's traits contrib keeps stats as categorised attributes. D0
        skipped them without a word, so a game built on traits got an empty
        report and no reason.

        """
        found, problems = _scan([_Attribute("strength", 12, category="traits")])
        self.assertEqual(len(found), 0)
        note = " ".join(problems)
        self.assertIn("traits", note)
        self.assertIn("provider", note)

    def test_a_ceiling_seen_exceeded_is_a_warning_naming_the_character(self):
        found, _ = _scan(
            [_Attribute("hp", 50), _Attribute("hp_max", 100)],
            [_Attribute("hp", 120), _Attribute("hp_max", 100)],
        )
        hp = found.candidates["db.hp"]
        self.assertEqual(hp.confidence, confidence.MEDIUM)
        self.assertTrue(any("#2" in warning for warning in hp.warnings))


# ------------------------------------------------------------ pairing, B.65


class TestPairingIsStructuralNotAList(TestCase):
    """
    B.32 and B.65. The addendum's own examples of games that are not fantasy.

    """

    def _paired(self, value, ceiling):
        found, _ = _scan([_Attribute(value, 40), _Attribute(ceiling, 100)])
        return found.candidates["db.%s" % value].maximum

    def test_the_addendums_nontraditional_pairs(self):
        for value, ceiling in (
            ("hull_integrity", "hull_capacity"),
            ("oxygen", "oxygen_capacity"),
            ("reactor_output", "reactor_capacity"),
            ("morale", "morale_limit"),
        ):
            self.assertEqual(self._paired(value, ceiling), "db.%s" % ceiling, value)

    def test_the_addendums_prefix_forms(self):
        """`max_hp` is B.32's own example, and D0 paired suffixes only."""
        self.assertEqual(self._paired("hp", "max_hp"), "db.max_hp")
        self.assertEqual(self._paired("mana", "maxmana"), "db.maxmana")

    def test_a_pair_in_a_language_the_scan_has_no_word_for(self):
        """
        `salud` / `salud_tope`: no ceiling word matches, so the pair is found
        from structure alone -- one name extends the other and was never below
        it -- and says so at a lower confidence.

        """
        found, _ = _scan(
            [_Attribute("salud", 40), _Attribute("salud_tope", 100)],
            [_Attribute("salud", 90), _Attribute("salud_tope", 100)],
        )
        salud = found.candidates["db.salud"]
        self.assertEqual(salud.maximum, "db.salud_tope")
        self.assertEqual(salud.pairing, "structure")
        self.assertEqual(salud.confidence, confidence.MEDIUM)

    def test_structure_does_not_pair_a_value_that_went_above_it(self):
        found, _ = _scan([_Attribute("salud", 40), _Attribute("salud_regen", 2)])
        self.assertIsNone(found.candidates["db.salud"].maximum)

    def test_structure_does_not_guess_between_two_candidates(self):
        found, _ = _scan(
            [_Attribute("salud", 4), _Attribute("salud_tope", 10), _Attribute("salud_banco", 50)]
        )
        self.assertIsNone(found.candidates["db.salud"].maximum)

    def test_structure_needs_more_than_one_reading(self):
        """
        Found against the lab: `poison` paired with `poison_left` -- rounds
        remaining, not a ceiling -- from a single character. "Never below it"
        on one reading proves nothing.

        """
        found, _ = _scan([_Attribute("poison", 1), _Attribute("poison_left", 3)])
        self.assertIsNone(found.candidates["db.poison"].maximum)

    def test_a_shared_stem_pairs_but_cannot_be_high(self):
        """
        Found against the lab: `target_hp` / `target_max` pair through the stem
        `target` and are the target's health, not the player's.

        """
        found, _ = _scan(
            [_Attribute("hull_integrity", 40), _Attribute("hull_capacity", 100)],
            [_Attribute("hull_integrity", 60), _Attribute("hull_capacity", 100)],
        )
        hull = found.candidates["db.hull_integrity"]
        self.assertEqual(hull.pairing, "stem")
        self.assertEqual(hull.confidence, confidence.MEDIUM)

    def test_a_stem_shared_with_a_name_points_at_the_target_slot(self):
        found, _ = _scan(
            [
                _Attribute("target_hp", 4),
                _Attribute("target_max", 9),
                _Attribute("target_name", "a dummy"),
            ],
            [
                _Attribute("target_hp", 6),
                _Attribute("target_max", 9),
                _Attribute("target_name", "a rat"),
            ],
        )
        warnings = " ".join(found.candidates["db.target_hp"].warnings)
        self.assertIn("db.target_name", warnings)
        self.assertIn("target slot", warnings)

    def test_a_ceiling_does_not_pair_with_text(self):
        found, _ = _scan([_Attribute("hp", 40), _Attribute("hp_max", "lots")])
        self.assertIsNone(found.candidates["db.hp"].maximum)


# --------------------------------------------------------- confidence, B.28


class TestConfidenceIsThreeWordsAndAlwaysExplained(TestCase):
    """B.28 and B.33."""

    def _with_source(self, found, name, kind="number"):
        found.add(Candidate("db.%s" % name, name, "static", "characters.py:4", kind))

    def _assessed(self, runtime, static=()):
        found = CandidateSet()
        people = [_Character(1, runtime)]
        candidates, _ = runtime_scan.scan_characters(people)
        for candidate in candidates:
            found.add(candidate)
        for name in static:
            self._with_source(found, name)
        found.pair_maximums()
        found.assess(sampled=1)
        return found

    def test_the_levels_are_the_addendums(self):
        self.assertEqual(confidence.LEVELS, ("HIGH", "MEDIUM", "LOW"))

    def test_hp_82_of_100_with_source_is_high(self):
        """B.64's first confidence example, verbatim."""
        found = self._assessed(
            [_Attribute("hp", 82), _Attribute("hp_max", 100)], static=("hp", "hp_max")
        )
        self.assertEqual(found.candidates["db.hp"].confidence, confidence.HIGH)

    def test_energy_40_with_no_maximum_is_not_high(self):
        """B.64's second: must not be presented as an equivalent pair."""
        found = self._assessed([_Attribute("energy", 40)])
        self.assertEqual(found.candidates["db.energy"].confidence, confidence.MEDIUM)

    def test_a_pair_seen_only_in_source_is_low(self):
        found = CandidateSet()
        self._with_source(found, "hp")
        self._with_source(found, "hp_max")
        found.pair_maximums()
        found.assess(sampled=0)
        self.assertEqual(found.candidates["db.hp"].confidence, confidence.LOW)

    def test_on_one_character_of_many_is_a_warning_and_a_step_down(self):
        found, _ = _scan(
            [_Attribute("hp", 5), _Attribute("hp_max", 9)],
            [_Attribute("gold", 1)],
            [_Attribute("gold", 2)],
        )
        hp = found.candidates["db.hp"]
        self.assertEqual(hp.confidence, confidence.MEDIUM)
        self.assertTrue(any("1 of 3" in warning for warning in hp.warnings))

    def test_every_candidate_says_why(self):
        found, _ = _scan(
            [
                _Attribute("hp", 5),
                _Attribute("hp_max", 9),
                _Attribute("gold", 3),
                _Attribute("poisoned", True),
                _Attribute("title", "the Brave"),
            ]
        )
        for candidate in found.candidates.values():
            self.assertTrue(candidate.reasons, candidate.expression)

    def test_it_is_deterministic(self):
        rows = [_Attribute("hp", 5), _Attribute("hp_max", 9), _Attribute("gold", 3)]
        first = report.render(_scan(rows)[0])
        second = report.render(_scan(list(reversed(rows)))[0])
        self.assertEqual(first, second)

    def test_the_source_that_disagrees_with_the_live_value_is_a_warning(self):
        found = CandidateSet()
        found.add(Candidate("db.hp", "hp", "static", "characters.py:4", "text"))
        candidates, _ = runtime_scan.scan_characters([_Character(1, [_Attribute("hp", 5)])])
        for candidate in candidates:
            found.add(candidate)
        found.assess(sampled=1)
        self.assertTrue(found.candidates["db.hp"].warnings)


# -------------------------------------------------------------- slots, D0 bug


class TestEachKindGoesWhereItCanBeUsed(TestCase):
    """
    D0 put every candidate under `resources`. A text attribute there resolves
    to no number, so the bar never draws: a pasted setting that silently does
    nothing -- which this project has now found five times in its own client,
    and would have been generating for other people.

    """

    def test_text_is_not_suggested_as_a_resource(self):
        found, _ = _scan([_Attribute("title", "the Brave"), _Attribute("hp", 5)])
        bindings = _bindings(report.render(found))
        self.assertNotIn("title", bindings.get("resources", {}))

    def test_text_is_still_mentioned(self):
        found, _ = _scan([_Attribute("title", "the Brave")])
        self.assertIn("db.title", report.render(found))

    def test_a_flag_is_offered_as_an_effect_not_a_bar(self):
        found, _ = _scan([_Attribute("poisoned", True)])
        self.assertEqual(found.candidates["db.poisoned"].slot, "effects")


# ------------------------------------------------------------ structure, B.22


class _Base:
    """Stands in for an Evennia base class."""


_Base.__module__ = "evennia.objects.objects"


class _Handler:
    def get(self, name):
        raise AssertionError("the handler was called")


class _Tripwire(AttributeProperty):
    """An AttributeProperty that records being read through."""

    touched = []

    def __get__(self, instance, owner):
        _Tripwire.touched.append(self._key)
        return 0


class _GameCharacter(_Base):
    """A typeclass with the things B.22 asks about."""

    tripwire = _Tripwire(5)
    oxygen = AttributeProperty(100)
    faction_rank = AttributeProperty(0, category="factions")

    @lazy_property
    def stats(self):
        return _Handler()


class TestTheStructuralPass(TestCase):
    def test_the_lineage_ends_at_the_first_evennia_class(self):
        chain = structure.lineage(_GameCharacter)
        self.assertEqual(chain[0], "%s._GameCharacter" % __name__)
        self.assertEqual(chain[-1], "evennia.objects.objects._Base")

    def test_a_declared_attribute_is_found_without_touching_the_descriptor(self):
        _Tripwire.touched.clear()
        candidates, problems = structure.declared_attributes(_GameCharacter)
        self.assertEqual(_Tripwire.touched, [])
        names = {c.name: c for c in candidates}
        self.assertIn("tripwire", names)
        self.assertIn("oxygen", names)
        self.assertEqual(names["oxygen"].kind, "number")
        self.assertEqual(names["oxygen"].origin, "typeclass")

    def test_the_tripwire_would_notice_getattr(self):
        """The counterfactual: reading it the obvious way runs the descriptor."""
        _Tripwire.touched.clear()
        getattr(_GameCharacter, "tripwire")
        self.assertEqual(_Tripwire.touched, ["tripwire"])

    def test_a_categorised_declaration_is_reported_not_suggested(self):
        candidates, problems = structure.declared_attributes(_GameCharacter)
        self.assertNotIn("faction_rank", {c.name for c in candidates})
        self.assertIn("faction_rank", " ".join(problems))

    def test_a_game_handler_recommends_a_provider_and_generates_nothing(self):
        """
        B.66: `character.stats.get("health").current` must not generate an
        unsafe binding. The handler is named, and the advice is a provider.

        """
        notes = structure.handler_notes(_GameCharacter)
        self.assertEqual(len(notes), 1)
        self.assertIn("stats", notes[0])
        self.assertIn("AETOS_PROVIDERS", notes[0])

    def test_evennias_own_handlers_are_not_reported(self):
        from evennia.objects.objects import DefaultCharacter

        self.assertEqual(structure.handler_notes(DefaultCharacter), [])


def _command(key, doc, locks="cmd:all()", module=None):
    """A Command subclass made on the spot, with a chosen module."""
    from evennia.commands.command import Command

    made = type("Cmd%s" % key.title(), (Command,), {"key": key, "__doc__": doc, "locks": locks})
    made.__module__ = module or "world.combat"
    return made()


class _CmdSet:
    def __init__(self, *commands):
        self.commands = list(commands)
        self.key = "GameCmdSet"


class TestCommandsBecomeActionCandidates(TestCase):
    """B.22: commands may become candidate context actions."""

    def test_a_game_command_that_takes_an_argument(self):
        actions, _ = structure.game_commands(
            [_CmdSet(_command("attack", "Hit something.\n\nUsage:\n  attack <target>\n"))]
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].command, "attack {target}")
        self.assertEqual(actions[0].confidence, confidence.MEDIUM)
        self.assertTrue(actions[0].reasons)

    def test_two_arguments_cannot_both_be_the_target(self):
        """
        Found against the lab: `setres <name> <value>` was suggested as a target
        action at MEDIUM. Its argument is a resource name and a number.

        """
        actions, _ = structure.game_commands(
            [_CmdSet(_command("setres", "Usage:\n  setres <name> <value>\n"))]
        )
        self.assertEqual(actions[0].confidence, confidence.LOW)

    def test_one_with_no_usage_line_is_low(self):
        actions, _ = structure.game_commands([_CmdSet(_command("dance", "Dance."))])
        self.assertEqual(actions[0].confidence, confidence.LOW)

    def test_a_staff_command_is_not_a_player_action(self):
        actions, problems = structure.game_commands(
            [_CmdSet(_command("smite", "Usage:\n  smite <x>", locks="cmd:perm(Builder)"))]
        )
        self.assertEqual(actions, [])

    def test_a_command_set_that_failed_to_load_is_said_out_loud(self):
        """
        Found against the lab. Evennia does not raise when a command set will
        not import: it substitutes an empty one keyed `_CMDSET_ERROR`. D3's first
        run read that as "this game has no commands".

        """
        broken = type("Broken", (), {"key": structure.ERROR_CMDSET_KEY, "commands": []})()
        holder = type("Holder", (), {"id": 54})()
        holder.cmdset = type("Handler", (), {"all": lambda _self: [broken]})()
        cmdsets, problems = structure.cmdsets_of(holder)
        self.assertEqual(cmdsets, [])
        self.assertIn("#54", " ".join(problems))
        self.assertIn("could not load", " ".join(problems))

    def test_evennias_default_commands_are_not_game_actions(self):
        from evennia.commands.default.cmdset_character import CharacterCmdSet

        actions, _ = structure.game_commands([CharacterCmdSet()])
        self.assertEqual(actions, [])

    def test_a_system_command_is_skipped(self):
        actions, _ = structure.game_commands([_CmdSet(_command("__noinput_command", "x"))])
        self.assertEqual(actions, [])


# ------------------------------------------------------------ fresh, B.64


class TestFreshEvennia(TestCase):
    """
    B.64, the critical genre-neutrality test. A pristine character, Evennia's
    own typeclass and Evennia's own commands must produce nothing -- no health
    bar for a game with no health.

    """

    def setUp(self):
        from evennia.utils import create

        self.character = create.create_object(
            "evennia.objects.objects.DefaultCharacter", key="Pristine"
        )

    def tearDown(self):
        self.character.delete()

    def test_nothing_is_invented(self):
        from evennia.commands.default.cmdset_character import CharacterCmdSet
        from evennia.objects.objects import DefaultCharacter

        found = CandidateSet()
        candidates, problems = runtime_scan.scan_characters([self.character])
        declared, more = structure.declared_attributes(DefaultCharacter)
        actions, _ = structure.game_commands([CharacterCmdSet()])
        for candidate in candidates + declared:
            found.add(candidate)
        for action in actions:
            found.add_action(action)
        found.pair_maximums()
        found.assess(sampled=1)

        for slot in schema.BINDING_SLOTS:
            self.assertEqual(found.by_slot(slot), [], slot)
        self.assertEqual(structure.handler_notes(DefaultCharacter), [])


# --------------------------------------------------------------- the report


class TestTheReportExplainsAndStaysPastable(TestCase):
    def _report(self):
        found, problems = _scan(
            [
                _Attribute("hp", 82),
                _Attribute("hp_max", 100),
                _Attribute("poisoned", False),
            ],
            [_Attribute("hp", 70), _Attribute("hp_max", 100), _Attribute("poisoned", True)],
        )
        found.add_action(
            structure.game_commands([_CmdSet(_command("attack", "Usage:\n  attack <target>"))])[0][
                0
            ]
        )
        return report.render(found, problems, context={"characters": ["#1 Ada", "#2 Bo"]})

    def test_it_passes_the_validator_that_will_read_it(self):
        """
        Stronger than "it parses": D1's own validator accepts it, so pasting it
        cannot fail at startup.

        """
        schema.validate_bindings(_bindings(self._report()))

    def test_low_confidence_is_offered_but_not_selected(self):
        """B.28: low-confidence findings are not selected by default."""
        text = self._report()
        bindings = _bindings(text)
        self.assertNotIn("effects", bindings)
        self.assertIn('#         "poisoned"', text)

    def test_a_low_entry_inside_an_active_slot_is_still_commented_out(self):
        """
        The case that matters. A slot where everything is LOW is commented out
        whole by a different line; the first version of this suite only tested
        that one, and a mutation that selected LOW entries passed it.

        """
        found = CandidateSet()
        for candidate in runtime_scan.scan_characters(
            [_Character(1, [_Attribute("hp", 5), _Attribute("hp_max", 9)])]
        )[0]:
            found.add(candidate)
        found.add(Candidate("db.focus", "focus", "static", "characters.py:9", "number"))
        found.pair_maximums()
        found.assess(sampled=1)
        text = report.render(found)
        resources = _bindings(text)["resources"]
        self.assertIn("hp", resources)
        self.assertNotIn("focus", resources)
        self.assertIn('#         "focus"', text)

    def test_what_is_selected(self):
        bindings = _bindings(self._report())
        self.assertEqual(bindings["resources"]["hp"]["maximum"], "db.hp_max")
        self.assertEqual(bindings["actions"]["attack"]["command"], "attack {target}")

    def test_each_suggestion_answers_the_addendums_five_questions(self):
        """
        B.33: what was found, where, why it may matter, how confident, and what
        accepting it generates.

        """
        text = self._report()
        for marker in ("found:", "why:", "makes:", "HIGH"):
            self.assertIn(marker, text)

    def test_it_says_who_was_read(self):
        self.assertIn("#1 Ada", self._report())

    def test_every_expression_passes_the_grammar(self):
        bindings = _bindings(self._report())
        for slot, entries in bindings.items():
            for entry in entries.values():
                for field in schema.EXPRESSION_FIELDS & set(entry):
                    self.assertTrue(schema.is_valid_expression(entry[field]))


class TestTheCommandLine(TestCase):
    def test_a_representative_can_be_named(self):
        source = (DISCOVERY.parent / "management" / "commands" / "aetos.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("--character", source)
        self.assertIn("--typeclass", source)

    def test_it_initialises_evennia_the_way_the_launcher_does(self):
        """
        Without it a game's command set module imports `evennia.default_cmds`
        while it is still None, and Evennia substitutes its empty error set.

        """
        source = (DISCOVERY.parent / "management" / "commands" / "aetos.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("evennia._init()", source)


def _source(name):
    """
    One discovery module's source.

    Args:
        name (str): File name inside the discovery package.

    Returns:
        str: The file's text.

    """
    return (DISCOVERY / name).read_text(encoding="utf-8")
