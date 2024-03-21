"""
Achievements

This provides a system for adding and tracking player achievements in your game.

Achievements are defined as dicts, loosely similar to the prototypes system.

An example of an achievement dict:

    EXAMPLE_ACHIEVEMENT = {
        "name": "Some Achievement",
        "desc": "This is not a real achievement.",
        "category": "crafting",
        "tracking": "box",
        "count": 5,
        "prereqs": "ANOTHER_ACHIEVEMENT",
    }

The recognized fields for an achievement are:

- name (str): The name of the achievement. This is not the key and does not need to be unique.
- desc (str): The longer description of the achievement. Common uses for this would be flavor text
        or hints on how to complete it.
- category (str): The type of things this achievement tracks. e.g. visiting 10 locations might have
        a category of "post move", or killing 10 rats might have a category of "defeat".
- tracking (str or list): The *specific* thing this achievement tracks. e.g. the above example of
        10 rats, the tracking field would be "rat".
- tracking_type: The options here are "sum" and "separate". "sum" means that matching any tracked
        item will increase the total. "separate" means all tracked items are counted individually.
        This is only useful when tracking is a list. The default is "sum".
- count (int): The total tallies the tracked item needs for this to be completed. e.g. for the rats
        example, it would be 10. The default is 1
- prereqs (str or list): An optional achievement key or list of keys that must be completed before
        this achievement is available.

To add achievement tracking, put `track_achievements` in your relevant hooks.

Example:

    def at_use(self, user, **kwargs):
        # track this use for any achievements about using an object named our name
        finished_achievements = track_achievements(user, category="use", tracking=self.key)

Despite the example, it's likely to be more useful to reference a tag than the object's key.
"""

from collections import Counter
from django.conf import settings
from evennia.utils import logger
from evennia.utils.utils import all_from_module, is_iter, make_iter, string_partial_matching
from evennia.utils.evmore import EvMore
from evennia.commands.default.muxcommand import MuxCommand

# this is either a string of the attribute name, or a tuple of strings of the attribute name and category
_ACHIEVEMENT_ATTR = make_iter(getattr(settings, "ACHIEVEMENT_ATTRIBUTE", "achievements"))

_ACHIEVEMENT_INFO = None


def _load_achievements():
    """
    Loads the achievement data from settings, if it hasn't already been loaded.

    Returns:
        achievements (dict) - the loaded achievement info
    """
    global _ACHIEVEMENT_INFO
    if _ACHIEVEMENT_INFO is None:
        _ACHIEVEMENT_INFO = {}
        if modules := getattr(settings, "ACHIEVEMENT_MODULES", None):
            for module_path in make_iter(modules):
                _ACHIEVEMENT_INFO |= {
                    key.lower(): val
                    for key, val in all_from_module(module_path).items()
                    if isinstance(val, dict)
                }
        else:
            logger.log_warn("No achievement modules have been added to settings.")
    return _ACHIEVEMENT_INFO


