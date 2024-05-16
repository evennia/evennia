# Procedurally generated Dungeon

The rooms that we discussed in the [lesson about Rooms](./Beginner-Tutorial-Rooms.md) are all _manually_ generated. That is, a human builder would have to sit down and spawn each room manually, either in-game or using code. 

In this lesson we'll explore _procedural_ generation of the rooms making up our game's underground dungeon. Procedural means that its rooms are spawned automatically and semi-randomly as players explore, creating a different dungeon layout every time.

## Design Concept 

This describes how the procedural generation should work at a high level. It's important to understand this before we start writing code.

We will assume our dungeon exists on a 2D plane (x,y, no z directions). We will only use N,E,S,W compass directions, but there is no reason this design couldn't work with SE, NW etc, except that this could make it harder for the player to visualize. More possible directions also make it more likely to produce collisions and one-way exits (see below).

This design is pretty simple, but just by playing with some of its settings, it can produce very different-feeling dungeon systems.

### The starting room

The idea is that all players will descend down a well to get to the start of the dungeon. The bottom of the well is a statically created room that won't change.

```{code-block}
:caption: Starting room
            
                 Branch N                
                    ▲                    
                    │                    
           ┌────────┼────────┐           
           │        │n       │           
           │        ▼        │           
           │                 │           
           │                e│           
Branch W ◄─┼─►     up▲     ◄─┼─► Branch E1
           │w                │           
           │                 │           
           │        ▲        │           
           │        │s       │           
           └────────┼────────┘           
                    │                    
                    ▼                    
                 Branch S               
```

The magic happens when you choose one of the exits from this room (except the one leading you back to the surface). Let's assume a PC descends down to the start room and moves `east`:

- The first person to go east will spawn a new "Dungeon branch" (Branch E1 in the diagram). This is a separate "instance" of dungeon compared to what would spawn if moving through any of the other exits. Rooms spawned within one dungeon branch will never overlap with that of another dungeon branch. 
- A timer starts. While this timer is active, everyone going `east` will end up in Branch E1. This allows for players to team up and collaborate to take on a branch. 
- After the timer runs out, everyone going `east` will instead end up in a _new_ Branch E2. This is a new branch that has no overlap with Branch E1. 
- PCs in Branches E1 and E2 can always retreat `west` back to the starting room, but after the timer runs out this is now a one-way exit - they won't be able to return to their old branches if they do.

### Generating new branch rooms

Each dungeon branch is itself tracking the layout of rooms belonging to this branch on an (X, Y) coordinate grid.

```{code-block}
:caption: Creating the eastern branch and its first room
                   ?         
                   ▲         
                   │         
┌─────────┐   ┌────┼────┐    
│         │   │A   │    │    
│         │   │   PC    │    
│  start◄─┼───┼─► is  ──┼──►?
│         │   │   here  │    
│         │   │    │    │    
└─────────┘   └────┼────┘    
                   │         
                   ▼         
```

The start room is always at coordinate `(0, 0)`.  

A dungeon room is only created when actually moving to it. In the above example, the PC moved `east` from the start room, which initiated a new dungeon branch. The branch also created a new room (room `A`) at coordinate `(1,0)`. In this case it (randomly) seeded this room with three exits `north`, `east` and `south`.
Since this branch was just created, the exit back to the start room is still two-way.

This is the procedure the dungeon branch follows when spawning a new room:

- It always creates an exit back to the room we came from.
- It checks how many unexplored exits we have in the dungeon right now. That is, how many exits we haven't yet traversed. This number must never be zero unless we want a dungeon that can be 'finished'. The maximum number of unexplored exits open at any given time is a setting we can experiment with. A small max number leads to linear dungeon, a bigger number makes the dungeon sprawling and maze-like.
- Outgoing exits (exits not leading back to where we came) are generated with the following rules:
    - Randomly create between 0 and the number of outgoing exits allowed by the room and the branches' current budget of allowed open unexplored exits.
    - Create 0 outgoing exits (a dead-end) only if this would leave at least one unexplored exit open somewhere in the dungeon branch.
    - Do _not_ create an exit that would connect the exit to a previously generated room (so we prefer exits leading to new places rather than back to old ones)
    - If a previously created exit end up pointing to a newly created room, this _is_ allowed, and is the only time a one-way exit will happen (example below). All other exits are always two-way exits. This also presents the only small chance of closing out a dungeon with no way to proceed but to return to the start.
    - Never create an exit back to the start room (e.g. from another direction). The only way to get back to the start room is by back tracking.

In the following examples, we assume the maximum number of unexplored exits allowed open at any time is set to 4. 

