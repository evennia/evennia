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


import os
import time
from datetime import datetime
from traceback import format_exc

from twisted import logger as twisted_logger
from twisted.internet.threads import deferToThread
from twisted.python import logfile
from twisted.python import util as twisted_util

log = twisted_logger.Logger()

_LOGDIR = None
_LOG_ROTATE_SIZE = None
_TIMEZONE = None
_CHANNEL_LOG_NUM_TAIL_LINES = None

_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _log(msg, logfunc, prefix="", **kwargs):
    try:
        msg = str(msg)
    except Exception as err:
        msg = str(e)
    if kwargs:
        logfunc(msg, **kwargs)
    else:
        try:
            for line in msg.splitlines():
                logfunc("{line}", prefix=prefix, line=line)
        except Exception as err:
            log.error("Log failure: {err}", err=err)


# log call functions (each has legacy aliases)


def log_info(msg, **kwargs):
    """
    Logs any generic debugging/informative info that should appear in the log.

    Args:
        msg: (string) The message to be logged.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    _log(msg, log.info, **kwargs)


info = log_info
log_infomsg = log_info
log_msg = log_info


def log_warn(msg, **kwargs):
    """
    Logs warnings that aren't critical but should be noted.

    Args:
        msg (str): The message to be logged.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    _log(msg, log.warn, **kwargs)


warn = log_warn
warning = log_warn
log_warnmsg = log_warn


def log_err(msg, **kwargs):
    """
    Logs an error message to the server log.

    Args:
        msg (str): The message to be logged.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    _log(msg, log.error, **kwargs)


error = log_err
err = log_err
log_errmsg = log_err


def log_trace(msg=None, **kwargs):
    """
    Log a traceback to the log. This should be called from within an
    exception.

    Args:
        msg (str, optional): Adds an extra line with added info
            at the end of the traceback in the log.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    tracestring = format_exc()
    if tracestring:
        _log(tracestring, log.error, prefix="!!", **kwargs)
        if msg:
            _log(msg, log.error, prefix="!!", **kwargs)


log_tracemsg = log_trace
exception = log_trace
critical = log_trace
trace = log_trace


