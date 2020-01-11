"""
Unit tests for all sorts of inline text-tag parsing, like ANSI, html conversion, inlinefuncs etc

"""
import re
from django.test import TestCase
from evennia.utils.ansi import ANSIString
from evennia.utils.text2html import TextToHTMLparser
from evennia.utils import inlinefuncs


class ANSIStringTestCase(TestCase):
    def checker(self, ansi, raw, clean):
        """
        Verifies the raw and clean strings of an ANSIString match expected
        output.
        """
        self.assertEqual(str(ansi.clean()), clean)
        self.assertEqual(str(ansi.raw()), raw)

    def table_check(self, ansi, char, code):
        """
        Verifies the indexes in an ANSIString match what they should.
        """
        self.assertEqual(ansi._char_indexes, char)
        self.assertEqual(ansi._code_indexes, code)

    def test_instance(self):
        """
        Make sure the ANSIString is always constructed correctly.
        """
        clean = "This isA|r testTest"
        encoded = "\x1b[1m\x1b[32mThis is\x1b[1m\x1b[31mA|r test\x1b[0mTest\x1b[0m"
        target = ANSIString(r"|gThis is|rA||r test|nTest|n")
        char_table = [9, 10, 11, 12, 13, 14, 15, 25, 26, 27, 28, 29, 30, 31, 32, 37, 38, 39, 40]
        code_table = [
            0,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            16,
            17,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            33,
            34,
            35,
            36,
            41,
            42,
            43,
            44,
        ]
        self.checker(target, encoded, clean)
        self.table_check(target, char_table, code_table)
        self.checker(ANSIString(target), encoded, clean)
        self.table_check(ANSIString(target), char_table, code_table)
        self.checker(ANSIString(encoded, decoded=True), encoded, clean)
        self.table_check(ANSIString(encoded, decoded=True), char_table, code_table)
        self.checker(ANSIString("Test"), "Test", "Test")
        self.table_check(ANSIString("Test"), [0, 1, 2, 3], [])
        self.checker(ANSIString(""), "", "")

    def test_slice(self):
        """
        Verifies that slicing an ANSIString results in expected color code
        distribution.
        """
        target = ANSIString(r"|gTest|rTest|n")
        result = target[:3]
        self.checker(result, "\x1b[1m\x1b[32mTes", "Tes")
        result = target[:4]
        self.checker(result, "\x1b[1m\x1b[32mTest\x1b[1m\x1b[31m", "Test")
        result = target[:]
        self.checker(result, "\x1b[1m\x1b[32mTest\x1b[1m\x1b[31mTest\x1b[0m", "TestTest")
        result = target[:-1]
        self.checker(result, "\x1b[1m\x1b[32mTest\x1b[1m\x1b[31mTes", "TestTes")
        result = target[0:0]
        self.checker(result, "", "")

    def test_split(self):
        """
        Verifies that re.split and .split behave similarly and that color
        codes end up where they should.
        """
        target = ANSIString("|gThis is |nA split string|g")
        first = ("\x1b[1m\x1b[32mThis is \x1b[0m", "This is ")
        second = ("\x1b[1m\x1b[32m\x1b[0m split string\x1b[1m\x1b[32m", " split string")
        re_split = re.split("A", target)
        normal_split = target.split("A")
        self.assertEqual(re_split, normal_split)
        self.assertEqual(len(normal_split), 2)
        self.checker(normal_split[0], *first)
        self.checker(normal_split[1], *second)

    def test_join(self):
        """
        Verify that joining a set of ANSIStrings works.
        """
        # This isn't the desired behavior, but the expected one. Python
        # concatenates the in-memory representation with the built-in string's
        # join.
        l = [ANSIString("|gTest|r") for _ in range(0, 3)]
        # Force the generator to be evaluated.
        result = "".join(l)
        self.assertEqual(str(result), "TestTestTest")
        result = ANSIString("").join(l)
        self.checker(
            result,
            "\x1b[1m\x1b[32mTest\x1b[1m\x1b[31m\x1b[1m\x1b"
            "[32mTest\x1b[1m\x1b[31m\x1b[1m\x1b[32mTest"
            "\x1b[1m\x1b[31m",
            "TestTestTest",
        )

    def test_len(self):
        """
        Make sure that length reporting on ANSIStrings does not include
        ANSI codes.
        """
        self.assertEqual(len(ANSIString("|gTest|n")), 4)

    def test_capitalize(self):
        """
        Make sure that capitalization works. This is the simplest of the
        _transform functions.
        """
        target = ANSIString("|gtest|n")
        result = "\x1b[1m\x1b[32mTest\x1b[0m"
        self.checker(target.capitalize(), result, "Test")

    def test_mxp_agnostic(self):
        """
        Make sure MXP tags are not treated like ANSI codes, but normal text.
        """
        mxp1 = "|lclook|ltat|le"
        mxp2 = "Start to |lclook here|ltclick somewhere here|le first"
        self.assertEqual(15, len(ANSIString(mxp1)))
        self.assertEqual(53, len(ANSIString(mxp2)))
        # These would indicate an issue with the tables.
        self.assertEqual(len(ANSIString(mxp1)), len(ANSIString(mxp1).split("\n")[0]))
        self.assertEqual(len(ANSIString(mxp2)), len(ANSIString(mxp2).split("\n")[0]))
        self.assertEqual(mxp1, ANSIString(mxp1))
        self.assertEqual(mxp2, str(ANSIString(mxp2)))

    def test_add(self):
        """
        Verify concatenation works correctly.
        """
        a = ANSIString("|gTest")
        b = ANSIString("|cString|n")
        c = a + b
        result = "\x1b[1m\x1b[32mTest\x1b[1m\x1b[36mString\x1b[0m"
        self.checker(c, result, "TestString")
        char_table = [9, 10, 11, 12, 22, 23, 24, 25, 26, 27]
        code_table = [0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16, 17, 18, 19, 20, 21, 28, 29, 30, 31]
        self.table_check(c, char_table, code_table)

    def test_strip(self):
        """
        Test the ansi-aware .strip() methods
        """
        a = ANSIString("   |r   Test of stuff |b with spaces   |n   ")
        b = ANSIString("|r|b")
        self.assertEqual(a.strip(), ANSIString("|rTest of stuff |b with spaces|n"))
        self.assertEqual(a.lstrip(), ANSIString("|rTest of stuff |b with spaces   |n   "))
        self.assertEqual(a.rstrip(), ANSIString("   |r   Test of stuff |b with spaces|n"))
        self.assertEqual(b.strip(), b)


