"""
Generic function parser for functions embedded in a string, on the form
`$funcname(*args, **kwargs)`, for example:

    "A string $foo() with $bar(a, b, c, $moo(), d=23) etc."

Each arg/kwarg can also be another nested function. These will be executed from
the deepest-nested first and used as arguments for the higher-level function.

This is the base for all forms of embedded func-parsing, like inlinefuncs and
protfuncs. Each function available to use must be registered as a 'safe'
function for the parser to accept it. This is usually done in a module with
regular Python functions on the form:

```python
# in a module whose path is passed to the parser

def _helper(x):
    # use underscore to NOT make the function available as a callable

def funcname(*args, **kwargs):
    # this can be accecssed as $funcname(*args, **kwargs)
    # it must always accept *args and **kwargs.
    ...
    return something

```

Usage:

```python
from evennia.utils.funcparser

parser = FuncParser("path.to.module_with_callables")
result = parser.parse("String with $funcname() in it")

```

The `FuncParser` also accepts a direct dict mapping of `{'name': callable, ...}`.


"""
import re
import dataclasses
import inspect
import random
from functools import partial
from django.conf import settings
from ast import literal_eval
from simpleeval import simple_eval
from evennia.utils import logger
from evennia.utils.utils import (
    make_iter, callables_from_module, variable_from_module, pad, crop, justify)
from evennia.utils import search
from evennia.utils.verb_conjugation.conjugate import verb_actor_stance_components

_CLIENT_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_MAX_NESTING = 20

_ESCAPE_CHAR = "\\"
_START_CHAR = "$"


@dataclasses.dataclass
class ParsedFunc:
    """
    Represents a function parsed from the string

    """
    prefix: str = "$"
    funcname: str = ""
    args: list = dataclasses.field(default_factory=list)
    kwargs: dict = dataclasses.field(default_factory=dict)

    # state storage
    fullstr: str = ""
    infuncstr: str = ""
    single_quoted: bool = False
    double_quoted: bool = False
    current_kwarg: str = ""
    open_lparens: int = 0
    open_lsquate: int = 0
    open_lcurly: int = 0
    exec_return = ""

    def get(self):
        return self.funcname, self.args, self.kwargs

    def __str__(self):
        return self.fullstr + self.infuncstr


class ParsingError(RuntimeError):
    """
    Failed to parse for some reason.
    """
    pass


