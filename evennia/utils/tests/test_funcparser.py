"""

Test the funcparser module.

"""

import time
import unittest
from ast import literal_eval
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from parameterized import parameterized
from simpleeval import simple_eval

from evennia.utils import funcparser, test_resources


def _test_callable(*args, **kwargs):
    kwargs.pop("funcparser", None)
    kwargs.pop("raise_errors", None)
    argstr = ", ".join(args)
    kwargstr = ""
    if kwargs:
        kwargstr = (", " if args else "") + ", ".join(f"{key}={val}" for key, val in kwargs.items())
    return f"_test({argstr}{kwargstr})"


def _repl_callable(*args, **kwargs):
    if args:
        return f"r{args[0]}r"
    return "rr"


def _double_callable(*args, **kwargs):
    if args:
        try:
            return int(args[0]) * 2
        except ValueError:
            pass
    return "N/A"


def _eval_callable(*args, **kwargs):
    if args:
        return simple_eval(args[0])

    return ""


def _clr_callable(*args, **kwargs):
    clr, string, *rest = args
    return f"|{clr}{string}|n"


def _typ_callable(*args, **kwargs):
    try:
        if isinstance(args[0], str):
            return type(literal_eval(args[0]))
        else:
            return type(args[0])
    except (SyntaxError, ValueError):
        return type("")


def _add_callable(*args, **kwargs):
    if len(args) > 1:
        return literal_eval(args[0]) + literal_eval(args[1])
    return ""


def _lit_callable(*args, **kwargs):
    return literal_eval(args[0])


def _lsum_callable(*args, **kwargs):
    if isinstance(args[0], (list, tuple)):
        return sum(val for val in args[0])
    return ""


def _raises_callable(*args, **kwargs):
    raise RuntimeError("Test exception raised by test callable")


def _pass_callable(*args, **kwargs):
    kwargs.pop("funcparser", None)
    kwargs.pop("raise_errors", None)
    return str(args) + str(kwargs)


_test_callables = {
    "foo": _test_callable,
    "bar": _test_callable,
    "with spaces": _test_callable,
    "repl": _repl_callable,
    "double": _double_callable,
    "eval": _eval_callable,
    "clr": _clr_callable,
    "typ": _typ_callable,
    "add": _add_callable,
    "lit": _lit_callable,
    "sum": _lsum_callable,
    "raise": _raises_callable,
    "pass": _pass_callable,
}


