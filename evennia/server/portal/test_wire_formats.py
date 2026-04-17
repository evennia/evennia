"""
Tests for WebSocket wire formats and subprotocol negotiation.

Tests cover:
    - gmcp_utils.py: encode_gmcp / decode_gmcp
    - Wire format codecs: EvenniaV1, Terminal, JsonStandard, GmcpStandard
    - WebSocket subprotocol negotiation in webclient.py
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, Mock

# ---------------------------------------------------------------------------
# GMCP utilities
# ---------------------------------------------------------------------------


class TestGmcpEncode(TestCase):
    """Tests for gmcp_utils.encode_gmcp()."""

    def setUp(self):
        from evennia.server.portal.gmcp_utils import encode_gmcp

        self.encode = encode_gmcp

    def test_known_mapping(self):
        """Commands in EVENNIA_TO_GMCP should use the mapped name."""
        result = self.encode("client_options")
        self.assertEqual(result, "Core.Supports.Get")

    def test_known_mapping_with_args(self):
        result = self.encode("get_value", "hp")
        self.assertEqual(result, 'Char.Value.Get "hp"')

    def test_underscore_to_dotted(self):
        """Underscored names should become dotted with capitalization."""
        result = self.encode("char_vitals")
        self.assertEqual(result, "Char.Vitals")

    def test_no_underscore_gets_core_prefix(self):
        """Single-word commands get Core. prefix."""
        result = self.encode("ping")
        self.assertEqual(result, "Core.Ping")

    def test_already_title_case_preserved(self):
        result = self.encode("Ping")
        self.assertEqual(result, "Core.Ping")

    def test_fully_uppercase_preserved(self):
        """Fully uppercase segments should stay uppercase."""
        result = self.encode("char_HP")
        self.assertEqual(result, "Char.HP")

    def test_no_args_no_kwargs(self):
        result = self.encode("ping")
        self.assertEqual(result, "Core.Ping")

    def test_single_arg(self):
        result = self.encode("ping", "test")
        self.assertEqual(result, 'Core.Ping "test"')

    def test_multiple_args(self):
        result = self.encode("ping", "a", "b")
        self.assertEqual(result, 'Core.Ping ["a", "b"]')

    def test_kwargs_only(self):
        result = self.encode("ping", hp=100)
        self.assertEqual(result, 'Core.Ping {"hp": 100}')

    def test_args_and_kwargs(self):
        result = self.encode("ping", "a", hp=100)
        self.assertEqual(result, 'Core.Ping ["a", {"hp": 100}]')


class TestGmcpDecode(TestCase):
    """Tests for gmcp_utils.decode_gmcp()."""

    def setUp(self):
        from evennia.server.portal.gmcp_utils import decode_gmcp

        self.decode = decode_gmcp

    def test_known_mapping(self):
        """Known GMCP package names should map to Evennia names."""
        result = self.decode("Core.Supports.Get")
        self.assertIn("client_options", result)
        self.assertEqual(result["client_options"], [[], {}])

    def test_package_to_underscore(self):
        """Unknown package names should become lowercase underscore."""
        result = self.decode("Char.Vitals")
        self.assertIn("char_vitals", result)

    def test_core_prefix_stripped(self):
        """Core. prefix should be stripped from the command name."""
        result = self.decode("Core.Ping")
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [[], {}])

    def test_string_arg(self):
        result = self.decode('Core.Ping "test"')
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [["test"], {}])

    def test_array_arg(self):
        result = self.decode('Core.Ping ["a", "b"]')
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [["a", "b"], {}])

    def test_dict_arg(self):
        result = self.decode('Core.Ping {"hp": 100}')
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [[], {"hp": 100}])

    def test_bytes_input(self):
        result = self.decode(b"Core.Ping")
        self.assertIn("ping", result)

    def test_empty_input(self):
        result = self.decode("")
        self.assertEqual(result, {})

    def test_non_json_structure(self):
        """Non-JSON data after command name should be treated as string."""
        result = self.decode("Core.Ping hello world")
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [["hello world"], {}])

    def test_falsy_scalar_zero(self):
        """GMCP payloads of 0 should not be dropped."""
        result = self.decode("Core.Ping 0")
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [[0], {}])

    def test_falsy_scalar_false(self):
        """GMCP payloads of false should not be dropped."""
        result = self.decode("Core.Ping false")
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [[False], {}])

    def test_null_payload(self):
        """GMCP payloads of null should be passed through."""
        result = self.decode("Core.Ping null")
        self.assertIn("ping", result)
        self.assertEqual(result["ping"], [[None], {}])


# ---------------------------------------------------------------------------
# Wire format base
# ---------------------------------------------------------------------------


class TestWireFormatBase(TestCase):
    """Tests for the WireFormat abstract base class."""

    def test_abstract_methods_raise(self):
        from evennia.server.portal.wire_formats.base import WireFormat

        fmt = WireFormat()
        with self.assertRaises(NotImplementedError):
            fmt.decode_incoming(b"", False)
        with self.assertRaises(NotImplementedError):
            fmt.encode_default("cmd")

    def test_encode_prompt_delegates_to_encode_text(self):
        """Default encode_prompt should call encode_text with send_prompt=True."""
        from evennia.server.portal.wire_formats.base import WireFormat

        fmt = WireFormat()
        # Monkey-patch encode_text to verify delegation
        fmt.encode_text = MagicMock(return_value=(b"test", False))
        result = fmt.encode_prompt("hello", options={"raw": False})
        fmt.encode_text.assert_called_once()
        call_kwargs = fmt.encode_text.call_args
        self.assertTrue(call_kwargs.kwargs["options"]["send_prompt"])


# ---------------------------------------------------------------------------
# Evennia V1 wire format
# ---------------------------------------------------------------------------


class TestEvenniaV1Format(TestCase):
    """Tests for the v1.evennia.com wire format."""

    def setUp(self):
        from evennia.server.portal.wire_formats.evennia_v1 import EvenniaV1Format

        self.fmt = EvenniaV1Format()

    def test_name(self):
        self.assertEqual(self.fmt.name, "v1.evennia.com")

    def test_supports_oob(self):
        self.assertTrue(self.fmt.supports_oob)

    # --- decode ---

    def test_decode_text(self):
        payload = json.dumps(["text", ["look"], {}]).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_oob_command(self):
        payload = json.dumps(["logged_in", [], {}]).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertEqual(result, {"logged_in": [[], {}]})

    def test_decode_invalid_json(self):
        result = self.fmt.decode_incoming(b"not json", is_binary=False)
        self.assertIsNone(result)

    def test_decode_short_array(self):
        payload = json.dumps(["text"]).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIsNone(result)

    # --- encode text ---

    def test_encode_text_basic(self):
        result = self.fmt.encode_text("Hello |rworld|n", protocol_flags={})
        self.assertIsNotNone(result)
        data, is_binary = result
        self.assertFalse(is_binary)
        parsed = json.loads(data)
        self.assertEqual(parsed[0], "text")
        # Should contain HTML (from parse_html)
        self.assertIsInstance(parsed[1][0], str)

    def test_encode_text_none(self):
        result = self.fmt.encode_text(None, protocol_flags={})
        self.assertIsNone(result)

    def test_encode_text_no_args(self):
        result = self.fmt.encode_text(protocol_flags={})
        self.assertIsNone(result)

    def test_encode_text_prompt(self):
        result = self.fmt.encode_text("HP: 100", protocol_flags={}, options={"send_prompt": True})
        data, is_binary = result
        parsed = json.loads(data)
        self.assertEqual(parsed[0], "prompt")

    def test_encode_text_nocolor(self):
        result = self.fmt.encode_text(
            "Hello |rworld|n", protocol_flags={}, options={"nocolor": True}
        )
        data, _ = result
        parsed = json.loads(data)
        # With nocolor, ANSI should be stripped
        self.assertNotIn("|r", parsed[1][0])

    # --- encode default (OOB) ---

    def test_encode_default(self):
        result = self.fmt.encode_default("custom_cmd", "arg1", protocol_flags={}, key="val")
        data, is_binary = result
        self.assertFalse(is_binary)
        parsed = json.loads(data)
        self.assertEqual(parsed[0], "custom_cmd")

    def test_encode_default_options_skipped(self):
        """The 'options' command should be silently dropped."""
        result = self.fmt.encode_default("options", protocol_flags={})
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Terminal wire format
# ---------------------------------------------------------------------------


class TestTerminalFormat(TestCase):
    """Tests for the terminal.mudstandards.org wire format."""

    def setUp(self):
        from evennia.server.portal.wire_formats.terminal import TerminalFormat

        self.fmt = TerminalFormat()

    def test_name(self):
        self.assertEqual(self.fmt.name, "terminal.mudstandards.org")

    def test_no_oob(self):
        self.assertFalse(self.fmt.supports_oob)

    # --- decode ---

    def test_decode_binary(self):
        payload = "look".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=True)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_strips_whitespace(self):
        payload = "  look  \n".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=True)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_empty(self):
        result = self.fmt.decode_incoming(b"   ", is_binary=True)
        self.assertIsNone(result)

    def test_decode_invalid_utf8(self):
        result = self.fmt.decode_incoming(b"\xff\xfe", is_binary=True)
        self.assertIsNone(result)

    # --- encode text ---

    def test_encode_text_binary_frame(self):
        result = self.fmt.encode_text("Hello world", protocol_flags={})
        self.assertIsNotNone(result)
        data, is_binary = result
        self.assertTrue(is_binary)
        self.assertIsInstance(data, bytes)

    def test_encode_text_preserves_ansi(self):
        """Terminal format should output real ANSI escape sequences."""
        result = self.fmt.encode_text("Hello |rworld|n", protocol_flags={})
        data, _ = result
        text = data.decode("utf-8")
        # parse_ansi converts |r to ESC[31m (or similar)
        self.assertIn("\033[", text)

    def test_encode_text_none(self):
        result = self.fmt.encode_text(None, protocol_flags={})
        self.assertIsNone(result)

    # --- encode default (OOB) ---

    def test_encode_default_returns_none(self):
        """OOB should be silently dropped for terminal format."""
        result = self.fmt.encode_default("custom_cmd", "arg1", protocol_flags={})
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# JSON MUD Standards wire format
# ---------------------------------------------------------------------------


class TestJsonStandardFormat(TestCase):
    """Tests for the json.mudstandards.org wire format."""

    def setUp(self):
        from evennia.server.portal.wire_formats.json_standard import JsonStandardFormat

        self.fmt = JsonStandardFormat()

    def test_name(self):
        self.assertEqual(self.fmt.name, "json.mudstandards.org")

    def test_supports_oob(self):
        self.assertTrue(self.fmt.supports_oob)

    # --- decode ---

    def test_decode_binary_as_text(self):
        """BINARY frames should be treated as raw text input."""
        payload = "look".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=True)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_binary_empty(self):
        result = self.fmt.decode_incoming(b"   ", is_binary=True)
        self.assertIsNone(result)

    def test_decode_text_envelope(self):
        """TEXT frames should be parsed as JSON envelopes."""
        envelope = {"proto": "text", "id": "", "data": "look around"}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertEqual(result, {"text": [["look around"], {}]})

    def test_decode_gmcp_envelope(self):
        """GMCP-in-JSON envelopes should be decoded."""
        envelope = {"proto": "gmcp", "id": "Core.Ping", "data": ""}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("ping", result)

    def test_decode_gmcp_envelope_with_data(self):
        envelope = {"proto": "gmcp", "id": "Char.Vitals", "data": '{"hp": 100}'}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("char_vitals", result)

    def test_decode_websocket_close(self):
        envelope = {"proto": "websocket_close", "id": "", "data": ""}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("websocket_close", result)

    def test_decode_invalid_json_text_frame(self):
        result = self.fmt.decode_incoming(b"not json", is_binary=False)
        self.assertIsNone(result)

    def test_decode_generic_proto(self):
        """Unknown proto should pass through as-is."""
        envelope = {"proto": "custom", "id": "my_cmd", "data": '{"key": "val"}'}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("my_cmd", result)
        self.assertEqual(result["my_cmd"], [[], {"key": "val"}])

    # --- encode text ---

    def test_encode_text_binary_frame(self):
        """Text should be sent as BINARY frames with raw ANSI."""
        result = self.fmt.encode_text("Hello world", protocol_flags={})
        data, is_binary = result
        self.assertTrue(is_binary)
        self.assertIsInstance(data, bytes)

    def test_encode_text_preserves_ansi(self):
        result = self.fmt.encode_text("Hello |rworld|n", protocol_flags={})
        data, _ = result
        text = data.decode("utf-8")
        self.assertIn("\033[", text)

    # --- encode prompt ---

    def test_encode_prompt_as_json_text_frame(self):
        """Prompts should be JSON envelopes in TEXT frames."""
        result = self.fmt.encode_prompt("HP: 100>", protocol_flags={})
        data, is_binary = result
        self.assertFalse(is_binary)
        envelope = json.loads(data.decode("utf-8"))
        self.assertEqual(envelope["proto"], "prompt")

    # --- encode default (OOB) ---

    def test_encode_default_gmcp_in_json(self):
        """OOB should be encoded as GMCP-in-JSON envelope."""
        result = self.fmt.encode_default("ping", protocol_flags={})
        data, is_binary = result
        self.assertFalse(is_binary)
        envelope = json.loads(data.decode("utf-8"))
        self.assertEqual(envelope["proto"], "gmcp")
        self.assertEqual(envelope["id"], "Core.Ping")

    def test_encode_default_options_skipped(self):
        result = self.fmt.encode_default("options", protocol_flags={})
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# GMCP MUD Standards wire format
# ---------------------------------------------------------------------------


class TestGmcpStandardFormat(TestCase):
    """Tests for the gmcp.mudstandards.org wire format."""

    def setUp(self):
        from evennia.server.portal.wire_formats.gmcp_standard import GmcpStandardFormat

        self.fmt = GmcpStandardFormat()

    def test_name(self):
        self.assertEqual(self.fmt.name, "gmcp.mudstandards.org")

    def test_supports_oob(self):
        self.assertTrue(self.fmt.supports_oob)

    # --- decode ---

    def test_decode_binary_as_text(self):
        payload = "look".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=True)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_text_as_gmcp(self):
        """TEXT frames should be parsed as raw GMCP strings."""
        payload = "Core.Ping".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("ping", result)

    def test_decode_gmcp_with_data(self):
        payload = 'Char.Vitals {"hp": 100}'.encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertIn("char_vitals", result)
        self.assertEqual(result["char_vitals"], [[], {"hp": 100}])

    def test_decode_binary_invalid_utf8(self):
        result = self.fmt.decode_incoming(b"\xff\xfe", is_binary=True)
        self.assertIsNone(result)

    def test_decode_text_invalid_utf8(self):
        result = self.fmt.decode_incoming(b"\xff\xfe", is_binary=False)
        self.assertIsNone(result)

    # --- encode text ---

    def test_encode_text_binary_frame(self):
        result = self.fmt.encode_text("Hello world", protocol_flags={})
        data, is_binary = result
        self.assertTrue(is_binary)
        self.assertIsInstance(data, bytes)

    # --- encode prompt ---

    def test_encode_prompt_binary_frame(self):
        """GMCP format sends prompts as BINARY frames like regular text."""
        result = self.fmt.encode_prompt("HP: 100>", protocol_flags={})
        data, is_binary = result
        self.assertTrue(is_binary)

    # --- encode default (OOB) ---

    def test_encode_default_gmcp_text_frame(self):
        """OOB should be raw GMCP strings in TEXT frames."""
        result = self.fmt.encode_default("ping", protocol_flags={})
        data, is_binary = result
        self.assertFalse(is_binary)
        text = data.decode("utf-8")
        self.assertTrue(text.startswith("Core.Ping"))

    def test_encode_default_with_args(self):
        result = self.fmt.encode_default("ping", "test", protocol_flags={})
        data, _ = result
        text = data.decode("utf-8")
        self.assertIn("Core.Ping", text)
        self.assertIn("test", text)

    def test_encode_default_options_skipped(self):
        result = self.fmt.encode_default("options", protocol_flags={})
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Wire format registry
# ---------------------------------------------------------------------------


class TestWireFormatRegistry(TestCase):
    """Tests for the wire_formats package registry."""

    def test_registry_has_all_formats(self):
        from evennia.server.portal.wire_formats import WIRE_FORMATS

        self.assertIn("v1.evennia.com", WIRE_FORMATS)
        self.assertIn("json.mudstandards.org", WIRE_FORMATS)
        self.assertIn("gmcp.mudstandards.org", WIRE_FORMATS)
        self.assertIn("terminal.mudstandards.org", WIRE_FORMATS)

    def test_registry_order_prefers_json(self):
        """json.mudstandards.org should be first (highest priority)."""
        from evennia.server.portal.wire_formats import WIRE_FORMATS

        keys = list(WIRE_FORMATS.keys())
        self.assertEqual(keys[0], "json.mudstandards.org")

    def test_registry_instances_are_correct_types(self):
        from evennia.server.portal.wire_formats import (
            WIRE_FORMATS,
            EvenniaV1Format,
            GmcpStandardFormat,
            JsonStandardFormat,
            TerminalFormat,
        )

        self.assertIsInstance(WIRE_FORMATS["v1.evennia.com"], EvenniaV1Format)
        self.assertIsInstance(WIRE_FORMATS["json.mudstandards.org"], JsonStandardFormat)
        self.assertIsInstance(WIRE_FORMATS["gmcp.mudstandards.org"], GmcpStandardFormat)
        self.assertIsInstance(WIRE_FORMATS["terminal.mudstandards.org"], TerminalFormat)


# ---------------------------------------------------------------------------
# WebSocket subprotocol negotiation (integration tests)
# ---------------------------------------------------------------------------


class TestWebSocketSubprotocolNegotiation(TestCase):
    """
    Tests for the onConnect() subprotocol negotiation in WebSocketClient.

    These test the negotiation logic in isolation without starting a full
    Twisted reactor, by directly calling onConnect() with mock request objects.
    """

    def _make_client(self):
        """Create a WebSocketClient without connecting it."""
        from evennia.server.portal.webclient import WebSocketClient

        client = WebSocketClient()
        return client

    def _make_request(self, protocols=None):
        """Create a mock ConnectionRequest with the given protocols list."""
        request = Mock()
        request.protocols = protocols or []
        return request

    def test_no_subprotocol_offered(self):
        """Client sends no Sec-WebSocket-Protocol → v1 fallback, returns None."""
        client = self._make_client()
        request = self._make_request(protocols=[])
        result = client.onConnect(request)
        self.assertIsNone(result)
        self.assertIsNotNone(client.wire_format)
        self.assertEqual(client.wire_format.name, "v1.evennia.com")

    def test_v1_subprotocol_offered(self):
        """Client offers v1.evennia.com → selected and returned."""
        client = self._make_client()
        request = self._make_request(protocols=["v1.evennia.com"])
        result = client.onConnect(request)
        self.assertEqual(result, "v1.evennia.com")
        self.assertEqual(client.wire_format.name, "v1.evennia.com")

    def test_json_subprotocol_offered(self):
        client = self._make_client()
        request = self._make_request(protocols=["json.mudstandards.org"])
        result = client.onConnect(request)
        self.assertEqual(result, "json.mudstandards.org")
        self.assertEqual(client.wire_format.name, "json.mudstandards.org")

    def test_gmcp_subprotocol_offered(self):
        client = self._make_client()
        request = self._make_request(protocols=["gmcp.mudstandards.org"])
        result = client.onConnect(request)
        self.assertEqual(result, "gmcp.mudstandards.org")
        self.assertEqual(client.wire_format.name, "gmcp.mudstandards.org")

    def test_terminal_subprotocol_offered(self):
        client = self._make_client()
        request = self._make_request(protocols=["terminal.mudstandards.org"])
        result = client.onConnect(request)
        self.assertEqual(result, "terminal.mudstandards.org")
        self.assertEqual(client.wire_format.name, "terminal.mudstandards.org")

    def test_server_preference_wins(self):
        """When client offers multiple, server's preference order wins."""
        client = self._make_client()
        # Client offers terminal first, but server prefers json
        request = self._make_request(
            protocols=["terminal.mudstandards.org", "json.mudstandards.org"]
        )
        result = client.onConnect(request)
        # Server preference: json > gmcp > terminal > v1
        self.assertEqual(result, "json.mudstandards.org")

    def test_unknown_subprotocol_falls_back(self):
        """Client offers only unknown protocols → v1 fallback."""
        client = self._make_client()
        request = self._make_request(protocols=["unknown.protocol"])
        result = client.onConnect(request)
        self.assertIsNone(result)
        self.assertEqual(client.wire_format.name, "v1.evennia.com")

    def test_mixed_known_and_unknown(self):
        """Client offers unknown + known → known is selected."""
        client = self._make_client()
        request = self._make_request(protocols=["unknown.protocol", "terminal.mudstandards.org"])
        result = client.onConnect(request)
        self.assertEqual(result, "terminal.mudstandards.org")

    def test_empty_subprotocols_setting(self):
        """WEBSOCKET_SUBPROTOCOLS=[] disables negotiation; clients fall back to v1."""
        from evennia.server.portal import webclient

        original = webclient._get_supported_subprotocols
        webclient._get_supported_subprotocols = lambda: []
        try:
            client = self._make_client()
            request = self._make_request(protocols=["json.mudstandards.org"])
            result = client.onConnect(request)
            # No match possible — falls back to v1, returns None
            self.assertIsNone(result)
            self.assertEqual(client.wire_format.name, "v1.evennia.com")
        finally:
            webclient._get_supported_subprotocols = original


