from mock import patch

from evennia.utils.test_resources import BaseEvenniaCommandTest, BaseEvenniaTest

from . import achievements

_dummy_achievements = {
    "ACHIEVE_ONE": {
        "name": "First Achievement",
        "desc": "A first achievement for first achievers.",
        "category": "login",
    },
    "COUNTING_ACHIEVE": {
        "name": "The Count",
        "desc": "One, two, three! Three counters! Ah ah ah!",
        "category": "get",
        "tracking": "thing",
        "count": 3,
    },
    "COUNTING_TWO": {
        "name": "Son of the Count",
        "desc": "Four, five, six! Six counters!",
        "category": "get",
        "tracking": "thing",
        "count": 3,
        "prereqs": "COUNTING_ACHIEVE",
    },
    "SEPARATE_ITEMS": {
        "name": "Apples and Pears",
        "desc": "Get some apples and some pears.",
        "category": "get",
        "tracking": ("apple", "pear"),
        "tracking_type": "separate",
        "count": 3,
    },
}


class TestAchievements(BaseEvenniaTest):
    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_completion(self):
        """no defined count means a single match completes it"""
        self.assertIn(
            "ACHIEVE_ONE",
            achievements.track_achievements(self.char1, category="login", track="first"),
        )

    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_counter_progress(self):
        """progressing a counter should update the achiever"""
        # this should not complete any achievements; verify it returns the right empty result
        self.assertEqual(achievements.track_achievements(self.char1, "get", "thing"), tuple())
        # first, verify that the data is created
        self.assertTrue(self.char1.attributes.has("achievements"))
        self.assertEqual(self.char1.db.achievements["COUNTING_ACHIEVE"]["progress"], 1)
        # verify that it gets updated
        achievements.track_achievements(self.char1, "get", "thing")
        self.assertEqual(self.char1.db.achievements["COUNTING_ACHIEVE"]["progress"], 2)

        # also verify that `get_achievement_progress` returns the correct data
        self.assertEqual(
            achievements.get_achievement_progress(self.char1, "COUNTING_ACHIEVE"), {"progress": 2}
        )

    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_prereqs(self):
        """verify progress is not counted on achievements with unmet prerequisites"""
        achievements.track_achievements(self.char1, "get", "thing")
        # this should mark progress on COUNTING_ACHIEVE, but NOT on COUNTING_TWO
        self.assertEqual(
            achievements.get_achievement_progress(self.char1, "COUNTING_ACHIEVE"), {"progress": 1}
        )
        self.assertEqual(achievements.get_achievement_progress(self.char1, "COUNTING_TWO"), {})

        # now we complete COUNTING_ACHIEVE...
        self.assertIn(
            "COUNTING_ACHIEVE", achievements.track_achievements(self.char1, "get", "thing", count=2)
        )
        # and track again to progress COUNTING_TWO
        achievements.track_achievements(self.char1, "get", "thing")
        self.assertEqual(
            achievements.get_achievement_progress(self.char1, "COUNTING_TWO"), {"progress": 1}
        )

    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_separate_tracking(self):
        """achievements with 'tracking_type': 'separate' should count progress for each item"""
        # getting one item only increments that one item
        achievements.track_achievements(self.char1, "get", "apple")
        progress = achievements.get_achievement_progress(self.char1, "SEPARATE_ITEMS")
        self.assertEqual(progress["progress"], [1, 0])
        # the other item then increments that item
        achievements.track_achievements(self.char1, "get", "pear")
        progress = achievements.get_achievement_progress(self.char1, "SEPARATE_ITEMS")
        self.assertEqual(progress["progress"], [1, 1])
        # completing one does not complete the achievement
        self.assertEqual(
            achievements.track_achievements(self.char1, "get", "apple", count=2), tuple()
        )
        # completing the second as well DOES complete the achievement
        self.assertIn(
            "SEPARATE_ITEMS", achievements.track_achievements(self.char1, "get", "pear", count=2)
        )

    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_search_achievement(self):
        """searching for achievements by name"""
        results = achievements.search_achievement("count")
        self.assertEqual(["COUNTING_ACHIEVE", "COUNTING_TWO"], list(results.keys()))


class TestAchieveCommand(BaseEvenniaCommandTest):
    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_switches(self):
        # print only achievements that have no prereqs
        expected_output = "\n".join(
            f"{data['name']}\n{data['desc']}\nNot Started"
            for key, data in _dummy_achievements.items()
            if not data.get("prereqs")
        )
        self.call(achievements.CmdAchieve(), "", expected_output)
        # print all achievements
        expected_output = "\n".join(
            f"{data['name']}\n{data['desc']}\nNot Started"
            for key, data in _dummy_achievements.items()
        )
        self.call(achievements.CmdAchieve(), "/all", expected_output)
        # these should both be empty
        self.call(achievements.CmdAchieve(), "/progress", "There are no matching achievements.")
        self.call(achievements.CmdAchieve(), "/done", "There are no matching achievements.")
        # update one and complete one, then verify they show up correctly
        achievements.track_achievements(self.char1, "login")
        achievements.track_achievements(self.char1, "get", "thing")
        self.call(
            achievements.CmdAchieve(),
            "/progress",
            "The Count\nOne, two, three! Three counters! Ah ah ah!\n33% complete",
        )
        self.call(
            achievements.CmdAchieve(),
            "/done",
            "First Achievement\nA first achievement for first achievers.\nCompleted!",
        )

    @patch(
        "evennia.contrib.game_systems.achievements.achievements._ACHIEVEMENT_DATA",
        _dummy_achievements,
    )
    def test_search(self):
        # by default, only returns matching items that are trackable
        self.call(
            achievements.CmdAchieve(),
            " count",
            "The Count\nOne, two, three! Three counters! Ah ah ah!\nNot Started",
        )
        # with switches, returns matching items from the switch set
        self.call(
            achievements.CmdAchieve(),
            "/all count",
            "The Count\nOne, two, three! Three counters! Ah ah ah!\nNot Started\n"
            + "Son of the Count\nFour, five, six! Six counters!\nNot Started",
        )