def log_dep(msg, **kwargs):
    """
    Prints a deprecation message.

    Args:
        msg (str): The deprecation message to log.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    _log(msg, log.warn, prefix="DP", **kwargs)


dep = log_dep
deprecated = log_dep
log_depmsg = log_dep


def log_sec(msg, **kwargs):
    """
    Prints a security-related message.

    Args:
        msg (str): The security message to log.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.

    """
    _log(msg, log.info, prefix="SS", **kwargs)


sec = log_sec
security = log_sec
log_secmsg = log_sec


def log_server(msg, **kwargs):
    """
    This is for the Portal to log captured Server stdout messages (it's
    usually only used during startup, before Server log is open)

    Args:
        msg (str): The message to be logged.
        **kwargs: If given, The `msg` is parsed as a format string with `{..}`
            formatting markers that should match the keywords.
    """
    _log(msg, log.info, prefix="Server", **kwargs)


class GetLogObserver:
    """
    Sets up how the system logs are formatted.

    """

    component_prefix = ""
    event_levels = {
        twisted_logger.LogLevel.debug: "??",
        twisted_logger.LogLevel.info: "..",
        twisted_logger.LogLevel.warn: "WW",
        twisted_logger.LogLevel.error: "EE",
        twisted_logger.LogLevel.critical: "!!",
    }

    def format_log_event(self, event):
        """
        By assigning log_system here, we skip the spammy display of namespace/level
        in the default log output.

        [component_prefix] [date] [system/lvl] [msg]

        """
        # setting log_system fills the [..] block after the time stamp
        prefix = event.get("prefix", "")
        if prefix:
            event["log_system"] = prefix
        else:
            lvl = event.get("log_level", twisted_logger.LogLevel.info)
            event["log_system"] = self.event_levels.get(lvl, "-")
        event["log_format"] = str(event.get("log_format", ""))
        component_prefix = self.component_prefix or ""
        log_msg = twisted_logger.formatEventAsClassicLogText(
            event, formatTime=lambda e: twisted_logger.formatTime(e, _TIME_FORMAT)
        )
        return f"{component_prefix}{log_msg}"

    def __call__(self, outfile):
        return twisted_logger.FileLogObserver(outfile, self.format_log_event)


# Called by server/portal on startup


class GetPortalLogObserver(GetLogObserver):
    component_prefix = "|Portal| "


class GetServerLogObserver(GetLogObserver):
    component_prefix = ""


# logging overrides


def timeformat(when=None):
    """
    This helper function will format the current time in the same
    way as the twisted logger does, including time zone info. Only
    difference from official logger is that we only use two digits
    for the year and don't show timezone for GMT times.

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

    if tz_offset == 0:
        tz = ""
    else:
        tz_hour = abs(int(tz_offset // 3600))
        tz_mins = abs(int(tz_offset // 60 % 60))
        tz_sign = "-" if tz_offset >= 0 else "+"
        tz = "%s%02d%s" % (tz_sign, tz_hour, (":%02d" % tz_mins if tz_mins else ""))

    return "%d-%02d-%02d %02d:%02d:%02d%s" % (
        when.year - 2000,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second,
        tz,
    )


class WeeklyLogFile(logfile.DailyLogFile):
    """
    Log file that rotates once per week by default. Overrides key methods to change format.

    """

    def __init__(self, name, directory, defaultMode=None, day_rotation=7, max_size=1000000):
        """
        Args:
            name (str): Name of log file.
            directory (str): Directory holding the file.
            defaultMode (str): Permissions used to create file. Defaults to
                current permissions of this file if it exists.
            day_rotation (int): How often to rotate the file.
            max_size (int): Max size of log file before rotation (regardless of
                time). Defaults to 1M.

        """
        self.day_rotation = day_rotation
        self.max_size = max_size
        self.size = 0
        logfile.DailyLogFile.__init__(self, name, directory, defaultMode=defaultMode)

    def _openFile(self):
        logfile.DailyLogFile._openFile(self)
        self.size = self._file.tell()

    def shouldRotate(self):
        """Rotate when the date has changed since last write"""
        # all dates here are tuples (year, month, day)
        now = self.toDate()
        then = self.lastDate
        return (
            now[0] > then[0]
            or now[1] > then[1]
            or now[2] > (then[2] + self.day_rotation)
            or self.size >= self.max_size
        )

    def suffix(self, tupledate):
        """Return the suffix given a (year, month, day) tuple or unixtime.
        Format changed to have 03 for march instead of 3 etc (retaining unix
        file order)

        If we get duplicate suffixes in location (due to hitting size limit),
        we append __1, __2 etc.

        Examples:
            server.log.2020_01_29
            server.log.2020_01_29__1
            server.log.2020_01_29__2

        """
        suffix = ""
        copy_suffix = 0
        while True:
            try:
                suffix = "_".join(["{:02d}".format(part) for part in tupledate])
            except Exception:
                # try taking a float unixtime
                suffix = "_".join(["{:02d}".format(part) for part in self.toDate(tupledate)])

            suffix += f"__{copy_suffix}" if copy_suffix else ""

            if os.path.exists(f"{self.path}.{suffix}"):
                # Append a higher copy_suffix to try to break the tie (starting from 2)
                copy_suffix += 1
            else:
                break
        return suffix

    def rotate(self):
        try:
            super().rotate()
        except Exception:
            log_trace(f"Could not rotate the log file {self.name}.")

    def write(self, data):
        """
        Write data to log file

        """
        logfile.BaseLogFile.write(self, data)
        self.lastDate = max(self.lastDate, self.toDate())
        self.size += len(data)


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
    num_lines_to_append = max(1, _CHANNEL_LOG_NUM_TAIL_LINES)

    def rotate(self, num_lines_to_append=None):
        """
        Rotates our log file and appends some number of lines from
        the previous log to the start of the new one.

        """
        append_tail = (
            num_lines_to_append if num_lines_to_append is not None else self.num_lines_to_append
        )
        if not append_tail:
            logfile.LogFile.rotate(self)
            return
        lines = tail_log_file(self.path, 0, self.num_lines_to_append)
        super().rotate()
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
        lines = []
        for line in self._file.readlines(*args, **kwargs):
            try:
                lines.append(line.decode("utf-8"))
            except UnicodeDecodeError:
                try:
                    lines.append(str(line))
                except Exception:
                    lines.append("")
        return lines


_LOG_FILE_HANDLES = {}  # holds open log handles
_LOG_FILE_HANDLE_COUNTS = {}
_LOG_FILE_HANDLE_RESET = 500


def _open_log_file(filename):
    """
    Helper to open the log file (always in the log dir) and cache its
    handle.  Will create a new file in the log dir if one didn't
    exist.

    To avoid keeping the filehandle open indefinitely we reset it every
    _LOG_FILE_HANDLE_RESET accesses. This may help resolve issues for very
    long uptimes and heavy log use.

    """
    # we delay import of settings to keep logger module as free
    # from django as possible.
    global _LOG_FILE_HANDLES, _LOG_FILE_HANDLE_COUNTS, _LOGDIR, _LOG_ROTATE_SIZE
    if not _LOGDIR:
        from django.conf import settings

        _LOGDIR = settings.LOG_DIR
        _LOG_ROTATE_SIZE = max(1000, settings.CHANNEL_LOG_ROTATE_SIZE)

    filename = os.path.join(_LOGDIR, filename)
    if filename in _LOG_FILE_HANDLES:
        _LOG_FILE_HANDLE_COUNTS[filename] += 1
        if _LOG_FILE_HANDLE_COUNTS[filename] > _LOG_FILE_HANDLE_RESET:
            # close/refresh handle
            _LOG_FILE_HANDLES[filename].close()
            del _LOG_FILE_HANDLES[filename]
        else:
            # return cached handle
            return _LOG_FILE_HANDLES[filename]
    try:
        filehandle = EvenniaLogFile.fromFullPath(filename, rotateLength=_LOG_ROTATE_SIZE)
        # filehandle = open(filename, "a+")  # append mode + reading
        _LOG_FILE_HANDLES[filename] = filehandle
        _LOG_FILE_HANDLE_COUNTS[filename] = 0
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


def log_file_exists(filename="game.log"):
    """
    Determine if a log-file already exists.

    Args:
        filename (str): The filename (within the log-dir).

    Returns:
        bool: If the log file exists or not.

    """
    global _LOGDIR
    if not _LOGDIR:
        from django.conf import settings

        _LOGDIR = settings.LOG_DIR

    filename = os.path.join(_LOGDIR, filename)
    return os.path.exists(filename)


def rotate_log_file(filename="game.log", num_lines_to_append=None):
    """
    Force-rotate a log-file, without

    Args:
        filename (str): The log file, located in settings.LOG_DIR.
        num_lines_to_append (int, optional): Include N number of
            lines from previous file in new one. If `None`, use default.
            Set to 0 to include no lines.

    """
    if log_file_exists(filename):
        file_handle = _open_log_file(filename)
        if file_handle:
            file_handle.rotate(num_lines_to_append=num_lines_to_append)


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
        lines_found = lines_found[-nlines - offset : -offset if offset else None]
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
            return deferToThread(seek_file, filehandle, offset, nlines, callback).addErrback(
                errback
            )
        else:
            return seek_file(filehandle, offset, nlines, callback)
    else:
        return None
