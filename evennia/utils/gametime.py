"""
The gametime module handles the global passage of time in the mud.

It also supplies some useful methods to convert between
in-mud time and real-world time as well allows to get the
total runtime of the server and the current uptime.
"""
from __future__ import division
import time
from django.conf import settings
from evennia.server.models import ServerConfig

# Speed-up factor of the in-game time compared
# to real time.

TIMEFACTOR = settings.TIME_FACTOR

# Only set if gametime_reset was called at some point.
GAME_TIME_OFFSET = ServerConfig.objects.conf("gametime_offset", default=0)

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
        _SERVER_EPOCH = ServerConfig.objects.conf("server_epoch", default=None) \
                        or time.time() - runtime()
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
    gtime = epoch + (runtime() - GAME_TIME_OFFSET) * TIMEFACTOR
    return gtime


def reset_gametime():
    """
    Resets the game time to make it start from the current time. Note that
    the epoch set by `settings.TIME_GAME_EPOCH` will still apply.

    """
    global GAME_TIME_OFFSET
    GAME_TIME_OFFSET = runtime()
    ServerConfig.objects.conf("gametime_offset", GAME_TIME_OFFSET)
