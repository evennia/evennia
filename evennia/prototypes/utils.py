"""

Prototype utilities

"""

_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")


class PermissionError(RuntimeError):
    pass


def prototype_to_str(prototype):
    """
    Format a prototype to a nice string representation.

    Args:
        prototype (dict): The prototype.
    """

    header = (
        "|cprototype key:|n {}, |ctags:|n {}, |clocks:|n {} \n"
        "|cdesc:|n {} \n|cprototype:|n ".format(
           prototype['prototype_key'],
           ", ".join(prototype['prototype_tags']),
           prototype['prototype_locks'],
           prototype['prototype_desc']))
    proto = ("{{\n  {} \n}}".format(
        "\n  ".join(
            "{!r}: {!r},".format(key, value) for key, value in
             sorted(prototype.items()) if key not in _PROTOTYPE_META_NAMES)).rstrip(","))
    return header + proto


def prototype_diff_from_object(prototype, obj):
    """
    Get a simple diff for a prototype compared to an object which may or may not already have a
    prototype (or has one but changed locally). For more complex migratations a manual diff may be
    needed.

    Args:
        prototype (dict): Prototype.
        obj (Object): Object to

    Returns:
        diff (dict): Mapping for every prototype key: {"keyname": "REMOVE|UPDATE|KEEP", ...}

    """
    prot1 = prototype
    prot2 = prototype_from_object(obj)

    diff = {}
    for key, value in prot1.items():
        diff[key] = "KEEP"
        if key in prot2:
            if callable(prot2[key]) or value != prot2[key]:
                diff[key] = "UPDATE"
        elif key not in prot2:
            diff[key] = "REMOVE"

    return diff
