"""
General helper functions that don't fit neatly under any given category.

They provide some useful string and conversion methods that might
be of use when designing your own game.

"""
from __future__ import division, print_function
from builtins import object, range
from future.utils import viewkeys, raise_

import os
import sys
import imp
import types
import math
import re
import textwrap
import random
from importlib import import_module
from inspect import ismodule, trace
from collections import defaultdict, OrderedDict
from twisted.internet import threads, defer, reactor
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _
from evennia.utils import logger

_MULTIMATCH_SEPARATOR = settings.SEARCH_MULTIMATCH_SEPARATOR

try:
    import cPickle as pickle
except ImportError:
    import pickle

ENCODINGS = settings.ENCODINGS
_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH


def is_iter(iterable):
    """
    Checks if an object behaves iterably.

    Args:
        iterable (any): Entity to check for iterability.

    Returns:
        is_iterable (bool): If `iterable` is iterable or not.

    Notes:
        Strings are *not* accepted as iterable (although they are
        actually iterable), since string iterations are usually not
        what we want to do with a string.

    """
    return hasattr(iterable, '__iter__')

def make_iter(obj):
    """
    Makes sure that the object is always iterable.

    Args:
        obj (any): Object to make iterable.

    Returns:
        iterable (list or iterable): The same object
            passed-through or made iterable.

    """
    return not hasattr(obj, '__iter__') and [obj] or obj


def wrap(text, width=_DEFAULT_WIDTH, indent=0):
    """
    Safely wrap text to a certain number of characters.

    Args:
        text (str): The text to wrap.
        width (int, optional): The number of characters to wrap to.
        indent (int): How much to indent new lines (the first line
            will not be indented)

    Returns:
        text (str): Properly wrapped text.

    """
    if not text:
        return ""
    text = to_unicode(text)
    indent = " " * indent
    return to_str(textwrap.fill(text, width, subsequent_indent=indent))
# alias - fill
fill = wrap


def pad(text, width=_DEFAULT_WIDTH, align="c", fillchar=" "):
    """
    Pads to a given width.

    Args:
        text (str): Text to pad.
        width (int, optional): The width to pad to, in characters.
        align (str, optional): This is one of 'c', 'l' or 'r' (center,
            left or right).
        fillchar (str, optional): The character to fill with.

    Returns:
        text (str): The padded text.

    """
    align = align if align in ('c', 'l', 'r') else 'c'
    fillchar = fillchar[0] if fillchar else " "
    if align == 'l':
        return text.ljust(width, fillchar)
    elif align == 'r':
        return text.rjust(width, fillchar)
    else:
        return text.center(width, fillchar)


def crop(text, width=_DEFAULT_WIDTH, suffix="[...]"):
    """
    Crop text to a certain width, throwing away text from too-long
    lines.

    Args:
        text (str): Text to crop.
        width (int, optional): Width of line to crop, in characters.
        suffix (str, optional): This is appended to the end of cropped
            lines to show that the line actually continues. Cropping
            will be done so that the suffix will also fit within the
            given width. If width is too small to fit both crop and
            suffix, the suffix will be dropped.

    Returns:
        text (str): The cropped text.

    """

    utext = to_unicode(text)
    ltext = len(utext)
    if ltext <= width:
        return text
    else:
        lsuffix = len(suffix)
        utext = utext[:width] if lsuffix >= width else "%s%s" % (utext[:width - lsuffix], suffix)
        return to_str(utext)


def dedent(text):
    """
    Safely clean all whitespace at the left of a paragraph.

    Args:
        text (str): The text to dedent.

    Returns:
        text (str): Dedented string.

    Notes:
        This is useful for preserving triple-quoted string indentation
        while still shifting it all to be next to the left edge of the
        display.

    """
    if not text:
        return ""
    return textwrap.dedent(text)


def list_to_string(inlist, endsep="and", addquote=False):
    """
    This pretty-formats a list as string output, adding an optional
    alternative separator to the second to last entry.  If `addquote`
    is `True`, the outgoing strings will be surrounded by quotes.

    Args:
        inlist (list): The list to print.
        endsep (str, optional): If set, the last item separator will
            be replaced with this value.
        addquote (bool, optional): This will surround all outgoing
            values with double quotes.

    Returns:
        liststr (str): The list represented as a string.

    Examples:

        ```python
         # no endsep:
            [1,2,3] -> '1, 2, 3'
         # with endsep=='and':
            [1,2,3] -> '1, 2 and 3'
         # with addquote and endsep
            [1,2,3] -> '"1", "2" and "3"'
        ```

    """
    if not endsep:
        endsep = ","
    else:
        endsep = " " + endsep
    if not inlist:
        return ""
    if addquote:
        if len(inlist) == 1:
            return "\"%s\"" % inlist[0]
        return ", ".join("\"%s\"" % v for v in inlist[:-1]) + "%s %s" % (endsep, "\"%s\"" % inlist[-1])
    else:
        if len(inlist) == 1:
            return str(inlist[0])
        return ", ".join(str(v) for v in inlist[:-1]) + "%s %s" % (endsep, inlist[-1])


def wildcard_to_regexp(instring):
    """
    Converts a player-supplied string that may have wildcards in it to
    regular expressions. This is useful for name matching.

    Args:
        instring (string): A string that may potentially contain
            wildcards (`*` or `?`).

    Returns:
        regex (str): A string where wildcards were replaced with
            regular expressions.

    """
    regexp_string = ""

    # If the string starts with an asterisk, we can't impose the beginning of
    # string (^) limiter.
    if instring[0] != "*":
        regexp_string += "^"

    # Replace any occurances of * or ? with the appropriate groups.
    regexp_string += instring.replace("*", "(.*)").replace("?", "(.{1})")

    # If there's an asterisk at the end of the string, we can't impose the
    # end of string ($) limiter.
    if instring[-1] != "*":
        regexp_string += "$"

    return regexp_string


