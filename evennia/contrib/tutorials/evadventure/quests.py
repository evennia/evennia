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

    each step is represented by two methods on this object:
    check_<name> and complete_<name>

    """
    # name + category must be globally unique. They are
    # queried as name:category or just name, if category is empty.
    name = ""
    category = ""
    # example: steps = ["start", "step1", "step2", "end"]
    steps = []

    def __init__(self):
        step = 0

    def check():
        pass


    def progress(self, quester, *args, **kwargs):
        """

        """

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
    quest_storage_attribute = "_quests"
    quest_storage_attribute_category = "evadventure"

    def __init__(self, obj):
        self.obj = obj
        self.storage = obj.attributes.get(
            self.quest_storage_attribute,
            category=self.quest_storage_attribute_category,
            default={}
        )

    def quest_storage_key(self, name, category):
        return f"{name}:{category}"

    def has(self, quest_name, quest_category=""):
        """
        Check if a given quest is registered with the Character.

        Args:
            quest_name (str): The name of the quest to check for.
            quest_category (str, optional): Quest category, if any.

        Returns:
            bool: If the character is following this quest or not.

        """
        return bool(self.get(quest_name, quest_category))

    def get(self, quest_name, quest_category=""):
        """
        Get the quest stored on character, if any.

        Args:
            quest_name (str): The name of the quest to check for.
            quest_category (str, optional): Quest category, if any.

        Returns:
            EvAdventureQuest or None: The quest stored, or None if
                Character is not on this quest.

        """
        return self.storage.get(self.quest_key(quest_storage_name, quest_category))

    def add(self, quest, autostart=True):
        """
        Add a new quest

        Args:
            quest (EvAdventureQuest): The quest to start.
            autostart (bool, optional): If set, the quest will
                start immediately.

        """



