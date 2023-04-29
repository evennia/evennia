# In-game Rooms 

A _room_ describes a specific location in the game world. Being an abstract concept, it can represent any area of game content that is convenient to group together.  In this lesson we will also create a small in-game automap.

In EvAdventure, we will have two main types of rooms: 
- Normal, above-ground rooms. Based on a fixed map, these will be created once and then don't change. We'll cover them in this lesson. 
- Dungeon rooms - these will be examples of _procedurally generated_ rooms, created on the fly as the players explore the underworld. Being subclasses of the normal room, we'll get to them in the [Dungeon generation lesson](Beginner-Tutorial-Dungeon).

## The base room

Our Evadventure-rooms need some extra functionality 
- We need to know if we can do combat in them, if PvP is ok and if you can die in the room. 
- We want to show a little _map_ as part of the room description. For this to work we need to remember to always use cardinal directions to connect rooms (north, east etc). 

> Create a new module `evadventure/rooms.py`.

```python
# in evadventure/rooms.py

from evennia import AttributeProperty, DefaultRoom

class EvAdventureRoom(DefaultRoom):
	"""
    Simple room supporting some EvAdventure-specifics.
 
    """
 
    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

``` 

Our EvadventureRoom is very simple. We create three Attributes that defines if combat is allowed in the room, and if so if pvp is allowed and finally if death is allowed. Later on we must make sure our combat systems honors these values. This allows us to create 'safe' training rooms and the like. 

That's really all there we _really_ need for the basic room. It'd make for a very short lesson though, so let's add a map too.


## PvP room 

Here's a room that allows non-lethal PvP (sparring):

```python

# in evadventure/rooms.py

class EvAdventurePvPRoom(EvAdventureRoom):
    """
    Room where PvP can happen, but noone gets killed.
    
    """
    
    allow_combat = AttributeProperty(True, autocreate=False)
    allow_pvp = AttributeProperty(True, autocreate=False)
    
    def get_display_footer(self, looker, **kwargs):
        """
        Customize footer of description.
        """
        return "|yNon-lethal PvP combat is allowed here!|n"
```

