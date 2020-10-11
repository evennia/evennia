# Gametime Tutorial


A lot of games use a separate time system we refer to as *game time*. This runs in parallel to what
we usually think of as *real time*.  The game time might run at a different speed, use different
names for its time units or might even use a completely custom calendar. You don't need to rely on a
game time system at all. But if you do, Evennia offers basic tools to handle these various
situations. This tutorial will walk you through these features.

### A game time with a standard calendar

Many games let their in-game time run faster or slower than real time, but still use our normal
real-world calendar. This is common both for games set in present day as well as for games in
historical or futuristic settings. Using a standard calendar has some advantages:

- Handling repetitive actions is much easier, since converting from the real time experience to the
in-game perceived one is easy.
- The intricacies of the real world calendar, with leap years and months of different length etc are
automatically handled by the system.

Evennia's game time features assume a standard calendar (see the relevant section below for a custom
calendar).

#### Setting up game time for a standard calendar

All is done through the settings.  Here are the settings you should use if you want a game time with
a standard calendar:

```python
# in a file settings.py in mygame/server/conf
# The time factor dictates if the game world runs faster (timefactor>1)
# or slower (timefactor<1) than the real world.
TIME_FACTOR = 2.0

# The starting point of your game time (the epoch), in seconds.
# In Python a value of 0 means Jan 1 1970 (use negatives for earlier
# start date). This will affect the returns from the utils.gametime
# module.
TIME_GAME_EPOCH = None
```

By default, the game time runs twice as fast as the real time.  You can set the time factor to be 1
(the game time would run exactly at the same speed than the real time) or lower (the game time will
be slower than the real time).  Most games choose to have the game time spinning faster (you will
find some games that have a time factor of 60, meaning the game time runs sixty times as fast as the
real time, a minute in real time would be an hour in game time).

The epoch is a slightly more complex setting.  It should contain a number of seconds that would
indicate the time your game started.  As indicated, an epoch of 0 would mean January 1st, 1970.  If
you want to set your time in the future, you just need to find the starting point in seconds.  There
are several ways to do this in Python, this method will show you how to do it in local time:

```python
# We're looking for the number of seconds representing
# January 1st, 2020
from datetime import datetime
import time
start = datetime(2020, 1, 1)
time.mktime(start.timetuple())
```

This should return a huge number - the number of seconds since Jan 1 1970. Copy that directly into
your settings (editing `server/conf/settings.py`):

```python
# in a file settings.py in mygame/server/conf
TIME_GAME_EPOCH = 1577865600
```

Reload the game with `@reload`, and then use the `@time` command.  You should see something like
this:

```
+----------------------------+-------------------------------------+
| Server time                |                                     |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| Current uptime             | 20 seconds                          |
| Total runtime              | 1 day, 1 hour, 55 minutes           |
| First start                | 2017-02-12 15:47:50.565000          |
| Current time               | 2017-02-13 17:43:10.760000          |
+----------------------------+-------------------------------------+
| In-Game time               | Real time x 2                       |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| Epoch (from settings)      | 2020-01-01 00:00:00                 |
| Total time passed:         | 1 day, 17 hours, 34 minutes         |
| Current time               | 2020-01-02 17:34:55.430000          |
+----------------------------+-------------------------------------+
```

The line that is most relevant here is the game time epoch.  You see it shown at 2020-01-01.  From
this point forward, the game time keeps increasing.  If you keep typing `@time`, you'll see the game
time updated correctly... and going (by default) twice as fast as the real time.

#### Time-related events

The `gametime` utility also has a way to schedule game-related events, taking into account your game
time, and assuming a standard calendar (see below for the same feature with a custom calendar).  For
instance, it can be used to have a specific message every (in-game) day at 6:00 AM showing how the
sun rises.

The function `schedule()` should be used here.  It will create a [script](./Scripts) with some
additional features to make sure the script is always executed when the game time matches the given
parameters.

The `schedule` function takes the following arguments:

- The *callback*, a function to be called when time is up.
- The keyword `repeat` (`False` by default) to indicate whether this function should be called
repeatedly.
- Additional keyword arguments `sec`, `min`, `hour`, `day`, `month` and `year` to describe the time
to schedule.  If the parameter isn't given, it assumes the current time value of this specific unit.

Here is a short example for making the sun rise every day:

```python
# in a file ingame_time.py in mygame/world/

from evennia.utils import gametime
from typeclasses.rooms import Room

def at_sunrise():
    """When the sun rises, display a message in every room."""
    # Browse all rooms
    for room in Room.objects.all():
        room.msg_contents("The sun rises from the eastern horizon.")

def start_sunrise_event():
    """Schedule an sunrise event to happen every day at 6 AM."""
    script = gametime.schedule(at_sunrise, repeat=True, hour=6, min=0, sec=0)
    script.key = "at sunrise"
```

If you want to test this function, you can easily do something like:

```
@py from world import ingame_time; ingame_time.start_sunrise_event()
```

The script will be created silently. The `at_sunrise` function will now be called every in-game day
at 6 AM. You can use the `@scripts` command to see it. You could stop it using `@scripts/stop`. If
we hadn't set `repeat` the sun would only have risen once and then never again.

