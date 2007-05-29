import session_mgr

"""
Holds the events scheduled in scheduler.py.
"""

def evt_check_sessions():
   """
   Event: Check all of the connected sessions.
   """
   session_mgr.check_all_sessions()