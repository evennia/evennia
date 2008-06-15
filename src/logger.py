"""
Logging facilities

This file should have an absolute minimum in imports. If you'd like to layer
additional functionality on top of some of the methods below, wrap them in
a higher layer module.
"""
from twisted.python import log

def log_errmsg(errormsg):
    """
    Prints/logs an error message to the server log.

    errormsg: (string) The message to be logged.
    """
    log.err('ERROR: %s' % (errormsg,))

def log_infomsg(infomsg):
    """
    Prints any generic debugging/informative info that should appear in the log.

    debugmsg: (string) The message to be logged.
    """
    log.msg('%s' % (infomsg,))
