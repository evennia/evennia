"""
The gametime module handles the global passage of time in the mud.

It also supplies some useful methods to convert between
in-mud time and real-world time as well allows to get the
total runtime of the server and the current uptime.

"""

import time
from datetime import datetime, timedelta

from django.conf import settings
from django.db.utils import OperationalError

from evennia import DefaultScript
from evennia.server.models import ServerConfig
from evennia.utils.create import create_script

# Speed-up factor of the in-game time compared
# to real time.

TIMEFACTOR = settings.TIME_FACTOR
IGNORE_DOWNTIMES = settings.TIME_IGNORE_DOWNTIMES


# Only set if gametime_reset was called at some point.
try:
    GAME_TIME_OFFSET = ServerConfig.objects.conf("gametime_offset", default=0)
except OperationalError:
    # the db is not initialized
    print("Gametime offset could not load - db not set up.")
    GAME_TIME_OFFSET = 0

# Common real-life time measure, in seconds.
# You should not change this.

# these are kept updated by the server maintenance loop
SERVER_START_TIME = 0.0
SERVER_RUNTIME_LAST_UPDATED = 0.0
SERVER_RUNTIME = 0.0

# note that these should not be accessed directly since they may
# need further processing. Access from server_epoch() and game_epoch().
_SERVER_EPOCH = None
_GAME_EPOCH = None

# Helper Script dealing in gametime (created by `schedule` function
# below).


class TimeScript(DefaultScript):
    """Gametime-sensitive script."""

    def at_script_creation(self):
        """The script is created."""
        self.key = "unknown scr"
        self.interval = 100
        self.start_delay = True
        self.persistent = True

    def at_repeat(self):
        """Call the callback and reset interval."""
        callback = self.db.callback
        args = self.db.schedule_args or []
        kwargs = self.db.schedule_kwargs or {}
        if callback:
            callback(*args, **kwargs)

        seconds = real_seconds_until(**self.db.gametime)
        self.start(interval=seconds, force_restart=True)


# Access functions


def runtime():
    """
    Get the total runtime of the server since first start (minus
    downtimes)

    Args:
        format (bool, optional): Format into a time representation.

    Returns:
        time (float or tuple): The runtime or the same time split up
            into time units.

    """
    return SERVER_RUNTIME + time.time() - SERVER_RUNTIME_LAST_UPDATED


def server_epoch():
    """
    Get the server epoch. We may need to calculate this on the fly.

    """
    global _SERVER_EPOCH
    if not _SERVER_EPOCH:
        _SERVER_EPOCH = (
            ServerConfig.objects.conf("server_epoch", default=None) or time.time() - runtime()
        )
    return _SERVER_EPOCH


def uptime():
    """
    Get the current uptime of the server since last reload

    Args:
        format (bool, optional): Format into time representation.

    Returns:
        time (float or tuple): The uptime or the same time split up
            into time units.

    """
    return time.time() - SERVER_START_TIME


def portal_uptime():
    """
    Get the current uptime of the portal.

    Returns:
        time (float): The uptime of the portal.
    """
    from evennia.server.sessionhandler import SESSIONS

    return time.time() - SESSIONS.portal_start_time


def game_epoch():
    """
    Get the game epoch.

    """
    game_epoch = settings.TIME_GAME_EPOCH
    return game_epoch if game_epoch is not None else server_epoch()


def gametime(absolute=False):
    """
    Get the total gametime of the server since first start (minus downtimes)

    Args:
        absolute (bool, optional): Get the absolute game time, including
            the epoch. This could be converted to an absolute in-game
            date.

    Returns:
        time (float): The gametime as a virtual timestamp.

    Notes:
        If one is using a standard calendar, one could convert the unformatted
        return to a date using Python's standard `datetime` module like this:
        `datetime.datetime.fromtimestamp(gametime(absolute=True))`

    """
    epoch = game_epoch() if absolute else 0
    if IGNORE_DOWNTIMES:
        gtime = epoch + (time.time() - server_epoch()) * TIMEFACTOR
    else:
        gtime = epoch + (runtime() - GAME_TIME_OFFSET) * TIMEFACTOR
    return gtime


