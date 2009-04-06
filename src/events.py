"""
Holds the global events scheduled in scheduler.py.

Events are sub-classed from IntervalEvent (which is not to be used directly).
Create your sub-class, call src.scheduler.add_event(YourEventClass()) to add
it to the global scheduler.
"""
import time
from twisted.internet import task
import session_mgr
from src import scheduler

class IntervalEvent(object):
    """
    Represents an event that is triggered periodically. Sub-class this and
    fill in the stub function.
    """
    # This is what shows up on @ps in-game.
    name = None
    # An interval (in seconds) for execution.
    interval = None
    # A timestamp (int) for the last time the event was fired.
    time_last_executed = None
    # A reference to the task.LoopingCall object.
    looped_task = None
    
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
        return (self.time_last_executed + self.interval) - time.time()
    
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
    name = 'IEvt_Check_Sessions'
    interval = 60
    description = "Session consistency checks."
    
    def event_function(self):
        """
        This is the function that is fired every self.interval seconds.
        """
        session_mgr.check_all_sessions()

def add_global_events():
    """
    When the server is started up, this is triggered to add all of the
    events in this file to the scheduler.
    """
    # Create an instance and add it to the scheduler.
    scheduler.add_event(IEvt_Check_Sessions())