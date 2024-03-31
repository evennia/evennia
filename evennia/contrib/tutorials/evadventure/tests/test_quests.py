"""
Testing Quest functionality.

"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import BaseEvenniaTest

from .. import quests
from ..objects import EvAdventureObject
from .mixins import EvAdventureMixin


class _TestQuest(quests.EvAdventureQuest):
    """
    Test quest.

    """

    key = "testquest"
    desc = "A test quest!"

    start_step = "A"
    end_text = "This task is completed."

    help_A = "You need to do A first."
    help_B = "Next, do B."

    def step_A(self, *args, **kwargs):
        """
        Quest-step A is completed when quester carries an item with tag "QuestA" and category
        "quests".
        """
        # note - this could be done with a direct db query instead to avoid a loop, for a
        # unit test it's fine though
        if any(obj for obj in self.quester.contents if obj.tags.has("QuestA", category="quests")):
            self.quester.msg("Completed step A of quest!")
            self.current_step = "B"
            self.progress()

    def step_B(self, *args, **kwargs):
        """
        Quest-step B is completed when the progress-check is called with a special kwarg
        "complete_quest_B"

        """
        if kwargs.get("complete_quest_B", False):
            self.quester.msg("Completed step B of quest!")
            self.quester.db.test_quest_counter = 0
            self.current_step = "C"
            self.progress()

    def help_C(self):
        """Testing the method-version of getting a help entry"""
        return f"Only C left now, {self.quester.key}!"

    def step_C(self, *args, **kwargs):
        """
        Step C (final) step of quest completes when a counter on quester is big enough.

        """
        if self.quester.db.test_quest_counter and self.quester.db.test_quest_counter > 5:
            self.quester.msg("Quest complete! Get XP rewards!")
            self.quester.db.xp += 10
            self.complete()

    def cleanup(self):
        """
        Cleanup data related to quest.

        """
        del self.quester.db.test_quest_counter


class EvAdventureQuestTest(EvAdventureMixin, BaseEvenniaTest):
    """
    Test questing.

    """

    def setUp(self):
        super().setUp()
        self.character.quests.add(_TestQuest)
        self.character.msg = MagicMock()

    def _get_quest(self):
        return self.character.quests.get(_TestQuest.key)

    def _fulfillA(self):
        """Fulfill quest step A"""
        EvAdventureObject.create(
            key="quest obj", location=self.character, tags=(("QuestA", "quests"),)
        )

    def _fulfillC(self):
        """Fullfill quest step C"""
        self.character.db.test_quest_counter = 6

    def test_help(self):
        """Get help"""
        quest = self._get_quest()
        # get help for a specific quest
        help_txt = quest.help()
        self.assertEqual(help_txt, "You need to do A first.")

        # help for finished quest
        quest.complete()
        help_txt = quest.help()
        self.assertEqual(help_txt, "You have completed this quest.")

    def test_progress__fail(self):
        """
        Check progress without having any.
        """
        quest = self._get_quest()
        # progress quest
        quest.progress()

        # still on step A
        self.assertEqual(quest.current_step, "A")

    def test_progress(self):
        """
        Fulfill the quest steps in sequence.

        """
        quest = self._get_quest()

        # A requires a certain object in inventory
        self._fulfillA()
        quest.progress()
        self.assertEqual(quest.current_step, "B")

        # B requires progress be called with specific kwarg
        # should not step (no kwarg)
        quest.progress()
        self.assertEqual(quest.current_step, "B")

        # should step (kwarg sent)
        quest.progress(complete_quest_B=True)
        self.assertEqual(quest.current_step, "C")

        # C requires a counter Attribute on char be high enough
        self._fulfillC()
        quest.progress()
        self.assertEqual(quest.current_step, "C")  # still on last step
        self.assertEqual(quest.is_completed, True)
