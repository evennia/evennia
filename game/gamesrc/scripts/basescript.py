"""
The base object to inherit from when implementing new Scripts.

Scripts are objects that handle everything in the game having
a time-component (i.e. that may change with time, with or without
a player being involved in the change). Scripts can work like "events",
in that they are triggered at regular intervals to do a certain script,
but an Script set on an object can also be responsible for silently 
checking if its state changes, so as to update it. Evennia use several
in-built scripts to keep track of things like time, to clean out
dropped connections etc. 

New Script objects (from these classes) are created using the
src.utils.create.create_script(scriptclass, ...) where scriptclass
is the python path to the specific class of script you want to use. 
"""

from src.scripts.scripts import Script as BaseScript

class Script(BaseScript):
    """
    All scripts should inherit from this class and implement
    some or all of its hook functions and variables.

    Important variables controlling the script object:
     self.key - the name of all scripts inheriting from this class
                (defaults to <unnamed>), used in lists and searches.
     self.desc - a description of the script, used in lists
     self.interval (seconds) - How often the event is triggered and calls self.at_repeat()
                 (see below) Defaults to 0 - that is, never calls at_repeat().
     self.start_delay (True/False). If True, will wait self.interval seconds
                befor calling self.at_repeat() for the first time. Defaults to False.
     self.repeats - The number of times at_repeat() should be called before automatically
                  stopping the script. Default is 0, which means infinitely many repeats.
     self.persistent (True/False). If True, the script will survive a server restart 
                (defaults to False). 

     self.obj (game Object)- this ties this script to a particular object. It is
          usually not needed to set this parameter explicitly; it's set in the 
          create methods. 


    Hook methods (should also include self as the first argument):
     at_script_creation() - called only once, when an object of this class
                            is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat 
                  stats at regular intervals is only valid to run while there is 
                  actual combat going on). 
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first call
                  to at_repeat(). 
      at_repeat() - Called every self.interval seconds. It will be called immediately
                  upon launch unless self.delay_start is True, which will delay
                  the first call of this method by self.interval seconds. If 
                  self.interval==0, this method will never be called. 
      at_stop() - Called as the script object is stopped and is about to be removed from
                  the game, e.g. because is_valid() returned False.
    """
    pass 
