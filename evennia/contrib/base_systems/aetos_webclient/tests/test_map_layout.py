"""
Tests for Aetos map layout and routing.

Blueprint section 21 requires the layout algorithm to be deterministic, stable,
collision-aware and able to handle disconnected components, and section 58 lists
map layout and pathfinding as Python-tested. The properties matter more than the
exact coordinates: a map that reshuffles itself between syncs is worse than no
map, because a player builds a mental model from it.

"""

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import map_layout


def room(identifier, name=None, distance=0):
    """Build a room dict."""
    return {"id": identifier, "name": name or identifier, "distance": distance}


def link(source, target, direction):
    """Build an exit dict."""
    return {"from": source, "to": target, "direction": direction}


class TestDirectionVectors(TestCase):
    """Direction handling."""

    def test_cardinals_map_to_unit_vectors(self):
        self.assertEqual(map_layout.direction_vector("north"), (0, -1, 0))
        self.assertEqual(map_layout.direction_vector("east"), (1, 0, 0))

    def test_abbreviations_are_understood(self):
        """Games abbreviate; "n" is as common as "north"."""
        self.assertEqual(map_layout.direction_vector("n"), map_layout.direction_vector("north"))
        self.assertEqual(
            map_layout.direction_vector("sw"), map_layout.direction_vector("southwest")
        )

    def test_case_and_whitespace_are_tolerated(self):
        self.assertEqual(map_layout.direction_vector("  NORTH "), (0, -1, 0))

    def test_up_and_down_change_the_z_level(self):
        self.assertEqual(map_layout.direction_vector("up"), (0, 0, 1))
        self.assertEqual(map_layout.direction_vector("down"), (0, 0, -1))

    def test_a_non_directional_exit_has_no_vector(self):
        """
        "enter tent" and "portal" are legitimate exits. Having no vector is a
        case to handle, not an error.

        """
        self.assertIsNone(map_layout.direction_vector("enter the tent"))
        self.assertIsNone(map_layout.direction_vector(""))
        self.assertIsNone(map_layout.direction_vector(None))

    def test_opposites(self):
        self.assertEqual(map_layout.opposite_direction("north"), "south")
        self.assertEqual(map_layout.opposite_direction("up"), "down")
        self.assertIsNone(map_layout.opposite_direction("portal"))


