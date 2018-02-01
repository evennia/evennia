"""
Module defining basic eventfuncs for the event system.

Eventfuncs are just Python functions that can be used inside of calllbacks.

"""

from evennia import ObjectDB, ScriptDB
from evennia.contrib.ingame_python.utils import InterruptEvent


def deny():
    """
    Deny, that is stop, the callback here.

    Notes:
        This function will raise an exception to terminate the callback
        in a controlled way.  If you use this function in an event called
        prior to a command, the command will be cancelled as well.  Good
        situations to use the `deny()` function are in events that begins
        by `can_`, because they usually can be cancelled as easily as that.

    """
    raise InterruptEvent


def get(**kwargs):
    """
    Return an object with the given search option or None if None is found.

    Kwargs:
        Any searchable data or property (id, db_key, db_location...).

    Returns:
        The object found that meet these criteria for research, or
        None if none is found.

    Notes:
        This function is very useful to retrieve objects with a specific
        ID.  You know that room #32 exists, but you don't have it in
        the callback variables.  Quite simple:
            room = get(id=32)

        This function doesn't perform a search on objects, but a direct
        search in the database.  It's recommended to use it for objects
        you know exist, using their IDs or other unique attributes.
        Looking for objects by key is possible (use `db_key` as an
        argument) but remember several objects can share the same key.

    """
    try:
        object = ObjectDB.objects.get(**kwargs)
    except ObjectDB.DoesNotExist:
        object = None

    return object


def call_event(obj, event_name, seconds=0):
    """
    Call the specified event in X seconds.

    Args:
        obj (Object): the typeclassed object containing the event.
        event_name (str): the event name to be called.
        seconds (int or float): the number of seconds to wait before calling
                the event.

    Notes:
        This eventfunc can be used to call other events from inside of an
        event in a given time.  This will create a pause between events.  This
        will not freeze the game, and you can expect characters to move
        around (unless you prevent them from doing so).

        Variables that are accessible in your event using 'call()' will be
        kept and passed on to the event to call.

        Chained callbacks are designed for this very purpose: they
        are never called automatically by the game, rather, they need
        to be called from inside another event.

    """
    script = type(obj.callbacks).script
    if script:
        # If seconds is 0, call the event immediately
        if seconds == 0:
            locals = dict(script.ndb.current_locals)
            obj.callbacks.call(event_name, locals=locals)
        else:
            # Schedule the task
            script.set_task(seconds, obj, event_name)
