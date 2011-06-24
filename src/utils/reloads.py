"""
This holds the mechanism for reloading the game modules on the
fly. It's in this separate module since it's not a good idea to
keep it in server.py since it messes with importing, and it's
also not good to tie such important functionality to a user-definable
command class. 
"""

import time 
from django.db.models.loading import AppCache
from django.utils.datastructures import SortedDict
from django.conf import settings
from src.scripts.models import ScriptDB
from src.objects.models import ObjectDB
from src.players.models import PlayerDB
from src.comms.models import Channel, Msg
from src.help.models import HelpEntry

from src.typeclasses import models as typeclassmodels
from src.comms import channelhandler
from src.comms.models import Channel
from src.utils import reimport, utils, logger 

def start_reload_loop():
    """
    This starts the asynchronous reset loop. While
    important that it runs asynchronously (to not block the
    mud while its running), the order at which things are 
    updated does matter. 
    """

    def run_loop():
        ""
        cemit_info('-'*50)
        cemit_info(" Starting asynchronous server reload.")
        reload_modules()         
        reload_scripts()
        reload_commands()
        reset_loop()
        
    def at_return(r):
        "default callback"
        cemit_info(" Asynchronous server reload finished.\n" + '-'*50)
    def at_err(e):
        "error callback"        
        string = " Reload: Asynchronous reset exited with an error:\n {r%s{n" % e.getErrorMessage()
        cemit_info(string)
        
    utils.run_async(run_loop, at_return, at_err)


def reload_modules():
    """
    Reload modules that don't have any variables that can be reset.
    Note that python reloading is a tricky art and strange things have
    been known to happen if debugging and reloading a lot. A server 
    cold reboot is often needed eventually.

    """
    # We protect e.g. src/ from reload since reloading it in a running
    # server can create unexpected results (and besides, non-evennia devs 
    # should never need to do that anyway). Updating src requires a server
    # reboot. Modules in except_dirs are considered ok to reload despite being
    # inside src/
    protected_dirs = ('src.', 'django.', 'twisted.')     # note that these MUST be tuples!
    except_dirs = ('src.commands.default.',) #                          "  

    # flag 'dangerous' typeclasses (those which retain a memory
    # reference, notably Scripts with a timer component) for
    # non-reload, since these cannot be safely cleaned from memory
    # without causing havoc. A server reboot is required for updating
    # these (or killing all running, timed scripts).
    unsafe_modules = []
    for scriptobj in ScriptDB.objects.get_all_scripts():
        if (scriptobj.interval > -1) and scriptobj.typeclass_path:
            unsafe_modules.append(scriptobj.typeclass_path)            
    unsafe_modules = list(set(unsafe_modules))

    def safe_dir_to_reload(modpath):
        "Check so modpath is not a subdir of a protected dir, and not an ok exception"
        return not any(modpath.startswith(pdir) and not any(modpath.startswith(edir) for edir in except_dirs) for pdir in protected_dirs)
    def safe_mod_to_reload(modpath):
        "Check so modpath is not in an unsafe module"
        return not any(mpath.startswith(modpath) for mpath in unsafe_modules)
                                               
    #cemit_info(" Cleaning module caches ...")

    # clean as much of the caches as we can
    cache = AppCache()
    cache.app_store = SortedDict()
    #cache.app_models = SortedDict() # cannot clean this, it resets ContentTypes!
    cache.app_errors = {}
    cache.handled = {}
    cache.loaded = False
 
    # find modified modules 
    modified = reimport.modified()
    safe_dir_modified = [mod for mod in modified if safe_dir_to_reload(mod)]
    unsafe_dir_modified = [mod for mod in modified if mod not in safe_dir_modified]
    safe_modified = [mod for mod in safe_dir_modified if safe_mod_to_reload(mod)]
    unsafe_mod_modified = [mod for mod in safe_dir_modified if mod not in safe_modified]

    string = ""
    if unsafe_dir_modified or unsafe_mod_modified:

        if unsafe_mod_modified:
            string += "\n {rModules containing Script classes with a timer component{n" 
            string += "\n {rand which has already spawned instances cannot be reloaded safely.{n"             
        string += "\n {rThese module(s) can only be reloaded by server reboot:{n\n  %s\n"
        string = string % ", ".join(unsafe_dir_modified + unsafe_mod_modified)

    if string:
        cemit_info(string) 

    if safe_modified:
        cemit_info(" Reloading safe module(s):{n\n  %s" % "\n  ".join(safe_modified))
        reimport.reimport(*safe_modified)
        wait_time = 5
        cemit_info(" Waiting %s secs to give modules time to re-cache ..." % wait_time)
        time.sleep(wait_time)        
        cemit_info(" ... all safe modules reloaded.") 
    else:
        cemit_info(" No modules reloaded.")

    # clean out cache dictionary of typeclasses, exits and channels    
    typeclassmodels.reset()    
    channelhandler.CHANNELHANDLER.update()

    # run through all objects in database, forcing re-caching.

     
def reload_scripts(scripts=None, obj=None, key=None, 
                   dbref=None, init_mode=False):
    """
    Run a validation of the script database.
    obj - only validate scripts on this object
    key - only validate scripts with this key
    dbref - only validate the script with this unique idref    
    emit_to_obj - which object to receive error message
    init_mode - during init-mode, non-persistent scripts are 
                cleaned out. All persistent scripts are force-started.

    """

    nr_started, nr_stopped = ScriptDB.objects.validate(scripts=scripts, 
                                                       obj=obj, key=key, 
                                                       dbref=dbref, 
                                                       init_mode=init_mode)
    if nr_started or nr_stopped:
        string = " Started %s script(s). Stopped %s invalid script(s)." % \
            (nr_started, nr_stopped)            
        cemit_info(string)
    
def reload_commands():
    from src.commands import cmdsethandler
    cmdsethandler.CACHED_CMDSETS = {}
    #cemit_info(" Cleaned cmdset cache.")

def reset_loop():
    "Reload and restart all entities that can be reloaded."    
    # run the reset loop on all objects
    cemit_info(" Resetting all cached database entities ...")
    t1 = time.time()
    [h.locks.reset() for h in HelpEntry.objects.all()]
    [m.locks.reset() for m in Msg.objects.all()]
    [c.locks.reset() for c in Channel.objects.all()]    
    [s.locks.reset() for s in ScriptDB.objects.all()]
    [(o.typeclass(o), o.cmdset.reset(), o.locks.reset(), o.at_cache()) for o in ObjectDB.get_all_cached_instances()]    
    [(p.typeclass(p), p.cmdset.reset(), p.locks.reset()) for p in PlayerDB.get_all_cached_instances()]

    t2 = time.time()
    cemit_info(" ... Reset finished in %g seconds." % (t2-t1))

def cemit_info(message):
    """
    Sends the info to a pre-set channel. This channel is 
    set by CHANNEL_MUDINFO in settings.
    """

    logger.log_infomsg(message)
    infochan = None
    try:
        infochan = settings.CHANNEL_MUDINFO
        infochan = Channel.objects.get_channel(infochan[0])
    except Exception:
        pass
    if infochan:        
        cname = infochan.key
        cmessage = "\n".join(["[%s][reload]: %s" % (cname, line) for line in message.split('\n')])        
        infochan.msg(cmessage)        
    else:
        cmessage = "\n".join(["[MUDINFO][reload] %s" % line for line in message.split('\n')])                        
        logger.log_infomsg(cmessage)
