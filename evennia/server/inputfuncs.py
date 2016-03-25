"""
Functions for processing input commands.

All global functions in this module whose name does not start with "_"
is considered an inputfunc. Each function must have the following
callsign:

    inputfunc(session, *args, **kwargs)

There is one special function, the "default" function, which is called
on a no-match. It has this callsign:

    default(session, cmdname, *args, **kwargs)

Evennia knows which modules to use for inputfuncs by
settings.INPUT_FUNC_MODULES.

"""
from future.utils import viewkeys

from django.conf import settings
from evennia.commands.cmdhandler import cmdhandler
from evennia.utils.logger import log_err
from evennia.utils.utils import to_str


_IDLE_COMMAND = settings.IDLE_COMMAND
_GA = object.__getattribute__
_SA = object.__setattr__
_NA = lambda o: "N/A"

_ERROR_INPUT = "Inputfunc {name}({session}): Wrong/unrecognized input: {inp}"


# All global functions are inputfuncs available to process inputs

def text(session, *args, **kwargs):
    """
    Main text input from the client. This will execute a command
    string on the server.

    Args:
        text (str): First arg is used as text-command input. Other
            arguments are ignored.

    """
    #from evennia.server.profiling.timetrace import timetrace
    #text = timetrace(text, "ServerSession.data_in")

    text = args[0] if args else None

    #explicitly check for None since text can be an empty string, which is
    #also valid
    if text is None:
        return
    # this is treated as a command input
    # handle the 'idle' command
    if text.strip() == _IDLE_COMMAND:
        session.update_session_counters(idle=True)
        return
    if session.player:
        # nick replacement
        puppet = session.puppet
        if puppet:
            text = puppet.nicks.nickreplace(text,
                          categories=("inputline", "channel"), include_player=True)
        else:
            text = session.player.nicks.nickreplace(text,
                        categories=("inputline", "channels"), include_player=False)
    cmdhandler(session, text, callertype="session", session=session)
    session.update_session_counters()


def echo(session, *args, **kwargs):
    """
    Echo test function
    """
    print "Inputfunc echo:", session, args, kwargs
    session.data_out(text="Echo returns: ")
    session.data_out(echo=(args, kwargs))


def default(session, cmdname, *args, **kwargs):
    """
    Default catch-function. This is like all other input functions except
    it will get `cmdname` as the first argument.

    """
    err = "Session {sessid}: Input command not recognized:\n" \
            " name: '{cmdname}'\n" \
            " args, kwargs: {args}, {kwargs}"
    log_err(err.format(sessid=session.sessid, cmdname=cmdname, args=args, kwargs=kwargs))


def client_options(session, *args, **kwargs):
    """
    This allows the client an OOB way to inform us about its name and capabilities.
    This will be integrated into the session settings

    Kwargs:
        get (bool): If this is true, return the settings as a dict
            (ignore all other kwargs).
        client (str): A client identifier, like "mushclient".
        version (str): A client version
        ansi (bool): Supports ansi colors
        xterm256 (bool): Supports xterm256 colors or not
        mxp (bool): Supports MXP or not
        utf-8 (bool): Supports UTF-8 or not
        screenreader (bool): Screen-reader mode on/off
        mccp (bool): MCCP compression on/off
        screenheight (int): Screen height in lines
        screenwidth (int): Screen width in characters

    """
    flags = session.protocol_flags
    if kwargs.get("get", False):
        # return current settings
        options = dict((key, flags[key]) for key in flags
                if key in ("ANSI", "XTERM256", "MXP",
                           "UTF-8", "SCREENREADER",
                           "MCCP", "SCREENHEIGHT",
                           "SCREENWIDTH"))
        session.msg(client_options=options)
        return

    for key, value in kwargs.iteritems():
        key = key.lower()
        if key == "client":
            flags["CLIENTNAME"] = to_str(value)
        elif key == "version":
            if "CLIENTNAME" in flags:
                flags["CLIENTNAME"] = "%s %s" % (flags["CLIENTNAME"], to_str(value))
        elif key == "ansi":
            flags["ANSI"] = bool(value)
        elif key == "xterm256":
            flags["XTERM256"] = bool(value)
        elif key == "mxp":
            flags["MXP"] = bool(value)
        elif key == "utf-8":
            flags["UTF-8"] = bool(value)
        elif key == "screenreader":
            flags["SCREENREADER"] = bool(value)
        elif key == "mccp":
            flags["MCCP"] = bool(value)
        elif key == "screenheight":
            flags["SCREENHEIGHT"] = int(value)
        elif key == "screenwidth":
            flags["SCREENWIDTH"] = int(value)
        elif not key == "options":
            err = _ERROR_INPUT.format(
                    name="client_settings", session=session, inp=key)
            session.msg(text=err)
    session.protocol_flags = flags
    # we must update the portal as well
    session.sessionhandler.session_portal_sync(session)


