"""
Tests for M23 -- the server-described UI manifest.

A game describes its interface through `AETOS_UI`: what its resources are
called, what order they sit in, and when they are worth announcing.

The line this milestone has to hold is between **description** and **data**.
`AETOS_UI` says a resource called `health` exists and what to call it; it says
nothing about where the number comes from, which is the D-track's job. Keeping
them apart means a game can describe its interface today, without Discovery, and
adopt bindings later without rewriting any of it.

"""

import re
from pathlib import Path

from django.test import TestCase, override_settings

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    manifest,
    ui_manifest,
)

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"
RESOURCES_JS = (JS_DIR / "resources.js").read_text(encoding="utf-8")


class TestItDescribesRatherThanSupplies(TestCase):
    """
    The boundary against the D-track.

    """

    def test_a_descriptor_carries_no_value(self):
        """
        `value`, `maximum` and the rest belong to a provider. A descriptor that
        carried them would be a second source of truth about the numbers, and
        the two would eventually disagree.

        """
        with override_settings(
            AETOS_UI={"resources": [{"id": "health", "label": "Health", "value": 99}]}
        ):
            described = ui_manifest.get_ui_description()
        descriptor = described["resources"][0]
        for forbidden in ("value", "maximum", "current"):
            self.assertNotIn(forbidden, descriptor)

    def test_it_cannot_name_a_data_source(self):
        """
        Sourcing values is `AETOS_BINDINGS` (D-track). A settings key that
        looked like a binding must be refused here rather than half-working.

        """
        with override_settings(AETOS_UI={"bindings": {"health": "db.hp"}}):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_the_module_reaches_nothing_but_settings_and_resources(self):
        source = Path(ui_manifest.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import evennia.objects",
            "search_object",
            "DefaultCharacter",
            "AttributeProperty",
            ".db.",
            ".attributes",
        ):
            self.assertNotIn(forbidden, source, "ui_manifest reads game data via %r" % forbidden)


class TestMalformedSettingsAreRefused(TestCase):
    """
    Unknown keys are an error rather than being ignored.

    A typo in a settings key is otherwise silent, and a developer believing they
    had renamed a gauge would simply never see it change. The same rule
    `AETOS_FEATURES` follows.

    """

    def test_an_unknown_section_is_refused(self):
        with override_settings(AETOS_UI={"resourcs": []}):
            with self.assertRaises(ui_manifest.AetosUIError) as caught:
                ui_manifest.get_ui_description()
        # The message names the valid options, because "unknown section" alone
        # sends somebody to the documentation for a typo.
        self.assertIn("Valid sections", str(caught.exception))

    def test_an_unknown_panel_is_refused(self):
        with override_settings(AETOS_UI={"panels": {"invetory": {"title": "Bag"}}}):
            with self.assertRaises(ui_manifest.AetosUIError) as caught:
                ui_manifest.get_ui_description()
        self.assertIn("Valid panels", str(caught.exception))

    def test_a_resource_without_an_id_is_refused(self):
        with override_settings(AETOS_UI={"resources": [{"label": "Health"}]}):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_a_duplicate_declaration_is_refused(self):
        """
        Two declarations of one resource have no defensible resolution -- the
        second is either a mistake or a merge nobody asked for.

        """
        with override_settings(
            AETOS_UI={"resources": [{"id": "health"}, {"id": "health", "label": "HP"}]}
        ):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_a_non_dict_setting_is_refused(self):
        with override_settings(AETOS_UI=["health"]):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_absent_settings_are_not_an_error(self):
        """
        A game that says nothing gets the zero-configuration client, which is
        the whole progressive-enhancement premise.

        `AETOS_UI=None` explicitly, not read from the ambient settings. A test
        that reads what the surrounding game happens to declare asserts a fact
        about the deployment rather than about the code, and fails the moment
        somebody configures the lab -- which is exactly what happened here, and
        happened once before at A5 for the same reason.

        """
        with override_settings(AETOS_UI=None):
            described = ui_manifest.get_ui_description()
        self.assertEqual(described, {"resources": [], "panels": {}})


