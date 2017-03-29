"""
Module containing the EventHandler for individual objects.
"""

from collections import namedtuple

class EventsHandler(object):

    """
    The event handler for a specific object.

    The script that contains all events will be reached through this
    handler.  This handler is therefore a shortcut to be used by
    developers.  This handler (accessible through `obj.events`) is a
    shortcut to manipulating events within this object, getting,
    adding, editing, deleting and calling them.

    """

    script = None

    def __init__(self, obj):
        self.obj = obj

    def all(self):
        """
        Return all events linked to this object.

        Returns:
            All events in a dictionary event_name: event}.  The event
            is returned as a namedtuple to simply manipulation.

        """
        events = {}
        handler = type(self).script
        if handler:
            dicts = handler.get_events(self.obj)
            for event_name, in_list in dicts.items():
                new_list = []
                for event in in_list:
                    event = self.format_event(event)
                    new_list.append(event)

                if new_list:
                    events[event_name] = new_list

        return events

    def get(self, event_name):
        """
        Return the events associated with this name.

        Args:
            event_name (str): the name of the event.

        This method returns a list of Event objects (namedtuple
        representations).  If the event name cannot be found in the
        object's events, return an empty list.

        """
        return self.all().get(event_name, [])

    def get_variable(self, variable_name):
        """
        Return the variable value or None.

        Args:
            variable_name (str): the name of the variable.

        Returns:
            Either the variable's value or None.

        """
        handler = type(self).script
        if handler:
            return handler.get_variable(variable_name)

        return None

    def add(self, event_name, code, author=None, valid=False, parameters=""):
        """
        Add a new event for this object.

        Args:
            event_name (str): the name of the event to add.
            code (str): the Python code associated with this event.
            author (Character or Player, optional): the author of the event.
            valid (bool, optional): should the event be connected?
            parameters (str, optional): optional parameters.

        Returns:
            The event definition that was added or None.

        """
        handler = type(self).script
        if handler:
            return self.format_event(handler.add_event(self.obj, event_name, code,
                    author=author, valid=valid, parameters=parameters))

    def edit(self, event_name, number, code, author=None, valid=False):
        """
        Edit an existing event bound to this object.

        Args:
            event_name (str): the name of the event to edit.
            number (int): the event number to be changed.
            code (str): the Python code associated with this event.
            author (Character or Player, optional): the author of the event.
            valid (bool, optional): should the event be connected?

        Returns:
            The event definition that was edited or None.

        Raises:
            RuntimeError if the event is locked.

        """
        handler = type(self).script
        if handler:
            return self.format_event(handler.edit_event(self.obj, event_name,
                    number, code, author=author, valid=valid))

    def remove(self, event_name, number):
        """
        Delete the specified event bound to this object.

        Args:
            event_name (str): the name of the event to delete.
            number (int): the number of the event to delete.

        Raises:
            RuntimeError if the event is locked.

        """
        handler = type(self).script
        if handler:
            handler.del_event(self.obj, event_name, number)

    def call(self, event_name, *args, **kwargs):
        """
        Call the specified event(s) bound to this object.

        Args:
            event_name (str): the event name to call.
            *args: additional variables for this event.

        Kwargs:
            number (int, optional): call just a specific event.
            parameters (str, optional): call an event with parameters.
            locals (dict, optional): a locals replacement.

        Returns:
            True to report the event was called without interruption,
            False otherwise.  If the EventHandler isn't found, return
            None.

        """
        handler = type(self).script
        if handler:
            return handler.call_event(self.obj, event_name, *args, **kwargs)

        return None

    @staticmethod
    def format_event(event):
        """
        Return the Event namedtuple to represent the specified event.

        Args:
            event (dict): the event definition.

        The event given in argument should be a dictionary containing
        the expected fields for an event (code, author, valid...).

        """
        if "obj" not in event:
            event["obj"] = None
        if "name" not in event:
            event["name"] = "unknown"
        if "number" not in event:
            event["number"] = -1
        if "code" not in event:
            event["code"] = ""
        if "author" not in event:
            event["author"] = None
        if "valid" not in event:
            event["valid"] = False
        if "parameters" not in event:
            event["parameters"] = ""
        if "created_on" not in event:
            event["created_on"] = None
        if "updated_by" not in event:
            event["updated_by"] = None
        if "updated_on" not in event:
            event["updated_on"] = None

        return Event(**event)

Event = namedtuple("Event", ("obj", "name", "number", "code", "author",
        "valid", "parameters", "created_on", "updated_by", "updated_on"))
