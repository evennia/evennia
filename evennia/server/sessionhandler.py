"""
This module defines handlers for storing sessions when handles
sessions of users connecting to the server.

There are two similar but separate stores of sessions:

- ServerSessionHandler - this stores generic game sessions
     for the game. These sessions has no knowledge about
     how they are connected to the world.
- PortalSessionHandler - this stores sessions created by
     twisted protocols. These are dumb connectors that
     handle network communication but holds no game info.

"""
import time
from codecs import decode as codecs_decode

from django.conf import settings
from django.utils.translation import gettext as _

from evennia.commands.cmdhandler import CMD_LOGINSTART
from evennia.server.portal import amp
from evennia.server.signals import (
    SIGNAL_ACCOUNT_POST_FIRST_LOGIN,
    SIGNAL_ACCOUNT_POST_LAST_LOGOUT,
    SIGNAL_ACCOUNT_POST_LOGIN,
    SIGNAL_ACCOUNT_POST_LOGOUT,
)
from evennia.utils.logger import log_trace
from evennia.utils.utils import (
    callables_from_module,
    class_from_module,
    delay,
    is_iter,
    make_iter,
)

_FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED = settings.FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED
_BROADCAST_SERVER_RESTART_MESSAGES = settings.BROADCAST_SERVER_RESTART_MESSAGES

# delayed imports
_AccountDB = None
_ServerSession = None
_ServerConfig = None
_ScriptDB = None
_OOB_HANDLER = None

_ERR_BAD_UTF8 = _("Your client sent an incorrect UTF-8 sequence.")


class DummySession(object):
    sessid = 0


DUMMYSESSION = DummySession()

_SERVERNAME = settings.SERVERNAME
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_IDLE_TIMEOUT = settings.IDLE_TIMEOUT
_DELAY_CMD_LOGINSTART = settings.DELAY_CMD_LOGINSTART
_MAX_SERVER_COMMANDS_PER_SECOND = 100.0
_MAX_SESSION_COMMANDS_PER_SECOND = 5.0
_MODEL_MAP = None
_FUNCPARSER = None


# input handlers

_INPUT_FUNCS = {}
for modname in make_iter(settings.INPUT_FUNC_MODULES):
    _INPUT_FUNCS.update(callables_from_module(modname))


def delayed_import():
    """
    Helper method for delayed import of all needed entities.

    """
    global _ServerSession, _AccountDB, _ServerConfig, _ScriptDB
    if not _ServerSession:
        # we allow optional arbitrary serversession class for overloading
        _ServerSession = class_from_module(settings.SERVER_SESSION_CLASS)
    if not _AccountDB:
        from evennia.accounts.models import AccountDB as _AccountDB
    if not _ServerConfig:
        from evennia.server.models import ServerConfig as _ServerConfig
    if not _ScriptDB:
        from evennia.scripts.models import ScriptDB as _ScriptDB
    # including once to avoid warnings in Python syntax checkers
    assert _ServerSession, "ServerSession class could not load"
    assert _AccountDB, "AccountDB class could not load"
    assert _ServerConfig, "ServerConfig class could not load"
    assert _ScriptDB, "ScriptDB class c ould not load"


# -----------------------------------------------------------
# SessionHandler base class
# ------------------------------------------------------------


