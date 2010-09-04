"""
General helper functions that don't fit neatly under any given category.

They provide some useful string and conversion methods that might
be of use when designing your own game. 
"""
import os
import textwrap
from django.conf import settings

def is_iter(iterable):
    """
    Checks if an object behaves iterably. However,
    strings are not accepted as iterable (although
    they are actually iterable), since string iterations
    are usually not what we want to do with a string.
    """
    if isinstance(iterable, basestring):
        # skip all forms of strings (str, unicode etc)
        return False     
    try:
        # check if object implements iter protocol
        return iter(iterable)
    except TypeError:
        return False 

def fill(text, width=78):
    """
    Safely wrap text to a certain number of characters.

    text: (str) The text to wrap.
    width: (int) The number of characters to wrap to.
    """
    if not text:
        return ""
    return textwrap.fill(str(text), width)

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
        
    days      = seconds / 86400
    seconds -= days * 86400
    hours     = seconds / 3600
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
        Full-detailed, long-winded format.
        """
        days_str = hours_str = minutes_str = ''
        if days > 0:
            days_str = '%i days, ' % (days,)
        if days or hours > 0:
            hours_str = '%i hours, ' % (hours,)
        if hours or minutes > 0:
            minutes_str = '%i minutes, ' % (minutes,)
        seconds_str = '%i seconds' % (seconds,)
        
        retval = '%s%s%s%s' % (days_str, hours_str, minutes_str, seconds_str,)
        return retval  
    
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
    a system path (src/objects/models.py). Calculates all paths as
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
    if type(dbref) == str:
        dbref = dbref.lstrip('#')
        try:
            dbref = int(dbref)
            if dbref < 1:
                return None 
        except Exception:
            return None
        return dbref

def to_unicode(obj, encoding='utf-8'):
    """
    This decodes a suitable object to 
    the unicode format. Note that one
    needs to encode it back to utf-8 
    before writing to disk or printing.
    """
    if isinstance(obj, basestring) \
            and not isinstance(obj, unicode):
        try:
            obj = unicode(obj, encoding)
        except UnicodeDecodeError:
            raise Exception("Error: '%s' contains invalid character(s) not in %s." % (obj, encoding))
        return obj

def to_str(obj, encoding='utf-8'):
    """
    This encodes a unicode string
    back to byte-representation, 
    for printing, writing to disk etc.
    """
    if isinstance(obj, basestring) \
            and isinstance(obj, unicode):
        try:
            obj = obj.encode(encoding)
        except UnicodeEncodeError:
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
