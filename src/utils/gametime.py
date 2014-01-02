"""
The gametime module handles the global passage of time in the mud.

It also supplies some useful methods to convert between
in-mud time and real-world time as well allows to get the
total runtime of the server and the current uptime.
"""

from django.conf import settings
from src.scripts.scripts import Script
from src.scripts.models import ScriptDB
from src.utils.create import create_script
from src.utils import logger

# name of script that keeps track of the time

GAME_TIME_SCRIPT = "sys_game_time"

# Speed-up factor of the in-game time compared
# to real time.

TIMEFACTOR = settings.TIME_FACTOR

# How often this script runs and updates the game time

UPDATE_INTERVAL = settings.TIME_UPDATE_INTERVAL

# Common real-life time measures, in seconds.
# You should not change these.

REAL_TICK = max(1.0, settings.TIME_TICK)  # Smallest time unit (min 1s)
REAL_MIN = 60.0  # seconds per minute in real world

# Game-time units, in real-life seconds. These are supplied as
# a convenient measure for determining the current in-game time,
# e.g. when defining events. The words month, week and year can
# of course mean whatever units of time are used in the game.

TICK = REAL_TICK * TIMEFACTOR
MIN = settings.TIME_SEC_PER_MIN
HOUR = MIN * settings.TIME_MIN_PER_HOUR
DAY = HOUR * settings.TIME_HOUR_PER_DAY
WEEK = DAY * settings.TIME_DAY_PER_WEEK
MONTH = WEEK * settings.TIME_WEEK_PER_MONTH
YEAR = MONTH * settings.TIME_MONTH_PER_YEAR


class GameTime(Script):
    """
    This sets up an script that keeps track of the
    in-game time and some other time units.
    """
    def at_script_creation(self):
        """
        Setup the script
        """
        self.key = "sys_game_time"
        self.desc = "Keeps track of the game time"
        self.interval = UPDATE_INTERVAL
        self.persistent = True
        self.start_delay = True
        self.attributes.add("game_time", 0.0)  # IC time
        self.attributes.add("run_time", 0.0)  # OOC time
        self.attributes.add("up_time", 0.0)  # OOC time

    def at_repeat(self):
        """
        Called every minute to update the timers.
        """
        # We store values as floats to avoid drift over time
        game_time = float(self.attributes.get("game_time"))
        run_time = float(self.attributes.get("run_time"))
        up_time = float(self.attributes.get("up_time"))
        self.attributes.add("game_time", game_time + UPDATE_INTERVAL * TIMEFACTOR)
        self.attributes.add("run_time", run_time + UPDATE_INTERVAL)
        self.attributes.add("up_time", up_time + UPDATE_INTERVAL)

    def at_start(self):
        """
        This is called once every server restart.
        We reset the up time.
        """
        self.attributes.add("up_time", 0.0)
        self.interval = UPDATE_INTERVAL


# Access routines

def format(seconds, divisors, modify_seconds=True):
    """
    Takes a list of divisors by which to divide the seconds, also passed
    in, by. The result of each division will be returned in the order it
    was performed, starting from the beginning of the divisors list.

    The default behavior is to, after first dividing the number of seconds
    by the divisor, mod the seconds by the divisor and, at the very end,
    return the left over seconds by appending to the list. When passed a
    list of divisors such as [31536000, 2628000, 604800, 86400, 3600, 60]
    this results in the years, months, weeks, days, hours, minutes, and
    seconds that have passed, according to ths seconds value passed in,
    being returned via tuple.

    If modify_seconds=False then the order the divisors are passed in
    have no meaning other than placement in the results set and there is
    no remainder to append to the end of the results.
    """
    results = []
    for divisor in divisors:
        results.append(seconds / divisor)
        if modify_seconds:
            seconds = seconds % divisor
    if modify_seconds:
        results.append(seconds)
    return tuple(results)


def gametime_format(seconds):
    """
    Converts the count in seconds into an integer tuple of the form
    (years, months, weeks, days, hours, minutes, seconds) where
    several of the entries may be 0.

    We want to keep a separate version of this (rather than just
    rescale the real time once and use the normal realtime_format
    below) since the admin might for example decide to change how many
    hours a 'day' is in their game etc.
    """
    return format(seconds, [YEAR, MONTH, WEEK, DAY, HOUR, MIN])


def realtime_format(seconds):
    """
    As gametime format, but with real time units
    """
    return format(seconds, [31536000, 2628000, 604800, 86400, 3600, 60])


def gametime(format=False):
    """
    Find the current in-game time (in seconds) since the start of the mud.
    The value returned from this function can be used to track the 'true'
    in-game time since only the time the game has actually been active will
    be adding up (ignoring downtimes).

    format - instead of returning result in seconds, format to (game-) time
    units.
    """
    try:
        script = ScriptDB.objects.get_all_scripts(GAME_TIME_SCRIPT)[0]
    except (KeyError, IndexError):
        logger.log_trace("GameTime script not found.")
        return
    # we return this as an integer (second-precision is good enough)
    game_time = int(script.attributes.get("game_time"))
    if format:
        return gametime_format(game_time)
    return game_time


def runtime(format=False):
    """
    Get the total actual time the server has been running (minus downtimes)
    """
    try:
        script = ScriptDB.objects.get_all_scripts(GAME_TIME_SCRIPT)[0]
    except (KeyError, IndexError):
        logger.log_trace("GameTime script not found.")
        return
    # we return this as an integer (second-precision is good enough)
    run_time = int(script.attributes.get("run_time"))
    if format:
        return realtime_format(run_time)
    return run_time


def uptime(format=False):
    """
    Get the actual time the server has been running since last downtime.
    """
    try:
        script = ScriptDB.objects.get_all_scripts(GAME_TIME_SCRIPT)[0]
    except (KeyError, IndexError):
        logger.log_trace("GameTime script not found.")
        return
    # we return this as an integer (second-precision is good enough)
    up_time = int(script.attributes.get("up_time"))
    if format:
        return realtime_format(up_time)
    return up_time


def gametime_to_realtime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0):
    """
    This method helps to figure out the real-world time it will take until an
    in-game time has passed. E.g. if an event should take place a month later
    in-game, you will be able to find the number of real-world seconds this
    corresponds to (hint: Interval events deal with real life seconds).

    Example:
     gametime_to_realtime(days=2) -> number of seconds in real life from
                                now after which 2 in-game days will have passed.
    """
    real_time = (secs + mins * MIN + hrs * HOUR + days * DAY + weeks * WEEK + \
        months * MONTH + yrs * YEAR) / TIMEFACTOR
    return real_time


def realtime_to_gametime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0):
    """
    This method calculates how large an in-game time a real-world time
    interval would correspond to. This is usually a lot less interesting
    than the other way around.

     Example:
      realtime_to_gametime(days=2) -> number of game-world seconds
                                      corresponding to 2 real days.
    """
    game_time = TIMEFACTOR * (secs + mins * 60 + hrs * 3600 + days * 86400 +
                         weeks * 604800 + months * 2419200 + yrs * 29030400)
    return game_time


# Time administration routines

def init_gametime():
    """
    This is called once, when the server starts for the very first time.
    """
    # create the GameTime script and start it
    game_time = create_script(GameTime)
    game_time.start()
