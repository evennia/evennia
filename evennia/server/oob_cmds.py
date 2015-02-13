"""
Out-of-band default plugin commands available for OOB handler.

This module implements commands as defined by the MSDP standard
(http://tintin.sourceforge.net/msdp/), but is independent of the
actual transfer protocol (webclient, MSDP, GMCP etc). It also
implements several OOB commands unique to Evennia (both some
external and some for testing)

The available OOB commands can be extended by changing

    `settings.OOB_PLUGIN_MODULES`

This module must contain a global dictionary CMD_MAP. This is a
dictionary that maps the call available in the OOB call to a function
in this module (this allows you to map multiple oob cmdnames to a
single actual Python function, for example).

For example, if the OOB strings received looks like this:

    MDSP.LISTEN [desc, key]         # GMCP (wrapping to MSDP)
    LISTEN ARRAY VAL desc VAL key   # MSDP

and CMD_MAP = {"LISTEN", listen} then this would result in a call to a
function "listen" in this module, with the arguments *("desc", "key").

oob functions have the following call signature:

    function(oobhandler, session, *args, **kwargs)

where oobhandler is a back-reference to the central oob handler (this
allows for deactivating itself in various ways), session is the active
session and *args, **kwargs are what is sent from the oob call.

A function called with OOB_ERROR will retrieve error strings if it is
defined. It will get the error message as its 3rd argument.

    oob_error(oobhandler, session, error, *args, **kwargs)

This allows for customizing error handling.

Data is usually returned to the user via a return OOB call:

   session.msg(oob=(oobcmdname, (args,), {kwargs}))

Oobcmdnames (like "MSDP.LISTEN" / "LISTEN" above) are case-sensitive.
Note that args, kwargs must be iterable. Non-iterables will be
interpreted as a new command name (you can send multiple oob commands
with one msg() call))

Evennia introduces two internal extensions to MSDP, and that is the
MSDP_ARRAY and MSDP_TABLE commands. These are never sent across the
wire to the client (so this is fully compliant with the MSDP
protocol), but tells the Evennia OOB Protocol that you want to send a
"bare" array or table to the client, without prepending any command
name.

"""

from django.conf import settings
_GA = object.__getattribute__
_SA = object.__setattr__
_NA_SEND = lambda o: "N/A"


#------------------------------------------------------------
# All OOB commands must be on the form
#      cmdname(oobhandler, session, *args, **kwargs)
#------------------------------------------------------------

#
# General OOB commands
#

def oob_error(oobhandler, session, errmsg, *args, **kwargs):
    """
    Error handling method. Error messages are relayed here.

    Args:
        oobhandler (OOBHandler): The main OOB handler.
        session (Session): The session to receive the error
        errmsg (str): The failure message

    A function with this name is special and is also called by the
    oobhandler when an error occurs already at the execution stage
    (such as the oob function not being recognized or having the wrong
    args etc). Call this from other oob functions to centralize error
    management.

    """
    session.msg(oob=("err", ("ERROR " + errmsg,)))

def oob_echo(oobhandler, session, *args, **kwargs):
    """
    Test echo function. Echoes args, kwargs sent to it.

    Args:
        oobhandler (OOBHandler): The main OOB handler.
        session (Session): The Session to receive the echo.
        args (list of str): Echo text.
        kwargs (dict of str, optional): Keyed echo text

    """
    session.msg(oob=("echo", args, kwargs))

##OOB{"repeat":10}
def oob_repeat(oobhandler, session, oobfuncname, interval, *args, **kwargs):
    """
    Called as REPEAT <oobfunc> <interval>
    Repeats a given OOB command with a certain frequency.

    Args:
        oobhandler (OOBHandler): main OOB handler.
        session (Session): Session creating the repeat
        oobfuncname (str): OOB function called every interval seconds
        interval (int): Interval of repeat, in seconds.

    Notes:
        The command checks so that it cannot repeat itself.

    """
    if oobfuncname != "REPEAT":
        oobhandler.add_repeat(None, session.sessid, oobfuncname, interval, *args, **kwargs)


##OOB{"UNREPEAT":10}
def oob_unrepeat(oobhandler, session, oobfuncname, interval):
    """
    Called with UNREPEAT <oobfunc> <interval>
    Disable repeating callback.

    Args:
        oobhandler (OOBHandler): main OOB handler.
        session (Session): Session controlling the repeat
        oobfuncname (str): OOB function called every interval seconds
        interval (int): Interval of repeat, in seconds.

    Notes:
        The command checks so that it cannot repeat itself.


    """
    oobhandler.remove_repeat(None, session.sessid, oobfuncname, interval)


