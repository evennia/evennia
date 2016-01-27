"""
Sessionhandler for portal sessions
"""
from __future__ import print_function
from __future__ import division

from time import time
from collections import deque
from twisted.internet import reactor
from django.conf import settings
from evennia.server.sessionhandler import SessionHandler, PCONN, PDISCONN, PCONNSYNC

# module import
_MOD_IMPORT = None

# throttles
_MAX_CONNECTION_RATE = float(settings.MAX_CONNECTION_RATE)
_MAX_COMMAND_RATE = float(settings.MAX_COMMAND_RATE)

_MIN_TIME_BETWEEN_CONNECTS = 1.0 / float(settings.MAX_CONNECTION_RATE)
_ERROR_COMMAND_OVERFLOW = settings.COMMAND_RATE_WARNING

_CONNECTION_QUEUE = deque()

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

    def __init__(self, *args, **kwargs):
        """
        Init the handler

        """
        super(PortalSessionHandler, self).__init__(*args, **kwargs)
        self.portal = None
        self.latest_sessid = 0
        self.uptime = time()
        self.connection_time = 0

        self.connection_last = time()
        self.connection_task = None
        self.command_counter = 0
        self.command_counter_reset = time()
        self.command_overflow = False

    def at_server_connection(self):
        """
        Called when the Portal establishes connection with the Server.
        At this point, the AMP connection is already established.

        """
        self.connection_time = time()

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
            self.latest_sessid += 1
            session.sessid = self.latest_sessid
            session.server_connected = False
            _CONNECTION_QUEUE.appendleft(session)
            if len(_CONNECTION_QUEUE) > 1:
                session.data_out("%s DoS protection is active. You are queued to connect in %g seconds ..." % (
                                 settings.SERVERNAME,
                                 len(_CONNECTION_QUEUE)*_MIN_TIME_BETWEEN_CONNECTS))
        now = time()
        if (now - self.connection_last < _MIN_TIME_BETWEEN_CONNECTS) or not self.portal.amp_protocol:
            if not session or not self.connection_task:
                self.connection_task = reactor.callLater(_MIN_TIME_BETWEEN_CONNECTS, self.connect, None)
            self.connection_last = now
            return
        elif not session:
            if _CONNECTION_QUEUE:
                # keep launching tasks until queue is empty
                self.connection_task = reactor.callLater(_MIN_TIME_BETWEEN_CONNECTS, self.connect, None)
            else:
                self.connection_task = None
        self.connection_last = now

        if _CONNECTION_QUEUE:
            # sync with server-side
            session = _CONNECTION_QUEUE.pop()
            sessdata = session.get_sync_data()

            self[session.sessid] = session
            session.server_connected = True
            self.portal.amp_protocol.send_AdminPortal2Server(session,
                                                             operation=PCONN,
                                                             sessiondata=sessdata)

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
                sessdata = dict((key, val) for key, val in sessdata.items() if key in ("protocol_key",
                                                                                       "address",
                                                                                       "sessid",
                                                                                       "suid",
                                                                                       "conn_time",
                                                                                       "protocol_flags",
                                                                                       "server_data",))
                self.portal.amp_protocol.send_AdminPortal2Server(session,
                                                                 operation=PCONNSYNC,
                                                                 sessiondata=sessdata)

    def disconnect(self, session):
        """
        Called from portal when the connection is closed from the
        portal side.

        Args:
            session (PortalSession): Session to disconnect.

        """
        global _CONNECTION_QUEUE
        if session in _CONNECTION_QUEUE:
            # connection was already dropped before we had time
            # to forward this to the Server, so now we just remove it.
            _CONNECTION_QUEUE.remove(session)
            return
        self.portal.amp_protocol.send_AdminPortal2Server(session,
                                                         operation=PDISCONN)

    def server_connect(self, protocol_path="", config=dict()):
        """
        Called by server to force the initialization of a new protocol
        instance. Server wants this instance to get a unique sessid
        and to be connected back as normal. This is used to initiate
        irc/imc2/rss etc connections.

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
            sessid (int): Session id to disconnect.
            reason (str, optional): Motivation for disconect.

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
        for session in self.values():
            session.disconnect(reason)
            del session
        self = {}

    def server_logged_in(self, session, data):
        """
        The server tells us that the session has been authenticated.
        Update it. Called by the Server.

        Args:
            session (Session): Session logging in.
            data (dict): The session sync data.

        """
        session.load_sync_data(data)

    def server_session_sync(self, serversessions):
        """
        Server wants to save data to the portal, maybe because it's
        about to shut down. We don't overwrite any sessions here, just
        update them in-place and remove any that are out of sync
        (which should normally not be the case)

        Args:
            serversessions (dict): This is a dictionary

                `{sessid:{property:value},...}` describing
                the properties to sync on all sessions.
        """
        to_save = [sessid for sessid in serversessions if sessid in self]
        to_delete = [sessid for sessid in self if sessid not in to_save]
        # save protocols
        for sessid in to_save:
            self[sessid].load_sync_data(serversessions[sessid])
        # disconnect out-of-sync missing protocols
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

    def session_from_suid(self, suid):
        """
        Given a session id, retrieve the session (this is primarily
        intended to be called by web clients)

        Args:
            suid (int): Session id.

        Returns:
            session (list): The matching session, if found.

        """
        return [sess for sess in self.get_sessions(include_unloggedin=True)
                if hasattr(sess, 'suid') and sess.suid == suid]

    def announce_all(self, message):
        """
        Send message to all connected sessions.

        Args:
            message (str):  Message to relay.

        """
        for session in self.values():
            session.data_out(message)

    def oobstruct_parser(self, oobstruct):
        """
         Helper method for each session to use to parse oob structures
         (The 'oob' kwarg of the msg() method).

         Args:
            oobstruct (str or iterable): A structure representing
                an oob command on one of the following forms:
                    - "cmdname"
                    - "cmdname", "cmdname"
                    - ("cmdname", arg)
                    - ("cmdname",(args))
                    - ("cmdname",{kwargs}
                    - ("cmdname", (args), {kwargs})
                    - (("cmdname", (args,), {kwargs}), ("cmdname", (args,), {kwargs}))
            and any combination of argument-less commands or commands with only
            args, only kwargs or both.

        Returns:
            structure (tuple): A generic OOB structure on the form
                `((cmdname, (args,), {kwargs}), ...)`, where the two last
                args and kwargs may be empty

        """
        def _parse(oobstruct):
            slen = len(oobstruct)
            if not oobstruct:
                return tuple(None, (), {})
            elif not hasattr(oobstruct, "__iter__"):
                # a singular command name, without arguments or kwargs
                return (oobstruct, (), {})
            # regardless of number of args/kwargs, the first element must be
            # the function name. We will not catch this error if not, but
            # allow it to propagate.
            if slen == 1:
                return (oobstruct[0], (), {})
            elif slen == 2:
                if isinstance(oobstruct[1], dict):
                    # (cmdname, {kwargs})
                    return (oobstruct[0], (), dict(oobstruct[1]))
                elif isinstance(oobstruct[1], (tuple, list)):
                    # (cmdname, (args,))
                    return (oobstruct[0], tuple(oobstruct[1]), {})
                else:
                    # (cmdname, arg)
                    return (oobstruct[0], (oobstruct[1],), {})
            else:
                # (cmdname, (args,), {kwargs})
                return (oobstruct[0], tuple(oobstruct[1]), dict(oobstruct[2]))

        if hasattr(oobstruct, "__iter__"):
            # differentiate between (cmdname, cmdname),
            # (cmdname, (args), {kwargs}) and ((cmdname,(args),{kwargs}),
            # (cmdname,(args),{kwargs}), ...)

            if oobstruct and isinstance(oobstruct[0], basestring):
                return (list(_parse(oobstruct)),)
            else:
                out = []
                for oobpart in oobstruct:
                    out.append(_parse(oobpart))
                return (list(out),)
        return (_parse(oobstruct),)


    def data_in(self, session, text="", **kwargs):
        """
        Called by portal sessions for relaying data coming
        in from the protocol to the server.

        Args:
            session (PortalSession): Session receiving data.

        Kwargs:
            text (str): Text from protocol.
            kwargs (any): Other data from protocol.

        Notes:
            Data is serialized before passed on.

        """
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "portalsessionhandler.data_in")

        if session:
            now = time()
            if self.command_counter > _MAX_COMMAND_RATE:
                # data throttle (anti DoS measure)
                dT = now - self.command_counter_reset
                self.command_counter = 0
                self.command_counter_reset = now
                self.command_overflow = dT < 1.0
                if self.command_overflow:
                    reactor.callLater(1.0, self.data_in, None)
            if self.command_overflow:
                self.data_out(session, text=_ERROR_COMMAND_OVERFLOW)
                return
            # relay data to Server
            self.command_counter += 1
            session.cmd_last = now
            self.portal.amp_protocol.send_MsgPortal2Server(session,
                                                       text=text,
                                                       **kwargs)
        else:
           # called by the callLater callback
            if self.command_overflow:
                self.command_overflow = False
                reactor.callLater(1.0, self.data_in, None)


    def data_out(self, session, text=None, **kwargs):
        """
        Called by server for having the portal relay messages and data
        to the correct session protocol. We also convert oob input to
        a generic form here.

        Args:
            session (Session): Session sending data.

        Kwargs:
            text (str): Text from protocol.
            kwargs (any): Other data from protocol.

        """
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "portalsessionhandler.data_out")

        if session:
            # convert oob to the generic format
            if "oob" in kwargs:
                kwargs["oob"] = self.oobstruct_parser(kwargs["oob"])
            session.data_out(text=text, **kwargs)

PORTAL_SESSIONS = PortalSessionHandler()