def time_format(seconds, style=0):
    """
    Function to return a 'prettified' version of a value in seconds.

    Args:
        seconds (int): Number if seconds to format.
        style (int): One of the following styles:
            0. "1d 08:30"
            1. "1d"
            2. "1 day, 8 hours, 30 minutes"
            3. "1 day, 8 hours, 30 minutes, 10 seconds"
    """
    if seconds < 0:
        seconds = 0
    else:
        # We'll just use integer math, no need for decimal precision.
        seconds = int(seconds)

    days = seconds // 86400
    seconds -= days * 86400
    hours = seconds // 3600
    seconds -= hours * 3600
    minutes = seconds // 60
    seconds -= minutes * 60

    if style is 0:
        """
        Standard colon-style output.
        """
        if days > 0:
            retval = '%id %02i:%02i' % (days, hours, minutes,)
        else:
            retval = '%02i:%02i' % (hours, minutes,)
        return retval

    elif style is 1:
        """
        Simple, abbreviated form that only shows the highest time amount.
        """
        if days > 0:
            return '%id' % (days,)
        elif hours > 0:
            return '%ih' % (hours,)
        elif minutes > 0:
            return '%im' % (minutes,)
        else:
            return '%is' % (seconds,)
    elif style is 2:
        """
        Full-detailed, long-winded format. We ignore seconds.
        """
        days_str = hours_str = ''
        minutes_str = '0 minutes'
        
        if days > 0:
            if days == 1:
                days_str = '%i day, ' % days
            else:
                days_str = '%i days, ' % days
        if days or hours > 0:
            if hours == 1:
                hours_str = '%i hour, ' % hours
            else:
                hours_str = '%i hours, ' % hours
        if hours or minutes > 0:
            if minutes == 1:
                minutes_str = '%i minute ' % minutes
            else:
                minutes_str = '%i minutes ' % minutes
        retval = '%s%s%s' % (days_str, hours_str, minutes_str)
    elif style is 3:
        """
        Full-detailed, long-winded format. Includes seconds.
        """
        days_str = hours_str = minutes_str = seconds_str = ''
        if days > 0:
            if days == 1:
                days_str = '%i day, ' % days
            else:
                days_str = '%i days, ' % days
        if days or hours > 0:
            if hours == 1:
                hours_str = '%i hour, ' % hours
            else:
                hours_str = '%i hours, ' % hours
        if hours or minutes > 0:
            if minutes == 1:
                minutes_str = '%i minute ' % minutes
            else:
                minutes_str = '%i minutes ' % minutes
        if minutes or seconds > 0:
            if seconds == 1:
                seconds_str = '%i second ' % seconds
            else:
                seconds_str = '%i seconds ' % seconds
        retval = '%s%s%s%s' % (days_str, hours_str, minutes_str, seconds_str)

    return retval.strip()


def datetime_format(dtobj):
    """
    Pretty-prints the time since a given time.

    Args:
        dtobj (datetime): An datetime object, e.g. from Django's
            `DateTimeField`.

    Returns:
        deltatime (str): A string describing how long ago `dtobj`
            took place.

    """

    year, month, day = dtobj.year, dtobj.month, dtobj.day
    hour, minute, second = dtobj.hour, dtobj.minute, dtobj.second
    now = timezone.now()

    if year < now.year:
        # another year
        timestring = str(dtobj.date())
    elif dtobj.date() < now.date():
        # another date, same year
        timestring = "%02i-%02i" % (day, month)
    elif hour < now.hour - 1:
        # same day, more than 1 hour ago
        timestring = "%02i:%02i" % (hour, minute)
    else:
        # same day, less than 1 hour ago
        timestring = "%02i:%02i:%02i" % (hour, minute, second)
    return timestring


def host_os_is(osname):
    """
    Check to see if the host OS matches the query.

    Args:
        osname (str): Common names are "posix" (linux/unix/mac) and
            "nt" (windows).

    Args:
        is_os (bool): If the os matches or not.

    """
    return os.name == osname


def get_evennia_version():
    """
    Helper method for getting the current evennia version.

    Returns:
        version (str): The version string.

    """
    import evennia
    return evennia.__version__


def pypath_to_realpath(python_path, file_ending='.py'):
    """
    Converts a dotted Python path to an absolute path under the
    Evennia library directory or under the current game directory.

    Args:
        python_path (str): a dot-python path
        file_ending (str): a file ending, including the period.

    Returns:
        abspaths (list of str): The two absolute paths created by prepending
            `EVENNIA_DIR` and `GAME_DIR` respectively. These are checked for
            existence before being returned, so this may be an empty list.

    """
    pathsplit = python_path.strip().split('.')
    paths = [os.path.join(settings.EVENNIA_DIR, *pathsplit),
             os.path.join(settings.GAME_DIR, *pathsplit)]
    if file_ending:
        # attach file ending to the paths if not already set (a common mistake)
        file_ending = ".%s" % file_ending if not file_ending.startswith(".") else file_ending
        paths = ["%s%s" % (p, file_ending) if not p.endswith(file_ending) else p
                 for p in paths]
    # check so the paths actually exists before returning
    return [p for p in paths if os.path.isfile(p)]


