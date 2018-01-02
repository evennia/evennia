"""
Mixins for the aware contrib.  Add one of these to your inheritance tree
on your typeclasses:

- `AwareMixin`: give access to the signal handler and aciton handler.
- `SignalsMixin`: give access to the signal handler only.
- `ActionsMixin`: gives access to the action handler only.

"""

from evennia.utils.utils import lazy_property
from evennia.contrib.aware.actionhandler import ActionHandler
from evennia.contrib.aware.signalhandler import SignalHandler

class ActionsMixin(object):

    """
    Mixin to add the action handler in `obj.actions`.
    """

    @lazy_property
    def actions(self):
        """Return te ActionHandler."""
        return ActionHandler(self)


class SignalsMixin(object):

    """
    Mixin to add the signal handler in `obj.signals`.
    """

    @lazy_property
    def signals(self):
        """Return te SignalHandler."""
        return SignalHandler(self)


class AwareMixin(ActionsMixin, SignalsMixin):

    """
    Mixin with both action and signal handler.
    """

    pass