# ---------------------------------------------------------------------------
# Integration: full message round-trip through wire formats
# ---------------------------------------------------------------------------


class TestEvenniaV1RoundTrip(TestCase):
    """Test encode → decode round-trip for v1.evennia.com."""

    def setUp(self):
        from evennia.server.portal.wire_formats.evennia_v1 import EvenniaV1Format

        self.fmt = EvenniaV1Format()

    def test_oob_roundtrip(self):
        """Encode an OOB command and decode the result."""
        encoded = self.fmt.encode_default("custom_cmd", "arg1", protocol_flags={})
        data, is_binary = encoded
        # Decode it back
        result = self.fmt.decode_incoming(data, is_binary=is_binary)
        self.assertIn("custom_cmd", result)


class TestGmcpRoundTrip(TestCase):
    """Test encode → decode round-trip for gmcp.mudstandards.org."""

    def setUp(self):
        from evennia.server.portal.wire_formats.gmcp_standard import GmcpStandardFormat

        self.fmt = GmcpStandardFormat()

    def test_oob_roundtrip_no_args(self):
        """Encode a command without args and decode."""
        encoded = self.fmt.encode_default("ping", protocol_flags={})
        data, is_binary = encoded
        result = self.fmt.decode_incoming(data, is_binary=is_binary)
        self.assertIn("ping", result)

    def test_oob_roundtrip_with_kwargs(self):
        """Encode a command with kwargs and decode."""
        encoded = self.fmt.encode_default("get_value", protocol_flags={}, hp=100)
        data, is_binary = encoded
        result = self.fmt.decode_incoming(data, is_binary=is_binary)
        self.assertIn("get_value", result)


