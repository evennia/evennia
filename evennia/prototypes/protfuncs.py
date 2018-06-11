"""
Protfuncs are function-strings embedded in a prototype and allows for a builder to create a
prototype with custom logics without having access to Python. The Protfunc is parsed using the
inlinefunc parser but is fired at the moment the spawning happens, using the creating object's
session as input.

In the prototype dict, the protfunc is specified as a string inside the prototype, e.g.:

    { ...

    "key": "$funcname(arg1, arg2, ...)"

    ...  }

and multiple functions can be nested (no keyword args are supported). The result will be used as the
value for that prototype key for that individual spawn.

Available protfuncs are callables in one of the modules of `settings.PROTOTYPEFUNC_MODULES`. They
are specified as functions

    def funcname (*args, **kwargs)

where *args are the arguments given in the prototype, and **kwargs are inserted by Evennia:

    - session (Session): The Session of the entity spawning using this prototype.
    - prototype_key (str): The currently spawning prototype-key.
    - prototype (dict): The dict this protfunc is a part of.
    - testing (bool): This is set if this function is called as part of the prototype validation; if
        set, the protfunc should take care not to perform any persistent actions, such as operate on
        objects or add things to the database.

Any traceback raised by this function will be handled at the time of spawning and abort the spawn
before any object is created/updated. It must otherwise return the value to store for the specified
prototype key (this value must be possible to serialize in an Attribute).

"""

from ast import literal_eval
from random import randint as base_randint, random as base_random

from django.conf import settings
from evennia.utils import inlinefuncs
from evennia.utils.utils import callables_from_module
from evennia.utils.utils import justify as base_justify, is_iter
from evennia.prototypes.prototypes import value_to_obj_or_any


_PROTOTYPEFUNCS = {}

for mod in settings.PROTOTYPEFUNC_MODULES:
    try:
        callables = callables_from_module(mod)
        if mod == __name__:
            callables.pop("protfunc_parser")
        _PROTOTYPEFUNCS.update(callables)
    except ImportError:
        pass


def protfunc_parser(value, available_functions=None, **kwargs):
    """
    Parse a prototype value string for a protfunc and process it.

    Available protfuncs are specified as callables in one of the modules of
    `settings.PROTOTYPEFUNC_MODULES`, or specified on the command line.

    Args:
        value (any): The value to test for a parseable protfunc. Only strings will be parsed for
            protfuncs, all other types are returned as-is.
        available_functions (dict, optional): Mapping of name:protfunction to use for this parsing.

    Kwargs:
        any (any): Passed on to the inlinefunc.

    Returns:
        any (any): A structure to replace the string on the prototype level. If this is a
            callable or a (callable, (args,)) structure, it will be executed as if one had supplied
            it to the prototype directly. This structure is also passed through literal_eval so one
            can get actual Python primitives out of it (not just strings). It will also identify
            eventual object #dbrefs in the output from the protfunc.


    """
    if not isinstance(value, basestring):
        return value
    available_functions = _PROTOTYPEFUNCS if available_functions is None else available_functions
    result = inlinefuncs.parse_inlinefunc(value, _available_funcs=available_functions, **kwargs)
    result = value_to_obj_or_any(result)
    try:
        return literal_eval(result)
    except ValueError:
        return result



# default protfuncs

def random(*args, **kwargs):
    """
    Usage: $random()
    Returns a random value in the interval [0, 1)

    """
    return base_random()


def randint(*args, **kwargs):
    """
    Usage: $randint(start, end)
    Returns random integer in interval [start, end]

    """
    if len(args) != 2:
        raise TypeError("$randint needs two arguments - start and end.")
    start, end = int(args[0]), int(args[1])
    return base_randint(start, end)


def left_justify(*args, **kwargs):
    """
    Usage: $left_justify(<text>)
    Returns <text> left-justified.

    """
    if args:
        return base_justify(args[0], align='l')
    return ""


def right_justify(*args, **kwargs):
    """
    Usage: $right_justify(<text>)
    Returns <text> right-justified across screen width.

    """
    if args:
        return base_justify(args[0], align='r')
    return ""


def center_justify(*args, **kwargs):

    """
    Usage: $center_justify(<text>)
    Returns <text> centered in screen width.

    """
    if args:
        return base_justify(args[0], align='c')
    return ""


def full_justify(*args, **kwargs):

    """
    Usage: $full_justify(<text>)
    Returns <text> filling up screen width by adding extra space.

    """
    if args:
        return base_justify(args[0], align='f')
    return ""


def protkey(*args, **kwargs):
    """
    Usage: $protkey(<key>)
    Returns the value of another key in this prototoype. Will raise an error if
        the key is not found in this prototype.

    """
    if args:
        prototype = kwargs['prototype']
        return prototype[args[0]]


def add(*args, **kwargs):
    """
    Usage: $add(val1, val2)
    Returns the result of val1 + val2. Values must be
        valid simple Python structures possible to add,
        such as numbers, lists etc.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        return literal_eval(val1) + literal_eval(val2)
    raise ValueError("$add requires two arguments.")


def sub(*args, **kwargs):
    """
    Usage: $del(val1, val2)
    Returns the value of val1 - val2. Values must be
        valid simple Python structures possible to
        subtract.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        return literal_eval(val1) - literal_eval(val2)
    raise ValueError("$sub requires two arguments.")


def mul(*args, **kwargs):
    """
    Usage: $mul(val1, val2)
    Returns the value of val1 * val2. The values must be
        valid simple Python structures possible to
        multiply, like strings and/or numbers.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        return literal_eval(val1) * literal_eval(val2)
    raise ValueError("$mul requires two arguments.")


def div(*args, **kwargs):
    """
    Usage: $div(val1, val2)
    Returns the value of val1 / val2. Values must be numbers and
        the result is always a float.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        return literal_eval(val1) / float(literal_eval(val2))
    raise ValueError("$mult requires two arguments.")


def eval(*args, **kwargs):
    """
    Usage $eval(<expression>)
    Returns evaluation of a simple Python expression. The string may *only* consist of the following
        Python literal structures: strings, numbers, tuples, lists, dicts, booleans,
        and None. The strings can also contain #dbrefs. Escape embedded protfuncs as $$protfunc(..)
        - those will then be evaluated *after* $eval.

    """
    string = args[0] if args else ''
    struct = literal_eval(string)

    def _recursive_parse(val):
        # an extra round of recursive parsing, to catch any escaped $$profuncs
        if is_iter(val):
            stype = type(val)
            if stype == dict:
                return {_recursive_parse(key): _recursive_parse(v) for key, v in val.items()}
            return stype((_recursive_parse(v) for v in val))
        return protfunc_parser(val)

    return _recursive_parse(struct)
