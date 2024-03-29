# Achievements

A simple, but reasonably comprehensive, system for tracking achievements. Achievements are defined using ordinary Python dicts, reminiscent of the core prototypes system, and while it's expected you'll use it only on Characters or Accounts, they can be tracked for any typeclassed object.

The contrib provides several functions for tracking and accessing achievements, as well as a basic in-game command for viewing achievement status.

## Creating achievements

This achievement system is designed to use ordinary dicts for the achievement data - however, there are certain keys which, if present in the dict, define how the achievement is progressed or completed.

- **key** (str): *Default value if unset: the variable name.* The unique, case-insensitive key identifying this achievement.
- **name** (str): The searchable name for the achievement. Doesn't need to be unique.
- **desc** (str): A longer description of the achievement. Common uses for this would be flavor text or hints on how to complete it.
- **category** (str): The category of conditions which this achievement tracks. It will most likely be an action and you will most likely specify it based on where you're checking from. e.g. killing 10 rats might have a category of "defeat", which you'd then check from your code that runs when a player defeats something.
- **tracking** (str or list): The *specific* condition this achievement tracks. e.g. the previous example of killing rats might have a `"tracking"` value of `"rat"`. This value will most likely be taken from a specific object in your code, like a tag on the defeated object, or the ID of a visited location. An achievement can also track multiple things: instead of only tracking buying apples, you might want to track apples and pears. For that situation, you can assign it to a list of values to check against: e.g. `["apple", "pear"]`
- **tracking_type** (str): *Default value if unset: `"sum"`* There are two valid tracking types: "sum" (which is the default) and "separate". `"sum"` will increment a single counter every time any of the tracked items match. `"separate"` will have a counter for each individual item in the tracked items. (This is really only useful when `"tracking"` is a list.)
- **count** (int): *Default value if unset: 1* The number of tallies this achievement's requirements need to build up in order to complete the achievement. e.g. the previous example of killing rats would have a `"count"` value of `10`. For achievements using the "separate" tracking type, *each* item being tracked must tally up to this number to be completed
- **prereqs** (str or list): The *keys* of any achievements which must be completed before this achievement can start tracking progress. An achievement's key is the variable name it's assigned to in your achievement module.

You can add any additional keys to your achievement dicts that you want, and they'll be included with all the rest of the achievement data when using the contrib's functions. This could be useful if you want to add extra metadata to your achievements for your own features.

### Example achievements

A simple achievement which you can get just for logging in the first time. This achievement has no prerequisites and it only needs to be fulfilled once to complete, so it doesn't need to define most of the fields.
```python
# This achievement has the unique key of "first_login_achieve"
FIRST_LOGIN_ACHIEVE = {
    "name": "Welcome!", # the searchable, player-friendly display name
    "desc": "We're glad to have you here.", # the longer description
    "category": "login", # the type of action this tracks
    "tracking": "first", # the specific login action
}
```

An achievement for killing 10 rats, and another for killing 10 *dire* rats which requires the "kill 10 rats" achievement to be completed first.
```python
# This achievement has the unique key of "ten_rats" instead of "achieve_ten_rats"
ACHIEVE_TEN_RATS = {
    "key": "ten_rats",
    "name": "The Usual",
    "desc": "Why do all these inns have rat problems?",
    "category": "defeat",
    "tracking": "rat",
    "count": 10,
}

ACHIEVE_DIRE_RATS = {
    "name": "Once More, But Bigger",
    "desc": "Somehow, normal rats just aren't enough any more.",
    "category": "defeat",
    "tracking": "dire rat",
    "count": 10,
    "prereqs": "ACHIEVE_TEN_RATS",
}
```

An achievement for buying 5 each of apples, oranges, and pears.
```python
FRUIT_BASKET_ACHIEVEMENT = {
    "name": "A Fan of Fruit", # note, there is no desc here - that's allowed!
    "category": "buy",
    "tracking": ("apple", "orange", "pear"),
    "count": 5,
    "tracking_type": "separate",
}
```


## Installation

Once you've defined your achievement dicts in one or more module, assign that module to the `ACHIEVEMENT_CONTRIB_MODULES` setting in your settings.py

