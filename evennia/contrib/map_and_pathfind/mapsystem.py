r"""
Implement mapping, with path searching.

This builds a map graph based on an ASCII map-string with special, user-defined symbols.

```python
    # in module passed to 'Map' class. It will either a dict
    # MAP_DATA with keys 'map' and (optionally) 'legend', or
    # the MAP/LEGEND variables directly.

    MAP = r'''
                           1
     + 0 1 2 3 4 5 6 7 8 9 0

    10 #
        \
     9   #-#-#-#
         |\    |
     8   #-#-#-#-----#
         |     |
     7   #-#---#-#-#-#-#
         |         |x|x|
     6   o-#-#-#   #-#-#
            \      |x|x|
     5   o---#-#   #-#-#
        /
     4 #
        \
     3   #-#-#-#
             | |
     2       #-#-#-# #
             ^
     1       #-#     #
             |
     0 #-#---o

     + 0 1 2 3 4 5 6 7 8 9 1
                           0

    '''

    LEGEND = {'#': mapsystem.MapNode, '|': mapsystem.NSMapLink,...}

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

The XY positions represent XY positions in the game world. When existing, they are usually
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

See `./example_maps.py` for some empty grid areas to start from.

----
"""
from collections import defaultdict
from scipy.sparse.csgraph import dijkstra
from scipy.sparse import csr_matrix
from scipy import zeros
from evennia.utils.utils import variable_from_module, mod_import


_BIG = 999999999999

_REVERSE_DIRECTIONS = {
    "n": "s",
    "ne": "sw",
    "e": "w",
    "se": "nw",
    "s": "n",
    "sw": "ne",
    "w": "e",
    "nw": "se"
}

_MAPSCAN = {
    "n": (0, 1),
    "ne": (1, 1),
    "e": (1, 0),
    "se": (1, -1),
    "s": (0, -1),
    "sw": (-1, -1),
    "w": (-1, 0),
    "nw": (1, -1)
}


class MapError(RuntimeError):
    pass

class MapParserError(MapError):
    pass


class MapNode:
    """
    This represents a 'room' node on the map.

    A node is always located at an (int, int) location
    on the map, even if it actually represents a throughput
    to another node.

    """
    # symbol used in map definition
    symbol = '#'
    # if printing this node should show another symbol. If set
    # to the empty string, use `symbol`.
    display_symbol = ''

    # set during generation, but is also used for identification of the node
    node_index = None

    def __init__(self, x, y, node_index):
        """
        Initialize the mapnode.

        Args:
            x (int): Coordinate on xygrid.
            y (int): Coordinate on xygrid.
            node_index (int): This identifies this node with a running
                index number required for pathfinding.

        """

        self.x = x
        self.y = y

        # XYgrid coordinate
        self.X = x // 2
        self.Y = y // 2

        self.node_index = node_index

        if not self.display_symbol:
            self.display_symbol = self.symbol

        # this indicates linkage in 8 cardinal directions on the string-map,
        # n,ne,e,se,s,sw,w,nw and link that to a node (always)
        self.links = {}
        # this maps
        self.weights = {}
        # lowest direction to a given neighbor
        self.cheapest_to_node = {}

    def build_links(self, xygrid):
        """
        Start tracking links in all cardinal directions to
        tie this to another node.

        Args:
            xygrid (dict): A 2d dict-of-dicts with x,y coordinates as keys and nodes as values.

        """
        # we must use the xygrid coordinates
        x, y = self.x, self.y

        # scan in all directions for links
        for direction, (dx, dy) in _MAPSCAN.items():

            # note that this is using the string-coordinate system, not the room-one,
            # - there are two string coordinates (node + link) per room coordinate
            # hence we can step in integer steps
            lx, ly = x + dx, y + dy

            if lx in xygrid and ly in xygrid[lx]:
                link = xygrid[lx][ly]
                # just because there is a link here, doesn't mean it's
                # connected to this node. If so the `end_node` will be None.

                end_node, weight = link.traverse(_REVERSE_DIRECTIONS[direction], xygrid)
                if end_node:
                    # the link could be followed to an end node!
                    node_index = end_node.node_index
                    self.links[direction] = end_node
                    self.weights[node_index] = weight

                    cheapest = self.cheapest_to_node.get(node_index, ("", _BIG))[1]
                    if weight < cheapest:
                        self.cheapest_to_node[node_index] = (direction, weight)

    def linkweights(self, nnodes):
        """
        Retrieve all the weights for the direct links to all other nodes.

        Args:
            nnodes (int): The total number of nodes

        Returns:
            scipy.array: Array of weights of the direct links to other nodes.
                The weight will be 0 for nodes not directly connected to one another.

        Notes:
            A node can at most have 8 connections (the cardinal directions).

        """
        link_graph = zeros(nnodes)
        for node_index, weight in self.weights.items():
            link_graph[node_index] = weight
        return link_graph

    def get_cheapest_link_to(self, node):
        """
        Get the cheapest path to a node (there may be several possible).

        Args:
            node (MapNode): The node to get to.

        Returns:
            str: The direction (nw, se etc) to get to that node in the cheapest way.

        """
        return self.cheapest_to_node[node.node_index][0]


