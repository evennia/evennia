"""
Inline functions (nested form).

This parser accepts nested inlinefunctions on the form

```
$funcname(arg, arg, ...)
```

embedded in any text where any arg can be another $funcname{} call.
This functionality is turned off by default - to activate,
`settings.INLINEFUNC_ENABLED` must be set to `True`.

Each token starts with "$funcname(" where there must be no space
between the $funcname and (. It ends with a matched ending parentesis.
")".

Inside the inlinefunc definition, one can use `\` to escape. This is
mainly needed for escaping commas in flowing text (which would
otherwise be interpreted as an argument separator), or to escape `}`
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

Error handling:
   Syntax errors, notably not completely closing all inlinefunc
   blocks, will lead to the entire string remaining unparsed.

"""

import re
from django.conf import settings
from evennia.utils import utils


# example/testing inline functions

def pad(*args, **kwargs):
    """
    Inlinefunc. Pads text to given width.

    Args:
        text (str, optional): Text to pad.
        width (str, optional): Will be converted to integer. Width
            of padding.
        align (str, optional): Alignment of padding; one of 'c', 'l' or 'r'.
        fillchar (str, optional): Character used for padding. Defaults to a space.

    Kwargs:
        session (Session): Session performing the pad.

    Example:
        `$pad(text, width, align, fillchar)`

    """
    text, width, align, fillchar = "", 78, 'c', ' '
    nargs = len(args)
    if nargs > 0:
        text = args[0]
    if nargs > 1:
        width = int(args[1]) if args[1].strip().isdigit() else 78
    if nargs > 2:
        align = args[2] if args[2] in ('c', 'l', 'r') else 'c'
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
    Kwargs:
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


