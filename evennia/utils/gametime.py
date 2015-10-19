"""
The gametime module handles the global passage of time in the mud.

It also supplies some useful methods to convert between
in-mud time and real-world time as well allows to get the
total runtime of the server and the current uptime.
"""
from __future__ import division

from time import time
from django.conf import settings

# Speed-up factor of the in-game time compared
# to real time.

TIMEFACTOR = settings.TIME_FACTOR

# Common real-life time measure, in seconds.
# You should not change this.

REAL_MIN = 60.0  # seconds per minute in real world

# Game-time units, in real-life seconds. These are supplied as
# a convenient measure for determining the current in-game time,
# e.g. when defining in-game events. The words month, week and year can
# be used to mean whatever units of time are used in the game.

MIN = settings.TIME_SEC_PER_MIN
HOUR = MIN * settings.TIME_MIN_PER_HOUR
DAY = HOUR * settings.TIME_HOUR_PER_DAY
WEEK = DAY * settings.TIME_DAY_PER_WEEK
MONTH = WEEK * settings.TIME_WEEK_PER_MONTH
YEAR = MONTH * settings.TIME_MONTH_PER_YEAR

# these are kept updated by the server maintenance loop
SERVER_START_TIME = 0.0
SERVER_RUNTIME_LAST_UPDATED = 0.0
SERVER_RUNTIME = 0.0

def _format(seconds, *divisors) :
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


# Access functions

def runtime(format=False):
    """
    Get the total runtime of the server since first start (minus
    downtimes)

    Args:
        format (bool, optional): Format into a time representation.

    Returns:
        time (float or tuple): The runtime or the same time split up
            into time units.

    """
    runtime = SERVER_RUNTIME + (time() - SERVER_RUNTIME_LAST_UPDATED)
    if format:
        return _format(runtime, 31536000, 2628000, 604800, 86400, 3600, 60)
    return runtime

def uptime(format=False):
    """
    Get the current uptime of the server since last reload

    Args:
        format (bool, optional): Format into time representation.

    Returns:
        time (float or tuple): The uptime or the same time split up
            into time units.

    """
    uptime = time() - SERVER_START_TIME
    if format:
        return _format(uptime, 31536000, 2628000, 604800, 86400, 3600, 60)
    return uptime

def gametime(format=False):
    """
    Get the total gametime of the server since first start (minus downtimes)

    Args:
        format (bool, optional): Format into time representation.

    Returns:
        time (float or tuple): The gametime or the same time split up
            into time units.

    """
    gametime = runtime() * TIMEFACTOR
    if format:
        return _format(gametime, YEAR, MONTH, WEEK, DAY, HOUR, MIN)
    return gametime


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
    realtime = (secs + mins * MIN + hrs * HOUR + days * DAY + weeks * WEEK + \
                months * MONTH + yrs * YEAR) / TIMEFACTOR
    if format:
        return _format(realtime, 31536000, 2628000, 604800, 86400, 3600, 60)
    return realtime


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
    gametime = TIMEFACTOR * (secs + mins * 60 + hrs * 3600 + days * 86400 +
                             weeks * 604800 + months * 2628000 + yrs * 31536000)
    if format:
        return _format(gametime, YEAR, MONTH, WEEK, DAY, HOUR, MIN)
    return gametime

