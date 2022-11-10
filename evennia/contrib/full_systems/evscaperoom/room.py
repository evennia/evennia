"""
Room class and mechanics for the Evscaperoom.

This is a special room class that not only depicts the evscaperoom itself, it
also acts as a central store for the room state, score etc. When deleting this,
that particular escaperoom challenge should be gone.

"""

from evennia import DefaultCharacter, DefaultObject, DefaultRoom, logger, utils
from evennia.locks.lockhandler import check_lockstring
from evennia.utils.ansi import strip_ansi
from evennia.utils.utils import lazy_property, list_to_string

from .commands import CmdSetEvScapeRoom
from .objects import EvscaperoomObject
from .state import StateHandler


class EvscapeRoom(EvscaperoomObject, DefaultRoom):
    """
    The room to escape from.

    """

    def at_object_creation(self):
        """
        Called once, when the room is first created.

        """
        super().at_object_creation()

        # starting state
        self.db.state = None  # name
        self.db.prev_state = None

        # this is used for tagging of all objects belonging to this
        # particular room instance, so they can be cleaned up later
        # this is accessed through the .tagcategory getter.
        self.db.tagcategory = "evscaperoom_{}".format(self.key)

        # room progress statistics
        self.db.stats = {
            "progress": 0,  # in percent
            "score": {},  # reason: score
            "max_score": 100,
            "hints_used": 0,  # total across all states
            "hints_total": 41,
            "total_achievements": 14,
        }

        self.cmdset.add(CmdSetEvScapeRoom, persistent=True)

        self.log("Room created and log started.")

    @lazy_property
    def statehandler(self):
        return StateHandler(self)

    @property
    def state(self):
        return self.statehandler.current_state

    def log(self, message, caller=None):
        """
        Log to a file specificially for this room.
        """
        caller = f"[caller.key]: " if caller else ""

        logger.log_file(
            strip_ansi(f"{caller}{message.strip()}"), filename=self.tagcategory + ".log"
        )

    def score(self, new_score, reason):
        """
        We don't score individually but for everyone in room together.
        You can only be scored for a given reason once."""
        if reason not in self.db.stats["score"]:
            self.log(f"score: {reason} ({new_score}pts)")
            self.db.stats["score"][reason] = new_score

    def progress(self, new_progress):
        "Progress is what we set it to be (0-100%)"
        self.log(f"progress: {new_progress}%")
        self.db.stats["progress"] = new_progress

    def achievement(self, caller, achievement, subtext=""):
        """
        Give the caller a personal achievment. You will only
        ever get one of the same type

        Args:
            caller (Object): The receiver of the achievement.
            achievement (str): The title/name of the achievement.
            subtext (str, optional): Eventual subtext/explanation
                of the achievement.
        """
        achievements = caller.attributes.get("achievements", category=self.tagcategory)
        if not achievements:
            achievements = {}
        if achievement not in achievements:
            self.log(f"achievement: {caller} earned '{achievement}' - {subtext}")
            achievements[achievement] = subtext
            caller.attributes.add("achievements", achievements, category=self.tagcategory)

    def get_all_characters(self):
        """
        Get the player characters in the room.

        Returns:
            chars (Queryset): The characters.

        """
        return DefaultCharacter.objects.filter_family(db_location=self)

    def set_flag(self, flagname):
        self.db.flags[flagname] = True

    def unset_flag(self, flagname):
        if flagname in self.db.flags:
            del self.db.flags[flagname]

    def check_flag(self, flagname):
        return self.db.flags.get(flagname, False)

    def check_perm(self, caller, permission):
        return check_lockstring(caller, f"dummy:perm({permission})")

    def tag_character(self, character, tag, category=None):
        """
        Tag a given character in this room.

        Args:
            character (Character): Player character to tag.
            tag (str): Tag to set.
            category (str, optional): Tag-category. If unset, use room's
                tagcategory.

        """
        category = category if category else self.db.tagcategory
        character.tags.add(tag, category=category)

    def tag_all_characters(self, tag, category=None):
        """
        Set a given tag on all players in the room.

        Args:
            room (EvscapeRoom): The room to escape from.
            tag (str): The tag to set.
            category (str, optional): If unset, will use the room's tagcategory.

        """
        category = category if category else self.tagcategory

        for char in self.get_all_characters():
            char.tags.add(tag, category=category)

    def character_cleanup(self, char):
        """
        Clean all custom tags/attrs on a character.

        """
        if self.tagcategory:
            char.tags.remove(category=self.tagcategory)
            char.attributes.remove(category=self.tagcategory)

    def character_exit(self, char):
        """
        Have a character exit the room - return them to the room menu.

        """
        self.log(f"EXIT: {char} left room")
        from .menu import run_evscaperoom_menu

        self.character_cleanup(char)
        char.location = char.home

        # check if room should be deleted
        if len(self.get_all_characters()) < 1:
            self.delete()

        # we must run menu after deletion so we don't include this room!
        run_evscaperoom_menu(char)

    # Evennia hooks

    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):
        """
        Called when an object arrives in the room. This can be used to
        sum up the situation, set tags etc.

        """
        if utils.inherits_from(moved_obj, "evennia.objects.objects.DefaultCharacter"):
            self.log(f"JOIN: {moved_obj} joined room")
            self.state.character_enters(moved_obj)

    def at_object_leave(self, moved_obj, target_location, move_type="move", **kwargs):
        """
        Called when an object leaves the room; if this is a Character we need
        to clean them up and move them to the menu state.

        """
        if utils.inherits_from(moved_obj, "evennia.objects.objects.DefaultCharacter"):
            self.character_cleanup(moved_obj)
        if len(self.get_all_characters()) <= 1:
            # after this move there'll be no more characters in the room - delete the room!
            self.delete()
            # logger.log_info("DEBUG: Don't delete room when last player leaving")

    def delete(self):
        """
        Delete this room and all items related to it. Only move the players.

        """
        self.db.deleting = True
        for char in self.get_all_characters():
            self.character_exit(char)
        for obj in self.contents:
            obj.delete()
        self.log("END: Room cleaned up and deleted")
        return super().delete()

    def return_appearance(self, looker, **kwargs):
        obj, pos = self.get_position(looker)
        pos = (
            f"\n|x[{self.position_prep_map[pos]} on " f"{obj.get_display_name(looker)}]|n"
            if obj
            else ""
        )

        admin_only = ""
        if self.check_perm(looker, "Admin"):
            # only for admins
            objs = DefaultObject.objects.filter_family(db_location=self).exclude(id=looker.id)
            admin_only = "\n|xAdmin only: " + list_to_string(
                [obj.get_display_name(looker) for obj in objs]
            )

        return f"{self.db.desc}{pos}{admin_only}"