def dbref(dbref, reqhash=True):
    """
    Converts/checks if input is a valid dbref.

    Args:
        dbref (int or str): A datbase ref on the form N or #N.
        reqhash (bool, optional): Require the #N form to accept
            input as a valid dbref.

    Returns:
        dbref (int or None): The integer part of the dbref or `None`
            if input was not a valid dbref.

    """
    if reqhash:
        num = (int(dbref.lstrip('#')) if (isinstance(dbref, basestring) and
                                           dbref.startswith("#") and
                                           dbref.lstrip('#').isdigit())
                                       else None)
        return num if num > 0 else None
    elif isinstance(dbref, basestring):
        dbref = dbref.lstrip('#')
        return int(dbref) if dbref.isdigit() and int(dbref) > 0 else None
    else:
        return dbref if isinstance(dbref, int) else None


def dbid_to_obj(inp, objclass, raise_errors=True):
    """
    Convert a #dbid to a valid object.

    Args:
        inp (str or int): A valid dbref.
        objclass (class): A valid django model to filter against.
        raise_errors (bool, optional): Whether to raise errors
            or return `None` on errors.

    Returns:
        obj (Object or None): An entity loaded from the dbref.

    Raises:
        Exception: If `raise_errors` is `True` and
            `objclass.objects.get(id=dbref)` did not return a valid
            object.

    """
    dbid = dbref(inp)
    if not dbid:
        # we only convert #dbrefs
        return inp
    try:
        if int(inp) < 0:
            return None
    except ValueError:
        return None

    # if we get to this point, inp is an integer dbref; get the matching object
    try:
        return objclass.objects.get(id=inp)
    except Exception:
        if raise_errors:
            raise
        return inp


def to_unicode(obj, encoding='utf-8', force_string=False):
    """
    This decodes a suitable object to the unicode format.

    Args:
        obj (any): Object to decode to unicode.
        encoding (str, optional): The encoding type to use for the
            dedoding.
        force_string (bool, optional): Always convert to string, no
            matter what type `obj` is initially.

    Returns:
        result (unicode or any): Will return a unicode object if input
            was a string. If input was not a string, the original will be
            returned unchanged unless `force_string` is also set.

    Notes:
        One needs to encode the obj back to utf-8 before writing to disk
        or printing. That non-string objects are let through without
        conversion is important for e.g. Attributes.

    """

    if force_string and not isinstance(obj, basestring):
        # some sort of other object. Try to
        # convert it to a string representation.
        if hasattr(obj, '__str__'):
            obj = obj.__str__()
        elif hasattr(obj, '__unicode__'):
            obj = obj.__unicode__()
        else:
            # last resort
            obj = str(obj)

    if isinstance(obj, basestring) and not isinstance(obj, unicode):
        try:
            obj = unicode(obj, encoding)
            return obj
        except UnicodeDecodeError:
            for alt_encoding in ENCODINGS:
                try:
                    obj = unicode(obj, alt_encoding)
                    return obj
                except UnicodeDecodeError:
                    pass
        raise Exception("Error: '%s' contains invalid character(s) not in %s." % (obj, encoding))
    return obj


def to_str(obj, encoding='utf-8', force_string=False):
    """
    This encodes a unicode string back to byte-representation,
    for printing, writing to disk etc.

    Args:
        obj (any): Object to encode to bytecode.
        encoding (str, optional): The encoding type to use for the
            encoding.
        force_string (bool, optional): Always convert to string, no
            matter what type `obj` is initially.

    Notes:
        Non-string objects are let through without modification - this
        is required e.g. for Attributes. Use `force_string` to force
        conversion of objects to strings.

    """

    if force_string and not isinstance(obj, basestring):
        # some sort of other object. Try to
        # convert it to a string representation.
        try:
            obj = str(obj)
        except Exception:
            obj = unicode(obj)

    if isinstance(obj, basestring) and isinstance(obj, unicode):
        try:
            obj = obj.encode(encoding)
            return obj
        except UnicodeEncodeError:
            for alt_encoding in ENCODINGS:
                try:
                    obj = obj.encode(encoding)
                    return obj
                except UnicodeEncodeError:
                    pass
        raise Exception("Error: Unicode could not encode unicode string '%s'(%s) to a bytestring. " % (obj, encoding))
    return obj


def validate_email_address(emailaddress):
    """
    Checks if an email address is syntactically correct.

    Args:
        emailaddress (str): Email address to validate.

    Returns:
        is_valid (bool): If this is a valid email or not.

    Notes.
        (This snippet was adapted from
        http://commandline.org.uk/python/email-syntax-check.)

    """

    emailaddress = r"%s" % emailaddress

    domains = ("aero", "asia", "biz", "cat", "com", "coop",
               "edu", "gov", "info", "int", "jobs", "mil", "mobi", "museum",
               "name", "net", "org", "pro", "tel", "travel")

    # Email address must be more than 7 characters in total.
    if len(emailaddress) < 7:
        return False  # Address too short.

    # Split up email address into parts.
    try:
        localpart, domainname = emailaddress.rsplit('@', 1)
        host, toplevel = domainname.rsplit('.', 1)
    except ValueError:
        return False  # Address does not have enough parts.

    # Check for Country code or Generic Domain.
    if len(toplevel) != 2 and toplevel not in domains:
        return False  # Not a domain name.

    for i in '-_.%+.':
        localpart = localpart.replace(i, "")
    for i in '-_.':
        host = host.replace(i, "")

    if localpart.isalnum() and host.isalnum():
        return True  # Email address is fine.
    else:
        return False  # Email address has funny characters.


