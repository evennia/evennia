"""
Maprunner

This is a stand-alone program for baking and preparing grid-maps.

## Baking

The Dijkstra algorithm is very powerful for pathfinding, but for very large grids it can be slow
to build the initial distance-matrix. As an example, for an extreme case of 10 000 nodes, all
connected along all 8 cardinal directions, there are so many possible combinations that it
takes about 25 seconds on medium hardware to build the matrix. 40 000 nodes takes about 9 minutes.

Once the matrix is built, pathfinding across the entire grid is a <0.1s operation however. So as
long as the grid doesn't change, it's a good idea to pre-build it. Pre-building like this is
often referred to as 'baking' the asset.

This program will build and run the Dijkstra on a given map and store the result as a
serialized binary file in the `mygame/server/.cache/ directory. If it exists, the Map
will load this file. If the map changed since it was saved, the file will be automatically
be rebuilt.

"""