class TestJsonStandardRoundTrip(TestCase):
    """Test encode → decode round-trip for json.mudstandards.org."""

    def setUp(self):
        from evennia.server.portal.wire_formats.json_standard import JsonStandardFormat

        self.fmt = JsonStandardFormat()

    def test_oob_roundtrip(self):
        """Encode an OOB command as GMCP-in-JSON and decode."""
        encoded = self.fmt.encode_default("ping", protocol_flags={})
        data, is_binary = encoded
        result = self.fmt.decode_incoming(data, is_binary=is_binary)
        self.assertIn("ping", result)

    def test_prompt_roundtrip(self):
        """Encode a prompt and verify the envelope."""
        encoded = self.fmt.encode_prompt("HP: 100>", protocol_flags={})
        data, is_binary = encoded
        self.assertFalse(is_binary)
        envelope = json.loads(data.decode("utf-8"))
        self.assertEqual(envelope["proto"], "prompt")
        self.assertIn("HP:", envelope["data"])


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------


class TestTerminalEdgeCases(TestCase):
    """Edge-case tests for TerminalFormat."""

    def setUp(self):
        from evennia.server.portal.wire_formats.terminal import TerminalFormat

        self.fmt = TerminalFormat()

    def test_decode_text_frame_treated_as_text(self):
        """TEXT frames should still be decoded as text input."""
        payload = "look".encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        self.assertEqual(result, {"text": [["look"], {}]})

    def test_decode_empty_bytes(self):
        """Empty bytes should return None."""
        result = self.fmt.decode_incoming(b"", is_binary=True)
        self.assertIsNone(result)

    def test_decode_empty_bytes_text_frame(self):
        """Empty TEXT frame bytes should return None."""
        result = self.fmt.decode_incoming(b"", is_binary=False)
        self.assertIsNone(result)


