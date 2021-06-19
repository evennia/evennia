r"""
# Map

The `Map` class represents one XY-grid of interconnected map-legend components. It's built from an
ASCII representation, where unique characters represents each type of component. The Map parses the
map into an internal graph that can be efficiently used for pathfinding the shortest route between
any two nodes (rooms).

Each room (MapNode) can have exits (links) in 8 cardinal directions (north, northwest etc) as well
as up and down. These are indicated in code as 'n', 'ne', 'e', 'se', 's', 'sw', 'w',
'nw', 'u' and 'd'.


```python
    # in module passed to 'Map' class. It will either a dict
    # MAP_DATA with keys 'map' and (optionally) 'legend', or
    # the MAP/LEGEND variables directly.

    MAP = r'''
                           1
     + 0 1 2 3 4 5 6 7 8 9 0

    10 #   # # #     #
        \  I I I     d
     9   #-#-#-#     |
         |\    |     u
     8   #-#-#-#-----#-----o
         |     |           |
     7   #-#---#-#-#-#-#   |
         |         |x|x|   |
     6   o-#-#-#   #-#-#-#-#
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

    # optional, for more control
    MAP_DATA = {
        "map": MAP,
        "legend": LEGEND,
    }

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

See `./map_example.py` for some empty grid areas to start from.

----
"""
import pickle
from collections import defaultdict
from os import mkdir
from os.path import isdir, isfile, join as pathjoin

try:
    from scipy.sparse.csgraph import dijkstra
    from scipy.sparse import csr_matrix
    from scipy import zeros
except ImportError as err:
    raise ImportError(
        f"{err}\nThe XYZgrid contrib requires "
        "the SciPy package. Install with `pip install scipy'.")
from django.conf import settings
from evennia.utils.utils import variable_from_module, mod_import
from evennia.utils import logger

from .utils import MapError, MapParserError, BIGVAL
from . import map_legend

_CACHE_DIR = settings.CACHE_DIR


# these are all symbols used for x,y coordinate spots
DEFAULT_LEGEND = {
    "#": map_legend.BasicMapNode,
    "I": map_legend.InterruptMapNode,
    "|": map_legend.NSMapLink,
    "-": map_legend.EWMapLink,
    "/": map_legend.NESWMapLink,
    "\\": map_legend.SENWMapLink,
    "x": map_legend.CrossMapLink,
    "+": map_legend.PlusMapLink,
    "v": map_legend.NSOneWayMapLink,
    "^": map_legend.SNOneWayMapLink,
    "<": map_legend.EWOneWayMapLink,
    ">": map_legend.WEOneWayMapLink,
    "o": map_legend.RouterMapLink,
    "u": map_legend.UpMapLink,
    "d": map_legend.DownMapLink,
    "b": map_legend.BlockedMapLink,
    "i": map_legend.InterruptMapLink,
    't': map_legend.TeleporterMapLink,
    'T': map_legend.MapTransitionLink,
}

# --------------------------------------------
# Map parser implementation


