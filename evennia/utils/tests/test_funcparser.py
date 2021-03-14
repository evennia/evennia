"""

Test the funcparser module.

"""

from parameterized import parameterized
from django.test import TestCase

from evennia.utils import funcparser


def _test_callable(*args, **kwargs):
    argstr = ", ".join(args)
    kwargstr = ""
    if kwargs:
        kwargstr = (", " if args else "") + (
            ", ".join(f"{key}={val}" for key, val in kwargs.items()))
    return f"_test({argstr}{kwargstr})"


_test_callables = {
    "foo": _test_callable,
    "bar": _test_callable,
    "with spaces": _test_callable,
}

class TestFuncParser(TestCase):
    """
    Test the FuncParser class

    """

    def setUp(self):

        self.parser = funcparser.FuncParser(
            _test_callables
        )

    @parameterized.expand([
        ("This is a normal string", "This is a normal string"),
        ("This is $foo()", "This is _test()"),
        ("This is $bar() etc.", "This is _test() etc."),
        ("This is $with spaces() etc.", "This is _test() etc."),
        ("Two $foo(), $bar() and $foo", "Two _test(), _test() and $foo"),
        ("Test args1 $foo(a,b,c)", "Test args1 _test(a, b, c)"),
        ("Test args2 $bar(foo, bar, too)", "Test args2 _test(foo,  bar,  too)"),
        ("Test kwarg1 $bar(foo=1, bar='foo', too=ere)",
         "Test kwarg1 _test(foo=1,  bar=foo,  too=ere)"),
        ("Test kwarg2 $bar(foo,bar,too=ere)",
         "Test kwarg2 _test(foo, bar, too=ere)"),
        ("Test nest1 $foo($bar(foo, bar, too=ere))",
         "Test nest1 _test(_test(foo, bar, too=ere))"),
    ])
    def test_parse(self, string, expected):
        """
        Test parsing of string.

        """
        ret = self.parser.parse(string, raise_errors=True)
        self.assertEqual(expected, ret, "Parsing mismatch")