class FuncParser:
    """
    Sets up a parser for strings containing $funcname(*args, **kwargs) substrings.

    """

    def __init__(self,
                 callables,
                 start_char=_START_CHAR,
                 escape_char=_ESCAPE_CHAR,
                 max_nesting=_MAX_NESTING,
                 **default_kwargs):
        """
        Initialize the parser.

        Args:
            callables (str, module, list or dict): Where to find
                'safe' functions to make available in the parser. These modules
                can have a dict `FUNCPARSER_CALLABLES = {"funcname": callable, ...}`.
                If no such dict exists, all callables in provided modules (whose names
                don't start with an underscore) will be loaded as callables. Each
                callable will will be available to call as `$funcname(*args, **kwags)`
                during parsing. If `callables` is a `str`, this should be the path
                to such a module. A `list` can either be a list of paths or module
                objects. If a `dict`, this should be a direct mapping
                `{"funcname": callable, ...}` to use.
            start_char (str, optional): A character used to identify the beginning
                of a parseable function. Default is `$`.
            escape_char (str, optional): Prepend characters with this to have
                them not count as a function. Default is `\\`.
            max_nesting (int, optional): How many levels of nested function calls
                are allowed, to avoid exploitation. Default is 20.
            **default_kwargs: These kwargs will be passed into all callables. These
                kwargs can be overridden both by kwargs passed direcetly to `.parse` _and_
                by kwargs given directly in the string `$funcname` call. They are
                suitable for global defaults that is intended to be changed by the
                user. To _guarantee_ a call always gets a particular kwarg, pass it
                into `.parse` as `**reserved_kwargs` instead.

        """
        if isinstance(callables, dict):
            loaded_callables = {**callables}
        else:
            # load all modules/paths in sequence. Later-added will override
            # earlier same-named callables (allows for overriding evennia defaults)
            loaded_callables = {}
            for module_or_path in make_iter(callables):
                callables_mapping = variable_from_module(
                    module_or_path, variable="FUNCPARSER_CALLABLES")
                if callables_mapping:
                    try:
                        # mapping supplied in variable
                        loaded_callables.update(callables_mapping)
                    except ValueError:
                        raise ParsingError(
                            f"Failure to parse - {module_or_path}.FUNCPARSER_CALLABLES "
                            "(must be a dict {'funcname': callable, ...})")
                else:
                    # use all top-level variables
                    # (handles both paths and module instances
                    loaded_callables.update(callables_from_module(module_or_path))
        self.validate_callables(loaded_callables)
        self.callables = loaded_callables
        self.escape_char = escape_char
        self.start_char = start_char
        self.default_kwargs = default_kwargs

    def validate_callables(self, callables):
        """
        Validate the loaded callables. Each callable must support at least
        `funcname(*args, **kwargs)`.
        property.

        Args:
            callables (dict): A mapping `{"funcname": callable, ...}` to validate

        Raise:
            AssertionError: If invalid callable was found.

        Notes:
            This is also a good method to override for individual parsers
            needing to run any particular pre-checks.

        """
        for funcname, clble in callables.items():
            try:
                mapping = inspect.getfullargspec(clble)
            except TypeError:
                logger.log_trace(f"Could not run getfullargspec on {funcname}: {clble}")
            else:
                assert mapping.varargs, f"Parse-func callable '{funcname}' does not support *args."
                assert mapping.varkw, f"Parse-func callable '{funcname}' does not support **kwargs."

    def execute(self, parsedfunc, raise_errors=False, **reserved_kwargs):
        """
        Execute a parsed function

        Args:
            parsedfunc (ParsedFunc): This dataclass holds the parsed details
                of the function.
            raise_errors (bool, optional): Raise errors. Otherwise return the
                string with the function unparsed.
            **reserved_kwargs: These kwargs are _guaranteed_ to always be passed into
                the callable on every call. It will override any default kwargs
                _and_ also a same-named kwarg given manually in the $funcname
                call. This is often used by Evennia to pass required data into
                the callable, for example the current Session for inlinefuncs.
        Returns:
            any: The result of the execution. If this is a nested function, it
                can be anything, otherwise it will be converted to a string later.
                Always a string on un-raised error (the unparsed function string).

        Raises:
            ParsingError, any: A `ParsingError` if the function could not be
            found, otherwise error from function definition. Only raised if
            `raise_errors` is `True`

        Notes:
            The kwargs passed into the callable will be a mixture of the
            `default_kwargs` passed into `FuncParser.__init__`, kwargs given
            directly in the `$funcdef` string, and the `reserved_kwargs` this
            function gets from `.parse()`. For colliding keys, funcdef-defined
            kwargs will override default kwargs while reserved kwargs will always
            override the other two.

        """
        funcname, args, kwargs = parsedfunc.get()
        func = self.callables.get(funcname)

        if not func:
            if raise_errors:
                available = ", ".join(f"'{key}'" for key in self.callables)
                raise ParsingError(f"Unknown parsed function '{str(parsedfunc)}' "
                                   f"(available: {available})")
            return str(parsedfunc)

        # build kwargs in the proper priority order
        kwargs = {**self.default_kwargs, **kwargs, **reserved_kwargs}

        try:
            return func(*args, **kwargs)
        except ParsingError:
            if raise_errors:
                raise
            return str(parsedfunc)
        except Exception:
            logger.log_trace()
            if raise_errors:
                raise
            return str(parsedfunc)

    def parse(self, string, raise_errors=False, escape=False,
              strip=False, return_str=True, **reserved_kwargs):
        """
        Use parser to parse a string that may or may not have `$funcname(*args, **kwargs)`
        - style tokens in it. Only the callables used to initiate the parser
          will be eligible for parsing, others will remain un-parsed.

        Args:
            string (str): The string to parse.
            raise_errors (bool, optional): By default, a failing parse just
                means not parsing the string but leaving it as-is. If this is
                `True`, errors (like not closing brackets) will lead to an
                ParsingError.
            escape (bool, optional): If set, escape all found functions so they
                are not executed by later parsing.
            strip (bool, optional): If set, strip any inline funcs from string
                as if they were not there.
            return_str (bool, optional): If set (default), always convert the
                parse result to a string, otherwise return the result of the
                latest called inlinefunc (if called separately).
            **reserved_kwargs: If given, these are guaranteed to _always_ pass
                as part of each parsed callable's **kwargs. These  override
                same-named default options given in `__init__` as well as any
                same-named kwarg given in the string function. This is because
                it is often used by Evennia to pass necessary kwargs into each
                callable (like the current Session object for inlinefuncs).

        Returns:
            str or any: The parsed string, or the same string on error (if
                `raise_errors` is `False`). This is always a string

        Raises:
            ParsingError: If a problem is encountered and `raise_errors` is True.

        """
        start_char = self.start_char
        escape_char = self.escape_char

        # replace e.g. $$ with \$ so we only need to handle one escape method
        string = string.replace(start_char + start_char, escape_char + start_char)

        # parsing state
        callstack = []

        single_quoted = False
        double_quoted = False
        open_lparens = 0  # open (
        open_lsquare = 0  # open [
        open_lcurly = 0   # open {
        escaped = False
        current_kwarg = ""
        exec_return = ""

        curr_func = None
        fullstr = ''  # final string
        infuncstr = ''  # string parts inside the current level of $funcdef (including $)

        for char in string:

            if escaped:
                # always store escaped characters verbatim
                if curr_func:
                    infuncstr += char
                else:
                    fullstr += char
                escaped = False
                continue

            if char == escape_char:
                # don't store the escape-char itself
                escaped = True
                continue

            if char == start_char:
                # start a new function definition (not escaped as $$)

                if curr_func:
                    # we are starting a nested funcdef
                    return_str = True
                    if len(callstack) > _MAX_NESTING:
                        # stack full - ignore this function
                        if raise_errors:
                            raise ParsingError("Only allows for parsing nesting function defs "
                                               f"to a max depth of {_MAX_NESTING}.")
                        infuncstr += char
                        continue
                    else:
                        # store state for the current func and stack it
                        curr_func.current_kwarg = current_kwarg
                        curr_func.infuncstr = infuncstr
                        curr_func.single_quoted = single_quoted
                        curr_func.double_quoted = double_quoted
                        curr_func.open_lparens = open_lparens
                        curr_func.open_lsquare = open_lsquare
                        curr_func.open_lcurly = open_lcurly
                        current_kwarg = ""
                        infuncstr = ""
                        single_quoted = False
                        double_quoted = False
                        open_lparens = 0
                        open_lsquare = 0
                        open_lcurly = 0
                        exec_return = ""
                        callstack.append(curr_func)

                # start a new func
                curr_func = ParsedFunc(prefix=char, fullstr=char)
                continue

            if not curr_func:
                # a normal piece of string
                fullstr += char
                # this must always be a string
                return_str = True
                continue

            # in a function def (can be nested)

            if exec_return != '' and char not in (",=)"):
                # if exec_return is followed by any other character
                # than one demarking an arg,kwarg or function-end
                # it must immediately merge as a string
                infuncstr += str(exec_return)
                exec_return = ''

            if char == "'":  # note that this is the same as "\'"
                # a single quote - flip status
                single_quoted = not single_quoted
                infuncstr += char
                continue

            if char == '"':  # note that this is the same as '\"'
                # a double quote = flip status
                double_quoted = not double_quoted
                infuncstr += char
                continue

            if double_quoted or single_quoted:
                # inside a string definition - this escapes everything else
                infuncstr += char
                continue

            # special characters detected inside function def
            if char == '(':
                if not curr_func.funcname:
                    # end of a funcdef name
                    curr_func.funcname = infuncstr
                    curr_func.fullstr += infuncstr + char
                    infuncstr = ''
                else:
                    # just a random left-parenthesis
                    infuncstr += char
                # track the open left-parenthesis
                open_lparens += 1
                continue

            if char in '[]':
                # a square bracket - start/end of a list?
                infuncstr += char
                open_lsquare += -1 if char == ']' else 1
                continue

            if char in '{}':
                # a curly bracket - start/end of dict/set?
                infuncstr += char
                open_lcurly += -1 if char == '}' else 1
                continue

            if char == '=':
                # beginning of a keyword argument
                if exec_return != '':
                    infuncstr = exec_return
                current_kwarg = infuncstr.strip()
                curr_func.kwargs[current_kwarg] = ""
                curr_func.fullstr += infuncstr + char
                infuncstr = ''
                continue

            if char in (',)'):
                # commas and right-parens may indicate arguments ending

                if open_lparens > 1:
                    # one open left-parens is ok (beginning of arglist), more
                    # indicate we are inside an unclosed, nested (, so
                    # we need to not count this as a new arg or end of funcdef.
                    infuncstr += char
                    open_lparens -= 1 if char == ')' else 0
                    continue

                if open_lcurly > 0 or open_lsquare > 0:
                    # also escape inside an open [... or {... structure
                    infuncstr += char
                    continue

                if exec_return != '':
                    # store the execution return as-received
                    if current_kwarg:
                        curr_func.kwargs[current_kwarg] = exec_return
                    else:
                        curr_func.args.append(exec_return)
                else:
                    # store a string instead
                    if current_kwarg:
                        curr_func.kwargs[current_kwarg] = infuncstr.strip()
                    elif infuncstr.strip():
                        # don't store the empty string
                        curr_func.args.append(infuncstr.strip())

                # note that at this point either exec_return or infuncstr will
                # be empty. We need to store the full string so we can print
                # it 'raw' in case this funcdef turns out to e.g. lack an
                # ending paranthesis
                curr_func.fullstr += str(exec_return) + infuncstr + char

                current_kwarg = ""
                exec_return = ''
                infuncstr = ''

                if char == ')':
                    # closing the function list - this means we have a
                    # ready function-def to run.
                    open_lparens = 0

                    if strip:
                        # remove function as if it returned empty
                        exec_return = ''
                    elif escape:
                        # get function and set it as escaped
                        exec_return = escape_char + curr_func.fullstr
                    else:
                        # execute the function - the result may be a string or
                        # something else
                        exec_return = self.execute(
                            curr_func, raise_errors=raise_errors, **reserved_kwargs)

                    if callstack:
                        # unnest the higher-level funcdef from stack
                        # and continue where we were
                        curr_func = callstack.pop()
                        current_kwarg = curr_func.current_kwarg
                        if curr_func.infuncstr:
                            # if we have an ongoing string, we must merge the
                            # exec into this as a part of that string
                            infuncstr = curr_func.infuncstr + str(exec_return)
                            exec_return = ''
                        curr_func.infuncstr = ''
                        single_quoted = curr_func.single_quoted
                        double_quoted = curr_func.double_quoted
                        open_lparens = curr_func.open_lparens
                        open_lsquare = curr_func.open_lsquare
                        open_lcurly = curr_func.open_lcurly
                    else:
                        # back to the top-level string - this means the
                        # exec_return should always be converted to a string.
                        curr_func = None
                        fullstr += str(exec_return)
                        if return_str:
                            exec_return = ''
                        infuncstr = ''
                continue

            infuncstr += char

        if curr_func:
            # if there is a still open funcdef or defs remaining in callstack,
            # these are malformed (no closing bracket) and we should get their
            # strings as-is.
            callstack.append(curr_func)
            for _ in range(len(callstack)):
                infuncstr = str(callstack.pop()) + infuncstr

        if not return_str and exec_return != '':
            # return explicit return
            return exec_return

        # add the last bit to the finished string
        fullstr += infuncstr

        return fullstr

    def parse_to_any(self, string, raise_errors=False, **reserved_kwargs):
        """
        This parses a string and if the string only contains a "$func(...)",
        the return will be the return value of that function, even if it's not
        a string. If mixed in with other strings, the result will still always
        be a string.

        Args:
            string (str): The string to parse.
            raise_errors (bool, optional): If unset, leave a failing (or
                unrecognized) inline function as unparsed in the string. If set,
                raise an ParsingError.
            **reserved_kwargs: If given, these are guaranteed to _always_ pass
                as part of each parsed callable's **kwargs. These  override
                same-named default options given in `__init__` as well as any
                same-named kwarg given in the string function. This is because
                it is often used by Evennia to pass necessary kwargs into each
                callable (like the current Session object for inlinefuncs).

        Returns:
            any: The return from the callable. Or string if the callable is not
                given alone in the string.

        Raises:
            ParsingError: If a problem is encountered and `raise_errors` is True.

        Notes:
            This is a convenience wrapper for `self.parse(..., return_str=False)` which
            accomplishes the same thing.

        Examples:
            ::

                from ast import literal_eval
                from evennia.utils.funcparser import FuncParser


                def ret1(*args, **kwargs):
                    return 1

                parser = FuncParser({"lit": lit})

                assert parser.parse_to_any("$ret1()" == 1
                assert parser.parse_to_any("$ret1() and text" == '1 and text'

        """
        return self.parse(string, raise_errors=False, escape=False, strip=False,
                          return_str=False, **reserved_kwargs)


