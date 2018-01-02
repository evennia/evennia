"""
Scripts for the aware contrib.
"""

from evennia import DefaultScript
from evennia.utils import utils
from evennia.contrib.aware.utils import Action, do_action

class AlreadyExists(Exception):
    pass

def make_storable_callback(callback, call_on=None):
    # TODO: Extend this definition to allow non-instance callbacks
    if callable(callback) and getattr(callback, "__self__", None):
        callback = (callback.__self__, callback.__name__)
    elif isinstance(callback, (str, unicode)):
        callback = (call_on, callback)
    return callback


class AwareStorage(DefaultScript):

    """
    Global script to store information regarding signals and actions.
    """
    
    instance = None

    def at_script_creation(self):
        self.key = "aware_storage"
        self.desc = "Aware storage global script"
        self.persistent = True

        # Persistent storage
        self.db.subscribers = {}
        self.db.actions = {}
        self.db.action_storage = {}
        self.db.unpacked_actions = []

    def at_start(self):
        self.ndb.traces = {}
        self.ndb.free_id = 1
        self.ndb.action_ids = []

        # Generate action IDs
        for obj, actions in self.db.actions.items():
            for action in actions:
                action_id = action.get("action_id")
                if action_id:
                    self.ndb.action_ids.append(action_id)
        
        if self.ndb.action_ids:
            self.free_id = max(self.ndb.action_ids) + 1

        # Load the awarefuncs
        addresses = ["evennia.contrib.aware.awarefuncs"]
        self.ndb.awarefuncs = {}
        for address in addresses:
            if utils.pypath_to_realpath(address):
                self.ndb.awarefuncs.update(utils.all_from_module(address))

        # Write in the `instance` class variable since it is started
        type(self).instance = self

    def add_subscriber(self, signal, obj, *args, **kwargs):
        """
        Add a new link between a signal, a subscriber (object) and an action.

        Args:
            signal (str): the signal, can use sub-categories.
            obj (Object): the object wanted to subscribe to this signal.
            action (str, optional): action, as a pre-configured awarefunc.
            callback (callable): callback to be called if the signal is thrown.
            Any (any): other keywords as needed.

        Notes:
            One can use the separator in order to specify signals with
            a hierarchy.  The default separator being ":", one could
            send the signal "sound:crying:child" for instance.

            Awarefuncs are pre-configured actions to perform simple
            and generic actions.  The best example is probably "cmd",
            which allows to have the object use a command.  The key
            of the action should be specified in the `action` keyword.

            Notice that actions and callbacks are exclusive: if a
            callback object is specified, then it will be used.  Otherwise,
            the action will be used.  The default action being "cmd",
            the default behavior would be to execute a command.

        """
        if "callback" in kwargs:
            callback = kwargs["callback"]
            if callback and callable(callback) and getattr(callback, "__self__", None):
                callback = (callback.__self__, callback.__name__)
                kwargs["callback"] = callback

        signature = {
                "args": args,
                "kwargs": kwargs,
        }
        if signal not in self.db.subscribers:
            self.db.subscribers[signal] = {}
        subscribers = self.db.subscribers[signal]
        if obj not in subscribers:
            subscribers[obj] = []
        signatures = subscribers[obj]
        if signature in signatures:
            raise AlreadyExists("{sub} is already subscribed to {signal} with that action/callback".format(sub=obj, signal=signal))
        else:
            signatures.append(signature)

        # Add the tag on the object
        if not obj.tags.get(signal, category="signal"):
            obj.tags.add(signal, category="signal")

        return True

    def remove_subscriber(self, signal, obj, action="cmd", callback=None, **kwargs):
        callback = make_storable_callback(callback, obj)
        signature = {
                "action": action,
                "callback": callback,
                "kwargs": kwargs,
        }
        if not signal in self.db.subscribers:
            return False
        
        subscribers = self.db.subscribers[signal]
        if obj not in subscribers:
            return False
        
        signatures = subscribers[obj]
        if signature in signatures:
            signatures.remove(signature)
        else:
            # Perhaps we should raise an error here?
            return False
        
        # Remove the tag if necessary
        if obj.tags.get(signal, category="signal"):
            obj.tags.remove(signal, category="signal")

        return True

    def add_action(self, signal, obj, *args, **kwargs):
        """
        Add an action to the objects' priority queue.

        Args:
            obj (Object): the object having to go for act.
            any (Any): any other positional arguments to send to the action.

        Kwargs:
            action (str, optional): the name of the generic awarefunc.
            callback (callback, optional): the specific callback.
            priority (int, optional): the priority of this action.
            delay (int, optional): delay in seconds before executing this action.

        Notes:
            The specified action will be added in the priority queue of
            actions for this object.  An action ID will be generated for
            this action.  Unless otherwise specified, the action will
            be called almost immediately (after a little pause to
            ensure actions don't collide with each other).
            
            The `priority` keyword will specify the order of actions.
            A higher priority will be first in the action queue.  If
            the priority isn't specified, a priority 0 is assumed.

        """
        action_id = self.ndb.free_id
        self.ndb.free_id += 1
        self.ndb.action_ids.append(action_id)

        # Extract the keyword arguments
        action = "cmd"
        if "aciton" in kwargs:
            action = kwargs.pop("action")

        callback = None
        if "callback" in kwargs:
            callback = kwargs.pop("callback")

        priority = 0
        if "priority" in kwargs:
            priority = kwargs.pop("priority")

        delay = 0
        if "delay" in kwargs:
            delay = kwargs.pop("delay")

        if obj not in self.db.actions:
            self.db.actions[obj] = []
        actions = self.db.actions[obj]

        action_indice = 0
        if "action_indice" in kwargs:
            action_indice = kwargs.pop("action_indice")
        else:
            # Determine the action_indice based on priority
            action_indice = -1
            for indice, description in enumerate(actions):
                if description.get("priority", 0) < priority:
                    action_indice = indice
                    break

        # Save the actions
        representation = {
                "action_id": action_id,
                "action": action,
                "callback": callback,
                "priority": priority,
                "delay": delay,
        }
        representation.update(kwargs)
        if action_indice < 0:
            actions.append(dict(action_id=action_id, priority=priority, delay=delay))
        else:
            actions.insert(action_indice, dict(action_id=action_id, priority=priority, delay=delay))

        # Store the arguments for this action
        kwargs = representation.copy()
        del kwargs["action_id"]
        self.db.unpacked_actions[action_id] = [list(args), kwargs]

        # Program the task to execute if high in priority
        if len(actions) == 1 or action_indice == 0:
            unpacked_signal = signal.kwargs.copy()
            unpacked_signal["name"] = signal.name
            unpacked_signal["local"] = signal.local
            unpacked_signal["from_obj"] = signal.from_obj
            unpacked_signal["location"] = signal.location
            unpacked_signal["propagation"] = signal.propagation
            unpacked_signal["toward"] = signal.toward
            unpacked_signal["backward"] = signal.backward
            utils.delay(delay, do_action, unpacked_signal, obj, action_id, persistent=True)

        return Action(*args, **representation)

