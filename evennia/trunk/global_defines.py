# Do not mess with the default types (0-5).
OBJECT_TYPES = (
   (0, 'NOTHING'),
   (1, 'PLAYER'),
   (2, 'ROOM'),
   (3, 'THING'),
   (4, 'EXIT'),
   (5, 'GARBAGE'),
)

# This is a list of flags that the server actually uses. Anything not in this
# list is a custom flag.
SERVER_FLAGS = ["CONNECTED"]

# These flags are not saved.
NOSAVE_FLAGS = ["CONNECTED"]

# These flags can't be modified by players.
NOSET_FLAGS = ["CONNECTED"]

# These attribute names can't be modified by players.
NOSET_ATTRIBS = ["TEST"]
