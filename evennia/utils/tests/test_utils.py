"""
Unit tests for the utilities of the evennia.utils.utils module.

TODO: Not nearly all utilities are covered yet.

"""

import os.path
import mock

from django.test import TestCase
from datetime import datetime
from twisted.internet import task

from evennia.utils.ansi import ANSIString
from evennia.utils import utils
from evennia.utils.test_resources import EvenniaTest


class TestIsIter(TestCase):
    def test_is_iter(self):
        self.assertEqual(True, utils.is_iter([1, 2, 3, 4]))
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
        self.assertEqual("1, 2, 3", utils.list_to_string([1, 2, 3], endsep=""))
        self.assertEqual('"1", "2", "3"', utils.list_to_string([1, 2, 3], endsep="", addquote=True))
        self.assertEqual("1, 2 and 3", utils.list_to_string([1, 2, 3]))
        self.assertEqual(
            '"1", "2" and "3"', utils.list_to_string([1, 2, 3], endsep="and", addquote=True)
        )


class TestMLen(TestCase):
    """
    Verifies that m_len behaves like len in all situations except those
    where MXP may be involved.
    """

    def test_non_mxp_string(self):
        self.assertEqual(utils.m_len("Test_string"), 11)

    def test_mxp_string(self):
        self.assertEqual(utils.m_len("|lclook|ltat|le"), 2)

    def test_mxp_ansi_string(self):
        self.assertEqual(utils.m_len(ANSIString("|lcl|gook|ltat|le|n")), 2)

    def test_non_mxp_ansi_string(self):
        self.assertEqual(utils.m_len(ANSIString("|gHello|n")), 5)

    def test_list(self):
        self.assertEqual(utils.m_len([None, None]), 2)

    def test_dict(self):
        self.assertEqual(utils.m_len({"hello": True, "Goodbye": False}), 2)


class TestDisplayLen(TestCase):
    """
    Verifies that display_len behaves like m_len in all situations except those
    where asian characters are involved.
    """

    def test_non_mxp_string(self):
        self.assertEqual(utils.display_len("Test_string"), 11)

    def test_mxp_string(self):
        self.assertEqual(utils.display_len("|lclook|ltat|le"), 2)

    def test_mxp_ansi_string(self):
        self.assertEqual(utils.display_len(ANSIString("|lcl|gook|ltat|le|n")), 2)

    def test_non_mxp_ansi_string(self):
        self.assertEqual(utils.display_len(ANSIString("|gHello|n")), 5)

    def test_list(self):
        self.assertEqual(utils.display_len([None, None]), 2)

    def test_dict(self):
        self.assertEqual(utils.display_len({"hello": True, "Goodbye": False}), 2)

    def test_east_asian(self):
        self.assertEqual(utils.display_len("서서서"), 6)


class TestANSIString(TestCase):
    """
    Verifies that ANSIString's string-API works as intended.
    """

    def setUp(self):
        self.example_raw = "|relectric |cboogaloo|n"
        self.example_ansi = ANSIString(self.example_raw)
        self.example_str = "electric boogaloo"
        self.example_output = "\x1b[1m\x1b[31melectric \x1b[1m\x1b[36mboogaloo\x1b[0m"

    def test_length(self):
        self.assertEqual(len(self.example_ansi), 17)

    def test_clean(self):
        self.assertEqual(self.example_ansi.clean(), self.example_str)

    def test_raw(self):
        self.assertEqual(self.example_ansi.raw(), self.example_output)

    def test_format(self):
        self.assertEqual(f"{self.example_ansi:0<20}", self.example_output + "000")


