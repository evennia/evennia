from builtins import range

import re

try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

from .ansi import ANSIString
from evennia import utils


class ANSIStringTestCase(TestCase):
    def checker(self, ansi, raw, clean):
        """
        Verifies the raw and clean strings of an ANSIString match expected
        output.
        """
        self.assertEqual(unicode(ansi.clean()), clean)
        self.assertEqual(unicode(ansi.raw()), raw)

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
        clean = u'This isA{r testTest'
        encoded = u'\x1b[1m\x1b[32mThis is\x1b[1m\x1b[31mA{r test\x1b[0mTest\x1b[0m'
        target = ANSIString(r'{gThis is{rA{{r test{nTest{n')
        char_table = [9, 10, 11, 12, 13, 14, 15, 25, 26, 27, 28, 29, 30, 31,
                      32, 37, 38, 39, 40]
        code_table = [0, 1, 2, 3, 4, 5, 6, 7, 8, 16, 17, 18, 19, 20, 21, 22,
                      23, 24, 33, 34, 35, 36, 41, 42, 43, 44]
        self.checker(target, encoded, clean)
        self.table_check(target, char_table, code_table)
        self.checker(ANSIString(target), encoded, clean)
        self.table_check(ANSIString(target), char_table, code_table)
        self.checker(ANSIString(encoded, decoded=True), encoded, clean)
        self.table_check(ANSIString(encoded, decoded=True), char_table,
                         code_table)
        self.checker(ANSIString('Test'), u'Test', u'Test')
        self.table_check(ANSIString('Test'), [0, 1, 2, 3], [])
        self.checker(ANSIString(''), u'', u'')

    def test_slice(self):
        """
        Verifies that slicing an ANSIString results in expected color code
        distribution.
        """
        target = ANSIString(r'{gTest{rTest{n')
        result = target[:3]
        self.checker(result, u'\x1b[1m\x1b[32mTes', u'Tes')
        result = target[:4]
        self.checker(result, u'\x1b[1m\x1b[32mTest\x1b[1m\x1b[31m', u'Test')
        result = target[:]
        self.checker(
            result,
            u'\x1b[1m\x1b[32mTest\x1b[1m\x1b[31mTest\x1b[0m',
            u'TestTest')
        result = target[:-1]
        self.checker(
            result,
            u'\x1b[1m\x1b[32mTest\x1b[1m\x1b[31mTes',
            u'TestTes')
        result = target[0:0]
        self.checker(
            result,
            u'',
            u'')

    def test_split(self):
        """
        Verifies that re.split and .split behave similarly and that color
        codes end up where they should.
        """
        target = ANSIString("{gThis is {nA split string{g")
        first = (u'\x1b[1m\x1b[32mThis is \x1b[0m', u'This is ')
        second = (u'\x1b[1m\x1b[32m\x1b[0m split string\x1b[1m\x1b[32m',
                  u' split string')
        re_split = re.split('A', target)
        normal_split = target.split('A')
        self.assertEqual(re_split, normal_split)
        self.assertEqual(len(normal_split), 2)
        self.checker(normal_split[0], *first)
        self.checker(normal_split[1], *second)

    def test_join(self):
        """
        Verify that joining a set of ANSIStrings works.
        """
        # This isn't the desired behavior, but the expected one. Python
        # concatinates the in-memory representation with the built-in string's
        # join.
        l = [ANSIString("{gTest{r") for s in range(0, 3)]
        # Force the generator to be evaluated.
        result = "".join(l)
        self.assertEqual(unicode(result), u'TestTestTest')
        result = ANSIString("").join(l)
        self.checker(result, u'\x1b[1m\x1b[32mTest\x1b[1m\x1b[31m\x1b[1m\x1b'
                             u'[32mTest\x1b[1m\x1b[31m\x1b[1m\x1b[32mTest'
                             u'\x1b[1m\x1b[31m', u'TestTestTest')

    def test_len(self):
        """
        Make sure that length reporting on ANSIStrings does not include
        ANSI codes.
        """
        self.assertEqual(len(ANSIString('{gTest{n')), 4)

    def test_capitalize(self):
        """
        Make sure that capitalization works. This is the simplest of the
        _transform functions.
        """
        target = ANSIString('{gtest{n')
        result = u'\x1b[1m\x1b[32mTest\x1b[0m'
        self.checker(target.capitalize(), result, u'Test')

    def test_mxp_agnostic(self):
        """
        Make sure MXP tags are not treated like ANSI codes, but normal text.
        """
        mxp1 = "{lclook{ltat{le"
        mxp2 = "Start to {lclook here{ltclick somewhere here{le first"
        self.assertEqual(15, len(ANSIString(mxp1)))
        self.assertEqual(53, len(ANSIString(mxp2)))
        # These would indicate an issue with the tables.
        self.assertEqual(len(ANSIString(mxp1)), len(ANSIString(mxp1).split("\n")[0]))
        self.assertEqual(len(ANSIString(mxp2)), len(ANSIString(mxp2).split("\n")[0]))
        self.assertEqual(mxp1, ANSIString(mxp1))
        self.assertEqual(mxp2, unicode(ANSIString(mxp2)))

    def test_add(self):
        """
        Verify concatination works correctly.
        """
        a = ANSIString("{gTest")
        b = ANSIString("{cString{n")
        c = a + b
        result = u'\x1b[1m\x1b[32mTest\x1b[1m\x1b[36mString\x1b[0m'
        self.checker(c, result, u'TestString')
        char_table = [9, 10, 11, 12, 22, 23, 24, 25, 26, 27]
        code_table = [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 13, 14, 15, 16, 17, 18, 19, 20, 21, 28, 29, 30, 31
        ]
        self.table_check(c, char_table, code_table)