def clr(*args, **kwargs):
    """
    Inlinefunc. Colorizes nested text.

    Args:
        startclr (str, optional): An ANSI color abbreviation without the
            prefix `|`, such as `r` (red foreground) or `[r` (red background).
        text (str, optional): Text
        endclr (str, optional): The color to use at the end of the string. Defaults
            to `|n` (reset-color).
    Kwargs:
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


# we specify a default nomatch function to use if no matching func was
# found. This will be overloaded by any nomatch function defined in
# the imported modules.
_INLINE_FUNCS = {"nomatch": lambda *args, **kwargs: "<UKNOWN>",
        "stackfull": lambda *args, **kwargs: "\n (not parsed: inlinefunc stack size exceeded.)"}


# load custom inline func modules.
for module in utils.make_iter(settings.INLINEFUNC_MODULES):
    try:
        _INLINE_FUNCS.update(utils.callables_from_module(module))
    except ImportError as err:
        if module == "server.conf.inlinefuncs":
            # a temporary warning since the default module changed name
            raise ImportError("Error: %s\nPossible reason: mygame/server/conf/inlinefunc.py should "
                  "be renamed to mygame/server/conf/inlinefuncs.py (note the S at the end)." % err)
        else:
            raise


# remove the core function if we include examples in this module itself
#_INLINE_FUNCS.pop("inline_func_parse", None)


# The stack size is a security measure. Set to <=0 to disable.
try:
    _STACK_MAXSIZE = settings.INLINEFUNC_STACK_MAXSIZE
except AttributeError:
    _STACK_MAXSIZE = 20

# regex definitions

_RE_STARTTOKEN = re.compile(r"(?<!\\)\$(\w+)\(") # unescaped $funcname{ (start of function call)

_RE_TOKEN = re.compile(r"""
                        (?<!\\)\'\'\'(?P<singlequote>.*?)(?<!\\)\'\'\'| # unescaped single-triples (escapes all inside them)
                        (?<!\\)\"\"\"(?P<doublequote>.*?)(?<!\\)\"\"\"| # unescaped normal triple quotes (escapes all inside them)
                        (?P<comma>(?<!\\)\,)|                           # unescaped , (argument separator)
                        (?P<end>(?<!\\)\))|                             # unescaped ) (end of function call)
                        (?P<start>(?<!\\)\$\w+\()|                      # unescaped $funcname( (start of function call)
                        (?P<escaped>\\'|\\"|\\\)|\\$\w+\()|             # escaped tokens should re-appear in text
                        (?P<rest>[\w\s.-\/#!%\^&\*;:=\-_`~\|\(}{\[\]]+|\"{1}|\'{1}) # everything else should also be included""",
                        re.UNICODE + re.IGNORECASE + re.VERBOSE + re.DOTALL)


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
        super(ParseStack, self).__init__(*args, **kwargs)
        # always start stack with the empty string
        list.append(self, "")
        # indicates if the top of the stack is a string or not
        self._string_last = True

    def append(self, item):
        """
        The stack will merge strings, add other things as normal
        """
        if isinstance(item, basestring):
            if self._string_last:
                self[-1] += item
            else:
                list.append(self, item)
                self._string_last = True
        else:
            # everything else is added as normal
            list.append(self, item)
            self._string_last = False


class InlinefuncError(RuntimeError):
    pass

def parse_inlinefunc(string, strip=False, **kwargs):
    """
    Parse the incoming string.

    Args:
        string (str): The incoming string to parse.
        strip (bool, optional): Whether to strip function calls rather than
            execute them.
    Kwargs:
        session (Session): This is sent to this function by Evennia when triggering
            it. It is passed to the inlinefunc.
        kwargs (any): All other kwargs are also passed on to the inlinefunc.


    """
    global _PARSING_CACHE
    if string in _PARSING_CACHE:
        # stack is already cached
        stack = _PARSING_CACHE[string]
    elif not _RE_STARTTOKEN.search(string):
        # if there are no unescaped start tokens at all, return immediately.
        return string
    else:
        # no cached stack; build a new stack and continue
        stack = ParseStack()

    # process string on stack
    ncallable = 0
    for match in _RE_TOKEN.finditer(string):
        gdict = match.groupdict()
        if gdict["singlequote"]:
            stack.append(gdict["singlequote"])
        elif gdict["doublequote"]:
            stack.append(gdict["doublequote"])
        elif gdict["end"]:
            if ncallable <= 0:
                stack.append(")")
                continue
            args = []
            while stack:
                operation = stack.pop()
                if callable(operation):
                    if not strip:
                        stack.append((operation, [arg for arg in reversed(args)]))
                    ncallable -= 1
                    break
                else:
                    args.append(operation)
        elif gdict["start"]:
            funcname = _RE_STARTTOKEN.match(gdict["start"]).group(1)
            try:
                # try to fetch the matching inlinefunc from storage
                stack.append(_INLINE_FUNCS[funcname])
            except KeyError:
                stack.append(_INLINE_FUNCS["nomatch"])
                stack.append(funcname)
            ncallable += 1
        elif gdict["escaped"]:
            # escaped tokens
            token = gdict["escaped"].lstrip("\\")
            stack.append(token)
        elif gdict["comma"]:
            if ncallable > 0:
                # commas outside strings and inside a callable are
                # used to mark argument separation - we use None
                # in the stack to indicate such a separation.
                stack.append(None)
            else:
                # no callable active - just a string
                stack.append(",")
        else:
            # the rest
            stack.append(gdict["rest"])

    if ncallable > 0:
        # this means not all inlinefuncs were complete
        return string

    if _STACK_MAXSIZE > 0 and _STACK_MAXSIZE < len(stack):
        # if stack is larger than limit, throw away parsing
        return string + gdict["stackfull"](*args, **kwargs)
    else:
        # cache the stack
        _PARSING_CACHE[string] = stack

    # run the stack recursively
    def _run_stack(item, depth=0):
        retval = item
        if isinstance(item, tuple):
            if strip:
                return ""
            else:
                func, arglist = item
                args = [""]
                for arg in arglist:
                    if arg is None:
                        # an argument-separating comma - start a new arg
                        args.append("")
                    else:
                        # all other args should merge into one string
                        args[-1] += _run_stack(arg, depth=depth+1)
                # execute the inlinefunc at this point or strip it.
                kwargs["inlinefunc_stack_depth"] = depth
                retval = "" if strip else func(*args, **kwargs)
        return utils.to_str(retval, force_string=True)

    # execute the stack from the cache
    return "".join(_run_stack(item) for item in _PARSING_CACHE[string])

#
# Nick templating
#

"""
This supports the use of replacement templates in nicks:

This happens in two steps:

1) The user supplies a template that is converted to a regex according
   to the unix-like templating language.
2) This regex is tested against nicks depending on which nick replacement
   strategy is considered (most commonly inputline).
3) If there is a template match and there are templating markers,
   these are replaced with the arguments actually given.

@desc $1 $2 $3

This will be converted to the following regex:

\@desc (?P<1>\w+) (?P<2>\w+) $(?P<3>\w+)

Supported template markers (through fnmatch)
   *       matches anything (non-greedy)     -> .*?
   ?       matches any single character      ->
   [seq]   matches any entry in sequence
   [!seq]  matches entries not in sequence
Custom arg markers
   $N      argument position (1-99)

"""
import fnmatch
_RE_NICK_ARG = re.compile(r"\\(\$)([1-9][0-9]?)")
_RE_NICK_TEMPLATE_ARG = re.compile(r"(\$)([1-9][0-9]?)")
_RE_NICK_SPACE = re.compile(r"\\ ")


class NickTemplateInvalid(ValueError):
    pass


def initialize_nick_templates(in_template, out_template):
    """
    Initialize the nick templates for matching and remapping a string.

    Args:
        in_template (str): The template to be used for nick recognition.
        out_template (str): The template to be used to replace the string
            matched by the in_template.

    Returns:
        regex  (regex): Regex to match against strings
        template (str): Template with markers {arg1}, {arg2}, etc for
            replacement using the standard .format method.

    Raises:
        NickTemplateInvalid: If the in/out template does not have a matching
            number of $args.

    """
    # create the regex for in_template
    regex_string = fnmatch.translate(in_template)
    n_inargs = len(_RE_NICK_ARG.findall(regex_string))
    regex_string = _RE_NICK_SPACE.sub("\s+", regex_string)
    regex_string = _RE_NICK_ARG.sub(lambda m: "(?P<arg%s>.+?)" % m.group(2), regex_string)

    # create the out_template
    template_string = _RE_NICK_TEMPLATE_ARG.sub(lambda m: "{arg%s}" % m.group(2), out_template)

    # validate the tempaltes - they should at least have the same number of args
    n_outargs = len(_RE_NICK_TEMPLATE_ARG.findall(out_template))
    if n_inargs != n_outargs:
        print n_inargs, n_outargs
        raise NickTemplateInvalid

    return re.compile(regex_string), template_string


def parse_nick_template(string, template_regex, outtemplate):
    """
    Parse a text using a template and map it to another template

    Args:
        string (str): The input string to processj
        template_regex (regex): A template regex created with
            initialize_nick_template.
        outtemplate (str): The template to which to map the matches
            produced by the template_regex. This should have $1, $2,
            etc to match the regex.

    """
    match = template_regex.match(string)
    if match:
        return outtemplate.format(**match.groupdict())
    return string


