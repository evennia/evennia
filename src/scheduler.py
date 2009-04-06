"""
This file contains the event scheduler system.

ADDING AN EVENT:
* Create an event sub-class in events.py. 
* Add it to the add_global_events() function at the end of the module.
* Profit.
"""

# List of IntervalEvent sub-classed objects.
schedule = []

def start_events():
    """
    Start the event system, which is built on Twisted's framework.
    """
    for event in schedule:
        event.start_event_loop()
        
def add_event(event):
    """
    Adds an event instance to the scheduled event list.
    
    Args:
     * event: (IntervalEvent) The event to add to the scheduler.
    """
    schedule.append(event)
    event.start_event_loop()