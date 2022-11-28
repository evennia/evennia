"""
Unit tests for the utilities of the evennia.utils.utils module.

TODO: Not nearly all utilities are covered yet.

"""

import os.path
import random
from datetime import datetime, timedelta

import mock
from django.test import TestCase
from parameterized import parameterized
from twisted.internet import task

from evennia.utils import utils
from evennia.utils.ansi import ANSIString
from evennia.utils.test_resources import BaseEvenniaTest


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
    list_to_string(inlist, sep=",", endsep=", and", addquote=False)

    Examples:
     with defaults:
        [1,2,3] -> '1, 2, and 3'
     with endsep==',':
        [1,2,3] -> '1, 2, 3'
     with sep==';' and endsep==';':
        [1,2,3] -> '1; 2; 3'
     with sep=='or':
        [1,2,3] -> '1 or 2, and 3'
     with endsep=='and':
        [1,2,3] -> '1, 2 and 3'
     with endsep=='; and':
        [1,2,3] -> '1, 2; and 3'
     with endsep=='':
        [1,2,3] -> '1, 2 3'
     with addquote and endsep="and"
        [1,2,3] -> '"1", "2" and "3"'
    """

    def test_list_to_string(self):
        self.assertEqual("1, 2, and 3", utils.list_to_string([1, 2, 3]))
        self.assertEqual("1, 2, 3", utils.list_to_string([1, 2, 3], endsep=","))
        self.assertEqual("1, 2 and 3", utils.list_to_string([1, 2, 3], endsep="and"))
        self.assertEqual("1, 2 3", utils.list_to_string([1, 2, 3], endsep=""))
        self.assertEqual("1; 2; 3", utils.list_to_string([1, 2, 3], sep=";", endsep=";"))
        self.assertEqual("1 or 2, and 3", utils.list_to_string([1, 2, 3], sep="or"))
        self.assertEqual("1, 2; and 3", utils.list_to_string([1, 2, 3], endsep="; and"))
        self.assertEqual(
            '"1", "2", "3"', utils.list_to_string([1, 2, 3], endsep=",", addquote=True)
        )
        self.assertEqual(
            '"1", "2" and "3"', utils.list_to_string([1, 2, 3], endsep="and", addquote=True)
        )
        self.assertEqual("1 and 2", utils.list_to_string([1, 2]))


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
    def _path_to_file(self, filename):
        testdir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(testdir, filename)

    def test_mod_import(self):
        loaded_mod = utils.mod_import("evennia.utils.ansi")
        self.assertIsNotNone(loaded_mod)

    def test_mod_import_invalid(self):
        loaded_mod = utils.mod_import("evennia.utils.invalid_module")
        self.assertIsNone(loaded_mod)

    def test_mod_import_from_path(self):
        test_path = self._path_to_file("test_eveditor.py")
        loaded_mod = utils.mod_import_from_path(test_path)
        self.assertIsNotNone(loaded_mod)

    def test_mod_import_from_path_invalid(self):
        test_path = self._path_to_file("invalid_filename.py")
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


class TestFormatGrid(TestCase):

    maxDiff = None

    def setUp(self):
        # make the random only semi-random with a fixed seed
        random.seed(1)

    def tearDown(self):
        # restore normal randomness
        random.seed(None)

    def _generate_elements(self, basewidth, variation, amount):
        return [
            "X" * max(1, basewidth + int(random.randint(-variation, variation)))
            for _ in range(amount)
        ]

    def test_even_grid(self):
        """Grid with small variations"""
        elements = self._generate_elements(3, 1, 30)
        rows = utils.format_grid(elements, width=78)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(len(row) == 78 for row in rows))

    def test_disparate_grid(self):
        """Grid with big variations"""
        elements = self._generate_elements(3, 15, 30)
        rows = utils.format_grid(elements, width=82, sep="  ")
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(len(row) == 82 for row in rows))

    def test_huge_grid(self):
        """Grid with very long strings"""
        elements = self._generate_elements(70, 20, 30)
        rows = utils.format_grid(elements, width=78)
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(len(row) == 78 for row in rows))

    def test_overlap(self):
        """Grid with elements overlapping into the next slot"""
        elements = (
            "alias",
            "batchcode",
            "batchcommands",
            "cmdsets",
            "copy",
            "cpattr",
            "desc",
            "destroy",
            "dig",
            "examine",
            "find",
            "force",
            "lock",
        )
        rows = utils.format_grid(elements, width=78)
        self.assertEqual(len(rows), 3)
        for element in elements:
            self.assertTrue(element in "\n".join(rows), f"element {element} is missing.")

    def test_breakline(self):
        """Grid with line-long elements in middle"""
        elements = self._generate_elements(6, 4, 30)
        elements[10] = elements[20] = "-" * 78
        rows = utils.format_grid(elements, width=78)
        self.assertEqual(len(rows), 8)
        for element in elements:
            self.assertTrue(element in "\n".join(rows), f"element {element} is missing.")


class TestPercent(TestCase):
    """
    Test the utils.percentage function.
    """

    def test_ok_input(self):
        result = utils.percent(3, 0, 10)
        self.assertEqual(result, "30.0%")
        result = utils.percent(2.5, 0, 5, formatting=None)
        self.assertEqual(result, 50.0)

    def test_bad_input(self):
        """Gracefully handle weird input."""
        self.assertEqual(utils.percent(3, 10, 1), "0.0%")
        self.assertEqual(utils.percent(3, None, 1), "100.0%")
        self.assertEqual(utils.percent(1, 1, 1), "100.0%")
        self.assertEqual(utils.percent(3, 1, 1), "0.0%")
        self.assertEqual(utils.percent(3, 0, 1), "100.0%")
        self.assertEqual(utils.percent(-3, 0, 1), "0.0%")


class TestSafeConvert(TestCase):
    """
    Test evennia.utils.utils.safe_convert_to_types

    """

    @parameterized.expand(
        [
            (
                ("1", "2", 3, 4, "5"),
                {"a": 1, "b": "2", "c": 3},
                ((int, float, str, int), {"a": int, "b": float}),  # "
                (1, 2.0, "3", 4, "5"),
                {"a": 1, "b": 2.0, "c": 3},
            ),
            (
                ("1 + 2", "[1, 2, 3]", [3, 4, 5]),
                {"a": "3 + 4", "b": 5},
                (("py", "py", "py"), {"a": "py", "b": "py"}),
                (3, [1, 2, 3], [3, 4, 5]),
                {"a": 7, "b": 5},
            ),
        ]
    )
    def test_conversion(self, args, kwargs, converters, expected_args, expected_kwargs):
        """
        Test the converter with different inputs

        """
        result_args, result_kwargs = utils.safe_convert_to_types(
            converters, *args, raise_errors=True, **kwargs
        )
        self.assertEqual(expected_args, result_args)
        self.assertEqual(expected_kwargs, result_kwargs)

    def test_conversion__fail(self):
        """
        Test failing conversion

        """
        from evennia.utils.funcparser import ParsingError

        with self.assertRaises(ValueError):
            utils.safe_convert_to_types((int,), *("foo",), raise_errors=True)

        with self.assertRaises(ParsingError) as err:
            utils.safe_convert_to_types(("py", {}), *("foo",), raise_errors=True)


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
    obj.ndb.dummy_var = "dummy_func ran"
    return True


class TestDelay(BaseEvenniaTest):
    """
    Test utils.delay.
    """

    def setUp(self):
        super().setUp()
        # get a reference of TASK_HANDLER
        self.timedelay = 5
        global _TASK_HANDLER
        if _TASK_HANDLER is None:
            from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER
        _TASK_HANDLER.clock = task.Clock()
        self.char1.ndb.dummy_var = False

    def tearDown(self):
        super().tearDown()
        _TASK_HANDLER.clear()

    def test_call_early(self):
        # call a task early with call
        for pers in (True, False):
            t = utils.delay(self.timedelay, dummy_func, self.char1.dbref, persistent=pers)
            result = t.call()
            self.assertTrue(result)
            self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")
            self.assertTrue(t.exists())
            self.assertTrue(t.active())
            self.char1.ndb.dummy_var = False

    def test_do_task(self):
        # call the task early with do_task
        for pers in (True, False):
            t = utils.delay(self.timedelay, dummy_func, self.char1.dbref, persistent=pers)
            # call the task early to test Task.call and TaskHandler.call_task
            result = t.do_task()
            self.assertTrue(result)
            self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")
            self.assertFalse(t.exists())
            self.char1.ndb.dummy_var = False

    def test_deferred_call(self):
        # wait for deferred to call
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")
            self.assertFalse(t.exists())
            self.char1.ndb.dummy_var = False

    def test_short_deferred_call(self):
        # wait for deferred to call with a very short time
        timedelay = 0.1
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")
            self.assertFalse(t.exists())
            self.char1.ndb.dummy_var = False

    def test_active(self):
        timedelay = self.timedelay
        t = utils.delay(timedelay, dummy_func, self.char1.dbref)
        self.assertTrue(_TASK_HANDLER.active(t.get_id()))
        self.assertTrue(t.active())
        _TASK_HANDLER.clock.advance(timedelay)  # make time pass
        self.assertFalse(_TASK_HANDLER.active(t.get_id()))
        self.assertFalse(t.active())

    def test_called(self):
        timedelay = self.timedelay
        t = utils.delay(timedelay, dummy_func, self.char1.dbref)
        self.assertFalse(t.called)
        _TASK_HANDLER.clock.advance(timedelay)  # make time pass
        self.assertTrue(t.called)

    def test_cancel(self):
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            success = t.cancel()
            self.assertFalse(t.active())
            self.assertTrue(success)
            self.assertTrue(t.exists())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, False)

    def test_remove(self):
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            success = t.remove()
            self.assertTrue(success)
            self.assertFalse(t.active())
            self.assertFalse(t.exists())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, False)

    def test_remove_canceled(self):
        # remove a canceled task
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            success = t.cancel()
            self.assertTrue(success)
            self.assertTrue(t.exists())
            self.assertFalse(t.active())
            success = t.remove()
            self.assertTrue(success)
            self.assertFalse(t.exists())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, False)

    def test_pause_unpause(self):
        # remove a canceled task
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            self.assertTrue(t.active())
            t.pause()
            self.assertTrue(t.paused)
            t.unpause()
            self.assertFalse(t.paused)
            self.assertEqual(self.char1.ndb.dummy_var, False)
            t.pause()
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            self.assertEqual(self.char1.ndb.dummy_var, False)
            t.unpause()
            self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")
            self.char1.ndb.dummy_var = False

    def test_auto_stale_task_removal(self):
        # automated removal of stale tasks.
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            t.cancel()
            self.assertFalse(t.active())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            if pers:
                self.assertTrue(t.get_id() in _TASK_HANDLER.to_save)
            self.assertTrue(t.get_id() in _TASK_HANDLER.tasks)
            # Make task handler's now time, after the stale timeout
            _TASK_HANDLER._now = datetime.now() + timedelta(
                seconds=_TASK_HANDLER.stale_timeout + timedelay + 1
            )
            # add a task to test automatic removal
            t2 = utils.delay(timedelay, dummy_func, self.char1.dbref)
            if pers:
                self.assertFalse(t.get_id() in _TASK_HANDLER.to_save)
            self.assertFalse(t.get_id() in _TASK_HANDLER.tasks)
            self.assertEqual(self.char1.ndb.dummy_var, False)
            _TASK_HANDLER.clear()

    def test_manual_stale_task_removal(self):
        # manual removal of stale tasks.
        timedelay = self.timedelay
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            t.cancel()
            self.assertFalse(t.active())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            if pers:
                self.assertTrue(t.get_id() in _TASK_HANDLER.to_save)
            self.assertTrue(t.get_id() in _TASK_HANDLER.tasks)
            # Make task handler's now time, after the stale timeout
            _TASK_HANDLER._now = datetime.now() + timedelta(
                seconds=_TASK_HANDLER.stale_timeout + timedelay + 1
            )
            _TASK_HANDLER.clean_stale_tasks()  # cleanup of stale tasks in in the save method
            if pers:
                self.assertFalse(t.get_id() in _TASK_HANDLER.to_save)
            self.assertFalse(t.get_id() in _TASK_HANDLER.tasks)
            self.assertEqual(self.char1.ndb.dummy_var, False)
            _TASK_HANDLER.clear()

    def test_disable_stale_removal(self):
        # manual removal of stale tasks.
        timedelay = self.timedelay
        _TASK_HANDLER.stale_timeout = 0
        for pers in (False, True):
            t = utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=pers)
            t.cancel()
            self.assertFalse(t.active())
            _TASK_HANDLER.clock.advance(timedelay)  # make time pass
            if pers:
                self.assertTrue(t.get_id() in _TASK_HANDLER.to_save)
            self.assertTrue(t.get_id() in _TASK_HANDLER.tasks)
            # Make task handler's now time, after the stale timeout
            _TASK_HANDLER._now = datetime.now() + timedelta(
                seconds=_TASK_HANDLER.stale_timeout + timedelay + 1
            )
            t2 = utils.delay(timedelay, dummy_func, self.char1.dbref)
            if pers:
                self.assertTrue(t.get_id() in _TASK_HANDLER.to_save)
            self.assertTrue(t.get_id() in _TASK_HANDLER.tasks)
            self.assertEqual(self.char1.ndb.dummy_var, False)
            # manual removal should still work
            _TASK_HANDLER.clean_stale_tasks()  # cleanup of stale tasks in in the save method
            if pers:
                self.assertFalse(t.get_id() in _TASK_HANDLER.to_save)
            self.assertFalse(t.get_id() in _TASK_HANDLER.tasks)
            _TASK_HANDLER.clear()

    def test_server_restart(self):
        # emulate a server restart
        timedelay = self.timedelay
        utils.delay(timedelay, dummy_func, self.char1.dbref, persistent=True)
        _TASK_HANDLER.clear(False)  # remove all tasks from task handler, do not save this change.
        _TASK_HANDLER.clock.advance(timedelay)  # advance twisted reactor time past callback time
        self.assertEqual(self.char1.ndb.dummy_var, False)  # task has not run
        _TASK_HANDLER.load()  # load persistent tasks from database.
        _TASK_HANDLER.create_delays()  # create new deffered instances from persistent tasks
        _TASK_HANDLER.clock.advance(
            timedelay
        )  # Clock must advance to trigger, even if past timedelay
        self.assertEqual(self.char1.ndb.dummy_var, "dummy_func ran")


class TestIntConversions(TestCase):
    def test_int2str(self):
        self.assertEqual("three", utils.int2str(3))
        # special adjective conversion
        self.assertEqual("3rd", utils.int2str(3, adjective=True))
        # generic adjective conversion
        self.assertEqual("5th", utils.int2str(5, adjective=True))
        # No mapping return int as str
        self.assertEqual("15", utils.int2str(15))

    def test_str2int(self):
        # simple conversions
        self.assertEqual(5, utils.str2int("5"))

        # basic mapped numbers
        self.assertEqual(3, utils.str2int("three"))
        self.assertEqual(20, utils.str2int("twenty"))

        # multi-place numbers
        self.assertEqual(2345, utils.str2int("two thousand, three hundred and forty-five"))

        # ordinal numbers
        self.assertEqual(1, utils.str2int("1st"))
        self.assertEqual(1, utils.str2int("first"))
        self.assertEqual(4, utils.str2int("fourth"))
        # ordinal sound-change conversions
        self.assertEqual(5, utils.str2int("fifth"))
        self.assertEqual(20, utils.str2int("twentieth"))

        with self.assertRaises(ValueError):
            utils.str2int("not a number")


class TestJustify(TestCase):
    def test_justify_whitespace(self):
        result = utils.justify(" ", 1, align="l")
        self.assertEqual(" ", result)

        result = utils.justify("", 1, align="l")
        self.assertEqual(" ", result)

    @parameterized.expand(
        [
            (5, "Task \n ID  "),
            (6, " Task \n  ID  "),
            (7, "Task ID"),
            (8, "Task ID "),
            (9, " Task ID "),
            (10, " Task ID  "),
            (11, "  Task ID  "),
        ]
    )
    def test_center_justify_small(self, width, expected):
        result = utils.justify("Task ID", width, align="c", indent=0, fillchar=" ")
        self.assertEqual(expected, result)

    def test_justify_ansi(self):
        """
        Justify ansistring

        """

        from evennia.utils.ansi import ANSI_RED

        line = ANSIString("This is a |rred|n word")

        result = utils.justify(line, align="c", width=30)

        self.assertIn(ANSI_RED, str(result))
