"""

At_server_startstop module template

Copy this module one level up, to gamesrc/conf/, name it what you
will and use it as a template for your modifications.

Then edit settings.AT_SERVER_STARTSTOP_MODULE to point to your new
module.

This module contains functions that are imported and called by the
server whenever it changes its running status. At the point these
functions are run, all applicable hooks on individual objects have
already been executed. The main purpose of this is module is to have a
safe place to initialize eventual custom modules that your game needs
to start up or load.

The module should define at least these global functions:

at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    pass

def at_server_stop():
    """
    This is called just before a server is shut down, regardless
    of it is fore a reload, reset or shutdown.
    """
    pass

def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass

def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass

def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass

def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or reset.
    """
    pass
