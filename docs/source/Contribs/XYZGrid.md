# XYZGrid contribution

This contrib adds a 'coordinate grid' to the game, with rooms that are aware of
their X, Y, Z coordinate. It also adds shortest-path pathfinding, auto-stepping
and map visualization.

The system consists of 2D (XY) maps, where the Z
coordinate is the name of the map. Each map can be linked together.

The grid supports 8 cardinal directions (north, northeast, east etc) as well as
a 'fake' up/down directions (you enter up/down in-game but are actually moving to
a different XY position on the same map).

An (XY) map is defined as a Python string, using a simple syntax;

```
#-#-#-#      #
|  /         d
#-#          |   #
   \         u   |\
o---#--------#---+-#-#
|            ^   |/
|            |   #
v            |
#-#-#-#-#----#
    |x|x|
    #-#-#-#

```

(descriptions of components are found below).

Basically the system will parse this string together with a _legend_ (a mapping
describing how each symbol of the map behaves) to generate a representation of
the map that can then be _spawned_ into actual rooms and exits. The map can also
contain links to other maps this (map transitions).

The generation and maintenance of the map topology (how rooms are placed and
relate to each other) are maintained entirely from outside of the game.

## Installation

1. Import and add the `evennia.contrib.commands.XYZGridCmdSet` to the
   `CharacterCmdset` cmdset in `mygame/commands.default_cmds.py`. Reload
   the server. This makes the `map`, `goto/path` and modified `teleport`  and
   `open` commands available in-game.
2. Edit `mygame/server/conf/settings.py` and set

        EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.launchcmd.xyzcommand'

3. Run the new `evennia xyzgrid help` for instructions on how to build the grid.

## Example usage

After installation, do the following (from your command line, where the
`evennia` command is available) to install an example grid:

    evennia xyzgrid init
    evennia xyzgrid add evennia.contrib.xyzgrid.map_example
    evennia xyzgrid list
    evennia xyzgrid show "the large tree"
    evennia xyzgrid show "the small cave"
    evennia xyzgrid build
    evennia reload

(remember to reload the server after build operations).

Now you can log into the
server and do `teleport (3,0,the large tree)` to teleport into the map.

You can use `open togrid = (3, 0, the large tree)` to open a permanent (one-way)
exit from your current location into the grid. To make a way back to a non-grid
location just stand in a grid room and open a new exit out of it:
`open tolimbo = #2`.

Try `goto view` to go to the top of the tree and `goto dungeon` to go down to
the dungeon entrance at the bottom of the tree.

## A note on 3D = 2D + 1D

Since actual 3D movement usually is impractical to visualize in text, most
action in this contrib takes place on 2-dimenstional XY-planes we refer to as
_Maps_.  Changing Z-coordinate means moving to another Map. Maps does not need
be the same size as one another and there is no (enforced) concept of moving
'up' or 'down' between maps - instead you basically 'teleport' between them,
which means you can have your characters end up anywhere you want in the next
map, regardless of which XY coordinate they were leaving from.

If you really want an actual 3D coordinate system, you could make all maps the
same size and name them `0`, `1`, `2` etc. But most users will want to just
treat each map as a location, and name the "Z-coordinate" things like `Dungeon
of Doom`, `The ice queen's palace` or `City of Blackhaven`.

Whereas the included rooms and exits can be used for 'true' 3D movement, the more
advanced tools like pathfinding will only operate within each XY `Map`.

## Components of the XYgrid

1. The Map String - describes the topology of a single
   map/location/Z-coordinate.
2. The Map Legend - describes how to parse each symbol in the map string to a
   topological relation, such as 'a room' or 'a two-way link east-west'.
3. The XYMap - combines the Map String and Legend into a parsed object with
   pathfinding and visual-range handling.
4. The MultiMap - tracks multiple maps
5. Rooms, Exits and Prototypes - custom Typeclasses that understands XYZ coordinates.
   The prototype describes how to build a database-entity from a given
   Map Legend component.
6. The Grid - the combination of prototype-built rooms/exits with Maps for
   pathfinding and visualization. This is kept in-sync with changes to Map
   Strings.


### The Map string

A `Map` represents one Z-coordinate/location. The Map starts out as an text
string visually laying out one 2D map (so one Z-position). It is created
manually by the developer/builder outside of the game. The string-map
has one character per node(room) and descibe how rooms link together. Each
symbol is linked to a particular abstract Python class which helps parse
the map-string. While the contrib comes with a large number of nodes and links,
one can also make one's own.

```
MAP = r"""

+ 0 1 2 3

3 #-#---o
    v   |
2   #-# |
    |x| ^
1   #-#-#
   / \
0 #   #d#

+ 0 1 2 3

"""

```
Above, only the two `+`-characters in the upper-left and bottom-left are
required to mark the start of grid area - the numbered axes are optional but
recommended for readability! Note that the coordinate system has (0, 0) in the
bottom left - this means that +Y movement is 'upwards' in the string as
expected.