class TestFuncParser(TestCase):
    """
    Test the FuncParser class

    """

    def setUp(self):

        self.parser = funcparser.FuncParser(_test_callables)

    def test_constructor_wrong_args(self):
        # Given list argument doesn't contain modules or paths.
        with self.assertRaises(AttributeError):
            parser = funcparser.FuncParser(["foo", _test_callable])

    def test_constructor_ignore_non_callables(self):
        # Ignores callables that aren't actual functions.
        parser = funcparser.FuncParser({"foo": 1, "bar": "baz"})

    @patch("evennia.utils.funcparser.variable_from_module")
    def test_constructor_raises(self, patched_variable_from_module):
        # Patched variable from module returns FUNCPARSER_CALLABLES that isn't dict.
        patched_variable_from_module.return_value = ["foo"]
        with self.assertRaises(funcparser.ParsingError):
            parser = funcparser.FuncParser("foo.module")

    @parameterized.expand(
        [
            ("Test normal string", "Test normal string"),
            ("Test noargs1 $foo()", "Test noargs1 _test()"),
            ("Test noargs2 $bar() etc.", "Test noargs2 _test() etc."),
            ("Test noargs3 $with spaces() etc.", "Test noargs3 _test() etc."),
            ("Test noargs4 $foo(), $bar() and $foo", "Test noargs4 _test(), _test() and $foo"),
            ("$foo() Test noargs5", "_test() Test noargs5"),
            ("Test args1 $foo(a,b,c)", "Test args1 _test(a, b, c)"),
            ("Test args2 $bar(foo, bar,    too)", "Test args2 _test(foo, bar, too)"),
            (r'Test args3 $bar(foo, bar, "   too")', "Test args3 _test(foo, bar,    too)"),
            ("Test args4 $foo('')", "Test args4 _test('')"),  # ' treated as literal
            ('Test args4 $foo("")', "Test args4 _test()"),
            ("Test args5 $foo(\(\))", "Test args5 _test(())"),
            ("Test args6 $foo(\()", "Test args6 _test(()"),
            ("Test args7 $foo(())", "Test args7 _test(())"),
            ("Test args8 $foo())", "Test args8 _test())"),
            ("Test args9 $foo(=)", "Test args9 _test(=)"),
            ("Test args10 $foo(\,)", "Test args10 _test(,)"),
            (r'Test args10 $foo(",")', "Test args10 _test(,)"),
            ("Test args11 $foo(()", "Test args11 $foo(()"),  # invalid syntax
            (
                r'Test kwarg1 $bar(foo=1, bar="foo", too=ere)',
                "Test kwarg1 _test(foo=1, bar=foo, too=ere)",
            ),
            ("Test kwarg2 $bar(foo,bar,too=ere)", "Test kwarg2 _test(foo, bar, too=ere)"),
            ("test kwarg3 $foo(foo = bar, bar = ere )", "test kwarg3 _test(foo=bar, bar=ere)"),
            (
                r"test kwarg4 $foo(foo =' bar ',\" bar \"= ere )",
                "test kwarg4 _test(foo=' bar ', \" bar \"=ere)",
            ),
            (
                "Test nest1 $foo($bar(foo,bar,too=ere))",
                "Test nest1 _test(_test(foo, bar, too=ere))",
            ),
            (
                "Test nest2 $foo(bar,$repl(a),$repl()=$repl(),a=b) etc",
                "Test nest2 _test(bar, rar, rr=rr, a=b) etc",
            ),
            ("Test nest3 $foo(bar,$repl($repl($repl(c))))", "Test nest3 _test(bar, rrrcrrr)"),
            (
                "Test nest4 $foo($bar(a,b),$bar(a,$repl()),$bar())",
                "Test nest4 _test(_test(a, b), _test(a, rr), _test())",
            ),
            ("Test escape1 \\$repl(foo)", "Test escape1 $repl(foo)"),
            (
                'Test escape2 "This is $foo() and $bar($bar())", $repl()',
                'Test escape2 "This is _test() and _test(_test())", rr',
            ),
            (
                "Test escape3 'This is $foo() and $bar($bar())', $repl()",
                "Test escape3 'This is _test() and _test(_test())', rr",
            ),
            (
                "Test escape4 $$foo() and $$bar(a,b), $repl()",
                "Test escape4 $foo() and $bar(a,b), rr",
            ),
            ("Test with color |r$foo(a,b)|n is ok", "Test with color |r_test(a, b)|n is ok"),
            ("Test malformed1 This is $foo( and $bar(", "Test malformed1 This is $foo( and $bar("),
            (
                "Test malformed2 This is $foo( and  $bar()",
                "Test malformed2 This is $foo( and  _test()",
            ),
            ("Test malformed3 $", "Test malformed3 $"),
            (
                "Test malformed4 This is $foo(a=b and $bar(",
                "Test malformed4 This is $foo(a=b and $bar(",
            ),
            (
                "Test malformed5 This is $foo(a=b, and $repl()",
                "Test malformed5 This is $foo(a=b, and rr",
            ),
            ("Test nonstr 4x2 = $double(4)", "Test nonstr 4x2 = 8"),
            ("Test nonstr 4x2 = $double(foo)", "Test nonstr 4x2 = N/A"),
            ("Test clr $clr(r, This is a red string!)", "Test clr |rThis is a red string!|n"),
            ("Test eval1 $eval(21 + 21 - 10)", "Test eval1 32"),
            ("Test eval2 $eval((21 + 21) / 2)", "Test eval2 21.0"),
            ("Test eval3 $eval(\"'21' + 'foo' + 'bar'\")", "Test eval3 21foobar"),
            (r"Test eval4 $eval('21' + '$repl()' + \"\" + str(10 // 2))", "Test eval4 21rr5"),
            (
                r"Test eval5 $eval(\'21\' + \'\$repl()\' + \'\' + str(10 // 2))",
                "Test eval5 21$repl()5",
            ),
            ("Test eval6 $eval(\"'$repl(a)' + '$repl(b)'\")", "Test eval6 rarrbr"),
            ("Test type1 $typ([1,2,3,4])", "Test type1 <class 'list'>"),
            ("Test type2 $typ((1,2,3,4))", "Test type2 <class 'tuple'>"),
            ("Test type3 $typ({1,2,3,4})", "Test type3 <class 'set'>"),
            ("Test type4 $typ({1:2,3:4})", "Test type4 <class 'dict'>"),
            ("Test type5 $typ(1), $typ(1.0)", "Test type5 <class 'int'>, <class 'float'>"),
            (
                "Test type6 $typ(\"'1'\"), $typ('\"1.0\"')",
                "Test type6 <class 'str'>, <class 'str'>",
            ),
            ("Test add1 $add(1, 2)", "Test add1 3"),
            ("Test add2 $add([1,2,3,4], [5,6])", "Test add2 [1, 2, 3, 4, 5, 6]"),
            ("Test literal1 $sum($lit([1,2,3,4,5,6]))", "Test literal1 21"),
            ("Test literal2 $typ($lit(1))", "Test literal2 <class 'int'>"),
            ("Test literal3 $typ($lit(1)aaa)", "Test literal3 <class 'str'>"),
            ("Test literal4 $typ(aaa$lit(1))", "Test literal4 <class 'str'>"),
            ("Test spider's thread", "Test spider's thread"),
        ]
    )
    def test_parse(self, string, expected):
        """
        Test parsing of string.

        """
        # t0 = time.time()
        # from evennia import set_trace;set_trace()
        ret = self.parser.parse(string, raise_errors=True)
        # t1 = time.time()
        # print(f"time: {(t1-t0)*1000} ms")
        self.assertEqual(expected, ret)

    @parameterized.expand(
        (
            "Test malformed This is $dummy(a, b) and $bar(",
            "Test $funcNotFound()",
        )
    )
    def test_parse_raise_unparseable(self, unparseable):
        """
        Make sure error is raised if told to do so.

        """
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(unparseable, raise_errors=True)

    @parameterized.expand(
        [
            # max_nest, cause error for 4 nested funcs?
            (0, False),
            (1, False),
            (2, False),
            (3, False),
            (4, True),
            (5, True),
            (6, True),
        ]
    )
    def test_parse_max_nesting(self, max_nest, ok):
        """
        Make sure it is an error if the max nesting value is reached. We test
        four nested functions against differnt MAX_NESTING values.

        TODO: Does this make sense? When it sees the first function, len(callstack)
        is 0. It doesn't raise until the stack length is greater than the
        _MAX_NESTING value, which means you can nest 4 values with a value of
        2, as demonstrated by this test.
        """
        string = "$add(1, $add(1, $add(1, $eval(42))))"

        with patch("evennia.utils.funcparser._MAX_NESTING", max_nest):
            if ok:
                ret = self.parser.parse(string, raise_errors=True)
                self.assertEqual(ret, "45")
            else:
                with self.assertRaises(funcparser.ParsingError):
                    self.parser.parse(string, raise_errors=True)

    def test_parse_underlying_exception(self):
        string = "test $add(1, 1) $raise()"
        ret = self.parser.parse(string)

        # TODO: Does this return value actually make sense?
        # It completed the first function call.
        self.assertEqual("test 2 $raise()", ret)

        with self.assertRaises(RuntimeError):
            self.parser.parse(string, raise_errors=True)

    def test_parse_strip(self):
        """
        Test the parser's strip functionality.

        """
        string = "Test $foo(a,b, $bar()) and $repl($eval(3+2)) things"
        ret = self.parser.parse(string, strip=True)
        self.assertEqual("Test  and  things", ret)

    def test_parse_whitespace_preserved(self):
        string = "The answer is $foobar(1, x)"  # not found, so should be preserved
        ret = self.parser.parse(string)
        self.assertEqual("The answer is $foobar(1, x)", ret)

        string = 'The $pass(testing,  bar= $dum(b = "test2" , a), ) $pass('
        ret = self.parser.parse(string)
        self.assertEqual("The ('testing',){'bar': '$dum(b = \"test2\" , a)'} $pass(", ret)

    def test_parse_escape(self):
        """
        Test the parser's escape functionality.

        """
        string = "Test $foo(a) and $bar() and $rep(c) things"
        ret = self.parser.parse(string, escape=True)
        self.assertEqual("Test \$foo(a) and \$bar() and \$rep(c) things", ret)

    def test_parse_lit(self):
        """
        Get non-strings back from parsing.

        """
        string = "$lit(123)"

        # normal parse
        ret = self.parser.parse(string)
        self.assertEqual("123", ret)
        self.assertTrue(isinstance(ret, str))

        # parse lit
        ret = self.parser.parse_to_any(string)
        self.assertEqual(123, ret)
        self.assertTrue(isinstance(ret, int))

        ret = self.parser.parse_to_any("$lit([1,2,3,4])")
        self.assertEqual([1, 2, 3, 4], ret)
        self.assertTrue(isinstance(ret, list))

        ret = self.parser.parse_to_any("$lit(\"''\")")
        self.assertEqual("", ret)
        self.assertTrue(isinstance(ret, str))

        ret = self.parser.parse_to_any(r"$lit(\'\')")
        self.assertEqual("", ret)
        self.assertTrue(isinstance(ret, str))

        # mixing a literal with other chars always make a string
        ret = self.parser.parse_to_any(string + "aa")
        self.assertEqual("123aa", ret)
        self.assertTrue(isinstance(ret, str))

        ret = self.parser.parse_to_any("test")
        self.assertEqual("test", ret)
        self.assertTrue(isinstance(ret, str))

    def test_kwargs_overrides(self):
        """
        Test so default kwargs are added and overridden properly

        """
        # default kwargs passed on initializations
        parser = funcparser.FuncParser(_test_callables, test="foo")
        ret = parser.parse("This is a $foo() string")
        self.assertEqual("This is a _test(test=foo) string", ret)

        # override in the string itself

        ret = parser.parse("This is a $foo(test=bar,foo=moo) string")
        self.assertEqual("This is a _test(test=bar, foo=moo) string", ret)

        # parser kwargs override the other types

        ret = parser.parse("This is a $foo(test=bar,foo=moo) string", test="override", foo="bar")
        self.assertEqual("This is a _test(test=override, foo=bar) string", ret)

        # non-overridden kwargs shine through

        ret = parser.parse("This is a $foo(foo=moo) string", foo="bar")
        self.assertEqual("This is a _test(test=foo, foo=bar) string", ret)


