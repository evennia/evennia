"""

Tests for the XYZgrid system.

"""
from random import randint
from unittest import mock

from django.test import TestCase
from parameterized import parameterized

from evennia.utils.test_resources import BaseEvenniaTest

from . import xymap, xymap_legend, xyzgrid, xyzroom

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

MAP12a = r"""

+ 0 1

1 #-T
  |
0 #-#

+ 0 1

"""


MAP12b = r"""

+ 0 1

1 #-#
    |
0 T-#

+ 0 1

"""


class _MapTest(BaseEvenniaTest):
    """
    Parent for map tests

    """

    map_data = {"map": MAP1, "zcoord": "map1"}
    map_display = MAP1_DISPLAY

    def setUp(self):
        """Set up grid and map"""
        super().setUp()
        self.grid, err = xyzgrid.XYZGrid.create("testgrid")
        self.grid.add_maps(self.map_data)
        self.map = self.grid.get_map(self.map_data["zcoord"])

        # output to console
        # def _log(msg):
        #     print(msg)
        # self.grid.log = _log

    def tearDown(self):
        self.grid.delete()
        xyzroom.XYZRoom.objects.all().delete()
        xyzroom.XYZExit.objects.all().delete()


class TestMap1(_MapTest):
    """
    Test the Map class with a simple 4-node map

    """

    def test_str_output(self):
        """Check the display_map"""
        self.assertEqual(str(self.map).replace("||", "|").strip(), MAP1_DISPLAY)

    def test_node_from_coord(self):
        node = self.map.get_node_from_coord((1, 1))
        self.assertEqual(node.X, 1)
        self.assertEqual(node.x, 2)
        self.assertEqual(node.X, 1)
        self.assertEqual(node.y, 2)

    def test_get_shortest_path(self):
        directions, path = self.map.get_shortest_path((0, 0), (1, 1))
        self.assertEqual(directions, ["e", "n"])
        self.assertEqual(
            [str(node) for node in path],
            [
                str(self.map.node_index_map[0]),
                "<LinkNode '-' XY=(0.5,0)>",
                str(self.map.node_index_map[1]),
                "<LinkNode '|' XY=(1,0.5)>",
                str(self.map.node_index_map[3]),
            ],
        )

    @parameterized.expand(
        [
            ((0, 0), "| \n#-", [["|", " "], ["#", "-"]]),
            ((1, 0), " |\n-#", [[" ", "|"], ["-", "#"]]),
            ((0, 1), "#-\n| ", [["#", "-"], ["|", " "]]),
            ((1, 1), "-#\n |", [["-", "#"], [" ", "|"]]),
        ]
    )
    def test_get_visual_range__scan(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point.

        """
        mapstr = self.map.get_visual_range(coord, dist=1, mode="scan", character=None)
        maplst = self.map.get_visual_range(
            coord, dist=1, mode="scan", return_str=False, character=None
        )
        maplst = [[part.replace("||", "|") for part in partlst] for partlst in maplst]
        self.assertEqual(expectstr, mapstr.replace("||", "|"))
        self.assertEqual(expectlst, maplst[::-1])

    @parameterized.expand(
        [
            ((0, 0), "| \n@-", [["|", " "], ["@", "-"]]),
            ((1, 0), " |\n-@", [[" ", "|"], ["-", "@"]]),
            ((0, 1), "@-\n| ", [["@", "-"], ["|", " "]]),
            ((1, 1), "-@\n |", [["-", "@"], [" ", "|"]]),
        ]
    )
    def test_get_visual_range__scan__character(self, coord, expectstr, expectlst):
        """
        Test displaying a part of the map around a central point, showing the
        character @-symbol in that spot.

        """
        mapstr = self.map.get_visual_range(coord, dist=1, mode="scan", character="@")
        maplst = self.map.get_visual_range(
            coord, dist=1, mode="scan", return_str=False, character="@"
        )
        maplst = [[part.replace("||", "|") for part in partlst] for partlst in maplst]
        self.assertEqual(expectstr, mapstr.replace("||", "|"))
        self.assertEqual(expectlst, maplst[::-1])  # flip y-axis for print

    @parameterized.expand(
        [
            ((0, 0), 1, "#  \n|  \n@-#"),
            ((0, 1), 1, "@-#\n|  \n#  "),
            ((1, 0), 1, "  #\n  |\n#-@"),
            ((1, 1), 1, "#-@\n  |\n  #"),
            ((0, 0), 2, "#-#\n| |\n@-#"),
        ]
    )
    def test_get_visual_range__nodes__character(self, coord, dist, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(coord, dist=dist, mode="nodes", character="@")
        self.assertEqual(expected, mapstr.replace("||", "|"))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 4)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 8)


class TestMap2(_MapTest):
    """
    Test with Map2 - a bigger map with multi-step links

    """

    map_data = {"map": MAP2, "zcoord": "map2"}
    map_display = MAP2_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        # strip the leftover spaces on the right to better
        # work with text editor stripping this automatically ...
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(stripped_map.replace("||", "|"), MAP2_DISPLAY)

    def test_node_from_coord(self):
        for mapnode in self.map.node_index_map.values():
            node = self.map.get_node_from_coord((mapnode.X, mapnode.Y))
            self.assertEqual(node, mapnode)
            self.assertEqual(node.x // 2, node.X)
            self.assertEqual(node.y // 2, node.Y)

    @parameterized.expand(
        [
            ((1, 0), (4, 0), ("e", "e", "e")),  # straight path
            ((1, 0), (5, 1), ("n", "e", "e", "e")),  # shortcut over long link
            ((2, 2), (2, 5), ("n", "n")),  # shortcut over long link (vertical)
            ((4, 4), (0, 5), ("w", "n", "w", "w")),  # shortcut over long link (vertical)
            ((4, 0), (0, 5), ("n", "w", "n", "n", "n", "w", "w")),  # across entire grid
            ((4, 0), (0, 5), ("n", "w", "n", "n", "n", "w", "w")),  # across entire grid
            ((5, 3), (0, 3), ("s", "w", "w", "w", "w", "n")),  # down and back
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand(
        [
            ((1, 0), "#-#-#-#\n|   |  \n#-#-#--\n  |    \n  @-#-#"),
            (
                (2, 2),
                "    #---#\n    |   |\n#   |   #\n|   |    \n#-#-@-#--\n|   "
                "|    \n#-#-#---#\n  |     |\n  #-#-#-#",
            ),
            ((4, 5), "#-#-@  \n|   |  \n#---#  \n|   |  \n|   #-#"),
            ((5, 2), "--#  \n  |  \n  #-#\n    |\n#---@\n     \n--#-#\n  |  \n#-#  "),
        ]
    )
    def test_get_visual_range__scan__character(self, coord, expected):
        """
        Test showing smaller part of grid, showing @-character in the middle.

        """
        mapstr = self.map.get_visual_range(coord, dist=4, mode="scan", character="@")
        self.assertEqual(expected, mapstr.replace("||", "|"))

    def test_extended_path_tracking__horizontal(self):
        """
        Crossing multi-gridpoint links should be tracked properly.

        """
        node = self.map.get_node_from_coord((4, 1))
        self.assertEqual(
            {
                direction: [step.symbol for step in steps]
                for direction, steps in node.xy_steps_to_node.items()
            },
            {"e": ["-"], "s": ["|"], "w": ["-", "-", "-"]},
        )

    def test_extended_path_tracking__vertical(self):
        """
        Testing multi-gridpoint links in the vertical direction.

        """
        node = self.map.get_node_from_coord((2, 2))
        self.assertEqual(
            {
                direction: [step.symbol for step in steps]
                for direction, steps in node.xy_steps_to_node.items()
            },
            {"n": ["|", "|", "|"], "e": ["-"], "s": ["|"], "w": ["-"]},
        )

    @parameterized.expand(
        [
            ((0, 0), 2, None, "@"),  # outside of any known node
            ((4, 5), 0, None, "@"),  # 0 distance
            ((1, 0), 2, None, "#-#-#  \n  |    \n  @-#-#"),
            ((0, 5), 1, None, "@-#"),
            (
                (0, 5),
                4,
                None,
                "@-#-#-#-#\n    |    \n    #---#\n    |    \n    |    \n    |    \n    #    ",
            ),
            ((5, 1), 3, None, "  #      \n  |      \n#-#---#-@\n      |  \n    #-#  "),
            (
                (2, 2),
                2,
                None,
                "    #      \n    |      \n    #---#  \n    |      \n    |      \n    |      \n"
                "#-#-@-#---#\n    |      \n  #-#---#  ",
            ),
            ((2, 2), 2, (5, 5), "  |  \n  |  \n#-@-#\n  |  \n#-#--"),  # limit display size
            ((2, 2), 4, (3, 3), " | \n-@-\n | "),
            ((2, 2), 4, (1, 1), "@"),
        ]
    )
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(
            coord, dist=dist, mode="nodes", character="@", max_size=max_size
        )
        self.assertEqual(expected, mapstr.replace("||", "|"))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 24)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 54)


class TestMap3(_MapTest):
    """
    Test Map3 - Map with diagonal links

    """

    map_data = {"map": MAP3, "zcoord": "map3"}
    map_display = MAP3_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP3_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((0, 0), (1, 0), ()),  # no node at (1, 0)!
            ((2, 0), (5, 0), ("e", "e")),  # straight path
            ((0, 0), (1, 1), ("ne",)),
            ((4, 1), (4, 3), ("nw", "ne")),
            ((4, 1), (4, 3), ("nw", "ne")),
            ((2, 2), (3, 5), ("nw", "ne")),
            ((2, 2), (1, 5), ("nw", "n", "n")),
            ((5, 5), (0, 0), ("sw", "s", "sw", "w", "sw", "sw")),
            ((5, 5), (0, 0), ("sw", "s", "sw", "w", "sw", "sw")),
            ((5, 2), (1, 2), ("sw", "nw", "w", "nw", "s")),
            ((4, 1), (1, 1), ("s", "w", "nw")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand(
        [
            (
                (2, 2),
                2,
                None,
                "      #  \n     /   \n  # /    \n  |/     \n  #     #\n  |\\   / \n  # @-#  \n  "
                "|/   \\ \n  #     #\n / \\     \n#   #    ",
            ),
            ((5, 2), 2, None, "  #  \n  |  \n  #  \n / \\ \n#   @\n \\ / \n  #  \n  |  \n  #  "),
        ]
    )
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(
            coord, dist=dist, mode="nodes", character="@", max_size=max_size
        )
        self.assertEqual(expected, mapstr.replace("||", "|"))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 18)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 44)


class TestMap4(_MapTest):
    """
    Test Map4 - Map with + and x crossing links

    """

    map_data = {"map": MAP4, "zcoord": "map4"}
    map_display = MAP4_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP4_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((1, 0), (1, 2), ("n",)),  # cross + vertically
            ((0, 1), (2, 1), ("e",)),  # cross + horizontally
            ((4, 1), (1, 0), ("w", "w", "n", "e", "s")),
            ((1, 2), (2, 3), ("ne",)),  # cross x
            ((1, 2), (2, 3), ("ne",)),
            ((2, 2), (0, 4), ("w", "ne", "nw", "w")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 16)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 44)


class TestMap5(_MapTest):
    """
    Test Map5 - Small map with one-way links

    """

    map_data = {"map": MAP5, "zcoord": "map5"}
    map_display = MAP5_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP5_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((0, 0), (1, 0), ("e",)),  # cross one-way
            ((1, 0), (0, 0), ()),  # blocked
            ((0, 1), (1, 1), ("e",)),  # should still take shortest
            ((1, 1), (0, 1), ("n", "w", "s")),  # take long way around
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 6)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 8)


class TestMap6(_MapTest):
    """
    Test Map6 - Bigger map with one-way links in different directions

    """

    map_data = {"map": MAP6, "zcoord": "map6"}
    map_display = MAP6_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP6_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((0, 0), (2, 0), ("e", "e")),  # cross one-way
            ((2, 0), (0, 0), ("e", "n", "w", "s", "w")),  # blocked, long way around
            ((4, 0), (3, 0), ("w",)),
            ((3, 0), (4, 0), ("n", "e", "s")),
            ((1, 1), (1, 2), ("n",)),
            ((1, 2), (1, 1), ("e", "e", "s", "w")),
            ((3, 1), (1, 4), ("w", "n", "n")),
            ((0, 4), (0, 0), ("e", "e", "e", "s", "s", "s", "w", "s", "w")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        Test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 18)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 38)


class TestMap7(_MapTest):
    """
    Test Map7 - Small test of dynamic link node

    """

    map_data = {"map": MAP7, "zcoord": "map7"}
    map_display = MAP7_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP7_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((1, 0), (1, 2), ("n",)),
            ((1, 2), (1, 0), ("s",)),
            ((0, 1), (2, 1), ("e",)),
            ((2, 1), (0, 1), ("w",)),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 6)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 8)


class TestMap8(_MapTest):
    """
    Test Map8 - Small test of dynamic link node

    """

    map_data = {"map": MAP8, "zcoord": "map8"}
    map_display = MAP8_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP8_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((2, 0), (2, 2), ("n",)),
            ((0, 0), (5, 3), ("e", "e")),
            ((5, 1), (0, 3), ("w", "w", "n", "w")),
            ((1, 1), (2, 2), ("n", "w", "s")),
            ((5, 3), (5, 3), ()),
            ((5, 3), (0, 4), ("s", "n", "w", "n")),
            ((1, 4), (3, 3), ("e", "w", "e")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand(
        [
            (
                (2, 2),
                1,
                None,
                "  #-o  \n    |  \n#   o  \n|   |  \no-o-@-#\n    "
                "|  \n    o  \n    |  \n    #  ",
            ),
        ]
    )
    def test_get_visual_range__nodes__character(self, coord, dist, max_size, expected):
        """
        Get sub-part of map with node-mode.

        """
        mapstr = self.map.get_visual_range(
            coord, dist=dist, mode="nodes", character="@", max_size=max_size
        )
        self.assertEqual(expected, mapstr.replace("||", "|"))

    @parameterized.expand(
        [
            (
                (2, 2),
                (3, 2),
                1,
                None,
                "  #-o  \n    |  \n#   o  \n|   |  \no-o-@..\n    |  \n    o  "
                "\n    |  \n    #  ",
            ),
            (
                (2, 2),
                (5, 3),
                1,
                None,
                "  #-o  \n    |  \n#   o  \n|   |  \no-o-@-#\n    .  \n    .  "
                "\n    .  \n    ...",
            ),
            (
                (2, 2),
                (5, 3),
                2,
                None,
                "#-#-o      \n|  \\|      \n#-o-o-#   .\n|   |\\    .\no-o-@-"
                "#   .\n    .    . \n    .   .  \n    .  .   \n#---...    ",
            ),
            ((5, 3), (2, 2), 2, (13, 7), "    o-o\n    | |\n    o-@\n      .\n.     .\n.    . "),
            (
                (5, 3),
                (1, 1),
                2,
                None,
                "        o-o\n        | |\n        o-@\n.         .\n.....     "
                ".\n    .    . \n    .   .  \n    .  .   \n#---...    ",
            ),
        ]
    )
    def test_get_visual_range_with_path(self, coord, target, dist, max_size, expected):
        """
        Get visual range with a path-to-target marked.

        """
        mapstr = self.map.get_visual_range(
            coord,
            dist=dist,
            mode="nodes",
            target=target,
            target_path_style=".",
            character="@",
            max_size=max_size,
        )
        self.assertEqual(expected, mapstr.replace("||", "|"))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 12)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 28)


class TestMap9(_MapTest):
    """
    Test Map9 - a map with up/down links.

    """

    map_data = {"map": MAP9, "zcoord": "map9"}
    map_display = MAP9_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP9_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((0, 0), (0, 1), ("u",)),
            ((0, 0), (1, 0), ("d",)),
            ((1, 0), (2, 1), ("d", "u", "e", "u", "e", "d")),
            ((2, 1), (0, 1), ("u", "w", "d", "w")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 12)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 24)


class TestMap10(_MapTest):
    """
    Test Map10 - a map with blocked- and interrupt links/nodes. These are
    'invisible' nodes and won't show up in the map display.

    """

    map_data = {"map": MAP10, "zcoord": "map10"}
    map_display = MAP10_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP10_DISPLAY, stripped_map.replace("||", "|"))

    # interrupts are only relevant to the auto-stepper
    @parameterized.expand(
        [
            ((0, 0), (1, 0), ("n", "e", "s")),
            ((3, 0), (3, 1), ()),  # the blockage hinders this
            ((1, 3), (0, 4), ("e", "n", "w", "w")),
            ((0, 1), (3, 2), ("e", "n", "e", "e")),
            ((0, 1), (0, 3), ("e", "n", "n", "w")),
            ((1, 3), (0, 3), ("w",)),
            ((3, 2), (2, 2), ("w",)),
            ((3, 2), (1, 2), ("w", "w")),
            ((3, 3), (0, 3), ("w", "w")),
            ((2, 2), (3, 2), ("e",)),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand(
        [
            ((2, 2), (3, 2), ("e",), ((2, 2), (2.5, 2), (3, 2))),
            (
                (3, 3),
                (0, 3),
                ("w", "w"),
                ((3, 3), (2.5, 3.0), (2.0, 3.0), (1.5, 3.0), (1, 3), (0.5, 3), (0, 3)),
            ),
        ]
    )
    def test_paths(self, startcoord, endcoord, expected_directions, expected_path):
        """
        Test path locations.

        """
        directions, path = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))
        strpositions = [(step.X, step.Y) for step in path]
        self.assertEqual(expected_path, tuple(strpositions))

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 18)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 42)


class TestMap11(_MapTest):
    """
    Test Map11 - a map teleporter links.

    """

    map_data = {"map": MAP11, "zcoord": "map11"}
    map_display = MAP11_DISPLAY

    def test_str_output(self):
        """Check the display_map"""
        stripped_map = "\n".join(line.rstrip() for line in str(self.map).split("\n"))
        self.assertEqual(MAP11_DISPLAY, stripped_map.replace("||", "|"))

    @parameterized.expand(
        [
            ((2, 0), (1, 2), ("e", "nw", "e")),
            ((1, 2), (2, 0), ("w", "se", "w")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    @parameterized.expand(
        [
            (
                (3, 0),
                (0, 2),
                ("nw",),
                ((3, 0), (2.5, 0.5), (2.0, 1.0), (1.0, 1.0), (0.5, 1.5), (0, 2)),
            ),
            (
                (0, 2),
                (3, 0),
                ("se",),
                ((0, 2), (0.5, 1.5), (1.0, 1.0), (2.0, 1.0), (2.5, 0.5), (3, 0)),
            ),
        ]
    )
    def test_paths(self, startcoord, endcoord, expected_directions, expected_path):
        """
        Test path locations.

        """
        directions, path = self.map.get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))
        strpositions = [(step.X, step.Y) for step in path]
        self.assertEqual(expected_path, tuple(strpositions))

    @parameterized.expand(
        [
            ((2, 0), (1, 2), 3, None, "...    \n .     \n  . .  \n     . \n    @.."),
            ((1, 2), (2, 0), 3, None, "..@    \n .     \n  . .  \n     . \n    ..."),
        ]
    )
    def test_get_visual_range_with_path(self, coord, target, dist, max_size, expected):
        """
        Get visual range with a path-to-target marked.

        """
        mapstr = self.map.get_visual_range(
            coord,
            dist=dist,
            mode="nodes",
            target=target,
            target_path_style=".",
            character="@",
            max_size=max_size,
        )

        self.assertEqual(expected, mapstr)

    def test_spawn(self):
        """
        Spawn the map into actual objects.

        """
        self.grid.spawn()
        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 4)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 6)


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

    @parameterized.expand(
        [
            ((10, 10), 0.03),
            ((100, 100), 5),
        ]
    )
    def test_grid_creation(self, gridsize, max_time):
        """
        Test of grid-creataion performance for Nx, Ny grid.

        """
        # import cProfile
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        mapobj = xymap.XYMap({"map": grid}, Z="testmap")
        # t0 = time()
        mapobj.parse()
        # cProfile.runctx('mapobj.parse()', globals(), locals())
        # t1 = time()
        # if (t1 - t0 > max_time):
        #     print(f"Map creation of ({Xmax}x{Ymax}) grid slower "
        #           f"than expected {max_time}s.")

    @parameterized.expand(
        [
            ((10, 10), 10**-3),
            ((20, 20), 10**-3),
        ]
    )
    def test_grid_pathfind(self, gridsize, max_time):
        """
        Test pathfinding performance for Nx, Ny grid.

        """
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        mapobj = xymap.XYMap({"map": grid}, Z="testmap")
        mapobj.parse()

        # t0 = time()
        mapobj.calculate_path_matrix()
        # t1 = time()
        # print(f"pathfinder matrix for grid {Xmax}x{Ymax}: {t1 - t0}s")

        # get the maximum distance and 9 other random points in the grid
        start_end_points = [((0, 0), (Xmax - 1, Ymax - 1))]
        for _ in range(9):
            start_end_points.append(
                ((randint(0, Xmax), randint(0, Ymax)), (randint(0, Xmax), randint(0, Ymax)))
            )

        # t0 = time()
        for startcoord, endcoord in start_end_points:
            mapobj.get_shortest_path(startcoord, endcoord)
        # t1 = time()
        # if (t1 - t0) / 10 > max_time:
        #     print(f"Pathfinding for ({Xmax}x{Ymax}) grid slower "
        #           f"than expected {max_time}s.")

    @parameterized.expand(
        [
            ((10, 10), 4, 0.01),
            ((20, 20), 4, 0.01),
        ]
    )
    def test_grid_visibility(self, gridsize, dist, max_time):
        """
        Test grid visualization performance for Nx, Ny grid for
        different visibility distances.

        """
        Xmax, Ymax = gridsize
        grid = self._get_grid(Xmax, Ymax)
        mapobj = xymap.XYMap({"map": grid}, Z="testmap")
        mapobj.parse()

        # t0 = time()
        mapobj.calculate_path_matrix()
        # t1 = time()
        # print(f"pathfinder matrix for grid {Xmax}x{Ymax}: {t1 - t0}s")

        # get random center points in grid and a range of targets to visualize the
        # path to
        start_end_points = [((0, 0), (Xmax - 1, Ymax - 1))]  # include max distance
        for _ in range(9):
            start_end_points.append(
                ((randint(0, Xmax), randint(0, Ymax)), (randint(0, Xmax), randint(0, Ymax)))
            )

        # t0 = time()
        for coord, target in start_end_points:
            mapobj.get_visual_range(coord, dist=dist, mode="nodes", character="@", target=target)
        # t1 = time()
        # if (t1 - t0) / 10 > max_time:
        #     print(f"Visual Range calculation for ({Xmax}x{Ymax}) grid "
        #           f"slower than expected {max_time}s.")


class TestXYZGrid(BaseEvenniaTest):
    """
    Test base grid class with a single map, including spawning objects.

    """

    zcoord = "map1"

    def setUp(self):
        self.grid, err = xyzgrid.XYZGrid.create("testgrid")

        self.map_data1 = {"map": MAP1, "zcoord": self.zcoord}

        self.grid.add_maps(self.map_data1)

    def tearDown(self):
        self.grid.delete()

    def test_str_output(self):
        """Check the display_map"""
        xymap = self.grid.get_map(self.zcoord)
        stripped_map = "\n".join(line.rstrip() for line in str(xymap).split("\n"))
        self.assertEqual(MAP1_DISPLAY, stripped_map.replace("||", "|"))

    def test_spawn(self):
        """Spawn objects for the grid"""
        self.grid.spawn()
        # import sys
        # sys.stderr.write("\nrooms: " + repr(xyzroom.XYZRoom.objects.all()))
        # sys.stderr.write("\n\nexits: " + repr(xyzroom.XYZExit.objects.all()) + "\n")

        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 4)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 8)


# map transitions
class Map12aTransition(xymap_legend.TransitionMapNode):
    symbol = "T"
    target_map_xyz = (1, 0, "map12b")


class Map12bTransition(xymap_legend.TransitionMapNode):
    symbol = "T"
    target_map_xyz = (0, 1, "map12a")


class TestXYZGridTransition(BaseEvenniaTest):
    """
    Test the XYZGrid class and transitions between maps.

    """

    def setUp(self):
        super().setUp()
        self.grid, err = xyzgrid.XYZGrid.create("testgrid")

        self.map_data12a = {"map": MAP12a, "zcoord": "map12a", "legend": {"T": Map12aTransition}}
        self.map_data12b = {"map": MAP12b, "zcoord": "map12b", "legend": {"T": Map12bTransition}}

        self.grid.add_maps(self.map_data12a, self.map_data12b)

    def tearDown(self):
        self.grid.delete()

    @parameterized.expand(
        [
            ((1, 0), (1, 1), ("w", "n", "e")),
            ((1, 1), (1, 0), ("w", "s", "e")),
        ]
    )
    def test_shortest_path(self, startcoord, endcoord, expected_directions):
        """
        test shortest-path calculations throughout the grid.

        """
        directions, _ = self.grid.get_map("map12a").get_shortest_path(startcoord, endcoord)
        self.assertEqual(expected_directions, tuple(directions))

    def test_spawn(self):
        """
        Spawn the two maps into actual objects.

        """
        self.grid.spawn()

        self.assertEqual(xyzroom.XYZRoom.objects.all().count(), 6)
        self.assertEqual(xyzroom.XYZExit.objects.all().count(), 10)

        room1 = xyzroom.XYZRoom.objects.get_xyz(xyz=(0, 1, "map12a"))
        room2 = xyzroom.XYZRoom.objects.get_xyz(xyz=(1, 0, "map12b"))
        east_exit = [exi for exi in room1.exits if exi.db_key == "east"][0]
        west_exit = [exi for exi in room2.exits if exi.db_key == "west"][0]

        # make sure exits traverse the maps
        self.assertEqual(east_exit.db_destination, room2)
        self.assertEqual(west_exit.db_destination, room1)


class TestBuildExampleGrid(BaseEvenniaTest):
    """
    Test building the map-example (this takes about 30s)

    """

    def setUp(self):
        # build and populate grid
        super().setUp()
        self.grid, err = xyzgrid.XYZGrid.create("testgrid")

        # def _log(msg):
        #     print(msg)
        # self.grid.log = _log

    def tearDown(self):
        self.grid.delete()

    def test_build(self):
        """
        Build the map example.

        """
        mapdatas = self.grid.maps_from_module("evennia.contrib.grid.xyzgrid.example")
        self.assertEqual(len(mapdatas), 2)

        self.grid.add_maps(*mapdatas)
        self.grid.spawn()

        # testing
        room1a = xyzroom.XYZRoom.objects.get_xyz(xyz=(3, 0, "the large tree"))
        room1b = xyzroom.XYZRoom.objects.get_xyz(xyz=(10, 8, "the large tree"))
        room2a = xyzroom.XYZRoom.objects.get_xyz(xyz=(1, 0, "the small cave"))
        room2b = xyzroom.XYZRoom.objects.get_xyz(xyz=(1, 3, "the small cave"))

        self.assertEqual(room1a.key, "Dungeon Entrance")
        self.assertTrue(room1a.db.desc.startswith("To the east"))
        self.assertEqual(room1b.key, "A gorgeous view")
        self.assertTrue(room1b.db.desc.startswith("The view from here is breathtaking,"))
        self.assertEqual(room2a.key, "The entrance")
        self.assertTrue(room2a.db.desc.startswith("This is the entrance to"))
        self.assertEqual(room2b.key, "North-west corner of the atrium")
        self.assertTrue(room2b.db.desc.startswith("Sunlight sifts down"))


mock_room_callbacks = mock.MagicMock()
mock_exit_callbacks = mock.MagicMock()


class TestXyzRoom(xyzroom.XYZRoom):
    def at_object_creation(self):
        mock_room_callbacks.at_object_creation()


class TestXyzExit(xyzroom.XYZExit):
    def at_object_creation(self):
        mock_exit_callbacks.at_object_creation()


MAP_DATA = {
    "map": """

    + 0 1

    0 #-#

    + 0 1

  """,
    "zcoord": "map1",
    "prototypes": {
        ("*", "*"): {
            "key": "room",
            "desc": "A room.",
            "prototype_parent": "xyz_room",
        },
        ("*", "*", "*"): {
            "desc": "A passage.",
            "prototype_parent": "xyz_exit",
        },
    },
    "options": {
        "map_visual_range": 1,
        "map_mode": "scan",
    },
}


class TestCallbacks(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        mock_room_callbacks.reset_mock()
        mock_exit_callbacks.reset_mock()

    def setup_grid(self, map_data):
        self.grid, err = xyzgrid.XYZGrid.create("testgrid")

        def _log(msg):
            print(msg)

        self.grid.log = _log

        self.map_data = map_data
        self.grid.add_maps(map_data)

    def tearDown(self):
        super().tearDown()
        self.grid.delete()

    def test_typeclassed_xyzroom_and_xyzexit_with_at_object_creation_are_called(self):
        map_data = dict(MAP_DATA)
        for prototype_key, prototype_value in map_data["prototypes"].items():
            if len(prototype_key) == 2:
                prototype_value["typeclass"] = "evennia.contrib.grid.xyzgrid.tests.TestXyzRoom"
            if len(prototype_key) == 3:
                prototype_value["typeclass"] = "evennia.contrib.grid.xyzgrid.tests.TestXyzExit"
        self.setup_grid(map_data)

        self.grid.spawn()

        # Two rooms and 2 exits, Each one should have gotten one `at_object_creation` callback.
        self.assertEqual(
            mock_room_callbacks.at_object_creation.mock_calls, [mock.call(), mock.call()]
        )
        self.assertEqual(
            mock_exit_callbacks.at_object_creation.mock_calls, [mock.call(), mock.call()]
        )
