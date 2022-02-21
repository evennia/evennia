# Static In Game Map


## Introduction

This tutorial describes the creation of an in-game map display based on a pre-drawn map. It also
details how to use the [Batch code processor](../Components/Batch-Code-Processor.md) for advanced building. There is
also the [Dynamic in-game map tutorial](./Dynamic-In-Game-Map.md) that works in the opposite direction,
by generating a map from an existing grid of rooms.

Evennia does not require its rooms to be positioned in a "logical" way. Your exits could be named
anything. You could make an exit "west" that leads to a room described to be in the far north. You
could have rooms inside one another, exits leading back to the same room or describing spatial
geometries impossible in the real world.

That said, most games *do* organize their rooms in a logical fashion, if nothing else to retain the
sanity of their players. And when they do, the game becomes possible to map. This tutorial will give
an example of a simple but flexible in-game map system to further help player's to navigate. We will

To simplify development and error-checking we'll break down the work into bite-size chunks, each
building on what came before. For this we'll make extensive use of the [Batch code processor](Batch-
Code-Processor), so you may want to familiarize yourself with that.

1. **Planning the map** - Here we'll come up with a small example map to use for the rest of the
tutorial.
2. **Making a map object** - This will showcase how to make a static in-game "map" object a
Character could pick up and look at.
3. **Building the map areas** - Here we'll actually create the small example area according to the
map we designed before.
4. **Map code** - This will link the map to the location so our output looks something like this:

    ```
    crossroads(#3)
    ↑╚∞╝↑
    ≈↑│↑∩  The merger of two roads. To the north looms a mighty castle.
    O─O─O  To the south, the glow of a campfire can be seen. To the east lie
    ≈↑│↑∩  the vast mountains and to the west is heard the waves of the sea.
    ↑▲O▲↑
    
    Exits: north(#8), east(#9), south(#10), west(#11)
    ```

We will henceforth assume your game folder is name named `mygame` and that you haven't modified the
default commands. We will also not be using [Colors](../Concepts/Colors.md) for our map since they
don't show in the documentation wiki.

## Planning the Map

Let's begin with the fun part! Maps in MUDs come in many different [shapes and
sizes](http://journal.imaginary-realities.com/volume-05/issue-01/modern-interface-modern-
mud/index.html). Some appear as just boxes connected by lines. Others have complex graphics that are
external to the game itself.

