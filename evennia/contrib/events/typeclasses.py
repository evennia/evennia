"""
Patched typeclasses for Evennia.
"""

from evennia import DefaultCharacter, DefaultExit, DefaultObject, DefaultRoom
from evennia import ScriptDB
from evennia.utils.utils import inherits_from, lazy_property
from evennia.contrib.events.custom import (
        create_event_type, patch_hook, create_time_event)
from evennia.contrib.events.handler import EventsHandler

class PatchedCharacter:

    """Patched typeclass for DefaultCharcter."""

    @staticmethod
    @patch_hook(DefaultCharacter, "announce_move_from")
    def announce_move_from(character, destination, msg=None, hook=None):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.  Customizing the message through events is possible.

        Args:
            destination (Object): The place we are going to.
            msg (optional): a custom message to replace the default one.

        """
        if not character.location:
            return

        if msg:
            string = msg
        else:
            string = "{character} is leaving {origin}, heading for {destination}."

        # Get the exit from location to destination
        location = character.location
        exits = [o for o in location.contents if o.location is location and o.destination is destination]
        if exits:
            exits[0].events.call("msg_leave", character, exits[0],
                    location, destination, string)
            string = exits[0].events.get_variable("message")

        mapping = {
                "character": character,
                "exit": exits[0] if exits else "somewhere",
                "origin": location or "nowhere",
                "destination": destination or "nowhere",
        }

        # If there's no string, don't display anything
        # It can happen if the "message" variable in events is set to None
        if not string:
            return

        location.msg_contents(string, exclude=(character, ), mapping=mapping)

    @staticmethod
    @patch_hook(DefaultCharacter, "announce_move_to")
    def announce_move_to(character, source_location, msg=None, hook=None):
        """
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (Object): The place we came from
            msg (str, optional): the default message to be displayed.

        """

        if not source_location and character.location.has_player:
            # This was created from nowhere and added to a player's
            # inventory; it's probably the result of a create command.
            string = "You now have %s in your possession." % self.get_display_name(self.location)
            character.location.msg(string)
            return

        if source_location:
            if msg:
                string = msg
            else:
                string = "{character} arrives to {destination} from {origin}."
        else:
            string = "{character} arrives to {destination}."

        origin = source_location
        destination = character.location
        if origin:
            exits = [o for o in destination.contents if o.location is destination and o.destination is origin]
            if exits:
                exits[0].events.call("msg_arrive", character, exits[0],
                        origin, destination, string)
                string = exits[0].events.get_variable("message")

        mapping = {
                "character": character,
                "exit": exits[0] if exits else "somewhere",
                "origin": origin or "nowhere",
                "destination": destination or "nowhere",
        }

        # If there's no string, don't display anything
        # It can happen if the "message" variable in events is set to None
        if not string:
            return

        destination.msg_contents(string, exclude=(character, ), mapping=mapping)


class PatchedObject(object):
    @lazy_property
    def events(self):
        """Return the EventsHandler."""
        return EventsHandler(self)

class PatchedExit(object):

    """Patched exit to patch some hooks of DefaultExit."""

    @staticmethod
    @patch_hook(DefaultExit, "at_traverse")
    def at_traverse(exit, traversing_object, target_location, hook=None):
        """
        This hook is responsible for handling the actual traversal,
        normally by calling
        `traversing_object.move_to(target_location)`. It is normally
        only implemented by Exit objects. If it returns False (usually
        because `move_to` returned False), `at_after_traverse` below
        should not be called and instead `at_failed_traverse` should be
        called.

        Args:
            traversing_object (Object): Object traversing us.
            target_location (Object): Where target is going.

        """
        is_character = inherits_from(traversing_object, DefaultCharacter)
        if is_character:
            allow = exit.events.call("can_traverse", traversing_object,
                    exit, exit.location)
            if not allow:
                return

        hook(exit, traversing_object, target_location)

        # After traversing
        if is_character:
            exit.events.call("traverse", traversing_object,
                    exit, exit.location, exit.destination)


## Default events
# Exit events
create_event_type(DefaultExit, "can_traverse", ["character", "exit", "room"],
    """
    Can the character traverse through this exit?
    This event is called when a character is about to traverse this
    exit.  You can use the deny() function to deny the character from
    exitting for this time.

    Variables you can use in this event:
        character: the character that wants to traverse this exit.
        exit: the exit to be traversed.
        room: the room in which stands the character before moving.
