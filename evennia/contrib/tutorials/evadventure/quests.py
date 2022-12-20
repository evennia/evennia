"""
A simple quest system for EvAdventure.

A quest is represented by a quest-handler sitting as
.quest on a Character. Individual Quests are objects
that track the state and can have multiple steps, each
of which are checked off during the quest's progress.

The player can use the quest handler to track the
progress of their quests.

A quest ending can mean a reward or the start of
another quest.

"""

from copy import copy, deepcopy

from evennia.utils import dbserialize


class EvAdventureQuest:
    """
    This represents a single questing unit of quest.

    Properties:
        name (str): Main identifier for the quest.
        category (str, optional): This + name must be globally unique.
    it ends - it then pauses after the last completed step.

    Each step of the quest is represented by a `.step_<stepname>` method. This should check
    the status of the quest-step and update the `.current_step` or call `.complete()`. There
    are also `.help_<stepname>` which is either a class-level help string or a method
    returning a help text. All properties should be stored on the quester.

    Example:
    ```py
    class MyQuest(EvAdventureQuest):
        '''A quest with two steps that ar'''

        start_step = "A"

        help_A = "You need a '_quest_A_flag' on yourself to finish this step!"
        help_B = "Finally, you need more than 4 items in your inventory!"

        def step_A(self, *args, **kwargs):
            if self.quester.db._quest_A_flag == True:
                self.quester.msg("Completed the first step of the quest.")
                self.current_step = "end"
                self.progress()

        def step_end(self, *args, **kwargs):
            if len(self.quester.contents) > 4:
                self.quester.msg("Quest complete!")
                self.complete()
    ```
    """

    key = "basequest"
    desc = "This is the base quest class"
    start_step = "start"

    completed_text = "This quest is completed!"
    abandoned_text = "This quest is abandoned."

    # help entries for quests (could also be methods)
    help_start = "You need to start first"
    help_end = "You need to end the quest"

    def __init__(self, quester, start_step=None):
        if " " in self.key:
            raise TypeError("The Quest name must not have spaces in it.")

        self.quester = quester
        self._current_step = start_step or self.start_step
        self.is_completed = False
        self.is_abandoned = False

    def __serialize_dbobjs__(self):
        self.quester = dbserialize.dbserialize(self.quester)

    def __deserialize_dbobjs__(self):
        if isinstance(self.quester, bytes):
            self.quester = dbserialize.dbunserialize(self.quester)

    @property
    def questhandler(self):
        return self.quester.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, step_name):
        self._current_step = step_name
        self.questhandler.do_save = True

    def abandon(self):
        """
        Call when quest is abandoned.

        """
        self.is_abandoned = True
        self.cleanup()

    def complete(self):
        """
        Call this to end the quest.

        """
        self.is_completed = True
        self.cleanup()

    def progress(self, *args, **kwargs):
        """
        This is called whenever the environment expects a quest may need stepping. This will
        determine which quest-step we are on and run `step_<stepname>`, which in turn will figure
        out if the step is complete or not.

        Args:
            *args, **kwargs: Will be passed into the step method.

        """
        if not (self.is_completed or self.is_abandoned):
            getattr(self, f"step_{self.current_step}")(*args, **kwargs)

    def help(self):
        """
        This is used to get help (or a reminder) of what needs to be done to complete the current
        quest-step.

        Returns:
            str: The help text for the current step.

        """
        if self.is_completed:
            return self.completed_text
        if self.is_abandoned:
            return self.abandoned_text

        help_resource = (
            getattr(self, f"help_{self.current_step}", None)
            or "You need to {self.current_step} ..."
        )
        if callable(help_resource):
            # the help_<current_step> can be a method to call
            return help_resource()
        else:
            # normally it's just a string
            return str(help_resource)

    # step methods and hooks

    def step_start(self, *args, **kwargs):
        """
        Example step that completes immediately.

        """
        self.complete()

    def cleanup(self):
        """
        This is called both when completing the quest, or when it is abandoned prematurely.
        Make sure to cleanup any quest-related data stored when following the quest.

        """
        pass


class EvAdventureQuestHandler:
    """
    This sits on the Character, as `.quests`.

    It's initiated using a lazy property on the Character:

    ```
    @lazy_property
    def quests(self):
        return EvAdventureQuestHandler(self)
    ```

    """

    quest_storage_attribute_key = "_quests"
    quest_storage_attribute_category = "evadventure"

    def __init__(self, obj):
        self.obj = obj
        self.do_save = False
        self._load()

    def _load(self):
        self.storage = self.obj.attributes.get(
            self.quest_storage_attribute_key,
            category=self.quest_storage_attribute_category,
            default={},
        )

    def _save(self):
        self.obj.attributes.add(
            self.quest_storage_attribute_key,
            self.storage,
            category=self.quest_storage_attribute_category,
        )
        self._load()  # important
        self.do_save = False

    def has(self, quest_key):
        """
        Check if a given quest is registered with the Character.

        Args:
            quest_key (str): The name of the quest to check for.
            quest_category (str, optional): Quest category, if any.

        Returns:
            bool: If the character is following this quest or not.

        """
        return bool(self.storage.get(quest_key))

    def get(self, quest_key):
        """
        Get the quest stored on character, if any.

        Args:
            quest_key (str): The name of the quest to check for.

        Returns:
            EvAdventureQuest or None: The quest stored, or None if
                Character is not on this quest.

        """
        return self.storage.get(quest_key)

    def add(self, quest):
        """
        Add a new quest

        Args:
            quest (EvAdventureQuest): The quest class to start.

        """
        self.storage[quest.key] = quest(self.obj)
        self._save()

    def remove(self, quest_key):
        """
        Remove a quest. If not complete, it will be abandoned.

        Args:
            quest_key (str): The quest to remove.

        """
        quest = self.storage.pop(quest_key, None)
        if not quest.is_completed:
            # make sure to cleanup
            quest.abandon()
        self._save()

    def get_help(self, quest_key=None):
        """
        Get help text for a quest or for all quests. The help text is
        a combination of the description of the quest and the help-text
        of the current step.

        Args:
            quest_key (str, optional): The quest-key. If not given, get help for all
                quests in handler.

        Returns:
            list: Help texts, one for each quest, or only one if `quest_key` is given.

        """
        help_texts = []
        if quest_key in self.storage:
            quests = [self.storage[quest_key]]
        else:
            quests = self.storage.values()

        for quest in quests:
            help_texts.append(f"|c{quest.key}|n\n {quest.desc}\n\n - {quest.help()}")
        return help_texts

    def progress(self, quest_key=None, *args, **kwargs):
        """
        Check progress of a given quest or all quests.

        Args:
            quest_key (str, optional): If given, check the progress of this quest (if we have it),
                otherwise check progress on all quests.
            *args, **kwargs: Will be passed into each quest's `progress` call.

        """
        if quest_key in self.storage:
            quests = [self.storage[quest_key]]
        else:
            quests = self.storage.values()

        for quest in quests:
            quest.progress(*args, **kwargs)

        if self.do_save:
            # do_save is set by the quest
            self._save()
