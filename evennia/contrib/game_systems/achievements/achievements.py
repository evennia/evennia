"""
Achievements

This provides a system for adding and tracking player achievements in your game.

Achievements are defined as dicts, loosely similar to the prototypes system.

An example of an achievement dict:

    ACHIEVE_DIRE_RATS = {
        "name": "Once More, But Bigger",
        "desc": "Somehow, normal rats just aren't enough any more.",
        "category": "defeat",
        "tracking": "dire rat",
        "count": 10,
        "prereqs": "ACHIEVE_TEN_RATS",
    }

The recognized fields for an achievement are:

- key (str): The unique, case-insensitive key identifying this achievement. The variable name is
        used by default.
- name (str): The name of the achievement. This is not the key and does not need to be unique.
- desc (str): The longer description of the achievement. Common uses for this would be flavor text
        or hints on how to complete it.
- category (str): The category of conditions which this achievement tracks. It will most likely be
        an action and you will most likely specify it based on where you're checking from.
        e.g. killing 10 rats might have a category of "defeat", which you'd then check from your code
        that runs when a player defeats something.
- tracking (str or list): The specific condition this achievement tracks. e.g. for the above example of
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

    def at_defeated(self, victor):
        # called when this object is defeated in combat
        # we'll use the "mob_type" tag category as the tracked information for achievements
        mob_type = self.tags.get(category="mob_type")
        track_achievements(victor, category="defeated", tracking=mob_type, count=1)

"""

from collections import Counter

from django.conf import settings

from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils import logger
from evennia.utils.evmore import EvMore
from evennia.utils.utils import (
    all_from_module,
    is_iter,
    make_iter,
    string_partial_matching,
)

# this is either a string of the attribute name, or a tuple of strings of the attribute name and category
_ACHIEVEMENT_ATTR = make_iter(getattr(settings, "ACHIEVEMENT_CONTRIB_ATTRIBUTE", "achievements"))
_ATTR_KEY = _ACHIEVEMENT_ATTR[0]
_ATTR_CAT = _ACHIEVEMENT_ATTR[1] if len(_ACHIEVEMENT_ATTR) > 1 else None

# load the achievements data
_ACHIEVEMENT_DATA = {}
if modules := getattr(settings, "ACHIEVEMENT_CONTRIB_MODULES", None):
    for module_path in make_iter(modules):
        module_achieves = {
            val.get("key", key).lower(): val
            for key, val in all_from_module(module_path).items()
            if isinstance(val, dict) and not key.startswith("_")
        }
        if any(key in _ACHIEVEMENT_DATA for key in module_achieves.keys()):
            logger.log_warn(
                "There are conflicting achievement keys! Only the last achievement registered to the key will be recognized."
            )
        _ACHIEVEMENT_DATA |= module_achieves
else:
    logger.log_warn("No achievement modules have been added to settings.")


def _read_player_data(achiever):
    """
    helper function to get a player's achievement data from the database.

    Args:
        achiever (Object or Account):   The achieving entity

    Returns:
        dict:  The deserialized achievement data.
    """
    if data := achiever.attributes.get(_ATTR_KEY, default={}, category=_ATTR_CAT):
        # detach the data from the db
        data = data.deserialize()
    # return the data
    return data or {}


def _write_player_data(achiever, data):
    """
    helper function to write a player's achievement data to the database.

    Args:
        achiever (Object or Account):  The achieving entity
        data (dict):  The full achievement data for this entity.

    Returns:
        None

    Notes:
        This function will overwrite any existing achievement data for the entity.
    """
    achiever.attributes.add(_ATTR_KEY, data, category=_ATTR_CAT)


