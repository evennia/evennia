"""
Custom gametime

Contrib - Griatch 2017, vlgeoff 2017

This implements the evennia.utils.gametime module but supporting
a custom calendar for your game world. It allows for scheduling
events to happen at given in-game times, taking this custom
calendar into account.

Usage:

Use as the normal gametime module, that is by importing and using the
helper functions in this module in your own code. The calendar can be
customized by adding the `TIME_UNITS` dictionary to your settings
file. This maps unit names to their length, expressed in the smallest
unit. Here's the default as an example:

    TIME_UNITS = {
        "sec": 1,
        "min": 60,
        "hr": 60 * 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "week": 60 * 60 * 24 * 7,
        "month": 60 * 60 * 24 * 7 * 4,
        "yr": 60 * 60 * 24 * 7 * 4 * 12,
        "year": 60 * 60 * 24 * 7 * 4 * 12, }

When using a custom calendar, these time unit names are used as kwargs to
the converter functions in this module.

"""

# change these to fit your game world

from django.conf import settings

from evennia import DefaultScript
from evennia.utils import gametime
from evennia.utils.create import create_script

# The game time speedup  / slowdown relative real time
TIMEFACTOR = settings.TIME_FACTOR

# These are the unit names understood by the scheduler.
# Each unit must be consistent and expressed in seconds.
UNITS = getattr(
    settings,
    "TIME_UNITS",
    {
        # default custom calendar
        "sec": 1,
        "min": 60,
        "hr": 60 * 60,
        "hour": 60 * 60,
        "day": 60 * 60 * 24,
        "week": 60 * 60 * 24 * 7,
        "month": 60 * 60 * 24 * 7 * 4,
        "yr": 60 * 60 * 24 * 7 * 4 * 12,
        "year": 60 * 60 * 24 * 7 * 4 * 12,
    },
)


