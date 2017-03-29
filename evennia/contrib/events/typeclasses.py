"""
Patched typeclasses for Evennia.

These typeclasses are not inherited from DefaultObject and other
Evennia default types.  They softly "patch" some of these object hooks
however.  While this adds a new layer in this module, it's (normally)
more simple to use from game designers, since it doesn't require a
new inheritance.  These replaced hooks are only active if the event
system is active.  You shouldn't need to change this module, just
override the hooks as you usually do in your custom typeclasses.
Calling super() would call the Default hooks (which would call the
event hook without further ado).

"""

from evennia import DefaultCharacter, DefaultExit, DefaultObject, DefaultRoom
from evennia import ScriptDB
from evennia.utils.utils import inherits_from, lazy_property
from evennia.contrib.events.custom import (
        create_event_type, patch_hook, create_time_event)
from evennia.contrib.events.handler import EventsHandler

class EventCharacter:

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
        exits = []
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

    @staticmethod
    @patch_hook(DefaultCharacter, "at_before_move")
    def at_before_move(character, destination, hook=None):
        """
        Called just before starting to move this object to
        destination.

        Args:
            destination (Object): The object we are moving to

        Returns:
            shouldmove (bool): If we should move or not.

        Notes:
            If this method returns False/None, the move is cancelled
            before it is even started.

        """
        origin = character.location
        Room = DefaultRoom
        if isinstance(origin, Room) and isinstance(destination, Room):
            can = character.events.call("can_move", character,
                    origin, destination)
            if can:
                can = origin.events.call("can_move", character, origin)
                if can:
                    # Call other character's 'can_part' event
                    for present in [o for o in origin.contents if isinstance(
                            o, DefaultCharacter) and o is not character]:
                        can = present.events.call("can_part", present, character)
                        if not can:
                            break

            if can is None:
                return True

            return can

        return True

    @staticmethod
    @patch_hook(DefaultCharacter, "at_after_move")
    def at_after_move(character, source_location, hook=None):
        """
        Called after move has completed, regardless of quiet mode or
        not.  Allows changes to the object due to the location it is
        now in.

        Args:
            source_location (Object): Wwhere we came from. This may be `None`.

        """
        hook(character, source_location)
        origin = source_location
        destination = character.location
        Room = DefaultRoom
        if isinstance(origin, Room) and isinstance(destination, Room):
            character.events.call("move", character, origin, destination)
            destination.events.call("move", character, origin, destination)

            # Call the 'greet' event of characters in the location
            for present in [o for o in destination.contents if isinstance(
                    o, DefaultCharacter)]:
                present.events.call("greet", present, character)

    @staticmethod
    @patch_hook(DefaultCharacter, "at_object_delete")
    def at_object_delete(character, hook=None):
        """
        Called just before the database object is permanently
        delete()d from the database. If this method returns False,
        deletion is aborted.

        """
        if not character.events.call("can_delete", character):
            return False

        character.events.call("delete", character)
        return True

    @staticmethod
    @patch_hook(DefaultCharacter, "at_post_puppet")
    def at_post_puppet(character, hook=None):
        """
        Called just after puppeting has been completed and all
        Player<->Object links have been established.

        Note:
            You can use `self.player` and `self.sessions.get()` to get
            player and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        hook(character)
        character.events.call("puppeted", character)

        # Call the room's puppeted_in event
        location = character.location
        if location and isinstance(location, DefaultRoom):
            location.events.call("puppeted_in", character, location)

    @staticmethod
    @patch_hook(DefaultCharacter, "at_pre_unpuppet")
    def at_pre_unpuppet(character, hook=None):
        """
        Called just before beginning to un-connect a puppeting from
        this Player.

        Note:
            You can use `self.player` and `self.sessions.get()` to get
            player and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        character.events.call("unpuppeted", character)
        hook(character)

        # Call the room's unpuppeted_in event
        location = character.location
        if location and isinstance(location, DefaultRoom):
            location.events.call("unpuppeted_in", character, location)


class EventExit(object):

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


class EventRoom:

    """Soft-patching of room's default hooks."""

    @staticmethod
    @patch_hook(DefaultRoom, "at_object_delete")
    def at_object_delete(room, hook=None):
        """
        Called just before the database object is permanently
        delete()d from the database. If this method returns False,
        deletion is aborted.

        """
        if not room.events.call("can_delete", room):
            return False

        room.events.call("delete", room)
        return True


class EventObject(object):

    """Patched default object."""

    @lazy_property
    def events(self):
        """Return the EventsHandler."""
        return EventsHandler(self)

## Default events
# Character events
create_event_type(DefaultCharacter, "can_move", ["character",
        "origin", "destination"], """
    Can the character move?
    This event is called before the character moves into another
    location.  You can prevent the character from moving
    using the 'deny()' function.

    Variables you can use in this event:
        character: the character connected to this event.
        origin: the current location of the character.
        destination: the future location of the character.
    """)
