"""

Tests for the Mapsystem

"""

from time import time
from random import randint
from unittest import TestCase
from parameterized import parameterized
from . import map_single

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

MAP3 = r"""

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

MAP3_DISPLAY = r"""
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

MAP4 = r"""

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

MAP4_DISPLAY = r"""
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

MAP5 = r"""

+ 0 1 2

2 #-#
  | |
1 #>#

0 #>#

+ 0 1 2

"""

MAP5_DISPLAY = r"""
#-#
| |
#>#

#>#
""".strip()

MAP6 = r"""

 + 0 1 2 3 4

 4 #-#-#-#
     ^   |
 3   |   #>#
     |   | |
 2   #-#-#-#
     ^   v
 1   #---#-#
     |   | |
 0 #-#>#-#<#

 + 0 1 2 3 4

"""

MAP6_DISPLAY = r"""
#-#-#-#
  ^   |
  |   #>#
  |   | |
  #-#-#-#
  ^   v
  #---#-#
  |   | |
#-#>#-#<#
""".strip()


MAP7 = r"""
+ 0 1 2

2 #-#
    |
1 #-o-#
    |
0   #-#

+ 0 1 2

"""

MAP7_DISPLAY = r"""
#-#
  |
#-o-#
  |
  #-#
""".strip()


MAP8 = r"""
+ 0 1 2 3 4 5

4 #-#-o o o-o
  |  \|/| | |
3 #-o-o-# o-#
  |  /|\    |
2 o-o-#-#   o
    | |    /
1   #-o-#-o-#
      |  /
0 #---#-o

+ 0 1 2 3 4 5

"""

MAP8_DISPLAY = r"""
#-#-o o o-o
|  \|/| | |
#-o-o-# o-#
|  /|\    |
o-o-#-#   o
  | |    /
  #-o-#-o-#
    |  /
#---#-o
""".strip()


MAP9 = r"""
+ 0 1 2 3

3 #-#-#-#
    d d d
2   | | |
    u u u
1 #-# #-#
  u   d
0 #d# #u#

+ 0 1 2 3

"""

MAP9_DISPLAY = r"""
#-#-#-#
  d d d
  | | |
  u u u
#-# #-#
u   d
#d# #u#
""".strip()


MAP10 = r"""

 + 0 1 2 3

 4 #---#-#
      b  |
 3 #i#---#
   |/|
 2 # #-I-#
     |
 1 #-#b#-#
   | |   b
 0 #b#-#-#

 + 0 1 2 3

"""

# note that I,i,b are invisible
MAP10_DISPLAY = r"""
#---#-#
   /  |
#-#---#
|/|
# #-#-#
  |
#-#-#-#
| |   |
#-#-#-#
""".strip()


MAP11 = r"""

+ 0 1 2 3

2 #-#
   \
1   t t
       \
0     #-#

+ 0 1 2 3

"""


MAP11_DISPLAY = r"""
#-#
 \

     \
    #-#
""".strip()


