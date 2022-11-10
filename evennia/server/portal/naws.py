"""

NAWS - Negotiate About Window Size

This implements the NAWS telnet option as per
https://www.ietf.org/rfc/rfc1073.txt

NAWS allows telnet clients to report their current window size to the
client and update it when the size changes

"""
from codecs import encode as codecs_encode

from django.conf import settings

NAWS = bytes([31])  # b"\x1f"
IS = bytes([0])  # b"\x00"

# default taken from telnet specification
DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
DEFAULT_HEIGHT = settings.CLIENT_DEFAULT_HEIGHT

# try to get the customized mssp info, if it exists.


class Naws:
    """
    Implements the NAWS protocol. Add this to a variable on the telnet
    protocol to set it up.

    """

    def __init__(self, protocol):
        """
        initialize NAWS by storing protocol on ourselves and calling
        the client to see if it supports NAWS.

        Args:
            protocol (Protocol): The active protocol instance.

        """
        self.naws_step = 0
        self.protocol = protocol
        self.protocol.protocol_flags["SCREENWIDTH"] = {
            0: DEFAULT_WIDTH
        }  # windowID (0 is root):width
        self.protocol.protocol_flags["SCREENHEIGHT"] = {0: DEFAULT_HEIGHT}  # windowID:width
        self.protocol.negotiationMap[NAWS] = self.negotiate_sizes
        self.protocol.do(NAWS).addCallbacks(self.do_naws, self.no_naws)

    def no_naws(self, option):
        """
        Called when client is not reporting NAWS. This is the normal
        operation.

        Args:
            option (Option): Not used.

        """
        self.protocol.handshake_done()

    def do_naws(self, option):
        """
        Client wants to negotiate all the NAWS information.

        Args:
            option (Option): Not used.

        """
        self.protocol.handshake_done()

    def negotiate_sizes(self, options):
        """
        Step through the NAWS handshake.

        Args:
            option (list): The incoming NAWS options.

        """
        if len(options) == 4:
            # NAWS is negotiated with 16bit words
            width = options[0] + options[1]
            self.protocol.protocol_flags["SCREENWIDTH"][0] = int(codecs_encode(width, "hex"), 16)
            height = options[2] + options[3]
            self.protocol.protocol_flags["SCREENHEIGHT"][0] = int(codecs_encode(height, "hex"), 16)
