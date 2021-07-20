# XYZgrid

Full grid coordinate- pathfinding and visualization system
Evennia Contrib by Griatch 2021

The default Evennia's rooms are non-euclidian - they can connect
to each other with any types of exits without necessarily having a clear
position relative to each other. This gives maximum flexibility, but many games
want to use cardinal movements (north, east etc) and also features like finding
the shortest-path between two points.

This contrib forces each room to exist on a 3-dimensional XYZ grid and also
implements very efficient pathfinding along with tools for displaying
your current visual-range and a lot of related features.

The rooms of the grid are entirely controlled from outside the game, using
python modules with strings and dicts defining the map(s) of the game. It's
possible to combine grid- with non-grid rooms, and you can decorate
grid rooms as much as you like in-game, but you cannot spawn new grid
rooms without editing the map files outside of the game.

The full docs are found as
[Contribs/XYZGrid](https://evennia.com/docs/latest/Contributions/XYZGrid.html)
in the docs.

## Installation

1. Import and add the `evennia.contrib.commands.XYZGridCmdSet` to the
   `CharacterCmdset` cmdset in `mygame/commands.default_cmds.py`. Reload
   the server. This makes the `map`, `goto/path` and modified `teleport`  and
   `open` commands available in-game.
2. Edit `mygame/server/conf/settings.py` and set

        EXTRA_LAUNCHER_COMMANDS['xyzgrid'] = 'evennia.contrib.launchcmd.xyzcommand'

3. Run the new `evennia xyzgrid help` for instructions on how to spawn the grid.

## Example usage

After installation, do the following (from your command line, where the
`evennia` command is available) to install an example grid:

    evennia xyzgrid init
    evennia xyzgrid add evennia.contrib.xyzgrid.example
    evennia xyzgrid list
    evennia xyzgrid show "the large tree"
    evennia xyzgrid show "the small cave"
    evennia xyzgrid spawn
    evennia reload

(remember to reload the server after spawn operations).

Now you can log into the
server and do `teleport (3,0,the large tree)` to teleport into the map.

You can use `open togrid = (3, 0, the large tree)` to open a permanent (one-way)
exit from your current location into the grid. To make a way back to a non-grid
location just stand in a grid room and open a new exit out of it:
`open tolimbo = #2`.

Try `goto view` to go to the top of the tree and `goto dungeon` to go down to
the dungeon entrance at the bottom of the tree.
