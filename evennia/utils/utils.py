# -*- encoding: utf-8 -*-
"""
General helper functions that don't fit neatly under any given category.

They provide some useful string and conversion methods that might
be of use when designing your own game.

"""
import gc
import importlib
import importlib.machinery
import importlib.util
import inspect
import math
import os
import random
import re
import sys
import textwrap
import threading
import traceback
import types
from ast import literal_eval
from collections import OrderedDict, defaultdict
from inspect import getmembers, getmodule, getmro, ismodule, trace
from os.path import join as osjoin
from string import punctuation
from unicodedata import east_asian_width

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email as django_validate_email
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from simpleeval import simple_eval
from twisted.internet import reactor, threads
from twisted.internet.defer import returnValue  # noqa - used as import target
from twisted.internet.task import deferLater

from evennia.utils import logger

_MULTIMATCH_TEMPLATE = settings.SEARCH_MULTIMATCH_TEMPLATE
_EVENNIA_DIR = settings.EVENNIA_DIR
_GAME_DIR = settings.GAME_DIR
_IS_MAIN_THREAD = threading.current_thread().name == "MainThread"

ENCODINGS = settings.ENCODINGS

_TASK_HANDLER = None
_TICKER_HANDLER = None
_STRIP_UNSAFE_TOKENS = None
_ANSISTRING = None

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


def is_iter(obj):
    """
    Checks if an object behaves iterably.

    Args:
        obj (any): Entity to check for iterability.

    Returns:
        is_iterable (bool): If `obj` is iterable or not.

    Notes:
        Strings are *not* accepted as iterable (although they are
        actually iterable), since string iterations are usually not
        what we want to do with a string.

    """
    if isinstance(obj, (str, bytes)):
        return False

    try:
        return iter(obj) and True
    except TypeError:
        return False


def make_iter(obj):
    """
    Makes sure that the object is always iterable.

    Args:
        obj (any): Object to make iterable.

    Returns:
        iterable (list or iterable): The same object
            passed-through or made iterable.

    """
    return not is_iter(obj) and [obj] or obj


def wrap(text, width=None, indent=0):
    """
    Safely wrap text to a certain number of characters.

    Args:
        text (str): The text to wrap.
        width (int, optional): The number of characters to wrap to.
        indent (int): How much to indent each line (with whitespace).

    Returns:
        text (str): Properly wrapped text.

    """
    width = width if width else settings.CLIENT_DEFAULT_WIDTH
    if not text:
        return ""
    indent = " " * indent
    return to_str(textwrap.fill(text, width, initial_indent=indent, subsequent_indent=indent))


# alias - fill
fill = wrap


def pad(text, width=None, align="c", fillchar=" "):
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
    width = width if width else settings.CLIENT_DEFAULT_WIDTH
    align = align if align in ("c", "l", "r") else "c"
    fillchar = fillchar[0] if fillchar else " "
    if align == "l":
        return text.ljust(width, fillchar)
    elif align == "r":
        return text.rjust(width, fillchar)
    else:
        return text.center(width, fillchar)


def crop(text, width=None, suffix="[...]"):
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
    width = width if width else settings.CLIENT_DEFAULT_WIDTH
    ltext = len(text)
    if ltext <= width:
        return text
    else:
        lsuffix = len(suffix)
        text = text[:width] if lsuffix >= width else "%s%s" % (text[: width - lsuffix], suffix)
        return to_str(text)


def dedent(text, baseline_index=None, indent=None):
    """
    Safely clean all whitespace at the left of a paragraph.

    Args:
        text (str): The text to dedent.
        baseline_index (int, optional): Which row to use as a 'base'
            for the indentation. Lines will be dedented to this level but
            no further. If None, indent so as to completely deindent the
            least indented text.
        indent (int, optional): If given, force all lines to this indent.
            This bypasses `baseline_index`.

    Returns:
        text (str): Dedented string.

    Notes:
        This is useful for preserving triple-quoted string indentation
        while still shifting it all to be next to the left edge of the
        display.

    """
    if not text:
        return ""
    if indent is not None:
        lines = text.split("\n")
        ind = " " * indent
        indline = "\n" + ind
        return ind + indline.join(line.strip() for line in lines)
    elif baseline_index is None:
        return textwrap.dedent(text)
    else:
        lines = text.split("\n")
        baseline = lines[baseline_index]
        spaceremove = len(baseline) - len(baseline.lstrip(" "))
        return "\n".join(
            line[min(spaceremove, len(line) - len(line.lstrip(" "))) :] for line in lines
        )


