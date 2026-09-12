"""
Tests for the Aetos provider system.

Two things matter most here and are tested hardest:

* **Visibility.** A provider that surfaces an object a character cannot see is an
  information-disclosure bug, not a cosmetic one. Hidden exits in particular must
  stay hidden.
* **Containment.** Providers are game-supplied code running inside a websocket
  handler. One that raises must cost a widget, never the session.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import providers
from evennia.contrib.base_systems.aetos_webclient.providers import base, defaults
from evennia.utils.test_resources import EvenniaTest


class BrokenResourceProvider(base.AetosResourceProvider):
    """A provider that always fails, standing in for buggy game code."""

    def get_resources(self, character):
        raise RuntimeError("this provider is broken on purpose")


class NotAProvider:
    """Deliberately not a provider subclass."""


class TestProviderRegistryDefaults(TestCase):
    """A game that has configured nothing."""

    def test_all_slots_resolve(self):
        resolved = providers.get_providers()
        self.assertEqual(set(resolved), set(providers.PROVIDER_SLOTS))

    def test_entities_and_map_have_working_defaults(self):
        """These need no game cooperation, so they are provided out of the box."""
        resolved = providers.get_providers()
        self.assertIsInstance(resolved["entities"], defaults.DefaultEntityProvider)
        self.assertIsInstance(resolved["map"], defaults.DefaultMapProvider)

    def test_resources_defaults_to_exposing_nothing(self):
        """
        There is no genre-neutral way to guess a game's resources. Inventing a
        "health" default would be exactly the genre assumption this project
        forbids, so the default provider is inert and no widget appears.

        """
        resolved = providers.get_providers()
        self.assertEqual(resolved["resources"].get_resources(None), [])

    def test_actions_defaults_to_exposing_nothing(self):
        resolved = providers.get_providers()
        self.assertEqual(resolved["actions"].get_actions(None), [])


class TestProviderConfiguration(TestCase):
    """Games replacing providers through settings."""

    @override_settings(
        AETOS_PROVIDERS={
            "resources": (
                "evennia.contrib.base_systems.aetos_webclient.tests."
                "test_providers.BrokenResourceProvider"
            )
        }
    )
    def test_a_configured_provider_is_used(self):
        self.assertIsInstance(providers.get_providers()["resources"], BrokenResourceProvider)

    @override_settings(
        AETOS_PROVIDERS={
            "resources": (
                "evennia.contrib.base_systems.aetos_webclient.tests."
                "test_providers.BrokenResourceProvider"
            )
        }
    )
    def test_unconfigured_slots_keep_their_defaults(self):
        """Overriding one provider must not blank the others."""
        resolved = providers.get_providers()
        self.assertIsInstance(resolved["map"], defaults.DefaultMapProvider)

    @override_settings(AETOS_PROVIDERS={"resources": "world.does.not.Exist"})
    def test_unimportable_provider_is_a_clear_error(self):
        with self.assertRaises(providers.AetosProviderError) as ctx:
            providers.get_providers()
        self.assertIn("AETOS_PROVIDERS", str(ctx.exception))
        self.assertIn("world.does.not.Exist", str(ctx.exception))

    @override_settings(
        AETOS_PROVIDERS={
            "map": (
                "evennia.contrib.base_systems.aetos_webclient.tests." "test_providers.NotAProvider"
            )
        }
    )
    def test_wrong_provider_type_is_rejected(self):
        """
        A path pointing at the wrong kind of class must fail at load time. Left
        unchecked it would silently produce an empty map that looks like a bug in
        Aetos rather than a typo in settings.

        """
        with self.assertRaises(providers.AetosProviderError):
            providers.get_providers()

    @override_settings(AETOS_PROVIDERS={"mapp": "some.path"})
    def test_unknown_slot_is_rejected(self):
        """A misspelled slot would otherwise be silently ignored."""
        with self.assertRaises(providers.AetosProviderError) as ctx:
            providers.get_providers()
        self.assertIn("mapp", str(ctx.exception))

    @override_settings(AETOS_PROVIDERS=["resources"])
    def test_non_dict_setting_is_rejected(self):
        with self.assertRaises(providers.AetosProviderError):
            providers.get_providers()

    @override_settings(AETOS_PROVIDERS={"resources": 42})
    def test_non_string_path_is_rejected(self):
        with self.assertRaises(providers.AetosProviderError):
            providers.get_providers()


class TestSafeCall(TestCase):
    """Containment of failing game-supplied providers."""

    def test_a_raising_provider_returns_the_fallback(self):
        """
        The player must still get a working client. A broken resource provider
        costs the resource widget, not the session.

        """
        result = base.safe_call(BrokenResourceProvider(), "get_resources", [], None)
        self.assertEqual(result, [])

    def test_a_missing_method_returns_the_fallback(self):
        result = base.safe_call(NotAProvider(), "get_resources", ["fallback"], None)
        self.assertEqual(result, ["fallback"])

    def test_a_working_provider_is_passed_through(self):
        provider = defaults.DefaultEntityProvider()
        self.assertEqual(base.safe_call(provider, "get_room_entities", None, None), [])


class TestDefaultEntityProvider(EvenniaTest):
    """Room contents on an ordinary Evennia game."""

    def setUp(self):
        super().setUp()
        self.provider = defaults.DefaultEntityProvider()

    def test_lists_room_contents(self):
        entities = self.provider.get_room_entities(self.char1)
        names = {entity["name"] for entity in entities}
        self.assertIn(self.obj1.key, names)

    def test_excludes_the_observer(self):
        """A character is not an entity in its own room listing."""
        entities = self.provider.get_room_entities(self.char1)
        self.assertNotIn(str(self.char1.id), {entity["id"] for entity in entities})

    def test_classifies_exits_structurally(self):
        """Anything with a destination is an exit, whatever it is called."""
        entities = self.provider.get_room_entities(self.char1)
        exits = [entity for entity in entities if entity["kind"] == defaults.KIND_EXIT]
        self.assertTrue(exits)
        self.assertEqual(exits[0]["destination"], str(self.room2.id))

    def test_classifies_characters(self):
        entities = self.provider.get_room_entities(self.char1)
        kinds = {entity["name"]: entity["kind"] for entity in entities}
        self.assertEqual(kinds.get(self.char2.key), defaults.KIND_CHARACTER)

    def test_handles_a_character_with_no_location(self):
        """A character in the void must not crash the provider."""
        self.char1.location = None
        self.assertEqual(self.provider.get_room_entities(self.char1), [])

    def test_hidden_objects_are_not_exposed(self):
        """
        SECURITY: an object the character cannot view must never reach the
        client. Aetos honours Evennia's own view/search locks.

        """
        self.obj1.locks.add("view:false()")
        entities = self.provider.get_room_entities(self.char1)
        self.assertNotIn(str(self.obj1.id), {entity["id"] for entity in entities})


class TestDefaultMapProvider(EvenniaTest):
    """The zero-configuration local room graph."""

    def setUp(self):
        super().setUp()
        self.provider = defaults.DefaultMapProvider()

    def test_includes_the_current_room(self):
        data = self.provider.get_map(self.char1)
        self.assertEqual(data["current"], str(self.room1.id))
        self.assertIn(str(self.room1.id), {room["id"] for room in data["rooms"]})

    def test_walks_to_connected_rooms(self):
        data = self.provider.get_map(self.char1)
        self.assertIn(str(self.room2.id), {room["id"] for room in data["rooms"]})

    def test_records_the_link_with_its_direction(self):
        data = self.provider.get_map(self.char1)
        links = [link for link in data["exits"] if link["to"] == str(self.room2.id)]
        self.assertTrue(links)
        self.assertEqual(links[0]["direction"], self.exit.key)

    def test_records_distance_from_the_origin(self):
        data = self.provider.get_map(self.char1)
        distances = {room["id"]: room["distance"] for room in data["rooms"]}
        self.assertEqual(distances[str(self.room1.id)], 0)
        self.assertEqual(distances[str(self.room2.id)], 1)

    def test_handles_a_character_with_no_location(self):
        self.char1.location = None
        data = self.provider.get_map(self.char1)
        self.assertEqual(data, {"rooms": [], "exits": [], "current": None})

    def test_hidden_exits_stay_hidden(self):
        """
        SECURITY: a secret door must not be revealed by the mapper. The blueprint
        requires hidden exits remain hidden unless the server exposes them.

        """
        self.exit.locks.add("view:false()")
        data = self.provider.get_map(self.char1)
        self.assertEqual(data["exits"], [])
        self.assertNotIn(str(self.room2.id), {room["id"] for room in data["rooms"]})

    def test_never_links_to_a_room_it_did_not_send(self):
        """
        A dangling link would make the client reference a room it has no data
        for. Links beyond the walk depth are dropped rather than emitted.

        """
        data = self.provider.get_map(self.char1)
        known = {room["id"] for room in data["rooms"]}
        for link in data["exits"]:
            self.assertIn(link["to"], known)
            self.assertIn(link["from"], known)


class TestEntityClassification(EvenniaTest):
    """
    Structural classification of room contents.

    Regression guard: an earlier implementation tested `hasattr(obj,
    "at_pre_puppet")`, but that hook is defined on DefaultObject, so every
    object in the game has it and ordinary items were classified as characters
    and listed under "People Here".

    """

    def setUp(self):
        super().setUp()
        self.provider = defaults.DefaultEntityProvider()

    def _kind_of(self, obj):
        for entity in self.provider.get_room_entities(self.char1):
            if entity["id"] == str(obj.id):
                return entity["kind"]
        return None

    def test_a_plain_object_is_not_a_character(self):
        """An item must never appear in the people list."""
        self.assertEqual(self._kind_of(self.obj1), defaults.KIND_OBJECT)

    def test_a_character_is_a_character(self):
        self.assertEqual(self._kind_of(self.char2), defaults.KIND_CHARACTER)

    def test_an_exit_is_an_exit(self):
        """Exits are classified by having a destination, before anything else."""
        self.assertEqual(self._kind_of(self.exit), defaults.KIND_EXIT)

    def test_classification_uses_the_games_own_character_typeclass(self):
        """
        Aetos must not hardcode a character class. Pointing the setting at a
        class the object is not an instance of must stop it being classified as
        a character.

        """
        with override_settings(BASE_CHARACTER_TYPECLASS="evennia.objects.objects.DefaultExit"):
            self.assertEqual(self._kind_of(self.char2), defaults.KIND_OBJECT)