#
# MSDP protocol standard commands
#
# MSDP suggests the following standard name conventions for making
# different properties available to the player

# "CHARACTER_NAME", "SERVER_ID",  "SERVER_TIME", "AFFECTS", "ALIGNMENT", "EXPERIENCE", "EXPERIENCE_MAX", "EXPERIENCE_TNL",
# "HEALTH", "HEALTH_MAX", "LEVEL", "RACE", "CLASS", "MANA", "MANA_MAX", "WIMPY", "PRACTICE", "MONEY", "MOVEMENT",
# "MOVEMENT_MAX", "HITROLL", "DAMROLL", "AC", "STR", "INT", "WIS", "DEX", "CON", "OPPONENT_HEALTH", "OPPONENT_HEALTH_MAX",
# "OPPONENT_LEVEL", "OPPONENT_NAME", "AREA_NAME", "ROOM_EXITS", "ROOM_VNUM", "ROOM_NAME", "WORLD_TIME", "CLIENT_ID",
# "CLIENT_VERSION", "PLUGIN_ID", "ANSI_COLORS", "XTERM_256_COLORS", "UTF_8", "SOUND", "MXP", "BUTTON_1", "BUTTON_2",
# "BUTTON_3", "BUTTON_4", "BUTTON_5", "GAUGE_1", "GAUGE_2","GAUGE_3", "GAUGE_4", "GAUGE_5"


# mapping from MSDP standard names to Evennia variables
OOB_SENDABLE = {
        "CHARACTER_NAME": lambda o: o.key,
        "SERVER_ID": lambda o: settings.SERVERNAME,
        "ROOM_NAME": lambda o: o.db_location.key,
        "ANSI_COLORS": lambda o: True,
        "XTERM_256_COLORS": lambda o: True,
        "UTF_8": lambda o: True
    }


##OOB{"SEND":"CHARACTER_NAME"} - from webclient
def oob_send(oobhandler, session, *args, **kwargs):
    """
    Called with the SEND MSDP command.
    This function directly returns the value of the given variable to
    the session. It assumes the object on which the variable sits
    belongs to the session.

    Args:
        oobhandler (OOBHandler): oobhandler reference
        session (Session): Session object
        args (str): any number of properties to return. These
            must belong to the OOB_SENDABLE dictionary.
    Examples:
        oob input: ("SEND", "CHARACTER_NAME", "SERVERNAME")
        oob output: ("MSDP_TABLE", "CHARACTER_NAME", "Amanda",
                     "SERVERNAME", "Evennia")

    """
    # mapping of MSDP name to a property
    obj = session.get_puppet_or_player()
    ret = {}
    if obj:
        for name in (a.upper() for a in args if a):
            try:
                print "MSDP SEND inp:", name
                value = OOB_SENDABLE.get(name, _NA_SEND)(obj)
                ret[name] = value
            except Exception, e:
                ret[name] = str(e)
        # return, make sure to use the right case
        session.msg(oob=("MSDP_TABLE", (), ret))
    else:
        session.msg(oob=("err", ("You must log in first.",)))


# mapping standard MSDP keys to Evennia field names
OOB_REPORTABLE = {
        "CHARACTER_NAME": "db_key",
        "ROOM_NAME": "db_location",
        "TEST" : "test"
        }

