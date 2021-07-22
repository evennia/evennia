# XYZGrid contrib

```versionadded:: 1.0
```

This optional contrib adds a 'coordinate grid' to Evennia. It allows for
defining the grid as simple ascii maps that are then spawned into rooms that are
aware of their X, Y, Z coordinates. The system includes shortest-path
pathfinding, auto-stepping and in-game map visualization (with visibility
range). Grid-management is done outside of the game using a new evennia-launcher
option.

<script id="asciicast-Zz36JuVAiPF0fSUR09Ii7lcxc" src="https://asciinema.org/a/Zz36JuVAiPF0fSUR09Ii7lcxc.js" async></script>

```
#-#-#-#   #
|  /      d
#-#       |   #
   \      u   |\
o---#-----#---+-#-#
|         ^   |/
|         |   #
v         |    \
#-#-#-#-#-# #---#
    |x|x|     /
    #-#-#    #-
```

```
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                     #---#
                                    /
                                   @-
-~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dungeon Entrance
To the east, a narrow opening leads into darkness.
Exits: northeast and east

```

## Installation

1. Import and add the `evennia.contrib.commands.XYZGridCmdSet` to the
   `CharacterCmdset` cmdset in `mygame/commands.default_cmds.py`. Reload
   the server. This makes the `map`, `goto/path` and the modified `teleport` and
   `open` commands available in-game.
2. Edit `mygame/server/conf/settings.py` and add

       EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.launchcmd.xyzcommand'

   and

       PROTOTYPE_MODULES += [’evennia.contrib.xyzgrid.prototypes’]

   This will add the new ability to enter `evennia xyzgrid <option>` on the
   command line.  It will also make the `xyz_room` and `xyz_exit` prototypes
   available for use as prototype-parents when spawning the grid.
3. Run `evennia xyzgrid help` for available options.

## Overview

The grid contrib consists of multiple components.

1. The `XYMap` - This class parses modules with special _Map strings_
   and _Map legends_ into one Python object. It has helpers for pathfinding and
   visual-range handling.
2. The `XYZGrid` - This is a singleton [Script](../Components/Scripts) that
   stores all `XYMaps` in the game. It is the central point for managing the 'grid'
   of the game.
3. `XYZRoom` and `XYZExit`are custom typeclasses that use
   [Tags](../Components/Tags)
   to know which X,Y,Z coordinate they are located at. The `XYZGrid` is
   abstract until it is used to _spawn_ these database entities into
   something you can actually interract with in the game. The `XYZRoom`
   typeclass is using its `return_appearance` hook to display the in-game map.
4. Custom _Commands_ have been added for interacting with XYZ-aware locations.
5. A new custom _Launcher command_, `evennia xyzgrid <options>` is used to
   manage the grid from the terminal (no game login is needed).

We'll start exploring these components with an example.

## First example usage

After installation, do the following from your command line (where the
`evennia` command is available):

    $ evennia xyzgrid init

use `evennia xyzgrid help` to see all options)
This will create a new `XYZGrid` [Script](../Components/Scripts) if one didn't already exist.
The `evennia xyzgrid` is a custom launch option added only for this contrib.

The xyzgrid-contrib comes with a full grid example. Let's add it:

    $ evennia xyzgrid add evennia.contrib.xyzgrid.example

You can now list the maps on your grid:

    $ evennia xyzgrid list

You'll find there are two new maps added. You can find a lot of extra info
about each map with the `show` subcommand:

    $ evennia xyzgrid show "the large tree"
    $ evennia xyzgrid show "the small cave"

