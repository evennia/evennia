"""Tests for text2html """

import unittest

import mock
from django.test import TestCase

from evennia.utils.html import HTML_PARSER, to_html


class TestText2Html(TestCase):
    def setUp(self):
        self.parser = HTML_PARSER

    def test_convert_markup(self):
        test_chunks = (((('fg_color', 'R'),), 'red'), ((('reset', 'n'),), 'foo'))
        self.assertEqual(
            '<span class="color-001">red</span>foo',
            self.parser.convert_markup( test_chunks ),
        )
    
    def test_parse(self):
        """We do the bulk of the test cases here, since it takes a raw markup string"""
        self.assertEqual("foo", self.parser.parse("foo",))
        self.assertEqual(
            '<span class="color-001">red</span>foo',
            self.parser.parse('|Rred|nfoo'),
        )
        self.assertEqual(
            '<span class="bgcolor-001">red</span>foo',
            self.parser.parse('|[Rred|nfoo'),
        )
        self.assertEqual(
            '<span class="bgcolor-001 color-002">red</span>foo',
            self.parser.parse('|[R|Gred|nfoo'),
        )
        self.assertEqual(
            'a <span class="underline">red</span>foo',
            self.parser.parse('a |ured|nfoo'),
        )
        self.assertEqual(
            'a <span class="bgcolor-007 color-000">red</span>foo',
            self.parser.parse('a |*red|nfoo'),
        )

    def test_convert_linebreaks(self):
        self.assertEqual("foo", self.parser.convert_linebreaks("foo"))
        self.assertEqual("a<br> redfoo<br>", self.parser.convert_linebreaks("a\n redfoo\n"))

    def test_convert_urls(self):
        self.assertEqual("foo", self.parser.convert_urls("foo"))
        self.assertEqual(
            'a <a href="http://redfoo" target="_blank">http://redfoo</a> runs',
            self.parser.convert_urls("a http://redfoo runs"),
        )

    @unittest.skip
    def test_sub_text(self):
        mocked_match = mock.Mock()

        mocked_match.groupdict.return_value = {"htmlchars": "foo"}
        self.assertEqual("foo", self.parser.sub_text(mocked_match))

        mocked_match.groupdict.return_value = {"htmlchars": "", "lineend": "foo"}
        self.assertEqual("<br>", self.parser.sub_text(mocked_match))

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

    def test_to_html(self):
        """Test entire parse mechanism"""
        self.assertEqual("foo", to_html("foo"))
        self.maxDiff = None
        self.assertEqual(
            to_html("|^|[CHello|n|u|rW|go|yr|bl|md|c!|[G!"),
            '<span class="bgcolor-006 blink">'
            "Hello"
            '</span><span class="color-009 underline">'
            "W"
            '</span><span class="color-010 underline">'
            "o"
            '</span><span class="color-011 underline">'
            "r"
            '</span><span class="color-012 underline">'
            "l"
            '</span><span class="color-013 underline">'
            "d"
            '</span><span class="color-014 underline">'
            "!"
            '</span><span class="bgcolor-002 color-014 underline">'
            "!"
            "</span>",
        )


class TestURLSchemes(TestCase):
    def setUp(self):
        self.parser = HTML_PARSER

    def tearDown(self):
        del self.parser

    def test_url_scheme_ftp(self):
        self.assertEqual(
            self.parser.convert_urls("ftp.example.com"),
            '<a href="http://ftp.example.com" target="_blank">ftp.example.com</a>',
        )

    def test_url_scheme_www(self):
        self.assertEqual(
            self.parser.convert_urls("www.example.com"),
            '<a href="http://www.example.com" target="_blank">www.example.com</a>',
        )

    def test_url_scheme_ftpproto(self):
        self.assertEqual(
            self.parser.convert_urls("ftp://ftp.example.com"),
            '<a href="ftp://ftp.example.com" target="_blank">ftp://ftp.example.com</a>',
        )

    def test_url_scheme_http(self):
        self.assertEqual(
            self.parser.convert_urls("http://example.com"),
            '<a href="http://example.com" target="_blank">http://example.com</a>',
        )

    def test_url_scheme_https(self):
        self.assertEqual(
            self.parser.convert_urls("https://example.com"),
            '<a href="https://example.com" target="_blank">https://example.com</a>',
        )

    def test_url_chars_slash(self):
        self.assertEqual(
            self.parser.convert_urls("www.example.com/homedir"),
            '<a href="http://www.example.com/homedir" target="_blank">www.example.com/homedir</a>',
        )

    def test_url_chars_colon(self):
        self.assertEqual(
            self.parser.convert_urls("https://example.com:8000/login/"),
            '<a href="https://example.com:8000/login/" target="_blank">'
            "https://example.com:8000/login/</a>",
        )

    def test_url_chars_querystring(self):
        self.assertEqual(
            self.parser.convert_urls("https://example.com/submitform?field1=val1+val3&field2=val2"),
            '<a href="https://example.com/submitform?field1=val1+val3&field2=val2" target="_blank">'
            "https://example.com/submitform?field1=val1+val3&field2=val2</a>",
        )

    def test_url_chars_anchor(self):
        self.assertEqual(
            self.parser.convert_urls("http://www.example.com/menu#section_1"),
            '<a href="http://www.example.com/menu#section_1" target="_blank">'
            "http://www.example.com/menu#section_1</a>",
        )

    def test_url_chars_exclam(self):
        self.assertEqual(
            self.parser.convert_urls(
                "https://groups.google.com/forum/" "?fromgroups#!categories/evennia/ainneve"
            ),
            '<a href="https://groups.google.com/forum/?fromgroups#!categories/evennia/ainneve"'
            ' target="_blank">https://groups.google.com/forum/?fromgroups#!categories/evennia/ainneve</a>',
        )

    def test_url_edge_following_period_eol(self):
        self.assertEqual(
            self.parser.convert_urls("www.example.com."),
            '<a href="http://www.example.com" target="_blank">www.example.com</a>.',
        )

    def test_url_edge_following_period(self):
        self.assertEqual(
            self.parser.convert_urls("see www.example.com. "),
            'see <a href="http://www.example.com" target="_blank">www.example.com</a>. ',
        )

    def test_url_edge_brackets(self):
        self.assertEqual(
            self.parser.convert_urls("[http://example.com/]"),
            '[<a href="http://example.com/" target="_blank">http://example.com/</a>]',
        )

    def test_url_edge_multiline(self):
        self.assertEqual(
            self.parser.convert_urls("  * http://example.com/info\n  * bullet"),
            '  * <a href="http://example.com/info" target="_blank">'
            "http://example.com/info</a>\n  * bullet",
        )

    def test_url_edge_following_htmlentity(self):
        self.assertEqual(
            self.parser.convert_urls("http://example.com/info&lt;span&gt;"),
            '<a href="http://example.com/info" target="_blank">http://example.com/info</a>&lt;span&gt;',
        )

    def test_url_edge_surrounded_spans(self):
        self.assertEqual(
            self.parser.convert_urls('</span>http://example.com/<span class="red">'),
            '</span><a href="http://example.com/" target="_blank">'
            'http://example.com/</a><span class="red">',
        )

    def test_non_url_with_www(self):
        self.assertEqual(
            self.parser.convert_urls("Awwww.this should not be highlighted"),
            "Awwww.this should not be highlighted",
        )

    def test_invalid_www_url(self):
        self.assertEqual(self.parser.convert_urls("www.t"), "www.t")
