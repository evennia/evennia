"""
Inline functions (nested form).

This parser accepts nested inlinefunctions on the form

```python
$funcname(arg, arg, ...)
```

embedded in any text where any arg can be another ``$funcname()`` call.
This functionality is turned off by default - to activate,
`settings.INLINEFUNC_ENABLED` must be set to `True`.

Each token starts with `$funcname(` where there must be no space
between the `$funcname` and `"("`. The inlinefunc ends with a matched ending parentesis.
`")"`.

Inside the inlinefunc definition, one can use `\` to escape. This is
mainly needed for escaping commas in flowing text (which would
otherwise be interpreted as an argument separator), or to escape `)`
when not intended to close the function block. Enclosing text in
matched `\"\"\"` (triple quotes) or `'''` (triple single-quotes) will
also escape *everything* within without needing to escape individual
characters.

The available inlinefuncs are defined as global-level functions in
modules defined by `settings.INLINEFUNC_MODULES`. They are identified
by their function name (and ignored if this name starts with `_`). They
should be on the following form:

```python
def funcname (*args, **kwargs):
    # ...
```

Here, the arguments given to `$funcname(arg1,arg2)` will appear as the
`*args` tuple. This will be populated by the arguments given to the
inlinefunc in-game - the only part that will be available from
in-game. `**kwargs` are not supported from in-game but are only used
internally by Evennia to make details about the caller available to
the function. The kwarg passed to all functions is `session`, the
Sessionobject for the object seeing the string. This may be `None` if
the string is sent to a non-puppetable object. The inlinefunc should
never raise an exception.

There are two reserved function names:

- "nomatch": This is called if the user uses a functionname that is
  not registered. The nomatch function will get the name of the
  not-found function as its first argument followed by the normal
  arguments to the given function. If not defined the default effect is
  to print `<UNKNOWN>` to replace the unknown function.
- "stackfull": This is called when the maximum nested function stack is reached.
  When this happens, the original parsed string is returned and the result of
  the `stackfull` inlinefunc is appended to the end. By default this is an
  error message.

Syntax errors, notably failing to completely closing all inlinefunc
blocks, will lead to the entire string remaining unparsed. Inlineparsing should
never traceback.

----

"""

import re
import fnmatch
import random as base_random
from django.conf import settings

from evennia.utils import utils, logger

# The stack size is a security measure. Set to <=0 to disable.
_STACK_MAXSIZE = settings.INLINEFUNC_STACK_MAXSIZE


# example/testing inline functions


