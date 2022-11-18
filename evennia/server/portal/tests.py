try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

try:
    from django.utils import unittest
except ImportError:
    import unittest

import json
import pickle
import string
import sys

import mock
from autobahn.twisted.websocket import WebSocketServerFactory
from mock import MagicMock, Mock
from twisted.conch.telnet import DO, DONT, IAC, NAWS, SB, SE, WILL
from twisted.internet.base import DelayedCall
from twisted.test import proto_helpers
from twisted.trial.unittest import TestCase as TwistedTestCase

from evennia.server.portal import irc
from evennia.utils.test_resources import BaseEvenniaTest

from .amp import (
    AMP_MAXLEN,
    AMPMultiConnectionProtocol,
    MsgPortal2Server,
    MsgServer2Portal,
)
from .amp_server import AMPServerFactory
from .mccp import MCCP
from .mssp import MSSP
from .mxp import MXP
from .naws import DEFAULT_HEIGHT, DEFAULT_WIDTH
from .portal import PORTAL_SESSIONS
from .suppress_ga import SUPPRESS_GA
from .telnet import TelnetProtocol, TelnetServerFactory
from .telnet_oob import MSDP, MSDP_VAL, MSDP_VAR
from .ttype import IS, TTYPE
from .webclient import WebSocketClient


class TestAMPServer(TwistedTestCase):
    """
    Test AMP communication
    """

    def setUp(self):
        super().setUp()
        portal = Mock()
        factory = AMPServerFactory(portal)
        self.proto = factory.buildProtocol(("localhost", 0))
        self.transport = MagicMock()  # proto_helpers.StringTransport()
        self.transport.client = ["localhost"]
        self.transport.write = MagicMock()

    def test_amp_out(self):
        self.proto.makeConnection(self.transport)

        self.proto.data_to_server(MsgServer2Portal, 1, test=2)

        if pickle.HIGHEST_PROTOCOL == 5:
            # Python 3.8+
            byte_out = (
                b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgServer2Portal\x00\x0b"
                b"packed_data\x00 x\xdak`\x9d*\xc8\x00\x01\xde\x8c\xb5SzXJR"
                b"\x8bK\xa6x3\x15\xb7M\xd1\x03\x00VU\x07u\x00\x00"
            )
        elif pickle.HIGHEST_PROTOCOL == 4:
            # Python 3.7
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
        if pickle.HIGHEST_PROTOCOL == 5:
            # Python 3.8+
            byte_out = (
                b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgPortal2Server\x00\x0b"
                b"packed_data\x00 x\xdak`\x9d*\xc8\x00\x01\xde\x8c\xb5SzXJR"
                b"\x8bK\xa6x3\x15\xb7M\xd1\x03\x00VU\x07u\x00\x00"
            )
        elif pickle.HIGHEST_PROTOCOL == 4:
            # Python 3.7
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

        if pickle.HIGHEST_PROTOCOL == 5:
            # Python 3.8+
            self.transport.write.assert_called_with(
                b"\x00\x04_ask\x00\x011\x00\x08_command\x00\x10MsgServer2Portal\x00\x0bpacked_data"
                b"\x00wx\xda\xed\xc6\xc1\t\x80 \x00@Q#=5Z\x0b\xb8\x80\x13\xe85h\x80\x8e\xbam`Dc\xf4><\xf8g"
                b"\x1a[\xf8\xda\x97\xa3_\xb1\x95\xdaz\xbe\xe7\x1a\xde\x03\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe0\x1f\x1eP\x1d\x02\r\x00\rpacked_data.2"
                b"\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08\xc0\xa0\xb4&\xf0\xfdg\x10a\xa3"
                b"\xd9RUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU\xf5\xfb\x03m\xe0\x06"
                b"\x1d\x00\rpacked_data.3\x00Zx\xda\xed\xc3\x01\r\x00\x00\x08\xc0\xa0\xb4&\xf0\xfdg\x10a"
                b"\xa3fSUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU\xf5\xfb\x03n\x1c"
                b"\x06\x1e\x00\rpacked_data.4\x00Zx\xda\xed\xc3\x01\t\x00\x00\x0c\x03\xa0\xb4O\xb0\xf5gA"
                b"\xae`\xda\x8b\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa"
                b"\xaa\xaa\xaa\xdf\x0fnI\x06,\x00\rpacked_data.5\x00\x18x\xdaK-.)I\xc5\x8e\xa7\xb22@\xc0"
                b"\x94\xe2\xb6)z\x00Z\x1e\x0e\xb6\x00\x00"
            )
        elif pickle.HIGHEST_PROTOCOL == 4:
            # Python 3.7
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
        super().setUp()
        factory = TelnetServerFactory()
        factory.protocol = TelnetProtocol
        factory.sessionhandler = PORTAL_SESSIONS
        factory.sessionhandler.portal = Mock()
        self.proto = factory.buildProtocol(("localhost", 0))
        self.transport = proto_helpers.StringTransport()
        self.addCleanup(factory.sessionhandler.disconnect_all)

    @mock.patch("evennia.server.portal.portalsessionhandler.reactor", new=MagicMock())
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
        self.assertFalse(self.proto.protocol_flags["TTYPE"])
        self.assertTrue(self.proto.protocol_flags["ANSI"])
        self.proto.dataReceived(IAC + WILL + TTYPE)
        self.proto.dataReceived(b"".join([IAC, SB, TTYPE, IS, b"MUDLET", IAC, SE]))
        self.assertTrue(self.proto.protocol_flags["XTERM256"])
        self.assertEqual(self.proto.protocol_flags["CLIENTNAME"], "MUDLET")
        self.assertTrue(self.proto.protocol_flags["FORCEDENDLINE"])
        self.assertTrue(self.proto.protocol_flags["NOGOAHEAD"])
        self.assertFalse(self.proto.protocol_flags["NOPROMPTGOAHEAD"])
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


