"""
Scripts for the event system.
"""

from datetime import datetime
from Queue import Queue

from evennia import DefaultScript
from evennia import logger
from evennia.contrib.events.exceptions import InterruptEvent
from evennia.contrib.events.custom import connect_event_types, patch_hooks
from evennia.contrib.events import typeclasses
from evennia.utils.utils import all_from_module

class EventHandler(DefaultScript):

    """Event handler that contains all events in a global script."""

    def at_script_creation(self):
        self.key = "event_handler"
        self.desc = "Global event handler"
        self.persistent = True

        # Permanent data to be stored
        self.db.events = {}
        self.db.to_valid = []

    def at_start(self):
        """Set up the event system."""
        self.ndb.event_types = {}
        connect_event_types()
        patch_hooks()

    def get_events(self, obj):
        """
        Return a dictionary of the object's events.

        Args:
            obj (Object): the connected objects.

        """
        return self.db.events.get(obj, {})

    def get_event_types(self, obj):
        """
        Return a dictionary of event types on this object.

        Args:
            obj (Object): the connected object.

        """
        types = {}
        event_types = self.ndb.event_types
        classes = Queue()
        classes.put(type(obj))
        while not classes.empty():
            typeclass = classes.get()
            typeclass_name = typeclass.__module__ + "." + typeclass.__name__
            types.update(event_types.get(typeclass_name, {}))

            # Look for the parent classes
            for parent in typeclass.__bases__:
                classes.put(parent)

        return types

    def add_event(self, obj, event_name, code, author=None, valid=False):
        """
        Add the specified event.

        Args:
            obj (Object): the Evennia typeclassed object to be modified.
            event_name (str): the name of the event to add.
            code (str): the Python code associated with this event.
            author (optional, Character, Player): the author of the event.
            valid (optional, bool): should the event be connected?

        This method doesn't check that the event type exists.

        """
        obj_events = self.db.events.get(obj, {})
        if not obj_events:
            self.db.events[obj] = {}
            obj_events = self.db.events[obj]

        events = obj_events.get(event_name, [])
        if not events:
            obj_events[event_name] = []
            events = obj_events[event_name]

        # Add the event in the list
        events.append({
                "created_on": datetime.now(),
                "author": author,
                "valid": valid,
                "code": code,
        })

        # If not valid, set it in 'to_valid'
        if not valid:
            self.db.to_valid.append((obj, event_name, len(events) - 1))

        # Build the definition to return (a dictionary)
        definition = dict(events[-1])
        definition["obj"] = obj
        definition["name"] = event_name
        definition["number"] = len(events) - 1
        return definition

    def edit_event(self, obj, event_name, number, code, author=None,
            valid=False):
        """
        Edit the specified event.

        Args:
            obj (Object): the Evennia typeclassed object to be modified.
            event_name (str): the name of the event to add.
            number (int): the event number to be changed.
            code (str): the Python code associated with this event.
            author (optional, Character, Player): the author of the event.
            valid (optional, bool): should the event be connected?

        This method doesn't check that the event type exists.

        """
        obj_events = self.db.events.get(obj, {})
        if not obj_events:
            self.db.events[obj] = {}
            obj_events = self.db.events[obj]

        events = obj_events.get(event_name, [])
        if not events:
            obj_events[event_name] = []
            events = obj_events[event_name]

        # Edit the event
        events[number].update({
                "updated_on": datetime.now(),
                "updated_by": author,
                "valid": valid,
                "code": code,
        })

        # If not valid, set it in 'to_valid'
        if not valid and (obj, event_name, number) not in self.db.to_valid:
            self.db.to_valid.append((obj, event_name, number))

    def accept_event(self, obj, event_name, number):
        """
        Valid an event.

        Args:
            obj (Object): the object containing the event.
            event_name (str): the name of the event.
            number (int): the number of the event.

        """
        obj_events = self.db.events.get(obj, {})
        events = obj_events.get(event_name, [])

        # Accept and connect the event
        events[number].update({"valid": True})
        if (obj, event_name, number) in self.db.to_valid:
            self.db.to_valid.remove((obj, event_name, number))

    def call_event(self, obj, event_name, *args):
        """
        Call the event.

        Args:
            obj (Object): the Evennia typeclassed object.
            event_name (str): the event name to call.
            *args: additional variables for this event.

        Returns:
            True to report the event was called without interruption,
            False otherwise.

        """
        # First, look for the event type corresponding to this name
        # To do so, go back the inheritance tree
        event_type = self.get_event_types(obj).get(event_name)
        if not event_type:
            logger.log_err("The event {} for the object {} (typeclass " \
                    "{}) can't be found".format(event_name, obj, type(obj)))
            return False

        # Prepare the locals
        locals = all_from_module("evennia.contrib.events.helpers")
        for i, variable in enumerate(event_type[0]):
            try:
                locals[variable] = args[i]
            except IndexError:
                logger.log_err("event {} of {} ({}): need variable " \
                        "{} in position {}".format(event_name, obj,
                        type(obj), variable, i))
                return False

        # Now execute all the valid events linked at this address
        events = self.db.events.get(obj, {}).get(event_name, [])
        for event in events:
            if not event["valid"]:
                continue

            try:
                exec(event["code"], locals, locals)
            except InterruptEvent:
                return False

        return True