def track_achievements(achiever, category=None, tracking=None, count=1, **kwargs):
    """
    Update and check achievement progress.

    Args:
        achiever (Account or Character):  The entity that's collecting achievement progress.

    Keyword args:
        category (str or None):  The category of an achievement.
        tracking (str or None):  The specific item being tracked in the achievement.

    Returns:
        completed (tuple):  The keys of any achievements that were completed by this update.
    """
    if not (all_achievements := _load_achievements()):
        # there are no achievements available, there's nothing to do
        return tuple()

    # split out the achievement attribute info
    attr_key = _ACHIEVEMENT_ATTR[0]
    attr_cat = _ACHIEVEMENT_ATTR[1] if len(_ACHIEVEMENT_ATTR) > 1 else None

    # get the achiever's progress data, and detach from the db so we only read/write once
    if progress_data := achiever.attributes.get(attr_key, default={}, category=attr_cat):
        progress_data = progress_data.deserialize()

    # filter all of the achievements down to the relevant ones
    relevant_achievements = (
        (key, val)
        for key, val in all_achievements.items()
        if (not category or category in make_iter(val["category"]))  # filter by category
        and (not tracking or tracking in make_iter(val["tracking"]))  # filter by tracked item
        and not progress_data.get(key, {}).get("completed")  # filter by completion status
        and all(
            progress_data.get(prereq, {}).get("completed")
            for prereq in make_iter(val.get("prereqs", []))
        )  # filter by prereqs
    )

    completed = []
    # loop through all the relevant achievements and update the progress data
    for achieve_key, achieve_data in relevant_achievements:
        if target_count := achieve_data.get("count"):
            # check if we need to track things individually or not
            separate_totals = achieve_data.get("tracking_type", "sum") == "separate"
            if achieve_key not in progress_data:
                progress_data[achieve_key] = {}
            if separate_totals and is_iter(achieve_data["tracking"]):
                # do the special handling for tallying totals separately
                i = achieve_data["tracking"].index(tracking)
                if "progress" not in progress_data[achieve_key]:
                    # initialize the item counts
                    progress_data[achieve_key]["progress"] = [
                        0 for _ in range(len(achieve_data["tracking"]))
                    ]
                # increment the matching index count
                progress_data[achieve_key]["progress"][i] += count
                # have we reached the target on all items? if so, we've completed it
                if min(progress_data[achieve_key]["progress"]) >= target_count:
                    completed.append(achieve_key)
            else:
                progress_count = progress_data[achieve_key].get("progress", 0)
                # update the achievement data
                progress_data[achieve_key]["progress"] = progress_count + count
                # have we reached the target? if so, we've completed it
                if progress_data[achieve_key]["progress"] >= target_count:
                    completed.append(achieve_key)
        else:
            # no count means you just need to do the thing to complete it
            completed.append(achieve_key)

    for key in completed:
        if key not in progress_data:
            progress_data[key] = {}
        progress_data[key]["completed"] = True

    # write the updated progress back to the achievement attribute
    achiever.attributes.add(attr_key, progress_data, category=attr_cat)

    # return all the achievements we just completed
    return tuple(completed)


def get_achievement(key):
    """
    Get an achievement by its key.

    Args:
        key (str):  The achievement key. This is the variable name the achievement dict is assigned to.

    Returns:
        dict or None: The achievement data, or None if it doesn't exist
    """
    if not (all_achievements := _load_achievements()):
        # there are no achievements available, there's nothing to do
        return None
    if data := all_achievements.get(key):
        return dict(data)
    return None


def all_achievements():
    """
    Returns a dict of all achievements in the game.
    """
    # we do this to prevent accidental in-memory modification of reference data
    return dict((key, dict(val)) for key, val in _load_achievements().items())


def get_progress(achiever, key):
    """
    Retrieve the progress data on a particular achievement for a particular achiever.

    Args:
        achiever (Account or Character):  The entity tracking achievement progress.
        key (str): The achievement key

    Returns:
        data (dict): The progress data
    """
    # split out the achievement attribute info
    attr_key = _ACHIEVEMENT_ATTR[0]
    attr_cat = _ACHIEVEMENT_ATTR[1] if len(_ACHIEVEMENT_ATTR) > 1 else None
    if progress_data := achiever.attributes.get(attr_key, default={}, category=attr_cat):
        # detach the data from the db to avoid data corruption and return the data
        return progress_data.deserialize().get(key, {})
    else:
        # just return an empty dict
        return {}


def search_achievement(search_term):
    """
    Search for an achievement by name.

    Args:
        search_term (str):  The string to search for.

    Returns:
        results (dict):  A dict of key:data pairs of matching achievements.
    """
    if not (all_achievements := _load_achievements()):
        # there are no achievements available, there's nothing to do
        return {}
    keys, names = zip(*((key, val["name"]) for key, val in all_achievements.items()))
    indices = string_partial_matching(names, search_term)

    return dict((keys[i], dict(all_achievements[keys[i]])) for i in indices)