#
# Default funcparser callables. These are made available from this module's
# FUNCPARSER_CALLABLES.
#

def funcparser_callable_eval(*args, **kwargs):
    """
    Funcparser callable. This will combine safe evaluations to try to parse the
    incoming string into a python object. If it fails, the return will be same
    as the input.

    Args
        string (str): The string to parse. Only simple literals or operators are allowed.

    Returns:
        any: The string parsed into its Python form, or the same as input.

    Example:
        `$py(1)`
        `$py([1,2,3,4])`
        `$py(3 + 4)`

    """
    if not args:
        return ''
    inp = args[0]
    if not isinstance(inp, str):
        # already converted
        return inp
    try:
        return literal_eval(inp)
    except Exception:
        try:
            return simple_eval(inp)
        except Exception:
            return inp


def funcparser_callable_toint(*args, **kwargs):
    """Usage: toint(43.0) -> 43"""
    inp = funcparser_callable_eval(*args, **kwargs)
    try:
        return int(inp)
    except TypeError:
        return inp


def _apply_operation_two_elements(*args, operator="+", **kwargs):
    """
    Helper operating on two arguments

    Args:
        val1 (any): First value to operate on.
        val2 (any): Second value to operate on.

    Return:
        any: The result of val1 + val2. Values must be
            valid simple Python structures possible to add,
            such as numbers, lists etc. The $eval is usually
            better for non-list arithmetic.

    """
    if not len(args) > 1:
        return ''
    val1, val2 = args[0], args[1]
    # try to convert to python structures, otherwise, keep as strings
    if isinstance(val1, str):
        try:
            val1 = literal_eval(val1.strip())
        except Exception:
            pass
    if isinstance(val2, str):
        try:
            val2 = literal_eval(val2.strip())
        except Exception:
            pass
    if operator == "+":
        return val1 + val2
    elif operator == "-":
        return val1 - val2
    elif operator == "*":
        return val1 * val2
    elif operator == "/":
        return val1 / val2


