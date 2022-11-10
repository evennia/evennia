"""
Generic function parser for functions embedded in a string, on the form
`$funcname(*args, **kwargs)`, for example:

```
"A string $foo() with $bar(a, b, c, $moo(), d=23) etc."
```

Each arg/kwarg can also be another nested function. These will be executed
inside-out and their return will used as arguments for the enclosing function
(so the same as for regular Python function execution).

This is the base for all forms of embedded func-parsing, like inlinefuncs and
protfuncs. Each function available to use must be registered as a 'safe'
function for the parser to accept it. This is usually done in a module with
regular Python functions on the form:

```python
# in a module whose path is passed to the parser

def _helper(x):
    # use underscore to NOT make the function available as a callable

def funcname(*args, **kwargs):
    # this can be accessed as $funcname(*args, **kwargs)
    # it must always accept *args and **kwargs.
    ...
    return something
```

Usage:

```python
from evennia.utils.funcparser import FuncParser

parser = FuncParser("path.to.module_with_callables")
result = parser.parse("String with $funcname() in it")

```

The `FuncParser` also accepts a direct dict mapping of `{'name': callable, ...}`.

---

"""
import dataclasses
import inspect
import random

from django.conf import settings

from evennia.utils import logger, search
from evennia.utils.utils import (
    callables_from_module,
    crop,
    int2str,
    justify,
    make_iter,
    pad,
    safe_convert_to_types,
    variable_from_module,
)
from evennia.utils.verb_conjugation.conjugate import verb_actor_stance_components
from evennia.utils.verb_conjugation.pronouns import pronoun_to_viewpoints

# setup

_CLIENT_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH
_MAX_NESTING = settings.FUNCPARSER_MAX_NESTING
_START_CHAR = settings.FUNCPARSER_START_CHAR
_ESCAPE_CHAR = settings.FUNCPARSER_ESCAPE_CHAR


@dataclasses.dataclass
class _ParsedFunc:
    """
    Represents a function parsed from the string

    """

    prefix: str = _START_CHAR
    funcname: str = ""
    args: list = dataclasses.field(default_factory=list)
    kwargs: dict = dataclasses.field(default_factory=dict)

    # state storage
    fullstr: str = ""
    infuncstr: str = ""
    rawstr: str = ""
    double_quoted: int = -1
    current_kwarg: str = ""
    open_lparens: int = 0
    open_lsquate: int = 0
    open_lcurly: int = 0
    exec_return = ""

    def get(self):
        return self.funcname, self.args, self.kwargs

    def __str__(self):
        return self.prefix + self.rawstr + self.infuncstr


class ParsingError(RuntimeError):
    """
    Failed to parse for some reason.
    """

    pass


