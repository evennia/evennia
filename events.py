import session_mgr

"""
Holds the events scheduled in scheduler.py.
"""

schedule = {
              'check_sessions': 60,
           }
           
lastrun = {}

def check_sessions():
   """
   Check all of the connected sessions.
   """
   session_mgr.check_all_sessions()
