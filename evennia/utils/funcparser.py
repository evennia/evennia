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

    # state storage
    fullstr: str = ""
    infuncstr: str = ""
    single_quoted: bool = False
    double_quoted: bool = False
    current_kwarg: str = ""

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
                 safe_callables,
                 start_char=_START_CHAR,
                 escape_char=_ESCAPE_CHAR,
                 max_nesting=_MAX_NESTING,
                 **default_kwargs):
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
            **default_kwargs: These kwargs will be passed into all callables. These
                kwargs can be overridden both by kwargs passed direcetly to `.parse` _and_
                by kwargs given directly in the string `$funcname` call. They are
                suitable for global defaults that is intended to be changed by the
                user. To _guarantee_ a call always gets a particular kwarg, pass it
                into `.parse` as `**reserved_kwargs` instead.

        """
        if isinstance(safe_callables, dict):
            callables = {**safe_callables}
        else:
            # load all modules/paths in sequence. Later-added will override
            # earlier same-named callables (allows for overriding evennia defaults)
            callables = {}
            for safe_callable in make_iter(safe_callables):
                # callables_from_module handles both paths and module instances
                callables.update(callables_from_module(safe_callable))
        self.validate_callables(callables)
        self.callables = callables
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
            mapping = inspect.getfullargspec(clble)
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
            return str(func(*args, **kwargs))
        except Exception:
            logger.log_trace()
            if raise_errors:
                raise
            return str(parsedfunc)

    def parse(self, string, raise_errors=False, **reserved_kwargs):
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
            **reserved_kwargs: If given, these are guaranteed to _always_ pass
                as part of each parsed callable's **kwargs. These  override
                same-named default options given in `__init__` as well as any
                same-named kwarg given in the string function. This is because
                it is often used by Evennia to pass necessary kwargs into each
                callable (like the current Session object for inlinefuncs).

        Returns:
            str: The parsed string, or the same string on error (if `raise_errors` is `False`)

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
        open_lparens = 0
        escaped = False
        current_kwarg = ""

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
                        curr_func.open_lparens = open_lparens
                        curr_func.single_quoted = single_quoted
                        curr_func.double_quoted = double_quoted
                        current_kwarg = ""
                        infuncstr = ""
                        open_lparens = 0
                        single_quoted = False
                        double_quoted = False
                        callstack.append(curr_func)

                # start a new func
                curr_func = ParsedFunc(prefix=char, fullstr=char)
                continue

            if not curr_func:
                # a normal piece of string
                fullstr += char
                continue

            # in a function def (can be nested)

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
                # inside a string escape
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

            if char == '=':
                # beginning of a keyword argument
                current_kwarg = infuncstr.strip()
                curr_func.kwargs[current_kwarg] = ""
                curr_func.fullstr += infuncstr + char
                infuncstr = ''
                continue

            if char in (',', ')'):
                # commas and right-parens may indicate arguments ending

                if open_lparens > 1:
                    # inside an unclosed, nested ( - this is neither
                    # closing the function-def nor indicating a new arg
                    # at the funcdef level
                    infuncstr += char
                    open_lparens -= 1 if char == ')' else 0
                    continue

                # end current arg/kwarg one way or another
                if current_kwarg:
                    curr_func.kwargs[current_kwarg] = infuncstr.strip()
                    current_kwarg = ""
                elif infuncstr.strip():
                    curr_func.args.append(infuncstr.strip())

                # we need to store the full string so we can print it 'raw' in
                # case this funcdef turns out to e.g. lack an ending paranthesis
                curr_func.fullstr += infuncstr + char
                infuncstr = ''

                if char == ')':
                    # closing the function list - this means we have a
                    # ready function-def to run.
                    open_lparens = 0
                    infuncstr = self.execute(
                        curr_func, raise_errors=raise_errors, **reserved_kwargs)

                    curr_func = None
                    if callstack:
                        # unnest the higher-level funcdef from stack
                        # and continue where we were
                        curr_func = callstack.pop()
                        current_kwarg = curr_func.current_kwarg
                        infuncstr = curr_func.infuncstr + infuncstr
                        curr_func.infuncstr = ''
                        open_lparens = curr_func.open_lparens
                        single_quoted = curr_func.single_quoted
                        double_quoted = curr_func.double_quoted
                    else:
                        # back to the top-level string
                        curr_func = None
                        fullstr += infuncstr
                        infuncstr = ''
                continue

            # no special char
            infuncstr += char

        if curr_func:
            # if there is a still open funcdef or defs remaining in callstack,
            # these are malformed (no closing bracket) and we should get their
            # strings as-is.
            callstack.append(curr_func)
            for _ in range(len(callstack)):
                infuncstr = str(callstack.pop()) + infuncstr

        # add the last bit to the finished string and return
        fullstr += infuncstr
        return fullstr
