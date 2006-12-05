import time
import events

class Scheduler:
   """
   A really simple scheduler. We can probably get a lot fancier with this
   in the future, but it'll do for now.
   
   Open up events.py for a schedule of events and their respective functions.
   """
   def __init__(self, server):
      self.server = server
      
   # The timer method to be triggered by the main server loop.
   def heartbeat(self):
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
               event_func(self.server)
               
            # We'll get a new reading for time for accuracy.
            events.lastrun[event] = time.time()