def funcparser_callable_add(*args, **kwargs):
    """Usage: $add(val1, val2) -> val1 + val2"""
    return _apply_operation_two_elements(*args, operator='+', **kwargs)


def funcparser_callable_sub(*args, **kwargs):
    """Usage: $sub(val1, val2) -> val1 - val2"""
    return _apply_operation_two_elements(*args, operator='-', **kwargs)


def funcparser_callable_mult(*args, **kwargs):
    """Usage: $mult(val1, val2) -> val1 * val2"""
    return _apply_operation_two_elements(*args, operator='*', **kwargs)


def funcparser_callable_div(*args, **kwargs):
    """Usage: $mult(val1, val2) -> val1 / val2"""
    return _apply_operation_two_elements(*args, operator='/', **kwargs)


def funcparser_callable_round(*args, **kwargs):
    """
    Funcparser callable. Rounds an incoming float to a
    certain number of significant digits.

    Args:
        inp (str or number): If a string, it will attempt
            to be converted to a number first.
        significant (int): The number of significant digits.  Default is None -
            this will turn the result into an int.

    Returns:
        any: The rounded value or inp if inp was not a number.

    Examples:
        - `$round(3.5434343, 3)` - gives 3.543
        - `$round($random(), 2)` - rounds random result, e.g 0.22

    """
    if not args:
        return ''
    inp, *significant = args
    significant = significant[0] if significant else '0'
    lit_inp = inp
    if isinstance(inp, str):
        try:
            lit_inp = literal_eval(inp)
        except Exception:
            return inp
    try:
        int(significant)
    except Exception:
        significant = 0
    try:
        round(lit_inp, significant)
    except Exception:
        return ''