We used the `@py` command here: nothing prevents you from adding the system into your game code.
Remember to be careful not to add each event at startup, however, otherwise there will be a lot of
overlapping events scheduled when the sun rises.

The `schedule` function when using `repeat` set to `True` works with the higher, non-specified unit.
In our example, we have specified hour, minute and second.  The higher unit we haven't specified is
day: `schedule` assumes we mean "run the callback every day at the specified time".  Therefore, you
can have an event that runs every hour at HH:30, or every month on the 3rd day.

> A word of caution for repeated scripts on a monthly or yearly basis: due to the variations in the
real-life calendar you need to be careful when scheduling events for the end of the month or year.
For example, if you set a script to run every month on the 31st it will run in January but find no
such day in February, April etc. Similarly, leap years may change the number of days in the year.

### A game time with a custom calendar

Using a custom calendar to handle game time is sometimes needed if you want to place your game in a
fictional universe.  For instance you may want to create the Shire calendar which Tolkien described
having 12 months, each which 30 days. That would give only 360 days per year (presumably hobbits
weren't really fond of the hassle of following the astronomical calendar).  Another example would be
creating a planet in a different solar system with, say, days 29 hours long and months of only 18
days.

Evennia handles custom calendars through an optional *contrib* module, called `custom_gametime`.
Contrary to the normal `gametime` module described above it is not active by default.

#### Setting up the custom calendar

In our first example of the Shire calendar, used by hobbits in books by Tolkien, we don't really
need the notion of weeks... but we need the notion of months having 30 days, not 28.

The custom calendar is defined by adding the `TIME_UNITS` setting to your settings file. It's a
dictionary containing as keys the name of the units, and as value the number of seconds (the
smallest unit for us) in this unit. Its keys must be picked among the following: "sec", "min",
"hour", "day", "week", "month" and "year" but you don't have to include them all.  Here is the
configuration for the Shire calendar:

```python
# in a file settings.py in mygame/server/conf
TIME_UNITS = {"sec": 1,
              "min": 60,
              "hour": 60 * 60,
              "day": 60 * 60 * 24,
              "month": 60 * 60 * 24 * 30,
              "year": 60 * 60 * 24 * 30 * 12 }
```

We give each unit we want as keys.  Values represent the number of seconds in that unit.  Hour is
set to 60 * 60 (that is, 3600 seconds per hour).  Notice that we don't specify the week unit in this
configuration:  instead, we skip from days to months directly.

In order for this setting to work properly, remember all units have to be multiples of the previous
units.  If you create "day", it needs to be multiple of hours, for instance.

So for our example, our settings may look like this:

```python
# in a file settings.py in mygame/server/conf
# Time factor
TIME_FACTOR = 4

# Game time epoch
TIME_GAME_EPOCH = 0

# Units
TIME_UNITS = {
        "sec": 1,
        "min": 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "month": 60 * 60 * 24 * 30,
        "year": 60 * 60 * 24 * 30 * 12,
}
```

Notice we have set a time epoch of 0.  Using a custom calendar, we will come up with a nice display
of time on our own. In our case the game time starts at year 0, month 0, day 0, and at midnight.

Note that while we use "month", "week" etc in the settings, your game may not use those terms in-
game, instead referring to them as "cycles", "moons", "sand falls" etc. This is just a matter of you
displaying them differently. See next section.

#### A command to display the current game time

As pointed out earlier, the `@time` command is meant to be used with a standard calendar, not a
custom one.  We can easily create a new command though.  We'll call it `time`, as is often the case
on other MU*.  Here's an example of how we could write it (for the example, you can create a file
`showtime.py` in your `commands` directory and paste this code in it):

```python
# in a file mygame/commands/gametime.py

from evennia.contrib import custom_gametime

from commands.command import Command

class CmdTime(Command):

    """
    Display the time.

    Syntax:
        time

    """

    key = "time"
    locks = "cmd:all()"

    def func(self):
        """Execute the time command."""
        # Get the absolute game time
        year, month, day, hour, min, sec = custom_gametime.custom_gametime(absolute=True)
        string = "We are in year {year}, day {day}, month {month}."
        string += "\nIt's {hour:02}:{min:02}:{sec:02}."
        self.msg(string.format(year=year, month=month, day=day,
                hour=hour, min=min, sec=sec))
```

Don't forget to add it in your CharacterCmdSet to see this command:

```python
# in mygame/commands/default_cmdset.py

from commands.gametime import CmdTime   # <-- Add

# ...

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """
    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        # ...
        self.add(CmdTime())   # <- Add
```

Reload your game with the `@reload` command.  You should now see the `time` command.  If you enter
it, you might see something like:

    We are in year 0, day 0, month 0.
    It's 00:52:17.

You could display it a bit more prettily with names for months and perhaps even days, if you want.
And if "months" are called "moons" in your game, this is where you'd add that.

#### Time-related events in custom gametime

The `custom_gametime` module also has a way to schedule game-related events, taking into account
your game time (and your custom calendar).  It can be used to have a specific message every day at
6:00 AM, to show the sun rises, for instance. The `custom_gametime.schedule` function works in the
same way as described for the default one above.