def time_to_tuple(seconds, *divisors):
    """
    Helper function. Creates a tuple of even dividends given a range
    of divisors.

    Args:
        seconds (int): Number of seconds to format
        *divisors (int): a sequence of numbers of integer dividends. The
            number of seconds will be integer-divided by the first number in
            this sequence, the remainder will be divided with the second and
            so on.
    Returns:
        time (tuple): This tuple has length len(*args)+1, with the
            last element being the last remaining seconds not evenly
            divided by the supplied dividends.

    """
    results = []
    seconds = int(seconds)
    for divisor in divisors:
        results.append(seconds // divisor)
        seconds %= divisor
    results.append(seconds)
    return tuple(results)


def gametime_to_realtime(format=False, **kwargs):
    """
    This method helps to figure out the real-world time it will take until an
    in-game time has passed. E.g. if an event should take place a month later
    in-game, you will be able to find the number of real-world seconds this
    corresponds to (hint: Interval events deal with real life seconds).

    Keyword Args:
        format (bool): Formatting the output.
        days, month etc (int): These are the names of time units that must
            match the `settings.TIME_UNITS` dict keys.

    Returns:
        time (float or tuple): The realtime difference or the same
            time split up into time units.

    Example:
         gametime_to_realtime(days=2) -> number of seconds in real life from
                        now after which 2 in-game days will have passed.

    """
    # Dynamically creates the list of units based on kwarg names and UNITs list
    rtime = 0
    for name, value in kwargs.items():
        # Allow plural names (like mins instead of min)
        if name not in UNITS and name.endswith("s"):
            name = name[:-1]

        if name not in UNITS:
            raise ValueError("the unit {} isn't defined as a valid " "game time unit".format(name))
        rtime += value * UNITS[name]
    rtime /= TIMEFACTOR
    if format:
        return time_to_tuple(rtime, 31536000, 2628000, 604800, 86400, 3600, 60)
    return rtime


def realtime_to_gametime(secs=0, mins=0, hrs=0, days=1, weeks=1, months=1, yrs=0, format=False):
    """
    This method calculates how much in-game time a real-world time
    interval would correspond to. This is usually a lot less
    interesting than the other way around.

    Keyword Args:
        times (int): The various components of the time.
        format (bool): Formatting the output.

    Returns:
        time (float or tuple): The gametime difference or the same
            time split up into time units.

    Note:
        days/weeks/months start from 1 (there is no day/week/month 0). This makes it
            consistent with the real world datetime.

    Raises:
        ValueError: If trying to add a days/weeks/months of <=0.

    Example:
      realtime_to_gametime(days=2) -> number of game-world seconds

    """
    if days <= 0 or weeks <= 0 or months <= 0:
        raise ValueError(
            "realtime_to_gametime: days/weeks/months cannot be set <= 0, " "they start from 1."
        )

    # days/weeks/months start from 1, we need to adjust them to work mathematically.
    days, weeks, months = days - 1, weeks - 1, months - 1

    gtime = TIMEFACTOR * (
        secs
        + mins * 60
        + hrs * 3600
        + days * 86400
        + weeks * 604800
        + months * 2628000
        + yrs * 31536000
    )
    if format:
        units = sorted(set(UNITS.values()), reverse=True)
        # Remove seconds from the tuple
        del units[-1]

        return time_to_tuple(gtime, *units)
    return gtime


def custom_gametime(absolute=False):
    """
    Return the custom game time as a tuple of units, as defined in settings.

    Args:
        absolute (bool, optional): return the relative or absolute time.

    Returns:
        The tuple describing the game time.  The length of the tuple
        is related to the number of unique units defined in the
        settings.  By default, the tuple would be (year, month,
        week, day, hour, minute, second).

    """
    current = gametime.gametime(absolute=absolute)
    units = sorted(set(UNITS.values()), reverse=True)
    del units[-1]
    return time_to_tuple(current, *units)


def real_seconds_until(**kwargs):
    """
    Return the real seconds until game time.

    If the game time is 5:00, TIME_FACTOR is set to 2 and you ask
    the number of seconds until it's 5:10, then this function should
    return 300 (5 minutes).

    Args:
        times (str: int): the time units.

    Example:
        real_seconds_until(hour=5, min=10, sec=0)

    Returns:
        The number of real seconds before the given game time is up.

    Notes:
        day/week/month start from 1, not from 0 (there is no month 0 for example)

    """
    current = gametime.gametime(absolute=True)
    units = sorted(set(UNITS.values()), reverse=True)
    # Remove seconds from the tuple
    del units[-1]
    divisors = list(time_to_tuple(current, *units))

    # For each keyword, add in the unit's
    units.append(1)
    higher_unit = None
    for unit, value in kwargs.items():
        if unit in ("day", "week", "month"):
            # these start from 1 so we must adjust
            value -= 1

        # Get the unit's index
        if unit not in UNITS:
            raise ValueError(f"Unknown unit '{unit}'. Allowed: {', '.join(UNITS)}")

        seconds = UNITS[unit]
        index = units.index(seconds)
        divisors[index] = value
        if higher_unit is None or higher_unit > index:
            higher_unit = index

    # Check the projected time
    # Note that it can be already passed (the given time may be in the past)
    projected = 0
    for i, value in enumerate(divisors):
        seconds = units[i]
        projected += value * seconds

    if projected <= current:
        # The time is in the past, increase the higher unit
        if higher_unit:
            divisors[higher_unit - 1] += 1
        else:
            divisors[0] += 1

    # Get the projected time again
    projected = 0
    for i, value in enumerate(divisors):
        seconds = units[i]
        projected += value * seconds

    return (projected - current) / TIMEFACTOR


def schedule(callback, repeat=False, **kwargs):
    """
    Call the callback when the game time is up.

    Args:
        callback (function): The callback function that will be called. This
            must be a top-level function since the script will be persistent.
        repeat (bool, optional): Should the callback be called regularly?
        day, month, etc (str: int): The time units to call the callback; should
            match the keys of TIME_UNITS.

    Returns:
        script (Script): The created script.

    Examples:
        schedule(func, min=5, sec=0)          # Will call next hour at :05.
        schedule(func, hour=2, min=30, sec=0) # Will call the next day at 02:30.
    Notes:
        This function will setup a script that will be called when the
        time corresponds to the game time.  If the game is stopped for
        more than a few seconds, the callback may be called with a
        slight delay. If `repeat` is set to True, the callback will be
        called again next time the game time matches the given time.
        The time is given in units as keyword arguments.

    """
    seconds = real_seconds_until(**kwargs)
    script = create_script(
        "evennia.contrib.base_systems.custom_gametime.GametimeScript",
        key="GametimeScript",
        desc="A timegame-sensitive script",
        interval=seconds,
        start_delay=True,
        repeats=-1 if repeat else 1,
    )
    script.db.callback = callback
    script.db.gametime = kwargs
    return script


# Scripts dealing in gametime (use `schedule`  to create it)


class GametimeScript(DefaultScript):

    """Gametime-sensitive script."""

    def at_script_creation(self):
        """The script is created."""
        self.key = "unknown scr"
        self.interval = 100
        self.start_delay = True
        self.persistent = True

    def at_repeat(self):
        """Call the callback and reset interval."""

        from evennia.utils.utils import calledby

        callback = self.db.callback
        if callback:
            callback()

        seconds = real_seconds_until(**self.db.gametime)
        self.start(interval=seconds, force_restart=True)
