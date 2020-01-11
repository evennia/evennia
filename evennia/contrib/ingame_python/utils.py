"""
Functions to extend the event system.

These functions are to be used by developers to customize events and callbacks.

"""

from textwrap import dedent

from django.conf import settings
from evennia import logger
from evennia import ScriptDB
from evennia.utils.create import create_script
from evennia.utils.gametime import real_seconds_until as standard_rsu
from evennia.utils.utils import class_from_module
from evennia.contrib.custom_gametime import UNITS
from evennia.contrib.custom_gametime import gametime_to_realtime
from evennia.contrib.custom_gametime import real_seconds_until as custom_rsu

# Temporary storage for events waiting for the script to be started
EVENTS = []


def get_event_handler():
    """Return the event handler or None."""
    try:
        script = ScriptDB.objects.get(db_key="event_handler")
    except ScriptDB.DoesNotExist:
        logger.log_trace("Can't get the event handler.")
        script = None

    return script


def register_events(path_or_typeclass):
    """
    Register the events in this typeclass.

    Args:
        path_or_typeclass (str or type): the Python path leading to the
                class containing events, or the class itself.

    Returns:
        The typeclass itself.

    Notes:
        This function will read events from the `_events` class variable
        defined in the typeclass given in parameters.  It will add
        the events, either to the script if it exists, or to some
        temporary storage, waiting for the script to be initialized.

    """
    if isinstance(path_or_typeclass, str):
        typeclass = class_from_module(path_or_typeclass)
    else:
        typeclass = path_or_typeclass

    typeclass_name = typeclass.__module__ + "." + typeclass.__name__
    try:
        storage = ScriptDB.objects.get(db_key="event_handler")
        assert storage.is_active
        assert storage.ndb.events is not None
    except (ScriptDB.DoesNotExist, AssertionError):
        storage = EVENTS

    # If the script is started, add the event directly.
    # Otherwise, add it to the temporary storage.
    for name, tup in getattr(typeclass, "_events", {}).items():
        if len(tup) == 4:
            variables, help_text, custom_call, custom_add = tup
        elif len(tup) == 3:
            variables, help_text, custom_call = tup
            custom_add = None
        elif len(tup) == 2:
            variables, help_text = tup
            custom_call = None
            custom_add = None
        else:
            variables = help_text = custom_call = custom_add = None

        if isinstance(storage, list):
            storage.append((typeclass_name, name, variables, help_text, custom_call, custom_add))
        else:
            storage.add_event(typeclass_name, name, variables, help_text, custom_call, custom_add)

    return typeclass


# Custom callbacks for specific event types


def get_next_wait(format):
    """
    Get the length of time in seconds before format.

    Args:
        format (str): a time format matching the set calendar.

    Returns:
        until (int or float): the number of seconds until the event.
        usual (int or float): the usual number of seconds between events.
        format (str): a string format representing the time.

    Notes:
        The time format could be something like "2018-01-08 12:00".  The
        number of units set in the calendar affects the way seconds are
        calculated.

    """
    calendar = getattr(settings, "EVENTS_CALENDAR", None)
    if calendar is None:
        logger.log_err(
            "A time-related event has been set whereas "
            "the gametime calendar has not been set in the settings."
        )
        return
    elif calendar == "standard":
        rsu = standard_rsu
        units = ["min", "hour", "day", "month", "year"]
    elif calendar == "custom":
        rsu = custom_rsu
        back = dict([(value, name) for name, value in UNITS.items()])
        sorted_units = sorted(back.items())
        del sorted_units[0]
        units = [n for v, n in sorted_units]

    params = {}
    for delimiter in ("-", ":"):
        format = format.replace(delimiter, " ")

    pieces = list(reversed(format.split()))
    details = []
    i = 0
    for uname in units:
        try:
            piece = pieces[i]
        except IndexError:
            break

        if not piece.isdigit():
            logger.log_trace(
                "The time specified '{}' in {} isn't " "a valid number".format(piece, format)
            )
            return

        # Convert the piece to int
        piece = int(piece)
        params[uname] = piece
        details.append("{}={}".format(uname, piece))
        if i < len(units):
            next_unit = units[i + 1]
        else:
            next_unit = None
        i += 1

    params["sec"] = 0
    details = " ".join(details)
    until = rsu(**params)
    usual = -1
    if next_unit:
        kwargs = {next_unit: 1}
        usual = gametime_to_realtime(**kwargs)
    return until, usual, details


def time_event(obj, event_name, number, parameters):
    """
    Create a time-related event.

    Args:
        obj (Object): the object on which sits the event.
        event_name (str): the event's name.
        number (int): the number of the event.
        parameters (str): the parameter of the event.

    """
    seconds, usual, key = get_next_wait(parameters)
    script = create_script(
        "evennia.contrib.ingame_python.scripts.TimeEventScript", interval=seconds, obj=obj
    )
    script.key = key
    script.desc = "event on {}".format(key)
    script.db.time_format = parameters
    script.db.number = number
    script.ndb.usual = usual


def keyword_event(callbacks, parameters):
    """
    Custom call for events with keywords (like push, or pull, or turn...).

    Args:
        callbacks (list of dict): the list of callbacks to be called.
        parameters (str): the actual parameters entered to trigger the callback.

    Returns:
        A list containing the callback dictionaries to be called.

    Notes:
        This function should be imported and added as a custom_call
        parameter to add the event when the event supports keywords
        as parameters.  Keywords in parameters are one or more words
        separated by a comma.  For instance, a 'push 1, one' callback can
        be set to trigger when the player 'push 1' or 'push one'.

    """
    key = parameters.strip().lower()
    to_call = []
    for callback in callbacks:
        keys = callback["parameters"]
        if not keys or key in [p.strip().lower() for p in keys.split(",")]:
            to_call.append(callback)

    return to_call


def phrase_event(callbacks, parameters):
    """
    Custom call for events with keywords in sentences (like say or whisper).

    Args:
        callbacks (list of dict): the list of callbacks to be called.
        parameters (str): the actual parameters entered to trigger the callback.

    Returns:
        A list containing the callback dictionaries to be called.

    Notes:
        This function should be imported and added as a custom_call
        parameter to add the event when the event supports keywords
        in phrases as parameters.  Keywords in parameters are one or more
        words separated by a comma.  For instance, a 'say yes, okay' callback
        can be set to trigger when the player says something containing
        either "yes" or "okay" (maybe 'say I don't like it, but okay').

    """
    phrase = parameters.strip().lower()
    # Remove punctuation marks
    punctuations = ',.";?!'
    for p in punctuations:
        phrase = phrase.replace(p, " ")
    words = phrase.split()
    words = [w.strip("' ") for w in words if w.strip("' ")]
    to_call = []
    for callback in callbacks:
        keys = callback["parameters"]
        if not keys or any(key.strip().lower() in words for key in keys.split(",")):
            to_call.append(callback)

    return to_call


class InterruptEvent(RuntimeError):

    """
    Interrupt the current event.

    You shouldn't have to use this exception directly, probably use the
    `deny()` function that handles it instead.

    """

    pass
