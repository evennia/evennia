"""
Custom Evennia launcher command option for maintaining the grid in a separate process than the main
server (since this can be slow).

To use, add to the settings:
::

    EXTRA_LAUNCHER_COMMANDS.update({'xyzgrid': 'evennia.contrib.grid.xyzgrid.launchcmd.xyzcommand'})

You should now be able to do
::

    evennia xyzgrid <options>

Use `evennia xyzgrid help` for usage help.

"""

from os.path import join as pathjoin

from django.conf import settings

import evennia
from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid
from evennia.utils import ansi

_HELP_SHORT = """
evennia xyzgrid help | list | init | add | spawn | initpath | delete [<options>]
 Manages the XYZ grid. Use 'xyzgrid help <option>' for documentation.
"""

_HELP_HELP = """
evennia xyzgrid <command> [<options>]
Manages the XYZ grid.

help <command>   - get help about each command:
    list            - show list
    init            - initialize grid (only one time)
    add             - add new maps to grid
    spawn           - spawn added maps into actual db-rooms/exits
    initpath        - (re)creates pathfinder matrices
    delete          - delete part or all of grid
"""

_HELP_LIST = """
list

    Lists the map grid structure and any loaded maps.

list <Z|mapname>

    Display the given XYmap in more detail. Also 'show' works. Use quotes around
    map-names with spaces.

Examples:

    evennia xyzgrid list
    evennia xyzgrid list mymap
    evennia xyzgrid list "the small cave"
"""

_HELP_INIT = """
init

    First start of the grid. This will create the XYZGrid global script. No maps are loaded yet!
    It's safe to run this command multiple times; the grid will only be initialized once.

Example:

    evennia xyzgrid init
"""


_HELP_ADD = """
add <path.to.xymap.module> [<path> <path>,...]

    Add path(s) to one or more modules containing XYMap definitions. The module will be parsed
    for

    - a XYMAP_DATA - a dict on this form:
        {"map": mapstring, "zcoord": mapname/zcoord, "legend": dict, "prototypes": dict}
        describing one single XYmap, or
    - a XYMAP_DATA_LIST - a list of multiple dicts on the XYMAP_DATA form. This allows for
        embedding multiple maps in the same module. See evennia/contrib/grid/xyzgrid/example.py
        for an example of how this looks.

    Note that adding a map does *not* spawn it. If maps are linked to one another, you should
    add all linked maps before running 'spawn', or you'll get errors when creating transitional
    exits between maps.

Examples:

    evennia xyzgrid add evennia.contrib.grid.xyzgrid.example
    evennia xyzgrid add world.mymap1 world.mymap2 world.mymap3
"""

_HELP_SPAWN = """
spawn

    spawns/updates the entire database grid based on the added maps. For a new grid, this will
    spawn all new rooms/exits (and may take a good while!). For updating, rooms may be
    removed/spawned if a map changed since the last spawn.

spawn "(X,Y,Z|mapname)"

    spawns/updates only a part of the grid. Remember the quotes around the coordinate (this
    is mostly because shells don't like them)! Use '*' as a wild card for XY coordinates.
    This should usually only be used if the full grid has already been built once - otherwise
    inter-map transitions may fail! Z is the name/z-coordinate of the map to spawn.

Examples:

    evennia xyzgrid spawn                  - spawn all
    evennia xyzgrid "(*, *, mymap1)"       - spawn everything of map/zcoord mymap1
    evennia xyzgrid "(12, 5, mymap1)"      - spawn only coordinate (12, 5) on map/zcoord mymap1
"""

_HELP_INITPATH = """
initpath

    Recreates the pathfinder matrices for the entire grid. These are used for all shortest-path
    calculations. The result will be cached to disk (in mygame/server/.cache/). If not run, each
    map will run this automatically first time it's used. Running this will always force to
    respawn the cache.

initpath Z|mapname

    recreate the pathfinder matrix for a specific map only. Z is the name/z-coordinate of the
    map. If the map name has spaces in it, use quotes.

Examples:

    evennia xyzgrid initpath
    evennia xyzgrid initpath mymap1
    evennia xyzgrid initpath "the small cave"
"""

_HELP_DELETE = """
delete

    WARNING: This will delete the entire xyz-grid (all maps), and *all* rooms/exits built to
    match it (they serve no purpose without the grid). You will be asked to confirm before
    continuing with this operation.

delete Z|mapname

    Remove a previously added XYmap with the name/z-coordinate Z. If the map was built, this
    will also wipe all its spawned rooms/exits. You will be asked to confirm before continuing
    with this operation. Use quotes if the Z/mapname contains spaces.

Examples:

    evennia xyzgrid delete
    evennia xyzgrid delete mymap1
    evennia xyzgrid delete "the small cave"
"""