def inherits_from(obj, parent):
    """
    Takes an object and tries to determine if it inherits at *any*
    distance from parent.

    Args:
        obj (any): Object to analyze. This may be either an instance
            or a class.
        parent (any): Can be either instance, class or python path to class.

    Returns:
        inherits_from (bool): If `parent` is a parent to `obj` or not.

    Notes:
        What differs this function from e.g.  `isinstance()` is that `obj`
        may be both an instance and a class, and parent may be an
        instance, a class, or the python path to a class (counting from
        the evennia root directory).

    """

    if callable(obj):
        # this is a class
        obj_paths = ["%s.%s" % (mod.__module__, mod.__name__) for mod in obj.mro()]
    else:
        obj_paths = ["%s.%s" % (mod.__module__, mod.__name__) for mod in obj.__class__.mro()]

    if isinstance(parent, basestring):
        # a given string path, for direct matching
        parent_path = parent
    elif callable(parent):
        # this is a class
        parent_path = "%s.%s" % (parent.__module__, parent.__name__)
    else:
        parent_path = "%s.%s" % (parent.__class__.__module__, parent.__class__.__name__)
    return any(1 for obj_path in obj_paths if obj_path == parent_path)


def server_services():
    """
    Lists all services active on the Server. Observe that since
    services are launched in memory, this function will only return
    any results if called from inside the game.

    Returns:
        services (dict): A dict of available services.

    """
    from evennia.server.sessionhandler import SESSIONS
    if hasattr(SESSIONS, "server") and hasattr(SESSIONS.server, "services"):
        server = SESSIONS.server.services.namedServices
    else:
        # This function must be called from inside the evennia process.
        server = {}
    del SESSIONS
    return server


def uses_database(name="sqlite3"):
    """
    Checks if the game is currently using a given database. This is a
    shortcut to having to use the full backend name.

    Args:
        name (str): One of 'sqlite3', 'mysql', 'postgresql_psycopg2'
        or 'oracle'.

    Returns:
        uses (bool): If the given database is used or not.

    """
    try:
        engine = settings.DATABASES["default"]["ENGINE"]
    except KeyError:
        engine = settings.DATABASE_ENGINE
    return engine == "django.db.backends.%s" % name


def delay(delay=2, callback=None, retval=None):
    """
    Delay the return of a value.

    Args:
      delay (int or float): The delay in seconds
      callback (callable, optional): Will be called without arguments
        or with `retval` after delay seconds.
      retval (any, optional): Whis will be returned by this function
        after a delay, or as input to callback.

    Returns:
        deferred (deferred): Will fire fire with callback after
            `delay` seconds. Note that if `delay()` is used in the
            commandhandler callback chain, the callback chain can be
            defined directly in the command body and don't need to be
            specified here.

    """
    callb = callback or defer.Deferred().callback
    if retval is not None:
        return reactor.callLater(delay, callb, retval)
    else:
        return reactor.callLater(delay, callb)


_TYPECLASSMODELS = None
_OBJECTMODELS = None
def clean_object_caches(obj):
    """
    Clean all object caches on the given object.

    Args:
        obj (Object instace): An object whose caches to clean.

    Notes:
        This is only the contents cache these days.

    """
    global _TYPECLASSMODELS, _OBJECTMODELS
    if not _TYPECLASSMODELS:
        from evennia.typeclasses import models as _TYPECLASSMODELS

    if not obj:
        return
    # contents cache
    try:
        _SA(obj, "_contents_cache", None)
    except AttributeError:
        pass

    # on-object property cache
    [_DA(obj, cname) for cname in viewkeys(obj.__dict__)
                     if cname.startswith("_cached_db_")]
    try:
        hashid = _GA(obj, "hashid")
        _TYPECLASSMODELS._ATTRIBUTE_CACHE[hashid] = {}
    except AttributeError:
        pass


_PPOOL = None
_PCMD = None
_PROC_ERR = "A process has ended with a probable error condition: process ended by signal 9."
def run_async(to_execute, *args, **kwargs):
    """
    Runs a function or executes a code snippet asynchronously.

    Args:
        to_execute (callable): If this is a callable, it will be
            executed with *args and non-reserved *kwargs as arguments.
            The callable will be executed using ProcPool, or in a thread
            if ProcPool is not available.

    Kwargs:
        at_return (callable): Should point to a callable with one
            argument.  It will be called with the return value from
            to_execute.
        at_return_kwargs (dict): This dictionary will be used as
            keyword arguments to the at_return callback.
        at_err (callable): This will be called with a Failure instance
            if there is an error in to_execute.
        at_err_kwargs (dict): This dictionary will be used as keyword
            arguments to the at_err errback.

    Notes:
        All other `*args` and `**kwargs` will be passed on to
        `to_execute`. Run_async will relay executed code to a thread
        or procpool.

        Use this function with restrain and only for features/commands
        that you know has no influence on the cause-and-effect order of your
        game (commands given after the async function might be executed before
        it has finished). Accessing the same property from different threads
        can lead to unpredicted behaviour if you are not careful (this is called a
        "race condition").

        Also note that some databases, notably sqlite3, don't support access from
        multiple threads simultaneously, so if you do heavy database access from
        your `to_execute` under sqlite3 you will probably run very slow or even get
        tracebacks.

    """

    # handle special reserved input kwargs
    callback = kwargs.pop("at_return", None)
    errback = kwargs.pop("at_err", None)
    callback_kwargs = kwargs.pop("at_return_kwargs", {})
    errback_kwargs = kwargs.pop("at_err_kwargs", {})

    if callable(to_execute):
        # no process pool available, fall back to old deferToThread mechanism.
        deferred = threads.deferToThread(to_execute, *args, **kwargs)
    else:
        # no appropriate input for this server setup
        raise RuntimeError("'%s' could not be handled by run_async" % to_execute)

    # attach callbacks
    if callback:
        deferred.addCallback(callback, **callback_kwargs)
    deferred.addErrback(errback, **errback_kwargs)


