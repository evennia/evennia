"""
A simple quest system for EvAdventure.

A quest is represented by a quest-handler sitting as
`.quests` on a Character. Individual Quests are child classes of `EvAdventureQuest` with
methods for each step of the quest. The quest handler can add, remove, and track the progress
by calling the `progress` method on the quest. Persistent changes are stored on the quester
using the `add_data` and `get_data` methods with an Attribute as storage backend.

A quest ending can mean a reward or the start of
another quest.

"""

from evennia import Command


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

        help_A = "You need a 'A_flag' attribute on yourself to finish this step!"
        help_B = "Finally, you need more than 4 items in your inventory!"

        def step_A(self, *args, **kwargs):
            if self.get_data("A_flag") == True:
                self.quester.msg("Completed the first step of the quest.")
                self.current_step = "end"
                self.progress()

        def step_B(self, *args, **kwargs):


        def step_end(self, *args, **kwargs):
            if len(self.quester.contents) > 4:
                self.quester.msg("Quest complete!")
                self.complete()
    ```
    """

    key = "base quest"
    desc = "This is the base quest class"
    start_step = "start"

    # help entries for quests (could also be methods)
    help_start = "You need to start first"
    help_end = "You need to end the quest"

    def __init__(self, quester):
        self.quester = quester
        self.data = self.questhandler.load_quest_data(self.key)
        self._current_step = self.get_data("current_step")

        if not self._current_step:
            self._current_step = self.start_step

    def add_data(self, key, value):
        """
        Add data to the quest. This saves it permanently.

        Args:
            key (str): The key to store the data under.
            value (any): The data to store.

        """
        self.data[key] = value
        self.questhandler.save_quest_data(self.key)

    def get_data(self, key, default=None):
        """
        Get data from the quest.

        Args:
            key (str): The key to get data for.
            default (any, optional): The default value to return if key is not found.

        Returns:
            any: The data stored under the key.

        """
        return self.data.get(key, default)

    def remove_data(self, key):
        """
        Remove data from the quest permanently.

        Args:
            key (str): The key to remove.

        """
        self.data.pop(key, None)
        self.questhandler.save_quest_data(self.key)

    @property
    def questhandler(self):
        return self.quester.quests

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, step_name):
        self._current_step = step_name
        self.add_data("current_step", step_name)

    @property
    def status(self):
        return self.get_data("status", "started")

    @status.setter
    def status(self, value):
        self.add_data("status", value)

    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def is_abandoned(self):
        return self.status == "abandoned"

    @property
    def is_failed(self):
        return self.status == "failed"

    def complete(self):
        """
        Complete the quest.

        """
        self.status = "completed"

    def abandon(self):
        """
        Abandon the quest.

        """
        self.status = "abandoned"

    def fail(self):
        """
        Fail the quest.

        """
        self.status = "failed"

    def progress(self, *args, **kwargs):
        """
        This is called whenever the environment expects a quest may need stepping. This will
        determine which quest-step we are on and run `step_<stepname>`, which in turn will figure
        out if the step is complete or not.

        Args:
            *args, **kwargs: Will be passed into the step method.

        Notes:
            `self.quester` is available as the character following the quest.

        """
        getattr(self, f"step_{self.current_step}")(*args, **kwargs)

    def help(self, *args, **kwargs):
        """
        This is used to get help (or a reminder) of what needs to be done to complete the current
        quest-step. It will look for a `help_<stepname>` method or string attribute on the quest.

        Args:
            *args, **kwargs: Will be passed into any help_* method.

        Returns:
            str: The help text for the current step.

        """
        if self.status in ("abandoned", "completed", "failed"):
            help_resource = getattr(
                self, f"help_{self.status}", f"You have {self.status} this quest."
            )
        else:
            help_resource = getattr(self, f"help_{self.current_step}", "No help available.")

        if callable(help_resource):
            # the help_* methods can be used to dynamically generate help
            return help_resource(*args, **kwargs)
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

        This is for cleaning up any extra state that were set during the quest (stuff in self.data
        is automatically cleaned up)
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

    quest_data_attribute_template = "_quest_data_{quest_key}"
    quest_data_attribute_category = "evadventure"

    def __init__(self, obj):
        self.obj = obj
        self.quests = {}
        self.quest_classes = {}
        self._load()

    def _load(self):
        self.quest_classes = self.obj.attributes.get(
            self.quest_storage_attribute_key,
            category=self.quest_storage_attribute_category,
            default={},
        )
        # instantiate all quests
        for quest_key, quest_class in self.quest_classes.items():
            self.quests[quest_key] = quest_class(self.obj)

    def _save(self):
        self.obj.attributes.add(
            self.quest_storage_attribute_key,
            self.quest_classes,
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
        return bool(self.quests.get(quest_key))

    def get(self, quest_key):
        """
        Get the quest stored on character, if any.

        Args:
            quest_key (str): The name of the quest to check for.

        Returns:
            EvAdventureQuest or None: The quest stored, or None if
                Character is not on this quest.

        """
        return self.quests.get(quest_key)

    def all(self):
        """
        Get all quests stored on character.

        Returns:
            list: All quests stored on character.

        """
        return list(self.quests.values())

    def add(self, quest_class):
        """
        Add a new quest

        Args:
            quest_class (EvAdventureQuest): The quest class to start.

        """
        self.quest_classes[quest_class.key] = quest_class
        self.quests[quest_class.key] = quest_class(self.obj)
        self._save()

    def remove(self, quest_key):
        """
        Remove a quest. If not complete, it will be abandoned.

        Args:
            quest_key (str): The quest to remove.

        """
        quest = self.quests.pop(quest_key, None)
        if not quest.is_completed:
            # make sure to cleanup
            quest.abandon()
        self.quest_classes.pop(quest_key, None)
        self.quests.pop(quest_key, None)
        self._save()

    def save_quest_data(self, quest_key):
        """
        Save data for a quest. We store this on the quester as well as updating the quest itself.

        Args:
            quest_key (str): The quest to save data for. The data is assumed to be stored on the
                quest as `.data` (a dict).

        """
        quest = self.get(quest_key)
        if quest:
            self.obj.attributes.add(
                self.quest_data_attribute_template.format(quest_key=quest_key),
                quest.data,
                category=self.quest_data_attribute_category,
            )

    def load_quest_data(self, quest_key):
        """
        Load data for a quest.

        Args:
            quest_key (str): The quest to load data for.

        Returns:
            dict: The data stored for the quest.

        """
        return self.obj.attributes.get(
            self.quest_data_attribute_template.format(quest_key=quest_key),
            category=self.quest_data_attribute_category,
            default={},
        )


class CmdQuests(Command):
    """
    List all quests and their statuses as well as get info about the status of
    a specific quest.

    Usage:
        quests
        quest <questname>

    """

    key = "quests"
    aliases = ["quest"]

    def parse(self):
        self.quest_name = self.args.strip()

    def func(self):
        if self.quest_name:
            quest = self.caller.quests.get(self.quest_name)
            if not quest:
                self.msg(f"Quest {self.quest_name} not found.")
                return
            self.msg(f"Quest {quest.key}: {quest.status}\n{quest.help()}")
            return

        quests = self.caller.quests.all()
        if not quests:
            self.msg("No quests.")
            return

        for quest in quests:
            self.msg(f"Quest {quest.key}: {quest.status}")
