"""
Logging facilities

These are thin wrappers on top of Twisted's logging facilities; logs
are all directed either to stdout (if Evennia is running in
interactive mode) or to $GAME_DIR/server/logs.

The log_file() function uses its own threading system to log to
arbitrary files in $GAME_DIR/server/logs.

Note: All logging functions have two aliases, log_type() and
log_typemsg(). This is for historical, back-compatible reasons.

"""

from __future__ import division

import os
import time
from datetime import datetime
from traceback import format_exc
from twisted.python import log, logfile
from twisted.internet.threads import deferToThread


_LOGDIR = None
_LOG_ROTATE_SIZE = None
_TIMEZONE = None
_CHANNEL_LOG_NUM_TAIL_LINES = None


def timeformat(when=None):
    """
    This helper function will format the current time in the same
    way as twisted's logger does, including time zone info.

    Args:
        when (int, optional): This is a time in POSIX seconds on the form
            given by time.time(). If not given, this function will
            use the current time.

    Returns:
        timestring (str): A formatted string of the given time.
    """
    when = when if when else time.time()

    # time zone offset: UTC - the actual offset
    tz_offset = datetime.utcfromtimestamp(when) - datetime.fromtimestamp(when)
    tz_offset = tz_offset.days * 86400 + tz_offset.seconds
    # correct given time to utc
    when = datetime.utcfromtimestamp(when - tz_offset)
    tz_hour = abs(int(tz_offset // 3600))
    tz_mins = abs(int(tz_offset // 60 % 60))
    tz_sign = "-" if tz_offset >= 0 else "+"

    return '%d-%02d-%02d %02d:%02d:%02d%s%02d%02d' % (
        when.year, when.month, when.day,
        when.hour, when.minute, when.second,
        tz_sign, tz_hour, tz_mins)


def log_trace(errmsg=None):
    """
    Log a traceback to the log. This should be called from within an
    exception.

    Args:
        errmsg (str, optional): Adds an extra line with added info
            at the end of the traceback in the log.

    """
    tracestring = format_exc()
    try:
        if tracestring:
            for line in tracestring.splitlines():
                log.msg('[::] %s' % line)
        if errmsg:
            try:
                errmsg = str(errmsg)
            except Exception as e:
                errmsg = str(e)
            for line in errmsg.splitlines():
                log.msg('[EE] %s' % line)
    except Exception:
        log.msg('[EE] %s' % errmsg)
log_tracemsg = log_trace


def log_err(errmsg):
    """
    Prints/logs an error message to the server log.

    Args:
        errmsg (str): The message to be logged.

    """
    try:
        errmsg = str(errmsg)
    except Exception as e:
        errmsg = str(e)
    for line in errmsg.splitlines():
        log.msg('[EE] %s' % line)
    # log.err('ERROR: %s' % (errmsg,))
log_errmsg = log_err


def log_warn(warnmsg):
    """
    Prints/logs any warnings that aren't critical but should be noted.

    Args:
        warnmsg (str): The message to be logged.

    """
    try:
        warnmsg = str(warnmsg)
    except Exception as e:
        warnmsg = str(e)
    for line in warnmsg.splitlines():
        log.msg('[WW] %s' % line)
    # log.msg('WARNING: %s' % (warnmsg,))
log_warnmsg = log_warn


def log_info(infomsg):
    """
    Prints any generic debugging/informative info that should appear in the log.

    infomsg: (string) The message to be logged.
    """
    try:
        infomsg = str(infomsg)
    except Exception as e:
        infomsg = str(e)
    for line in infomsg.splitlines():
        log.msg('[..] %s' % line)
log_infomsg = log_info


def log_dep(depmsg):
    """
    Prints a deprecation message.

    Args:
        depmsg (str): The deprecation message to log.
    """
    try:
        depmsg = str(depmsg)
    except Exception as e:
        depmsg = str(e)
    for line in depmsg.splitlines():
        log.msg('[DP] %s' % line)
log_depmsg = log_dep


# Arbitrary file logger

class EvenniaLogFile(logfile.LogFile):
    """
    A rotating logfile based off Twisted's LogFile. It overrides
    the LogFile's rotate method in order to append some of the last
    lines of the previous log to the start of the new log, in order
    to preserve a continuous chat history for channel log files.
    """
    # we delay import of settings to keep logger module as free
    # from django as possible.
    global _CHANNEL_LOG_NUM_TAIL_LINES
    if _CHANNEL_LOG_NUM_TAIL_LINES is None:
        from django.conf import settings
        _CHANNEL_LOG_NUM_TAIL_LINES = settings.CHANNEL_LOG_NUM_TAIL_LINES
    num_lines_to_append = _CHANNEL_LOG_NUM_TAIL_LINES

    def rotate(self):
        """
        Rotates our log file and appends some number of lines from
        the previous log to the start of the new one.
        """
        append_tail = self.num_lines_to_append > 0
        if not append_tail:
            logfile.LogFile.rotate(self)
            return
        lines = tail_log_file(self.path, 0, self.num_lines_to_append)
        logfile.LogFile.rotate(self)
        for line in lines:
            self.write(line)

    def seek(self, *args, **kwargs):
        """
        Convenience method for accessing our _file attribute's seek method,
        which is used in tail_log_function.
        Args:
            *args: Same args as file.seek
            **kwargs: Same kwargs as file.seek
        """
        return self._file.seek(*args, **kwargs)

    def readlines(self, *args, **kwargs):
        """
        Convenience method for accessing our _file attribute's readlines method,
        which is used in tail_log_function.
        Args:
            *args: same args as file.readlines
            **kwargs: same kwargs as file.readlines

        Returns:
            lines (list): lines from our _file attribute.
        """
        return self._file.readlines(*args, **kwargs)

_LOG_FILE_HANDLES = {}  # holds open log handles


def _open_log_file(filename):
    """
    Helper to open the log file (always in the log dir) and cache its
    handle.  Will create a new file in the log dir if one didn't
    exist.
    """
    # we delay import of settings to keep logger module as free
    # from django as possible.
    global _LOG_FILE_HANDLES, _LOGDIR, _LOG_ROTATE_SIZE
    if not _LOGDIR:
        from django.conf import settings
        _LOGDIR = settings.LOG_DIR
        _LOG_ROTATE_SIZE = settings.CHANNEL_LOG_ROTATE_SIZE

    filename = os.path.join(_LOGDIR, filename)
    if filename in _LOG_FILE_HANDLES:
        # cache the handle
        return _LOG_FILE_HANDLES[filename]
    else:
        try:
            filehandle = EvenniaLogFile.fromFullPath(filename, rotateLength=_LOG_ROTATE_SIZE)
            # filehandle = open(filename, "a+")  # append mode + reading
            _LOG_FILE_HANDLES[filename] = filehandle
            return filehandle
        except IOError:
            log_trace()
    return None


def log_file(msg, filename="game.log"):
    """
    Arbitrary file logger using threads.

    Args:
        msg (str): String to append to logfile.
        filename (str, optional): Defaults to 'game.log'. All logs
            will appear in the logs directory and log entries will start
            on new lines following datetime info.

    """
    def callback(filehandle, msg):
        """Writing to file and flushing result"""
        msg = "\n%s [-] %s" % (timeformat(), msg.strip())
        filehandle.write(msg)
        # since we don't close the handle, we need to flush
        # manually or log file won't be written to until the
        # write buffer is full.
        filehandle.flush()

    def errback(failure):
        """Catching errors to normal log"""
        log_trace()

    # save to server/logs/ directory
    filehandle = _open_log_file(filename)
    if filehandle:
        deferToThread(callback, filehandle, msg).addErrback(errback)


def tail_log_file(filename, offset, nlines, callback=None):
    """
    Return the tail of the log file.

    Args:
        filename (str): The name of the log file, presumed to be in
            the Evennia log dir.
        offset (int): The line offset *from the end of the file* to start
            reading from. 0 means to start at the latest entry.
        nlines (int): How many lines to return, counting backwards
            from the offset. If file is shorter, will get all lines.
        callback (callable, optional): A function to manage the result of the
            asynchronous file access. This will get a list of lines. If unset,
            the tail will happen synchronously.

    Returns:
        lines (deferred or list): This will be a deferred if `callable` is given,
            otherwise it will be a list with The nline entries from the end of the file, or
            all if the file is shorter than nlines.

    """
    def seek_file(filehandle, offset, nlines, callback):
        """step backwards in chunks and stop only when we have enough lines"""
        lines_found = []
        buffer_size = 4098
        block_count = -1
        while len(lines_found) < (offset + nlines):
            try:
                # scan backwards in file, starting from the end
                filehandle.seek(block_count * buffer_size, os.SEEK_END)
            except IOError:
                # file too small for this seek, take what we've got
                filehandle.seek(0)
                lines_found = filehandle.readlines()
                break
            lines_found = filehandle.readlines()
            block_count -= 1
        # return the right number of lines
        lines_found = lines_found[-nlines-offset:-offset if offset else None]
        if callback:
            callback(lines_found)
            return None
        else:
            return lines_found

    def errback(failure):
        """Catching errors to normal log"""
        log_trace()

    filehandle = _open_log_file(filename)
    if filehandle:
        if callback:
            return deferToThread(seek_file, filehandle, offset, nlines, callback).addErrback(errback)
        else:
            return seek_file(filehandle, offset, nlines, callback)
    else:
        return None
