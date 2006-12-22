import time
"""
A really simple scheduler. We can probably get a lot fancier with this
in the future, but it'll do for now.

ADDING AN EVENT:
* Add an entry to the 'schedule' dictionary.
* Add the proper event_ function here.
* Profit.
"""

schedule = {
              'event_example': 60,
           }
           
lastrun = {}

"""
BEGIN EVENTS
"""
def event_example():
   """
   This is where the example event would be placed. 
   """
   pass
"""
END EVENTS
"""
   
# The timer method to be triggered by the main server loop.
def heartbeat():
   """
   Handle one tic/heartbeat.
   """
   tictime = time.time()
   for event in schedule:
      try: 
         lastrun[event]
      except: 
         lastrun[event] = time.time()
      
      diff = tictime - lastrun[event]

      if diff >= schedule[event]:
         event_func = getattr(self, event)
   
         if callable(event_func):
            event_func()
            
         # We'll get a new reading for time for accuracy.
         lastrun[event] = time.time()
