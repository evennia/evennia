"""
Typeclasses for the in-game Python system.

To use them, change your base typeclasses to inherit from the classes in this
module (EventObject, EventRoom, EventCharacter and EventExit) instead of the
default ones in evennia core.

"""

from evennia import DefaultCharacter, DefaultExit, DefaultObject, DefaultRoom
from evennia import ScriptDB
from evennia.utils.utils import delay, inherits_from, lazy_property
from evennia.contrib.ingame_python.callbackhandler import CallbackHandler
from evennia.contrib.ingame_python.utils import register_events, time_event, phrase_event

# Character help
CHARACTER_CAN_DELETE = """
Can the character be deleted?
This event is called before the character is deleted.  You can use
'deny()' in this event to prevent this character from being deleted.
If this event doesn't prevent the character from being deleted, its
'delete' event is called right away.

Variables you can use in this event:
    character: the character connected to this event.
"""

CHARACTER_CAN_MOVE = """
Can the character move?
This event is called before the character moves into another
location.  You can prevent the character from moving
using the 'deny()' eventfunc.

Variables you can use in this event:
    character: the character connected to this event.
    origin: the current location of the character.
    destination: the future location of the character.
"""

CHARACTER_CAN_PART = """
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
"""

CHARACTER_CAN_SAY = """
Before another character can say something in the same location.
This event is called before another character says something in the
character's location.  The "something" in question can be modified,
or the action can be prevented by using 'deny()'.  To change the
content of what the character says, simply change the variable
'message' to another string of characters.

Variables you can use in this event:
    speaker: the character who is using the say command.
    character: the character connected to this event.
    message: the text spoken by the character.
"""

CHARACTER_DELETE = """
Before deleting the character.
This event is called just before deleting this character.  It shouldn't
be prevented (using the `deny()` function at this stage doesn't
have any effect).  If you want to prevent deletion of this character,
use the event `can_delete` instead.

Variables you can use in this event:
    character: the character connected to this event.
"""

CHARACTER_GREET = """
A new character arrives in the location of this character.
This event is called when another character arrives in the location
where the current character is.  For instance, a puppeted character
arrives in the shop of a shopkeeper (assuming the shopkeeper is
a character).  As its name suggests, this event can be very useful
to have NPC greeting one another, or accounts, who come to visit.

Variables you can use in this event:
    character: the character connected to this event.
    newcomer: the character arriving in the same location.
"""

CHARACTER_MOVE = """
After the character has moved into its new room.
This event is called when the character has moved into a new
room.  It is too late to prevent the move at this point.

Variables you can use in this event:
    character: the character connected to this event.
    origin: the old location of the character.
    destination: the new location of the character.
"""

CHARACTER_PUPPETED = """
When the character has been puppeted by an account.
This event is called when an account has just puppeted this character.
This can commonly happen when an account connects onto this character,
or when puppeting to a NPC or free character.

Variables you can use in this event:
    character: the character connected to this event.
"""

CHARACTER_SAY = """
After another character has said something in the character's room.
This event is called right after another character has said
something in the same location..  The action cannot be prevented
at this moment.  Instead, this event is ideal to create keywords
that would trigger a character (like a NPC) in doing something
if a specific phrase is spoken in the same location.
To use this event, you have to specify a list of keywords as
parameters that should be present, as separate words, in the
spoken phrase.  For instance, you can set an event tthat would
fire if the phrase spoken by the character contains "menu" or
"dinner" or "lunch":
    @call/add ... = say menu, dinner, lunch
Then if one of the words is present in what the character says,
this event will fire.

Variables you can use in this event:
    speaker: the character speaking in this room.
    character: the character connected to this event.
    message: the text having been spoken by the character.
"""

