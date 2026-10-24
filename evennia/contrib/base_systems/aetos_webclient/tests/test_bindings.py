"""
Tests for D1, the binding resolver.

D1's gate is one sentence: a health bar appears from nothing but

    AETOS_BINDINGS = {
        "resources": {
            "health": {"label": "Health", "value": "db.hp", "maximum": "db.hp_max"},
        },
    }

with no custom Python class anywhere. `TestTheGate` is that sentence, run.

**The security tests are the substance of D1, not an afterthought.** Addendum
B.59 names what must fail -- `__class__`, `__globals__`, `method()`, `foo[0]`,
`foo + bar`, `lambda`, `import`, and semicolon and newline injection -- and a
resolver that quietly accepts any one of them has reintroduced `eval` with extra
steps. That failure is invisible: the setting still looks like a path, the widget
still renders, and nothing in any output says what happened.

So there are two layers and both are tested. The **grammar** decides what may be
written, and D0 already shipped it with the hole it existed to prevent (it
accepted `db.__class__`, because a dunder is an identifier). The **resolver**
decides what actually happens when one is read, and it is tested against objects
that record whether they were touched -- because a grammar test proves what was
refused and only a resolver test proves what was not called.

"""

from unittest import mock

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import bindings, manifest, providers
from evennia.contrib.base_systems.aetos_webclient.bindings import (
    bound_providers,
)
from evennia.contrib.base_systems.aetos_webclient.bindings import (
    resolver as resolver_module,
)
from evennia.contrib.base_systems.aetos_webclient.bindings import schema
from evennia.contrib.base_systems.aetos_webclient.providers import base

HEALTH = {
    "resources": {
        "health": {"label": "Health", "value": "db.hp", "maximum": "db.hp_max"},
    },
}


class _Attributes:
    """A stand-in for Evennia's AttributeHandler, recording what was asked for."""

    def __init__(self, values):
        self.values = values
        self.asked = []

    def get(self, key, default=None):
        self.asked.append(key)
        return self.values.get(key, default)


class _Character:
    """A stand-in for a Character. Holds attributes and nothing else."""

    def __init__(self, **values):
        self.attributes = _Attributes(values)


class _Tripwire:
    """
    An object that records every way it was reached.

    Stored *in* a character attribute, so the resolver meets it on the second
    level of `db.name.child`. Anything it records is something the resolver did
    that it promised not to.

    """

    def __init__(self):
        self.calls = []
        self.gets = []
        self.items = []

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        return "called"

    def __getattr__(self, name):
        self.gets.append(name)
        return "traversed"

    def __getitem__(self, key):
        self.items.append(key)
        return "subscripted"

    @property
    def touched(self):
        return bool(self.calls or self.gets or self.items)


class TestTheGate(TestCase):
    """
    D1's gate, exactly as the roadmap words it.

    """

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_PROVIDERS={})
    def test_a_health_bar_appears_from_the_settings_block_alone(self):
        character = _Character(hp=42, hp_max=50)
        resolved = providers.get_providers()["resources"]

        self.assertEqual(
            resolved.get_resources(character),
            [{"id": "health", "label": "Health", "value": 42, "maximum": 50}],
        )

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_PROVIDERS={})
    def test_with_no_custom_python_class_anywhere(self):
        """
        The other half of the gate. A test that passed because the lab game
        happened to have a provider would prove nothing.

        """
        self.assertEqual(providers.get_providers()["resources"].name, "resources (bindings)")

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_the_declaration_switches_the_feature_on_by_itself(self):
        """
        Having to also write `AETOS_FEATURES = {"resources": True}` is exactly
        the second step that makes a zero-code feature feel broken.

        """
        self.assertTrue(manifest.get_features()["resources"])

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_PROVIDERS={})
    def test_the_payload_is_the_shape_the_normaliser_expects(self):
        """
        A binding that produced a subtly different resource dict would render
        once and then diverge on thresholds, announcements or labels -- and
        those are the accessibility surface.

        """
        from evennia.contrib.base_systems.aetos_webclient import resources

        raw = providers.get_providers()["resources"].get_resources(_Character(hp=42, hp_max=50))
        normalized = resources.normalize_resources(raw)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["id"], "health")
        self.assertEqual(normalized[0]["value"], 42)