class FuncParser:
    """
    Sets up a parser for strings containing `$funcname(*args, **kwargs)`
    substrings.

    """

    def __init__(
        self,
        callables,
        start_char=_START_CHAR,
        escape_char=_ESCAPE_CHAR,
        max_nesting=_MAX_NESTING,
        **default_kwargs,
    ):
        """
        Initialize the parser.

        Args:
            callables (str, module, list or dict): Where to find
                'safe' functions to make available in the parser. If a `dict`,
                it should be a direct mapping `{"funcname": callable, ...}`. If
                one or mode modules or module-paths, the module(s) are first checked
                for a dict `FUNCPARSER_CALLABLES = {"funcname", callable, ...}`. If
                no such variable exists, all callables in the module (whose name does
                not start with an underscore) will be made available to the parser.
            start_char (str, optional): A character used to identify the beginning
                of a parseable function. Default is `$`.
            escape_char (str, optional): Prepend characters with this to have
                them not count as a function. Default is the backtick, `\\\\`.
            max_nesting (int, optional): How many levels of nested function calls
                are allowed, to avoid exploitation. Default is 20.
            **default_kwargs: These kwargs will be passed into all callables. These
                kwargs can be overridden both by kwargs passed direcetly to `.parse` *and*
                by kwargs given directly in the string `$funcname` call. They are
                suitable for global defaults that is intended to be changed by the
                user. To guarantee a call always gets a particular kwarg, pass it
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
                    module_or_path, variable="FUNCPARSER_CALLABLES"
                )
                if callables_mapping:
                    try:
                        # mapping supplied in variable
                        loaded_callables.update(callables_mapping)
                    except ValueError:
                        raise ParsingError(
                            f"Failure to parse - {module_or_path}.FUNCPARSER_CALLABLES "
                            "(must be a dict {'funcname': callable, ...})"
                        )
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
            parsedfunc (_ParsedFunc): This dataclass holds the parsed details
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
                raise ParsingError(
                    f"Unknown parsed function '{str(parsedfunc)}' (available: {available})"
                )
            return str(parsedfunc)

        # build kwargs in the proper priority order
        kwargs = {
            **self.default_kwargs,
            **kwargs,
            **reserved_kwargs,
            **{"funcparser": self, "raise_errors": raise_errors},
        }

        try:
            ret = func(*args, **kwargs)
            return ret
        except ParsingError:
            if raise_errors:
                raise
            return str(parsedfunc)
        except Exception:
            logger.log_trace()
            if raise_errors:
                raise
            return str(parsedfunc)

    def parse(
        self,
        string,
        raise_errors=False,
        escape=False,
        strip=False,
        return_str=True,
        **reserved_kwargs,
    ):
        """
        Use parser to parse a string that may or may not have
        `$funcname(*args, **kwargs)` - style tokens in it. Only the callables
        used to initiate the parser will be eligible for parsing.

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

        double_quoted = -1
        open_lparens = 0  # open (
        open_lsquare = 0  # open [
        open_lcurly = 0  # open {
        escaped = False
        current_kwarg = ""
        exec_return = ""

        curr_func = None
        fullstr = ""  # final string
        infuncstr = ""  # string parts inside the current level of $funcdef (including $)
        literal_infuncstr = False

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
                    if len(callstack) >= _MAX_NESTING - 1:
                        # stack full - ignore this function
                        if raise_errors:
                            raise ParsingError(
                                "Only allows for parsing nesting function defs "
                                f"to a max depth of {_MAX_NESTING}."
                            )
                        infuncstr += char
                        continue
                    else:
                        # store state for the current func and stack it
                        curr_func.current_kwarg = current_kwarg
                        curr_func.infuncstr = infuncstr
                        curr_func.double_quoted = double_quoted
                        curr_func.open_lparens = open_lparens
                        curr_func.open_lsquare = open_lsquare
                        curr_func.open_lcurly = open_lcurly
                        # we must strip the remaining funcstr so it's not counted twice
                        curr_func.rawstr = curr_func.rawstr[: -len(infuncstr)]
                        current_kwarg = ""
                        infuncstr = ""
                        double_quoted = -1
                        open_lparens = 0
                        open_lsquare = 0
                        open_lcurly = 0
                        exec_return = ""
                        literal_infuncstr = False
                        callstack.append(curr_func)

                # start a new func
                curr_func = _ParsedFunc(prefix=char, fullstr=char)
                continue

            if not curr_func:
                # a normal piece of string
                fullstr += char
                # this must always be a string
                return_str = True
                continue

            # in a function def (can be nested)

            curr_func.rawstr += char

            if exec_return != "" and char not in (",=)"):
                # if exec_return is followed by any other character
                # than one demarking an arg,kwarg or function-end
                # it must immediately merge as a string
                infuncstr += str(exec_return)
                exec_return = ""

            if char == '"':  # note that this is the same as '\"'
                # a double quote = flip status
                if double_quoted == 0:
                    infuncstr = infuncstr[1:]
                    double_quoted = -1
                elif double_quoted > 0:
                    prefix = infuncstr[0:double_quoted]
                    infuncstr = prefix + infuncstr[double_quoted + 1 :]
                    double_quoted = -1
                else:
                    infuncstr += char
                    infuncstr = infuncstr.strip()
                    double_quoted = len(infuncstr) - 1
                    literal_infuncstr = True

                continue

            if double_quoted >= 0:
                # inside a string definition - this escapes everything else
                infuncstr += char
                continue

            # special characters detected inside function def
            if char == "(":
                if not curr_func.funcname:
                    # end of a funcdef name
                    curr_func.funcname = infuncstr
                    curr_func.fullstr += infuncstr + char
                    infuncstr = ""
                else:
                    # just a random left-parenthesis
                    infuncstr += char
                # track the open left-parenthesis
                open_lparens += 1
                continue

            if char in "[]":
                # a square bracket - start/end of a list?
                infuncstr += char
                open_lsquare += -1 if char == "]" else 1
                continue

            if char in "{}":
                # a curly bracket - start/end of dict/set?
                infuncstr += char
                open_lcurly += -1 if char == "}" else 1
                continue

            if char == "=":
                # beginning of a keyword argument
                if exec_return != "":
                    infuncstr = exec_return
                current_kwarg = infuncstr.strip()
                curr_func.kwargs[current_kwarg] = ""
                curr_func.fullstr += infuncstr + char
                infuncstr = ""
                continue

            if char in (",)"):
                # commas and right-parens may indicate arguments ending

                if open_lparens > 1:
                    # one open left-parens is ok (beginning of arglist), more
                    # indicate we are inside an unclosed, nested (, so
                    # we need to not count this as a new arg or end of funcdef.
                    infuncstr += char
                    open_lparens -= 1 if char == ")" else 0
                    continue

                if open_lcurly > 0 or open_lsquare > 0:
                    # also escape inside an open [... or {... structure
                    infuncstr += char
                    continue

                if exec_return != "":
                    # store the execution return as-received
                    if current_kwarg:
                        curr_func.kwargs[current_kwarg] = exec_return
                    else:
                        curr_func.args.append(exec_return)
                else:
                    if not literal_infuncstr:
                        infuncstr = infuncstr.strip()

                    # store a string instead
                    if current_kwarg:
                        curr_func.kwargs[current_kwarg] = infuncstr
                    elif literal_infuncstr or infuncstr.strip():
                        # don't store the empty string
                        curr_func.args.append(infuncstr)

                # note that at this point either exec_return or infuncstr will
                # be empty. We need to store the full string so we can print
                # it 'raw' in case this funcdef turns out to e.g. lack an
                # ending paranthesis
                curr_func.fullstr += str(exec_return) + infuncstr + char

                current_kwarg = ""
                exec_return = ""
                infuncstr = ""
                literal_infuncstr = False

                if char == ")":
                    # closing the function list - this means we have a
                    # ready function-def to run.
                    open_lparens = 0

                    if strip:
                        # remove function as if it returned empty
                        exec_return = ""
                    elif escape:
                        # get function and set it as escaped
                        exec_return = escape_char + curr_func.fullstr
                    else:
                        # execute the function - the result may be a string or
                        # something else
                        exec_return = self.execute(
                            curr_func, raise_errors=raise_errors, **reserved_kwargs
                        )

                    if callstack:
                        # unnest the higher-level funcdef from stack
                        # and continue where we were
                        curr_func = callstack.pop()
                        current_kwarg = curr_func.current_kwarg
                        if curr_func.infuncstr:
                            # if we have an ongoing string, we must merge the
                            # exec into this as a part of that string
                            infuncstr = curr_func.infuncstr + str(exec_return)
                            exec_return = ""
                        curr_func.infuncstr = ""
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
                            exec_return = ""
                        infuncstr = ""
                        literal_infuncstr = False
                continue

            infuncstr += char

        if curr_func:
            # if there is a still open funcdef or defs remaining in callstack,
            # these are malformed (no closing bracket) and we should get their
            # strings as-is.
            callstack.append(curr_func)
            for inum, _ in enumerate(range(len(callstack))):
                funcstr = str(callstack.pop())
                if inum == 0 and funcstr.endswith(infuncstr):
                    # avoid double-echo of nested function calls. This should
                    # produce a good result most of the time, but it's not 100%
                    # guaranteed to, since it can ignore genuine duplicates
                    infuncstr = funcstr
                else:
                    infuncstr = funcstr + infuncstr

        if not return_str and exec_return != "":
            # return explicit return
            return exec_return

        # add the last bit to the finished string
        fullstr += infuncstr

        return fullstr

    def parse_to_any(
        self, string, raise_errors=False, escape=False, strip=False, **reserved_kwargs
    ):
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
            escape (bool, optional): If set, escape all found functions so they
                are not executed by later parsing.
            strip (bool, optional): If set, strip any inline funcs from string
                as if they were not there.
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
        return self.parse(
            string,
            raise_errors=raise_errors,
            escape=escape,
            strip=strip,
            return_str=False,
            **reserved_kwargs,
        )


