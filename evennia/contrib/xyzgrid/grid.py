"""
The grid

This represents the full XYZ grid, which consists of

- 2D `Map`-objects parsed from Map strings and Map-legend components. Each represents one
  Z-coordinate or location.
- `Prototypes` for how to build each XYZ component into 'real' rooms and exits.
- Actual in-game rooms and exits, mapped to the game based on Map data.

The grid has three main functions:
- Building new rooms/exits from scratch based on one or more Maps.
- Updating the rooms/exits tied to an existing Map when the Map string
  of that map changes.


"""

class XYZGrid:
    pass
