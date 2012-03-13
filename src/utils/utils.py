"""
General helper functions that don't fit neatly under any given category.

They provide some useful string and conversion methods that might
be of use when designing your own game. 


"""
import os, sys, imp
import textwrap
import datetime
import random
from twisted.internet import threads
from django.conf import settings

ENCODINGS = settings.ENCODINGS

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
    version_file_path = "%s%s%s" % (settings.BASE_PATH, os.sep, "VERSION")
    try:
        return open(version_file_path).readline().strip('\n').strip()
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
<    may be an instance, a class, or the python path to a class (counting
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

def run_async(async_func, at_return=None, at_err=None):
    """
    This wrapper will use Twisted's asynchronous features to run a slow
    function using a separate reactor thread. In effect this means that 
    the server will not be blocked while the slow process finish. 

    Use this function with restrain and only for features/commands
    that you know has no influence on the cause-and-effect order of your
    game (commands given after the async function might be executed before
    it has finished).
    
    async_func() - function that should be run asynchroneously
    at_return(r) - if given, this function will be called when async_func returns
                   value r at the end of a successful execution
    at_err(e) - if given, this function is called if async_func fails with an exception e. 
                use e.trap(ExceptionType1, ExceptionType2)

    """
    # create deferred object 
    
    deferred = threads.deferToThread(async_func)
    if at_return:
        deferred.addCallback(at_return)
    if at_err:
        deferred.addErrback(at_err)
    # always add a logging errback as a last catch
    def default_errback(e):
        from src.utils import logger
        logger.log_trace(e)   
    deferred.addErrback(default_errback)


def check_evennia_dependencies():
    """
    Checks the versions of Evennia's dependencies.

    Returns False if a show-stopping version mismatch is found.
    """

    # defining the requirements
    python_min = '2.5'
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

def mod_import(mod_path, propname=None):
    """
    Takes filename of a module (a python path or a full pathname)
    and imports it. If property is given, return the named 
    property from this module instead of the module itself. 
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

    # first try to import as a python path
    try:        
        mod = __import__(mod_path, fromlist=["None"])
    except ImportError:
        
        # try absolute path import instead

        if not os.path.isabs(mod_path):
            mod_path = os.path.abspath(mod_path)
        path, filename = mod_path.rsplit(os.path.sep, 1)
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

    if mod and propname:
        # we have a module, extract the sought property from it.
        try:
            mod_prop = mod.__dict__[to_str(propname)]
        except KeyError:
            log_trace("Could not import property '%s' from module %s." % (propname, mod_path))            
            return None 
        return mod_prop
    return mod 

def variable_from_module(modpath, variable, default=None):
    """
    Retrieve a given variable from a module. The variable must be
    defined globally in the module. This can be used to implement
    arbitrary plugin imports in the server. 

    If module cannot be imported or variable not found, default
    is returned.
    """
    try:
        mod = __import__(modpath, fromlist=["None"])
        return mod.__dict__.get(variable, default)
    except ImportError:
        return default

def string_from_module(modpath, variable=None, default=None):
    """
    This is a variation used primarily to get login screens randomly
    from a module.

    This obtains a string from a given module python path.  Using a
    specific variable name will also retrieve non-strings.
    
    The variable must be global within that module - that is, defined
    in the outermost scope of the module. The value of the variable
    will be returned. If not found, default is returned. If no variable is
    given, a random string variable is returned.

    This is useful primarily for storing various game strings in a
    module and extract them by name or randomly.
    """
    mod = __import__(modpath, fromlist=[None])
    if variable:
        return mod.__dict__.get(variable, default)
    else:
        mvars = [val for key, val in mod.__dict__.items() 
                 if not key.startswith('_') and isinstance(val, basestring)]    
        if not mvars:
            return default
        return mvars[random.randint(0, len(mvars)-1)]

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
