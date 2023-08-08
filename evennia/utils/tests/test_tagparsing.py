"""
Unit tests for all sorts of inline text-tag parsing, like ANSI, html conversion, inlinefuncs etc

"""
import re

from django.test import TestCase, override_settings

from evennia.utils import funcparser
from evennia.utils.evstring import EvString
from evennia.utils.text2html import TextToHTMLparser


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
        target = EvString(r"|gThis is|rA||r test|nTest|n")
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
        self.checker(EvString(target), encoded, clean)
        self.table_check(EvString(target), char_table, code_table)
        self.checker(EvString(encoded, decoded=True), encoded, clean)
        self.table_check(EvString(encoded, decoded=True), char_table, code_table)
        self.checker(EvString("Test"), "Test", "Test")
        self.table_check(EvString("Test"), [0, 1, 2, 3], [])
        self.checker(EvString(""), "", "")

    def test_slice(self):
        """
        Verifies that slicing an ANSIString results in expected color code
        distribution.
        """
        target = EvString(r"|gTest|rTest|n")
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
        target = EvString("|gThis is |nA split string|g")
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
        l = [EvString("|gTest|r") for _ in range(0, 3)]
        # Force the generator to be evaluated.
        result = "".join(l)
        self.assertEqual(str(result), "TestTestTest")
        result = EvString("").join(l)
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
        self.assertEqual(len(EvString("|gTest|n")), 4)

    def test_capitalize(self):
        """
        Make sure that capitalization works. This is the simplest of the
        _transform functions.
        """
        target = EvString("|gtest|n")
        result = "\x1b[1m\x1b[32mTest\x1b[0m"
        self.checker(target.capitalize(), result, "Test")

    def test_mxp_agnostic(self):
        """
        Make sure MXP tags are not treated like ANSI codes, but normal text.
        """
        mxp1 = "|lclook|ltat|le"
        mxp2 = "Start to |lclook here|ltclick somewhere here|le first"
        mxp3 = "Check out |luhttps://www.example.com|ltmy website|le!"
        self.assertEqual(15, len(EvString(mxp1)))
        self.assertEqual(53, len(EvString(mxp2)))
        self.assertEqual(53, len(EvString(mxp3)))
        # These would indicate an issue with the tables.
        self.assertEqual(len(EvString(mxp1)), len(EvString(mxp1).split("\n")[0]))
        self.assertEqual(len(EvString(mxp2)), len(EvString(mxp2).split("\n")[0]))
        self.assertEqual(len(EvString(mxp3)), len(EvString(mxp3).split("\n")[0]))
        self.assertEqual(mxp1, EvString(mxp1))
        self.assertEqual(mxp2, str(EvString(mxp2)))
        self.assertEqual(mxp3, str(EvString(mxp3)))

    def test_add(self):
        """
        Verify concatenation works correctly.
        """
        a = EvString("|gTest")
        b = EvString("|cString|n")
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
        a = EvString("   |r   Test of stuff |b with spaces   |n   ")
        b = EvString("|r|b")
        self.assertEqual(a.strip(), EvString("|rTest of stuff |b with spaces|n"))
        self.assertEqual(a.lstrip(), EvString("|rTest of stuff |b with spaces   |n   "))
        self.assertEqual(a.rstrip(), EvString("   |r   Test of stuff |b with spaces|n"))
        self.assertEqual(b.strip(), b)

    def test_regex_search(self):
        """
        Test regex-search in ANSIString - the found position should ignore any ansi-markers
        """
        string = EvString(" |r|[b  Test ")
        match = re.search(r"Test", string)
        self.assertTrue(match)
        self.assertEqual(match.span(), (3, 7))

    def test_regex_replace(self):
        """
        Inserting text into an ansistring at an index position should ignore
        the ansi markers but not remove them!

        """
        string = EvString("A |rTest|n string")
        match = re.search(r"Test", string)
        ix1, ix2 = match.span()
        self.assertEqual((ix1, ix2), (2, 6))

        result = string[:ix1] + "Replacement" + string[ix2:]
        expected = EvString("A |rReplacement|n string")

        self.assertEqual(expected, result)

    def test_slice_insert(self):
        """
        Inserting a slice should not remove ansi markup (issue #2205)
        """
        string = EvString("|rTest|n")
        split_string = string[:0] + "Test" + string[4:]
        self.assertEqual(string.raw(), split_string.raw())

    def test_slice_insert_longer(self):
        """
        The ANSIString replays the color code before the split in order to
        produce a *visually* identical result. The result is a longer string in
        raw characters, but one which correctly represents the color output.
        """
        string = EvString("A bigger |rTest|n of things |bwith more color|n")
        # from evennia import set_trace;set_trace()
        split_string = string[:9] + "Test" + string[13:]
        self.assertEqual(
            repr(
                (
                    EvString("A bigger ")
                    + EvString("|rTest")  # note that the |r|n is replayed together on next line
                    + EvString("|r|n of things |bwith more color|n")
                ).raw()
            ),
            repr(split_string.raw()),
        )

    def test_slice_full(self):
        string = EvString("A bigger |rTest|n of things |bwith more color|n")
        split_string = string[:]
        self.assertEqual(string.raw(), split_string.raw())


class TestTextToHTMLparser(TestCase):
    def setUp(self):
        self.parser = TextToHTMLparser()

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
