# Dynamic In Game Map


## Introduction

An often desired feature in a MUD is to show an in-game map to help navigation. The [Static in-game
map](Static-In-Game-Map) tutorial solves this by creating a *static* map, meaning the map is pre-
drawn once and for all - the rooms are then created to match that map. When walking around, parts of
the static map is then cut out and displayed next to the room description.

In this tutorial we'll instead do it the other way around; We will dynamically draw the map based on
the relationships we find between already existing rooms.

## The Grid of Rooms

There are at least two requirements needed for this tutorial to work.

1. The structure of your mud has to follow a logical layout. Evennia supports the layout of your
world to be 'logically' impossible with rooms looping to themselves or exits leading to the other
side of the map. Exits can also be named anything, from "jumping out the window" to "into the fifth
dimension". This tutorial assumes you can only move in the cardinal directions (N, E, S and W).
2. Rooms must be connected and linked together for the map to be generated correctly. Vanilla
Evennia comes with a admin command [@tunnel](./Default-Command-Help#tunnel-cmdtunnel) that allows a
user to create rooms in the cardinal directions, but additional work is needed to assure that rooms
are connected. For example, if you `@tunnel east` and then immediately do `@tunnel west` you'll find
that you have created two completely stand-alone rooms. So care is needed if you want to create a
"logical" layout. In this tutorial we assume you have such a grid of rooms that we can generate the
map from.

## Concept

Before getting into the code, it is beneficial to understand and conceptualize how this is going to
work. The idea is analogous to a worm that starts at your current position. It chooses a direction
and 'walks' outward from it, mapping its route as it goes. Once it has traveled a pre-set distance
it stops and starts over in another direction. An important note is that we want a system which is
easily callable and not too complicated. Therefore we will wrap this entire code into a custom
Python class (not a typeclass as this doesn't use any core objects from evennia itself).

We are going to create something that displays like this when you type 'look':

```
    Hallway

          [.]   [.]
          [@][.][.][.][.]
          [.]   [.]   [.]

    The distant echoes of the forgotten
    wail throughout the empty halls.

    Exits: North, East, South
```

Your current location is defined by `[@]` while the `[.]`s are other rooms that the "worm" has seen
since departing from your location.

## Setting up the Map Display

First we must define the components for displaying the map. For the "worm" to know what symbol to
draw on the map we will have it check an Attribute on the room it visits called `sector_type`. For
this tutorial we understand two symbols - a normal room and the room with us in it. We also define a
fallback symbol for rooms without said Attribute - that way the map will still work even if we
didn't prepare the room correctly. Assuming your game folder is named `mygame`, we create this code
in `mygame/world/map.py.`

```python
# in mygame/world/map.py

# the symbol is identified with a key "sector_type" on the
# Room. Keys None and "you" must always exist.
SYMBOLS = { None : ' . ', # for rooms without sector_type Attribute
            'you' : '[@]',
            'SECT_INSIDE': '[.]' }
```

Since trying to access an unset Attribute returns `None`, this means rooms without the `sector_type`
Atttribute will show as ` . `. Next we start building the custom class `Map`. It will hold all
methods we need.

```python
# in mygame/world/map.py

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None
```

- `self.caller` is normally your Character object, the one using the map.
- `self.max_width/length` determine the max width and length of the map that will be generated. Note
that it's important that these variables are set to *odd* numbers to make sure the display area has
a center point.
- ` self.worm_has_mapped` is building off the worm analogy above. This dictionary will store all
rooms the "worm" has mapped as well as its relative position within the grid. This is the most
important variable as it acts as a 'checker' and 'address book' that is able to tell us where the
worm has been and what it has mapped so far.
- `self.curX/Y` are coordinates representing the worm's current location on the grid.


Before any sort of mapping can actually be done we need to create an empty display area and do some
sanity checks on it by using the following methods.

```python
# in mygame/world/map.py

class Map(object):
    # [... continued]

    def create_grid(self):
        # This method simply creates an empty grid/display area
        # with the specified variables from __init__(self):
        board = []
        for row in range(self.max_width):
            board.append([])
            for column in range(self.max_length):
                board[row].append('   ')
        return board

    def check_grid(self):
        # this method simply checks the grid to make sure
        # that both max_l and max_w are odd numbers.
        return True if self.max_length % 2 != 0 or self.max_width % 2 != 0\
            else False
```

Before we can set our worm on its way, we need to know some of the computer science behind all this
called 'Graph Traversing'. In Pseudo code what we are trying to accomplish is this:

```python
# pseudo code

def draw_room_on_map(room, max_distance):
    self.draw(room)

    if max_distance == 0:
        return

    for exit in room.exits:
        if self.has_drawn(exit.destination):
            # skip drawing if we already visited the destination
            continue
        else:
            # first time here!
            self.draw_room_on_map(exit.destination, max_distance - 1)
```

The beauty of Python is that our actual code of doing this doesn't differ much if at all from this
Pseudo code example.

- `max_distance` is a variable indicating to our Worm how many rooms AWAY from your current location
will it map. Obviously the larger the number the more time it will take if your current location has
many many rooms around you.

The first hurdle here is what value to use for 'max_distance'. There is no reason for the worm to
travel further than what is actually displayed to you. For example, if your current location is
placed in the center of a display area of size `max_length = max_width = 9`, then the worm need only
go `4` spaces in either direction:

```
[.][.][.][.][@][.][.][.][.]
 4  3  2  1  0  1  2  3  4
```

The max_distance can be set dynamically based on the size of the display area. As your width/length
changes it becomes a simple algebraic linear relationship which is simply `max_distance =
(min(max_width, max_length) -1) / 2`.

## Building the Mapper

Now we can start to fill our Map object with some methods. We are still missing a few methods that
are very important:

* `self.draw(self, room)` - responsible for actually drawing room to grid.
* `self.has_drawn(self, room)` - checks to see if the room has been mapped and worm has already been
here.
* `self.median(self, number)` - a simple utility method that finds the median (middle point) from 0,
n
* `self.update_pos(self, room, exit_name)` - updates the worm's physical position by reassigning
self.curX/Y. .accordingly
* `self.start_loc_on_grid(self)` - the very first initial draw on the grid representing your
location in the middle of the grid
* 'self.show_map` - after everything is done convert the map into a readable string`
* `self.draw_room_on_map(self, room, max_distance)` - the main method that ties it all together.`


Now that we know which methods we need, let's refine our initial `__init__(self)` to pass some
conditional statements and set it up to start building the display.


```python
#mygame/world/map.py

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None

        if self.check_grid():
            # we have to store the grid into a variable
            self.grid = self.create_grid()
            # we use the algebraic relationship
            self.draw_room_on_map(caller.location,
                                  ((min(max_width, max_length) -1 ) / 2)

```

Here we check to see if the parameters for the grid are okay, then we create an empty canvas and map
our initial location as the first room!

As mentioned above, the code for the `self.draw_room_on_map()` is not much different than the Pseudo
code. The method is shown below:

```python
# in mygame/world/map.py, in the Map class

def draw_room_on_map(self, room, max_distance):
    self.draw(room)

    if max_distance == 0:
        return

    for exit in room.exits:
        if exit.name not in ("north", "east", "west", "south"):
            # we only map in the cardinal directions. Mapping up/down would be
            # an interesting learning project for someone who wanted to try it.
            continue
        if self.has_drawn(exit.destination):
            # we've been to the destination already, skip ahead.
            continue

        self.update_pos(room, exit.name.lower())
        self.draw_room_on_map(exit.destination, max_distance - 1)
```

The first thing the "worm" does is to draw your current location in `self.draw`. Lets define that...

```python
#in mygame/word/map.py, in the Map class

def draw(self, room):
    # draw initial ch location on map first!
    if room == self.caller.location:
        self.start_loc_on_grid()
        self.worm_has_mapped[room] = [self.curX, self.curY]
    else:
        # map all other rooms
        self.worm_has_mapped[room] = [self.curX, self.curY]
        # this will use the sector_type Attribute or None if not set.
        self.grid[self.curX][self.curY] = SYMBOLS[room.db.sector_type]
```

In `self.start_loc_on_grid()`:

```python
def median(self, num):
    lst = sorted(range(0, num))
    n = len(lst)
    m = n -1
    return (lst[n//2] + lst[m//2]) / 2.0

def start_loc_on_grid(self):
    x = self.median(self.max_width)
    y = self.median(self.max_length)
    # x and y are floats by default, can't index lists with float types
    x, y = int(x), int(y)

    self.grid[x][y] = SYMBOLS['you']
    self.curX, self.curY = x, y # updating worms current location
```

After the system has drawn the current map it checks to see if the `max_distance` is `0` (since this
is the inital start phase it is not). Now we handle the iteration once we have each individual exit
in the room. The first thing it does is check if the room the Worm is in has been mapped already..
lets define that...


```python
def has_drawn(self, room):
    return True if room in self.worm_has_mapped.keys() else False
```

If `has_drawn` returns `False` that means the worm has found a room that hasn't been mapped yet. It
will then 'move' there. The self.curX/Y sort of lags behind, so we have to make sure to track the
position of the worm; we do this in `self.update_pos()` below.

```python
def update_pos(self, room, exit_name):
    # this ensures the coordinates stays up to date
    # to where the worm is currently at.
    self.curX, self.curY = \
      self.worm_has_mapped[room][0], self.worm_has_mapped[room][1]

    # now we have to actually move the pointer
    # variables depending on which 'exit' it found
    if exit_name == 'east':
        self.curY += 1
    elif exit_name == 'west':
        self.curY -= 1
    elif exit_name == 'north':
        self.curX -= 1
    elif exit_name == 'south':
        self.curX += 1
```

Once the system updates the position of the worm it feeds the new room back into the original
`draw_room_on_map()` and starts the process all over again..

That is essentially the entire thing. The final method is to bring it all together and make a nice
presentational string out of it using the `self.show_map()` method.

```python
def show_map(self):
    map_string = ""
    for row in self.grid:
        map_string += " ".join(row)
        map_string += "\n"

    return map_string
```

## Using the Map

In order for the map to get triggered we store it on the Room typeclass. If we put it in
`return_appearance` we will get the map back every time we look at the room.

> `return_appearance` is a default Evennia hook available on all objects; it is called e.g. by the
`look` command to get the description of something (the room in this case).

```python
# in mygame/typeclasses/rooms.py

from evennia import DefaultRoom
from world.map import Map

class Room(DefaultRoom):
    
    def return_appearance(self, looker):
        # [...]
        string = f"{Map(looker).show_map()}\n"
        # Add all the normal stuff like room description,
        # contents, exits etc.
        string += "\n" + super().return_appearance(looker)
        return string
```

Obviously this method of generating maps doesn't take into account of any doors or exits that are
hidden.. etc.. but hopefully it serves as a good base to start with. Like previously mentioned, it
is very important to have a solid foundation on rooms before implementing this. You can try this on
vanilla evennia by using @tunnel and essentially you can just create a long straight/edgy non-
looping rooms that will show on your in-game map.

The above example will display the map above the room description. You could also use an
[EvTable](github:evennia.utils.evtable) to place description and map next to each other. Some other
things you can do is to have a [Command](./Commands) that displays with a larger radius, maybe with a
legend and other features.

Below is the whole `map.py` for your reference. You need to update your `Room` typeclass (see above)
to actually call it. Remember that to see different symbols for a location you also need to set the
`sector_type` Attribute on the room to one of the keys in the `SYMBOLS` dictionary. So in this
example, to make a room be mapped as `[.]` you would set the room's `sector_type` to
`"SECT_INSIDE"`. Try it out with `@set here/sector_type = "SECT_INSIDE"`. If you wanted all new
rooms to have a given sector symbol, you could change the default in the `SYMBOLS´ dictionary below,
or you could add the Attribute in the Room's `at_object_creation` method.

```python
#mygame/world/map.py

# These are keys set with the Attribute sector_type on the room.
# The keys None and "you" must always exist.
SYMBOLS = { None : ' . ',  # for rooms without a sector_type attr
            'you' : '[@]',
            'SECT_INSIDE': '[.]' }

class Map(object):

    def __init__(self, caller, max_width=9, max_length=9):
        self.caller = caller
        self.max_width = max_width
        self.max_length = max_length
        self.worm_has_mapped = {}
        self.curX = None
        self.curY = None

        if self.check_grid():
            # we actually have to store the grid into a variable
            self.grid = self.create_grid()
            self.draw_room_on_map(caller.location,
                                 ((min(max_width, max_length) -1 ) / 2))
    
    def update_pos(self, room, exit_name):
        # this ensures the pointer variables always
        # stays up to date to where the worm is currently at.
        self.curX, self.curY = \
           self.worm_has_mapped[room][0], self.worm_has_mapped[room][1]

        # now we have to actually move the pointer
        # variables depending on which 'exit' it found
        if exit_name == 'east':
            self.curY += 1
        elif exit_name == 'west':
            self.curY -= 1
        elif exit_name == 'north':
            self.curX -= 1
        elif exit_name == 'south':
            self.curX += 1

    def draw_room_on_map(self, room, max_distance):
        self.draw(room)

        if max_distance == 0:
            return
        
        for exit in room.exits:
            if exit.name not in ("north", "east", "west", "south"):
                # we only map in the cardinal directions. Mapping up/down would be
                # an interesting learning project for someone who wanted to try it.
                continue
            if self.has_drawn(exit.destination):
                # we've been to the destination already, skip ahead.
                continue

            self.update_pos(room, exit.name.lower())
            self.draw_room_on_map(exit.destination, max_distance - 1)
        
    def draw(self, room):
        # draw initial caller location on map first!
        if room == self.caller.location:
            self.start_loc_on_grid()
            self.worm_has_mapped[room] = [self.curX, self.curY]
        else:
            # map all other rooms
            self.worm_has_mapped[room] = [self.curX, self.curY]
            # this will use the sector_type Attribute or None if not set.
            self.grid[self.curX][self.curY] = SYMBOLS[room.db.sector_type]

    def median(self, num):
        lst = sorted(range(0, num))
        n = len(lst)
        m = n -1
        return (lst[n//2] + lst[m//2]) / 2.0
   
    def start_loc_on_grid(self):
        x = self.median(self.max_width)
        y = self.median(self.max_length)
        # x and y are floats by default, can't index lists with float types
        x, y = int(x), int(y)

        self.grid[x][y] = SYMBOLS['you']
        self.curX, self.curY = x, y # updating worms current location
     

    def has_drawn(self, room):
        return True if room in self.worm_has_mapped.keys() else False


    def create_grid(self):
        # This method simply creates an empty grid
        # with the specified variables from __init__(self):
        board = []
        for row in range(self.max_width):
            board.append([])
            for column in range(self.max_length):
                board[row].append('   ')
        return board

    def check_grid(self):
        # this method simply checks the grid to make sure
        # both max_l and max_w are odd numbers
        return True if self.max_length % 2 != 0 or \
                    self.max_width % 2 != 0 else False

    def show_map(self):
        map_string = ""
        for row in self.grid:
            map_string += " ".join(row)
            map_string += "\n"

        return map_string
```

## Final Comments

The Dynamic map could be expanded with further capabilities. For example, it could mark exits or
allow NE, SE etc directions as well. It could have colors for different terrain types. One could
also look into up/down directions and figure out how to display that in a good way.