class MapLink:
    """
    This represents a link between up to 8 nodes. A link is always
    located on a (.5, .5) location on the map like (1.5, 2.5).

    Each link has a 'weight' from 1...inf, whis indicates how 'slow'
    it is to traverse that link. This is used by the Dijkstra algorithm
    to find the 'fastest' route to a point. By default this weight is 1
    for every link, but a locked door, terrain etc could increase this
    and have the algorithm prefer to use another route.

    It is usually bidirectional, but could also be one-directional.
    It is also possible for a link to have some sort of blockage, like
    a door.

    """
    # link setup
    symbol = "|"
    display_symbol = ""
    # this indicates linkage start:end in 8 cardinal directions on the string-map,
    # n,ne,e,se,s,sw,w,nw. A link is described as {startpos:endpoit}, like connecting
    # the named corners with a line. If the inverse direction is also possible, it
    # must also be specified. So a south-northward, two-way link would be described
    # as {"s": "n", "n": "s"}. The get_directions method can be customized to
    # dynamically modify this during parsing.
    directions = {}
    # this is required for pathfinding. Each weight is defined as {startpos:weight}, where
    # the startpos is the direction of the cell (n,ne etc) where the link *starts*. The
    # weight is a value > 0, smaller than _BIG. The get_directions method can be
    # customized to modify this during parsing.
    weights = {}
    default_weight = 1
    # This setting only applies if this is the *first* link in a chain of multiple links. Usually,
    # when multiple links are used to tie together two nodes, the default is to average the weight
    # across all links. With this disabled, the weights will be added and a long link will be
    # considered 'longer' by the pathfinder.
    average_long_link_weights = True

    def __init__(self, x, y):
        """
        Initialize the link.

        Args:
            x (int): The xygrid x coordinate
            y (int): The xygrid y coordinate.

        """
        self.x = x
        self.y = y
        if not self.display_symbol:
            self.display_symbol = self.symbol

    def get_visually_connected(self, xygrid, directions=None):
        """
        A helper to get all directions to which there appears to be a
        visual link/node. This does not trace the link and check weights etc.

        Args:
            link (MapLink): Currently active link.
            xygrid (dict): 2D dict with x,y coordinates as keys.
            directions (list, optional): The directions (n, ne etc) to check
                visual connection to.

        Returns:
            dict: Mapping {direction: node_or_link} wherever such was found.

        """
        if not directions:
            directions = _REVERSE_DIRECTIONS
        links = {}
        for direction in directions:
            dx, dy = _MAPSCAN[direction]
            end_x, end_y = self.x + dx, self.y + dy
            if end_x in xygrid and end_y in xygrid[end_x]:
                links[direction] = xygrid[end_x][end_y]
        return links

    def get_directions(self, start_direction, xygrid):
        """
        Hook to override for customizing how the directions are
        determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Returns:
            dict: The directions map {start_direction:end_direction} of
            the link. By default this is just self.directions.

        """
        return self.directions

    def get_weights(self, start_direction, xygrid, current_weight):
        """
        Hook to override for customizing how the weights are determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            xygrid (dict): 2D dict with x,y coordinates as keys.
            current_weight (int): This can have an existing value if
                we are progressing down a multi-step path.

        Returns:
            dict: The directions map {start_direction:weight} of
            the link. By default this is just self.weights

        """
        return self.weights

    def traverse(self, start_direction, xygrid, _weight=0, _linklen=1):
        """
        Recursively traverse a set of links.

        Args:
            start_direction (str): The direction (n, ne etc) from which
                this traversal originates for this link.
            xygrid (dict): 2D dict with x,y coordinates as keys.
        Kwargs:
            _weight (int): Internal use.
            _linklen (int): Internal use.

        Returns:
            tuple: The (node, weight) result of the traversal.

        Raises:
            MapParserError: If a link lead to nowhere.

        """
        # from evennia import set_trace;set_trace()
        end_direction = self.get_directions(start_direction, xygrid).get(start_direction)
        if not end_direction:
            raise MapParserError(f"Link at ({self.x}, {self.y}) was connected to "
                                 f"from {start_direction}, but does not link that way.")

        dx, dy = _MAPSCAN[end_direction]
        end_x, end_y = self.x + dx, self.y + dy
        try:
            next_target = xygrid[end_x][end_y]
        except KeyError:
            raise MapParserError(f"Link at ({self.x}, {self.y}) points to "
                                 f"empty space in direction {end_direction}!")

        _weight += self.get_weights(
            start_direction, xygrid, _weight).get(
                start_direction, self.default_weight)

        if hasattr(next_target, "node_index"):
            # we reached a node, this is the end of the link.
            # we average the weight across all traversed link segments.
            return next_target, (
                _weight / max(1, _linklen) if self.average_long_link_weights else _weight)
        else:
            # we hit another link. Progress recursively.
            return next_target.traverse(
                _REVERSE_DIRECTIONS[end_direction],
                xygrid, _weight=_weight, _linklen=_linklen + 1)


