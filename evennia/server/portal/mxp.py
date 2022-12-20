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

from django.conf import settings

LINKS_SUB = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
URL_SUB = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)

# MXP Telnet option
MXP = bytes([91])  # b"\x5b"

MXP_TEMPSECURE = "\x1B[4z"
MXP_SEND = MXP_TEMPSECURE + '<SEND HREF="\\1">' + "\\2" + MXP_TEMPSECURE + "</SEND>"
MXP_URL = MXP_TEMPSECURE + '<A HREF="\\1">' + "\\2" + MXP_TEMPSECURE + "</A>"


def mxp_parse(text):
    """
    Replaces links to the correct format for MXP.

    Args:
        text (str): The text to parse.

    Returns:
        parsed (str): The parsed text.

    """
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = LINKS_SUB.sub(MXP_SEND, text)
    text = URL_SUB.sub(MXP_URL, text)
    return text


class Mxp:
    """
    Implements the MXP protocol.

    """

    def __init__(self, protocol):
        """
        Initializes the protocol by checking if the client supports it.

        Args:
            protocol (Protocol): The active protocol instance.

        """
        self.protocol = protocol
        self.protocol.protocol_flags["MXP"] = False
        if settings.MXP_ENABLED:
            self.protocol.will(MXP).addCallbacks(self.do_mxp, self.no_mxp)

    def no_mxp(self, option):
        """
        Called when the Client reports to not support MXP.

        Args:
            option (Option): Not used.

        """
        self.protocol.protocol_flags["MXP"] = False
        self.protocol.handshake_done()

    def do_mxp(self, option):
        """
        Called when the Client reports to support MXP.

        Args:
            option (Option): Not used.

        """
        if settings.MXP_ENABLED:
            self.protocol.protocol_flags["MXP"] = True
            self.protocol.requestNegotiation(MXP, b"")
        else:
            self.protocol.wont(MXP)
        self.protocol.handshake_done()
