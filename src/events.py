"""
Holds the global events scheduled in scheduler.py.

Events are sub-classed from IntervalEvent (which is not to be used directly).
Create your sub-class, call src.scheduler.add_event(YourEventClass()) to add
it to the global scheduler.

Use @ps to view the event list.

The events set with the member variable persistent equal to True will be
stored in persistent cache and will survive server downtime. 
"""
import time
import copy 
from twisted.internet import task
from django.conf import settings
import session_mgr
from src import scheduler
from src import defines_global
from src.objects.models import Object
from src.cache import cache
from src import logger
from src import gametime

class IntervalEvent(object):
    """
    Represents an event that is triggered periodically. Sub-class this and
    fill in the stub function.

    self.repeats decides if this event will fire indefinitely or only a
    certain number of times.
    """    
    def __init__(self, description="IntervalEvent"):
        """
        Executed when the class is instantiated.
        """
        # This is a globally unique ID of this event. If None, a new one will
        # be allocated when the event is added to the scheduler.
        self.pid = None
        # This is set to prevent a Nonetype exception on @ps before the
        # event is fired for the first time.
        self.time_last_executed = time.time()
        # This used to describe the event in @ps listings.
        self.description = description
        # An interval (in seconds) for execution.
        self.interval = None
        # How many times to repeat this event.
        # None : indefinitely,
        # positive integer : number of times
        self.repeats = None 
        # A reference to the task.LoopingCall object.
        self.looped_task = None
        # If true, the event definition will survive a reboot.
        self.persistent = False

    def __getstate__(self):        
        """
        Used by pickle.
        """
        edict = copy.copy(self.__dict__)
        edict["looped_task"] = None 
        edict["pid"] = None
        return edict

    def __unicode__(self):
        """
        String representation of the event.
        """
        return self.description

    def __eq__(self, event2):
        """
        Handles comparison operations.
        """
        return self.pid == event2.pid

    def __hash__(self):
        """
        Used for dictionary key comparisons.
        """
        return self.pid

    def start_event_loop(self):
        """
        Called to start up the event loop when the event is added to the
        scheduler.
        """
        # Set the call-back function for the task to trigger_event, but pass
        # a reference to the event function.
        self.looped_task = task.LoopingCall(self.fire_event)
        # Start the task up with the specified interval.
        self.looped_task.start(self.interval, now=False)

    def stop_event_loop(self):
        """
        Called to stop the event loop when the event is removed from the
        scheduler.
        """
        self.looped_task.stop()
    
    def event_function(self):
        """                    
        ### Over-ride this in your sub-class. ###
        """   
        pass
    
    def get_nextfire(self):
        """
        Returns a value in seconds when the event is going to fire off next.
        """
        return max(0, (self.time_last_executed + self.interval) - time.time())
    
    def set_lastfired(self):
        """
        Sets the timestamp (int) that the event was last fired.
        """
        self.time_last_executed = time.time()
        
    def fire_event(self):
        """
        Set the last ran stamp and fire off the event.
        Stop repeating if number of repeats have been achieved.  
        """
        self.set_lastfired()        
        self.event_function()
        if self.repeats != None:
            self.repeats -= 1
            if self.repeats <= 0 and self.pid != None:
                scheduler.del_event(self.pid)
            

# Some default server events

class IEvt_Check_Sessions(IntervalEvent):
    """
    Event: Check all of the connected sessions.
    """
    def __init__(self):
        super(IEvt_Check_Sessions, self).__init__()
        #self.name = 'IEvt_Check_Sessions'
        self.interval = 60
        self.description = "Session consistency checks."
        self.persistent = True
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        session_mgr.check_all_sessions()

class IEvt_Destroy_Objects(IntervalEvent):
    """
    Event: Clean out all objects marked for destruction.
    """
    def __init__(self):
        super(IEvt_Destroy_Objects, self).__init__()
        #self.name = 'IEvt_Destroy_Objects'
        self.interval = 1800
        self.description = "Clean out objects marked for destruction."
        self.persistent = True

    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        going_objects = Object.objects.filter(type__exact=defines_global.OTYPE_GOING)
        for obj in going_objects:
            obj.delete()

class IEvt_Sync_PCache(IntervalEvent):
    """
    Event: Sync the persistent cache to with the database.
    This is an important event since it also makes sure to
    update the time stamp. 
    """
    def __init__(self):
        super(IEvt_Sync_PCache, self).__init__()
        #self.name = 'IEvt_Sync_PCache'
        self.interval = settings.CACHE_BACKUP_INTERVAL
        self.description = "Backup pcache to disk."
        self.persistent = True

    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        infostring = "Syncing time, events and persistent cache to disk."
        logger.log_infomsg(infostring)        
        # updating the current time                 
        time0 = time.time()
        time1 = gametime.time(time0)        
        cache.set_pcache("_game_time0", time0)
        cache.set_pcache("_game_time", time1)
        # update the event database to pcache
        ecache = [event for event in scheduler.SCHEDULE
                  if event.persistent]            
        cache.set_pcache("_persistent_event_cache", ecache)            
        # save pcache to disk.
        cache.save_pcache()
