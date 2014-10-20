"""
Sessionhandler for portal sessions
"""
import time
from src.server.sessionhandler import SessionHandler, PCONN, PDISCONN, PSYNC, PCONNSYNC

_MOD_IMPORT = None

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
        Called by protocol at first connect. This adds a not-yet
        authenticated session using an ever-increasing counter for sessid.
        """
        self.latest_sessid += 1
        sessid = self.latest_sessid
        session.sessid = sessid
        sessdata = session.get_sync_data()
        self.sessions[sessid] = session
        # sync with server-side
        if self.portal.amp_protocol:  # this is a timing issue
            self.portal.amp_protocol.call_remote_ServerAdmin(sessid,
                                                         operation=PCONN,
                                                         data=sessdata)
    def sync(self, session):
        """
        Called by the protocol of an already connected session. This
        can be used to sync the session info in a delayed manner,
        such as when negotiation and handshakes are delayed.
        """
        if session.sessid:
            # only use if session already has sessid (i.e. has already connected)
            sessdata = session.get_sync_data()
            if self.portal.amp_protocol:
                # we only send sessdata that should not have changed
                # at the server level at this point
                sessdata = dict((key, val) for key, val in sessdata.items() if key in ("protocol_key",
                                                                                       "address",
                                                                                       "sessid",
                                                                                       "suid",
                                                                                       "conn_time",
                                                                                       "protocol_flags",
                                                                                       "server_data",))
                self.portal.amp_protocol.call_remote_ServerAdmin(session.sessid,
                                                                 operation=PCONNSYNC,
                                                                 data=sessdata)

    def disconnect(self, session):
        """
        Called from portal side when the connection is closed
        from the portal side.
        """
        sessid = session.sessid
        if sessid in self.sessions:
            del self.sessions[sessid]
        del session
        # tell server to also delete this session
        self.portal.amp_protocol.call_remote_ServerAdmin(sessid,
                                                         operation=PDISCONN)


    def server_connect(self, protocol_path="", config=dict()):
        """
        Called by server to force the initialization of a new
        protocol instance. Server wants this instance to get
        a unique sessid and to be connected back as normal. This
        is used to initiate irc/imc2/rss etc connections.

        protocol_path - full python path to the class factory
                    for the protocol used, eg
                    'src.server.portal.irc.IRCClientFactory'
        config - dictionary of configuration options, fed as **kwarg
                 to protocol class' __init__ method.

        The called protocol class must have a method start()
        that calls the portalsession.connect() as a normal protocol.
        """
        global _MOD_IMPORT
        if not _MOD_IMPORT:
            from src.utils.utils import variable_from_module as _MOD_IMPORT
        path, clsname = protocol_path.rsplit(".", 1)
        cls = _MOD_IMPORT(path, clsname)
        if not cls:
            raise RuntimeError("ServerConnect: protocol factory '%s' not found." % protocol_path)
        protocol = cls(self, **config)
        protocol.start()

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

    def server_logged_in(self, sessid, data):
        """
        The server tells us that the session has been
        authenticated. Updated it.
        """
        sess = self.get_session(sessid)
        sess.load_sync_data(data)

    def server_session_sync(self, serversessions):
        """
        Server wants to save data to the portal, maybe because it's about
        to shut down. We don't overwrite any sessions here, just update
        them in-place and remove any that are out of sync (which should
        normally not be the case)

        serversessions - dictionary {sessid:{property:value},...} describing
                         the properties to sync on all sessions
        """
        to_save = [sessid for sessid in serversessions if sessid in self.sessions]
        to_delete = [sessid for sessid in self.sessions if sessid not in to_save]
        # save protocols
        for sessid in to_save:
            self.sessions[sessid].load_sync_data(serversessions[sessid])
        # disconnect out-of-sync missing protocols
        for sessid in to_delete:
            self.server_disconnect(sessid)

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

    def data_in(self, session, text="", **kwargs):
        """
        Called by portal sessions for relaying data coming
        in from the protocol to the server. data is
        serialized before passed on.
        """
        self.portal.amp_protocol.call_remote_MsgPortal2Server(session.sessid,
                                                              msg=text,
                                                              data=kwargs)

    def announce_all(self, message):
        """
        Send message to all connection sessions
        """
        for session in self.sessions.values():
            session.data_out(message)

    def data_out(self, sessid, text=None, **kwargs):
        """
        Called by server for having the portal relay messages and data
        to the correct session protocol.
        """
        session = self.sessions.get(sessid, None)
        if session:
            session.data_out(text=text, **kwargs)

PORTAL_SESSIONS = PortalSessionHandler()
