try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

try:
    from django.utils import unittest
except ImportError:
    import unittest

import sys
import string
import mock
from mock import Mock, MagicMock
from evennia.server.portal import irc

from twisted.conch.telnet import IAC, WILL, DONT, SB, SE, NAWS, DO
from twisted.test import proto_helpers
from twisted.trial.unittest import TestCase as TwistedTestCase

from .telnet import TelnetServerFactory, TelnetProtocol
from .portal import PORTAL_SESSIONS
from .suppress_ga import SUPPRESS_GA
from .naws import DEFAULT_HEIGHT, DEFAULT_WIDTH
from .ttype import TTYPE, IS
from .mccp import MCCP
from .mssp import MSSP
from .mxp import MXP
from .telnet_oob import MSDP, MSDP_VAL, MSDP_VAR

from .amp import AMPMultiConnectionProtocol, MsgServer2Portal, MsgPortal2Server, AMP_MAXLEN
from .amp_server import AMPServerFactory


class TestAMPServer(TwistedTestCase):
    """
    Test AMP communication
    """

    def setUp(self):
        super(TestAMPServer, self).setUp()
        portal = Mock()
        factory = AMPServerFactory(portal)
        self.proto = factory.buildProtocol(("localhost", 0))
        self.transport = MagicMock()  # proto_helpers.StringTransport()
        self.transport.client = ["localhost"]
        self.transport.write = MagicMock()

    def test_amp_out(self):
        self.proto.makeConnection(self.transport)

        self.proto.data_to_server(MsgServer2Portal, 1, test=2)
        byte_out = (
            b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgServer2Portal\x00\x0b"
            b"packed_data\x00 x\xdak`\x99*\xc8\x00\x01\xde\x8c\xb5SzXJR"
            b"\x8bK\xa6x3\x15\xb7M\xd1\x03\x00V:\x07t\x00\x00"
        )
        self.transport.write.assert_called_with(byte_out)
        with mock.patch("evennia.server.portal.amp.amp.AMP.dataReceived") as mocked_amprecv:
            self.proto.dataReceived(byte_out)
            mocked_amprecv.assert_called_with(byte_out)

    def test_amp_in(self):
        self.proto.makeConnection(self.transport)

        self.proto.data_to_server(MsgPortal2Server, 1, test=2)
        byte_out = (
            b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgPortal2Server\x00\x0b"
            b"packed_data\x00 x\xdak`\x99*\xc8\x00\x01\xde\x8c\xb5SzXJR"
            b"\x8bK\xa6x3\x15\xb7M\xd1\x03\x00V:\x07t\x00\x00"
        )
        self.transport.write.assert_called_with(byte_out)
        with mock.patch("evennia.server.portal.amp.amp.AMP.dataReceived") as mocked_amprecv:
            self.proto.dataReceived(byte_out)
            mocked_amprecv.assert_called_with(byte_out)

    def test_large_msg(self):
        """
        Send message larger than AMP_MAXLEN - should be split into several
        """
        self.proto.makeConnection(self.transport)
        outstr = "test" * AMP_MAXLEN
        self.proto.data_to_server(MsgServer2Portal, 1, test=outstr)

        if sys.version < "3.7":
            self.transport.write.assert_called_with(
                b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgServer2Portal\x00\x0bpacked_data"
                b"\x00xx\xda\xed\xc6\xc1\t\x800\x10\x00\xc1\x13\xaf\x01\xeb\xb2\x01\x1bH"
                b'\x05\xe6+X\x80\xcf\xd8m@I\x1d\x99\x85\x81\xbd\xf3\xdd"c\xb4/W{'
                b"\xb2\x96\xb3\xb6\xa3\x7fk\x8c\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00`\x0e?Pv\x02\x16\x00\r"
                b"packed_data.2\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08\xc0\xa0\xb4&\xf0\xfdg\x10a"
                b"\xa3\xd9RUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU\xf5\xfb"
                b"\x03m\xe0\x06\x1d\x00\rpacked_data.3\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08\xc0\xa0"
                b"\xb4&\xf0\xfdg\x10a\xa3fSUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"
                b"UUUUU\xf5\xfb\x03n\x1c\x06\x1e\x00\rpacked_data.4\x00Zx\xda\xed\xc3\x01\t\x00"
                b"\x00\x0c\x03\xa0\xb4O\xb0\xf5gA\xae`\xda\x8b\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xdf\x0fnI"
                b"\x06,\x00\rpacked_data.5\x00\x14x\xdaK-.)I\xc5\x8e\xa7\x14\xb7M\xd1\x03\x00"
                b"\xe7s\x0e\x1c\x00\x00"
            )
        else:
            self.transport.write.assert_called_with(
                b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgServer2Portal\x00\x0bpacked_data"
                b"\x00wx\xda\xed\xc6\xc1\t\x80 \x00@Q#o\x8e\xd6\x02-\xe0\x04z\r\x1a\xa0\xa3m+$\xd2"
                b"\x18\xbe\x0f\x0f\xfe\x1d\xdf\x14\xfe\x8e\xedjO\xac\xb9\xd4v\xf6o\x0f\xf3\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00X\xc3\x00P\x10\x02\x0c\x00\rpacked_data.2\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08"
                b"\xc0\xa0\xb4&\xf0\xfdg\x10a\xa3\xd9RUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"
                b"\xf5\xfb\x03m\xe0\x06\x1d\x00\rpacked_data.3\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08"
                b"\xc0\xa0\xb4&\xf0\xfdg\x10a\xa3fSUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU"
                b"\xf5\xfb\x03n\x1c\x06\x1e\x00\rpacked_data.4\x00Zx\xda\xed\xc3\x01\t\x00\x00\x0c"
                b"\x03\xa0\xb4O\xb0\xf5gA\xae`\xda\x8b\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xdf\x0fnI\x06,\x00\rpacked_data.5"
                b"\x00\x18x\xdaK-.)I\xc5\x8e\xa7\xb22@\xc0\x94\xe2\xb6)z\x00Z\x1e\x0e\xb6\x00\x00"
            )


