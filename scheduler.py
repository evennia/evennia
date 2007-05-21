import events
from twisted.internet import protocol, reactor, defer
"""
A really simple scheduler. We can probably get a lot fancier with this
in the future, but it'll do for now.

ADDING AN EVENT:
* Add an entry to the 'schedule' dictionary in the 'events' file.
* Add the proper event_ function here.
* Profit.
"""
   
# The timer method to be triggered by the main server loop.
def start_events():
   """
   Handle one tic/heartbeat.
   """
   for event in events.schedule:
      event_func = getattr(events, event)

      if callable(event_func):
         reactor.callLater(events.schedule[event][0], event_func)
