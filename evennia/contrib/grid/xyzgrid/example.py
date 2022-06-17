"""
Example xymaps to use with the XYZgrid contrib. Build outside of the game using
the `evennia xyzgrid` launcher command.

First add the launcher extension in your mygame/server/conf/settings.py:

    EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand'

Then

    evennia xyzgrid init
    evennia xyzgrid add evennia.contrib.grid.xyzgrid.map_example
    evennia xyzgrid build




"""

from evennia.contrib.grid.xyzgrid import xymap_legend

# default prototype parent. It's important that
# the typeclass inherits from the XYZRoom (or XYZExit)
# if adding the evennia.contrib.grid.xyzgrid.prototypes to
# settings.PROTOTYPE_MODULES, one could just set the
# prototype_parent to 'xyz_room' and 'xyz_exit' here
# instead.

ROOM_PARENT = {
    "key": "An empty room",
    "prototype_key": "xyz_exit_prototype",
    # "prototype_parent": "xyz_room",
    "typeclass": "evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom",
    "desc": "An empty room.",
}

EXIT_PARENT = {
    "prototype_key": "xyz_exit_prototype",
    # "prototype_parent": "xyz_exit",
    "typeclass": "evennia.contrib.grid.xyzgrid.xyzroom.XYZExit",
    "desc": "A path to the next location.",
}


# ---------------------------------------- map1
# The large tree
#
# this exemplifies the various map symbols
# but is not heavily prototyped

MAP1 = r"""
                       1
 + 0 1 2 3 4 5 6 7 8 9 0

 8   #-------#-#-------I
      \               /
 7     #-#---#     t-#
       |\    |
 6   #i#-#b--#-t
       |     |
 5     o-#---#
          \ /
 4     o---#-#
      /    d
 3   #-----+-------#
           |       d
 2         |       |
           v       u
 1         #---#>#-#
          /
 0       #-T

 + 0 1 2 3 4 5 6 7 8 9 0
                       1
"""


class TransitionToCave(xymap_legend.TransitionMapNode):
    """
    A transition from 'the large tree' to 'the small cave' map. This node is never spawned
    into a room but only acts as a target for finding the exit's destination.

    """

    symbol = "T"
    target_map_xyz = (1, 0, "the small cave")


# extends the default legend
LEGEND_MAP1 = {"T": TransitionToCave}


# link coordinates to rooms
PROTOTYPES_MAP1 = {
    # node/room prototypes
    (3, 0): {
        "key": "Dungeon Entrance",
        "desc": "To the east, a narrow opening leads into darkness.",
    },
    (4, 1): {
        "key": "Under the foilage of a giant tree",
        "desc": "High above the branches of a giant tree blocks out the sunlight. A slide "
        "leading down from the upper branches ends here.",
    },
    (4, 4): {
        "key": "The slide",
        "desc": "A slide leads down to the ground from here. It looks like a one-way trip.",
    },
    (6, 1): {
        "key": "Thorny path",
        "desc": "To the east is a pathway of thorns. If you get through, you don't think you'll be "
        "able to get back here the same way.",
    },
    (8, 1): {"key": "By a large tree", "desc": "You are standing at the root of a great tree."},
    (8, 3): {"key": "At the top of the tree", "desc": "You are at the top of the tree."},
    (3, 7): {
        "key": "Dense foilage",
        "desc": "The foilage to the east is extra dense. It will take forever to get through it.",
    },
    (5, 6): {
        "key": "On a huge branch",
        "desc": "To the east is a glowing light, may be a teleporter to a higher branch.",
    },
    (9, 7): {
        "key": "On an enormous branch",
        "desc": "To the west is a glowing light. It may be a teleporter to a lower branch.",
    },
    (10, 8): {
        "key": "A gorgeous view",
        "desc": "The view from here is breathtaking, showing the forest stretching far and wide.",
    },
    # default rooms
    ("*", "*"): {
        "key": "Among the branches of a giant tree",
        "desc": "These branches are wide enough to easily walk on. There's green all around.",
    },
    # directional prototypes
    (3, 0, "e"): {"desc": "A dark passage into the underworld."},
}