CHARACTER_TIME = """
A repeated event to be called regularly.
This event is scheduled to repeat at different times, specified
as parameters.  You can set it to run every day at 8:00 AM (game
time).  You have to specify the time as an argument to @call/add, like:
    @call/add here = time 8:00
The parameter (8:00 here) must be a suite of digits separated by
spaces, colons or dashes.  Keep it as close from a recognizable
date format, like this:
    @call/add here = time 06-15 12:20
This event will fire every year on June the 15th at 12 PM (still
game time).  Units have to be specified depending on your set calendar
(ask a developer for more details).

Variables you can use in this event:
    character: the character connected to this event.
"""

CHARACTER_UNPUPPETED = """
When the character is about to be un-puppeted.
This event is called when an account is about to un-puppet the
character, which can happen if the account is disconnecting or
changing puppets.

Variables you can use in this event:
    character: the character connected to this event.
"""


@register_events
class EventCharacter(DefaultCharacter):

    """Typeclass to represent a character and call event types."""

    _events = {
        "can_delete": (["character"], CHARACTER_CAN_DELETE),
        "can_move": (["character", "origin", "destination"], CHARACTER_CAN_MOVE),
        "can_part": (["character", "departing"], CHARACTER_CAN_PART),
        "can_say": (["speaker", "character", "message"], CHARACTER_CAN_SAY, phrase_event),
        "delete": (["character"], CHARACTER_DELETE),
        "greet": (["character", "newcomer"], CHARACTER_GREET),
        "move": (["character", "origin", "destination"], CHARACTER_MOVE),
        "puppeted": (["character"], CHARACTER_PUPPETED),
        "say": (["speaker", "character", "message"], CHARACTER_SAY, phrase_event),
        "time": (["character"], CHARACTER_TIME, None, time_event),
        "unpuppeted": (["character"], CHARACTER_UNPUPPETED),
    }

    @lazy_property
    def callbacks(self):
        """Return the CallbackHandler."""
        return CallbackHandler(self)

    def announce_move_from(self, destination, msg=None, mapping=None):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        Args:
            destination (Object): The place we are going to.
            msg (str, optional): a replacement message.
            mapping (dict, optional): additional mapping objects.

        You can override this method and call its parent with a
        message to simply change the default message.  In the string,
        you can use the following as mappings (between braces):
            object: the object which is moving.
            exit: the exit from which the object is moving (if found).
            origin: the location of the object before the move.
            destination: the location of the object after moving.

        """
        if not self.location:
            return

        string = msg or "{object} is leaving {origin}, heading for {destination}."

        # Get the exit from location to destination
        location = self.location
        exits = [
            o for o in location.contents if o.location is location and o.destination is destination
        ]
        mapping = mapping or {}
        mapping.update({"character": self})

        if exits:
            exits[0].callbacks.call(
                "msg_leave", self, exits[0], location, destination, string, mapping
            )
            string = exits[0].callbacks.get_variable("message")
            mapping = exits[0].callbacks.get_variable("mapping")

        # If there's no string, don't display anything
        # It can happen if the "message" variable in events is set to None
        if not string:
            return

        super().announce_move_from(destination, msg=string, mapping=mapping)

    def announce_move_to(self, source_location, msg=None, mapping=None):
        """
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (Object): The place we came from
            msg (str, optional): the replacement message if location.
            mapping (dict, optional): additional mapping objects.

        You can override this method and call its parent with a
        message to simply change the default message.  In the string,
        you can use the following as mappings (between braces):
            object: the object which is moving.
            exit: the exit from which the object is moving (if found).
            origin: the location of the object before the move.
            destination: the location of the object after moving.

        """

        if not source_location and self.location.has_account:
            # This was created from nowhere and added to an account's
            # inventory; it's probably the result of a create command.
            string = "You now have %s in your possession." % self.get_display_name(self.location)
            self.location.msg(string)
            return

        if source_location:
            string = msg or "{character} arrives to {destination} from {origin}."
        else:
            string = "{character} arrives to {destination}."

        origin = source_location
        destination = self.location
        exits = []
        mapping = mapping or {}
        mapping.update({"character": self})

        if origin:
            exits = [
                o
                for o in destination.contents
                if o.location is destination and o.destination is origin
            ]
            if exits:
                exits[0].callbacks.call(
                    "msg_arrive", self, exits[0], origin, destination, string, mapping
                )
                string = exits[0].callbacks.get_variable("message")
                mapping = exits[0].callbacks.get_variable("mapping")

        # If there's no string, don't display anything
        # It can happen if the "message" variable in events is set to None
        if not string:
            return

        super().announce_move_to(source_location, msg=string, mapping=mapping)

    def at_before_move(self, destination):
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
        origin = self.location
        Room = DefaultRoom
        if isinstance(origin, Room) and isinstance(destination, Room):
            can = self.callbacks.call("can_move", self, origin, destination)
            if can:
                can = origin.callbacks.call("can_move", self, origin)
                if can:
                    # Call other character's 'can_part' event
                    for present in [
                        o
                        for o in origin.contents
                        if isinstance(o, DefaultCharacter) and o is not self
                    ]:
                        can = present.callbacks.call("can_part", present, self)
                        if not can:
                            break

            if can is None:
                return True

            return can

        return True

    def at_after_move(self, source_location):
        """
        Called after move has completed, regardless of quiet mode or
        not.  Allows changes to the object due to the location it is
        now in.

        Args:
            source_location (Object): Wwhere we came from. This may be `None`.

        """
        super().at_after_move(source_location)

        origin = source_location
        destination = self.location
        Room = DefaultRoom
        if isinstance(origin, Room) and isinstance(destination, Room):
            self.callbacks.call("move", self, origin, destination)
            destination.callbacks.call("move", self, origin, destination)

            # Call the 'greet' event of characters in the location
            for present in [
                o for o in destination.contents if isinstance(o, DefaultCharacter) and o is not self
            ]:
                present.callbacks.call("greet", present, self)

    def at_object_delete(self):
        """
        Called just before the database object is permanently
        delete()d from the database. If this method returns False,
        deletion is aborted.

        """
        if not self.callbacks.call("can_delete", self):
            return False

        self.callbacks.call("delete", self)
        return True

    def at_post_puppet(self):
        """
        Called just after puppeting has been completed and all
        Account<->Object links have been established.

        Note:
            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        super().at_post_puppet()

        self.callbacks.call("puppeted", self)

        # Call the room's puppeted_in event
        location = self.location
        if location and isinstance(location, DefaultRoom):
            location.callbacks.call("puppeted_in", self, location)

    def at_pre_unpuppet(self):
        """
        Called just before beginning to un-connect a puppeting from
        this Account.

        Note:
            You can use `self.account` and `self.sessions.get()` to get
            account and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        self.callbacks.call("unpuppeted", self)

        # Call the room's unpuppeted_in event
        location = self.location
        if location and isinstance(location, DefaultRoom):
            location.callbacks.call("unpuppeted_in", self, location)

        super().at_pre_unpuppet()

    def at_before_say(self, message, **kwargs):
        """
        Before the object says something.

        This hook is by default used by the 'say' and 'whisper'
        commands as used by this command it is called before the text
        is said/whispered and can be used to customize the outgoing
        text from the object. Returning `None` aborts the command.

        Args:
            message (str): The suggested say/whisper text spoken by self.
        Kwargs:
            whisper (bool): If True, this is a whisper rather than
                a say. This is sent by the whisper command by default.
                Other verbal commands could use this hook in similar
                ways.
            receiver (Object): If set, this is a target for the say/whisper.

        Returns:
            message (str): The (possibly modified) text to be spoken.

        """
        # First, try the location
        location = getattr(self, "location", None)
        location = (
            location
            if location and inherits_from(location, "evennia.objects.objects.DefaultRoom")
            else None
        )
        if location and not kwargs.get("whisper", False):
            allow = location.callbacks.call("can_say", self, location, message, parameters=message)
            message = location.callbacks.get_variable("message")
            if not allow or not message:
                return

            # Browse all the room's other characters
            for obj in location.contents:
                if obj is self or not inherits_from(
                    obj, "evennia.objects.objects.DefaultCharacter"
                ):
                    continue

                allow = obj.callbacks.call("can_say", self, obj, message, parameters=message)
                message = obj.callbacks.get_variable("message")
                if not allow or not message:
                    return

        return message

    def at_say(self, message, **kwargs):
        """
        Display the actual say (or whisper) of self.

        This hook should display the actual say/whisper of the object in its
        location.  It should both alert the object (self) and its
        location that some text is spoken.  The overriding of messages or
        `mapping` allows for simple customization of the hook without
        re-writing it completely.

        Args:
            message (str): The text to be conveyed by self.
            msg_self (str, optional): The message to echo to self.
            msg_location (str, optional): The message to echo to self's location.
            receiver (Object, optional): An eventual receiver of the message
                (by default only used by whispers).
            msg_receiver(str, optional): Specific message for receiver only.
            mapping (dict, optional): Additional mapping in messages.
        Kwargs:
            whisper (bool): If this is a whisper rather than a say. Kwargs
                can be used by other verbal commands in a similar way.

        Notes:

            Messages can contain {} markers, which must
            If used, `msg_self`, `msg_receiver`  and `msg_location` should contain
            references to other objects between braces, the way `location.msg_contents`
            would allow.  For instance:
                msg_self = 'You say: "{speech}"'
                msg_location = '{object} says: "{speech}"'
                msg_receiver = '{object} whispers: "{speech}"'

            The following mappings can be used in both messages:
                object: the object speaking.
                location: the location where object is.
                speech: the text spoken by self.

            You can use additional mappings if you want to add other
            information in your messages.

        """

        super().at_say(message, **kwargs)
        location = getattr(self, "location", None)
        location = (
            location
            if location and inherits_from(location, "evennia.objects.objects.DefaultRoom")
            else None
        )

        if location and not kwargs.get("whisper", False):
            location.callbacks.call("say", self, location, message, parameters=message)

            # Call the other characters' "say" event
            presents = [
                obj
                for obj in location.contents
                if obj is not self
                and inherits_from(obj, "evennia.objects.objects.DefaultCharacter")
            ]
            for present in presents:
                present.callbacks.call("say", self, present, message, parameters=message)


# Exit help
EXIT_CAN_TRAVERSE = """
Can the character traverse through this exit?
This event is called when a character is about to traverse this
exit.  You can use the deny() function to deny the character from
exitting for this time.