""")
create_event_type(DefaultExit, "msg_arrive", ["character", "exit",
        "origin", "destination", "message"], """
    Customize the message when a character arrives through this exit.
    This event is called when a character arrives through this exit.
    To customize the message that will be sent to the room where the
    character arrives, change the value of the variable "message"
    to give it your custom message.  The character itself will not be
    notified.  You can use mapping between braces, like this:
        message = "{character} climbs out of a hole."
    In your mapping, you can use {character} (the character who has
    arrived), {exit} (the exit), {origin} (the room in which
    the character was), and {destination} (the room in which the character
    now is).  If you need to customize the message with other information,
    you can also set "message" to None and send something else instead.

    Variables you can use in this event:
        character: the character who is arriving through this exit.
        exit: the exit having been traversed.
        origin: the past location of the character.
        destination: the current location of the character.
        message: the message to be displayed in the destination.
""")
create_event_type(DefaultExit, "msg_leave", ["character", "exit",
        "origin", "destination", "message"], """
    Customize the message when a character leaves through this exit.
    This event is called when a character leaves through this exit.
    To customize the message that will be sent to the room where the
    character came from, change the value of the variable "message"
    to give it your custom message.  The character itself will not be
    notified.  You can use mapping between braces, like this:
        message = "{character} falls into a hole!"
    In your mapping, you can use {character} (the character who is
    about to leave), {exit} (the exit), {origin} (the room in which
    the character is), and {destination} (the room in which the character
    is heading for).  If you need to customize the message with other
    information, you can also set "message" to None and send something
    else instead.

    Variables you can use in this event:
        character: the character who is leaving through this exit.
        exit: the exit being traversed.
        origin: the location of the character.
        destination: the destination of the character.
        message: the message to be displayed in the location.
""")
create_event_type(DefaultExit, "time", ["exit"], """
    A repeated event to be called regularly.
    This event is scheduled to repeat at different times, specified
    as parameters.  You can set it to run every day at 8:00 AM (game
    time).  You have to specify the time as an argument to @event/add, like:
        @event/add north = time 8:00
    The parameter (8:00 here) must be a suite of digits separated by
    spaces, colons or dashes.  Keep it as close from a recognizable
    date format, like this:
        @event/add south = time 06-15 12:20
    This event will fire every year on June the 15th at 12 PM (still
    game time).  Units have to be specified depending on your set calendar
    (ask a developer for more details).

    Variables you can use in this event:
        exit: the exit connected to this event.
    """, create_time_event)
create_event_type(DefaultExit, "traverse", ["character", "exit",
        "origin", "destination"], """
    After the characer has traversed through this exit.
    This event is called after a character has traversed through this
    exit.  Traversing cannot be prevented using 'deny()' at this
    point.  The character will be in a different room and she will
    have received the room's description when this event is called.

    Variables you can use in this event:
        character: the character who has traversed through this exit.
        exit: the exit that was just traversed through.
        origin: the exit's location (where the character was before moving).
        destination: the character's location after moving.
    """)

# Room events
create_event_type(DefaultRoom, "time", ["room"], """
    A repeated event to be called regularly.
    This event is scheduled to repeat at different times, specified
    as parameters.  You can set it to run every day at 8:00 AM (game
    time).  You have to specify the time as an argument to @event/add, like:
        @event/add here = time 8:00
    The parameter (8:00 here) must be a suite of digits separated by
    spaces, colons or dashes.  Keep it as close from a recognizable
    date format, like this:
        @event/add here = time 06-15 12:20
    This event will fire every year on June the 15th at 12 PM (still
    game time).  Units have to be specified depending on your set calendar
    (ask a developer for more details).

    Variables you can use in this event:
        room: the room connected to this event.
    """, create_time_event)
