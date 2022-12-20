r"""
# XYMap

The `XYMap` class represents one XY-grid of interconnected map-legend components. It's built from an
ASCII representation, where unique characters represents each type of component. The Map parses the
map into an internal graph that can be efficiently used for pathfinding the shortest route between
any two nodes (rooms).

Each room (MapNode) can have exits (links) in 8 cardinal directions (north, northwest etc) as well
as up and down. These are indicated in code as 'n', 'ne', 'e', 'se', 's', 'sw', 'w',
'nw', 'u' and 'd'.


```python
    # in module passed to 'Map' class

    MAP = r'''
                           1
     + 0 1 2 3 4 5 6 7 8 9 0

    10 #   # # #     #-I-#
        \  i i i     d
     9   #-#-#-#     |
         |\    |     u
     8   #-#-#-#-----#b----o
         |     |           |
     7   #-#---#-#-#-#-#   |
         |         |x|x|   |
     6   o-#-#-#   #-#-#-#b#
            \      |x|x|
     5   o---#-#<--#-#-#
        /    |
     4 #-----+-# #---#
        \    | |  \ /
     3   #b#-#-#   x   #
             | |  / \ u
     2       #-#-#---#
             ^       d
     1       #-#     #
             |
     0 #-#---o

     + 0 1 2 3 4 5 6 7 8 9 1
                           0

    '''


    LEGEND = {'#': xyzgrid.MapNode, '|': xyzgrid.NSMapLink,...}

    # read by parser if XYMAP_DATA_LIST doesn't exist
    XYMAP_DATA = {
        "map": MAP,
        "legend": LEGEND,
        "zcoord": "City of Foo",
        "prototypes": {
            (0,1): { ... },
            (1,3): { ... },
            ...
        }

    }

    # will be parsed first, allows for multiple map-data dicts from one module
    XYMAP_DATA_LIST = [
        XYMAP_DATA
    ]

```

The two `+` signs  in the upper/lower left corners are required and marks the edge of the map area.
The origo of the grid is always two steps right and two up from the bottom test marker and the grid
extends to two lines below the top-left marker. Anything outside the grid is ignored, so numbering
the coordinate axes is optional but recommended for readability.

The XY positions represent coordinates positions in the game world. When existing, they are usually
represented by Rooms in-game. The links between nodes would normally represent Exits, but the length
of links on the map have no in-game equivalence except that traversing a multi-step link will place
you in a location with an XY coordinate different from what you'd expect by a single step (most
games don't relay the XY position to the player anyway).

In the map string, every XY coordinate must have exactly one spare space/line between them - this is
used for node linkings. This finer grid which has 2x resolution of the `XYgrid` is only used by the
mapper and is referred to as the `xygrid` (small xy) internally. Note that an XY position can also
be held by a link (for example a passthrough).

The nodes and links can be customized by add your own implementation of `MapNode` or `MapLink` to
the LEGEND dict, mapping them to a particular character symbol. A `MapNode` can only be added
on an even XY coordinate while `MapLink`s can be added anywhere on the xygrid.

See `./example.py` for a full grid example.

----
"""
import pickle
from collections import defaultdict
from os import mkdir
from os.path import isdir, isfile
from os.path import join as pathjoin

try:
    from scipy import zeros
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
except ImportError as err:
    raise ImportError(
        f"{err}\nThe XYZgrid contrib requires "
        "the SciPy package. Install with `pip install scipy'."
    )
from django.conf import settings

from evennia.prototypes import prototypes as protlib
from evennia.prototypes.spawner import flatten_prototype
from evennia.utils import logger
from evennia.utils.utils import is_iter, mod_import, variable_from_module

from . import xymap_legend
from .utils import BIGVAL, MapError, MapParserError

_NO_DB_PROTOTYPES = True
if hasattr(settings, "XYZGRID_USE_DB_PROTOTYPES"):
    _NO_DB_PROTOTYPES = not settings.XYZGRID_USE_DB_PROTOTYPES

_CACHE_DIR = settings.CACHE_DIR
_LOADED_PROTOTYPES = None
_XYZROOMCLASS = None

MAP_DATA_KEYS = ["zcoord", "map", "legend", "prototypes", "options", "module_path"]

DEFAULT_LEGEND = xymap_legend.LEGEND

# --------------------------------------------
# Map parser implementation