class CmdAchieve(MuxCommand):
    """
    view achievements

    Usage:
        achievements[/switches] [args]

    Switches:
        all          View all achievements, including locked ones.
        completed    View achievements you've completed.
        progress     View achievements you have partially completed

    Check your achievement statuses or browse the list. Providing a command argument
    will search all your currently unlocked achievements for matches, and the switches
    will filter the list to something other than "all unlocked". Combining a command
    argument with a switch will search only in that list.

    Examples:
        achievements apples
        achievements/all
        achievements/progress rats
    """

    key = "achievements"
    aliases = (
        "achievement",
        "achieve",
    )
    switch_options = ("progress", "completed", "done", "all")

    def format_achievement(self, achievement_data):
        """
        Formats the raw achievement data for display.

        Args:
            achievement_data (dict):  The data to format.

        Returns
            str: The display string to be sent to the caller.

        """
        template = """\
|w{name}|n
{desc}
{status}
""".rstrip()

        if achievement_data.get("completed"):
            # it's done!
            status = "|gCompleted!|n"
        elif not achievement_data.get("progress"):
            status = "|yNot Started|n"
        else:
            count = achievement_data.get("count")
            # is this achievement tracking items separately?
            if is_iter(achievement_data["progress"]):
                # we'll display progress as how many items have been completed
                completed = Counter(val >= count for val in achievement_data["progress"])[True]
                pct = (completed * 100) // count
            else:
                # we display progress as the percent of the total count
                pct = (achievement_data["progress"] * 100) // count
            status = f"{pct}% complete"

        return template.format(
            name=achievement_data.get("name", ""),
            desc=achievement_data.get("desc", ""),
            status=status,
        )

    def func(self):
        if self.args:
            # we're doing a name lookup
            if not (achievements := search_achievement(self.args.strip())):
                self.msg(f"Could not find any achievements matching '{self.args.strip()}'.")
                return
        else:
            # we're checking against all achievements
            if not (achievements := all_achievements()):
                self.msg("There are no achievements in this game.")
                return

        # split out the achievement attribute info
        attr_key = _ACHIEVEMENT_ATTR[0]
        attr_cat = _ACHIEVEMENT_ATTR[1] if len(_ACHIEVEMENT_ATTR) > 1 else None

        # get the achiever's progress data, and detach from the db so we only read once
        if progress_data := self.caller.attributes.get(attr_key, default={}, category=attr_cat):
            progress_data = progress_data.deserialize()
        # if the caller is not an account, we get their account progress too
        if self.caller != self.account:
            if account_progress := self.account.attributes.get(
                attr_key, default={}, category=attr_cat
            ):
                progress_data |= account_progress.deserialize()

        # go through switch options
        # we only show achievements that are in progress
        if "progress" in self.switches:
            # we filter our data to incomplete achievements, and combine the base achievement data into it
            achievement_data = {
                key: achievements[key] | data
                for key, data in progress_data.items()
                if not data.get("completed")
            }

        # we only show achievements that are completed
        elif "completed" in self.switches or "done" in self.switches:
            # we filter our data to finished achievements, and combine the base achievement data into it
            achievement_data = {
                key: achievements[key] | data
                for key, data in progress_data.items()
                if data.get("completed")
            }

        # we show ALL achievements
        elif "all" in self.switches:
            # we merge our progress data into the full dict of achievements
            achievement_data = achievements | progress_data

        # we show all of the currently available achievements regardless of progress status
        else:
            achievement_data = {
                key: data
                for key, data in achievements.items()
                if all(
                    progress_data.get(prereq, {}).get("completed")
                    for prereq in make_iter(data.get("prereqs", []))
                )
            } | progress_data

        if not achievement_data:
            self.msg("There are no matching achievements.")
            return

        achievement_str = "\n".join(
            self.format_achievement(data) for _, data in achievement_data.items()
        )
        EvMore(self.caller, achievement_str)
