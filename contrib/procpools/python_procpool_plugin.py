"""
Python ProcPool plugin

Evennia contribution - Griatch 2012

This is a plugin for the Evennia services. It will make the service
and run_async in python_procpool.py available to the system.

To activate, add the following line to your settings file:

SERVER_SERVICES_PLUGIN_MODULES.append("contrib.procpools.python_procpool_plugin")

Next reboot the server and the new service will be available.

If you want to adjust the defaults, copy this file to
game/gamesrc/conf/ and re-point
settings.SERVER_SERVICES_PLUGINS_MODULES to that file instead.  This
is to avoid clashes with eventual upstream modifications to this file.

It is not recommended to use this with an SQLite3 database, at least
if you plan to do many out-of-process database writes. SQLite3 does
not work very well with a high frequency of off-process writes due to
file locking clashes. Test what works with your mileage.

"""
import os
import sys
from django.conf import settings


# Process Pool setup

# convenient flag to turn off process pool without changing settings
PROCPOOL_ENABLED = True
# relay process stdout to log (debug mode, very spammy)
PROCPOOL_DEBUG = False
# max/min size of the process pool. Will expand up to max limit on demand.
PROCPOOL_MIN_NPROC = 5
PROCPOOL_MAX_NPROC = 20
# maximum time (seconds) a process may idle before being pruned from
# pool (if pool bigger than minsize)
PROCPOOL_IDLETIME = 20
# after sending a command, this is the maximum time in seconds the process
# may run without returning. After this time the process will be killed. This
# can be seen as a fallback; the run_async method takes a keyword proc_timeout
# that will override this value on a per-case basis.
PROCPOOL_TIMEOUT = 10
# only change if the port clashes with something else on the system
PROCPOOL_PORT = 5001
# 0.0.0.0 means listening to all interfaces
PROCPOOL_INTERFACE = '127.0.0.1'
# user-id and group-id to run the processes as (for OS:es supporting this).
# If you plan to run unsafe code one could experiment with setting this
# to an unprivileged user.
PROCPOOL_UID = None
PROCPOOL_GID = None
# real path to a directory where all processes will be run. If
# not given, processes will be executed in game/.
PROCPOOL_DIRECTORY = None


# don't need to change normally
SERVICE_NAME = "PythonProcPool"

# plugin hook

def start_plugin_services(server):
    """
    This will be called by the Evennia Server when starting up.

    server - the main Evennia server application
    """
    if not PROCPOOL_ENABLED:
        return

    # terminal output
    print '  amp (Process Pool): %s' % PROCPOOL_PORT

    from contrib.procpools.ampoule import main as ampoule_main
    from contrib.procpools.ampoule import service as ampoule_service
    from contrib.procpools.ampoule import pool as ampoule_pool
    from contrib.procpools.ampoule.main import BOOTSTRAP as _BOOTSTRAP
    from contrib.procpools.python_procpool import PythonProcPoolChild

    # for some reason absolute paths don't work here, only relative ones.
    apackages = ("twisted",
                 os.path.join(os.pardir, "contrib", "procpools", "ampoule"),
                 os.path.join(os.pardir, "ev"),
                 "settings")
    aenv = {"DJANGO_SETTINGS_MODULE":"settings",
            "DATABASE_NAME":settings.DATABASES.get("default", {}).get("NAME") or settings.DATABASE_NAME}
    if PROCPOOL_DEBUG:
        _BOOTSTRAP = _BOOTSTRAP % "log.startLogging(sys.stderr)"
    else:
        _BOOTSTRAP = _BOOTSTRAP % ""
    procpool_starter = ampoule_main.ProcessStarter(packages=apackages,
                                                   env=aenv,
                                                   path=PROCPOOL_DIRECTORY,
                                                   uid=PROCPOOL_UID,
                                                   gid=PROCPOOL_GID,
                                                   bootstrap=_BOOTSTRAP,
                                                   childReactor=sys.platform == 'linux2' and "epoll" or "default")
    procpool = ampoule_pool.ProcessPool(name=SERVICE_NAME,
                                        min=PROCPOOL_MIN_NPROC,
                                        max=PROCPOOL_MAX_NPROC,
                                        recycleAfter=500,
                                        timeout=PROCPOOL_TIMEOUT,
                                        maxIdle=PROCPOOL_IDLETIME,
                                        ampChild=PythonProcPoolChild,
                                        starter=procpool_starter)
    procpool_service = ampoule_service.AMPouleService(procpool,
                                                      PythonProcPoolChild,
                                                      PROCPOOL_PORT,
                                                      PROCPOOL_INTERFACE)
    procpool_service.setName(SERVICE_NAME)
    # add the new services to the server
    server.services.addService(procpool_service)