def check_evennia_dependencies():
    """
    Checks the versions of Evennia's dependencies including making
    some checks for runtime libraries.

    Returns:
        result (bool): `False` if a show-stopping version mismatch is
            found.

    """

    # check main dependencies
    from evennia.server.evennia_launcher import check_main_evennia_dependencies
    not_error = check_main_evennia_dependencies()

    errstring = ""
    # South is no longer used ...
    if 'south' in settings.INSTALLED_APPS:
        errstring += "\n ERROR: 'south' found in settings.INSTALLED_APPS. " \
                     "\n   South is no longer used. If this was added manually, remove it."
        not_error = False
    # IRC support
    if settings.IRC_ENABLED:
        try:
            import twisted.words
            twisted.words  # set to avoid debug info about not-used import
        except ImportError:
            errstring += "\n ERROR: IRC is enabled, but twisted.words is not installed. Please install it." \
                         "\n   Linux Debian/Ubuntu users should install package 'python-twisted-words', others" \
                         "\n   can get it from http://twistedmatrix.com/trac/wiki/TwistedWords."
            not_error = False
    errstring = errstring.strip()
    if errstring:
        mlen = max(len(line) for line in errstring.split("\n"))
        logger.log_err("%s\n%s\n%s" % ("-"*mlen, errstring, '-'*mlen))
    return not_error


def has_parent(basepath, obj):
    """
    Checks if `basepath` is somewhere in `obj`s parent tree.

    Args:
        basepath (str): Python dotpath to compare against obj path.
        obj (any): Object whose path is to be checked.

    Returns:
        has_parent (bool): If the check was successful or not.

    """
    try:
        return any(cls for cls in obj.__class__.mro()
                   if basepath == "%s.%s" % (cls.__module__, cls.__name__))
    except (TypeError, AttributeError):
        # this can occur if we tried to store a class object, not an
        # instance. Not sure if one should defend against this.
        return False


def mod_import(module):
    """
    A generic Python module loader.

    Args:
        module (str, module): This can be either a Python path
            (dot-notation like `evennia.objects.models`), an absolute path
            (e.g. `/home/eve/evennia/evennia/objects.models.py`) or an
            already imported module object (e.g. `models`)
    Returns:
        module (module or None): An imported module. If the input argument was
        already a module, this is returned as-is, otherwise the path is
        parsed and imported. Returns `None` and logs error if import failed.

    """

    if not module:
        return None

    if isinstance(module, types.ModuleType):
        # if this is already a module, we are done
        mod = module
    else:
        # first try to import as a python path
        try:
            mod = __import__(module, fromlist=["None"])
        except ImportError as ex:
            # check just where the ImportError happened (it could have been
            # an erroneous import inside the module as well). This is the
            # trivial way to do it ...
            if str(ex) != "Import by filename is not supported.":
                raise

            # error in this module. Try absolute path import instead

            if not os.path.isabs(module):
                module = os.path.abspath(module)
            path, filename = module.rsplit(os.path.sep, 1)
            modname = re.sub(r"\.py$", "", filename)

            try:
                result = imp.find_module(modname, [path])
            except ImportError:
                logger.log_trace("Could not find module '%s' (%s.py) at path '%s'" % (modname, modname, path))
                return
            try:
                mod = imp.load_module(modname, *result)
            except ImportError:
                logger.log_trace("Could not find or import module %s at path '%s'" % (modname, path))
                mod = None
            # we have to close the file handle manually
            result[0].close()
    return mod


def all_from_module(module):
    """
    Return all global-level variables from a module.

    Args:
        module (str, module): This can be either a Python path
            (dot-notation like `evennia.objects.models`), an absolute path
            (e.g. `/home/eve/evennia/evennia/objects.models.py`) or an
            already imported module object (e.g. `models`)

    Returns:
        variables (dict): A dict of {variablename: variable} for all
            variables in the given module.

    Notes:
        Ignores modules and variable names starting with an underscore.

    """
    mod = mod_import(module)
    if not mod:
        return {}
    return dict((key, val) for key, val in mod.__dict__.items()
                            if not (key.startswith("_") or ismodule(val)))


def variable_from_module(module, variable=None, default=None):
    """
    Retrieve a variable or list of variables from a module. The
    variable(s) must be defined globally in the module. If no variable
    is given (or a list entry is `None`), all global variables are
    extracted from the module.

    Args:
      module (string or module): Python path, absolute path or a module.
      variable (string or iterable, optional): Single variable name or iterable
          of variable names to extract. If not given, all variables in
          the module will be returned.
      default (string, optional): Default value to use if a variable fails to
          be extracted. Ignored if `variable` is not given.

    Returns:
        variables (value or list): A single value or a list of values
        depending on if `variable` is given or not. Errors in lists
        are replaced by the `default` argument.

    """

    if not module:
        return default

    mod = mod_import(module)

    if variable:
        result = []
        for var in make_iter(variable):
            if var:
                # try to pick a named variable
                result.append(mod.__dict__.get(var, default))
    else:
        # get all
        result = [val for key, val in mod.__dict__.items()
                         if not (key.startswith("_") or ismodule(val))]

    if len(result) == 1:
        return result[0]
    return result


