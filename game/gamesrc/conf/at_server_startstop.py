"""
This module contains functions that are imported and called by the
server whenever it changes its running status. At the point these
functions are run, all applicable hooks on individual objects have
already been executed. The main purpose of this is module is to have a
safe place to initialize eventual custom modules that your game needs
to start up or load.

The module should define at least these global functions: 

at_server_start() 
at_server_stop() 

The module used is defined by settings.AT_SERVER_STARTSTOP_MODULE.

"""

def at_server_start():
    """
    This is called every time the server starts up (also after a
    reload or reset).
    """
    pass

def at_server_stop():
    """
    This is called just before a server is shut down, reloaded or
    reset.
    """
    pass
