import re

try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase

from ansi import ANSIString


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