def track_achievements(achiever, category=None, tracking=None, count=1, **kwargs):
    """
    Update and check achievement progress.

    Args:
        achiever (Account or Character):  The entity that's collecting achievement progress.

    Keyword args:
        category (str or None):  The category of an achievement.
        tracking (str or None):  The specific item being tracked in the achievement.

    Returns:
        tuple:  The keys of any achievements that were completed by this update.
    """
    if not _ACHIEVEMENT_DATA:
        # there are no achievements available, there's nothing to do
        return tuple()

    # get the achiever's progress data
    progress_data = _read_player_data(achiever)

    # filter all of the achievements down to the relevant ones
    relevant_achievements = (
        (key, val)
        for key, val in _ACHIEVEMENT_DATA.items()
        if (not category or category in make_iter(val.get("category", [])))  # filter by category
        and (
            not tracking
            or not val.get("tracking")
            or tracking in make_iter(val.get("tracking", []))
        )  # filter by tracked item
        and not progress_data.get(key, {}).get("completed")  # filter by completion status
        and all(
            progress_data.get(prereq, {}).get("completed")
            for prereq in make_iter(val.get("prereqs", []))
        )  # filter by prereqs
    )

    completed = []
    # loop through all the relevant achievements and update the progress data
    for achieve_key, achieve_data in relevant_achievements:
        if target_count := achieve_data.get("count", 1):
            # check if we need to track things individually or not
            separate_totals = achieve_data.get("tracking_type", "sum") == "separate"
            if achieve_key not in progress_data:
                progress_data[achieve_key] = {}
            if separate_totals and is_iter(achieve_data.get("tracking")):
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
    _write_player_data(achiever, progress_data)

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
    if not _ACHIEVEMENT_DATA:
        # there are no achievements available, there's nothing to do
        return None
    if data := _ACHIEVEMENT_DATA.get(key.lower()):
        return dict(data)
    return None


def all_achievements():
    """
    Returns a dict of all achievements in the game.

    Returns:
      dict
    """
    # we do this to mitigate accidental in-memory modification of reference data
    return dict((key, dict(val)) for key, val in _ACHIEVEMENT_DATA.items())


def get_achievement_progress(achiever, key):
    """
    Retrieve the progress data on a particular achievement for a particular achiever.

    Args:
        achiever (Account or Character):  The entity tracking achievement progress.
        key (str): The achievement key

    Returns:
        dict: The progress data
    """
    if progress_data := _read_player_data(achiever):
        # get the specific key's data
        return progress_data.get(key, {})
    else:
        # just return an empty dict
        return {}


def search_achievement(search_term):
    """
    Search for an achievement containing the search term. If no matches are found in the achievement names, it searches
    in the achievement descriptions.

    Args:
        search_term (str):  The string to search for.

    Returns:
        dict:  A dict of key:data pairs of matching achievements.
    """
    if not _ACHIEVEMENT_DATA:
        # there are no achievements available, there's nothing to do
        return {}
    keys, names, descs = zip(
        *((key, val["name"], val["desc"]) for key, val in _ACHIEVEMENT_DATA.items())
    )
    indices = string_partial_matching(names, search_term)
    if not indices:
        indices = string_partial_matching(descs, search_term)

    return dict((keys[i], dict(_ACHIEVEMENT_DATA[keys[i]])) for i in indices)


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
        "achieves",
    )
    switch_options = ("progress", "completed", "done", "all")

    template = """\
|w{name}|n
{desc}
{status}
""".rstrip()

    def format_achievement(self, achievement_data):
        """
        Formats the raw achievement data for display.

        Args:
            achievement_data (dict):  The data to format.

        Returns
            str: The display string to be sent to the caller.

        """

        if achievement_data.get("completed"):
            # it's done!
            status = "|gCompleted!|n"
        elif not achievement_data.get("progress"):
            status = "|yNot Started|n"
        else:
            count = achievement_data.get("count", 1)
            # is this achievement tracking items separately?
            if is_iter(achievement_data["progress"]):
                # we'll display progress as how many items have been completed
                completed = Counter(val >= count for val in achievement_data["progress"])[True]
                pct = (completed * 100) // len(achievement_data["progress"])
            else:
                # we display progress as the percent of the total count
                pct = (achievement_data["progress"] * 100) // count
            status = f"{pct}% complete"

        return self.template.format(
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

        # get the achiever's progress data
        progress_data = _read_player_data(self.caller)
        if self.caller != self.account:
            progress_data |= _read_player_data(self.account)

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
            achievement_data = {
                key: data | progress_data.get(key, {}) for key, data in achievements.items()
            }

        # we show all of the currently available achievements regardless of progress status
        else:
            achievement_data = {
                key: data | progress_data.get(key, {})
                for key, data in achievements.items()
                if all(
                    progress_data.get(prereq, {}).get("completed")
                    for prereq in make_iter(data.get("prereqs", []))
                )
            }

        if not achievement_data:
            self.msg("There are no matching achievements.")
            return

        achievement_str = "\n".join(
            self.format_achievement(data) for _, data in achievement_data.items()
        )
        EvMore(self.caller, achievement_str)
