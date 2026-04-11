"""
Base wire format interface for WebSocket subprotocol codecs.

All wire format implementations must subclass WireFormat and implement
the encoding/decoding methods. Each format represents a specific
WebSocket subprotocol as defined by RFC 6455 Sec-WebSocket-Protocol
negotiation.
"""

import re

from django.conf import settings

from evennia.utils.ansi import parse_ansi

_RE_SCREENREADER_REGEX = re.compile(
    r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)
_RE_N = re.compile(r"\|n$")


class WireFormat:
    """
    Abstract base class for WebSocket wire format codecs.

    A wire format handles the translation between Evennia's internal
    message representation and the bytes sent over the WebSocket connection.

    Each subclass corresponds to a specific WebSocket subprotocol name
    (e.g., "v1.evennia.com", "json.mudstandards.org").

    Attributes:
        name (str): The subprotocol identifier string, used in
            Sec-WebSocket-Protocol negotiation.
        supports_oob (bool): Whether this format supports out-of-band
            data (structured commands beyond plain text).

    """

    name = None
    supports_oob = True

    @staticmethod
    def _extract_text_and_flags(args, kwargs, protocol_flags):
        """
        Extract text string and display flags from encode arguments.

        This is a shared helper for encode_text/encode_prompt in formats
        that use raw ANSI output (terminal, json, gmcp). The EvenniaV1
        format has its own logic (HTML conversion, raw mode) and does
        not use this helper.

        Args:
            args (tuple): Positional args passed to encode_text/encode_prompt.
                args[0] should be the text string.
            kwargs (dict): Keyword args. The "options" key is popped and
                inspected for "raw", "nocolor" and "screenreader" overrides.
            protocol_flags (dict or None): Session protocol flags.

        Returns:
            tuple or None: (text, raw, nocolor, screenreader) if text is
                valid, or None if there is no text to encode.

        """
        if args:
            text = args[0]
            if text is None:
                return None
        else:
            return None

        flags = protocol_flags or {}
        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        return (text, raw, nocolor, screenreader)

    @staticmethod
    def _process_ansi(text, raw, nocolor, screenreader):
        """
        Process Evennia ANSI markup into terminal escape sequences.

        Applies screenreader stripping, nocolor stripping, or full ANSI
        conversion depending on the flags. This is the shared logic for
        all non-HTML wire formats (terminal, json, gmcp).

        When raw is True, text is returned unmodified (no ANSI processing).

        For non-raw output, a trailing reset (|n) is appended to prevent
        color/attribute bleed into subsequent output, mirroring the
        TelnetProtocol behavior.

        Args:
            text (str): Text with Evennia ANSI markup (|r, |n, etc.).
            raw (bool): If True, bypass all ANSI processing.
            nocolor (bool): If True, strip all ANSI codes.
            screenreader (bool): If True, strip ANSI and apply
                SCREENREADER_REGEX_STRIP.

        Returns:
            str: Processed text with real ANSI escape sequences,
                stripped text, or raw text.

        """
        if raw:
            return text
        if screenreader:
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)
        elif nocolor:
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
        else:
            # Ensure ANSI state is reset at the end of the string to prevent
            # color/attribute bleed into subsequent output. This mirrors
            # TelnetProtocol/SSH behavior: strip any existing trailing |n,
            # then append ||n (preserving a literal trailing pipe via the ||
            # escape) or |n as appropriate.
            text = _RE_N.sub("", text) + ("||n" if text.endswith("|") else "|n")
            text = parse_ansi(text, xterm256=True, mxp=False)
        return text

    def decode_incoming(self, payload, is_binary, protocol_flags=None):
        """
        Decode an incoming WebSocket message into kwargs for data_in().

        Args:
            payload (bytes): Raw WebSocket message payload.
            is_binary (bool): True if this was a BINARY frame (opcode 2),
                False if it was a TEXT frame (opcode 1).
            protocol_flags (dict, optional): The session's protocol flags,
                which may affect decoding behavior.

        Returns:
            dict or None: A dict of kwargs to pass to session.data_in(),
                where each key is an inputfunc name and value is [args, kwargs].
                Returns None if the message should be silently ignored.

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement decode_incoming()"
        )

    def encode_text(self, *args, protocol_flags=None, **kwargs):
        """
        Encode text output for sending to the client.

        This handles the "text" outputfunc — the primary game output.
        The default implementation processes ANSI markup and returns a
        UTF-8 encoded BINARY frame. Subclasses that need a different
        encoding (e.g. HTML conversion) should override this method.

        Args:
            *args: Text arguments. args[0] is typically the text string.
            protocol_flags (dict, optional): Session protocol flags that
                may affect encoding (e.g., NOCOLOR, SCREENREADER, RAW).
            **kwargs: Additional keyword arguments. May include an
                "options" dict with keys like "raw", "nocolor",
                "screenreader", "send_prompt".

        Returns:
            tuple or None: A (data_bytes, is_binary) tuple for sendMessage(),
                or None if nothing should be sent.

        """
        extracted = self._extract_text_and_flags(args, kwargs, protocol_flags)
        if extracted is None:
            return None
        text, raw, nocolor, screenreader = extracted
        text = self._process_ansi(text, raw, nocolor, screenreader)
        return (text.encode("utf-8"), True)

    def encode_prompt(self, *args, protocol_flags=None, **kwargs):
        """
        Encode a prompt for sending to the client.

        Default implementation delegates to encode_text with the
        send_prompt option set.

        Args:
            *args: Prompt arguments.
            protocol_flags (dict, optional): Session protocol flags.
            **kwargs: Additional keyword arguments. May include an "options"
                dict; if absent, one is created with "send_prompt" set to True.

        Returns:
            tuple or None: A (data_bytes, is_binary) tuple for sendMessage(),
                or None if nothing should be sent.

        """
        options = kwargs.get("options", {})
        options["send_prompt"] = True
        kwargs["options"] = options
        return self.encode_text(*args, protocol_flags=protocol_flags, **kwargs)

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        Encode a non-text OOB command for sending to the client.

        This handles all outputfuncs that don't have a specific send_*
        method, including custom OOB commands.

        Args:
            cmdname (str): The OOB command name.
            *args: Command arguments.
            protocol_flags (dict, optional): Session protocol flags.
            **kwargs: Additional keyword arguments.

        Returns:
            tuple or None: A (data_bytes, is_binary) tuple for sendMessage(),
                or None if nothing should be sent (e.g., if the format
                doesn't support OOB).

        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement encode_default()"
        )
