r"""
Implement mapping, with path searching.

This builds a map graph based on an ASCII map-string with special, user-defined symbols.

```python
    # in module passed to Map class

    MAP = r'''
                           1
     + 0 1 2 3 4 5 6 7 8 9 0

     0 #
        \
     1   #-#-#-#
         |\    |
     2   #-#-#-#-----#
         |     |
     3   #-#---#-#-#-#-#
         |         |x|x|
     4   o-#-#-#   #-#-#
            \      |x|x|
     5   o---#-#   #-#-#
        /
     6 #
        \
     7   #-#-#-#
             | |
     8       #-#-#-# #
             ^
     9       #-#     #

    10

    '''

    LEGEND = {'#': mapsystem.MapNode, '|': mapsystem.NSMapLink,...}

    # optional, for more control
    MAP_DATA = {
        "map": MAP,
        "legend": LEGEND,
    }

```

The nodes and links can be customized by add your own implementation of `MapNode` or `MapLink` to
the LEGEND dict, mapping them to a particular character symbol.

The single `+` sign in the upper left corner is required and marks the origo of the mapping area and
the 0,0 position will always start one space right and one line down from it. The coordinate axes
numbering is optional, but recommended for readability.

Every x-column should be spaced with one space and the y-rows must have a line between them.

The coordinate positions all corresponds to map 'nodes'. These are usually rooms (which require an
in-game coordinate system to work with the map) but can also be abstract 'link nodes' that links
rooms together and have no in-game equivalence.

All in-between-coordinates positions are reserved for links and no nodes will be detected in those
positions (since it would then not have a proper x,y coordinate).



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
    "n": (0, -1),
    "ne": (1, -1),
    "e": (1, 0),
    "se": (1, 1),
    "s": (0, 1),
    "sw": (-1, 1),
    "w": (-1, 0),
    "nw": (-1, -1)
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
            x (int): X coordinate. This is the actual room coordinate.
            y (int): Y coordinate. This is the actual room coordinate.
            node_index (int): This identifies this node with a running
                index number required for pathfinding.

        """

        self.x = x
        self.y = y
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

    def build_links(self, string_map):
        """
        Start tracking links in all cardinal directions to
        tie this to another node.

        Args:
            string_map (dict): A 2d dict-of-dicts with x,y coordinates as keys and nodes as values.

        """
        # convert room-coordinates back to string-map coordinates
        x, y = self.x * 2, self.y * 2

        # scan in all directions for links
        for direction, (dx, dy) in _MAPSCAN.items():

            # note that this is using the string-coordinate system, not the room-one,
            # - there are two string coordinates (node + link) per room coordinate
            # hence we can step in integer steps
            lx, ly = x + dx, y + dy

            if lx in string_map and ly in string_map[lx]:
                link = string_map[lx][ly]
                # just because there is a link here, doesn't mean it's
                # connected to this node. If so the `end_node` will be None.

                end_node, weight = link.traverse(_REVERSE_DIRECTIONS[direction], string_map)
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
            x (int): The string-grid X coordinate of the link.
            y (int): The string-grid Y coordinate of the link.

        """

        self.x = x
        self.y = y
        if not self.display_symbol:
            self.display_symbol = self.symbol

    def get_visually_connected(self, string_map, directions=None):
        """
        A helper to get all directions to which there appears to be a
        visual link/node. This does not trace the link and check weights etc.

        Args:
            link (MapLink): Currently active link.
            string_map (dict): 2D dict with x,y coordinates as keys.
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
            if end_x in string_map and end_y in string_map[end_x]:
                links[direction] = string_map[end_x][end_y]
        return links

    def get_directions(self, start_direction, string_map):
        """
        Hook to override for customizing how the directions are
        determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            string_map (dict): 2D dict with x,y coordinates as keys.

        Returns:
            dict: The directions map {start_direction:end_direction} of
            the link. By default this is just self.directions.

        """
        return self.directions

    def get_weights(self, start_direction, string_map, current_weight):
        """
        Hook to override for customizing how the weights are determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            string_map (dict): 2D dict with x,y coordinates as keys.
            current_weight (int): This can have an existing value if
                we are progressing down a multi-step path.

        Returns:
            dict: The directions map {start_direction:weight} of
            the link. By default this is just self.weights

        """
        return self.weights

    def traverse(self, start_direction, string_map, _weight=0, _linklen=1):
        """
        Recursively traverse a set of links.

        Args:
            start_direction (str): The direction (n, ne etc) from which
                this traversal originates for this link.
            string_map (dict): 2D dict with x,y coordinates as keys.
        Kwargs:
            _weight (int): Internal use.
            _linklen (int): Internal use.

        Returns:
            tuple: The (node, weight) result of the traversal.

        Raises:
            MapParserError: If a link lead to nowhere.

        """
        # from evennia import set_trace;set_trace()
        end_direction = self.get_directions(start_direction, string_map).get(start_direction)
        if not end_direction:
            raise MapParserError(f"Link at ({self.x}, {self.y}) was connected to "
                                 f"from {start_direction}, but does not link that way.")

        dx, dy = _MAPSCAN[end_direction]
        end_x, end_y = self.x + dx, self.y + dy
        try:
            next_target = string_map[end_x][end_y]
        except KeyError:
            raise MapParserError(f"Link at ({self.x}, {self.y}) points to "
                                 f"empty space in direction {end_direction}!")

        _weight += self.get_weights(
            start_direction, string_map, _weight).get(
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
                string_map, _weight=_weight, _linklen=_linklen + 1)


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

    def get_directions(self, start_direction, string_map):
        # get all visually connected links
        directions = {}
        links = list(self.get_visually_connected(string_map).keys())
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
    "//": SENWMapLink,
    "x": CrossMapLink,
    "+": PlusMapLink,
    "v": NSOneWayMapLink,
    "^": SNOneWayMapLink,
    "<": EWOneWayMapLink,
    ">": WEOneWayMapLink,
}


