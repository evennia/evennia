"""
# Map legend components

Each map-legend component is either a 'mapnode' - something that represents and actual in-game
location (usually a room) or a 'maplink' - something connecting nodes together. The start of a link
usually shows as an Exit, but the length of the link has no in-game equivalent.

"""

try:
    from scipy import zeros
except ImportError as err:
    raise ImportError(
        f"{err}\nThe MapSystem contrib requires "
        "the SciPy package. Install with `pip install scipy'.")

from .utils import MAPSCAN, REVERSE_DIRECTIONS, MapParserError, BIGVAL


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
        for direction, (dx, dy) in MAPSCAN.items():

            lx, ly = x + dx, y + dy

            if lx in xygrid and ly in xygrid[lx]:
                link = xygrid[lx][ly]

                # just because there is a link here, doesn't mean it has a
                # connection in this direction. If so, the `end_node` will be None.
                end_node, weight, steps = link.traverse(REVERSE_DIRECTIONS[direction], xygrid)

                if end_node:
                    # the link could be followed to an end node!

                    # check the actual direction-alias to use, since this may be
                    # different than the xygrid cardinal directions. There must be
                    # no duplicates out of this node or there will be a
                    # multi-match error later!
                    first_step_name = steps[0].direction_aliases.get(direction, direction)
                    if first_step_name in self.closest_neighbor_names:
                        raise MapParserError(
                            f"has more than one outgoing direction '{first_step_name}'. "
                            "All directions out of a node must be unique.", self)
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
                    shortest_route = self.shortest_route_to_node.get(
                        node_index, ("", [], BIGVAL))[2]
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
    This represents one or more links between an 'incoming direction'
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
    # weight is a value > 0, smaller than BIGVAL. The get_weight method can be
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
                # is perfectly okay to not be linking back on the first step (to a node)
                return None, 0, None
            raise MapParserError(
                f"was connected to from the direction {start_direction}, but "
                "is not set up to link in that direction.", self)

        # note that if `get_direction` returns an unknown direction, this will be equivalent
        # to pointing to an empty location, which makes sense
        dx, dy = MAPSCAN.get(end_direction, (BIGVAL, BIGVAL))
        end_x, end_y = self.x + dx, self.y + dy
        try:
            next_target = xygrid[end_x][end_y]
        except KeyError:
            # check if we have some special action up our sleeve
            next_target = self.at_empty_target(end_direction, xygrid)

        if not next_target:
            raise MapParserError(
                f"points to empty space in the direction {end_direction}!", self)

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
                REVERSE_DIRECTIONS.get(end_direction, end_direction),
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
            directions = REVERSE_DIRECTIONS.keys()

        links = {}
        for direction in directions:
            dx, dy = MAPSCAN[direction]
            end_x, end_y = self.x + dx, self.y + dy
            if end_x in xygrid and end_y in xygrid[end_x]:
                # there is is something there, we need to check if it is either
                # a map node or a link connecting in our direction
                node_or_link = xygrid[end_x][end_y]
                if (node_or_link.multilink
                        or node_or_link.get_direction(direction, xygrid)):
                    links[direction] = node_or_link
        return links

    def at_empty_target(self, start_direction, end_direction, xygrid):
        """
        This is called by `.traverse` when it finds this link pointing to nowhere.

        Args:
            start_direction (str): The direction (n, ne etc) from which
                this traversal originates for this link.
            end_direction (str): The direction found from `get_direction` earlier.
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Returns:
            MapNode, MapLink or None: The next target to go to from here. `None` if this
            is an error that should be reported.

        Notes:
            This is usually a mapping error (returning `None`) but may have practical use, such as
            teleporting or transitioning to another map.

        """
        return None

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

    def get_display_symbol(self, xygrid, **kwargs):
        """
        Hook to override for customizing how the display_symbol is determined.
        This is called after all other hooks, at map visualization.

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

class SmartRerouterMapLink(MapLink):
    r"""
    A 'smart' link without visible direction, but which uses its topological surroundings
    to figure out how it connects. All such links are two-way. It can be used to create 'knees' and
    multi-crossings of links. Remember that this is still a link, so user will not 'stop' at it,
    even if placed on an XY position!

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
                if REVERSE_DIRECTIONS[direction] in unhandled_links_copy:
                    directions[direction] = REVERSE_DIRECTIONS[
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
                        f"cannot determine how to connect in/out directions {links}.", self)

                directions[unhandled_links[0]] = unhandled_links[1]
                directions[unhandled_links[1]] = unhandled_links[0]

            self.directions = directions

        return self.directions.get(start_direction)

