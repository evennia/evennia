"""
Prototypes for building the XYZ-grid into actual game-rooms.

Add this to mygame/conf/settings/settings.py:

    PROTOTYPE_MODULES += ['evennia.contrib.xyzgrid.prototypes']

"""

# Note - the XYZRoom/exit parents track the XYZ coordinates automatically
# so we don't need to add custom tags to them here.
_ROOM_PARENT = {
    'prototype_tags': ("xyzroom", ),
    'typeclass': 'evennia.contrib.xyzgrid.xyzroom.XYZRoom'
}

_EXIT_PARENT = {
    'prototype_tags': ("xyzexit", ),
    'typeclass': 'evennia.contrib.xyzgrid.xyzroom.XYZExit'
}

PROTOTYPE_LIST = [
    {
        'prototype_key': 'xyz_room_prototype',
        'prototype_parent': _ROOM_PARENT,
        'key': "A non-descript room",
    },{
        'prototype_key': 'xyz_transition_room_prototype',
        'prototype_parent': _ROOM_PARENT,
        'typeclass': 'evennia.contrib.xyzgrid.xyzroom.XYZMapTransitionRoom',
    },{
        'prototype_key': 'xyz_exit_prototype',
        'prototype_parent': _EXIT_PARENT,
    }
]
