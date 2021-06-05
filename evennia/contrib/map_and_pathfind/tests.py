"""

Tests for the Mapsystem

"""

from unittest import TestCase, mock
from . import mapsystem


MAP1 = """

 + 0 1 2

 0 #-#
   | |
 1 #-#


"""
MAP1_DISPLAY = """
#-#
| |
#-#
""".strip()


class TestMap1(TestCase):
    """
    Test the Map class with a simple map and default symbol legend.

    """

    def setUp(self):
        self.map = mapsystem.Map({"map": MAP1})

    def test_str_output(self):
        """Check the display_map"""
        self.assertEqual(str(self.map).strip(), MAP1_DISPLAY)

    def test_node_from_coord(self):
        node = self.map._get_node_from_coord(1, 1)
        self.assertEqual(node.x, 1)
        self.assertEqual(node.y, 1)

    def test_get_shortest_path(self):
        nodepath, linkpath = self.map.get_shortest_path((0, 0), (1, 1))
        self.assertEqual([node.node_index for node in nodepath], [0, 1, 3])
        self.assertEqual(linkpath, ['e', 's'])

    def test_get_map_region(self):
        string = self.map.get_map_region(1, 0, dist=1)
        lst = self.map.get_map_region(1, 0, dist=1, return_str=False)

        self.assertEqual(string, "|\n#-")
        self.assertEqual(lst, [["|"], ['#', '-']])


