"""
Sessionhandler for portal sessions
"""


import time
from collections import deque, namedtuple
from twisted.internet import reactor
from django.conf import settings
from evennia.server.sessionhandler import SessionHandler, PCONN, PDISCONN, PCONNSYNC, PDISCONNALL
from evennia.utils.logger import log_trace

# module import
_MOD_IMPORT = None

# global throttles
_MAX_CONNECTION_RATE = float(settings.MAX_CONNECTION_RATE)
# per-session throttles
_MAX_COMMAND_RATE = float(settings.MAX_COMMAND_RATE)
_MAX_CHAR_LIMIT = int(settings.MAX_CHAR_LIMIT)

_MIN_TIME_BETWEEN_CONNECTS = 1.0 / float(_MAX_CONNECTION_RATE)
_MIN_TIME_BETWEEN_COMMANDS = 1.0 / float(_MAX_COMMAND_RATE)

_ERROR_COMMAND_OVERFLOW = settings.COMMAND_RATE_WARNING
_ERROR_MAX_CHAR = settings.MAX_CHAR_LIMIT_WARNING

_CONNECTION_QUEUE = deque()

DUMMYSESSION = namedtuple("DummySession", ["sessid"])(0)

# -------------------------------------------------------------
# Portal-SessionHandler class
# -------------------------------------------------------------


