"""
JSON MUD Standards wire format (json.mudstandards.org).

This implements the JSON subprotocol from the MUD Standards WebSocket
proposal (https://mudstandards.org/websocket/).

Per the standard:
    - BINARY frames contain regular ANSI in- and output (UTF-8 encoded)
    - TEXT frames contain JSON payloads with the structure:
        {"proto": "<string>", "id": "<string>", "data": "<string>"}

This is the most flexible standard format, supporting GMCP, custom
protocols, and any future structured data through the JSON envelope.
"""

import json

from evennia.server.portal.gmcp_utils import decode_gmcp, encode_gmcp

from .base import WireFormat


class JsonStandardFormat(WireFormat):
    """
    MUD Standards JSON envelope wire format.

    Wire format:
        BINARY frames: Raw ANSI text (UTF-8), used for game text I/O.
        TEXT frames: JSON envelope {"proto", "id", "data"} for
            structured/OOB data.

    Text handling:
        Outgoing text retains ANSI escape codes (no HTML conversion).
        Text is sent as BINARY frames.

    OOB:
        Supported via TEXT frames. The "proto" field identifies the
        protocol (e.g., "gmcp"), "id" identifies the command, and
        "data" carries the JSON payload.
    """

    name = "json.mudstandards.org"
    supports_oob = True

    def decode_incoming(self, payload, is_binary, protocol_flags=None):
        """
        Decode incoming WebSocket message.

        BINARY frames are treated as raw text input.
        TEXT frames are parsed as JSON envelopes.

        Args:
            payload (bytes): The raw frame payload.
            is_binary (bool): True for BINARY frames, False for TEXT.
            protocol_flags (dict, optional): Not used.

        Returns:
            dict or None: kwargs for data_in().

        """
        if is_binary:
            # BINARY frame = raw text input
            try:
                text = payload.decode("utf-8").strip()
            except UnicodeDecodeError:
                return None
            if not text:
                return None
            return {"text": [[text], {}]}
        else:
            # TEXT frame = JSON envelope
            try:
                envelope = json.loads(payload.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None

            if not isinstance(envelope, dict):
                return None

            proto = envelope.get("proto", "")
            cmd_id = envelope.get("id", "")
            data = envelope.get("data", "")

            # Validate envelope field types — malformed envelopes are dropped
            if not isinstance(proto, str):
                return None
            if not isinstance(cmd_id, str):
                cmd_id = str(cmd_id) if cmd_id is not None else ""
            if not isinstance(data, str):
                try:
                    data = json.dumps(data)
                except (TypeError, ValueError):
                    data = str(data)

            return self._decode_envelope(proto, cmd_id, data)

    def _decode_envelope(self, proto, cmd_id, data):
        """
        Decode a JSON envelope into Evennia inputfunc kwargs.

        Args:
            proto (str): The protocol identifier (e.g., "gmcp", "text").
            cmd_id (str): The command identifier (e.g., GMCP package name).
            data (str): The payload string.

        Returns:
            dict or None: kwargs for data_in().

        """
        if proto == "gmcp":
            # GMCP: id is the package name, data is the JSON payload
            cmd_id = cmd_id.strip()
            if not cmd_id:
                return None
            gmcp_string = "%s %s" % (cmd_id, data) if data else cmd_id
            return decode_gmcp(gmcp_string)

        elif proto == "text":
            # Text input sent via JSON envelope
            if not data:
                return None
            return {"text": [[data], {}]}

        elif proto == "websocket_close":
            return {"websocket_close": [[], {}]}

        else:
            # Generic protocol — pass through as-is.
            # Prefer cmd_id as the inputfunc name, fall back to proto.
            try:
                parsed_data = json.loads(data) if data else {}
            except (json.JSONDecodeError, ValueError):
                parsed_data = data

            args = []
            kwargs = {}
            if isinstance(parsed_data, dict):
                kwargs = parsed_data
            elif isinstance(parsed_data, list):
                args = parsed_data
            else:
                args = [parsed_data]

            funcname = cmd_id if cmd_id else proto
            if not funcname:
                return None
            return {funcname: [args, kwargs]}

    def encode_prompt(self, *args, protocol_flags=None, **kwargs):
        """
        Encode a prompt.

        For the JSON standard format, prompts are sent as a JSON envelope
        in a TEXT frame with proto="prompt", allowing the client to
        distinguish prompts from regular text.

        Returns:
            tuple or None: (json_bytes, False) for TEXT frame.

        """
        extracted = self._extract_text_and_flags(args, kwargs, protocol_flags)
        if extracted is None:
            return None
        text, raw, nocolor, screenreader = extracted
        text = self._process_ansi(text, raw, nocolor, screenreader)

        envelope = {
            "proto": "prompt",
            "id": "",
            "data": text,
        }
        return (json.dumps(envelope).encode("utf-8"), False)

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        Encode an OOB command as a GMCP-in-JSON envelope.

        OOB commands are sent as TEXT frames with the JSON envelope format.
        The command is translated to GMCP naming conventions and wrapped
        in a {"proto": "gmcp", "id": "Package.Name", "data": "..."} envelope.

        Args:
            cmdname (str): The OOB command name.
            *args: Command arguments.
            protocol_flags (dict, optional): Not used.
            **kwargs: Command keyword arguments.

        Returns:
            tuple or None: (json_bytes, False) for TEXT frame, or None
                if cmdname is "options".

        """
        if cmdname == "options":
            return None

        kwargs.pop("options", None)

        # Encode as GMCP string first, then wrap in JSON envelope
        gmcp_string = encode_gmcp(cmdname, *args, **kwargs)

        # Split the GMCP string into package name and payload
        parts = gmcp_string.split(None, 1)
        gmcp_package = parts[0]
        gmcp_data = parts[1] if len(parts) > 1 else ""

        envelope = {
            "proto": "gmcp",
            "id": gmcp_package,
            "data": gmcp_data,
        }
        return (json.dumps(envelope).encode("utf-8"), False)
