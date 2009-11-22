"""
This file contains the event scheduler system.

ADDING AN EVENT:
* Create an event sub-class from the IntervalEvent class in events.py. 
* Call src.scheduler.add_event() with your IntervalEvent subclass as the arg.
* Make sure that the module where your add_event() call resides is either
  imported, or that add_event() is called by a command or some kind of action.
* Profit.
"""
from src.cache import cache
CACHE_NAME = "_persistent_event_cache"

# dict of IntervalEvent sub-classed objects, keyed by their
# process id:s.
SCHEDULE = []

def next_free_pid():
    """
    Find the next free pid
    """
    pids = [event.pid for event in SCHEDULE]
    if not pids:
        return 0 
    maxpid = max(pids)
    freepids = [pid for pid in xrange(maxpid+1) if pid not in pids]
    if freepids:
        return min(freepids)
    return maxpid + 1  
    
def add_event(event):
    """
    Adds an event instance to the scheduled event list. Call this any time you
    need to add a custom event to the global scheduler.
    
    Args:
     * event: (IntervalEvent) The event to add to the scheduler.
    Returns:
     * pid :  (int) The process ID assigned to this event, for future reference. 
    """
    # Make sure not to add multiple instances of the same event. 
    matches = [i for i, stored_event in enumerate(SCHEDULE)
               if event == stored_event]
    if matches:
        #print "replacing existing event pid=%i: %s" % (event.pid, event.name)
        # Before replacing an event, stop its old incarnation.
        del_event(matches[0])
        SCHEDULE[matches[0]] = event
    else:
        # Add a new event with a fresh pid. 
        event.pid = next_free_pid()
        #print "adding new event with fresh pid=%i: %s" % (event.pid,event.name)
        SCHEDULE.append(event)
    event.start_event_loop()

    if event.persistent:
        # We have to sync to disk, otherwise we might end up
        # in situations (such as after a crash) where an object exists,
        # but the event tied to it does not.
        ecache = [event for event in SCHEDULE if event.persistent]            
        cache.set_pcache("_persistent_event_cache", ecache)
        cache.save_pcache()
        
    return event.pid 

def get_event(pid):
    """
    Return an event with the given pid, if it exists,
    otherwise return None.
    """
    pid = int(pid)
    imatches = [i for i, stored_event in enumerate(SCHEDULE)
                if stored_event.pid == pid]
    if imatches:
        return SCHEDULE[imatches[0]]

def del_event(pid):
    """
    Remove an event from scheduler. There should never be more than one
    event with a certain pid, this cleans up in case there are any multiples.
    """    
    pid = int(pid)
    imatches = [i for i, stored_event in enumerate(SCHEDULE)
                if stored_event.pid == pid]
    for imatch in imatches:
        event = SCHEDULE[imatch]
        event.stop_event_loop()
        del SCHEDULE[imatch]

        if event.persistent:
            # We have to sync to disk, otherwise we might end
            # up in situations (such as after a crash) where an
            # object has been removed, but the event tied to it remains.
            ecache = [event for event in SCHEDULE
                      if event.persistent]            
            cache.set_pcache("_persistent_event_cache", ecache)
            cache.save_pcache()
