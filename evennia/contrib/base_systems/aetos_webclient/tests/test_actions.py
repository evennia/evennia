"""
Tests for Aetos contextual actions.

An action is a label plus an ordinary game command. Two things matter:

* **Aetos grants no authority.** Offering an action does not make it legal. The
  command travels the ordinary command path and the server rules on it, exactly
  as if the player had typed it.

* **Provider output is untrusted.** A malformed action reaching the client would
  render a button that sends nonsense, so validation happens server-side.

"""

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import state
from evennia.contrib.base_systems.aetos_webclient.providers import defaults
from evennia.utils.test_resources import EvenniaTest


class TestActionNormalization(TestCase):
    """Validation of a provider's action list."""

    def test_accepts_a_well_formed_action(self):
        actions = state._normalize_actions([{"label": "Look", "command": "look sword"}])
        self.assertEqual(actions[0]["label"], "Look")
        self.assertEqual(actions[0]["command"], "look sword")

    def test_provides_both_plain_and_display_labels(self):
        """
        A label may carry colour markup for display, but the command must be
        sent verbatim. Conflating them would put markup into a command the
        server cannot parse.

        """
        actions = state._normalize_actions([{"label": "|rAttack|n", "command": "attack goblin"}])
        self.assertEqual(actions[0]["label"], "Attack")
        self.assertIn("color-", actions[0]["display"])
        self.assertEqual(actions[0]["command"], "attack goblin")

    def test_rejects_an_action_with_no_command(self):
        """A button that sends nothing is worse than no button."""
        self.assertEqual(state._normalize_actions([{"label": "Look"}]), [])

    def test_rejects_an_action_with_no_label(self):
        self.assertEqual(state._normalize_actions([{"command": "look"}]), [])

    def test_rejects_non_string_fields(self):
        for entry in (
            {"label": 5, "command": "look"},
            {"label": "Look", "command": 5},
            {"label": None, "command": None},
        ):
            self.assertEqual(state._normalize_actions([entry]), [])

    def test_drops_malformed_entries_individually(self):
        """One bad action must not discard the whole menu."""
        actions = state._normalize_actions(
            [{"label": "Look", "command": "look"}, "nonsense", None, {"bad": True}]
        )
        self.assertEqual(len(actions), 1)

    def test_a_non_list_yields_nothing(self):
        for value in (None, "look", 7, {"label": "Look"}):
            self.assertEqual(state._normalize_actions(value), [])

    def test_action_count_is_bounded(self):
        """A buggy provider must not produce an unbounded menu."""
        actions = state._normalize_actions(
            [{"label": "A%d" % i, "command": "look %d" % i} for i in range(500)]
        )
        self.assertLessEqual(len(actions), state.MAX_ACTIONS_PER_ENTITY)

    def test_long_commands_are_truncated(self):
        actions = state._normalize_actions([{"label": "Long", "command": "x" * 5000}])
        self.assertLessEqual(len(actions[0]["command"]), state.MAX_ACTION_COMMAND_LENGTH)


class TestDefaultActionProvider(EvenniaTest):
    """
    The zero-configuration action set.

    Blueprint section 11 promises basic context actions with no custom game code,
    so the defaults must be commands a fresh Evennia install genuinely has --
    look, get, drop -- rather than genre guesses.

    """

    def setUp(self):
        super().setUp()
        self.provider = defaults.DefaultActionProvider()

    def test_no_target_yields_no_actions(self):
        self.assertEqual(self.provider.get_actions(self.char1), [])

    def test_no_character_yields_no_actions(self):
        self.assertEqual(self.provider.get_actions(None, target=self.obj1), [])

    def test_every_target_can_at_least_be_looked_at(self):
        """`look` exists in every stock game and applies to anything visible."""
        actions = self.provider.get_actions(self.char1, target=self.obj1)
        self.assertIn("Look", [entry["label"] for entry in actions])

    def test_an_object_in_the_room_offers_get(self):
        actions = self.provider.get_actions(self.char1, target=self.obj1)
        labels = [entry["label"] for entry in actions]
        self.assertIn("Get", labels)
        self.assertNotIn("Drop", labels)

    def test_a_carried_object_offers_drop_instead(self):
        """
        Which of get/drop is useful depends on where the object is. Offering
        both would always show one that cannot work.

        """
        self.obj1.location = self.char1
        actions = self.provider.get_actions(self.char1, target=self.obj1)
        labels = [entry["label"] for entry in actions]
        self.assertIn("Drop", labels)
        self.assertNotIn("Get", labels)

    def test_an_exit_offers_traversal_by_its_own_name(self):
        actions = self.provider.get_actions(self.char1, target=self.exit)
        commands = [entry["command"] for entry in actions]
        self.assertIn(self.exit.key, commands)

    def test_a_character_is_not_offered_get(self):
        """Picking up another character is not a stock action."""
        actions = self.provider.get_actions(self.char1, target=self.char2)
        self.assertNotIn("Get", [entry["label"] for entry in actions])

    def test_commands_are_plain_text(self):
        """
        Every action is exactly what a player could type. Nothing here is a
        privileged call, which is what keeps the server authoritative.

        """
        actions = self.provider.get_actions(self.char1, target=self.obj1)
        for entry in actions:
            self.assertIsInstance(entry["command"], str)
            self.assertTrue(entry["command"].strip())


class TestActionsTravelWithEntities(EvenniaTest):
    """
    Actions are attached to the entity they belong to.

    A parallel list would let a client render a menu against the wrong target --
    a mismatch that stays invisible until a player acts on the wrong thing.

    """

    def test_entities_carry_their_actions(self):
        payload = state.build_sync(self.char1)
        entities = payload["entities"]["items"]
        self.assertTrue(entities)
        self.assertTrue(all("actions" in entity for entity in entities))

    def test_exits_carry_actions_too(self):
        payload = state.build_sync(self.char1)
        exits = payload["room"]["exits"]
        self.assertTrue(exits)
        self.assertTrue(all("actions" in entry for entry in exits))

    def test_a_character_with_no_location_is_handled(self):
        self.char1.location = None
        payload = state.build_sync(self.char1)
        self.assertEqual(payload["entities"]["items"], [])

    @override_settings(
        AETOS_PROVIDERS={
            "actions": "evennia.contrib.base_systems.aetos_webclient.providers"
            ".base.AetosActionProvider"
        }
    )
    def test_a_game_can_disable_actions_entirely(self):
        """
        Replacing the provider with the inert base removes every menu. A game
        that does not want contextual actions must be able to say so.

        """
        payload = state.build_sync(self.char1)
        for entity in payload["entities"]["items"]:
            self.assertEqual(entity["actions"], [])