def string_from_module(module, variable=None, default=None):
    """
    This is a wrapper for `variable_from_module` that requires return
    value to be a string to pass. It's primarily used by login screen.

    Args:
      module (string or module): Python path, absolute path or a module.
      variable (string or iterable, optional): Single variable name or iterable
          of variable names to extract. If not given, all variables in
          the module will be returned.
      default (string, optional): Default value to use if a variable fails to
          be extracted. Ignored if `variable` is not given.

    Returns:
        variables (value or list): A single (string) value or a list of values
        depending on if `variable` is given or not. Errors in lists (such
        as the value not being a string) are replaced by the `default` argument.

    """
    val = variable_from_module(module, variable=variable, default=default)
    if val:
        if variable:
            return val
        else:
            result = [v for v in make_iter(val) if isinstance(v, basestring)]
            return result if result else default
    return default


def random_string_from_module(module):
    """
    Returns a random global string from a module.

    Args:
        module (string or module): Python path, absolute path or a module.

    Returns:
        random (string): A random stribg variable from `module`.
    """
    return random.choice(string_from_module(module))


def fuzzy_import_from_module(path, variable, default=None, defaultpaths=None):
    """
    Import a variable based on a fuzzy path. First the literal
    `path` will be tried, then all given `defaultpaths` will be
    prepended to see a match is found.

    Args:
        path (str): Full or partial python path.
        variable (str): Name of variable to import from module.
        default (string, optional): Default value to use if a variable fails to
          be extracted. Ignored if `variable` is not given.
        defaultpaths (iterable, options): Python paths to attempt in order if
            importing directly from `path` doesn't work.

    Returns:
        value (any): The variable imported from the module, or `default`, if
            not found.

    """
    paths = [path] + make_iter(defaultpaths)
    for modpath in paths:
        try:
            mod = import_module(path)
        except ImportError as ex:
            if not str(ex).startswith ("No module named %s" % path):
                # this means the module was found but it
                # triggers an ImportError on import.
                raise ex
            return getattr(mod, variable, default)
    return default


def class_from_module(path, defaultpaths=None):
    """
    Return a class from a module, given the module's path. This is
    primarily used to convert db_typeclass_path:s to classes.

    Args:
        path (str): Full Python dot-path to module.
        defaultpaths (iterable, optional): If a direc import from `path` fails,
            try subsequent imports by prepending those paths to `path`.

    Returns:
        class (Class): An uninstatiated class recovered from path.

    Raises:
        ImportError: If all loading failed.

    """
    cls = None
    if defaultpaths:
        paths = [path] + ["%s.%s" % (dpath, path) for dpath in make_iter(defaultpaths)] if defaultpaths else []
    else:
        paths = [path]

    for testpath in paths:
        if "." in path:
            testpath, clsname = testpath.rsplit(".", 1)
        else:
            raise ImportError("the path '%s' is not on the form modulepath.Classname." % path)
        try:
            mod = import_module(testpath, package="evennia")
        except ImportError:
            if len(trace()) > 2:
                # this means the error happened within the called module and
                # we must not hide it.
                exc = sys.exc_info()
                raise_(exc[1], None, exc[2])
            else:
                # otherwise, try the next suggested path
                continue
        try:
            cls = getattr(mod, clsname)
            break
        except AttributeError:
            if len(trace()) > 2:
                # AttributeError within the module, don't hide it
                exc = sys.exc_info()
                raise_(exc[1], None, exc[2])
    if not cls:
        err = "Could not load typeclass '%s'" % path
        if defaultpaths:
            err += "\nPaths searched:\n    %s" % "\n    ".join(paths)
        else:
            err += "."
        raise ImportError(err)
    return cls
# alias
object_from_module = class_from_module

def init_new_player(player):
    """
    Deprecated.
    """
    from evennia.utils import logger
    logger.log_dep("evennia.utils.utils.init_new_player is DEPRECATED and should not be used.")


def string_similarity(string1, string2):
    """
    This implements a "cosine-similarity" algorithm as described for example in
       *Proceedings of the 22nd International Conference on Computation
       Linguistics* (Coling 2008), pages 593-600, Manchester, August 2008.
    The measure-vectors used is simply a "bag of words" type histogram
    (but for letters).

    Args:
        string1 (str): String to compare (may contain any number of words).
        string2 (str): Second string to compare (any number of words).

    Returns:
        similarity (float): A value 0...1 rating how similar the two
            strings are.

    """
    vocabulary = set(list(string1 + string2))
    vec1 = [string1.count(v) for v in vocabulary]
    vec2 = [string2.count(v) for v in vocabulary]
    try:
        return float(sum(vec1[i] * vec2[i] for i in range(len(vocabulary)))) / \
               (math.sqrt(sum(v1**2 for v1 in vec1)) * math.sqrt(sum(v2**2 for v2 in vec2)))
    except ZeroDivisionError:
        # can happen if empty-string cmdnames appear for some reason.
        # This is a no-match.
        return 0


