# Do not mess with the default types (0-5). This is passed to the Object
# model's 'choices' argument.
OBJECT_TYPES = (
   (0, 'NOTHING'),
   (1, 'PLAYER'),
   (2, 'ROOM'),
   (3, 'THING'),
   (4, 'EXIT'),
   (5, 'GOING'),
   (6, 'GARBAGE'),
)

# Hate to duplicate the above, but it's the easiest way.
OTYPE_NOTHING = 0
OTYPE_PLAYER = 1
OTYPE_ROOM = 2
OTYPE_THING = 3
OTYPE_EXIT = 4
OTYPE_GOING = 5
OTYPE_GARBAGE = 6

# This is a list of flags that the server actually uses. Anything not in this
# list is a custom flag.
SERVER_FLAGS = ["CONNECTED", "DARK", "FLOATING", "GAGGED", "HAVEN", "OPAQUE", "SAFE", "SLAVE", "SUSPECT", "TRANSPARENT"]

# These flags are not saved.
NOSAVE_FLAGS = ["CONNECTED"]

# These flags can't be modified by players.
NOSET_FLAGS = ["CONNECTED"]

# These attribute names can't be modified by players.
NOSET_ATTRIBS = ["MONEY", "ALIAS", "LASTPAGED", "CHANLIST", "LAST", "LASTSITE"]

# These attributes don't show up on objects when examined.
HIDDEN_ATTRIBS = ["CHANLIST"]

# Server version number.
EVENNIA_REVISION = '$Rev$'
EVENNIA_VERSION = 'Alpha'

# The message to show when the user lacks permissions for something.
NOPERMS_MSG = "You do not have the necessary permissions to do that."

# Message seen when object doesn't control the other object.
NOCONTROL_MSG = "You don't have authority over that object."
