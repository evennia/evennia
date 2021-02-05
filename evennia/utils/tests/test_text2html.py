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

        parser.tabstop = 2
        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "tab": "\t",
            "space": "",
        }
        self.assertEqual(" &nbsp;", parser.sub_text(mocked_match))

        mocked_match.groupdict.return_value = {
            "htmlchars": "",
            "lineend": "",
            "tab": "\t\t",
            "space": " ",
            "spacestart": " ",
        }
        self.assertEqual(" &nbsp; &nbsp;",
                         parser.sub_text(mocked_match))

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
        self.assertEqual(parser.parse("foo|>foo"),
                         "foo &nbsp;&nbsp;&nbsp;foo")

        # space and tab
        self.assertEqual(parser.parse("foo |>foo"),
                         "foo &nbsp;&nbsp;&nbsp;&nbsp;foo")

        # space, tab, space
        self.assertEqual(parser.parse("foo |> foo"),
                         "foo &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;foo")

    def test_parse_space_to_html(self):
        """test space parsing - a single space should be kept, two or more
        should get &nbsp;"""
        parser = text2html.HTML_PARSER
        # single space
        self.assertEqual(parser.parse("foo foo"),
                         "foo foo")
        # double space
        self.assertEqual(parser.parse("foo  foo"),
                         "foo &nbsp;foo")
        # triple space
        self.assertEqual(parser.parse("foo   foo"),
                         "foo &nbsp;&nbsp;foo")

    def test_parse_html(self):
        self.assertEqual("foo", text2html.parse_html("foo"))
        self.maxDiff = None
        self.assertEqual(
            # TODO: note that the blink is currently *not* correctly aborted
            # with |n here! This is probably not possible to correctly handle
            # with regex - a stateful parser may be needed.
            # blink back-cyan normal underline red green yellow blue magenta cyan back-green
            text2html.parse_html("|^|[CHello|n|u|rW|go|yr|bl|md|c!|[G!"),
            '<span class="blink">'
                '<span class="bgcolor-006">Hello</span>'   # noqa
                '<span class="underline">'
                    '<span class="color-009">W</span>'     # noqa
                    '<span class="color-010">o</span>'
                    '<span class="color-011">r</span>'
                    '<span class="color-012">l</span>'
                    '<span class="color-013">d</span>'
                    '<span class="color-014">!'
                        '<span class="bgcolor-002">!</span>'  # noqa
                    '</span>'
                '</span>'
            '</span>'
        )