def funcparser_callable_random(*args, **kwargs):
    """
    Funcparser callable. Returns a random number between 0 and 1, from 0 to a
    maximum value, or within a given range (inclusive).

    Args:
        minval (str, optional): Minimum value. If not given, assumed 0.
        maxval (str, optional): Maximum value.

    Notes:
        If either of the min/maxvalue has a '.' in it, a floating-point random
        value will be returned. Otherwise it will be an
        integer value in the given range.

    Examples:
        - `$random()` - random value [0 .. 1) (float).
        - `$random(5)` - random value [0..5] (int)
        - `$random(5.0)` - random value [0..5] (float)
        - `$random(5, 10)` - random value [5..10] (int)
        - `$random(5, 10.0)` - random value [5..10] (float)

    """
    nargs = len(args)
    if nargs == 1:
        # only maxval given
        minval, maxval = "0", args[0]
    elif nargs > 1:
        minval, maxval = args[:2]
    else:
        minval, maxval = ("0", "1")

    if "." in minval or "." in maxval:
        # float mode
        try:
            minval, maxval = float(minval), float(maxval)
        except ValueError:
            minval, maxval = 0, 1
        return minval + maxval * random.random()
    else:
        # int mode
        try:
            minval, maxval = int(minval), int(maxval)
        except ValueError:
            minval, maxval = 0, 1
        return random.randint(minval, maxval)

