"""
Functions for processing input commands.

All global functions in this module whose name does not start with "_"
is considered an inputfunc. Each function must have the following
callsign (where inputfunc name is always lower-case, no matter what the
OOB input name looked like):

    inputfunc(session, *args, **kwargs)

Where "options" is always one of the kwargs, containing eventual
protocol-options.
There is one special function, the "default" function, which is called
on a no-match. It has this callsign:

    default(session, cmdname, *args, **kwargs)

Evennia knows which modules to use for inputfuncs by
settings.INPUT_FUNC_MODULES.

"""

import importlib
from codecs import lookup as codecs_lookup
from django.conf import settings
from evennia.commands.cmdhandler import cmdhandler
from evennia.accounts.models import AccountDB
from evennia.utils.logger import log_err
from evennia.utils.utils import to_str

BrowserSessionStore = importlib.import_module(settings.SESSION_ENGINE).SessionStore


# always let "idle" work since we use this in the webclient
_IDLE_COMMAND = settings.IDLE_COMMAND
_IDLE_COMMAND = (_IDLE_COMMAND,) if _IDLE_COMMAND == "idle" else (_IDLE_COMMAND, "idle")
_GA = object.__getattribute__
_SA = object.__setattr__


def _NA(o):
    return "N/A"


_ERROR_INPUT = "Inputfunc {name}({session}): Wrong/unrecognized input: {inp}"


# All global functions are inputfuncs available to process inputs


def text(session, *args, **kwargs):
    """
    Main text input from the client. This will execute a command
    string on the server.

    Args:
        session (Session): The active Session to receive the input.
        text (str): First arg is used as text-command input. Other
            arguments are ignored.

    """
    # from evennia.server.profiling.timetrace import timetrace
    # text = timetrace(text, "ServerSession.data_in")

    txt = args[0] if args else None

    # explicitly check for None since text can be an empty string, which is
    # also valid
    if txt is None:
        return
    # this is treated as a command input
    # handle the 'idle' command
    if txt.strip() in _IDLE_COMMAND:
        session.update_session_counters(idle=True)
        return
    if session.account:
        # nick replacement
        puppet = session.puppet
        if puppet:
            txt = puppet.nicks.nickreplace(
                txt, categories=("inputline", "channel"), include_account=True
            )
        else:
            txt = session.account.nicks.nickreplace(
                txt, categories=("inputline", "channel"), include_account=False
            )
    kwargs.pop("options", None)
    cmdhandler(session, txt, callertype="session", session=session, **kwargs)
    session.update_session_counters()


def bot_data_in(session, *args, **kwargs):
    """
    Text input from the IRC and RSS bots.
    This will trigger the execute_cmd method on the bots in-game counterpart.

    Args:
        session (Session): The active Session to receive the input.
        text (str): First arg is text input. Other arguments are ignored.

    """

    txt = args[0] if args else None

    # Explicitly check for None since text can be an empty string, which is
    # also valid
    if txt is None:
        return
    # this is treated as a command input
    # handle the 'idle' command
    if txt.strip() in _IDLE_COMMAND:
        session.update_session_counters(idle=True)
        return
    kwargs.pop("options", None)
    # Trigger the execute_cmd method of the corresponding bot.
    session.account.execute_cmd(session=session, txt=txt, **kwargs)
    session.update_session_counters()


def echo(session, *args, **kwargs):
    """
    Echo test function
    """
    session.data_out(text="Echo returns: %s" % args)


def default(session, cmdname, *args, **kwargs):
    """
    Default catch-function. This is like all other input functions except
    it will get `cmdname` as the first argument.

    """
    err = (
        "Session {sessid}: Input command not recognized:\n"
        " name: '{cmdname}'\n"
        " args, kwargs: {args}, {kwargs}".format(
            sessid=session.sessid, cmdname=cmdname, args=args, kwargs=kwargs
        )
    )
    if session.protocol_flags.get("INPUTDEBUG", False):
        session.msg(err)
    log_err(err)


