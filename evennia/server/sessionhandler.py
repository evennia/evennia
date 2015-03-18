"""
This module defines handlers for storing sessions when handles
sessions of users connecting to the server.

There are two similar but separate stores of sessions:
  ServerSessionHandler - this stores generic game sessions
         for the game. These sessions has no knowledge about
         how they are connected to the world.
  PortalSessionHandler - this stores sessions created by
         twisted protocols. These are dumb connectors that
         handle network communication but holds no game info.

"""

from time import time
from django.conf import settings
from evennia.commands.cmdhandler import CMD_LOGINSTART
from evennia.utils.utils import variable_from_module, is_iter, \
                            to_str, to_unicode, strip_control_sequences, make_iter

try:
    import cPickle as pickle
except ImportError:
    import pickle

# delayed imports
_PlayerDB = None
_ServerSession = None
_ServerConfig = None
_ScriptDB = None
_OOB_HANDLER = None


# AMP signals
PCONN = chr(1)        # portal session connect
PDISCONN = chr(2)     # portal session disconnect
PSYNC = chr(3)        # portal session sync
SLOGIN = chr(4)       # server session login
SDISCONN = chr(5)     # server session disconnect
SDISCONNALL = chr(6)  # server session disconnect all
SSHUTD = chr(7)       # server shutdown
SSYNC = chr(8)        # server session sync
SCONN = chr(9)        # server portal connection (for bots)
PCONNSYNC = chr(10)   # portal post-syncing session

# i18n
from django.utils.translation import ugettext as _

_SERVERNAME = settings.SERVERNAME
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_IDLE_TIMEOUT = settings.IDLE_TIMEOUT
_MAX_SERVER_COMMANDS_PER_SECOND = 100.0
_MAX_SESSION_COMMANDS_PER_SECOND = 5.0


_ERROR_COMMAND_OVERFLOW = "You entered commands too fast. Wait a moment and try again."

def delayed_import():
    "Helper method for delayed import of all needed entities"
    global _ServerSession, _PlayerDB, _ServerConfig, _ScriptDB
    if not _ServerSession:
        # we allow optional arbitrary serversession class for overloading
        modulename, classname = settings.SERVER_SESSION_CLASS.rsplit(".", 1)
        _ServerSession = variable_from_module(modulename, classname)
    if not _PlayerDB:
        from evennia.players.models import PlayerDB as _PlayerDB
    if not _ServerConfig:
        from evennia.server.models import ServerConfig as _ServerConfig
    if not _ScriptDB:
        from evennia.scripts.models import ScriptDB as _ScriptDB
    # including once to avoid warnings in Python syntax checkers
    _ServerSession, _PlayerDB, _ServerConfig, _ScriptDB


#-----------------------------------------------------------
# SessionHandler base class
#------------------------------------------------------------

class SessionHandler(object):
    """
    This handler holds a stack of sessions.
    """
    def __init__(self):
        """
        Init the handler.
        """
        self.sessions = {}

    def get_sessions(self, include_unloggedin=False):
        """
        Returns the connected session objects.
        """
        if include_unloggedin:
            return self.sessions.values()
        else:
            return [session for session in self.sessions.values() if session.logged_in]

    def get_session(self, sessid):
        """
        Get session by sessid
        """
        return self.sessions.get(sessid, None)

    def get_all_sync_data(self):
        """
        Create a dictionary of sessdata dicts representing all
        sessions in store.
        """
        return dict((sessid, sess.get_sync_data()) for sessid, sess in self.sessions.items())


#------------------------------------------------------------
# Server-SessionHandler class
#------------------------------------------------------------

