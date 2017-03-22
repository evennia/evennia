"""
Scripts for the event system.
"""

from datetime import datetime, timedelta
from Queue import Queue

from django.conf import settings
from evennia import DefaultObject, DefaultScript, ScriptDB
from evennia import logger
from evennia.utils.dbserialize import dbserialize
from evennia.utils.utils import all_from_module, delay
from evennia.contrib.events.custom import (
        connect_event_types, get_next_wait, patch_hooks)
from evennia.contrib.events.exceptions import InterruptEvent
from evennia.contrib.events.handler import EventsHandler as Handler
from evennia.contrib.events import typeclasses

class EventHandler(DefaultScript):

    """
    The event handler that contains all events in a global script.

    This script shouldn't be created more than once.  It contains
    event types (in a non-persistent attribute) and events (in a
    persistent attribute).  The script method would help adding,
    editing and deleting these events.

    """

    def at_script_creation(self):
        self.key = "event_handler"
        self.desc = "Global event handler"
        self.persistent = True

        # Permanent data to be stored
        self.db.events = {}
        self.db.to_valid = []
        self.db.locked = []

        # Tasks
        self.db.task_id = 0
        self.db.tasks = {}

    def at_start(self):
        """Set up the event system."""
        self.ndb.event_types = {}
        connect_event_types()
        patch_hooks()

        # Generate locals
        self.ndb.current_locals = {}
        self.ndb.fresh_locals = {}
        addresses = ["evennia.contrib.events.helpers"]
        addresses.extend(getattr(settings, "EVENTS_HELPERS_LOCATIONS", []))
        for address in addresses:
            self.ndb.fresh_locals.update(all_from_module(address))

        # Restart the delayed tasks
        now = datetime.now()
        for task_id, definition in tuple(self.db.tasks.items()):
            future, obj, event_name, locals = definition
            seconds = (future - now).total_seconds()
            if seconds < 0:
                seconds = 0

            delay(seconds, complete_task, task_id)

        # Place the script in the EventsHandler
        Handler.script = self
        DefaultObject.events = typeclasses.PatchedObject.events

    def get_events(self, obj):
        """
        Return a dictionary of the object's events.

        Args:
            obj (Object): the connected objects.

        Returns:
            A dictionary of the object's events.

        Note:
            This method can be useful to override in some contexts,
            when several objects would share events.

        """
        obj_events = self.db.events.get(obj, {})
        events = {}
        for event_name, event_list in obj_events.items():
            new_list = []
            for i, event in enumerate(event_list):
                event = dict(event)
                event["obj"] = obj
                event["name"] = event_name
                event["number"] = i
                new_list.append(event)

            if new_list:
                events[event_name] = new_list

        return events

    def get_event_types(self, obj):
        """
        Return a dictionary of event types on this object.

        Args:
            obj (Object): the connected object.

        Returns:
            A dictionary of the object's event types.

        Note:
            Event types would define what the object can have as
            events.  Note, however, that chained events will not
            appear in event types and are handled separately.

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

    def add_event(self, obj, event_name, code, author=None, valid=False,
            parameters=""):
        """
        Add the specified event.

        Args:
            obj (Object): the Evennia typeclassed object to be extended.
            event_name (str): the name of the event to add.
            code (str): the Python code associated with this event.
            author (Character or Player, optional): the author of the event.
            valid (bool, optional): should the event be connected?
            parameters (str, optional): optional parameters.

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
                "parameters": parameters,
        })

        # If not valid, set it in 'to_valid'
        if not valid:
            self.db.to_valid.append((obj, event_name, len(events) - 1))

        # Call the custom_add if needed
        custom_add = self.get_event_types(obj).get(
                event_name, [None, None, None])[2]
        if custom_add:
            custom_add(obj, event_name, len(events) - 1, parameters)

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
            obj (Object): the Evennia typeclassed object to be edited.
            event_name (str): the name of the event to edit.
            number (int): the event number to be changed.
            code (str): the Python code associated with this event.
            author (Character or Player, optional): the author of the event.
            valid (bool, optional): should the event be connected?

        Raises:
            RuntimeError if the event is locked.

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

        # If locked, don't edit it
        if (obj, event_name, number) in self.db.locked:
            raise RuntimeError("this event is locked.")

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
        elif valid and (obj, event_name, number) in self.db.to_valid:
            self.db.to_valid.remove((obj, event_name, number))

        # Build the definition to return (a dictionary)
        definition = dict(events[number])
        definition["obj"] = obj
        definition["name"] = event_name
        definition["number"] = number
        return definition

    def del_event(self, obj, event_name, number):
        """
        Delete the specified event.

        Args:
            obj (Object): the typeclassed object containing the event.
            event_name (str): the name of the event to delete.
            number (int): the number of the event to delete.

        Raises:
            RuntimeError if the event is locked.

        """
        obj_events = self.db.events.get(obj, {})
        events = obj_events.get(event_name, [])

        # If locked, don't edit it
        if (obj, event_name, number) in self.db.locked:
            raise RuntimeError("this event is locked.")

        # Delete the event itself
        try:
            code = events[number]["code"]
        except IndexError:
            return
        else:
            logger.log_info("Deleting event {} {} of {}:\n{}".format(
                    event_name, number, obj, code))
            del events[number]

        # Change IDs of events to be validated
        i = 0
        while i < len(self.db.to_valid):
            t_obj, t_event_name, t_number = self.db.to_valid[i]
            if obj is t_obj and event_name == t_event_name:
                if t_number == number:
                    # Strictly equal, delete the event
                    del self.db.to_valid[i]
                    i -= 1
                elif t_number > number:
                    # Change the ID for this event
                    self.db.to_valid.insert(i, (t_obj, t_event_name,
                            t_number - 1))
                    del self.db.to_valid[i + 1]
            i += 1

        # Update locked event
        for i, line in enumerate(self.db.locked):
            t_obj, t_event_name, t_number = line
            if obj is t_obj and event_name == t_event_name:
                if number < t_number:
                    self.db.locked[i] = (t_obj, t_event_name, t_number - 1)

        # Delete time-related events associated with this object
        for script in list(obj.scripts.all()):
            if isinstance(script, TimeEventScript):
                if script.obj is obj and script.db.event_name == event_name:
                    if script.db.number == number:
                        script.stop()
                    elif script.db.number > number:
                        script.db.number -= 1

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

    def call_event(self, obj, event_name, *args, **kwargs):
        """
        Call the event.

        Args:
            obj (Object): the Evennia typeclassed object.
            event_name (str): the event name to call.
            *args: additional variables for this event.

        Kwargs:
            number (int, optional): call just a specific event.
            parameters (str, optional): call an event with parameters.
            locals (dict, optional): a locals replacement.

        Returns:
            True to report the event was called without interruption,
            False otherwise.

        """
        # First, look for the event type corresponding to this name
        number = kwargs.get("number")
        parameters = kwargs.get("parameters")
        locals = kwargs.get("locals")

        # Errors should not pass silently
        allowed = ("number", "parameters", "locals")
        if any(k for k in kwargs if k not in allowed):
            raise TypeError("Unknown keyword arguments were specified " \
                    "to call events: {}".format(kwargs))

        event_type = self.get_event_types(obj).get(event_name)
        if locals is None and not event_type:
            logger.log_err("The event {} for the object {} (typeclass " \
                    "{}) can't be found".format(event_name, obj, type(obj)))
            return False

        # Prepare the locals if necessary
        if locals is None:
            locals = self.ndb.fresh_locals.copy()
            for i, variable in enumerate(event_type[0]):
                try:
                    locals[variable] = args[i]
                except IndexError:
                    logger.log_trace("event {} of {} ({}): need variable " \
                            "{} in position {}".format(event_name, obj,
                            type(obj), variable, i))
                    return False
        else:
            locals = {key: value for key, value in locals.items()}

        events = self.db.events.get(obj, {}).get(event_name, [])

        # Filter down of events if there is a custom call
        if event_type:
            custom_call = event_type[3]
            if custom_call:
                events = custom_call(events, parameters)

        # Now execute all the valid events linked at this address
        self.ndb.current_locals = locals
        for i, event in enumerate(events):
            if not event["valid"]:
                continue

            if number is not None and i != number:
                continue

            try:
                exec(event["code"], locals, locals)
            except InterruptEvent:
                return False

        return True

    def set_task(self, seconds, obj, event_name):
        """
        Set and schedule a task to run.

        This method allows to schedule a "persistent" task.
        'utils.delay' is called, but a copy of the task is kept in
        the event handler, and when the script restarts (after reload),
        the differed delay is called again.

        Args:
            seconds (int, float): the delay in seconds from now.
            obj (Object): the typecalssed object connected to the event.
            event_name (str): the event's name.

        Note:
            The dictionary of locals is frozen and will be available
            again when the task runs.  This feature, however, is limited
            by the database: all data cannot be saved.  Lambda functions,
            class methods, objects inside an instance and so on will
            not be kept in the locals dictionary.

        """
        now = datetime.now()
        delta = timedelta(seconds=seconds)
        task_id = self.db.task_id
        self.db.task_id += 1

        # Collect and freeze current locals
        locals = {}
        for key, value in self.ndb.current_locals.items():
            try:
                dbserialize(value)
            except TypeError:
                continue
            else:
                locals[key] = value

        self.db.tasks[task_id] = (now + delta, obj, event_name, locals)
        delay(seconds, complete_task, task_id)


