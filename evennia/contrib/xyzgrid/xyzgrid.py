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
- Fascilitate communication between the in-game entities and their Map.


"""
import itertools
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger
from .xymap import XYMap


class XYZGrid(DefaultScript):
    """
    Main grid class. This organizes the Maps based on their name/Z-coordinate.

    """
    def at_script_creation(self):
        """
        What we store persistently is the module-paths to each map.

        """
        self.db.map_data = {}

    def reload(self):
        """
        Reload the grid. This is done on a server reload and is also necessary if adding a new map
        since this may introduce new between-map traversals.

        """
        # build the nodes of each map
        for name, xymap in self.grid:
            xymap.parse_first_pass()
        # link everything together
        for name, xymap in self.grid:
            xymap.parse_second_pass()

    def add_map(self, mapdata, new=True):
        """
        Add new map to the grid.

        Args:
            mapdata (dict): A structure `{"map": <mapstr>, "legend": <legenddict>,
                "name": <name>, "prototypes": <dict-of-dicts>}`. The `prototypes are
                coordinate-specific overrides for nodes/links on the map, keyed with their
                (X,Y) coordinate (use .5 for link-positions between nodes).
            new (bool, optional): If the data should be resaved.

        Raises:
            RuntimeError: If mapdata is malformed.


        Notes:
            After this, you need to run `.sync_to_grid` to make the new map actually
            available in-game.

        """
        name = mapdata.get('name')
        if not name:
            raise RuntimeError("XYZGrid.add_map data must contain 'name'.")

        # this will raise MapErrors if there are issues with the map
        self.grid[name] = XYMap(mapdata, name=name, grid=self)
        if new:
            self.db.map_data[name] = mapdata

    def remove_map(self, zcoord, remove_objects=False):
        """
        Remove a map from the grid.

        Args:
            name (str): The map to remove.
            remove_objects (bool, optional): If the synced database objects (rooms/exits) should
                be removed alongside this map.
        """
        if zcoord in self.grid:
            self.db.map_data.pop(zcoord)
            self.grid.pop(zcoord)

        if remove_objects:
            pass

    def sync_to_grid(self, coord=(None, None, None), direction=None):
        """
        Create/recreate/update the in-game grid based on the stored Maps or for a specific Map
        or coordinate.

        Args:
            coord (tuple, optional): An (X,Y,Z) coordinate, where Z is the name of the map. `None`
                acts as a wildcard.
            direction (str, optional): A cardinal direction ('n', 'ne' etc). If given, sync only the
            exit in the given direction. `None` acts as a wildcard.

        Examples:
            - `coord=(1, 3, 'foo')` - sync a specific element of map 'foo' only.
            - `coord=(None, None, 'foo') - sync all elements of map 'foo'
            - `coord=(1, 3, None) - sync all (1,3) coordinates on all maps (rarely useful)
            - `coord=(None, None, None)` - sync all maps.
            - `coord=(1, 3, 'foo')`, `direction='ne'` - sync only the north-eastern exit
                out of the specific node on map 'foo'.

        """
        x, y, z = coord

        if z is None:
            xymaps = self.grid
        elif z in self.grid:
            xymaps = [self.grid[z]]
        else:
            raise RuntimeError(f"The 'z' coordinate/name '{z}' is not found on the grid.")

        # first syncing pass (only nodes/rooms)
        synced = []
        for xymap in xymaps:
            for node in xymap.node_index_map.values():
                if (x is None or x == node.X) and (y is None or y == node.Y):
                    node.sync_node_to_grid()
                    synced.append(node)
        # second pass (links/exits)
        for node in synced:
            node.sync_links_to_grid()

    def at_init(self):
        """
        Called when the script loads into memory after a reload. This will load all map data into
        memory.

        """
        nmaps = 0
        for mapname, mapdata in self.db.map_data:
            self.add_map(mapdata, new=False)
            nmaps += 1
        self.reload()
        logger.log_info(f"Loaded {nmaps} map(s) onto the grid.")
