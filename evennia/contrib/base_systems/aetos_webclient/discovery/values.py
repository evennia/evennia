"""
Describing a live value without running anything the value owns.

WHY THIS NEEDS ITS OWN MODULE. B.20 asks the runtime pass to show what it found
-- `db.hp 82 int`, `db.current_target Goblin Object` -- and the obvious way to
show a value is `repr(value)`. That is a method call on an object of the game's
choosing. A custom class's `__repr__` can query the database, raise, recurse
forever through a structure that contains itself, or return a megabyte. So
nothing here calls a method a game could have overridden:

- **Numbers, booleans and text** are formatted by discovery, from the value.
- **A game object** is shown by its `db_key` and `id` -- model fields read
  straight off the row, not `get_display_name()` or `__str__`, both of which a
  typeclass may override.
- **A collection** is shown by its size and nothing else. Its contents are where
  a nested `password` would be, and walking it is where a recursive structure
  would hang the command.
- **Anything else** is shown as its type's name: `a Trait`. The honest answer to
  "what is this" when the only way to find out is to run its code.

Text is cut short rather than shown whole. A report is for recognising a value
("oh, that's the title"), not for reading it, and a bounded line is a line that
cannot carry somebody's whole biography into an issue tracker.

"""

from collections.abc import Iterable, Mapping

#: The longest text value shown, in characters, before it is cut.
MAX_SHOWN_TEXT = 32


def _is_game_object(value):
    """
    Whether a value is an Evennia typeclassed entity.

    Args:
        value: Anything.

    Returns:
        bool: True for objects, accounts, scripts and channels.

    Notes:
        Imported inside the function so that importing discovery never pulls
        the model layer in by itself -- the command defers its imports for the
        same reason.

    """
    from evennia.typeclasses.models import TypedObject

    return isinstance(value, TypedObject)


def kind_of(value):
    """
    What a live value is, in discovery's vocabulary.

    Args:
        value: The attribute's value.

    Returns:
        str: One of `candidates.KINDS`.

    Notes:
        `bool` before `int`, because `True` is an `int` in Python and a flag
        reported as a number would be suggested as a health bar.

        Evennia wraps saved lists and dicts in saver types, which register as
        `MutableMapping` and `MutableSequence`, so a `_SaverDict` is a dict for
        every purpose discovery has.

    """
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if _is_game_object(value):
        return "object"
    # `isinstance` against the abstract base classes, never `hasattr(value, ...)`.
    # `hasattr` on an instance goes through that instance's `__getattr__`, which
    # is the game's code; the ABCs look at the *type*.
    if isinstance(value, (Mapping, Iterable)):
        return "collection"
    return "unknown"


def shown(value):
    """
    A short, safe description of a value for the report.

    Args:
        value: The attribute's value.

    Returns:
        str: e.g. `82`, `'the Brave'`, `Goblin (#12)`, `3 items`, `a Trait`.

    """
    kind = kind_of(value)
    if kind == "boolean":
        return "True" if value else "False"
    if kind == "number":
        if isinstance(value, float):
            return ("%.2f" % value).rstrip("0").rstrip(".")
        return "%d" % value
    if kind == "text":
        if len(value) > MAX_SHOWN_TEXT:
            return "'%s...'" % value[:MAX_SHOWN_TEXT]
        return "'%s'" % value
    if kind == "object":
        # Model fields, not methods. `db_key` is the column; `key` and
        # `get_display_name()` are overridable.
        return "%s (#%s)" % (getattr(value, "db_key", "?"), getattr(value, "id", "?"))
    if kind == "collection":
        try:
            size = len(value)
        except Exception:
            return "a %s" % type(value).__name__
        return "%d item%s" % (size, "" if size == 1 else "s")
    return "a %s" % type(value).__name__