The return of `get_display_footer` will show after the [main room description](Objects#changing-an-objects-appearance), showing that the room is a sparring room. This means that when a player drops to 0 HP, they will lose the combat, but don't stand any risk of dying (weapons wear out normally during sparring though).

## Adding a room map

We want a dynamic map that visualizes the exits you can use at any moment. Here's how our room will display: 

```{shell}
  o o o
   \|/
  o-@-o
    | 
    o
The crossroads 
A place where many roads meet. 
Exits: north, norteast, south, west, and nortwest
```

> Documentation does not show ansi colors.

Let's expand the base `EvAdventureRoom` with the map.

```python
# in evadventyre/rooms.py

from copy import deepcopy
from evennia import DefaultCharacter
from evennia.utils.utils import inherits_from

CHAR_SYMBOL = "|w@|n"
CHAR_ALT_SYMBOL = "|w>|n"
ROOM_SYMBOL = "|bo|n"
LINK_COLOR = "|B"

_MAP_GRID = [
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", "@", " ", " "],
    [" ", " ", " ", " ", " "],
    [" ", " ", " ", " ", " "],
]
_EXIT_GRID_SHIFT = {
    "north": (0, 1, "||"),
    "east": (1, 0, "-"),
    "south": (0, -1, "||"),
    "west": (-1, 0, "-"),
    "northeast": (1, 1, "/"),
    "southeast": (1, -1, "\\"),
    "southwest": (-1, -1, "/"),
    "northwest": (-1, 1, "\\"),
}

class EvAdventureRoom(DefaultRoom): 

    # ... 

    def format_appearance(self, appearance, looker, **kwargs):
        """Don't left-strip the appearance string"""
        return appearance.rstrip()
 
    def get_display_header(self, looker, **kwargs):
        """
        Display the current location as a mini-map.
 
        """
        # make sure to not show make a map for users of screenreaders.
        # for optimization we also don't show it to npcs/mobs
        if not inherits_from(looker, DefaultCharacter) or (
            looker.account and looker.account.uses_screenreader()
        ):
            return ""
 
        # build a map
        map_grid = deepcopy(_MAP_GRID)
        dx0, dy0 = 2, 2
        map_grid[dy0][dx0] = CHAR_SYMBOL
        for exi in self.exits:
            dx, dy, symbol = _EXIT_GRID_SHIFT.get(exi.key, (None, None, None))
            if symbol is None:
                # we have a non-cardinal direction to go to - indicate this
                map_grid[dy0][dx0] = CHAR_ALT_SYMBOL
                continue
            map_grid[dy0 + dy][dx0 + dx] = f"{LINK_COLOR}{symbol}|n"
            if exi.destination != self:
                map_grid[dy0 + dy + dy][dx0 + dx + dx] = ROOM_SYMBOL
 
        # Note that on the grid, dy is really going *downwards* (origo is
        # in the top left), so we need to reverse the order at the end to mirror it
        # vertically and have it come out right.
        return "  " + "\n  ".join("".join(line) for line in reversed(map_grid))
```

The string returned from `get_display_header` will end up at the top of the [room description](Objects#changing-an-objects-description), a good place to have the map appear! 

The map itself consists of the 2D matrix `_MAP_GRID`. This is a 2D area described by a list of Python lists. To find a given place in the list, you first first need to find which of the nested lists to use, and then which element to use in that list. Indices start from 0 in Python. So to draw the `o` symbol for the southermost room, you'd need to do so at `_MAP_GRID[4][2]`. 

The `_EXIT_GRID_SHIFT` indicates the direction to go for each cardinal exit, along with the map symbol to draw at that point. So `"east": (1, 0, "-")` means the east exit will be drawn one step in the positive x direction (to the right), using the "-" symbol. For symbols like `|` and "\\" we need to escape with a double-symbol since these would otherwise be interpreted as part of other formatting. 

We start by making a `deepcopy` of the `_MAP_GRID`. This is so that we don't modify the original but always have an empty template to work from. 

We use `@` to indicate the location of the player (at coordinate `(2, 2)`). We then take the actual exits from the room use their names to figure out what symbols to draw out from the center. Once we have placed all the exit- and room-symbols in the grid, we merge it all together into a single string on the last line: 

```python
return "  " + "\n  ".join("".join(line) for line in reversed(map_grid))
```

At the end we use Python's standard [join](https://www.w3schools.com/python/ref_string_join.asp) to convert the grid into a single string. In doing so we must flip the grid upside down (reverse the outermost list). Why is this? If you think about how a MUD game displays its data - by printing at the bottom and then scrolling upwards - you'll realize that Evennia has to send out the top of your map _first_ and the bottom of it _last_ for it to show correctly to the user. 

We want to be able to get on/off the grid if so needed. So if a room has a non-cardinal exit in it (like 'back' or up/down), we'll indicate this by showing the `>` symbol instead of the `@` in your current room.

## Testing 

> Create a new module `evadventure/tests/test_rooms.py`.

```{sidebar} 
You can find a ready testing module [here in the tutorial folder](evennia.contrib.tutorials.evadventure.tests.test_rooms).
```
The main thing to test with our new rooms is the map. Here's the basic principle for how to do this testing:

```python
# in evadventure/tests/test_rooms.py

from evennia import DefaultExit, create_object
from evennia.utils.test_resources import EvenniaTestCase
from ..characters import EvAdventureCharacter 
from ..rooms import EvAdventureRoom

class EvAdventureRoomTest(EvenniaTestCase): 

    def test_map(self): 
        center_room = create_object(EvAdventureRoom, key="room_center")
        
        n_room = create_object(EvAdventureRoom, key="room_n)
        create_object(DefaultExit, 
                      key="north", location=center_room, destination=n_room)
        ne_room = create_object(EvAdventureRoom, key="room=ne")
        create_object(DefaultExit,
			          key="northeast", location=center_room, destination=ne_room)
        # ... etc for all cardinal directions 
        
        char = create_object(EvAdventureCharacter, 
					         key="TestChar", location=center_room)					        
		desc = center_room.return_appearance(char)

        # compare the desc we got with the expected description here

```

## Conclusion  

In this lesson we manipulated strings and made a map. Changing the description of an object is a big part of changing the 'graphics' of a text-based game, so checking out the [documentation on this](Objects#changing-an-objects-description) is good extra reading.
