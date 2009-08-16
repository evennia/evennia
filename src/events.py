"""
Holds the global events scheduled in scheduler.py.

Events are sub-classed from IntervalEvent (which is not to be used directly).
Create your sub-class, call src.scheduler.add_event(YourEventClass()) to add
it to the global scheduler.

Use @ps to view the event list.
"""
import time
from twisted.internet import task
import session_mgr
from src import scheduler
from src import defines_global
from src.objects.models import Object

class IntervalEvent(object):
    """
    Represents an event that is triggered periodically. Sub-class this and
    fill in the stub function.
    """    
    def __init__(self):
        """
        Executed when the class is instantiated.
        """
        # This is set to prevent a Nonetype exception on @ps before the
        # event is fired for the first time.
        self.time_last_executed = time.time()
        # This is what shows up on @ps in-game.
        self.name = None
        # An interval (in seconds) for execution.
        self.interval = None
        # A reference to the task.LoopingCall object.
        self.looped_task = None
    
    def __unicode__(self):
        """
        String representation of the event.
        """
        return self.name
    
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
    
    def event_function(self):
        """                    
        ### Over-ride this in your sub-class. ###
        """   
        pass
    
    def get_nextfire(self):
        """
        Returns a value in seconds when the event is going to fire off next.
        """
        return max(0,(self.time_last_executed + self.interval) - time.time())
    
    def set_lastfired(self):
        """
        Sets the timestamp (int) that the event was last fired.
        """
        self.time_last_executed = time.time()
        
    def fire_event(self):
        """
        Set the last ran stamp and fire off the event.
        """
        self.set_lastfired()
        self.event_function()

class IEvt_Check_Sessions(IntervalEvent):
    """
    Event: Check all of the connected sessions.
    """
    def __init__(self):
        super(IEvt_Check_Sessions, self).__init__()
        self.name = 'IEvt_Check_Sessions'
        self.interval = 60
        self.description = "Session consistency checks."
    
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
        self.name = 'IEvt_Destroy_Objects'
        self.interval = 1800
        self.description = "Clean out objects marked for destruction."

    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        going_objects = Object.objects.filter(type__exact=defines_global.OTYPE_GOING)
        for obj in going_objects:
            obj.delete()
    
def add_global_events():
    """
    When the server is started up, this is triggered to add all of the
    events in this file to the scheduler.
    """
    # Create an instance and add it to the scheduler.
    scheduler.add_event(IEvt_Check_Sessions())
    scheduler.add_event(IEvt_Destroy_Objects())

