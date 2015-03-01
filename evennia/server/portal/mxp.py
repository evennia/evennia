"""
MXP - Mud eXtension Protocol.

Partial implementation of the MXP protocol.
The MXP protocol allows more advanced formatting options for telnet clients
that supports it (mudlet, zmud, mushclient are a few)

This only implements the SEND tag.

More information can be found on the following links:
http://www.zuggsoft.com/zmud/mxp.htm
http://www.mushclient.com/mushclient/mxp.htm
http://www.gammon.com.au/mushclient/addingservermxp.htm
"""
import re

LINKS_SUB =  re.compile(r'\{lc(.*?)\{lt(.*?)\{le', re.DOTALL)

MXP = "\x5B"
MXP_TEMPSECURE = "\x1B[4z"
MXP_SEND = MXP_TEMPSECURE + \
           "<SEND HREF='\\1'>" + \
           "\\2" + \
           MXP_TEMPSECURE + \
           "</SEND>"

def mxp_parse(text):
    """
    Replaces links to the correct format for MXP.
    """
    text = text.replace("&", "&amp;") \
               .replace("<", "&lt;") \
               .replace(">", "&gt;")

    text = LINKS_SUB.sub(MXP_SEND, text)
    return text

class Mxp(object):
    """
    Implements the MXP protocol.
    """

    def __init__(self, protocol):
        """Initializes the protocol by checking if the client supports it."""
        self.protocol = protocol
        self.protocol.protocol_flags["MXP"] = False
        self.protocol.will(MXP).addCallbacks(self.do_mxp, self.no_mxp)

    def no_mxp(self, option):
        """
        Client does not support MXP.
        """
        self.protocol.protocol_flags["MXP"] = False
        self.protocol.handshake_done()

    def do_mxp(self, option):
        """
        Client does support MXP.
        """
        self.protocol.protocol_flags["MXP"] = True
        self.protocol.handshake_done()
        self.protocol.requestNegotiation(MXP, '')