class TestCoordinateAssignment(TestCase):
    """Placing rooms on a grid."""

    def setUp(self):
        self.rooms = [room("a"), room("b"), room("c")]
        self.exits = [
            link("a", "b", "north"),
            link("b", "a", "south"),
            link("b", "c", "east"),
            link("c", "b", "west"),
        ]

    def test_origin_is_placed_at_zero(self):
        layout = map_layout.assign_coordinates(self.rooms, self.exits, origin="a")
        self.assertEqual(layout["positions"]["a"], [0, 0, 0])

    def test_directions_are_followed(self):
        layout = map_layout.assign_coordinates(self.rooms, self.exits, origin="a")
        self.assertEqual(layout["positions"]["b"], [0, -1, 0])
        self.assertEqual(layout["positions"]["c"], [1, -1, 0])

    def test_every_room_is_placed(self):
        layout = map_layout.assign_coordinates(self.rooms, self.exits, origin="a")
        self.assertEqual(set(layout["positions"]), {"a", "b", "c"})

    def test_vertical_exits_change_level(self):
        rooms = [room("a"), room("b")]
        exits = [link("a", "b", "up")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertEqual(layout["positions"]["b"][2], 1)

    def test_empty_input_is_handled(self):
        layout = map_layout.assign_coordinates([], [])
        self.assertEqual(layout["positions"], {})

    def test_a_room_with_no_exits_is_still_placed(self):
        layout = map_layout.assign_coordinates([room("lonely")], [])
        self.assertIn("lonely", layout["positions"])


class TestDeterminism(TestCase):
    """
    The same graph must always produce the same coordinates.

    A map that reshuffles between syncs destroys the mental model a player builds
    of the world, which is the main thing a map is for.

    """

    def test_repeated_runs_agree(self):
        rooms = [room(str(i)) for i in range(8)]
        exits = []
        for i in range(7):
            exits.append(link(str(i), str(i + 1), "east"))
        first = map_layout.assign_coordinates(rooms, exits, origin="0")
        second = map_layout.assign_coordinates(rooms, exits, origin="0")
        self.assertEqual(first["positions"], second["positions"])

    def test_input_ordering_does_not_matter(self):
        """
        A provider may return rooms in any order -- database iteration order is
        not guaranteed. The layout must not depend on it.

        """
        rooms = [room("a"), room("b"), room("c")]
        exits = [link("a", "b", "north"), link("b", "c", "east")]
        forward = map_layout.assign_coordinates(rooms, exits, origin="a")
        reversed_layout = map_layout.assign_coordinates(
            list(reversed(rooms)), list(reversed(exits)), origin="a"
        )
        self.assertEqual(forward["positions"], reversed_layout["positions"])

    def test_default_origin_is_stable(self):
        """With no origin given, the choice must still not vary."""
        rooms = [room("b"), room("a")]
        exits = [link("a", "b", "north")]
        first = map_layout.assign_coordinates(rooms, exits)
        second = map_layout.assign_coordinates(list(reversed(rooms)), exits)
        self.assertEqual(first["positions"], second["positions"])


class TestStability(TestCase):
    """Adding a room must not move the rooms already placed."""

    def test_extending_the_graph_leaves_existing_rooms_alone(self):
        rooms = [room("a"), room("b")]
        exits = [link("a", "b", "north")]
        before = map_layout.assign_coordinates(rooms, exits, origin="a")

        rooms.append(room("c"))
        exits.append(link("b", "c", "east"))
        after = map_layout.assign_coordinates(rooms, exits, origin="a")

        self.assertEqual(before["positions"]["a"], after["positions"]["a"])
        self.assertEqual(before["positions"]["b"], after["positions"]["b"])


class TestCollisions(TestCase):
    """
    Real MUD geography does not close squarely.

    A loop of three rooms joined north/east/west cannot be drawn on a grid
    without two rooms wanting the same cell. Stacking them silently would draw a
    confident lie; the layout nudges and records the conflict so a client can say
    the geometry is approximate.

    """

    def test_conflicting_rooms_do_not_share_a_cell(self):
        rooms = [room("a"), room("b"), room("c")]
        # b and c both sit north of a.
        exits = [link("a", "b", "north"), link("a", "c", "north")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        positions = list(layout["positions"].values())
        self.assertEqual(len(positions), len({tuple(p) for p in positions}))

    def test_a_conflict_is_reported(self):
        rooms = [room("a"), room("b"), room("c")]
        exits = [link("a", "b", "north"), link("a", "c", "north")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertTrue(layout["conflicts"])

    def test_conflict_resolution_is_deterministic(self):
        rooms = [room("a"), room("b"), room("c")]
        exits = [link("a", "b", "north"), link("a", "c", "north")]
        first = map_layout.assign_coordinates(rooms, exits, origin="a")
        second = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertEqual(first["positions"], second["positions"])

    def test_non_directional_exits_are_placed_and_reported(self):
        """
        An exit with no direction still leads somewhere the player can reach, so
        the room is placed -- but its position is not geographic and the client
        is told so.

        """
        rooms = [room("a"), room("tent")]
        exits = [link("a", "tent", "enter the tent")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertIn("tent", layout["positions"])
        reasons = [entry["reason"] for entry in layout["conflicts"]]
        self.assertIn("non-directional", reasons)


class TestDisconnectedComponents(TestCase):
    """
    A separate zone or an unlinked build is common. Dropping it would hide rooms
    the player can see.

    """

    def test_all_components_are_placed(self):
        rooms = [room("a"), room("b"), room("x"), room("y")]
        exits = [link("a", "b", "north"), link("x", "y", "north")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertEqual(set(layout["positions"]), {"a", "b", "x", "y"})

    def test_component_count_is_reported(self):
        rooms = [room("a"), room("x")]
        layout = map_layout.assign_coordinates(rooms, [], origin="a")
        self.assertEqual(layout["components"], 2)

    def test_components_do_not_overlap(self):
        rooms = [room("a"), room("b"), room("x"), room("y")]
        exits = [link("a", "b", "north"), link("x", "y", "north")]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        positions = [tuple(p) for p in layout["positions"].values()]
        self.assertEqual(len(positions), len(set(positions)))


class TestRouting(TestCase):
    """Shortest-path routing, used by click-to-walk."""

    def setUp(self):
        self.rooms = [room("a"), room("b"), room("c"), room("far")]
        self.exits = [
            link("a", "b", "north"),
            link("b", "c", "east"),
            link("a", "c", "northeast"),
        ]

    def test_finds_a_route(self):
        route = map_layout.find_route(self.rooms, self.exits, "a", "c")
        self.assertIsNotNone(route)

    def test_prefers_the_fewest_moves(self):
        """
        A player walks moves, not distance. The direct northeast link is one
        step; going via b is two.

        """
        route = map_layout.find_route(self.rooms, self.exits, "a", "c")
        self.assertEqual(len(route), 1)
        self.assertEqual(route[0]["direction"], "northeast")

    def test_route_steps_name_their_direction_and_destination(self):
        route = map_layout.find_route(self.rooms, self.exits, "a", "b")
        self.assertEqual(route[0]["direction"], "north")
        self.assertEqual(route[0]["to"], "b")

    def test_same_room_is_an_empty_route(self):
        """Not None: "already there" is success, not failure."""
        self.assertEqual(map_layout.find_route(self.rooms, self.exits, "a", "a"), [])

    def test_unreachable_returns_none(self):
        self.assertIsNone(map_layout.find_route(self.rooms, self.exits, "a", "far"))

    def test_unknown_rooms_return_none(self):
        self.assertIsNone(map_layout.find_route(self.rooms, self.exits, "a", "nope"))

    def test_exits_are_one_way_unless_declared_both_ways(self):
        """
        Evennia exits are directional objects. A route must not assume a way back
        exists, or click-to-walk would send a player into a one-way drop.

        """
        self.assertIsNone(map_layout.find_route(self.rooms, self.exits, "b", "a"))


class TestSurroundingsDescription(TestCase):
    """
    The non-visual map (blueprint section 47).

    Generated from the same graph the picture is drawn from, so the two cannot
    disagree.

    """

    def setUp(self):
        self.map_data = {
            "current": "a",
            "rooms": [
                room("a", "Town Square", 0),
                room("b", "Tower Road", 1),
                room("c", "Old Forest", 2),
            ],
            "exits": [link("a", "b", "north"), link("b", "c", "east")],
        }

    def test_reports_the_current_location_by_name(self):
        described = map_layout.describe_surroundings(self.map_data)
        self.assertEqual(described["location"], "Town Square")

    def test_lists_exits_with_their_destination_names(self):
        """
        "North: Tower Road" orients a player; "North" alone does not.

        """
        described = map_layout.describe_surroundings(self.map_data)
        self.assertEqual(described["exits"][0]["direction"], "north")
        self.assertEqual(described["exits"][0]["name"], "Tower Road")

    def test_lists_nearby_landmarks_beyond_the_immediate_exits(self):
        described = map_layout.describe_surroundings(self.map_data)
        names = [entry["name"] for entry in described["landmarks"]]
        self.assertIn("Old Forest", names)
        self.assertNotIn("Tower Road", names)

    def test_landmarks_are_ordered_nearest_first(self):
        described = map_layout.describe_surroundings(self.map_data)
        distances = [entry["distance"] for entry in described["landmarks"]]
        self.assertEqual(distances, sorted(distances))

    def test_handles_an_unknown_current_room(self):
        """A character in an unmapped room must not crash the description."""
        described = map_layout.describe_surroundings(dict(self.map_data, current="zzz"))
        self.assertIsNone(described["location"])

    def test_handles_an_empty_map(self):
        described = map_layout.describe_surroundings({"rooms": [], "exits": [], "current": None})
        self.assertIsNone(described["location"])
        self.assertEqual(described["exits"], [])
