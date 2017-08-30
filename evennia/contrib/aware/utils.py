"""
Module containing generic utilities for the aware contrib.
"""

from Queue import Queue

from evennia import ObjectDB
from evennia.utils.create import create_script
from evennia.utils.logger import log_err, log_trace
from evennia.utils import utils


# Constants
SCRIPT = None
_SIGNAL_SEPARATOR = ":"

# Classes
class Action(object):

    """Class to represent an action.

    An action is to connect an object and a signal.  This class will
    determine what the object should do if this signal is thrown.
    Basic actions are just commands, that could be demonstrated as:
    "If you receive the signal 'enemy', attack it."  More complex
    actions can be defined through custom awarefuncs (see below) or callbackss.

    """

    def __init__(self, *args, **kwargs):
        self.action_id = None
        self.action = "cmd"
        self.callback = None
        self.priority = 0
        self.delay = 0

        # Extract arguments for kwargs
        if "action_id" in kwargs:
            self.action_id = kwargs.pop("action_id")

        if "action" in kwargs:
            self.action = kwargs.pop("action")

        if "callback" in kwargs:
            self.callback = kwargs.pop("callback")

        if "priority" in kwargs:
            self.priority = kwargs.pop("priority")
        
        if "delay" in kwargs:
            self.delay = kwargs.pop("delay")

        self.args = args
        self.kwargs = kwargs

    def __repr__(self):
        return "<Action {}>".format(self.name)

    @property
    def name(self):
        """Return a prettier name for the action."""
        args = ", ".join(str(arg) for arg in self.args)
        kwargs = tuple(sorted(self.kwargs.items()))
        kwargs = (("priority", self.priority), ("delay", self.delay)) + kwargs
        kwargs = ", ".join(["{}={}".format(key, value) for key, value in kwargs])
        msg = "{}".format(self.action_id)
        if self.callback:
            msg += "with callback {}".format(self.callback)
        else:
            msg += self.action

        msg += " ("
        if args:
            msg += args
            if kwargs:
                msg += ", "
        
        msg += kwargs + ")"
        return msg


class Signal(object):

    """
    A signal.

    Signals are created when they are thrown.  They possess a name
    with optional sub-categories using the defined separator.
    They also have keywords (given as keyword
    arguments during creation).

    """

    def __init__(self, name, **kwargs):
        self.name = name
        self.local = kwargs.get("local", True)
        self.from_obj = kwargs.get("from_obj")
        self.location = kwargs.get("location", self.from_obj)
        self.propagation = kwargs.get("propagation", 0)
        self.toward = kwargs.get("toward")
        self.backward = kwargs.get("backward")
        self.kwargs = kwargs

    def __repr__(self):
        kwargs = ", ".join(["{}={}".format(arg, value) for arg, value in self.kwargs.items()])
        return "<Signal {} ({})>".format(self.name, kwargs)

    def throw(self, script):
        """Throw the signal, replacing keyword arguments."""
        trace = [{"source": self.__dict__.copy()}]
        script.ndb.traces[self.name] = trace
      
        # If a local signal, get the possible locations
        if self.local:
            graph = Queue()
            visited = [self.location]
            locations = {self.location: (0, None)}
            graph.put((0, self.location))
            path_toward = {}
            path_backward = {}
            while not graph.empty():
                distance, location = graph.get()
                if distance > self.propagation:
                    continue

                trace.append({"explore": {"location": location, "distance": distance}})
                for exit in ObjectDB.objects.filter(db_destination__isnull=False).filter(
                            db_location=location):
                    destination = exit.destination
                    if destination in visited:
                        continue

                    visited.append(destination)
                    return_exits = ObjectDB.objects.filter(db_location=destination, db_destination=location)
                    return_exit = return_exits[0] if return_exits else None
                    graph.put((distance + 1, destination))
                    locations[destination] = (distance + 1, return_exit)

                    # Resume the list of exits toward the signal and away from it
                    toward = path_toward.get((location, self.location), {}).copy()
                    toward[destination] = return_exit
                    path_toward[(destination, self.location)] = toward
                    backward = path_backward.get((self.location, location), {}).copy()
                    backward[location] = exit
                    path_backward[(self.location, destination)] = backward

            # We now have a list of locations with distance and exit
            # Get the objects with the signal name as tag
            subscribed = ObjectDB.objects.filter(db_location__in=visited,
                    db_tags__db_key=self.name, db_tags__db_category="signal")

            # Browse the list of objects and send them the signal
            # Sort by distance from location
            subscribed = sorted(subscribed, key=lambda obj: locations[obj.location][0])
            for obj in subscribed:
                location = obj.location
                distance, exit = locations[location]

                toward = path_toward.get((location, self.location), {})
                backward = path_backward.get((self.location, location), {})
                self.distance = distance
                self.toward = toward
                self.backward = backward
                trace.append({"throw": {"obj": obj, "distance": distance, "toward": toward, "backward": backward}})

                # Get the list of actions to which this object is subscribed for this signal
                actions = script.db.subscribers.get(self.name, {}).get(obj, [])
                for action in actions:
                    args = action.get("args", ())
                    kwargs = action.get("kwargs", {})
                    if hasattr(obj, "actions"):
                        obj.actions.add(self, *args, **kwargs)