#
# Default funcparser callables. These are made available from this module's
# FUNCPARSER_CALLABLES.
#


def funcparser_callable_eval(*args, **kwargs):
    """
    Funcparser callable. This will combine safe evaluations to try to parse the
    incoming string into a python object. If it fails, the return will be same
    as the input.

    Args:
        string (str): The string to parse. Only simple literals or operators are allowed.

    Returns:
        any: The string parsed into its Python form, or the same as input.

    Examples:
        - `$py(1) -> 1`
        - `$py([1,2,3,4] -> [1, 2, 3]`
        - `$py(3 + 4) -> 7`

    """
    args, kwargs = safe_convert_to_types(("py", {}), *args, **kwargs)
    return args[0] if args else ""


def funcparser_callable_toint(*args, **kwargs):
    """Usage: $toint(43.0) -> 43"""
    inp = funcparser_callable_eval(*args, **kwargs)
    try:
        return int(inp)
    except TypeError:
        return inp
    except ValueError:
        return inp


def funcparser_callable_int2str(*args, **kwargs):
    """
    Usage: $int2str(1) -> 'one' etc, up to 12->twelve.

    Args:
        number (int): The number. If not an int, will be converted.

    Uses the int2str utility function.
    """
    if not args:
        return ""
    try:
        number = int(args[0])
    except ValueError:
        return args[0]
    return int2str(number)