class TestIRC(TestCase):
    def test_plain_ansi(self):
        """
        Test that printable characters do not get mangled.
        """
        irc_ansi = irc.parse_ansi_to_irc(string.printable)
        ansi_irc = irc.parse_irc_to_ansi(string.printable)
        self.assertEqual(irc_ansi, string.printable)
        self.assertEqual(ansi_irc, string.printable)

    def test_bold(self):
        s_irc = "\x02thisisatest"
        s_eve = r"|hthisisatest"
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)
        self.assertEqual(s_eve, irc.parse_irc_to_ansi(s_irc))

    def test_italic(self):
        s_irc = "\x02thisisatest"
        s_eve = r"|hthisisatest"
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)

    def test_colors(self):
        color_map = (
            ("\0030", r"|w"),
            ("\0031", r"|X"),
            ("\0032", r"|B"),
            ("\0033", r"|G"),
            ("\0034", r"|r"),
            ("\0035", r"|R"),
            ("\0036", r"|M"),
            ("\0037", r"|Y"),
            ("\0038", r"|y"),
            ("\0039", r"|g"),
            ("\00310", r"|C"),
            ("\00311", r"|c"),
            ("\00312", r"|b"),
            ("\00313", r"|m"),
            ("\00314", r"|x"),
            ("\00315", r"|W"),
            ("\00399,5", r"|[r"),
            ("\00399,3", r"|[g"),
            ("\00399,7", r"|[y"),
            ("\00399,2", r"|[b"),
            ("\00399,6", r"|[m"),
            ("\00399,10", r"|[c"),
            ("\00399,15", r"|[w"),
            ("\00399,1", r"|[x"),
        )

        for m in color_map:
            self.assertEqual(irc.parse_irc_to_ansi(m[0]), m[1])
            self.assertEqual(m[0], irc.parse_ansi_to_irc(m[1]))

    def test_identity(self):
        """
        Test that the composition of the function and
        its inverse gives the correct string.
        """

        s = r"|wthis|Xis|gis|Ma|C|complex|*string"

        self.assertEqual(irc.parse_irc_to_ansi(irc.parse_ansi_to_irc(s)), s)