class SingleMap:
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
    mapcorner_symbol = '+'
    max_pathfinding_length = 500
    empty_symbol = ' '
    # we normally only accept one single character for the legend key
    legend_key_exceptions = ("\\")

    def __init__(self, map_module_or_dict, name="map", other_maps=None):
        """
        Initialize the map parser by feeding it the map.

        Args:
            map_module_or_dict (str, module or dict): Path or module pointing to a map. If a dict,
                this should be a dict with a MAP_DATA key 'map' and optionally a 'legend'
                dicts to specify the map structure.
            name (str, optional): Unique identifier for this map. Needed if the game uses
                more than one map. Used when referencing this map during map transitions,
                baking of pathfinding matrices etc. This will be overridden by any 'name' given
                in the MAP_DATA itself.
            other_maps (dict, optional): Reference to mapping {name: SingleMap, ...} representing
                all possible maps one could potentially reach from this map. This is usually
                provided by the MutlMap handler.

        Notes:
            The map deals with two sets of coorinate systems:
            - grid-coordinates x,y are the character positions in the map string.
            - world-coordinates X,Y are the in-world coordinates of nodes/rooms.
              There are fewer of these since they ignore the 'link' spaces between
              the nodes in the grid, so

                  X = x // 2
                  Y = y // 2

        """
        self.name = name

        self.mapstring = ""

        # store so we can reload
        self.map_module_or_dict = map_module_or_dict

        self.other_maps = other_maps
        self.room_prototypes = None

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
        if name:
            if not isdir(_CACHE_DIR):
                mkdir(_CACHE_DIR)
            self.pathfinder_baked_filename = pathjoin(_CACHE_DIR, f"{name}.P")

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
        return f"<Map {self.max_X + 1}x{self.max_Y + 1}, {len(self.node_index_map)} nodes>"

    def _parse(self):
        """
        Parses the numerical grid from the string. The result of this is a 2D array
        of [[MapNode,...], [MapNode, ...]] with MapLinks inside them describing their
        linkage to other nodes. See the class docstring for details of how the grid
        should be defined.

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

        mapstring = self.mapstring
        if mapstring.count(mapcorner_symbol) < 2:
            raise MapParserError(
                f"The mapstring must have at least two '{mapcorner_symbol}' "
                "symbols marking the upper- and bottom-left corners of the "
                "grid area.")

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
        for botleft_marker_y, line in enumerate(maplines[topleft_marker_y + 1:]):
            if line.find(mapcorner_symbol) == topleft_marker_x:
                break
        if botleft_marker_y == -1:
            raise MapParserError(f"No bottom-left corner-marker ({mapcorner_symbol}) found! "
                                 "Make sure it lines up with the top-left corner-marker "
                                 f"(found at column {topleft_marker_x} of the string).")
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
                        f"Symbol '{char}' on XY=({ix / 2:g},{iy / 2:g}) "
                        "is not found in LEGEND."
                    )
                if hasattr(mapnode_or_link_class, "node_index"):
                    # A mapnode. Mapnodes can only be placed on even grid positions, where
                    # there are integer X,Y coordinates defined.

                    if not (even_iy and ix % 2 == 0):
                        raise MapParserError(
                            f"Symbol '{char}' on XY=({ix / 2:g},{iy / 2:g}) marks a "
                            "MapNode but is located between integer (X,Y) positions (only "
                            "Links can be placed between coordinates)!")

                    # save the node to several different maps for different uses
                    # in both coordinate systems
                    iX, iY = ix // 2, iy // 2
                    max_X, max_Y = max(max_X, iX), max(max_Y, iY)
                    node_index += 1

                    xygrid[ix][iy] = XYgrid[iX][iY] = node_index_map[node_index] = \
                        mapnode_or_link_class(node_index=node_index, x=ix, y=iy)

                else:
                    # we have a link at this xygrid position (this is ok everywhere)
                    xygrid[ix][iy] = mapnode_or_link_class(ix, iy)

        # second pass: Here we loop over all nodes and have them connect to each other
        # via the detected linkages.
        for node in node_index_map.values():
            node.scan_all_directions(xygrid)

        # build display map
        display_map = [[" "] * (max_x + 1) for _ in range(max_y + 1)]
        for ix, ydct in xygrid.items():
            for iy, node_or_link in ydct.items():
                display_map[iy][ix] = node_or_link.get_display_symbol(xygrid, mapinstance=self)

        if self.room_prototypes:
            # validate that prototypes are actually all represented by a node on the grid.
            node_positions = []
            for node in node_index_map:
                # check so every node has a prototype
                node_coord = (node.X, node.Y)
                node_positions.append(node_coord)
                if node_coord not in self.room_prototypes:
                    raise MapParserError(
                        f"Symbol '{char}' on XY=({node_coord[0]},{node_coord[1]}) has "
                        "no corresponding entry in the `rooms` prototype dictionary."
                    )
                for (iX, iY) in self.room_prototypes:
                    # also check in the reverse direction - so every prototype has a node
                    if (iX, iY) not in node_positions:
                        raise MapParserError(
                            f"There is a room prototype for XY=({iX},{iY}), but that position "
                            "of the map grid lacks a node."
                        )

        # store
        self.max_x, self.max_y = max_x, max_y
        self.xygrid = xygrid

        self.max_X, self.max_Y = max_X, max_Y
        self.XYgrid = XYgrid

        self.node_index_map = node_index_map
        self.display_map = display_map

    def _get_topology_around_coord(self, coord, dist=2):
        """
        Get all links and nodes up to a certain distance from an XY coordinate.

        Args:
            coord (tuple), the X,Y coordinate of the center point.
            dist (int): How many nodes away from center point to find paths for.

        Returns:
            tuple: A tuple of 5 elements `(coords, xmin, xmax, ymin, ymax)`, where the
                first element is a list of xy-coordinates (on xygrid) for all linked nodes within
                range. This is meant to be used with the xygrid for extracting a subset
                for display purposes. The others are the minimum size of the rectangle
                surrounding the area containing `coords`.

        Notes:
            This performs a depth-first pass down the the given dist.

        """
        def _scan_neighbors(start_node, points, dist=2,
                            xmin=BIGVAL, ymin=BIGVAL, xmax=0, ymax=0, depth=0):

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
                        end_node, points, dist=dist,
                        xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax,
                        depth=depth + 1)

            return points, xmin, xmax, ymin, ymax

        center_node = self.get_node_from_coord(coord)
        points, xmin, xmax, ymin, ymax = _scan_neighbors(center_node, [], dist=dist)
        return list(set(points)), xmin, xmax, ymin, ymax

    def _calculate_path_matrix(self):
        """
        Solve the pathfinding problem using Dijkstra's algorithm. This will try to
        load the solution from disk if possible.

        """
        if self.pathfinder_baked_filename and isfile(self.pathfinder_baked_filename):
            # check if the solution for this grid was already solved previously.

            mapstr, dist_matrix, pathfinding_routes = "", None, None
            with open(self.pathfinder_baked_filename, 'rb') as fil:
                try:
                    mapstr, dist_matrix, pathfinding_routes = pickle.load(fil)
                except Exception:
                    logger.log_trace()
            if (mapstr == self.mapstring
                    and dist_matrix is not None
                    and pathfinding_routes is not None):
                # this is important - it means the map hasn't changed so
                # we can re-use the stored data!
                self.dist_matrix = dist_matrix
                self.pathfinding_routes = pathfinding_routes
                return

        # build a matrix representing the map graph, with 0s as impassable areas

        nnodes = len(self.node_index_map)
        pathfinding_graph = zeros((nnodes, nnodes))
        for inode, node in self.node_index_map.items():
            pathfinding_graph[inode, :] = node.linkweights(nnodes)

        # create a sparse matrix to represent link relationships from each node
        pathfinding_matrix = csr_matrix(pathfinding_graph)

        # solve using Dijkstra's algorithm
        self.dist_matrix, self.pathfinding_routes = dijkstra(
            pathfinding_matrix, directed=True,
            return_predecessors=True, limit=self.max_pathfinding_length)

        if self.pathfinder_baked_filename:
            # try to cache the results
            with open(self.pathfinder_baked_filename, 'wb') as fil:
                pickle.dump((self.mapstring, self.dist_matrix, self.pathfinding_routes),
                            fil, protocol=4)

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
            existing one.

        """
        if not map_module_or_dict:
            map_module_or_dict = self.map_module_or_dict

        mapdata = {}
        if isinstance(map_module_or_dict, dict):
            mapdata = map_module_or_dict
        else:
            mod = mod_import(map_module_or_dict)
            mapdata = variable_from_module(mod, "MAP_DATA")
            if not mapdata:
                # try to read mapdata directly from global variables
                mapdata['name'] = variable_from_module(mod, "NAME", default=self.name)
                mapdata['map'] = variable_from_module(mod, "MAP")
                mapdata['legend'] = variable_from_module(mod, "LEGEND", default=DEFAULT_LEGEND)
                mapdata['rooms'] = variable_from_module(mod, "ROOMS")

        # validate
        for key in mapdata.get('legend', DEFAULT_LEGEND):
            if not key or len(key) > 1:
                if key not in self.legend_key_exceptions:
                    raise MapError(f"Map-legend key '{key}' is invalid: All keys must "
                                   "be exactly one character long. Use the node/link's "
                                   "`.display_symbol` property to change how it is "
                                   "displayed.")
        if 'map' not in mapdata or not mapdata['map']:
            raise MapError("No map found. Add 'map' key to map-data (MAP_DATA) dict or "
                           "add variable MAP to a module passed into the parser.")

        self.room_prototypes = mapdata.get('rooms')

        # store/update result
        self.name = mapdata.get('name', self.name)
        self.mapstring = mapdata['map']
        # merge the custom legend onto the default legend to allow easily
        # overriding only parts of it
        self.legend = {**DEFAULT_LEGEND, **map_module_or_dict.get("legend", DEFAULT_LEGEND)}

        # process the new(?) data
        self._parse()

    def get_node_from_coord(self, coords):
        """
        Get a MapNode from a coordinate.

        Args:
            coords (tuple): X,Y coordinates on XYgrid.

        Returns:
            MapNode: The node found at the given coordinates. Returns
                `None` if there is no mapnode at the given coordinate.

        Raises:
            MapError: If trying to specify an iX,iY outside
                of the grid's maximum bounds.

        """
        if not self.XYgrid:
            self.parse()

        iX, iY = coords
        if not ((0 <= iX <= self.max_X) and (0 <= iY <= self.max_Y)):
            raise MapError(f"get_node_from_coord got coordinate {coords} which is "
                           f"outside the grid size of (0,0) - ({self.max_X}, {self.max_Y}).")
        try:
            return self.XYgrid[coords[0]][coords[1]]
        except KeyError:
            return None

    def get_shortest_path(self, startcoord, endcoord):
        """
        Get the shortest route between two points on the grid.

        Args:
            startcoord (tuple): A starting (X,Y) coordinate on the XYgrid (in-game coordinate) for
                where we start from.
            endcoord (tuple or MapNode): The end (X,Y) coordinate on the XYgrid (in-game coordinate)
                we want to find the shortest route to.

        Returns:
            tuple: Two lists, first containing the list of directions as strings (n, ne etc) and
            the second is a mixed list of MapNodes and string-directions in a sequence describing
            the full path including the start- and end-node.

        """
        startnode = self.get_node_from_coord(startcoord)
        endnode = self.get_node_from_coord(endcoord)

        if not (startnode and endnode):
            # no node at given coordinate. No path is possible.
            return [], []

        try:
            istartnode = startnode.node_index
            inextnode = endnode.node_index
        except AttributeError:
            raise MapError(f"Map.get_shortest_path received start/end nodes {startnode} and "
                           f"{endnode}. They must both be MapNodes (not Links)")

        if self.pathfinding_routes is None:
            self._calculate_path_matrix()

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

            if any(1 for step in shortest_route_to[1] if step.interrupt_path):
                # detected an interrupt in linkage - discard what we have so far
                directions = []
                path = [nextnode]

            if nextnode.interrupt_path and nextnode is not startnode:
                directions = []
                path = [nextnode]

        # we have the path - reverse to get the correct order
        directions = directions[::-1]
        path = path[::-1]

        return directions, path

    def get_visual_range(self, coord, dist=2, mode='nodes',
                         character='@',
                         target=None, target_path_style="|y{display_symbol}|n",
                         max_size=None,
                         return_str=True):
        """
        Get a part of the grid centered on a specific point and extended a certain number
        of nodes or grid points in every direction.

        Args:
            coord (tuple): (X,Y) in-world coordinate location. If this is not the location
                of a node on the grid, the `character` or the empty-space symbol (by default
                an empty space) will be shown.
            dist (int, optional): Number of gridpoints distance to show. Which
                grid to use depends on the setting of `only_nodes`. Set to `None` to
                always show the entire grid.
            mode (str, optional): One of 'scan' or 'nodes'. In 'scan' mode, dist measure
                number of xy grid points in all directions and doesn't care about if visible
                nodes are reachable or not. If 'nodes', distance measure how many linked nodes
                away from the center coordinate to display.
            character (str, optional): Place this symbol at the `coord` position
                of the displayed map. The center node' symbol is shown if this is falsy.
            target (tuple, optional): A target XY coordinate to go to. The path to this
                (or the beginning of said path, if outside of visual range) will be
                marked according to `target_path_style`.
            target_path_style (str or callable, optional): This is use for marking the path
                found when `path_to_coord` is given. If a string, it accepts a formatting marker
                `display_symbol` which will be filled with the `display_symbol` of each node/link
                the path passes through. This allows e.g. to color the path. If a callable, this
                will receive the MapNode or MapLink object for every step of the path and and
                must return the suitable string to display at the position of the node/link.
            max_size (tuple, optional): A max `(width, height)` to crop the displayed
                return to. Make both odd numbers to get a perfect center.
                If unset, display-size can grow up to the full size of the grid.
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
        iX, iY = coord
        # convert inputs to xygrid
        width, height = self.max_x + 1, self.max_y + 1
        ix, iy = max(0, min(iX * 2, width)), max(0, min(iY * 2, height))
        display_map = self.display_map
        xmin, xmax, ymin, ymax = 0, width - 1, 0, height - 1

        if dist is None:
            # show the entire grid
            gridmap = self.display_map
            ixc, iyc = ix, iy

        elif dist is None or dist <= 0 or not self.get_node_from_coord(coord):
            # There is no node at these coordinates. Show
            # nothing but ourselves or emptiness
            return character if character else self.empty_symbol

        elif mode == 'nodes':
            # dist measures only full, reachable nodes.
            points, xmin, xmax, ymin, ymax = self._get_topology_around_coord(coord, dist=dist)

            ixc, iyc = ix - xmin, iy - ymin
            # note - override width/height here since our grid is
            # now different from the original for future cropping
            width, height = xmax - xmin + 1, ymax - ymin + 1
            gridmap = [[" "] * width for _ in range(height)]
            for (ix0, iy0) in points:
                gridmap[iy0 - ymin][ix0 - xmin] = display_map[iy0][ix0]

        elif mode == 'scan':
            # scan-mode - dist measures individual grid points

            xmin, xmax = max(0, ix - dist), min(width, ix + dist + 1)
            ymin, ymax = max(0, iy - dist), min(height, iy + dist + 1)
            ixc, iyc = ix - xmin, iy - ymin
            gridmap = [line[xmin:xmax] for line in display_map[ymin:ymax]]

        else:
            raise MapError(f"Map.get_visual_range 'mode' was '{mode}' "
                           "- it must be either 'scan' or 'nodes'.")
        if character:
            gridmap[iyc][ixc] = character  # correct indexing; it's a list of lines

        if target:
            # stylize path to target

            def _default_callable(node):
                return target_path_style.format(
                    display_symbol=node.get_display_symbol(self.xygrid))

            if callable(target_path_style):
                _target_path_style = target_path_style
            else:
                _target_path_style = _default_callable

            _, path = self.get_shortest_path(coord, target)

            maxstep = dist if mode == 'nodes' else dist / 2
            nsteps = 0
            for node_or_link in path[1:]:
                if hasattr(node_or_link, "node_index"):
                    nsteps += 1
                if nsteps >= maxstep:
                    break
                # don't decorate current (character?) location
                ix, iy = node_or_link.x, node_or_link.y
                if xmin <= ix <= xmax and ymin <= iy <= ymax:
                    gridmap[iy - ymin][ix - xmin] = _target_path_style(node_or_link)

        if max_size:
            # crop grid to make sure it doesn't grow too far
            max_x, max_y = max_size
            xmin, xmax = max(0, ixc - max_x // 2), min(width, ixc + max_x // 2 + 1)
            ymin, ymax = max(0, iyc - max_y // 2), min(height, iyc + max_y // 2 + 1)
            gridmap = [line[xmin:xmax] for line in gridmap[ymin:ymax]]

        if return_str:
            # we must flip the y-axis before returning the string
            return "\n".join("".join(line) for line in gridmap[::-1])
        else:
            return gridmap
