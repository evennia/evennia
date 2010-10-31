"""
This holds the mechanism for reloading the game modules on the
fly. It's in this separate module since it's not a good idea to
keep it in server.py since it messes with importing, and it's
also not good to tie such important functionality to a user-definable
command class. 
"""

from django.db.models.loading import AppCache
from django.utils.datastructures import SortedDict
from django.conf import settings
from src.scripts.models import ScriptDB
from src.typeclasses import models as typeclassmodels
from src.objects import exithandler 
from src.comms import channelhandler
from src.comms.models import Channel
from src.utils import reimport 
from src.utils import logger

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
    # reboot.
    protected_dirs = ('src.',)

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
        "Check so modpath is not a subdir of a protected dir"
        return not any(modpath.startswith(pdir) for pdir in protected_dirs)
    def safe_mod_to_reload(modpath):
        "Check so modpath is not in an unsafe module"
        return not any(mpath.startswith(modpath) for mpath in unsafe_modules)
                                               
    cemit_info('-'*50 +"\n Cleaning module caches ...")

    # clean as much of the caches as we can
    cache = AppCache()
    cache.app_store = SortedDict()
    cache.app_models = SortedDict()
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
        string += "\n WARNING: Some modules can not be reloaded"
        string += "\n since it would not be safe to do so.\n"
        if unsafe_dir_modified:
            string += "\n-The following module(s) is/are located in the src/ directory and"
            string += "\n should not be reloaded without a server reboot:\n  %s\n" 
            string = string % unsafe_dir_modified
        if unsafe_mod_modified:
            string += "\n-The following modules contains at least one Script class with a timer"
            string += "\n component and which has already spawned instances - these cannot be "
            string += "\n safely cleaned from memory on the fly. Stop all the affected scripts "
            string += "\n or restart the server to safely reload:\n  %s\n"
            string = string % unsafe_mod_modified
    if string:
        cemit_info(string) 

    if safe_modified:
        cemit_info(" Reloading module(s):\n  %s ..." % safe_modified)
        reimport.reimport(*safe_modified)
        cemit_info(" ...all safe modules reloaded.") 
    else:
        cemit_info(" Nothing was reloaded.")

    # clean out cache dictionary of typeclasses, exits and channe    
    typeclassmodels.reset()
    exithandler.EXITHANDLER.reset()
    channelhandler.CHANNELHANDLER.reset()
     
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
    cemit_info(" Validating scripts ...")
    nr_started, nr_stopped = ScriptDB.objects.validate(scripts=scripts, 
                                                       obj=obj, key=key, 
                                                       dbref=dbref, 
                                                       init_mode=init_mode)

    string = " Started %s script(s). Stopped %s invalid script(s)." % \
                                          (nr_started, nr_stopped)            
    cemit_info(string)
    
def reload_commands():
    from src.commands import cmdsethandler
    cmdsethandler.CACHED_CMDSETS = {}
    cemit_info(" Cleaned cmdset cache.\n" + '-'*50)

def cemit_info(message):
    """
    Sends the info to a pre-set channel. This channel is 
    set by CHANNEL_MUDINFO in settings.
    """
    logger.log_infomsg(message)
    try:
        infochan = settings.CHANNEL_MUDINFO
        infochan = Channel.objects.get_channel(infochan[0])
    except Exception:
        return 
    cname = infochan.key
    cmessage = "\n".join(["[%s]: %s" % (cname, line) for line in message.split('\n')])        
    infochan.msg(cmessage)        

