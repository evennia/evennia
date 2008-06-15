"""
This module is responsible for managing scripts and their connection to the
Object class model. It is important to keep this as independent from the
codebase as possible in order to allow for drop-in replacements. All
interaction with actual script methods should happen via calls to Objects.
"""
import os
from traceback import format_exc

import settings
from src import logger

# A dictionary with keys equivalent to the script's name and values that
# contain references to the associated module for each key.
cached_scripts = {}

def scriptlink(source_obj, scriptname):
    """
    Each Object will refer to this function when trying to execute a function
    contained within a scripted module. For the sake of ease of management,
    modules are cached and compiled as they are requested and stored in
    the cached_scripts dictionary.
    
    Returns a reference to an instance of the script's class as per it's
    class_factory() method.
    
    source_obj: (Object) A reference to the object being scripted.
    scriptname: (str) Name of the module to load (minus 'scripts').
    """
    # The module is already cached, just return it rather than re-load.
    retval = cached_scripts.get(scriptname, False)
    if retval:
        return retval.class_factory(source_obj)

    ##
    ## NOTE: Only go past here when the script isn't already cached.
    ##
    
    # Split the script name up by periods to give us the directory we need
    # to change to. I really wish we didn't have to do this, but there's some
    # strange issue with __import__ and more than two directories worth of
    # nesting.
    path_split = scriptname.split('.')
    newpath_str = '/'.join(path_split[:-1])
    # Lop the module name off the end.
    modname = path_split[-1]

    try:
        # Change the working directory to the location of the script and import.
        os.chdir('%s/%s/' % (settings.SCRIPT_ROOT, newpath_str))
        logger.log_infomsg("SCRIPT: Caching and importing %s." % (modname))
        modreference = __import__(modname)
        # Store the module reference for later fast retrieval.
        cached_scripts[scriptname] = modreference
    except ImportError:
        logger.log_infomsg('Error importing %s: %s' % (modname, format_exc()))
        os.chdir(settings.BASE_PATH)
        return
    except OSError:
        logger.log_infomsg('Invalid module path: %s' % (format_exc()))
        os.chdir(settings.BASE_PATH)
        return

    # Change back to the original working directory.
    os.chdir(settings.BASE_PATH)

    # The new script module has been cached, return the reference.
    return modreference.class_factory(source_obj)
