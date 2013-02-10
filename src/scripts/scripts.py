"""
This module contains the base Script class that all
scripts are inheriting from.

It also defines a few common scripts.
"""

from sys import getsizeof
from time import time
from collections import defaultdict
from twisted.internet.defer import maybeDeferred
from twisted.internet.task import LoopingCall
from django.conf import settings
from src.server import caches
from src.typeclasses.typeclass import TypeClass
from src.scripts.models import ScriptDB
from src.comms import channelhandler
from src.utils import logger, is_pypy
from django.utils.translation import ugettext as _

__all__ = ["Script", "DoNothing", "CheckSessions", "ValidateScripts", "ValidateChannelHandler"]
if not is_pypy:
    __all__.append("ClearAttributeCache")

_SESSIONS = None
_ATTRIBUTE_CACHE_MAXSIZE = settings.ATTRIBUTE_CACHE_MAXSIZE # attr-cache size in MB.

#
# Base script, inherit from Script below instead.
#
class ScriptClass(TypeClass):
    """
    Base class for scripts. Don't inherit from this, inherit from Script instead.
    """
    # private methods

    def __eq__(self, other):
        """
        This has to be located at this level, having it in the
        parent doesn't work.
        """
        try:
            return other.dbid == self.dbid
        except Exception:
            return False

    def _start_task(self, start_now=True):
        "start task runner"

        self.ndb.twisted_task = LoopingCall(self._step_task)
        if self.ndb._paused_time:
            # we had paused the script, restarting
            #print " start with paused time:", self.key, self.ndb._paused_time
            self.ndb.twisted_task.start(self.ndb._paused_time, now=False)
        else:
            # starting script anew.
            #print "_start_task: self.interval:", self.key, self.dbobj.interval
            self.ndb.twisted_task.start(self.dbobj.interval, now=start_now and not self.start_delay)
        self.ndb.time_last_called = int(time())

    def _stop_task(self):
        "stop task runner"
        try:
            #print "stopping twisted task:", id(self.ndb.twisted_task), self.obj
            if self.ndb.twisted_task and self.ndb.twisted_task.running:
                self.ndb.twisted_task.stop()
        except Exception:
            logger.log_trace()
    def _step_err_callback(self, e):
        "callback for runner errors"
        cname = self.__class__.__name__
        estring = _("Script %(key)s(#%(dbid)i) of type '%(cname)s': at_repeat() error '%(err)s'.") % \
                   {"key":self.key, "dbid":self.dbid, "cname":cname, "err":e.getErrorMessage()}
        try:
            self.dbobj.db_obj.msg(estring)
        except Exception:
            pass
        logger.log_errmsg(estring)
    def _step_succ_callback(self):
        "step task runner. No try..except needed due to defer wrap."
        if not self.is_valid():
            self.stop()
            return
        self.at_repeat()
        repeats = self.dbobj.db_repeats
        if repeats <= 0:
            pass # infinite repeat
        elif repeats == 1:
            self.stop()
            return
        else:
            self.dbobj.db_repeats -= 1
        self.ndb.time_last_called = int(time())
        self.save()

        if self.ndb._paused_time:
            # this means we were running an unpaused script, for the time remaining
            # after the pause. Now we start a normal-running timer again.
            #print "switching to normal run:", self.key
            del self.ndb._paused_time
            self._stop_task()
            self._start_task(start_now=False)


    def _step_task(self):
        "step task"
        try:
            d = maybeDeferred(self._step_succ_callback)
            d.addErrback(self._step_err_callback)
            return d
        except Exception:
            logger.log_trace()


    # Public methods

    def time_until_next_repeat(self):
        """
        Returns the time in seconds until the script will be
        run again. If this is not a stepping script, returns None.
        This is not used in any way by the script's stepping
        system; it's only here for the user to be able to
        check in on their scripts and when they will next be run.
        """
        try:
            if self.ndb._paused_time:
                return max(0, (self.ndb.time_last_called + self.ndb._paused_time) - int(time()))
            else:
                return max(0, (self.ndb.time_last_called + self.dbobj.db_interval) - int(time()))
        except Exception:
            return None

    def start(self, force_restart=False):
        """
        Called every time the script is started (for
        persistent scripts, this is usually once every server start)

        force_restart - if True, will always restart the script, regardless
                        of if it has started before.

        returns 0 or 1 to indicated the script has been started or not. Used in counting.
        """
        #print "Script %s (%s) start (active:%s, force:%s) ..." % (self.key, id(self.dbobj),
        #                                                          self.is_active, force_restart)

        if self.dbobj.is_active and not force_restart:
            # script already runs and should not be restarted.
            return 0

        obj = self.obj
        if obj:
            # check so the scripted object is valid and initalized
            try:
                object.__getattribute__(obj, 'cmdset')
            except AttributeError:
                # this means the object is not initialized.
                self.dbobj.is_active = False
                return 0

        # try to restart a paused script
        if self.unpause():
            return 1

        # try to start the script from scratch
        try:
            self.dbobj.is_active = True
            self.at_start()
            if self.dbobj.db_interval > 0:
                self._start_task()
            return 1
        except Exception:
            logger.log_trace()
            self.dbobj.is_active = False
            return 0

    def stop(self, kill=False):
        """
        Called to stop the script from running.
        This also deletes the script.

        kill - don't call finishing hooks.
        """
        #print "stopping script %s" % self.key
        #import pdb
        #pdb.set_trace()
        if not kill:
            try:
                self.at_stop()
            except Exception:
                logger.log_trace()
        if self.dbobj.db_interval > 0:
            try:
                self._stop_task()
            except Exception:
                logger.log_trace("Stopping script %s(%s)" % (self.key, self.dbid))
                pass
        try:
            self.dbobj.delete()
        except AssertionError:
            logger.log_trace()
            return 0
        return 1

    def pause(self):
        """
        This stops a running script and stores its active state.
        """
        #print "pausing", self.key, self.time_until_next_repeat()
        dt = self.time_until_next_repeat()
        if dt == None:
            return
        self.db._paused_time = dt
        self._stop_task()

    def unpause(self):
        """
        Restart a paused script. This WILL call at_start().
        """
        #print "unpausing", self.key, self.db._paused_time
        dt = self.db._paused_time
        if dt == None:
            return False
        try:
            self.dbobj.is_active = True
            self.at_start()
            self.ndb._paused_time = dt
            self._start_task(start_now=False)
            del self.db._paused_time
        except Exception:
            logger.log_trace()
            self.dbobj.is_active = False
            return False
        return True

    # hooks
    def at_script_creation(self):
        "placeholder"
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
    def at_init(self):
        "called when typeclass re-caches. Usually not used for scripts."
        pass