Variables you can use in this event:
    character: the character that wants to traverse this exit.
    exit: the exit to be traversed.
    room: the room in which stands the character before moving.
"""

EXIT_MSG_ARRIVE = """
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
    mapping: a dictionary containing the mapping of the message.
"""

EXIT_MSG_LEAVE = """
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
    mapping: a dictionary containing additional mapping.
"""

EXIT_TIME = """
A repeated event to be called regularly.
This event is scheduled to repeat at different times, specified
as parameters.  You can set it to run every day at 8:00 AM (game
time).  You have to specify the time as an argument to @call/add, like:
    @call/add north = time 8:00
The parameter (8:00 here) must be a suite of digits separated by
spaces, colons or dashes.  Keep it as close from a recognizable
date format, like this:
    @call/add south = time 06-15 12:20
This event will fire every year on June the 15th at 12 PM (still
game time).  Units have to be specified depending on your set calendar
(ask a developer for more details).

Variables you can use in this event:
    exit: the exit connected to this event.
"""

EXIT_TRAVERSE = """
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
"""


@register_events
class EventExit(DefaultExit):

    """Modified exit including management of events."""

    _events = {
        "can_traverse": (["character", "exit", "room"], EXIT_CAN_TRAVERSE),
        "msg_arrive": (
            ["character", "exit", "origin", "destination", "message", "mapping"],
            EXIT_MSG_ARRIVE,
        ),
        "msg_leave": (
            ["character", "exit", "origin", "destination", "message", "mapping"],
            EXIT_MSG_LEAVE,
        ),
        "time": (["exit"], EXIT_TIME, None, time_event),
        "traverse": (["character", "exit", "origin", "destination"], EXIT_TRAVERSE),
    }

    @lazy_property
    def callbacks(self):
        """Return the CallbackHandler."""
        return CallbackHandler(self)

    def at_traverse(self, traversing_object, target_location):
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
            allow = self.callbacks.call("can_traverse", traversing_object, self, self.location)
            if not allow:
                return

        super().at_traverse(traversing_object, target_location)

        # After traversing
        if is_character:
            self.callbacks.call(
                "traverse", traversing_object, self, self.location, self.destination
            )


# Object help
OBJECT_DROP = """
When a character drops this object.
This event is called when a character drops this object.  It is
called after the command has ended and displayed its message, and
the action cannot be prevented at this time.