def funcparser_callable_randint(*args, **kwargs):
    """
    Usage: $randint(start, end):

    Legacy alias - alwas returns integers.

    """
    return int(funcparser_callable_random(*args, **kwargs))


def funcparser_callable_choice(*args, **kwargs):
    """
    FuncParser callable. Picks a random choice from a list.

    Args:
        listing (list): A list of items to randomly choose between.
            This will be converted from a string to a real list.

    Returns:
        any: The randomly chosen element.

    Example:
        - `$choice([key, flower, house])`
        - `$choice([1, 2, 3, 4])`

    """
    if not args:
        return ''
    inp = args[0]
    if not isinstance(inp, str):
        inp = literal_eval(inp)
    return random.choice(inp)


def funcparser_callable_pad(*args, **kwargs):
    """
    FuncParser callable. Pads text to given width, optionally with fill-characters

    Args:
        text (str): Text to pad.
        width (int): Width of padding.
        align (str, optional): Alignment of padding; one of 'c', 'l' or 'r'.
        fillchar (str, optional): Character used for padding. Defaults to a space.

    Example:
        - `$pad(text, 12, l, ' ')`
        - `$pad(text, width=12, align=c, fillchar=-)`

    """
    if not args:
        return ''
    text, *rest = args
    nrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if nrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except TypeError:
        width = _CLIENT_DEFAULT_WIDTH

    align = kwargs.get("align", rest[1] if nrest > 1 else 'c')
    fillchar = kwargs.get("fillchar", rest[2] if nrest > 2 else ' ')
    if align not in ('c', 'l', 'r'):
        align = 'c'
    return pad(str(text), width=width, align=align, fillchar=fillchar)


def funcparser_callable_space(*args, **kwarg):
    """
    Usage: $space(43)

    Insert a length of space.

    """
    if not args:
        return ''
    try:
        width = int(args[0])
    except TypeError:
        width = 1
    return " " * width


def funcparser_callable_crop(*args, **kwargs):
    """
    FuncParser callable. Crops ingoing text to given widths.

    Args:
        text (str, optional): Text to crop.
        width (str, optional): Will be converted to an integer. Width of
            crop in characters.
        suffix (str, optional): End string to mark the fact that a part
            of the string was cropped. Defaults to `[...]`.

    Example:
        `$crop(text, 78, [...])`
        `$crop(text, width=78, suffix='[...]')`

    """
    if not args:
        return ''
    text, *rest = args
    nrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if nrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except TypeError:
        width = _CLIENT_DEFAULT_WIDTH
    suffix = kwargs.get('suffix', rest[1] if nrest > 1 else "[...]")
    return crop(str(text), width=width, suffix=str(suffix))


def funcparser_callable_justify(*args, **kwargs):
    """
    Justify text across a width, default across screen width.

    Args:
        text (str): Text to justify.
        width (int, optional): Defaults to default screen width.
        align (str, optional): One of 'l', 'c', 'r' or 'f' for 'full'.
        indent (int, optional): Intendation of text block, if any.

    Returns:
        str: The justified text.

    Examples:
        - $just(text, width=40)
        - $just(text, align=r, indent=2)

    """
    if not args:
        return ''
    text, *rest = args
    lrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if lrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except TypeError:
        width = _CLIENT_DEFAULT_WIDTH
    align = str(kwargs.get("align", rest[1] if lrest > 1 else 'f'))
    try:
        indent = int(kwargs.get("indent", rest[2] if lrest > 2 else 0))
    except TypeError:
        indent = 0
    return justify(str(text), width=width, align=align, indent=indent)


