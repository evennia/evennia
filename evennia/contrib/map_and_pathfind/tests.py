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

MAP4 = r"""

 + 0 1

 1 #-#
   |\|
 0 #-#

 + 0 1

"""

MAP4 = r"""

   + 0 1 2 3 4 5

   5 #-#---#   #
       |  / \ /
   4   # /   #
       |/    |
   3   #     #
       |\   / \
   2   # #-#   #
       |/   \ /
   1   #     #
      / \    |
   0 #   #---#-#

   + 0 1 2 3 4 5

"""

MAP4_DISPLAY = r"""
#-#---#   #
  |  / \ /
  # /   #
  |/    |
  #     #
  |\   / \
  # #-#   #
  |/   \ /
  #     #
 / \    |
#   #---#-#
""".strip()

MAP5 = r"""

 + 0 1 2 3 4

 4 #-# #---#
      x   /
 3   #-#-#
     |x x|
 2 #-#-#-#
   | |   |
 1 #-+-#-+-#
     |   |
 0   #---#

 + 0 1 2 3 4

"""

MAP5_DISPLAY = r"""
#-# #---#
   x   /
  #-#-#
  |x x|
#-#-#-#
| |   |
#-+-#-+-#
  |   |
  #---#
""".strip()


class TestMap1(TestCase):
    """
    Test the Map class with a simple 4-node map

    """

    def setUp(self):
        self.map = mapsystem.Map({"map": MAP1})

    def test_str_output(self):
        """Check the display_map"""
        self.assertEqual(str(self.map).strip(), MAP1_DISPLAY)

    def test_node_from_coord(self):
        node = self.map.get_node_from_coord((1, 1))
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

    @parameterized.expand([
        ((0, 0), 1, '#  \n|  \n@-#'),
        ((0, 1), 1, '@-#\n|  \n#  '),
        ((1, 0), 1, '  #\n  |\n#-@'),
        ((1, 1), 1, '#-@\n  |\n  #'),
        ((0, 0), 2, ''),

    ])
    def test_get_map_display__nodes__character(self, coord, dist, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_map_display(coord, dist=dist, mode='nodes', character='@')
        self.assertEqual(expected, mapstr)

class TestMap2(TestCase):
    """
    Test with Map2 - a bigger map with multi-step links

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
            node = self.map.get_node_from_coord((mapnode.X, mapnode.Y))
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
    def test_get_map_display__scan__character(self, coord, expected):
        """
        Test showing smaller part of grid, showing @-character in the middle.

        """
        mapstr = self.map.get_map_display(coord, dist=4, character='@')
        self.assertEqual(expected, mapstr)

    def test_extended_path_tracking__horizontal(self):
        """
        Crossing multi-gridpoint links should be tracked properly.

        """
        node = self.map.get_node_from_coord((4, 1))
        self.assertEqual(
            node.xy_steps_in_direction,
            {'e': ['e'],
             's': ['s'],
             'w': ['w', 'w', 'w']}
        )

    def test_extended_path_tracking__vertical(self):
        """
        Testing multi-gridpoint links in the vertical direction.

        """
        node = self.map.get_node_from_coord((2, 2))
        self.assertEqual(
            node.xy_steps_in_direction,
            {'n': ['n', 'n', 'n'],
             'e': ['e'],
             's': ['s'],
             'w': ['w']}
        )

    @parameterized.expand([
        ((0, 0), 2, None, '@'),  # outside of any known node
        ((4, 5), 0, None, '@'),  # 0 distance
        ((1, 0), 2, None,
         '#-#-#  \n  |    \n  @-#-#'),
        ((0, 5), 1, None, '@-#'),
        ((0, 5), 4, None,
         '@-#-#-#-#\n    |    \n    #---#\n    |    \n    |    \n    |    \n    #    '),
        ((5, 1), 3, None, '  #      \n  |      \n#-#---#-@\n      |  \n    #-#  '),
        ((2, 2), 2, None,
         '    #      \n    |      \n    #---#  \n    |      \n    |      \n    |      \n'
         '#-#-@-#---#\n    |      \n  #-#---#  '),
        ((2, 2), 2, (5, 5),  # limit display size
         '  |  \n  |  \n#-@-#\n  |  \n#-#--'),
        ((2, 2), 4, (3, 3), ' | \n-@-\n | '),
        ((2, 2), 4, (1, 1), '@')
    ])
    def test_get_map_display__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_map_display(coord, dist=dist, mode='nodes', character='@',
                                          max_size=max_size)
        self.assertEqual(expected, mapstr)


class TestMap4(TestCase):
    """
    Test Map4 - Map with diaginal links

    """
    def setUp(self):
        self.map = mapsystem.Map({"map": MAP4})

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP4_DISPLAY, stripped_map)

    @parameterized.expand([
        ((0, 0), (1, 0), ()),  # no node at (1, 0)!
        ((2, 0), (5, 0), ('e', 'e')),  # straight path
        ((0, 0), (1, 1), ('ne', )),
        ((4, 1), (4, 3), ('nw', 'ne')),
        ((4, 1), (4, 3), ('nw', 'ne')),
        ((2, 2), (3, 5), ('nw', 'ne')),
        ((2, 2), (1, 5), ('nw', 'n', 'n')),
        ((5, 5), (0, 0), ('sw', 's', 'sw', 'w', 'sw', 'sw')),
        ((5, 5), (0, 0), ('sw', 's', 'sw', 'w', 'sw', 'sw')),
        ((5, 2), (1, 2), ('sw', 'nw', 'w', 'nw', 's')),
        ((4, 1), (1, 1), ('s', 'w', 'nw'))
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand([
        ((2, 2), 2, None,
         '      #  \n     /   \n  # /    \n  |/     \n  #     #\n   \\   / '
         '\n  # @-#  \n  |/   \\ \n  #     #\n / \\     \n#   #    '),
        ((5, 2), 2, None, '')
    ])
    def test_get_map_display__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_map_display(coord, dist=dist, mode='nodes', character='@',
                                          max_size=max_size)
        print(repr(mapstr))
        self.assertEqual(expected, mapstr)

class TestMap5(TestCase):
    """
    Test Map5 - Map with + and x crossing links

    """
    def setUp(self):
        self.map = mapsystem.Map({"map": MAP5})

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP5_DISPLAY, stripped_map)

    @parameterized.expand([
        ((1, 0), (1, 2), ('n',)),  # cross + vertically
        ((0, 1), (2, 1), ('e',)),  # cross + horizontally
        ((4, 1), (1, 0), ('w', 'w', 'n', 'e', 's')),
        ((1, 2), (2, 3), ('ne', )),  # cross x
        ((1, 2), (2, 3), ('ne', )),
        ((2, 2), (0, 4), ('w', 'ne', 'nw', 'w')),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))
