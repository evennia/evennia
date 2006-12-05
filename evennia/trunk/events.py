"""
This is the events module, where all of the code for periodic events needs
to reside.

ADDING AN EVENT:
* Add an entry to the 'schedule' dictionary.
* Add the proper event_ function here.
* Profit.
"""

schedule = {
              'event_example': 60,
           }
           
lastrun = {}

def event_example(server):
   """
   This is where the example event would be placed. 
   """
   pass
