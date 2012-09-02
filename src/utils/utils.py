"""
General helper functions that don't fit neatly under any given category.

They provide some useful string and conversion methods that might
be of use when designing your own game.

"""

import os, sys, imp, types, math
import textwrap, datetime, random
from inspect import ismodule
from collections import defaultdict
from twisted.internet import threads
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

try:
    import cPickle as pickle
except ImportError:
    import pickle

ENCODINGS = settings.ENCODINGS
_LOGGER = None

def is_iter(iterable):
    """
    Checks if an object behaves iterably. However,
    strings are not accepted as iterable (although
    they are actually iterable), since string iterations
    are usually not what we want to do with a string.
    """
    return hasattr(iterable, '__iter__')

def make_iter(obj):
    "Makes sure that the object is always iterable."
    if not hasattr(obj, '__iter__'): return [obj]
    return obj

def fill(text, width=78, indent=0):
    """
    Safely wrap text to a certain number of characters.

    text: (str) The text to wrap.
    width: (int) The number of characters to wrap to.
    indent: (int) How much to indent new lines (the first line
                  will not be indented)
    """
    if not text:
        return ""
    indent = " " * indent
    return textwrap.fill(str(text), width, subsequent_indent=indent)


def crop(text, width=78, suffix="[...]"):
    """
    Crop text to a certain width, adding suffix to show the line
    continues. Cropping will be done so that the suffix will also fit
    within the given width.
    """
    ltext = len(to_str(text))
    if ltext <= width:
        return text
    else:
        lsuffix = len(suffix)
        return "%s%s" % (text[:width-lsuffix], suffix)

def dedent(text):
    """
    Safely clean all whitespace at the left
    of a paragraph. This is useful for preserving
    triple-quoted string indentation while still
    shifting it all to be next to the left edge of
    the display.
    """
    if not text:
        return ""
    return textwrap.dedent(text)

def list_to_string(inlist, endsep="and", addquote=False):
    """
    This pretty-formats a list as string output, adding
    an optional alternative separator to the second to last entry.
    If addquote is True, the outgoing strints will be surrounded by quotes.

    [1,2,3] -> '1, 2 and 3'
    """
    if not inlist:
        return ""
    if addquote:
        if len(inlist) == 1:
            return "\"%s\"" % inlist[0]
        return ", ".join("\"%s\"" % v for v in inlist[:-1]) + " %s %s" % (endsep, "\"%s\"" % inlist[-1])
    else:
        if len(inlist) == 1:
            return str(inlist[0])
        return ", ".join(str(v) for v in inlist[:-1]) + " %s %s" % (endsep, inlist[-1])

def wildcard_to_regexp(instring):
    """
    Converts a player-supplied string that may have wildcards in it to regular
    expressions. This is useful for name matching.

    instring: (string) A string that may potentially contain wildcards (* or ?).
    """
    regexp_string = ""

    # If the string starts with an asterisk, we can't impose the beginning of
    # string (^) limiter.
    if instring[0] != "*":
        regexp_string += "^"

    # Replace any occurances of * or ? with the appropriate groups.
    regexp_string += instring.replace("*","(.*)").replace("?", "(.{1})")

    # If there's an asterisk at the end of the string, we can't impose the
    # end of string ($) limiter.
    if instring[-1] != "*":
        regexp_string += "$"

    return regexp_string

def time_format(seconds, style=0):
    """
    Function to return a 'prettified' version of a value in seconds.

    Style 0: 1d 08:30
    Style 1: 1d
    Style 2: 1 day, 8 hours, 30 minutes, 10 seconds
    """
    if seconds < 0:
        seconds = 0
    else:
        # We'll just use integer math, no need for decimal precision.
        seconds = int(seconds)

    days     = seconds / 86400
    seconds -= days * 86400
    hours    = seconds / 3600
    seconds -= hours * 3600
    minutes  = seconds / 60
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

    return retval

