"""

Helpers and resources for the map system.

"""

BIGVAL = 999999999999

REVERSE_DIRECTIONS = {
    "n": "s",
    "ne": "sw",
    "e": "w",
    "se": "nw",
    "s": "n",
    "sw": "ne",
    "w": "e",
    "nw": "se",
}

MAPSCAN = {
    "n": (0, 1),
    "ne": (1, 1),
    "e": (1, 0),
    "se": (1, -1),
    "s": (0, -1),
    "sw": (-1, -1),
    "w": (-1, 0),
    "nw": (-1, 1),
}

# errors for Map system


class MapError(RuntimeError):
    def __init__(self, error="", node_or_link=None):
        prefix = ""
        if node_or_link:
            prefix = (
                f"{node_or_link.__class__.__name__} '{node_or_link.symbol}' "
                f"at XYZ=({node_or_link.X:g},{node_or_link.Y:g},{node_or_link.Z}) "
            )
        self.node_or_link = node_or_link
        self.message = f"{prefix}{error}"
        super().__init__(self.message)


class MapParserError(MapError):
    pass


class MapTransition(RuntimeWarning):
    """
    Used when signaling to the parser that a link
    leads to another map.

    """

    pass
