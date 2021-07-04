"""
Custom Evennia launcher command option for building/rebuilding the grid in a separate process than
the main server (since this can be slow).

To use, add to the settings:
::

    EXTRA_LAUNCHER_COMMANDS.update({'xyzgrid': 'evennia.contrib.xyzgrid.launchcmd.xyzcommand'})

You should now be able to do
::

    evennia xyzgrid <options>

Use `evennia xyzgrid help` for usage help.

"""

from evennia.contrib.xyzgrid.xyzgrid import get_xyzgrid

_HELP_SHORT = """
evennia xyzgrid help|list|init|add|build|initpath|delete [<options>]
Manages the XYZ grid. Use 'xyzgrid help' for documentation.
"""

_HELP_LONG = """
evennia xyzgrid list

    Lists the map grid structure and any loaded maps.

evennia xyzgrid list Z|mapname

    Display the given XYmap in more detail. Also 'show' works.

evennia xyzgrid init

    First start of the grid. This will create the XYZGrid global script. No maps are loaded yet!
    It's safe to run this command multiple times; the grid will only be initialized once.

evennia xyzgrid add path.to.xymap.module

    Add one or more XYmaps (each a string-map representing one Z position along with prototypes
    etc). The module will be parsed for

    - a XYMAP_DATA a dict
        {"map": mapstring, "zcoord": mapname/zcoord, "legend": dict, "prototypes": dict}
        describing one single XYmap, or
    - a XYMAP_LIST - a list of multiple dicts on the XYMAP_DATA form. This allows to load
        multiple maps from the same module.

    Note that adding a map does *not* build it. If maps are linked to one another, you should add
    all linked maps before building, or you'll get errors when spawning the linking exits.

evennia xyzgrid build

    Builds/updates the entire database grid based on the added maps. For a new grid, this will spawn
    all new rooms/exits (and may take a good while!). For updating, rooms may be removed/spawned if
    a map changed since the last build.

evennia xyzgrid build (X,Y,Z|mapname)

    Builds/updates only a part of the grid. This should usually only be used if the full grid has
    already been built once - otherwise inter-map transitions may fail! Z is the name/z-coordinate
    of the map.  Use '*' as a wildcard. For example (*, *, mymap) will only update map `mymap` and
    (12, 6, mymap) will only update position (12, 6) on the map 'mymap'.

evennia xyzgrid initpath

    Recreates the pathfinder matrices for the entire grid. These are used for all shortest-path
    calculations. The result will be cached to disk (in mygame/server/.cache/). If not run, each map
    will run this automatically first time it's used. Running this will always force to rebuild the
    cache.

evennia xyzgrid initpath Z|mapname

    recreate the pathfinder matrix for a specific map only. Z is the name/z-coordinate of the map.

evennia xyzgrid delete Z|mapname

    Remove a previously added XYmap with the name/z-coordinate Z. E.g. 'remove mymap'. If the map
    was built, this will also wipe all its spawned rooms/exits. You will be asked to confirm before
    continuing with this operation.

evennia xyzgrid delete

    WARNING: This will delete the entire xyz-grid (all maps), and *all* rooms/exits built to match
    it (they serve no purpose without the grid). You will be asked to confirm before continuing with
    this operation.

"""

def _option_list(**suboptions):
    """
    List/view grid.

    """
    xyzgrid = get_xyzgrid()
    xymap_data = xyzgrid.grid
    if not xymap_data:
        print("The XYZgrid is currently empty. Use 'add' to add paths to your map data.")
        return

    if not suboptions:
        print("XYMaps stored in grid:")
        for zcoord, xymap in sorted(xymap_data.items(), key=lambda tup: tup[0]):
            print(str(xymap))


def _option_init(**suboptions):
    """
    Initialize a new grid. Will fail if a Grid already exists.

    """
    grid = get_xyzgrid()
    print(f"The grid is initalized as the Script 'XYZGrid'({grid.dbref})")

def _option_add(**suboptions):
    """
    Add a new map to the grid.

    """

def _option_build(**suboptions):
    """
    Build the grid or part of it.

    """

def _option_initpath(**suboptions):
    """
    Initialize the pathfinding matrices for grid or part of it.

    """

def _option_delete(**suboptions):
    """
    Delete the grid or parts of it.

    """

    if not suboptions:
        repl = input("WARNING: This will delete the ENTIRE Grid and wipe all rooms/exits!"
                     "\nObjects/Chars inside deleted rooms will be moved to their home locations."
                     "\nThis can't be undone. Are you sure you want to continue? Y/[N]?")
        if repl.lower() not in ('yes', 'y'):
            print("Aborted.")
        else:
            print("Deleting grid ...")
            grid = get_xyzgrid()
            grid.delete()
    else:
        pass


def xyzcommand(*args):
    """
    Evennia launcher command. This is made available as `evennia xyzgrid` on the command line,
    once `settings.EXTRA_LAUNCHER_COMMANDS` is updated.

    """
    if not args:
        print(_HELP_SHORT.strip())
        return

    option, *suboptions = args

    if option in ('help', 'h'):
        print(f"{_HELP_SHORT.strip()}\n{_HELP_LONG.rstrip()}")

    if option in ('list', 'show'):
        _option_list(*suboptions)
    elif option == 'init':
        _option_init(*suboptions)
    elif option == 'add':
        _option_add(*suboptions)
    elif option == 'build':
        _option_build(*suboptions)
    elif option == 'initpath':
        _option_initpath(*suboptions)
    elif option == 'delete':
        _option_delete(*suboptions)