def get_client_options(session, *args, **kwargs):
    """
    Alias wrapper for getting options
    """
    client_options(session, get=True)


def login(session, *args, **kwargs):
    """
    Peform a login. This only works if session is currently not logged
    in. This will also automatically throttle too quick attempts.

    Kwargs:
        name (str): Player name
        password (str): Plain-text password

    """
    if not session.logged_in and "name" in kwargs and "password" in kwargs:
        from evennia.commands.default.unloggedin import create_normal_player
        player = create_normal_player(session, kwargs["name"], kwargs["password"])
        if player:
            session.sessionhandler.login(session, player)


def get_value(session, *args, **kwargs):
    """
    Return the value of a given attribute or db_property on the
    session's current player or character.

    Kwargs:

    """



def repeat(session, *args, **kwargs):
    """
    Call a named
    """



# aliases for GMCP
core_hello = client_options             # Core.Hello
core_supports_set = client_options      # Core.Supports.Set
core_supports_get = get_client_options  # Core.Supports.Get
char_login = login                      # Char.Login


#------------------------------------------------------------------------------------





##OOB{"repeat":10}
def oob_repeat(session, oobfuncname, interval, *args, **kwargs):
    """
    Called as REPEAT <oobfunc> <interval> <args>
    Repeats a given OOB command with a certain frequency.

    Args:
        session (Session): Session creating the repeat
        oobfuncname (str): OOB function called every interval seconds
        interval (int): Interval of repeat, in seconds.

    Notes:
        The command checks so that it cannot repeat itself.

    """
    if not oobfuncname:
        oob_error(session, "Usage: REPEAT <oobfuncname>, <interval>")
        return
    # limit repeat actions to minimum 5 seconds interval
    interval = 20 if not interval else (max(5, interval))
    obj = session.get_puppet_or_player()
    if obj and oobfuncname != "REPEAT":
        INPUT_HANDLER.add_repeater(obj, session, oobfuncname, interval, *args, **kwargs)


##OOB{"UNREPEAT":10}
def oob_unrepeat(session, oobfuncname, interval):
    """
    Called with UNREPEAT <oobfunc> <interval>
    Disable repeating callback.

    Args:
        session (Session): Session controlling the repeater
        oobfuncname (str): OOB function called every interval seconds
        interval (int): Interval of repeater, in seconds.

    Notes:
        The command checks so that it cannot repeat itself.


    """
    obj = session.get_puppet_or_player()
    if obj:
        INPUT_HANDLER.remove_repeater(obj, session, oobfuncname, interval)


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
_OOB_SENDABLE = {
        "CHARACTER_NAME": lambda o: o.key,
        "SERVER_ID": lambda o: settings.SERVERNAME,
        "ROOM_NAME": lambda o: o.db_location.key,
        "ANSI_COLORS": lambda o: True,
        "XTERM_256_COLORS": lambda o: True,
        "UTF_8": lambda o: True
    }


##OOB{"SEND":"CHARACTER_NAME"} - from webclient
def oob_send(session, *args, **kwargs):
    """
    Called with the SEND MSDP command.
    This function directly returns the value of the given variable to
    the session. It assumes the object on which the variable sits
    belongs to the session.

    Args:
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
                value = OOB_SENDABLE.get(name, _NA)(obj)
                ret[name] = value
            except Exception as e:
                ret[name] = str(e)
        # return, make sure to use the right case
        session.msg(oob=("MSDP_TABLE", (), ret))
    else:
        oob_error(session, "You must log in first.")


# mapping standard MSDP keys to Evennia field names
_OOB_REPORTABLE = {
        "CHARACTER_NAME": "db_key",
        "ROOM_NAME": "db_location",
        "TEST" : "test"
        }

##OOB{"REPORT":"TEST"}
def oob_report(session, *args, **kwargs):
    """
    Called with the `REPORT PROPNAME` MSDP command.
    Monitors the changes of given property name. Assumes reporting
    happens on an object controlled by the session.

    Args:
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
        ret = []
        for name in args:
            propname = OOB_REPORTABLE.get(name, None)
            if not propname:
                oob_error(session, "No Reportable property '%s'. Use LIST REPORTABLE_VARIABLES." % propname)
            # the field_monitors require an oob function as a callback when they report a change.
            elif propname.startswith("db_"):
                INPUT_HANDLER.add_field_monitor(obj, session, propname, "return_field_report")
                ret.append(to_str(_GA(obj, propname), force_string=True))
            else:
                INPUT_HANDLER.add_attribute_monitor(obj, session, propname, "return_attribute_report")
                ret.append(_GA(obj, "db_value"))
        session.msg(oob=("MSDP_ARRAY", ret))
    else:
        oob_error(session, "You must log in first.")


