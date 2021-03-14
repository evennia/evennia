"""
Generic function parser for functions embedded in a string. The

```
$funcname(*args, **kwargs)
```

Each arg/kwarg can also be another nested function. These will be executed
from the deepest-nested first and used as arguments for the higher-level
function:

```
$funcname($func2(), $func3(arg1, arg2), foo=bar)
```

This is the base for all forms of embedded func-parsing, like inlinefuncs and
protfuncs. Each function available to use must be registered as a 'safe'
function for the parser to accept it. This is usually done in a module with
regular Python functions on the form:

```python
# in a module whose path is passed to the parser

def _helper(x):
    # prefix with underscore to not make this function available as a
    # parsable func

def funcname(*args, **kwargs):
    # this can be accecssed as $funcname(*args, **kwargs)
    ...
    return some_string

```

"""
import dataclasses
import inspect
import re
from evennia.utils import logger
from evennia.utils.utils import make_iter, callables_from_module

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

    def get(self):
        return self.funcname[len(self.prefix):], self.args, self.kwargs

    def __str__(self):
        argstr = ", ".join(str(arg) for arg in self.args)
        kwargstr = ", " + ", ".join(
            f"{key}={val}" for key, val in self.kwargs.items()) if self.kwargs else ""
        return f"{self.prefix}{self.funcname}({argstr}{kwargstr})"


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
                 safe_callables,
                 start_char=_START_CHAR,
                 escape_char=_ESCAPE_CHAR,
                 max_nesting=_MAX_NESTING,
                 **kwargs):
        """
        Initialize the parser.

        Args:
            safe_callables (str, module, list or dict): Where to find
                'safe' functions to make available in the parser. All callables
                in provided modules (whose names don't start with an
                underscore) are considered valid functions to access as
                `$funcname(*args, **kwags)` during parsing. If a `str`, this
                should be the path to such a module. A `list` can either be a
                list of paths or module objects. If a `dict`, this should be a
                mapping `{"funcname": callable, ...}` - this will be used
                directly as valid parseable functions.
            start_char (str, optional): A character used to identify the beginning
                of a parseable function. Default is `$`.
            escape_char (str, optional): Prepend characters with this to have
                them not count as a function. Default is `\\`.
            max_nesting (int, optional): How many levels of nested function calls
                are allowed, to avoid exploitation.
            **kwargs: If given - these kwargs will always be passed to _every_
                callable parsed and executed by this parser instance.

        """
        if isinstance(safe_callables, dict):
            callables = {**safe_callables}
        else:
            # load all modules/paths in sequence. Later-added will override earlier
            # same-named callables (allows for overriding evennia defaults)
            callables = {}
            for safe_callable in make_iter(safe_callables):
                # callables_from_module handles both paths and module instances
                callables.update(callables_from_module(safe_callable))
        self.validate_callables(callables)
        self.callables = callables
        self.escape_char = escape_char
        self.start_char = start_char
        self.default_kwargs = kwargs

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
            mapping = inspect.getfullargspec(clble)
            assert mapping.varargs, f"Parse-func callable '{funcname}' does not support *args."
            assert mapping.varkw, f"Parse-func callable '{funcname}' does not support **kwargs."

    def execute(self, parsedfunc, raise_errors=False):
        """
        Execute a parsed function

        Args:
            parsedfunc (ParsedFunc): This dataclass holds the parsed details
                of the function.
            raise_errors (bool, optional): Raise errors. Otherwise return the
                string with the function unparsed.

        Returns:
            any: The result of the execution. If this is a nested function, it
                can be anything, otherwise it will be converted to a string later.
                Always a string on un-raised error (the unparsed function string).

        Raises:
            ParsingError, any: A `ParsingError` if the function could not be found, otherwise
                error from function definition. Only raised if `raise_errors` is `True`

        """
        funcname, args, kwargs = parsedfunc.get()
        func = self.callables.get(funcname)

        if not func:
            if raise_errors:
                available = ", ".join(f"'{key}'" for key in self.callables)
                raise ParsingError(f"Unknown parsed function '{str(parsedfunc)}' "
                                   f"(available: {available})")
            return str(parsedfunc)

        try:
            return str(func(*args, **kwargs))
        except Exception:
            logger.log_trace()
            if raise_errors:
                raise
            return str(parsedfunc)

    def parse(self, string, raise_errors=False, **kwargs):
        """
        Use parser to parse a string that may or may not have `$funcname(*args, **kwargs)`
        - style tokens in it. Only the callables used to initiate the parser
          will be eligible for parsing, others will remain un-parsed.

        Args:
            string (str): The string to parse.
            raise_errors (bool, optional): By default, a failing parse just means not parsing the
                string but leaving it as-is. If this is `True`, errors (like not closing brackets)
                will lead to an ParsingError.
            **kwargs: If given, these are extra options to pass as `**kwargs` into each
                parsed callable. These will override any same-named kwargs given earlier
                to `FuncParser.__init__`.

        Returns:
            str: The parsed string, or the same string on error (if `raise_errors` is `False`)

        Raises:
            ParsingError: If a problem is encountered and `raise_errors` is True.

        """
        callables = self.callables
        # prepare kwargs to pass into callables
        callable_kwargs = {**self.default_kwargs}
        callable_kwargs.update(kwargs)

        start_char = self.start_char
        escape_char = self.escape_char

        # parsing state
        callstack = []

        single_quoted = False
        double_quoted = False
        escaped = False
        current_kwarg = None

        curr_func = None
        fullstr = ''
        workstr = ''

        #from evennia import set_trace;set_trace()

        for char in string:
            if escaped:
                # always store escaped characters verbatim
                workstr += char
                escaped = False
                continue
            if char == escape_char:
                # don't store the escape-char itself
                escaped = True
                continue
            if char == "'":
                # a single quote - flip status
                single_quoted = not single_quoted
                continue
            if char == '"':
                # a double quote = flip status
                double_quoted = not double_quoted
                continue

            if not (double_quoted or single_quoted):
                # not in a string escape
                if char == start_char:
                    # start a new function
                    if curr_func:
                        # nested func
                        if len(callstack) >= _MAX_NESTING:
                            # stack full - ignore this function
                            if raise_errors:
                                raise ParsingError("Only allows for parsing nesting function defs "
                                                   f"to a max depth of {_MAX_NESTING}.")
                            workstr += char
                            continue
                        else:
                            # store what we have and stack it
                            if current_kwarg:
                                curr_func.kwargs[current_kwarg] = workstr
                                current_kwarg = None
                            else:
                                curr_func.args.append(workstr)
                            workstr = ''
                            callstack.append(curr_func)
                    else:
                        # entering a funcdef, flush workstr
                        fullstr += workstr
                        workstr = char
                    # start a new func
                    curr_func = ParsedFunc(prefix=char)
                    continue

                if curr_func:
                    # currently parsing a func
                    if char == '(':
                        # end of a funcdef
                        curr_func.funcname = workstr
                        workstr = ''
                        continue
                    if char == '=':
                        # beginning of a keyword argument
                        current_kwarg = workstr
                        curr_func.kwargs[current_kwarg] = None
                        workstr = ''
                        continue
                    if char in (',', ')'):
                        # end current arg/kwarg one way or another
                        if current_kwarg:
                            curr_func.kwargs[current_kwarg] = workstr
                            current_kwarg = None
                        else:
                            curr_func.args.append(workstr)
                        workstr = ''

                        if char == ')':
                            # closing the function list - this means we have a
                            # ready function def to run.

                            workstr += self.execute(curr_func, raise_errors=raise_errors)

                            curr_func = None
                            if callstack:
                                # get a new func from stack, if any
                                curr_func = callstack.pop(0)
                            else:
                                fullstr += workstr
                                workstr = ''
                        continue

            workstr += char

        fullstr += workstr
        return fullstr


