"""
Over-arching map system for representing a larger number of Maps linked together with transitions.

"""
from .map_single import SingleMap


class MultiMap:
    """
    Coordinate multiple maps.

    """

    def __init__(self):
        self.maps = {}

    def add_map(self, map_module_or_dict, name="map"):
        """
        Add a new map to the multimap store.

        Args:
            map_module_or_dict (str, module or dict): Path or module pointing to a map. If a dict,
                this should be a dict with a key 'map' and optionally a 'legend', 'name' and
                `prototypes` keys.
            name (str): Unique identifier for this map. Needed if the game uses
                more than one map. Used when referencing this map during map transitions,
                baking of pathfinding matrices etc.

        """
        self.maps[name] = SingleMap(map_module_or_dict, name=name, other_maps=self.maps)
