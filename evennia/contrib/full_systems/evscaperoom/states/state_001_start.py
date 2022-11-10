"""
First room state

This simple example sets up an empty one-state room with a door and a key.
After unlocking, opening the door and leaving the room, the player is
teleported back to the evscaperoom menu.


"""

from evennia.contrib.full_systems.evscaperoom import objects
from evennia.contrib.full_systems.evscaperoom.state import BaseState

GREETING = """
This is the situation, {name}:

You are locked in this room ... get out! Simple as that!

"""


ROOM_DESC = """
This is a featureless room. On one wall is a *door. On the other wall is a
*button marked "GET HELP".

There is a *key lying on the floor.

"""

# Example object

DOOR_DESC = """
This is a simple example door leading out of the room.

"""


class Door(objects.Openable):
    """
    The door leads out of the room.

    """

    start_open = False

    def at_object_creation(self):
        super().at_object_creation()
        self.set_flag("door")  # target for key

    def at_open(self, caller):
        # only works if the door was unlocked
        self.msg_room(caller, f"~You ~open *{self.key}")

    def at_focus_leave(self, caller, **kwargs):
        if self.check_flag("open"):
            self.msg_room(caller, "~You ~leave the room!")
            self.msg_char(caller, "Congrats!")
            # exit evscaperoom
            self.room.character_exit(caller)
        else:
            self.msg_char(caller, "The door is closed. You cannot leave!")


# key

KEY_DESC = """
A simple room key. A paper label is attached to it.
"""

KEY_READ = """
A paper label is attached to the key. It reads.

    |rOPEN THE DOOR WITH ME|n

A little on the nose, but this is an example room after all ...
"""

KEY_APPLY = """
~You insert the *key into the *door, turns it and ... the door unlocks!

"""


class Key(objects.Insertable, objects.Readable):
    "A key for opening the door"

    # where this key applies (must be flagged as such)
    target_flag = "door"

    def at_apply(self, caller, action, obj):
        obj.set_flag("unlocked")  # unlocks the door
        self.msg_room(caller, KEY_APPLY.strip())

    def at_read(self, caller, *args, **kwargs):
        self.msg_char(caller, KEY_READ.strip())

    def get_cmd_signatures(self):
        return [], "You can *read the label or *insert the key into something."


# help button

BUTTON_DESC = """
On the wall is a button marked

    PRESS ME FOR HELP

"""


class HelpButton(objects.EvscaperoomObject):
    def at_focus_push(self, caller, **kwargs):
        "this adds the 'push' action to the button"

        hint = self.room.state.get_hint()
        if hint is None:
            self.msg_char(caller, "There are no more hints to be had.")
        else:
            self.msg_room(
                caller, f"{caller.key} pushes *button and gets the " f'hint:\n "{hint.strip()}"|n'
            )


# state

STATE_HINT_LVL1 = """
The door is locked. What is usually used for unlocking doors?
"""

STATE_HINT_LVL2 = """
This is just an example. Do what comes naturally. Examine what's on the floor.
"""

STATE_HINT_LVL3 = """
Insert the *key in the *door. Then open the door and leave! Yeah, it's really
that simple.

"""


class State(BaseState):
    """
    This class (with exactly this name) must exist in every state module.

    """

    # this makes these hints available to the .get_hint method.
    hints = [STATE_HINT_LVL1, STATE_HINT_LVL2, STATE_HINT_LVL3]

    def character_enters(self, char):
        "Called when char enters room at this state"
        self.cinematic(GREETING.format(name=char.key))

    def init(self):
        "Initialize state"

        # describe the room
        self.room.db.desc = ROOM_DESC

        # create the room objects
        door = self.create_object(Door, key="door to the cabin", aliases=["door"])
        door.db.desc = DOOR_DESC.strip()

        key = self.create_object(Key, key="key", aliases=["room key"])
        key.db.desc = KEY_DESC.strip()

        button = self.create_object(HelpButton, key="button", aliases=["help button"])
        button.db.desc = BUTTON_DESC.strip()

    def clean(self):
        "Cleanup operations on the state, when it's over"
        super().clean()