class SessionHandler(dict):
    """
    This handler holds a stack of sessions.

    """

    def __getitem__(self, key):
        """
        Clean out None-sessions automatically.

        """
        if None in self:
            del self[None]
        return super().__getitem__(key)

    def get(self, key, default=None):
        """
        Clean out None-sessions automatically.

        """
        if None in self:
            del self[None]
        return super().get(key, default)

    def __setitem__(self, key, value):
        """
        Don't assign None sessions"

        """
        if key is not None:
            super().__setitem__(key, value)

    def __contains__(self, key):
        """
        None-keys are not accepted.

        """
        return False if key is None else super().__contains__(key)

    def get_sessions(self, include_unloggedin=False):
        """
        Returns the connected session objects.

        Args:
            include_unloggedin (bool, optional): Also list Sessions
                that have not yet authenticated.

        Returns:
            sessions (list): A list of `Session` objects.

        """
        if include_unloggedin:
            return list(self.values())
        else:
            return [session for session in self.values() if session.logged_in]

    def get_all_sync_data(self):
        """
        Create a dictionary of sessdata dicts representing all
        sessions in store.

        Returns:
            syncdata (dict): A dict of sync data.

        """
        return dict((sessid, sess.get_sync_data()) for sessid, sess in self.items())

    def clean_senddata(self, session, kwargs):
        """
        Clean up data for sending across the AMP wire. Also apply the
        FuncParser using callables from `settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES`.

        Args:
            session (Session): The relevant session instance.
            kwargs (dict) Each keyword represents a send-instruction, with the keyword itself being
                the name of the instruction (like "text"). Suitable values for each keyword are:
                - arg                ->  [[arg], {}]
                - [args]             ->  [[args], {}]
                - {kwargs}           ->  [[], {kwargs}]
                - [args, {kwargs}]   ->  [[arg], {kwargs}]
                - [[args], {kwargs}] ->  [[args], {kwargs}]

        Returns:
            kwargs (dict): A cleaned dictionary of cmdname:[[args],{kwargs}] pairs,
            where the keys, args and kwargs have all been converted to
            send-safe entities (strings or numbers), and funcparser parsing has been
            applied.

        """
        global _FUNCPARSER
        if not _FUNCPARSER:
            from evennia.utils.funcparser import FuncParser

            _FUNCPARSER = FuncParser(
                settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES, raise_errors=True
            )

        options = kwargs.pop("options", None) or {}
        raw = options.get("raw", False)
        strip_inlinefunc = options.get("strip_inlinefunc", False)

        def _utf8(data):
            if isinstance(data, bytes):
                try:
                    data = codecs_decode(data, session.protocol_flags["ENCODING"])
                except LookupError:
                    # wrong encoding set on the session. Set it to a safe one
                    session.protocol_flags["ENCODING"] = "utf-8"
                    data = codecs_decode(data, "utf-8")
                except UnicodeDecodeError:
                    # incorrect unicode sequence
                    session.sendLine(_ERR_BAD_UTF8)
                    data = ""

            return data

        def _validate(data):
            """
            Helper function to convert data to AMP-safe (picketable) values"

            """
            if isinstance(data, dict):
                newdict = {}
                for key, part in data.items():
                    newdict[key] = _validate(part)
                return newdict
            elif is_iter(data):
                return [_validate(part) for part in data]
            elif isinstance(data, (str, bytes)):
                data = _utf8(data)

                if (
                    _FUNCPARSER_PARSE_OUTGOING_MESSAGES_ENABLED
                    and not raw
                    and isinstance(self, ServerSessionHandler)
                ):
                    # only apply funcparser on the outgoing path (sessionhandler->)
                    # data = parse_inlinefunc(data, strip=strip_inlinefunc, session=session)
                    data = _FUNCPARSER.parse(data, strip=strip_inlinefunc, session=session)

                return str(data)
            elif (
                hasattr(data, "id")
                and hasattr(data, "db_date_created")
                and hasattr(data, "__dbclass__")
            ):
                # convert database-object to their string representation.
                return _validate(str(data))
            else:
                return data

        rkwargs = {}
        for key, data in kwargs.items():
            key = _validate(key)
            if not data:
                if key == "text":
                    # we don't allow sending text = None, this must mean
                    # that the text command is not to be used.
                    continue
                rkwargs[key] = [[], {}]
            elif isinstance(data, dict):
                rkwargs[key] = [[], _validate(data)]
            elif is_iter(data):
                data = tuple(data)
                if isinstance(data[-1], dict):
                    if len(data) == 2:
                        if is_iter(data[0]):
                            rkwargs[key] = [_validate(data[0]), _validate(data[1])]
                        else:
                            rkwargs[key] = [[_validate(data[0])], _validate(data[1])]
                    else:
                        rkwargs[key] = [_validate(data[:-1]), _validate(data[-1])]
                else:
                    rkwargs[key] = [_validate(data), {}]
            else:
                rkwargs[key] = [[_validate(data)], {}]
            rkwargs[key][1]["options"] = dict(options)
        # make sure that any "prompt" message will be processed last
        # by moving it to the end
        if "prompt" in rkwargs:
            prompt = rkwargs.pop("prompt")
            rkwargs["prompt"] = prompt
        return rkwargs