def random(*args, **kwargs):
    """
    Inlinefunc. Returns a random number between
    0 and 1, from 0 to a maximum value, or within a given range (inclusive).

    Args:
        minval (str, optional): Minimum value. If not given, assumed 0.
        maxval (str, optional): Maximum value.

    Keyword argumuents:
        session (Session): Session getting the string.

    Notes:
        If either of the min/maxvalue has a '.' in it, a floating-point random
        value will be returned. Otherwise it will be an integer value in the
        given range.

    Example:
        `$random()`
        `$random(5)`
        `$random(5, 10)`

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
        return "{:.2f}".format(minval + maxval * base_random.random())
    else:
        # int mode
        try:
            minval, maxval = int(minval), int(maxval)
        except ValueError:
            minval, maxval = 0, 1
        return str(base_random.randint(minval, maxval))


def pad(*args, **kwargs):
    """
    Inlinefunc. Pads text to given width.

    Args:
        text (str, optional): Text to pad.
        width (str, optional): Will be converted to integer. Width
            of padding.
        align (str, optional): Alignment of padding; one of 'c', 'l' or 'r'.
        fillchar (str, optional): Character used for padding. Defaults to a
            space.

    Keyword Args:
        session (Session): Session performing the pad.

    Example:
        `$pad(text, width, align, fillchar)`

    """
    text, width, align, fillchar = "", 78, "c", " "
    nargs = len(args)
    if nargs > 0:
        text = args[0]
    if nargs > 1:
        width = int(args[1]) if args[1].strip().isdigit() else 78
    if nargs > 2:
        align = args[2] if args[2] in ("c", "l", "r") else "c"
    if nargs > 3:
        fillchar = args[3]
    return utils.pad(text, width=width, align=align, fillchar=fillchar)


def crop(*args, **kwargs):
    """
    Inlinefunc. Crops ingoing text to given widths.

    Args:
        text (str, optional): Text to crop.
        width (str, optional): Will be converted to an integer. Width of
            crop in characters.
        suffix (str, optional): End string to mark the fact that a part
            of the string was cropped. Defaults to `[...]`.
    Keyword Args:
        session (Session): Session performing the crop.

    Example:
        `$crop(text, width=78, suffix='[...]')`

    """
    text, width, suffix = "", 78, "[...]"
    nargs = len(args)
    if nargs > 0:
        text = args[0]
    if nargs > 1:
        width = int(args[1]) if args[1].strip().isdigit() else 78
    if nargs > 2:
        suffix = args[2]
    return utils.crop(text, width=width, suffix=suffix)


def space(*args, **kwargs):
    """
    Inlinefunc. Inserts an arbitrary number of spaces. Defaults to 4 spaces.

    Args:
        spaces (int, optional): The number of spaces to insert.

    Keyword Args:
        session (Session): Session performing the crop.

    Example:
        `$space(20)`

    """
    width = 4
    if args:
        width = abs(int(args[0])) if args[0].strip().isdigit() else 4
    return " " * width


def clr(*args, **kwargs):
    """
    Inlinefunc. Colorizes nested text.

    Args:
        startclr (str, optional): An ANSI color abbreviation without the
            prefix `|`, such as `r` (red foreground) or `[r` (red background).
        text (str, optional): Text
        endclr (str, optional): The color to use at the end of the string. Defaults
            to `|n` (reset-color).
    Keyword Args:
        session (Session): Session object triggering inlinefunc.

    Example:
        `$clr(startclr, text, endclr)`

    """
    text = ""
    nargs = len(args)
    if nargs > 0:
        color = args[0].strip()
    if nargs > 1:
        text = args[1]
        text = "|" + color + text
    if nargs > 2:
        text += "|" + args[2].strip()
    else:
        text += "|n"
    return text


def null(*args, **kwargs):
    return args[0] if args else ""


def nomatch(name, *args, **kwargs):
    """
    Default implementation of nomatch returns the function as-is as a string.

    """
    kwargs.pop("inlinefunc_stack_depth", None)
    kwargs.pop("session")

    return "${name}({args}{kwargs})".format(
        name=name,
        args=",".join(args),
        kwargs=",".join("{}={}".format(key, val) for key, val in kwargs.items()),
    )


_INLINE_FUNCS = {}

# we specify a default nomatch function to use if no matching func was
# found. This will be overloaded by any nomatch function defined in
# the imported modules.
_DEFAULT_FUNCS = {
    "nomatch": lambda *args, **kwargs: "<UNKNOWN>",
    "stackfull": lambda *args, **kwargs: "\n (not parsed: ",
}

_INLINE_FUNCS.update(_DEFAULT_FUNCS)

# load custom inline func modules.
for module in utils.make_iter(settings.INLINEFUNC_MODULES):
    try:
        _INLINE_FUNCS.update(utils.callables_from_module(module))
    except ImportError as err:
        if module == "server.conf.inlinefuncs":
            # a temporary warning since the default module changed name
            raise ImportError(
                "Error: %s\nPossible reason: mygame/server/conf/inlinefunc.py should "
                "be renamed to mygame/server/conf/inlinefuncs.py (note "
                "the S at the end)." % err
            )
        else:
            raise


# regex definitions

_RE_STARTTOKEN = re.compile(r"(?<!\\)\$(\w+)\(")  # unescaped $funcname( (start of function call)

# note: this regex can be experimented with at https://regex101.com/r/kGR3vE/2
_RE_TOKEN = re.compile(
    r"""
      (?<!\\)\'\'\'(?P<singlequote>.*?)(?<!\\)\'\'\'|  # single-triplets escape all inside
      (?<!\\)\"\"\"(?P<doublequote>.*?)(?<!\\)\"\"\"|  # double-triplets escape all inside
      (?P<comma>(?<!\\)\,)|                            # , (argument sep)
      (?P<end>(?<!\\)\))|                              # ) (possible end of func call)
      (?P<leftparens>(?<!\\)\()|                       # ( (lone left-parens)
      (?P<start>(?<!\\)\$\w+\()|                       # $funcname (start of func call)
      (?P<escaped>                                     # escaped tokens to re-insert sans backslash
            \\\'|\\\"|\\\)|\\\$\w+\(|\\\()|
      (?P<rest>                                        # everything else to re-insert verbatim
            \$(?!\w+\()|\'|\"|\\|[^),$\'\"\\\(]+)""",
    re.UNICODE | re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

# Cache for function lookups.
_PARSING_CACHE = utils.LimitedSizeOrderedDict(size_limit=1000)


class ParseStack(list):
    """
    Custom stack that always concatenates strings together when the
    strings are added next to one another. Tuples are stored
    separately and None is used to mark that a string should be broken
    up into a new chunk. Below is the resulting stack after separately
    appending 3 strings, None, 2 strings, a tuple and finally 2
    strings:

    [string + string + string,
    None
    string + string,
    tuple,
    string + string]

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # always start stack with the empty string
        list.append(self, "")
        # indicates if the top of the stack is a string or not
        self._string_last = True

    def __eq__(self, other):
        return (
            super().__eq__(other)
            and hasattr(other, "_string_last")
            and self._string_last == other._string_last
        )

    def __ne__(self, other):
        return not self.__eq__(other)

    def append(self, item):
        """
        The stack will merge strings, add other things as normal
        """
        if isinstance(item, str):
            if self._string_last:
                self[-1] += item
            else:
                list.append(self, item)
                self._string_last = True
        else:
            # everything else is added as normal
            list.append(self, item)
            self._string_last = False


# class InlinefuncError(RuntimeError):
#     pass
#
#
# def parse_inlinefunc(string, strip=False, available_funcs=None, stacktrace=False, **kwargs):
#     """
#     Parse the incoming string.
#
#     Args:
#         string (str): The incoming string to parse.
#         strip (bool, optional): Whether to strip function calls rather than
#             execute them.
#         available_funcs (dict, optional): Define an alternative source of functions to parse for.
#             If unset, use the functions found through `settings.INLINEFUNC_MODULES`.
#         stacktrace (bool, optional): If set, print the stacktrace to log.
#     Keyword Args:
#         session (Session): This is sent to this function by Evennia when triggering
#             it. It is passed to the inlinefunc.
#         kwargs (any): All other kwargs are also passed on to the inlinefunc.
#
#
#     """
#     global _PARSING_CACHE
#     usecache = False
#     if not available_funcs:
#         available_funcs = _INLINE_FUNCS
#         usecache = True
#     else:
#         # make sure the default keys are available, but also allow overriding
#         tmp = _DEFAULT_FUNCS.copy()
#         tmp.update(available_funcs)
#         available_funcs = tmp
#
#     if usecache and string in _PARSING_CACHE:
#         # stack is already cached
#         stack = _PARSING_CACHE[string]
#     elif not _RE_STARTTOKEN.search(string):
#         # if there are no unescaped start tokens at all, return immediately.
#         return string
#     else:
#         # no cached stack; build a new stack and continue
#         stack = ParseStack()
#
#         # process string on stack
#         ncallable = 0
#         nlparens = 0
#         nvalid = 0
#
#         if stacktrace:
#             out = "STRING: {} =>".format(string)
#             print(out)
#             logger.log_info(out)
#
#         for match in _RE_TOKEN.finditer(string):
#             gdict = match.groupdict()
#
#             if stacktrace:
#                 out = " MATCH: {}".format({key: val for key, val in gdict.items() if val})
#                 print(out)
#                 logger.log_info(out)
#
#             if gdict["singlequote"]:
#                 stack.append(gdict["singlequote"])
#             elif gdict["doublequote"]:
#                 stack.append(gdict["doublequote"])
#             elif gdict["leftparens"]:
#                 # we have a left-parens inside a callable
#                 if ncallable:
#                     nlparens += 1
#                 stack.append("(")
#             elif gdict["end"]:
#                 if nlparens > 0:
#                     nlparens -= 1
#                     stack.append(")")
#                     continue
#                 if ncallable <= 0:
#                     stack.append(")")
#                     continue
#                 args = []
#                 while stack:
#                     operation = stack.pop()
#                     if callable(operation):
#                         if not strip:
#                             stack.append((operation, [arg for arg in reversed(args)]))
#                         ncallable -= 1
#                         break
#                     else:
#                         args.append(operation)
#             elif gdict["start"]:
#                 funcname = _RE_STARTTOKEN.match(gdict["start"]).group(1)
#                 try:
#                     # try to fetch the matching inlinefunc from storage
#                     stack.append(available_funcs[funcname])
#                     nvalid += 1
#                 except KeyError:
#                     stack.append(available_funcs["nomatch"])
#                     stack.append(funcname)
#                     stack.append(None)
#                 ncallable += 1
#             elif gdict["escaped"]:
#                 # escaped tokens
#                 token = gdict["escaped"].lstrip("\\")
#                 stack.append(token)
#             elif gdict["comma"]:
#                 if ncallable > 0:
#                     # commas outside strings and inside a callable are
#                     # used to mark argument separation - we use None
#                     # in the stack to indicate such a separation.
#                     stack.append(None)
#                 else:
#                     # no callable active - just a string
#                     stack.append(",")
#             else:
#                 # the rest
#                 stack.append(gdict["rest"])
#
#         if ncallable > 0:
#             # this means not all inlinefuncs were complete
#             return string
#
#         if _STACK_MAXSIZE > 0 and _STACK_MAXSIZE < nvalid:
#             # if stack is larger than limit, throw away parsing
#             return string + available_funcs["stackfull"](*args, **kwargs)
#         elif usecache:
#             # cache the stack - we do this also if we don't check the cache above
#             _PARSING_CACHE[string] = stack
#
#     # run the stack recursively
#     def _run_stack(item, depth=0):
#         retval = item
#         if isinstance(item, tuple):
#             if strip:
#                 return ""
#             else:
#                 func, arglist = item
#                 args = [""]
#                 for arg in arglist:
#                     if arg is None:
#                         # an argument-separating comma - start a new arg
#                         args.append("")
#                     else:
#                         # all other args should merge into one string
#                         args[-1] += _run_stack(arg, depth=depth + 1)
#                 # execute the inlinefunc at this point or strip it.
#                 kwargs["inlinefunc_stack_depth"] = depth
#                 retval = "" if strip else func(*args, **kwargs)
#         return utils.to_str(retval)
#
#     retval = "".join(_run_stack(item) for item in stack)
#     if stacktrace:
#         out = "STACK: \n{} => {}\n".format(stack, retval)
#         print(out)
#         logger.log_info(out)
#
#     # execute the stack
#     return retval
#
#
# def raw(string):
#     """
#     Escape all inlinefuncs in a string so they won't get parsed.
#
#     Args:
#         string (str): String with inlinefuncs to escape.
#     """
#
#     def _escape(match):
#         return "\\" + match.group(0)
#
#     return _RE_STARTTOKEN.sub(_escape, string)