class TestNothingIsCalledSubscriptedOrTraversed(TestCase):
    """
    B.59, checked against the resolver rather than only against the grammar.

    A grammar test proves what was refused. Only a test with an object that
    records being touched proves what was *not called*, and that is the promise
    the whole design rests on.

    """

    def setUp(self):
        self.resolver = resolver_module.AetosBindingResolver()

    def test_a_stored_object_is_never_called(self):
        tripwire = _Tripwire()
        character = _Character(thing=tripwire)
        for expression in ("db.thing", "db.thing.hp"):
            self.resolver.resolve(character, expression)
        self.assertEqual(tripwire.calls, [])

    def test_a_stored_object_is_never_traversed_with_getattr(self):
        """
        The rejected reading of `db.stats.hp`. Allowing it would have the
        resolver running the game's `__getattr__` on an arbitrary object, which
        is the thing this design exists to avoid.

        """
        tripwire = _Tripwire()
        character = _Character(stats=tripwire)
        self.assertIsNone(self.resolver.resolve(character, "db.stats.hp"))
        self.assertEqual(tripwire.gets, [])

    def test_a_stored_object_is_never_subscripted(self):
        tripwire = _Tripwire()
        character = _Character(stats=tripwire)
        self.resolver.resolve(character, "db.stats.hp")
        self.assertEqual(tripwire.items, [])

    def test_a_real_dict_is_read_because_a_dict_lookup_can_do_nothing_else(self):
        """
        The case that is allowed, and why. `character.db.stats = {"hp": 50}` is
        ordinary Evennia, and reading a key out of a genuine mapping cannot run
        game code.

        """
        character = _Character(stats={"hp": 50})
        self.assertEqual(self.resolver.resolve(character, "db.stats.hp"), 50)

    def test_every_rejected_expression_resolves_to_nothing(self):
        """
        Not merely refused by the grammar -- fed to the resolver, which is where
        it would matter.

        """
        tripwire = _Tripwire()
        character = _Character(hp=tripwire, thing=tripwire, stats=tripwire)
        for expression in schema.REJECTED_EXPRESSIONS:
            with self.subTest(expression=expression):
                self.assertIsNone(self.resolver.resolve(character, expression))
        self.assertFalse(tripwire.touched, "a refused expression still reached the object")

    def test_the_grammar_is_rechecked_at_use_not_only_at_startup(self):
        """
        A caller that built an expression by concatenation is refused rather
        than trusted. There must be no path into the traversal that skips the
        check.

        """
        source = resolver_module.__file__.replace(".pyc", ".py")
        with open(source, "r", encoding="utf-8") as handle:
            body = handle.read()
        traversal = body[body.index("def resolve(self, character, expression)") :]
        self.assertLess(
            traversal.index("is_valid_expression"),
            traversal.index("attributes.get"),
            "the expression is read before it is validated",
        )

    def test_the_resolver_contains_no_evaluator(self):
        """
        Parsed, not grepped.

        The first version of this searched the raw source and failed on the
        resolver's own docstring, which says `getattr(value, name)` while
        explaining why it does not do that. A text search cannot tell an
        explanation from an instruction, and the version that could would be
        "grep, but skip the comments" -- an AST with extra steps and no
        guarantees.

        """
        import ast

        with open(resolver_module.__file__.replace(".pyc", ".py"), "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())

        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        for forbidden in ("eval", "exec", "compile", "__import__", "getattr"):
            self.assertNotIn(forbidden, called, "the resolver calls %s" % forbidden)


class TestResolutionIsForgivingAboutTheGameAndStrictAboutTheGrammar(TestCase):
    """
    A missing attribute is an ordinary state, not an error.

    """

    def setUp(self):
        self.resolver = resolver_module.AetosBindingResolver()

    def test_an_attribute_that_does_not_exist_yet_is_none(self):
        """
        A new character, a half-built feature, a binding written before the
        attribute. All normal, none an error.

        """
        self.assertIsNone(self.resolver.resolve(_Character(), "db.hp"))

    def test_a_character_that_raises_costs_one_widget_and_not_the_session(self):
        character = _Character()
        character.attributes.get = mock.Mock(side_effect=RuntimeError("mid-deletion"))
        self.assertIsNone(self.resolver.resolve(character, "db.hp"))

    def test_no_character_at_all_is_none(self):
        self.assertIsNone(self.resolver.resolve(None, "db.hp"))

    def test_a_numeric_string_is_accepted(self):
        """
        Evennia attributes are whatever was assigned, and `"50"` out of a parsed
        command is common enough that refusing it would look like a bug in
        Aetos.

        """
        self.assertEqual(self.resolver.resolve_number(_Character(hp="50"), "db.hp"), 50)
        self.assertEqual(self.resolver.resolve_number(_Character(hp="2.5"), "db.hp"), 2.5)

    def test_a_flag_is_not_a_number(self):
        """
        `db.is_bleeding = True` bound to a resource meant something, and a bar
        reading "1 / 1" is not it.

        """
        self.assertIsNone(self.resolver.resolve_number(_Character(hp=True), "db.hp"))

    def test_text_that_is_not_a_number_is_not_guessed_at(self):
        self.assertIsNone(self.resolver.resolve_number(_Character(hp="healthy"), "db.hp"))


class TestTheErrorsAreForSomebodyWhoDidNotWantToWritePython(TestCase):
    """
    `AETOS_BINDINGS` exists for a developer who did not want to write a provider
    class. Telling them their value "did not match `^db\\.(?!__)[A-Za-z_]...`"
    is telling them to go and find somebody who did.

    Each case below is *recognised* rather than merely rejected, because "you
    cannot call a method here" is a fix and "invalid" is a puzzle.

    """

    def _refusal(self, declaration):
        with self.assertRaises(bindings.AetosBindingError) as caught:
            bindings.validate_bindings(declaration, error_class=bindings.AetosBindingError)
        return str(caught.exception)

    def test_a_method_call_says_bindings_never_call_anything(self):
        message = self._refusal({"resources": {"h": {"label": "H", "value": "db.hp()"}}})
        self.assertIn("method call", message)
        self.assertIn("AETOS_PROVIDERS", message)

    def test_indexing_names_the_alternative_that_works(self):
        message = self._refusal({"resources": {"h": {"label": "H", "value": "db.stats[0]"}}})
        self.assertIn("db.stats.hp", message)

    def test_a_missing_db_prefix_explains_what_db_is(self):
        message = self._refusal({"resources": {"h": {"label": "H", "value": "hp"}}})
        self.assertIn("character.db.hp", message)

    def test_arithmetic_says_where_computed_values_belong(self):
        message = self._refusal({"resources": {"h": {"label": "H", "value": "db.hp + 1"}}})
        self.assertIn("AETOS_PROVIDERS", message)

    def test_a_dunder_is_named_as_a_python_internal(self):
        message = self._refusal({"resources": {"h": {"label": "H", "value": "db.__class__"}}})
        self.assertIn("Python internal", message)

    def test_a_message_never_shows_a_regular_expression(self):
        for expression in schema.REJECTED_EXPRESSIONS:
            declaration = {"resources": {"h": {"label": "H", "value": expression}}}
            message = self._refusal(declaration)
            for fragment in ("(?!", "[A-Za-z", "\\w", "^db"):
                self.assertNotIn(fragment, message, "%r produced a regex" % expression)

    def test_every_message_names_the_slot_and_the_key(self):
        message = self._refusal({"resources": {"vitality": {"label": "V", "value": "nope"}}})
        self.assertIn("'resources'", message)
        self.assertIn("'vitality'", message)


class TestTheDeclarationIsValidatedAsAWhole(TestCase):
    """
    One bad entry refuses the lot.

    A game that misspelled one binding and shipped the other three has a client
    that half works, and "half of my bars appeared" is much harder to debug than
    "Aetos refused it and told me which line".

    """

    def _refuse(self, declaration):
        with self.assertRaises(bindings.AetosBindingError):
            bindings.validate_bindings(declaration, error_class=bindings.AetosBindingError)

    def test_a_missing_required_field_is_refused(self):
        self._refuse({"resources": {"h": {"value": "db.hp"}}})
        self._refuse({"resources": {"h": {"label": "Health"}}})

    def test_an_unknown_field_is_refused_rather_than_ignored(self):
        """
        A typo in a field name is silent otherwise: the game believes it set a
        maximum and the bar is unbounded.

        """
        self._refuse({"resources": {"h": {"label": "H", "value": "db.hp", "maxium": "db.m"}}})

    def test_an_unknown_slot_is_refused(self):
        self._refuse({"stats": {"h": {"label": "H", "value": "db.hp"}}})

    def test_the_setting_must_be_a_dict(self):
        self._refuse([{"resources": {}}])

    def test_absent_is_not_an_error(self):
        """
        The zero-configuration client is the whole progressive-enhancement
        premise.

        """
        self.assertEqual(bindings.validate_bindings(None), {})

    def test_a_label_may_be_any_text_including_something_that_looks_like_a_path(self):
        """
        Only the expression fields are parsed as expressions. A game that wrote
        `"label": "db.hp"` meant the words -- an odd label, but theirs.

        """
        validated = bindings.validate_bindings(
            {"resources": {"h": {"label": "db.hp", "value": "db.hp"}}},
            error_class=bindings.AetosBindingError,
        )
        self.assertEqual(validated["resources"]["h"]["label"], "db.hp")


class CustomResourceProvider(base.AetosResourceProvider):
    """
    A hand-written provider, for the precedence tests.

    Module level rather than nested inside the test class, because
    `AETOS_PROVIDERS` takes a dotted path and `class_from_module` cannot reach a
    class defined inside another class. That constraint applies to games too, so
    it is better for a test to trip over it here than for a developer to meet it
    in their own settings.

    """

    name = "custom"

    def get_resources(self, character):
        """
        Args:
            character (Object): Unused.

        Returns:
            list: One recognisable resource.

        """
        return [{"id": "custom", "label": "Custom", "value": 1}]


class TestPrecedence(TestCase):
    """
    custom > binding > default.

    Stated in one place, in the order somebody would guess: the more specific
    thing wins.

    """

    def test_a_provider_class_beats_a_binding_for_the_same_slot(self):
        """
        The case a developer mid-migration hits. Getting both, or getting the
        binding while they are still editing the class, would be a bad surprise
        either way.

        """
        path = "%s.%s" % (__name__, "CustomResourceProvider")
        with override_settings(AETOS_BINDINGS=HEALTH, AETOS_PROVIDERS={"resources": path}):
            self.assertEqual(providers.get_providers()["resources"].name, "custom")

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_PROVIDERS={})
    def test_a_binding_beats_the_default(self):
        self.assertIsInstance(
            providers.get_providers()["resources"], bound_providers.BoundResourceProvider
        )

    @override_settings(AETOS_PROVIDERS={})
    def test_no_binding_leaves_the_default_in_place(self):
        resolved = providers.get_providers()["resources"]
        self.assertNotIsInstance(resolved, bound_providers.BoundResourceProvider)
        self.assertEqual(resolved.get_resources(_Character(hp=1)), [])

    @override_settings(AETOS_BINDINGS={"resources": {}}, AETOS_PROVIDERS={})
    def test_an_empty_slot_binds_nothing(self):
        """
        A game that declared the key and deleted its entries has bound nothing.
        Counting it would switch a feature flag on for a widget with no rows.

        """
        self.assertEqual(bindings.bound_slots(), set())
        self.assertNotIsInstance(
            providers.get_providers()["resources"], bound_providers.BoundResourceProvider
        )

    @override_settings(
        AETOS_BINDINGS={"effects": {"x": {"label": "X", "value": "db.x"}}},
        AETOS_PROVIDERS={},
    )
    def test_a_slot_without_a_declarative_provider_falls_back(self):
        """
        A declarable slot with no provider yet gets the stock default rather
        than something half-built.

        This used `effects` as its example, because at D1 that slot really was
        declarable and unserved. D2 served all five, so the example had to go --
        and the *property* did not, because it is what makes adding the next
        slot safe: it can be declared and validated for as long as it takes to
        write its provider, and during that window a game gets the client it
        would have had anyway.

        Demonstrated by removing a row from the table rather than by finding a
        slot that happens to be missing, so the test cannot be quietly retired
        again by somebody filling a gap.

        """
        self.assertIn("effects", bindings.bound_slots())

        with mock.patch.dict(bound_providers.PROVIDERS, clear=False) as table:
            del table["effects"]
            self.assertIsNone(bindings.provider_for("effects"))
            resolved = providers.get_providers()["effects"]
            self.assertNotIsInstance(resolved, bound_providers.BoundEffectProvider)
            self.assertEqual(resolved.get_effects(_Character(x=1)), [])