# ----------------------------------
# Default nodes and link classes

class NSMapLink(MapLink):
    symbol = "|"
    directions = {"s": "n", "n": "s"}


class EWMapLink(MapLink):
    symbol = "-"
    directions = {"e": "w", "w": "e"}


class NESWMapLink(MapLink):
    symbol = "/"
    directions = {"ne": "sw", "sw": "ne"}


class SENWMapLink(MapLink):
    symbol = "\\"
    directions = {"se": "nw", "nw": "se"}


class CrossMapLink(MapLink):
    symbol = "x"
    directions = {"ne": "sw", "sw": "ne",
                  "se": "nw", "nw": "se"}


class PlusMapLink(MapLink):
    symbol = "+"
    directions = {"s": "n", "n": "s",
                  "e": "w", "w": "e"}


class NSOneWayMapLink(MapLink):
    symbol = "v"
    directions = {"n": "s"}


class SNOneWayMapLink(MapLink):
    symbol = "^"
    directions = {"s": "n"}


class EWOneWayMapLink(MapLink):
    symbol = "<"
    directions = {"e": "w"}


class WEOneWayMapLink(MapLink):
    symbol = ">"
    directions = {"w": "e"}


class DynamicMapLink(MapLink):
    r"""
    This can be used both on a node position and link position but does not represent a location
    in-game, but is only intended to help link things together. The dynamic link has no visual
    direction so we parse the visual surroundings in the map to see if it's obvious what is
    connected to what. If there are links on carinally opposite sites, these are considered
    pass-throughs. If determining this is not possible, or there is an uneven number of links, an
    error is raised.
    ::
          /
        -o    - this is ok, there can only be one path

         |
        -o-   - this will be assumed to be two links
         |

        \|/
        -o-   - all are passing straight through
        /|\

        -o-   - w-e pass, other is sw-s
        /|

        -o    - invalid
        /|

    """
    symbol = "o"

    def get_directions(self, start_direction, xygrid):
        # get all visually connected links
        directions = {}
        links = list(self.get_visually_connected(xygrid).keys())
        loop_links = links.copy()
        # first get all cross-through links
        for direction in loop_links:
            if _REVERSE_DIRECTIONS[direction] in loop_links:
                directions[direction] = links.pop(direction)

        # check if we have any non-cross-through paths to handle
        if len(links) != 2:
            links = "-".join(links)
            raise MapParserError(
                f"dynamic link at grid ({self.x, self.y}) cannot determine "
                f"where how to connect links leading to/from {links}.")
        directions[links[0]] = links[1]
        directions[links[1]] = links[0]

        return directions


# these are all symbols used for x,y coordinate spots
# at (0,1) etc.
DEFAULT_LEGEND = {
    "#": MapNode,
    "o": MapLink,
    "|": NSMapLink,
    "-": EWMapLink,
    "/": NESWMapLink,
    "\\": SENWMapLink,
    "x": CrossMapLink,
    "+": PlusMapLink,
    "v": NSOneWayMapLink,
    "^": SNOneWayMapLink,
    "<": EWOneWayMapLink,
    ">": WEOneWayMapLink,
}