class TestTextToHTMLparser(TestCase):
    def setUp(self):
        self.parser = TextToHTMLparser()

    def tearDown(self):
        del self.parser

    def test_url_scheme_ftp(self):
        self.assertEqual(
            self.parser.convert_urls("ftp.example.com"),
            '<a href="ftp.example.com" target="_blank">ftp.example.com</a>',
        )

    def test_url_scheme_www(self):
        self.assertEqual(
            self.parser.convert_urls("www.example.com"),
            '<a href="www.example.com" target="_blank">www.example.com</a>',
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
            '<a href="www.example.com/homedir" target="_blank">www.example.com/homedir</a>',
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

    def test_url_edge_leadingw(self):
        self.assertEqual(
            self.parser.convert_urls("wwww.example.com"),
            'w<a href="www.example.com" target="_blank">www.example.com</a>',
        )

    def test_url_edge_following_period_eol(self):
        self.assertEqual(
            self.parser.convert_urls("www.example.com."),
            '<a href="www.example.com" target="_blank">www.example.com</a>.',
        )

    def test_url_edge_following_period(self):
        self.assertEqual(
            self.parser.convert_urls("see www.example.com. "),
            'see <a href="www.example.com" target="_blank">www.example.com</a>. ',
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


class TestInlineFuncs(TestCase):
    """Test the nested inlinefunc module"""

    def test_nofunc(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc("as$382ewrw w we w werw,|44943}"),
            "as$382ewrw w we w werw,|44943}",
        )

    def test_incomplete(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc("testing $blah{without an ending."),
            "testing $blah{without an ending.",
        )

    def test_single_func(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc("this is a test with $pad(centered, 20) text in it."),
            "this is a test with       centered       text in it.",
        )

    def test_nested(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc(
                "this $crop(is a test with $pad(padded, 20) text in $pad(pad2, 10) a crop, 80)"
            ),
            "this is a test with        padded        text in    pad2    a crop",
        )

    def test_escaped(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc(
                "this should be $pad('''escaped,''' and '''instead,''' cropped $crop(with a long,5) text., 80)"
            ),
            "this should be                    escaped, and instead, cropped with  text.                    ",
        )

    def test_escaped2(self):
        self.assertEqual(
            inlinefuncs.parse_inlinefunc(
                'this should be $pad("""escaped,""" and """instead,""" cropped $crop(with a long,5) text., 80)'
            ),
            "this should be                    escaped, and instead, cropped with  text.                    ",
        )