class TestFeatureDerivation(TestCase):
    """
    A binding implies its capability -- and never argues with an explicit
    setting.

    """

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_FEATURES={"resources": False})
    def test_an_explicit_false_wins(self):
        """
        A game that declared bindings and then set the flag off is turning the
        widget off on purpose -- mid-migration, or behind a launch date. A
        helpful override would be Aetos arguing with it.

        """
        self.assertFalse(manifest.get_features()["resources"])

    @override_settings(AETOS_BINDINGS=HEALTH, AETOS_FEATURES={"map": True})
    def test_deriving_one_flag_does_not_disturb_another(self):
        features = manifest.get_features()
        self.assertTrue(features["resources"])
        self.assertTrue(features["map"])

    @override_settings(AETOS_FEATURES={})
    def test_nothing_is_derived_from_nothing(self):
        self.assertFalse(manifest.get_features()["resources"])

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_the_manifest_carries_the_derived_flag(self):
        """
        Through `build_manifest`, not just `get_features` -- the client reads
        the manifest, and a flag derived in a function nothing calls would be a
        feature that never appears.

        """
        self.assertTrue(manifest.build_manifest()["features"]["resources"])


class TestAMalformedSettingReachesTheDeveloperNotThePlayer(TestCase):
    """
    The one place a binding fails quietly, and the thing that makes that
    acceptable.

    """

    @override_settings(AETOS_BINDINGS={"resources": {"h": {"value": "db.hp()"}}})
    def test_a_bad_binding_does_not_break_a_login(self):
        """
        `bound_slots` swallows the error deliberately. A typo in settings.py
        must not turn into a failed connection for everybody playing.

        """
        self.assertEqual(bindings.bound_slots(), set())
        self.assertIsInstance(manifest.build_manifest(), dict)

    def test_the_startup_check_is_what_reports_it(self):
        """
        The trade above only works if the developer is told somewhere.

        """
        from evennia.contrib.base_systems.aetos_webclient import checks

        names = [name for name, _, _ in checks._setting_validators()]
        self.assertIn("AETOS_BINDINGS", names)

    @override_settings(AETOS_BINDINGS={"resources": {"h": {"value": "db.hp()"}}})
    def test_and_it_actually_fires(self):
        from evennia.contrib.base_systems.aetos_webclient import checks

        found = checks.check_settings_are_valid(None)
        self.assertTrue(
            any("AETOS_BINDINGS" in warning.msg for warning in found),
            "a malformed AETOS_BINDINGS produced no startup warning",
        )