def real_seconds_until(sec=None, min=None, hour=None, day=None, month=None, year=None):
    """
    Return the real seconds until game time.

    Args:
        sec (int or None): number of absolute seconds.
        min (int or None): number of absolute minutes.
        hour (int or None): number of absolute hours.
        day (int or None): number of absolute days.
        month (int or None): number of absolute months.
        year (int or None): number of absolute years.

    Returns:
        The number of real seconds before the given game time is up.

    Example:
        real_seconds_until(hour=5, min=10, sec=0)

        If the game time is 5:00, TIME_FACTOR is set to 2 and you ask
        the number of seconds until it's 5:10, then this function should
        return 300 (5 minutes).


    """
    current = datetime.fromtimestamp(gametime(absolute=True))
    s_sec = sec if sec is not None else current.second
    s_min = min if min is not None else current.minute
    s_hour = hour if hour is not None else current.hour
    s_day = day if day is not None else current.day
    s_month = month if month is not None else current.month
    s_year = year if year is not None else current.year
    projected = datetime(s_year, s_month, s_day, s_hour, s_min, s_sec)

    if projected <= current:
        # We increase one unit of time depending on parameters
        if month is not None:
            projected = projected.replace(year=s_year + 1)
        elif day is not None:
            try:
                projected = projected.replace(month=s_month + 1)
            except ValueError:
                projected = projected.replace(month=1)
        elif hour is not None:
            projected += timedelta(days=1)
        elif min is not None:
            projected += timedelta(seconds=3600)
        else:
            projected += timedelta(seconds=60)

    # Get the number of gametime seconds between these two dates
    seconds = (projected - current).total_seconds()
    return seconds / TIMEFACTOR


def schedule(
    callback,
    repeat=False,
    sec=None,
    min=None,
    hour=None,
    day=None,
    month=None,
    year=None,
    *args,
    **kwargs,
):
    """
    Call a callback at a given in-game time.

    Args:
        callback (function): The callback function that will be called. Note
            that the callback must be a module-level function, since the script will
            be persistent. The callable should be on the form `callable(*args, **kwargs)`
            where args/kwargs are passed into this schedule.
        repeat (bool, optional): Defines if the callback should be called regularly
            at the specified time.
        sec (int or None): Number of absolute game seconds at which to run repeat.
        min (int or None): Number of absolute minutes.
        hour (int or None): Number of absolute hours.
        day (int or None): Number of absolute days.
        month (int or None): Number of absolute months.
        year (int or None): Number of absolute years.
        *args: Passed into the callable. Must be possible to store in Attribute.
        **kwargs: Passed into the callable. Must be possible to store in Attribute.

    Returns:
        Script: The created Script handling the scheduling.

    Examples:
        ::
            schedule(func, min=5, sec=0)  # Will call 5 minutes past the next (in-game) hour.
            schedule(func, hour=2, min=30, sec=0)  # Will call the next (in-game) day at 02:30.

    """
    seconds = real_seconds_until(sec=sec, min=min, hour=hour, day=day, month=month, year=year)
    script = create_script(
        "evennia.utils.gametime.TimeScript",
        key="TimeScript",
        desc="A gametime-sensitive script",
        interval=seconds,
        start_delay=True,
        repeats=-1 if repeat else 1,
    )
    script.db.callback = callback
    script.db.gametime = {
        "sec": sec,
        "min": min,
        "hour": hour,
        "day": day,
        "month": month,
        "year": year,
    }
    script.db.schedule_args = args
    script.db.schedule_kwargs = kwargs
    return script


def reset_gametime():
    """
    Resets the game time to make it start from the current time. Note that
    the epoch set by `settings.TIME_GAME_EPOCH` will still apply.

    """
    global GAME_TIME_OFFSET
    GAME_TIME_OFFSET = runtime()
    ServerConfig.objects.conf("gametime_offset", GAME_TIME_OFFSET)