def oob_return_field_report(session, fieldname, obj, *args, **kwargs):
    """
    This is a helper command called by the monitor when fieldname
    changes. It is not part of the official MSDP specification but is
    a callback used by the monitor to format the result before sending
    it on.

    Args:
        session (Session): The Session object controlling this oob function.
        fieldname (str): The name of the Field to report on.

    """
    session.msg(oob=("MSDP_TABLE", (),
                     {fieldname: to_str(getattr(obj, fieldname), force_string=True)}))


def oob_return_attribute_report(session, fieldname, obj, *args, **kwargs):
    """
    This is a helper command called by the monitor when an Attribute
    changes. We need to handle this a little differently from fields
    since we are generally not interested in the field  name (it's
    always db_value for Attributes) but the Attribute's name.

    This command is not part of the official MSDP specification but is
    a callback used by the monitor to format the result before sending
    it on.

    Args:
        session (Session): The Session object controlling this oob function.
        fieldname (str): The name of the Attribute to report on.

    """
    session.msg(oob=("MSDP_TABLE", (),
                     {obj.db_key: to_str(getattr(obj, fieldname), force_string=True)}))


##OOB{"UNREPORT": "TEST"}
def oob_unreport(session, *args, **kwargs):
    """
    This removes tracking for the given data.

    Args:
        session (Session): Session controling this command.

    """
    obj = session.get_puppet_or_player()
    if obj:
        for name in (a.upper() for a in args if a):
            propname = OOB_REPORTABLE.get(name, None)
            if not propname:
                oob_error(session, "No Un-Reportable property '%s'. Use LIST REPORTABLE_VARIABLES." % propname)
            elif propname.startswith("db_"):
                INPUT_HANDLER.remove_field_monitor(obj, session, propname, "oob_return_field_report")
            else:  # assume attribute
                INPUT_HANDLER.remove_attribute_monitor(obj, session, propname, "oob_return_attribute_report")
    else:
        oob_error(session, "You must log in first.")


##OOB{"LIST":"COMMANDS"}
def oob_list(session, mode, *args, **kwargs):
    """
    Called with the `LIST <MODE>`  MSDP command.

    Args:
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
    elif mode == "REPORTABLE_VARIABLES":
        session.msg(oob=("REPORTABLE_VARIABLES", tuple(key for key in viewkeys(OOB_REPORTABLE))))
    elif mode == "REPORTED_VARIABLES":
        # we need to check so as to use the right return value depending on if it is
        # an Attribute (identified by tracking the db_value field) or a normal database field
        # reported is a list of tuples (obj, propname, args, kwargs)
        reported = INPUT_HANDLER.get_all_monitors(session)
        reported = [rep[0].key if rep[1] == "db_value" else rep[1] for rep in reported]
        session.msg(oob=("REPORTED_VARIABLES", reported))
    elif mode == "SENDABLE_VARIABLES":
        session.msg(oob=("SENDABLE_VARIABLES", tuple(key for key in viewkeys(OOB_REPORTABLE))))
    elif mode == "CONFIGURABLE_VARIABLES":
        # Not implemented (game specific)
        oob_error(session, "Not implemented (game specific)")
    else:
        # mode == "LISTS" or not given
        session.msg(oob=("LISTS",("REPORTABLE_VARIABLES",
                                  "REPORTED_VARIABLES",
                                  # "CONFIGURABLE_VARIABLES",
                                  "SENDABLE_VARIABLES")))

#
# Cmd mapping
#

# this maps the commands to the names available to use from
# the oob call. The standard MSDP commands are capitalized
# as per the protocol, Evennia's own commands are not.
#CMD_MAP = {"oob_error": oob_error, # will get error messages
#           "return_field_report": oob_return_field_report,
#           "return_attribute_report": oob_return_attribute_report,
#           # MSDP
#           "REPEAT": oob_repeat,
#           "UNREPEAT": oob_unrepeat,
#           "SEND": oob_send,
#           "ECHO": oob_echo,
#           "REPORT": oob_report,
#           "UNREPORT": oob_unreport,
#           "LIST": oob_list,
#           # GMCP
#           }