# --------------------------------------------
# Map parser implementation


class Map:
    r"""
    This represents a map of interconnected nodes/rooms. Each room is connected to each other as a
    directed graph with optional 'weights' between the the connections. It is created from a map
    string with symbols describing the topological layout. It also provides pathfinding using the
    Dijkstra algorithm.

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
    max_pathfinding_length = 1000
    empty_symbol = ' '
    # we normally only accept one single character for the legend key
    legend_key_exceptions = ("\\")

    def __init__(self, map_module_or_dict):
        """
        Initialize the map parser by feeding it the map.

        Args:
            map_module_or_dict (str, module or dict): Path or module pointing to a map. If a dict,
                this should be a dict with a key 'map' and optionally a 'legend'
                dicts to specify the map structure.

        Notes:
            The map deals with two sets of coorinate systems:
            - grid-coordinates x,y are the character positions in the map string.
            - world-coordinates X,Y are the in-world coordinates of nodes/rooms.
              There are fewer of these since they ignore the 'link' spaces between
              the nodes in the grid, so

                  X = x // 2
                  Y = y // 2

        """
        # store so we can reload
        self.map_module_or_dict = map_module_or_dict

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
        self.pathfinding_matrix = None
        self.dist_matrix = None
        self.pathfinding_routes = None

        # load data and parse it
        self.reload()

    def __str__(self):
        return "\n".join("".join(line) for line in self.display_map)

    def _get_node_from_coord(self, X, Y):
        """
        Get a MapNode from a coordinate.

        Args:
            X (int): X-coordinate on XY (game) grid.
            Y (int): Y-coordinate on XY (game) grid.

        Returns:
            MapNode: The node found at the given coordinates.


        """
        if not self.XYgrid:
            self.parse()

        try:
            return self.XYgrid[X][Y]
        except IndexError:
            raise MapError("_get_node_from_coord got coordinate ({x},{y}) which is "
                           "outside the grid size of (0,0) - ({self.width}, {self.height}).")

    def _calculate_path_matrix(self):
        """
        Solve the pathfinding problem using Dijkstra's algorithm.

        """
        nnodes = len(self.node_index_map)

        pathfinding_graph = zeros((nnodes, nnodes))
        # build a matrix representing the map graph, with 0s as impassable areas
        for inode, node in self.node_index_map.items():
            pathfinding_graph[:, inode] = node.linkweights(nnodes)

        # create a sparse matrix to represent link relationships from each node
        pathfinding_matrix = csr_matrix(pathfinding_graph)

        # solve using Dijkstra's algorithm
        self.dist_matrix, self.pathfinding_routes = dijkstra(
            pathfinding_matrix, directed=True,
            return_predecessors=True, limit=1000)

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
            raise MapParserError(f"The mapstring must have at least two '{mapcorner_symbol}' "
                                 "symbols marking the upper- and bottom-left corners of the "
                                 "grid area.")

        # find the the position (in the string as a whole) of the top-left corner-marker
        maplines = mapstring.split("\n")
        topleft_marker_x, topleft_marker_y = -1, -1
        for topleft_marker_y, line in enumerate(maplines):
            topleft_marker_x = line.find(mapcorner_symbol)
            if topleft_marker_x != -1:
                break
        if topleft_marker_x == -1 or topleft_marker_y == -1:
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

        # in-string_position of the top- and bottom-left grid corners (2 steps in from marker)
        # the bottom-left corner is also the origo (0,0) of the grid.
        topleft_y = topleft_marker_y + 2
        origo_x, origo_y = botleft_marker_x + 2, botleft_marker_y + 2

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
                        f"Symbol '{char}' on xygrid position ({ix},{iy}) is not found in LEGEND."
                    )
                if hasattr(mapnode_or_link_class, "node_index"):
                    # A mapnode. Mapnodes can only be placed on even grid positions, where
                    # there are integer X,Y coordinates defined.

                    if not (even_iy and ix % 2 == 0):
                        raise MapParserError(
                            f"Symbol '{char}' (xygrid ({ix},{iy}) marks a Node but is located "
                            "between valid (X,Y) positions!")

                    # save the node to several different maps for different uses
                    # in both coordinate systems
                    iX, iY = ix // 2, iy // 2
                    max_X, max_Y = max(max_X, iX), max(max_Y, iY)
                    node_index += 1

                    xygrid[ix][iy] = XYgrid[iX][iY] = node_index_map[node_index] = \
                        mapnode_or_link_class(node_index=node_index, x=ix, y=iy)

                else:
                    # we have a link at this xygrid position (this is ok everywhere)
                    xygrid[ix][iy] = mapnode_or_link_class(x=ix, y=iy)

        # second pass: Here we loop over all nodes and have them connect to each other
        # via the detected linkages.
        for node in node_index_map.values():
            node.build_links(xygrid)

        # build display map
        display_map = [[" "] * (max_x + 1) for _ in range(max_y + 1)]
        for ix, ydct in xygrid.items():
            for iy, node_or_link in ydct.items():
                display_map[iy][ix] = node_or_link.display_symbol

        # store
        self.max_x, self.max_y = max_x, max_y
        self.xygrid = xygrid

        self.max_X, self.max_Y = max_X, max_Y
        self.XYgrid = XYgrid

        self.node_index_map = node_index_map
        self.display_map = display_map

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
                mapdata['map'] = variable_from_module(mod, "MAP")
                mapdata['legend'] = variable_from_module(mod, "LEGEND", default=DEFAULT_LEGEND)

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

        # store/update result
        self.mapstring = mapdata['map']
        self.legend = map_module_or_dict.get("legend", DEFAULT_LEGEND)

        # process the new(?) data
        self._parse()

    def get_shortest_path(self, startcoord, endcoord):
        """
        Get the shortest route between two points on the grid.

        Args:
            startcoord (tuple): A starting (X,Y) coordinate on the XYgrid (in-game coordinate) for
                where we start from.
            endcoord (tuple or MapNode): The end (X,Y) coordinate on the XYgrid (in-game coordinate)
                we want to find the shortest route to.

        Returns:
            tuple: Two lists, first one containing the shortest sequence of map nodes to
            traverse and the second a list of directions (n, se etc) describing the path.

        """
        istartnode = self._get_node_from_coord(*startcoord).node_index
        endnode = self._get_node_from_coord(*endcoord)

        if not self.pathfinding_routes:
            self._calculate_path_matrix()

        pathfinding_routes = self.pathfinding_routes
        node_index_map = self.node_index_map

        nodepath = [endnode]
        linkpath = []
        inextnode = endnode.node_index

        while pathfinding_routes[istartnode, inextnode] != -9999:
            # the -9999 is set by algorithm for unreachable nodes or end-node
            inextnode = pathfinding_routes[istartnode, inextnode]
            nodepath.append(node_index_map[inextnode])
            linkpath.append(nodepath[-1].get_cheapest_link_to(nodepath[-2]))

        # we have the path - reverse to get the correct order
        nodepath = nodepath[::-1]
        linkpath = linkpath[::-1]

        return nodepath, linkpath

    def get_map_display(self, coord, dist=2, character='@', return_str=True):
        """
        Display the map centered on a point and everything around it within a certain distance.

        Args:
            coord (tuple): (X,Y) in-world coordinate location.
            dist (int, optional): Number of gridpoints distance to show.
                A value of 2 will show adjacent nodes, a value
                of 1 will only show links from current node. If this is None,
                show entire map centered on iX,iY.
            character (str, optional): Place this symbol at the `coord` position
                of the displayed map. Ignored if falsy.
            return_str (bool, optional): Return result as an
                already formatted string.

        Returns:
            str or list: Depending on value of `return_str`. If a list,
                this is 2D grid of lines, [[str,str,str,...], [...]] where
                each element is a single character in the display grid. To
                extract a character at (ix,iy) coordinate from it, use
                indexing `outlist[iy][ix]` in that order.

        """
        iX, iY = coord
        # convert inputs to xygrid
        width, height = self.max_x + 1, self.max_y + 1
        ix, iy = max(0, min(iX * 2, width)), max(0, min(iY * 2, height))

        if dist is None:
            gridmap = self.display_map
            ixc, iyc = ix, iy
        else:
            left, right = max(0, ix - dist), min(width, ix + dist + 1)
            bottom, top = max(0, iy - dist), min(height, iy + dist + 1)
            ixc, iyc = ix - left, iy - bottom
            gridmap = [line[left:right] for line in self.display_map[bottom:top]]

        if character:
            gridmap[iyc][ixc] = character  # correct indexing; it's a list of lines

        if return_str:
            return "\n".join("".join(line) for line in gridmap)
        else:
            return gridmap