# legacy for backwards compatibility
def funcparser_callable_left_justify(*args, **kwargs):
    "Usage: $ljust(text)"
    return funcparser_callable_justify(*args, align='l', **kwargs)


def funcparser_callable_right_justify(*args, **kwargs):
    "Usage: $rjust(text)"
    return funcparser_callable_justify(*args, align='r', **kwargs)


def funcparser_callable_center_justify(*args, **kwargs):
    "Usage: $cjust(text)"
    return funcparser_callable_justify(*args, align='c', **kwargs)


def funcparser_callable_clr(*args, **kwargs):
    """
    FuncParser callable. Colorizes nested text.

    Args:
        startclr (str, optional): An ANSI color abbreviation without the
            prefix `|`, such as `r` (red foreground) or `[r` (red background).
        text (str, optional): Text
        endclr (str, optional): The color to use at the end of the string. Defaults
            to `|n` (reset-color).
    Kwargs:
        color (str, optional): If given,

    Example:
        - `$clr(r, text, n)`
        - `$clr(r, text)`
        - `$clr(text, start=r, end=n)`

    """
    if not args:
        return ''
    startclr, text, endclr = '', '', ''
    if len(args) > 1:
        # $clr(pre, text, post))
        startclr, *rest = args
        if rest:
            text, *endclr = rest
            if endclr:
                endclr = endclr[0]
    else:
        # $clr(text, start=pre, end=post)
        text = args[0]
        startclr = kwargs.get("start", '')
        endclr = kwargs.get("end", '')

    startclr = "|" + startclr if startclr else ""
    endclr = "|" + endclr if endclr else ("|n" if startclr else '')
    return f"{startclr}{text}{endclr}"


def funcparser_callable_search(*args, caller=None, access="control", **kwargs):
    """
    FuncParser callable. Finds an object based on name or #dbref. Note that
    this requries the parser be called with the caller's Session for proper
    security. If called without session, the call is aborted.

    Args:
        query (str): The key or dbref to search for.

    Kwargs:
        return_list (bool): If set, return a list of objects with
            0, 1 or more matches to `query`. Defaults to False.
        type (str): One of 'obj', 'account', 'script'
        caller (Entity): Supplied to Parser. This is required and will
            be passed into the access check for the entity being searched for.
            The 'control' permission is required.
        access (str): Which locktype access to check. Unset to disable the
            security check.

    Returns:
        any: An entity match or None if no match or a list if `return_list` is set.

    Raise:
        ParsingError: If zero/multimatch and `return_list` is False, or caller was not
            passed into parser.

    Examples:
        - "$search(#233)"
        - "$search(Tom, type=account)"
        - "$search(meadow, return_list=True)"

    """
    return_list = kwargs.get("return_list", "false").lower() == "true"

    if not args:
        return [] if return_list else None
    if not caller:
        raise ParsingError("$search requires a `caller` passed to the parser.")

    query = str(args[0])

    typ = kwargs.get("type", "obj")
    targets = []
    if typ == "obj":
        targets = search.search_object(query)
    elif typ == "account":
        targets = search.search_account(query)
    elif typ == "script":
        targets = search.search_script(query)

    if not targets:
        if return_list:
            return []
        raise ParsingError(f"$search: Query '{query}' gave no matches.")

    if len(targets) > 1 and not return_list:
        raise ParsingError("$search: Query '{query}' found {num} matches. "
                           "Set return_list=True to accept a list".format(
                               query=query, num=len(targets)))

    for target in targets:
        if not target.access(caller, target, access):
            raise ParsingError('$search Cannot add found entity - access failure.')

    return list(targets) if return_list else targets[0]


def funcparser_callable_search_list(*args, caller=None, access="control", **kwargs):
    """
    Usage: $objlist(#123)

    Legacy alias for search with a return_list=True kwarg preset.

    """
    return funcparser_callable_search(*args, caller=caller, access=access,
                                      return_list=True, **kwargs)