class TestTimeformat(TestCase):
    """
    Default function header from utils.py:
    time_format(seconds, style=0)

    """

    def test_style_0(self):
        """Test the style 0 of time_format."""
        self.assertEqual(utils.time_format(0, 0), "00:00")
        self.assertEqual(utils.time_format(28, 0), "00:00")
        self.assertEqual(utils.time_format(92, 0), "00:01")
        self.assertEqual(utils.time_format(300, 0), "00:05")
        self.assertEqual(utils.time_format(660, 0), "00:11")
        self.assertEqual(utils.time_format(3600, 0), "01:00")
        self.assertEqual(utils.time_format(3725, 0), "01:02")
        self.assertEqual(utils.time_format(86350, 0), "23:59")
        self.assertEqual(utils.time_format(86800, 0), "1d 00:06")
        self.assertEqual(utils.time_format(130800, 0), "1d 12:20")
        self.assertEqual(utils.time_format(530800, 0), "6d 03:26")

    def test_style_1(self):
        """Test the style 1 of time_format."""
        self.assertEqual(utils.time_format(0, 1), "0s")
        self.assertEqual(utils.time_format(28, 1), "28s")
        self.assertEqual(utils.time_format(92, 1), "1m")
        self.assertEqual(utils.time_format(300, 1), "5m")
        self.assertEqual(utils.time_format(660, 1), "11m")
        self.assertEqual(utils.time_format(3600, 1), "1h")
        self.assertEqual(utils.time_format(3725, 1), "1h")
        self.assertEqual(utils.time_format(86350, 1), "23h")
        self.assertEqual(utils.time_format(86800, 1), "1d")
        self.assertEqual(utils.time_format(130800, 1), "1d")
        self.assertEqual(utils.time_format(530800, 1), "6d")

    def test_style_2(self):
        """Test the style 2 of time_format."""
        self.assertEqual(utils.time_format(0, 2), "0 minutes")
        self.assertEqual(utils.time_format(28, 2), "0 minutes")
        self.assertEqual(utils.time_format(92, 2), "1 minute")
        self.assertEqual(utils.time_format(300, 2), "5 minutes")
        self.assertEqual(utils.time_format(660, 2), "11 minutes")
        self.assertEqual(utils.time_format(3600, 2), "1 hour, 0 minutes")
        self.assertEqual(utils.time_format(3725, 2), "1 hour, 2 minutes")
        self.assertEqual(utils.time_format(86350, 2), "23 hours, 59 minutes")
        self.assertEqual(utils.time_format(86800, 2), "1 day, 0 hours, 6 minutes")
        self.assertEqual(utils.time_format(130800, 2), "1 day, 12 hours, 20 minutes")
        self.assertEqual(utils.time_format(530800, 2), "6 days, 3 hours, 26 minutes")

    def test_style_3(self):
        """Test the style 3 of time_format."""
        self.assertEqual(utils.time_format(0, 3), "")
        self.assertEqual(utils.time_format(28, 3), "28 seconds")
        self.assertEqual(utils.time_format(92, 3), "1 minute 32 seconds")
        self.assertEqual(utils.time_format(300, 3), "5 minutes 0 seconds")
        self.assertEqual(utils.time_format(660, 3), "11 minutes 0 seconds")
        self.assertEqual(utils.time_format(3600, 3), "1 hour, 0 minutes")
        self.assertEqual(utils.time_format(3725, 3), "1 hour, 2 minutes 5 seconds")
        self.assertEqual(utils.time_format(86350, 3), "23 hours, 59 minutes 10 seconds")
        self.assertEqual(utils.time_format(86800, 3), "1 day, 0 hours, 6 minutes 40 seconds")
        self.assertEqual(utils.time_format(130800, 3), "1 day, 12 hours, 20 minutes 0 seconds")
        self.assertEqual(utils.time_format(530800, 3), "6 days, 3 hours, 26 minutes 40 seconds")

    def test_style_4(self):
        """Test the style 4 of time_format."""
        self.assertEqual(utils.time_format(0, 4), "0 seconds")
        self.assertEqual(utils.time_format(28, 4), "28 seconds")
        self.assertEqual(utils.time_format(92, 4), "a minute")
        self.assertEqual(utils.time_format(300, 4), "5 minutes")
        self.assertEqual(utils.time_format(660, 4), "11 minutes")
        self.assertEqual(utils.time_format(3600, 4), "an hour")
        self.assertEqual(utils.time_format(3725, 4), "an hour")
        self.assertEqual(utils.time_format(86350, 4), "23 hours")
        self.assertEqual(utils.time_format(86800, 4), "a day")
        self.assertEqual(utils.time_format(130800, 4), "a day")
        self.assertEqual(utils.time_format(530800, 4), "6 days")
        self.assertEqual(utils.time_format(3030800, 4), "a month")
        self.assertEqual(utils.time_format(7030800, 4), "2 months")
        self.assertEqual(utils.time_format(40030800, 4), "a year")
        self.assertEqual(utils.time_format(90030800, 4), "2 years")

    def test_unknown_format(self):
        """Test that unknown formats raise exceptions."""
        self.assertRaises(ValueError, utils.time_format, 0, 5)
        self.assertRaises(ValueError, utils.time_format, 0, "u")