Variables you can use in this event:
    character: the character having dropped the object.
    obj: the object connected to this event.
"""

OBJECT_GET = """
When a character gets this object.
This event is called when a character gets this object.  It is
called after the command has ended and displayed its message, and
the action cannot be prevented at this time.

Variables you can use in this event:
    character: the character having picked up the object.
    obj: the object connected to this event.
"""

OBJECT_TIME = """
A repeated event to be called regularly.
This event is scheduled to repeat at different times, specified
as parameters.  You can set it to run every day at 8:00 AM (game
time).  You have to specify the time as an argument to @call/add, like:
    @call/add here = time 8:00
The parameter (8:00 here) must be a suite of digits separated by
spaces, colons or dashes.  Keep it as close from a recognizable
date format, like this:
    @call/add here = time 06-15 12:20
This event will fire every year on June the 15th at 12 PM (still
game time).  Units have to be specified depending on your set calendar
(ask a developer for more details).

Variables you can use in this event:
    object: the object connected to this event.
"""


@register_events
class EventObject(DefaultObject):

    """Default object with management of events."""

    _events = {
        "drop": (["character", "obj"], OBJECT_DROP),
        "get": (["character", "obj"], OBJECT_GET),
        "time": (["object"], OBJECT_TIME, None, time_event),
    }

    @lazy_property
    def callbacks(self):
        """Return the CallbackHandler."""
        return CallbackHandler(self)

    def at_get(self, getter):
        """
        Called by the default `get` command when this object has been
        picked up.

        Args:
            getter (Object): The object getting this object.

        Notes:
            This hook cannot stop the pickup from happening. Use
            permissions for that.

        """
        super().at_get(getter)
        self.callbacks.call("get", getter, self)

    def at_drop(self, dropper):
        """
        Called by the default `drop` command when this object has been
        dropped.

        Args:
            dropper (Object): The object which just dropped this object.

        Notes:
            This hook cannot stop the drop from happening. Use
            permissions from that.

        """
        super().at_drop(dropper)
        self.callbacks.call("drop", dropper, self)


# Room help
ROOM_CAN_DELETE = """
Can the room be deleted?
This event is called before the room is deleted.  You can use
'deny()' in this event to prevent this room from being deleted.
If this event doesn't prevent the room from being deleted, its
'delete' event is called right away.

