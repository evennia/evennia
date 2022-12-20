"""
Protfuncs are FuncParser-callables that can be embedded in a prototype to
provide custom logic without having access to Python. The protfunc is parsed at
the time of spawning, using the creating object's session as input. If the
protfunc returns a non-string, this is what will be added to the prototype.

In the prototype dict, the protfunc is specified as a string inside the prototype, e.g.:

    { ...

    "key": "$funcname(args, kwargs)"

    ...  }

Available protfuncs are either all callables in one of the modules of `settings.PROT_FUNC_MODULES`
or all callables added to a dict FUNCPARSER_CALLABLES in such a module.

    def funcname (*args, **kwargs)

At spawn-time the spawner passes the following extra kwargs into each callable (in addition to
what is added in the call itself):

    - session (Session): The Session of the entity spawning using this prototype.
    - prototype (dict): The dict this protfunc is a part of.
    - current_key (str): The active key this value belongs to in the prototype.

Any traceback raised by this function will be handled at the time of spawning and abort the spawn
before any object is created/updated. It must otherwise return the value to store for the specified
prototype key (this value must be possible to serialize in an Attribute).

"""

from evennia.utils import funcparser


def protfunc_callable_protkey(*args, **kwargs):
    """
    Usage: $protkey(keyname)
    Returns the value of another key in this prototoype. Will raise an error if
        the key is not found in this prototype.

    """
    if not args:
        return ""

    prototype = kwargs.get("prototype", {})
    fieldname = args[0]
    prot_value = None
    if fieldname in prototype:
        prot_value = prototype[fieldname]
    else:
        # check if it's an attribute
        for attrtuple in prototype.get("attrs", []):
            if attrtuple[0] == fieldname:
                prot_value = attrtuple[1]
                break
        else:
            raise AttributeError(
                f"{fieldname} not found in prototype\n{prototype}\n"
                "(neither as prototype-field or as an Attribute"
            )
    if callable(prot_value):
        raise RuntimeError(
            f"Error in prototype\n{prototype}\n$protkey can only reference static "
            f"values/attributes (found {prot_value})"
        )
    try:
        return funcparser.funcparser_callable_eval(prot_value, **kwargs)
    except funcparser.ParsingError:
        return prot_value


# this is picked up by FuncParser
FUNCPARSER_CALLABLES = {
    "protkey": protfunc_callable_protkey,
    **funcparser.FUNCPARSER_CALLABLES,
    **funcparser.SEARCHING_CALLABLES,
}
