# test with game/manage.py test
import unittest

from evennia.utils import utils

class TestIsIter(unittest.TestCase):
    def test_is_iter(self):
        self.assertEqual(True, utils.is_iter([1,2,3,4]))
        self.assertEqual(False, utils.is_iter("This is not an iterable"))

class TestCrop(unittest.TestCase):
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

class TestDedent(unittest.TestCase):
    def test_dedent(self):
        #print "Did TestDedent run?"
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

class TestListToString(unittest.TestCase):
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
    #print "Did TestListToString run?"
    def test_list_to_string(self):
        self.assertEqual('1, 2, 3', utils.list_to_string([1,2,3], endsep=""))
        self.assertEqual('"1", "2", "3"', utils.list_to_string([1,2,3], endsep="", addquote=True))
        self.assertEqual('1, 2 and 3', utils.list_to_string([1,2,3]))
        self.assertEqual('"1", "2" and "3"', utils.list_to_string([1,2,3], endsep="and", addquote=True))

