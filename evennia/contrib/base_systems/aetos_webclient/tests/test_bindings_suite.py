"""
Tests for D2, the declarative provider suite.

D2's gate: **each provider emits exactly the payload a hand-written one would,
through the same normalisers. The client must be unable to tell which
integration path supplied the data.**

That is not a nice-to-have, it is the reason the D-track can exist at all. M16
routed every slot through `character_state` and `resources` precisely so that
there would be one shape; a declarative path that produced a *nearly* identical
dict would be a second code path with a second set of bugs, and the first place
they would show is the accessibility surface -- thresholds, announcements and
labels are all computed from the normalised shape.

So `TestTheClientCannotTell` builds each payload twice, once from a binding and
once from a hand-written provider with the same data, and requires the two to be
equal *after normalisation*. Equality after the normaliser is the honest test:
before it, two providers may legitimately differ in what they omit.

WHAT EACH SLOT'S DECLARATION LOOKS LIKE is a design decision per slot, and the
interesting ones are recorded here as tests rather than left in a docstring:
an empty equipment slot is kept while an absent resource is dropped; a target
with no name is no target; zero is not an active effect; and an action is
offered but never made legal.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import character_state, providers
from evennia.contrib.base_systems.aetos_webclient.bindings import bound_providers
from evennia.contrib.base_systems.aetos_webclient.providers import base
from evennia.contrib.base_systems.aetos_webclient.tests.test_bindings import _Character

EQUIPMENT = {
    "equipment": {
        "weapon": {"label": "Weapon", "value": "db.gear.weapon"},
        "head": {"label": "Head", "value": "db.gear.head"},
    }
}

EFFECTS = {
    "effects": {
        "poison": {
            "label": "Poisoned",
            "value": "db.poison",
            "remaining": "db.poison_left",
            "kind": "harmful",
        },
        "blessed": {"label": "Blessed", "value": "db.blessed"},
    }
}

TARGET = {
    "target": {
        "name": {"label": "Target", "value": "db.target_name"},
        "health": {"label": "Health", "value": "db.target_hp", "maximum": "db.target_max"},
    }
}

ACTIONS = {
    "actions": {
        "attack": {"label": "Attack", "command": "attack {target}"},
        "flee": {"label": "Flee", "command": "flee"},
    }
}


class _Target:
    """A stand-in for an entity a context menu was opened on."""

    def __init__(self, name="a rat"):
        self.name = name

    def get_display_name(self, looker):
        return self.name


class TestTheClientCannotTell(TestCase):
    """
    D2's gate, one slot at a time.

    Each payload is built twice -- from a binding and from a hand-written
    provider carrying the same data -- and compared *after* the normaliser. A
    difference here is a second code path into the client, which is the thing
    the provider architecture exists to prevent.

    """

    @override_settings(AETOS_BINDINGS=EQUIPMENT)
    def test_equipment(self):
        character = _Character(gear={"weapon": "a rusty sword", "head": None})

        bound = bound_providers.BoundEquipmentProvider().get_equipment(character)
        handwritten = [
            {
                "slot": "weapon",
                "label": "Weapon",
                "item": {"id": "weapon", "name": "a rusty sword"},
            },
            {"slot": "head", "label": "Head", "item": None},
        ]

        expected = character_state.normalize_equipment(handwritten)
        # Guards the comparison. Two empty lists are equal, and a gate that
        # passes on nothing is the same defect as a regex that matches nothing.
        self.assertEqual(len(expected), 2)
        self.assertEqual(character_state.normalize_equipment(bound), expected)

    @override_settings(AETOS_BINDINGS=EFFECTS)
    def test_effects(self):
        character = _Character(poison=True, poison_left=30, blessed=False)

        bound = bound_providers.BoundEffectProvider().get_effects(character)
        handwritten = [
            {"id": "poison", "label": "Poisoned", "kind": "harmful", "remaining": 30},
        ]

        expected = character_state.normalize_effects(handwritten)
        self.assertEqual(len(expected), 1)
        self.assertEqual(character_state.normalize_effects(bound), expected)

    @override_settings(AETOS_BINDINGS=TARGET)
    def test_target(self):
        character = _Character(target_name="a rat", target_hp=4, target_max=10)

        bound = bound_providers.BoundTargetProvider().get_target(character)
        handwritten = {
            "id": "name",
            "name": "a rat",
            "resources": [{"id": "health", "label": "Health", "value": 4, "maximum": 10}],
        }

        expected = character_state.normalize_target(handwritten)
        self.assertEqual(expected.get("name"), "a rat")
        self.assertEqual(len(expected["resources"]), 1)
        self.assertEqual(character_state.normalize_target(bound), expected)

    @override_settings(AETOS_BINDINGS=ACTIONS)
    def test_actions(self):
        """
        Actions have no normaliser of their own -- they are a label and a
        command -- so this compares the payload directly, which is what the
        client receives.

        """
        built = bound_providers.BoundActionProvider().get_actions(_Character(), _Target())
        self.assertEqual(
            built,
            [
                {"label": "Attack", "command": "attack a rat"},
                {"label": "Flee", "command": "flee"},
            ],
        )


class TestEachSlotsOwnRule(TestCase):
    """
    The decisions that are not shared, and would be wrong if they were.

    """

    @override_settings(AETOS_BINDINGS=EQUIPMENT)
    def test_an_empty_equipment_slot_is_kept(self):
        """
        The opposite of the resources rule, on purpose. "Nothing on your head"
        is information; dropping empty slots would make a bare character
        indistinguishable from a game with no equipment at all.

        """
        built = bound_providers.BoundEquipmentProvider().get_equipment(
            _Character(gear={"weapon": "a sword"})
        )
        self.assertEqual([slot["slot"] for slot in built], ["weapon", "head"])
        self.assertIsNone(built[1]["item"])

    @override_settings(AETOS_BINDINGS={"resources": {"hp": {"label": "HP", "value": "db.hp"}}})
    def test_an_absent_resource_is_dropped(self):
        """
        And the other half of that pair. A resource that will not resolve is not
        empty, it is absent -- the game never had that number for this
        character, and a bar reading 0 would say something false.

        """
        self.assertEqual(bound_providers.BoundResourceProvider().get_resources(_Character()), [])

    @override_settings(AETOS_BINDINGS=EFFECTS)
    def test_zero_is_not_an_active_effect(self):
        """
        A countdown that has reached 0 has expired. An effect list that goes on
        showing it is one a player learns to distrust.

        """
        built = bound_providers.BoundEffectProvider().get_effects(_Character(poison=0, blessed=1))
        self.assertEqual([effect["id"] for effect in built], ["blessed"])

    @override_settings(AETOS_BINDINGS=EFFECTS)
    def test_an_effect_is_active_whether_it_is_a_flag_or_a_count(self):
        """
        `db.poisoned = True` and `db.poison_stacks = 3` both mean poisoned. A
        game should not have to pick one to suit Aetos.

        """
        for value in (True, 3, "yes", 0.5):
            with self.subTest(value=value):
                built = bound_providers.BoundEffectProvider().get_effects(_Character(poison=value))
                self.assertEqual([effect["id"] for effect in built], ["poison"])

    @override_settings(AETOS_BINDINGS=TARGET)
    def test_a_target_with_no_name_is_no_target(self):
        """
        An empty dict is what "nothing is targeted" looks like everywhere else,
        so the widget hides itself with no special case.

        """
        built = bound_providers.BoundTargetProvider().get_target(
            _Character(target_hp=4, target_max=10)
        )
        self.assertEqual(built, {})

    @override_settings(AETOS_BINDINGS=TARGET)
    def test_a_target_is_never_returned_with_bars_and_no_name(self):
        """
        Which would be worse than returning nothing: a player would see a health
        bar belonging to something the client could not name.

        """
        built = bound_providers.BoundTargetProvider().get_target(_Character(target_name=""))
        self.assertEqual(built, {})

    @override_settings(AETOS_BINDINGS={"target": {"health": {"label": "H", "value": "db.hp"}}})
    def test_a_target_declaration_with_no_name_entry_yields_nothing(self):
        self.assertEqual(bound_providers.BoundTargetProvider().get_target(_Character(hp=5)), {})

    @override_settings(AETOS_BINDINGS=ACTIONS)
    def test_no_actions_are_offered_without_a_target(self):
        """
        These are *context* actions. A declaration cannot know what a game's
        targetless commands are.

        """
        self.assertEqual(bound_providers.BoundActionProvider().get_actions(_Character(), None), [])

    @override_settings(AETOS_BINDINGS=ACTIONS)
    def test_an_entity_that_cannot_name_itself_costs_the_menu_not_the_session(self):
        class _Broken:
            def get_display_name(self, looker):
                raise RuntimeError("mid-deletion")

        self.assertEqual(
            bound_providers.BoundActionProvider().get_actions(_Character(), _Broken()), []
        )


class TestActionsAreOfferedNotGranted(TestCase):
    """
    Server authority, blueprint 2.4. Nothing a binding offers may bypass a
    command, a lock, a cooldown or a permission.

    """

    @override_settings(AETOS_BINDINGS=ACTIONS)
    def test_an_action_is_an_ordinary_command_string(self):
        """
        Not a protocol message, not a server call. What is sent is what a player
        could have typed, so the server decides in exactly the same way.

        """
        built = bound_providers.BoundActionProvider().get_actions(_Character(), _Target())
        for action in built:
            self.assertIsInstance(action["command"], str)
            self.assertEqual(set(action) - {"kind"}, {"label", "command"})

    def test_the_command_template_takes_one_placeholder_and_no_expressions(self):
        """
        A second placeholder would be the first step towards a template language
        living in settings.py, and the D-track's argument is that the first step
        is the one to refuse.

        """
        self.assertEqual(bound_providers.BoundActionProvider.TARGET_PLACEHOLDER, "{target}")

    @override_settings(AETOS_BINDINGS=ACTIONS)
    def test_a_command_is_never_resolved_as_a_binding_expression(self):
        """
        `command` is not in `EXPRESSION_FIELDS`, so `"command": "db.hp"` is the
        literal words -- an odd command, but the game's own. Reading it as an
        expression would make a settings string mean two different things
        depending on its contents.

        """
        from evennia.contrib.base_systems.aetos_webclient.bindings import schema

        self.assertNotIn("command", schema.EXPRESSION_FIELDS)


class TestThePrecedenceAndDerivationRulesHoldForEverySlot(TestCase):
    """
    D1 established both against `resources`. A rule proved on one slot and
    applied to five is a rule that has been tested once.

    """

    ALL_FIVE = {
        "resources": {"hp": {"label": "HP", "value": "db.hp"}},
        "equipment": {"weapon": {"label": "Weapon", "value": "db.weapon"}},
        "target": {"name": {"label": "Target", "value": "db.t"}},
        "effects": {"poison": {"label": "Poisoned", "value": "db.poison"}},
        "actions": {"attack": {"label": "Attack", "command": "attack {target}"}},
    }

    @override_settings(AETOS_BINDINGS=ALL_FIVE, AETOS_PROVIDERS={})
    def test_every_slot_is_served_by_its_bound_provider(self):
        resolved = providers.get_providers()
        for slot in self.ALL_FIVE:
            with self.subTest(slot=slot):
                self.assertIsInstance(resolved[slot], bound_providers.PROVIDERS[slot])

    @override_settings(AETOS_BINDINGS=ALL_FIVE)
    def test_every_declared_slot_derives_its_feature_flag(self):
        from evennia.contrib.base_systems.aetos_webclient import manifest

        features = manifest.get_features()
        for slot in self.ALL_FIVE:
            with self.subTest(slot=slot):
                self.assertTrue(features[slot], "%s did not derive its flag" % slot)

    @override_settings(AETOS_BINDINGS=ALL_FIVE, AETOS_FEATURES={"effects": False})
    def test_an_explicit_false_still_wins_on_any_slot(self):
        from evennia.contrib.base_systems.aetos_webclient import manifest

        features = manifest.get_features()
        self.assertFalse(features["effects"])
        self.assertTrue(features["equipment"])

    def test_a_provider_class_still_beats_a_binding_on_any_slot(self):
        path = "%s.%s" % (__name__, "CustomEquipmentProvider")
        with override_settings(AETOS_BINDINGS=self.ALL_FIVE, AETOS_PROVIDERS={"equipment": path}):
            resolved = providers.get_providers()
            self.assertEqual(resolved["equipment"].name, "custom equipment")
            # ...and the slots it did not claim are still bound.
            self.assertIsInstance(resolved["effects"], bound_providers.BoundEffectProvider)

    def test_the_table_covers_every_slot_the_schema_allows(self):
        """
        The guard that would have caught D1 shipping five schema slots and one
        provider, if D1 had claimed to serve them all. It did not, and said so;
        D2 is where the claim becomes true.

        """
        from evennia.contrib.base_systems.aetos_webclient.bindings import schema

        self.assertEqual(set(bound_providers.PROVIDERS), set(schema.BINDING_SLOTS))


class CustomEquipmentProvider(base.AetosEquipmentProvider):
    """A hand-written provider, for the precedence test above."""

    name = "custom equipment"

    def get_equipment(self, character):
        """
        Args:
            character (Object): Unused.

        Returns:
            list: One recognisable slot.

        """
        return [{"slot": "hand", "label": "Hand", "item": None}]


class TestNoFieldIsAcceptedThatNothingReads(TestCase):
    """
    Every optional field the schema allows must reach the payload, or it is a
    setting that appears to work and changes nothing -- the defect this project
    keeps finding, and one a schema makes very easy to introduce.

    """

    def test_every_optional_field_is_read_somewhere(self):
        from pathlib import Path

        from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR
        from evennia.contrib.base_systems.aetos_webclient.bindings import schema

        source = (Path(AETOS_STATIC_DIR).parent / "bindings" / "bound_providers.py").read_text(
            encoding="utf-8"
        )

        for slot, fields in schema.BINDING_FIELDS.items():
            for field in fields["optional"]:
                with self.subTest(slot=slot, field=field):
                    self.assertIn(
                        '"%s"' % field,
                        source,
                        "AETOS_BINDINGS accepts %r on a %s binding and nothing reads it"
                        % (field, slot),
                    )

    @override_settings(
        AETOS_BINDINGS={
            "effects": {
                "burn": {
                    "label": "Burning",
                    "value": "db.burn",
                    "kind": "harmful",
                    "description": "Taking damage each turn.",
                    "remaining": "db.burn_left",
                    "duration": "db.burn_total",
                }
            }
        }
    )
    def test_a_fully_declared_effect_carries_all_of_it(self):
        built = bound_providers.BoundEffectProvider().get_effects(
            _Character(burn=1, burn_left=6, burn_total=10)
        )
        self.assertEqual(
            built[0],
            {
                "id": "burn",
                "label": "Burning",
                "kind": "harmful",
                "description": "Taking damage each turn.",
                "remaining": 6,
                "duration": 10,
            },
        )

    @override_settings(
        AETOS_BINDINGS={
            "equipment": {
                "weapon": {
                    "label": "Weapon",
                    "value": "db.weapon",
                    "kind": "sword",
                    "category": "melee",
                }
            }
        }
    )
    def test_a_fully_declared_equipment_slot_carries_all_of_it(self):
        built = bound_providers.BoundEquipmentProvider().get_equipment(
            _Character(weapon="a rusty sword")
        )
        self.assertEqual(built[0]["item"]["kind"], "sword")
        self.assertEqual(built[0]["item"]["category"], "melee")
