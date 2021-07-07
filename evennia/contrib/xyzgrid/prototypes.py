"""
Default prototypes for building the XYZ-grid into actual game-rooms.

Add this to mygame/conf/settings/settings.py:

    PROTOTYPE_MODULES += ['evennia.contrib.xyzgrid.prototypes']

The prototypes can then be used in mapping prototypes as

    {'prototype_parent': 'xyz_room', ...}

and/or

    {'prototype_parent': 'xyz_exit', ...}

"""

# required by the prototype importer
PROTOTYPE_LIST = [
    {
        'prototype_key': 'xyz_room',
        'typeclass': 'evennia.contrib.xyzgrid.xyzroom.XYZRoom',
        'prototype_tags': ("xyzroom", ),
        'key': "A room",
        'desc': "An empty room."
    }, {
        'prototype_key': 'xyz_exit',
        'prototype_tags': ("xyzexit", ),
        'typeclass': 'evennia.contrib.xyzgrid.xyzroom.XYZExit',
        'desc': "An exit."
    }
]