### Map Legend

The map legend is a mapping of one-character symbols to Python classes
representing _Nodes_ (usually equivalent to in-game rooms) or _Links_ (which
usually start as an Exit, but the length of the link only describes the
target-destination and has no in-game representation otherwise). These 'map
components' are Python classes that can be inherited and modified as needed.

The default legend support nearly 20 different symbols, including:

- Nodes (rooms) are always on XY coordinates (not between) and
- 8 two-way cardinal directions (n, ne etc)
- up/down - this is a 'fake' up-down using XY coordinates for ease of
  visualization (the exit is just called 'up' or 'down', unless you display the
  actual coordinate to the user they'll never know the difference).
- One-way links in 4 cardinal directions (not because it's hard to add more,
  but because there are no obvious ASCII characters for the diaginal movements ...)
- Multi-step links are by default considered as one step in-game.
- 'Invisible' symbols that are used to block or act as deterrent for the
  pathfinder to use certain routes (like a hidden entrance you should be
  auto-pathing through).
- 'Points of interest' are nodes or links where the auto-stepper will always
  stop, even if it can see what's behind. This is great for places where you
  expect to have a door or a guard (which are not represented on the map).
- Teleporter-links, for jumping from one edge of the map to the other without
  having to draw an actual link across. Good for maps that 'wrap around'.
- Transitional links between maps/locations/Z-positions. Note that pathfinding
  will _not_ work across map transitions.

### Map

All `Map strings` are combined with their `Map Legends` to be parsed into a `Map`
object. The `Map` object has the relations between all nodes stored in a very
efficient matrix for quick lookup. This allows for:

- Shortest-path finding. The shortest-path from one coordinate to another
  is calculated using an optimized implementation of the
  [Dijkstra algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm).
  While large solutions can be slow (up to 20 seconds for a 10 000 node map
  with 8 cardinal links between every room), the solution is cached to disk -
  meaning that as long as the map-string does not change, subsequent
  path-finding operations are all very fast (<0.1s, usually much faster).
  Once retrieving the route, the player can easily be auto-stepped along it.
- Visual-range - useful for displaying the map to the user as they move. The
  system can either show everything within a certain grid-distance, or a
  certain number of connected nodes away from the character's position.
- Visualize-paths. The system can highlight the path to a target on the grid.
  Useful for showing where the pathfinder is moving you.
- The Map parser can be customized so as to give different weight to longer
  links - by default a 3-step long link has the same 'weight' for the
  pathfinder as two nodes next to each other. This could be combined with
  some measure of it taking longer to traverse such exits.


### MultiMap

Multiple `Maps` (or 'Z coordinates') are combined together in the `MultiMap`
handler.  The MultiMap knows all maps in the game because it must be possible to
transition from one to the other by giving the name/Z-coordinate to jump to.

It's worth pointing out that neither `Maps`, nor `MultiMap` has any direct
link to the game at this point - these are all just abstract _representations_
of the game world stored in memory.


### Rooms and Exits

The component (_Nodes_ and _Links_ both) of each `Map` can have a `prototype`
dict associated with it. This is the default used when converting this node/link
into something actually visible in-game. It is also possible to override
the default on a per-XY coordinate level.

- For _Nodes_, the `evennia.contrib.xyzgrid.room.XYZRoom` typeclass (or a child
  thereof) should be used. This sets up storage of the XYZ-coordinates correctly
  (using `Tags`).
- For _Links_, one uses the `evennia.contrib.xyzgrid.room.XYZExit` typeclass
  (or a child thereof). This also sets up the proper coordinates, both for the
  location they are in and for the exit's destination.


### The Grid

The combination of `MultiMaps` and `prototypes` are used to create the `Grid`, a
series of coordinate-bound rooms/exits actually present in the game world. Each
node of this grid has a unique `(X, Y, Z)` position (no duplicates).

Once the prototypes have been used to create the grid, it must be kept in-sync
with any changes in map-strings `Map` structures - otherwise pathfinding and
visual-range displays will not work (or at least be confusingly inaccurate). So
changes should _only_ be done on the Map-string outside of the game, _not_ by
digging new XYZRooms manually!

The contrib provides a sync mechanism. This compares the stored `Map` with
the current topology and rebuilds/removes any nodes/rooms/links/exits that
has changed. Since this process can be slow, you need to run this manually when
you know you've made a change.

Remember that syncing is only necesssary for topological changes! That is,
changes visible in the map string. Fixing the `desc` of a room or adding a new
enemy does not require any re-sync. Also, things not visible on the
map (like a secret entrance) should not be available to the pathfinder anyway.

You can dig non-XYZRoom objects and link them to `XYZRooms` with no issues -
they will work like normal in-game. But such rooms (and exits leading to/from
them) are _not_ considered part of the grid for the purposes of pathfinding etc.
Exactly how to organize this depends on your game.