_TOPICS_MAP = {
    "list": _HELP_LIST,
    "init": _HELP_INIT,
    "add": _HELP_ADD,
    "spawn": _HELP_SPAWN,
    "initpath": _HELP_INITPATH,
    "delete": _HELP_DELETE,
}

evennia._init()


def _option_help(*suboptions):
    """
    Show help <command> aid.

    """
    if not suboptions:
        topic = _HELP_HELP
    else:
        topic = _TOPICS_MAP.get(suboptions[0], _HELP_HELP)
    print(topic.strip())


def _option_list(*suboptions):
    """
    List/view grid.

    """

    xyzgrid = get_xyzgrid()

    # override grid's logger to echo directly to console
    def _log(msg):
        print(msg)

    xyzgrid.log = _log

    xymap_data = xyzgrid.grid
    if not xymap_data:
        if xyzgrid.db.map_data:
            print("Grid could not load due to errors.")
        else:
            print("The XYZgrid is currently empty. Use 'add' to add paths to your map data.")
        return

    if not suboptions:
        print("XYMaps stored in grid:")
        for zcoord, xymap in sorted(xymap_data.items(), key=lambda tup: tup[0]):
            print("\n" + str(repr(xymap)) + ":\n")
            print(ansi.parse_ansi(str(xymap)))
        return

    zcoord = " ".join(suboptions)
    xymap = xyzgrid.get_map(zcoord)
    if not xymap:
        print(f"No XYMap with Z='{zcoord}' was found on grid.")
    else:
        nrooms = xyzgrid.get_room(("*", "*", zcoord)).count()
        nnodes = len(xymap.node_index_map)
        print("\n" + str(repr(xymap)) + ":\n")
        checkwarning = True
        if not nrooms:
            print(f"{nrooms} / {nnodes} rooms are spawned.")
            checkwarning = False
        elif nrooms < nnodes:
            print(
                f"{nrooms} / {nnodes} rooms are spawned\n"
                "Note: Transitional nodes are *not* spawned (they just point \n"
                "to another map), so the 'missing room(s)' may just be from such nodes."
            )
        elif nrooms > nnodes:
            print(
                f"{nrooms} / {nnodes} rooms are spawned\n"
                "Note: Maybe some rooms were removed from map. Run 'spawn' to re-sync."
            )
        else:
            print(f"{nrooms} / {nnodes} rooms are spawned\n")

        if checkwarning:
            print(
                "Note: This check is not complete; it does not consider changed map "
                "topology\nlike relocated nodes/rooms and new/removed links/exits - this "
                "is calculated only during a spawn."
            )
        print("\nDisplayed map (as appearing in-game):\n\n" + ansi.parse_ansi(str(xymap)))
        print(
            "\nRaw map string (including axes and invisible nodes/links):\n" + str(xymap.mapstring)
        )
        print(f"\nCustom map options: {xymap.options}\n")
        legend = []
        for key, node_or_link in xymap.legend.items():
            legend.append(f"{key} - {node_or_link.__doc__.strip()}")
        print("Legend (all elements may not be present on map):\n " + "\n ".join(legend))


def _option_init(*suboptions):
    """
    Initialize a new grid. Will fail if a Grid already exists.

    """
    grid = get_xyzgrid()
    print(f"The grid is initalized as the Script '{grid.key}'({grid.dbref})")


def _option_add(*suboptions):
    """
    Add one or more map to the grid. Supports `add path,path,path,...`

    """
    grid = get_xyzgrid()

    # override grid's logger to echo directly to console
    def _log(msg):
        print(msg)

    grid.log = _log

    xymap_data_list = []
    for path in suboptions:
        maps = grid.maps_from_module(path)
        if not maps:
            print(f"No maps found with the path {path}.\nSeparate multiple paths with spaces. ")
            return
        mapnames = "\n ".join(f"'{m['zcoord']}'" for m in maps)
        print(f" XYMaps from {path}:\n {mapnames}")
        xymap_data_list.extend(maps)
    grid.add_maps(*xymap_data_list)
    try:
        grid.reload()
    except Exception as err:
        print(err)
    else:
        print(f"Added (or readded) {len(xymap_data_list)} XYMaps to grid.")


