"""

MSSP - Mud Server Status Protocol

This implements the MSSP telnet protocol as per
http://tintin.sourceforge.net/mssp/.  MSSP allows web portals and
listings to have their crawlers find the mud and automatically
extract relevant information about it, such as genre, how many
active players and so on.


"""
from django.conf import settings
from evennia.utils import utils

MSSP = b"\x46"
MSSP_VAR = b"\x01"
MSSP_VAL = b"\x02"

# try to get the customized mssp info, if it exists.
MSSPTable_CUSTOM = utils.variable_from_module(settings.MSSP_META_MODULE, "MSSPTable", default={})


class Mssp(object):
    """
    Implements the MSSP protocol. Add this to a variable on the telnet
    protocol to set it up.

    """

    def __init__(self, protocol):
        """
        initialize MSSP by storing protocol on ourselves and calling
        the client to see if it supports MSSP.

        Args:
            protocol (Protocol): The active protocol instance.

        """
        self.protocol = protocol
        self.protocol.will(MSSP).addCallbacks(self.do_mssp, self.no_mssp)

    def get_player_count(self):
        """
        Get number of logged-in players.

        Returns:
            count (int): The number of players in the MUD.

        """
        return str(self.protocol.sessionhandler.count_loggedin())

    def get_uptime(self):
        """
        Get how long the portal has been online (reloads are not counted).

        Returns:
            uptime (int): Number of seconds of uptime.

        """
        return str(self.protocol.sessionhandler.uptime)

    def no_mssp(self, option):
        """
        Called when mssp is not requested. This is the normal
        operation.

        Args:
            option (Option): Not used.

        """
        self.protocol.handshake_done()

    def do_mssp(self, option):
        """
        Negotiate all the information.

        Args:
            option (Option): Not used.

        """

        self.mssp_table = {
            # Required fields
            "NAME": settings.SERVERNAME,
            "PLAYERS": self.get_player_count,
            "UPTIME": self.get_uptime,
            "PORT": list(
                reversed(settings.TELNET_PORTS)
            ),  # most important port should be last in list
            # Evennia auto-filled
            "CRAWL DELAY": "-1",
            "CODEBASE": utils.get_evennia_version(mode="pretty"),
            "FAMILY": "Custom",
            "ANSI": "1",
            "GMCP": "1" if settings.TELNET_OOB_ENABLED else "0",
            "ATCP": "0",
            "MCCP": "1",
            "MCP": "0",
            "MSDP": "1" if settings.TELNET_OOB_ENABLED else "0",
            "MSP": "0",
            "MXP": "1",
            "PUEBLO": "0",
            "SSL": "1" if settings.SSL_ENABLED else "0",
            "UTF-8": "1",
            "ZMP": "0",
            "VT100": "1",
            "XTERM 256 COLORS": "1",
        }

        # update the static table with the custom one
        if MSSPTable_CUSTOM:
            self.mssp_table.update(MSSPTable_CUSTOM)

        varlist = b""
        for variable, value in self.mssp_table.items():
            if callable(value):
                value = value()
            if utils.is_iter(value):
                for partval in value:
                    varlist += (
                        MSSP_VAR + bytes(variable, "utf-8") + MSSP_VAL + bytes(partval, "utf-8")
                    )
            else:
                varlist += MSSP_VAR + bytes(variable, "utf-8") + MSSP_VAL + bytes(value, "utf-8")

        # send to crawler by subnegotiation
        self.protocol.requestNegotiation(MSSP, varlist)
        self.protocol.handshake_done()
