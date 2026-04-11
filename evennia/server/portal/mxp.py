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
import weakref

from django.conf import settings

LINKS_SUB = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
URL_SUB = re.compile(r"\|lu(.*?)\|lt(.*?)\|le", re.DOTALL)

# MXP Telnet option
MXP = bytes([91])  # b"\x5b"

MXP_TEMPSECURE = "\x1b[4z"
MXP_SEND = MXP_TEMPSECURE + '<SEND HREF="\\1">' + "\\2" + MXP_TEMPSECURE + "</SEND>"
MXP_URL = MXP_TEMPSECURE + '<A HREF="\\1">' + "\\2" + MXP_TEMPSECURE + "</A>"


def mxp_parse(text):
    """
    Parse Evennia's MXP link markup into MXP escape sequences suitable for
    sending to MXP-enabled clients.

    Converts ``|lc<cmd>|lt<label>|le`` to a clickable SEND tag and
    ``|lu<url>|lt<label>|le`` to a clickable URL tag. Non-MXP text
    is left unchanged — MXP clients only interpret tags inside
    secure-mode markers, so surrounding text is treated as literal.

    Messages containing no MXP markup are returned unchanged.

    Args:
        text (str): The text to parse.

    Returns:
        str: The parsed text with MXP sequences substituted, or the
            original text if no MXP markup was found.

    Examples:
        ``|lchelp overview|lthelp overview|le`` becomes
        ``\\x1b[4z<SEND HREF="help overview">help overview\\x1b[4z</SEND>``
    """

    if "|lc" not in text and "|lu" not in text:
        return text

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
        self.protocol = weakref.ref(protocol)
        self.protocol().protocol_flags["MXP"] = False
        if settings.MXP_ENABLED:
            self.protocol().will(MXP).addCallbacks(self.do_mxp, self.no_mxp)

    def no_mxp(self, option):
        """
        Called when the Client reports to not support MXP.

        Args:
            option (Option): Not used.

        """
        self.protocol().protocol_flags["MXP"] = False
        self.protocol().handshake_done()

    def do_mxp(self, option):
        """
        Called when the Client reports to support MXP.

        Args:
            option (Option): Not used.

        """
        if settings.MXP_ENABLED:
            self.protocol().protocol_flags["MXP"] = True
            self.protocol().requestNegotiation(MXP, b"")
        else:
            self.protocol().wont(MXP)
        self.protocol().handshake_done()
