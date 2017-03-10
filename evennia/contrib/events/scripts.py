"""
Scripts for the event system.
"""

from datetime import datetime
from Queue import Queue

from evennia import DefaultScript
from evennia import logger
from evennia.contrib.events.extend import patch_hooks
from evennia.contrib.events import typeclasses

class EventHandler(DefaultScript):

    """Event handler that contains all events in a global script."""

    def at_script_creation(self):
        self.key = "event_handler"
        self.desc = "Global event handler"
        self.persistent = True

        # Permanent data to be stored
        self.db.event_types = {}
        self.db.events = {}

    def at_start(self):
        """Set up the event system."""
        patch_hooks()

    def add_event(self, obj, event_name, code, author=None, valid=True):
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
        event_type = None
        event_types = self.db.event_types
        classes = Queue()
        classes.put(type(obj))
        while not classes.empty():
            typeclass = classes.get()
            typeclass_name = typeclass.__module__ + "." + typeclass.__name__
            event_type = event_types.get(typeclass_name, {}).get(event_name)
            if event_type:
                break
            else:
                # Look for the parent classes
                for parent in typeclass.__bases__:
                    classes.put(parent)

        # If there is still no event_type
        if not event_type:
            logger.log_err("The event {} for the object {} (typeclass " \
                    "{}) can't be found".format(event_name, obj, type(obj)))
            return False

        # Prepare the locals
        locals = {}
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

            exec(event["code"], locals, locals)
