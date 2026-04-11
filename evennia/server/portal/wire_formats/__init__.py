"""
Wire format codecs for WebSocket subprotocol support.

This package implements the strategy pattern for WebSocket wire formats,
allowing Evennia to support multiple WebSocket subprotocols as defined by
the MUD Standards WebSocket proposal (https://mudstandards.org/websocket/).

Each wire format is a self-contained codec that handles encoding outgoing
data and decoding incoming data for a specific WebSocket subprotocol.

Supported subprotocols:
    - v1.evennia.com: Evennia's legacy JSON array format
    - json.mudstandards.org: MUD Standards JSON envelope format
    - gmcp.mudstandards.org: GMCP over WebSocket
    - terminal.mudstandards.org: Raw ANSI terminal over WebSocket
"""

from .base import WireFormat
from .evennia_v1 import EvenniaV1Format
from .gmcp_standard import GmcpStandardFormat
from .json_standard import JsonStandardFormat
from .terminal import TerminalFormat

# Registry of all available wire formats, keyed by subprotocol name.
# Note: Dict order only affects the default negotiation priority when
# settings.WEBSOCKET_SUBPROTOCOLS is not set (None). When the setting
# is configured, it controls the order in which subprotocols are matched
# against a client's offered list.
WIRE_FORMATS = {
    fmt.name: fmt
    for fmt in [
        JsonStandardFormat(),
        GmcpStandardFormat(),
        TerminalFormat(),
        EvenniaV1Format(),
    ]
}

__all__ = [
    "WireFormat",
    "EvenniaV1Format",
    "JsonStandardFormat",
    "GmcpStandardFormat",
    "TerminalFormat",
    "WIRE_FORMATS",
]
