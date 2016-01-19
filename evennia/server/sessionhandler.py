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
from builtins import object
from future.utils import listvalues

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

class DummySession(object):
    sessid = 0
DUMMYSESSION = DummySession()

# AMP signals
PCONN = chr(1)        # portal session connect
PDISCONN = chr(2)     # portal session disconnect
PSYNC = chr(3)        # portal session sync
SLOGIN = chr(4)       # server session login
SDISCONN = chr(5)     # server session disconnect
SDISCONNALL = chr(6)  # server session disconnect all
SSHUTD = chr(7)       # server shutdown
SSYNC = chr(8)        # server session sync
SCONN = chr(11)        # server portal connection (for bots)
PCONNSYNC = chr(12)   # portal post-syncing session

# i18n
from django.utils.translation import ugettext as _

_SERVERNAME = settings.SERVERNAME
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_IDLE_TIMEOUT = settings.IDLE_TIMEOUT
_MAX_SERVER_COMMANDS_PER_SECOND = 100.0
_MAX_SESSION_COMMANDS_PER_SECOND = 5.0


def delayed_import():
    """
    Helper method for delayed import of all needed entities.

    """
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

class SessionHandler(dict):
    """
    This handler holds a stack of sessions.

    """
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
            return listvalues(self)
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

    def __init__(self, *args, **kwargs):
        """
        Init the handler.

        """
        super(ServerSessionHandler, self).__init__(*args, **kwargs)
        self.server = None
        self.server_data = {"servername": _SERVERNAME}

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
        global _ServerSession, _PlayerDB, _ScriptDB

        sess = _ServerSession()
        sess.sessionhandler = self
        sess.load_sync_data(portalsessiondata)
        if sess.logged_in and sess.uid:
            # this can happen in the case of auto-authenticating
            # protocols like SSH
            sess.player = _PlayerDB.objects.get_player_from_uid(sess.uid)
        sess.at_sync()
        # validate all scripts
        _ScriptDB.objects.validate()
        self[sess.sessid] = sess
        sess.data_in(CMD_LOGINSTART)

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
        global _ServerSession, _PlayerDB, _ServerConfig, _ScriptDB

        for sess in self.values():
            # we delete the old session to make sure to catch eventual
            # lingering references.
            del sess

        for sessid, sessdict in portalsessionsdata.items():
            sess = _ServerSession()
            sess.sessionhandler = self
            sess.load_sync_data(sessdict)
            if sess.uid:
                sess.player = _PlayerDB.objects.get_player_from_uid(sess.uid)
            self[sessid] = sess
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
            The new session will use the supplied player-bot uid to
            initiate an already logged-in connection. The Portal will
            treat this as a normal connection and henceforth so will
            the Server.

        """
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION, operation=SCONN,
                                protocol_path=protocol_path, config=configdict)

    def portal_shutdown(self):
        """
        Called by server when shutting down the portal.

        """
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION,
                                                         operation=SSHUTD)

    def login(self, session, player, testmode=False):
        """
        Log in the previously unloggedin session and the player we by
        now should know is connected to it. After this point we assume
        the session to be logged in one way or another.

        Args:
            session (Session): The Session to authenticate.
            player (Player): The Player identified as associated with this Session.
            testmode (bool, optional): This is used by unittesting for
                faking login without any AMP being actually active.

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
        if not testmode:
            self.server.amp_protocol.send_AdminServer2Portal(session,
                                                         operation=SLOGIN,
                                                         sessiondata={"logged_in": True})
        player.at_post_login(session=session)

    def disconnect(self, session, reason=""):
        """
        Called from server side to remove session and inform portal
        of this fact.

        Args:
            session (Session): The Session to disconnect.
            reason (str, optional): A motivation for the disconnect.

        """
        session = self.get(session.sessid)
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
        del self[sessid]
        # inform portal that session should be closed.
        self.server.amp_protocol.send_AdminServer2Portal(session,
                                                         operation=SDISCONN,
                                                         reason=reason)

    def all_sessions_portal_sync(self):
        """
        This is called by the server when it reboots. It syncs all session data
        to the portal. Returns a deferred!

        """
        sessdata = self.get_all_sync_data()
        return self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION,
                                                         operation=SSYNC,
                                                         sessiondata=sessdata)

    def disconnect_all_sessions(self, reason="You have been disconnected."):
        """
        Cleanly disconnect all of the connected sessions.

        Args:
            reason (str, optional): The reason for the disconnection.

        """

        for session in self:
            del session
        # tell portal to disconnect all sessions
        self.server.amp_protocol.send_AdminServer2Portal(DUMMYSESSION,
                                                         operation=SDISCONNALL,
                                                         reason=reason)

    def disconnect_duplicate_sessions(self, curr_session,
                      reason=_("Logged in from elsewhere. Disconnecting.")):
        """
        Disconnects any existing sessions with the same user.

        args:
            curr_session (Session): Disconnect all Sessions matching this one.
            reason (str, optional): A motivation for disconnecting.

        """
        uid = curr_session.uid
        doublet_sessions = [sess for sess in self.values()
                            if sess.logged_in
                            and sess.uid == uid
                            and sess != curr_session]
        for session in doublet_sessions:
            self.disconnect(session, reason)

    def validate_sessions(self):
        """
        Check all currently connected sessions (logged in and not) and
        see if any are dead or idle.

        """
        tcurr = time()
        reason = _("Idle timeout exceeded, disconnecting.")
        for session in (session for session in self.values()
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
        return len(set(session.uid for session in self.values() if session.logged_in))

    def all_connected_players(self):
        """
        Get a unique list of connected and logged-in Players.

        Returns:
            players (list): All conected Players (which may be fewer than the
                amount of Sessions due to multi-playing).

        """
        return list(set(session.player for session in self.values() if session.logged_in and session.player))

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

    def session_from_player(self, player, sessid):
        """
        Given a player and a session id, return the actual session
        object.

        Args:
            player (Player): The Player to get the Session from.
            sessid (int or list): Session id(s).

        Returns:
            sessions (Session or list): Session(s) found.

        """
        sessions = [self[sid] for sid in make_iter(sessid)
                    if sid in self and self[sid].logged_in and player.uid == self[sid].uid]
        return sessions[0] if len(sessions) == 1 else sessions

    def sessions_from_player(self, player):
        """
        Given a player, return all matching sessions.

        Args:
            player (Player): Player to get sessions from.

        Returns:
            sessions (list): All Sessions associated with this player.

        """
        uid = player.uid
        return [session for session in self.values() if session.logged_in and session.uid == uid]

    def sessions_from_puppet(self, puppet):
        """
        Given a puppeted object, return all controlling sessions.

        Args:
            puppet (Object): Object puppeted

        Returns.
            sessions (Session or list): Can be more than one of Object is controlled by
                more than one Session (MULTISESSION_MODE > 1).

        """
        sessions = puppet.sessid.get()
        return sessions[0] if len(sessions) == 1 else sessions
    sessions_from_character = sessions_from_puppet

    def announce_all(self, message):
        """
        Send message to all connected sessions

        Args:
            message (str): Message to send.

        """
        for sess in self.values():
            self.data_out(sess, message)

    def data_out(self, session, text="", **kwargs):
        """
        Sending data Server -> Portal

        Args:
            session (Session): Session to relay to.
            text (str, optional): text data to return

        """
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "ServerSessionHandler.data_out")

        try:
            text = text and to_str(to_unicode(text), encoding=session.encoding)
        except LookupError:
            # wrong encoding set on the session. Set it to a safe one
            session.encoding = "utf-8"
            text = to_str(to_unicode(text), encoding=session.encoding)


        # send across AMP
        self.server.amp_protocol.send_MsgServer2Portal(session,
                                                       text=text,
                                                       **kwargs)

    def data_in(self, session, text="", **kwargs):
        """
        Data Portal -> Server.
        We also intercept OOB communication here.

        Args:
            sessions (Session): Session.

        Kwargs:
            text (str): Text from protocol.
            kwargs (any): Other data from protocol.

        """
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "ServerSessionHandler.data_in")
        if session:
            text = text and to_unicode(strip_control_sequences(text), encoding=session.encoding)
            if "oob" in kwargs:
                # incoming data is always on the form (cmdname, args, kwargs)
                global _OOB_HANDLER
                if not _OOB_HANDLER:
                    from evennia.server.oobhandler import OOB_HANDLER as _OOB_HANDLER
                funcname, args, kwargs = kwargs.pop("oob")
                if funcname:
                    _OOB_HANDLER.execute_cmd(session, funcname, *args, **kwargs)

            # pass the rest off to the session
            session.data_in(text=text, **kwargs)

SESSION_HANDLER = ServerSessionHandler()
SESSIONS = SESSION_HANDLER # legacy
