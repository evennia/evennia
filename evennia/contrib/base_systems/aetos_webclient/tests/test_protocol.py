"""
Tests for the Aetos protocol.

The hello payload arrives from a browser and is untrusted input, so these tests
cover malformed structure as thoroughly as the happy path. They also pin the
forward- and backward-compatibility behaviour, which is the part most likely to
be broken by a well-meaning later change.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import (
    AETOS_STATIC_DIR,
    constants,
    protocol,
    state,
)
from evennia.contrib.base_systems.aetos_webclient.providers import base


class TestMessageNames(TestCase):
    """Wire names are a frozen contract at protocol v1."""

    def test_all_message_names_are_namespaced(self):
        """
        Every Aetos message must be prefixed so it cannot collide with an
        Evennia outputfunc or another contrib's messages.

        """
        names = [protocol.MSG_HELLO, protocol.MSG_MANIFEST, protocol.MSG_SYNC]
        names.extend(protocol.DELTA_MESSAGES)
        for name in names:
            self.assertTrue(name.startswith("aetos_"), "%r is not namespaced" % name)

    def test_delta_message_list_has_no_duplicates(self):
        """A duplicate would mean a delta is emitted twice per sync."""
        self.assertEqual(len(protocol.DELTA_MESSAGES), len(set(protocol.DELTA_MESSAGES)))

    def test_hello_is_not_listed_as_a_delta(self):
        """hello is client->server; it must never be emitted in a sync."""
        self.assertNotIn(protocol.MSG_HELLO, protocol.DELTA_MESSAGES)


class TestBuildHello(TestCase):
    """The payload a client sends on connect."""

    def test_declares_the_current_protocol_version(self):
        self.assertEqual(protocol.build_hello()["protocol"], constants.PROTOCOL_VERSION)

    def test_defaults_to_the_aetos_client_name(self):
        self.assertEqual(protocol.build_hello()["client"], constants.CLIENT_NAME)

    def test_defaults_to_advertising_all_known_capabilities(self):
        payload = protocol.build_hello()
        self.assertEqual(set(payload["capabilities"]), protocol.KNOWN_CAPABILITIES)

    def test_round_trips_through_the_parser(self):
        """What a client builds, a server must accept."""
        parsed = protocol.parse_hello(protocol.build_hello())
        self.assertTrue(parsed.is_compatible)
        self.assertEqual(parsed.client, constants.CLIENT_NAME)


class TestParseHelloAcceptsValidInput(TestCase):
    """The happy path and the deliberately permissive parts of it."""

    def test_parses_a_minimal_hello(self):
        """Only 'protocol' is genuinely required."""
        hello = protocol.parse_hello({"protocol": 1})
        self.assertEqual(hello.protocol, 1)
        self.assertEqual(hello.capabilities, frozenset())

    def test_capabilities_are_exposed_via_supports(self):
        hello = protocol.parse_hello({"protocol": 1, "capabilities": ["map", "resources"]})
        self.assertTrue(hello.supports(protocol.CAPABILITY_MAP))
        self.assertFalse(hello.supports(protocol.CAPABILITY_MEDIA))

    def test_unknown_capabilities_are_accepted_not_rejected(self):
        """
        A newer client may advertise capabilities this server has never heard
        of. Rejecting the hello would lock it out entirely; the correct
        behaviour is to serve it and ignore what we do not understand.

        """
        hello = protocol.parse_hello({"protocol": 1, "capabilities": ["map", "telepathy"]})
        self.assertTrue(hello.is_compatible)
        self.assertEqual(hello.unknown_capabilities, frozenset({"telepathy"}))

    def test_empty_capability_strings_are_dropped(self):
        hello = protocol.parse_hello({"protocol": 1, "capabilities": ["", "map", ""]})
        self.assertEqual(hello.capabilities, frozenset({"map"}))

    def test_duplicate_capabilities_collapse(self):
        hello = protocol.parse_hello({"protocol": 1, "capabilities": ["map", "map", "map"]})
        self.assertEqual(hello.capabilities, frozenset({"map"}))


class TestProtocolVersionCompatibility(TestCase):
    """Version handling must degrade in both directions."""

    def test_current_version_is_compatible(self):
        hello = protocol.parse_hello({"protocol": constants.PROTOCOL_VERSION})
        self.assertTrue(hello.is_compatible)

    def test_a_newer_client_is_still_served(self):
        """
        A client speaking protocol 99 is served at this server's version. It is
        the client's job to degrade. Refusing would mean every server upgrade
        broke every older client and vice versa.

        """
        hello = protocol.parse_hello({"protocol": 99})
        self.assertTrue(hello.is_compatible)

    def test_protocol_zero_is_rejected(self):
        """There is no protocol 0; this indicates a malformed or probing client."""
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": 0})

    def test_negative_protocol_is_rejected(self):
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": -1})


class TestParseHelloRejectsMalformedInput(TestCase):
    """
    Hostile and malformed payloads.

    This is untrusted browser input; every one of these is reachable by anyone
    who can open a websocket.

    """

    def test_rejects_a_non_mapping_payload(self):
        for payload in ([], "hello", 42, None):
            with self.assertRaises(protocol.AetosProtocolError):
                protocol.parse_hello(payload)

    def test_rejects_a_missing_protocol_version(self):
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"client": "aetos"})

    def test_rejects_a_non_integer_protocol_version(self):
        for value in ("1", 1.0, [1], {"v": 1}):
            with self.assertRaises(protocol.AetosProtocolError):
                protocol.parse_hello({"protocol": value})

    def test_rejects_boolean_protocol_version(self):
        """
        bool subclasses int in Python, so `True` would otherwise be accepted as
        protocol version 1. This is the classic isinstance(x, int) trap.

        """
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": True})

    def test_rejects_a_non_string_client_name(self):
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": 1, "client": 12345})

    def test_rejects_non_list_capabilities(self):
        for value in ("map", {"map": True}, 7):
            with self.assertRaises(protocol.AetosProtocolError):
                protocol.parse_hello({"protocol": 1, "capabilities": value})

    def test_rejects_non_string_capability_entries(self):
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": 1, "capabilities": ["map", 7]})

    def test_rejects_an_oversized_capability_list(self):
        """An unbounded list is a cheap memory amplifier for an attacker."""
        oversized = ["cap%d" % i for i in range(protocol.MAX_CAPABILITIES + 1)]
        with self.assertRaises(protocol.AetosProtocolError):
            protocol.parse_hello({"protocol": 1, "capabilities": oversized})

    def test_accepts_a_capability_list_at_the_limit(self):
        """The boundary itself must be allowed, not rejected off-by-one."""
        at_limit = ["cap%d" % i for i in range(protocol.MAX_CAPABILITIES)]
        hello = protocol.parse_hello({"protocol": 1, "capabilities": at_limit})
        self.assertEqual(len(hello.capabilities), protocol.MAX_CAPABILITIES)

    def test_truncates_an_overlong_capability_string(self):
        """Bounded rather than rejected: a long name is odd, not hostile."""
        hello = protocol.parse_hello({"protocol": 1, "capabilities": ["x" * 5000]})
        entry = next(iter(hello.capabilities))
        self.assertEqual(len(entry), protocol.MAX_CAPABILITY_LENGTH)

    def test_truncates_an_overlong_client_name(self):
        hello = protocol.parse_hello({"protocol": 1, "client": "c" * 5000})
        self.assertEqual(len(hello.client), protocol.MAX_CAPABILITY_LENGTH)


class TestClientConstantsMatchServer(TestCase):
    """
    The browser duplicates a few protocol constants.

    `aetos.js` must know the protocol version and message names before any server
    data has arrived, since it has to send the very first message. That
    duplication is unavoidable, so it is pinned here: drift between the two would
    otherwise surface as a client that silently never handshakes.

    """

    def setUp(self):
        from pathlib import Path

        from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

        self.script = (Path(AETOS_STATIC_DIR) / "aetos" / "js" / "aetos.js").read_text(
            encoding="utf-8"
        )

    def test_client_declares_the_same_protocol_version(self):
        self.assertIn("AETOS_PROTOCOL_VERSION = %d" % constants.PROTOCOL_VERSION, self.script)

    def test_client_knows_every_handshake_message_name(self):
        for name in (protocol.MSG_HELLO, protocol.MSG_MANIFEST, protocol.MSG_SYNC):
            self.assertIn('"%s"' % name, self.script)

    def test_client_handles_every_delta_message(self):
        """
        A delta the client does not map would be silently dropped: the server
        would send state that never reaches a widget.

        """
        for name in protocol.DELTA_MESSAGES:
            self.assertIn(name, self.script)

    def test_client_advertises_only_known_capabilities(self):
        """
        A typo in the client's capability list would advertise a capability the
        server has never heard of, silently disabling that feature.

        """
        import re

        block = re.search(r"AETOS_CAPABILITIES\s*=\s*\[(.*?)\]", self.script, re.DOTALL)
        self.assertIsNotNone(block, "AETOS_CAPABILITIES not found in aetos.js")
        advertised = set(re.findall(r'"([a-z_]+)"', block.group(1)))
        self.assertTrue(advertised)
        self.assertTrue(
            advertised <= protocol.KNOWN_CAPABILITIES,
            "client advertises unknown capabilities: %s"
            % sorted(advertised - protocol.KNOWN_CAPABILITIES),
        )


class TestTheStoreKnowsEverySyncSection(TestCase):
    """
    Regression guard for a silent data loss.

    `store.js` keeps an allowlist of sections and `applySync` discards anything
    absent from it. M16 added `inventory` and `equipment` to `build_sync`, added
    widgets that subscribed to them, and never added them to that array.

    The result was perfectly quiet: the server sent the payload, the widgets
    subscribed, the store dropped it, and the panels rendered empty forever. No
    error, no warning, and nothing in a screenshot to notice -- an empty
    inventory looks exactly like an empty inventory.

    So the two lists are compared directly.

    """

    def _store_sections(self):
        """
        Extract the section allowlist from store.js.

        Returns:
            set: Section names the client store accepts.

        """
        source = (Path(AETOS_STATIC_DIR) / "aetos" / "js" / "store.js").read_text(encoding="utf-8")
        block = source[source.index("var SECTIONS = [") : source.index("];")]
        return set(re.findall(r'"(\w+)"', block))

    def _sync_sections(self):
        """
        Build a sync and read its top-level keys.

        Returns:
            set: Section names the server sends.

        """
        payload = state.build_sync(None, self._providers())
        return set(payload)

    def _providers(self):
        """
        Inert providers, so the shape is exercised without a database.

        Returns:
            dict: Provider instances by slot.

        """
        return {
            "resources": base.AetosResourceProvider(),
            "entities": base.AetosEntityProvider(),
            "actions": base.AetosActionProvider(),
            "map": base.AetosMapProvider(),
            "inventory": base.AetosInventoryProvider(),
            "equipment": base.AetosEquipmentProvider(),
            "target": base.AetosTargetProvider(),
            "effects": base.AetosEffectProvider(),
        }

    def test_the_store_accepts_every_section_the_server_sends(self):
        missing = self._sync_sections() - self._store_sections()
        self.assertEqual(
            missing,
            set(),
            "build_sync sends %s but store.js discards them -- silently" % sorted(missing),
        )

    def test_the_store_declares_no_section_the_server_never_sends(self):
        """
        The other direction is a weaker problem -- a dead key rather than lost
        data -- but it is still a list that has drifted from what it describes.

        `connection` and `manifest` are client-side concerns that never appear
        in a sync, so they are expected.

        """
        client_only = {"connection", "manifest"}
        extra = self._store_sections() - self._sync_sections() - client_only
        self.assertEqual(extra, set(), "store.js declares unused sections %s" % sorted(extra))