Variables you can use in this event:
    room: the room connected to this event.
"""

ROOM_CAN_MOVE = """
Can the character move into this room?
This event is called before the character can move into this
specific room.  You can prevent the move by using the 'deny()'
function.

Variables you can use in this event:
    character: the character who wants to move in this room.
    room: the room connected to this event.
"""

ROOM_CAN_SAY = """
Before a character can say something in this room.
This event is called before a character says something in this
room.  The "something" in question can be modified, or the action
can be prevented by using 'deny()'.  To change the content of what
the character says, simply change the variable 'message' to another
string of characters.

Variables you can use in this event:
    character: the character who is using the say command.
    room: the room connected to this event.
    message: the text spoken by the character.
"""

ROOM_DELETE = """
Before deleting the room.
This event is called just before deleting this room.  It shouldn't
be prevented (using the `deny()` function at this stage doesn't
have any effect).  If you want to prevent deletion of this room,
use the event `can_delete` instead.

Variables you can use in this event:
    room: the room connected to this event.
"""

ROOM_MOVE = """
After the character has moved into this room.
This event is called when the character has moved into this
room.  It is too late to prevent the move at this point.

Variables you can use in this event:
    character: the character connected to this event.
    origin: the old location of the character.
    destination: the new location of the character.
"""

ROOM_PUPPETED_IN = """
After the character has been puppeted in this room.
This event is called after a character has been puppeted in this
room.  This can happen when an account, having connected, begins
to puppet a character.  The character's location at this point,
if it's a room, will see this event fire.

