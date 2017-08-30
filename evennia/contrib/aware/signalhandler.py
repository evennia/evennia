"""
`SignalHandler` and `Signal` classes.

The `SignalHandler`, available through `obj.signals`  once installed, can be used to:

- Throw signals.
- Subscribe to signals.

"""

from evennia import ObjectDB, ScriptDB
from evennia.utils.create import create_script
from evennia.utils import delay
from evennia.contrib.aware.scripts import AwareStorage
from evennia.contrib.aware.utils import Signal

class SignalHandler(object):

    """
    SignalHandler accessible through `obj.signals`.
    """

    def __init__(self, obj):
        self.obj = obj

    def subscribe(self, signal, *args, **kwargs):
        """Add subscriber to script - raises scripts.AlreadyExists"""
        script = AwareStorage.instance
        if script is None:
            return False

        return script.add_subscriber(signal, self.obj, *args, **kwargs)

    def unsubscribe(self, signal, action="cmd", callback=None, **kwargs):
        script = AwareStorage.instance
        if script is None:
            return False

        return script.remove_subscriber(signal, self.obj, action, callback, **kwargs)

    def throw(self, signal, **kwargs):
        script = AwareStorage.instance
        if script is None:
            return False

        if "from_obj" not in kwargs:
            kwargs["from_obj"] = self.obj
        if "location" not in kwargs:
            kwargs["location"] = self.obj
        signal = Signal(signal, **kwargs)
        signal.throw(script)

