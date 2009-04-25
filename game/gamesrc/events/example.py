"""
Example of the event system. To try it out, make sure to import it from somewhere
covered by @reload (like the script parent). Create an object inheriting
the red_button parent to see its effects (e.g. @create button=examples/red_button)

Technically the event don't contain any game logics, all it does is locate all
objects inheriting to a particular script parent and calls one of its functions
at a regular interval.
"""

from src.events import IntervalEvent
from src.scheduler import add_event
from src.objects.models import Object

#the logger is useful for debugging since there is no source object to send to
from src.logger import log_infomsg

#Example of the event system. This example adds an event to the red_button parent
#in parents/examples. It makes the button blink temptingly at a regular interval.

class EventBlinkButton(IntervalEvent):
    """    
    This event lets the button flash at regular intervals. 
    """
    def __init__(self):
        """
        A custom init method also storing the source object.

        """
        super(EventBlinkButton, self).__init__()
        self.name = 'event_blink_red_button'
        #how often to blink, in seconds
        self.interval = 30 
        #the description is seen when you run @ps in-game.
        self.description = "Blink red buttons regularly."            

    def event_function(self):
        """
        This stub function is automatically fired every self.interval seconds.

        In this case we do a search for all objects inheriting from the correct
        parent and call a function on them.
        """
        #find all objects inheriting from red_button (parents are per definition
        #stored with the gamesrc/parent/ drawer as a base)
        parent = 'examples.red_button'
        buttons = Object.objects.global_object_script_parent_search(parent)
        log_infomsg("buttons found: %s" % buttons)

        for b in buttons:
            b.scriptlink.blink()
        
#create and add the event to the global handler
blink_event = EventBlinkButton()
add_event(blink_event)