Variables you can use in this event:
    character: the character who have just been puppeted in this room.
    room: the room connected to this event.
"""

ROOM_SAY = """
After the character has said something in the room.
This event is called right after a character has said something
in this room.  The action cannot be prevented at this moment.
Instead, this event is ideal to create actions that will respond
to something being said aloud.  To use this event, you have to
specify a list of keywords as parameters that should be present,
as separate words, in the spoken phrase.  For instance, you can
set an event tthat would fire if the phrase spoken by the character
contains "menu" or "dinner" or "lunch":
    @call/add ... = say menu, dinner, lunch
Then if one of the words is present in what the character says,
this event will fire.

Variables you can use in this event:
    character: the character having spoken in this room.
    room: the room connected to this event.
    message: the text having been spoken by the character.
"""

ROOM_TIME = """
A repeated event to be called regularly.
This event is scheduled to repeat at different times, specified
as parameters.  You can set it to run every day at 8:00 AM (game
time).  You have to specify the time as an argument to @call/add, like:
    @call/add here = time 8:00
The parameter (8:00 here) must be a suite of digits separated by
spaces, colons or dashes.  Keep it as close from a recognizable
date format, like this:
    @call/add here = time 06-15 12:20
This event will fire every year on June the 15th at 12 PM (still
game time).  Units have to be specified depending on your set calendar
(ask a developer for more details).

Variables you can use in this event:
    room: the room connected to this event.
"""

ROOM_UNPUPPETED_IN = """
Before the character is un-puppeted in this room.
This event is called before a character is un-puppeted in this
room.  This can happen when an account, puppeting a character, is
disconnecting.  The character's location at this point, if it's a
room, will see this event fire.

Variables you can use in this event:
    character: the character who is about to be un-puppeted in this room.
    room: the room connected to this event.
"""


@register_events
class EventRoom(DefaultRoom):

    """Default room with management of events."""

    _events = {
        "can_delete": (["room"], ROOM_CAN_DELETE),
        "can_move": (["character", "room"], ROOM_CAN_MOVE),
        "can_say": (["character", "room", "message"], ROOM_CAN_SAY, phrase_event),
        "delete": (["room"], ROOM_DELETE),
        "move": (["character", "origin", "destination"], ROOM_MOVE),
        "puppeted_in": (["character", "room"], ROOM_PUPPETED_IN),
        "say": (["character", "room", "message"], ROOM_SAY, phrase_event),
        "time": (["room"], ROOM_TIME, None, time_event),
        "unpuppeted_in": (["character", "room"], ROOM_UNPUPPETED_IN),
    }

    @lazy_property
    def callbacks(self):
        """Return the CallbackHandler."""
        return CallbackHandler(self)

    def at_object_delete(self):
        """
        Called just before the database object is permanently
        delete()d from the database. If this method returns False,
        deletion is aborted.

        """
        if not self.callbacks.call("can_delete", self):
            return False

        self.callbacks.call("delete", self)
        return True
