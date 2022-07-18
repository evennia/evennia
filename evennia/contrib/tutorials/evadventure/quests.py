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


class EvAdventureQuest:
    """
    This represents a single questing unit of quest.

    Properties:
        name (str): Main identifier for the quest.
        category (str, optional): This + name must be globally unique.
        steps (list): A list of strings, representing how many steps are
            in the quest. The first step is always the beginning, when the quest is presented.
            The last step is always the end of the quest. It is possible to abort the quest before
    it ends - it then pauses after the last completed step.

    Each step is represented by three methods on this object:
    `check_<stepname>` and `complete_<stepname>`. `help_<stepname>` is used to get
    a guide/reminder on what you are supposed to do.

    """

    # name + category must be globally unique. They are
    # queried as name:category or just name, if category is empty.
    key = "basequest"
    desc = "This is the base quest. It will just step through its steps immediately."
    start_step = "start"
    end_text = "This quest is completed!"

    # help entries for quests
    help_start = "You need to start first"
    help_end = "You need to end the quest"

    def __init__(self, questhandler, start_step="start"):
        if " " in self.key:
            raise TypeError("The Quest name must not have spaces in it.")

        self.questhandler = questhandler
        self.current_step = start_step
        self.completed = False

    @property
    def quester(self):
        return self.questhandler.obj

    def end_quest(self):
        """
        Call this to end the quest.

        """
        self.completed = True

    def progress(self, *args, **kwargs):
        """
        This is called whenever the environment expects a quest may be complete.
        This will determine which quest-step we are on, run check_<stepname>, and if it
        succeeds, continue with complete_<stepname>.

        Args:
            *args, **kwargs: Will be passed into the check/complete methods.

        """
        if getattr(self, f"check_{self.current_step}")(*args, **kwargs):
            getattr(self, f"complete_{self.current_step}")(*args, **kwargs)

    def help(self):
        """
        This is used to get help (or a reminder) of what needs to be done to complete the current
        quest-step.

        Returns:
            str: The help text for the current step.

        """
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

    # step methods

    def check_start(self, *args, **kwargs):
        """
        Check if the starting conditions are met.

        Returns:
            bool: If this step is complete or not. If complete, the `complete_start`
            method will fire.

        """
        return True

    def complete_start(self, *args, **kwargs):
        """
        Completed start. This should change `.current_step` to the next step to complete
        and call `self.progress()` just in case the next step is already completed too.

        """
        self.quester.msg("Completed the first step of the quest.")
        self.current_step = "end"
        self.progress()

    def check_end(self, *args, **kwargs):
        return True

    def complete_end(self, *args, **kwargs):
        self.quester.msg("Quest complete!")
        self.end_quest()


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

    def add(self, quest, autostart=True):
        """
        Add a new quest

        Args:
            quest (EvAdventureQuest): The quest to start.
            autostart (bool, optional): If set, the quest will
                start immediately.

        """
        self.storage[quest.key] = quest
        self._save()

    def remove(self, quest_key):
        """
        Remove a quest.

        Args:
            quest_key (str): The quest to remove.

        """
        self.storage.pop(quest_key, None)
        self._save()

    def help(self, quest_key=None):
        """
        Get help text for a quest or for all quests. The help text is
        a combination of the description of the quest and the help-text
        of the current step.

        """
        help_text = []
        if quest_key in self.storage:
            quests = [self.storage[quest_key]]

        for quest in quests:
            help_text.append(f"|c{quest.key}|n\n {quest.desc}\n\n - {quest.help}")
        return "---".join(help_text)

    def progress(self, quest_key=None):
        """
        Check progress of a given quest or all quests.

        Args:
            quest_key (str, optional): If given, check the progress of this quest (if we have it),
                otherwise check progress on all quests.

        """
        if quest_key in self.storage:
            quests = [self.storage[quest_key]]
        else:
            quests = self.storage.values()

        for quest in quests:
            quest.progress()