class TestIsIter(TestCase):
    def test_is_iter(self):
        self.assertEqual(True, utils.is_iter([1,2,3,4]))
        self.assertEqual(False, utils.is_iter("This is not an iterable"))


class TestCrop(TestCase):
    def test_crop(self):
        # No text, return no text
        self.assertEqual("", utils.crop("", width=10, suffix="[...]"))
        # Input length equal to max width, no crop
        self.assertEqual("0123456789", utils.crop("0123456789", width=10, suffix="[...]"))
        # Input length greater than max width, crop (suffix included in width)
        self.assertEqual("0123[...]", utils.crop("0123456789", width=9, suffix="[...]"))
        # Input length less than desired width, no crop
        self.assertEqual("0123", utils.crop("0123", width=9, suffix="[...]"))
        # Width too small or equal to width of suffix
        self.assertEqual("012", utils.crop("0123", width=3, suffix="[...]"))
        self.assertEqual("01234", utils.crop("0123456", width=5, suffix="[...]"))


class TestDedent(TestCase):
    def test_dedent(self):
        # Empty string, return empty string
        self.assertEqual("", utils.dedent(""))
        # No leading whitespace
        self.assertEqual("TestDedent", utils.dedent("TestDedent"))
        # Leading whitespace, single line
        self.assertEqual("TestDedent", utils.dedent("   TestDedent"))
        # Leading whitespace, multi line
        input_string = "  hello\n  world"
        expected_string = "hello\nworld"
        self.assertEqual(expected_string, utils.dedent(input_string))


class TestListToString(TestCase):
    """
    Default function header from utils.py:
    list_to_string(inlist, endsep="and", addquote=False)

    Examples:
     no endsep:
        [1,2,3] -> '1, 2, 3'
     with endsep=='and':
        [1,2,3] -> '1, 2 and 3'
     with addquote and endsep
        [1,2,3] -> '"1", "2" and "3"'
    """
    def test_list_to_string(self):
        self.assertEqual('1, 2, 3', utils.list_to_string([1,2,3], endsep=""))
        self.assertEqual('"1", "2", "3"', utils.list_to_string([1,2,3], endsep="", addquote=True))
        self.assertEqual('1, 2 and 3', utils.list_to_string([1,2,3]))
        self.assertEqual('"1", "2" and "3"', utils.list_to_string([1,2,3], endsep="and", addquote=True))


