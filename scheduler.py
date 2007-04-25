import time
import events
"""
A really simple scheduler. We can probably get a lot fancier with this
in the future, but it'll do for now.

ADDING AN EVENT:
* Add an entry to the 'schedule' dictionary in the 'events' file.
* Add the proper event_ function here.
* Profit.
"""
   
# The timer method to be triggered by the main server loop.
def heartbeat():
   """
   Handle one tic/heartbeat.
   """
   tictime = time.time()
   for event in events.schedule:
      try: 
         events.lastrun[event]
      except: 
         events.lastrun[event] = time.time()
      
      diff = tictime - events.lastrun[event]

      if diff >= events.schedule[event]:
         event_func = getattr(events, event)
   
         if callable(event_func):
            event_func()
            
         # We'll get a new reading for time for accuracy.
         events.lastrun[event] = time.time()