class XYMap:
    r"""
    This represents a single map of interconnected nodes/rooms, parsed from a ASCII map
    representation.

    Each room is connected to each other as a directed graph with optional 'weights' between the the
    connections. It is created from a map string with symbols describing the topological layout. It
    also provides pathfinding using the Dijkstra algorithm.

    The map-string is read from a string or from a module.  The grid area of the string is marked by
    two `+` characters - one in the top left of the area and the other in the bottom left.
    The grid starts two spaces/lines in from the 'open box' created by these two markers and extend
    any width to the right.
    Any other markers or comments can be added outside of the grid - they will be ignored.  Every
    grid coordinate must always be separated by exactly one space/line since the space between
    are used for links.
    ::
        '''
                               1 1 1
         + 0 1 2 3 4 5 6 7 8 9 0 1 2 ...

         4       #         #   #
                 |          \ /
         3     #-#-#     #   #
               |          \ /
         2     #-#-#       #
               |x|x|       |
         1     #-#-#-#-#-#-#
              /
         0 #-#

         + 0 1 2 3 4 5 6 7 8 9 1 1 1 ...
                               0 1 2
        '''

    So origo (0,0) is in the bottom-left and north is +y movement, south is -y movement
    while east/west is +/- x movement as expected. Adding numbers to axes is optional
    but recommended for readability!

    """
    mapcorner_symbol = "+"
    max_pathfinding_length = 500
    empty_symbol = " "
    # we normally only accept one single character for the legend key
    legend_key_exceptions = "\\"

    def __init__(self, map_module_or_dict, Z="map", xyzgrid=None):
        """
        Initialize the map parser by feeding it the map.

        Args:
            map_module_or_dict (str, module or dict): Path or module pointing to a map. If a dict,
                this should be a dict with a MAP_DATA key 'map' and optionally a 'legend'
                dicts to specify the map structure.
            Z (int or str, optional): Name or Z-coord for for this map. Needed if the game uses
                more than one map. If not given, it can also be embedded in the
                `map_module_or_dict`. Used when referencing this map during map transitions,
                baking of pathfinding matrices etc.
            xyzgrid (.xyzgrid.XYZgrid): A top-level grid this map is a part of.

        Notes:
            Interally, the map deals with two sets of coordinate systems:
            - grid-coordinates x,y are the character positions in the map string.
            - world-coordinates X,Y are the in-world coordinates of nodes/rooms.
              There are fewer of these since they ignore the 'link' spaces between
              the nodes in the grid, s

                  X = x // 2
                  Y = y // 2

            - The Z-coordinate, if given, is only used when transitioning between maps
              on the supplied `grid`.

        """
        global _LOADED_PROTOTYPES
        if not _LOADED_PROTOTYPES:
            # inject default prototypes, but don't override prototype-keys loaded from
            # settings, if they exist (that means the user wants to replace the defaults)
            protlib.load_module_prototypes(
                "evennia.contrib.grid.xyzgrid.prototypes", override=False
            )
            _LOADED_PROTOTYPES = True

        self.Z = Z
        self.xyzgrid = xyzgrid

        self.mapstring = ""
        self.raw_mapstring = ""

        # store so we can reload
        self.map_module_or_dict = map_module_or_dict

        self.prototypes = None
        self.options = None

        # transitional mapping
        self.symbol_map = None

        # map setup
        self.xygrid = None
        self.XYgrid = None
        self.display_map = None
        self.max_x = 0
        self.max_y = 0
        self.max_X = 0
        self.max_Y = 0

        # Dijkstra algorithm variables
        self.node_index_map = None
        self.dist_matrix = None
        self.pathfinding_routes = None

        self.pathfinder_baked_filename = None
        if Z:
            if not isdir(_CACHE_DIR):
                mkdir(_CACHE_DIR)
            self.pathfinder_baked_filename = pathjoin(_CACHE_DIR, f"{Z}.P")

        # load data and parse it
        self.reload()

    def __str__(self):
        """
        Print the string representation of the map.
        Since the y-axes origo is at the bottom, we must flip the
        y-axis before printing (since printing is always top-to-bottom).

        """
        return "\n".join("".join(line) for line in self.display_map[::-1])

    def __repr__(self):
        nnodes = 0
        if self.node_index_map:
            nnodes = len(self.node_index_map)
        return f"<XYMap(Z={self.Z}), {self.max_X + 1}x{self.max_Y + 1}, {nnodes} nodes>"

    def log(self, msg):
        if self.xyzgrid:
            self.xyzgrid.log(msg)
        else:
            logger.log_info(msg)

    def reload(self, map_module_or_dict=None):
        """
        (Re)Load a map.

        Args:
            map_module_or_dict (str, module or dict, optional): See description for the variable
                in the class' `__init__` function. If given, replace the already loaded
                map with a new one. If not given, the existing one given on class creation
                will be reloaded.
            parse (bool, optional): If set, auto-run `.parse()` on the newly loaded data.

        Notes:
            This will both (re)load the data and parse it into a new map structure, replacing any
            existing one. The valid mapstructure is:
            ::

                {
                    "map": <str>,
                    "zcoord": <int or str>, # optional
                    "legend": <dict>,       # optional
                    "prototypes": <dict>    # optional
                    "options": <dict>       # optional
                }

        """
        if not map_module_or_dict:
            map_module_or_dict = self.map_module_or_dict

        mapdata = {}
        if isinstance(map_module_or_dict, dict):
            # map-structure provided directly
            mapdata = map_module_or_dict
        else:
            # read from contents of module
            mod = mod_import(map_module_or_dict)
            mapdata_list = variable_from_module(mod, "XYMAP_DATA_LIST")
            if mapdata_list and self.Z:
                # use the stored Z value to figure out which map data we want
                mapping = {mapdata.get("zcoord") for mapdata in mapdata_list}
                mapdata = mapping.get(self.Z, {})

            if not mapdata:
                mapdata = variable_from_module(mod, "XYMAP_DATA")

        if not mapdata:
            raise MapError(
                "No valid XYMAP_DATA or XYMAP_DATA_LIST could be found from "
                f"{map_module_or_dict}."
            )

        # validate
        if any(key for key in mapdata if key not in MAP_DATA_KEYS):
            raise MapError(
                f"Mapdata has keys {list(mapdata)}, but only " f"keys {MAP_DATA_KEYS} are allowed."
            )

        for key in mapdata.get("legend", DEFAULT_LEGEND):
            if not key or len(key) > 1:
                if key not in self.legend_key_exceptions:
                    raise MapError(
                        f"Map-legend key '{key}' is invalid: All keys must "
                        "be exactly one character long. Use the node/link's "
                        "`.display_symbol` property to change how it is "
                        "displayed."
                    )
        if "map" not in mapdata or not mapdata["map"]:
            raise MapError("No map found. Add 'map' key to map-data dict.")
        for key, prototype in mapdata.get("prototypes", {}).items():
            if not (is_iter(key) and (2 <= len(key) <= 3)):
                raise MapError(
                    f"Prototype override key {key} is malformed: It must be a "
                    "coordinate (X, Y) for nodes or (X, Y, direction) for links; "
                    "where direction is a supported direction string ('n', 'ne', etc)."
                )

        # store/update result
        self.Z = mapdata.get("zcoord", self.Z)
        self.mapstring = mapdata["map"]
        self.prototypes = mapdata.get("prototypes", {})
        self.options = mapdata.get("options", {})

        # merge the custom legend onto the default legend to allow easily
        # overriding only parts of it
        self.legend = {**DEFAULT_LEGEND, **map_module_or_dict.get("legend", DEFAULT_LEGEND)}

        # initialize any prototypes on the legend entities
        for char, node_or_link_class in self.legend.items():
            prototype = node_or_link_class.prototype
            if not prototype or isinstance(prototype, dict):
                # nothing more to do
                continue
            # we need to load the prototype dict onto each for ease of access. Note that
            proto = protlib.search_prototype(
                prototype, require_single=True, no_db=_NO_DB_PROTOTYPES
            )[0]
            node_or_link_class.prototype = proto

    def parse(self):
        """
        Parses the numerical grid from the string. The first pass means parsing out
        all nodes. The linking-together of nodes is not happening until the second pass
        (the reason for this is that maps can also link to other maps, so all maps need
        to have gone through their first parsing-passes before they can be linked together).

        See the class docstring for details of how the grid should be defined.

        Notes:
            In this parsing, the 'xygrid' is the full range of chraracters read from
            the string. The `XYgrid` is used to denote the game-world coordinates
            (which doesn't include the links)

        """
        mapcorner_symbol = self.mapcorner_symbol
        # this allows for string-based [x][y] mapping with arbitrary objects
        xygrid = defaultdict(dict)
        # mapping nodes to real X,Y positions
        XYgrid = defaultdict(dict)
        # needed by pathfinder
        node_index_map = {}
        # used by transitions
        symbol_map = defaultdict(list)

        mapstring = self.mapstring
        if mapstring.count(mapcorner_symbol) < 2:
            raise MapParserError(
                f"The mapstring must have at least two '{mapcorner_symbol}' "
                "symbols marking the upper- and bottom-left corners of the "
                "grid area."
            )

        # find the the position (in the string as a whole) of the top-left corner-marker
        maplines = mapstring.split("\n")
        topleft_marker_x, topleft_marker_y = -1, -1
        for topleft_marker_y, line in enumerate(maplines):
            topleft_marker_x = line.find(mapcorner_symbol)
            if topleft_marker_x != -1:
                break
        if -1 in (topleft_marker_x, topleft_marker_y):
            raise MapParserError(f"No top-left corner-marker ({mapcorner_symbol}) found!")

        # find the position (in the string as a whole) of the bottom-left corner-marker
        # this is always in a stright line down from the first marker
        botleft_marker_x, botleft_marker_y = topleft_marker_x, -1
        for botleft_marker_y, line in enumerate(maplines[topleft_marker_y + 1 :]):
            if line.find(mapcorner_symbol) == topleft_marker_x:
                break
        if botleft_marker_y == -1:
            raise MapParserError(
                f"No bottom-left corner-marker ({mapcorner_symbol}) found! "
                "Make sure it lines up with the top-left corner-marker "
                f"(found at column {topleft_marker_x} of the string)."
            )
        # the actual coordinate is dy below the topleft marker so we need to shift
        botleft_marker_y += topleft_marker_y + 1

        # in-string_position of the top- and bottom-left grid corners (2 steps in from marker)
        # the bottom-left corner is also the origo (0,0) of the grid.
        topleft_y = topleft_marker_y + 2
        origo_x, origo_y = botleft_marker_x + 2, botleft_marker_y - 1

        # highest actually filled grid points
        max_x = 0
        max_y = 0
        max_X = 0
        max_Y = 0
        node_index = -1

        # first pass: read string-grid (left-right, bottom-up) and parse all grid points
        for iy, line in enumerate(reversed(maplines[topleft_y:origo_y])):
            even_iy = iy % 2 == 0
            for ix, char in enumerate(line[origo_x:]):
                # from now on, coordinates are on the xygrid.

                if char == self.empty_symbol:
                    continue

                # only set this if there's actually something on the line
                max_x, max_y = max(max_x, ix), max(max_y, iy)

                mapnode_or_link_class = self.legend.get(char)
                if not mapnode_or_link_class:
                    raise MapParserError(
                        f"Symbol '{char}' on XY=({ix / 2:g},{iy / 2:g}) " "is not found in LEGEND."
                    )
                if hasattr(mapnode_or_link_class, "node_index"):
                    # A mapnode. Mapnodes can only be placed on even grid positions, where
                    # there are integer X,Y coordinates defined.

                    if not (even_iy and ix % 2 == 0):
                        raise MapParserError(
                            f"Symbol '{char}' on XY=({ix / 2:g},{iy / 2:g}) marks a "
                            "MapNode but is located between integer (X,Y) positions (only "
                            "Links can be placed between coordinates)!"
                        )

                    # save the node to several different maps for different uses
                    # in both coordinate systems
                    iX, iY = ix // 2, iy // 2
                    max_X, max_Y = max(max_X, iX), max(max_Y, iY)
                    node_index += 1

                    xygrid[ix][iy] = XYgrid[iX][iY] = node_index_map[
                        node_index
                    ] = mapnode_or_link_class(
                        x=ix, y=iy, Z=self.Z, node_index=node_index, symbol=char, xymap=self
                    )

                else:
                    # we have a link at this xygrid position (this is ok everywhere)
                    xygrid[ix][iy] = mapnode_or_link_class(
                        x=ix, y=iy, Z=self.Z, symbol=char, xymap=self
                    )

                # store the symbol mapping for transition lookups
                symbol_map[char].append(xygrid[ix][iy])

        # store before building links
        self.max_x, self.max_y = max_x, max_y
        self.max_X, self.max_Y = max_X, max_Y
        self.xygrid = xygrid
        self.XYgrid = XYgrid
        self.node_index_map = node_index_map
        self.symbol_map = symbol_map

        # build all links
        for node in node_index_map.values():
            node.build_links()

        # build display map
        display_map = [[" "] * (max_x + 1) for _ in range(max_y + 1)]
        for ix, ydct in xygrid.items():
            for iy, node_or_link in ydct.items():
                display_map[iy][ix] = node_or_link.get_display_symbol()

        for node in node_index_map.values():
            # override node-prototypes, ignore if no prototype
            # is defined (some nodes should not be spawned)
            if node.prototype:
                node_coord = (node.X, node.Y)
                # load prototype from override, or use default
                try:
                    node.prototype = flatten_prototype(
                        self.prototypes.get(
                            node_coord, self.prototypes.get(("*", "*"), node.prototype)
                        ),
                        no_db=_NO_DB_PROTOTYPES,
                    )
                except Exception as err:
                    raise MapParserError(f"Room prototype malformed: {err}", node)
                # do the same for links (x, y, direction) coords
                for direction, maplink in node.first_links.items():
                    try:
                        maplink.prototype = flatten_prototype(
                            self.prototypes.get(
                                node_coord + (direction,),
                                self.prototypes.get(("*", "*", "*"), maplink.prototype),
                            ),
                            no_db=_NO_DB_PROTOTYPES,
                        )
                    except Exception as err:
                        raise MapParserError(f"Exit prototype malformed: {err}", maplink)

        # store
        self.display_map = display_map

    def _get_topology_around_coord(self, xy, dist=2):
        """
        Get all links and nodes up to a certain distance from an XY coordinate.

        Args:
            xy (tuple), the X,Y coordinate of the center point.
            dist (int): How many nodes away from center point to find paths for.

        Returns:
            tuple: A tuple of 5 elements `(xy_coords, xmin, xmax, ymin, ymax)`, where the
                first element is a list of xy-coordinates (on xygrid) for all linked nodes within
                range. This is meant to be used with the xygrid for extracting a subset
                for display purposes. The others are the minimum size of the rectangle
                surrounding the area containing `xy_coords`.

        Notes:
            This performs a depth-first pass down the the given dist.

        """

        def _scan_neighbors(
            start_node, points, dist=2, xmin=BIGVAL, ymin=BIGVAL, xmax=0, ymax=0, depth=0
        ):

            x0, y0 = start_node.x, start_node.y
            points.append((x0, y0))
            xmin, xmax = min(xmin, x0), max(xmax, x0)
            ymin, ymax = min(ymin, y0), max(ymax, y0)

            if depth < dist:
                # keep stepping
                for direction, end_node in start_node.links.items():
                    x, y = x0, y0
                    for link in start_node.xy_steps_to_node[direction]:
                        x, y = link.x, link.y
                        points.append((x, y))
                        xmin, xmax = min(xmin, x), max(xmax, x)
                        ymin, ymax = min(ymin, y), max(ymax, y)

                    points, xmin, xmax, ymin, ymax = _scan_neighbors(
                        end_node,
                        points,
                        dist=dist,
                        xmin=xmin,
                        ymin=ymin,
                        xmax=xmax,
                        ymax=ymax,
                        depth=depth + 1,
                    )

            return points, xmin, xmax, ymin, ymax

        center_node = self.get_node_from_coord(xy)
        points, xmin, xmax, ymin, ymax = _scan_neighbors(center_node, [], dist=dist)
        return list(set(points)), xmin, xmax, ymin, ymax

    def calculate_path_matrix(self, force=False):
        """
        Solve the pathfinding problem using Dijkstra's algorithm. This will try to
        load the solution from disk if possible.

        Args:
            force (bool, optional): If the cache should always be rebuilt.

        """
        if not force and self.pathfinder_baked_filename and isfile(self.pathfinder_baked_filename):
            # check if the solution for this grid was already solved previously.

            mapstr, dist_matrix, pathfinding_routes = "", None, None
            with open(self.pathfinder_baked_filename, "rb") as fil:
                try:
                    mapstr, dist_matrix, pathfinding_routes = pickle.load(fil)
                except Exception:
                    logger.log_trace()
            if (
                mapstr == self.mapstring
                and dist_matrix is not None
                and pathfinding_routes is not None
            ):
                # this is important - it means the map hasn't changed so
                # we can re-use the stored data!
                self.dist_matrix = dist_matrix
                self.pathfinding_routes = pathfinding_routes

        # build a matrix representing the map graph, with 0s as impassable areas

        nnodes = len(self.node_index_map)
        pathfinding_graph = zeros((nnodes, nnodes))
        for inode, node in self.node_index_map.items():
            pathfinding_graph[inode, :] = node.linkweights(nnodes)

        # create a sparse matrix to represent link relationships from each node
        pathfinding_matrix = csr_matrix(pathfinding_graph)

        # solve using Dijkstra's algorithm
        self.dist_matrix, self.pathfinding_routes = dijkstra(
            pathfinding_matrix,
            directed=True,
            return_predecessors=True,
            limit=self.max_pathfinding_length,
        )

        if self.pathfinder_baked_filename:
            # try to cache the results
            with open(self.pathfinder_baked_filename, "wb") as fil:
                pickle.dump(
                    (self.mapstring, self.dist_matrix, self.pathfinding_routes), fil, protocol=4
                )

    def spawn_nodes(self, xy=("*", "*")):
        """
        Convert the nodes of this XYMap into actual in-world rooms by spawning their
        related prototypes in the correct coordinate positions. This must be done *first*
        before spawning links (with `spawn_links` because exits require the target destination
        to exist. It's also possible to only spawn a subset of the map

        Args:
            xy (tuple, optional): An (X,Y) coordinate of node(s). `'*'` acts as a wildcard.

        Examples:
            - `xy=(1, 3) - spawn (1,3) coordinate only.
            - `xy=('*', 1) - spawn all nodes in the first row of the map only.
            - `xy=('*', '*')` - spawn all nodes

        Returns:
            list: A list of nodes that were spawned.

        """
        global _XYZROOMCLASS
        if not _XYZROOMCLASS:
            from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom as _XYZROOMCLASS
        x, y = xy
        wildcard = "*"
        spawned = []

        # find existing nodes, in case some rooms need to be removed
        map_coords = [
            (node.X, node.Y)
            for node in sorted(self.node_index_map.values(), key=lambda n: (n.Y, n.X))
        ]
        for existing_room in _XYZROOMCLASS.objects.filter_xyz(xyz=(x, y, self.Z)):
            roomX, roomY, _ = existing_room.xyz
            if (roomX, roomY) not in map_coords:
                self.log(f"  deleting room at {existing_room.xyz} (not found on map).")
                existing_room.delete()

        # (re)build nodes (will not build already existing rooms)
        for node in sorted(self.node_index_map.values(), key=lambda n: (n.Y, n.X)):
            if (x in (wildcard, node.X)) and (y in (wildcard, node.Y)):
                node.spawn()
                spawned.append(node)
        return spawned

    def spawn_links(self, xy=("*", "*"), nodes=None, directions=None):
        """
        Convert links of this XYMap into actual in-game exits by spawning their related
        prototypes. It's possible to only spawn a specic exit by specifying the node and

        Args:
            xy (tuple, optional): An (X,Y) coordinate of node(s). `'*'` acts as a wildcard.
            nodes (list, optional): If given, only consider links out of these nodes. This also
                affects `xy`, so that if there are no nodes of given coords in `nodes`, no
                links will be spawned at all.
            directions (list, optional): A list of cardinal directions ('n', 'ne' etc). If given,
                sync only the exit in the given directions (`xy` limits which links out of which
                nodes should be considered). If unset, there are no limits to directions.
        Examples:
            - `xy=(1, 3 )`, `direction='ne'` - sync only the north-eastern exit
                out of the (1, 3) node.

        """
        x, y = xy
        wildcard = "*"

        if not nodes:
            nodes = sorted(self.node_index_map.values(), key=lambda n: (n.Z, n.Y, n.X))

        for node in nodes:
            if (x in (wildcard, node.X)) and (y in (wildcard, node.Y)):
                node.spawn_links(directions=directions)

    def get_node_from_coord(self, xy):
        """
        Get a MapNode from a coordinate.

        Args:
            xy (tuple): X,Y coordinate on XYgrid.

        Returns:
            MapNode: The node found at the given coordinates. Returns
                `None` if there is no mapnode at the given coordinate.

        Raises:
            MapError: If trying to specify an iX,iY outside
                of the grid's maximum bounds.

        """
        if not self.XYgrid:
            self.parse()

        iX, iY = xy
        if not ((0 <= iX <= self.max_X) and (0 <= iY <= self.max_Y)):
            raise MapError(
                f"get_node_from_coord got coordinate {xy} which is "
                f"outside the grid size of (0,0) - ({self.max_X}, {self.max_Y})."
            )
        try:
            return self.XYgrid[iX][iY]
        except KeyError:
            return None

    def get_components_with_symbol(self, symbol):
        """
        Find all map components (nodes, links) with a given symbol in this map.

        Args:
            symbol (char): A single character-symbol to search for.

        Returns:
            list: A list of MapNodes and/or MapLinks found with the matching symbol.

        """
        return self.symbol_map.get(symbol, [])

    def get_shortest_path(self, start_xy, end_xy):
        """
        Get the shortest route between two points on the grid.

        Args:
            start_xy (tuple): A starting (X,Y) coordinate on the XYgrid (in-game coordinate) for
                where we start from.
            end_xy (tuple or MapNode): The end (X,Y) coordinate on the XYgrid (in-game coordinate)
                we want to find the shortest route to.

        Returns:
            tuple: Two lists, first containing the list of directions as strings (n, ne etc) and
            the second is a mixed list of MapNodes and all MapLinks in a sequence describing
            the full path including the start- and end-node.

        """
        startnode = self.get_node_from_coord(start_xy)
        endnode = self.get_node_from_coord(end_xy)

        if not (startnode and endnode):
            # no node at given coordinate. No path is possible.
            return [], []

        try:
            istartnode = startnode.node_index
            inextnode = endnode.node_index
        except AttributeError:
            raise MapError(
                f"Map.get_shortest_path received start/end nodes {startnode} and "
                f"{endnode}. They must both be MapNodes (not Links)"
            )

        if self.pathfinding_routes is None:
            self.calculate_path_matrix()

        pathfinding_routes = self.pathfinding_routes
        node_index_map = self.node_index_map

        path = [endnode]
        directions = []

        while pathfinding_routes[istartnode, inextnode] != -9999:
            # the -9999 is set by algorithm for unreachable nodes or if trying
            # to go a node we are already at (the start node in this case since
            # we are working backwards).
            inextnode = pathfinding_routes[istartnode, inextnode]
            nextnode = node_index_map[inextnode]
            shortest_route_to = nextnode.shortest_route_to_node[path[-1].node_index]

            directions.append(shortest_route_to[0])
            path.extend(shortest_route_to[1][::-1] + [nextnode])

        # we have the path - reverse to get the correct order
        directions = directions[::-1]
        path = path[::-1]

        return directions, path

    def get_visual_range(
        self,
        xy,
        dist=2,
        mode="nodes",
        character="@",
        target=None,
        target_path_style="|y{display_symbol}|n",
        max_size=None,
        indent=0,
        return_str=True,
    ):
        """
        Get a part of the grid centered on a specific point and extended a certain number
        of nodes or grid points in every direction.

        Args:
            xy (tuple): (X,Y) in-world coordinate location. If this is not the location
                of a node on the grid, the `character` or the empty-space symbol (by default
                an empty space) will be shown.
            dist (int, optional): Number of gridpoints distance to show. Which
                grid to use depends on the setting of `only_nodes`. Set to `None` to
                always show the entire grid.
            mode (str, optional): One of 'scan' or 'nodes'. In 'scan' mode, dist measure
                number of xy grid points in all directions and doesn't care about if visible
                nodes are reachable or not. If 'nodes', distance measure how many linked nodes
                away from the center coordinate to display.
            character (str, optional): Place this symbol at the `xy` position
                of the displayed map. The center node's symbol is shown if this is falsy.
            target (tuple, optional): A target XY coordinate to go to. The path to this
                (or the beginning of said path, if outside of visual range) will be
                marked according to `target_path_style`.
            target_path_style (str or callable, optional): This is use for marking the path
                found when `target` is given. If a string, it accepts a formatting marker
                `display_symbol` which will be filled with the `display_symbol` of each node/link
                the path passes through. This allows e.g. to color the path. If a callable, this
                will receive the MapNode or MapLink object for every step of the path and and
                must return the suitable string to display at the position of the node/link.
            max_size (tuple, optional): A max `(width, height)` to crop the displayed
                return to. Make both odd numbers to get a perfect center. Set either of
                the tuple values to `None` to make that coordinate unlimited. Set entire
                tuple to None let display-size able to grow up to full size of grid.
            indent (int, optional): How far to the right to indent the map area (only
                applies to `return_str=True`).
            return_str (bool, optional): Return result as an already formatted string
                or a 2D list.

        Returns:
            str or list: Depending on value of `return_str`. If a list,
                this is 2D grid of lines, [[str,str,str,...], [...]] where
                each element is a single character in the display grid. To
                extract a character at (ix,iy) coordinate from it, use
                indexing `outlist[iy][ix]` in that order.

        Notes:
            If outputting a list, the y-axis must first be reversed before printing since printing
            happens top-bottom and the y coordinate system goes bottom-up. This can be done simply
            with this before building the final string to send/print.

                printable_order_list = outlist[::-1]

            If mode='nodes', a `dist` of 2 will give the following result in a row of nodes:

               #-#-@----------#-#

            This display may thus visually grow much bigger than expected (both horizontally and
            vertically). consider setting `max_size` if wanting to restrict the display size. Also
            note that link 'weights' are *included* in this estimate, so if links have weights > 1,
            fewer nodes may be found for a given `dist`.

            If mode=`scan`, a dist of 2 on the above example would instead give

                #-@--

            This mode simply shows a cut-out subsection of the map you are on. The `dist` is
            measured on xygrid, so two steps per XY coordinate. It does not consider links or
            weights and may also show nodes not actually reachable at the moment:

                | |
                # @-#

        """
        iX, iY = xy
        # convert inputs to xygrid
        width, height = self.max_x + 1, self.max_y + 1
        ix, iy = max(0, min(iX * 2, width)), max(0, min(iY * 2, height))
        display_map = self.display_map
        xmin, xmax, ymin, ymax = 0, width - 1, 0, height - 1

        if dist is None:
            # show the entire grid
            gridmap = self.display_map
            ixc, iyc = ix, iy

        elif dist is None or dist <= 0 or not self.get_node_from_coord(xy):
            # There is no node at these coordinates. Show
            # nothing but ourselves or emptiness
            return character if character else self.empty_symbol

        elif mode == "nodes":
            # dist measures only full, reachable nodes.
            points, xmin, xmax, ymin, ymax = self._get_topology_around_coord(xy, dist=dist)

            ixc, iyc = ix - xmin, iy - ymin
            # note - override width/height here since our grid is
            # now different from the original for future cropping
            width, height = xmax - xmin + 1, ymax - ymin + 1
            gridmap = [[" "] * width for _ in range(height)]
            for (ix0, iy0) in points:
                gridmap[iy0 - ymin][ix0 - xmin] = display_map[iy0][ix0]

        elif mode == "scan":
            # scan-mode - dist measures individual grid points

            xmin, xmax = max(0, ix - dist), min(width, ix + dist + 1)
            ymin, ymax = max(0, iy - dist), min(height, iy + dist + 1)
            ixc, iyc = ix - xmin, iy - ymin
            gridmap = [line[xmin:xmax] for line in display_map[ymin:ymax]]

        else:
            raise MapError(
                f"Map.get_visual_range 'mode' was '{mode}' "
                "- it must be either 'scan' or 'nodes'."
            )
        if character:
            gridmap[iyc][ixc] = character  # correct indexing; it's a list of lines

        if target:
            # stylize path to target

            def _default_callable(node):
                return target_path_style.format(display_symbol=node.get_display_symbol())

            if callable(target_path_style):
                _target_path_style = target_path_style
            else:
                _target_path_style = _default_callable

            _, path = self.get_shortest_path(xy, target)

            maxstep = dist if mode == "nodes" else dist / 2
            nsteps = 0
            for node_or_link in path[1:]:
                if hasattr(node_or_link, "node_index"):
                    nsteps += 1
                if nsteps > maxstep:
                    break
                # don't decorate current (character?) location
                ix, iy = node_or_link.x, node_or_link.y
                if xmin <= ix <= xmax and ymin <= iy <= ymax:
                    gridmap[iy - ymin][ix - xmin] = _target_path_style(node_or_link)

        if max_size:
            # crop grid to make sure it doesn't grow too far
            max_x, max_y = max_size
            max_x = self.max_x if max_x is None else max_x
            max_y = self.max_y if max_y is None else max_y
            xmin, xmax = max(0, ixc - max_x // 2), min(width, ixc + max_x // 2 + 1)
            ymin, ymax = max(0, iyc - max_y // 2), min(height, iyc + max_y // 2 + 1)
            gridmap = [line[xmin:xmax] for line in gridmap[ymin:ymax]]

        if return_str:
            # we must flip the y-axis before returning the string
            indent = indent * " "
            return indent + f"\n{indent}".join("".join(line) for line in gridmap[::-1])
        else:
            return gridmap
