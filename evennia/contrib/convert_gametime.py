"""
Convert gametime

Contrib - Griatch 2017

This is the game-dependent part of the evennia.utils.gametime module
that used to be settable from the settings file. Since this was just
a bunch of conversion routines, it is now moved to a contrib since it
is highly unlikely its use is of general game use. The utils.gametime
module deals in seconds, and you can use this contrib to convert
that to fit the calendar of your game.

Usage:
    Import and use as-is or copy this module to mygame/world and
    modify it to your needs there.

"""

# change these to fit your game world

from django.conf import settings

# The game time speedup  / slowdown relative real time
TIMEFACTOR = settings.TIME_FACTOR

# Game-time units, in real-life seconds. These are supplied as a
# convenient measure for determining the current in-game time, e.g.
# when defining in-game events. The words month, week and year can  be
# used to mean whatever units of time are used in your game.

MIN = 60          # seconds per minute
HOUR = MIN * 60   # minutes per hour
DAY = HOUR * 24   # hours per day
WEEK = DAY * 7    # days per week
MONTH = WEEK * 4  # weeks per month
YEAR = MONTH * 12 # months per year


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


def gametime_to_realtime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0, format=False):
    """
    This method helps to figure out the real-world time it will take until an
    in-game time has passed. E.g. if an event should take place a month later
    in-game, you will be able to find the number of real-world seconds this
    corresponds to (hint: Interval events deal with real life seconds).

    Kwargs:
        times (int): The various components of the time.
        format (bool): Formatting the output.

    Returns:
        time (float or tuple): The realtime difference or the same
            time split up into time units.

    Example:
         gametime_to_realtime(days=2) -> number of seconds in real life from
                        now after which 2 in-game days will have passed.

    """
    rtime = (secs + mins * MIN + hrs * HOUR + days * DAY + weeks * WEEK + \
                months * MONTH + yrs * YEAR) / TIMEFACTOR
    if format:
        return time_to_tuple(rtime, 31536000, 2628000, 604800, 86400, 3600, 60)
    return rtime


def realtime_to_gametime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0, format=False):
    """
    This method calculates how much in-game time a real-world time
    interval would correspond to. This is usually a lot less
    interesting than the other way around.

    Kwargs:
        times (int): The various components of the time.
        format (bool): Formatting the output.

    Returns:
        time (float or tuple): The gametime difference or the same
            time split up into time units.

     Example:
      realtime_to_gametime(days=2) -> number of game-world seconds
                                      corresponding to 2 real days.

    """
    gtime = TIMEFACTOR * (secs + mins * 60 + hrs * 3600 + days * 86400 +
                             weeks * 604800 + months * 2628000 + yrs * 31536000)
    if format:
        return time_to_tuple(gtime, YEAR, MONTH, WEEK, DAY, HOUR, MIN)
    return gtime

