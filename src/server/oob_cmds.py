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

A function named OOB_ERROR will retrieve error strings if it is
defined. It will get the error message as its 3rd argument.

Data is usually returned via
  session.msg(oob=(cmdname, (args,), {kwargs}))
Note that args, kwargs must be iterable/dict, non-iterables will
be interpreted as a new command name.

"""

from django.conf import settings
_GA = object.__getattribute__
_SA = object.__setattr__
_NA_SEND = lambda o: "N/A"

#------------------------------------------------------------
# All OOB commands must be on the form
#      cmdname(oobhandler, session, *args, **kwargs)
#------------------------------------------------------------

def OOB_ERROR(oobhandler, session, errmsg, *args, **kwargs):
    """
    A function with this name is special and is called by the oobhandler when an error
    occurs already at the execution stage (such as the oob function
    not being recognized or having the wrong args etc).
    """
    session.msg(oob=("err", ("ERROR " + errmsg,)))


def ECHO(oobhandler, session, *args, **kwargs):
    "Test/debug function, simply returning the args and kwargs"
    session.msg(oob=("echo", args, kwargs))

##OOB{"SEND":"CHARACTER_NAME"}
def SEND(oobhandler, session, *args, **kwargs):
    """
    This function directly returns the value of the given variable to the
    session.
    """
    obj = session.get_puppet_or_player()
    ret = {}
    if obj:
        for name in (a.upper() for a in args if a):
            try:
                value = OOB_SENDABLE.get(name, _NA_SEND)(obj)
                ret[name] = value
            except Exception, e:
                ret[name] = str(e)
        session.msg(oob=("send", ret))
    else:
        session.msg(oob=("err", ("You must log in first.",)))

##OOB{"REPORT":"TEST"}
def REPORT(oobhandler, session, *args, **kwargs):
    """
    This creates a tracker instance to track the data given in *args.

    The tracker will return with a oob structure
        oob={"report":["attrfieldname", (args,), {kwargs}}

    Note that the data name is assumed to be a field is it starts with db_*
    and an Attribute otherwise.

    "Example of tracking changes to the db_key field and the desc" Attribite:
        REPORT(oobhandler, session, "CHARACTER_NAME", )
    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            trackname = OOB_REPORTABLE.get(name, None)
            if not trackname:
                session.msg(oob=("err", ("No Reportable property '%s'. Use LIST REPORTABLE_VARIABLES." % trackname,)))
            elif trackname.startswith("db_"):
                oobhandler.track_field(obj, session.sessid, trackname)
            else:
                oobhandler.track_attribute(obj, session.sessid, trackname)
    else:
        session.msg(oob=("err", ("You must log in first.",)))


##OOB{"UNREPORT": "TEST"}
def UNREPORT(oobhandler, session, *args, **kwargs):
    """
    This removes tracking for the given data given in *args.
    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            trackname = OOB_REPORTABLE.get(name, None)
            if not trackname:
                session.msg(oob=("err", ("No Un-Reportable property '%s'. Use LIST REPORTED_VALUES." % name,)))
            elif trackname.startswith("db_"):
                oobhandler.untrack_field(obj, session.sessid, trackname)
            else:  # assume attribute
                oobhandler.untrack_attribute(obj, session.sessid, trackname)
    else:
        session.msg(oob=("err", ("You must log in first.",)))


##OOB{"LIST":"COMMANDS"}
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
        # we need to check so as to use the right return value depending on if it is
        # an Attribute (identified by tracking the db_value field) or a normal database field
        reported = oobhandler.get_all_tracked(session)
        reported = [stored[2] if stored[2] != "db_value" else stored[4][0] for stored in reported]
        session.msg(oob=("list", ["REPORTED_VARIABLES"] + reported))
    elif mode == "SENDABLE_VARIABLES":
        session.msg(oob=("list", ("SENDABLE_VARIABLES",) +
                                  tuple(key for key in OOB_REPORTABLE.keys())))
    elif mode == "CONFIGURABLE_VARIABLES":
        # Not implemented (game specific)
        pass
    else:
        session.msg(oob=("err", ("LIST", "Unsupported mode",)))

def _repeat_callback(oobhandler, session, *args, **kwargs):
    "Set up by REPEAT"
    session.msg(oob=("repeat", ("Repeat!",)))

##OOB{"REPEAT":10}
def REPEAT(oobhandler, session, interval, *args, **kwargs):
    """
    Test command for the repeat functionality. Note that the args/kwargs
    must not be db objects (or anything else non-picklable), rather use
    dbrefs if so needed. The callback must be defined globally and
    will be called as
       callback(oobhandler, session, *args, **kwargs)
    """
    oobhandler.repeat(None, session.sessid, interval, _repeat_callback, *args, **kwargs)


##OOB{"UNREPEAT":10}
def UNREPEAT(oobhandler, session, interval):
    """
    Disable repeating callback
    """
    oobhandler.unrepeat(None, session.sessid, interval)


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

# mapping for which properties may be tracked. Each value points either to a database field
# (starting with db_*) or an Attribute name.
OOB_REPORTABLE = {
        "CHARACTER_NAME": "db_key",
        "ROOM_NAME": "db_location",
        "TEST" : "test"
        }