class TestMap1(TestCase):
    """
    Test the Map class with a simple 4-node map

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP1}, name="testmap")

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
             "<LinkNode '-' XY=(0.5,0)>",
             str(self.map.node_index_map[1]),
             "<LinkNode '|' XY=(1,0.5)>",
             str(self.map.node_index_map[3])]
        )

    @parameterized.expand([
        ((0, 0), "| \n#-", [["|", " "], ["#", "-"]]),
        ((1, 0), " |\n-#", [[" ", "|"], ["-", "#"]]),
        ((0, 1), "#-\n| ", [["#", "-"], ["|", " "]]),
        ((1, 1), "-#\n |", [["-", "#"], [" ", "|"]]),

    ])
    def test_get_visual_range__scan(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point.

        """
        mapstr = self.map.get_visual_range(coord, dist=1, mode='scan', character=None)
        maplst = self.map.get_visual_range(coord, dist=1, mode='scan', return_str=False,
                                           character=None)
        self.assertEqual(expectstr, mapstr)
        self.assertEqual(expectlst, maplst[::-1])

    @parameterized.expand([
        ((0, 0), "| \n@-", [["|", " "], ["@", "-"]]),
        ((1, 0), " |\n-@", [[" ", "|"], ["-", "@"]]),
        ((0, 1), "@-\n| ", [["@", "-"], ["|", " "]]),
        ((1, 1), "-@\n |", [["-", "@"], [" ", "|"]]),

    ])
    def test_get_visual_range__scan__character(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point, showing the
        character @-symbol in that spot.

        """
        mapstr = self.map.get_visual_range(coord, dist=1, mode='scan', character='@')
        maplst = self.map.get_visual_range(coord, dist=1, mode='scan', return_str=False,
                                           character='@')
        self.assertEqual(expectstr, mapstr)
        self.assertEqual(expectlst, maplst[::-1])  # flip y-axis to match print direction

    @parameterized.expand([
        ((0, 0), 1, '#  \n|  \n@-#'),
        ((0, 1), 1, '@-#\n|  \n#  '),
        ((1, 0), 1, '  #\n  |\n#-@'),
        ((1, 1), 1, '#-@\n  |\n  #'),
        ((0, 0), 2, '#-#\n| |\n@-#'),

    ])
    def test_get_visual_range__nodes__character(self, coord, dist, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes', character='@')
        self.assertEqual(expected, mapstr)

class TestMap2(TestCase):
    """
    Test with Map2 - a bigger map with multi-step links

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP2}, name="testmap")

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
    def test_get_visual_range__scan__character(self, coord, expected):
        """
        Test showing smaller part of grid, showing @-character in the middle.

        """
        mapstr = self.map.get_visual_range(coord, dist=4, mode='scan', character='@')
        self.assertEqual(expected, mapstr)

    def test_extended_path_tracking__horizontal(self):
        """
        Crossing multi-gridpoint links should be tracked properly.

        """
        node = self.map.get_node_from_coord((4, 1))
        self.assertEqual(
            {direction: [step.symbol for step in steps]
             for direction, steps in node.xy_steps_to_node.items()},
            {'e': ['-'],
             's': ['|'],
             'w': ['-', '-', '-']}
        )

    def test_extended_path_tracking__vertical(self):
        """
        Testing multi-gridpoint links in the vertical direction.

        """
        node = self.map.get_node_from_coord((2, 2))
        self.assertEqual(
            {direction: [step.symbol for step in steps]
             for direction, steps in node.xy_steps_to_node.items()},
            {'n': ['|', '|', '|'],
             'e': ['-'],
             's': ['|'],
             'w': ['-']}
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
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes', character='@',
                                           max_size=max_size)
        self.assertEqual(expected, mapstr)


class TestMap3(TestCase):
    """
    Test Map3 - Map with diagonal links

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP3}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP3_DISPLAY, stripped_map)

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
            '      #  \n     /   \n  # /    \n  |/     \n  #     #\n  |\\   / \n  # @-#  \n  '
            '|/   \\ \n  #     #\n / \\     \n#   #    '),
        ((5, 2), 2, None, '  #  \n  |  \n  #  \n / \\ \n#   @\n \\ / \n  #  \n  |  \n  #  ')
    ])
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes', character='@',
                                           max_size=max_size)
        self.assertEqual(expected, mapstr)

class TestMap4(TestCase):
    """
    Test Map4 - Map with + and x crossing links

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP4}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP4_DISPLAY, stripped_map)

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


class TestMap5(TestCase):
    """
    Test Map5 - Small map with one-way links

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP5}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP5_DISPLAY, stripped_map)

    @parameterized.expand([
        ((0, 0), (1, 0), ('e',)),  # cross one-way
        ((1, 0), (0, 0), ()),  # blocked
        ((0, 1), (1, 1), ('e',)),  # should still take shortest
        ((1, 1), (0, 1), ('n', 'w', 's')),  # take long way around
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))


class TestMap6(TestCase):
    """
    Test Map6 - Bigger map with one-way links in different directions

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP6}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP6_DISPLAY, stripped_map)

    @parameterized.expand([
        ((0, 0), (2, 0), ('e', 'e')),  # cross one-way
        ((2, 0), (0, 0), ('e', 'n', 'w', 's', 'w')),  # blocked, long way around
        ((4, 0), (3, 0), ('w',)),
        ((3, 0), (4, 0), ('n', 'e', 's')),
        ((1, 1), (1, 2), ('n',)),
        ((1, 2), (1, 1), ('e', 'e', 's', 'w')),
        ((3, 1), (1, 4), ('w', 'n', 'n')),
        ((0, 4), (0, 0), ('e', 'e', 'e', 's', 's', 's', 'w', 's', 'w')),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))


