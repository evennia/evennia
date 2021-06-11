r"""
# Map system

Evennia - Griatch 2021

Implement mapping, with path searching.

This builds a map graph based on an ASCII map-string with special, user-defined symbols.
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

    10 #             #
        \            d
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
     3   #-#-#-#   x   #
             | |  / \ u
     2       #-#-#---#
             ^       d
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

try:
    from scipy.sparse.csgraph import dijkstra
    from scipy.sparse import csr_matrix
    from scipy import zeros
except ImportError as err:
    raise ImportError(
        f"{err}\nThe MapSystem contrib requires "
        "the SciPy package. Install with `pip install scipy'.")
from evennia.utils.utils import variable_from_module, mod_import


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
    "nw": (-1, 1)
}

_BIG = 999999999999


# errors for Map system

class MapError(RuntimeError):
    pass

class MapParserError(MapError):
    pass

# Nodes/Links

class MapNode:
    """
    This represents a 'room' node on the map. Note that the map system deals with two grids, the
    finer `xygrid`, which is the per-character grid on the map, and the `XYgrid` which contains only
    the even-integer coordinates and also represents in-game coordinates/rooms. MapNodes are always
    located on even X,Y coordinates on the map grid and in-game.

    Attributes on the node class:

    - `symbol` (str) - The character to parse from the map into this node. By default this
      is '#' and must be a single character, with the exception of `\\
    - `display_symbol` (str or `None`) - This is what is used to visualize this node later. This
      symbol must still only have a visual size of 1, but you could e.g. use some fancy unicode
      character (be aware of encodings to different clients though) or, commonly, add color
      tags around it. For further customization, the `.get_display_symbol` method receives
      the full grid and can return a dynamically determined display symbol. If set to `None`,
      the `symbol` is used.
    - `interrupt_path` (bool): If this is set, the shortest-path algorithm will include this
      node as normally, but stop when reaching it, even if not having reached its target yet. This
      is useful for marking 'points of interest' along a route, or places where you are not
      expected to be able to continue without some further in-game action not covered by the map
      (such as a guard or locked gate etc).

    """
    # symbol used to identify this link on the map
    symbol = '#'
    # if printing this node should show another symbol. If set
    # to the empty string, use `symbol`.
    display_symbol = None

    # internal use. Set during generation, but is also used for identification of the node
    node_index = None

    # this should always be left True and avoids inifinite loops during querying.
    multilink = True
    # this will interrupt a shortest-path step (useful for 'points' of interest, stop before
    # a door etc).
    interrupt_path = False

    def __init__(self, x, y, node_index=0):
        """
        Initialize the mapnode.

        Args:
            x (int): Coordinate on xygrid.
            y (int): Coordinate on xygrid.
            node_index (int): This identifies this node with a running
                index number required for pathfinding. This is used
                internally and should not be set manually.

        """

        self.x = x
        self.y = y

        # XYgrid coordinate
        self.X = x // 2
        self.Y = y // 2

        self.node_index = node_index

        # this indicates linkage in 8 cardinal directions on the string-map,
        # n,ne,e,se,s,sw,w,nw and link that to a node (always)
        self.links = {}
        # this maps
        self.weights = {}
        # lowest direction to a given neighbor
        self.shortest_route_to_node = {}
        # maps the directions (on the xygrid NOT on XYgrid!) taken if stepping
        # out from this node in a  given direction until you get to the end node.
        # This catches  eventual longer link chains that would otherwise be lost
        # {startdirection: [direction, ...], ...}
        # where the directional path-lists also include the start-direction
        self.xy_steps_to_node = {}
        # direction-names of the closest neighbors to the node
        self.closest_neighbor_names = {}

    def __str__(self):
        return f"<MapNode '{self.symbol}' {self.node_index} XY=({self.X},{self.Y})"

    def __repr__(self):
        return str(self)

    def scan_all_directions(self, xygrid):
        """
        This is called by the map parser when this node is encountered. It tells the node
        to scan in all directions and follow any found links to other nodes. Since there
        could be multiple steps to reach another node, the system will iterate down each
        path and store it once and for all.

        Args:
            xygrid (dict): A 2d dict-of-dicts with x,y coordinates as keys and nodes as values.

        Notes:
            This sets up all data needed for later use of this node in pathfinding and
            other operations. The method can't run immediately when the node is created
            since a complete parsed xygrid is required.

        """
        # we must use the xygrid coordinates
        x, y = self.x, self.y

        # scan in all directions for links
        for direction, (dx, dy) in _MAPSCAN.items():

            lx, ly = x + dx, y + dy

            if lx in xygrid and ly in xygrid[lx]:
                link = xygrid[lx][ly]

                # just because there is a link here, doesn't mean it has a
                # connection in this direction. If so, the `end_node` will be None.
                end_node, weight, steps = link.traverse(_REVERSE_DIRECTIONS[direction], xygrid)

                if end_node:
                    # the link could be followed to an end node!

                    # check the actual direction-alias to use, since this may be
                    # different than the xygrid cardinal directions. There must be
                    # no duplicates out of this node or there will be a
                    # multi-match error later!
                    first_step_name = steps[0].direction_aliases.get(direction, direction)
                    if first_step_name in self.closest_neighbor_names:
                        raise MapParserError(
                            f"MapNode '{self.symbol}' at XY=({self.X:g},{self.Y:g}) has more "
                            f"than one outgoing direction '{first_step_name}'. All directions "
                            "out of a node must be unique.")
                    self.closest_neighbor_names[first_step_name] = direction

                    node_index = end_node.node_index
                    self.weights[node_index] = weight
                    self.links[direction] = end_node
                    # this is useful for map building later - there could be multiple
                    # links tied together until getting to the node
                    self.xy_steps_to_node[direction] = steps

                    # used for building the shortest path. Note that we store the
                    # aliased link directions here, for quick display by the
                    # shortest-route solver
                    shortest_route = self.shortest_route_to_node.get(node_index, ("", [], _BIG))[2]
                    if weight < shortest_route:
                        self.shortest_route_to_node[node_index] = (first_step_name, steps, weight)

    def linkweights(self, nnodes):
        """
        Retrieve all the weights for the direct links to all other nodes. This is
        used for the efficient generation of shortest-paths.

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

    def get_display_symbol(self, xygrid, **kwargs):
        """
        Hook to override for customizing how the display_symbol is determined.

        Args:
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Returns:
            str: The display-symbol to use. This must visually be a single character
            but could have color markers, use a unicode font etc.

        Notes:
            By default, just setting .display_symbol is enough.

        """
        return self.symbol if self.display_symbol is None else self.display_symbol


class MapLink:
    """
    This represents one or more links between an 'incoming diretion'
    and an 'outgoing direction'. It's like a railway track between
    MapNodes. A Link can be placed on any location in the grid, but even when
    on an integer XY position they still don't represent an actual in-game place
    but just a link between such places (the Nodes).

    Each link has a 'weight' >=1,  this indicates how 'slow'
    it is to traverse that link. This is used by the Dijkstra algorithm
    to find the 'fastest' route to a point. By default this weight is 1
    for every link, but a locked door, terrain etc could increase this
    and have the shortest-path algorithm prefer to use another route.

    Attributes on the link class:

    - `symbol` (str) - The character to parse from the map into this node. This must be a single
      character, with the exception of `\\`.
    - `display_symbol` (str or None)  - This is what is used to visualize this node later. This
      symbol must still only have a visual size of 1, but you could e.g. use some fancy unicode
      character (be aware of encodings to different clients though) or, commonly, add color
      tags around it. For further customization, the `.get_display_symbol` method receives
      the full grid and can return a dynamically determined display symbol. If `None`, the
      `symbol` is used.
    - `default_weight` (int) - Each link direction covered by this link can have its seprate weight,
      this is used if none is specified in a particular direction. This value must be >= 1,
      and can be higher than 1 if a link should be less favored.
    - `directions` (dict) - this specifies which link edge to which other link-edge this link
      is connected; A link connecting the link's sw edge to its easted edge would be written
      as `{'sw': 'e'}` and read 'connects from southwest to east'. Note that if you want the
      link to go both ways, also the inverse (east to southwest) must also be added.
    - `weights (dict)` This maps a link's start direction to a weight. So for the
      `{'sw': 'e'}` link, a weight would be given as `{'sw': 2}`. If not given, a link will
      use the `default_weight`.
    - `average_long_link_weights` (bool): This applies to the *first* link out of a node only.
      When tracing links to another node, multiple links could be involved, each with a weight.
      So for a link chain with default weights, `#---#` would give a total weight of 3. With this
      setting, the weight will be 3 / 3 = 1. That is, for evenly weighted links, the length
      of the link doesn't matter.
    - `direction_aliases` (dict): When displaying a direction during pathfinding, one may want
      to display a different 'direction' than the cardinal on-map one. For example 'up' may be
      visualized on the map as a 'n' movement, but the found path over this link should show
      as 'u'. In that case, the alias would be `{'n': 'u'}`.
    - `multilink` (bool): If set, this link accepts links from all directions. It will usually
      use a custom get_direction to determine what these are based on surrounding topology. This
      setting is necessary to avoid infinite loops when such multilinks are next to each other.
    - `interrupt_path` (bool): If set, a shortest-path solution will include this link as normal,
      but will stop short of actually moving past this link.

    """
    # symbol for identifying this link on the map
    symbol = ""
    # if `None`, use .symbol
    display_symbol = None
    default_weight = 1
    # This setting only applies if this is the *first* link in a chain of multiple links. Usually,
    # when multiple links are used to tie together two nodes, the default is to average the weight
    # across all links. With this disabled, the weights will be added and a long link will be
    # considered 'longer' by the pathfinder.
    average_long_link_weights = True
    # this indicates linkage start:end in 8 cardinal directions on the string-map,
    # n,ne,e,se,s,sw,w,nw. A link is described as {startpos:endpoit}, like connecting
    # the named corners with a line. If the inverse direction is also possible, it
    # must also be specified. So a south-northward, two-way link would be described
    # as {"s": "n", "n": "s"}. The get_direction method can be customized to
    # return something else.
    directions = {}
    # for displaying the directions during pathfinding, you may want to show a different
    # direction than the cardinal one. For example, 'up' may be 'n' on the map, but
    # the direction when moving should be 'u'. This would be a alias {'n': 'u'}.
    direction_aliases = {}
    # this is required for pathfinding and contains cardinal directions (n, ne etc) only.
    # Each weight is defined as {startpos:weight}, where
    # the startpos is the direction of the cell (n,ne etc) where the link *starts*. The
    # weight is a value > 0, smaller than _BIG. The get_weight method can be
    # customized to modify to return something else.
    weights = {}
    # this shortcuts neighbors trying to figure out if they can connect to this link
    # - if this is set, they always can (similarly as to a node)
    multilink = False
    # this link does not block/reroute pathfinding, but makes the actual path always stop when
    # trying to cross it.
    interrupt_path = False

    def __init__(self, x, y):
        """
        Initialize the link.

        Args:
            x (int): The xygrid x coordinate
            y (int): The xygrid y coordinate.

        """
        self.x = x
        self.y = y

        self.X = x / 2
        self.Y = y / 2

    def __str__(self):
        return f"<LinkNode '{self.symbol}' XY=({self.X:g},{self.Y:g})>"

    def __repr__(self):
        return str(self)

    def traverse(self, start_direction, xygrid, _weight=0, _linklen=1, _steps=None):
        """
        Recursively traverse the links out of this LinkNode.

        Args:
            start_direction (str): The direction (n, ne etc) from which
                this traversal originates for this link.
            xygrid (dict): 2D dict with x,y coordinates as keys.
        Kwargs:
            _weight (int): Internal use.
            _linklen (int): Internal use.
            _steps (list): Internal use.

        Returns:
            tuple: The (node, weight, links) result of the traversal, where links
                is a list of directions (n, ne etc) that describes how to to get
                to the node on the grid. This includes the first direction.

        Raises:
            MapParserError: If a link lead to nowhere.

        """
        end_direction = self.get_direction(start_direction, xygrid)
        if not end_direction:
            if _steps is None:
                # is perfectly okay to not be linking to a node
                return None, 0, None
            raise MapParserError(f"Link '{self.symbol}' at "
                                 f"XY=({self.X:g},{self.Y:g}) "
                                 f"was connected to from the direction {start_direction}, but "
                                 "is not set up to link in that direction.")

        dx, dy = _MAPSCAN[end_direction]
        end_x, end_y = self.x + dx, self.y + dy
        try:
            next_target = xygrid[end_x][end_y]
        except KeyError:
            raise MapParserError(f"Link '{self.symbol}' at "
                                 f"XY=({self.X:g},{self.Y:g}) "
                                 "points to empty space in the direction {end_direction}!")

        _weight += self.get_weight(start_direction, xygrid, _weight)
        if _steps is None:
            _steps = []
        _steps.append(self)

        if hasattr(next_target, "node_index"):
            # we reached a node, this is the end of the link.
            # we average the weight across all traversed link segments.
            return (
                next_target,
                _weight / max(1, _linklen) if self.average_long_link_weights else _weight,
                _steps
            )

        else:
            # we hit another link. Progress recursively.
            return next_target.traverse(
                _REVERSE_DIRECTIONS[end_direction],
                xygrid, _weight=_weight, _linklen=_linklen + 1, _steps=_steps)

    def get_linked_neighbors(self, xygrid, directions=None):
        """
        A helper to get all directions to which there appears to be a
        visual link/node. This does not trace the length of the link and check weights etc.

        Args:
            xygrid (dict): 2D dict with x,y coordinates as keys.
            directions (list, optional): Only scan in these directions.

        Returns:
            dict: Mapping {direction: node_or_link} wherever such was found.

        """
        if not directions:
            directions = _REVERSE_DIRECTIONS.keys()

        links = {}
        for direction in directions:
            dx, dy = _MAPSCAN[direction]
            end_x, end_y = self.x + dx, self.y + dy
            if end_x in xygrid and end_y in xygrid[end_x]:
                # there is is something there, we need to check if it is either
                # a map node or a link connecting in our direction
                node_or_link = xygrid[end_x][end_y]
                if (node_or_link.multilink
                        or node_or_link.get_direction(direction, xygrid)):
                    links[direction] = node_or_link
        return links

    def get_display_symbol(self, xygrid, **kwargs):
        """
        Hook to override for customizing how the display_symbol is determined.

        Args:
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Kwargs:
            mapinstance (Map): The current Map instance.

        Returns:
            str: The display-symbol to use. This must visually be a single character
            but could have color markers, use a unicode font etc.

        Notes:
            By default, just setting .display_symbol is enough.

        """
        return self.symbol if self.display_symbol is None else self.display_symbol

    def get_direction(self, start_direction, xygrid, **kwargs):
        """
        Hook to override for customizing how the directions are
        determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Returns:
            str: The 'out' direction side of the link - where the link
                leads to.

        Example:
            With the default legend, if the link is a straght vertical link
            (`|`) and `start_direction` is `s` (link is approached from
            from the south side), then this function will return `n'.

        """
        return self.directions.get(start_direction)

    def get_weight(self, start_direction, xygrid, current_weight, **kwargs):
        """
        Hook to override for customizing how the weights are determined.

        Args:
            start_direction (str): The starting direction (n, ne etc).
            xygrid (dict): 2D dict with x,y coordinates as keys.
            current_weight (int): This can have an existing value if
                we are progressing down a multi-step path.

        Returns:
            int: The weight to use for a link from `start_direction`.

        """
        return self.weights.get(start_direction, self.default_weight)


class SmartMapLink(MapLink):
    """
    A 'smart' link withot visible direction, but which uses its topological surroundings
    to figure out how it connects. A limited link will prefer to connect two Nodes directly and
    if there are more than two nodes directly neighboring, it will raise an MapParserError.
    If two nodes are not found, it will link to any combination of links- or nodes as long as
    it can un-ambiguously determine which direction they lead.

    Placing a smart-link directly between two nodes/links will always be a two-way connection,
    whereas if it connects a node with another link, it will be a one-way connection in the
    direction of the link.

    Example with the up-down directions:
    ::

        #
        u     - moving up in BOTH directions will bring you to the other node (two-way)
        #

        #
        d     - this better represents the 'real' up/down behavior.
        u
        #

        #
        |     - one-way up from the lower node to the upper
        u
        #

        #-#
        u     - okay since the up-link prioritizes the nodes
        #

        #u#
        u    - invalid since top-left node has two 'up' directions to go to
        #

        #     |
        u# or u-   - invalid.
        #     |

    """
    multilink = True

    def get_direction(self, start_direction, xygrid):
        """
        Figure out the direction from a specific source direction based on grid topology.

        """
        # get all visually connected links
        if not self.directions:
            directions = {}
            neighbors = self.get_linked_neighbors(xygrid)
            nodes = [direction for direction, neighbor in neighbors.items()
                     if hasattr(neighbor, 'node_index')]

            if len(nodes) == 2:
                # prefer link to these two nodes
                for direction in nodes:
                    directions[direction] = _REVERSE_DIRECTIONS[direction]
            elif len(neighbors) - len(nodes) == 1:
                for direction in neighbors:
                    directions[direction] = _REVERSE_DIRECTIONS[direction]
            else:
                raise MapParserError(
                    f"MapLink '{self.symbol}' at "
                    f"XY=({self.X:g},{self.Y:g}) must have exactly two connections - either "
                    f"two nodes or unambiguous link directions. Found neighbor(s) in directions "
                    f"{list(neighbors.keys())}.")

            self.directions = directions
        return self.directions.get(start_direction)


class InvisibleSmartMapLink(SmartMapLink):
    """
    This is a smart maplink that does not show as such on the map - instead it will figure out
    how it should look had it been one of the 'normal' cardinal-direction links and display
    itself as that instead. This doesn't change its functionality, only the symbol shown
    on the map display. This only works for cardinal-direction links.

    It makes use of `display_symbol_aliases` mapping, which maps a sorted set of
    `((start, end), (end, start))` (two-way) or `((start, end),)` (one-way) directions
    to a symbol in the current map legend - this is the symbol alias to use. The matching
    MapLink or MapNode will be initialized at the current position only for the purpose of getting
    its display_symbol.

    Example:
        display_symbol_aliases = `{(('n', 's'), ('s', n')): '|', ...}`

    If no `display_symbol_aliases` are given, the regular display_symbol is used.

    """

    # this allows for normal movement directions even if the invisible-node
    # is marked with a different symbol.
    direction_aliases = {
        'n': 'n', 'ne': 'ne', 'e': 'e', 'se': 'se',
        's': 's', 'sw': 'sw', 'w': 'w', 'nw': 'nw'
    }

    # replace current link position with what the smart links "should" look like
    display_symbol_aliases = {
        (('n', 's'), ('s', 'n')): '|',
        (('n', 's'),): 'v',
        (('s', 'n')): '^',
        (('e', 'w'), ('w', 'e')): '-',
        (('e', 'w'),): '>',
        (('w', 'e'),): '<',
        (('nw', 'se'), ('sw', 'ne')): '\\',
        (('ne', 'sw'), ('sw', 'ne')): '/',
    }

    def get_display_symbol(self, xygrid, **kwargs):
        """
        The SmartMapLink already calculated the directions before this, so we
        just need to figure out what to replace this with in order to make this 'invisible'

        Depending on how we are connected, we figure out how the 'normal' link
        should look and use that instead.

        """
        if not hasattr(self, "_cached_display_symbol"):
            mapinstance = kwargs['mapinstance']

            legend = mapinstance.legend
            default_symbol = (
                self.symbol if self.display_symbol is None else self.display_symbol)
            self._cached_display_symbol = default_symbol

            dirtuple = tuple((key, self.directions[key])
                             for key in sorted(self.directions.keys()))

            replacement_symbol = self.display_symbol_aliases.get(dirtuple, default_symbol)

            if replacement_symbol != self.symbol:
                node_or_link_class = legend.get(replacement_symbol)
                if node_or_link_class:
                    # initiate class in the current location and run get_display_symbol
                    # to get what it would show.
                    self._cached_display_symbol = node_or_link_class(
                        self.x, self.y).get_display_symbol(xygrid, **kwargs)
        return self._cached_display_symbol


class SmartRerouterMapLink(MapLink):
    r"""
    A 'smart' link without visible direction, but which uses its topological surroundings
    to figure out how it connects. The rerouter can only be connected to with other links, not
    by nodes. All such links are two-way. It can be used to create 'knees' and multi-crossings
    of links. Remember that this is still a link, so user will not 'stop' at it, even if
    placed on an XY position!

    If there are links on cardinally opposite sites, these are considered pass-throughs, and
    If determining the path of a set of input/output directions this is not possible, or there is an
    uneven number of links, an `MapParserError` is raised.

    Example with the RedirectLink:
    ::
          /
        -o    - this is ok, there can only be one path, e-ne

         |
        -o-   - equivalent to '+', one n-s and one w-e link crossing
         |

        \|/
        -o-   - all are passing straight through
        /|\

        -o-   - w-e pass straight through, other link is sw-s
        /|

        -o    - invalid; impossible to know which input goes to which output
        /|

    """
    multilink = True

    def get_direction(self, start_direction, xygrid):
        """
        Dynamically determine the direction based on a source direction and grid topology.

        """
        # get all visually connected links
        if not self.directions:
            directions = {}
            unhandled_links = list(self.get_linked_neighbors(xygrid).keys())

            # get all straight lines (n-s, sw-ne etc) we can trace through
            # the dynamic link and remove them from the unhandled_links list
            unhandled_links_copy = unhandled_links.copy()
            for direction in unhandled_links_copy:
                if _REVERSE_DIRECTIONS[direction] in unhandled_links_copy:
                    directions[direction] = _REVERSE_DIRECTIONS[
                        unhandled_links.pop(unhandled_links.index(direction))]

            # check if we have any non-cross-through paths left to handle
            n_unhandled = len(unhandled_links)
            if n_unhandled:
                # still remaining unhandled links. If there's not exactly
                # one 'incoming' and one 'outgoing' we can't figure out
                # where to go in a non-ambiguous way.
                if n_unhandled != 2:
                    links = ", ".join(unhandled_links)
                    raise MapParserError(
                        f"MapLink '{self.symbol}' at "
                        f"XY=({self.X:g},{self.Y:g}) cannot determine "
                        f"how to connect in/out directions {links}.")

                directions[unhandled_links[0]] = unhandled_links[1]
                directions[unhandled_links[1]] = unhandled_links[0]

            self.directions = directions

        return self.directions.get(start_direction)


# ----------------------------------
# Default nodes and link classes

class BasicMapNode(MapNode):
    """Basic map Node"""
    symbol = "#"

class InterruptMapNode(MapNode):
    """A point of interest, where pathfinder will stop"""
    symbol = "i"
    display_symbol = "#"
    interrupt_path = True

class NSMapLink(MapLink):
    """Two-way, North-South link"""
    symbol = "|"
    directions = {"n": "s", "s": "n"}


class EWMapLink(MapLink):
    """Two-way, East-West link"""
    symbol = "-"
    directions = {"e": "w", "w": "e"}


class NESWMapLink(MapLink):
    """Two-way, NorthWest-SouthWest link"""
    symbol = "/"
    directions = {"ne": "sw", "sw": "ne"}

class SENWMapLink(MapLink):
    """Two-way, SouthEast-NorthWest link"""
    symbol = "\\"
    directions = {"se": "nw", "nw": "se"}


class PlusMapLink(MapLink):
    """Two-way, crossing North-South and East-West links"""
    symbol = "+"
    directions = {"s": "n", "n": "s",
                  "e": "w", "w": "e"}

class CrossMapLink(MapLink):
    """Two-way, crossing NorthEast-SouthWest and SouthEast-NorthWest links"""
    symbol = "x"
    directions = {"ne": "sw", "sw": "ne",
                  "se": "nw", "nw": "se"}

class NSOneWayMapLink(MapLink):
    """One-way North-South link"""
    symbol = "v"
    directions = {"n": "s"}


class SNOneWayMapLink(MapLink):
    """One-way South-North link"""
    symbol = "^"
    directions = {"s": "n"}


class EWOneWayMapLink(MapLink):
    """One-way East-West link"""
    symbol = "<"
    directions = {"e": "w"}


class WEOneWayMapLink(MapLink):
    """One-way West-East link"""
    symbol = ">"
    directions = {"w": "e"}


class UpMapLink(SmartMapLink):
    """Up direction. Note that this still uses the xygrid!"""
    symbol = 'u'

    # all movement over this link is 'up', regardless of where on the xygrid we move.
    direction_aliases = {'n': symbol, 'ne': symbol, 'e': symbol, 'se': symbol,
                         's': symbol, 'sw': symbol, 'w': symbol, 'nw': symbol}

class DownMapLink(UpMapLink):
    """Works exactly like `UpMapLink` but for the 'down' direction."""
    symbol = 'd'
    # all movement over this link is 'down', regardless of where on the xygrid we move.
    direction_aliases = {'n': symbol, 'ne': symbol, 'e': symbol, 'se': symbol,
                         's': symbol, 'sw': symbol, 'w': symbol, 'nw': symbol}


class InterruptMapLink(InvisibleSmartMapLink):
    """A (still passable) link that causes the pathfinder to stop before crossing."""
    symbol = "i"
    interrupt_path = True


class BlockedMapLink(InvisibleSmartMapLink):
    """
    A high-weight (but still passable) link that causes the shortest-path algorithm to consider this
    a blocked path. The block will not show up in the map display, paths will just never use this
    link.

    """
    symbol = 'b'
    weights = {'n': _BIG, 'ne': _BIG, 'e': _BIG, 'se': _BIG,
               's': _BIG, 'sw': _BIG, 'w': _BIG, 'nw': _BIG}


class RouterMapLink(SmartRerouterMapLink):
    """Connects multiple links to build knees, pass-throughs etc."""
    symbol = "o"


# these are all symbols used for x,y coordinate spots
# at (0,1) etc.
DEFAULT_LEGEND = {
    "#": BasicMapNode,
    "I": InterruptMapNode,
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
    "o": RouterMapLink,
    "u": UpMapLink,
    "d": DownMapLink,
    "b": BlockedMapLink,
    "i": InterruptMapLink,
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
    max_pathfinding_length = 500
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
        self.dist_matrix = None
        self.pathfinding_routes = None

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
                            xmin=_BIG, ymin=_BIG, xmax=0, ymax=0, depth=0):

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
        Solve the pathfinding problem using Dijkstra's algorithm.

        """
        nnodes = len(self.node_index_map)

        pathfinding_graph = zeros((nnodes, nnodes))
        # build a matrix representing the map graph, with 0s as impassable areas
        for inode, node in self.node_index_map.items():
            pathfinding_graph[inode, :] = node.linkweights(nnodes)

        # create a sparse matrix to represent link relationships from each node
        pathfinding_matrix = csr_matrix(pathfinding_graph)

        # solve using Dijkstra's algorithm
        self.dist_matrix, self.pathfinding_routes = dijkstra(
            pathfinding_matrix, directed=True,
            return_predecessors=True, limit=self.max_pathfinding_length)

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
                    xygrid[ix][iy] = mapnode_or_link_class(x=ix, y=iy)

        # second pass: Here we loop over all nodes and have them connect to each other
        # via the detected linkages.
        for node in node_index_map.values():
            node.scan_all_directions(xygrid)

        # build display map
        display_map = [[" "] * (max_x + 1) for _ in range(max_y + 1)]
        for ix, ydct in xygrid.items():
            for iy, node_or_link in ydct.items():
                display_map[iy][ix] = node_or_link.get_display_symbol(xygrid, mapinstance=self)

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
                return target_path_style.format(display_symbol=node)

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
