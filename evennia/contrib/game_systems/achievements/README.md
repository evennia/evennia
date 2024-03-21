# Achievements

A simple, but reasonably comprehensive, system for tracking achievements. Achievements are defined using ordinary Python dicts, reminiscent of the core prototypes system, and while it's expected you'll use it only on Characters or Accounts, they can be tracked for any typeclassed object.

## Installation

Once you've defined your achievement dicts in a module, assign that module to the `ACHIEVEMENT_CONTRIB_MODULES` setting in your settings.py

Optionally, you can specify what attribute achievement progress is stored in, with the setting `ACHIEVEMENT_CONTRIB_ATTRIBUTE`. By default it's just "achievements".

There is also a command available to let players check their achievements - `from evennia.contrib.game_systems.achievements.achievements import CmdAchieve` and then add `CmdAchieve` to your default Character and/or Account cmdsets.

#### Settings examples

One module:

```python
# in server/conf/settings.py

ACHIEVEMENT_CONTRIB_MODULES = "world.achievements"
```

Multiple modules, with a custom-defined attribute:

```python
# in server/conf/settings.py

ACHIEVEMENT_CONTRIB_MODULES = ["world.crafting.achievements", "world.mobs.achievements"]
ACHIEVEMENT_CONTRIB_ATTRIBUTE = "achieve_progress"
```

A custom-defined attribute including category:

```python
# in server/conf/settings.py

ACHIEVEMENT_CONTRIB_MODULES = "world.achievements"
ACHIEVEMENT_CONTRIB_ATTRIBUTE = ("achievements", "systems")
```

## Usage

### Defining your achievements

This achievement system is designed to use ordinary dicts for the achievement data - however, there are certain keys which, if present in the dict, define how the achievement is progressed or completed.

- **name** (str): The searchable name for the achievement. Doesn't need to be unique.
- **desc** (str): A longer description of the achievement. Common uses for this would be flavor text or hints on how to complete it.
- **category** (str): The type of actions this achievement tracks. e.g. purchasing 10 apples might have a category of "buy", or killing 10 rats might have a category of "defeat".
- **tracking** (str or list): The *specific* things this achievement tracks. e.g. the previous example of killing rats might have a `"tracking"` value of `"rat"`. An achievement can also track multiple things: instead of only tracking buying apples, you might want to track apples and pears. For that situation, you can assign it to a list of values to check against: e.g. `["apple", "pear"]`
- **tracking_type** (str): *Default value if unset: `"sum"`* There are two valid tracking types: "sum" (which is the default) and "separate". `"sum"` will increment a single counter every time any of the tracked items match. `"separate"` will have a counter for each individual item in the tracked items. (This is really only useful when `"tracking"` is a list.)
- **count** (int): *Default value if unset: 1* The number of tallies this achievement's requirements need to build up in order to complete the achievement. e.g. the previous example of killing rats would have a `"count"` value of `10`. For achievements using the "separate" tracking type, *each* item being tracked must tally up to this number to be completed
- **prereqs** (str or list): The *keys* of any achievements which must be completed before this achievement can start tracking progress. An achievement's key is the variable name it's assigned to in your achievement module.

You can add any additional keys to your achievement dicts that you want, and they'll be included with all the rest of the achievement data when using the contrib's functions. This could be useful if you want to add extra metadata to your achievements for your own features.

#### Examples

A simple achievement which you can get just for logging in the first time. This achievement has no prerequisites and it only needs to be fulfilled once to complete, so it doesn't need to define most of the keys.
```python
# This achievement has the unique key of "FIRST_LOGIN_ACHIEVE"
FIRST_LOGIN_ACHIEVE = {
    "name": "Welcome!", # the searchable, player-friendly display name
    "desc": "We're glad to have you here.", # the longer description
    "category": "login", # the type of action this tracks
    "tracking": "first", # the specific login action
}
```

An achievement for killing 10 rats, and another for killing 10 *dire* rats which requires the "kill 10 rats" achievement to be completed first.
```python
ACHIEVE_TEN_RATS = {
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

### `track_achievements`

The primary mechanism for using the achievements system is the `track_achievements` function. In any actions or functions in your game's mechanics which you might want to track in an achievement, add a call to `track_achievements` to update the achievement progress for that individual.

For example, you might have a collection achievement for buying 10 apples, and a general `buy` command players could use. In your `buy` command, after the purchase is completed, you could add the following line:

```python
    track_achievements(self.caller, "buy", obj.name, count=quantity)
```

In this case, `obj` is the fruit that was just purchased, and `quantity` is the amount they bought.

The `track_achievements` function does also return a value: an iterable of keys for any achievements which were newly completed by that update. You can ignore this value, or you can use it to e.g. send a message to the player with their latest achievements.

### The `achievements` command

The contrib's provided command, `CmdAchieve`, aims to be usable as-is, with multiple switches to filter achievements by various progress statuses and the ability to search by achievement names.

To make it easier to integrate into your own particular game (e.g. accommodating some of that extra achievement data you might have added), the code for formatting a particular achievement's data for display is in `CmdAchieve.format_achievement`, making it easy to overload for your custom display styling without reimplementing the whole command.