def datetime_format(dtobj):
    """
    Takes a datetime object instance (e.g. from django's DateTimeField)
    and returns a string describing how long ago that date was.
    """

    year, month, day = dtobj.year, dtobj.month, dtobj.day
    hour, minute, second = dtobj.hour, dtobj.minute, dtobj.second
    now = datetime.datetime.now()

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
    """
    if os.name == osname:
        return True
    return False

def get_evennia_version():
    """
    Check for the evennia version info.
    """
    try:
        f = open(settings.BASE_PATH + os.sep + "VERSION.txt", 'r')
        return "%s-r%s" % (f.read().strip(), os.popen("hg id -i").read().strip())
    except IOError:
        return "Unknown version"

def pypath_to_realpath(python_path, file_ending='.py'):
    """
    Converts a path on dot python form (e.g. 'src.objects.models') to
    a system path ($BASE_PATH/src/objects/models.py). Calculates all paths as
    absoulte paths starting from the evennia main directory.
    """
    pathsplit = python_path.strip().split('.')
    if not pathsplit:
        return python_path
    path = settings.BASE_PATH
    for directory in pathsplit:
        path = os.path.join(path, directory)
    if file_ending:
        return "%s%s" % (path, file_ending)
    return path

def dbref(dbref):
    """
    Converts/checks if input is a valid dbref Valid forms of dbref
    (database reference number) are either a string '#N' or
    an integer N.  Output is the integer part.
    """
    if isinstance(dbref, basestring):
        dbref = dbref.lstrip('#')
        try:
            dbref = int(dbref)
            if dbref < 1:
                return None
        except Exception:
            return None
        return dbref
    return None

def to_unicode(obj, encoding='utf-8', force_string=False):
    """
    This decodes a suitable object to the unicode format. Note that
    one needs to encode it back to utf-8 before writing to disk or
    printing. Note that non-string objects are let through without
    conversion - this is important for e.g. Attributes. Use
    force_string to enforce conversion of objects to string. .
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
    for printing, writing to disk etc. Note that non-string
    objects are let through without modification - this is
    required e.g. for Attributes. Use force_string to force
    conversion of objects to strings.
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

    (This snippet was adapted from
    http://commandline.org.uk/python/email-syntax-check.)
    """

    emailaddress = r"%s" % emailaddress

    domains = ("aero", "asia", "biz", "cat", "com", "coop",
               "edu", "gov", "info", "int", "jobs", "mil", "mobi", "museum",
               "name", "net", "org", "pro", "tel", "travel")

    # Email address must be more than 7 characters in total.
    if len(emailaddress) < 7:
        return False # Address too short.

    # Split up email address into parts.
    try:
        localpart, domainname = emailaddress.rsplit('@', 1)
        host, toplevel = domainname.rsplit('.', 1)
    except ValueError:
        return False # Address does not have enough parts.

    # Check for Country code or Generic Domain.
    if len(toplevel) != 2 and toplevel not in domains:
        return False # Not a domain name.

    for i in '-_.%+.':
        localpart = localpart.replace(i, "")
    for i in '-_.':
        host = host.replace(i, "")

    if localpart.isalnum() and host.isalnum():
        return True # Email address is fine.
    else:
        return False # Email address has funny characters.


def inherits_from(obj, parent):
    """
    Takes an object and tries to determine if it inherits at any distance
    from parent. What differs this function from e.g. isinstance()
    is that obj may be both an instance and a class, and parent
    may be an instance, a class, or the python path to a class (counting
    from the evennia root directory).
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



def format_table(table, extra_space=1):
    """
    Takes a table of collumns: [[val,val,val,...], [val,val,val,...], ...]
    where each val will be placed on a separate row in the column. All
    collumns must have the same number of rows (some positions may be
    empty though).

    The function formats the columns to be as wide as the widest member
    of each column.

    extra_space defines how much extra padding should minimum be left between
    collumns.

    print the resulting list e.g. with

    for ir, row in enumarate(ftable):
        if ir == 0:
            # make first row white
            string += "\n{w" + ""join(row) + "{n"
        else:
            string += "\n" + "".join(row)
    print string

    """
    if not table:
        return [[]]

    max_widths = [max([len(str(val)) for val in col]) for col in table]
    ftable = []
    for irow in range(len(table[0])):
        ftable.append([str(col[irow]).ljust(max_widths[icol]) + " " * extra_space
                       for icol, col in enumerate(table)])
    return ftable



_FROM_MODEL_MAP = None
_TO_DBOBJ = lambda o: (hasattr(o, "dbobj") and o.dbobj) or o
_TO_PACKED_DBOBJ = lambda natural_key, dbref: ('__packed_dbobj__', natural_key, dbref)
def to_pickle(data, do_pickle=True, emptypickle=True):
    """
    Prepares object for being pickled. This will remap database models
    into an intermediary format, making them easily retrievable later.

    obj - a python object to prepare for pickling
    do_pickle - return a pickled object
    emptypickle - allow pickling also a None/empty value (False will be pickled)
                  This has no effect if do_pickle is False

    Database objects are stored as ('__packed_dbobj__', <natural_key_tuple>, <dbref>)
    """
    # prepare globals
    global _DUMPS, _LOADS, _FROM_MODEL_MAP
    if not _DUMPS:
        _DUMPS = lambda data: to_str(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
    if not _LOADS:
        _LOADS = lambda data: pickle.loads(to_str(data))
    if not _FROM_MODEL_MAP:
        _FROM_MODEL_MAP = defaultdict(str)
        _FROM_MODEL_MAP.update(dict((c.model, c.natural_key()) for c in ContentType.objects.all()))

    def iter_db2id(item):
        "recursively looping over iterable items, finding dbobjs"
        dtype = type(item)
        if dtype in (basestring, int, float):
            return item
        elif dtype == tuple:
            return tuple(iter_db2id(val) for val in item)
        elif dtype == dict:
            return dict((key, iter_db2id(val)) for key, val in item.items())
        else:
            item = _TO_DBOBJ(item)
            natural_key = _FROM_MODEL_MAP[hasattr(item, "id") and hasattr(item, '__class__') and item.__class__.__name__.lower()]
            if natural_key:
                return _TO_PACKED_DBOBJ(natural_key, item.id)
        return item
    # do recursive conversion
    data = iter_db2id(data)
    if do_pickle and not (not emptypickle and not data and data != False):
        return _DUMPS(data)
    return data

_TO_MODEL_MAP = None
_IS_PACKED_DBOBJ = lambda o: type(o)== tuple and len(o)==3 and o[0]=='__packed_dbobj__'
_TO_TYPECLASS = lambda o: (hasattr(o, 'typeclass') and o.typeclass) or o
def from_pickle(data, do_pickle=True):
    """
    Converts back from a data stream prepared with to_pickle. This will
    re-acquire database objects stored in the special format.

    obj - an object or a pickle, as indicated by the do_pickle flag
    do_pickle - actually unpickle the input before continuing
    """
    # prepare globals
    global _DUMPS, _LOADS, _TO_MODEL_MAP
    if not _DUMPS:
        _DUMPS = lambda data: to_str(pickle.dumps(data, pickle.HIGHEST_PROTOCOL))
    if not _LOADS:
        _LOADS = lambda data: pickle.loads(to_str(data))
    if not _TO_MODEL_MAP:
        _TO_MODEL_MAP = defaultdict(str)
        _TO_MODEL_MAP.update(dict((c.natural_key(), c.model_class()) for c in ContentType.objects.all()))

    def iter_id2db(item):
        "Recreate all objects recursively"
        dtype = type(item)
        if dtype in (basestring, int, float):
            return item
        elif _IS_PACKED_DBOBJ(item): # this is a tuple and must be done before tuple-check
            return  _TO_TYPECLASS(_TO_MODEL_MAP[item[1]].objects.get(id=item[2]))
        elif dtype == tuple:
            return tuple(iter_id2db(val) for val in item)
        elif dtype == dict:
            return dict((key, iter_id2db(val)) for key, val in item.items())
        return item
    if do_pickle:
        data = _LOADS(data)
    # do recursive conversion
    return iter_id2db(data)

_PPOOL = None
_PCMD = None
_DUMPS = None
_LOADS = None
def run_async(to_execute, *args, **kwargs):
    """
    Runs a function or executes a code snippet asynchronously.

    Inputs:
    to_execute (callable or string) - if a callable, this function
               will be executed in a separate thread, using the
               *args/**kwargs as input.
               If a string, this string must be a source snippet.
               This string will executed using the ProcPool is
               enabled, if not this will raise a RunTimeError.

    reserved kwargs:
        'at_return' -should point to a callable with one argument.
                    It will be called with the return value from
                    to_execute.
        'at_return_kwargs' - this dictionary which be used as keyword
                             arguments to the at_return callback.
        'at_err' - this will be called with a Failure instance if
                       there is an error in to_execute.
        'at_err_kwargs' - this dictionary will be used as keyword
                          arguments to the at_err errback.

    *args   - if to_execute is a callable, these args will be used
              as arguments for that function. If to_execute is a string
              *args are not used.
    *kwargs - if to_execute is a callable, these kwargs will be used
              as keyword arguments in that function. If a string, they
              instead are used to define the executable environment
              that should be available to execute the code in to_execute.

    run_async will either relay the code to a thread or to a processPool
    depending on input and what is available in the system. To activate
    Process pooling, settings.PROCPOOL_ENABLE must be set.

    to_execute in string form should handle all imports needed. kwargs
    can be used to send objects and properties. Such properties will
    be pickled, except Database Objects which will be sent across
    on a special format and re-loaded on the other side.

    To get a return value from your code snippet, Use the _return()
    function: Every call to this function from your snippet will
    append the argument to an internal list of returns. This return value
    (or a list) will be the first argument to the at_return callback.

    Use this function with restrain and only for features/commands
    that you know has no influence on the cause-and-effect order of your
    game (commands given after the async function might be executed before
    it has finished). Accessing the same property from different threads/processes
    can lead to unpredicted behaviour if you are not careful (this is called a
    "race condition").

    Also note that some databases, notably sqlite3, don't support access from
    multiple threads simultaneously, so if you do heavy database access from
    your to_execute under sqlite3 you will probably run very slow or even get
    tracebacks.

    """
    # handle all global imports.
    global _PPOOL, _PCMD
    if _PPOOL == None:
        # Try to load process Pool
        from src.server.sessionhandler import SESSIONS as _SESSIONS
        try:
            _PPOOL = _SESSIONS.server.services.namedServices.get("ProcPool").pool
        except AttributeError:
            _PPOOL = False
    if not _PCMD:
        from src.server.procpool import ExecuteCode as _PCMD

    # helper converters for callbacks/errbacks
    def convert_return(f):
        def func(ret, *args, **kwargs):
            rval = ret["response"] and from_pickle(ret["response"])
            if f: return f(rval, *args, **kwargs)
            else: return rval
        return func
    def convert_err(f):
        def func(err, *args, **kwargs):
            err.trap(Exception)
            err = err.getErrorMessage()
            if f:
                return f(err, *args, **kwargs)
            else:
                global _LOGGER
                if not _LOGGER:
                    from src.utils import logger as _LOGGER
                err = "Error reported from subprocess: '%s'" % err
                _LOGGER.log_errmsg(err)
        return func

    # handle special reserved input kwargs
    callback = convert_return(kwargs.pop("at_return", None))
    errback = convert_err(kwargs.pop("at_err", None))
    callback_kwargs = kwargs.pop("at_return_kwargs", {})
    errback_kwargs = kwargs.pop("at_err_kwargs", {})

    if isinstance(to_execute, basestring) and _PPOOL:
        # run source code in process pool
        cmdargs = {"source": to_str(to_execute)}
        cmdargs["environment"] = to_pickle(kwargs, emptypickle=False) or ""
        # defer to process pool
        deferred = _PPOOL.doWork(_PCMD, **cmdargs)
    elif callable(to_execute):
        # no process pool available, or we gave an explicit function and not code. Use threading.
        deferred = threads.deferToThread(to_execute, *args, **kwargs)
    else:
        # no appropriate input
        raise RuntimeError("'%s' could not be handled by run_async" % to_execute)

    # attach callbacks
    if callback:
        deferred.addCallback(callback, **callback_kwargs)
    deferred.addErrback(errback, **errback_kwargs)

def check_evennia_dependencies():
    """
    Checks the versions of Evennia's dependencies.

    Returns False if a show-stopping version mismatch is found.
    """
    # defining the requirements
    python_min = '2.6'
    twisted_min = '10.0'
    django_min = '1.2'
    south_min = '0.7'
    nt_stop_python_min = '2.7'

    errstring = ""
    no_error = True

    # Python
    pversion = ".".join([str(num) for num in sys.version_info if type(num) == int])
    if pversion < python_min:
        errstring += "\n WARNING: Python %s used. Evennia recommends version %s or higher (but not 3.x)." % (pversion, python_min)
    if os.name == 'nt' and pversion < nt_stop_python_min:
        errstring += "\n WARNING: Windows requires Python %s or higher in order to restart/stop the server from the command line."
        errstring += "\n          (You need to restart/stop from inside the game.)" % nt_stop_python_min
    # Twisted
    try:
        import twisted
        tversion = twisted.version.short()
        if tversion < twisted_min:
            errstring += "\n WARNING: Twisted %s found. Evennia recommends version %s or higher." % (twisted.version.short(), twisted_min)
    except ImportError:
        errstring += "\n ERROR: Twisted does not seem to be installed."
        no_error = False
    # Django
    try:
        import django
        dversion = ".".join([str(num) for num in django.VERSION if type(num) == int])
        if dversion < django_min:
            errstring += "\n ERROR: Django version %s found. Evennia requires version %s or higher." % (dversion, django_min)
            no_error = False
    except ImportError:
        errstring += "\n ERROR: Django does not seem to be installed."
        no_error = False
    # South
    try:
        import south
        sversion = south.__version__
        if sversion < south_min:
            errstring += "\n WARNING: South version %s found. Evennia recommends version %s or higher." % (sversion, south_min)
    except ImportError:
        pass
    # IRC support
    if settings.IRC_ENABLED:
        try:
            import twisted.words
            twisted.words # set to avoid debug info about not-used import
        except ImportError:
            errstring += "\n ERROR: IRC is enabled, but twisted.words is not installed. Please install it."
            errstring += "\n   Linux Debian/Ubuntu users should install package 'python-twisted-words', others"
            errstring += "\n   can get it from http://twistedmatrix.com/trac/wiki/TwistedWords."
            no_error = False
    errstring = errstring.strip()
    if errstring:
        print "%s\n %s\n%s" % ("-"*78, errstring, '-'*78)
    return no_error

def has_parent(basepath, obj):
    "Checks if basepath is somewhere in objs parent tree."
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
        module - this can be either a Python path (dot-notation like src.objects.models),
                 an absolute path (e.g. /home/eve/evennia/src/objects.models.py)
                 or an already import module object (e.g. models)
    Returns:
        an imported module. If the input argument was already a model, this is returned as-is,
        otherwise the path is parsed and imported.
    Error:
        returns None. The error is also logged.
    """

    def log_trace(errmsg=None):
        """
        Log a traceback to the log. This should be called
        from within an exception. errmsg is optional and
        adds an extra line with added info.
        """
        from traceback import format_exc
        from twisted.python import log
        print errmsg

        tracestring = format_exc()
        if tracestring:
            for line in tracestring.splitlines():
                log.msg('[::] %s' % line)
        if errmsg:
            try:
                errmsg = to_str(errmsg)
            except Exception, e:
                errmsg = str(e)
            for line in errmsg.splitlines():
                log.msg('[EE] %s' % line)

    if not module:
        return None

    if type(module) == types.ModuleType:
        # if this is already a module, we are done
        mod = module
    else:
        # first try to import as a python path
        try:
            mod = __import__(module, fromlist=["None"])
        except ImportError:

            # try absolute path import instead

            if not os.path.isabs(module):
                module = os.path.abspath(module)
            path, filename = module.rsplit(os.path.sep, 1)
            modname = filename.rstrip('.py')

            try:
                result = imp.find_module(modname, [path])
            except ImportError:
                log_trace("Could not find module '%s' (%s.py) at path '%s'" % (modname, modname, path))
                return
            try:
                mod = imp.load_module(modname, *result)
            except ImportError:
                log_trace("Could not find or import module %s at path '%s'" % (modname, path))
                mod = None
            # we have to close the file handle manually
            result[0].close()
    return mod

def variable_from_module(module, variable=None, default=None):
    """
    Retrieve a variable or list of variables from a module. The variable(s) must be defined
    globally in the module. If no variable is given (or a list entry is None), a random variable
    is extracted from the module.

    If module cannot be imported or given variable not found, default
    is returned.

    Args:
      module (string or module)- python path, absolute path or a module
      variable (string or iterable) - single variable name or iterable of variable names to extract
      default (string) - default value to use if a variable fails to be extracted.
    Returns:
      a single value or a list of values depending on the type of 'variable' argument. Errors in lists
      are replaced by the 'default' argument."""

    if not module:
        return default
    mod = mod_import(module)

    result = []
    for var in make_iter(variable):
        if var:
            # try to pick a named variable
            result.append(mod.__dict__.get(var, default))
        else:
            # random selection
            mvars = [val for key, val in mod.__dict__.items() if not (key.startswith("_") or ismodule(val))]
            result.append((mvars and random.choice(mvars)) or default)
    if len(result) == 1:
        return result[0]
    return result

def string_from_module(module, variable=None, default=None):
    """
    This is a wrapper for variable_from_module that requires return
    value to be a string to pass. It's primarily used by login screen.
    """
    val = variable_from_module(module, variable=variable, default=default)
    if isinstance(val, basestring):
        return val
    elif is_iter(val):
        return [(isinstance(v, basestring) and v or default) for v in val]
    return default

def init_new_player(player):
    """
    Helper method to call all hooks, set flags etc on a newly created
    player (and potentially their character, if it exists already)
    """
    # the FIRST_LOGIN flags are necessary for the system to call
    # the relevant first-login hooks.
    if player.character:
        player.character.db.FIRST_LOGIN = True
    player.db.FIRST_LOGIN = True

def string_similarity(string1, string2):
    """
    This implements a "cosine-similarity" algorithm as described for example in
       Proceedings of the 22nd International Conference on Computation Linguistics
       (Coling 2008), pages 593-600, Manchester, August 2008
    The measure vectors used is simply a "bag of words" type histogram (but for letters).

    The function returns a value 0...1 rating how similar the two strings are. The strings can
    contain multiple words.
    """
    vocabulary = set(list(string1 + string2))
    vec1 = [string1.count(v) for v in vocabulary]
    vec2 = [string2.count(v) for v in vocabulary]
    return float(sum(vec1[i]*vec2[i] for i in range(len(vocabulary)))) / \
           (math.sqrt(sum(v1**2 for v1 in vec1)) * math.sqrt(sum(v2**2 for v2 in vec2)))

def string_suggestions(string, vocabulary, cutoff=0.6, maxnum=3):
    """
    Given a string and a vocabulary, return a match or a list of suggestsion based on
    string similarity.

    Args:
        string (str)- a string to search for
        vocabulary (iterable) - a list of available strings
        cutoff (int, 0-1) - limit the similarity matches (higher, the more exact is required)
        maxnum (int) - maximum number of suggestions to return
    Returns:
        list of suggestions from vocabulary (could be empty if there are no matches)
    """
    return [tup[1] for tup in sorted([(string_similarity(string, sugg), sugg) for sugg in vocabulary],
                                      key=lambda tup: tup[0], reverse=True) if tup[0] >= cutoff][:maxnum]
