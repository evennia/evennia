"""
Patched typeclasses for Evennia.
"""

from evennia import DefaultCharacter, DefaultExit
from evennia import ScriptDB
from evennia.contrib.events.extend import create_event_type, patch_hook
from evennia.utils.utils import inherits_from

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
        script = ScriptDB.objects.get(db_key="event_handler")
        if is_character:
            allow = script.call_event(exit, "can_traverse", traversing_object,
                    exit, exit.location)
            if not allow:
                return

        hook(exit, traversing_object, target_location)

        # After traversing
        if is_character:
            script.call_event(exit, "traverse", traversing_object,
                    exit, exit.location, exit.destination)


# Default events
create_event_type(DefaultExit, "can_traverse", ["character", "exit", "room"],
    """
    Can the character traverse through this exit?
    This event is called when a character is about to traverse this
    exit.  You can use the deny() function to deny the character from
    using this exit for the time being.  The 'character' variable
    contains the character who wants to traverse through this exit.
    The 'exit' variable contains the exit, the 'room' variable
    contains the room in which the character and exit are.
""")
create_event_type(DefaultExit, "traverse", ["character", "exit",
        "origin", "destination"], """
    After the characer has traversed through this exit.
    This event is called after a character has traversed through this
    exit.  Traversing cannot be prevented using 'deny()' at this
    point.  The character will be in a different room and she will
    have received the room's description when this event is called.
    The 'character' variable contains the character who has traversed
    through this exit.  The 'exit' variable contains the exit, the
    'origin' variable contains the room in which the character was
    before traversing, while 'destination' contains the room in which
    the character now is.
    """)