class ServerSessionHandler(SessionHandler):
    """
    This object holds the stack of sessions active in the game at
    any time.

    A session register with the handler in two steps, first by
    registering itself with the connect() method. This indicates an
    non-authenticated session. Whenever the session is authenticated
    the session together with the related player is sent to the login()
    method.

    """

    # AMP communication methods

    def __init__(self):
        """
        Init the handler.
        """
        self.sessions = {}
        self.server = None
        self.server_data = {"servername": _SERVERNAME}

    def portal_connect(self, portalsession):
        """
        Called by Portal when a new session has connected.
        Creates a new, unlogged-in game session.

        portalsession is a dictionary of all property:value keys
                      defining the session and which is marked to
                      be synced.
        """
        delayed_import()
        global _ServerSession, _PlayerDB, _ScriptDB

        sess = _ServerSession()
        sess.sessionhandler = self
        sess.load_sync_data(portalsession)
        if sess.logged_in and sess.uid:
            # this can happen in the case of auto-authenticating
            # protocols like SSH
            sess.player = _PlayerDB.objects.get_player_from_uid(sess.uid)
        sess.at_sync()
        # validate all scripts
        _ScriptDB.objects.validate()
        self.sessions[sess.sessid] = sess
        sess.data_in(CMD_LOGINSTART)

    def portal_session_sync(self, portalsessiondata):
        """
        Called by Portal when it wants to update a single session (e.g.
        because of all negotiation protocols have finally replied)
        """
        sessid = portalsessiondata.get("sessid")
        session = self.sessions.get(sessid)
        if session:
            # since some of the session properties may have had
            # a chance to change already before the portal gets here
            # the portal doesn't send all sessiondata but only
            # ones which should only be changed from portal (like
            # protocol_flags etc)
            session.load_sync_data(portalsessiondata)

    def portal_disconnect(self, sessid):
        """
        Called by Portal when portal reports a closing of a session
        from the portal side.
        """
        session = self.sessions.get(sessid, None)
        if not session:
            return
        self.disconnect(session)

    def portal_sessions_sync(self, portalsessions):
        """
        Syncing all session ids of the portal with the ones of the
        server. This is instantiated by the portal when reconnecting.

        portalsessions is a dictionary {sessid: {property:value},...} defining
                      each session and the properties in it which should
                      be synced.
        """
        delayed_import()
        global _ServerSession, _PlayerDB, _ServerConfig, _ScriptDB

        for sess in self.sessions.values():
            # we delete the old session to make sure to catch eventual
            # lingering references.
            del sess

        for sessid, sessdict in portalsessions.items():
            sess = _ServerSession()
            sess.sessionhandler = self
            sess.load_sync_data(sessdict)
            if sess.uid:
                sess.player = _PlayerDB.objects.get_player_from_uid(sess.uid)
            self.sessions[sessid] = sess
            sess.at_sync()

        # after sync is complete we force-validate all scripts
        # (this also starts them)
        init_mode = _ServerConfig.objects.conf("server_restart_mode", default=None)
        _ScriptDB.objects.validate(init_mode=init_mode)
        _ServerConfig.objects.conf("server_restart_mode", delete=True)
        # announce the reconnection
        self.announce_all(_(" ... Server restarted."))

    # server-side access methods

    def start_bot_session(self, protocol_path, configdict):
        """
        This method allows the server-side to force the Portal to create
        a new bot session using the protocol specified by protocol_path,
        which should be the full python path to the class, including the
        class name, like "evennia.server.portal.irc.IRCClient".
        The new session will use the supplied player-bot uid to
        initiate an already logged-in connection. The Portal will
        treat this as a normal connection and henceforth so will the
        Server.
        """
        data = {"protocol_path":protocol_path,
                "config":configdict}
        self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SCONN,
                                                         data=data)

    def portal_shutdown(self):
        """
        Called by server when shutting down the portal.
        """
        self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SSHUTD,
                                                         data="")

    def login(self, session, player, testmode=False):
        """
        Log in the previously unloggedin session and the player we by
        now should know is connected to it. After this point we
        assume the session to be logged in one way or another.

        testmode - this is used by unittesting for faking login without
        any AMP being actually active
        """

        # we have to check this first before uid has been assigned
        # this session.

        if not self.sessions_from_player(player):
            player.is_connected = True

        # sets up and assigns all properties on the session
        session.at_login(player)

        # player init
        player.at_init()

        # Check if this is the first time the *player* logs in
        if player.db.FIRST_LOGIN:
            player.at_first_login()
            del player.db.FIRST_LOGIN

        player.at_pre_login()

        if _MULTISESSION_MODE == 0:
            # disconnect all previous sessions.
            self.disconnect_duplicate_sessions(session)

        nsess = len(self.sessions_from_player(player))
        string = "Logged in: {player} {address} ({nsessions} session(s) total)"
        string = string.format(player=player,address=session.address, nsessions=nsess)
        session.log(string)

        session.logged_in = True
        # sync the portal to the session
        sessdata = {"logged_in": True}
        if not testmode:
            self.server.amp_protocol.call_remote_PortalAdmin(session.sessid,
                                                         operation=SLOGIN,
                                                         data=sessdata)
        player.at_post_login(sessid=session.sessid)

    def disconnect(self, session, reason=""):
        """
        Called from server side to remove session and inform portal
        of this fact.
        """
        session = self.sessions.get(session.sessid)
        if not session:
            return

        if hasattr(session, "player") and session.player:
            # only log accounts logging off
            nsess = len(self.sessions_from_player(session.player)) - 1
            string = "Logged out: {player} {address} ({nsessions} sessions(s) remaining)"
            string = string.format(player=session.player, address=session.address, nsessions=nsess)
            session.log(string)

        session.at_disconnect()
        sessid = session.sessid
        del self.sessions[sessid]
        # inform portal that session should be closed.
        self.server.amp_protocol.call_remote_PortalAdmin(sessid,
                                                         operation=SDISCONN,
                                                         data=reason)

    def all_sessions_portal_sync(self):
        """
        This is called by the server when it reboots. It syncs all session data
        to the portal. Returns a deferred!
        """
        sessdata = self.get_all_sync_data()
        return self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SSYNC,
                                                         data=sessdata)

    def disconnect_all_sessions(self, reason="You have been disconnected."):
        """
        Cleanly disconnect all of the connected sessions.
        """

        for session in self.sessions:
            del session
        # tell portal to disconnect all sessions
        self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SDISCONNALL,
                                                         data=reason)

    def disconnect_duplicate_sessions(self, curr_session,
                      reason=_("Logged in from elsewhere. Disconnecting.")):
        """
        Disconnects any existing sessions with the same user.
        """
        uid = curr_session.uid
        doublet_sessions = [sess for sess in self.sessions.values()
                            if sess.logged_in
                            and sess.uid == uid
                            and sess != curr_session]
        for session in doublet_sessions:
            self.disconnect(session, reason)

    def validate_sessions(self):
        """
        Check all currently connected sessions (logged in and not)
        and see if any are dead or idle
        """
        tcurr = time()
        reason = _("Idle timeout exceeded, disconnecting.")
        for session in (session for session in self.sessions.values()
                        if session.logged_in and _IDLE_TIMEOUT > 0
                        and (tcurr - session.cmd_last) > _IDLE_TIMEOUT):
            self.disconnect(session, reason=reason)

    def player_count(self):
        """
        Get the number of connected players (not sessions since a
        player may have more than one session depending on settings).
        Only logged-in players are counted here.

        Returns:
            nplayer (int): Number of connected players

        """
        return len(set(session.uid for session in self.sessions.values() if session.logged_in))

    def all_connected_players(self):
        """
        Get a unique list of connected and logged-in Players.

        Returns:
            players (list): All conected Players (which may be fewer than the
                amount of Sessions due to multi-playing).

        """
        return list(set(session.player for session in self.sessions.values() if session.logged_in and session.player))

    def session_from_sessid(self, sessid):
        """
        Return session based on sessid, or None if not found
        """
        if is_iter(sessid):
            return [self.sessions.get(sid) for sid in sessid if sid in self.sessions]
        return self.sessions.get(sessid)

    def session_from_player(self, player, sessid):
        """
        Given a player and a session id, return the actual session object
        """
        if is_iter(sessid):
            sessions = [self.sessions.get(sid) for sid in sessid]
            s = [sess for sess in sessions if sess and sess.logged_in and player.uid == sess.uid]
            return s
        session = self.sessions.get(sessid)
        return session and session.logged_in and player.uid == session.uid and session or None

    def sessions_from_player(self, player):
        """
        Given a player, return all matching sessions.
        """
        uid = player.uid
        return [session for session in self.sessions.values() if session.logged_in and session.uid == uid]

    def sessions_from_puppet(self, puppet):
        """
        Given a puppeted object, return all controlling sessions.
        """
        sessid = puppet.sessid.get()
        if is_iter(sessid):
            return [self.sessions.get(sid) for sid in sessid if sid in self.sessions]
        return self.sessions.get(sessid)
    sessions_from_character = sessions_from_puppet

    def announce_all(self, message):
        """
        Send message to all connected sessions
        """
        for sess in self.sessions.values():
            self.data_out(sess, message)

    def data_out(self, session, text="", **kwargs):
        """
        Sending data Server -> Portal

        Args:
            session (Session): Session object
            text (str, optional): text data to return
            _nomulti (bool, optional): if given, only this
                session will receive the rest of the data,
                regardless of MULTISESSION_MODE. This is an
                internal variable that will not be passed on.
                This is ignored for MULTISESSION_MODE = 1,
                since all messages are mirrored everywhere for
                that.
            _forced_nomulti (bool, optional): Like _nomulti,
                but works even when MULTISESSION_MODE = 1.
                Useful for connection handling messages.

        """
        sessions = make_iter(session)
        session = sessions[0]
        text = text and to_str(to_unicode(text), encoding=session.encoding)
        multi = not kwargs.pop("_nomulti", None)
        forced_nomulti = kwargs.pop("_forced_nomulti", None)
        # Mode 1 mirrors to all.
        if _MULTISESSION_MODE == 1:
            multi = True
        # ...Unless we're absolutely sure.
        if forced_nomulti:
            multi = False

        if multi:
            if _MULTISESSION_MODE == 1:
                if session.player:
                    sessions = self.sessions_from_player(session.player)
            if _MULTISESSION_MODE == 2:
                if session.player:
                    sessions = self.sessions_from_player(session.player)
            elif _MULTISESSION_MODE == 3:
                if session.puppet:
                    sessions = self.sessions_from_puppet(session.puppet)
                elif session.player:
                    sessions = self.sessions_from_player(session.player)

        # send to all found sessions
        for session in sessions:
            self.server.amp_protocol.call_remote_MsgServer2Portal(sessid=session.sessid,
                                                                  msg=text,
                                                                  data=kwargs)

    def data_in(self, sessid, text="", **kwargs):
        """
        Data Portal -> Server.
        We also intercept OOB communication here.
        """
        session = self.sessions.get(sessid, None)
        if session:
            text = text and to_unicode(strip_control_sequences(text), encoding=session.encoding)
            if "oob" in kwargs:
                # incoming data is always on the form (cmdname, args, kwargs)
                global _OOB_HANDLER
                if not _OOB_HANDLER:
                    from evennia.server.oobhandler import OOB_HANDLER as _OOB_HANDLER
                funcname, args, kwargs = kwargs.pop("oob")
                #print "OOB session.data_in:", funcname, args, kwargs
                if funcname:
                    _OOB_HANDLER.execute_cmd(session, funcname, *args, **kwargs)

            # pass the rest off to the session
            session.data_in(text=text, **kwargs)

SESSION_HANDLER = ServerSessionHandler()
SESSIONS = SESSION_HANDLER # legacy
