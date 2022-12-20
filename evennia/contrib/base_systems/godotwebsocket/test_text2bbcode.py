"""Tests for text2bbcode """

import mock
from django.test import TestCase

from evennia.contrib.base_systems.godotwebsocket import text2bbcode
from evennia.utils import ansi


class TestText2Bbcode(TestCase):
    def test_format_styles(self):
        parser = text2bbcode.BBCODE_PARSER
        self.assertEqual("foo", parser.format_styles("foo"))
        self.assertEqual(
            "[color=#800000]red[/color]foo",
            parser.format_styles(
                ansi.ANSI_UNHILITE + ansi.ANSI_RED + "red" + ansi.ANSI_NORMAL + "foo"
            ),
        )
        self.assertEqual(
            "[bgcolor=#800000]red[/bgcolor]foo",
            parser.format_styles(ansi.ANSI_BACK_RED + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            "[bgcolor=#800000][color=#008000]red[/color][/bgcolor]foo",
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
            "a [u]red[/u]foo",
            parser.format_styles("a " + ansi.ANSI_UNDERLINE + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            "a [blink]red[/blink]foo",
            parser.format_styles("a " + ansi.ANSI_BLINK + "red" + ansi.ANSI_NORMAL + "foo"),
        )
        self.assertEqual(
            "a [bgcolor=#c0c0c0][color=#000000]red[/color][/bgcolor]foo",
            parser.format_styles("a " + ansi.ANSI_INVERSE + "red" + ansi.ANSI_NORMAL + "foo"),
        )

    def test_convert_urls(self):
        parser = text2bbcode.BBCODE_PARSER
        self.assertEqual("foo", parser.convert_urls("foo"))
        self.assertEqual(
            "a [url=http://redfoo]http://redfoo[/url] runs",
            parser.convert_urls("a http://redfoo runs"),
        )

    def test_sub_mxp_links(self):
        parser = text2bbcode.BBCODE_PARSER
        mocked_match = mock.Mock()
        mocked_match.groups.return_value = ["cmd", "text"]

        self.assertEqual("[mxp=send cmd=cmd]text[/mxp]", parser.sub_mxp_links(mocked_match))

    def test_sub_text(self):
        parser = text2bbcode.BBCODE_PARSER

        mocked_match = mock.Mock()

        mocked_match.groupdict.return_value = {"lineend": "foo"}
        self.assertEqual("\n", parser.sub_text(mocked_match))

    def test_parse_bbcode(self):
        self.assertEqual("foo", text2bbcode.parse_to_bbcode("foo"))
        self.maxDiff = None
        self.assertEqual(
            text2bbcode.parse_to_bbcode("|^|[CHello|n|u|rW|go|yr|bl|md|c!|[G!"),
            "[blink][bgcolor=#008080]Hello[/bgcolor][/blink]"
            "[u][color=#ff0000]W[/color][/u]"
            "[u][color=#00ff00]o[/color][/u]"
            "[u][color=#ffff00]r[/color][/u]"
            "[u][color=#0000ff]l[/color][/u]"
            "[u][color=#ff00ff]d[/color][/u]"
            "[u][color=#00ffff]![/color][/u]"
            "[u][bgcolor=#008000][color=#00ffff]![/color][/bgcolor][/u]",
        )
