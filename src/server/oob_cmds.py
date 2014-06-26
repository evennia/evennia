"""
Out-of-band default plugin commands available for OOB handler.

This module implements commands as defined by the MSDP standard
(http://tintin.sourceforge.net/msdp/), but is independent of the
actual transfer protocol (webclient, MSDP, GMCP etc).

This module is pointed to by settings.OOB_PLUGIN_MODULES. All functions
(not classes) defined globally in this module will be made available
to the oob mechanism.

oob functions have the following call signature:
    function(oobhandler, session, *args, **kwargs)

where oobhandler is a back-reference to the central OOB_HANDLER
instance and session is the active session to get return data.

The function names are not case-sensitive (this allows for names
like "LIST" which would otherwise collide with Python builtins).

A function named _OOB_ERROR will retrieve error strings if it is
defined. It will get the error message as its 3rd argument.
"""

from django.conf import settings
_GA = object.__getattribute__
_SA = object.__setattr__
_NA_REPORT = lambda o: (None, "N/A")
_NA_SEND = lambda o: "N/A"

#------------------------------------------------------------
# All OOB commands must be on the form
#      cmdname(oobhandler, session, *args, **kwargs)
#------------------------------------------------------------

def _OOB_ERROR(oobhandler, session, errmsg, *args, **kwargs):
    """
    A function with this name is special and is called by the oobhandler when an error
    occurs already at the execution stage (such as the oob function
    not being recognized or having the wrong args etc).
    """
    session.msg(oob=("send", {"ERROR": errmsg}))


def ECHO(oobhandler, session, *args, **kwargs):
    "Test/debug function, simply returning the args and kwargs"
    session.msg(oob=("echo", args, kwargs))


def SEND(oobhandler, session, *args, **kwargs):
    """
    This function directly returns the value of the given variable to the
    session.
    """
    print "In SEND:", oobhandler, session, args
    obj = session.get_puppet_or_player()
    ret = {}
    if obj:
        for name in (a.upper() for a in args if a):
            try:
                value = OOB_SENDABLE.get(name, _NA_SEND)(obj)
                ret[name] = value
            except Exception, e:
                ret[name] = str(e)
    # return result
    session.msg(oob=("send", ret))


def REPORT(oobhandler, session, *args, **kwargs):
    """
    This creates a tracker instance to track the data given in *args.

    Note that the data name is assumed to be a field is it starts with db_*
    and an Attribute otherwise.

    "Example of tracking changes to the db_key field and the desc" Attribite:
        REPORT(oobhandler, session, "CHARACTER_NAME", )
    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            typ, val = OOB_REPORTABLE.get(name, _NA_REPORT)(obj)
            if typ == "field":
                oobhandler.track_field(obj, session.sessid, name)
            elif typ == "attribute":
                oobhandler.track_attribute(obj, session.sessid, name)


def UNREPORT(oobhandler, session, vartype="prop", *args, **kwargs):
    """
    This removes tracking for the given data given in *args.
    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            typ, val = OOB_REPORTABLE.get(name, _NA_REPORT)
            if typ == "field":
                oobhandler.untrack_field(obj, session.sessid, name)
            else:  # assume attribute
                oobhandler.untrack_attribute(obj, session.sessid, name)


def LIST(oobhandler, session, mode, *args, **kwargs):
    """
    List available properties. Mode is the type of information
    desired:
        "COMMANDS"               Request an array of commands supported
                                 by the server.
        "LISTS"                  Request an array of lists supported
                                 by the server.
        "CONFIGURABLE_VARIABLES" Request an array of variables the client
                                 can configure.
        "REPORTABLE_VARIABLES"   Request an array of variables the server
                                 will report.
        "REPORTED_VARIABLES"     Request an array of variables currently
                                 being reported.
        "SENDABLE_VARIABLES"     Request an array of variables the server
                                 will send.
    """
    mode = mode.upper()
    if mode == "COMMANDS":
        session.msg(oob=("list", ("COMMANDS",
                                  "LIST",
                                  "REPORT",
                                  "UNREPORT",
                                  # "RESET",
                                  "SEND")))
    elif mode == "LISTS":
        session.msg(oob=("list", ("LISTS",
                                  "REPORTABLE_VARIABLES",
                                  "REPORTED_VARIABLES",
                                  # "CONFIGURABLE_VARIABLES",
                                  "SENDABLE_VARIABLES")))
    elif mode == "REPORTABLE_VARIABLES":
        session.msg(oob=("list", ("REPORTABLE_VARIABLES",) +
                                  tuple(key for key in OOB_REPORTABLE.keys())))
    elif mode == "REPORTED_VARIABLES":
        session.msg(oob=("list", ("REPORTED_VARIABLES",) +
                                    tuple(oobhandler.get_all_tracked(session))))
    elif mode == "SENDABLE_VARIABLES":
        session.msg(oob=("list", ("SENDABLE_VARIABLES",) +
                                  tuple(key for key in OOB_REPORTABLE.keys())))
    #elif mode == "CONFIGURABLE_VARIABLES":
    #    pass
    else:
        session.msg(oob=("list", ("unsupported mode",)))


# Mapping for how to retrieve each property name.
# Each entry should point to a callable that gets the interesting object as
# input and returns the relevant value.

# MSDP recommends the following standard name mappings for general compliance:
# "CHARACTER_NAME", "SERVER_ID",  "SERVER_TIME", "AFFECTS", "ALIGNMENT", "EXPERIENCE", "EXPERIENCE_MAX", "EXPERIENCE_TNL",
# "HEALTH", "HEALTH_MAX", "LEVEL", "RACE", "CLASS", "MANA", "MANA_MAX", "WIMPY", "PRACTICE", "MONEY", "MOVEMENT",
# "MOVEMENT_MAX", "HITROLL", "DAMROLL", "AC", "STR", "INT", "WIS", "DEX", "CON", "OPPONENT_HEALTH", "OPPONENT_HEALTH_MAX",
# "OPPONENT_LEVEL", "OPPONENT_NAME", "AREA_NAME", "ROOM_EXITS", "ROOM_VNUM", "ROOM_NAME", "WORLD_TIME", "CLIENT_ID",
# "CLIENT_VERSION", "PLUGIN_ID", "ANSI_COLORS", "XTERM_256_COLORS", "UTF_8", "SOUND", "MXP", "BUTTON_1", "BUTTON_2",
# "BUTTON_3", "BUTTON_4", "BUTTON_5", "GAUGE_1", "GAUGE_2","GAUGE_3", "GAUGE_4", "GAUGE_5"

OOB_SENDABLE = {
        "CHARACTER_NAME": lambda o: o.key,
        "SERVER_ID": lambda o: settings.SERVERNAME,
        "ROOM_NAME": lambda o: o.db_location.key,
        "ANSI_COLORS": lambda o: True,
        "XTERM_256_COLORS": lambda o: True,
        "UTF_8": lambda o: True
    }

# mapping for which properties may be tracked. Each callable should return a tuple (type, value) where
# the type is one of "field" or "attribute" depending on what is being tracked.
OOB_REPORTABLE = {
        "CHARACTER_NAME": lambda o: ("field", o.key),
        "ROOM_NAME": lambda o: ("attribute", o.db_location.key)
        }
