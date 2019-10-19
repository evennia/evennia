"""Tests for text2html """

from django.test import TestCase
from evennia.utils import ansi, text2html
import mock


class TestText2Html(TestCase):

    def test_re_color(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_color("foo"))
        self.assertEqual(
            "<span class=\"err\">red</span>foo",
            parser.re_color(ansi.ANSI_RED + "red" + ansi.ANSI_NORMAL + "foo"))

    def test_re_bold(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_bold("foo"))
        self.assertEqual(
            # "a <strong>red</strong>foo",  # TODO: why not?
            "a <strong>redfoo</strong>",
            parser.re_bold(
                "a " + ansi.ANSI_HILITE + "red" + ansi.ANSI_UNHILITE + "foo"))

    def test_re_underline(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_underline("foo"))
        self.assertEqual(
            "a <span class=\"underline\">red</span>" + ansi.ANSI_NORMAL + "foo",
            parser.re_underline(
                "a " + ansi.ANSI_UNDERLINE + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"))

    def test_re_blinking(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_blinking("foo"))
        self.assertEqual(
            "a <span class=\"blink\">red</span>" + ansi.ANSI_NORMAL + "foo",
            parser.re_blinking(
                "a " + ansi.ANSI_BLINK + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"))

    def test_re_inversing(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_inversing("foo"))
        self.assertEqual(
            "a <span class=\"inverse\">red</span>" + ansi.ANSI_NORMAL + "foo",
            parser.re_inversing(
                "a " + ansi.ANSI_INVERSE + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"))

    def test_remove_bells(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_bells("foo"))
        self.assertEqual(
            "a red" + ansi.ANSI_NORMAL + "foo",
            parser.remove_bells(
                "a " + ansi.ANSI_BEEP + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"))

    def test_remove_backspaces(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_backspaces("foo"))
        self.assertEqual("redfoo",
            parser.remove_backspaces("a\010redfoo"))

    def test_convert_linebreaks(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_linebreaks("foo"))
        self.assertEqual(
            "a<br> redfoo<br>",
            parser.convert_linebreaks("a\n redfoo\n"))

    def test_convert_urls(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_urls("foo"))
        self.assertEqual(
            "a <a href=\"http://redfoo\" target=\"_blank\">http://redfoo</a> runs",
            parser.convert_urls("a http://redfoo runs"))
            # TODO: doesn't URL encode correctly

    def test_re_double_space(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_double_space("foo"))
        self.assertEqual(
            "a &nbsp;red &nbsp;&nbsp;&nbsp;foo",
            parser.re_double_space("a  red    foo"))
