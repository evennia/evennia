"""
Example of the event system. To try it out, make sure to import it from somewhere
covered by @reload (like the script parent). Create an object inheriting
the red_button parent to see its effects (e.g. @create button=examples/red_button)

Technically the event don't contain any game logics, all it does is locate all
objects inheriting to a particular script parent and calls one of its functions
at a regular interval.

Note that this type of event will cause *all* red buttons to blink at the same
time, regardless when they were created. This is a very efficient way
to do it (it is also very useful for global events like weather patterns
and day-night cycles), but you can also add events directly to individual objecs
(see the example event in gamesrc/parents/examples/red_button)
"""

import traceback 
from src.events import IntervalEvent
from src import scheduler
from src.objects.models import Object

#the logger is useful for debugging
from src import logger

class EventBlinkButton(IntervalEvent):
    """    
    This event lets the button flash at regular intervals. 
    """
    def __init__(self):
        """
        Note that we do NOT make this event persistent across
        reboots since we are actually creating it (i.e. restarting it)
        every time the module is reloaded. 
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

        Note that we must make sure to handle all tracebacks in this
        function to avoid trouble. 
        """
        #find all objects inheriting from red_button (parents are per definition
        #stored with the gamesrc/parent/ drawer as a base)
        parent = 'examples.red_button'
        buttons = Object.objects.global_object_script_parent_search(parent)

        for b in buttons:
            try:
                b.scriptlink.blink()
            except:
                # Print all tracebacks to the log instead of letting them by. 
                # This is important, we must handle these exceptions gracefully!
                logger.log_errmsg(traceback.print_exc())
                
#create and add the event to the global handler
blink_event = EventBlinkButton()
scheduler.add_event(blink_event)
