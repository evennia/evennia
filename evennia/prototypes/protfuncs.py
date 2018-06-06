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

Any traceback raised by this function will be handled at the time of spawning and abort the spawn
before any object is created/updated. It must otherwise return the value to store for the specified
prototype key (this value must be possible to serialize in an Attribute).

"""

from django.conf import settings
from evennia.utils import inlinefuncs
from evennia.utils.utils import callables_from_module


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
        value (string): The value to test for a parseable protfunc.
        available_functions (dict, optional): Mapping of name:protfunction to use for this parsing.

    Kwargs:
        any (any): Passed on to the inlinefunc.

    Returns:
        any (any): A structure to replace the string on the prototype level. If this is a
            callable or a (callable, (args,)) structure, it will be executed as if one had supplied
            it to the prototype directly.

    """
    if not isinstance(value, basestring):
        return value
    available_functions = _PROTOTYPEFUNCS if available_functions is None else available_functions
    return inlinefuncs.parse_inlinefunc(value, _available_funcs=available_functions, **kwargs)


# default protfuncs
