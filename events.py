import time
from twisted.internet import protocol, reactor, defer
import session_mgr

"""
Holds the events scheduled in scheduler.py.
"""

# Dictionary of events with a list in the form of: [<interval>, <lastrantime>]
schedule = {
              'check_sessions': [60, None]
           }
           

def check_sessions():
   """
   Event: Check all of the connected sessions.
   """
   session_mgr.check_all_sessions()
   schedule['check_sessions'][1] = time.time()
   reactor.callLater(schedule['check_sessions'][0], check_sessions)
