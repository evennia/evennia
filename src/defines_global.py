import os

# Object type keys, DO NOT CHANGE!
OTYPE_NOTHING = 0
OTYPE_PLAYER = 1
OTYPE_ROOM = 2
OTYPE_THING = 3
OTYPE_EXIT = 4
OTYPE_GOING = 5
OTYPE_GARBAGE = 6

# Do not mess with the default types (0-5). This is passed to the Object
# model's 'choices' argument.
OBJECT_TYPES = (
    (OTYPE_NOTHING, 'NOTHING'),
    (OTYPE_PLAYER, 'PLAYER'),
    (OTYPE_ROOM, 'ROOM'),
    (OTYPE_THING, 'THING'),
    (OTYPE_EXIT, 'EXIT'),
    (OTYPE_GOING, 'GOING'),
    (OTYPE_GARBAGE, 'GARBAGE'),
)

# These attribute names can't be modified by players.
NOSET_ATTRIBS = ["MONEY", "ALIAS", "LASTPAGED", "__CHANLIST", "LAST", 
                 "__PARENT", "LASTSITE", "LOCKS"]

# These attributes don't show up on objects when examined.
HIDDEN_ATTRIBS = ["__CHANLIST", "__PARENT", "LOCKS"]

# Server version number.
REVISION = os.popen('svnversion .', 'r').readline().strip()
if not REVISION:
    REVISION = "Unknown"

# Clip out the SVN keyword information
EVENNIA_VERSION = 'Alpha ' + REVISION

# The message to show when the user lacks permissions for something.
NOPERMS_MSG = "You do not have the necessary permissions to do that."

# Message seen when object doesn't control the other object.
NOCONTROL_MSG = "You don't have authority over that object."

# Default descs when creating new objects
DESC_PLAYER = "An average person."
DESC_ROOM = "There is nothing special about this place."
DESC_THING = "You see nothing special."
DESC_EXIT = "This is an exit out of here."