If you want to peek at how the grid's code, open
[evennia/contrib/xyzgrid/example.py](api:evennia.contrib.xyzgrid.example).
(We'll explain the details in later sections).

So far the grid is 'abstract' and has no actual in-game presence. Let's
spawn actual rooms/exits from it. This will take a little while.

    $ evennia xyzgrid spawn

This will take prototypes stored with each map's _map legend_ and use that
to build XYZ-aware rooms there. It will also parse all links to make suitable
exits between locations. You should rerun this command if you ever modify the
layout/prototypes of your grid. Running it multiple times is safe.

    $ evennia reload

(or `evennia start` if server was not running). This is important to do after
every spawning operation, since the `evennia xyzgrid` operates outside of the
regular evennia process. Reloading makes sure all caches are refreshed.

Now you can log into the server. Some new commands should be available to you.

    teleport (3,0,the large tree)

The `teleport` command now accepts an optional (X, Y, Z) coordinate. Teleporting
to a room-name or `#dbref` still works the same. This will teleport you onto the
grid. You should see a map-display. Try walking around.

    map

This new builder-only command shows the current map in its full form (also
showing 'invisible' markers usually not visible to users.

    teleport (3, 0)

Once you are in a grid-room, you can teleport to another grid room _on the same
map_ without specifying the Z coordinate/map name.

You can use `open` to make an exit back to the 'non-grid', but remember that you
mustn't use a cardinal direction to do so - if you do, the `evennia xyzgrid spawn`
will likely remove it next time you run it.

    open To limbo;limbo = #2
    limbo

You are back in Limbo (which doesn't know anything about XYZ coordinates). You
can however make a permanent link back into the gridmap:

    open To grid;grid = (3,0,the large tree)
    grid

This is how you link non-grid and grid locations together. You could for example
embed a house 'inside' the grid this way.

the `(3,0,the large tree)` is a 'Dungeon entrance'. If you walk east you'll
_transition_ into "the small cave" map. This is a small underground dungeon
with limited visibility. Go back outside again (back on "the large tree" map).

    path view

This finds the shortest path to the "A gorgeous view" room, high up in the large
tree. If you have color in your client, you should see the start of the path
visualized in yellow.

    goto view

This will start auto-walking you to the view. On the way you'll both move up
into the tree as well as traverse an in-map teleporter. Use `goto` on its own
to abort the auto-walk.

When you are done exploring, open the terminal (outside the game) again and
remove everything:

    $ evennia xyzgrid delete

You will be asked to confirm the deletion of the grid and unloading of the
XYZGrid script. Reload the server afterwards. If you were on a map that was
deleted you will have been moved back to your home location.

## Defining an XYMap

For a module to be suitable to pass to `evennia xyzgrid add <module>`, the
module must contain one of the following variables:

- `XYMAP_DATA` - a dict containing data that fully defines the XYMap
- `XYMAP_DATA_LIST` - a list of `XYMAP_DATA` dicts. If this exists, it will take
  precedence. This allows for storing multiple maps in one module.


The `XYMAP_DATA` dict has the following form:

```
XYMAP_DATA = {
    "zcoord": <str>
    "map": <str>,
    "legend": <dict, optional>,
    "prototypes": <dict, optional>
    "options": <dict, optional>
}

```

- `"zcoord"` (str): The Z-coordinate/map name of the map.
- `"map"` (str): A _Map string_ describing the topology of the map.
- `"legend"` (dict, optional): Maps each symbol on the map to Python code. This
  dict can be left out or only partially filled - any symbol not specified will
  instead use the default legend from the contrib.
- `"prototypes"` (dict, optional): This is a dict that maps map-coordinates
  to custom prototype overrides. This is used when spawning the map into
  actual rooms/exits.
- `"options"` (dict, optional): These are passed into the `return_appearance`
  hook of the room and allows for customizing how a map should be displayed,
  how pathfinding should work etc.

Here's a minimal example of the whole setup:

```
# In, say, a module gamedir/world/mymap.py

MAPSTR = r"""

+ 0 1 2

2 #-#-#
     /
1 #-#
  |  \
0 #---#

+ 0 1 2


"""
# use only defaults
LEGEND = {}

# tweak only one room. The 'xyz_room/exit' parents are made available
# by adding the xyzgrid prototypes to settings during installation.
# the '*' are wildcards and allows for giving defaults on this map.
PROTOTYPES = {
    (0, 0): {
	"prototype_parent": "xyz_room",
	"key": "A nice glade",
        "desc": "Sun shines through the branches above.}
    (0, 0, 'e'): {
	"prototype_parent": "xyz_exit",
	"desc": "A quiet path through the foilage"
    }
    ('*', '*'): {
	"prototype_parent": "xyz_room",
	"key": "In a bright forest",
	"desc": "There is green all around."
    },
    ('*', '*', '*'): {
	"prototype_parent": "xyz_exit",
	"desc": "The path leads further into the forest."
}

# collect all info for this one map
XYMAP_DATA = {
    "zcoord": "mymap"  # important!
    "map": MAPSTR,
    "legend": LEGEND,
    "prototypes": PROTOTYPES,
    "options": {}
}

# this can be skipped if there is only one map in module
XYMAP_DATA_LIST = [
    XYMAP_DATA
]

```

The above map would be added to the grid with

    $ evennia xyzgrid add world.mymap

In the following sections we'll discuss each component in turn.

### The Zcoord

Each XYMap on the grid has a Z-coordinate which usually can be treated just as the
name of the map. This is a string that must be unique across the entire grid.
It is added as the key 'zcoord' to `XYMAP_DATA`.

Actual 3D movement is usually impractical in a text-based game, so all movements
and pathfinding etc happens within each XYMap (up/down is 'faked' within the XY
plane). Even for the most hardcore of sci-fi space game, moving on a 2D plane
usually makes it much easier for players than to attempt to have them visualize
actual 3D movements.

If you really wanted an actual 3D coordinate system, you could theoretically
make all maps the same size and name them `0`, `1`, `2` etc. But even then, you
could not freely move up/down between every point (a special Transitional Node
is required as outlined below). Also pathfinding will only work per-XYMap.

Most users will want to just treat each map as a location, and name the
"Z-coordinate" things like `Dungeon of Doom`, `The ice queen's palace` or `City
of Blackhaven`.

### Map String

The creation of a new map starts with a _Map string_. This allows you to 'draw'
your map, describing and how rooms are positioned in an X,Y coordinate system.
It is added to `XYMAP_DATA` with the key 'map'.

```
MAPSTR = r"""

+ 0 1 2

2 #-#-#
     /
1 #-#
  |  \
0 #---#

+ 0 1 2

"""

```

On the coordinate axes, only the two `+` are significant - the numbers are
_optional_, so this is equivalent:

```
MAPSTR = r"""

+

  #-#-#
     /
  #-#
  | \
  #---#

+

"""
```
> Even though it's optional, it's highly recommended that you add numbers to
> your axes - if only for your own sanity.

The coordinate area starts _two spaces to the right_ and _two spaces
below/above_ the mandatory `+` signs (which marks the corners of the map area).
Origo `(0,0)` is in the bottom left (so X-coordinate increases to the right and
Y-coordinate increases towards the top). There is no limit to how high/wide the
map can be, but splitting a large world into multiple maps can make it easier
to organize.

Position is important on the grid. Full coordinates are placed on every _second_
space along all axes. Between these 'full' coordinates are `.5` coordinates.
Note that there are _no_ `.5` coordinates spawned in-game; they are only used
in the map string to have space to describe how rooms/nodes link to one another.

    + 0 1 2 3 4 5

    4           E
       B
    3

    2         D

    1    C

    0 A

    + 0 1 2 3 4 5

- `A` is at origo, `(0, 0)` (a 'full' coordinate)
- `B` is at `(0.5, 3.5)`
- `C` is at `(1.5, 1)`
- `D` is at `(4, 2)` (a 'full' coordinate).
- `E` is the top-right corner of the map, at `(5, 4)` (a 'full' coordinate)

The map string consists of two main classes of entities - _nodes_ and _links_.
- A _node_ usually represents a _room_ in-game (but not always). Nodes must
  _always_ be placed on a 'full' coordinate.
- A _link_ describes a connection between two nodes. In-game, links are usuallyj
  represented by _exits_. A link can be placed
  anywhere in the coordinate space (both on full and 0.5 coordinates). Multiple
  links are often _chained_ together, but the chain must always end in nodes
  on both sides.

> Even though a link-chain may consist of several steps, like `#-----#`,
> in-game it will still only represent one 'step' (e.g. you go 'east' only once
> to move from leftmost to the rightmost node/room).


### Map legend

There can be many different types of _nodes_ and _links_. Whereas the map
string describes where they are located, the _Map Legend_ connects each symbol
on the map to Python code.

```

LEGEND = {
    '#': xymap_legend.MapNode,
    '-': xymap_legende.EWMapLink
}

# added to XYMAP_DATA dict as 'legend': LEGEND below

```

The legend is optional, and any symbol not explicitly given in your legend will
fall back to its value in the default legend [outlined below](#default-legend).

- [MapNode](api:evennia.contrib.xyzgrid.xymap_legend#evennia.contrib.xyzgrid.xymap_legend.MapNode)
  is the base class for all nodes.
- [MapLink](api:evennia.contrib.xyzgrid.xymap_legend#evennia.contrib.xyzgrid.xymap_legend.MapLink)
  is the base class for all links.

As the _Map String_ is parsed, each found symbol is looked up in the legend and
initialized into the corresponding MapNode/Link instance.

#### Important node/link properties

These are relevant if you want to customize the map. The contrib already comes
with a full set of map elements that use these properties in various ways
(described in the next section).

Some useful properties of the
[MapNode](api:evennia.contrib.xyzgrid.xymap_legend#evennia.contrib.xyzgrid.xymap_legend.MapNode)
class (see class doc for hook methods):

- `symbol` (str) - The character to parse from the map into this node. By default this
  is `'#'` and _must_ be a single character (with the exception of `\\` that must
  be escaped to be used). Whatever this value defaults to, it is replaced at
  run-time by the symbol used in the legend-dict.
- `display_symbol` (str or `None`) - This is what is used to visualize this node
  in-game. This symbol must still only have a visual size of 1, but you could e.g.
  use some fancy unicode character (be aware of encodings to different clients
  though) or, commonly, add color tags around it. The `.get_display_symbol`
  of this class can be customized to generate this dynamically; by default it
  just returns `.display_symbol`. If set to `None` (default), the `symbol` is
  used.
- `interrupt_path` (bool): If this is set, the shortest-path algorithm will
  include this node normally, but the auto-stepper will stop when reaching it,
  even if not having reached its target yet. This is useful for marking 'points of
  interest' along a route, or places where you are not expected to be able to
  continue without some
  further in-game action not covered by the map (such as a guard or locked gate
  etc).
- `prototype` (dict) - The default `prototype` dict to use for reproducing this
  map component on the game grid. This is used if not overridden specifically
  for this coordinate in the "prototype" dict of `XYMAP_DATA`.. If this is not
  given, nothing will be spawned for this coordinate (a 'virtual' node can be
  useful for various reasons, mostly map-transitions).

Some useful properties of the
[MapLink](api:evennia.contrib.xyzgrid.xymap_legend#evennia.contrib.xyzgrid.xymap_legend.MapLink)
class (see class doc for hook methods):

- `symbol` (str) - The character to parse from the map into this node. This must
  be a single character, with the exception of `\\`. This will be replaced
  at run-time by the symbol used in the legend-dict.
- `display_symbol` (str or None)  - This is what is used to visualize this node
  later. This symbol must still only have a visual size of 1, but you could e.g.
  use some fancy unicode character (be aware of encodings to different clients
  though) or, commonly, add color tags around it. For further customization, the
  `.get_display_symbol` can be used.
- `default_weight` (int) - Each link direction covered by this link can have its
  separate weight (used for pathfinding). This is used if none specific weight
  is specified in a particular link direction.  This value must be >= 1, and can
  be higher than 1 if a link should be less favored.
- `directions` (dict) - this specifies which from which link edge to which other
  link-edge this link is connected; A link connecting the link's sw edge to its
  easted edge would be written as `{'sw': 'e'}` and read 'connects from southwest
  to east' This ONLY takes cardinal directions (not up/down). Note that if you
  want the link to go both ways, also the inverse (east to southwest) must be
  added.
- `weights (dict)` This maps a link's start direction to a weight. So for the
  `{'sw': 'e'}` link, a weight would be given as `{'sw': 2}`. If not given, a
  link will use the `default_weight`.
- `average_long_link_weights` (bool): This applies to the *first* link out of a
  node only.  When tracing links to another node, multiple links could be
  involved, each with a weight.  So for a link chain with default weights, `#---#`
  would give a total weight of 3. With this setting (default), the weight will
  be (1+1+1) / 3 = 1.  That is, for evenly weighted links, the length of the
  link-chain doesn't matter (this is usually what makes most sense).
- `direction_aliases` (dict): When displaying a direction during pathfinding,
  one may want to display a different 'direction' than the cardinal on-map one.
  For example 'up' may be visualized on the map as a 'n' movement, but the found
  path over this link should show as 'u'. In that case, the alias would be
  `{'n': 'u'}`.
- `multilink` (bool): If set, this link accepts links from all directions. It
  will usually use a custom `.get_direction` method to determine what these are
  based on surrounding topology. This setting is necessary to avoid infinite
  loops when such multilinks are next to each other.
- `interrupt_path` (bool): If set, a shortest-path solution will include this
  link as normal, but auto-stepper will stop short of actually moving past this
  link.
- `prototype` (dict) - The default `prototype` dict to use for reproducing this
  map component on the game grid. This is only relevant for the *first* link out
  of a Node (the continuation of the link is only used to determine its
  destination). This can be overridden on a per-direction basis.
- `spawn_aliases` (dict): A mapping `{direction: (key, alias, alias, ...),}`to
  use when spawning actual exits from this link. If not given, a sane set of
  defaults (`n=(north, n)` etc) will be used. This is required if you use any
  custom directions outside of the cardinal directions + up/down. The exit's key
  (useful for auto-walk) is usually retrieved by calling
  `node.get_exit_spawn_name(direction)`

Below is an example that changes the map's nodes to show up as red
(maybe for a lava map?):

```
from evennia.contrib.xyzgrid import xymap_legend

class RedMapNode(xymap_legend.MapNode):
    display_symbol = "|r#|n"


LEGEND = {
   '#': RedMapNode
}

```

#### Default Legend


Below is the default map legend. The `symbol` is what should be put in the Map
string. It must always be a single character. The `display-symbol` is what is
actually visualized when displaying the map to players in-game. This could have
colors etc. All classes are found in `evennia.contrib.xyzgrid.xymap_legend` and
their names are included to make it easy to know what to override.

```eval_rst
=============  ==============  ====  ===================  =========================================
symbol         display-symbol  type  class                description
=============  ==============  ====  ===================  =========================================
#              #               node  `BasicMapNode`       A basic node/room.
T                              node  `MapTransitionNode`  Transition-target for links between maps
                                                          (see below)
I (letter I)   #               node  `InterruptMapNode`   Point of interest, auto-step will always
                                                          stop here (see below).
\|             \|              link  `NSMapLink`          North-South two-way
\-             \-              link  `EWMapLink`          East-West two-way
/              /               link  `NESWMapLink`        NorthEast-SouthWest two-way
\\             \\              link  `SENWMapLink`        NorthWest two-way
u              u               link  `UpMapLink`          Up, one or two-way (see below)
d              d               link  `DownMapLink`        Down, one or two-way (see below)
x              x               link  `CrossMapLink`       SW-NE and SE-NW two-way
\+             \+              link  `PlusMapLink`        Crossing N-S and E-W two-way
v              v               link  `NSOneWayMapLink`    North-South one-way
^              ^               link  `SNOneWayMapLink`    South-North one-way
<              <               link  `EWOneWayMapLink`    East-West one-way
>              >               link  `WEOneWayMapLink`    West-East one-way
o              o               link  `RouterMapLink`      Routerlink, used for making link 'knees'
                                                          and non-orthogonal crosses (see below)
b              (varies)        link  `BlockedMapLink`     Block pathfinder from using this link.
                                                          Will appear as logically placed normal
                                                          link (see below).
i              (varies)        link  `InterruptMapLink`   Interrupt-link; auto-step will never
                                                          cross this link (must move manually, see
                                                          below)
t                              link  `TeleporterMapLink`  Inter-map teleporter; will teleport to
                                                          same-symbol teleporter on the same map.
                                                          (see below)
=============  ==============  ====  ===================  =========================================

```



#### Map Nodes

The basic map node (`#`) usually represents a 'room' in the game world. Links
can connect to the node from any of the 8 cardinal directions, but since nodes
must _only_ exist on full coordinates, they can never appear directly next to
each other.

    \|/
    -#-
    /|\

    ##     invalid!

All links or link-chains _must_ end in nodes on both sides.


    #-#-----#

    #-#-----   invalid!

#### One-way links

`>`,`<`, `v`, `^` are used to indicate one-way links. These indicators should
either be _first_ or _last_ in a link chain (think of them as arrows):

    #----->#
    #>-----#

These two are equivalent, but the first one is arguably easier to read. It is also
faster to parse since the parser on the rightmost node immediately sees that the
link in that direction is impassable from that direction.

> Note that there are no one-way equivalents to the `\` and `/` directions. This
> is not because it can't be done but because there are no obvious ASCII
> characters to represent diagonal arrows. If you want them, it's easy enough to
> subclass the existing one-way map-legend to add one-way versions of diagonal
> movement as well.

#### Up- and Down-links

Links like `u` and `d` don't have a clear indicator which directions they
connect (unlike e.g. `|` and `-`).

So placing them (and many similar types of map elements) requires that the
directions are visually clear. For example, multiple links cannot connect to the
up-down links (it'd be unclear which leads where) and if adjacent to a node, the
link will prioritize connecting to the node. Here are some examples:

        #
        u    - moving up in BOTH directions will bring you to the other node (two-way)
        #

        #
        |    - one-way up from the lower node to the upper, south to go back
        u
        #

        #
        ^    - true one-way up movement, combined with a one-way 'n' link
        u
        #

        #
        d    - one-way up, one-way down again (standard up/down behavior)
        u
        #

        #u#
        u    - invalid since top-left node has two 'up' directions to go to
        #

        #     |
        u# or u-   - invalid since the direction of u is unclear
        #     |


#### Interrupt-nodes

An interrupt-node (`I`, `InterruptMapNode`) is a node that acts like any other
node except it is considered a 'point of interest' and the auto-walk of the
`goto` command will always stop auto-stepping at this location.

	#-#-I-#-#

So if auto-walking from left to right, the auto-walk will correctly map a path
to the end room, but will always stop at the `I` node. If the user _starts_ from
the `I` room, they will move away from it without interruption (so you can
manually run the `goto` again to resume the auto-step).

The use of this room is to anticipate blocks not covered by the map. For example
there could be a guard standing in this room that will arrest you unless you
show them the right paperwork - trying to auto-walk past them would be bad!

By default, this node looks just like a normal `#` to the player.

#### Interrupt-links

The interrupt-link (`i`, `InterruptMapLink`) is equivalent to the
`InterruptMapNode` except it applies to a link. While the pathfinder will
correctly trace a path to the other side, the auto-stepper will never cross an
interrupting link - you have to do so 'manually'. Similarly to up/down links,
the InterruptMapLink must be placed so that its direction is un-ambiguous (with
a priority of linking to nearby nodes).

	#-#-#i#-#

When pathfinding from left to right, the pathfinder will find the end room just
fine, but when auto-stepping, it will always stop at the node just to the left
of the `i` link. Rerunning `goto` will not matter.

This is useful for automatically handle in-game blocks not part of the map.
An example would be a locked door - rather than having the auto-stepper trying
to walk accross the door exit (and failing), it should stop and let the user
cross the threshold manually before they can continue.

Same as for interrupt-nodes, the interrupt-link looks like the expected link to the user
(so in the above example, it would show as `-`).

#### Blocked links

Blockers (`b`, `BlockedMapLink`) indicates a route that the pathfinder should not use. The
pathfinder will treat it as impassable even though it will be spawned as a
normal exit in-game.


	#-#-#b#-#

There is no way to auto-step from left to right because the pathfinder will
treat the `b` (block) as if there was no link there (technically it sets the
link's `weight` to a very high number). The player will need to auto-walk to the
room just to the left of the block, manually step over the block and then
continue from there.

This is useful both for actual blocks (maybe the room is full of rubble?) and in
order to avoid players auto-walking into hidden areas or finding the way out of
a labyrinth etc. Just hide the labyrinth's exit behind a block and `goto exit`
will not work (admittedly one may want to turn off pathfinding altogether on
such maps).


#### Router-links

Routers (`o`, `RouterMapLink`) allow for connecting nodes with links at an
angle, by creating a 'knee'.

	#----o
	|     \
	#-#-#  o
	       |
	     #-o

Above, you can move east between from the top-left room and the bottommost
room. Remember that the length of links does not matter, so in-game this will
only be one step (one exit `east` in each of the two rooms).

Routers can link connect multiple connections as long as there as as many
'ingoing' as there are 'outgoing' links. If in doubt, the system will assume a
link will continue to the outgoing link on the opposite side of the router.

          /
        -o    - this is ok, there can only be one path, w-ne

         |
        -o-   - equivalent to '+': one n-s and one w-e link crossing
         |

        \|/
        -o-   - all links are passing straight through
        /|\

        -o-   - w-e link pass straight through, other link is sw-s
        /|

        -o    - invalid; impossible to know which input goes to which output
        /|


#### Teleporter Links

Teleporters (`TeleportMapLink`) always come in pairs using the same map symbol
(`'t'` by default).  When moving into one link, movement continues out the
matching teleport link. The pair must both be on the same XYMap and both sides
must connect/chain to a node (like all links). Only a single link (or node) may
connect to the teleport link.

Pathfinding will also work correctly across the teleport.

	#-t     t-#

Moving east from the leftmost node will have you appear at the rightmost node
and vice versa (think of the two `t` as thinking they are in the same location).

Teleportation movement is always two-way, but you can use one-way links to
create the effect of a one-way teleport:

	#-t    t>#

In this example you can move east across the teleport, but not west since the
teleporter-link is hidden behind a one-way exit.

	#-t#     (invalid!)

The above is invalid since only one link/node may connect to the teleport at a
time.

You can have multiple teleports on the same map, by assigning each pair a
different (unused) unique symbol in your map legend:


```python
# in your map definition module

from evennia.contrib.xyzgrid import xymap_legend

MAPSTR = r"""

+ 0 1 2 3 4

2 t q #   q
  | v/ \  |
1 #-#-p #-#
  |       |
0 #-t p>#-#

+ 0 1 2 3 4

"""

LEGEND = {
    't': xymap_legend.TeleporterMapLink,
    'p': xymap_legend.TeleporterMapLink,
    'q': xymap_legend.TeleportermapLink,
}


```

#### Map-Transition Nodes

The map transition (`MapTransitionNode`) teleports between XYMaps (a
Z-coordinate transition, if you will), like walking from the "Dungeon" map to
the "Castle" map. Unlike other nodes, the MapTransitionNode is never spawned
into an actual room (it has no prototype). It just holds an XYZ
coordinate pointing to somewhere on the other map. The link leading _to_ the
node will use those coordinates to make an exit pointing there. Only one single
link may lead to this type of node.

Unlike for `TeleporterMapLink`, there need _not_ be a matching
`MapTransitionNode` on the other map - the transition can choose to send the
player to _any_ valid coordinate on the other map.

Each MapTransitionNode has a property `target_map_xyz` that holds the XYZ
coordinate the player should end up in when going towards this node. This
must be customized in a child class for every transition.

If there are more than one transition, separate transition classes should be
added, with different map-legend symbols:


```python
# in your map definition module (let's say this is mapB)

from evennia.contrib.xyzgrid import xymap_legend

MAPSTR = r"""

+ 0 1 2

2   #-C
    |
1 #-#-#
     \
0 A-#-#

+ 0 1 2


"""

class TransitionToMapA(xymap_legend.MapTransitionNode):
    """Transition to MapA"""
    target_map_xyz = (1, 4, "mapA")

class TransitionToMapC(xymap_legend.MapTransitionNode):
    """Transition to MapB"""
    target_map_xyz = (12, 14, "mapC")

LEGEND = {
    'A': TransitionToMapA
    'C': TransitionToMapC

}

```

Moving west from `(1,0)` will bring you to `(1,4)` of MapA, and moving east from
`(1,2)` will bring you to `(12,14)` on MapC (assuming those maps exist).

A map transition is always one-way, and can lead to the coordinates of _any_
existing node on the other map:

	map1        map2

	#-T         #-#---#-#-#-#

A player moving east towards `T` could for example end up at the 4th `#` from
the left on map2 if so desired (even though it doesn't make sense visually).
There is no way to get back to map1 from there.

To create the effect of a two-way transition, one can set up a mirrored
transition-node on the other map:

	citymap    dungeonmap

	#-T        T-#


The transition-node of each map above has `target_map_xyz` pointing to the
coordinate of the `#` node of the other map (_not_ to the other `T`, that is not
spawned and would lead to the exit finding no destination!). The result is that
one can go east into the dungeon and then immediately go back west to the city
across the map boundary.

### Prototypes

[Prototypes](../Components/Prototypes) are dicts that describe how to _spawn_ a new instance
of an object. Each of the _nodes_ and _links_ above have a default prototype
that allows the `evennia xyzgrid spawn` command to convert them to
a [XYZRoom](api:evennia.contrib.xyzgrid.xyzroom#XYZRoom)
or an [XYZExit](api:evennia.contrib.xyzgrid.xyzroom#XYZExit) respectively.

The default prototypes are found in `evennia.contrib.xyzgrid.prototypes` (added
during installation of this contrib), with `prototype_key`s `"xyz_room"` and
`"xyz_exit"` - use these as `prototype_parent` to add your own custom prototypes.

The `"prototypes"` key of the XYMap-data dict allows you to customize which
prototype is used for each coordinate in your XYMap. The coordinate is given as
`(X, Y)` for nodes/rooms and `(X, Y, direction)` for links/exits, where the
direction is one of "n", "ne", "e", "se", "s", "sw", "w", "nw", "u" or "d". For
exits, it's recommended to _not_ set a `key` since this is generated
automatically by the grid spawner to be as expected ("north" with alias "n", for
example).

A special coordinate is `*`. This acts as a wild card for that coordinate and
allows you to add 'default' prototypes to be used for rooms.


```python

MAPSTR = r"""

+ 0 1

1 #-#
   \
0 #-#

+ 0 1


"""


PROTOTYPES = {
    (0,0): {
	"prototype_parent": "xyz_room",
	"key": "End of a the tunnel",
	"desc": "This is is the end of the dark tunnel. It smells of sewage."
    },
    (0,0, 'e') : {
	"prototype_parent": "xyz_exit",
	"desc": "The tunnel continues into darkness to the east"
    },
    (1,1): {
	"prototype_parent": "xyz_room",
	"key": "Other end of the tunnel",
	"desc": The other end of the dark tunnel. It smells better here."
    }
    # defaults
    ('*', '*'): {
    	"prototype_parent": "xyz_room",
	"key": "A dark tunnel",
	"desc": "It is dark here."
    },
    ('*', '*', '*'): {
	"prototype_parent": "xyz_exit",
	"desc": "The tunnel stretches into darkness."
    }
}

XYMAP_DATA = {
    # ...
    "prototypes": PROTOTYPES
    # ...
}

```

When spawning the above map, the room at the bottom-left and top-right of the
map will get custom descriptions and names, while the others will have default
values. One exit (the east exit out of the room in the bottom-left will have a
custom description.

> If you are used to using prototypes, you may notice that we didn't add a
> `prototype_key` for the above prototypes. This is normally required for every
> prototype. This is for convenience - if
> you don't add a `prototype_key`, the grid will automatically generate one for
> you - a hash based on the current XYZ (+ direction) of the node/link to spawn.

If you find yourself changing your prototypes after already spawning the
grid/map, you can rerun `evennia xyzgrid spawn` again; The changes will be
picked up and applied to the existing objects.

#### Extending the base prototypes

The default prototypes are found in `evennia.contrib.xyzgrid.prototypes` and
should be included as `prototype_parents` for prototypes on the map. Would it
not be nice to be able to change these and have the change apply to all of the
grid? You can, by adding the following to your `mygame/server/conf/settings.py`:

    XYZROOM_PARENT_PROTOTYPE_OVERRIDE = {"typeclass": "myxyzroom.MyXYZRoom"}
    XYZEXIT_PARENT_PROTOTYPE_OVERRIDE = {...}

Only add what you want to change - these dicts will _extend_ the default parent
prototypes rather than replace them. As long as you define your map's prototypes
to use a `prototype_parent` of `"xyz_room"` and/or `"xyz_exit"`, your changes
will now be applied. You may need to respawn your grid and reload the server
after a change like this.

### Options

The last element of the `XYMAP_DATA` dict is the `"options"`, for example

```
XYMAP_DATA = {
    # ...
    "options": {
	"map_visual_range": 2
    }
}

```

The `options` dict is passed as `**kwargs` to `XYZRoom.return_appearance`
when visualizing the map in-game. It allows for making different maps display
differently from one another (note that while these options are convenient one
could of course also override `return_appearance` entirely by inheriting from
`XYZRoom` and then pointing to it in your prototypes).

The default visualization is this:

```
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                     #---#
                                    /
                                   @-
-~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Dungeon Entrance
To the east, a narrow opening leads into darkness.
Exits: northeast and east

```

- `map_display` (bool): This turns off the display entirely for this map.
- `map_character_symbol` (str): The symbol used to show 'you' on the map. It can
  have colors but should only take up one character space. By default this is a
  green `@`.
- `map_visual_range` (int): This how far away from your current location you can
  see.
- `map_mode` (str): This is either "node" or "scan" and affects how the visual
  range is calculated.
  In "node" mode, the range shows how many _nodes_ away from that you can see. In "scan"
  mode you can instead see that many _on-screen characters_ away from your character.
  To visualize, assume this is the full map (where '@' is the character location):

      #----------------#
      |                |
      |                |
      # @------------#-#
      |                |
      #----------------#

  This is what the player will see in 'nodes' mode with `map_visual_range=2`:

      @------------#-#

  ... and in 'scan' mode:

      |
      |
      # @--
      |
      #----

  The 'nodes' mode has the advantage of showing only connected links and is
  great for navigation but depending on the map it can include nodes quite
  visually far away from you. The 'scan' mode can accidentally reveal unconnected
  parts of the map (see example above), but limiting the range can be used as a
  way to hide information.

  This is what the player will see in 'nodes' mode with `map_visual_range=1`:

      @------------#

  ... and in 'scan' mode:

      @-

  One could for example use 'nodes' for outdoor/town maps and 'scan' for
  exploring dungeons.

- `map_align` (str): One of 'r', 'c' or 'l'. This shifts the map relative to
  the room text. By default it's centered.
- `map_target_path_style`: How to visualize the path to a target. This is a
  string that takes the `{display_symbol}` formatting tag. This will be replaced
  with the `display_symbol` of each map element in the path. By default this is
  `"|y{display_symbol}|n"`, that is, the path is colored yellow.
- `map_fill_all` (bool): If the map area should fill the entire client width
  (default) or change to always only be as wide as the room description. Note
  that in the latter case, the map can end up 'dancing around' in the client window
  if descriptions vary a lot in width.
- `map_separator_char` (str): The char to use for the separator-lines between the map
  and the room description. Defaults to `"|x~|n"` - wavy, dark-grey lines.


Changing the options of an already spawned map does not require re-spawning the
map, but you _do_ need to reload the server!

### About the Pathfinder

The new `goto` command exemplifies the use of the _Pathfinder_. This
is an algorithm that calculates the shortest route between nodes (rooms) on an
XY-map of arbitrary size and complexity. It allows players to quickly move to
a location if they know that location's name. Here are some details about

- The pathfinder parses the nodes and links to build a matrix of distances
  of moving from each node to _all_ other nodes on one XYMap. The path
  is solved using the
  [Dijkstra algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm).
- The pathfinder's matrices can take a long time to build for very large maps.
  Therefore they are are cached as pickled binary files in
  `mygame/server/.cache/` and only rebuilt if the map changes. They are safe to
  delete (you can also use `evennia xyzgrid initpath` to force-create/rebuild the cache files).
- Once cached, the pathfinder is fast (Finding a 500-step shortest-path over
  20 000 nodes/rooms takes below 0.1s).
- It's important to remember that the pathfinder only works within _one_ XYMap.
  It will not find paths across map transitions. If this is a concern, one can consider
  making all regions of the game as one XYMap. This probably works fine, but makes it
  harder to add/remove new maps to/from the grid.
- The pathfinder will actually sum up the 'weight' of each link to determine which is
  the 'cheapest' (shortest) route. By default every link except blocking links have
  a cost of 1 (so cost is equal to the number of steps to move between nodes).
  Individual links can however change this to a higher/lower weight (must be >=1).
  A higher weight means the pathfinder will be less likely to use that route
  compared to others (this can also be vidually confusing for the user, so use with care).
- The pathfinder will _average_ the weight of long link-chains. Since all links
  default to having the same weight (=1), this means that
  `#-#` has the same movement cost as `#----#` even though it is visually 'shorter'.
  This behavior can be changed per-link by using links with
`average_long_link_weights = False`.


##  XYZGrid

The `XYZGrid` is a [Global Script](../Components/Scripts) that holds all `XYMap` objects on
the grid. There should be only one XYZGrid created at any time.

To access the grid in-code, there are several ways:

- You can search for the grid like any other Script. It's named "XYZGrid".

	grid = evennia.search_script("XYZGrid")[0]

  (`search_script` always returns a list)
- You can get it with `evennia.contrib.xyzgrid.xyzgrid.get_xyzgrid`

	from evennia.contrib.xyzgrid.xyzgrid import get_xyzgrid
	grid = get_xyzgrid()

  This will *always* return a grid, creating an empty grid if one didn't
  previously exist. So this is also the recommended way of creating a fresh grid
  in-code.
- You can get it from an existing XYZRoom/Exit by accessing their `.xyzgrid`
  property

	grid = self.caller.location.xyzgrid  # if currently in grid room

Most tools on the grid class have to do with loading/adding and deleting maps,
something you are expected to use the `evennia xyzgrid` commands for. But there
are also several methods that are generally useful:

- `.get_room(xyz)` - Get a room at a specific coordinate `(X, Y, Z)`. This will
  only work if the map has been actually spawned first. For example
  `.get_room((0,4,"the dark castle))`. Use `'*'` as a wild card, so
  `.get_room(('*','*',"the dark castle))` will get you all rooms spawned on the dark
 castle map.
- `.get_exit(xyz, name)` - get a particular exit, e.g.
  `.get_exit((0,4,"the dark castle", "north")`. You can also use `'*'` as
  wildcards.

One can also access particular parsed `XYMap` objects on the `XYZGrid` directly:

- `.grid` - this is the actual (cached) store of all XYMaps, as `{zcoord: XYMap, ...}`
- `.get_map(zcoord)` - get a specific XYMap.
- `.all_maps()` - get a list of all XYMaps.

Unless you want to heavily change how the map works (or learn what it does), you
will probably never need to modify the `XYZMap` object itself. You may want to
know how to call find the pathfinder though:

- `xymap.get_shortest_path(start_xy, end_xy)`
- `xymap.get_visual_range(xy, dist=2, **kwargs)`

See the [XYMap](api:evennia.contrib.xyzgrid.xymap#XYMap) documentation for
details.


## XYZRoom and XYZExit

These are new custom [Typeclasses](../Components/Typeclasses) located in
`evennia.contrib.xyzgrid.xyzroom`. They extend the base `DefaultRoom` and
`DefaultExit` to be aware of their `X`, `Y` and `Z` coordinates.

```warning::

    You should usually **not** create XYZRooms/Exits manually. They are intended
    to be created/deleted based on the layout of the grid. So to add a new room, add
    a new node to your map. To delete it, you remove it. Then rerun
    **evennia xyzgrid spawn**. Having manually created XYZRooms/exits in the mix
    can lead to them getting deleted or the system getting confused.

    If you **still** want to create XYZRoom/Exits manually (don't say we didn't
    warn you!), you should do it with their `XYZRoom.create()` and
    `XYZExit.create()` methods. This makes sure the XYZ they use are unique.

```

Useful (extra) properties on `XYZRoom`, `XYZExit`:

- `xyz` The `(X, Y, Z)` coordinate of the entity, for example `(23, 1, "greenforest")`
- `xyzmap` The `XYMap` this belongs to.
- `get_display_name(looker)` - this has been modified to show the coordinates of
  the entity as well as the `#dbref` if you have Builder or higher privileges.
- `return_appearance(looker, **kwargs)` - this has been extensively modified for
  `XYZRoom`, to display the map. The `options` given in `XYMAP_DATA` will appear
  as `**kwargs` to this method and if you override this you can customize the
  map display in depth.
- `xyz_destination` (only for `XYZExits`) - this gives the xyz-coordinate of
  the exit's destination.

The coordinates are stored as [Tags](../Components/Tags) where both rooms and exits tag
categories `room_x_coordinate`, `room_y_coordinate` and `room_z_coordinate`
while exits use the same in addition to tags for their destination, with tag
categories `exit_dest_x_coordinate`, `exit_dest_y_coordinate` and
`exit_dest_z_coordinate`.

The make it easier to query the database by coordinates, each typeclass offers
custom manager methods. The filter methods allow for `'*'` as a wildcard.

```python

# find a list of all rooms in map foo
rooms = XYZRoom.objects.filter_xyz(('*', '*', 'foo'))

# find list of all rooms with name "Tunnel" on map foo
rooms = XYZRoom.objects.filter_xyz(('*', '*', 'foo'), db_key="Tunnel")

# find all rooms in the first column of map footer
rooms = XYZRoom.objects.filter_xyz((0, '*', 'foo'))

# find exactly one room at given coordinate (no wildcards allowed)
room = XYZRoom.objects.get_xyz((13, 2, foo))

# find all exits in a given room
exits = XYZExit.objects.filter_xyz((10, 4, foo))

# find all exits pointing to a specific destination (from all maps)
exits = XYZExit.objects.filter_xyz_exit(xyz_destination=(13,5,'bar'))

# find exits from a room to anywhere on another map
exits = XYZExit.objects.filter_xyz_exit(xyz=(1, 5, 'foo'), xyz_destination=('*', '*', 'bar'))

# find exactly one exit to specific destination (no wildcards allowed)
exit = XYZExit.objects.get_xyz_exit(xyz=(0, 12, 'foo'), xyz_destination=(5, 2, 'foo'))

```

You can customize the XYZRoom/Exit by having the grid spawn your own subclasses
of them. To do this you need to override the prototype used to spawn rooms on
the grid. Easiest is to modify the base prototype-parents in settings (see the
[Extending the base prototypes](#extending-the-base-prototypes) section above).

## Working with the grid

The work flow of working with the grid is usually as follows:

1. Prepare a module with a _Map String_, _Map Legend_, _Prototypes_ and
   _Options_ packaged into a dict `XYMAP_DATA`. Include multiple maps per module
   by adding several `XYMAP_DATA` to a variable `XYMAP_DATA_LIST` instead.
2. If your map contains `TransitionMapNodes`, the target map must either also be
   added or already exist in the grid. If not, you should skip that node for
   now (otherwise you'll face errors when spawning because the exit-destination
   does not exist).
2. Run `evennia xyzgrid add <module>` to register the maps with the grid. If no
   grid existed, it will be created by this. Fix any errors reported by the
   parser.
3. Inspect the parsed map(s) with `evennia xyzgrid show <zcoord>` and make sure
   they look okay.
4. Run `evennia xyzgrid spawn` to spawn/update maps into actual `XYZRoom`s and
   `XYZExit`s.
5. If you want you can now tweak your grid manually by usual building commands.
   Anything you do _not_ specify in your grid prototypes you can
   modify locally in your game - as long as the whole room/exit is not deleted,
   those will be untouched by `evennia xyzgrid spawn`.  You can also dig/open
   exits to other rooms 'embedded' in your grid. These exits must _not_ be named
   one of the grid directions (north, northeast, etc, nor up/down) or the grid
   will delete it next `evennia xyzgrid spawn` runs (since it's not on the map).
6. If you want to add new grid-rooms/exits you should _always_ do so by
   modifying the _Map String_ and then rerunning `evennia xyzgrid spawn` to
   apply the changes.
