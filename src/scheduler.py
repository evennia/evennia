"""
This file contains the event scheduler system.

ADDING AN EVENT:
* Create an event sub-class from the IntervalEvent class in events.py. 
* Call src.scheduler.add_event() with your IntervalEvent subclass as the arg.
* Make sure that the module where your add_event() call resides is either
  imported, or that add_event() is called by a command or some kind of action.
* Profit.
"""

# List of IntervalEvent sub-classed objects.
schedule = []
        
def add_event(event):
    """
    Adds an event instance to the scheduled event list. Call this any time you
    need to add a custom event to the global scheduler.
    
    Args:
     * event: (IntervalEvent) The event to add to the scheduler.
    """
    schedule.append(event)
    event.start_event_loop()