class TestDescriptorContent(TestCase):
    """What a declaration produces."""

    def test_a_label_defaults_to_the_id(self):
        """
        Rather than to a blank. An unlabelled gauge is announced as "edit,
        blank" or worse, and the id is at least a word.

        """
        with override_settings(AETOS_UI={"resources": [{"id": "stamina"}]}):
            described = ui_manifest.get_ui_description()
        self.assertEqual(described["resources"][0]["label"], "stamina")

    def test_thresholds_use_the_same_validator_as_providers(self):
        """
        Two validators for one concept is how a client ends up announcing at
        25% in one place and 0.25 in another.

        """
        source = Path(ui_manifest.__file__).read_text(encoding="utf-8")
        self.assertIn("resources.normalize_threshold(entry)", source)

    def test_an_unknown_threshold_key_is_refused(self):
        """
        Found the hard way: `state_text` and `announce` are A.77's field names
        for a *resource*, not a threshold. Declared here they were accepted
        silently and produced a threshold with an empty label at the default
        level -- one that would never announce anything useful, with nothing to
        say why.

        A provider supplying the same mistake is tolerated and dropped, because
        a provider is runtime game code. A *setting* is a developer typing a
        literal, where a wrong key is a mistake they want told about.

        """
        with override_settings(
            AETOS_UI={
                "resources": [{"id": "health", "thresholds": [{"at": 0.25, "state_text": "hurt"}]}]
            }
        ):
            with self.assertRaises(ui_manifest.AetosUIError) as caught:
                ui_manifest.get_ui_description()
        self.assertIn("state_text", str(caught.exception))
        self.assertIn("Valid keys", str(caught.exception))

    def test_a_threshold_without_a_label_is_refused(self):
        """
        It announces nothing a player can act on, which makes it
        indistinguishable from having no threshold at all.

        """
        with override_settings(
            AETOS_UI={"resources": [{"id": "health", "thresholds": [{"at": 0.25}]}]}
        ):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_a_valid_threshold_is_kept(self):
        with override_settings(
            AETOS_UI={
                "resources": [
                    {
                        "id": "health",
                        "thresholds": [{"at": 0.25, "label": "badly hurt", "level": "critical"}],
                    }
                ]
            }
        ):
            described = ui_manifest.get_ui_description()
        threshold = described["resources"][0]["thresholds"][0]
        self.assertEqual(threshold["label"], "badly hurt")
        self.assertEqual(threshold["level"], "critical")

    def test_a_provider_threshold_is_still_tolerant(self):
        """
        The asymmetry, asserted. A provider is contained by `safe_call` and
        expected to be imperfect; a malformed threshold from one is dropped
        rather than raising.

        """
        from evennia.contrib.base_systems.aetos_webclient import resources as res

        self.assertIsNone(res.normalize_threshold("nonsense"))
        self.assertIsNone(res.normalize_threshold({"label": "no at value"}))

    def test_a_panel_title_is_kept(self):
        with override_settings(AETOS_UI={"panels": {"resources": {"title": "Vitals"}}}):
            described = ui_manifest.get_ui_description()
        self.assertEqual(described["panels"]["resources"]["title"], "Vitals")

    def test_an_empty_panel_title_is_refused(self):
        """
        A title is the panel's accessible name as well as its heading, so a
        blank one is worth refusing rather than silently dropping.

        """
        with override_settings(AETOS_UI={"panels": {"resources": {"title": "  "}}}):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_declarations_are_bounded(self):
        many = [{"id": "r%d" % index} for index in range(200)]
        with override_settings(AETOS_UI={"resources": many}):
            described = ui_manifest.get_ui_description()
        self.assertLessEqual(len(described["resources"]), ui_manifest.MAX_DESCRIBED_RESOURCES)