class TeleporterMapLink(MapLink):
    """
    The teleport link works by connecting to nowhere - and will then continue
    on another teleport link with the same symbol elsewhere on the map. The teleport
    symbol must connect to only one other link (not to a node).

    For this to work, there must be exactly one other teleport with the same `.symbol` on the map.
    The two teleports will always operate as two-way connections, but by making the 'out-link' on
    one side one-way, the effect will be that of a one-way teleport.

    Example:
    ::

          t #
         /  |   -  moving ne from the left node will bring the user to the rightmost node
       -#   t      as if the two teleporters were connected (two way).

       -#-t t># - one-way teleport from left to right.

       -#t       - invalid, may only connect to another link

       -#-t-#    - invalid, only one connected link is allowed.

    """
    symbol = 't'
    # usually invisible
    display_symbol = ' '
    direction_name = 'teleport'

    def __init__(self, *args):
        super().__init__(*args)
        self.paired_teleporter = None

    def at_empty_target(self, start_direction, xygrid):
        """
        Called during traversal, when finding an unknown direction out of the link (same as
        targeting a link at an empty spot on the grid). This will also search for
        a unique, matching teleport to send to.

        Args:
            start_direction (str): The direction (n, ne etc) from which this traversal originates
                for this link.
            xygrid (dict): 2D dict with x,y coordinates as keys.

        Returns:
            TeleporterMapLink: The paired teleporter.

        Raises:
            MapParserError: We raise this explicitly rather than returning `None` if we don't find
                another teleport. This avoids us getting the default (and in this case confusing)
                'pointing to an empty space' error we'd get if returning `None`.

        """
        if not self.paired_teleporter:
            # scan for another teleporter
            symbol = self.symbol
            found_teleporters = []
            for iy, line in xygrid.items():
                for ix, node_or_link in xygrid[iy].items():
                    if node_or_link.symbol == symbol and node_or_link is not self:
                        found_teleporters.append(node_or_link)

            if not found_teleporters:
                raise MapParserError("found no matching teleporter to link to.", self)
            if len(found_teleporters) > 1:
                raise MapParserError(
                    "found too many matching teleporters (must be exactly one more): "
                    f"{found_teleporters}", self)

            other_teleporter = found_teleporters[0]
            # link the two so we don't need to scan again for the other one
            self.paired_teleporter = other_teleporter
            other_teleporter.paired_teleporter = self

        return self.paired_teleporter

    def get_direction(self, start_direction, xygrid):
        """
        Figure out the connected link and paired teleport.

        """
        if not self.directions:
            neighbors = self.get_linked_neighbors(xygrid)

            if len(neighbors) != 1:
                raise MapParserError("must have exactly one link connected to it.", self)
            direction, link = next(iter(neighbors.items()))
            if hasattr(link, 'node_index'):
                raise MapParserError("can only connect to a Link. Found {link} in "
                                     "direction {direction}.", self)
            # the string 'teleport' will not be understood by the traverser, leading to
            # this being interpreted as an empty target and the `at_empty_target`
            # hook firing when trying to traverse this link.
            direction_name = self.direction_name
            if start_direction == direction_name:
                # called while traversing another teleport
                # - we must make sure we can always access/leave the teleport.
                self.directions = {direction_name: direction,
                                   direction: direction_name}
            else:
                # called while traversing a normal link
                self.directions = {start_direction: direction_name,
                                   direction_name: direction}

        return self.directions.get(start_direction)


class MapTransitionLink(TeleporterMapLink):
    """
    This link teleports the user to another map and lets them continue moving
    from there. Like the TeleporterMapLink, the map-transition symbol must connect to only one other
    link (not directly to a node).

    The other map will be scanned for a matching `.symbol` that must also be a MapTransitionLink.
    The link is always two-way, but the link connecting to the transition can be one-way to create
    a one-way transition. Make new links with different symbols (like A, B, C, ...) to link
    multiple maps together.

    Note that unlike for teleports, pathfinding will *not* work across the map-transition.

    Examples:
    ::

        map1    map2

           T
          /     T-#    - movement to the transition-link will continue on the other map.
        -#

           T
          /
        -#      T>#    - one-way link from map1 to map2

        -#t       - invalid, may only connect to another link

        -#-t-#    - invalid, only one connected link is allowed.

    """
    symbol = 'T'
    display_symbol = ' '
    direction_name = 'transition'
    interrupt_path = True

    map1_name = 'map'
    map2_name = 'map'

    def __init__(self, *args):
        super().__init__(*args)
        self.map1 = None
        self.map2 = None

    def at_empty_target(self, start_direction, end_direction, xygrid):
        """
        This is called by .traverse when it finds this link pointing to nowhere.

        Args:
            start_direction (str): The direction (n, ne etc) from which
                this traversal originates for this link.
            end_direction (str): The direction found from `get_direction` earlier.
            xygrid (dict): 2D dict with x,y coordinates as keys.

        """
        # TODO - this needs some higher-level handler to work.


class SmartMapLink(MapLink):
    """
    A 'smart' link withot visible direction, but which uses its topological surroundings
    to figure out how it connects. Unlike the `SmartRerouterMapLink`, this link type is
    also a 'direction' of its own and can thus connect directly to nodes. It can only describe
    one transition and will prefer connecting two nodes if there are other possibilities. If the
    linking is unclear or there are more than two nodes directly neighboring, a MapParserError will
    be raised.  If two nodes are not found, it will link to any combination of links- or nodes as
    long as it can un-ambiguously determine which direction they lead.

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
                    directions[direction] = REVERSE_DIRECTIONS[direction]
            elif len(neighbors) - len(nodes) == 1:
                for direction in neighbors:
                    directions[direction] = REVERSE_DIRECTIONS[direction]
            else:
                raise MapParserError(
                    f"must have exactly two connections - either "
                    f"two nodes or unambiguous link directions. Found neighbor(s) in directions "
                    f"{list(neighbors.keys())}.", self)

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


# ----------------------------------
# Default nodes and link classes

class BasicMapNode(MapNode):
    """Basic map Node"""
    symbol = "#"


class InterruptMapNode(MapNode):
    """A point of interest, where pathfinder will stop"""
    symbol = "I"
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
    weights = {'n': BIGVAL, 'ne': BIGVAL, 'e': BIGVAL, 'se': BIGVAL,
               's': BIGVAL, 'sw': BIGVAL, 'w': BIGVAL, 'nw': BIGVAL}


class RouterMapLink(SmartRerouterMapLink):
    """Connects multiple links to build knees, pass-throughs etc."""
    symbol = "o"