class TestTheBoundProviderBehavesLikeAHandWrittenOne(TestCase):
    """
    The client must not be able to tell which route supplied the data.

    """

    def setUp(self):
        self.provider = bound_providers.BoundResourceProvider()

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_a_value_that_will_not_resolve_is_omitted_not_zeroed(self):
        """
        A bar reading 0 says "you are dead". A missing bar says "this is not
        available", and only one of those is true when the attribute does not
        exist yet.

        """
        self.assertEqual(self.provider.get_resources(_Character()), [])

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_a_missing_maximum_leaves_an_unbounded_counter(self):
        built = self.provider.get_resources(_Character(hp=42))
        self.assertEqual(built[0]["value"], 42)
        self.assertNotIn("maximum", built[0])

    @override_settings(
        AETOS_BINDINGS={
            "resources": {
                "zulu": {"label": "Z", "value": "db.z"},
                "alpha": {"label": "A", "value": "db.a"},
            }
        }
    )
    def test_the_declared_order_is_the_order_on_screen(self):
        """
        Python dicts keep insertion order, so settings.py order is the one thing
        a developer controls here without another field. Sorting would take it
        away for no reason.

        """
        built = self.provider.get_resources(_Character(z=1, a=2))
        self.assertEqual([resource["id"] for resource in built], ["zulu", "alpha"])

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_it_describes_which_keys_it_serves(self):
        """
        "resources (bindings)" alone leaves a developer wondering which of their
        declarations are live.

        """
        described = self.provider.describe()
        self.assertEqual(described["bound"], ["health"])

    @override_settings(AETOS_BINDINGS=HEALTH)
    def test_it_never_reports_the_expressions_or_the_values(self):
        """
        The inspector payload reaches a client. Where a game keeps its data is
        not something a player needs, and neither is what is in it.

        """
        described = str(self.provider.describe())
        self.assertNotIn("db.hp", described)

    @override_settings(AETOS_BINDINGS={"resources": {"h": {"value": "db.hp()", "label": "H"}}})
    def test_a_malformed_declaration_yields_no_resources_rather_than_raising(self):
        """
        This provider runs inside a websocket handler. Losing one widget beats
        losing the session.

        """
        self.assertEqual(self.provider.get_resources(_Character(hp=1)), [])