class PortalSessionHandler(SessionHandler):
    """
    This object holds the sessions connected to the portal at any time.
    It is synced with the server's equivalent SessionHandler over the AMP
    connection.

    Sessions register with the handler using the connect() method. This
    will assign a new unique sessionid to the session and send that sessid
    to the server using the AMP connection.

    """

    def __init__(self, *args, **kwargs):
        """
        Init the handler

        """
        super().__init__(*args, **kwargs)
        self.portal = None
        self.latest_sessid = 0
        self.uptime = time.time()
        self.connection_time = 0

        self.connection_last = self.uptime
        self.connection_task = None

    def at_server_connection(self):
        """
        Called when the Portal establishes connection with the Server.
        At this point, the AMP connection is already established.

        """
        self.connection_time = time.time()

    def connect(self, session):
        """
        Called by protocol at first connect. This adds a not-yet
        authenticated session using an ever-increasing counter for
        sessid.

        Args:
            session (PortalSession): The Session connecting.

        Notes:
            We implement a throttling mechanism here to limit the speed at
            which new connections are accepted - this is both a stop
            against DoS attacks as well as helps using the Dummyrunner
            tester with a large number of connector dummies.

        """
        global _CONNECTION_QUEUE

        if session:
            # assign if we are first-connectors
            if not session.sessid:
                # if the session already has a sessid (e.g. being inherited in the
                # case of a webclient auto-reconnect), keep it
                self.latest_sessid += 1
                session.sessid = self.latest_sessid
            session.server_connected = False
            _CONNECTION_QUEUE.appendleft(session)
            if len(_CONNECTION_QUEUE) > 1:
                session.data_out(
                    text=[
                        [
                            "%s DoS protection is active. You are queued to connect in %g seconds ..."
                            % (
                                settings.SERVERNAME,
                                len(_CONNECTION_QUEUE) * _MIN_TIME_BETWEEN_CONNECTS,
                            )
                        ],
                        {},
                    ]
                )
        now = time.time()
        if (
            now - self.connection_last < _MIN_TIME_BETWEEN_CONNECTS
        ) or not self.portal.amp_protocol:
            if not session or not self.connection_task:
                self.connection_task = reactor.callLater(
                    _MIN_TIME_BETWEEN_CONNECTS, self.connect, None
                )
            self.connection_last = now
            return
        elif not session:
            if _CONNECTION_QUEUE:
                # keep launching tasks until queue is empty
                self.connection_task = reactor.callLater(
                    _MIN_TIME_BETWEEN_CONNECTS, self.connect, None
                )
            else:
                self.connection_task = None
        self.connection_last = now

        if _CONNECTION_QUEUE:
            # sync with server-side
            session = _CONNECTION_QUEUE.pop()
            sessdata = session.get_sync_data()

            self[session.sessid] = session
            session.server_connected = True
            self.portal.amp_protocol.send_AdminPortal2Server(
                session, operation=PCONN, sessiondata=sessdata
            )

    def sync(self, session):
        """
        Called by the protocol of an already connected session. This
        can be used to sync the session info in a delayed manner, such
        as when negotiation and handshakes are delayed.

        Args:
            session (PortalSession): Session to sync.

        """
        if session.sessid and session.server_connected:
            # only use if session already has sessid and has already connected
            # once to the server - if so we must re-sync woth the server, otherwise
            # we skip this step.
            sessdata = session.get_sync_data()
            if self.portal.amp_protocol:
                # we only send sessdata that should not have changed
                # at the server level at this point
                sessdata = dict(
                    (key, val)
                    for key, val in sessdata.items()
                    if key
                    in (
                        "protocol_key",
                        "address",
                        "sessid",
                        "csessid",
                        "conn_time",
                        "protocol_flags",
                        "server_data",
                    )
                )
                self.portal.amp_protocol.send_AdminPortal2Server(
                    session, operation=PCONNSYNC, sessiondata=sessdata
                )

    def disconnect(self, session):
        """
        Called from portal when the connection is closed from the
        portal side.

        Args:
            session (PortalSession): Session to disconnect.
            delete (bool, optional): Delete the session from
                the handler. Only time to not do this is when
                this is called from a loop, such as from
                self.disconnect_all().

        """
        global _CONNECTION_QUEUE
        if session in _CONNECTION_QUEUE:
            # connection was already dropped before we had time
            # to forward this to the Server, so now we just remove it.
            _CONNECTION_QUEUE.remove(session)
            return

        if session.sessid in self and not hasattr(self, "_disconnect_all"):
            # if this was called directly from the protocol, the
            # connection is already dead and we just need to cleanup
            del self[session.sessid]

        # Tell the Server to disconnect its version of the Session as well.
        self.portal.amp_protocol.send_AdminPortal2Server(session, operation=PDISCONN)

    def disconnect_all(self):
        """
        Disconnect all sessions, informing the Server.
        """

        def _callback(result, sessionhandler):
            # we set a watchdog to stop self.disconnect from deleting
            # sessions while we are looping over them.
            sessionhandler._disconnect_all = True
            for session in sessionhandler.values():
                session.disconnect()
            del sessionhandler._disconnect_all

        # inform Server; wait until finished sending before we continue
        # removing all the sessions.
        self.portal.amp_protocol.send_AdminPortal2Server(
            DUMMYSESSION, operation=PDISCONNALL
        ).addCallback(_callback, self)

    def server_connect(self, protocol_path="", config=dict()):
        """
        Called by server to force the initialization of a new protocol
        instance. Server wants this instance to get a unique sessid
        and to be connected back as normal. This is used to initiate
        irc/rss etc connections.

        Args:
            protocol_path (st): Full python path to the class factory
                for the protocol used, eg
                'evennia.server.portal.irc.IRCClientFactory'
            config (dict): Dictionary of configuration options, fed as
                **kwarg to protocol class' __init__ method.

        Raises:
            RuntimeError: If The correct factory class is not found.

        Notes:
            The called protocol class must have a method start()
            that calls the portalsession.connect() as a normal protocol.

        """
        global _MOD_IMPORT
        if not _MOD_IMPORT:
            from evennia.utils.utils import variable_from_module as _MOD_IMPORT
        path, clsname = protocol_path.rsplit(".", 1)
        cls = _MOD_IMPORT(path, clsname)
        if not cls:
            raise RuntimeError("ServerConnect: protocol factory '%s' not found." % protocol_path)
        protocol = cls(self, **config)
        protocol.start()

    def server_disconnect(self, session, reason=""):
        """
        Called by server to force a disconnect by sessid.

        Args:
            session (portalsession): Session to disconnect.
            reason (str, optional): Motivation for disconnect.

        """
        if session:
            session.disconnect(reason)
            if session.sessid in self:
                # in case sess.disconnect doesn't delete it
                del self[session.sessid]
            del session

    def server_disconnect_all(self, reason=""):
        """
        Called by server when forcing a clean disconnect for everyone.

        Args:
            reason (str, optional): Motivation for disconnect.

        """
        for session in list(self.values()):
            session.disconnect(reason)
            del session
        self.clear()

    def server_logged_in(self, session, data):
        """
        The server tells us that the session has been authenticated.
        Update it. Called by the Server.

        Args:
            session (Session): Session logging in.
            data (dict): The session sync data.

        """
        session.load_sync_data(data)
        session.at_login()

    def server_session_sync(self, serversessions, clean=True):
        """
        Server wants to save data to the portal, maybe because it's
        about to shut down. We don't overwrite any sessions here, just
        update them in-place.

        Args:
            serversessions (dict): This is a dictionary

                `{sessid:{property:value},...}` describing
                the properties to sync on all sessions.
            clean (bool): If True, remove any Portal sessions that are
                not included in serversessions.
        """
        to_save = [sessid for sessid in serversessions if sessid in self]
        # save protocols
        for sessid in to_save:
            self[sessid].load_sync_data(serversessions[sessid])
        if clean:
            # disconnect out-of-sync missing protocols
            to_delete = [sessid for sessid in self if sessid not in to_save]
            for sessid in to_delete:
                self.server_disconnect(sessid)

    def count_loggedin(self, include_unloggedin=False):
        """
        Count loggedin connections, alternatively count all connections.

        Args:
            include_unloggedin (bool): Also count sessions that have
            not yet authenticated.

        Returns:
            count (int): Number of sessions.

        """
        return len(self.get_sessions(include_unloggedin=include_unloggedin))

    def sessions_from_csessid(self, csessid):
        """
        Given a session id, retrieve the session (this is primarily
        intended to be called by web clients)

        Args:
            csessid (int): Session id.

        Returns:
            session (list): The matching session, if found.

        """
        return [
            sess
            for sess in self.get_sessions(include_unloggedin=True)
            if hasattr(sess, "csessid") and sess.csessid and sess.csessid == csessid
        ]

    def announce_all(self, message):
        """
        Send message to all connected sessions.

        Args:
            message (str):  Message to relay.

        Notes:
            This will create an on-the fly text-type
            send command.

        """
        for session in self.values():
            self.data_out(session, text=[[message], {}])

    def data_in(self, session, **kwargs):
        """
        Called by portal sessions for relaying data coming
        in from the protocol to the server.

        Args:
            session (PortalSession): Session receiving data.

        Kwargs:
            kwargs (any): Other data from protocol.

        Notes:
            Data is serialized before passed on.

        """
        try:
            text = kwargs["text"]
            if (_MAX_CHAR_LIMIT > 0) and len(text) > _MAX_CHAR_LIMIT:
                if session:
                    self.data_out(session, text=[[_ERROR_MAX_CHAR], {}])
                return
        except Exception:
            # if there is a problem to send, we continue
            pass
        if session:
            now = time.time()

            try:
                command_counter_reset = session.command_counter_reset
            except AttributeError:
                command_counter_reset = session.command_counter_reset = now
                session.command_counter = 0

            # global command-rate limit
            if max(0, now - command_counter_reset) > 1.0:
                # more than a second since resetting the counter. Refresh.
                session.command_counter_reset = now
                session.command_counter = 0

            session.command_counter += 1

            if session.command_counter * _MIN_TIME_BETWEEN_COMMANDS > 1.0:
                self.data_out(session, text=[[_ERROR_COMMAND_OVERFLOW], {}])
                return

            if not self.portal.amp_protocol:
                # this can happen if someone connects before AMP connection
                # was established (usually on first start)
                reactor.callLater(1.0, self.data_in, session, **kwargs)
                return

            # scrub data
            kwargs = self.clean_senddata(session, kwargs)

            # relay data to Server
            session.cmd_last = now
            self.portal.amp_protocol.send_MsgPortal2Server(session, **kwargs)

    def data_out(self, session, **kwargs):
        """
        Called by server for having the portal relay messages and data
        to the correct session protocol.

        Args:
            session (Session): Session sending data.

        Kwargs:
            kwargs (any): Each key is a command instruction to the
            protocol on the form key = [[args],{kwargs}]. This will
            call a method send_<key> on the protocol. If no such
            method exixts, it sends the data to a method send_default.

        """
        # from evennia.server.profiling.timetrace import timetrace  # DEBUG
        # text = timetrace(text, "portalsessionhandler.data_out")  # DEBUG

        # distribute outgoing data to the correct session methods.
        if session:
            for cmdname, (cmdargs, cmdkwargs) in kwargs.items():
                funcname = "send_%s" % cmdname.strip().lower()
                if hasattr(session, funcname):
                    # better to use hassattr here over try..except
                    # - avoids hiding AttributeErrors in the call.
                    try:
                        getattr(session, funcname)(*cmdargs, **cmdkwargs)
                    except Exception:
                        log_trace()
                else:
                    try:
                        # note that send_default always takes cmdname
                        # as arg too.
                        session.send_default(cmdname, *cmdargs, **cmdkwargs)
                    except Exception:
                        log_trace()


PORTAL_SESSIONS = PortalSessionHandler()