def justify(text, width=None, align="l", indent=0, fillchar=" "):
    """
    Fully justify a text so that it fits inside `width`. When using
    full justification (default) this will be done by padding between
    words with extra whitespace where necessary. Paragraphs will
    be retained.

    Args:
        text (str): Text to justify.
        width (int, optional): The length of each line, in characters.
        align (str, optional): The alignment, 'l', 'c', 'r', 'f' or 'a'
            for left, center, right, full justification. The 'a' stands for
            'absolute' and means the text will be returned unmodified.
        indent (int, optional): Number of characters indentation of
            entire justified text block.
        fillchar (str): The character to use to fill. Defaults to empty space.

    Returns:
        justified (str): The justified and indented block of text.

    """
    # we need to retain ansitrings
    global _ANSISTRING
    if not _ANSISTRING:
        from evennia.utils.ansi import ANSIString as _ANSISTRING

    is_ansi = isinstance(text, _ANSISTRING)
    lb = _ANSISTRING("\n") if is_ansi else "\n"

    def _process_line(line):
        """
        helper function that distributes extra spaces between words. The number
        of gaps is nwords - 1 but must be at least 1 for single-word lines. We
        distribute odd spaces to one of the gaps.
        """
        line_rest = width - (wlen + ngaps)

        gap = _ANSISTRING(" ") if is_ansi else " "

        if line_rest > 0:
            if align == "l":
                if line[-1] == "\n\n":
                    line[-1] = sp * (line_rest - 1) + "\n" + sp * width + "\n" + sp * width
                else:
                    line[-1] += sp * line_rest
            elif align == "r":
                line[0] = sp * line_rest + line[0]
            elif align == "c":
                pad = sp * (line_rest // 2)
                line[0] = pad + line[0]
                if line[-1] == "\n\n":
                    line[-1] += (
                        pad + sp * (line_rest % 2 - 1) + "\n" + sp * width + "\n" + sp * width
                    )
                else:
                    line[-1] = line[-1] + pad + sp * (line_rest % 2)
            else:  # align 'f'
                gap += sp * (line_rest // max(1, ngaps))
                rest_gap = line_rest % max(1, ngaps)
                for i in range(rest_gap):
                    line[i] += sp
        elif not any(line):
            return [sp * width]
        return gap.join(line)

    width = width if width is not None else settings.CLIENT_DEFAULT_WIDTH
    sp = fillchar

    if align == "a":
        # absolute mode - just crop or fill to width
        abs_lines = []
        for line in text.split("\n"):
            nlen = len(line)
            if len(line) < width:
                line += sp * (width - nlen)
            else:
                line = crop(line, width=width, suffix="")
            abs_lines.append(line)
        return lb.join(abs_lines)

    # all other aligns requires splitting into paragraphs and words

    # split into paragraphs and words
    paragraphs = [text]  # re.split("\n\s*?\n", text, re.MULTILINE)
    words = []
    for ip, paragraph in enumerate(paragraphs):
        if ip > 0:
            words.append(("\n", 0))
        words.extend((word, len(word)) for word in paragraph.split())

    if not words:
        # Just whitespace!
        return sp * width

    ngaps = 0
    wlen = 0
    line = []
    lines = []

    while words:
        if not line:
            # start a new line
            word = words.pop(0)
            wlen = word[1]
            line.append(word[0])
        elif (words[0][1] + wlen + ngaps) >= width:
            # next word would exceed word length of line + smallest gaps
            lines.append(_process_line(line))
            ngaps, wlen, line = 0, 0, []
        else:
            # put a new word on the line
            word = words.pop(0)
            line.append(word[0])
            if word[1] == 0:
                # a new paragraph, process immediately
                lines.append(_process_line(line))
                ngaps, wlen, line = 0, 0, []
            else:
                wlen += word[1]
                ngaps += 1

    if line:  # catch any line left behind
        lines.append(_process_line(line))
    indentstring = sp * indent
    out = lb.join([indentstring + line for line in lines])
    return lb.join([indentstring + line for line in lines])


def columnize(string, columns=2, spacing=4, align="l", width=None):
    """
    Break a string into a number of columns, using as little
    vertical space as possible.

    Args:
        string (str): The string to columnize.
        columns (int, optional): The number of columns to use.
        spacing (int, optional): How much space to have between columns.
        width (int, optional): The max width of the columns.
            Defaults to client's default width.

    Returns:
        columns (str): Text divided into columns.

    Raises:
        RuntimeError: If given invalid values.

    """
    columns = max(1, columns)
    spacing = max(1, spacing)
    width = width if width else settings.CLIENT_DEFAULT_WIDTH

    w_spaces = (columns - 1) * spacing
    w_txt = max(1, width - w_spaces)

    if w_spaces + columns > width:  # require at least 1 char per column
        raise RuntimeError("Width too small to fit columns")

    colwidth = int(w_txt / (1.0 * columns))

    # first make a single column which we then split
    onecol = justify(string, width=colwidth, align=align)
    onecol = onecol.split("\n")

    nrows, dangling = divmod(len(onecol), columns)
    nrows = [nrows + 1 if i < dangling else nrows for i in range(columns)]

    height = max(nrows)
    cols = []
    istart = 0
    for irows in nrows:
        cols.append(onecol[istart : istart + irows])
        istart = istart + irows
    for col in cols:
        if len(col) < height:
            col.append(" " * colwidth)

    sep = " " * spacing
    rows = []
    for irow in range(height):
        rows.append(sep.join(col[irow] for col in cols))

    return "\n".join(rows)


def iter_to_str(iterable, sep=",", endsep=", and", addquote=False):
    """
    This pretty-formats an iterable list as string output, adding an optional
    alternative separator to the second to last entry.  If `addquote`
    is `True`, the outgoing strings will be surrounded by quotes.

    Args:
        iterable (any): Usually an iterable to print. Each element must be possible to
            present with a string. Note that if this is a generator, it will be
            consumed by this operation.
        sep (str, optional): The string to use as a separator for each item in the iterable.
        endsep (str, optional): The last item separator will be replaced with this value.
        addquote (bool, optional): This will surround all outgoing
            values with double quotes.

    Returns:
        str: The list represented as a string.

    Notes:
        Default is to use 'Oxford comma', like 1, 2, 3, and 4.

    Examples:

        ```python
        >>> iter_to_string([1,2,3], endsep=',')
        '1, 2, 3'
        >>> iter_to_string([1,2,3], endsep='')
        '1, 2 3'
        >>> iter_to_string([1,2,3], ensdep='and')
        '1, 2 and 3'
        >>> iter_to_string([1,2,3], sep=';', endsep=';')
        '1; 2; 3'
        >>> iter_to_string([1,2,3], addquote=True)
        '"1", "2", and "3"'
        ```

    """
    iterable = list(make_iter(iterable))
    if not iterable:
        return ""
    len_iter = len(iterable)

    if addquote:
        iterable = tuple(f'"{val}"' for val in iterable)
    else:
        iterable = tuple(str(val) for val in iterable)

    if endsep:
        if endsep.startswith(sep):
            # oxford comma alternative
            endsep = endsep[1:] if len_iter < 3 else endsep
        elif endsep[0] not in punctuation:
            # add a leading space if endsep is a word
            endsep = " " + str(endsep).strip()

    # also add a leading space if separator is a word
    if sep not in punctuation:
        sep = " " + sep

    if len_iter == 1:
        return str(iterable[0])
    elif len_iter == 2:
        return f"{endsep} ".join(str(v) for v in iterable)
    else:
        return f"{sep} ".join(str(v) for v in iterable[:-1]) + f"{endsep} {iterable[-1]}"


# legacy aliases
list_to_string = iter_to_str
iter_to_string = iter_to_str


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
            4. highest unit (like "3 years" or "8 months" or "1 second")
    Returns:
        timeformatted (str): A pretty time string.
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

    retval = ""
    if style == 0:
        """
        Standard colon-style output.
        """
        if days > 0:
            retval = "%id %02i:%02i" % (days, hours, minutes)
        else:
            retval = "%02i:%02i" % (hours, minutes)
        return retval

    elif style == 1:
        """
        Simple, abbreviated form that only shows the highest time amount.
        """
        if days > 0:
            return "%id" % (days,)
        elif hours > 0:
            return "%ih" % (hours,)
        elif minutes > 0:
            return "%im" % (minutes,)
        else:
            return "%is" % (seconds,)
    elif style == 2:
        """
        Full-detailed, long-winded format. We ignore seconds.
        """
        days_str = hours_str = ""
        minutes_str = "0 minutes"

        if days > 0:
            if days == 1:
                days_str = "%i day, " % days
            else:
                days_str = "%i days, " % days
        if days or hours > 0:
            if hours == 1:
                hours_str = "%i hour, " % hours
            else:
                hours_str = "%i hours, " % hours
        if hours or minutes > 0:
            if minutes == 1:
                minutes_str = "%i minute " % minutes
            else:
                minutes_str = "%i minutes " % minutes
        retval = "%s%s%s" % (days_str, hours_str, minutes_str)
    elif style == 3:
        """
        Full-detailed, long-winded format. Includes seconds.
        """
        days_str = hours_str = minutes_str = seconds_str = ""
        if days > 0:
            if days == 1:
                days_str = "%i day, " % days
            else:
                days_str = "%i days, " % days
        if days or hours > 0:
            if hours == 1:
                hours_str = "%i hour, " % hours
            else:
                hours_str = "%i hours, " % hours
        if hours or minutes > 0:
            if minutes == 1:
                minutes_str = "%i minute " % minutes
            else:
                minutes_str = "%i minutes " % minutes
        if minutes or seconds > 0:
            if seconds == 1:
                seconds_str = "%i second " % seconds
            else:
                seconds_str = "%i seconds " % seconds
        retval = "%s%s%s%s" % (days_str, hours_str, minutes_str, seconds_str)
    elif style == 4:
        """
        Only return the highest unit.
        """
        if days >= 730:  # Several years
            return "{} years".format(days // 365)
        elif days >= 365:  # One year
            return "a year"
        elif days >= 62:  # Several months
            return "{} months".format(days // 31)
        elif days >= 31:  # One month
            return "a month"
        elif days >= 2:  # Several days
            return "{} days".format(days)
        elif days > 0:
            return "a day"
        elif hours >= 2:  # Several hours
            return "{} hours".format(hours)
        elif hours > 0:  # One hour
            return "an hour"
        elif minutes >= 2:  # Several minutes
            return "{} minutes".format(minutes)
        elif minutes > 0:  # One minute
            return "a minute"
        elif seconds >= 2:  # Several seconds
            return "{} seconds".format(seconds)
        elif seconds == 1:
            return "a second"
        else:
            return "0 seconds"
    else:
        raise ValueError("Unknown style for time format: %s" % style)

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

    now = timezone.now()

    if dtobj.year < now.year:
        # another year (Apr 5, 2019)
        timestring = dtobj.strftime(f"%b {dtobj.day}, %Y")
    elif dtobj.date() < now.date():
        # another date, same year  (Apr 5)
        timestring = dtobj.strftime(f"%b {dtobj.day}")
    elif dtobj.hour < now.hour - 1:
        # same day, more than 1 hour ago (10:45)
        timestring = dtobj.strftime("%H:%M")
    else:
        # same day, less than 1 hour ago (10:45:33)
        timestring = dtobj.strftime("%H:%M:%S")
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


def get_evennia_version(mode="long"):
    """
    Helper method for getting the current evennia version.

    Args:
        mode (str, optional): One of:
            - long: 0.9.0 rev342453534
            - short: 0.9.0
            - pretty: Evennia 0.9.0

    Returns:
        version (str): The version string.

    """
    import evennia

    vers = evennia.__version__
    if mode == "short":
        return vers.split()[0].strip()
    elif mode == "pretty":
        vers = vers.split()[0].strip()
        return f"Evennia {vers}"
    else:  # mode "long":
        return vers


def pypath_to_realpath(python_path, file_ending=".py", pypath_prefixes=None):
    """
    Converts a dotted Python path to an absolute path under the
    Evennia library directory or under the current game directory.

    Args:
        python_path (str): A dot-python path
        file_ending (str): A file ending, including the period.
        pypath_prefixes (list): A list of paths to test for existence. These
            should be on python.path form. EVENNIA_DIR and GAME_DIR are automatically
            checked, they need not be added to this list.

    Returns:
        abspaths (list): All existing, absolute paths created by
            converting `python_path` to an absolute paths and/or
            prepending `python_path` by `settings.EVENNIA_DIR`,
            `settings.GAME_DIR` and by`pypath_prefixes` respectively.

    Notes:
        This will also try a few combinations of paths to allow cases
        where pypath is given including the "evennia." or "mygame."
        prefixes.

    """
    path = python_path.strip().split(".")
    plong = osjoin(*path) + file_ending
    pshort = (
        osjoin(*path[1:]) + file_ending if len(path) > 1 else plong
    )  # in case we had evennia. or mygame.
    prefixlong = (
        [osjoin(*ppath.strip().split(".")) for ppath in make_iter(pypath_prefixes)]
        if pypath_prefixes
        else []
    )
    prefixshort = (
        [
            osjoin(*ppath.strip().split(".")[1:])
            for ppath in make_iter(pypath_prefixes)
            if len(ppath.strip().split(".")) > 1
        ]
        if pypath_prefixes
        else []
    )
    paths = (
        [plong]
        + [osjoin(_EVENNIA_DIR, prefix, plong) for prefix in prefixlong]
        + [osjoin(_GAME_DIR, prefix, plong) for prefix in prefixlong]
        + [osjoin(_EVENNIA_DIR, prefix, plong) for prefix in prefixshort]
        + [osjoin(_GAME_DIR, prefix, plong) for prefix in prefixshort]
        + [osjoin(_EVENNIA_DIR, plong), osjoin(_GAME_DIR, plong)]
        + [osjoin(_EVENNIA_DIR, prefix, pshort) for prefix in prefixshort]
        + [osjoin(_GAME_DIR, prefix, pshort) for prefix in prefixshort]
        + [osjoin(_EVENNIA_DIR, prefix, pshort) for prefix in prefixlong]
        + [osjoin(_GAME_DIR, prefix, pshort) for prefix in prefixlong]
        + [osjoin(_EVENNIA_DIR, pshort), osjoin(_GAME_DIR, pshort)]
    )
    # filter out non-existing paths
    return list(set(p for p in paths if os.path.isfile(p)))


def dbref(inp, reqhash=True):
    """
    Converts/checks if input is a valid dbref.

    Args:
        inp (int, str): A database ref on the form N or #N.
        reqhash (bool, optional): Require the #N form to accept
            input as a valid dbref.

    Returns:
        dbref (int or None): The integer part of the dbref or `None`
            if input was not a valid dbref.

    """
    if reqhash:
        num = (
            int(inp.lstrip("#"))
            if (isinstance(inp, str) and inp.startswith("#") and inp.lstrip("#").isdigit())
            else None
        )
        return num if isinstance(num, int) and num > 0 else None
    elif isinstance(inp, str):
        inp = inp.lstrip("#")
        return int(inp) if inp.isdigit() and int(inp) > 0 else None
    else:
        return inp if isinstance(inp, int) else None


def dbref_to_obj(inp, objclass, raise_errors=True):
    """
    Convert a #dbref to a valid object.

    Args:
        inp (str or int): A valid #dbref.
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
        if dbid < 0:
            return None
    except ValueError:
        return None

    # if we get to this point, inp is an integer dbref; get the matching object
    try:
        return objclass.objects.get(id=dbid)
    except Exception:
        if raise_errors:
            raise
        return inp


# legacy alias
dbid_to_obj = dbref_to_obj


# some direct translations for the latinify
_UNICODE_MAP = {
    "EM DASH": "-",
    "FIGURE DASH": "-",
    "EN DASH": "-",
    "HORIZONTAL BAR": "-",
    "HORIZONTAL ELLIPSIS": "...",
    "LEFT SINGLE QUOTATION MARK": "'",
    "RIGHT SINGLE QUOTATION MARK": "'",
    "LEFT DOUBLE QUOTATION MARK": '"',
    "RIGHT DOUBLE QUOTATION MARK": '"',
}


def latinify(string, default="?", pure_ascii=False):
    """
    Convert a unicode string to "safe" ascii/latin-1 characters.
    This is used as a last resort when normal encoding does not work.

    Arguments:
        string (str): A string to convert to 'safe characters' convertible
            to an latin-1 bytestring later.
        default (str, optional): Characters resisting mapping will be replaced
            with this character or string. The intent is to apply an encode operation
            on the string soon after.

    Returns:
        string (str): A 'latinified' string where each unicode character has been
            replaced with a 'safe' equivalent available in the ascii/latin-1 charset.
    Notes:
        This is inspired by the gist by Ricardo Murri:
            https://gist.github.com/riccardomurri/3c3ccec30f037be174d3

    """

    from unicodedata import name

    if isinstance(string, bytes):
        string = string.decode("utf8")

    converted = []
    for unich in iter(string):
        try:
            ch = unich.encode("utf8").decode("ascii")
        except UnicodeDecodeError:
            # deduce a latin letter equivalent from the Unicode data
            # point name; e.g., since `name(u'á') == 'LATIN SMALL
            # LETTER A WITH ACUTE'` translate `á` to `a`.  However, in
            # some cases the unicode name is still "LATIN LETTER"
            # although no direct equivalent in the Latin alphabet
            # exists (e.g., Þ, "LATIN CAPITAL LETTER THORN") -- we can
            # avoid these cases by checking that the letter name is
            # composed of one letter only.
            # We also supply some direct-translations for some particular
            # common cases.
            what = name(unich)
            if what in _UNICODE_MAP:
                ch = _UNICODE_MAP[what]
            else:
                what = what.split()
                if what[0] == "LATIN" and what[2] == "LETTER" and len(what[3]) == 1:
                    ch = what[3].lower() if what[1] == "SMALL" else what[3].upper()
                else:
                    ch = default
        converted.append(chr(ord(ch)))
    return "".join(converted)


def to_bytes(text, session=None):
    """
    Try to encode the given text to bytes, using encodings from settings or from Session. Will
    always return a bytes, even if given something that is not str or bytes.

    Args:
        text (any): The text to encode to bytes. If bytes, return unchanged. If not a str, convert
            to str before converting.
        session (Session, optional): A Session to get encoding info from. Will try this before
            falling back to settings.ENCODINGS.

    Returns:
        encoded_text (bytes): the encoded text following the session's protocol flag followed by the
            encodings specified in settings.ENCODINGS.  If all attempt fail, log the error and send
            the text with "?" in place of problematic characters.  If the specified encoding cannot
            be found, the protocol flag is reset to utf-8.  In any case, returns bytes.

    Notes:
        If `text` is already bytes, return it as is.

    """
    if isinstance(text, bytes):
        return text
    if not isinstance(text, str):
        # convert to a str representation before encoding
        try:
            text = str(text)
        except Exception:
            text = repr(text)

    default_encoding = session.protocol_flags.get("ENCODING", "utf-8") if session else "utf-8"
    try:
        return text.encode(default_encoding)
    except (LookupError, UnicodeEncodeError):
        for encoding in settings.ENCODINGS:
            try:
                return text.encode(encoding)
            except (LookupError, UnicodeEncodeError):
                pass
        # no valid encoding found. Replace unconvertable parts with ?
        return text.encode(default_encoding, errors="replace")


def to_str(text, session=None):
    """
    Try to decode a bytestream to a python str, using encoding schemas from settings
    or from Session. Will always return a str(), also if not given a str/bytes.

    Args:
        text (any): The text to encode to bytes. If a str, return it. If also not bytes, convert
            to str using str() or repr() as a fallback.
        session (Session, optional): A Session to get encoding info from. Will try this before
            falling back to settings.ENCODINGS.

    Returns:
        decoded_text (str): The decoded text.

    Notes:
        If `text` is already str, return it as is.
    """
    if isinstance(text, str):
        return text
    if not isinstance(text, bytes):
        # not a byte, convert directly to str
        try:
            return str(text)
        except Exception:
            return repr(text)

    default_encoding = session.protocol_flags.get("ENCODING", "utf-8") if session else "utf-8"
    try:
        return text.decode(default_encoding)
    except (LookupError, UnicodeDecodeError):
        for encoding in settings.ENCODINGS:
            try:
                return text.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                pass
        # no valid encoding found. Replace unconvertable parts with ?
        return text.decode(default_encoding, errors="replace")


def validate_email_address(emailaddress):
    """
    Checks if an email address is syntactically correct. Makes use
    of the django email-validator for consistency.

    Args:
        emailaddress (str): Email address to validate.

    Returns:
        bool: If this is a valid email or not.

    """
    try:
        django_validate_email(str(emailaddress))
    except DjangoValidationError:
        return False
    except Exception:
        logger.log_trace()
        return False
    else:
        return True


def inherits_from(obj, parent):
    """
    Takes an object and tries to determine if it inherits at *any*
    distance from parent.

    Args:
        obj (any): Object to analyze. This may be either an instance or
            a class.
        parent (any): Can be either an instance, a class or the python
            path to the class.

    Returns:
        inherits_from (bool): If `parent` is a parent to `obj` or not.

    Notes:
        What differentiates this function from Python's `isinstance()` is the
        flexibility in the types allowed for the object and parent being compared.

    """

    if callable(obj):
        # this is a class
        obj_paths = ["%s.%s" % (mod.__module__, mod.__name__) for mod in obj.mro()]
    else:
        obj_paths = ["%s.%s" % (mod.__module__, mod.__name__) for mod in obj.__class__.mro()]

    if isinstance(parent, str):
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
        name (str): One of 'sqlite3', 'mysql', 'postgresql' or 'oracle'.

    Returns:
        uses (bool): If the given database is used or not.

    """
    try:
        engine = settings.DATABASES["default"]["ENGINE"]
    except KeyError:
        engine = settings.DATABASE_ENGINE
    return engine == "django.db.backends.%s" % name


def delay(timedelay, callback, *args, **kwargs):
    """
    Delay the calling of a callback (function).

    Args:
        timedelay (int or float): The delay in seconds.
        callback (callable): Will be called as `callback(*args, **kwargs)`
            after `timedelay` seconds.
        *args: Will be used as arguments to callback
    Keyword Args:
        persistent (bool, optional): If True the delay remains after a server restart.
            persistent is False by default.
        any (any): Will be used as keyword arguments to callback.

    Returns:
        task (TaskHandlerTask): An instance of a task.
            Refer to, evennia.scripts.taskhandler.TaskHandlerTask

    Notes:
        The task handler (`evennia.scripts.taskhandler.TASK_HANDLER`) will
        be called for persistent or non-persistent tasks.
        If persistent is set to True, the callback, its arguments
        and other keyword arguments will be saved (serialized) in the database,
        assuming they can be.  The callback will be executed even after
        a server restart/reload, taking into account the specified delay
        (and server down time).
        Keep in mind that persistent tasks arguments and callback should not
        use memory references.
        If persistent is set to True the delay function will return an int
        which is the task's id intended for use with TASK_HANDLER's do_task
        and remove methods.
        All persistent tasks whose time delays have passed will be called on server startup.

    """
    global _TASK_HANDLER
    if _TASK_HANDLER is None:
        from evennia.scripts.taskhandler import TASK_HANDLER as _TASK_HANDLER

    return _TASK_HANDLER.add(timedelay, callback, *args, **kwargs)


def repeat(
    interval, callback, persistent=True, idstring="", stop=False, store_key=None, *args, **kwargs
):
    """
    Start a repeating task using the TickerHandler.

    Args:
        interval (int): How often to call callback.
        callback (callable): This will be called with `*args, **kwargs` every
            `interval` seconds. This must be possible to pickle regardless
            of if `persistent` is set or not!
        persistent (bool, optional): If ticker survives a server reload.
        idstring (str, optional): Separates multiple tickers. This is useful
            mainly if wanting to set up multiple repeats for the same
            interval/callback but with different args/kwargs.
        stop (bool, optional): If set, use the given parameters to _stop_ a running
            ticker instead of creating a new one.
        store_key (tuple, optional): This is only used in combination with `stop` and
            should be the return given from the original `repeat` call. If this
            is given, all other args except `stop` are ignored.
        *args: Used as arguments to `callback`.
        **kwargs: Keyword-arguments to pass to `callback`.

    Returns:
        tuple or None: The tuple is the `store_key` - the identifier for the
        created ticker.  Store this and pass into unrepat() in order to to stop
        this ticker later. Returns `None` if `stop=True`.

    Raises:
        KeyError: If trying to stop a ticker that was not found.

    """
    global _TICKER_HANDLER
    if _TICKER_HANDLER is None:
        from evennia.scripts.tickerhandler import TICKER_HANDLER as _TICKER_HANDLER

    if stop:
        # we pass all args, but only store_key matters if given
        _TICKER_HANDLER.remove(
            interval=interval,
            callback=callback,
            idstring=idstring,
            persistent=persistent,
            store_key=store_key,
        )
    else:
        return _TICKER_HANDLER.add(
            interval=interval, callback=callback, idstring=idstring, persistent=persistent
        )


def unrepeat(store_key):
    """
    This is used to stop a ticker previously started with `repeat`.

    Args:
        store_key (tuple): This is the return from `repeat`, used to uniquely
            identify the ticker to stop. Without the store_key, the ticker
            must be stopped by passing its parameters to `TICKER_HANDLER.remove`
            directly.

    Returns:
        bool: True if a ticker was stopped, False if not (for example because no
            matching ticker was found or it was already stopped).

    """
    try:
        repeat(None, None, stop=True, store_key=store_key)
        return True
    except KeyError:
        return False


_PPOOL = None
_PCMD = None
_PROC_ERR = "A process has ended with a probable error condition: process ended by signal 9."


def run_async(to_execute, *args, **kwargs):
    """
    Runs a function or executes a code snippet asynchronously.

    Args:
        to_execute (callable): If this is a callable, it will be
            executed with `*args` and non-reserved `**kwargs` as arguments.
            The callable will be executed using ProcPool, or in a thread
            if ProcPool is not available.
    Keyword Args:
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
    if "south" in settings.INSTALLED_APPS:
        errstring += (
            "\n ERROR: 'south' found in settings.INSTALLED_APPS. "
            "\n   South is no longer used. If this was added manually, remove it."
        )
        not_error = False
    # IRC support
    if settings.IRC_ENABLED:
        try:
            import twisted.words

            twisted.words  # set to avoid debug info about not-used import
        except ImportError:
            errstring += (
                "\n ERROR: IRC is enabled, but twisted.words is not installed. Please install it."
                "\n   Linux Debian/Ubuntu users should install package 'python-twisted-words', "
                "\n others can get it from http://twistedmatrix.com/trac/wiki/TwistedWords."
            )
            not_error = False
    errstring = errstring.strip()
    if errstring:
        mlen = max(len(line) for line in errstring.split("\n"))
        logger.log_err("%s\n%s\n%s" % ("-" * mlen, errstring, "-" * mlen))
    return not_error


def has_parent(basepath, obj):
    """
    Checks if `basepath` is somewhere in obj's parent tree.

    Args:
        basepath (str): Python dotpath to compare against obj path.
        obj (any): Object whose path is to be checked.

    Returns:
        has_parent (bool): If the check was successful or not.

    """
    try:
        return any(
            cls
            for cls in obj.__class__.mro()
            if basepath == "%s.%s" % (cls.__module__, cls.__name__)
        )
    except (TypeError, AttributeError):
        # this can occur if we tried to store a class object, not an
        # instance. Not sure if one should defend against this.
        return False


def mod_import_from_path(path):
    """
    Load a Python module at the specified path.

    Args:
        path (str): An absolute path to a Python module to load.

    Returns:
        (module or None): An imported module if the path was a valid
        Python module. Returns `None` if the import failed.

    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    dirpath, filename = path.rsplit(os.path.sep, 1)
    modname = filename.rstrip(".py")

    try:
        return importlib.machinery.SourceFileLoader(modname, path).load_module()
    except OSError:
        logger.log_trace(f"Could not find module '{modname}' ({modname}.py) at path '{dirpath}'")
        return None


def mod_import(module):
    """
    A generic Python module loader.

    Args:
        module (str, module): This can be either a Python path
            (dot-notation like `evennia.objects.models`), an absolute path
            (e.g. `/home/eve/evennia/evennia/objects/models.py`) or an
            already imported module object (e.g. `models`)
    Returns:
        (module or None): An imported module. If the input argument was
        already a module, this is returned as-is, otherwise the path is
        parsed and imported. Returns `None` and logs error if import failed.

    """
    if not module:
        return None

    if isinstance(module, types.ModuleType):
        # if this is already a module, we are done
        return module

    if module.endswith(".py") and os.path.exists(module):
        return mod_import_from_path(module)

    try:
        return importlib.import_module(module)
    except ImportError:
        return None


def all_from_module(module):
    """
    Return all global-level variables defined in a module.

    Args:
        module (str, module): This can be either a Python path
            (dot-notation like `evennia.objects.models`), an absolute path
            (e.g. `/home/eve/evennia/evennia/objects.models.py`) or an
            already imported module object (e.g. `models`)

    Returns:
        dict: A dict of {variablename: variable} for all
            variables in the given module.

    Notes:
        Ignores modules and variable names starting with an underscore, as well
        as variables imported into the module from other modules.

    """
    mod = mod_import(module)
    if not mod:
        return {}
    # make sure to only return variables actually defined in this
    # module if available (try to avoid imports)
    members = getmembers(mod, predicate=lambda obj: getmodule(obj) in (mod, None))
    return dict((key, val) for key, val in members if not key.startswith("_"))


def callables_from_module(module):
    """
    Return all global-level callables defined in a module.

    Args:
        module (str, module): A python-path to a module or an actual
            module object.

    Returns:
        callables (dict): A dict of {name: callable, ...} from the module.

    Notes:
        Will ignore callables whose names start with underscore "_".

    """
    mod = mod_import(module)
    if not mod:
        return {}
    # make sure to only return callables actually defined in this module (not imports)
    members = getmembers(mod, predicate=lambda obj: callable(obj) and getmodule(obj) == mod)
    return dict((key, val) for key, val in members if not key.startswith("_"))


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

    if not mod:
        return default

    if variable:
        result = []
        for var in make_iter(variable):
            if var:
                # try to pick a named variable
                result.append(mod.__dict__.get(var, default))
    else:
        # get all
        result = [
            val for key, val in mod.__dict__.items() if not (key.startswith("_") or ismodule(val))
        ]

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
            result = [v for v in make_iter(val) if isinstance(v, str)]
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
            mod = importlib.import_module(modpath)
        except ImportError as ex:
            if not str(ex).startswith("No module named %s" % modpath):
                # this means the module was found but it
                # triggers an ImportError on import.
                raise ex
            return getattr(mod, variable, default)
    return default


def class_from_module(path, defaultpaths=None, fallback=None):
    """
    Return a class from a module, given the class' full python path. This is
    primarily used to convert db_typeclass_path:s to classes.

    Args:
        path (str): Full Python dot-path to module.
        defaultpaths (iterable, optional): If a direct import from `path` fails,
            try subsequent imports by prepending those paths to `path`.
        fallback (str): If all other attempts fail, use this path as a fallback.
            This is intended as a last-resort. In the example of Evennia
            loading, this would be a path to a default parent class in the
            evennia repo itself.

    Returns:
        class (Class): An uninstantiated class recovered from path.

    Raises:
        ImportError: If all loading failed.

    """
    cls = None
    err = ""
    if defaultpaths:
        paths = (
            [path] + ["%s.%s" % (dpath, path) for dpath in make_iter(defaultpaths)]
            if defaultpaths
            else []
        )
    else:
        paths = [path]

    for testpath in paths:
        if "." in path:
            testpath, clsname = testpath.rsplit(".", 1)
        else:
            raise ImportError("the path '%s' is not on the form modulepath.Classname." % path)

        try:
            if not importlib.util.find_spec(testpath, package="evennia"):
                continue
        except ModuleNotFoundError:
            continue

        try:
            mod = importlib.import_module(testpath, package="evennia")
        except ModuleNotFoundError:
            err = traceback.format_exc(30)
            break

        try:
            cls = getattr(mod, clsname)
            break
        except AttributeError:
            if len(trace()) > 2:
                # AttributeError within the module, don't hide it
                err = traceback.format_exc(30)
                break
    if not cls:
        err = "\nCould not load typeclass '{}'{}".format(
            path, " with the following traceback:\n" + err if err else ""
        )
        if defaultpaths:
            err += "\nPaths searched:\n    %s" % "\n    ".join(paths)
        else:
            err += "."
        logger.log_err(err)
        if fallback:
            logger.log_warn(f"Falling back to {fallback}.")
            return class_from_module(fallback)
        else:
            # even fallback fails
            raise ImportError(err)
    return cls


# alias
object_from_module = class_from_module


def init_new_account(account):
    """
    Deprecated.
    """
    from evennia.utils import logger

    logger.log_dep("evennia.utils.utils.init_new_account is DEPRECATED and should not be used.")


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
        return float(sum(vec1[i] * vec2[i] for i in range(len(vocabulary)))) / (
            math.sqrt(sum(v1**2 for v1 in vec1)) * math.sqrt(sum(v2**2 for v2 in vec2))
        )
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
    return [
        tup[1]
        for tup in sorted(
            [(string_similarity(string, sugg), sugg) for sugg in vocabulary],
            key=lambda tup: tup[0],
            reverse=True,
        )
        if tup[0] >= cutoff
    ][:maxnum]


def string_partial_matching(alternatives, inp, ret_index=True):
    """
    Partially matches a string based on a list of `alternatives`.
    Matching is made from the start of each subword in each
    alternative. Case is not important. So e.g. "bi sh sw" or just
    "big" or "shiny" or "sw" will match "Big shiny sword". Scoring is
    done to allow to separate by most common denominator. You will get
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
            submatch = [
                last_index + alt_num
                for alt_num, alt_word in enumerate(alt_words[last_index:])
                if alt_word.startswith(inp_word)
            ]
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
    Format a 2D array of strings into a multi-column table.

    Args:
        table (list): A list of lists to represent columns in the
            table: `[[val,val,val,...], [val,val,val,...], ...]`, where
            each val will be placed on a separate row in the
            column. All columns must have the same number of rows (some
            positions may be empty though).
        extra_space (int, optional): Sets how much *minimum* extra
            padding (in characters) should  be left between columns.

    Returns:
        list: A list of lists representing the rows to print out one by one.

    Notes:
        The function formats the columns to be as wide as the widest member
        of each column.

        `evennia.utils.evtable` is more powerful than this, but this
        function can be useful when the number of columns and rows are
        unknown and must be calculated on the fly.

    Examples: ::

        ftable = format_table([[1,2,3], [4,5,6]])
        string = ""
        for ir, row in enumerate(ftable):
            if ir == 0:
                # make first row white
                string += "\\n|w" + "".join(row) + "|n"
            else:
                string += "\\n" + "".join(row)
        print(string)

    """

    if not table:
        return [[]]

    max_widths = [max([len(str(val)) for val in col]) for col in table]
    ftable = []
    for irow in range(len(table[0])):
        ftable.append(
            [
                str(col[irow]).ljust(max_widths[icol]) + " " * extra_space
                for icol, col in enumerate(table)
            ]
        )
    return ftable


def percent(value, minval, maxval, formatting="{:3.1f}%"):
    """
    Get a value in an interval as a percentage of its position
    in that interval. This also understands negative numbers.

    Args:
        value (number): This should be a value minval<=value<=maxval.
        minval (number or None): Smallest value in interval. This could be None
            for an open interval (then return will always be 100%)
        maxval (number or None): Biggest value in interval. This could be None
            for an open interval (then return will always be 100%)
        formatted (str, optional): This is a string that should
            accept one formatting tag. This will receive the
            current value as a percentage. If None, the
            raw float will be returned instead.
    Returns:
        str or float: The formatted value or the raw percentage as a float.
    Notes:
        We try to handle a weird interval gracefully.

        - If either maxval or minval is None (open interval), we (aribtrarily) assume 100%.
        - If minval > maxval, we return 0%.
        - If minval == maxval == value we are looking at a single value match and return 100%.
        - If minval == maxval != value we return 0%.
        - If value not in [minval..maxval], we set value to the  closest
          boundary, so the result will be 0% or 100%, respectively.

    """
    result = None
    if None in (minval, maxval):
        # we have no boundaries, percent calculation makes no sense,
        # we set this to 100% since it
        result = 100.0
    elif minval > maxval:
        # interval has no width so we cannot
        # occupy any position within it.
        result = 0.0
    elif minval == maxval == value:
        # this is a single value that we match
        result = 100.0
    elif minval == maxval != value:
        # interval has no width so we cannot be in it.
        result = 0.0

    if result is None:
        # constrain value to interval
        value = min(max(minval, value), maxval)

        # these should both be >0
        dpart = value - minval
        dfull = maxval - minval
        result = (dpart / dfull) * 100.0

    if isinstance(formatting, str):
        return formatting.format(result)
    return result


import functools  # noqa


def percentile(iterable, percent, key=lambda x: x):
    """
    Find the percentile of a list of values.

    Args:
        iterable (iterable): A list of values. Note N MUST BE already sorted.
        percent (float): A value from 0.0 to 1.0.
        key (callable, optional). Function to compute value from each element of N.

    Returns:
        float: The percentile of the values

    """
    if not iterable:
        return None
    k = (len(iterable) - 1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(iterable[int(k)])
    d0 = key(iterable[int(f)]) * (c - k)
    d1 = key(iterable[int(c)]) * (k - f)
    return d0 + d1


def format_grid(elements, width=78, sep="  ", verbatim_elements=None, line_prefix=""):
    """
    This helper function makes a 'grid' output, where it distributes the given
    string-elements as evenly as possible to fill out the given width.
    will not work well if the variation of length is very big!

    Args:
        elements (iterable): A 1D list of string elements to put in the grid.
        width (int, optional): The width of the grid area to fill.
        sep (str, optional): The extra separator to put between words. If
            set to the empty string, words may run into each other.
        verbatim_elements (list, optional): This is a list of indices pointing to
            specific items in the `elements` list. An element at this index will
            not be included in the calculation of the slot sizes. It will still
            be inserted into the grid at the correct position and may be surrounded
            by padding unless filling the entire line. This is useful for embedding
            decorations in the grid, such as horizontal bars.
        ignore_ansi (bool, optional): Ignore ansi markups when calculating white spacing.
        line_prefix (str, optional): A prefix to add at the beginning of each line.
            This can e.g. be used to preserve line color across line breaks.

    Returns:
        list: The grid as a list of ready-formatted rows. We return it
        like this to make it easier to insert decorations between rows, such
        as horizontal bars.
    """

    def _minimal_rows(elements):
        """
        Minimalistic distribution with minimal spacing, good for single-line
        grids but will look messy over many lines.
        """
        rows = [""]
        for element in elements:
            rowlen = display_len((rows[-1]))
            elen = display_len((element))
            if rowlen + elen <= width:
                rows[-1] += element
            else:
                rows.append(element)
        return rows

    def _weighted_rows(elements):
        """
        Dynamic-space, good for making even columns in a multi-line grid but
        will look strange for a single line.
        """
        wls = [display_len((elem)) for elem in elements]
        wls_percentile = [wl for iw, wl in enumerate(wls) if iw not in verbatim_elements]

        if wls_percentile:
            # get the nth percentile as a good representation of average width
            averlen = int(percentile(sorted(wls_percentile), 0.9)) + 2  # include extra space
            aver_per_row = width // averlen + 1
        else:
            # no adjustable rows, just keep all as-is
            aver_per_row = 1

        if aver_per_row == 1:
            # one line per row, output directly since this is trivial
            # we use rstrip here to remove extra spaces added by sep
            return [
                crop(element.rstrip(), width)
                + " " * max(0, width - display_len((element.rstrip())))
                for iel, element in enumerate(elements)
            ]

        indices = [averlen * ind for ind in range(aver_per_row - 1)]

        rows = []
        ic = 0
        row = ""
        for ie, element in enumerate(elements):

            wl = wls[ie]
            lrow = display_len((row))
            # debug = row.replace(" ", ".")

            if lrow + wl > width:
                # this slot extends outside grid, move to next line
                row += " " * (width - lrow)
                rows.append(row)
                if wl >= width:
                    # remove sep if this fills the entire line
                    element = element.rstrip()
                row = crop(element, width)
                ic = 0
            elif ic >= aver_per_row - 1:
                # no more slots available on this line
                row += " " * max(0, (width - lrow))
                rows.append(row)
                row = crop(element, width)
                ic = 0
            else:
                try:
                    while lrow > max(0, indices[ic]):
                        # slot too wide, extend into adjacent slot
                        ic += 1
                    row += " " * max(0, indices[ic] - lrow)
                except IndexError:
                    # we extended past edge of grid, crop or move to next line
                    if ic == 0:
                        row = crop(element, width)
                    else:
                        row += " " * max(0, width - lrow)
                    rows.append(row)
                    row = ""
                    ic = 0
                else:
                    # add a new slot
                    row += element + " " * max(0, averlen - wl)
                    ic += 1

            if ie >= nelements - 1:
                # last element, make sure to store
                row += " " * max(0, width - display_len((row)))
                rows.append(row)
        return rows

    if not elements:
        return []
    if not verbatim_elements:
        verbatim_elements = []

    nelements = len(elements)
    # add sep to all but the very last element
    elements = [elements[ie] + sep for ie in range(nelements - 1)] + [elements[-1]]

    if sum(display_len((element)) for element in elements) <= width:
        # grid fits in one line
        rows = _minimal_rows(elements)
    else:
        # full multi-line grid
        rows = _weighted_rows(elements)

    if line_prefix:
        return [line_prefix + row for row in rows]
    return rows


def get_evennia_pids():
    """
    Get the currently valid PIDs (Process IDs) of the Portal and
    Server by trying to access a PID file.

    Returns:
        server, portal (tuple): The PIDs of the respective processes,
            or two `None` values if not found.

    Examples:
        This can be used to determine if we are in a subprocess by

        ```python
        self_pid = os.getpid()
        server_pid, portal_pid = get_evennia_pids()
        is_subprocess = self_pid not in (server_pid, portal_pid)
        ```

    """
    server_pidfile = os.path.join(settings.GAME_DIR, "server.pid")
    portal_pidfile = os.path.join(settings.GAME_DIR, "portal.pid")
    server_pid, portal_pid = None, None
    if os.path.exists(server_pidfile):
        with open(server_pidfile, "r") as f:
            server_pid = f.read()
    if os.path.exists(portal_pidfile):
        with open(portal_pidfile, "r") as f:
            portal_pid = f.read()
    if server_pid and portal_pid:
        return int(server_pid), int(portal_pid)
    return None, None


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
        if 0 <= max_depth < depth:
            return
        for ref in gc.get_referents(o):
            idr = id(ref)
            if idr not in dct:
                dct[idr] = (ref, sys.getsizeof(ref, default=0))
                _recurse(ref, dct, depth + 1)

    sizedict = {}
    _recurse(obj, sizedict, 0)
    size = sys.getsizeof(obj) + sum([p[1] for p in sizedict.values()])
    return size


# lazy load handler
_missing = object()


class lazy_property:
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
    property "attributes" on the object. This is read-only since
    this functionality is pretty much exclusively used by handlers.

    """

    def __init__(self, func, name=None, doc=None):
        """Store all properties for now"""
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        """Triggers initialization"""
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
        obj.__dict__[self.__name__] = value
        return value

    def __set__(self, obj, value):
        """Protect against setting"""
        handlername = self.__name__
        raise AttributeError(
            _(
                "{obj}.{handlername} is a handler and can't be set directly. "
                "To add values, use `{obj}.{handlername}.add()` instead."
            ).format(obj=obj, handlername=handlername)
        )

    def __delete__(self, obj):
        """Protect against deleting"""
        handlername = self.__name__
        raise AttributeError(
            _(
                "{obj}.{handlername} is a handler and can't be deleted directly. "
                "To remove values, use `{obj}.{handlername}.remove()` instead."
            ).format(obj=obj, handlername=handlername)
        )


_STRIP_ANSI = None
_RE_CONTROL_CHAR = re.compile(
    "[%s]" % re.escape("".join([chr(c) for c in range(0, 32)]))
)  # + range(127,160)])))


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
    return _RE_CONTROL_CHAR.sub("", _STRIP_ANSI(string))


def calledby(callerdepth=1):
    """
    Only to be used for debug purposes. Insert this debug function in
    another function; it will print which function called it.

    Args:
        callerdepth (int or None): If None, show entire stack. If int, must be larger than 0.
            When > 1, it will print the sequence to that depth.

    Returns:
        calledby (str): A debug string detailing the code that called us.

    """
    import inspect

    def _stack_display(frame):
        path = os.path.sep.join(frame[1].rsplit(os.path.sep, 2)[-2:])
        return (
            f"> called by '{frame[3]}': {path}:{frame[2]} >>>"
            f" {frame[4][0].strip() if frame[4] else ''}"
        )

    stack = inspect.stack()

    out = []
    if callerdepth is None:
        callerdepth = len(stack) - 1

    # show range
    for idepth in range(1, max(1, callerdepth + 1)):
        # we must step one extra level back in stack since we don't want
        # to include the call of this function itself.
        out.append(_stack_display(stack[min(idepth + 1, len(stack) - 1)]))
    return "\n".join(out[::-1])


def m_len(target):
    """
    Provides length checking for strings with MXP patterns, and falls
    back to normal len for other objects.

    Args:
        target (str): A string with potential MXP components
            to search.

    Returns:
        length (int): The length of `target`, ignoring MXP components.

    """
    # Would create circular import if in module root.
    from evennia.utils.ansi import ANSI_PARSER

    if inherits_from(target, str) and "|lt" in target:
        return len(ANSI_PARSER.strip_mxp(target))
    return len(target)


def display_len(target):
    """
    Calculate the 'visible width' of text. This is not necessarily the same as the
    number of characters in the case of certain asian characters. This will also
    strip MXP patterns.

    Args:
        target (any): Something to measure the length of. If a string, it will be
            measured keeping asian-character and MXP links in mind.

    Return:
        int: The visible width of the target.

    """
    # Would create circular import if in module root.
    from evennia.utils.ansi import ANSI_PARSER

    if inherits_from(target, str):
        # str or ANSIString
        target = ANSI_PARSER.strip_mxp(target)
        target = ANSI_PARSER.parse_ansi(target, strip_ansi=True)
        extra_wide = ("F", "W")
        return sum(2 if east_asian_width(char) in extra_wide else 1 for char in target)
    else:
        return len(target)


# -------------------------------------------------------------------
# Search handler function
# -------------------------------------------------------------------
#
# Replace this hook function by changing settings.SEARCH_AT_RESULT.


def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """
    This is a generic hook for handling all processing of a search
    result, including error reporting. This is also called by the cmdhandler
    to manage errors in command lookup.

    Args:
        matches (list): This is a list of 0, 1 or more typeclass
            instances or Command instances, the matched result of the
            search. If 0, a nomatch error should be echoed, and if >1,
            multimatch errors should be given. Only if a single match
            should the result pass through.
        caller (Object): The object performing the search and/or which should
        receive error messages.
        query (str, optional): The search query used to produce `matches`.
        quiet (bool, optional): If `True`, no messages will be echoed to caller
            on errors.
    Keyword Args:
        nofound_string (str): Replacement string to echo on a notfound error.
        multimatch_string (str): Replacement string to echo on a multimatch error.

    Returns:
        processed_result (Object or None): This is always a single result
        or `None`. If `None`, any error reporting/handling should
        already have happened. The returned object is of the type we are
        checking multimatches for (e.g. Objects or Commands)

    """

    error = ""
    if not matches:
        # no results.
        error = kwargs.get("nofound_string") or _("Could not find '{query}'.").format(query=query)
        matches = None
    elif len(matches) > 1:
        multimatch_string = kwargs.get("multimatch_string")
        if multimatch_string:
            error = "%s\n" % multimatch_string
        else:
            error = _("More than one match for '{query}' (please narrow target):\n").format(
                query=query
            )

        for num, result in enumerate(matches):
            # we need to consider that result could be a Command, where .aliases
            # is a list of strings
            if hasattr(result.aliases, "all"):
                # result is a typeclassed entity where `.aliases` is an AliasHandler.
                aliases = result.aliases.all(return_objs=True)
                # remove pluralization aliases
                aliases = [
                    alias
                    for alias in aliases
                    if hasattr(alias, "category") and alias.category not in ("plural_key",)
                ]
            else:
                # result is likely a Command, where `.aliases` is a list of strings.
                aliases = result.aliases

            error += _MULTIMATCH_TEMPLATE.format(
                number=num + 1,
                name=result.get_display_name(caller)
                if hasattr(result, "get_display_name")
                else query,
                aliases=" [{alias}]".format(alias=";".join(aliases) if aliases else ""),
                info=result.get_extra_info(caller),
            )
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

        Keyword Args:
            size_limit (int): Use this to limit the number of elements
              alloweds to be in this list. By default the overshooting elements
              will be removed in FIFO order.
            fifo (bool, optional): Defaults to `True`. Remove overshooting elements
              in FIFO order. If `False`, remove in FILO order.

        """
        super().__init__()
        self.size_limit = kwargs.get("size_limit", None)
        self.filo = not kwargs.get("fifo", True)  # FIFO inverse of FILO
        self._check_size()

    def __eq__(self, other):
        ret = super().__eq__(other)
        if ret:
            return (
                ret
                and hasattr(other, "size_limit")
                and self.size_limit == other.size_limit
                and hasattr(other, "fifo")
                and self.fifo == other.fifo
            )
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def _check_size(self):
        filo = self.filo
        if self.size_limit is not None:
            while self.size_limit < len(self):
                self.popitem(last=filo)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._check_size()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._check_size()


def get_game_dir_path():
    """
    This is called by settings_default in order to determine the path
    of the game directory.

    Returns:
        path (str): Full OS path to the game dir

    """
    # current working directory, assumed to be somewhere inside gamedir.
    for inum in range(10):
        gpath = os.getcwd()
        if "server" in os.listdir(gpath):
            if os.path.isfile(os.path.join("server", "conf", "settings.py")):
                return gpath
        else:
            os.chdir(os.pardir)
    raise RuntimeError("server/conf/settings.py not found: Must start from inside game dir.")


def get_all_typeclasses(parent=None):
    """
    List available typeclasses from all available modules.

    Args:
        parent (str, optional): If given, only return typeclasses inheriting
            (at any distance) from this parent.

    Returns:
        dict: On the form `{"typeclass.path": typeclass, ...}`

    Notes:
        This will dynamically retrieve all abstract django models inheriting at
        any distance from the TypedObject base (aka a Typeclass) so it will
        work fine with any custom classes being added.

    """
    from evennia.typeclasses.models import TypedObject

    typeclasses = {
        "{}.{}".format(model.__module__, model.__name__): model
        for model in apps.get_models()
        if TypedObject in getmro(model)
    }
    if parent:
        typeclasses = {
            name: typeclass
            for name, typeclass in typeclasses.items()
            if inherits_from(typeclass, parent)
        }
    return typeclasses


def get_all_cmdsets(parent=None):
    """
    List available cmdsets from all available modules.

    Args:
        parent (str, optional): If given, only return cmdsets inheriting (at
            any distance) from this parent.

    Returns:
        dict: On the form {"cmdset.path": cmdset, ...}

    Notes:
        This will dynamically retrieve all abstract django models inheriting at
        any distance from the CmdSet base so it will work fine with any custom
        classes being added.

    """
    from evennia.commands.cmdset import CmdSet

    base_cmdset = class_from_module(parent) if parent else CmdSet

    cmdsets = {
        "{}.{}".format(subclass.__module__, subclass.__name__): subclass
        for subclass in base_cmdset.__subclasses__()
    }
    return cmdsets


def interactive(func):
    """
    Decorator to make a method pausable with `yield(seconds)`
    and able to ask for user-input with `response=yield(question)`.
    For the question-asking to work, one of the args or kwargs to the
    decorated function must be named 'caller'.

    Raises:
        ValueError: If asking an interactive question but the decorated
            function has no arg or kwarg named 'caller'.
        ValueError: If passing non int/float to yield using for pausing.

    Examples:

        ```python
        @interactive
        def myfunc(caller):
            caller.msg("This is a test")
            # wait five seconds
            yield(5)
            # ask user (caller) a question
            response = yield("Do you want to continue waiting?")
            if response == "yes":
                yield(5)
            else:
                # ...
        ```

    Notes:
       This turns the decorated function or method into a generator.

    """
    from evennia.utils.evmenu import get_input

    def _process_input(caller, prompt, result, generator):
        deferLater(reactor, 0, _iterate, generator, caller, response=result)
        return False

    def _iterate(generator, caller=None, response=None):
        try:
            if response is None:
                value = next(generator)
            else:
                value = generator.send(response)
        except StopIteration:
            pass
        else:
            if isinstance(value, (int, float)):
                delay(value, _iterate, generator, caller=caller)
            elif isinstance(value, str):
                if not caller:
                    raise ValueError(
                        "To retrieve input from a @pausable method, that method "
                        "must be called with a 'caller' argument)"
                    )
                get_input(caller, value, _process_input, generator=generator)
            else:
                raise ValueError("yield(val) in a @pausable method must have an int/float as arg.")

    def decorator(*args, **kwargs):
        argnames = inspect.getfullargspec(func).args
        caller = None
        if "caller" in argnames:
            # we assume this is an object
            caller = args[argnames.index("caller")]

        ret = func(*args, **kwargs)
        if isinstance(ret, types.GeneratorType):
            _iterate(ret, caller)
        else:
            return ret

    return decorator


def safe_convert_to_types(converters, *args, raise_errors=True, **kwargs):
    """
    Helper function to safely convert inputs to expected data types.

    Args:
        converters (tuple): A tuple `((converter, converter,...), {kwarg: converter, ...})` to
            match a converter to each element in `*args` and `**kwargs`.
            Each converter will will be called with the arg/kwarg-value as the only argument.
            If there are too few converters given, the others will simply not be converter. If the
            converter is given as the string 'py', it attempts to run
            `safe_eval`/`literal_eval` on  the input arg or kwarg value. It's possible to
            skip the arg/kwarg part of the tuple, an empty tuple/dict will then be assumed.
        *args: The arguments to convert with `argtypes`.
        raise_errors (bool, optional): If set, raise any errors. This will
            abort the conversion at that arg/kwarg. Otherwise, just skip the
            conversion of the failing arg/kwarg. This will be set by the FuncParser if
            this is used as a part of a FuncParser callable.
        **kwargs: The kwargs to convert with `kwargtypes`

    Returns:
        tuple: `(args, kwargs)` in converted form.

    Raises:
        utils.funcparser.ParsingError: If parsing failed in the `'py'`
            converter. This also makes this compatible with the FuncParser
            interface.
        any: Any other exception raised from other converters, if raise_errors is True.

    Notes:
        This function is often used to validate/convert input from untrusted sources. For
        security, the "py"-converter is deliberately limited and uses `safe_eval`/`literal_eval`
        which  only supports simple expressions or simple containers with literals. NEVER
        use the python `eval` or `exec` methods as a converter for any untrusted input! Allowing
        untrusted sources to execute arbitrary python on your server is a severe security risk,

    Example:
    ::

        $funcname(1, 2, 3.0, c=[1,2,3])

        def _funcname(*args, **kwargs):
            args, kwargs = safe_convert_input(((int, int, float), {'c': 'py'}), *args, **kwargs)
            # ...

    """
    container_end_char = {"(": ")", "[": "]", "{": "}"}  # tuples, lists, sets

    def _manual_parse_containers(inp):
        startchar = inp[0]
        endchar = inp[-1]
        if endchar != container_end_char.get(startchar):
            return
        return [str(part).strip() for part in inp[1:-1].split(",")]

    def _safe_eval(inp):
        if not inp:
            return ""
        if not isinstance(inp, str):
            # already converted
            return inp
        try:
            try:
                return literal_eval(inp)
            except ValueError:
                parts = _manual_parse_containers(inp)
                if not parts:
                    raise
                return parts

        except Exception as err:
            literal_err = f"{err.__class__.__name__}: {err}"
            try:
                return simple_eval(inp)
            except Exception as err:
                simple_err = f"{str(err.__class__.__name__)}: {err}"

        if raise_errors:
            from evennia.utils.funcparser import ParsingError

            err = (
                f"Errors converting '{inp}' to python:\n"
                f"literal_eval raised {literal_err}\n"
                f"simple_eval raised {simple_err}"
            )
            raise ParsingError(err)
        else:
            # fallback - convert to str
            return str(inp)

    # handle an incomplete/mixed set of input converters
    if not converters:
        return args, kwargs
    arg_converters, *kwarg_converters = converters
    arg_converters = make_iter(arg_converters)
    kwarg_converters = kwarg_converters[0] if kwarg_converters else {}

    # apply the converters
    if args and arg_converters:
        args = list(args)
        arg_converters = make_iter(arg_converters)
        for iarg, arg in enumerate(args[: len(arg_converters)]):
            converter = arg_converters[iarg]
            converter = _safe_eval if converter in ("py", "python") else converter
            try:
                args[iarg] = converter(arg)
            except Exception:
                if raise_errors:
                    raise
        args = tuple(args)
    if kwarg_converters and isinstance(kwarg_converters, dict):
        for key, converter in kwarg_converters.items():
            converter = _safe_eval if converter in ("py", "python") else converter
            if key in {**kwargs}:
                try:
                    kwargs[key] = converter(kwargs[key])
                except Exception:
                    if raise_errors:
                        raise
    return args, kwargs


def strip_unsafe_input(txt, session=None, bypass_perms=None):
    """
    Remove 'unsafe' text codes from text; these are used to elimitate
    exploits in user-provided data, such as html-tags, line breaks etc.

    Args:
        txt (str): The text to clean.
        session (Session, optional): A Session in order to determine if
            the check should be bypassed by permission (will be checked
            with the 'perm' lock, taking permission hierarchies into account).
        bypass_perms (list, optional): Iterable of permission strings
            to check for bypassing the strip. If not given, use
            `settings.INPUT_CLEANUP_BYPASS_PERMISSIONS`.

    Returns:
        str: The cleaned string.

    Notes:
        The `INPUT_CLEANUP_BYPASS_PERMISSIONS` list defines what account
        permissions are required to bypass this strip.

    """
    global _STRIP_UNSAFE_TOKENS
    if not _STRIP_UNSAFE_TOKENS:
        from evennia.utils.ansi import strip_unsafe_tokens as _STRIP_UNSAFE_TOKENS

    if session:
        obj = session.puppet if session.puppet else session.account
        bypass_perms = bypass_perms or settings.INPUT_CLEANUP_BYPASS_PERMISSIONS
        if obj.permissions.check(*bypass_perms):
            return txt

    # remove html codes
    txt = strip_tags(txt)
    txt = _STRIP_UNSAFE_TOKENS(txt)
    return txt


def copy_word_case(base_word, new_word):
    """
    Converts a word to use the same capitalization as a first word.

    Args:
        base_word (str): A word to get the capitalization from.
        new_word (str): A new word to capitalize in the same way as `base_word`.

    Returns:
        str: The `new_word` with capitalization matching the first word.

    Notes:
        This is meant for words. Longer sentences may get unexpected results.

        If the two words have a mix of capital/lower letters _and_ `new_word`
        is longer than `base_word`, the excess will retain its original case.

    """

    # Word
    if base_word.istitle():
        return new_word.title()
    # word
    elif base_word.islower():
        return new_word.lower()
    # WORD
    elif base_word.isupper():
        return new_word.upper()
    else:
        # WorD - a mix. Handle each character
        maxlen = len(base_word)
        shared, excess = new_word[:maxlen], new_word[maxlen - 1 :]
        return (
            "".join(
                char.upper() if base_word[ic].isupper() else char.lower()
                for ic, char in enumerate(new_word)
            )
            + excess
        )


def run_in_main_thread(function_or_method, *args, **kwargs):
    """
    Force a callable to execute in the main Evennia thread. This is only relevant when
    calling code from e.g. web views, which run in a separate threadpool. Use this
    to avoid race conditions.

    Args:
        function_or_method (callable): A function or method to fire.
        *args: Will be passed into the callable.
        **kwargs: Will be passed into the callable.

    """
    if _IS_MAIN_THREAD:
        return function_or_method(*args, **kwargs)
    else:
        return threads.blockingCallFromThread(reactor, function_or_method, *args, **kwargs)


_INT2STR_MAP_NOUN = {
    0: "no",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}
_INT2STR_MAP_ADJ = {1: "1st", 2: "2nd", 3: "3rd"}  # rest is Xth.


def int2str(number, adjective=False):
    """
    Convert a number to an English string for better display; so 1 -> one, 2 -> two etc
    up until 12, after which it will be '13', '14' etc.

    Args:
        number (int): The number to convert. Floats will be converted to ints.
        adjective (int): If set, map 1->1st, 2->2nd etc. If unset, map 1->one, 2->two etc.
            up to twelve.
    Return:
        str: The number expressed as a string.

    """
    number = int(number)
    if adjective:
        return _INT2STR_MAP_ADJ.get(number, f"{number}th")
    return _INT2STR_MAP_NOUN.get(number, str(number))


_STR2INT_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "thousand": 1000,
}
_STR2INT_ADJS = {
    "first": 1,
    "second": 2,
    "third": 3,
}


def str2int(number):
    """
    Converts a string to an integer.

    Args:
        number (str): The string to convert. It can be a digit such as "1", or a number word such as "one".

    Returns:
        int: The string represented as an integer.
    """
    number = str(number)
    original_input = number
    try:
        # it's a digit already
        return int(number)
    except:
        # if it's an ordinal number such as "1st", it'll convert to int with the last two characters chopped off
        try:
            return int(number[:-2])
        except:
            pass

    # convert sound changes for generic ordinal numbers
    if number[-2:] == "th":
        # remove "th"
        number = number[:-2]
        if number[-1] == "f":
            # e.g. twelfth, fifth
            number = number[:-1] + "ve"
        elif number[-2:] == "ie":
            # e.g. twentieth, fortieth
            number = number[:-2] + "y"
        # custom case for ninth
        elif number[-3:] == "nin":
            number += "e"

    if i := _STR2INT_MAP.get(number):
        # it's a single number, return it
        return i

    # remove optional "and"s
    number = number.replace(" and ", " ")

    # split number words by spaces, hyphens and commas, to accommodate multiple styles
    numbers = [word.lower() for word in re.split(r"[-\s\,]", number) if word]
    sums = []
    for word in numbers:
        # check if it's a known number-word
        if i := _STR2INT_MAP.get(word):
            if not len(sums):
                # initialize the list with the current value
                sums = [i]
            else:
                # if the previous number was smaller, it's a multiplier
                # e.g. the "two" in "two hundred"
                if sums[-1] < i:
                    sums[-1] = sums[-1] * i
                # otherwise, it's added on, like the "five" in "twenty five"
                else:
                    sums.append(i)
        elif i := _STR2INT_ADJS.get(word):
            # it's a special adj word; ordinal case will never be a multiplier
            sums.append(i)
        else:
            # invalid number-word, raise ValueError
            raise ValueError(f"String {original_input} cannot be converted to int.")
    return sum(sums)