Our map will be in-game text but that doesn't mean we're restricted to the normal alphabet! If
you've ever selected the [Wingdings font](https://en.wikipedia.org/wiki/Wingdings) in Microsoft Word
you will know there are a multitude of other characters around to use. When creating your game with
Evennia you have access to the [UTF-8 character encoding](https://en.wikipedia.org/wiki/UTF-8) which
put at your disposal [thousands of letters, number and geometric shapes](https://mcdlr.com/utf-8/#1).

For this exercise, we've copy-and-pasted from the pallet of special characters used over at 
[Dwarf Fortress](https://dwarffortresswiki.org/index.php/Character_table) to create what is hopefully
a pleasing and easy to understood landscape:

```
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩   Places the account can visit are indicated by "O".
≈≈↑║O║↑∩∩   Up the top is a castle visitable by the account.
≈≈↑╚∞╝↑∩∩   To the right is a cottage and to the left the beach.
≈≈≈↑│↑∩∩∩   And down the bottom is a camp site with tents.
≈≈O─O─O⌂∩   In the center is the starting location, a crossroads
≈≈≈↑│↑∩∩∩   which connect the four other areas.
≈≈↑▲O▲↑∩∩   
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
```
There are many considerations when making a game map depending on the play style and requirements
you intend to implement. Here we will display a 5x5 character map of the area surrounding the
account. This means making sure to account for 2 characters around every visitable location. Good
planning at this stage can solve many problems before they happen.

## Creating a Map Object

In this section we will try to create an actual "map" object that an account can pick up and look
at.

Evennia offers a range of [default commands](../Components/Default-Commands.md) for 
[creating objects and rooms in-game](Beginner-Tutorial/Part1/Building-Quickstart.md). While readily accessible, these commands are made to do very
specific, restricted things and will thus not offer as much flexibility to experiment (for an
advanced exception see [the FuncParser](../Components/FuncParser.md)). Additionally, entering long
descriptions and properties over and over in the game client can become tedious; especially when
testing and you may want to delete and recreate things over and over.

To overcome this, Evennia offers [batch processors](../Components/Batch-Processors.md) that work as input-files
created out-of-game. In this tutorial we'll be using the more powerful of the two available batch
processors, the [Batch Code Processor ](../Components/Batch-Code-Processor.md), called with the `@batchcode` command.
This is a very powerful tool. It allows you to craft Python files to act as blueprints of your
entire game world. These files have access to use Evennia's Python API directly. Batchcode allows
for easy editing and creation in whatever text editor you prefer, avoiding having to manually build
the world line-by-line inside the game.

> Important warning: `@batchcode`'s power is only rivaled by the `@py` command. Batchcode is so
powerful it should be reserved only for the [superuser](../Concepts/Building-Permissions.md). Think carefully
before you let others (such as `Developer`- level staff) run `@batchcode` on their own - make sure
you are okay with them running *arbitrary Python code* on your server.

While a simple example, the map object it serves as good way to try out `@batchcode`. Go to
`mygame/world` and create a new file there named `batchcode_map.py`:

```Python
# mygame/world/batchcode_map.py

from evennia import create_object
from evennia import DefaultObject

# We use the create_object function to call into existence a 
# DefaultObject named "Map" wherever you are standing.

map = create_object(DefaultObject, key="Map", location=caller.location)

# We then access its description directly to make it our map.

map.db.desc = """
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩
≈≈↑║O║↑∩∩
≈≈↑╚∞╝↑∩∩
≈≈≈↑│↑∩∩∩
≈≈O─O─O⌂∩
≈≈≈↑│↑∩∩∩
≈≈↑▲O▲↑∩∩
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
"""

# This message lets us know our map was created successfully.
caller.msg("A map appears out of thin air and falls to the ground.")
```

Log into your game project as the superuser and run the command 

```
@batchcode batchcode_map
```

This will load your `batchcode_map.py` file and execute the code (Evennia will look in your `world/`
folder automatically so you don't need to specify it).

A new map object should have appeared on the ground. You can view the map by using `look map`. Let's
take it with the `get map` command. We'll need it in case we get lost!

## Building the map areas

We've just used batchcode to create an object useful for our adventures. But the locations on that
map does not actually exist yet - we're all mapped up with nowhere to go! Let's use batchcode to
build a game area based on our map. We have five areas outlined: a castle, a cottage, a campsite, a
coastal beach and the crossroads which connects them. Create a new batchcode file for this in
`mygame/world`, named `batchcode_world.py`.

```Python
# mygame/world/batchcode_world.py

from evennia import create_object, search_object
from typeclasses import rooms, exits

# We begin by creating our rooms so we can detail them later.

centre = create_object(rooms.Room, key="crossroads")
north = create_object(rooms.Room, key="castle")
east = create_object(rooms.Room, key="cottage")
south = create_object(rooms.Room, key="camp")
west = create_object(rooms.Room, key="coast")

# This is where we set up the cross roads.
# The rooms description is what we see with the 'look' command.

centre.db.desc = """
The merger of two roads. A single lamp post dimly illuminates the lonely crossroads.
To the north looms a mighty castle. To the south the glow of a campfire can be seen.
To the east lie a wall of mountains and to the west the dull roar of the open sea.
"""

# Here we are creating exits from the centre "crossroads" location to 
# destinations to the north, east, south, and west. We will be able 
# to use the exit by typing it's key e.g. "north" or an alias e.g. "n".

centre_north = create_object(exits.Exit, key="north", 
                            aliases=["n"], location=centre, destination=north)
centre_east = create_object(exits.Exit, key="east", 
                            aliases=["e"], location=centre, destination=east)
centre_south = create_object(exits.Exit, key="south", 
                            aliases=["s"], location=centre, destination=south)
centre_west = create_object(exits.Exit, key="west", 
                            aliases=["w"], location=centre, destination=west)

# Now we repeat this for the other rooms we'll be implementing.
# This is where we set up the northern castle.

north.db.desc = "An impressive castle surrounds you. " \
                "There might be a princess in one of these towers."
north_south = create_object(exits.Exit, key="south", 
                            aliases=["s"], location=north, destination=centre)

# This is where we set up the eastern cottage.

east.db.desc = "A cosy cottage nestled among mountains " \
               "stretching east as far as the eye can see."
east_west = create_object(exits.Exit, key="west", 
                            aliases=["w"], location=east, destination=centre)

# This is where we set up the southern camp.

south.db.desc = "Surrounding a clearing are a number of " \
                "tribal tents and at their centre a roaring fire."
south_north = create_object(exits.Exit, key="north", 
                            aliases=["n"], location=south, destination=centre)

# This is where we set up the western coast.

west.db.desc = "The dark forest halts to a sandy beach. " \
               "The sound of crashing waves calms the soul."
west_east = create_object(exits.Exit, key="east", 
                            aliases=["e"], location=west, destination=centre)

# Lastly, lets make an entrance to our world from the default Limbo room.

limbo = search_object('Limbo')[0]
limbo_exit = create_object(exits.Exit, key="enter world", 
                            aliases=["enter"], location=limbo, destination=centre)

```

Apply this new batch code with `@batchcode batchcode_world`. If there are no errors in the code we
now have a nice mini-world to explore. Remember that if you get lost you can look at the map we
created!

## In-game minimap

Now we have a landscape and matching map, but what we really want is a mini-map that displays
whenever we move to a room or use the `look` command.

We *could* manually enter a part of the map into the description of every room like we did our map
object description. But some MUDs have tens of thousands of rooms! Besides, if we ever changed our
map we would have to potentially alter a lot of those room descriptions manually to match the
change. So instead we will make one central module to hold our map. Rooms will reference this
central location on creation and the map changes will thus come into effect when next running our
batchcode.

To make our mini-map we need to be able to cut our full map into parts. To do this we need to put it
in a format which allows us to do that easily. Luckily, python allows us to treat strings as lists
of characters allowing us to pick out the characters we need.

`mygame/world/map_module.py`
```Python
# We place our map into a sting here.
world_map = """\
≈≈↑↑↑↑↑∩∩
≈≈↑╔═╗↑∩∩
≈≈↑║O║↑∩∩
≈≈↑╚∞╝↑∩∩
≈≈≈↑│↑∩∩∩
≈≈O─O─O⌂∩
≈≈≈↑│↑∩∩∩
≈≈↑▲O▲↑∩∩
≈≈↑↑▲↑↑∩∩
≈≈↑↑↑↑↑∩∩
"""

# This turns our map string into a list of rows. Because python 
# allows us to treat strings as a list of characters, we can access 
# those characters with world_map[5][5] where world_map[row][column].
world_map = world_map.split('\n')

def return_map():
    """
    This function returns the whole map
    """
    map = ""
    
    #For each row in our map, add it to map
    for valuey in world_map:
        map += valuey
        map += "\n"
    
    return map

def return_minimap(x, y, radius = 2):
    """
    This function returns only part of the map.
    Returning all chars in a 2 char radius from (x,y)
    """
    map = ""
    
    #For each row we need, add the characters we need.
    for valuey in world_map[y-radius:y+radius+1]:         for valuex in valuey[x-radius:x+radius+1]:
            map += valuex
        map += "\n"
    
    return map
```

With our map_module set up, let's replace our hardcoded map in `mygame/world/batchcode_map.py` with
a reference to our map module. Make sure to import our map_module!

```python
# mygame/world/batchcode_map.py

from evennia import create_object
from evennia import DefaultObject
from world import map_module

map = create_object(DefaultObject, key="Map", location=caller.location)

map.db.desc = map_module.return_map()

caller.msg("A map appears out of thin air and falls to the ground.")
```

Log into Evennia as the superuser and run this batchcode. If everything worked our new map should
look exactly the same as the old map - you can use `@delete` to delete the old one (use a number to
pick which to delete).

Now, lets turn our attention towards our game's rooms. Let's use the `return_minimap` method we
created above in order to include a minimap in our room descriptions. This is a little more
complicated.

By itself we would have to settle for either the map being *above* the description with
`room.db.desc = map_string + description_string`, or the map going *below* by reversing their order.
Both options are rather unsatisfactory - we would like to have the map next to the text! For this
solution we'll explore the utilities that ship with Evennia. Tucked away in `evennia\evennia\utils`
is a little module called [EvTable](github:evennia.utils.evtable) . This is an advanced ASCII table
creator for you to utilize in your game. We'll use it by creating a basic table with 1 row and two
columns (one for our map and one for our text) whilst also hiding the borders. Open the batchfile
again

```python
# mygame\world\batchcode_world.py

# Add to imports
from evennia.utils import evtable
from world import map_module

# [...]

# Replace the descriptions with the below code.

# The cross roads.
# We pass what we want in our table and EvTable does the rest.
# Passing two arguments will create two columns but we could add more.
# We also specify no border.
centre.db.desc = evtable.EvTable(map_module.return_minimap(4,5), 
                 "The merger of two roads. A single lamp post dimly " \
                 "illuminates the lonely crossroads. To the north " \
                 "looms a mighty castle. To the south the glow of " \
                 "a campfire can be seen. To the east lie a wall of " \
                 "mountains and to the west the dull roar of the open sea.", 
                 border=None)
# EvTable allows formatting individual columns and cells. We use that here
# to set a maximum width for our description, but letting the map fill
# whatever space it needs. 
centre.db.desc.reformat_column(1, width=70)

# [...]

# The northern castle.
north.db.desc = evtable.EvTable(map_module.return_minimap(4,2), 
                "An impressive castle surrounds you. There might be " \
                "a princess in one of these towers.", 
                border=None)
north.db.desc.reformat_column(1, width=70)   

# [...]

# The eastern cottage.
east.db.desc = evtable.EvTable(map_module.return_minimap(6,5), 
               "A cosy cottage nestled among mountains stretching " \
               "east as far as the eye can see.", 
               border=None)
east.db.desc.reformat_column(1, width=70)

# [...]

# The southern camp.
south.db.desc = evtable.EvTable(map_module.return_minimap(4,7), 
                "Surrounding a clearing are a number of tribal tents " \
                "and at their centre a roaring fire.", 
                border=None)
south.db.desc.reformat_column(1, width=70)

# [...]

# The western coast.
west.db.desc = evtable.EvTable(map_module.return_minimap(2,5), 
               "The dark forest halts to a sandy beach. The sound of " \
               "crashing waves calms the soul.", 
               border=None)
west.db.desc.reformat_column(1, width=70)
```

Before we run our new batchcode, if you are anything like me you would have something like 100 maps
lying around and 3-4 different versions of our rooms extending from limbo. Let's wipe it all and
start with a clean slate. In Command Prompt you can run `evennia flush` to clear the database and
start anew. It won't reset dbref values however, so if you are at #100 it will start from there.
Alternatively you can navigate to `mygame/server` and delete the `evennia.db3` file. Now in  Command
Prompt use `evennia migrate` to have a completely freshly made database.

Log in to evennia and run `@batchcode batchcode_world` and you'll have a little world to explore.

## Conclusions

You should now have a mapped little world and a basic understanding of batchcode, EvTable and how
easily new game defining features can be added to Evennia.

You can easily build from this tutorial by expanding the map and creating more rooms to explore. Why
not add more features to your game by trying other tutorials: [Add weather to your world](Weather-
Tutorial), [fill your world with NPC's](./Tutorial-Aggressive-NPCs.md) or 
[implement a combat system](Beginner-Tutorial/Part3/Turn-based-Combat-System.md).
