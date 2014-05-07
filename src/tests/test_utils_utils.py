# test with game/manage.py test
import unittest

from src.utils import utils

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
        

class TestWildcardToRegexp(unittest.TestCase):
    def test_wildcard_to_regexp(self):
        # self.assertEqual(expected, wildcard_to_regexp(instring))
        assert True # TODO: implement your test here

class TestTimeFormat(unittest.TestCase):
    def test_time_format(self):
        # self.assertEqual(expected, time_format(seconds, style))
        assert True # TODO: implement your test here

class TestDatetimeFormat(unittest.TestCase):
    def test_datetime_format(self):
        # self.assertEqual(expected, datetime_format(dtobj))
        assert True # TODO: implement your test here

class TestHostOsIs(unittest.TestCase):
    def test_host_os_is(self):
        # self.assertEqual(expected, host_os_is(osname))
        assert True # TODO: implement your test here

class TestGetEvenniaVersion(unittest.TestCase):
    def test_get_evennia_version(self):
        # self.assertEqual(expected, get_evennia_version())
        assert True # TODO: implement your test here

class TestPypathToRealpath(unittest.TestCase):
    def test_pypath_to_realpath(self):
        # self.assertEqual(expected, pypath_to_realpath(python_path, file_ending))
        assert True # TODO: implement your test here

class TestToUnicode(unittest.TestCase):
    def test_to_unicode(self):
        # self.assertEqual(expected, to_unicode(obj, encoding, force_string))
        assert True # TODO: implement your test here

class TestToStr(unittest.TestCase):
    def test_to_str(self):
        # self.assertEqual(expected, to_str(obj, encoding, force_string))
        assert True # TODO: implement your test here

class TestValidateEmailAddress(unittest.TestCase):
    def test_validate_email_address(self):
        # self.assertEqual(expected, validate_email_address(emailaddress))
        assert True # TODO: implement your test here

class TestInheritsFrom(unittest.TestCase):
    def test_inherits_from(self):
        # self.assertEqual(expected, inherits_from(obj, parent))
        assert True # TODO: implement your test here

class TestServerServices(unittest.TestCase):
    def test_server_services(self):
        # self.assertEqual(expected, server_services())
        assert True # TODO: implement your test here

class TestUsesDatabase(unittest.TestCase):
    def test_uses_database(self):
        # self.assertEqual(expected, uses_database(name))
        assert True # TODO: implement your test here

class TestDelay(unittest.TestCase):
    def test_delay(self):
        # self.assertEqual(expected, delay(delay, callback, retval))
        assert True # TODO: implement your test here

class TestCleanObjectCaches(unittest.TestCase):
    def test_clean_object_caches(self):
        # self.assertEqual(expected, clean_object_caches(obj))
        assert True # TODO: implement your test here

class TestRunAsync(unittest.TestCase):
    def test_run_async(self):
        # self.assertEqual(expected, run_async(to_execute, *args, **kwargs))
        assert True # TODO: implement your test here

class TestCheckEvenniaDependencies(unittest.TestCase):
    def test_check_evennia_dependencies(self):
        # self.assertEqual(expected, check_evennia_dependencies())
        assert True # TODO: implement your test here

class TestHasParent(unittest.TestCase):
    def test_has_parent(self):
        # self.assertEqual(expected, has_parent(basepath, obj))
        assert True # TODO: implement your test here

class TestModImport(unittest.TestCase):
    def test_mod_import(self):
        # self.assertEqual(expected, mod_import(module))
        assert True # TODO: implement your test here

class TestAllFromModule(unittest.TestCase):
    def test_all_from_module(self):
        # self.assertEqual(expected, all_from_module(module))
        assert True # TODO: implement your test here

class TestVariableFromModule(unittest.TestCase):
    def test_variable_from_module(self):
        # self.assertEqual(expected, variable_from_module(module, variable, default))
        assert True # TODO: implement your test here

class TestStringFromModule(unittest.TestCase):
    def test_string_from_module(self):
        # self.assertEqual(expected, string_from_module(module, variable, default))
        assert True # TODO: implement your test here

class TestInitNewPlayer(unittest.TestCase):
    def test_init_new_player(self):
        # self.assertEqual(expected, init_new_player(player))
        assert True # TODO: implement your test here

class TestStringSimilarity(unittest.TestCase):
    def test_string_similarity(self):
        # self.assertEqual(expected, string_similarity(string1, string2))
        assert True # TODO: implement your test here

class TestStringSuggestions(unittest.TestCase):
    def test_string_suggestions(self):
        # self.assertEqual(expected, string_suggestions(string, vocabulary, cutoff, maxnum))
        assert True # TODO: implement your test here

class TestStringPartialMatching(unittest.TestCase):
    def test_string_partial_matching(self):
        # self.assertEqual(expected, string_partial_matching(alternatives, inp, ret_index))
        assert True # TODO: implement your test here

class TestFormatTable(unittest.TestCase):
    def test_format_table(self):
        # self.assertEqual(expected, format_table(table, extra_space))
        assert True # TODO: implement your test here

class TestGetEvenniaPids(unittest.TestCase):
    def test_get_evennia_pids(self):
        # self.assertEqual(expected, get_evennia_pids())
        assert True # TODO: implement your test here

if __name__ == '__main__':
    unittest.main()