class TestOrdering(TestCase):
    """
    A gauge that moves between second and fourth place between syncs is not a
    cosmetic problem for somebody navigating by position or by screen reader.

    """

    def _items(self, *ids):
        """
        Build a minimal resource list.

        Args:
            *ids (str): Resource ids, in arrival order.

        Returns:
            list: Resource dicts.

        """
        return [{"id": identifier, "label": identifier} for identifier in ids]

    def test_declared_order_wins_over_arrival_order(self):
        described = [{"id": "health", "order": 1}, {"id": "stamina", "order": 2}]
        ordered = ui_manifest.order_resources(self._items("stamina", "health"), described)
        self.assertEqual([item["id"] for item in ordered], ["health", "stamina"])

    def test_declaration_order_is_used_when_no_order_is_given(self):
        described = [{"id": "health"}, {"id": "stamina"}]
        ordered = ui_manifest.order_resources(self._items("stamina", "health"), described)
        self.assertEqual([item["id"] for item in ordered], ["health", "stamina"])

    def test_undeclared_resources_are_kept_and_sort_last(self):
        """
        Kept, not dropped. A game that adds a resource to its provider and
        forgets the declaration should see it appear at the bottom, not vanish
        -- the second failure is much harder to diagnose, and the first is
        self-correcting.

        """
        described = [{"id": "health", "order": 1}]
        ordered = ui_manifest.order_resources(self._items("mana", "health", "focus"), described)
        self.assertEqual([item["id"] for item in ordered], ["health", "mana", "focus"])

    def test_no_declarations_leaves_the_order_alone(self):
        items = self._items("a", "b", "c")
        self.assertEqual(ui_manifest.order_resources(items, []), items)


class TestTheManifestCarriesIt(TestCase):
    """The description has to reach the client."""

    def test_described_resources_appear_in_the_manifest(self):
        with override_settings(AETOS_UI={"resources": [{"id": "health", "label": "Health"}]}):
            payload = manifest.build_manifest()
        self.assertEqual(payload["resources"][0]["label"], "Health")

    def test_panels_appear_in_the_manifest(self):
        with override_settings(AETOS_UI={"panels": {"resources": {"title": "Vitals"}}}):
            payload = manifest.build_manifest()
        self.assertEqual(payload["panels"]["resources"]["title"], "Vitals")

    def test_the_keys_exist_even_when_nothing_is_declared(self):
        """
        Protocol v1 promised a stable shape, so a client can rely on the keys
        rather than testing for them.

        """
        payload = manifest.build_manifest()
        for key in ("resources", "panels", "widgets", "actions", "map", "media"):
            self.assertIn(key, payload)


class TestAPendingGaugeIsNotAnEmptyOne(TestCase):
    """
    An empty panel and a panel whose numbers have not arrived look identical,
    and they mean completely different things.

    """

    def test_a_declared_resource_renders_before_its_value(self):
        self.assertIn("function renderPending(descriptor)", RESOURCES_JS)

    def test_it_says_waiting_rather_than_showing_a_number(self):
        """
        A zero is a *value*, and showing one for a health bar that simply has
        not loaded is the worst possible wrong answer.

        """
        start = RESOURCES_JS.index("function renderPending(descriptor)")
        window = RESOURCES_JS[start : RESOURCES_JS.index("function renderResource", start)]
        self.assertIn('"waiting"', window)
        self.assertNotIn("0", window.replace('"0"', "").replace("aetos-resource", ""))

    def test_supplied_values_always_win(self):
        """
        A descriptor is a promise about the interface, not a second source of
        truth about the numbers.

        """
        start = RESOURCES_JS.index("update: function (context, data)")
        window = RESOURCES_JS[start : start + 1600]
        self.assertIn("supplied[resource.id] = true", window)
        self.assertIn("!supplied[descriptor.id]", window)

    def test_a_pending_gauge_is_never_announced(self):
        """
        Announcing "waiting" would be announcing the absence of news, which is
        the kind of interruption Quiet Mode exists to stop -- and it would fire
        on every reconnect.

        """
        start = RESOURCES_JS.index("pending.forEach(function (descriptor)")
        window = RESOURCES_JS[start : start + 220]
        self.assertNotIn("announce(", window)

    def test_a_declared_resource_counts_as_content(self):
        """
        Otherwise the panel marks itself empty and hides, which is the very
        situation the declaration exists to prevent.

        """
        start = RESOURCES_JS.index("update: function (context, data)")
        window = RESOURCES_JS[start : start + 1600]
        self.assertIn("(items.length || pending.length)", window)


