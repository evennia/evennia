"""Tests for text2html """

import unittest
from django.test import TestCase
from evennia.utils import ansi, text2html
import mock


class TestText2Html(TestCase):
    def test_re_color(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_color("foo"))
        self.assertEqual(
            '<span class="color-001">red</span>foo',
            parser.re_color(ansi.ANSI_UNHILITE + ansi.ANSI_RED + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            '<span class="bgcolor-001">red</span>foo',
            parser.re_color(ansi.ANSI_BACK_RED + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            '<span class="bgcolor-001"><span class="color-002">red</span></span>foo',
            parser.re_color(
                ansi.ANSI_BACK_RED
                + ansi.ANSI_UNHILITE
                + ansi.ANSI_GREEN
                + "red"
                + ansi.ANSI_NORMAL
                + "foo"
            ),
        )

    @unittest.skip("parser issues")
    def test_re_bold(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_bold("foo"))
        self.assertEqual(
            # "a <strong>red</strong>foo",  # TODO: why not?
            "a <strong>redfoo</strong>",
            parser.re_bold("a " + ansi.ANSI_HILITE + "red" + ansi.ANSI_UNHILITE + "foo"),
        )

    @unittest.skip("parser issues")
    def test_re_underline(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_underline("foo"))
        self.assertEqual(
            'a <span class="underline">red</span>' + ansi.ANSI_NORMAL + "foo",
            parser.re_underline(
                "a "
                + ansi.ANSI_UNDERLINE
                + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"
            ),
        )

    @unittest.skip("parser issues")
    def test_re_blinking(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_blinking("foo"))
        self.assertEqual(
            'a <span class="blink">red</span>' + ansi.ANSI_NORMAL + "foo",
            parser.re_blinking(
                "a "
                + ansi.ANSI_BLINK
                + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"
            ),
        )

    @unittest.skip("parser issues")
    def test_re_inversing(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_inversing("foo"))
        self.assertEqual(
            'a <span class="inverse">red</span>' + ansi.ANSI_NORMAL + "foo",
            parser.re_inversing(
                "a "
                + ansi.ANSI_INVERSE
                + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"
            ),
        )

    @unittest.skip("parser issues")
    def test_remove_bells(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_bells("foo"))
        self.assertEqual(
            "a red" + ansi.ANSI_NORMAL + "foo",
            parser.remove_bells(
                "a "
                + ansi.ANSI_BEEP
                + "red"
                + ansi.ANSI_NORMAL  # TODO: why does it keep it?
                + "foo"
            ),
        )

    def test_remove_backspaces(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_backspaces("foo"))
        self.assertEqual("redfoo", parser.remove_backspaces("a\010redfoo"))

    def test_convert_linebreaks(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_linebreaks("foo"))
        self.assertEqual("a<br> redfoo<br>", parser.convert_linebreaks("a\n redfoo\n"))

    @unittest.skip("parser issues")
    def test_convert_urls(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_urls("foo"))
        self.assertEqual(
            'a <a href="http://redfoo" target="_blank">http://redfoo</a> runs',
            parser.convert_urls("a http://redfoo runs"),
        )
        # TODO: doesn't URL encode correctly

    def test_re_double_space(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.re_double_space("foo"))
        self.assertEqual(
            "a &nbsp;red &nbsp;&nbsp;&nbsp;foo", parser.re_double_space("a  red    foo")
        )

    def test_sub_mxp_links(self):
        parser = text2html.HTML_PARSER
        mocked_match = mock.Mock()
        mocked_match.groups.return_value = ["cmd", "text"]
        self.assertEqual(
            r"""<a id="mxplink" href="#" """
            """onclick="Evennia.msg(&quot;text&quot;,[&quot;cmd&quot;],{});"""
            """return false;">text</a>""",
            parser.sub_mxp_links(mocked_match),
        )

    def test_sub_text(self):
        parser = text2html.HTML_PARSER
        mocked_match = mock.Mock()
        mocked_match.groupdict.return_value = {"htmlchars": "foo"}
        self.assertEqual("foo", parser.sub_text(mocked_match))
        mocked_match.groupdict.return_value = {"htmlchars": "", "lineend": "foo"}
        self.assertEqual("<br>", parser.sub_text(mocked_match))
        mocked_match.groupdict.return_value = {"htmlchars": "", "lineend": "", "firstspace": "foo"}
        self.assertEqual(" &nbsp;", parser.sub_text(mocked_match))
        parser.tabstop = 2
        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "firstspace": "",
            "space": "\t",
        }
        self.assertEqual(" &nbsp;&nbsp;", parser.sub_text(mocked_match))
        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "firstspace": "",
            "space": " ",
            "spacestart": " ",
        }
        mocked_match.group.return_value = " \t "
        self.assertEqual("&nbsp;&nbsp;&nbsp;&nbsp;", parser.sub_text(mocked_match))
        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "firstspace": "",
            "space": "",
            "spacestart": "",
        }
        self.assertEqual(None, parser.sub_text(mocked_match))

    def test_parse_html(self):
        self.assertEqual("foo", text2html.parse_html("foo"))
        self.maxDiff = None
        self.assertEqual(
            """<span class="blink"><span class="bgcolor-006">Hello </span><span class="underline"><span class="err">W</span><span class="err">o</span><span class="err">r</span><span class="err">l</span><span class="err">d</span><span class="err">!<span class="bgcolor-002">!</span></span></span></span>""",
            text2html.parse_html(
                ansi.ANSI_BLINK
                + ansi.ANSI_BACK_CYAN
                + "Hello "
                + ansi.ANSI_NORMAL
                + ansi.ANSI_UNDERLINE
                + ansi.ANSI_RED
                + "W"
                + ansi.ANSI_GREEN
                + "o"
                + ansi.ANSI_YELLOW
                + "r"
                + ansi.ANSI_BLUE
                + "l"
                + ansi.ANSI_MAGENTA
                + "d"
                + ansi.ANSI_CYAN
                + "!"
                + ansi.ANSI_BACK_GREEN
                + "!"
            ),
        )
