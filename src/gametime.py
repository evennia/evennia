"""
The gametime module handles the global passage of time in the mud.

It also supplies some useful methods to convert between
in-mud time and real-worl time.
"""

from django.conf import settings
import time as time_module
from src.cache import cache

# Speed-up factor of the in-game time compared
# to real time. 

TIMEFACTOR = settings.TIME_FACTOR

# Common real-life time measures, in seconds.
# You should normally not change these.

REAL_TICK = settings.TIME_TICK #This is the smallest time unit (minimum 1s)
REAL_MIN = 60.0 # seconds per minute in real world

# Game-time units, in real-life seconds. These are supplied as
# a convenient measure for determining the current in-game time,
# e.g. when defining events. The words month, week and year can
# of course be translated into any suitable measures. 

TICK = REAL_TICK / TIMEFACTOR
MIN = REAL_MIN / TIMEFACTOR
HOUR = MIN * settings.TIME_MIN_PER_HOUR
DAY = HOUR * settings.TIME_HOUR_PER_DAY
WEEK = DAY * settings.TIME_DAY_PER_WEEK
MONTH = WEEK * settings.TIME_WEEK_PER_MONTH
YEAR = MONTH * settings.TIME_MONTH_PER_YEAR

# Access routines

def time(currtime=None):
    """
    Find the current in-game time (in seconds) since the start of the mud.
    The value returned from this function can be used to track the 'true'
    in-game time since only the time the game has actually been active will
    be adding up (ignoring downtimes). 

    Obs: depending on how often the persistent cache is saved to disk
    (this is defined in the config file), there might be some discrepancy
    here after a server crash, notably that some time will be 'lost' (i.e.
    the time since last backup). If this is a concern, consider saving
    the cache more often. 

    currtime : An externally calculated current time to compare with.
               This is used by Evennia to make sure to sync the game 
               time to a new real-world timestamp
    """
    # saved real world timestamp (seconds since 1970 or so)
    time0 = cache.get_pcache("_game_time0")
    # saved game time at real-world time time0
    time1 = cache.get_pcache("_game_time")  
    if currtime:
        return time1 + (currtime - time0)
    else:
        return time1 + (time_module.time() - time0)

def gametime_to_realtime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0):
    """
    This method helps to figure out the real-world time it will take until a in-game time
    has passed. E.g. if an event should take place a month later in-game, you will be able
    to find the number of real-world seconds this corresponds to (hint: Interval events deal
    with real life seconds).     

    Example:
     gametime_to_realtime(days=2) -> number of seconds in real life from now after which
                                     2 in-game days will have passed. 
    """
    stot = secs/TIMEFACTOR + mins*MIN + hrs*HOUR + \
           days*DAY + weeks*WEEK + months*MONTH + yrs*YEAR
    return stot

def realtime_to_gametime(secs=0, mins=0, hrs=0, days=0,
                         weeks=0, months=0, yrs=0):
    """
    This method calculates how large an in-game time a real-world time interval would
    correspond to. This is usually a lot less interesting than the other way around. 

     Example: 
      realtime_to_gametime(days=2) -> number of game-world seconds
                                      corresponding to 2 real days.
    """
    stot = TIMEFACTOR * (secs + mins*60 + hrs*3600 + days*86400 + \
                         weeks*604800 + months*2419200 + yrs*29030400)
    return stot


# Time administration routines 

def time_init():
    """
    Called by Evennia's initial startup; this should normally not be called from
    a running game, it resets the global in-game time! 
    """
    time0 = time_module.time()
    time1 = 0
    cache.set_pcache("_game_time0", time0)
    cache.set_pcache("_game_time", time1)
    cache.save_pcache()
    
def time_save():
    """
    Force a save of the current time to persistent cache.
    
    Shutting down the server from within the mud will
    automatically call this routine.
    """
    time0 = time_module.time()
    time1 = time(time0)
    cache.set_pcache("_game_time0", time0)
    cache.set_pcache("_game_time", time1)
    cache.save_pcache()
    
def time_last_sync():
    """
    Calculates the time since the system was last synced to disk. This e.g. used
    to adjust event counters for offline time, resulting in a maximum error being
    the time between backups. 
    """
    # Real-world timestamp for last backup
    time0 = cache.get_pcache("_game_time0") 
    # The correction factor is the time
    # since last backup + downtime. 
    return time_module.time() - time0


