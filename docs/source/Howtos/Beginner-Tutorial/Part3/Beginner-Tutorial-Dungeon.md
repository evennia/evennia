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

Each branch is managed by an branch _orchestrator_. The orchestrator tracks the layout of rooms belonging to this branch on an (X, Y) coordinate grid.

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

A dungeon room is only created when actually moving to it. In the above example, the PC moved `east` from the start room, which initiated a new dungeon branch with its own branch orchestrator. The orchestrator also created a new room (room `A`) at coordinate `(1,0)`. In this case it (randomly) seeded this room with three exits `north`, `east` and `south`.
Since this branch was just created, the exit back to the start room is still two-way.

This is the procedure the orchestrator follows when spawning a new room:

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

1. PC moves `east` from the start room. A new room `A` (coordinate `(1, 0)` ) is created. After a while the exit back to the start room becomes a one-way exit. The branch can have at most 4 unexplored exits, and the orchestrator randomly adds three additional exits out of room `A`. 
2. PC moves `south`. A new room `B` (`(1,-1)`) is created, with two random exits, which is as many as the orchetrator is allowed to create at this time (4 are now open). It also always creates an exit back to the previous room (`A`)
3. PC moves `east` (coordinate (`(2, -1)`). A new room `C` is created. The orchestrator already has 3 exits unexplored, so it can only add one exit our of this room. 
4. PC moves `east` (`(3, -1)`). While the orchestrator still has a budget of one exit, it knows there are other unexplored exits elsewhere, and is allowed to randomly create 0 exits. This is a dead end. The PC must go back and explore another direction.

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

> If the maximum allowed number of open unexplored exits is small, this case is the only situation where it's possible to 'finish' the dungeon (having no more unexplored exits to follow). We accept this as a case where the PCs just have to turn back.

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

The orchestrator never creates a link back to the start room, but it _could_ have created up to two new exits `west` and/or `south`. Since there's still an unexplored exit `north` from room `A`, the orchestrator is also allowed to randomly assign 0 exits, which is what it did here. 

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

## Implementation

```{warning}
TODO: This part is TODO.
```