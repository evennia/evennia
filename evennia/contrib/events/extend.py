"""
Functions to extend the event system.

These funcitons are not helpers (helpers are in a separate module)
and are designed to be used more by developers to add event types.

"""

from evennia import logger
from evennia import ScriptDB

def create_event_type(typeclass, event_name, variables, help_text):
    """
    Create a new event type for a specific typeclass.

    Args:
        typeclass (type): the class defining tye typeclass to be used.
        event_name (str): the name of the event to be added.
        variables (list of str): a list of variable names.
        help_text (str): a help text of the event.

    Events obey the inheritance hierarchy: if you set an event on
    DefaultRoom, for instance, and if your Room typeclass inherits
    from DefaultRoom (the default), the event will be available to
    all rooms.  Objects of the typeclass set in argument will be
    able to set one or more events of that name.

    If the event already exists in the typeclass, replace it.

    """
    typeclass_name = typeclass.__module__ + "." + typeclass.__name__
    try:
        script = ScriptDB.objects.get(db_key="event_handler")
    except ScriptDB.DoesNotExist:
        logger.log_err("Can't create event {} in typeclass {}, the " \
                "script handler isn't defined".format(name, typeclass_name))
        return

    # Get the event types for this typeclass
    event_types = script.db.event_types.get(typeclass_name, {})
    if not event_types:
        script.db.event_types[typeclass_name] = event_types

    # Add or replace the event
    event_types[event_name] = (variables, help_text)

def del_event_type(typeclass, event_name):
    """
    Delete the event type for this typeclass.

    Args:
        typeclass (type): the class defining the typeclass.
        event_name (str): the name of the event to be deleted.

    If you want to delete an event type, you need to remove it from
    the typeclass that defined it: other typeclasses in the inheritance
    hierarchy are not affected.  This method doesn't remove the
    already-created events associated with individual objects.

    """
    typeclass_name = typeclass.__module__ + "." + typeclass.__name__
    try:
        script = ScriptDB.objects.get(db_key="event_handler")
    except ScriptDB.DoesNotExist:
        logger.log_err("Can't create event {} in typeclass {}, the " \
                "script handler isn't defined".format(name, typeclass_name))
        return

    # Get the event types for this typeclass
    event_types = script.db.event_types.get(typeclass_name, {})
    if event_name in event_types:
        del event_types[event_name]