# Script to call time-related events
class TimeEventScript(DefaultScript):

    """Gametime-sensitive script."""

    def at_script_creation(self):
        """The script is created."""
        self.start_delay = True
        self.persistent = True

        # Script attributes
        self.db.time_format = None
        self.db.event_name = "time"
        self.db.number = None

    def at_repeat(self):
        """Call the event and reset interval."""
        # Get the event handler and call the script
        try:
            script = ScriptDB.objects.get(db_key="event_handler")
        except ScriptDB.DoesNotExist:
            logger.log_trace("Can't get the event handler.")
            return

        if self.db.event_name and self.db.number is not None:
            obj = self.obj
            event_name = self.db.event_name
            number = self.db.number
            events = script.db.events.get(obj, {}).get(event_name)
            if events is None:
                logger.log_err("Cannot find the event {} on {}".format(
                        event_name, obj))
                return

            try:
                event = events[number]
            except IndexError:
                logger.log_err("Cannot find the event {} {} on {}".format(
                        event_name, number, obj))
                return

            script.call_event(obj, event_name, obj, number=number)

        if self.db.time_format:
            seconds, details = get_next_wait(self.db.time_format)
            self.restart(interval=seconds)


# Functions to manipulate tasks
def complete_task(task_id):
    """
    Mark the task in the event handler as complete.

    This function should be called automatically for individual tasks.

    Args:
        task_id (int): the task ID.

    """
    try:
        script = ScriptDB.objects.get(db_key="event_handler")
    except ScriptDB.DoesNotExist:
        logger.log_trace("Can't get the event handler.")
        return

    if task_id not in script.db.tasks:
        logger.log_err("The task #{} was scheduled, but it cannot be " \
                "found".format(task_id))
        return

    delta, obj, event_name, locals = script.db.tasks.pop(task_id)
    script.call_event(obj, event_name, locals=locals)