class TestJsonStandardEdgeCases(TestCase):
    """Edge-case tests for JsonStandardFormat."""

    def setUp(self):
        from evennia.server.portal.wire_formats.json_standard import JsonStandardFormat

        self.fmt = JsonStandardFormat()

    def test_decode_envelope_missing_proto(self):
        """JSON envelope with missing proto should use empty string default."""
        envelope = {"id": "my_cmd", "data": "test"}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        # Empty proto, cmd_id="my_cmd" → funcname="my_cmd"
        self.assertIn("my_cmd", result)

    def test_decode_envelope_missing_all_fields(self):
        """JSON envelope with no recognized fields returns None (empty funcname)."""
        payload = json.dumps({}).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        # proto="", cmd_id="", data="" → generic handler, funcname="" → None
        self.assertIsNone(result)

    def test_decode_envelope_missing_id_and_data(self):
        """Envelope with only proto="text" and no data should return None."""
        envelope = {"proto": "text"}
        payload = json.dumps(envelope).encode("utf-8")
        result = self.fmt.decode_incoming(payload, is_binary=False)
        # proto="text", data="" → empty text, treated as no input
        self.assertIsNone(result)

    def test_decode_binary_invalid_utf8(self):
        """Invalid UTF-8 in BINARY frame should return None."""
        result = self.fmt.decode_incoming(b"\xff\xfe", is_binary=True)
        self.assertIsNone(result)