def funcparser_callable_an(*args, **kwargs):
    """
    Usage: $an(thing) -> a thing

    Adds a/an depending on if the first letter of the given word is a consonant or not.

    """
    if not args:
        return ""
    item = str(args[0])
    if item and item[0] in "aeiouy":
        return f"an {item}"
    return f"a {item}"


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
    args, kwargs = safe_convert_to_types((("py", "py"), {}), *args, **kwargs)
    if not len(args) > 1:
        return ""
    val1, val2 = args[0], args[1]
    try:
        if operator == "+":
            return val1 + val2
        elif operator == "-":
            return val1 - val2
        elif operator == "*":
            return val1 * val2
        elif operator == "/":
            return val1 / val2
    except Exception:
        if kwargs.get("raise_errors"):
            raise
        return ""


def funcparser_callable_add(*args, **kwargs):
    """Usage: `$add(val1, val2) -> val1 + val2`"""
    return _apply_operation_two_elements(*args, operator="+", **kwargs)


def funcparser_callable_sub(*args, **kwargs):
    """Usage: ``$sub(val1, val2) -> val1 - val2`"""
    return _apply_operation_two_elements(*args, operator="-", **kwargs)


def funcparser_callable_mult(*args, **kwargs):
    """Usage: `$mult(val1, val2) -> val1 * val2`"""
    return _apply_operation_two_elements(*args, operator="*", **kwargs)


