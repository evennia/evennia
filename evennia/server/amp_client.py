"""
The Evennia Server service acts as an AMP-client when talking to the
Portal. This module sets up the Client-side communication.

"""

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
        Called when starting to try to connect to the MUD server.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.

        """
        pass

    def buildProtocol(self, addr):
        """
        Creates an AMPProtocol instance when connecting to the server.

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
        logger.log_info("Server lost connection to the Portal. Reconnecting ...")
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when an AMP connection attempt to the MUD server fails.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.
            reason (str): Eventual text describing why connection failed.

        """
        logger.log_info("Attempting to reconnect to Portal ...")
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class AMPServerClientProtocol(amp.AMPMultiConnectionProtocol):
    """
    This protocol describes the Server service (acting as an AMP-client)'s communication with the
    Portal (which acts as the AMP-server)

    """
    # sending AMP data

    def send_MsgServer2Portal(self, session, **kwargs):
        """
        Access method - executed on the Server for sending data
            to Portal.

        Args:
            session (Session): Unique Session.
            kwargs (any, optiona): Extra data.

        """
        return self.data_out(amp.MsgServer2Portal, session.sessid, **kwargs)

    def send_AdminServer2Portal(self, session, operation="", **kwargs):
        """
        Administrative access method called by the Server to send an
        instruction to the Portal.

        Args:
            session (Session): Session.
            operation (char, optional): Identifier for the server
                operation, as defined by the global variables in
                `evennia/server/amp.py`.
            data (str or dict, optional): Data going into the adminstrative.

        """
        return self.data_out(amp.AdminServer2Portal, session.sessid, operation=operation, **kwargs)

    # receiving AMP data

    @amp.MsgPortal2Server.responder
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
            # force a resync of sessions when portal reconnects to
            # server (e.g. after a server reboot) the data kwarg
            # contains a dict {sessid: {arg1:val1,...}}
            # representing the attributes to sync for each
            # session.
            server_sessionhandler.portal_sessions_sync(kwargs.get("sessiondata"))
        else:
            raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}