# Functions
def _get_script():
    """ Return the script and put it in the SCRIPT variable.
    
    Note:
    \
        This function will create the script if it can't be found.  If
        this function is called before the scripts are retrieved and
        started by Evennia, it means that this script could be created
        and you would end up with two copies of the `AwareStorage` script.
        Be sure to only call this function when you know Evennia has
        already started, loaded its scripts, and started them.

    """
    global SCRIPT
    if SCRIPT is not None:
        return SCRIPT

    AwareStorage = utils.class_from_module("evennia.contrib.aware.scripts.AwareStorage")
    SCRIPT = AwareStorage.instance

    # If SCRIPT is still None, create the script
    if SCRIPT is None:
        SCRIPT = create_script("evennia.contrib.aware.scripts.AwareStorage")

    return SCRIPT

def do_action(signal, obj, action_id):
    """Execute the specified action if appropriate.

    Note:
        This function will be called automatically by the `ActionHandler`
        when creating actions with or without delay.  It's not advised
        to call this function directly.  The action will be run if
        it is the top-most action of this object in terms of priority.
        Otherwise, it won't execute.

    """
    script = _get_script()
    args, kwargs = script.db.unpacked_actions.get(action_id, (None, None))
    args = list(args)
    kwargs = dict(kwargs)
    if args is None:
        log_err("The action ID]{} for obj={} cannot be found".format(action_id, obj))
        return

    # Check if this action is still higher n priority for this object
    actions = script.db.actions.get(obj, [])
    if actions and actions[0].get("action_id") == action_id:
        action = kwargs.get("action")
        callback = kwargs.get("calblack")
        if isinstance(callback, tuple):
            callback = getattr(callback[0], callback[1])
        
        if action is None and callback is None:
            log_err("Action of ID={} for obj={} has neither action nor callback".format(action_id, obj))
            return
        elif action:
            callback = script.ndb.awarefuncs[action]
        
        # Create the signal and storage
        signal = Signal(**signal)
        if action_id not in script.db.action_storage:
            script.db.action_storage[action_id] = []
        storage = script.db.action_storage

        # Remove action and callback from kwargs
        if "action" in kwargs:
            del kwargs["action"]
        if "callback" in kwargs:
            del kwargs["callback"]
        if "delay" in kwargs:
            del kwargs["delay"]
        if "priority" in kwargs:
            del kwargs["priority"]

        # Execute either the action or callback
        try:
            result = callback(obj, signal, storage, *args, **kwargs)
        except Exception as e:
            log_trace("An error occurred when execution action ID={} for obj={}".format(action_id, obj))
            terminate_action(obj, action_id)
        else:
            # Depending on the result, schedule the same action or the next to execute
            delay = 0
            next_action_id = None
            if isinstance(result, bool) and result:
                # Try to find the next action
                terminate_action(obj, action_id)
                if script.db.actions.get(obj):
                    next_action = script.db.actions[obj][0]
                    next_action_id = next_action["action_id"]
                    delay = next_action.get("delay", 0)
            elif isinstance(result, (int, float)):
                # If result is a number, schedule the same action to run in `result` seconds
                delay = result
                next_action_id = action_id
            else:
                next_action_id = action_id
                delay = 0
            
            # Schedule the next action
            if next_action_id is not None:
                utils.delay(delay, do_action, signal.__dict__.copy(), obj, next_action_id, persistent=True)

def terminate_action(obj, action_id):
    """Erase this action, removing it from the script."""
    script = _get_script()
    if action_id in script.ndb.action_ids:
        script.ndb.action_ids.remove(action_id)
    if action_id in script.db.unpacked_actions:
        del script.db.unpacked_actions[action_id]
    if action_id in script.db.action_storage:
        del script.db.action_storage[action_id]
    if obj in script.db.actions:
        script.db.actions[obj][:] = [action for action in script.db.actions[obj] if action.get("action_id") != action_id]
        if not script.db.actions[obj]:
            del script.db.actions[obj]

