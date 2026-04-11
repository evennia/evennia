"""
Evennia V1 wire format (v1.evennia.com).

This is Evennia's legacy WebSocket wire format. All messages are UTF-8
JSON text frames in the form:

    ["cmdname", [args], {kwargs}]

Text output is HTML-converted from ANSI before sending. This format
is used by Evennia's built-in webclient and is the default when no
WebSocket subprotocol is negotiated.
"""

import html
import json

from evennia.utils.ansi import parse_ansi
from evennia.utils.text2html import parse_html

from .base import WireFormat, _RE_SCREENREADER_REGEX


class EvenniaV1Format(WireFormat):
    """
    Evennia's legacy wire format: JSON arrays over TEXT frames.

    Wire format:
        All frames are TEXT (UTF-8 JSON).
        Structure: ["cmdname", [args], {kwargs}]

    Text handling:
        Outgoing text is converted from ANSI to HTML via parse_html().

    OOB:
        All commands are effectively OOB — the cmdname field can be
        any string, not just "text".
    """

    name = "v1.evennia.com"
    supports_oob = True

    def decode_incoming(self, payload, is_binary, protocol_flags=None):
        """
        Decode incoming JSON array message.

        Args:
            payload (bytes): UTF-8 encoded JSON: ["cmdname", [args], {kwargs}]
            is_binary (bool): Should be False for this format.
            protocol_flags (dict, optional): Not used by this format.

        Returns:
            dict or None: kwargs for data_in(), e.g. {"text": [["look"], {}]}

        """
        try:
            cmdarray = json.loads(str(payload, "utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if isinstance(cmdarray, (list, tuple)) and len(cmdarray) >= 3:
            return {cmdarray[0]: [cmdarray[1], cmdarray[2]]}
        return None

    def encode_text(self, *args, protocol_flags=None, **kwargs):
        """
        Encode text output as HTML-converted JSON.

        Converts ANSI color codes to HTML spans, applies screenreader
        and raw text options.

        Returns:
            tuple or None: (json_bytes, False) where False means TEXT frame.

        """
        if args:
            args = list(args)
            text = args[0]
            if text is None:
                return None
        else:
            return None

        flags = protocol_flags or {}
        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        client_raw = options.get("client_raw", False)
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        prompt = options.get("send_prompt", False)

        if screenreader:
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)

        cmd = "prompt" if prompt else "text"
        if raw:
            if client_raw:
                args[0] = text
            else:
                args[0] = html.escape(text)
        else:
            args[0] = parse_html(text, strip_ansi=nocolor)

        return (json.dumps([cmd, args, kwargs]).encode("utf-8"), False)

    def encode_prompt(self, *args, protocol_flags=None, **kwargs):
        """
        Encode a prompt as HTML-converted JSON with send_prompt flag.

        Returns:
            tuple or None: (json_bytes, False) for TEXT frame.

        """
        options = kwargs.get("options", {})
        options["send_prompt"] = True
        kwargs["options"] = options
        return self.encode_text(*args, protocol_flags=protocol_flags, **kwargs)

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        Encode any OOB command as a JSON array.

        Skips the "options" command (legacy behavior).

        Returns:
            tuple or None: (json_bytes, False) for TEXT frame, or None
                if cmdname is "options".

        """
        if cmdname == "options":
            return None
        return (json.dumps([cmdname, args, kwargs]).encode("utf-8"), False)
