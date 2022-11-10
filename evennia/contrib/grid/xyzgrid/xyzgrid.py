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
from evennia.scripts.scripts import DefaultScript
from evennia.utils import logger
from evennia.utils.utils import variable_from_module

from .xymap import XYMap
from .xyzroom import XYZExit, XYZRoom


class XYZGrid(DefaultScript):
    """
    Main grid class. This organizes the Maps based on their name/Z-coordinate.

    """

    def at_script_creation(self):
        """
        What we store persistently is data used to create each map (the legends, names etc)

        """
        self.db.map_data = {}
        self.desc = "Manages maps for XYZ-grid"

    @property
    def grid(self):
        if self.ndb.grid is None:
            self.reload()
        return self.ndb.grid

    def get_map(self, zcoord):
        """
        Get a specific xymap.

        Args:
            zcoord (str): The name/zcoord of the xymap.

        Returns:
            XYMap: Or None if no map was found.

        """
        return self.grid.get(zcoord)

    def all_maps(self):
        """
        Get all xymaps stored in the grid.

        Returns:
            list: All initialized xymaps stored with this grid.

        """
        return list(self.grid.values())

    def log(self, msg):
        logger.log_info(f"|grid| {msg}")

    def get_room(self, xyz, **kwargs):
        """
        Get one or more room objects from XYZ coordinate.

        Args:
            xyz (tuple): X,Y,Z coordinate of room to fetch. '*' acts
            as wild cards.

        Returns:
            Queryset: A queryset of XYZRoom(s) found.

        Raises:
            XYZRoom.DoesNotExist: If room is not found.

        Notes:
            This assumes the room was previously built.

        """
        return XYZRoom.objects.filter_xyz(xyz=xyz, **kwargs)

    def get_exit(self, xyz, name="north", **kwargs):
        """
        Get one or more exit object at coordinate.

        Args:
            xyz (tuple): X,Y,Z coordinate of the room the
                exit leads out of. '*' acts as a wildcard.
            name (str): The full name of the exit, e.g. 'north' or 'northwest'.
                The '*' acts as a wild card.

        Returns:
            Queryset: A queryset of XYZExit(s) found.

        """
        kwargs["db_key"] = name
        return XYZExit.objects.filter_xyz_exit(xyz=xyz, **kwargs)

    def maps_from_module(self, module_path):
        """
        Load map data from module. The loader will look for a dict XYMAP_DATA or a list of
        XYMAP_DATA_LIST (a list of XYMAP_DATA dicts). Each XYMAP_DATA dict should contain
        `{"xymap": mapstring, "zcoord": mapname/zcoord, "legend": dict, "prototypes": dict}`.

        Args:
            module_path (module_path): A python-path to a module containing
                map data as either `XYMAP_DATA` or `XYMAP_DATA_LIST` variables.

        Returns:
            list: List of zero, one or more xy-map data dicts loaded from the module.

        """
        map_data_list = variable_from_module(module_path, "XYMAP_DATA_LIST")
        if not map_data_list:
            map_data_list = [variable_from_module(module_path, "XYMAP_DATA")]
        # inject the python path in the map data
        for mapdata in map_data_list:
            if not mapdata:
                self.log(f"Could not find or load map from {module_path}.")
                return
            mapdata["module_path"] = module_path
        return map_data_list

    def reload(self):
        """
        Reload and rebuild the grid. This is done on a server reload.

        """
        self.log("(Re)loading grid ...")
        self.ndb.grid = {}
        nmaps = 0
        loaded_mapdata = {}
        changed = []
        mapdata = self.db.map_data

        if not mapdata:
            self.db.mapdata = mapdata = {}

        # generate all Maps - this will also initialize their components
        # and bake any pathfinding paths (or load from disk-cache)
        for zcoord, old_mapdata in mapdata.items():

            self.log(f"Loading map '{zcoord}'...")

            # we reload the map from module
            new_mapdata = loaded_mapdata.get(zcoord)
            if not new_mapdata:
                if "module_path" in old_mapdata:
                    for mapdata in self.maps_from_module(old_mapdata["module_path"]):
                        loaded_mapdata[mapdata["zcoord"]] = mapdata
                else:
                    # nowhere to reload from - use what we have
                    loaded_mapdata[zcoord] = old_mapdata

                new_mapdata = loaded_mapdata.get(zcoord)

            if new_mapdata != old_mapdata:
                self.log(f" XYMap data for Z='{zcoord}' has changed.")
                changed.append(zcoord)

            xymap = XYMap(dict(new_mapdata), Z=zcoord, xyzgrid=self)
            xymap.parse()
            xymap.calculate_path_matrix()
            self.ndb.grid[zcoord] = xymap
            nmaps += 1

        # re-store changed data
        for zcoord in changed:
            self.db.map_data[zcoord] = loaded_mapdata[zcoord]

        # store
        self.log(f"Loaded and linked {nmaps} map(s).")
        self.ndb.loaded = True

    def add_maps(self, *mapdatas):
        """
        Add map or maps to the grid.

        Args:
            *mapdatas (dict): Each argument is a dict structure
                `{"map": <mapstr>, "legend": <legenddict>, "name": <name>,
                "prototypes": <dict-of-dicts>, "module_path": <str>}`. The `prototypes are
                coordinate-specific overrides for nodes/links on the map, keyed with their
                (X,Y) coordinate within that map. The `module_path` is injected automatically
                by self.maps_from_module.

        Raises:
            RuntimeError: If mapdata is malformed.

        """
        for mapdata in mapdatas:
            zcoord = mapdata.get("zcoord")
            if not zcoord:
                raise RuntimeError("XYZGrid.add_map data must contain 'zcoord'.")

            self.db.map_data[zcoord] = mapdata

    def remove_map(self, *zcoords, remove_objects=True):
        """
        Remove an XYmap from the grid.

        Args:
            *zoords (str): The zcoords/XYmaps to remove.
            remove_objects (bool, optional): If the synced database objects (rooms/exits) should
                be removed alongside this map.
        """
        # from evennia import set_trace;set_trace()
        for zcoord in zcoords:
            if zcoord in self.db.map_data:
                self.db.map_data.pop(zcoord)
            if remove_objects:
                # we can't batch-delete because we want to run the .delete
                # method that also wipes exits and moves content to save locations
                for xyzroom in XYZRoom.objects.filter_xyz(xyz=("*", "*", zcoord)):
                    xyzroom.delete()
        self.reload()

    def delete(self):
        """
        Clear the entire grid, including database entities, then the grid too.

        """
        mapdata = self.db.map_data
        if mapdata:
            self.remove_map(*(zcoord for zcoord in self.db.map_data), remove_objects=True)
        super().delete()

    def spawn(self, xyz=("*", "*", "*"), directions=None):
        """
        Create/recreate/update the in-game grid based on the stored Maps or for a specific Map
        or coordinate.

        Args:
            xyz (tuple, optional): An (X,Y,Z) coordinate, where Z is the name of the map. `'*'`
                acts as a wildcard.
            directions (list, optional): A list of cardinal directions ('n', 'ne' etc).
                Spawn exits only the given direction. If unset, all needed directions are spawned.

        Examples:
            - `xyz=('*', '*', '*')` (default) - spawn/update all maps.
            - `xyz=(1, 3, 'foo')` - sync a specific element of map 'foo' only.
            - `xyz=('*', '*', 'foo') - sync all elements of map 'foo'
            - `xyz=(1, 3, '*') - sync all (1,3) coordinates on all maps (rarely useful)
            - `xyz=(1, 3, 'foo')`, `direction='ne'` - sync only the north-eastern exit
                out of the specific node on map 'foo'.

        """
        x, y, z = xyz
        wildcard = "*"

        if z == wildcard:
            xymaps = self.grid
        elif self.ndb.grid and z in self.ndb.grid:
            xymaps = {z: self.grid[z]}
        else:
            raise RuntimeError(f"The 'z' coordinate/name '{z}' is not found on the grid.")

        # first build all nodes/rooms
        for zcoord, xymap in xymaps.items():
            self.log(f"spawning/updating nodes for Z='{zcoord}' ...")
            xymap.spawn_nodes(xy=(x, y))

        # next build all links between nodes (including between maps)
        for zcoord, xymap in xymaps.items():
            self.log(f"spawning/updating links for Z='{zcoord}' ...")
            xymap.spawn_links(xy=(x, y), directions=directions)


def get_xyzgrid(print_errors=True):
    """
    Helper for getting the grid. This will create the XYZGrid global script if it didn't
    previously exist.

    Args:
        print_errors (bool, optional): Print errors directly to console rather than to log.

    """
    xyzgrid = XYZGrid.objects.all()
    if not xyzgrid:
        # create a new one
        xyzgrid, err = XYZGrid.create("XYZGrid")
        if err:
            raise RuntimeError(err)
        xyzgrid.reload()
        return xyzgrid
    elif len(xyzgrid) > 1:
        (
            "Warning: More than one XYZGrid instances were found. This is an error and "
            "only the first one will be used. Delete the other one(s) manually."
        )
    xyzgrid = xyzgrid[0]
    try:
        if not xyzgrid.ndb.loaded:
            xyzgrid.reload()
    except Exception as err:
        raise
        if print_errors:
            print(err)
        else:
            xyzgrid.log(str(err))
    return xyzgrid
