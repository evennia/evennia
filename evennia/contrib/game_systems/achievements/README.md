# Achievements

A simple, but reasonably comprehensive, system for tracking achievements. Achievements are defined using ordinary Python dicts, reminiscent of the core prototypes system, and while it's expected you'll use it only on Characters or Accounts, they can be tracked for any typeclassed object.

The contrib provides several functions for tracking and accessing achievements, as well as a basic in-game command for viewing achievement status.

## Installation

This contrib requires creation one or more module files containing your achievement data, which you then add to your settings file to make them available.

> See the section below on "Creating Achievements" for what to put in this module.

```python
# in server/conf/settings.py

ACHIEVEMENT_CONTRIB_MODULES = ["world.achievements"]
```

To allow players to check their achievements, you'll also want to add the `achievements` command to your default Character and/or Account command sets.

```python
# in commands/default_cmdsets.py

from evennia.contrib.game_systems.achievements.achievements import CmdAchieve

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        # ...
        self.add(CmdAchieve)
```

**Optional** - The achievements contrib stores individual progress data on the `achievements` attribute by default, visible via `obj.db.achievements`. You can change this by assigning an attribute (key, category) tuple to the setting `ACHIEVEMENT_CONTRIB_ATTRIBUTE`

Example:
```py
# in settings.py

ACHIEVEMENT_CONTRIB_ATTRIBUTE = ("progress_data", "achievements")
```


## Creating achievements

An achievement is represented by a simple python dictionary defined at the module level in your achievements module(s).

Each achievement requires certain specific keys to be defined to work properly, along with several optional keys that you can use to override defaults.

> Note: Any additional keys not described here are included in the achievement data when you access those acheivements through the contrib, so you can easily add your own extended features.

#### Required keys

- **name** (str): The searchable name for the achievement. Doesn't need to be unique.
- **category** (str): The category, or general type, of condition which can progress this achievement. Usually this will be a player action or result. e.g. you would use a category of "defeat" on an achievement for killing 10 rats.
- **tracking** (str or list): The specific subset of condition which can progress this achievement. e.g. you would use a tracking value of "rat" on an achievement for killing 10 rats. An achievement can also track multiple things, for example killing 10 rats or snakes. For that situation, assign a list of all the values to check against, e.g. `["rat", "snake"]`

#### Optional keys

- **key** (str): *Default value if unset: the variable name.* The unique, case-insensitive key identifying this achievement.
> Note: If any achievements have the same unique key, only *one* will be loaded. It is case-insensitive, but punctuation is respected - "ten_rats", "Ten_Rats" and "TEN_RATS" will conflict, but "ten_rats" and "ten rats" will not.
- **desc** (str): A longer description of the achievement. Common uses for this would be flavor text or hints on how to complete it.
- **count** (int): *Default value if unset: 1* The number of tallies this achievement's requirements need to build up in order to complete the achievement. e.g. killing 10 rats would have a `"count"` value of `10`. For achievements using the "separate" tracking type, *each* item being tracked must tally up to this number to be completed.
- **tracking_type** (str): *Default value if unset: `"sum"`* There are two valid tracking types: "sum" (which is the default) and "separate". `"sum"` will increment a single counter every time any of the tracked items match. `"separate"` will have a counter for each individual item in the tracked items. ("See the Example Achievements" section for a demonstration of the difference.)
- **prereqs** (str or list): The *keys* of any achievements which must be completed before this achievement can start tracking progress.


### Example achievements

A simple achievement which you can get just for logging in the first time. This achievement has no prerequisites and it only needs to be fulfilled once to complete.
```python
# This achievement has the unique key of "first_login_achieve"
FIRST_LOGIN_ACHIEVE = {
    "name": "Welcome!", # the searchable, player-friendly display name
    "desc": "We're glad to have you here.", # the longer description
    "category": "login", # the type of action this tracks
    "tracking": "first", # the specific login action
}
```

An achievement for killing a total of 10 rats, and another for killing 10 *dire* rats which requires the "kill 10 rats" achievement to be completed first. The dire rats achievement won't begin tracking *any* progress until the first achievement is completed.
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

An achievement for buying a total of 5 of apples, oranges, *or* pears. The "sum" tracking types means that all items are tallied together - so it can be completed by buying 5 apples, or 5 pears, or 3 apples, 1 orange and 1 pear, or any other combination of those three fruits that totals to 5.

```python
FRUIT_FAN_ACHIEVEMENT = {
    "name": "A Fan of Fruit", # note, there is no desc here - that's allowed!
    "category": "buy",
    "tracking": ("apple", "orange", "pear"),
    "count": 5,
    "tracking_type": "sum", # this is the default, but it's included here for clarity
}
```