class TestTheSchemaMovedForAReason(TestCase):
    """
    D0 put the grammar in `discovery/`, which is a development-time tool. D1
    moved it into `bindings/`, which is runtime.

    Left where it was, the live client would have imported a source scanner in
    order to read a setting. Easy to fix now, permanent in a year.

    """

    def test_the_grammar_lives_with_the_resolver(self):
        self.assertTrue(hasattr(bindings, "is_valid_expression"))

    def test_discovery_imports_it_rather_than_defining_its_own(self):
        from evennia.contrib.base_systems.aetos_webclient import discovery

        self.assertIs(discovery.is_valid_expression, bindings.is_valid_expression)

    def test_nothing_in_bindings_imports_discovery(self):
        """
        The dependency runs one way. A game in production never loads the source
        scanner to read a setting.

        """
        import ast
        from pathlib import Path

        from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

        package = Path(AETOS_STATIC_DIR).parent / "bindings"
        for path in sorted(package.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                for module in modules:
                    self.assertNotIn("discovery", module, "%s imports discovery" % path.name)


class TestTheGrammarIsAWhitelist(TestCase):
    """
    The security boundary of the whole D-track.

    `AETOS_BINDINGS` is written by the game's own developer, so this is not a
    defence against a hostile author. It is a defence against the resolver
    becoming an expression evaluator, which is what happens the first time
    somebody adds "just method calls" to make one game work.

    """

    def test_the_two_allowed_forms_are_allowed(self):
        self.assertTrue(schema.is_valid_expression("db.hp"))
        self.assertTrue(schema.is_valid_expression("db.stats.hp"))
        self.assertTrue(schema.is_valid_expression("db._private"))

    def test_every_rejected_form_is_rejected(self):
        """
        Addendum B.59's list, each with its own entry. A resolver that quietly
        accepts one of these has reintroduced `eval` with extra steps, and the
        failure would not show up in any output.

        """
        for expression, reason in schema.REJECTED_EXPRESSIONS.items():
            self.assertFalse(
                schema.is_valid_expression(expression),
                "%r (%s) was accepted" % (expression, reason),
            )

    def test_the_pattern_is_anchored_at_both_ends(self):
        """
        An unanchored pattern matches the `db.hp` inside `db.hp.__class__` and
        reports the whole string as valid. That is the mistake this grammar
        exists to prevent, made in the grammar itself.

        """
        self.assertFalse(schema.is_valid_expression("db.hp.__class__"))
        self.assertFalse(schema.is_valid_expression("xdb.hp"))
        self.assertFalse(schema.is_valid_expression("db.hp.mp.sp"))

    def test_a_non_string_is_refused_rather_than_coerced(self):
        for value in (5, None, ["db.hp"], {"value": "db.hp"}):
            self.assertFalse(schema.is_valid_expression(value))

    def test_parsing_an_invalid_expression_raises(self):
        """
        Rather than returning a half-parsed result. A caller that ignores the
        return value of a parse is the caller this exists to stop.

        """
        with self.assertRaises(ValueError):
            schema.expression_parts("db.hp()")

    def test_parsing_returns_the_attribute_names(self):
        self.assertEqual(schema.expression_parts("db.hp"), ("hp",))
        self.assertEqual(schema.expression_parts("db.stats.hp"), ("stats", "hp"))

    def test_every_slot_the_schema_names_has_fields_declared(self):
        for slot in schema.BINDING_SLOTS:
            self.assertIn(slot, schema.BINDING_FIELDS)
            self.assertTrue(schema.BINDING_FIELDS[slot]["required"])

    def test_it_records_what_is_deliberately_not_expressible(self):
        """
        The reasoning, not just the rule. The next person asked to add "just
        method calls" for one game needs the argument against it, and a
        rejection table does not carry one.

        """
        from pathlib import Path

        from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

        source = (Path(AETOS_STATIC_DIR).parent / "bindings" / "schema.py").read_text(
            encoding="utf-8"
        )
        for excluded in ("Method calls", "Indexing", "Arithmetic", "Dunders", "Statements"):
            self.assertIn(excluded, source)
