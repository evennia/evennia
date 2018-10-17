try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

try:
    from django.utils import unittest
except ImportError:
    import unittest

from mock import Mock
import string
from evennia.server.portal import irc

from twisted.test import proto_helpers
from twisted.trial.unittest import TestCase as TwistedTestCase

from .telnet import TelnetServerFactory, TelnetProtocol
from .portal import PORTAL_SESSIONS


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
        s_eve = r'|hthisisatest'
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)
        self.assertEqual(s_eve, irc.parse_irc_to_ansi(s_irc))

    def test_italic(self):
        s_irc = "\x02thisisatest"
        s_eve = r'|hthisisatest'
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)

    def test_colors(self):
        color_map = (("\0030",     r'|w'),
                     ("\0031",     r'|X'),
                     ("\0032",     r'|B'),
                     ("\0033",     r'|G'),
                     ("\0034",     r'|r'),
                     ("\0035",     r'|R'),
                     ("\0036",     r'|M'),
                     ("\0037",     r'|Y'),
                     ("\0038",     r'|y'),
                     ("\0039",     r'|g'),
                     ("\00310",    r'|C'),
                     ("\00311",    r'|c'),
                     ("\00312",    r'|b'),
                     ("\00313",    r'|m'),
                     ("\00314",    r'|x'),
                     ("\00315",    r'|W'),
                     ("\00399,5",  r'|[r'),
                     ("\00399,3",  r'|[g'),
                     ("\00399,7",  r'|[y'),
                     ("\00399,2",  r'|[b'),
                     ("\00399,6",  r'|[m'),
                     ("\00399,10", r'|[c'),
                     ("\00399,15", r'|[w'),
                     ("\00399,1",  r'|[x'))

        for m in color_map:
            self.assertEqual(irc.parse_irc_to_ansi(m[0]), m[1])
            self.assertEqual(m[0], irc.parse_ansi_to_irc(m[1]))

    def test_identity(self):
        """
        Test that the composition of the function and
        its inverse gives the correct string.
        """

        s = r'|wthis|Xis|gis|Ma|C|complex|*string'

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

    def test_connect(self):
        self.transport.client = ["localhost"]
        self.transport.setTcpKeepAlive = Mock()
        d = self.proto.makeConnection(self.transport)
        # TODO: Add rest of stuff for testing connection
        # clean up to prevent Unclean reactor
        self.proto.nop_keep_alive.stop()
        self.proto._handshake_delay.cancel()
        return d
