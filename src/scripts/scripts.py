"""
This module contains the base Script class that all
scripts are inheriting from.

It also defines a few common scripts. 
"""

from time import time 
from twisted.internet import task 
from src.server import sessionhandler
from src.typeclasses.typeclass import TypeClass
from src.scripts.models import ScriptDB
from src.comms import channelhandler 
from src.utils import logger

#
# Base script, inherit from Script below instead. 
#
class ScriptClass(TypeClass):
    """
    Base class for all Scripts. 
    """
    
    # private methods for handling timers. 

    def __eq__(self, other):
        """
        This has to be located at this level, having it in the
        parent doesn't work.
        """
        if other:
            return other.id == self.id
        return False 

    def _start_task(self):
        "start the task runner."
        if self.interval > 0:
            #print "Starting task runner"
            start_now = not self.start_delay
            self.ndb.twisted_task = task.LoopingCall(self._step_task)
            self.ndb.twisted_task.start(self.interval, now=start_now)          
            self.ndb.time_last_called = int(time())
            #self.save()
    def _stop_task(self):
        "stop the task runner"
        if hasattr(self.ndb, "twisted_task"):
            self.ndb.twisted_task.stop()
    def _step_task(self):
        "perform one repeat step of the script"        
        #print "Stepping task runner (obj %s)" % id(self)
        #print "Has dbobj: %s" % hasattr(self, 'dbobj') 
        if not self.is_valid():
            #the script is not valid anymore. Abort.
            self.stop()
            return 
        try:            
            self.at_repeat()
            if self.repeats:
                if self.repeats <= 1:
                    self.stop()
                    return 
                else:
                    self.repeats -= 1
            self.ndb.time_last_called = int(time())
            self.save()                
        except Exception:
            logger.log_trace()
            self._stop_task()

    def time_until_next_repeat(self):
        """
        Returns the time in seconds until the script will be
        run again. If this is not a stepping script, returns None. 
        This is not used in any way by the script's stepping
        system; it's only here for the user to be able to
        check in on their scripts and when they will next be run. 
        """
        if self.interval and hasattr(self.ndb, 'time_last_called'):
            return max(0, (self.ndb.time_last_called + self.interval) - int(time()))
        else:
            return None 

    def start(self, force_restart=False):
        """
        Called every time the script is started (for
        persistent scripts, this is usually once every server start)

        force_restart - if True, will always restart the script, regardless
                        of if it has started before. 
        """
        #print "Script %s (%s) start (active:%s, force:%s) ..." % (self.key, id(self.dbobj), 
        #                                                          self.is_active, force_restart)        
        if force_restart:
            self.is_active = False 
            
        should_start = True 
        if self.obj:
            try:
                #print "checking  cmdset ... for obj", self.obj
                dummy = object.__getattribute__(self.obj, 'cmdset')                
                #print "... checked cmdset"
            except AttributeError:
                #print "self.obj.cmdset not found. Setting is_active=False."
                self.is_active = False
                should_start = False
        if self.is_active and not force_restart:
            should_start = False

        if should_start:
            #print "... starting."        
            try:            
                self.is_active = True
                self.at_start()
                self._start_task()
                return 1
            except Exception:
                #print ".. error when starting"
                logger.log_trace()
                self.is_active = False 
                return 0
        else:
            # avoid starting over. 
            #print "... Start cancelled (invalid start or already running)."
            return 0 # this is used by validate() for counting started scripts        
            
    def stop(self):
        """
        Called to stop the script from running.
        This also deletes the script. 
        """
        #print "stopping script %s" % self.key
        try:
            self.at_stop()
        except Exception:
            logger.log_trace()
        if self.interval:
            try:
                self._stop_task()
            except Exception:
                pass
        self.is_running = False
        try:
            self.delete()
        except AssertionError:
            pass

    def is_valid(self):
        "placeholder"
        pass
    def at_start(self):
        "placeholder."
        pass        
    def at_stop(self):
        "placeholder"
        pass
    def at_repeat(self):
        "placeholder"
        pass