class TestMap7(TestCase):
    """
    Test Map7 - Small test of dynamic link node

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP7}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP7_DISPLAY, stripped_map)

    @parameterized.expand([
        ((1, 0), (1, 2), ('n', )),
        ((1, 2), (1, 0), ('s', )),
        ((0, 1), (2, 1), ('e', )),
        ((2, 1), (0, 1), ('w', )),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))


class TestMap8(TestCase):
    """
    Test Map8 - Small test of dynamic link node

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP8}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP8_DISPLAY, stripped_map)

    @parameterized.expand([
        ((2, 0), (2, 2), ('n',)),
        ((0, 0), (5, 3), ('e', 'e')),
        ((5, 1), (0, 3), ('w', 'w', 'n', 'w')),
        ((1, 1), (2, 2), ('n', 'w', 's')),
        ((5, 3), (5, 3), ()),
        ((5, 3), (0, 4), ('s', 'n', 'w', 'n')),
        ((1, 4), (3, 3), ('e', 'w', 'e')),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand([
        ((2, 2), 1, None, '  #-o  \n    |  \n#   o  \n|   |  \no-o-@-#\n    '
         '|  \n    o  \n    |  \n    #  '),
    ])
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes', character='@',
                                           max_size=max_size)
        self.assertEqual(expected, mapstr)

    @parameterized.expand([
        ((2, 2), (3, 2), 1, None, '  #-o  \n    |  \n#   o  \n|   |  \no-o-@.#\n    |  \n    o  '
            '\n    |  \n    #  '),
        ((2, 2), (5, 3), 1, None, '  #-o  \n    |  \n#   o  \n|   |  \no-o-@-#\n    .  \n    .  '
            '\n    .  \n    #  '),
        ((2, 2), (5, 3), 2, None, '#-#-o      \n|  \\|      \n#-o-o-#   #\n|   |\\    .\no-o-@-'
            '#   .\n    .    . \n    .   .  \n    .  .   \n#---...    '),
        ((5, 3), (2, 2), 2, (13, 7), '    o-o\n    | |\n    o-@\n      .\n#     .\n.    . '),
        ((5, 3), (1, 1), 2, None, '        o-o\n        | |\n        o-@\n          .\n    '
            '#     .\n    .    . \n    .   .  \n    .  .   \n#---...    ')
    ])
    def test_get_visual_range_with_path(self, coord, target, dist, max_size, expected):
        """
        Get visual range with a path-to-target marked.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes',
                                           target=target, target_path_style=".",
                                           character='@',
                                           max_size=max_size)
        self.assertEqual(expected, mapstr)


class TestMap9(TestCase):
    """
    Test Map9 - a map with up/down links.

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP9}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP9_DISPLAY, stripped_map)

    @parameterized.expand([
        ((0, 0), (0, 1), ('u',)),
        ((0, 0), (1, 0), ('d',)),
        ((1, 0), (2, 1), ('d', 'u', 'e', 'u', 'e', 'd')),
        ((2, 1), (0, 1), ('u', 'w', 'd', 'w')),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))


class TestMap10(TestCase):
    """
    Test Map10 - a map with blocked- and interrupt links/nodes. These are
    'invisible' nodes and won't show up in the map display.

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP10}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP10_DISPLAY, stripped_map)

    @parameterized.expand([
        ((0, 0), (1, 0), ('n', 'e', 's')),
        ((3, 0), (3, 1), ()),  # the blockage hinders this
        ((1, 3), (0, 4), ('e', 'n', 'w', 'w')),
        ((0, 1), (3, 2), ('e', 'n', 'e')),  # path interrupted by I node
        ((0, 1), (0, 3), ('e', 'n', 'n')),  # path interrupted by i link
        ((1, 3), (0, 3), ()),
        ((3, 2), (2, 2), ('w',)),
        ((3, 2), (1, 2), ('w',)),
        ((3, 3), (0, 3), ('w',)),
        ((2, 2), (3, 2), ('e',)),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand([
        ((2, 2), (3, 2), ('e', ), ((2, 2), (2.5, 2), (3, 2))),
        ((3, 3), (0, 3), ('w', ), ((3, 3), (2.5, 3.0), (2.0, 3.0), (1.5, 3.0), (1, 3))),
    ])
    def test_paths(self, startcoord, endcoord, expected_directions, expected_path):
        """
        Test path locations.

        """
        directions, path = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))
        strpositions = [(step.X, step.Y) for step in path]
        self.assertEqual(expected_path, tuple(strpositions))


class TestMap11(TestCase):
    """
    Test Map11 - a map teleporter links.

    """
    def setUp(self):
        self.map = map_single.SingleMap({"map": MAP11}, name="testmap")

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split('\n'))
        self.assertEqual(MAP11_DISPLAY, stripped_map)

    @parameterized.expand([
        ((2, 0), (1, 2), ('e', 'nw', 'e')),
        ((1, 2), (2, 0), ('w', 'se', 'w')),
    ])
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand([
        ((3, 0), (0, 2), ('nw', ),
         ((3, 0), (2.5, 0.5), (2.0, 1.0), (1.0, 1.0), (0.5, 1.5), (0, 2))),
        ((0, 2), (3, 0), ('se', ),
         ((0, 2), (0.5, 1.5), (1.0, 1.0), (2.0, 1.0), (2.5, 0.5), (3, 0))),
    ])
    def test_paths(self, startcoord, endcoord, expected_directions, expected_path):
        """
        Test path locations.

        """
        directions, path = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))
        strpositions = [(step.X, step.Y) for step in path]
        self.assertEqual(expected_path, tuple(strpositions))

    @parameterized.expand([
        ((2, 0), (1, 2), 3, None, '..#    \n .     \n  . .  \n     . \n    @..'),
        ((1, 2), (2, 0), 3, None, '..@    \n .     \n  . .  \n     . \n    #..'),

    ])
    def test_get_visual_range_with_path(self, coord, target, dist, max_size, expected):
        """
        Get visual range with a path-to-target marked.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode='nodes',
                                           target=target, target_path_style=".",
                                           character='@',
                                           max_size=max_size)
        self.assertEqual(expected, mapstr)