def string_suggestions(string, vocabulary, cutoff=0.6, maxnum=3):
    """
    Given a `string` and a `vocabulary`, return a match or a list of
    suggestions based on string similarity.

    Args:
        string (str): A string to search for.
        vocabulary (iterable): A list of available strings.
        cutoff (int, 0-1): Limit the similarity matches (the higher
            the value, the more exact a match is required).
        maxnum (int): Maximum number of suggestions to return.

    Returns:
        suggestions (list): Suggestions from `vocabulary` with a 
            similarity-rating that higher than or equal to `cutoff`.
            Could be empty if there are no matches.

    """
    return [tup[1] for tup in sorted([(string_similarity(string, sugg), sugg)
                                       for sugg in vocabulary],
                                           key=lambda tup: tup[0], reverse=True)
                                           if tup[0] >= cutoff][:maxnum]


def string_partial_matching(alternatives, inp, ret_index=True):
    """
    Partially matches a string based on a list of `alternatives`.
    Matching is made from the start of each subword in each
    alternative. Case is not important. So e.g. "bi sh sw" or just
    "big" or "shiny" or "sw" will match "Big shiny sword". Scoring is
    done to allow to separate by most common demoninator. You will get
    multiple matches returned if appropriate.

    Args:
        alternatives (list of str): A list of possible strings to
            match.
        inp (str): Search criterion.
        ret_index (bool, optional): Return list of indices (from alternatives
            array) instead of strings.
    Returns:
        matches (list): String-matches or indices if `ret_index` is `True`.

    """
    if not alternatives or not inp:
        return []

    matches = defaultdict(list)
    inp_words = inp.lower().split()
    for altindex, alt in enumerate(alternatives):
        alt_words = alt.lower().split()
        last_index = 0
        score = 0
        for inp_word in inp_words:
            # loop over parts, making sure only to visit each part once
            # (this will invalidate input in the wrong word order)
            submatch = [last_index + alt_num for alt_num, alt_word
                        in enumerate(alt_words[last_index:])
                                     if alt_word.startswith(inp_word)]
            if submatch:
                last_index = min(submatch) + 1
                score += 1
            else:
                score = 0
                break
        if score:
            if ret_index:
                matches[score].append(altindex)
            else:
                matches[score].append(alt)
    if matches:
        return matches[max(matches)]
    return []


def format_table(table, extra_space=1):
    """
    Note: `evennia.utils.evtable` is more powerful than this, but this
    function can be useful when the number of columns and rows are
    unknown and must be calculated on the fly.

    Args.
        table (list): A list of lists to represent columns in the
            table: `[[val,val,val,...], [val,val,val,...], ...]`, where
            each val will be placed on a separate row in the
            column. All columns must have the same number of rows (some
            positions may be empty though).
        extra_space (int, optional): Sets how much *minimum* extra
            padding (in characters) should  be left between columns.

    Returns:
        table (list): A list of lists representing the rows to print
            out one by one.

    Notes:
        The function formats the columns to be as wide as the widest member
        of each column.

    Examples:

        ```python
        for ir, row in enumarate(ftable):
            if ir == 0:
                # make first row white
                string += "\n{w" + ""join(row) + "{n"
            else:
                string += "\n" + "".join(row)
        print string
    ```
    """
    if not table:
        return [[]]

    max_widths = [max([len(str(val)) for val in col]) for col in table]
    ftable = []
    for irow in range(len(table[0])):
        ftable.append([str(col[irow]).ljust(max_widths[icol]) + " " * extra_space
                       for icol, col in enumerate(table)])
    return ftable


def get_evennia_pids():
    """
    Get the currently valid PIDs (Process IDs) of the Portal and
    Server by trying to access a PID file.

    Returns:
        server, portal (tuple): The PIDs of the respective processes,
            or two `None` values if not found.

    Examples:
        This can be used to determine if we are in a subprocess by
        something like:

        ```python
        self_pid = os.getpid()
        server_pid, portal_pid = get_evennia_pids()
        is_subprocess = self_pid not in (server_pid, portal_pid)
        ```
    """
    server_pidfile = os.path.join(settings.GAME_DIR, 'server.pid')
    portal_pidfile = os.path.join(settings.GAME_DIR, 'portal.pid')
    server_pid, portal_pid = None, None
    if os.path.exists(server_pidfile):
        f = open(server_pidfile, 'r')
        server_pid = f.read()
        f.close()
    if os.path.exists(portal_pidfile):
        f = open(portal_pidfile, 'r')
        portal_pid = f.read()
        f.close()
    if server_pid and portal_pid:
        return int(server_pid), int(portal_pid)
    return None, None

from gc import get_referents
from sys import getsizeof
def deepsize(obj, max_depth=4):
    """
    Get not only size of the given object, but also the size of
    objects referenced by the object, down to `max_depth` distance
    from the object.

    Args:
        obj (object): the object to be measured.
        max_depth (int, optional): maximum referential distance
            from `obj` that `deepsize()` should cover for
            measuring objects referenced by `obj`.

    Returns:
        size (int): deepsize of `obj` in Bytes.

    Notes:
        This measure is necessarily approximate since some
        memory is shared between objects. The `max_depth` of 4 is roughly
        tested to give reasonable size information about database models
        and their handlers.

    """
    def _recurse(o, dct, depth):
        if max_depth >= 0 and depth > max_depth:
            return
        for ref in get_referents(o):
            idr = id(ref)
            if not idr in dct:
                dct[idr] = (ref, getsizeof(ref, default=0))
                _recurse(ref, dct, depth+1)
    sizedict = {}
    _recurse(obj, sizedict, 0)
    #count = len(sizedict) + 1
    size = getsizeof(obj) + sum([p[1] for p in sizedict.values()])
    return size