class TestTelnet(TwistedTestCase):
    def setUp(self):
        super(TestTelnet, self).setUp()
        factory = TelnetServerFactory()
        factory.protocol = TelnetProtocol
        factory.sessionhandler = PORTAL_SESSIONS
        factory.sessionhandler.portal = Mock()
        self.proto = factory.buildProtocol(("localhost", 0))
        self.transport = proto_helpers.StringTransport()
        self.addCleanup(factory.sessionhandler.disconnect_all)

    def test_mudlet_ttype(self):
        self.transport.client = ["localhost"]
        self.transport.setTcpKeepAlive = Mock()
        d = self.proto.makeConnection(self.transport)
        # test suppress_ga
        self.assertTrue(self.proto.protocol_flags["NOGOAHEAD"])
        self.proto.dataReceived(IAC + DONT + SUPPRESS_GA)
        self.assertFalse(self.proto.protocol_flags["NOGOAHEAD"])
        self.assertEqual(self.proto.handshakes, 7)
        # test naws
        self.assertEqual(self.proto.protocol_flags["SCREENWIDTH"], {0: DEFAULT_WIDTH})
        self.assertEqual(self.proto.protocol_flags["SCREENHEIGHT"], {0: DEFAULT_HEIGHT})
        self.proto.dataReceived(IAC + WILL + NAWS)
        self.proto.dataReceived(b"".join([IAC, SB, NAWS, b"", b"x", b"", b"d", IAC, SE]))
        self.assertEqual(self.proto.protocol_flags["SCREENWIDTH"][0], 78)
        self.assertEqual(self.proto.protocol_flags["SCREENHEIGHT"][0], 45)
        self.assertEqual(self.proto.handshakes, 6)
        # test ttype
        self.assertTrue(self.proto.protocol_flags["FORCEDENDLINE"])
        self.assertFalse(self.proto.protocol_flags["TTYPE"])
        self.assertTrue(self.proto.protocol_flags["ANSI"])
        self.proto.dataReceived(IAC + WILL + TTYPE)
        self.proto.dataReceived(b"".join([IAC, SB, TTYPE, IS, b"MUDLET", IAC, SE]))
        self.assertTrue(self.proto.protocol_flags["XTERM256"])
        self.assertEqual(self.proto.protocol_flags["CLIENTNAME"], "MUDLET")
        self.proto.dataReceived(b"".join([IAC, SB, TTYPE, IS, b"XTERM", IAC, SE]))
        self.proto.dataReceived(b"".join([IAC, SB, TTYPE, IS, b"MTTS 137", IAC, SE]))
        self.assertEqual(self.proto.handshakes, 5)
        # test mccp
        self.proto.dataReceived(IAC + DONT + MCCP)
        self.assertFalse(self.proto.protocol_flags["MCCP"])
        self.assertEqual(self.proto.handshakes, 4)
        # test mssp
        self.proto.dataReceived(IAC + DONT + MSSP)
        self.assertEqual(self.proto.handshakes, 3)
        # test oob
        self.proto.dataReceived(IAC + DO + MSDP)
        self.proto.dataReceived(
            b"".join([IAC, SB, MSDP, MSDP_VAR, b"LIST", MSDP_VAL, b"COMMANDS", IAC, SE])
        )
        self.assertTrue(self.proto.protocol_flags["OOB"])
        self.assertEqual(self.proto.handshakes, 2)
        # test mxp
        self.proto.dataReceived(IAC + DONT + MXP)
        self.assertFalse(self.proto.protocol_flags["MXP"])
        self.assertEqual(self.proto.handshakes, 1)
        # clean up to prevent Unclean reactor
        self.proto.nop_keep_alive.stop()
        self.proto._handshake_delay.cancel()
        return d
