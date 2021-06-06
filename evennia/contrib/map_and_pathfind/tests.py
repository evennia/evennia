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
        node = self.map.get_node_from_coord(1, 1)
        self.assertEqual(node.X, 1)
        self.assertEqual(node.x, 2)
        self.assertEqual(node.X, 1)
        self.assertEqual(node.y, 2)

    def test_get_shortest_path(self):
        directions, path = self.map.get_shortest_path((0, 0), (1, 1))
        self.assertEqual(directions, ['e', 'n'])
        self.assertEqual(
            [str(node) for node in path],
            [str(self.map.node_index_map[0]),
             'e',
             str(self.map.node_index_map[1]),
             'n',
             str(self.map.node_index_map[3])]
        )

    @parameterized.expand([
        ((0, 0), "| \n#-", [["|", " "], ["#", "-"]]),
        ((1, 0), " |\n-#", [[" ", "|"], ["-", "#"]]),
        ((0, 1), "#-\n| ", [["#", "-"], ["|", " "]]),
        ((1, 1), "-#\n |", [["-", "#"], [" ", "|"]]),

    ])
    def test_get_map_display(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point.

        """
        mapstr = self.map.get_map_display(coord, dist=1, character=None)
        maplst = self.map.get_map_display(coord, dist=1, return_str=False, character=None)
        self.assertEqual(expectstr, mapstr)
        self.assertEqual(expectlst, maplst[::-1])

    @parameterized.expand([
        ((0, 0), "| \n@-", [["|", " "], ["@", "-"]]),
        ((1, 0), " |\n-@", [[" ", "|"], ["-", "@"]]),
        ((0, 1), "@-\n| ", [["@", "-"], ["|", " "]]),
        ((1, 1), "-@\n |", [["-", "@"], [" ", "|"]]),

    ])
    def test_get_map_display__character(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point, showing the
        character @-symbol in that spot.

        """
        mapstr = self.map.get_map_display(coord, dist=1, character='@')
        maplst = self.map.get_map_display(coord, dist=1, return_str=False, character='@')
        self.assertEqual(expectstr, mapstr)
        self.assertEqual(expectlst, maplst[::-1])  # flip y-axis to match print direction


class TestMap2(TestCase):
    """
    Test with Map2 - a bigger map with some links crossing nodes.

    """
    def setUp(self):
        self.map = mapsystem.Map({"map": MAP2})

    def test_str_output(self):
        """Check the display_map"""
        # strip the leftover spaces on the right to better
        # work with text editor stripping this automatically ...
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(stripped_map, MAP2_DISPLAY)

    def test_node_from_coord(self):
        for mapnode in self.map.node_index_map.values():
            node = self.map.get_node_from_coord(mapnode.X, mapnode.Y)
            self.assertEqual(node, mapnode)
            self.assertEqual(node.x // 2, node.X)
            self.assertEqual(node.y // 2, node.Y)

    @parameterized.expand([
        ((1, 0), (4, 0), ('e', 'e', 'e')),  # straight path
        ((1, 0), (5, 1), ('n', 'e', 'e', 'e')),  # shortcut over long link
        ((2, 2), (2, 5), ('n', 'n')),  # shortcut over long link (vertical)
        ((4, 4), (0, 5), ('w', 'n', 'w', 'w')),  # shortcut over long link (vertical)
        ((4, 0), (0, 5), ('n', 'w', 'n', 'n', 'n', 'w', 'w')),  # across entire grid
        ((4, 0), (0, 5), ('n', 'w', 'n', 'n', 'n', 'w', 'w')),  # across entire grid
        ((5, 3), (0, 3), ('s', 'w', 'w', 'w', 'w', 'n')),  # down and back
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand([
        ((1, 0), '#-#-#-#\n|   |  \n#-#-#--\n  |    \n  @-#-#'),
        ((2, 2), '    #---#\n    |   |\n#   |   #\n|   |    \n#-#-@-#--\n|   '
                 '|    \n#-#-#---#\n  |     |\n  #-#-#-#'),
        ((4, 5), '#-#-@  \n|   |  \n#---#  \n|   |  \n|   #-#'),
        ((5, 2), '--#  \n  |  \n  #-#\n    |\n#---@\n     \n--#-#\n  |  \n#-#  '),
    ])
    def test_get_map_display__character(self, coord, expected):
        """
        Test showing smaller part of grid, showing @-character in the middle.

        """
        mapstr = self.map.get_map_display(coord, dist=4, character='@')
        self.assertEqual(expected, mapstr)

    def test_extended_path_tracking__horizontal(self):
        node = self.map.get_node_from_coord(4, 1)
        self.assertEqual(
            node.xy_steps_in_direction,
            {'e': ['e'],
             's': ['s'],
             'w': ['w', 'w', 'w']}
        )

    def test_extended_path_tracking__vertical(self):
        node = self.map.get_node_from_coord(2, 2)
        self.assertEqual(
            node.xy_steps_in_direction,
            {'n': ['n', 'n', 'n'],
             'e': ['e'],
             's': ['s'],
             'w': ['w']}
        )

