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

    def encode_text(self, *args, protocol_flags=None, **kwargs):
        """
        Encode text output as raw ANSI in a BINARY frame.

        No HTML conversion is performed. ANSI color codes are preserved
        for the client to render.

        Returns:
            tuple or None: (ansi_bytes, True) where True means BINARY frame.

        """
        extracted = self._extract_text_and_flags(args, kwargs, protocol_flags)
        if extracted is None:
            return None
        text, nocolor, screenreader = extracted
        text = self._process_ansi(text, nocolor, screenreader)
        return (text.encode("utf-8"), True)

    def encode_prompt(self, *args, protocol_flags=None, **kwargs):
        """
        Encode a prompt as raw ANSI.

        For terminal mode, prompts are just text — there's no way
        to distinguish them from regular output at the wire level.

        Returns:
            tuple or None: (ansi_bytes, True) for BINARY frame.

        """
        return self.encode_text(*args, protocol_flags=protocol_flags, **kwargs)

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        OOB commands are not supported in terminal mode.

        Returns:
            None: Always returns None (OOB data is silently dropped).

        """
        return None
