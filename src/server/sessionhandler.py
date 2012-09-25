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

import time
from django.conf import settings
from src.commands.cmdhandler import CMD_LOGINSTART

_PLAYERDB = None

# AMP signals
PCONN = chr(1)       # portal session connect
PDISCONN = chr(2)    # portal session disconnect
PSYNC = chr(3)       # portal session sync
SLOGIN = chr(4)      # server session login
SDISCONN = chr(5)    # server session disconnect
SDISCONNALL = chr(6) # server session disconnect all
SSHUTD = chr(7)      # server shutdown
SSYNC = chr(8)       # server session sync

# i18n
from django.utils.translation import ugettext as _

SERVERNAME = settings.SERVERNAME
ALLOW_MULTISESSION = settings.ALLOW_MULTISESSION
IDLE_TIMEOUT = settings.IDLE_TIMEOUT

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
        self.server_data = {"servername":SERVERNAME}

    def portal_connect(self, sessid, session):
        """
        Called by Portal when a new session has connected.
        Creates a new, unlogged-in game session.
        """
        self.sessions[sessid] = session
        session.execute_cmd(CMD_LOGINSTART)

    def portal_disconnect(self, sessid):
        """
        Called by Portal when portal reports a closing of a session
        from the portal side.
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.disconnect()
            del self.sessions[session.sessid]
            self.session_count(-1)

    def portal_session_sync(self, sesslist):
        """
        Syncing all session ids of the portal with the ones of the server. This is instantiated
        by the portal when reconnecting.

        sesslist is a complete list of (sessid, session) pairs, matching the list on the portal.
                 if session was logged in, the amp handler will have logged them in before this point.
        """
        for sess in self.sessions.values():
            # we delete the old session to make sure to catch eventual lingering references.
            del sess
        for sess in sesslist:
            self.sessions[sess.sessid] = sess
            sess.at_sync()

    def portal_shutdown(self):
        """
        Called by server when shutting down the portal.
        """
        self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SSHUTD,
                                                         data="")
    # server-side access methods

    def disconnect(self, session, reason=""):
        """
        Called from server side to remove session and inform portal
        of this fact.
        """
        session = self.sessions.get(session.sessid, None)
        if session:
            sessid = session.sessid
            del self.sessions[sessid]
            # inform portal that session should be closed.
            self.server.amp_protocol.call_remote_PortalAdmin(sessid,
                                                             operation=SDISCONN,
                                                             data=reason)

    def login(self, session):
        """
        Log in the previously unloggedin session and the player we by
        now should know is connected to it. After this point we
        assume the session to be logged in one way or another.
        """
        # prep the session with player/user info

        if not ALLOW_MULTISESSION:
            # disconnect previous sessions.
            self.disconnect_duplicate_sessions(session)
        session.logged_in = True
        # sync the portal to this session
        sessdata = session.get_sync_data()
        self.server.amp_protocol.call_remote_PortalAdmin(session.sessid,
                                                         operation=SLOGIN,
                                                         data=sessdata)

    def all_sessions_portal_sync(self):
        """
        This is called by the server when it reboots. It syncs all session data
        to the portal. Returns a deferred!
        """
        sessdata = self.get_all_sync_data()
        return self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SSYNC,
                                                         data=sessdata)


    def disconnect_all_sessions(self, reason=_("You have been disconnected.")):
        """
        Cleanly disconnect all of the connected sessions.
        """

        for session in self.sessions:
            del session
        # tell portal to disconnect all sessions
        self.server.amp_protocol.call_remote_PortalAdmin(0,
                                                         operation=SDISCONNALL,
                                                         data=reason)

    def disconnect_duplicate_sessions(self, curr_session, reason = _("Logged in from elsewhere. Disconnecting.") ):
        """
        Disconnects any existing sessions with the same game object.
        """
        curr_char = curr_session.get_character()
        doublet_sessions = [sess for sess in self.sessions.values()
                            if sess.logged_in
                            and sess.get_character() == curr_char
                            and sess != curr_session]
        for session in doublet_sessions:
            self.disconnect(session, reason)

    def validate_sessions(self):
        """
        Check all currently connected sessions (logged in and not)
        and see if any are dead.
        """
        tcurr = time.time()
        reason= _("Idle timeout exceeded, disconnecting.")
        for session in (session for session in self.sessions.values()
                        if session.logged_in and IDLE_TIMEOUT > 0
                        and (tcurr - session.cmd_last) > IDLE_TIMEOUT):
            self.disconnect(session, reason=reason)

    def player_count(self):
        """
        Get the number of connected players (not sessions since a player
        may have more than one session connected if ALLOW_MULTISESSION is True)
        Only logged-in players are counted here.
        """
        return len(set(session.uid for session in self.sessions.values() if session.logged_in))

    def sessions_from_player(self, player):
        """
        Given a player, return any matching sessions.
        """
        uid = player.uid
        return [session for session in self.sessions.values() if session.logged_in and session.uid == uid]

    def sessions_from_character(self, character):
        """
        Given a game character, return any matching sessions.
        """
        player = character.player
        if player:
            return self.sessions_from_player(player)
        return None

    def announce_all(self, message):
        """
        Send message to all connected sessions
        """
        for sess in self.sessions.values():
            self.data_out(sess, message)

    def data_out(self, session, string="", data=""):
        """
        Sending data Server -> Portal
        """
        self.server.amp_protocol.call_remote_MsgServer2Portal(sessid=session.sessid,
                                                              msg=string,
                                                              data=data)
    def data_in(self, sessid, string="", data=""):
        """
        Data Portal -> Server
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.execute_cmd(string)

        # ignore 'data' argument for now; this is otherwise the place
        # to put custom effects on the server due to data input, e.g.
        # from a custom client.

    def oob_data_in(self, sessid, data):
        """
        OOB (Out-of-band) Data Portal -> Server
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.oob_data_in(data)

    def oob_data_out(self, session, data):
        """
        OOB (Out-of-band) Data Server -> Portal
        """
        self.server.amp_protocol.call_remote_OOBServer2Portal(session.sessid,
                                                              data=data)

#------------------------------------------------------------
# Portal-SessionHandler class
#------------------------------------------------------------

class PortalSessionHandler(SessionHandler):
    """
    This object holds the sessions connected to the portal at any time.
    It is synced with the server's equivalent SessionHandler over the AMP
    connection.

    Sessions register with the handler using the connect() method. This
    will assign a new unique sessionid to the session and send that sessid
    to the server using the AMP connection.

    """

    def __init__(self):
        """
        Init the handler
        """
        self.portal = None
        self.sessions = {}
        self.latest_sessid = 0
        self.uptime = time.time()
        self.connection_time = 0

    def at_server_connection(self):
        """
        Called when the Portal establishes connection with the
        Server. At this point, the AMP connection is already
        established.
        """
        self.connection_time = time.time()

    def connect(self, session):
        """
        Called by protocol at first connect. This adds a not-yet authenticated session
        using an ever-increasing counter for sessid.
        """
        self.latest_sessid += 1
        sessid = self.latest_sessid
        session.sessid = sessid
        sessdata = session.get_sync_data()
        self.sessions[sessid] = session
        # sync with server-side
        self.portal.amp_protocol.call_remote_ServerAdmin(sessid,
                                                         operation=PCONN,
                                                         data=sessdata)
    def disconnect(self, session):
        """
        Called from portal side when the connection is closed from the portal side.
        """
        sessid = session.sessid
        self.portal.amp_protocol.call_remote_ServerAdmin(sessid,
                                                         operation=PDISCONN)

    def server_disconnect(self, sessid, reason=""):
        """
        Called by server to force a disconnect by sessid
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.disconnect(reason)
            if sessid in self.sessions:
                # in case sess.disconnect doesn't delete it
                del self.sessions[sessid]
            del session

    def server_disconnect_all(self, reason=""):
        """
        Called by server when forcing a clean disconnect for everyone.
        """
        for session in self.sessions.values():
            session.disconnect(reason)
            del session
        self.sessions = {}

    def count_loggedin(self, include_unloggedin=False):
        """
        Count loggedin connections, alternatively count all connections.
        """
        return len(self.get_sessions(include_unloggedin=include_unloggedin))


    def session_from_suid(self, suid):
        """
        Given a session id, retrieve the session (this is primarily
        intended to be called by web clients)
        """
        return [sess for sess in self.get_sessions(include_unloggedin=True)
                if hasattr(sess, 'suid') and sess.suid == suid]

    def data_in(self, session, string="", data=""):
        """
        Called by portal sessions for relaying data coming
        in from the protocol to the server. data is
        serialized before passed on.
        """
        #print "portal_data_in:", string
        self.portal.amp_protocol.call_remote_MsgPortal2Server(session.sessid,
                                                              msg=string,
                                                              data=data)
    def announce_all(self, message):
        """
        Send message to all connection sessions
        """
        for session in self.sessions.values():
            session.data_out(message)

    def data_out(self, sessid, string="", data=""):
        """
        Called by server for having the portal relay messages and data
        to the correct session protocol.
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.data_out(string, data=data)

    def oob_data_in(self, session, data):
        """
        OOB (Out-of-band) data Portal -> Server
        """
        print "portal_oob_data_in:", data
        self.portal.amp_protocol.call_remote_OOBPortal2Server(session.sessid,
                                                              data=data)

    def oob_data_out(self, sessid, data):
        """
        OOB (Out-of-band) data Server -> Portal
        """
        print "portal_oob_data_out:", data
        session = self.sessions.get(sessid, None)
        if session:
            session.oob_data_out(data)

SESSIONS = ServerSessionHandler()
PORTAL_SESSIONS = PortalSessionHandler()
