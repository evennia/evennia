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

Available protfuncs are callables in one of the modules of `settings.PROT_FUNC_MODULES`. They
are specified as functions

    def funcname (*args, **kwargs)

where *args are the arguments given in the prototype, and **kwargs are inserted by Evennia:

    - session (Session): The Session of the entity spawning using this prototype.
    - prototype (dict): The dict this protfunc is a part of.
    - current_key (str): The active key this value belongs to in the prototype.
    - testing (bool): This is set if this function is called as part of the prototype validation; if
        set, the protfunc should take care not to perform any persistent actions, such as operate on
        objects or add things to the database.

Any traceback raised by this function will be handled at the time of spawning and abort the spawn
before any object is created/updated. It must otherwise return the value to store for the specified
prototype key (this value must be possible to serialize in an Attribute).

"""

from ast import literal_eval
from random import randint as base_randint, random as base_random, choice as base_choice
import re

from evennia.utils import search
from evennia.utils.utils import justify as base_justify, is_iter, to_str

_PROTLIB = None

_RE_DBREF = re.compile(r"\#[0-9]+")


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
        return base_justify(args[0], align="l")
    return ""


def right_justify(*args, **kwargs):
    """
    Usage: $right_justify(<text>)
    Returns <text> right-justified across screen width.

    """
    if args:
        return base_justify(args[0], align="r")
    return ""


def center_justify(*args, **kwargs):

    """
    Usage: $center_justify(<text>)
    Returns <text> centered in screen width.

    """
    if args:
        return base_justify(args[0], align="c")
    return ""


def choice(*args, **kwargs):
    """
    Usage: $choice(val, val, val, ...)
    Returns one of the values randomly
    """
    if args:
        return base_choice(args)
    return ""


def full_justify(*args, **kwargs):

    """
    Usage: $full_justify(<text>)
    Returns <text> filling up screen width by adding extra space.

    """
    if args:
        return base_justify(args[0], align="f")
    return ""


def protkey(*args, **kwargs):
    """
    Usage: $protkey(<key>)
    Returns the value of another key in this prototoype. Will raise an error if
        the key is not found in this prototype.

    """
    if args:
        prototype = kwargs["prototype"]
        return prototype[args[0].strip()]


def add(*args, **kwargs):
    """
    Usage: $add(val1, val2)
    Returns the result of val1 + val2. Values must be
        valid simple Python structures possible to add,
        such as numbers, lists etc.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        # try to convert to python structures, otherwise, keep as strings
        try:
            val1 = literal_eval(val1.strip())
        except Exception:
            pass
        try:
            val2 = literal_eval(val2.strip())
        except Exception:
            pass
        return val1 + val2
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
        # try to convert to python structures, otherwise, keep as strings
        try:
            val1 = literal_eval(val1.strip())
        except Exception:
            pass
        try:
            val2 = literal_eval(val2.strip())
        except Exception:
            pass
        return val1 - val2
    raise ValueError("$sub requires two arguments.")


def mult(*args, **kwargs):
    """
    Usage: $mul(val1, val2)
    Returns the value of val1 * val2. The values must be
        valid simple Python structures possible to
        multiply, like strings and/or numbers.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        # try to convert to python structures, otherwise, keep as strings
        try:
            val1 = literal_eval(val1.strip())
        except Exception:
            pass
        try:
            val2 = literal_eval(val2.strip())
        except Exception:
            pass
        return val1 * val2
    raise ValueError("$mul requires two arguments.")


def div(*args, **kwargs):
    """
    Usage: $div(val1, val2)
    Returns the value of val1 / val2. Values must be numbers and
        the result is always a float.

    """
    if len(args) > 1:
        val1, val2 = args[0], args[1]
        # try to convert to python structures, otherwise, keep as strings
        try:
            val1 = literal_eval(val1.strip())
        except Exception:
            pass
        try:
            val2 = literal_eval(val2.strip())
        except Exception:
            pass
        return val1 / float(val2)
    raise ValueError("$mult requires two arguments.")


def toint(*args, **kwargs):
    """
    Usage: $toint(<number>)
    Returns <number> as an integer.
    """
    if args:
        val = args[0]
        try:
            return int(literal_eval(val.strip()))
        except ValueError:
            return val
    raise ValueError("$toint requires one argument.")


def eval(*args, **kwargs):
    """
    Usage $eval(<expression>)
    Returns evaluation of a simple Python expression. The string may *only* consist of the following
        Python literal structures: strings, numbers, tuples, lists, dicts, booleans,
        and None. The strings can also contain #dbrefs. Escape embedded protfuncs as $$protfunc(..)
        - those will then be evaluated *after* $eval.

    """
    global _PROTLIB
    if not _PROTLIB:
        from evennia.prototypes import prototypes as _PROTLIB

    string = ",".join(args)
    struct = literal_eval(string)

    if isinstance(struct, str):
        # we must shield the string, otherwise it will be merged as a string and future
        # literal_evas will pick up e.g. '2' as something that should be converted to a number
        struct = '"{}"'.format(struct)

    # convert any #dbrefs to objects (also in nested structures)
    struct = _PROTLIB.value_to_obj_or_any(struct)

    return struct


def _obj_search(*args, **kwargs):
    "Helper function to search for an object"

    query = "".join(args)
    session = kwargs.get("session", None)
    return_list = kwargs.pop("return_list", False)
    account = None

    if session:
        account = session.account

    targets = search.search_object(query)

    if return_list:
        retlist = []
        if account:
            for target in targets:
                if target.access(account, target, "control"):
                    retlist.append(target)
        else:
            retlist = targets
        return retlist
    else:
        # single-match
        if not targets:
            raise ValueError("$obj: Query '{}' gave no matches.".format(query))
        if len(targets) > 1:
            raise ValueError(
                "$obj: Query '{query}' gave {nmatches} matches. Limit your "
                "query or use $objlist instead.".format(query=query, nmatches=len(targets))
            )
        target = targets[0]
        if account:
            if not target.access(account, target, "control"):
                raise ValueError(
                    "$obj: Obj {target}(#{dbref} cannot be added - "
                    "Account {account} does not have 'control' access.".format(
                        target=target.key, dbref=target.id, account=account
                    )
                )
        return target


def obj(*args, **kwargs):
    """
    Usage $obj(<query>)
    Returns one Object searched globally by key, alias or #dbref. Error if more than one.

    """
    obj = _obj_search(return_list=False, *args, **kwargs)
    if obj:
        return "#{}".format(obj.id)
    return "".join(args)


def objlist(*args, **kwargs):
    """
    Usage $objlist(<query>)
    Returns list with one or more Objects searched globally by key, alias or #dbref.

    """
    return ["#{}".format(obj.id) for obj in _obj_search(return_list=True, *args, **kwargs)]


def dbref(*args, **kwargs):
    """
    Usage $dbref(<#dbref>)
    Validate that a #dbref input is valid.
    """
    if not args or len(args) < 1 or _RE_DBREF.match(args[0]) is None:
        raise ValueError("$dbref requires a valid #dbref argument.")

    return obj(args[0])
