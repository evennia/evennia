"""

MCCP - Mud Client Compression Protocol

This implements the MCCP v2 telnet protocol as per
http://tintin.sourceforge.net/mccp/. MCCP allows for the server to
compress data when sending to supporting clients, reducing bandwidth
by 70-90%.. The compression is done using Python's builtin zlib
library. If the client doesn't support MCCP, server sends uncompressed
as normal.  Note: On modern hardware you are not likely to notice the
effect of MCCP unless you have extremely heavy traffic or sits on a
terribly slow connection.

This protocol is implemented by the telnet protocol importing
mccp_compress and calling it from its write methods.
"""
import zlib

# negotiations for v1 and v2 of the protocol
MCCP = b"\x56"
FLUSH = zlib.Z_SYNC_FLUSH


def mccp_compress(protocol, data):
    """
    Handles zlib compression, if applicable.

    Args:
        data (str): Incoming data to compress.

    Returns:
        stream (binary): Zlib-compressed data.

    """
    if hasattr(protocol, "zlib"):
        return protocol.zlib.compress(data) + protocol.zlib.flush(FLUSH)
    return data


class Mccp(object):
    """
    Implements the MCCP protocol. Add this to a
    variable on the telnet protocol to set it up.

    """

    def __init__(self, protocol):
        """
        initialize MCCP by storing protocol on
        ourselves and calling the client to see if
        it supports MCCP. Sets callbacks to
        start zlib compression in that case.

        Args:
            protocol (Protocol): The active protocol instance.

        """

        self.protocol = protocol
        self.protocol.protocol_flags["MCCP"] = False
        # ask if client will mccp, connect callbacks to handle answer
        self.protocol.will(MCCP).addCallbacks(self.do_mccp, self.no_mccp)

    def no_mccp(self, option):
        """
        Called if client doesn't support mccp or chooses to turn it off.

        Args:
            option (Option): Option dict (not used).

        """
        if hasattr(self.protocol, "zlib"):
            del self.protocol.zlib
        self.protocol.protocol_flags["MCCP"] = False
        self.protocol.handshake_done()

    def do_mccp(self, option):
        """
        The client supports MCCP. Set things up by
        creating a zlib compression stream.

        Args:
            option (Option): Option dict (not used).

        """
        self.protocol.protocol_flags["MCCP"] = True
        self.protocol.requestNegotiation(MCCP, b"")
        self.protocol.zlib = zlib.compressobj(9)
        self.protocol.handshake_done()
