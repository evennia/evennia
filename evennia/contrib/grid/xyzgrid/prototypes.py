"""
Default prototypes for building the XYZ-grid into actual game-rooms.

Add this to mygame/conf/settings/settings.py:

    PROTOTYPE_MODULES += ['evennia.contrib.grid.xyzgrid.prototypes']

The prototypes can then be used in mapping prototypes as

    {'prototype_parent': 'xyz_room', ...}

and/or

    {'prototype_parent': 'xyz_exit', ...}

"""
from django.conf import settings

try:
    room_override = settings.XYZROOM_PROTOTYPE_OVERRIDE
except AttributeError:
    room_override = {}

try:
    exit_override = settings.XYZEXIT_PROTOTYPE_OVERRIDE
except AttributeError:
    exit_override = {}

room_prototype = {
    "prototype_key": "xyz_room",
    "typeclass": "evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom",
    "prototype_tags": ("xyzroom",),
    "key": "A room",
    "desc": "An empty room.",
}
room_prototype.update(room_override)

exit_prototype = {
    "prototype_key": "xyz_exit",
    "typeclass": "evennia.contrib.grid.xyzgrid.xyzroom.XYZExit",
    "prototype_tags": ("xyzexit",),
    "desc": "An exit.",
}
exit_prototype.update(exit_override)

# accessed by the prototype importer
PROTOTYPE_LIST = [room_prototype, exit_prototype]
