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
        if inherits_from(traversing_object, DefaultCharacter):
            script = ScriptDB.objects.get(db_key="event_handler")
            script.call_event(exit, "at_traverse", traversing_object,
                    exit, exit.location)

        hook(exit, traversing_object, target_location)

# Default events
create_event_type(DefaultExit, "at_traverse", ["character", "exit", "room"],
        """When traversing""")
