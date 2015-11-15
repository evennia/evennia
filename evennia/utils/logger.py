"""
Logging facilities

Deprecated, use evennia.core.logger instead.
"""

import warnings
from evennia.core import logger

def timeformat(when=None):
    warnings.warn("use evennia.core.timeformat() instead.", DeprecationWarning)
    logger.timeformat(when=when)

def log_trace(errmsg=None):
    warnings.warn("use evennia.core.log_trace() instead.", DeprecationWarning)
    logger.log_trace(errmsg=errmsg)
log_tracemsg = log_trace


def log_err(errmsg):
    warnings.warn("use evennia.core.log_err() instead.", DeprecationWarning)
    logger.log_err(errmsg=errmsg)
log_errmsg = log_err


def log_warn(warnmsg):
    warnings.warn("use evennia.core.log_warn() instead.", DeprecationWarning)
    logger.log_warn(warnmsg=warnmsg)
log_warnmsg = log_warn


def log_info(infomsg):
    warnings.warn("use evennia.core.log_info() instead.", DeprecationWarning)
    logger.log_info(infomsg=infomsg)
log_infomsg = log_info


def log_dep(depmsg):
    warnings.warn("use evennia.core.log_dep() instead.", DeprecationWarning)
    logger.log_dep(depmsg=depmsg)
log_depmsg = log_dep

def log_file(msg, filename="game.log"):
    warnings.warn("use evennia.core.log_file() instead.", DeprecationWarning)
    logger.log_file(msg=msg, filename=filename)