class TestWebSocket(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.proto = WebSocketClient()
        self.proto.factory = WebSocketServerFactory()
        self.proto.factory.sessionhandler = PORTAL_SESSIONS
        self.proto.sessionhandler = PORTAL_SESSIONS
        self.proto.sessionhandler.portal = Mock()
        self.proto.transport = proto_helpers.StringTransport()
        # self.proto.transport = proto_helpers.FakeDatagramTransport()
        self.proto.transport.client = ["localhost"]
        self.proto.transport.setTcpKeepAlive = Mock()
        self.proto.state = MagicMock()
        self.addCleanup(self.proto.factory.sessionhandler.disconnect_all)
        DelayedCall.debug = True

    def tearDown(self):
        super().tearDown()

    @mock.patch("evennia.server.portal.portalsessionhandler.reactor", new=MagicMock())
    def test_data_in(self):
        self.proto.sessionhandler.data_in = MagicMock()
        self.proto.onOpen()
        msg = json.dumps(["logged_in", (), {}]).encode()
        self.proto.onMessage(msg, isBinary=False)
        self.proto.sessionhandler.data_in.assert_called_with(self.proto, logged_in=[[], {}])
        sendStr = "You can get anything you want at Alice's Restaurant."
        msg = json.dumps(["text", (sendStr,), {}]).encode()
        self.proto.onMessage(msg, isBinary=False)
        self.proto.sessionhandler.data_in.assert_called_with(self.proto, text=[[sendStr], {}])

    @mock.patch("evennia.server.portal.portalsessionhandler.reactor", new=MagicMock())
    def test_data_out(self):
        self.proto.onOpen()
        self.proto.sendLine = MagicMock()
        msg = json.dumps(["logged_in", (), {}])
        self.proto.sessionhandler.data_out(self.proto, text=[["Excepting Alice"], {}])
        self.proto.sendLine.assert_called_with(json.dumps(["text", ["Excepting Alice"], {}]))