def funcparser_callable_div(*args, **kwargs):
    """Usage: `$mult(val1, val2) -> val1 / val2`"""
    return _apply_operation_two_elements(*args, operator="/", **kwargs)


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
        - `$round(3.5434343, 3) -> 3.543`
        - `$round($random(), 2)` - rounds random result, e.g `0.22`

    """
    if not args:
        return ""
    args, _ = safe_convert_to_types(((float, int), {}), *args, **kwargs)

    num, *significant = args
    significant = significant[0] if significant else 0
    try:
        return round(num, significant)
    except Exception:
        if kwargs.get("raise_errors"):
            raise
        return ""


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
    args, _ = safe_convert_to_types((("py", "py"), {}), *args, **kwargs)

    nargs = len(args)
    if nargs == 1:
        # only maxval given
        minval, maxval = 0, args[0]
    elif nargs > 1:
        minval, maxval = args[:2]
    else:
        minval, maxval = 0, 1

    try:
        if isinstance(minval, float) or isinstance(maxval, float):
            return minval + ((maxval - minval) * random.random())
        else:
            return random.randint(minval, maxval)
    except Exception:
        if kwargs.get("raise_errors"):
            raise
        return ""


def funcparser_callable_randint(*args, **kwargs):
    """
    Usage: $randint(start, end):

    Legacy alias - always returns integers.

    """
    return int(funcparser_callable_random(*args, **kwargs))


def funcparser_callable_choice(*args, **kwargs):
    """
    FuncParser callable. Picks a random choice from a list.

    Args:
        listing (list): A list of items to randomly choose between.
            This will be converted from a string to a real list.
        *args: If multiple args are given, will pick one randomly from them.

    Returns:
        any: The randomly chosen element.

    Example:
        - `$choice(key, flower, house)`
        - `$choice([1, 2, 3, 4])`

    """
    if not args:
        return ""

    nargs = len(args)
    if nargs == 1:
        # this needs to be a list/tuple for this to make sense
        args, _ = safe_convert_to_types(("py", {}), args[0], **kwargs)
        args = make_iter(args[0]) if args else None
    else:
        # separate arg per entry
        converters = ["py" for _ in range(nargs)]
        args, _ = safe_convert_to_types((converters, {}), *args, **kwargs)

    if not args:
        return ""
    try:
        return random.choice(args)
    except Exception:
        if kwargs.get("raise_errors"):
            raise
        return ""


def funcparser_callable_pad(*args, **kwargs):
    """
    FuncParser callable. Pads text to given width, optionally with fill-characters

    Args:
        text (str): Text to pad.
        width (int): Width of padding.
        align (str, optional): Alignment of padding; one of 'c', 'l' or 'r'.
        fillchar (str, optional): Character used for padding. Defaults to a space.

    Example:
        - `$pad(text, 12, r, ' ') -> "        text"`
        - `$pad(text, width=12, align=c, fillchar=-) -> "----text----"`

    """
    if not args:
        return ""
    args, kwargs = safe_convert_to_types(
        ((str, int, str, str), {"width": int, "align": str, "fillchar": str}), *args, **kwargs
    )

    text, *rest = args
    nrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if nrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except (TypeError, ValueError):
        width = _CLIENT_DEFAULT_WIDTH

    align = kwargs.get("align", rest[1] if nrest > 1 else "c")
    fillchar = kwargs.get("fillchar", rest[2] if nrest > 2 else " ")
    if align not in ("c", "l", "r"):
        align = "c"
    return pad(str(text), width=width, align=align, fillchar=fillchar)


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
        - `$crop(A long text, 10, [...]) -> "A lon[...]"`
        - `$crop(text, width=11, suffix='[...]) -> "A long[...]"`

    """
    if not args:
        return ""
    text, *rest = args
    nrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if nrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except (TypeError, ValueError):
        width = _CLIENT_DEFAULT_WIDTH
    suffix = kwargs.get("suffix", rest[1] if nrest > 1 else "[...]")
    return crop(str(text), width=width, suffix=str(suffix))


def funcparser_callable_space(*args, **kwarg):
    """
    Usage: $space(43)

    Insert a length of space.

    """
    if not args:
        return ""
    try:
        width = int(args[0])
    except ValueError:
        width = 1
    return " " * width


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
        - `$just(text, width=40)`
        - `$just(text, align=r, indent=2)`

    """
    if not args:
        return ""
    text, *rest = args
    lrest = len(rest)
    try:
        width = int(kwargs.get("width", rest[0] if lrest > 0 else _CLIENT_DEFAULT_WIDTH))
    except (TypeError, ValueError):
        width = _CLIENT_DEFAULT_WIDTH
    align = str(kwargs.get("align", rest[1] if lrest > 1 else "f"))
    try:
        indent = int(kwargs.get("indent", rest[2] if lrest > 2 else 0))
    except (TypeError, ValueError):
        indent = 0
    return justify(str(text), width=width, align=align, indent=indent)


# legacy for backwards compatibility
def funcparser_callable_left_justify(*args, **kwargs):
    "Usage: $ljust(text)"
    return funcparser_callable_justify(*args, align="l", **kwargs)


def funcparser_callable_right_justify(*args, **kwargs):
    "Usage: $rjust(text)"
    return funcparser_callable_justify(*args, align="r", **kwargs)


def funcparser_callable_center_justify(*args, **kwargs):
    "Usage: $cjust(text)"
    return funcparser_callable_justify(*args, align="c", **kwargs)


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
        - `$clr(r, text, n) -> "|rtext|n"`
        - `$clr(r, text) -> "|rtext|n`
        - `$clr(text, start=r, end=n) -> "|rtext|n"`

    """
    if not args:
        return ""

    startclr, text, endclr = "", "", ""
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
        startclr = kwargs.get("start", "")
        endclr = kwargs.get("end", "")

    startclr = "|" + startclr if startclr else ""
    endclr = "|" + endclr if endclr else ("|n" if startclr else "")
    return f"{startclr}{text}{endclr}"