_CLIENT_OPTIONS = (
    "ANSI",
    "XTERM256",
    "MXP",
    "UTF-8",
    "SCREENREADER",
    "ENCODING",
    "MCCP",
    "SCREENHEIGHT",
    "SCREENWIDTH",
    "INPUTDEBUG",
    "RAW",
    "NOCOLOR",
    "NOGOAHEAD",
)


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
        inputdebug (bool): Debug input functions
        nocolor (bool): Strip color
        raw (bool): Turn off parsing

    """
    old_flags = session.protocol_flags
    if not kwargs or kwargs.get("get", False):
        # return current settings
        options = dict((key, old_flags[key]) for key in old_flags if key.upper() in _CLIENT_OPTIONS)
        session.msg(client_options=options)
        return

    def validate_encoding(val):
        # helper: change encoding
        try:
            codecs_lookup(val)
        except LookupError:
            raise RuntimeError("The encoding '|w%s|n' is invalid. " % val)
        return val

    def validate_size(val):
        return {0: int(val)}

    def validate_bool(val):
        if isinstance(val, str):
            return True if val.lower() in ("true", "on", "1") else False
        return bool(val)

    flags = {}
    for key, value in kwargs.items():
        key = key.lower()
        if key == "client":
            flags["CLIENTNAME"] = to_str(value)
        elif key == "version":
            if "CLIENTNAME" in flags:
                flags["CLIENTNAME"] = "%s %s" % (flags["CLIENTNAME"], to_str(value))
        elif key == "ENCODING":
            flags["ENCODING"] = validate_encoding(value)
        elif key == "ansi":
            flags["ANSI"] = validate_bool(value)
        elif key == "xterm256":
            flags["XTERM256"] = validate_bool(value)
        elif key == "mxp":
            flags["MXP"] = validate_bool(value)
        elif key == "utf-8":
            flags["UTF-8"] = validate_bool(value)
        elif key == "screenreader":
            flags["SCREENREADER"] = validate_bool(value)
        elif key == "mccp":
            flags["MCCP"] = validate_bool(value)
        elif key == "screenheight":
            flags["SCREENHEIGHT"] = validate_size(value)
        elif key == "screenwidth":
            flags["SCREENWIDTH"] = validate_size(value)
        elif key == "inputdebug":
            flags["INPUTDEBUG"] = validate_bool(value)
        elif key == "nocolor":
            flags["NOCOLOR"] = validate_bool(value)
        elif key == "raw":
            flags["RAW"] = validate_bool(value)
        elif key == "nogoahead":
            flags["NOGOAHEAD"] = validate_bool(value)
        elif key in (
            "Char 1",
            "Char.Skills 1",
            "Char.Items 1",
            "Room 1",
            "IRE.Rift 1",
            "IRE.Composer 1",
        ):
            # ignore mudlet's default send (aimed at IRE games)
            pass
        elif key not in ("options", "cmdid"):
            err = _ERROR_INPUT.format(name="client_settings", session=session, inp=key)
            session.msg(text=err)

    session.protocol_flags.update(flags)
    # we must update the protocol flags on the portal session copy as well
    session.sessionhandler.session_portal_partial_sync({session.sessid: {"protocol_flags": flags}})


def get_client_options(session, *args, **kwargs):
    """
    Alias wrapper for getting options.
    """
    client_options(session, get=True)


def get_inputfuncs(session, *args, **kwargs):
    """
    Get the keys of all available inputfuncs. Note that we don't get
    it from this module alone since multiple modules could be added.
    So we get it from the sessionhandler.
    """
    inputfuncsdict = dict(
        (key, func.__doc__) for key, func in session.sessionhandler.get_inputfuncs().items()
    )
    session.msg(get_inputfuncs=inputfuncsdict)


def login(session, *args, **kwargs):
    """
    Peform a login. This only works if session is currently not logged
    in. This will also automatically throttle too quick attempts.

    Kwargs:
        name (str): Account name
        password (str): Plain-text password

    """
    if not session.logged_in and "name" in kwargs and "password" in kwargs:
        from evennia.commands.default.unloggedin import create_normal_account

        account = create_normal_account(session, kwargs["name"], kwargs["password"])
        if account:
            session.sessionhandler.login(session, account)


_gettable = {
    "name": lambda obj: obj.key,
    "key": lambda obj: obj.key,
    "location": lambda obj: obj.location.key if obj.location else "None",
    "servername": lambda obj: settings.SERVERNAME,
}


def get_value(session, *args, **kwargs):
    """
    Return the value of a given attribute or db_property on the
    session's current account or character.

    Kwargs:
      name (str): Name of info value to return. Only names
        in the _gettable dictionary earlier in this module
        are accepted.

    """
    name = kwargs.get("name", "")
    obj = session.puppet or session.account
    if name in _gettable:
        session.msg(get_value={"name": name, "value": _gettable[name](obj)})


def _testrepeat(**kwargs):
    """
    This is a test function for using with the repeat
    inputfunc.

    Kwargs:
        session (Session): Session to return to.
    """
    import time

    kwargs["session"].msg(repeat="Repeat called: %s" % time.time())


_repeatable = {"test1": _testrepeat, "test2": _testrepeat}  # example only  # "


def repeat(session, *args, **kwargs):
    """
    Call a named function repeatedly. Note that
    this is meant as an example of limiting the number of
    possible call functions.

    Kwargs:
        callback (str): The function to call. Only functions
            from the _repeatable dictionary earlier in this
            module are available.
        interval (int): How often to call function (s).
            Defaults to once every 60 seconds with a minimum
                of 5 seconds.
        stop (bool): Stop a previously assigned ticker with
            the above settings.

    """
    from evennia.scripts.tickerhandler import TICKER_HANDLER

    name = kwargs.get("callback", "")
    interval = max(5, int(kwargs.get("interval", 60)))

    if name in _repeatable:
        if kwargs.get("stop", False):
            TICKER_HANDLER.remove(
                interval, _repeatable[name], idstring=session.sessid, persistent=False
            )
        else:
            TICKER_HANDLER.add(
                interval,
                _repeatable[name],
                idstring=session.sessid,
                persistent=False,
                session=session,
            )
    else:
        session.msg("Allowed repeating functions are: %s" % (", ".join(_repeatable)))


def unrepeat(session, *args, **kwargs):
    "Wrapper for OOB use"
    kwargs["stop"] = True
    repeat(session, *args, **kwargs)


_monitorable = {"name": "db_key", "location": "db_location", "desc": "desc"}


def _on_monitor_change(**kwargs):
    fieldname = kwargs["fieldname"]
    obj = kwargs["obj"]
    name = kwargs["name"]
    session = kwargs["session"]
    outputfunc_name = kwargs["outputfunc_name"]

    # the session may be None if the char quits and someone
    # else then edits the object

    if session:
        callsign = {outputfunc_name: {"name": name, "value": _GA(obj, fieldname)}}
        session.msg(**callsign)


def monitor(session, *args, **kwargs):
    """
    Adds monitoring to a given property or Attribute.

    Kwargs:
      name (str): The name of the property or Attribute
        to report. No db_* prefix is needed. Only names
        in the _monitorable dict earlier in this module
        are accepted.
      stop (bool): Stop monitoring the above name.
      outputfunc_name (str, optional): Change the name of
        the outputfunc name. This is used e.g. by MSDP which
        has its own specific output format.

    """
    from evennia.scripts.monitorhandler import MONITOR_HANDLER

    name = kwargs.get("name", None)
    outputfunc_name = kwargs("outputfunc_name", "monitor")
    if name and name in _monitorable and session.puppet:
        field_name = _monitorable[name]
        obj = session.puppet
        if kwargs.get("stop", False):
            MONITOR_HANDLER.remove(obj, field_name, idstring=session.sessid)
        else:
            # the handler will add fieldname and obj to the kwargs automatically
            MONITOR_HANDLER.add(
                obj,
                field_name,
                _on_monitor_change,
                idstring=session.sessid,
                persistent=False,
                name=name,
                session=session,
                outputfunc_name=outputfunc_name,
            )


def unmonitor(session, *args, **kwargs):
    """
    Wrapper for turning off monitoring
    """
    kwargs["stop"] = True
    monitor(session, *args, **kwargs)


def monitored(session, *args, **kwargs):
    """
    Report on what is being monitored

    """
    from evennia.scripts.monitorhandler import MONITOR_HANDLER

    obj = session.puppet
    monitors = MONITOR_HANDLER.all(obj=obj)
    session.msg(monitored=(monitors, {}))


def _on_webclient_options_change(**kwargs):
    """
    Called when the webclient options stored on the account changes.
    Inform the interested clients of this change.
    """
    session = kwargs["session"]
    obj = kwargs["obj"]
    fieldname = kwargs["fieldname"]
    clientoptions = _GA(obj, fieldname)

    # the session may be None if the char quits and someone
    # else then edits the object
    if session:
        session.msg(webclient_options=clientoptions)


def webclient_options(session, *args, **kwargs):
    """
    Handles retrieving and changing of options related to the webclient.

    If kwargs is empty (or contains just a "cmdid"), the saved options will be
    sent back to the session.
    A monitor handler will be created to inform the client of any future options
    that changes.

    If kwargs is not empty, the key/values stored in there will be persisted
    to the account object.

    Kwargs:
        <option name>: an option to save
    """
    account = session.account

    clientoptions = account.db._saved_webclient_options
    if not clientoptions:
        # No saved options for this account, copy and save the default.
        account.db._saved_webclient_options = settings.WEBCLIENT_OPTIONS.copy()
        # Get the _SaverDict created by the database.
        clientoptions = account.db._saved_webclient_options

    # The webclient adds a cmdid to every kwargs, but we don't need it.
    try:
        del kwargs["cmdid"]
    except KeyError:
        pass

    if not kwargs:
        # No kwargs: we are getting the stored options
        # Convert clientoptions to regular dict for sending.
        session.msg(webclient_options=dict(clientoptions))

        # Create a monitor. If a monitor already exists then it will replace
        # the previous one since it would use the same idstring
        from evennia.scripts.monitorhandler import MONITOR_HANDLER

        MONITOR_HANDLER.add(
            account,
            "_saved_webclient_options",
            _on_webclient_options_change,
            idstring=session.sessid,
            persistent=False,
            session=session,
        )
    else:
        # kwargs provided: persist them to the account object
        for key, value in kwargs.items():
            clientoptions[key] = value


# OOB protocol-specific aliases and wrappers

# GMCP aliases
hello = client_options
supports_set = client_options


# MSDP aliases (some of the the generic MSDP commands defined in the MSDP spec are prefixed
# by msdp_ at the protocol level)
# See https://tintin.sourceforge.io/protocols/msdp/


def msdp_list(session, *args, **kwargs):
    """
    MSDP LIST command

    """
    from evennia.scripts.monitorhandler import MONITOR_HANDLER

    args_lower = [arg.lower() for arg in args]
    if "commands" in args_lower:
        inputfuncs = [
            key[5:] if key.startswith("msdp_") else key
            for key in session.sessionhandler.get_inputfuncs().keys()
        ]
        session.msg(commands=(inputfuncs, {}))
    if "lists" in args_lower:
        session.msg(
            lists=(
                [
                    "commands",
                    "lists",
                    "configurable_variables",
                    "reportable_variables",
                    "reported_variables",
                    "sendable_variables",
                ],
                {},
            )
        )
    if "configurable_variables" in args_lower:
        session.msg(configurable_variables=(_CLIENT_OPTIONS, {}))
    if "reportable_variables" in args_lower:
        session.msg(reportable_variables=(_monitorable, {}))
    if "reported_variables" in args_lower:
        obj = session.puppet
        monitor_infos = MONITOR_HANDLER.all(obj=obj)
        fieldnames = [tup[1] for tup in monitor_infos]
        session.msg(reported_variables=(fieldnames, {}))
    if "sendable_variables" in args_lower:
        # no default sendable variables
        session.msg(sendable_variables=([], {}))


def msdp_report(session, *args, **kwargs):
    """
    MSDP REPORT command

    """
    kwargs["outputfunc_name":"report"]
    monitor(session, *args, **kwargs)


def msdp_unreport(session, *args, **kwargs):
    """
    MSDP UNREPORT command

    """
    unmonitor(session, *args, **kwargs)


# client specific


def external_discord_hello(session, *args, **kwargs):
    """
    Sent by Mudlet as a greeting; added here to avoid
    logging a missing inputfunc for it.
    """
    pass