def funcparser_callable_you(*args, you=None, receiver=None, mapping=None, capitalize=False, **kwargs):
    """
    Usage: $you() or $you(key)

    Replaces with you for the caller of the string, with the display_name
    of the caller for others.

    Kwargs:
        you (Object): The 'you' in the string. This is used unless another
            you-key is passed to the callable in combination with `mapping`.
        receiver (Object): The recipient of the string.
        mapping (dict, optional): This is a mapping `{key:Object, ...}` and is
            used to find which object `$you(key)` refers to. If not given, the
            `you` kwarg is used.
        capitalize (bool): Passed by the You helper, to capitalize you.

    Returns:
        str: The parsed string.

    Raises:
        ParsingError: If `you` and `receiver` were not supplied.

    Notes:
        The kwargs should be passed the to parser directly.

    Examples:
        This can be used by the say or emote hooks to pass actor stance
        strings. This should usually be combined with the $inflect() callable.

        - `With a grin, $you() $conj(jump) at $you(tommy).`

        The You-object will see "With a grin, you jump at Tommy."
        Tommy will see "With a grin, CharName jumps at you."
        Others will see "With a grin, CharName jumps at Tommy."

    """
    if args and mapping:
        # this would mean a $you(key) form
        try:
            you = mapping.get(args[0])
        except KeyError:
            pass

    if not (you and receiver):
        raise ParsingError("No you-object or receiver supplied to $you callable.")

    capitalize = bool(capitalize)
    if you == receiver:
        return "You" if capitalize else "you"
    return you.get_display_name(looker=receiver) if hasattr(you, "get_display_name") else str(you)


def funcparser_callable_You(*args, you=None, receiver=None, mapping=None, capitalize=True, **kwargs):
    """
    Usage: $You() - capitalizes the 'you' output.

    """
    return funcparser_callable_you(
        *args, you=you, receiver=receiver, mapping=mapping, capitalize=capitalize, **kwargs)


def funcparser_callable_conjugate(*args, you=None, receiver=None, **kwargs):
    """
    $conj(verb)

    Conjugate a verb according to if it should be 2nd or third person.
    Kwargs:
        you_obj (Object): The object who represents 'you' in the string.
        you_target (Object): The recipient of the string.

    Returns:
        str: The parsed string.

    Raises:
        ParsingError: If `you` and `recipient` were not both supplied.

    Notes:
        Note that it will not capitalized.
        This assumes that the active party (You) is the one performing the verb.
        This automatic conjugation will fail if the active part is another person
        than 'you'.
        The you/receiver should be passed to the parser directly.

    Exampels:
        This is often used in combination with the $you/You( callables.

        - `With a grin, $you() $conj(jump)`

        You will see "With a grin, you jump."
        Others will see "With a grin, CharName jumps."

    """
    if not args:
        return ''
    if not (you and receiver):
        raise ParsingError("No youj/receiver supplied to $conj callable")

    second_person_str, third_person_str = verb_actor_stance_components(args[0])
    return second_person_str if you == receiver else third_person_str


# these are made available as callables by adding 'evennia.utils.funcparser' as
# a callable-path when initializing the FuncParser.

FUNCPARSER_CALLABLES = {
    # 'standard' callables

    # eval and arithmetic
    "eval": funcparser_callable_eval,
    "add": funcparser_callable_add,
    "sub": funcparser_callable_sub,
    "mult": funcparser_callable_mult,
    "div": funcparser_callable_div,
    "round": funcparser_callable_round,
    "toint": funcparser_callable_toint,

    # randomizers
    "random": funcparser_callable_random,
    "randint": funcparser_callable_randint,
    "choice": funcparser_callable_choice,

    # string manip
    "pad": funcparser_callable_pad,
    "crop": funcparser_callable_crop,
    "just": funcparser_callable_justify,
    "ljust": funcparser_callable_left_justify,
    "rjust": funcparser_callable_right_justify,
    "cjust": funcparser_callable_center_justify,
    "justify": funcparser_callable_justify,  # aliases for backwards compat
    "justify_left": funcparser_callable_left_justify,
    "justify_right": funcparser_callable_right_justify,
    "justify_center": funcparser_callable_center_justify,
    "space": funcparser_callable_space,
    "clr": funcparser_callable_clr,
}

SEARCHING_CALLABLES = {
    # requires `caller` and optionally `access` to be passed into parser
    "search": funcparser_callable_search,
    "obj": funcparser_callable_search,  # aliases for backwards compat
    "objlist": funcparser_callable_search_list,
    "dbref": funcparser_callable_search,
}

ACTOR_STANCE_CALLABLES = {
    # requires `you`, `receiver` and `mapping` to be passed into parser
    "you": funcparser_callable_you,
    "You": funcparser_callable_You,
    "conj": funcparser_callable_conjugate,
}