class TestGmcpStandardEdgeCases(TestCase):
    """Edge-case tests for GmcpStandardFormat."""

    def setUp(self):
        from evennia.server.portal.wire_formats.gmcp_standard import GmcpStandardFormat

        self.fmt = GmcpStandardFormat()

    def test_decode_empty_binary(self):
        """Empty BINARY frame should return None."""
        result = self.fmt.decode_incoming(b"", is_binary=True)
        self.assertIsNone(result)

    def test_decode_binary_whitespace_only(self):
        """Whitespace-only BINARY frame should return None."""
        result = self.fmt.decode_incoming(b"   \n  ", is_binary=True)
        self.assertIsNone(result)


class TestBaseWireFormatHelpers(TestCase):
    """Tests for the shared helper methods on WireFormat base class."""

    def setUp(self):
        from evennia.server.portal.wire_formats.base import WireFormat

        self.base = WireFormat()

    def test_extract_text_and_flags_basic(self):
        """Basic extraction with no options or flags."""
        kwargs = {}
        result = self.base._extract_text_and_flags(("hello",), kwargs, {})
        self.assertEqual(result, ("hello", False, False, False))

    def test_extract_text_and_flags_none_text(self):
        """None as text should return None."""
        kwargs = {}
        result = self.base._extract_text_and_flags((None,), kwargs, {})
        self.assertIsNone(result)

    def test_extract_text_and_flags_no_args(self):
        """Empty args should return None."""
        kwargs = {}
        result = self.base._extract_text_and_flags((), kwargs, {})
        self.assertIsNone(result)

    def test_extract_text_and_flags_options_override(self):
        """Options should override protocol_flags."""
        kwargs = {"options": {"nocolor": True, "screenreader": True}}
        result = self.base._extract_text_and_flags(
            ("hello",), kwargs, {"NOCOLOR": False, "SCREENREADER": False}
        )
        self.assertEqual(result, ("hello", False, True, True))

    def test_extract_text_and_flags_raw_option(self):
        """Raw option should be extracted into the result tuple."""
        kwargs = {"options": {"raw": True}}
        result = self.base._extract_text_and_flags(("hello",), kwargs, {})
        self.assertEqual(result, ("hello", True, False, False))

    def test_extract_text_and_flags_raw_protocol_flag(self):
        """RAW protocol flag should be used when option is absent."""
        kwargs = {}
        result = self.base._extract_text_and_flags(("hello",), kwargs, {"RAW": True})
        self.assertEqual(result, ("hello", True, False, False))

    def test_extract_text_and_flags_from_protocol_flags(self):
        """Protocol flags should be used when options are absent."""
        kwargs = {}
        result = self.base._extract_text_and_flags(("hello",), kwargs, {"NOCOLOR": True})
        self.assertEqual(result, ("hello", False, True, False))

    def test_process_ansi_normal(self):
        """Normal mode should produce ANSI escape sequences."""
        text = self.base._process_ansi("Hello |rworld|n", False, False, False)
        self.assertIn("\033[", text)

    def test_process_ansi_nocolor(self):
        """Nocolor mode should strip all ANSI."""
        text = self.base._process_ansi("Hello |rworld|n", False, True, False)
        self.assertNotIn("\033[", text)
        self.assertNotIn("|r", text)

    def test_process_ansi_screenreader(self):
        """Screenreader mode should strip ANSI and apply regex."""
        text = self.base._process_ansi("Hello |rworld|n", False, False, True)
        self.assertNotIn("\033[", text)
        self.assertNotIn("|r", text)

    def test_process_ansi_raw(self):
        """Raw mode should return text unmodified."""
        text = self.base._process_ansi("Hello |rworld|n", True, False, False)
        self.assertEqual(text, "Hello |rworld|n")

    def test_process_ansi_trailing_reset(self):
        """Normal mode should append |n to prevent color bleed."""
        text = self.base._process_ansi("Hello |rworld", False, False, False)
        # Should end with ANSI reset sequence
        self.assertTrue(text.endswith("\033[0m"))

    def test_process_ansi_trailing_pipe_preserved(self):
        """A trailing literal pipe should be preserved, not stripped."""
        text = self.base._process_ansi("choice a|b|", False, False, False)
        # The || escape produces a literal pipe; the |n appends a reset.
        # The important thing is the literal pipe is not lost.
        self.assertIn("|", text.replace("\033[0m", ""))