#
# Base Script - inherit from this
#

class Script(ScriptClass):
    """
    This is the class you should inherit from, it implements
    the hooks called by the script machinery.
    """

    def __init__(self, dbobj):
        """
        This is the base TypeClass for all Scripts. Scripts describe events, timers and states in game,
        they can have a time component or describe a state that changes under certain conditions.

        Script API:

        * Available properties (only available on initiated Typeclass objects)

         key (string) - name of object
         name (string)- same as key
         aliases (list of strings) - aliases to the object. Will be saved to database as AliasDB entries but returned as strings.
         dbref (int, read-only) - unique #id-number. Also "id" can be used.
         dbobj (Object, read-only) - link to database model. dbobj.typeclass points back to this class
         typeclass (Object, read-only) - this links back to this class as an identified only. Use self.swap_typeclass() to switch.
         date_created (string) - time stamp of object creation
         permissions (list of strings) - list of permission strings

         desc (string)      - optional description of script, shown in listings
         obj (Object)       - optional object that this script is connected to and acts on (set automatically by obj.scripts.add())
         interval (int)     - how often script should run, in seconds. <=0 turns off ticker
         start_delay (bool) - if the script should start repeating right away or wait self.interval seconds
         repeats (int)      - how many times the script should repeat before stopping. <=0 means infinite repeats
         persistent (bool)  - if script should survive a server shutdown or not
         is_active (bool)   - if script is currently running

        * Handlers

         locks - lock-handler: use locks.add() to add new lock strings
         db - attribute-handler: store/retrieve database attributes on this self.db.myattr=val, val=self.db.myattr
         ndb - non-persistent attribute handler: same as db but does not create a database entry when storing data

        * Helper methods

         start() - start script (this usually happens automatically at creation and obj.script.add() etc)
         stop()  - stop script, and delete it
         pause() - put the script on hold, until unpause() is called. If script is persistent, the pause state will survive a shutdown.
         unpause() - restart a previously paused script. The script will continue as if it was never paused.
         time_until_next_repeat() - if a timed script (interval>0), returns time until next tick

        * Hook methods

         at_script_creation() - called only once, when an object of this
                                class is first created.
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
                      self.interval<=0, this method will never be called.
          at_stop() - Called as the script object is stopped and is about to be removed from
                      the game, e.g. because is_valid() returned False.
          at_server_reload() - Called when server reloads. Can be used to save temporary
                      variables you want should survive a reload.
          at_server_shutdown() - called at a full server shutdown.


          """
        super(Script, self).__init__(dbobj)

    def at_script_creation(self):
        """
        Only called once, by the create function.
        """
        self.key = "<unnamed>"
        self.desc = ""
        self.interval = 0 # infinite
        self.start_delay = False
        self.repeats = 0  # infinite
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
        scripts is at least once every server start. It will also be called
        when starting again after a pause (such as after a server reload)
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

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for restart/reboot.
        If you want to, for example, save non-persistent properties across a restart,
        this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully (i.e. not for
        a restart).
        """
        pass



# Some useful default Script types used by Evennia.

class DoNothing(Script):
    "An script that does nothing. Used as default fallback."
    def at_script_creation(self):
         "Setup the script"
         self.key = "sys_do_nothing"
         self.desc = _("This is an empty placeholder script.")

class Store(Script):
    "Simple storage script"
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_storage"
        self.desc = _("This is a generic storage container.")

class CheckSessions(Script):
    "Check sessions regularly."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_session_check"
        self.desc = _("Checks sessions so they are live.")
        self.interval = 60  # repeat every 60 seconds
        self.persistent = True

    def at_repeat(self):
        "called every 60 seconds"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        #print "session check!"
        #print "ValidateSessions run"
        _SESSIONS.validate_sessions()

class ValidateScripts(Script):
    "Check script validation regularly"
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_scripts_validate"
        self.desc = _("Validates all scripts regularly.")
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
        self.desc = _("Updates the channel handler")
        self.interval = 3700 # validate a little later than ValidateScripts
        self.persistent = True

    def at_repeat(self):
        "called every hour+"
        #print "ValidateChannelHandler run."
        channelhandler.CHANNELHANDLER.update()

class ClearAttributeCache(Script):
    "Clear the attribute cache."
    def at_script_creation(self):
        "Setup the script"
        self.key = "sys_cache_clear"
        self.desc = _("Clears the Attribute Cache")
        self.interval = 3600 * 2
        self.persistent = True
    def at_repeat(self):
        "called every 2 hours. Sets a max attr-cache limit to 100 MB." # enough for normal usage?
        if is_pypy:
            # pypy don't support get_size, so we have to skip out here.
            return
        attr_cache_size, _, _ = caches.get_cache_sizes()
        if attr_cache_size > _ATTRIBUTE_CACHE_MAXSIZE:
            caches.flush_attr_cache()
