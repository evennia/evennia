"""
Logging facilities

This file should have an absolute minimum in imports. If you'd like to layer
additional functionality on top of some of the methods below, wrap them in
a higher layer module.
"""
from traceback import format_exc
from twisted.python import log

def log_trace(errmsg=None):
    """
    Log a traceback to the log. This should be called
    from within an exception. errmsg is optional and
    adds an extra line with added info.
    """
    tracestring = format_exc()
    try:
        if tracestring:
            for line in tracestring.splitlines():
                log.msg('[::] %s' % line)
        if errmsg:
            try:
                errmsg = str(errmsg)
            except Exception, e:
                errmsg = str(e)
            for line in errmsg.splitlines():
                log.msg('[EE] %s' % line)
    except Exception:
        log.msg('[EE] %s' % errmsg )

def log_errmsg(errmsg):
    """
    Prints/logs an error message to the server log.

    errormsg: (string) The message to be logged.
    """
    try:
        errmsg = str(errmsg)
    except Exception, e:
        errmsg = str(e)
    for line in errmsg.splitlines():
        log.msg('[EE] %s' % line)
    #log.err('ERROR: %s' % (errormsg,))

def log_warnmsg(warnmsg):
    """
    Prints/logs any warnings that aren't critical but should be noted.

    warnmsg: (string) The message to be logged.
    """
    try:
        warnmsg = str(warnmsg)
    except Exception, e:
        warnmsg = str(e)
    for line in warnmsg.splitlines():
        log.msg('[WW] %s' % line)
    #log.msg('WARNING: %s' % (warnmsg,))

def log_infomsg(infomsg):
    """
    Prints any generic debugging/informative info that should appear in the log.

    infomsg: (string) The message to be logged.
    """
    try:
        infomsg = str(infomsg)
    except Exception, e:
        infomsg = str(e)
    for line in infomsg.splitlines():
        log.msg('[..] %s' % line)

def log_depmsg(depmsg):
    """
    Prints a deprecation message
    """
    try:
        depmsg = str(depmsg)
    except Exception, e:
        depmsg = str(e)
    for line in depmsg.splitlines():
        log.msg('[DP] %s' % line)