> Note: If any achievements have the same unique key, whichever conflicting achievement is processed *last* will be the only one loaded into the game. Case is ignored, so "ten_rats", "Ten_Rats" and "TEN_RATS" will conflict. "ten_rats" and "ten rats" will not.

```python
# in server/conf/settings.py

ACHIEVEMENT_CONTRIB_MODULES = ["world.achievements"]
```

There is also a command available to let players check their achievements - `from evennia.contrib.game_systems.achievements.achievements import CmdAchieve` and then add `CmdAchieve` to your default Character and/or Account cmdsets.

**Optional** - The achievements contrib stores individual progress data on the `achievements` attribute by default, visible via `obj.db.attributes`. You can change this in your settings if necessary, e.g.:

```py
# in settings.py

ACHIEVEMENT_CONTRIB_ATTRIBUTE = ("achievement_data", "systems")
```

## Usage

### `track_achievements`

The primary mechanism for using the achievements system is the `track_achievements` function. In any actions or functions in your game's mechanics which you might want to track in an achievement, add a call to `track_achievements` to update the achievement progress for that individual.

Using the "kill 10 rats" example achievement from earlier, you might have some code that triggers when a character is defeated: for the sake of example, we'll pretend we have an `at_defeated` method on the base Object class that gets called when the Object is defeated.

Adding achievement tracking to it could then look something like this:

```python
from contrib.game_systems.achievements import track_achievements

class Object(ObjectParent, DefaultObject):
    # ....

    def at_defeated(self, victor):
        """called when this object is defeated in combat"""
        # we'll use the "mob_type" tag category as the tracked information for achievements
        mob_type = self.tags.get(category="mob_type")
        track_achievements(victor, category="defeated", tracking=mob_type, count=1)
```

If a player defeats something tagged `rat` with a tag category of `mob_type`, it'd now count towards the rat-killing achievement.

The `track_achievements` function does also return a value: an iterable of keys for any achievements which were newly completed by that update. You can ignore this value, or you can use it to e.g. send a message to the player with their latest achievements.

### `search_achievement`

A utility function for searching achievements by name or description. It handles partial matching and returns a dictionary of matching achievements. The provided `achievement` command for in-game uses this function to find matching achievements from user inputs.

#### Example:
```py
>>> from evennia.contrib.game_systems.achievements import search_achievement
>>> search_achievement("fruit")
{'fruit_basket_achievement': {'name': 'A Fan of Fruit', 'category': 'buy', 'tracking': ('apple', 'orange', 'pear'), 'count': 5, 'tracking_type': 'separate'}}
>>> search_achievement("rat")
{'ten_rats': {'key': 'ten_rats', 'name': 'The Usual', 'desc': 'Why do all these inns have rat problems?', 'category': 'defeat', 'tracking': 'rat', 'count': 10}, {'achieve_dire_rats': {'name': 'Once More, But Bigger', 'desc': 'Somehow, normal rats just aren't enough any more.', 'category': 'defeat', 'tracking': 'dire rat', 'count': 10, 'prereqs': "ACHIEVE_TEN_RATS"}}
```

### `get_achievement`

A utility function for retrieving a specific achievement's data from the achievement's unique key. It cannot be used for searching, but if you already have an achievement's key - for example, from the results of `track_achievements` - you can retrieve the rest of its data this way.

#### Example:

```py
from evennia.contrib.game_systems.achievements import get_achievement

def toast(achiever, completed_list):
	if completed_list:
		# we've completed some achievements!
		completed_data = [get_achievement(key) for key in args]
		names = [data.get('name') for data in completed]
		achiever.msg(f"|wAchievement Get!|n {iter_to_str(name for name in names if name)}"))
```

### The `achievements` command

The contrib's provided command, `CmdAchieve`, aims to be usable as-is, with multiple switches to filter achievements by various progress statuses and the ability to search by achievement names.

To make it easier to integrate into your own particular game (e.g. accommodating some of that extra achievement data you might have added), the code for formatting a particular achievement's data for display is in `CmdAchieve.format_achievement`, making it easy to overload for your custom display styling without reimplementing the whole command.

#### Example output

```
> achievements
The Usual
Why do all these inns have rat problems?
70% complete
A Fan of Fruit

Not Started
```
```
> achievements/progress
The Usual
Why do all these inns have rat problems?
70% complete
```
```
> achievements/done
There are no matching achievements.
```
