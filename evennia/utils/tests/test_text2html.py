"""Tests for text2html """

import unittest

import mock
from django.test import TestCase

from evennia.utils import ansi, text2html


class TestText2Html(TestCase):
    def test_format_styles(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.format_styles("foo"))
        self.assertEqual(
            '<span class="color-001">red</span>foo',
            parser.format_styles(
                ansi.ANSI_UNHILITE + ansi.ANSI_RED + "red" + ansi.ANSI_NORMAL + "foo"
            ),
        )
        self.assertEqual(
            '<span class="bgcolor-001">red</span>foo',
            parser.format_styles(ansi.ANSI_BACK_RED + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            '<span class="bgcolor-001 color-002">red</span>foo',
            parser.format_styles(
                ansi.ANSI_BACK_RED
                + ansi.ANSI_UNHILITE
                + ansi.ANSI_GREEN
                + "red"
                + ansi.ANSI_NORMAL
                + "foo"
            ),
        )
        self.assertEqual(
            'a <span class="underline">red</span>foo',
            parser.format_styles("a " + ansi.ANSI_UNDERLINE + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            'a <span class="blink">red</span>foo',
            parser.format_styles("a " + ansi.ANSI_BLINK + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            'a <span class="bgcolor-007 color-000">red</span>foo',
            parser.format_styles("a " + ansi.ANSI_INVERSE + "red" + ansi.ANSI_NORMAL + "foo"),
        )

    def test_remove_bells(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_bells("foo"))
        self.assertEqual(
            "a red" + ansi.ANSI_NORMAL + "foo",
            parser.remove_bells("a " + ansi.ANSI_BEEP + "red" + ansi.ANSI_NORMAL + "foo"),
        )

    def test_remove_backspaces(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.remove_backspaces("foo"))
        self.assertEqual("redfoo", parser.remove_backspaces("a\010redfoo"))

    def test_convert_linebreaks(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_linebreaks("foo"))
        self.assertEqual("a<br> redfoo<br>", parser.convert_linebreaks("a\n redfoo\n"))

    def test_convert_urls(self):
        parser = text2html.HTML_PARSER
        self.assertEqual("foo", parser.convert_urls("foo"))
        self.assertEqual(
            'a <a href="http://redfoo" target="_blank">http://redfoo</a> runs',
            parser.convert_urls("a http://redfoo runs"),
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

        parser.tabstop = 2
        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "tab": "\t",
            "space": "",
        }
        self.assertEqual("  ", parser.sub_text(mocked_match))

        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "tab": "\t\t",
            "space": " ",
            "spacestart": " ",
        }
        self.assertEqual("    ", parser.sub_text(mocked_match))

        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "tab": "",
            "space": "",
            "spacestart": "",
        }
        self.assertEqual(None, parser.sub_text(mocked_match))

    def test_parse_tab_to_html(self):
        """Test entire parse mechanism"""
        parser = text2html.HTML_PARSER
        parser.tabstop = 4
        # single tab
        self.assertEqual(parser.parse("foo|>foo"), "foo    foo")

        # space and tab
        self.assertEqual(parser.parse("foo |>foo"), "foo     foo")

        # space, tab, space
        self.assertEqual(parser.parse("foo |> foo"), "foo      foo")

    def test_parse_html(self):
        self.assertEqual("foo", text2html.parse_html("foo"))
        self.maxDiff = None
        self.assertEqual(
            text2html.parse_html("|^|[CHello|n|u|rW|go|yr|bl|md|c!|[G!"),
            '<span class="blink bgcolor-006">'
            "Hello"
            '</span><span class="underline color-009">'
            "W"
            '</span><span class="underline color-010">'
            "o"
            '</span><span class="underline color-011">'
            "r"
            '</span><span class="underline color-012">'
            "l"
            '</span><span class="underline color-013">'
            "d"
            '</span><span class="underline color-014">'
            "!"
            '</span><span class="underline bgcolor-002 color-014">'
            "!"
            "</span>",
        )