@mock.patch(
    "evennia.utils.utils.timezone.now",
    new=mock.MagicMock(return_value=datetime(2019, 8, 28, 21, 56)),
)
class TestDateTimeFormat(TestCase):
    def test_datetimes(self):
        dtobj = datetime(2017, 7, 26, 22, 54)
        self.assertEqual(utils.datetime_format(dtobj), "Jul 26, 2017")
        dtobj = datetime(2019, 7, 26, 22, 54)
        self.assertEqual(utils.datetime_format(dtobj), "Jul 26")
        dtobj = datetime(2019, 8, 28, 19, 54)
        self.assertEqual(utils.datetime_format(dtobj), "19:54")
        dtobj = datetime(2019, 8, 28, 21, 32)
        self.assertEqual(utils.datetime_format(dtobj), "21:32:00")


class TestImportFunctions(TestCase):
    def _t_dir_file(self, filename):
        testdir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(testdir, filename)

    def test_mod_import(self):
        loaded_mod = utils.mod_import("evennia.utils.ansi")
        self.assertIsNotNone(loaded_mod)

    def test_mod_import_invalid(self):
        loaded_mod = utils.mod_import("evennia.utils.invalid_module")
        self.assertIsNone(loaded_mod)

    def test_mod_import_from_path(self):
        test_path = self._t_dir_file("test_eveditor.py")
        loaded_mod = utils.mod_import_from_path(test_path)
        self.assertIsNotNone(loaded_mod)

    def test_mod_import_from_path_invalid(self):
        test_path = self._t_dir_file("invalid_filename.py")
        loaded_mod = utils.mod_import_from_path(test_path)
        self.assertIsNone(loaded_mod)


class LatinifyTest(TestCase):
    def setUp(self):
        super().setUp()

        self.example_str = "It naïvely says, “plugh.”"
        self.expected_output = 'It naively says, "plugh."'

    def test_plain_string(self):
        result = utils.latinify(self.example_str)
        self.assertEqual(result, self.expected_output)

    def test_byte_string(self):
        byte_str = utils.to_bytes(self.example_str)
        result = utils.latinify(byte_str)
        self.assertEqual(result, self.expected_output)


_TASK_HANDLER = None


def dummy_func(obj):
    """
    Used in TestDelay.

    A function that:
        can be serialized
        uses no memory references
        uses evennia objects
    """
    # get a reference of object
    from evennia.objects.models import ObjectDB
    obj = ObjectDB.objects.object_search(obj)
    obj = obj[0]
    # make changes to object
    obj.ndb.dummy_var = 'dummy_func ran'


class TestDelay(EvenniaTest):
    """
    Test utils.delay.
    """

    def test_delay(self):
        # get a reference of TASK_HANDLER
        global _TASK_HANDLER
        if _TASK_HANDLER is None:
            from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER
        _TASK_HANDLER.clock = task.Clock()
        self.char1.ndb.dummy_var = False
        # test a persistent deferral, that completes after delay time
        task_id = utils.delay(1, dummy_func, self.char1.dbref, persistent=True)
        _TASK_HANDLER.clock.advance(1)  # make time pass
        self.assertEqual(self.char1.ndb.dummy_var, 'dummy_func ran')
        self.char1.ndb.dummy_var = False
        # test a non persisten deferral, that completes after delay time.
        deferal_inst = utils.delay(1, dummy_func, self.char1.dbref)
        _TASK_HANDLER.clock.advance(1)  # make time pass
        self.assertEqual(self.char1.ndb.dummy_var, 'dummy_func ran')
        self.char1.ndb.dummy_var = False
        # test canceling a deferral.
        deferal_inst = utils.delay(1, dummy_func, self.char1.dbref)
        deferal_inst.cancel()
        _TASK_HANDLER.clock.advance(1)  # make time pass
        self.assertEqual(self.char1.ndb.dummy_var, False)
        self.char1.ndb.dummy_var = False