class TestItCannotEscalate(TestCase):
    """
    Everything here is presentation metadata applied to data the game supplies
    through the ordinary channels, so a malformed or hostile `AETOS_UI`
    produces a badly labelled interface, never a privileged one.

    """

    def test_it_cannot_declare_a_feature(self):
        """
        Features stay in `AETOS_FEATURES`. A UI description that could switch a
        capability on would be a second, less-examined route to the same
        decision.

        """
        with override_settings(
            AETOS_UI={"features": {"scripting": True}},
            AETOS_FEATURES={},
        ):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_it_cannot_relax_automation_policy(self):
        with override_settings(
            AETOS_UI={"automation": {"scripting": True}},
        ):
            with self.assertRaises(ui_manifest.AetosUIError):
                ui_manifest.get_ui_description()

    def test_a_declaration_never_becomes_a_command(self):
        source = Path(ui_manifest.__file__).read_text(encoding="utf-8")
        for forbidden in ("execute", "msg(", "cmdstring", "at_cmdset", "commandTemplate"):
            self.assertNotIn(forbidden, source)

    def test_text_fields_are_bounded(self):
        long_label = "x" * 5000
        with override_settings(AETOS_UI={"resources": [{"id": "health", "label": long_label}]}):
            described = ui_manifest.get_ui_description()
        self.assertLess(len(described["resources"][0]["label"]), 500)


class TestAMalformedSettingCostsOnlyItself(TestCase):
    """
    A developer's typo must not cost a player their resources.

    """

    def test_the_sync_survives_a_broken_ui_setting(self):
        """
        The handshake reports it loudly, where a developer sees it. The sync
        path must not also fail, or one settings typo empties the client.

        """
        source = Path(Path(ui_manifest.__file__).parent / "state.py").read_text(encoding="utf-8")
        self.assertIn("except ui_manifest.AetosUIError", source)

    def test_the_handshake_still_reports_it(self):
        """
        Contained in the sync, surfaced at the handshake -- so it is neither
        fatal nor silent.

        **This test used to assert `AetosUIError` and was wrong about what that
        meant.** It checked that `build_manifest` raised, and read that as "the
        handshake reports it". The handshake catches `AetosManifestError` only,
        and `AetosUIError` is a sibling rather than a subclass -- so what
        actually happened was an unhandled exception leaving `aetos_hello`, and
        every player connecting to a game with a mistyped `AETOS_UI` got a
        connection that neither completed nor explained itself.

        The intent was right and the assertion was one layer too low: it pinned
        the mechanism instead of the outcome, so it went on passing while the
        outcome was the opposite of its own docstring. `build_manifest` now
        raises the type it has always documented, and
        `test_inputfuncs.test_no_malformed_setting_escapes_the_handshake`
        checks the outcome for every setting rather than for one.

        """
        with override_settings(AETOS_UI={"nonsense": True}):
            with self.assertRaises(manifest.AetosManifestError):
                manifest.build_manifest()

    def test_the_message_survives_the_translation(self):
        """
        Re-raising must not cost the developer the sentence naming their typo.

        """
        with override_settings(AETOS_UI={"resources": "not a list"}):
            with self.assertRaises(manifest.AetosManifestError) as caught:
                manifest.build_manifest()
        self.assertIn("AETOS_UI", str(caught.exception))