An achievement for buying 5 *each* of apples, oranges, and pears. The "separate" tracking type means that each of the tracked items is tallied independently of the other items - so you will need 5 apples, 5 oranges, and 5 pears.
```python
FRUIT_BASKET_ACHIEVEMENT = {
    "name": "Fruit Basket",
    "desc": "One kind of fruit just isn't enough.",
    "category": "buy",
    "tracking": ("apple", "orange", "pear"),
    "count": 5,
    "tracking_type": "separate",
}
```


## Usage

The two main things you'll need to do in order to use the achievements contrib in your game are **tracking achievements** and **getting achievement information**. The first is done with the function `track_achievements`; the second can be done with `search_achievement` or `get_achievement`.

### Tracking achievements

#### `track_achievements`

In any actions or functions in your game's mechanics which you might want to track in an achievement, add a call to `track_achievements` to update that player's achievement progress.

Using the "kill 10 rats" example achievement from earlier, you might have some code that triggers when a character is defeated: for the sake of example, we'll pretend we have an `at_defeated` method on the base Object class that gets called when the Object is defeated.

Adding achievement tracking to it could then look something like this:

```python
# in typeclasses/objects.py

from contrib.game_systems.achievements import track_achievements

class Object(ObjectParent, DefaultObject):
    # ....

    def at_defeated(self, victor):
        """called when this object is defeated in combat"""
        # we'll use the "mob_type" tag-category as the tracked info
        # this way we can have rats named "black rat" and "brown rat" that are both rats
        mob_type = self.tags.get(category="mob_type")
        # only one mob was defeated, so we include a count of 1
        track_achievements(victor, category="defeated", tracking=mob_type, count=1)
```

If a player defeats something tagged `rat` with a tag category of `mob_type`, it'd now count towards the rat-killing achievement.

You can also have the tracking information hard-coded into your game, for special or unique situations. The achievement described earlier, `FIRST_LOGIN_ACHIEVE`, for example, would be tracked like this:

```py
# in typeclasses/accounts.py
from contrib.game_systems.achievements import track_achievements

class Account(DefaultAccount):
    # ...

    def at_first_login(self, **kwargs):
        # this function is only called on the first time the account logs in
        # so we already know and can just tell the tracker that this is the first
        track_achievements(self, category="login", tracking="first")
```

The `track_achievements` function does also return a value: an iterable of keys for any achievements which were newly completed by that update. You can ignore this value, or you can use it to e.g. send a message to the player with their latest achievements.

### Getting achievements

The main method for getting a specific achievement's information is `get_achievement`, which takes an already-known achievement key and returns the data for that one achievement.

For handling more variable and player-friendly input, however, there is also `search_achievement`, which does partial matching on not just the keys, but also the display names and descriptions for the achievements.

#### `get_achievement`

A utility function for retrieving a specific achievement's data from the achievement's unique key. It cannot be used for searching, but if you already have an achievement's key - for example, from the results of `track_achievements` - you can retrieve its data this way.

#### Example:

```py
from evennia.contrib.game_systems.achievements import get_achievement

def toast(achiever, completed_list):
    if completed_list:
        # `completed_data` will be a list of dictionaries - unrecognized keys return empty dictionaries
        completed_data = [get_achievement(key) for key in args]
        names = [data.get('name') for data in completed]
        achiever.msg(f"|wAchievement Get!|n {iter_to_str(name for name in names if name)}"))
```

#### `search_achievement`

A utility function for searching achievements by name or description. It handles partial matching and returns a dictionary of matching achievements. The provided `achievement` command for in-game uses this function to find matching achievements from user inputs.

#### Example:

The first example does a search for "fruit", which returns the fruit medley achievement as it contains "fruit" in the key and name.

The second example searches for "usual", which returns the ten rats achievement due to its display name.

```py
>>> from evennia.contrib.game_systems.achievements import search_achievement
>>> search_achievement("fruit")
{'fruit_basket_achievement': {'name': 'Fruit Basket', 'desc': "One kind of fruit just isn't enough.", 'category': 'buy', 'tracking': ('apple', 'orange', 'pear'), 'count': 5, 'tracking_type': 'separate'}}
>>> search_achievement("usual")
{'ten_rats': {'key': 'ten_rats', 'name': 'The Usual', 'desc': 'Why do all these inns have rat problems?', 'category': 'defeat', 'tracking': 'rat', 'count': 10}}
```

### The `achievements` command

The contrib's provided command, `CmdAchieve`, aims to be usable as-is, with multiple switches to filter achievements by various progress statuses and the ability to search by achievement names.

To make it easier to customize for your own game (e.g. displaying some of that extra achievement data you might have added), the format and style code is split out from the command logic into the `format_achievement` method and the `template` attribute, both on `CmdAchieve`

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