#
# Base Script - inherit from this
#

class Script(ScriptClass):
    """
    This is the class you should inherit from, it implements
    the hooks called by the script machinery.
    """

    def at_script_creation(self):
        """
        Only called once, by the create function.
        """
        self.key = "<unnamed>"           
        self.desc = ""
        self.interval = 0
        self.start_delay = False
        self.repeats = 0
        self.persistent = False             
    
    def is_valid(self):
        """
        Is called to check if the script is valid to run at this time. 
        Should return a boolean. The method is assumed to collect all needed
        information from its related self.obj.
        """
        return True

    def at_start(self):
        """
        Called whenever the script is started, which for persistent
        scripts is at least once every server start. 
        """
        pass

    def at_repeat(self):
        """
        Called repeatedly if this Script is set to repeat
        regularly. 
        """
        pass
    
    def at_stop(self):
        """
        Called whenever when it's time for this script to stop
        (either because is_valid returned False or )
        """
        pass

# Some useful default Script types

class DoNothing(Script):
    "An script that does nothing. Used as default."
    def at_script_creation(self):    
        "Setup the script"
        self.key = "sys_do_nothing"
        self.desc = "This does nothing."
        self.persistent = False
    def is_valid(self):
        "This script disables itself as soon as possible"
        return False
    
class CheckSessions(Script):
    "Check sessions regularly."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_session_check"
        self.desc = "Checks sessions so they are live."        
        self.interval = 60  # repeat every 60 seconds        
        self.persistent = True            

    def at_repeat(self):
        "called every 60 seconds"
        #print "session check!"
        #print "ValidateSessions run"
        sessionhandler.check_all_sessions()

class ValidateScripts(Script):
    "Check script validation regularly"    
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_scripts_validate"
        self.desc = "Validates all scripts regularly."
        self.interval = 3600 # validate every hour.
        self.persistent = True

    def at_repeat(self):
        "called every hour"        
        #print "ValidateScripts run."
        ScriptDB.objects.validate()

class ValidateChannelHandler(Script):
    "Update the channelhandler to make sure it's in sync." 

    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_channels_validate"
        self.desc = "Updates the channel handler"    
        self.interval = 3700 # validate a little later than ValidateScripts
        self.persistent = True
    
    def at_repeat(self):
        "called every hour+"
        #print "ValidateChannelHandler run."
        channelhandler.CHANNELHANDLER.update()
                
class AddCmdSet(Script):
    """
    This script permanently assigns a command set
    to an object. This is called automatically by the cmdhandler
    when an object is assigned a persistent cmdset. 

    To use, create this script, then assign to the two attributes
    'cmdset' and 'add_default' as appropriate:
    > from src.utils import create
    > script = create.create_script('src.scripts.scripts.AddCmdSet')
    > script.db.cmdset = 'game.gamesrc.commands.mycmdset.MyCmdSet'
    > script.db.add_default = False 
    > obj.scripts.add(script)

    """
    def at_script_creation(self):
        "Setup the script"
        if not self.key:
            self.key = "add_cmdset"
        if not self.desc:
            self.desc = "Adds a cmdset to an object."
        self.persistent = True 

        # this needs to be assigned to upon creation.
        # It should be a string pointing to the right
        # cmdset module and cmdset class name, e.g.  
        # 'examples.cmdset_redbutton.RedButtonCmdSet'        
        # self.db.cmdset = <cmdset_path>
        # self.db.add_default = <bool>

    def at_start(self):
        "Get cmdset and assign it."
        cmdset = self.db.cmdset
        if cmdset:
            if self.db.add_default:
                self.obj.cmdset.add_default(cmdset)
            else:
                self.obj.cmdset.add(cmdset)
        
    def at_stop(self):
        """
        This removes the cmdset when the script stops
        """
        cmdset = self.db.cmdset        
        if cmdset:
            if self.db.add_default:
                self.obj.cmdset.delete_default()
            else:
                self.obj.cmdset.delete(cmdset)
