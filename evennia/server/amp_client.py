"""
The Evennia Server service acts as an AMP-client when talking to the
Portal. This module sets up the Client-side communication.

"""

import os
from evennia.server.portal import amp
from twisted.internet import protocol
from evennia.utils import logger


class AMPClientFactory(protocol.ReconnectingClientFactory):
    """
    This factory creates an instance of an AMP client connection. This handles communication from
    the be the Evennia 'Server' service to the 'Portal'. The client will try to auto-reconnect on a
    connection error.

    """

    # Initial reconnect delay in seconds.
    initialDelay = 1
    factor = 1.5
    maxDelay = 1
    noisy = False

    def __init__(self, server):
        """
        Initializes the client factory.

        Args:
            server (server): server instance.

        """
        self.server = server
        self.protocol = AMPServerClientProtocol
        self.maxDelay = 10
        # not really used unless connecting to multiple servers, but
        # avoids having to check for its existence on the protocol
        self.broadcasts = []

    def startedConnecting(self, connector):
        """
        Called when starting to try to connect to the Portal AMP server.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.

        """
        pass

    def buildProtocol(self, addr):
        """
        Creates an AMPProtocol instance when connecting to the AMP server.

        Args:
            addr (str): Connection address. Not used.

        """
        self.resetDelay()
        self.server.amp_protocol = AMPServerClientProtocol()
        self.server.amp_protocol.factory = self
        return self.server.amp_protocol

    def clientConnectionLost(self, connector, reason):
        """
        Called when the AMP connection to the MUD server is lost.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.
            reason (str): Eventual text describing why connection was lost.

        """
        logger.log_info("Server disconnected from the portal.")
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when an AMP connection attempt to the MUD server fails.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.
            reason (str): Eventual text describing why connection failed.

        """
        logger.log_msg("Attempting to reconnect to Portal ...")
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class AMPServerClientProtocol(amp.AMPMultiConnectionProtocol):
    """
    This protocol describes the Server service (acting as an AMP-client)'s communication with the
    Portal (which acts as the AMP-server)

    """

    # sending AMP data

    def connectionMade(self):
        """
        Called when a new connection is established.

        """
        # print("AMPClient new connection {}".format(self))
        info_dict = self.factory.server.get_info_dict()
        super(AMPServerClientProtocol, self).connectionMade()
        # first thing we do is to request the Portal to sync all sessions
        # back with the Server side. We also need the startup mode (reload, reset, shutdown)
        self.send_AdminServer2Portal(
            amp.DUMMYSESSION, operation=amp.PSYNC, spid=os.getpid(), info_dict=info_dict
        )
        # run the intial setup if needed
        self.factory.server.run_initial_setup()

    def data_to_portal(self, command, sessid, **kwargs):
        """
        Send data across the wire to the Portal

        Args:
            command (AMP Command): A protocol send command.
            sessid (int): A unique Session id.
            kwargs (any): Any data to pickle into the command.

        Returns:
            deferred (deferred or None): A deferred with an errback.

        Notes:
            Data will be sent across the wire pickled as a tuple
            (sessid, kwargs).

        """
        # print("server data_to_portal: {}, {}, {}".format(command, sessid, kwargs))
        return self.callRemote(command, packed_data=amp.dumps((sessid, kwargs))).addErrback(
            self.errback, command.key
        )

    def send_MsgServer2Portal(self, session, **kwargs):
        """
        Access method - executed on the Server for sending data
            to Portal.

        Args:
            session (Session): Unique Session.
            kwargs (any, optiona): Extra data.

        """
        return self.data_to_portal(amp.MsgServer2Portal, session.sessid, **kwargs)

    def send_AdminServer2Portal(self, session, operation="", **kwargs):
        """
        Administrative access method called by the Server to send an
        instruction to the Portal.

        Args:
            session (Session): Session.
            operation (char, optional): Identifier for the server
                operation, as defined by the global variables in
                `evennia/server/amp.py`.
            kwargs (dict, optional): Data going into the adminstrative.

        """
        return self.data_to_portal(
            amp.AdminServer2Portal, session.sessid, operation=operation, **kwargs
        )

    # receiving AMP data

    @amp.MsgStatus.responder
    def server_receive_status(self, question):
        return {"status": "OK"}

    @amp.MsgPortal2Server.responder
    @amp.catch_traceback
    def server_receive_msgportal2server(self, packed_data):
        """
        Receives message arriving to server. This method is executed
        on the Server.

        Args:
            packed_data (str): Data to receive (a pickled tuple (sessid,kwargs))

        """
        sessid, kwargs = self.data_in(packed_data)
        session = self.factory.server.sessions.get(sessid, None)
        if session:
            self.factory.server.sessions.data_in(session, **kwargs)
        return {}

    @amp.AdminPortal2Server.responder
    @amp.catch_traceback
    def server_receive_adminportal2server(self, packed_data):
        """
        Receives admin data from the Portal (allows the portal to
        perform admin operations on the server). This is executed on
        the Server.

        Args:
            packed_data (str): Incoming, pickled data.

        """
        sessid, kwargs = self.data_in(packed_data)
        operation = kwargs.pop("operation", "")
        server_sessionhandler = self.factory.server.sessions

        if operation == amp.PCONN:  # portal_session_connect
            # create a new session and sync it
            server_sessionhandler.portal_connect(kwargs.get("sessiondata"))

        elif operation == amp.PCONNSYNC:  # portal_session_sync
            server_sessionhandler.portal_session_sync(kwargs.get("sessiondata"))

        elif operation == amp.PDISCONN:  # portal_session_disconnect
            # session closed from portal sid
            session = server_sessionhandler.get(sessid)
            if session:
                server_sessionhandler.portal_disconnect(session)

        elif operation == amp.PDISCONNALL:  # portal_disconnect_all
            # portal orders all sessions to close
            server_sessionhandler.portal_disconnect_all()

        elif operation == amp.PSYNC:  # portal_session_sync
            # force a resync of sessions from the portal side. This happens on
            # first server-connect.
            server_restart_mode = kwargs.get("server_restart_mode", "shutdown")
            self.factory.server.run_init_hooks(server_restart_mode)
            server_sessionhandler.portal_sessions_sync(kwargs.get("sessiondata"))
            server_sessionhandler.portal_start_time = kwargs.get("portal_start_time")

        elif operation == amp.SRELOAD:  # server reload
            # shut down in reload mode
            server_sessionhandler.all_sessions_portal_sync()
            server_sessionhandler.server.shutdown(mode="reload")

        elif operation == amp.SRESET:
            # shut down in reset mode
            server_sessionhandler.all_sessions_portal_sync()
            server_sessionhandler.server.shutdown(mode="reset")

        elif operation == amp.SSHUTD:  # server shutdown
            # shutdown in stop mode
            server_sessionhandler.server.shutdown(mode="shutdown")

        else:
            raise Exception("operation %(op)s not recognized." % {"op": operation})

        return {}