for key, prot in PROTOTYPES_MAP1.items():
    if len(key) == 2:
        # we don't want to give exits the room typeclass!
        prot["prototype_parent"] = ROOM_PARENT
    else:
        prot["prototype_parent"] = EXIT_PARENT


XYMAP_DATA_MAP1 = {
    "zcoord": "the large tree",
    "map": MAP1,
    "legend": LEGEND_MAP1,
    "prototypes": PROTOTYPES_MAP1,
}

# -------------------------------------- map2
# The small cave
# this gives prototypes for every room

MAP2 = r"""
+ 0 1 2 3

3   #-#-#
    |x|
2 #-#-#
    |  \
1   #---#
    |  /
0 T-#-#

+ 0 1 2 3

"""

# custom map node
class TransitionToLargeTree(xymap_legend.TransitionMapNode):
    """
    A transition from 'the small cave' to 'the large tree' map. This node is never spawned
    into a room by only acts as a target for finding the exit's destination.

    """

    symbol = "T"
    target_map_xyz = (3, 0, "the large tree")


# this extends the default legend (that defines #,-+ etc)
LEGEND_MAP2 = {"T": TransitionToLargeTree}

# prototypes for specific locations
PROTOTYPES_MAP2 = {
    # node/rooms prototype overrides
    (1, 0): {
        "key": "The entrance",
        "desc": "This is the entrance to a small cave leading into the ground. "
        "Light sifts in from the outside, while cavernous passages disappear "
        "into darkness.",
    },
    (2, 0): {
        "key": "A gruesome sight.",
        "desc": "Something was killed here recently. The smell is unbearable.",
    },
    (1, 1): {
        "key": "A dark pathway",
        "desc": "The path splits three ways here. To the north a faint light can be seen.",
    },
    (3, 2): {
        "key": "Stagnant water",
        "desc": "A pool of stagnant, black water dominates this small chamber. To the nortwest "
        "a faint light can be seen.",
    },
    (0, 2): {"key": "A dark alcove", "desc": "This alcove is empty."},
    (1, 2): {
        "key": "South-west corner of the atrium",
        "desc": "Sunlight sifts down into a large underground chamber. Weeds and grass sprout "
        "between the stones.",
    },
    (2, 2): {
        "key": "South-east corner of the atrium",
        "desc": "Sunlight sifts down into a large underground chamber. Weeds and grass sprout "
        "between the stones.",
    },
    (1, 3): {
        "key": "North-west corner of the atrium",
        "desc": "Sunlight sifts down into a large underground chamber. Weeds and grass sprout "
        "between the stones.",
    },
    (2, 3): {
        "key": "North-east corner of the atrium",
        "desc": "Sunlight sifts down into a large underground chamber. Weeds and grass sprout "
        "between the stones. To the east is a dark passage.",
    },
    (3, 3): {
        "key": "Craggy crevice",
        "desc": "This is the deepest part of the dungeon. The path shrinks away and there "
        "is no way to continue deeper.",
    },
    # default fallback for undefined nodes
    ("*", "*"): {"key": "A dark room", "desc": "A dark, but empty, room."},
    # directional prototypes
    (1, 0, "w"): {"desc": "A narrow path to the fresh air of the outside world."},
    # directional fallbacks for unset directions
    ("*", "*", "*"): {"desc": "A dark passage"},
}

# this is required by the prototypes, but we add it all at once so we don't
# need to add it to every line above
for key, prot in PROTOTYPES_MAP2.items():
    if len(key) == 2:
        # we don't want to give exits the room typeclass!
        prot["prototype_parent"] = ROOM_PARENT
    else:
        prot["prototype_parent"] = EXIT_PARENT


XYMAP_DATA_MAP2 = {
    "map": MAP2,
    "zcoord": "the small cave",
    "legend": LEGEND_MAP2,
    "prototypes": PROTOTYPES_MAP2,
    "options": {"map_visual_range": 1, "map_mode": "scan"},
}

# This is read by the parser
XYMAP_DATA_LIST = [XYMAP_DATA_MAP1, XYMAP_DATA_MAP2]