#def parse_arguments(s, **kwargs):
#    """
#    This method takes a string and parses it as if it were an argument list to a function.
#    It supports both positional and named arguments.
#
#    Values are automatically converted to int or float if possible.
#    Values surrounded by single or double quotes are treated as strings.
#    Any other value is wrapped in a "FunctionArgument" class for later processing.
#
#    Args:
#        s (str): The string to convert.
#
#    Returns:
#        (list, dict): A tuple containing a list of arguments (list) and named arguments (dict).
#    """
#    global _ARG_ESCAPE_SIGN
#
#    args_list = []
#    args_dict = {}
#
#    # State (general)
#    inside = (False, None)  # Are we inside a quoted string? What is the quoted character?
#    skip = False  # Skip the current parameter?
#    escape = False  # Was the escape key used?
#    is_string = False  # Have we been inside a quoted string?
#    temp = ""  # Buffer
#    key = None  # Key (for named parameter)
#
#    def _parse_value(temp):
#        ret = temp.strip()
#        if not is_string:
#            try:
#                ret = int(ret)
#            except ValueError:
#                try:
#                    ret = float(ret)
#                except ValueError:
#                    if ret != "":
#                        return FunctionArgument(ret)
#
#        return ret
#
#    def _add_value(skip, key, args_list, args_dict, temp):
#        if not skip:
#            # Record value based on whether named parameters mode is set or not.
#            if key is not None:
#                args_dict[key] = _parse_value(temp)
#                key = None
#            else:
#                args_list.append(_parse_value(temp))
#
#    for c in s:
#        if c == _ARG_ESCAPE_SIGN:
#            # Escape sign used.
#            if escape:
#                # Already escaping: print escape sign itself.
#                temp += _ARG_ESCAPE_SIGN
#                escape = False
#            else:
#                # Enter escape mode.
#                escape = True
#        elif escape:
#            # Escape mode: print whatever comes after the symbol.
#            escape = False
#            temp += c
#        elif inside[0] is True:
#            # Inside single quotes or double quotes
#            # Wait for the end symbol, allow everything else through, allow escape sign for typing quotes in strings
#            if c == inside[1]:
#                # Leaving single/double quoted area
#                inside = (False, None)
#            else:
#                temp += c
#        elif c == "\"" or c == "'":
#            # Entering single/double quoted area
#            inside = (True, c)
#            is_string = True
#            continue
#        elif c == "=":
#            if is_string:
#                # Invalid syntax because we don't allow named parameters to be quoted.
#                return None
#            elif key is None:
#                # Named parameters mode and equals sign encountered. Record key and continue with value.
#                key = temp.strip()
#                temp = ""
#        elif c == ",":
#            # Comma encountered outside of quoted area.
#
#            _add_value(skip, key, args_list, args_dict, temp)
#
#            # Reset
#            temp = ""
#            skip = False
#            is_string = False
#            key = None
#        else:
#            # Any other character: add to buffer.
#            temp += c
#
#    if inside[0] is True:
#        # Invalid syntax because we are inside a quoted area.
#        return None
#    else:
#        _add_value(skip, key, args_list, args_dict, temp)
#
#    return args_list, args_dict
