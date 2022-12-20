"""
Scripts for the in-game Python system.
"""

import re
import sys
import traceback
from datetime import datetime, timedelta
from queue import Queue

from django.conf import settings

from evennia import ChannelDB, DefaultObject, DefaultScript, ScriptDB, logger
from evennia.contrib.base_systems.ingame_python.callbackhandler import CallbackHandler
from evennia.contrib.base_systems.ingame_python.utils import (
    EVENTS,
    InterruptEvent,
    get_next_wait,
)
from evennia.utils.ansi import raw
from evennia.utils.create import create_channel
from evennia.utils.dbserialize import dbserialize
from evennia.utils.utils import all_from_module, delay, pypath_to_realpath

# Constants
RE_LINE_ERROR = re.compile(r'^  File "\<string\>", line (\d+)')


class EventHandler(DefaultScript):

    """
    The event handler that contains all events in a global script.

    This script shouldn't be created more than once.  It contains
    event (in a non-persistent attribute) and callbacks (in a
    persistent attribute).  The script method would help adding,
    editing and deleting these events and callbacks.

    """

    def at_script_creation(self):
        """Hook called when the script is created."""
        self.key = "event_handler"
        self.desc = "Global event handler"
        self.persistent = True

        # Permanent data to be stored
        self.db.callbacks = {}
        self.db.to_valid = []
        self.db.locked = []

        # Tasks
        self.db.tasks = {}
        self.at_server_start()

    def at_server_start(self):
        """Set up the event system when starting.

        Note that this hook is called every time the server restarts
        (including when it's reloaded).  This hook performs the following
        tasks:

        -   Create temporarily stored events.
        -   Generate locals (individual events' namespace).
        -   Load eventfuncs, including user-defined ones.
        -   Re-schedule tasks that aren't set to fire anymore.
        -   Effectively connect the handler to the main script.

        """
        self.ndb.events = {}
        for typeclass, name, variables, help_text, custom_call, custom_add in EVENTS:
            self.add_event(typeclass, name, variables, help_text, custom_call, custom_add)

        # Generate locals
        self.ndb.current_locals = {}
        self.ndb.fresh_locals = {}
        addresses = ["evennia.contrib.base_systems.ingame_python.eventfuncs"]
        addresses.extend(getattr(settings, "EVENTFUNCS_LOCATIONS", ["world.eventfuncs"]))
        for address in addresses:
            if pypath_to_realpath(address):
                self.ndb.fresh_locals.update(all_from_module(address))

        # Restart the delayed tasks
        now = datetime.now()
        for task_id, definition in tuple(self.db.tasks.items()):
            future, obj, event_name, locals = definition
            seconds = (future - now).total_seconds()
            if seconds < 0:
                seconds = 0

            delay(seconds, complete_task, task_id)

        # Place the script in the CallbackHandler
        from evennia.contrib.base_systems.ingame_python import typeclasses

        CallbackHandler.script = self
        DefaultObject.callbacks = typeclasses.EventObject.callbacks

        # Create the channel if non-existent
        try:
            self.ndb.channel = ChannelDB.objects.get(db_key="everror")
        except ChannelDB.DoesNotExist:
            self.ndb.channel = create_channel(
                "everror",
                desc="Event errors",
                locks="control:false();listen:perm(Builders);send:false()",
            )

    def get_events(self, obj):
        """
        Return a dictionary of events on this object.

        Args:
            obj (Object or typeclass): the connected object or a general typeclass.

        Returns:
            A dictionary of the object's events.

        Notes:
            Events would define what the object can have as
            callbacks.  Note, however, that chained callbacks will not
            appear in events and are handled separately.

            You can also request the events of a typeclass, not a
            connected object.  This is useful to get the global list
            of events for a typeclass that has no object yet.

        """
        events = {}
        all_events = self.ndb.events
        classes = Queue()
        if isinstance(obj, type):
            classes.put(obj)
        else:
            classes.put(type(obj))

        invalid = []
        while not classes.empty():
            typeclass = classes.get()
            typeclass_name = typeclass.__module__ + "." + typeclass.__name__
            for key, etype in all_events.get(typeclass_name, {}).items():
                if key in invalid:
                    continue
                if etype[0] is None:  # Invalidate
                    invalid.append(key)
                    continue
                if key not in events:
                    events[key] = etype

            # Look for the parent classes
            for parent in typeclass.__bases__:
                classes.put(parent)

        return events

    def get_variable(self, variable_name):
        """
        Return the variable defined in the locals.

        This can be very useful to check the value of a variable that can be modified in an event, and whose value will be used in code.  This system allows additional customization.

        Args:
            variable_name (str): the name of the variable to return.

        Returns:
            The variable if found in the locals.
            None if not found in the locals.

        Note:
            This will return the variable from the current locals.
            Keep in mind that locals are shared between events.  As
            every event is called one by one, this doesn't pose
            additional problems if you get the variable right after
            an event has been executed.  If, however, you differ,
            there's no guarantee the variable will be here or will
            mean the same thing.

        """
        return self.ndb.current_locals.get(variable_name)

    def get_callbacks(self, obj):
        """
        Return a dictionary of the object's callbacks.

        Args:
            obj (Object): the connected objects.

        Returns:
            A dictionary of the object's callbacks.

        Note:
            This method can be useful to override in some contexts,
            when several objects would share callbacks.

        """
        obj_callbacks = self.db.callbacks.get(obj, {})
        callbacks = {}
        for callback_name, callback_list in obj_callbacks.items():
            new_list = []
            for i, callback in enumerate(callback_list):
                callback = dict(callback)
                callback["obj"] = obj
                callback["name"] = callback_name
                callback["number"] = i
                new_list.append(callback)

            if new_list:
                callbacks[callback_name] = new_list

        return callbacks

    def add_callback(self, obj, callback_name, code, author=None, valid=False, parameters=""):
        """
        Add the specified callback.

        Args:
            obj (Object): the Evennia typeclassed object to be extended.
            callback_name (str): the name of the callback to add.
            code (str): the Python code associated with this callback.
            author (Character or Account, optional): the author of the callback.
            valid (bool, optional): should the callback be connected?
            parameters (str, optional): optional parameters.

        Note:
            This method doesn't check that the callback type exists.

        """
        obj_callbacks = self.db.callbacks.get(obj, {})
        if not obj_callbacks:
            self.db.callbacks[obj] = {}
            obj_callbacks = self.db.callbacks[obj]

        callbacks = obj_callbacks.get(callback_name, [])
        if not callbacks:
            obj_callbacks[callback_name] = []
            callbacks = obj_callbacks[callback_name]

        # Add the callback in the list
        callbacks.append(
            {
                "created_on": datetime.now(),
                "author": author,
                "valid": valid,
                "code": code,
                "parameters": parameters,
            }
        )

        # If not valid, set it in 'to_valid'
        if not valid:
            self.db.to_valid.append((obj, callback_name, len(callbacks) - 1))

        # Call the custom_add if needed
        custom_add = self.get_events(obj).get(callback_name, [None, None, None, None])[3]
        if custom_add:
            custom_add(obj, callback_name, len(callbacks) - 1, parameters)

        # Build the definition to return (a dictionary)
        definition = dict(callbacks[-1])
        definition["obj"] = obj
        definition["name"] = callback_name
        definition["number"] = len(callbacks) - 1
        return definition

    def edit_callback(self, obj, callback_name, number, code, author=None, valid=False):
        """
        Edit the specified callback.

        Args:
            obj (Object): the Evennia typeclassed object to be edited.
            callback_name (str): the name of the callback to edit.
            number (int): the callback number to be changed.
            code (str): the Python code associated with this callback.
            author (Character or Account, optional): the author of the callback.
            valid (bool, optional): should the callback be connected?

        Raises:
            RuntimeError if the callback is locked.

        Note:
            This method doesn't check that the callback type exists.

        """
        obj_callbacks = self.db.callbacks.get(obj, {})
        if not obj_callbacks:
            self.db.callbacks[obj] = {}
            obj_callbacks = self.db.callbacks[obj]

        callbacks = obj_callbacks.get(callback_name, [])
        if not callbacks:
            obj_callbacks[callback_name] = []
            callbacks = obj_callbacks[callback_name]

        # If locked, don't edit it
        if (obj, callback_name, number) in self.db.locked:
            raise RuntimeError("this callback is locked.")

        # Edit the callback
        callbacks[number].update(
            {"updated_on": datetime.now(), "updated_by": author, "valid": valid, "code": code}
        )

        # If not valid, set it in 'to_valid'
        if not valid and (obj, callback_name, number) not in self.db.to_valid:
            self.db.to_valid.append((obj, callback_name, number))
        elif valid and (obj, callback_name, number) in self.db.to_valid:
            self.db.to_valid.remove((obj, callback_name, number))

        # Build the definition to return (a dictionary)
        definition = dict(callbacks[number])
        definition["obj"] = obj
        definition["name"] = callback_name
        definition["number"] = number
        return definition

    def del_callback(self, obj, callback_name, number):
        """
        Delete the specified callback.

        Args:
            obj (Object): the typeclassed object containing the callback.
            callback_name (str): the name of the callback to delete.
            number (int): the number of the callback to delete.

        Raises:
            RuntimeError if the callback is locked.

        """
        obj_callbacks = self.db.callbacks.get(obj, {})
        callbacks = obj_callbacks.get(callback_name, [])

        # If locked, don't edit it
        if (obj, callback_name, number) in self.db.locked:
            raise RuntimeError("this callback is locked.")

        # Delete the callback itself
        try:
            code = callbacks[number]["code"]
        except IndexError:
            return
        else:
            logger.log_info(
                "Deleting callback {} {} of {}:\n{}".format(callback_name, number, obj, code)
            )
            del callbacks[number]

        # Change IDs of callbacks to be validated
        i = 0
        while i < len(self.db.to_valid):
            t_obj, t_callback_name, t_number = self.db.to_valid[i]
            if obj is t_obj and callback_name == t_callback_name:
                if t_number == number:
                    # Strictly equal, delete the callback
                    del self.db.to_valid[i]
                    i -= 1
                elif t_number > number:
                    # Change the ID for this callback
                    self.db.to_valid.insert(i, (t_obj, t_callback_name, t_number - 1))
                    del self.db.to_valid[i + 1]
            i += 1

        # Update locked callback
        for i, line in enumerate(self.db.locked):
            t_obj, t_callback_name, t_number = line
            if obj is t_obj and callback_name == t_callback_name:
                if number < t_number:
                    self.db.locked[i] = (t_obj, t_callback_name, t_number - 1)

        # Delete time-related callbacks associated with this object
        for script in obj.scripts.all():
            if isinstance(script, TimecallbackScript):
                if script.obj is obj and script.db.callback_name == callback_name:
                    if script.db.number == number:
                        script.stop()
                    elif script.db.number > number:
                        script.db.number -= 1

    def accept_callback(self, obj, callback_name, number):
        """
        Valid a callback.

        Args:
            obj (Object): the object containing the callback.
            callback_name (str): the name of the callback.
            number (int): the number of the callback.

        """
        obj_callbacks = self.db.callbacks.get(obj, {})
        callbacks = obj_callbacks.get(callback_name, [])

        # Accept and connect the callback
        callbacks[number].update({"valid": True})
        if (obj, callback_name, number) in self.db.to_valid:
            self.db.to_valid.remove((obj, callback_name, number))

    def call(self, obj, callback_name, *args, **kwargs):
        """
        Call the connected callbacks.

        Args:
            obj (Object): the Evennia typeclassed object.
            callback_name (str): the callback name to call.
            *args: additional variables for this callback.

        Keyword Args:
            number (int, optional): call just a specific callback.
            parameters (str, optional): call a callback with parameters.
            locals (dict, optional): a locals replacement.

        Returns:
            True to report the callback was called without interruption,
            False otherwise.

        """
        # First, look for the callback type corresponding to this name
        number = kwargs.get("number")
        parameters = kwargs.get("parameters")
        locals = kwargs.get("locals")

        # Errors should not pass silently
        allowed = ("number", "parameters", "locals")
        if any(k for k in kwargs if k not in allowed):
            raise TypeError(
                "Unknown keyword arguments were specified " "to call callbacks: {}".format(kwargs)
            )

        event = self.get_events(obj).get(callback_name)
        if locals is None and not event:
            logger.log_err(
                "The callback {} for the object {} (typeclass "
                "{}) can't be found".format(callback_name, obj, type(obj))
            )
            return False

        # Prepare the locals if necessary
        if locals is None:
            locals = self.ndb.fresh_locals.copy()
            for i, variable in enumerate(event[0]):
                try:
                    locals[variable] = args[i]
                except IndexError:
                    logger.log_trace(
                        "callback {} of {} ({}): need variable "
                        "{} in position {}".format(callback_name, obj, type(obj), variable, i)
                    )
                    return False
        else:
            locals = {key: value for key, value in locals.items()}

        callbacks = self.get_callbacks(obj).get(callback_name, [])
        if event:
            custom_call = event[2]
            if custom_call:
                callbacks = custom_call(callbacks, parameters)

        # Now execute all the valid callbacks linked at this address
        self.ndb.current_locals = locals
        for i, callback in enumerate(callbacks):
            if not callback["valid"]:
                continue

            if number is not None and callback["number"] != number:
                continue

            try:
                exec(callback["code"], locals, locals)
            except InterruptEvent:
                return False
            except Exception:
                etype, evalue, tb = sys.exc_info()
                trace = traceback.format_exception(etype, evalue, tb)
                self.handle_error(callback, trace)

        return True

    def handle_error(self, callback, trace):
        """
        Handle an error in a callback.

        Args:
            callback (dict): the callback representation.
            trace (list): the traceback containing the exception.

        Notes:
            This method can be useful to override to change the default
            handling of errors.  By default, the error message is sent to
            the character who last updated the callback, if connected.
            If not, display to the everror channel.

        """
        callback_name = callback["name"]
        number = callback["number"]
        obj = callback["obj"]
        oid = obj.id
        logger.log_err(
            "An error occurred during the callback {} of "
            "{} (#{}), number {}\n{}".format(callback_name, obj, oid, number + 1, "\n".join(trace))
        )

        # Create the error message
        line = "|runknown|n"
        lineno = "|runknown|n"
        for error in trace:
            if error.startswith('  File "<string>", line '):
                res = RE_LINE_ERROR.search(error)
                if res:
                    lineno = int(res.group(1))

                    # Try to extract the line
                    try:
                        line = raw(callback["code"].splitlines()[lineno - 1])
                    except IndexError:
                        continue
                    else:
                        break

        exc = raw(trace[-1].strip("\n").splitlines()[-1])
        err_msg = "Error in {} of {} (#{})[{}], line {}:" " {}\n{}".format(
            callback_name, obj, oid, number + 1, lineno, line, exc
        )

        # Inform the last updater if connected
        updater = callback.get("updated_by")
        if updater is None:
            updater = callback["created_by"]

        if updater and updater.sessions.all():
            updater.msg(err_msg)
        else:
            err_msg = "Error in {} of {} (#{})[{}], line {}:" " {}\n          {}".format(
                callback_name, obj, oid, number + 1, lineno, line, exc
            )
            self.ndb.channel.msg(err_msg)

    def add_event(self, typeclass, name, variables, help_text, custom_call, custom_add):
        """
        Add a new event for a defined typeclass.

        Args:
            typeclass (str): the path leading to the typeclass.
            name (str): the name of the event to add.
            variables (list of str): list of variable names for this event.
            help_text (str): the long help text of the event.
            custom_call (callable or None): the function to be called
                    when the event fires.
            custom_add (callable or None): the function to be called when
                    a callback is added.

        """
        if typeclass not in self.ndb.events:
            self.ndb.events[typeclass] = {}

        events = self.ndb.events[typeclass]
        if name not in events:
            events[name] = (variables, help_text, custom_call, custom_add)

    def set_task(self, seconds, obj, callback_name):
        """
        Set and schedule a task to run.

        Args:
            seconds (int, float): the delay in seconds from now.
            obj (Object): the typecalssed object connected to the event.
            callback_name (str): the callback's name.

        Notes:
            This method allows to schedule a "persistent" task.
            'utils.delay' is called, but a copy of the task is kept in
            the event handler, and when the script restarts (after reload),
            the differed delay is called again.
            The dictionary of locals is frozen and will be available
            again when the task runs.  This feature, however, is limited
            by the database: all data cannot be saved.  Lambda functions,
            class methods, objects inside an instance and so on will
            not be kept in the locals dictionary.

        """
        now = datetime.now()
        delta = timedelta(seconds=seconds)

        # Choose a free task_id
        used_ids = list(self.db.tasks.keys())
        task_id = 1
        while task_id in used_ids:
            task_id += 1

        # Collect and freeze current locals
        locals = {}
        for key, value in self.ndb.current_locals.items():
            try:
                dbserialize(value)
            except TypeError:
                continue
            else:
                locals[key] = value

        self.db.tasks[task_id] = (now + delta, obj, callback_name, locals)
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
        """
        Call the event and reset interval.

        It is necessary to restart the script to reset its interval
        only twice after a reload.  When the script has undergone
        down time, there's usually a slight shift in game time.  Once
        the script restarts once, it will set the average time it
        needs for all its future intervals and should not need to be
        restarted.  In short, a script that is created shouldn't need
        to restart more than once, and a script that is reloaded should
        restart only twice.

        """
        if self.db.time_format:
            # If the 'usual' time is set, use it
            seconds = self.ndb.usual
            if seconds is None:
                seconds, usual, details = get_next_wait(self.db.time_format)
                self.ndb.usual = usual

            if self.interval != seconds:
                self.restart(interval=seconds)

        if self.db.event_name and self.db.number is not None:
            obj = self.obj
            if not obj.callbacks:
                return

            event_name = self.db.event_name
            number = self.db.number
            obj.callbacks.call(event_name, obj, number=number)


# Functions to manipulate tasks
def complete_task(task_id):
    """
    Mark the task in the event handler as complete.

    Args:
        task_id (int): the task ID.

    Note:
        This function should be called automatically for individual tasks.

    """
    try:
        script = ScriptDB.objects.get(db_key="event_handler")
    except ScriptDB.DoesNotExist:
        logger.log_trace("Can't get the event handler.")
        return

    if task_id not in script.db.tasks:
        logger.log_err("The task #{} was scheduled, but it cannot be " "found".format(task_id))
        return

    delta, obj, callback_name, locals = script.db.tasks.pop(task_id)
    script.call(obj, callback_name, locals=locals)