# ------------------------------------------------------------
# Server-SessionHandler class
# ------------------------------------------------------------


class ServerSessionHandler(SessionHandler):
    """
    This object holds the stack of sessions active in the game at any time.

    A session register with the handler in two steps, first by registering itself with the connect()
    method. This indicates an non-authenticated session. Whenever the session is authenticated the
    session together with the related account is sent to the login() method.

    """

    # AMP communication methods

    def __init__(self, *args, **kwargs):
        """
        Init the handler.

        """
        super().__init__(*args, **kwargs)
        self.server = None  # set at server initialization
        self.server_data = {"servername": _SERVERNAME}
        # will be set on psync
        self.portal_start_time = 0.0

    def _run_cmd_login(self, session):
        """
        Launch the CMD_LOGINSTART command. This is wrapped
        for delays.

        """
        if not session.logged_in:
            self.data_in(session, text=[[CMD_LOGINSTART], {}])

    def portal_connect(self, portalsessiondata):
        """
        Called by Portal when a new session has connected.
        Creates a new, unlogged-in game session.

        Args:
            portalsessiondata (dict): a dictionary of all property:value
                keys defining the session and which is marked to be
                synced.

        """
        delayed_import()
        global _ServerSession, _AccountDB, _ScriptDB

        sess = _ServerSession()
        sess.sessionhandler = self
        sess.load_sync_data(portalsessiondata)
        sess.at_sync()
        # validate all scripts
        # _ScriptDB.objects.validate()
        self[sess.sessid] = sess

        if sess.logged_in and sess.uid:
            # Session is already logged in. This can happen in the
            # case of auto-authenticating protocols like SSH or
            # webclient's session sharing
            account = _AccountDB.objects.get_account_from_uid(sess.uid)
            if account:
                # this will set account.is_connected too
                self.login(sess, account, force=True)
                return
            else:
                sess.logged_in = False
                sess.uid = None

        # show the first login command, may delay slightly to allow
        # the handshakes to finish.
        delay(_DELAY_CMD_LOGINSTART, self._run_cmd_login, sess)

    def portal_session_sync(self, portalsessiondata):
        """
        Called by Portal when it wants to update a single session (e.g.
        because of all negotiation protocols have finally replied)

        Args:
            portalsessiondata (dict): a dictionary of all property:value
                keys defining the session and which is marked to be
                synced.

        """
        sessid = portalsessiondata.get("sessid")
        session = self.get(sessid)
        if session:
            # since some of the session properties may have had
            # a chance to change already before the portal gets here
            # the portal doesn't send all sessiondata but only
            # ones which should only be changed from portal (like
            # protocol_flags etc)
            session.load_sync_data(portalsessiondata)

    def portal_sessions_sync(self, portalsessionsdata):
        """
        Syncing all session ids of the portal with the ones of the
        server. This is instantiated by the portal when reconnecting.

        Args:
            portalsessionsdata (dict): A dictionary
              `{sessid: {property:value},...}` defining each session and
              the properties in it which should be synced.

        """
        delayed_import()
        global _ServerSession, _AccountDB, _ServerConfig, _ScriptDB

        for sess in list(self.values()):
            # we delete the old session to make sure to catch eventual
            # lingering references.
            del sess

        for sessid, sessdict in portalsessionsdata.items():
            sess = _ServerSession()
            sess.sessionhandler = self
            sess.load_sync_data(sessdict)
            if sess.uid:
                sess.account = _AccountDB.objects.get_account_from_uid(sess.uid)
            self[sessid] = sess
            sess.at_sync()

        mode = "reload"

        # tell the server hook we synced
        self.server.at_post_portal_sync(mode)
        # announce the reconnection
        if _BROADCAST_SERVER_RESTART_MESSAGES:
            self.announce_all(_(" ... Server restarted."))

    def portal_disconnect(self, session):
        """
        Called from Portal when Portal session closed from the portal
        side. There is no message to report in this case.

        Args:
            session (Session): The Session to disconnect

        """
        # disconnect us without calling Portal since
        # Portal already knows.
        self.disconnect(session, reason="", sync_portal=False)

    def portal_disconnect_all(self):
        """
        Called from Portal when Portal is closing down. All
        Sessions should die. The Portal should not be informed.

        """
        # set a watchdog to avoid self.disconnect from deleting
        # the session while we are looping over them
        self._disconnect_all = True
        for session in self.values():
            session.disconnect()
        del self._disconnect_all

    # server-side access methods

    def start_bot_session(self, protocol_path, configdict):
        """
        This method allows the server-side to force the Portal to
        create a new bot session.

        Args:
            protocol_path (str): The  full python path to the bot's
                class.
            configdict (dict): This dict will be used to configure
                the bot (this depends on the bot protocol).

        Examples:
            start_bot_session("evennia.server.portal.irc.IRCClient",
                              {"uid":1,  "botname":"evbot", "channel":"#evennia",
                               "network:"irc.freenode.net", "port": 6667})

        Notes:
            The new session will use the supplied account-bot uid to
            initiate an already logged-in connection. The Portal will
            treat this as a normal connection and henceforth so will
            the Server.

        """
        self.server.amp_protocol.send_AdminServer2Portal(
            DUMMYSESSION, operation=amp.SCONN, protocol_path=protocol_path, config=configdict
        )

    def portal_restart_server(self):
        """
        Called by server when reloading. We tell the portal to start a new server instance.

        """
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION, operation=amp.SRELOAD)

    def portal_reset_server(self):
        """
        Called by server when reloading. We tell the portal to start a new server instance.

        """
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION, operation=amp.SRESET)

    def portal_shutdown(self):
        """
        Called by server when it's time to shut down (the portal will shut us down and then shut
        itself down)

        """
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION, operation=amp.PSHUTD)

    def login(self, session, account, force=False, testmode=False):
        """
        Log in the previously unloggedin session and the account we by now should know is connected
        to it. After this point we assume the session to be logged in one way or another.

        Args:
            session (Session): The Session to authenticate.
            account (Account): The Account identified as associated with this Session.
            force (bool): Login also if the session thinks it's already logged in
                (this can happen for auto-authenticating protocols)
            testmode (bool, optional): This is used by unittesting for
                faking login without any AMP being actually active.

        """
        if session.logged_in and not force:
            # don't log in a session that is already logged in.
            return

        account.is_connected = True

        # sets up and assigns all properties on the session
        session.at_login(account)

        # account init
        account.at_init()

        # Check if this is the first time the *account* logs in
        if account.db.FIRST_LOGIN:
            account.at_first_login()
            del account.db.FIRST_LOGIN

        account.at_pre_login()

        if _MULTISESSION_MODE == 0:
            # disconnect all previous sessions.
            self.disconnect_duplicate_sessions(session)

        nsess = len(self.sessions_from_account(account))
        string = "Logged in: {account} {address} ({nsessions} session(s) total)"
        string = string.format(account=account, address=session.address, nsessions=nsess)
        session.log(string)
        session.logged_in = True
        # sync the portal to the session
        if not testmode:
            self.server.amp_protocol.send_AdminServer2Portal(
                session, operation=amp.SLOGIN, sessiondata={"logged_in": True, "uid": session.uid}
            )
        account.at_post_login(session=session)
        if nsess < 2:
            SIGNAL_ACCOUNT_POST_FIRST_LOGIN.send(sender=account, session=session)
        SIGNAL_ACCOUNT_POST_LOGIN.send(sender=account, session=session)

    def disconnect(self, session, reason="", sync_portal=True):
        """
        Called from server side to remove session and inform portal
        of this fact.

        Args:
            session (Session): The Session to disconnect.
            reason (str, optional): A motivation for the disconnect.
            sync_portal (bool, optional): Sync the disconnect to
                Portal side. This should be done unless this was
                called by self.portal_disconnect().

        """
        session = self.get(session.sessid)
        if not session:
            return

        if hasattr(session, "account") and session.account:
            # only log accounts logging off
            nsess = len(self.sessions_from_account(session.account)) - 1
            sreason = " ({})".format(reason) if reason else ""
            string = "Logged out: {account} {address} ({nsessions} sessions(s) remaining){reason}"
            string = string.format(
                reason=sreason, account=session.account, address=session.address, nsessions=nsess
            )
            session.log(string)

            if nsess == 0:
                SIGNAL_ACCOUNT_POST_LAST_LOGOUT.send(sender=session.account, session=session)

        session.at_disconnect(reason)
        SIGNAL_ACCOUNT_POST_LOGOUT.send(sender=session.account, session=session)
        sessid = session.sessid
        if sessid in self and not hasattr(self, "_disconnect_all"):
            del self[sessid]
        if sync_portal:
            # inform portal that session should be closed.
            self.server.amp_protocol.send_AdminServer2Portal(
                session, operation=amp.SDISCONN, reason=reason
            )

    def all_sessions_portal_sync(self):
        """
        This is called by the server when it reboots. It syncs all session data
        to the portal. Returns a deferred!

        """
        sessdata = self.get_all_sync_data()
        return self.server.amp_protocol.send_AdminServer2Portal(
            DUMMYSESSION, operation=amp.SSYNC, sessiondata=sessdata
        )

    def session_portal_sync(self, session):
        """
        This is called by the server when it wants to sync a single session
        with the Portal for whatever reason. Returns a deferred!

        """
        sessdata = {session.sessid: session.get_sync_data()}
        return self.server.amp_protocol.send_AdminServer2Portal(
            DUMMYSESSION, operation=amp.SSYNC, sessiondata=sessdata, clean=False
        )

    def session_portal_partial_sync(self, session_data):
        """
        Call to make a partial update of the session, such as only a particular property.

        Args:
            session_data (dict): Store `{sessid: {property:value}, ...}` defining one or
                more sessions in detail.

        """
        return self.server.amp_protocol.send_AdminServer2Portal(
            DUMMYSESSION, operation=amp.SSYNC, sessiondata=session_data, clean=False
        )

    def disconnect_all_sessions(self, reason="You have been disconnected."):
        """
        Cleanly disconnect all of the connected sessions.

        Args:
            reason (str, optional): The reason for the disconnection.

        """

        for session in self:
            del session
        # tell portal to disconnect all sessions
        self.server.amp_protocol.send_AdminServer2Portal(
            DUMMYSESSION, operation=amp.SDISCONNALL, reason=reason
        )

    def disconnect_duplicate_sessions(
        self, curr_session, reason=_("Logged in from elsewhere. Disconnecting.")
    ):
        """
        Disconnects any existing sessions with the same user.

        args:
            curr_session (Session): Disconnect all Sessions matching this one.
            reason (str, optional): A motivation for disconnecting.

        """
        uid = curr_session.uid
        # we can't compare sessions directly since this will compare addresses and
        # mean connecting from the same host would not catch duplicates
        sid = id(curr_session)
        doublet_sessions = [
            sess for sess in self.values() if sess.logged_in and sess.uid == uid and id(sess) != sid
        ]

        for session in doublet_sessions:
            self.disconnect(session, reason)

    def validate_sessions(self):
        """
        Check all currently connected sessions (logged in and not) and
        see if any are dead or idle.

        """
        tcurr = time.time()
        reason = _("Idle timeout exceeded, disconnecting.")
        for session in (
            session
            for session in self.values()
            if session.logged_in
            and _IDLE_TIMEOUT > 0
            and (tcurr - session.cmd_last) > _IDLE_TIMEOUT
        ):
            self.disconnect(session, reason=reason)

    def account_count(self):
        """
        Get the number of connected accounts (not sessions since a
        account may have more than one session depending on settings).
        Only logged-in accounts are counted here.

        Returns:
            naccount (int): Number of connected accounts

        """
        return len(set(session.uid for session in self.values() if session.logged_in))

    def all_connected_accounts(self):
        """
        Get a unique list of connected and logged-in Accounts.

        Returns:
            accounts (list): All connected Accounts (which may be fewer than the
                amount of Sessions due to multi-playing).

        """
        return list(
            set(
                session.account
                for session in self.values()
                if session.logged_in and session.account
            )
        )

    def session_from_sessid(self, sessid):
        """
        Get session based on sessid, or None if not found

        Args:
            sessid (int or list): Session id(s).

        Return:
            sessions (Session or list): Session(s) found. This
                is a list if input was a list.

        """
        if is_iter(sessid):
            return [self.get(sid) for sid in sessid if sid in self]
        return self.get(sessid)

    def session_from_account(self, account, sessid):
        """
        Given an account and a session id, return the actual session
        object.

        Args:
            account (Account): The Account to get the Session from.
            sessid (int or list): Session id(s).

        Returns:
            sessions (Session or list): Session(s) found.

        """
        sessions = [
            self[sid]
            for sid in make_iter(sessid)
            if sid in self and self[sid].logged_in and account.uid == self[sid].uid
        ]
        return sessions[0] if len(sessions) == 1 else sessions

    def sessions_from_account(self, account):
        """
        Given an account, return all matching sessions.

        Args:
            account (Account): Account to get sessions from.

        Returns:
            sessions (list): All Sessions associated with this account.

        """
        uid = account.uid
        return [session for session in self.values() if session.logged_in and session.uid == uid]

    def sessions_from_puppet(self, puppet):
        """
        Given a puppeted object, return all controlling sessions.

        Args:
            puppet (Object): Object puppeted

        Returns.
            sessions (Session or list): Can be more than one of Object is controlled by more than
                one Session (MULTISESSION_MODE > 1).

        """
        sessions = puppet.sessid.get()
        return sessions[0] if len(sessions) == 1 else sessions

    sessions_from_character = sessions_from_puppet

    def sessions_from_csessid(self, csessid):
        """
        Given a client identification hash (for session types that offer them)
        return all sessions with a matching hash.

        Args
            csessid (str): The session hash.

        Returns:
            sessions (list): The sessions with matching .csessid, if any.

        """
        if csessid:
            return []
        return [
            session for session in self.values() if session.csessid and session.csessid == csessid
        ]

    def announce_all(self, message):
        """
        Send message to all connected sessions

        Args:
            message (str): Message to send.

        """
        for session in self.values():
            self.data_out(session, text=message)

    def data_out(self, session, **kwargs):
        """
        Sending data Server -> Portal

        Args:
            session (Session): Session to relay to.
            text (str, optional): text data to return

        Notes:
            The outdata will be scrubbed for sending across
            the wire here.
        """
        # clean output for sending
        kwargs = self.clean_senddata(session, kwargs)

        # send across AMP
        self.server.amp_protocol.send_MsgServer2Portal(session, **kwargs)

    def get_inputfuncs(self):
        """
        Get all registered inputfuncs (access function)

        Returns:
            inputfuncs (dict): A dict of {key:inputfunc,...}
        """
        return _INPUT_FUNCS

    def data_in(self, session, **kwargs):
        """
        We let the data take a "detour" to session.data_in
        so the user can override and see it all in one place.
        That method is responsible to in turn always call
        this class' `sessionhandler.call_inputfunc` with the
        (possibly processed) data.

        """
        if session:
            session.data_in(**kwargs)

    def call_inputfuncs(self, session, **kwargs):
        """
        Split incoming data into its inputfunc counterparts. This should be
        called by the `serversession.data_in` as
        `sessionhandler.call_inputfunc(self, **kwargs)`.

        We also intercept OOB communication here.

        Args:
            sessions (Session): Session.

        Keyword Args:
            any (tuple): Incoming data from protocol, each
                on the form `commandname=((args), {kwargs})`.

        """

        # distribute incoming data to the correct receiving methods.
        if session:
            input_debug = session.protocol_flags.get("INPUTDEBUG", False)
            for cmdname, (cmdargs, cmdkwargs) in kwargs.items():
                cname = cmdname.strip().lower()
                try:
                    cmdkwargs.pop("options", None)
                    if cname in _INPUT_FUNCS:
                        _INPUT_FUNCS[cname](session, *cmdargs, **cmdkwargs)
                    else:
                        _INPUT_FUNCS["default"](session, cname, *cmdargs, **cmdkwargs)
                except Exception as err:
                    if input_debug:
                        session.msg(err)
                    log_trace()


# import class from settings
_SESSION_HANDLER_CLASS = class_from_module(settings.SERVER_SESSION_HANDLER_CLASS)

# Instantiate class. These globals are used to provide singleton-like behavior.
SESSION_HANDLER = _SESSION_HANDLER_CLASS()
SESSIONS = SESSION_HANDLER  # legacy