# lazy load handler
_missing = object()
class lazy_property(object):
    """
    Delays loading of property until first access. Credit goes to the
    Implementation in the werkzeug suite:
    http://werkzeug.pocoo.org/docs/utils/#werkzeug.utils.cached_property

    This should be used as a decorator in a class and in Evennia is
    mainly used to lazy-load handlers:

        ```python
        @lazy_property
        def attributes(self):
            return AttributeHandler(self)
        ```

    Once initialized, the `AttributeHandler` will be available as a
    property "attributes" on the object.

    """
    def __init__(self, func, name=None, doc=None):
        "Store all properties for now"
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        "Triggers initialization"
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
        obj.__dict__[self.__name__] = value
        return value

_STRIP_ANSI = None
_RE_CONTROL_CHAR = re.compile('[%s]' % re.escape(''.join([unichr(c) for c in range(0,32)])))# + range(127,160)])))
def strip_control_sequences(string):
    """
    Remove non-print text sequences.

    Args:
        string (str): Text to strip.

    Returns.
        text (str): Stripped text.

    """
    global _STRIP_ANSI
    if not _STRIP_ANSI:
        from evennia.utils.ansi import strip_raw_ansi as _STRIP_ANSI
    return _RE_CONTROL_CHAR.sub('', _STRIP_ANSI(string))


def calledby(callerdepth=1):
    """
    Only to be used for debug purposes. Insert this debug function in
    another function; it will print which function called it.

    Args:
        callerdepth (int): Must be larger than 0. When > 1, it will
            print the caller of the caller etc.

    Returns:
        calledby (str): A debug string detailing which routine called
            us.

    """
    import inspect, os
    stack = inspect.stack()
    # we must step one extra level back in stack since we don't want
    # to include the call of this function itself.
    callerdepth = min(max(2, callerdepth + 1), len(stack)-1)
    frame = inspect.stack()[callerdepth]
    path = os.path.sep.join(frame[1].rsplit(os.path.sep, 2)[-2:])
    return "[called by '%s': %s:%s %s]" % (frame[3], path, frame[2], frame[4])


def m_len(target):
    """
    Provides length checking for strings with MXP patterns, and falls
    back to normal len for other objects.

    Args:
        target (string): A string with potential MXP components
            to search.

    Returns:
        length (int): The length of `target`, ignoring MXP components.

    """
    # Would create circular import if in module root.
    from evennia.utils.ansi import ANSI_PARSER
    if inherits_from(target, basestring):
        return len(ANSI_PARSER.strip_mxp(target))
    return len(target)

#------------------------------------------------------------------
# Search handler function
#------------------------------------------------------------------
#
# Replace this hook function by changing settings.SEARCH_AT_RESULT.
#

def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """
    This is a generic hook for handling all processing of a search
    result, including error reporting.

    Args:
        matches (list): This is a list of 0, 1 or more typeclass instances,
            the matched result of the search. If 0, a nomatch error should
            be echoed, and if >1, multimatch errors should be given. Only
            if a single match should the result pass through.
        caller (Object): The object performing the search and/or which should
        receive error messages.
    query (str, optional): The search query used to produce `matches`.
        quiet (bool, optional): If `True`, no messages will be echoed to caller
            on errors.

    Kwargs:
        nofound_string (str): Replacement string to echo on a notfound error.
        multimatch_string (str): Replacement string to echo on a multimatch error.

    Returns:
        processed_result (Object or None): This is always a single result
            or `None`. If `None`, any error reporting/handling should
            already have happened.
    """

    error = ""
    if not matches:
        # no results.
        error = kwargs.get("nofound_string") or _("Could not find '%s'." % query)
        matches = None
    elif len(matches) > 1:
        error = kwargs.get("multimatch_string", None)
        if not error:
            error = _("More than one match for '%s'" \
                     " (please narrow target):" % query)
            for num, result in enumerate(matches):
                error += "\n %i%s%s%s" % (
                    num + 1, _MULTIMATCH_SEPARATOR,
                    result.get_display_name(caller) if hasattr(result, "get_display_name") else result.key,
                    result.get_extra_info(caller))
        matches = None
    else:
        # exactly one match
        matches = matches[0]

    if error and not quiet:
        caller.msg(error.strip())
    return matches


class LimitedSizeOrderedDict(OrderedDict):
    """
    This dictionary subclass is both ordered and limited to a maximum
    number of elements. Its main use is to hold a cache that can never
    grow out of bounds.

    """
    def __init__(self, *args, **kwargs):
        """
        Limited-size ordered dict.

        Kwargs:
            size_limit (int): Use this to limit the number of elements
                alloweds to be in this list. By default the overshooting elements
                will be removed in FIFO order.
            fifo (bool, optional): Defaults to `True`. Remove overshooting elements
                in FIFO order. If `False`, remove in FILO order.

        """
        super(LimitedSizeOrderedDict, self).__init__()
        self.size_limit = kwargs.get("size_limit", None)
        self.filo = not kwargs.get("fifo", True) # FIFO inverse of FILO
        self._check_size()

    def _check_size(self):
        filo = self.filo
        if self.size_limit is not None:
            while self.size_limit < len(self):
                self.popitem(last=filo)

    def __setitem__(self, key, value):
        super(LimitedSizeOrderedDict, self).__setitem__(key, value)
        self._check_size()

    def update(self, *args, **kwargs):
        super(LimitedSizeOrderedDict, self).update(*args, **kwargs)
        self._check_size()
