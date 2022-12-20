"""
States represent the sequence of states the room goes through.

This module includes the BaseState class and the StateHandler
for managing states on the room.

The state handler operates on an Evscaperoom and changes
its state from one to another.

A given state is given as a module in states/ package. The
state is identified by its module name.

"""

from functools import wraps

from django.conf import settings

from evennia import logger, utils

from .objects import EvscaperoomObject
from .utils import create_evscaperoom_object, msg_cinematic, parse_for_things

# state setup
if hasattr(settings, "EVSCAPEROOM_STATE_PACKAGE"):
    _ROOMSTATE_PACKAGE = settings.EVSCAPEROOM_STATE_PACKAGE
else:
    _ROOMSTATE_PACKAGE = "evennia.contrib.full_systems.evscaperoom.states"
if hasattr(settings, "EVSCAPEROOM_START_STATE"):
    _FIRST_STATE = settings.EVSCAPEROOM_START_STATE
else:
    _FIRST_STATE = "state_001_start"

_GA = object.__getattribute__


# handler for managing states on room


class StateHandler(object):
    """
    This sits on the room and is used to progress through the states.

    """

    def __init__(self, room):
        self.room = room
        self.current_state_name = room.db.state or _FIRST_STATE
        self.prev_state_name = room.db.prev_state
        self.current_state = None
        self.current_state = self.load_state(self.current_state_name)

    def load_state(self, statename):
        """
        Load state without initializing it
        """
        try:
            mod = utils.mod_import(f"{_ROOMSTATE_PACKAGE}.{statename}")
        except Exception as err:
            logger.log_trace()
            self.room.msg_room(None, f"|rBUG: Could not load state {statename}: {err}!")
            self.room.msg_room(None, f"|rBUG: Falling back to {self.current_state_name}")
            return

        state = mod.State(self, self.room)
        return state

    def init_state(self):
        """
        Initialize a new state

        """
        self.current_state.init()

    def next_state(self, next_state=None):
        """
        Check if the current state is finished. This should be called whenever
        the players do actions that may affect the state of the room.

        Args:
            next_state (str, optional): If given, override the next_state given
                by the current state's check() method with this - this allows
                for branching paths (but the current state must still first agree
                that the check passes).

        Returns:
            state_changed (bool): True if the state changed, False otherwise.

        """
        # allows the state to enforce/customize what the next state should be
        next_state_name = self.current_state.next(next_state)
        if next_state_name:
            # we are ready to move on!

            next_state = self.load_state(next_state_name)
            if not next_state:
                raise RuntimeError(f"Could not load new state {next_state_name}!")

            self.prev_state_name = self.current_state_name
            self.current_state_name = next_state_name
            self.current_state.clean()
            self.prev_state = self.current_state
            self.current_state = next_state

            self.init_state()

            self.room.db.prev_state = self.prev_state_name
            self.room.db.state = self.current_state_name
            return True
        return False


# base state class


class BaseState(object):
    """
    Base object holding all callables for a state. This is here to
    allow easy overriding for child states.

    """

    next_state = "unset"
    # a sequence of hints to describe this state.
    hints = []

    def __init__(self, handler, room):
        """
        Initializer.

        Args:
            room (EvscapeRoom): The room tied to this state.
            handler (StateHandler): Back-reference to the handler
                storing this state.
        """
        self.handler = handler
        self.room = room
        # the name is derived from the name of the module
        self.name = self.__class__.__module__

    def __str__(self):
        return self.__class__.__module__

    def __repr__(self):
        return str(self)

    def _catch_errors(self, method):
        """
        Wrapper handling state method errors.

        """

        @wraps(method)
        def decorator(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except Exception:
                logger.log_trace(f"Error in State {__name__}")
                self.room.msg_room(
                    None,
                    f"|rThere was an unexpected error in State {__name__}. "
                    "Please |wreport|r this as an issue.|n",
                )
                raise  # TODO

        return decorator

    def __getattribute__(self, key):
        """
        Always wrap all callables in the error-handler

        """
        val = _GA(self, key)
        if callable(val):
            return _GA(self, "_catch_errors")(val)
        return val

    def get_hint(self):
        """
        Get a hint for how to solve this state.

        """
        hint_level = self.room.attributes.get("state_hint_level", default=-1)
        next_level = hint_level + 1
        if next_level < len(self.hints):
            # return the next hint in the sequence.
            self.room.db.state_hint_level = next_level
            self.room.db.stats["hints_used"] += 1
            self.room.log(
                f"HINT: {self.name.split('.')[-1]}, level {next_level + 1} "
                f"(total used: {self.room.db.stats['hints_used']})"
            )
            return self.hints[next_level]
        else:
            # no more hints for this state
            return None

    # helpers
    def msg(self, message, target=None, borders=False, cinematic=False):
        """
        Display messsage to everyone in room, or given target.
        """
        if cinematic:
            message = msg_cinematic(message, borders=borders)
        if target:
            options = target.attributes.get("options", category=self.room.tagcategory, default={})
            style = options.get("things_style", 2)
            # we assume this is a char
            target.msg(parse_for_things(message, things_style=style))
        else:
            self.room.msg_room(None, message)

    def cinematic(self, message, target=None):
        """
        Display a 'cinematic' sequence - centered, with borders.
        """
        self.msg(message, target=target, borders=True, cinematic=True)

    def create_object(self, typeclass=None, key="testobj", location=None, **kwargs):
        """
        This is a convenience-wrapper for quickly building EvscapeRoom objects.

        Keyword Args:
            typeclass (str): This can take just the class-name in the evscaperoom's
                objects.py module. Otherwise, a full path or the actual class
                is needed (for custom state objects, just give the class directly).
            key (str): Name of object.
            location (Object): If not given, this will be the current room.
            kwargs (any): Will be passed into create_object.
        Returns:
            new_obj (Object): The newly created object, if any.

        """
        if not location:
            location = self.room
        return create_evscaperoom_object(
            typeclass=typeclass,
            key=key,
            location=location,
            tags=[("room", self.room.tagcategory.lower())],
            **kwargs,
        )

    def get_object(self, key):
        """
        Find a named *non-character* object for this state in this room.

        Args:
            key (str): Object to search for.
        Returns:
            obj (Object): Object in the room.

        """
        match = EvscaperoomObject.objects.filter_family(
            db_key__iexact=key, db_tags__db_category=self.room.tagcategory.lower()
        )
        if not match:
            logger.log_err(f"get_object: No match for '{key}' in state ")
            return None
        return match[0]

    # state methods

    def init(self):
        """
        Initializes the state (usually by modifying the room in some way)

        """
        pass

    def clean(self):
        """
        Any cleanup operations after the state ends.

        """
        self.room.db.state_hint_level = -1

    def next(self, next_state=None):
        """
        Get the next state after this one.

        Args:
            next_state (str, optional): This allows the calling code
                to redirect to a different state than the 'default' one
                (creating branching paths in the game). Override this method
                to customize (by default the input will always override default
                set on the class)
        Returns:
            state_name (str or None): Name of next state to switch to. None
                to remain in this state. By default we check the room for the
                "finished" flag be set.
        """
        return next_state or self.next_state

    def character_enters(self, character):
        """
        Called when character enters the room in this state.

        """
        pass

    def character_leaves(self, character):
        """
        Called when character is whisked away (usually because of
        quitting). This method cannot influence the move itself; it
        happens just before room.character_cleanup()

        """
        pass