def funcparser_callable_pluralize(*args, **kwargs):
    """
    FuncParser callable. Handles pluralization of a word.

    Args:
        singular_word (str): The base (singular) word to optionally pluralize
        number (int): The number of elements; if 1 (or 0), use `singular_word` as-is,
            otherwise use plural form.
        plural_word (str, optional): If given, this will be used if `number`
            is greater than one. If not given, we simply add 's' to the end of
            `singular_word`.

    Example:
        - `$pluralize(thing, 2)` -> "things"
        - `$pluralize(goose, 18, geese)` -> "geese"

    """
    if not args:
        return ""
    nargs = len(args)
    if nargs > 2:
        singular_word, number, plural_word = args[:3]
    elif nargs > 1:
        singular_word, number = args[:2]
        plural_word = f"{singular_word}s"
    else:
        singular_word, number = args[0], 1
    return singular_word if abs(int(number)) in (0, 1) else plural_word


def funcparser_callable_search(*args, caller=None, access="control", **kwargs):
    """
    FuncParser callable. Finds an object based on name or #dbref. Note that
    this requries the parser be called with the caller's Session for proper
    security. If called without session, the call is aborted.

    Args:
        query (str): The key or dbref to search for. This can consist of any args used
            for one of the regular search methods. Also kwargs will be passed into
            the search (except the kwargs given below)

    Keyword Args:
        return_list (bool): If set, return a list of objects with
            0, 1 or more matches to `query`. Defaults to False.
        type (str): One of 'obj', 'account', 'script'
        caller (Entity): Supplied to Parser. This is required and will
            be passed into the access check for the entity being searched for.
            The 'control' permission is required.
        access (str): Which locktype access to check. Unset to disable the
            security check.
        **kwargs: Will be passed into the main search.

    Returns:
        any: An entity match or None if no match or a list if `return_list` is set.

    Raise:
        ParsingError: If zero/multimatch and `return_list` is False, or caller was not
            passed into parser.

    Examples:
        - "$search(#233)"
        - "$search(Tom, type=account)"
        - "$search(meadow, return_list=True)"
        - "$search(beach, category=outdoors, type=tag)

    """
    # clean out funcparser-specific kwargs so we can use the kwargs for
    # searching
    search_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key not in ("funcparser", "raise_errors", "type", "return_list")
    }
    return_list = str(kwargs.pop("return_list", "false")).lower() == "true"

    if not args:
        return [] if return_list else None
    if not caller:
        raise ParsingError("$search requires a `caller` passed to the parser.")

    typ = kwargs.get("type", "obj")
    targets = []
    if typ == "obj":
        targets = search.search_object(*args, **search_kwargs)
    elif typ == "account":
        targets = search.search_account(*args, **search_kwargs)
    elif typ == "script":
        targets = search.search_script(*args, **search_kwargs)
    elif typ == "tag":
        targets = search.search_object_by_tag(*args, **search_kwargs)

    if not targets:
        if return_list:
            return []
        raise ParsingError(f"$search: Query '{args[0]}' gave no matches.")

    if len(targets) > 1 and not return_list:
        raise ParsingError(
            "$search: Query '{query}' found {num} matches. "
            "Set return_list=True to accept a list".format(query=query, num=len(targets))
        )

    for target in targets:
        if not target.access(caller, access):
            raise ParsingError("$search Cannot add found entity - access failure.")

    return list(targets) if return_list else targets[0]


def funcparser_callable_search_list(*args, caller=None, access="control", **kwargs):
    """
    Usage: $objlist(#123)

    Legacy alias for search with a return_list=True kwarg preset.

    """
    return funcparser_callable_search(
        *args, caller=caller, access=access, return_list=True, **kwargs
    )


