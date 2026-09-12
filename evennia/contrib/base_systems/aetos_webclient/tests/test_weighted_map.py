"""
Tests for E6 -- mapper metadata and weighted routing.

Addendum C.19. The widget-SDK half of E6 shipped at M22.

Three things:

- **Optional edge cost.** Without it every edge costs 1, so a game that
  declares nothing gets exactly the breadth-first behaviour it had before.
- **Optional availability.** Routing excludes a shut door; describing the map
  does not, because a player is entitled to know it exists.
- **The ambiguity rule (C.6).** Aetos reports what the game said and invents
  nothing -- no inferred skill, class, guild, weather or roundtime restriction,
  and no guessed reason for a blocked exit.

The server and the client both route, so both implementations are pinned to the
same fixtures. Two shortest-path implementations that can disagree are worse
than one, because the disagreement only shows up as a route that fails halfway.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR, map_layout

MAP_JS = (Path(AETOS_STATIC_DIR) / "aetos" / "js" / "map.js").read_text(encoding="utf-8")


def _rooms(*ids):
    """
    Build a minimal room list.

    Args:
        *ids (str): Room ids.

    Returns:
        list: Room dicts.

    """
    return [{"id": identifier} for identifier in ids]


#: Two ways from `a` to `d`, both two moves. The northern one is expensive.
DIAMOND = [
    {"from": "a", "to": "b", "direction": "north", "cost": 9},
    {"from": "b", "to": "d", "direction": "east"},
    {"from": "a", "to": "c", "direction": "east"},
    {"from": "c", "to": "d", "direction": "north"},
]


class TestEdgeCost(TestCase):
    """C.19: without cost, edge cost is 1."""

    def test_an_absent_cost_is_one(self):
        self.assertEqual(map_layout.edge_cost({}), 1)
        self.assertEqual(map_layout.edge_cost({"cost": None}), 1)

    def test_a_declared_cost_is_used(self):
        self.assertEqual(map_layout.edge_cost({"cost": 8}), 8)
        self.assertEqual(map_layout.edge_cost({"cost": 2.5}), 2.5)

    def test_a_boolean_is_not_a_cost(self):
        """
        `True` is an int in Python and would silently mean "cost 1" -- right by
        accident and wrong as a habit.

        """
        self.assertEqual(map_layout.edge_cost({"cost": True}), 1)
        self.assertEqual(map_layout.edge_cost({"cost": False}), 1)

    def test_nonsense_falls_back_rather_than_raising(self):
        """
        A provider is game code. One bad number must not cost the player their
        whole map.

        """
        for bad in ("expensive", [], {}, float("nan")):
            self.assertEqual(map_layout.edge_cost({"cost": bad}), 1)

    def test_a_negative_cost_is_refused(self):
        """
        A negative edge would let a route improve by walking in circles, which
        Dijkstra cannot express and no game means.

        """
        self.assertEqual(map_layout.edge_cost({"cost": -5}), 1)

    def test_an_absurd_cost_is_clamped(self):
        """
        Arithmetic hygiene rather than a judgement about what "expensive"
        means: 1e308 makes every comparison in the search meaningless.

        """
        self.assertEqual(map_layout.edge_cost({"cost": 1e308}), map_layout.MAX_EDGE_COST)


class TestWeightedRouting(TestCase):
    """Dijkstra, which C.19 says suffices."""

    def test_the_cheap_route_wins_over_the_short_one(self):
        route = map_layout.find_route(_rooms("a", "b", "c", "d"), DIAMOND, "a", "d")
        self.assertEqual([step["direction"] for step in route], ["east", "north"])

    def test_the_cost_is_reported(self):
        cost = map_layout.route_cost(_rooms("a", "b", "c", "d"), DIAMOND, "a", "d")
        self.assertEqual(cost, 2)

    def test_without_costs_it_is_exactly_breadth_first(self):
        """
        The property that matters for every game that has not adopted this: no
        declared costs means every edge is 1, so the cheapest route is the one
        with fewest moves -- unchanged behaviour rather than an approximation
        of it.

        """
        uniform = [{key: value for key, value in link.items() if key != "cost"} for link in DIAMOND]
        route = map_layout.find_route(_rooms("a", "b", "c", "d"), uniform, "a", "d")
        self.assertEqual(len(route), 2)

    def test_a_longer_but_cheaper_route_is_chosen(self):
        """
        Three cheap moves beat one expensive one, which is the whole point of
        weighting and the case a move-counting search gets wrong.

        """
        exits = [
            {"from": "a", "to": "z", "direction": "up", "cost": 20},
            {"from": "a", "to": "m", "direction": "north"},
            {"from": "m", "to": "n", "direction": "north"},
            {"from": "n", "to": "z", "direction": "north"},
        ]
        route = map_layout.find_route(_rooms("a", "m", "n", "z"), exits, "a", "z")
        self.assertEqual(len(route), 3)
        self.assertEqual(map_layout.route_cost(_rooms("a", "m", "n", "z"), exits, "a", "z"), 3)

    def test_ties_resolve_the_same_way_every_time(self):
        """
        A map that suggests a different equally-good route on each sync is one
        nobody can follow.

        """
        exits = [
            {"from": "a", "to": "b", "direction": "north"},
            {"from": "a", "to": "c", "direction": "east"},
            {"from": "b", "to": "d", "direction": "east"},
            {"from": "c", "to": "d", "direction": "north"},
        ]
        rooms = _rooms("a", "b", "c", "d")
        first = map_layout.find_route(rooms, exits, "a", "d")
        for _ in range(5):
            self.assertEqual(map_layout.find_route(rooms, exits, "a", "d"), first)

    def test_an_unreachable_goal_returns_none(self):
        self.assertIsNone(map_layout.find_route(_rooms("a", "b"), [], "a", "b"))

    def test_being_there_already_is_an_empty_route(self):
        self.assertEqual(map_layout.find_route(_rooms("a"), [], "a", "a"), [])


class TestAvailability(TestCase):
    """A door the game says is shut."""

    def _blocked_diamond(self):
        """
        The diamond with the cheap eastern route barred.

        Returns:
            list: Link dicts.

        """
        return [
            (
                dict(link, available=False, reason="The gate is barred.")
                if link["from"] == "a" and link["direction"] == "east"
                else link
            )
            for link in DIAMOND
        ]

    def test_routing_goes_around_a_blocked_exit(self):
        route = map_layout.find_route(_rooms("a", "b", "c", "d"), self._blocked_diamond(), "a", "d")
        self.assertEqual([step["direction"] for step in route], ["north", "east"])

    def test_silence_means_available(self):
        """
        A game that says nothing about availability has an ordinary exit.
        Treating silence as "blocked" would empty the map of every game that
        has not adopted the field.

        """
        self.assertTrue(map_layout.edge_is_available({}))
        self.assertTrue(map_layout.edge_is_available({"available": True}))
        self.assertFalse(map_layout.edge_is_available({"available": False}))

    def test_a_blocked_exit_is_still_reported(self):
        """
        A player is entitled to know a door exists and is shut. A map that
        silently omits it looks like a map with a missing room, which is a
        worse thing to be looking at.

        """
        blocked = map_layout.blocked_exits(self._blocked_diamond())
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["direction"], "east")
        self.assertEqual(blocked[0]["reason"], "The gate is barred.")

    def test_no_reason_is_ever_invented(self):
        """
        C.6 and C.19. "unknown" is preferable to wrong, and a guessed reason is
        the confident error that costs a player their trust in the whole map.

        """
        blocked = map_layout.blocked_exits(
            [{"from": "a", "to": "b", "direction": "north", "available": False}]
        )
        self.assertIsNone(blocked[0]["reason"])

    def test_a_blocked_exit_still_occupies_the_map(self):
        """
        Position is geography; availability is a state of the door. Leaving a
        shut door out of the layout would move rooms around whenever one
        closed.

        """
        rooms = _rooms("a", "b")
        exits = [{"from": "a", "to": "b", "direction": "north", "available": False}]
        layout = map_layout.assign_coordinates(rooms, exits, origin="a")
        self.assertIn("b", layout["positions"])


class TestNoInference(TestCase):
    """
    C.19: **the client MUST NOT infer** skill, class, guild, weather or
    roundtime restrictions unless the provider supplies them.

    """

    def test_the_module_never_guesses_a_restriction(self):
        source = Path(map_layout.__file__).read_text(encoding="utf-8")
        code = re.sub(r'"""[\s\S]*?"""', "", source)
        code = re.sub(r"^\s*#.*$", "", code, flags=re.MULTILINE)
        for guess in (
            "skill",
            "class_",
            "guild",
            "weather",
            "roundtime",
            "stand",
            "swim",
            "climb",
            "retreat",
        ):
            self.assertNotIn(guess, code, "map_layout infers %r" % guess)

    def test_no_genre_specific_recovery_in_the_client(self):
        """
        C.19: Aetos core does not automatically stand, retreat, swim, climb,
        open doors or fight blockers. Those are game decisions.

        """
        code = re.sub(r"/\*[\s\S]*?\*/", "", MAP_JS)
        code = re.sub(r"^\s*//.*$", "", code, flags=re.MULTILINE)
        for guess in ("stand up", 'sendCommand("open', "retreat", "autoRecover"):
            self.assertNotIn(guess, code)


class TestBothImplementationsAgree(TestCase):
    """
    Two shortest-path implementations that can disagree are worse than one,
    because the disagreement only shows up as a route that fails halfway.

    Asserted structurally: the client mirrors the server's constants, its
    default, and its treatment of the awkward inputs.

    """

    def test_the_client_shares_the_default_cost(self):
        self.assertIn("var DEFAULT_EDGE_COST = 1;", MAP_JS)
        self.assertEqual(map_layout.DEFAULT_EDGE_COST, 1)

    def test_the_client_shares_the_clamp(self):
        self.assertIn("var MAX_EDGE_COST = 10000;", MAP_JS)
        self.assertEqual(map_layout.MAX_EDGE_COST, 10000)

    def test_the_client_also_refuses_a_boolean_cost(self):
        self.assertIn('typeof raw === "boolean"', MAP_JS)

    def test_the_client_also_refuses_a_negative_cost(self):
        self.assertIn("cost < 0", MAP_JS)

    def test_the_client_also_treats_silence_as_available(self):
        self.assertIn("link.available !== false", MAP_JS)

    def test_the_client_excludes_blocked_edges_from_routing(self):
        start = MAP_JS.index("function findRoute(mapData, from, to)")
        window = MAP_JS[start : MAP_JS.index("function blockedExits", start)]
        self.assertIn("edgeIsAvailable(link)", window)

    def test_both_break_ties_deterministically(self):
        start = MAP_JS.index("function cheapestUnsettled()")
        window = MAP_JS[start : MAP_JS.index("var current = cheapestUnsettled", start)]
        self.assertIn("room < chosen", window)

    def test_the_client_reports_a_blocked_reason_without_inventing_one(self):
        start = MAP_JS.index("function blockedExits(mapData)")
        window = MAP_JS[start : start + 700]
        self.assertIn('typeof link.reason === "string"', window)
        self.assertIn(": null", window)


class TestTheFailureMessageSaysWhatIsKnown(TestCase):
    """
    A player who can see a room on the map and cannot walk to it is owed better
    than "no route" -- that reads as a broken map rather than a shut door.

    """

    def test_a_blocked_reason_is_repeated_verbatim(self):
        start = MAP_JS.index("function walkTo(roomId)")
        window = MAP_JS[start : start + 1800]
        self.assertIn("blockedExits(data)", window)
        self.assertIn("blocked[0].reason", window)

    def test_it_falls_back_to_saying_only_that(self):
        start = MAP_JS.index("function walkTo(roomId)")
        window = MAP_JS[start : start + 1800]
        self.assertIn('"No route to that location."', window)
