"""
Tests for inventory, equipment, target and effects.

The through-line: a provider is game-supplied code, so nothing it returns is
trusted, and one bad entry costs that entry rather than the widget.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import (
    character_state,
    providers,
    state,
)
from evennia.contrib.base_systems.aetos_webclient.providers import base, defaults
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest


class TestItemNormalization(TestCase):
    """An item needs an id to be acted on and a name to be shown."""

    def test_a_valid_item_survives(self):
        item = character_state.normalize_item({"id": "7", "name": "lamp"})
        self.assertEqual(item["id"], "7")
        self.assertEqual(item["name"], "lamp")

    def test_an_item_without_an_id_is_dropped(self):
        self.assertIsNone(character_state.normalize_item({"name": "lamp"}))

    def test_an_item_without_a_name_is_dropped(self):
        self.assertIsNone(character_state.normalize_item({"id": "7"}))

    def test_a_non_dict_is_dropped(self):
        for junk in ("lamp", 7, None, [], object()):
            self.assertIsNone(character_state.normalize_item(junk))

    def test_markup_is_split_into_plain_and_display(self):
        """
        The plain form may end up in a command, so it must be exactly what a
        player would type; the display form keeps the colour the game chose.

        """
        item = character_state.normalize_item({"id": "7", "name": "|ybrass lamp|n"})
        self.assertEqual(item["name"], "brass lamp")
        self.assertIn("brass lamp", item["display"])
        self.assertNotIn("|y", item["display"])

    def test_a_quantity_of_zero_is_kept(self):
        """Zero is a real answer -- "you have 0 arrows" is worth showing."""
        item = character_state.normalize_item({"id": "7", "name": "arrow", "quantity": 0})
        self.assertEqual(item["quantity"], 0)

    def test_a_negative_quantity_is_dropped(self):
        item = character_state.normalize_item({"id": "7", "name": "arrow", "quantity": -3})
        self.assertNotIn("quantity", item)

    def test_a_nonsense_quantity_is_dropped_not_fatal(self):
        item = character_state.normalize_item({"id": "7", "name": "arrow", "quantity": "lots"})
        self.assertNotIn("quantity", item)
        self.assertEqual(item["name"], "arrow")

    def test_a_long_name_is_bounded(self):
        item = character_state.normalize_item({"id": "7", "name": "x" * 5000})
        self.assertLessEqual(len(item["name"]), character_state.MAX_LABEL_LENGTH)


class TestInventoryNormalization(TestCase):
    def test_one_bad_item_does_not_cost_the_others(self):
        items = character_state.normalize_inventory(
            [{"id": "1", "name": "a"}, {"name": "broken"}, {"id": "3", "name": "c"}]
        )
        self.assertEqual([item["name"] for item in items], ["a", "c"])

    def test_a_non_list_yields_nothing_rather_than_raising(self):
        for junk in (None, "items", 42, {"id": "1"}):
            self.assertEqual(character_state.normalize_inventory(junk), [])

    def test_the_list_is_bounded(self):
        raw = [{"id": str(i), "name": "item"} for i in range(5000)]
        self.assertEqual(
            len(character_state.normalize_inventory(raw)), character_state.MAX_INVENTORY_ITEMS
        )


class TestEquipmentNormalization(TestCase):
    """
    Slots are whatever the game calls them. Aetos names none of them.

    """

    def test_an_empty_slot_is_kept(self):
        """
        "Nothing on your head" is information a player needs. Dropping empty
        slots would make a bare character look like a game with no equipment.

        """
        slots = character_state.normalize_equipment([{"slot": "head", "label": "Head"}])
        self.assertEqual(len(slots), 1)
        self.assertIsNone(slots[0]["item"])

    def test_slot_order_is_the_providers(self):
        """Only the game knows whether its slots read head-to-toe or by hand."""
        raw = [{"slot": name} for name in ("boots", "head", "belt")]
        slots = character_state.normalize_equipment(raw)
        self.assertEqual([slot["slot"] for slot in slots], ["boots", "head", "belt"])

    def test_a_missing_label_falls_back_to_the_slot_name(self):
        slots = character_state.normalize_equipment([{"slot": "head"}])
        self.assertEqual(slots[0]["label"], "head")

    def test_a_duplicate_slot_is_dropped(self):
        """
        Two slots with the same id would render twice and the player could not
        tell which one was real.

        """
        slots = character_state.normalize_equipment(
            [
                {"slot": "head", "item": {"id": "1", "name": "helm"}},
                {"slot": "head", "item": {"id": "2", "name": "hat"}},
            ]
        )
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0]["item"]["name"], "helm")

    def test_a_slot_with_a_broken_item_becomes_an_empty_slot(self):
        """Better an honestly empty slot than a dropped one."""
        slots = character_state.normalize_equipment([{"slot": "head", "item": {"name": "helm"}}])
        self.assertEqual(len(slots), 1)
        self.assertIsNone(slots[0]["item"])

    def test_a_slot_without_an_id_is_dropped(self):
        self.assertEqual(character_state.normalize_equipment([{"label": "Head"}]), [])


class TestEffectNormalization(TestCase):
    def test_a_valid_effect_survives(self):
        effect = character_state.normalize_effect({"id": "poison", "label": "Poisoned"})
        self.assertEqual(effect["label"], "Poisoned")

    def test_an_unknown_kind_falls_back_rather_than_dropping_the_effect(self):
        """
        Tone is advisory. The label carries the meaning, so an unrecognised tone
        is no reason to hide the fact that a player is poisoned.

        """
        effect = character_state.normalize_effect(
            {"id": "p", "label": "Poisoned", "kind": "extremely bad"}
        )
        self.assertEqual(effect["kind"], character_state.DEFAULT_EFFECT_KIND)

    def test_kind_is_case_insensitive(self):
        effect = character_state.normalize_effect({"id": "p", "label": "P", "kind": "HARMFUL"})
        self.assertEqual(effect["kind"], "harmful")

    def test_a_single_stack_is_omitted(self):
        """Sending it would make every widget render a redundant "x1"."""
        effect = character_state.normalize_effect({"id": "p", "label": "P", "stacks": 1})
        self.assertNotIn("stacks", effect)

    def test_multiple_stacks_are_kept(self):
        effect = character_state.normalize_effect({"id": "p", "label": "P", "stacks": 4})
        self.assertEqual(effect["stacks"], 4)

    def test_infinite_remaining_is_dropped(self):
        """A countdown that never resolves is worse than no countdown."""
        effect = character_state.normalize_effect(
            {"id": "p", "label": "P", "remaining": float("inf")}
        )
        self.assertNotIn("remaining", effect)

    def test_nan_remaining_is_dropped(self):
        effect = character_state.normalize_effect(
            {"id": "p", "label": "P", "remaining": float("nan")}
        )
        self.assertNotIn("remaining", effect)

    def test_negative_remaining_is_clamped_to_zero(self):
        effect = character_state.normalize_effect({"id": "p", "label": "P", "remaining": -5})
        self.assertEqual(effect["remaining"], 0.0)

    def test_zero_remaining_is_kept(self):
        """
        Zero means "the server said none left", which is different from absent.
        The client shows it as expiring and waits for the server to confirm.

        """
        effect = character_state.normalize_effect({"id": "p", "label": "P", "remaining": 0})
        self.assertEqual(effect["remaining"], 0.0)

    def test_remaining_is_a_duration_not_a_timestamp(self):
        """
        The player's clock may be minutes off the server's, so an absolute time
        would be silently wrong for them. Sixty seconds stays sixty seconds.

        """
        effect = character_state.normalize_effect({"id": "p", "label": "P", "remaining": 60})
        self.assertEqual(effect["remaining"], 60.0)

    def test_duplicate_ids_are_collapsed(self):
        effects = character_state.normalize_effects(
            [{"id": "p", "label": "First"}, {"id": "p", "label": "Second"}]
        )
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["label"], "First")

    def test_the_list_is_bounded(self):
        raw = [{"id": str(i), "label": "e"} for i in range(500)]
        self.assertEqual(len(character_state.normalize_effects(raw)), character_state.MAX_EFFECTS)


class TestTargetNormalization(TestCase):
    def test_no_target_is_an_empty_dict(self):
        for junk in ({}, None, [], "nobody"):
            self.assertEqual(character_state.normalize_target(junk), {})

    def test_a_target_without_a_name_is_no_target(self):
        self.assertEqual(character_state.normalize_target({"id": "5"}), {})

    def test_target_resources_use_the_same_normalizer_as_the_players_own(self):
        """
        So a target's health bar and the player's cannot disagree about
        thresholds or rounding. Learning to read one teaches the other.

        """
        target = character_state.normalize_target(
            {
                "id": "5",
                "name": "goblin",
                "resources": [{"id": "hp", "label": "Health", "value": 3, "maximum": 10}],
            }
        )
        self.assertEqual(target["resources"][0]["value"], 3)
        self.assertEqual(target["resources"][0]["maximum"], 10)

    def test_a_broken_resource_does_not_cost_the_target(self):
        target = character_state.normalize_target(
            {"id": "5", "name": "goblin", "resources": "not a list"}
        )
        self.assertEqual(target["name"], "goblin")
        self.assertEqual(target["resources"], [])

    def test_target_effects_are_capped_lower_than_the_players_own(self):
        """
        A target panel is a glance, not a full status screen.

        """
        raw = [{"id": str(i), "label": "e"} for i in range(200)]
        target = character_state.normalize_target({"id": "5", "name": "g", "effects": raw})
        self.assertEqual(len(target["effects"]), character_state.MAX_TARGET_EFFECTS)

    def test_the_games_relationship_is_kept_separate_from_the_players_tags(self):
        """
        One is authoritative, the other is a private reminder that never leaves
        the browser. They arrive by entirely different routes and must not be
        confused.

        """
        target = character_state.normalize_target(
            {"id": "5", "name": "goblin", "relationship": "hostile"}
        )
        self.assertEqual(target["relationship"], "hostile")


class TestProviderSlots(TestCase):
    """
    Which of the four gets a default, and why.

    """

    def test_all_four_slots_are_registered(self):
        for slot in ("inventory", "equipment", "target", "effects"):
            self.assertIn(slot, providers.PROVIDER_SLOTS)
            self.assertIn(slot, providers.DEFAULT_PROVIDERS)

    def test_inventory_has_a_real_default(self):
        """
        `contents` is a stock Evennia concept, so carrying things is not a genre
        assumption and a pristine game gets an inventory widget for free.

        """
        self.assertIs(providers.DEFAULT_PROVIDERS["inventory"], defaults.DefaultInventoryProvider)

    def test_equipment_target_and_effects_stay_inert(self):
        """
        Evennia models none of them. Inventing slots or a current target would be
        exactly the genre assumption this project forbids -- the same reason
        resources have no default.

        """
        self.assertIs(providers.DEFAULT_PROVIDERS["equipment"], base.AetosEquipmentProvider)
        self.assertIs(providers.DEFAULT_PROVIDERS["target"], base.AetosTargetProvider)
        self.assertIs(providers.DEFAULT_PROVIDERS["effects"], base.AetosEffectProvider)

    def test_the_inert_defaults_return_empty(self):
        self.assertEqual(base.AetosEquipmentProvider().get_equipment(None), [])
        self.assertEqual(base.AetosTargetProvider().get_target(None), {})
        self.assertEqual(base.AetosEffectProvider().get_effects(None), [])


class BrokenProvider(base.AetosInventoryProvider):
    """A provider that raises, as third-party code sometimes does."""

    def get_inventory(self, character):
        raise RuntimeError("this provider is broken")


class LyingProvider(base.AetosEffectProvider):
    """A provider returning the wrong type entirely."""

    def get_effects(self, character):
        return "not a list at all"


class TestBuildSyncContainsFailures(BaseEvenniaTest):
    """
    A provider is game code running inside a websocket handler.

    Losing one widget beats losing the session, so every one of these must
    produce a usable sync rather than an exception.

    """

    def _providers(self, **overrides):
        resolved = {
            "resources": base.AetosResourceProvider(),
            "entities": defaults.DefaultEntityProvider(),
            "actions": defaults.DefaultActionProvider(),
            "map": defaults.DefaultMapProvider(),
            "inventory": defaults.DefaultInventoryProvider(),
            "equipment": base.AetosEquipmentProvider(),
            "target": base.AetosTargetProvider(),
            "effects": base.AetosEffectProvider(),
        }
        resolved.update(overrides)
        return resolved

    def test_the_four_sections_are_always_present(self):
        """
        The client relies on the shape at protocol v1, so a game exposing none of
        this still gets the keys.

        """
        payload = state.build_sync(self.char1, self._providers())
        self.assertEqual(payload["inventory"], {"items": []})
        self.assertEqual(payload["equipment"], {"slots": []})
        self.assertEqual(payload["effects"], {"items": []})
        self.assertEqual(payload["target"], {})

    def test_a_raising_provider_costs_only_its_section(self):
        payload = state.build_sync(self.char1, self._providers(inventory=BrokenProvider()))
        self.assertEqual(payload["inventory"], {"items": []})
        # Everything else still arrived.
        self.assertTrue(payload["room"])
        self.assertIn("map", payload)

    def test_a_provider_returning_the_wrong_type_is_survived(self):
        payload = state.build_sync(self.char1, self._providers(effects=LyingProvider()))
        self.assertEqual(payload["effects"], {"items": []})

    def test_carried_items_are_listed(self):
        lamp = create_object(DefaultObject, key="brass lamp", location=self.char1)
        payload = state.build_sync(self.char1, self._providers())
        names = [item["name"] for item in payload["inventory"]["items"]]
        self.assertIn("brass lamp", names)
        lamp.delete()

    def test_carried_items_carry_their_own_actions(self):
        """
        Carried objects resolve against the character rather than the room, so
        this would silently produce empty menus if the container were wrong.

        """
        lamp = create_object(DefaultObject, key="brass lamp", location=self.char1)
        payload = state.build_sync(self.char1, self._providers())
        item = [i for i in payload["inventory"]["items"] if i["name"] == "brass lamp"][0]
        self.assertTrue(item["actions"], "carried item got no actions")
        # It is held, so the useful action is to put it down, not to pick it up.
        labels = [action["label"] for action in item["actions"]]
        self.assertIn("Drop", labels)
        lamp.delete()

    def test_room_contents_are_not_listed_as_inventory(self):
        """
        The two lists come from different containers and must not blur -- an item
        on the floor shown as carried would have the player try to use it.

        """
        rock = create_object(DefaultObject, key="grey rock", location=self.room1)
        payload = state.build_sync(self.char1, self._providers())
        names = [item["name"] for item in payload["inventory"]["items"]]
        self.assertNotIn("grey rock", names)
        rock.delete()

    def test_an_unpuppeted_session_gets_empty_sections_not_an_error(self):
        payload = state.build_sync(None, self._providers())
        self.assertEqual(payload["inventory"], {"items": []})
        self.assertEqual(payload["target"], {})


class TestProviderConfiguration(TestCase):
    """A misconfigured slot fails loudly at load, not silently at runtime."""

    @override_settings(AETOS_PROVIDERS={"equipment": "evennia.does.not.Exist"})
    def test_an_unimportable_provider_names_the_slot(self):
        with self.assertRaises(providers.AetosProviderError) as caught:
            providers.get_providers()
        self.assertIn("equipment", str(caught.exception))

    @override_settings(
        AETOS_PROVIDERS={
            "target": "evennia.contrib.base_systems.aetos_webclient.providers"
            ".defaults.DefaultMapProvider"
        }
    )
    def test_a_provider_of_the_wrong_kind_is_rejected(self):
        """
        Pointing "target" at a map provider would otherwise produce a
        permanently empty target panel with no explanation.

        """
        with self.assertRaises(providers.AetosProviderError) as caught:
            providers.get_providers()
        self.assertIn("AetosTargetProvider", str(caught.exception))