def funcparser_callable_you(
    *args, caller=None, receiver=None, mapping=None, capitalize=False, **kwargs
):
    """
    Usage: $you() or $you(key)

    Replaces with you for the caller of the string, with the display_name
    of the caller for others.

    Keyword Args:
        caller (Object): The 'you' in the string. This is used unless another
            you-key is passed to the callable in combination with `mapping`.
        receiver (Object): The recipient of the string.
        mapping (dict, optional): This is a mapping `{key:Object, ...}` and is
            used to find which object `$you(key)` refers to. If not given, the
            `caller` kwarg is used.
        capitalize (bool): Passed by the You helper, to capitalize you.

    Returns:
        str: The parsed string.

    Raises:
        ParsingError: If `caller` and `receiver` were not supplied.

    Notes:
        The kwargs should be passed the to parser directly.

    Examples:
        This can be used by the say or emote hooks to pass actor stance
        strings. This should usually be combined with the $conj() callable.

        - `With a grin, $you() $conj(jump) at $you(tommy).`

        The caller-object will see "With a grin, you jump at Tommy."
        Tommy will see "With a grin, CharName jumps at you."
        Others will see "With a grin, CharName jumps at Tommy."

    """
    if args and mapping:
        # this would mean a $you(key) form
        try:
            caller = mapping.get(args[0])
        except KeyError:
            pass

    if not (caller and receiver):
        raise ParsingError("No caller or receiver supplied to $you callable.")

    capitalize = bool(capitalize)
    if caller == receiver:
        return "You" if capitalize else "you"
    return (
        caller.get_display_name(looker=receiver)
        if hasattr(caller, "get_display_name")
        else str(caller)
    )


def funcparser_callable_you_capitalize(
    *args, you=None, receiver=None, mapping=None, capitalize=True, **kwargs
):
    """
    Usage: $You() - capitalizes the 'you' output.

    """
    return funcparser_callable_you(
        *args, you=you, receiver=receiver, mapping=mapping, capitalize=capitalize, **kwargs
    )


def funcparser_callable_conjugate(*args, caller=None, receiver=None, **kwargs):
    """
    Usage: $conj(word, [options])

    Conjugate a verb according to if it should be 2nd or third person.

    Keyword Args:
        caller (Object): The object who represents 'you' in the string.
        receiver (Object): The recipient of the string.

    Returns:
        str: The parsed string.

    Raises:
        ParsingError: If `you` and `recipient` were not both supplied.

    Notes:
        Note that the verb will not be capitalized. It also
        assumes that the active party (You) is the one performing the verb.
        This automatic conjugation will fail if the active part is another person
        than 'you'. The caller/receiver must be passed to the parser directly.

    Examples:
        This is often used in combination with the $you/You( callables.

        - `With a grin, $you() $conj(jump)`

        You will see "With a grin, you jump."
        Others will see "With a grin, CharName jumps."

    """
    if not args:
        return ""
    if not (caller and receiver):
        raise ParsingError("No caller/receiver supplied to $conj callable")

    second_person_str, third_person_str = verb_actor_stance_components(args[0])
    return second_person_str if caller == receiver else third_person_str


