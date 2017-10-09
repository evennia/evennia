try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

try:
    from django.utils import unittest
except ImportError:
    import unittest

import string
from evennia.server.portal import irc


class TestIRC(TestCase):

    def test_plain_ansi(self):
        """
        Test that printable characters do not get mangled.
        """
        irc_ansi = irc.parse_ansi_to_irc(string.printable)
        ansi_irc = irc.parse_irc_to_ansi(string.printable)
        self.assertEqual(irc_ansi, string.printable)
        self.assertEqual(ansi_irc, string.printable)

    def test_evennia_strings(self):
        pass

    def test_irc_string(self):
        pass

    def test_bold(self):
        s_irc = "\x02thisisatest"
        s_eve = r'|hthisisatest'
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)
        self.assertEqual(s_eve, irc.prase_irc_to_ansi(s_irc))
    
    def test_italic(self):
        s_irc = "\x02thisisatest"
        s_eve = r'|hthisisatest'
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)

    def test_colors(self):
        color_map = (("\0030",  r'|w'), 
                     ("\0031",  r'|X'), 
                     ("\0032",  r'|B'), 
                     ("\0033", r'|G'),
                     ("\0034", r'|r'),
                     ("\0035", r'|R'),
                     ("\0036",  r'|M'),
                     ("\0037", r'|Y'),
                     ("\0038",  r'|y'),
                     ("\0039",  r'|g'),
                     ("\00310",  r'|C'),
                     ("\00311",  r'|c'),
                     ("\00312",  r'|b'),
                     ("\00313",  r'|m'),
                     ("\00314", r'|x'),
                     ("\00315", r'|W'))
 

        for m in color_map:
            self.assertEqual(irc.parse_irc_to_ansi(m[0]), m[1])
            self.assertEqual(m[0], irc.parse_ansi_to_irc(m[1]))

    
    def test_bold(self):
        s_irc = "\002thisisatest"
        s_eve = r'|hthisisatest'
        self.assertEqual(irc.parse_ansi_to_irc(s_eve), s_irc)
        self.assertEqual(s_eve, irc.parse_irc_to_ansi(s_irc))

    def test_underlined(self):
        pass

    def test_identity(self):
        """
        Test that the composition of the function and
        its inverse gives the correct string
        """
        pass