class TestMLen(TestCase):
    """
    Verifies that m_len behaves like len in all situations except those
    where MXP may be involved.
    """
    def test_non_mxp_string(self):
        self.assertEqual(utils.m_len('Test_string'), 11)

    def test_mxp_string(self):
        self.assertEqual(utils.m_len('{lclook{ltat{le'), 2)

    def test_mxp_ansi_string(self):
        self.assertEqual(utils.m_len(ANSIString('{lcl{gook{ltat{le{n')), 2)

    def test_non_mxp_ansi_string(self):
        self.assertEqual(utils.m_len(ANSIString('{gHello{n')), 5)

    def test_list(self):
        self.assertEqual(utils.m_len([None, None]), 2)

    def test_dict(self):
        self.assertEqual(utils.m_len({'hello': True, 'Goodbye': False}), 2)


from .text2html import TextToHTMLparser

class TestTextToHTMLparser(TestCase):
    def setUp(self):
        self.parser = TextToHTMLparser()

    def tearDown(self):
        del self.parser

    def test_url_scheme_ftp(self):
        self.assertEqual(self.parser.convert_urls('ftp.example.com'),
            '<a href="ftp.example.com" target="_blank">ftp.example.com</a>')

    def test_url_scheme_www(self):
        self.assertEqual(self.parser.convert_urls('www.example.com'),
            '<a href="www.example.com" target="_blank">www.example.com</a>')

    def test_url_scheme_ftpproto(self):
        self.assertEqual(self.parser.convert_urls('ftp://ftp.example.com'),
            '<a href="ftp://ftp.example.com" target="_blank">ftp://ftp.example.com</a>')

    def test_url_scheme_http(self):
        self.assertEqual(self.parser.convert_urls('http://example.com'),
            '<a href="http://example.com" target="_blank">http://example.com</a>')

    def test_url_scheme_https(self):
        self.assertEqual(self.parser.convert_urls('https://example.com'),
            '<a href="https://example.com" target="_blank">https://example.com</a>')

    def test_url_chars_slash(self):
        self.assertEqual(self.parser.convert_urls('www.example.com/homedir'),
            '<a href="www.example.com/homedir" target="_blank">www.example.com/homedir</a>')

    def test_url_chars_colon(self):
        self.assertEqual(self.parser.convert_urls('https://example.com:8000/login/'),
            '<a href="https://example.com:8000/login/" target="_blank">https://example.com:8000/login/</a>')

    def test_url_chars_querystring(self):
        self.assertEqual(self.parser.convert_urls('https://example.com/submitform?field1=val1+val3&field2=val2'),
            '<a href="https://example.com/submitform?field1=val1+val3&field2=val2" target="_blank">https://example.com/submitform?field1=val1+val3&field2=val2</a>')

    def test_url_chars_anchor(self):
        self.assertEqual(self.parser.convert_urls('http://www.example.com/menu#section_1'),
            '<a href="http://www.example.com/menu#section_1" target="_blank">http://www.example.com/menu#section_1</a>')

    def test_url_chars_exclam(self):
        self.assertEqual(self.parser.convert_urls('https://groups.google.com/forum/?fromgroups#!categories/evennia/ainneve'),
            '<a href="https://groups.google.com/forum/?fromgroups#!categories/evennia/ainneve" target="_blank">https://groups.google.com/forum/?fromgroups#!categories/evennia/ainneve</a>')

    def test_url_edge_leadingw(self):
        self.assertEqual(self.parser.convert_urls('wwww.example.com'),
            'w<a href="www.example.com" target="_blank">www.example.com</a>')

    def test_url_edge_following_period_eol(self):
        self.assertEqual(self.parser.convert_urls('www.example.com.'),
            '<a href="www.example.com" target="_blank">www.example.com</a>.')

    def test_url_edge_following_period(self):
        self.assertEqual(self.parser.convert_urls('see www.example.com. '),
            'see <a href="www.example.com" target="_blank">www.example.com</a>. ')

    def test_url_edge_brackets(self):
        self.assertEqual(self.parser.convert_urls('[http://example.com/]'),
            '[<a href="http://example.com/" target="_blank">http://example.com/</a>]')

    def test_url_edge_multiline(self):
        self.assertEqual(self.parser.convert_urls('  * http://example.com/info\n  * bullet'),
            '  * <a href="http://example.com/info" target="_blank">http://example.com/info</a>\n  * bullet')

    def test_url_edge_following_htmlentity(self):
        self.assertEqual(self.parser.convert_urls('http://example.com/info&lt;span&gt;'),
            '<a href="http://example.com/info" target="_blank">http://example.com/info</a>&lt;span&gt;')

    def test_url_edge_surrounded_spans(self):
        self.assertEqual(self.parser.convert_urls('</span>http://example.com/<span class="red">'),
            '</span><a href="http://example.com/" target="_blank">http://example.com/</a><span class="red">')