```{code-block}
:caption: After four steps in the eastern dungeon branch
                    ?                                 
                   ▲                                 
                   │                                 
┌─────────┐   ┌────┼────┐                            
│         │   │A   │    │                            
│         │   │         │                            
│  start◄─┼───┼─      ──┼─►?                         
│         │   │    ▲    │                            
│         │   │    │    │                            
└─────────┘   └────┼────┘                            
                   │                                 
              ┌────┼────┐   ┌─────────┐   ┌─────────┐
              │B   │    │   │C        │   │D        │
              │    ▼    │   │         │   │   PC    │
          ?◄──┼─      ◄─┼───┼─►     ◄─┼───┼─► is    │
              │         │   │         │   │   here  │
              │         │   │         │   │         │
              └─────────┘   └─────────┘   └─────────┘
```

1. PC moves `east` from the start room. A new room `A` (coordinate `(1, 0)` ) is created. After a while the exit back to the start room becomes a one-way exit. The branch can have at most 4 unexplored exits, and the dungeon branch randomly adds three additional exits out of room `A`. 
2. PC moves `south`. A new room `B` (`(1,-1)`) is created, with two random exits, which is as many as the orchetrator is allowed to create at this time (4 are now open). It also always creates an exit back to the previous room (`A`)
3. PC moves `east` (coordinate (`(2, -1)`). A new room `C` is created. The  dungaon branch already has 3 exits unexplored, so it can only add one exit our of this room. 
4. PC moves `east` (`(3, -1)`). While the dungeon branch still has a budget of one exit, it knows there are other unexplored exits elsewhere, and is allowed to randomly create 0 exits. This is a dead end. The PC must go back and explore another direction.

Let's change the dungeon a bit to do another example: 

```{code-block}
:caption: Looping around
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐              
│         │   │A   │    │              
│         │   │         │              
│  start◄─┼───┼─      ──┼──►?           
│         │   │    ▲    │              
│         │   │    │    │        ?     
└─────────┘   └────┼────┘        ▲     
                   │             │     
              ┌────┼────┐   ┌────┼────┐
              │B   │    │   │C   │    │
              │    ▼    │   │   PC    │
          ?◄──┼─      ◄─┼───┼─► is    │
              │         │   │   here  │
              │         │   │         │
              └─────────┘   └─────────┘

```

In this example the PC moved `east`, `south`, `east` but the exit out of room `C` is leading north, into a coordinate where `A` already has an exit pointing to. Going `north` here leads to the following: 

```{code-block}
:caption: Creation of a one-way exit
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐   ┌─────────┐
│         │   │A   │    │   │D   PC   │
│         │   │         │   │    is   │
│  start◄─┼───┼─      ──┼───┼─►  here │
│         │   │    ▲    │   │    ▲    │
│         │   │    │    │   │    │    │
└─────────┘   └────┼────┘   └────┼────┘
                   │             │     
              ┌────┼────┐   ┌────┼────┐
              │B   │    │   │C   │    │
              │    ▼    │   │    ▼    │
          ?◄──┼─      ◄─┼───┼─►       │
              │         │   │         │
              │         │   │         │
              └─────────┘   └─────────┘
```

As the PC moves `north`, the room `D` is created at `(2,0)`. 

While `C` to `D` get a two-way exit as normal, this creates a one-way exit from `A` to `D`. 

Whichever exit leads to actually creating the room gets the two-way exit, so if the PC had walked back from `C` and created room `D` by going `east` from room `A`, then the one-way exit would be from room `C` instead.

> If the maximum allowed number of open unexplored exits is small, this case is the only situation where it's possible to 'finish' the dungeon (having no more unexplored exits to follow). We accept this as a case where the PCs just have to turn back and try another dungeon branch.

```{code-block}
:caption: Never link back to start room
                   ?                   
                   ▲                   
                   │                   
┌─────────┐   ┌────┼────┐   ┌─────────┐
│         │   │A   │    │   │D        │
│         │   │         │   │         │
│  start◄─┼───┼─      ──┼───┼─►       │
│         │   │    ▲    │   │    ▲    │
│         │   │    │    │   │    │    │
└─────────┘   └────┼────┘   └────┼────┘
                   │             │     
┌─────────┐   ┌────┼────┐   ┌────┼────┐
│E        │   │B   │    │   │C   │    │
│  PC     │   │    ▼    │   │    ▼    │
│  is   ◄─┼───┼─►     ◄─┼───┼─►       │
│  here   │   │         │   │         │
│         │   │         │   │         │
└─────────┘   └─────────┘   └─────────┘
```

Here the PC moved `west` from room `B` creating room `E` at `(0, -1)`. 

The dungeon branch never creates a link back to the start room, but it _could_ have created up to two new exits `west` and/or `south`. Since there's still an unexplored exit `north` from room `A`, the  branch is also allowed to randomly assign 0 exits, which is what it did here. 

The PC needs to backtrack and go `north` from `A` to continue exploring this dungeon branch.

### Making the dungeon dangerous

A dungeon would not be interesting without peril! There needs to be monsters to slay, puzzles to solve and treasure to be had.

When PCs first enters a room, that room is marked as `not clear`. While a room is not cleared, the PCs _cannot use any of the unexplored exits out of that room_.  They _can_ still retreat back the way they came unless they become locked in combat, in which case they have to flee from that first. 

Once PCs have overcome the challenge of the room (and probably earned some reward), will it change to `clear` .  A room can auto-clear if it is spawned empty or has no challenge meant to block the PCs (like a written hint for a puzzle elsewhere).

Note that clear/non-clear only relates to the challenge associated with that room. Roaming monsters (see the [AI tutorial](./Beginner-Tutorial-AI.md)) can lead to combat taking place in previously 'cleared' rooms.

### Difficulty scaling

```{sidebar} Risk and reward
The concept of dungeon depth/difficulty works well together with limited resources. If healing is limited to what can be carried, this leads to players having to decide if they want to risk push deeper or take their current spoils and retreat back to the surface to recover.
```

The "difficulty" of the dungeon is measured by the "depth" PCs have delved to. This is given as the _radial distance_ from the start room, rounded down, found by the good old [Pythagorean theorem](https://en.wikipedia.org/wiki/Pythagorean_theorem):

    depth = int(math.sqrt(x**2 + y**2))

So if you are in room `(1, 1)` you are at difficulty 1. Conversely at room coordinate `(4,-5)`  the difficulty is 6. Increasing depth should lead to tougher challenges but greater rewards.

## Start Implementation

Let's implement the design now!

```{sidebar}
You can also find code examples of the dungeon generator at `evennia/contrib/tutorials`, in [evadventure/dungeon.py](evennia.contrib.tutorials.evadventure.dungeon).
```
> Create a new module `evadventure/dungeon.py`.

## Basic Dungeon rooms

This is the fundamental element of the design, so let's start here.

Back in the [lesson about rooms](./Beginner-Tutorial-Rooms.md) we created a basic `EvAdventureRoom` typeclass. 
We will expand on this for dungeon rooms.

```{code-block} python
:linenos: 
:emphasize-lines: 13-14,29,32,36, 38
# in evadventure/dungeon.py 

from evennia import AttributeProperty
from .rooms import EvAdventureRoom 


class EvAdventureDungeonRoom(EvAdventureRoom):
    """
    Dangerous dungeon room.

    """

    allow_combat = AttributeProperty(True, autocreate=False)
    allow_death = AttributeProperty(True, autocreate=False)

    # dungeon generation attributes; set when room is created
    dungeon_branch = AttributeProperty(None, autocreate=False)
    xy_coords = AttributeProperty(None, autocreate=False)

    def at_object_creation(self):
        """
        Set the `not_clear` tag on the room. This is removed when the room is
        'cleared', whatever that means for each room.

        We put this here rather than in the room-creation code so we can override
        easier (for example we may want an empty room which auto-clears).

        """
        self.tags.add("not_clear", category="dungeon_room")
    
    def clear_room(self):
        self.tags.remove("not_clear", category="dungeon_room")
    
    @property
    def is_room_clear(self):
        return not bool(self.tags.get("not_clear", category="dungeon_room"))

    def get_display_footer(self, looker, **kwargs):
        """
        Show if the room is 'cleared' or not as part of its description.

        """
        if self.is_room_clear:
            return ""
        else:
            return "|rThe path forwards is blocked!|n"
```

```{sidebar} Storing the room typeclass
For this tutorial, we're keeping all dungeon-related code in one module. But one _could_ also argue that they belong in `evadventure/rooms.py` together with the other rooms. This is only a matter of how you want to organize things. Feel free to organize however you prefer for your own game.
```

- **Lines 14-15**: Dungeon rooms are dangerous, so unlike base EvAdventure rooms, we allow combat and death to happen in them.
- **Line 17**: We store a reference to the dungeon branch so that we can access it during room creation if we want. This could be relevant if we want to know things about the dungeon branch as part of creating rooms.
- **Line 18**: The xy coords will be simply stored as a tuple `(x,y)` on the room. 

All other functionality is built to manage the "clear" state of the room. 

- **Line 29**: When we create the room Evennia will always call its `at_object_creation` hook. We make sure to add a add a [Tag](../../../Components/Tags.md) `not_clear` to it (category "dungeon_room" to avoid collisions with other systems).
- **Line 32**: We will use the `.clear_room()` method to remove this Tag once the room's challenge is overcome. 
- **Line 36** `.is_room_clear` is a convenient property for checking the tag. This hides the Tag so we don't need to worry about we track the clear-room state.
- **Line 38** The `get_display_footer` is a standard Evennia hook for customizing the room's footer display. 

## Dungeon exits 

The dungeon exits are special in that we want the very act of traversing them to create the room on the other side. 

```python
# in evadventure/dungeon.py 

# ...

from evennia import DefaultExit

# ... 

class EvAdventureDungeonExit(DefaultExit):
    """
    Dungeon exit. This will not create the target room until it's traversed.

    """

    def at_object_creation(self):
        """
        We want to block progressing forward unless the room is clear.

        """
        self.locks.add("traverse:not objloctag(not_clear, dungeon_room)")

    def at_traverse(self, traversing_object, target_location, **kwargs):
        pass  # to be implemented! 

    def at_failed_traverse(self, traversing_object, **kwargs):
        """
        Called when failing to traverse.

        """
        traversing_object.msg("You can't get through this way yet!")

```

For now, we have not actually created the code for creating a new room in the branch, so we leave the `at_traverse` method un-implemented for now. This hook is what is called by Evennia when traversing the exit. 

In the `at_object_creation` method we make sure to add a [Lock](../../../Components/Locks.md) of type "traverse", which will limit who can pass through this exit. We lock it with the [objlocktag](evennia.locks.lockfuncs.objloctag) Lock function. This checks if the accessed object (this exit)'s location (the dungeon room) has a tag "not_clear" with category "dungeon_room" on it. If it does, then the traversal _fails_. In other words, while the room is not cleared, this type of exit will not let anyone through. 

The `at_failed_traverse` hook lets us customize the error message if a PC tries to use the exit before the room is cleared. 

## Dungeon Branch and the xy grid

The dungeon branch is responsible for the structure of one instance of the dungeon.

### Grid coordinates and exit mappings

Before we start, we need to establish some constants about our grid - the xy plane we will be placing our rooms on. 

```python
# in evadventure/dungeon.py 

# ... 

# cardinal directions
_AVAILABLE_DIRECTIONS = [
    "north",
    "east",
    "south",
    "west",
]

_EXIT_ALIASES = {
    "north": ("n",),
    "east": ("e",),
    "south": ("s",),
    "west": ("w",),
}
# finding the reverse cardinal direction
_EXIT_REVERSE_MAPPING = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
}

# how xy coordinate shifts by going in direction
_EXIT_GRID_SHIFT = {
    "north": (0, 1),
    "east": (1, 0),
    "south": (0, -1),
    "west": (-1, 0),
}
```

In this tutorial we only allow NESW movement. You could easily add the NE, SE, SW, NW directions too if you wanted to. We make mappings for exit aliases (there is only one here, but there could be multiple per direction too). We also figure out the "reverse" directions so we'll easily be able to create a 'back exit' later. 

The `_EXIT_GRID_SHIFT` mapping indicates how the (x,y) coordinate shifts if you are moving in the specified direction. So if you stand in `(4,2)` and move `south`, you'll end up in `(4,1)`. 

#### Base structure of the Dungeon branch script

We will base this component off an Evennia [Script](../../../Components/Scripts.md) - these can be thought of game entities without a physical presence in the world. Scripts also have time-keeping properties.

```{code-block} 
:linenos: 
:emphasize-lines: 
# in evadventure/dungeon.py 

from evennia.utils import create
from evennia import DefaultScript

# ... 

class EvAdventureDungeonBranch(DefaultScript):
    """
    One script is created for every dungeon 'instance' created. The branch is
    responsible for determining what is created next when a character enters an
    exit within the dungeon.

    """
    # this determines how branching the dungeon will be
    max_unexplored_exits = 2
    max_new_exits_per_room = 2

    rooms = AttributeProperty(list())
    unvisited_exits = AttributeProperty(list())

    last_updated = AttributeProperty(datetime.utcnow())

    # the room-generator function; copied from the same-name value on the
    # start-room when the branch is first created
    room_generator = AttributeProperty(None, autocreate=False)

    # (x,y): room coordinates used up by the branch
    xy_grid = AttributeProperty(dict())
    start_room = AttributeProperty(None, autocreate=False)


    def register_exit_traversed(self, exit):
        """
        Tell the system the given exit was traversed. This allows us to track
        how many unvisited paths we have so as to not have it grow
        exponentially.

        """
        if exit.id in self.unvisited_exits:
            self.unvisited_exits.remove(exit.id)

    def create_out_exit(self, location, exit_direction="north"):
        """
        Create outgoing exit from a room. The target room is not yet created.

        """
        out_exit = create.create_object(
            EvAdventureDungeonExit,
            key=exit_direction,
            location=location,
            aliases=_EXIT_ALIASES[exit_direction],
        )
        self.unvisited_exits.append(out_exit.id)
        
    def delete(self):
        """
        Clean up the dungeon branch.

        """
        pass  # to be implemented
        
    def new_room(self, from_exit):
        """
        Create a new Dungeon room leading from the provided exit.

        Args:
            from_exit (Exit): The exit leading to this new room.

        """
        pass  # to be implemented
```

This sets up useful properties needed for the branch and sketches out some methods we will implement below. 

The branch has several main responsibilities: 
- Track how many un-explored exits are available (making sure to not exceed the maximum allowed). As PCs traverse these exits we must update appropriately.
- Create new rooms when an unexplored exit is traversed. This room can in turn have outgoing exits. We must also track these rooms and exits so we can delete them later when the branch is cleaned up. 
- The branch must also be able to delete itself, cleaning up all its resources and rooms.

Since the `register_exit_traversed` and `create_out_exit` are straightforward, we implement them right away. The only extra thing about exit creation is that it must make sure to register the new exit as 'un-visited' so the branch can track it.

### A note about the room-generator

Of special note is the `room_generator` property of `EvAdventureDungeonBranch`. This will point to a function. We make this a plug-in since generating a room is something we will probably want to heavily customize as we create the game content - this is where we would generate our challenges, room descriptions etc. 

It makes sense that the room generator must have a link to the dungeon branch, the current expected difficulty (depth in our case) and the xy coordinates to create the room at. 

Here is an example of a very basic room generator that just maps depth to different room descriptions: 

```
# in evadventure/dungeon.py (could also be put with game content files)

# ... 

def room_generator(dungeon_branch, depth, coords):
    """
    Plugin room generator

    This default one returns the same empty room but with different descriptions.

    Args:
        dungeon_branch (EvAdventureDungeonBranch): The current dungeon branch.
        depth (int): The 'depth' of the dungeon (radial distance from start room) this
            new room will be placed at.
        coords (tuple): The `(x,y)` coords that the new room will be created at.

    """
    room_typeclass = EvAdventureDungeonRoom

    # simple map of depth to name and desc of room
    name_depth_map = {
        1: ("Water-logged passage", "This earth-walled passage is dripping of water."),
        2: ("Passage with roots", "Roots are pushing through the earth walls."),
        3: ("Hardened clay passage", "The walls of this passage is of hardened clay."),
        4: ("Clay with stones", "This passage has clay with pieces of stone embedded."),
        5: ("Stone passage", "Walls are crumbling stone, with roots passing through it."),
        6: ("Stone hallway", "Walls are cut from rough stone."),
        7: ("Stone rooms", "A stone room, built from crude and heavy blocks."),
        8: ("Granite hall", "The walls are of well-fitted granite blocks."),
        9: ("Marble passages", "The walls are blank and shiny marble."),
        10: ("Furnished rooms", "The marble walls have tapestries and furnishings."),
    }
    key, desc = name_depth_map.get(depth, ("Dark rooms", "There is very dark here."))

    new_room = create.create_object(
        room_typeclass,
        key=key,
        attributes=(
            ("desc", desc),
            ("xy_coords", coords),
            ("dungeon_branch", dungeon_branch),
        ),
    )
    return new_room

```

There's a _lot_ of logic that can go into this function - depending on depth, coordinate or random chance we could generate all sorts of different rooms, and fill it with mobs, puzzles or what have you. Since we have access to the dungeon-branch object we could even change things in other rooms to make for really complex interactions (multi-room puzzles, anyone?).

This will come into play in [Part 4 of this tutorial](../Part4/Beginner-Tutorial-Part4-Overview.md), where we'll make use of the tools we are creating here to actually build the game world.

### Deleting a dungeon branch 

We will want to be able to clean up a branch. There are many reasons for this: 
- Once every PC has left the branch there is no way for them to return, so all that data is now just taking up space.
- Branches are not meant to be permanent. So if players were to just stop exploring and sit around in the branch for a very long time, we should have a way to just force them back out.

In order for properly cleaning out characters inside this dungeon, we make a few assumptions:
- When we create the dungeon branch, we give its script a unique identifier (e.g. something involving the current time).
- When we start the dungeon branch, we tag that character with the branch's unique identifier. 
- Similarly, when we create rooms inside this branch, we tag them with the branch's identifier.

If have done that it will be easy to find all characters and rooms associated with the branch in order to do this cleanup operation.

```python
# in evadventure/dungeon.py 

from evennia import search

# ... 

class EvAdventureDungeonBranch(DefaultScript):

    # ...

    def delete(self):
        """
        Clean up the dungeon branch, removing players safely

        """
        # first secure all characters in this branch back to the start room
        characters = search.search_object_by_tag(self.key, category="dungeon_character")
        start_room = self.start_room
        for character in characters:
            start_room.msg_contents(
                "Suddenly someone stumbles out of a dark exit, covered in dust!"
            )
            character.location = start_room
            character.msg(
                "|rAfter a long time of silence, the room suddenly rumbles and then collapses! "
                "All turns dark ...|n\n\nThen you realize you are back where you started."
            )
            character.tags.remove(self.key, category="dungeon_character")
        # next delete all rooms in the dungeon (this will also delete exits)
        rooms = search.search_object_by_tag(self.key, category="dungeon_room")
        for room in rooms:
            room.delete()
        # finally delete the branch itself
        super().delete()

    # ...

```

The `evennia.search.search_object_by_tag` is an in-built Evennia utility for finding objects tagged with a specific tag+category combination. 

1. First we get the characters and move them safely to the start room, with a relevant message.
2. Then we get all the rooms in the branch and delete them (exits will be deleted automatically).
3. Finally we delete the branch itself. 

### Creating a new dungeon room

This is the meat of the Dungeon branch's responsibilities. In this method we create the new room but also need to create exits leading back to where we came from as well as (randomly) generate exits to other parts of the dungeon. 


```{code-block}
:linenos: 
:emphasize-lines: 20,23,31,37,44,58,67,72,77
# in evadventure/dungeon.py 

from datetime import datetime
from random import shuffle

# ... 

class EvAdventureDungeonBranch(DefaultScript):

    # ...

    def new_room(self, from_exit):
        """
        Create a new Dungeon room leading from the provided exit.

        Args:
            from_exit (Exit): The exit leading to this new room.

        """
        self.last_updated = datetime.utcnow()
        # figure out coordinate of old room and figure out what coord the
        # new one would get
        source_location = from_exit.location
        x, y = source_location.attributes.get("xy_coords", default=(0, 0))
        dx, dy = _EXIT_GRID_SHIFT.get(from_exit.key, (0, 1))
        new_x, new_y = (x + dx, y + dy)

        # the dungeon's depth acts as a measure of the current difficulty level. This is the radial
        # distance from the (0, 0) (the entrance). The branch also tracks the highest
        # depth achieved.
        depth = int(sqrt(new_x**2 + new_y**2))

        new_room = self.room_generator(self, depth, (new_x, new_y))

        self.xy_grid[(new_x, new_y)] = new_room

        # always make a return exit back to where we came from
        back_exit_key = _EXIT_REVERSE_MAPPING.get(from_exit.key, "back")
        create.create_object(
            EvAdventureDungeonExit,
            key=back_exit_key,
            aliases=_EXIT_ALIASES.get(back_exit_key, ()),
            location=new_room,
            destination=from_exit.location,
            attributes=(
                (
                    "desc",
                    "A dark passage.",
                ),
            ),
            # we default to allowing back-tracking (also used for fleeing)
            locks=("traverse: true()",),
        )

        # figure out what other exits should be here, if any
        n_unexplored = len(self.unvisited_exits)

        if n_unexplored < self.max_unexplored_exits:
            # we have a budget of unexplored exits to open
            n_exits = min(self.max_new_exits_per_room, self.max_unexplored_exits)
            if n_exits > 1:
                n_exits = randint(1, n_exits)
            available_directions = [
                direction for direction in _AVAILABLE_DIRECTIONS if direction != back_exit_key
            ]
            # randomize order of exits
            shuffle(available_directions)
            for _ in range(n_exits):
                while available_directions:
                    # get a random direction and check so there isn't a room already
                    # created in that direction
                    direction = available_directions.pop(0)
                    dx, dy = _EXIT_GRID_SHIFT[direction]
                    target_coord = (new_x + dx, new_y + dy)
                    if target_coord not in self.xy_grid and target_coord != (0, 0):
                        # no room there (and not back to start room) - make an exit to it
                        self.create_out_exit(new_room, direction)
                        # we create this to avoid other rooms linking here, but don't create the
                        # room yet
                        self.xy_grid[target_coord] = None
                        break

        return new_room
```

A lot to unpack here! 

- **Line 17**: We store the 'last updated' time as the current UTC timestamp. As we discussed in the deletion section just above we need to know if a branch has been 'idle' for a long time, and this helps track that. 
- **Line 20**: The `from_exit` input is an Exit object (probably a `EvAdventureDungeonExit)` It is located in the 'source' location (where we start moving from).  On the subsequent lines we figure out the coordinates of the source and where we'd end up by moving in the direction suggested
- **Line 28**: Pythagorean theorem!
- **Line 30**: Here we call the `room_generator` plugin function we exemplified above to get the new room.
- **Line 34**: We always create a back-exit the way we came. This _overrides_ the default dungeon exit lock with `"traverse:true()"`, meaning the PCs will always be able to go back the way they came.
- **Line 44**: We could leave the `destination` field empty, but Evennia assumes exits have a `destination` field set when it displays things in the room etc. So to avoid having to change how rooms display things, this value should be set to _something_.  Since we don't want to create the actual destination yet we instead instead point the `destination` back to the current room. That is - if you could pass through this exit you'd end up in the same place. We'll use this below to identify non-explored exits.
- **Line 55**: We only create new exits our 'budget' of unexplored exits allows it.
- **Line 64**: On the line above we create a new list of all possible exits-directions the room can have (excluding the must-have back-exit). Here we shuffle this list in a random order. 
- **Line 69**: In this loop we pop off the first element of the shuffled list (so this is a random direction). On the following lines we check so that this direction is not pointing to an already existing dungeon room, nor back to the start room. If all is good we call our exit-creation method on **Line 74**.

In the end the outcome is a new room with at least one back-exit and 0 or more unexplored exits.

## Back to the dungeon exit class 

Now that we have the tools, we can go back to the `EvAdventureDungeonExit` class to implement that `at_traverse` method we skipped before.

```python
# in evadventure/dungeon.py 

# ... 

class EvAdventureDungeonExit(DefaultExit):

# ...
    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Called when traversing. `target_location` will be pointing back to
        ourselves if the target was not yet created. It checks the current
        location to get the dungeon-branch in use.

        """
        dungeon_branch = self.location.db.dungeon_branch
        if target_location == self.location:
            # destination points back to us - create a new room
            self.destination = target_location = dungeon_branch.new_room(
                self
            )
            dungeon_branch.register_exit_traversed(self)

        super().at_traverse(traversing_object, target_location, **kwargs)

```

We get the `EvAdventureDungeonBranch` instance and check out if this current exit is pointing back to the current room. If you read line 44 in the previous section, you'll notice that this is the way to find if this exit is previously non-explored! 

If so, we call the dungeon branche's `new_room` to generate a new room and change this exit's `destination` to it. We also make sure to call  `.register_exit_traversed` to show that is exit is now 'explored'.

We must also call the parent class' `at_traverse` using `super()` since that is what is actually moving the PC to the newly created location.

## Starting room exits 

We now have all the pieces for actually running a procedural dungeon branch once it's created. What's missing is the start room from which all branches originate. 

As described in the design, the room's exits will spawn new branches, but there should also be a time period while PCs will all end up in the same branch. So we need a special type of exit for those exits leading out of the starting room.

```{code-block} python
:linenos:
:emphasize-lines: 12,19,22,32
# in evennia/dungeon.py

# ... 

class EvAdventureDungeonStartRoomExit(DefaultExit):

    def reset_exit(self):
        """
        Flush the exit, so next traversal creates a new dungeon branch.

        """
        self.destination = self.location

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        When traversing create a new branch if one is not already assigned.

        """
        if target_location == self.location:
            # make a global branch script for this dungeon branch
            self.location.room_generator
            dungeon_branch = create.create_script(
                EvAdventureDungeonBranch,
                key=f"dungeon_branch_{self.key}_{datetime.utcnow()}",
                attributes=(
                    ("start_room", self.location),
                    ("room_generator", self.location.room_generator),
                ),
            )
            self.destination = target_location = dungeon_branch.new_room(self)
            # make sure to tag character when entering so we can find them again later
            traversing_object.tags.add(dungeon_branch.key, category="dungeon_character")

        super().at_traverse(traversing_object, target_location, **kwargs)
```

This exit has everything it needs for creating a new dungeon branch. 

- **Line 12**: Disconnects the exit from whatever it was connected to and links it back to the current room (a looping, worthless exit).
- **Line 19**: The `at_traverse` is called when someone moves through this exit. We detect that special condition above (destination equal to current location) to determine that this exit is currently leading nowhere and we should create a new branch. 
- **Line 22**: We create a new `EvAdventureDungeonBranch`and make sure to give it a unique `key` based on the current time. We also make sure to set its starting Attributes.
- **Line 32**: When the player traverses this exit, the character gets tagged with the appropriate tag for this dungeon branch. This can be used by the deletion mechanism later.

## Utility scripts 

Before we can create the starting room, we need two last utilities: 

- A timer for regularly resetting exits out of the starting room (so they create new branches).
- A repeating task for cleaning out old/idle dungeon branches.

Both of these scripts are expected to be created 'on' the start room, so `self.obj` will be the start room.

```python
# in evadventure/dungeon.py

from evennia.utils.utils import inherits_from

# ... 

class EvAdventureStartRoomResetter(DefaultScript):
    """
    Simple ticker-script. Introduces a chance of the room's exits cycling every
    interval.

    """

    def at_script_creation(self):
        self.key = "evadventure_dungeon_startroom_resetter"

    def at_repeat(self):
        """
        Called every time the script repeats.

        """
        room = self.obj
        for exi in room.exits:
            if inherits_from(exi, EvAdventureDungeonStartRoomExit) and random() < 0.5:
                exi.reset_exit()
```

This script is very simple - it just loops over all the start-room exits and resets each exit 50% of the time.

```python
# in evadventure/dungeon.py

# ... 

class EvAdventureDungeonBranchDeleter(DefaultScript):
    """
    Cleanup script. After some time a dungeon branch will 'collapse', forcing all players in it
    back to the start room.

    """

    # set at creation time when the start room is created
    branch_max_life = AttributeProperty(0, autocreate=False)

    def at_script_creation(self):
        self.key = "evadventure_dungeon_branch_deleter"

    def at_repeat(self):
        """
        Go through all dungeon-branchs and find which ones are too old.

        """
        max_dt = timedelta(seconds=self.branch_max_life)
        max_allowed_date = datetime.utcnow() - max_dt

        for branch in EvAdventureDungeonBranch.objects.all():
            if branch.last_updated < max_allowed_date:
                # branch is too old; tell it to clean up and delete itself
                branch.delete()

```

This script checks all branches and sees how long it was since they were last updated (that is, a new room created in them). If it's been too long, the branch will be deleted (which will dump all players back in the start room).

## Starting room

Finally, we need a class for the starting room. This room will need to be manually created, after which the branches should create themselves automatically.

```python
# in evadventure/dungeon.py

# ... 

class EvAdventureDungeonStartRoom(EvAdventureDungeonRoom):

    recycle_time = 60 * 5  # 5 mins
    branch_check_time = 60 * 60  # one hour
    branch_max_life = 60 * 60 * 24 * 7  # 1 week

    # allow for a custom room_generator function
    room_generator = AttributeProperty(lambda: room_generator, autocreate=False)

    def get_display_footer(self, looker, **kwargs):
        return (
            "|yYou sense that if you want to team up, "
            "you must all pick the same path from here ... or you'll quickly get separated.|n"
        )

    def at_object_creation(self):
        # want to set the script interval on creation time, so we use create_script with obj=self
        # instead of self.scripts.add() here
        create.create_script(
            EvAdventureStartRoomResetter, obj=self, interval=self.recycle_time, autostart=True
        )
        create.create_script(
            EvAdventureDungeonBranchDeleter,
            obj=self,
            interval=self.branch_check_time,
            autostart=True,
            attributes=(("branch_max_life", self.branch_max_life),),
        )

    def at_object_receive(self, obj, source_location, **kwargs):
        """
        Make sure to clean the dungeon branch-tag from characters when leaving a dungeon branch.

        """
        obj.tags.remove(category="dungeon_character")



```

All that is left for this room to do is to set up the scripts we created and make sure to clear out the branch tags of any object returning from a branch into this room. All other work is handled by the exits and the dungeon-branches.

## Testing 

```{sidebar}
Examples of unit testing files are found at `evennia/contrib/tutorials/` in [evadventure/tests/test_dungeon.py](evennia.contrib.tutorials.evadventure.tests.test_dungeon).
```

> Create `evadventure/tests/test_dungeon.py`.

Testing the procedural dungeon is best done both with unit tests and manually. 

To test manually, it's simple to in-game do 

```shell
> dig well:evadventure.dungeon.EvAdventureDungeonStartRoom = down,up
> down 
> create/drop north;n:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop east;e:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop south;s:evadventure.dungeon.EvAdventureDungeonStartRoomExit
> create/drop west;w:evadventure.dungeon.EvAdventureDungeonStartRoomExit
```
    
You should now be able to head out one of the exits and start exploring the dungeon! This is particularly useful once everything works a

To unit test, you create a start room and exits in code, and then emulate a character moving through the exits, making sure the results are as expected.  We leave this an exercise to the reader.

## Conclusions 

This is only skimming the surface of the possibilities of procedural generation, but with relatively easy means one can create an infinitely growing dungeon for players to explore.  

It's also worth that this only touches on how to procedurally generate the dungeon structure. It doesn't yet have much _content_ to fill the dungeon with. We will get back to that in [Part 4](../Part4/Beginner-Tutorial-Part4-Overview.md), where we'll make use of the code we've created to create game content.