create_event_type(DefaultCharacter, "can_delete", ["character"], """
    Can the character be deleted?
    This event is called before the character is deleted.  You can use
    'deny()' in this event to prevent this character from being deleted.
    If this event doesn't prevent the character from being deleted, its
    'delete' event is called right away.

    Variables you can use in this event:
        character: the character connected to this event.
    """)
create_event_type(DefaultCharacter, "can_part", ["character", "departing"], """
    Can the departing charaacter leave this room?
    This event is called before another character can move from the
    location where the current character also is.  This event can be
    used to prevent someone to leave this room if, for instance, he/she
    hasn't paid, or he/she is going to a protected area, past a guard,
    and so on.  Use 'deny()' to prevent the departing character from
    moving.

    Variables you can use in this event:
        departing: the character who wants to leave this room.
        character: the character connected to this event.
    """)
create_event_type(DefaultCharacter, "delete", ["character"], """
    Before deleting the character.
    This event is called just before deleting this character.  It shouldn't
    be prevented (using the `deny()` function at this stage doesn't
    have any effect).  If you want to prevent deletion of this character,
    use the event `can_delete` instead.

    Variables you can use in this event:
        character: the character connected to this event.
    """)
create_event_type(DefaultCharacter, "greet", ["character", "newcomer"], """
    A new character arrives in the location of this character.
    This event is called when another character arrives in the location
    where the current character is.  For instance, a puppeted character
    arrives in the shop of a shopkeeper (assuming the shopkeeper is
    a character).  As its name suggests, this event can be very useful
    to have NPC greeting one another, or players, who come to visit.

    Variables you can use in this event:
        character: the character connected to this event.
        newcomer: the character arriving in the same location.
    """)
create_event_type(DefaultCharacter, "move", ["character",
        "origin", "destination"], """
    After the character has moved into its new room.
    This event is called when the character has moved into a new
    room.  It is too late to prevent the move at this point.

    Variables you can use in this event:
        character: the character connected to this event.
        origin: the old location of the character.
        destination: the new location of the character.
    """)
create_event_type(DefaultCharacter, "puppeted", ["character"], """
    When the character has been puppeted by a player.
    This event is called when a player has just puppeted this character.
    This can commonly happen when a player connects onto this character,
    or when puppeting to a NPC or free character.

    Variables you can use in this event:
        character: the character connected to this event.
    """)
create_event_type(DefaultCharacter, "unpuppeted", ["character"], """
    When the character is about to be un-puppeted.
    This event is called when a player is about to un-puppet the
    character, which can happen if the player is disconnecting or
    changing puppets.

    Variables you can use in this event:
        character: the character connected to this event.
    """)

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
create_event_type(DefaultRoom, "can_delete", ["room"], """
    Can the room be deleted?
    This event is called before the room is deleted.  You can use
    'deny()' in this event to prevent this room from being deleted.
    If this event doesn't prevent the room from being deleted, its
    'delete' event is called right away.

    Variables you can use in this event:
        room: the room connected to this event.
    """)
create_event_type(DefaultRoom, "can_move", ["character", "room"], """
    Can the character move into this room?
    This event is called before the character can move into this
    specific room.  You can prevent the move by using the 'deny()'
    function.

    Variables you can use in this event:
        character: the character who wants to move in this room.
        room: the room connected to this event.
    """)
create_event_type(DefaultRoom, "delete", ["room"], """
    Before deleting the room.
    This event is called just before deleting this room.  It shouldn't
    be prevented (using the `deny()` function at this stage doesn't
    have any effect).  If you want to prevent deletion of this room,
    use the event `can_delete` instead.

    Variables you can use in this event:
        room: the room connected to this event.
    """)
create_event_type(DefaultRoom, "move", ["character",
        "origin", "destination"], """
    After the character has moved into this room.
    This event is called when the character has moved into this
    room.  It is too late to prevent the move at this point.

    Variables you can use in this event:
        character: the character connected to this event.
        origin: the old location of the character.
        destination: the new location of the character.
    """)
create_event_type(DefaultRoom, "puppeted_in", ["character", "room"], """
    After the character has been puppeted in this room.
    This event is called after a character has been puppeted in this
    room.  This can happen when a player, having connected, begins
    to puppet a character.  The character's location at this point,
    if it's a room, will see this event fire.

    Variables you can use in this event:
        character: the character who have just been puppeted in this room.
        room: the room connected to this event.
    """)
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
create_event_type(DefaultRoom, "unpuppeted_in", ["character", "room"], """
    Before the character is un-puppeted in this room.
    This event is called before a character is un-puppeted in this
    room.  This can happen when a player, puppeting a character, is
    disconnecting.  The character's location at this point, if it's a
    room, will see this event fire.

    Variables you can use in this event:
        character: the character who is about to be un-puppeted in this room.
        room: the room connected to this event.
    """)
