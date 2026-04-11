"""
Terminal wire format (terminal.mudstandards.org).

This implements the simplest MUD Standards WebSocket subprotocol:
raw ANSI/UTF-8 text in BINARY frames. No OOB support.

Per the MUD Standards proposal:
    "BINARY frames contain input/output and ANSI control codes.
     Encoded as UTF-8"

This format is suitable for basic terminal-style MUD clients that
want raw ANSI output without any structured data channel.
"""

from .base import WireFormat


class TerminalFormat(WireFormat):
    """
    Raw ANSI terminal wire format over BINARY WebSocket frames.

    Wire format:
        All frames are BINARY, containing UTF-8 ANSI text.
        No TEXT frames are used.

    Text handling:
        Outgoing text retains ANSI escape codes (no HTML conversion).
        ANSI is rendered by the client.

    OOB:
        Not supported. This format has no structured data channel.
    """

    name = "terminal.mudstandards.org"
    supports_oob = False

    def decode_incoming(self, payload, is_binary, protocol_flags=None):
        """
        Decode incoming WebSocket frame as raw text input.

        Both BINARY and TEXT frames are treated identically as UTF-8 text.

        Args:
            payload (bytes): Raw UTF-8 text from the client.
            is_binary (bool): True for BINARY frames, False for TEXT.
                Both are handled identically.
            protocol_flags (dict, optional): Not used.

        Returns:
            dict or None: {"text": [[text_string], {}]}

        """
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

        text = text.strip()
        if not text:
            return None

        return {"text": [[text], {}]}

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        OOB commands are not supported in terminal mode.

        Returns:
            None: Always returns None (OOB data is silently dropped).

        """
        return None