class TestMapStressTest(TestCase):
    """
    Performance test of map patfinder and visualizer.

    #-#-#-#-#....
    |x|x|x|x|
    #-#-#-#-#
    |x|x|x|x|
    #-#-#-#-#
    |x|x|x|x|
    #-#-#-#-#
    ...

    This should be a good stress-testing scenario because most each internal node has a maxiumum
    number of connections and options to consider.

    """

    def _get_grid(self, Xsize, Ysize):
        edge = f"+ {' ' * Xsize * 2}"
        l1 = f"\n  {'#-' * Xsize}#"
        l2 = f"\n  {'|x' * Xsize}|"

        return f"{edge}\n{(l1 + l2) * Ysize}{l1}\n\n{edge}"

    @parameterized.expand([
        ((10, 10), 0.01),
        ((100, 100), 1),
    ])
    def test_grid_creation(self, gridsize, max_time):
        """
        Test of grid-creataion performance for Nx, Ny grid.

        """
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        # print(f"\n\n{grid}\n")
        t0 = time()
        map_single.SingleMap({'map': grid}, name="testmap")
        t1 = time()
        self.assertLess(t1 - t0, max_time, f"Map creation of ({Xmax}x{Ymax}) grid slower "
                        f"than expected {max_time}s.")

    @parameterized.expand([
        ((10, 10), 10**-3),
        ((20, 20), 10**-3),
    ])
    def test_grid_pathfind(self, gridsize, max_time):
        """
        Test pathfinding performance for Nx, Ny grid.

        """
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        mapobj = map_single.SingleMap({'map': grid}, name="testmap")

        t0 = time()
        mapobj._calculate_path_matrix()
        t1 = time()
        # print(f"pathfinder matrix for grid {Xmax}x{Ymax}: {t1 - t0}s")

        # get the maximum distance and 9 other random points in the grid
        start_end_points = [((0, 0), (Xmax-1, Ymax-1))]
        for _ in range(9):
            start_end_points.append(((randint(0, Xmax), randint(0, Ymax)),
                                     (randint(0, Xmax), randint(0, Ymax))))

        t0 = time()
        for startcoord, endcoord in start_end_points:
            mapobj.get_shortest_path(startcoord, endcoord)
        t1 = time()
        self.assertLess((t1 - t0) / 10, max_time, f"Pathfinding for ({Xmax}x{Ymax}) grid slower "
                        f"than expected {max_time}s.")

    @parameterized.expand([
        ((10, 10), 4, 0.01),
        ((20, 20), 4, 0.01),
    ])
    def test_grid_visibility(self, gridsize, dist, max_time):
        """
        Test grid visualization performance for Nx, Ny grid for
        different visibility distances.

        """
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        mapobj = map_single.SingleMap({'map': grid}, name="testmap")

        t0 = time()
        mapobj._calculate_path_matrix()
        t1 = time()
        # print(f"pathfinder matrix for grid {Xmax}x{Ymax}: {t1 - t0}s")

        # get random center points in grid and a range of targets to visualize the
        # path to
        start_end_points = [((0, 0), (Xmax-1, Ymax-1))]  # include max distance
        for _ in range(9):
            start_end_points.append(((randint(0, Xmax), randint(0, Ymax)),
                                    (randint(0, Xmax), randint(0, Ymax))))

        t0 = time()
        for coord, target in start_end_points:
            mapobj.get_visual_range(coord, dist=dist, mode='nodes',
                                    character='@', target=target)
        t1 = time()
        self.assertLess((t1 - t0) / 10, max_time,
                        f"Visual Range calculation for ({Xmax}x{Ymax}) grid "
                        f"slower than expected {max_time}s.")


