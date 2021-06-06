"""

Tests for the Mapsystem

"""

from unittest import TestCase
from parameterized import parameterized
from . import mapsystem


MAP1 = """

 + 0 1 2

 1 #-#
   | |
 0 #-#

 + 0 1 2

"""

MAP1_DISPLAY = """
#-#
| |
#-#
""".strip()


MAP2 = """

 + 0 1 2 3 4 5

 5 #-#-#-#-#
       |   |
 4     #---#
       |   |
 3 #   |   #-#
   |   |     |
 2 #-#-#-#---#
   |   |
 1 #-#-#---#-#
     |     |
 0   #-#-#-#

 + 0 1 2 3 4 5

"""

MAP2_DISPLAY = """
#-#-#-#-#
    |   |
    #---#
    |   |
#   |   #-#
|   |     |
#-#-#-#---#
|   |
#-#-#---#-#
  |     |
  #-#-#-#
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
        self.assertEqual(node.X, 1)
        self.assertEqual(node.x, 2)
        self.assertEqual(node.X, 1)
        self.assertEqual(node.y, 2)

    def test_get_shortest_path(self):
        nodepath, linkpath = self.map.get_shortest_path((0, 0), (1, 1))
        self.assertEqual([node.node_index for node in nodepath], [0, 1, 3])
        self.assertEqual(linkpath, ['e', 'n'])

    @parameterized.expand([
        ((0, 0), "#-\n| ", [["#", "-"], ["|", " "]]),
        ((1, 0), "-#\n |", [["-", "#"], [" ", "|"]]),
        ((0, 1), "| \n#-", [["|", " "], ["#", "-"]]),
        ((1, 1), " |\n-#", [[" ", "|"], ["-", "#"]]),

    ])
    def test_get_map_display(self, coord, expectstr, expectlst):
        string = self.map.get_map_display(coord, dist=1, character=None)
        lst = self.map.get_map_display(coord, dist=1, return_str=False, character=None)
        self.assertEqual(string, expectstr)
        self.assertEqual(lst, expectlst)

    @parameterized.expand([
        ((0, 0), "@-\n| ", [["@", "-"], ["|", " "]]),
        ((1, 0), "-@\n |", [["-", "@"], [" ", "|"]]),
        ((0, 1), "| \n@-", [["|", " "], ["@", "-"]]),
        ((1, 1), " |\n-@", [[" ", "|"], ["-", "@"]]),

    ])
    def test_get_map_display__character(self, coord, expectstr, expectlst):
        string = self.map.get_map_display(coord, dist=1, character='@')
        lst = self.map.get_map_display(coord, dist=1, return_str=False, character='@')
        self.assertEqual(string, expectstr)
        self.assertEqual(lst, expectlst)


class TestMap2(TestCase):
    """
    Test with Map2 - a bigger map with some links crossing nodes.

    """
    def setUp(self):
        self.map = mapsystem.Map({"map": MAP2})

    def test_str_output(self):
        """Check the display_map"""
        self.assertEqual(str(self.map).strip(), MAP2_DISPLAY)