class _DummyObj:
    def __init__(self, name):
        self.name = name

    def get_display_name(self, looker=None):
        return self.name


class TestDefaultCallables(TestCase):
    """
    Test default callables.

    """

    def setUp(self):
        from django.conf import settings

        self.parser = funcparser.FuncParser(
            {**funcparser.FUNCPARSER_CALLABLES, **funcparser.ACTOR_STANCE_CALLABLES}
        )

        self.obj1 = _DummyObj("Char1")
        self.obj2 = _DummyObj("Char2")

    @parameterized.expand(
        [
            ("Test py1 $eval('')", "Test py1 "),
        ]
    )
    def test_callable(self, string, expected):
        """
        Test callables with various input strings

        """
        ret = self.parser.parse(string, raise_errors=True)
        self.assertEqual(expected, ret)

    @parameterized.expand(
        [
            ("$You() $conj(smile) at him.", "You smile at him.", "Char1 smiles at him."),
            ("$You() $conj(smile) at $You(char1).", "You smile at You.", "Char1 smiles at Char1."),
            ("$You() $conj(smile) at $You(char2).", "You smile at Char2.", "Char1 smiles at You."),
            (
                "$You(char2) $conj(smile) at $you(char1).",
                "Char2 smile at you.",
                "You smiles at Char1.",
            ),
            (
                "$You() $conj(smile) to $pron(yourself,m).",
                "You smile to yourself.",
                "Char1 smiles to himself.",
            ),
            (
                "$You() $conj(smile) to $pron(herself).",
                "You smile to yourself.",
                "Char1 smiles to herself.",
            ),  # reverse reference
        ]
    )
    def test_conjugate(self, string, expected_you, expected_them):
        """
        Test the $conj(), $you() and $pron callables with various input strings.
        """
        mapping = {"char1": self.obj1, "char2": self.obj2}
        ret = self.parser.parse(
            string, caller=self.obj1, receiver=self.obj1, mapping=mapping, raise_errors=True
        )
        self.assertEqual(expected_you, ret)
        ret = self.parser.parse(
            string, caller=self.obj1, receiver=self.obj2, mapping=mapping, raise_errors=True
        )
        self.assertEqual(expected_them, ret)

    def test_conjugate_missing_args(self):
        string = "You $conj(smile)"
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, raise_errors=True)

    @parameterized.expand(
        [
            ("male", "Char1 smiles at himself"),
            ("female", "Char1 smiles at herself"),
            ("neutral", "Char1 smiles at itself"),
            ("plural", "Char1 smiles at themselves"),
        ]
    )
    def test_pronoun_gender(self, gender, expected):
        string = "Char1 smiles at $pron(yourself)"

        self.obj1.gender = gender
        ret = self.parser.parse(string, caller=self.obj1, raise_errors=True)
        self.assertEqual(expected, ret)

        self.obj1.gender = lambda: gender
        ret = self.parser.parse(string, caller=self.obj1, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_pronoun_viewpoint(self):
        string = "Char1 smiles at $pron(I)"

        ret = self.parser.parse(string, caller=self.obj1, viewpoint="op", raise_errors=True)
        self.assertEqual("Char1 smiles at it", ret)

    def test_pronoun_capitalize(self):
        string = "Char1 smiles at $pron(I)"

        ret = self.parser.parse(string, caller=self.obj1, capitalize=True, raise_errors=True)
        self.assertEqual("Char1 smiles at It", ret)

        string = "Char1 smiles at $Pron(I)"
        ret = self.parser.parse(string, caller=self.obj1, capitalize=True, raise_errors=True)
        self.assertEqual("Char1 smiles at It", ret)

    @parameterized.expand(
        [
            ("Test $pad(Hello, 20, c, -) there", "Test -------Hello-------- there"),
            (
                "Test $pad(Hello, width=20, align=c, fillchar=-) there",
                "Test -------Hello-------- there",
            ),
            ("Test $crop(This is a long test, 12)", "Test This is[...]"),
            ("Some $space(10) here", "Some            here"),
            ("Some $clr(b, blue color) now", "Some |bblue color|n now"),
            ("Some $add(1, 2) things", "Some 3 things"),
            ("Some $sub(10, 2) things", "Some 8 things"),
            ("Some $mult(3, 2) things", "Some 6 things"),
            ("Some $div(6, 2) things", "Some 3.0 things"),
            ("Some $toint(6) things", "Some 6 things"),
            ("Some $toint(3 + 3) things", "Some 6 things"),
            ("Some $ljust(Hello, 30)", "Some Hello                         "),
            ("Some $rjust(Hello, 30)", "Some                          Hello"),
            ("Some $rjust(Hello, width=30)", "Some                          Hello"),
            ("Some $cjust(Hello, 30)", "Some             Hello             "),
            (
                "There $pluralize(is, 1, are) one $pluralize(goose, 1, geese) here.",
                "There is one goose here.",
            ),
            (
                "There $pluralize(is, 2, are) two $pluralize(goose, 2, geese) here.",
                "There are two geese here.",
            ),
            (
                "There is $int2str(1) murderer, but $int2str(12) suspects.",
                "There is one murderer, but twelve suspects.",
            ),
            ("There is $an(thing) here", "There is a thing here"),
            ("Some $eval(\"'-'*20\")Hello", "Some --------------------Hello"),
            ('$crop("spider\'s silk", 5)', "spide"),
            ("$crop(spider's silk, 5)", "spide"),
            ("$an(apple)", "an apple"),
            ("$round(2.9) apples", "3.0 apples"),
            ("$round(2.967, 1) apples", "3.0 apples"),
            # Degenerate cases
            ("$int2str() apples", " apples"),
            ("$int2str(x) apples", "x apples"),
            ("$int2str(1 + 1) apples", "1 + 1 apples"),
            ("$int2str(13) apples", "13 apples"),
            ("$toint([1, 2, 3]) apples", "[1, 2, 3] apples"),
            ("$an() foo bar", " foo bar"),
            ("$add(1) apple", " apple"),
            ("$add(1, [1, 2]) apples", " apples"),
            ("$round() apples", " apples"),
            ("$choice() apple", " apple"),
            ("A $pad() apple", "A  apple"),
            ("A $pad(tasty, 13, x, -) apple", "A ----tasty---- apple"),
            ("A $crop() apple", "A  apple"),
            ("A $space() apple", "A  apple"),
            ("A $justify() apple", "A  apple"),
            ("A $clr() apple", "A  apple"),
            ("A $clr(red) apple", "A red apple"),
            ("10 $pluralize()", "10 "),
            ("10 $pluralize(apple, 10)", "10 apples"),
            ("1 $pluralize(apple)", "1 apple"),
            ("You $conj()", "You "),
            ("$pron() smiles", " smiles"),
        ]
    )
    def test_other_callables(self, string, expected):
        """
        Test default callables.

        """
        ret = self.parser.parse(string, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_random(self):
        """
        Test random callable, with ranges of expected values.
        """
        string = "$random(1,10)"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(1 <= ret <= 10)

        string = "$random()"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(0 <= ret <= 1)

        string = "$random(2)"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(0 <= ret <= 2)

        string = "$random(1.0, 3.0)"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(isinstance(ret, float))
            self.assertTrue(1.0 <= ret <= 3.0)

        string = "$random([1,2]) apples"
        ret = self.parser.parse_to_any(string)
        self.assertEqual(" apples", ret)
        with self.assertRaises(TypeError):
            ret = self.parser.parse_to_any(string, raise_errors=True)

    # @unittest.skip("underlying function seems broken")
    def test_choice(self):
        """
        Test choice callable, where output could be either choice.
        """
        string = "$choice(red, green) apple"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("red apple", "green apple"))

        string = "$choice([red, green]) apple"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("red apple", "green apple"))

        string = "$choice(['red', 'green']) apple"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("red apple", "green apple"))

        string = "$choice([1, 2])"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("1", "2"))
        ret = self.parser.parse_to_any(string)
        self.assertIn(ret, (1, 2))

        string = "$choice(1, 2)"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("1", "2"))
        ret = self.parser.parse_to_any(string)
        self.assertIn(ret, (1, 2))

    def test_choice_quotes(self):
        """
        Test choice, but also commas embedded.
        """

        string = "$choice(spider's, devil's, mummy's, zombie's)"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("spider's", "devil's", "mummy's", "zombie's"))

        string = '$choice("Tiamat, queen of dragons", "Dracula, lord of the night")'
        ret = self.parser.parse(string)
        self.assertIn(ret, ("Tiamat, queen of dragons", "Dracula, lord of the night"))

        # single quotes are ignored, so this becomes many entries
        string = "$choice('Tiamat, queen of dragons', 'Dracula, lord of the night')"
        ret = self.parser.parse(string)
        self.assertIn(ret, ("'Tiamat", "queen of dragons'", "'Dracula", "lord of the night'"))

    def test_randint(self):
        string = "$randint(1.0, 3.0)"
        ret = self.parser.parse_to_any(string, raise_errors=True)
        self.assertTrue(isinstance(ret, int))
        self.assertTrue(1.0 <= ret <= 3.0)

    def test_nofunc(self):
        self.assertEqual(
            self.parser.parse("as$382ewrw w we w werw,|44943}"),
            "as$382ewrw w we w werw,|44943}",
        )

    def test_incomplete(self):
        self.assertEqual(
            self.parser.parse("testing $blah{without an ending."),
            "testing $blah{without an ending.",
        )

    def test_single_func(self):
        self.assertEqual(
            self.parser.parse("this is a test with $pad(centered, 20) text in it."),
            "this is a test with       centered       text in it.",
        )

    def test_nested(self):
        self.assertEqual(
            self.parser.parse(
                "this $crop(is a test with $pad(padded, 20) text in $pad(pad2, 10) a crop, 80)"
            ),
            "this is a test with        padded        text in    pad2    a crop",
        )

    def test_escaped(self):
        raw_str = (
            'this should be $pad("""escaped,""" and """instead,""" cropped $crop(with a long,5)'
            " text., 80)"
        )
        expected = (
            "this should be                    escaped, and instead, cropped with  text.           "
            "         "
        )
        result = self.parser.parse(raw_str)
        self.assertEqual(
            result,
            expected,
        )