def funcparser_callable_pronoun(*args, caller=None, receiver=None, capitalize=False, **kwargs):
    """

    Usage: $pron(word, [options])

    Adjust pronouns to the expected form. Pronouns are words you use instead of a
    proper name, such as 'him', 'herself', 'theirs' etc. These look different
    depending on who sees the outgoing string.

    The parser maps between this table ...

    ====================  =======  =======  ==========  ==========  ===========
    1st/2nd person        Subject  Object   Possessive  Possessive  Reflexive
                          Pronoun  Pronoun  Adjective   Pronoun     Pronoun
    ====================  =======  =======  ==========  ==========  ===========
    1st person               I        me        my        mine       myself
    1st person plural       we       us        our        ours       ourselves
    2nd person              you      you       your       yours      yourself
    2nd person plural       you      you       your       yours      yourselves
    ====================  =======  =======  ==========  ==========  ===========

    ... and this table (and vice versa).

    ====================  =======  =======  ==========  ==========  ===========
    3rd person            Subject  Object   Possessive  Possessive  Reflexive
                          Pronoun  Pronoun  Adjective   Pronoun     Pronoun
    ====================  =======  =======  ==========  ==========  ===========
    3rd person male         he       him       his        his        himself
    3rd person female       she      her       her        hers       herself
    3rd person neutral      it       it        its                   itself
    3rd person plural       they    them       their      theirs     themselves
    ====================  =======  =======  ==========  ==========  ===========

    This system will examine `caller` for either a property or a callable `.gender` to
    get a default gender fallback (if not specified in the call). If a callable,
    `.gender` will be called without arguments and should return a string
    `male`/`female`/`neutral`/`plural` (plural is considered a gender for this purpose).
    If no `gender` property/callable is found, `neutral` is used as a fallback.

    The pronoun-type default (if not specified in call) is `subject pronoun`.

    Args:
        pronoun (str): Input argument to parsed call. This can be any of the pronouns
            in the table above. If given in 1st/second form, they will be mappped to
            3rd-person form for others viewing the message (but will need extra input
            via the `gender`, see below). If given on 3rd person form, this will be
            mapped to 2nd person form for `caller` unless `viewpoint` is specified
            in options.
        options (str, optional): A space- or comma-separated string detailing `pronoun_type`,
            `gender`/`plural` and/or `viewpoint` to help the mapper differentiate between
            non-unique cases (such as if `you` should become `him` or `they`).
            Allowed values are:

            - `subject pronoun`/`subject`/`sp` (I, you, he, they)
            - `object pronoun`/`object/`/`op`  (me, you, him, them)
            - `possessive adjective`/`adjective`/`pa` (my, your, his, their)
            - `possessive pronoun`/`pronoun`/`pp`  (mine, yours, his, theirs)
            - `male`/`m`
            - `female`/`f`
            - `neutral`/`n`
            - `plural`/`p`
            - `1st person`/`1st`/`1`
            - `2nd person`/`2nd`/`2`
            - `3rd person`/`3rd`/`3`

    Keyword Args:

        caller (Object): The object creating the string. If this has a property 'gender',
            it will be checked for a string 'male/female/neutral' to determine
            the 3rd person gender (but if `pronoun_type` contains a gender
            component, that takes precedence). Provided automatically to the
            funcparser.
        receiver (Object): The recipient of the string. This being the same as
            `caller` or not helps determine 2nd vs 3rd-person forms. This is
            provided automatically by the funcparser.
        capitalize (bool): The input retains its capitalization. If this is set the output is
            always capitalized.

    Examples:

        ======================  =============    ===========
        Input                   caller sees      others see
        ======================  =============    ===========
        $pron(I, m)             I                he
        $pron(you,fo)           you              her
        $pron(yourself)         yourself         itself
        $pron(its)              your             its
        $pron(you,op,p)         you              them
        ======================  =============    ===========

    Notes:
        There is no option to specify reflexive pronouns since they are all unique
        and the mapping can always be auto-detected.

    """
    if not args:
        return ""

    pronoun, *options = args
    # options is either multiple args or a space-separated string
    if len(options) == 1:
        options = options[0]

    # default differentiators
    default_pronoun_type = "subject pronoun"
    default_gender = "neutral"
    default_viewpoint = "2nd person"

    if hasattr(caller, "gender"):
        if callable(caller.gender):
            default_gender = caller.gender()
        else:
            default_gender = caller.gender

    if "viewpoint" in kwargs:
        # passed into FuncParser initialization
        default_viewpoint = kwargs["viewpoint"]

    pronoun_1st_or_2nd_person, pronoun_3rd_person = pronoun_to_viewpoints(
        pronoun,
        options,
        pronoun_type=default_pronoun_type,
        gender=default_gender,
        viewpoint=default_viewpoint,
    )

    if capitalize:
        pronoun_1st_or_2nd_person = pronoun_1st_or_2nd_person.capitalize()
        pronoun_3rd_person = pronoun_3rd_person.capitalize()

    return pronoun_1st_or_2nd_person if caller == receiver else pronoun_3rd_person


def funcparser_callable_pronoun_capitalize(
    *args, caller=None, receiver=None, capitalize=True, **kwargs
):
    """
    Usage: $Pron(word, [options]) - always maps to a capitalized word.

    """
    return funcparser_callable_pronoun(
        *args, caller=caller, receiver=receiver, capitalize=capitalize, **kwargs
    )


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
    "pluralize": funcparser_callable_pluralize,
    "int2str": funcparser_callable_int2str,
    "an": funcparser_callable_an,
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
    "You": funcparser_callable_you_capitalize,
    "obj": funcparser_callable_you,
    "Obj": funcparser_callable_you_capitalize,
    "conj": funcparser_callable_conjugate,
    "pron": funcparser_callable_pronoun,
    "Pron": funcparser_callable_pronoun_capitalize,
}