def _option_spawn(*suboptions):
    """
    spawn the grid or part of it.

    """
    grid = get_xyzgrid()

    # override grid's logger to echo directly to console
    def _log(msg):
        print(msg)

    grid.log = _log

    if suboptions:
        opts = "".join(suboptions).strip("()")
        # coordinate tuple
        try:
            x, y, z = (part.strip() for part in opts.split(","))
        except ValueError:
            print(
                "spawn coordinate must be given as (X, Y, Z) tuple, where '*' act "
                "wild cards and Z is the mapname/z-coord of the map to load."
            )
            return
    else:
        x, y, z = "*", "*", "*"

    if x == y == z == "*":
        inp = input(
            "This will (re)spawn the entire grid. If it was built before, it may spawn \n"
            "new rooms or delete rooms that no longer matches the grid.\nDo you want to "
            "continue? [Y]/N? "
        )
    else:
        inp = input(
            "This will spawn/delete objects in the database matching grid coordinates \n"
            f"({x},{y},{z}) (where '*' is a wildcard).\nDo you want to continue? [Y]/N? "
        )
    if inp.lower() in ("no", "n"):
        print("Aborted.")
        return

    print("Beginner-Tutorial spawn ...")
    grid.spawn(xyz=(x, y, z))
    print(
        "... spawn complete!\nIt's recommended to reload the server to refresh caches if this "
        "modified an existing grid."
    )


def _option_initpath(*suboptions):
    """
    (Re)Initialize the pathfinding matrices for grid or part of it.

    """
    grid = get_xyzgrid()

    # override grid's logger to echo directly to console
    def _log(msg):
        print(msg)

    grid.log = _log

    xymaps = grid.all_maps()
    nmaps = len(xymaps)
    for inum, xymap in enumerate(xymaps):
        print(f"(Re)building pathfinding matrix for xymap Z={xymap.Z} ({inum+1}/{nmaps}) ...")
        xymap.calculate_path_matrix(force=True)

    cachepath = pathjoin(settings.GAME_DIR, "server", ".cache")
    print(f"... done. Data cached to {cachepath}.")


def _option_delete(*suboptions):
    """
    Delete the grid or parts of it. Allows mapname,mapname, ...

    """

    grid = get_xyzgrid()

    # override grid's logger to echo directly to console
    def _log(msg):
        print(msg)

    grid.log = _log

    if not suboptions:
        repl = input(
            "WARNING: This will delete the ENTIRE Grid and wipe all rooms/exits!"
            "\nObjects/Chars inside deleted rooms will be moved to their home locations."
            "\nThis can't be undone. Are you sure you want to continue? Y/[N]? "
        )
        if repl.lower() not in ("yes", "y"):
            print("Aborted.")
            return
        print("Deleting grid ...")
        grid.delete()
        print(
            "... done.\nPlease reload the server now; otherwise "
            "removed rooms may linger in cache."
        )
        return

    zcoords = (part.strip() for part in suboptions)
    err = False
    for zcoord in zcoords:
        if not grid.get_map(zcoord):
            print(f"Mapname/zcoord {zcoord} is not a part of the grid.")
            err = True
    if err:
        print("Valid mapnames/zcoords are\n:", "\n ".join(xymap.Z for xymap in grid.all_rooms()))
        return
    repl = input(
        "This will delete map(s) {', '.join(zcoords)} and wipe all corresponding\n"
        "rooms/exits!"
        "\nObjects/Chars inside deleted rooms will be moved to their home locations."
        "\nThis can't be undone. Are you sure you want to continue? Y/[N]? "
    )
    if repl.lower() not in ("yes", "y"):
        print("Aborted.")
        return

    print("Deleting selected xymaps ...")
    grid.remove_map(*zcoords, remove_objects=True)
    print(
        "... done.\nPlease reload the server to refresh room caches."
        "\nAlso remember to remove any links from remaining maps pointing to deleted maps."
    )


def xyzcommand(*args):
    """
    Evennia launcher command. This is made available as `evennia xyzgrid` on the command line,
    once added to `settings.EXTRA_LAUNCHER_COMMANDS`.

    """
    if not args:
        print(_HELP_SHORT.strip())
        return

    option, *suboptions = args

    if option in ("help", "h"):
        _option_help(*suboptions)
    if option in ("list", "show"):
        _option_list(*suboptions)
    elif option == "init":
        _option_init(*suboptions)
    elif option == "add":
        _option_add(*suboptions)
    elif option == "spawn":
        _option_spawn(*suboptions)
    elif option == "initpath":
        _option_initpath(*suboptions)
    elif option == "delete":
        _option_delete(*suboptions)
    else:
        print(f"Unknown option '{option}'. Use 'evennia xyzgrid help' for valid arguments.")
