"""
GMCP MUD Standards wire format (gmcp.mudstandards.org).

This implements the GMCP subprotocol from the MUD Standards WebSocket
proposal (https://mudstandards.org/websocket/).

Per the standard:
    - BINARY frames contain regular ANSI in- and output (UTF-8 encoded)
    - TEXT frames contain UTF-8 encoded GMCP commands in the standard
      format: "Package.Name json_payload"

This is a good match for MUD clients that natively speak GMCP, such as
Mudlet, as it maps directly to their existing GMCP handling without
the extra JSON envelope layer.
"""

from evennia.server.portal.gmcp_utils import decode_gmcp, encode_gmcp

from .base import WireFormat


class GmcpStandardFormat(WireFormat):
    """
    GMCP-native wire format over WebSocket.

    Wire format:
        BINARY frames: Raw ANSI text (UTF-8), used for game text I/O.
        TEXT frames: GMCP commands in standard format
            "Package.Name json_payload"

    Text handling:
        Outgoing text retains ANSI escape codes (no HTML conversion).
        Text is sent as BINARY frames.

    OOB:
        Supported via TEXT frames carrying GMCP messages. The GMCP
        format is: "Package.Name optional_json_payload"
    """

    name = "gmcp.mudstandards.org"
    supports_oob = True

    def decode_incoming(self, payload, is_binary, protocol_flags=None):
        """
        Decode incoming WebSocket message.

        BINARY frames are raw text input.
        TEXT frames are GMCP messages.

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
            # TEXT frame = GMCP command
            try:
                gmcp_data = payload.decode("utf-8")
            except UnicodeDecodeError:
                return None
            return decode_gmcp(gmcp_data)

    def encode_default(self, cmdname, *args, protocol_flags=None, **kwargs):
        """
        Encode an OOB command as a GMCP message in a TEXT frame.

        Args:
            cmdname (str): The OOB command name.
            *args: Command arguments.
            protocol_flags (dict, optional): Not used.
            **kwargs: Command keyword arguments.

        Returns:
            tuple or None: (gmcp_bytes, False) for TEXT frame, or None
                if cmdname is "options".

        """
        if cmdname == "options":
            return None

        kwargs.pop("options", None)

        gmcp_string = encode_gmcp(cmdname, *args, **kwargs)
        return (gmcp_string.encode("utf-8"), False)