class TestCallableSearch(test_resources.BaseEvenniaTest):
    """
    Test the $search(query) callable

    """

    def setUp(self):
        super().setUp()
        self.parser = funcparser.FuncParser(funcparser.SEARCHING_CALLABLES)

    def test_search_obj(self):
        """
        Test searching for an object

        """
        string = "$search(Char)"
        expected = self.char1

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_account(self):
        """
        Test searching for an account

        """
        string = "$search(TestAccount, type=account)"
        expected = self.account
        self.account.locks.add("control:id(%s)" % self.char1.dbref)

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_script(self):
        """
        Test searching for a script

        """
        string = "$search(Script, type=script)"
        expected = self.script
        self.script.locks.add("control:id(%s)" % self.char1.dbref)

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_obj_embedded(self):
        """
        Test searching for an object - embedded in str

        """
        string = "This is $search(Char) the guy."
        expected = "This is " + str(self.char1) + " the guy."

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_tag(self):
        """
        Test searching for a tag
        """
        self.char1.tags.add("foo")

        string = "This is $search(foo, type=tag)"
        expected = "This is %s" % str(self.char1)

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_not_found(self):
        string = "$search(foo)"
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=False)
        self.assertEqual("$search(foo)", ret)

        ret = self.parser.parse_to_any(
            string, caller=self.char1, return_list=True, raise_errors=False
        )
        self.assertEqual([], ret)

    def test_search_multiple_results_no_list(self):
        """
        Test exception when search returns multiple results but list is not requested
        """
        string = "$search(BaseObject)"
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)

    def test_search_no_access(self):
        string = "Go to $search(Room)"
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, caller=self.char2, return_list=True, raise_errors=True)

    def test_search_no_caller(self):
        string = "$search(Char)"
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, caller=None, raise_errors=True)

    def test_search_no_args(self):
        string = "$search()"
        ret = self.parser.parse(string, caller=self.char1, return_list=False, raise_errors=True)
        self.assertEqual("None", ret)

        ret = self.parser.parse(string, caller=self.char1, return_list=True, raise_errors=True)
        self.assertEqual("[]", ret)

    def test_search_nested__issue2902(self):
        """
        Search for objects by-tag, check that the result is a valid object

        """
        # we
        parser = funcparser.FuncParser(
            {**funcparser.SEARCHING_CALLABLES, **funcparser.FUNCPARSER_CALLABLES}
        )

        # set up search targets
        self.obj1.tags.add("beach", category="zone")
        self.obj2.tags.add("beach", category="zone")

        # first a plain search
        string = "$objlist(beach,category=zone,type=tag)"
        ret = parser.parse_to_any(string, caller=self.char1, raise_errors=True)

        self.assertEqual(ret, [self.obj1, self.obj2])

        # get random result from the possible matches
        string = "$choice($objlist(beach,category=zone,type=tag))"
        ret = parser.parse_to_any(string, caller=self.char1, raise_errors=True)

        self.assertIn(ret, [self.obj1, self.obj2])

        # test wrapping in $obj(), should just pass object through
        string = "$obj($choice($objlist(beach,category=zone,type=tag)))"
        ret = parser.parse_to_any(string, caller=self.char1, raise_errors=True)

        self.assertIn(ret, [self.obj1, self.obj2])
