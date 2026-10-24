"""
Tests for A3 -- the accessible map.

Addendum A.29. The rule underneath all of it is that the picture and the words
are two renderings of one dataset, not a graphic with a caption bolted on. So
these assert that the text form exists, is generated from the same graph, and is
not quietly second-class.

"""

import re
from pathlib import Path

from django.test import TestCase

from evennia.contrib.base_systems.aetos_webclient import AETOS_STATIC_DIR

JS_DIR = Path(AETOS_STATIC_DIR) / "aetos" / "js"


def _read(name):
    """
    Read a client module.

    Args:
        name (str): File name under the js directory.

    Returns:
        str: Contents.

    """
    return (JS_DIR / name).read_text(encoding="utf-8")


MAP = _read("map.js")
SHELL = _read("aetos.js")


class TestTheMapHasATextForm(TestCase):
    """A11Y-MAP-001, A11Y-MAP-002."""

    def test_the_current_room_is_stated(self):
        self.assertIn("Current location", MAP)

    def test_exits_are_buttons_naming_their_destination(self):
        """
        "North: Tower Road" tells a player far more than "North", and it is the
        difference between a list they can navigate by and a compass rose.

        """
        self.assertIn("exit.direction", MAP)
        self.assertIn('exit.direction + ": " + exit.name', MAP)

    def test_the_svg_is_hidden_from_assistive_technology(self):
        """
        A11Y-MAP-005. Exposing a few hundred graphical nodes to a screen reader
        for "completeness" produces noise, not information -- permissible only
        because the same data is fully available as text.

        """
        self.assertIn('"aria-hidden": "true"', MAP)


class TestRoutesAreWrittenOut(TestCase):
    """A11Y-MAP-003."""

    def test_a_route_can_be_described(self):
        self.assertIn("function describeRoute", MAP)

    def test_the_description_comes_from_the_same_steps_that_are_walked(self):
        """
        Not a parallel description. If the two could disagree, the one the
        player was reading would eventually be the wrong one.

        """
        start = MAP.index("lastRoute = describeRoute(")
        window = MAP[start : start + 500]
        self.assertIn("queueRoute(steps)", window)

    def test_the_steps_are_an_ordered_list(self):
        """
        <ol>, not <ul>. The order is the information, and a screen reader
        announcing "3 of 5" gives the player their position in the journey for
        free.

        """
        start = MAP.index("function renderRoute")
        window = MAP[start : start + 900]
        self.assertIn('createElement("ol")', window)

    def test_the_step_count_is_given_before_the_steps(self):
        """
        "Five steps" decides whether to go now. The list decides how.

        """
        start = MAP.index("function renderRoute")
        window = MAP[start : start + 900]
        self.assertLess(window.index("route-summary"), window.index('createElement("ol")'))

    def test_a_stale_route_is_dropped_when_the_map_moves(self):
        """
        Yesterday's route beside today's rooms is worse than no route.

        """
        self.assertIn("data.current !== lastRouteOrigin", MAP)


class TestPlacesAreSearchable(TestCase):
    """A11Y-MAP-004."""

    def test_there_is_a_places_list(self):
        self.assertIn("function renderPlaces", MAP)

    def test_it_is_filterable(self):
        self.assertIn("aetos-map-search", MAP)
        self.assertIn("indexOf(needle)", MAP)

    def test_the_search_field_has_a_label(self):
        """An unlabelled search box is announced as "edit", and nothing else."""
        self.assertIn("aetos-visually-hidden", MAP)
        self.assertIn('"for", "aetos-map-search"', MAP)

    def test_the_players_own_points_of_interest_are_included(self):
        self.assertIn("listPois", MAP)
        self.assertIn("poi: true", SHELL)

    def test_the_players_own_entries_are_labelled_as_theirs(self):
        """
        A.80 and the M11 rule: the game's knowledge and the player's private
        notes must never be confused. The visual marker is unavailable to
        exactly the player this list exists for, so it is said in words.

        """
        self.assertIn('" (your note)"', MAP)

    def test_an_unreachable_place_is_not_offered_as_a_button(self):
        """
        A disabled button suggests the route might exist. Plain text says it
        does not.

        """
        start = MAP.index("function renderPlaces")
        window = MAP[start : MAP.index("function renderText")]
        self.assertIn("if (entry.id && onWalk)", window)


class TestTheMapDoesNotDestroyTheDomItIsUpdating(TestCase):
    """
    A11Y-FOCUS-005, and the defect that A0's focus test caught here.

    The first version of the places search rebuilt the whole widget on every
    keystroke and then called `focus()` to put the player back. That is a
    workaround for a DOM being destroyed for no reason: a sync arriving while
    someone was typing would rebuild the field under them, and restoring focus
    by hand cannot fix a value that was already thrown away.

    Not replacing the element is the fix.

    """

    def test_the_map_never_calls_focus(self):
        self.assertNotIn(".focus()", MAP)

    def test_the_search_input_is_created_once_at_mount(self):
        start = MAP.index("mount: function (context)")
        end = MAP.index("update: function (context, mapData)")
        self.assertIn('input.id = "aetos-map-search"', MAP[start:end])

    def test_the_update_path_does_not_create_the_search_input(self):
        start = MAP.index("update: function (context, mapData)")
        self.assertNotIn('input.id = "aetos-map-search"', MAP[start:])

    def test_typing_refreshes_only_the_list(self):
        start = MAP.index("context.searchInput.addEventListener")
        window = MAP[start : start + 200]
        self.assertIn("refreshPlaces()", window)

    def test_the_listener_is_bound_once(self):
        """
        `update` runs on every sync. Binding there without a guard would add a
        listener per sync, and a hundred syncs later every keystroke would
        rebuild the list a hundred times.

        """
        self.assertIn("context.searchBound", MAP)


class TestRouteAnnouncementsAreCategorised(TestCase):
    """
    Movement is `important`; a failed route is a system message.

    Neither is `critical` -- the urgent region is for the connection dropping,
    and a route that cannot be found does not meet that bar.

    """

    def test_walking_announces_as_movement(self):
        self.assertIn('category: "movement"', MAP)

    def test_no_route_announces_as_system(self):
        self.assertIn('category: "system"', MAP)

    def test_nothing_in_the_map_is_critical(self):
        self.assertNotIn('priority: "critical"', MAP)
