"""

NAWS - Negotiate About Window Size

This implements the NAWS telnet option as per
https://www.ietf.org/rfc/rfc1073.txt

NAWS allows telnet clients to report their
current window size to the client and update
it when the size changes

"""
from django.conf import settings

NAWS = chr(31)
IS = chr(0)
# default taken from telnet specification
DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
DEFAULT_HEIGHT = settings.CLIENT_DEFAULT_HEIGHT

# try to get the customized mssp info, if it exists.

class Naws(object):
    """
    Implements the MSSP protocol. Add this to a
    variable on the telnet protocol to set it up.
    """
    def __init__(self, protocol):
        """
        initialize NAWS by storing protocol on ourselves
        and calling the client to see if it supports
        NAWS.
        """
        self.naws_step = 0
        self.protocol = protocol
        self.protocol.protocol_flags['SCREENWIDTH'] = {0: DEFAULT_WIDTH} # windowID (0 is root):width
        self.protocol.protocol_flags['SCREENHEIGHT'] = {0: DEFAULT_HEIGHT} # windowID:width
        self.protocol.negotiationMap[NAWS] = self.negotiate_sizes
        self.protocol.do(NAWS).addCallbacks(self.do_naws, self.no_naws)

    def no_naws(self, option):
        """
        This is the normal operation.
        """
        self.protocol.handshake_done()

    def do_naws(self, option):
        """
        Negotiate all the information.
        """
        self.protocol.handshake_done()

    def negotiate_sizes(self, options):
        if len(options) == 4:
           # NAWS is negotiated with 16bit words
           width = options[0] + options[1]
           self.protocol.protocol_flags['SCREENWIDTH'][0] = int(width.encode('hex'), 16)
           height = options[2] + options[3]
           self.protocol.protocol_flags['SCREENHEIGHT'][0] = int(height.encode('hex'), 16)

