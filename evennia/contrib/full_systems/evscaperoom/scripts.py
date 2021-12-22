"""
A simple cleanup script to wipe empty rooms

(This can happen if users leave 'uncleanly', such as by closing their browser
window)

Just start this global script manually or at server creation.
"""

from evennia import DefaultScript

from .room import EvscapeRoom


class CleanupScript(DefaultScript):
    def at_script_creation(self):

        self.key = "evscaperoom_cleanup"
        self.desc = "Cleans up empty evscaperooms"

        self.interval = 60 * 15

        self.persistent = True

    def at_repeat(self):

        for room in EvscapeRoom.objects.all():
            if not room.get_all_characters():
                # this room is empty
                room.log("END: Room cleaned by garbage collector.")
                room.delete()