class Map:
    """
    This represents a map of interconnected nodes/rooms. Each room is connected
    to each other as a directed graph with optional 'weights' between the the
    connections.

    This is a parser that parses a string with an ascii-created map into
    a 2D-array understood by the Dijkstra algorithm.

    The result of this is labeling every node in the tree with a number 0...N.

            The grid should be defined to be as readable as possible and every full coordinat must
            be separated by a space/empty line.  The single `+` in the upper left corner is used to
            tell the parser where the axes cross. The (0,0) point will start one space/line away
            from this point. The strict numbering is optional (the + is all that's needed), but it's
            highly recommended for readability!
            ::
                '''
                                       1 1 1
                 + 0 1 2 3 4 5 6 7 8 9 0 1 2 ...

                 0

                 1

                 2

                 .
                 .

                10

                11

                 .
                 .
                '''

    """
    mapcorner_symbol = '+'
    max_pathfinding_length = 1000
    empty_symbol = ' '

    def __init__(self, map_module_or_dict):
        """
        Initialize the map parser by feeding it the map.

        Args:
            map_module_or_dict (str, module or dict): Path or module pointing to a map. If a dict,
                this should be a dict with a key 'map' and optionally a 'legend'
                dicts to specify the map structure.

        """
        # load data from dict or file
        mapdata = {}
        if isinstance(map_module_or_dict, dict):
            mapdata = map_module_or_dict
        else:
            mod = mod_import(map_module_or_dict)
            mapdata = variable_from_module(mod, "MAP_DATA")
            if not mapdata:
                mapdata['map'] = variable_from_module(mod, "MAP")
                mapdata['legend'] = variable_from_module(mod, "LEGEND", default=DEFAULT_LEGEND)

        self.mapstring = mapdata['map']
        self.legend = map_module_or_dict.get("legend", DEFAULT_LEGEND)

        self.string_map = None
        self.node_map = None
        self.display_map = None
        self.width = 0
        self.height = 0

        # Dijkstra algorithm variables
        self.node_index_map = None
        self.pathfinding_matrix = None
        self.dist_matrix = None
        self.pathfinding_routes = None

        self.parse()

    def __str__(self):
        return "\n".join("".join(line) for line in self.display_map)

    def parse(self):
        """
        Parse the numberical grid in the string. The result of this is a 2D array
        of [[MapNode,...], [MapNode, ...]] with MapLinks inside them describing their
        linkage to other nodes.

        Notes:
        """
        mapcorner_symbol = self.mapcorner_symbol
        # this allows for string-based [x][y] mapping with arbitrary objects
        string_map = defaultdict(dict)
        # needed by pathfinder
        node_index_map = {}
        # mapping nodes to real x,y positions
        node_map = defaultdict(dict)

        mapstring = self.mapstring
        if mapcorner_symbol not in mapstring:
            raise MapParserError("mapstring must have a '+' in the upper left corner to mark "
                                 "the origo of the coordinate system.")

        # find the the (xstring, ystring) position where the corner symbol is
        maplines = mapstring.split("\n")
        mapcorner_x, mapcorner_y = 0, 0
        for mapcorner_y, line in enumerate(maplines):
            mapcorner_x = line.find(mapcorner_symbol)
            if mapcorner_x != -1:
                break

        # in-string_position of (x,y)
        origo_x, origo_y = mapcorner_x + 2, mapcorner_y + 2

        # we have placed the origo, start parsing the grid

        node_index = 0
        maxwidth = 0
        maxheight = 0

        # first pass: read string-grid and parse even (x,y) coordinates into nodes
        for iy, line in enumerate(maplines[origo_y:]):
            even_iy = iy % 2 == 0
            for ix, char in enumerate(line[origo_x:]):

                if char == self.empty_symbol:
                    continue

                even_ix = ix % 2 == 0
                maxwidth = max(maxwidth, ix + 1)
                maxheight = max(maxheight, iy + 1)  # only increase if there's something on the line

                mapnode_or_link_class = self.legend.get(char)
                if not mapnode_or_link_class:
                    raise MapParserError(
                        f"Symbol '{char}' on grid position ({ix,iy}) is not found in LEGEND.")

                if even_iy and even_ix:
                    # a node position will only appear on even positions in the string grid.
                    if hasattr(mapnode_or_link_class, "node_index"):
                        # this is an actual node that represents an in-game location
                        # - register it properly.
                        # the x,y stored on the node is the 'actual' xy position in the game
                        # world, not just the position in the string map (that is stored
                        # in the string_map indices instead).
                        realx, realy = ix // 2, iy // 2
                        string_map[ix][iy] = node_map[realx][realy] = node_index_map[node_index] = \
                            mapnode_or_link_class(node_index=node_index, x=realx, y=realy)
                        node_index += 1
                        continue

                # an in-between coordinates, or on-node position link
                string_map[ix][iy] = mapnode_or_link_class(x=ix, y=iy)

        # second pass: Here we loop over all nodes and have them connect to each other
        # via the detected linkages.
        for node in node_index_map.values():
            node.build_links(string_map)

        # build display map
        display_map = [[" "] * maxwidth for _ in range(maxheight)]
        for ix, ydct in string_map.items():
            for iy, node_or_link in ydct.items():
                display_map[iy][ix] = node_or_link.display_symbol

        # store
        self.width = maxwidth
        self.height = maxheight
        self.string_map = string_map
        self.node_index_map = node_index_map
        self.display_map = display_map
        self.node_map = node_map

    def _get_node_from_coord(self, x, y):
        """
        Get a MapNode from a coordinate.

        Args:
            x (int): X-coordinate on game grid.
            y (int): Y-coordinate on game grid.

        Returns:
            MapNode: The node found at the given coordinates.


        """
        if not self.node_map:
            self.parse()

        try:
            return self.node_map[x][y]
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

    def get_shortest_path(self, startcoord, endcoord):
        """
        Get the shortest route between two points on the grid.

        Args:
            startcoord (tuple or MapNode): A starting (x,y) coordinate for where
                we start from.
            endcoord (tuple or MapNode): The end (x,y) coordinate we want to
                find the shortest route to.

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

    def get_map_region(self, x, y, dist=2, return_str=True):
        """
        Display the map centered on a point and everything around it within a certain distance.

        Args:
            x (int): In-world X coordinate.
            y (int): In-world Y coordinate.
            dist (int): Number of gridpoints distance to show.
                A value of 2 will show adjacent nodes, a value
                of 1 will only show links from current node.
            return_str (bool, optional): Return result as an
                already formatted string.

        Returns:
            str or list: Depending on value of `return_str`. If a list,
                this is 2D list of lines, [[str,str,str,...], [...]] where
                each element is a single character in the display grid. To
                extract a coordinate from it, use listing[iy][ix]

        """
        width, height = self.width, self.height
        # convert to string-map coordinates. Remember that y grid grows downwards
        ix, iy = max(0, min(x * 2, width)), max(0, min(y * 2, height))
        left, right = max(0, ix - dist), min(width, ix + dist + 1)
        top, bottom = max(0, iy - dist), min(height, iy + dist + 1)
        output = []
        if return_str:
            for line in self.display_map[top:bottom]:
                output.append("".join(line[left:right]))
            return "\n".join(output)
        else:
            for line in self.display_map[top:bottom]:
                output.append(line[left:right])
            return output
