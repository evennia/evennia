"""
Module defining basic helpers for the event system.


Hlpers are just Python function that can be used inside of events.  They

"""

from evennia import ObjectDB
from evennia.contrib.events.exceptions import InterruptEvent

def deny():
    """
    Deny, that is stop, the event here.

    This function will raise an exception to terminate the event
    in a controlled way.  If you use this function in an event called
    prior to a command, the command will be cancelled as well.  Good
    situations to use the `deny()` function are in events that begins
    by `can_`, because they usually can be cancelled as easily as that.

    """
    raise InterruptEvent

def get(**kwargs):
    """
    Return an object with the given search option or None if None is found.

    This function is very useful to retrieve objects with a specific
    ID.  You know that room #32 exists, but you don't have it in
    the event variables.  Quite simple:
        room = get(id=32)

    This function doesn't perform a search on objects, but a direct
    search in the database.  It's recommended to use it for objects
    you know exist, using their IDs or other unique attributes.
    Looking for objects by key is possible (use `db_key` as an
    argument) but remember several objects can share the same key.

    Kwargs:
        Any searchable data or property (id, db_key, db_location...).

    Returns:
        The object found that meet these criteria for research, or
        None if none is found.

    """
    try:
        object = ObjectDB.objects.get(**kwargs)
    except ObjectDB.DoesNotExist:
        object = None

    return object