##OOB{"REPORT":"TEST"}
def oob_report(oobhandler, session, *args, **kwargs):
    """
    Called with the `REPORT PROPNAME` MSDP command.
    Monitors the changes of given property name. Assumes reporting
    happens on an objcet controlled by the session.

    Args:
        oobhandler (OOBHandler): The main OOB handler
        session (Session): The Session doing the monitoring. The
            property is assumed to sit on the entity currently
            controlled by the Session. If puppeting, this is an
            Object, otherwise the object will be the Player the
            Session belongs to.
        args (str or list): One or more property names to monitor changes in.
            If a name starts with `db_`, the property is assumed to
            be a field, otherwise an Attribute of the given name will
            be monitored (if it exists).

    Notes:
        When the property updates, the monitor will send a MSDP_ARRAY
        to the session of the form `(SEND, fieldname, new_value)`
    Examples:
        ("REPORT", "CHARACTER_NAME")
        ("MSDP_TABLE", "CHARACTER_NAME", "Amanda")

    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in args:
            propname = OOB_REPORTABLE.get(name, None)
            if not propname:
                session.msg(oob=("err", ("No Reportable property '%s'. Use LIST REPORTABLE_VARIABLES." % propname,)))
            # the field_monitors require an oob function as a callback when they report a change.
            elif propname.startswith("db_"):
                oobhandler.add_field_monitor(obj, session.sessid, propname, "return_field_report")
            else:
                oobhandler.add_attribute_monitor(obj, session.sessid, propname, "return_attribute_report")
    else:
        session.msg(oob=("err", ("You must log in first.",)))


def oob_return_field_report(oobhandler, session, fieldname, obj, *args, **kwargs):
    """
    This is a helper command called by the monitor when fieldname
    changes. It is not part of the official MSDP specification but is
    a callback used by the monitor to format the result before sending
    it on.
    """
    session.msg(oob=("MSDP_TABLE", (), {fieldname, getattr(obj, fieldname)}))


def oob_return_attribute_report(oobhandler, session, fieldname, obj, *args, **kwargs):
    """
    This is a helper command called by the monitor when an Attribute
    changes. We need to handle this a little differently from fields
    since we are generally not interested in the field  name (it's
    always db_value for Attributes) but the Attribute's name.

    This command is not part of the official MSDP specification but is
    a callback used by the monitor to format the result before sending
    it on.
    """
    session.msg(oob=("MSDP_TABLE", (), {obj.db_key, getattr(obj, fieldname)}))


##OOB{"UNREPORT": "TEST"}
def oob_unreport(oobhandler, session, *args, **kwargs):
    """
    This removes tracking for the given data.
    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            propname = OOB_REPORTABLE.get(name, None)
            if not propname:
                session.msg(oob=("err", ("No Un-Reportable property '%s'. Use LIST REPORTED_VALUES." % name,)))
            elif propname.startswith("db_"):
                oobhandler.remove_field_monitor(obj, session.sessid, propname, "oob_return_field_report")
            else:  # assume attribute
                oobhandler.remove_attribute_monitor(obj, session.sessid, propname, "oob_return_attribute_report")
    else:
        session.msg(oob=("err", ("You must log in first.",)))


##OOB{"LIST":"COMMANDS"}
def oob_list(oobhandler, session, mode, *args, **kwargs):
    """
    Called with the `LIST <MODE>`  MSDP command.

    Args:
        oobhandler (OOBHandler): The main OOB handler
        session (Session): The Session asking for the information
        mode (str): The available properties. One of
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
    Examples:
        oob in: LIST COMMANDS
        oob out: (COMMANDS, (SEND, REPORT, LIST, ...)
    """
    mode = mode.upper()
    if mode == "COMMANDS":
        session.msg(oob=("COMMANDS", ("LIST",
                                     "REPORT",
                                     "UNREPORT",
                                     # "RESET",
                                     "SEND")))
    elif mode == "LISTS":
        session.msg(oob=("LISTS",("REPORTABLE_VARIABLES",
                                  "REPORTED_VARIABLES",
                                  # "CONFIGURABLE_VARIABLES",
                                  "SENDABLE_VARIABLES")))
    elif mode == "REPORTABLE_VARIABLES":
        session.msg(oob=("REPORTABLE_VARIABLES", tuple(key for key in OOB_REPORTABLE.keys())))
    elif mode == "REPORTED_VARIABLES":
        # we need to check so as to use the right return value depending on if it is
        # an Attribute (identified by tracking the db_value field) or a normal database field
        # reported is a list of tuples (obj, propname, args, kwargs)
        reported = oobhandler.get_all_monitors(session.sessid)
        reported = [rep[0].key if rep[1] == "db_value" else rep[1] for rep in reported]
        session.msg(oob=("REPORTED_VARIABLES", reported))
    elif mode == "SENDABLE_VARIABLES":
        session.msg(oob=("SENDABLE_VARIABLES", tuple(key for key in OOB_REPORTABLE.keys())))
    elif mode == "CONFIGURABLE_VARIABLES":
        # Not implemented (game specific)
        session.msg(oob=("err", ("LIST", "Not implemented (game specific).")))
    else:
        session.msg(oob=("err", ("LIST", "Unsupported mode",)))


#
# Cmd mapping
#

# this maps the commands to the names available to use from
# the oob call. The standard MSDP commands are capitalized
# as per the protocol, Evennia's own commands are not.
CMD_MAP = {"oob_error": oob_error, # will get error messages
           "return_field_report": oob_return_field_report,
           "return_attribute_report": oob_return_attribute_report,
           "repeat": oob_repeat,
           "unrepeat": oob_unrepeat,
           "SEND": oob_send,
           "ECHO": oob_echo,
           "REPORT": oob_report,
           "UNREPORT": oob_unreport,
           "LIST": oob_list
           }

