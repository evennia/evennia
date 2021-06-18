MAP = r"""
                       1
 + 0 1 2 3 4 5 6 7 8 9 0

10   #-#-#-#-#
     |   |    \
 9   #---+---#-#-----I
      \  |          /
 8     #-#-#-#-#   #
       |\    |
 7   #i#-#-#+#-----#-t
       |     |
 6   #i#-#---#-#-#-#-#
       |         |x|x|
 5     o-#-#-#   #-#-#
          \ /    |x|x|
 4     o-o-#-#   #-#-#
      /         /
 3   #-#       /   #
      \       /    d
 2     o-o-#-#     |
           | |     u
 1         #-#-#># #
           ^       |
 0   T-----#-#     #-t

 + 0 1 2 3 4 5 6 7 8 9 0
                       1
"""

# use default legend
LEGEND = {


}

PARENT = {
    "key": "An empty dungeon room",
    "prototype_key": "dungeon_doom_prot",
    "typeclass": "evennia.contrib.mapsystem.rooms.XYRoom",
    "desc": "Air is cold and stale in this barren room."
}

# link coordinates to rooms
ROOMS = {
    "base_prototype": PARENT,
    (1, 0): {
        "key": "Dungeon Entrance",
        "prototype_parent": PARENT,
        "desc": "A dark entrance."
    },
    (4, 0): {
        "key": "Antechamber",
        "prototype_parent": PARENT,
        "desc": "A small antechamber",
    }
}


MAP_DATA = {
    "name": "Dungeon of Doom",
    "map": MAP,
    "legend": LEGEND,
    "rooms": ROOMS,
}