from evennia.utils import nested_inlinefuncs

class TestNestedInlineFuncs(TestCase):
    "Test the nested inlinefunc module"
    def test_nofunc(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            "as$382ewrw w we w werw,|44943}"),
            "as$382ewrw w we w werw,|44943}")

    def test_incomplete(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            "testing $blah{without an ending."),
            "testing $blah{without an ending.")

    def test_single_func(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            "this is a test with $pad(centered, 20) text in it."),
            "this is a test with       centered       text in it.")

    def test_nested(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            "this $crop(is a test with $pad(padded, 20) text in $pad(pad2, 10) a crop, 80)"),
            "this is a test with        padded        text in    pad2    a crop")

    def test_escaped(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            "this should be $pad('''escaped,''' and '''instead,''' cropped $crop(with a long,5) text., 80)"),
            "this should be                    escaped, and instead, cropped with  text.                    ")

    def test_escaped2(self):
        self.assertEqual(nested_inlinefuncs.parse_inlinefunc(
            'this should be $pad("""escaped,""" and """instead,""" cropped $crop(with a long,5) text., 80)'),
            "this should be                    escaped, and instead, cropped with  text.                    ")

from evennia.utils import evform

class TestEvForm(TestCase):
    def test_form(self):
        self.assertEqual(unicode(evform._test()),
            u'.------------------------------------------------.\n|                                                |\n|  Name: \x1b[1m\x1b[32mTom\x1b[1m\x1b[32m \x1b[1m\x1b[32mthe\x1b[1m\x1b[32m \x1b[0m       Player: \x1b[1m\x1b[33mGriatch\x1b[0m        \x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[0m  |\n|        \x1b[1m\x1b[32mBouncer\x1b[0m\x1b[0m                                 |\n|                                                |\n >----------------------------------------------<\n|                                                |\n| Desc:  A sturdy \x1b[0m      STR: 12 \x1b[0m    DEX: 10 \x1b[0m     |\n|        fellow\x1b[0m         INT: 5  \x1b[0m    STA: 18 \x1b[0m     |\n|                       LUC: 10     MAG: 3       |\n|                                                |\n >----------------------------------------------<\n|          |                                     |\n| HP|MV |M\x1b[0m | Skill       |Value     |Exp        \x1b[0m |\n| ~~+~~~+~ | ~~~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~~ |\n| **|***\x1b[0m|*\x1b[0m | Shooting    |12        |550/1200   \x1b[0m\x1b[0m |\n|   |**\x1b[0m |*\x1b[0m | Herbalism   |14        |990/1400   \x1b[0m\x1b[0m |\n|   |   |*\x1b[0m | Smithing    |9         |205/900    \x1b[0m |\n|          |                                     |\n ------------------------------------------------\n')
    def test_ansi_escape(self):
        # note that in a msg() call, the result would be the  correct |-----,
        # in a print, ansi only gets called once, so ||----- is the result
        self.assertEqual(unicode(evform.EvForm(form={"FORM":"\n||-----"})), "||-----")
