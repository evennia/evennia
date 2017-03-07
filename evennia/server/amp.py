"""
Contains the protocols, commands, and client factory needed for the Server
and Portal to communicate with each other, letting Portal work as a proxy.
Both sides use this same protocol.

The separation works like this:

Portal - (AMP client) handles protocols. It contains a list of connected
         sessions in a dictionary for identifying the respective player
         connected. If it loses the AMP connection it will automatically
         try to reconnect.

Server - (AMP server) Handles all mud operations. The server holds its own list
         of sessions tied to player objects. This is synced against the portal
         at startup and when a session connects/disconnects

"""
from __future__ import print_function

# imports needed on both server and portal side
import os
import time
from collections import defaultdict, namedtuple
from itertools import count
from cStringIO import StringIO
try:
    import cPickle as pickle
except ImportError:
    import pickle
from twisted.protocols import amp
from twisted.internet import protocol
from twisted.internet.defer import Deferred
from evennia.utils import logger
from evennia.utils.utils import to_str, variable_from_module
import zlib  # Used in Compressed class

DUMMYSESSION = namedtuple('DummySession', ['sessid'])(0)

# communication bits
# (chr(9) and chr(10) are \t and \n, so skipping them)

PCONN = chr(1)         # portal session connect
PDISCONN = chr(2)      # portal session disconnect
PSYNC = chr(3)         # portal session sync
SLOGIN = chr(4)        # server session login
SDISCONN = chr(5)      # server session disconnect
SDISCONNALL = chr(6)   # server session disconnect all
SSHUTD = chr(7)        # server shutdown
SSYNC = chr(8)         # server session sync
SCONN = chr(11)        # server creating new connection (for irc bots and etc)
PCONNSYNC = chr(12)    # portal post-syncing a session
PDISCONNALL = chr(13)  # portal session disconnect all
AMP_MAXLEN = amp.MAX_VALUE_LENGTH    # max allowed data length in AMP protocol (cannot be changed)

BATCH_RATE = 250     # max commands/sec before switching to batch-sending
BATCH_TIMEOUT = 0.5  # how often to poll to empty batch queue, in seconds

# buffers
_SENDBATCH = defaultdict(list)
_MSGBUFFER = defaultdict(list)


def get_restart_mode(restart_file):
    """
    Parse the server/portal restart status

    Args:
        restart_file (str): Path to restart.dat file.

    Returns:
        restart_mode (bool): If the file indicates the server is in
            restart mode or not.

    """
    if os.path.exists(restart_file):
        flag = open(restart_file, 'r').read()
        return flag == "True"
    return False


class AmpServerFactory(protocol.ServerFactory):
    """
    This factory creates the Server as a new AMPProtocol instance for accepting
    connections from the Portal.
    """
    noisy = False

    def __init__(self, server):
        """
        Initialize the factory.

        Args:
            server (Server): The Evennia server service instance.
            protocol (Protocol): The protocol the factory creates
                instances of.

        """
        self.server = server
        self.protocol = AMPProtocol

    def buildProtocol(self, addr):
        """
        Start a new connection, and store it on the service object.

        Args:
            addr (str): Connection address. Not used.

        Returns:
            protocol (Protocol): The created protocol.

        """
        self.server.amp_protocol = AMPProtocol()
        self.server.amp_protocol.factory = self
        return self.server.amp_protocol


class AmpClientFactory(protocol.ReconnectingClientFactory):
    """
    This factory creates an instance of the Portal, an AMPProtocol
    instances to use to connect

    """
    # Initial reconnect delay in seconds.
    initialDelay = 1
    factor = 1.5
    maxDelay = 1
    noisy = False

    def __init__(self, portal):
        """
        Initializes the client factory.

        Args:
            portal (Portal): Portal instance.

        """
        self.portal = portal
        self.protocol = AMPProtocol

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
        self.portal.amp_protocol = AMPProtocol()
        self.portal.amp_protocol.factory = self
        return self.portal.amp_protocol

    def clientConnectionLost(self, connector, reason):
        """
        Called when the AMP connection to the MUD server is lost.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.
            reason (str): Eventual text describing why connection was lost.

        """
        if hasattr(self, "server_restart_mode"):
            self.portal.sessions.announce_all(" Server restarting ...")
            self.maxDelay = 2
        else:
            # Don't translate this; avoid loading django on portal side.
            self.maxDelay = 10
            self.portal.sessions.announce_all(" ... Portal lost connection to Server.")
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when an AMP connection attempt to the MUD server fails.

        Args:
            connector (Connector): Twisted Connector instance representing
                this connection.
            reason (str): Eventual text describing why connection failed.

        """
        if hasattr(self, "server_restart_mode"):
            self.maxDelay = 2
        else:
            self.maxDelay = 10
        self.portal.sessions.announce_all(" ...")
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


# AMP Communication Command types

class Compressed(amp.String):
    """
    This is a customn AMP command Argument that both handles too-long
    sends as well as uses zlib for compression across the wire. The
    batch-grouping of too-long sends is borrowed from the "mediumbox"
    recipy at twisted-hacks's ~glyph/+junk/amphacks/mediumbox.

    """

    def fromBox(self, name, strings, objects, proto):
        """
        Converts from box representation to python. We
        group very long data into batches.
        """
        value = StringIO()
        value.write(strings.get(name))
        for counter in count(2):
            # count from 2 upwards
            chunk = strings.get("%s.%d" % (name, counter))
            if chunk is None:
                break
            value.write(chunk)
        objects[name] = value.getvalue()

    def toBox(self, name, strings, objects, proto):
        """
        Convert from data to box. We handled too-long
        batched data and put it together here.
        """
        value = StringIO(objects[name])
        strings[name] = value.read(AMP_MAXLEN)
        for counter in count(2):
            chunk = value.read(AMP_MAXLEN)
            if not chunk:
                break
            strings["%s.%d" % (name, counter)] = chunk

    def toString(self, inObject):
        """
        Convert to send on the wire, with compression.
        """
        return zlib.compress(inObject, 9)

    def fromString(self, inString):
        """
        Convert (decompress) from the wire to Python.
        """
        return zlib.decompress(inString)


class MsgPortal2Server(amp.Command):
    """
    Message Portal -> Server

    """
    key = "MsgPortal2Server"
    arguments = [('packed_data', Compressed())]
    errors = {Exception: 'EXCEPTION'}
    response = []


class MsgServer2Portal(amp.Command):
    """
    Message Server -> Portal

    """
    key = "MsgServer2Portal"
    arguments = [('packed_data', Compressed())]
    errors = {Exception: 'EXCEPTION'}
    response = []


class AdminPortal2Server(amp.Command):
    """
    Administration Portal -> Server

    Sent when the portal needs to perform admin operations on the
    server, such as when a new session connects or resyncs

    """
    key = "AdminPortal2Server"
    arguments = [('packed_data', Compressed())]
    errors = {Exception: 'EXCEPTION'}
    response = []


class AdminServer2Portal(amp.Command):
    """
    Administration Server -> Portal

    Sent when the server needs to perform admin operations on the
    portal.

    """
    key = "AdminServer2Portal"
    arguments = [('packed_data', Compressed())]
    errors = {Exception: 'EXCEPTION'}
    response = []


class FunctionCall(amp.Command):
    """
    Bidirectional Server <-> Portal

    Sent when either process needs to call an arbitrary function in
    the other. This does not use the batch-send functionality.

    """
    key = "FunctionCall"
    arguments = [('module', amp.String()),
                 ('function', amp.String()),
                 ('args', amp.String()),
                 ('kwargs', amp.String())]
    errors = {Exception: 'EXCEPTION'}
    response = [('result', amp.String())]


# Helper functions for pickling.

dumps = lambda data: to_str(pickle.dumps(to_str(data), pickle.HIGHEST_PROTOCOL))
loads = lambda data: pickle.loads(to_str(data))


# -------------------------------------------------------------
# Core AMP protocol for communication Server <-> Portal
# -------------------------------------------------------------

class AMPProtocol(amp.AMP):
    """
    This is the protocol that the MUD server and the proxy server
    communicate to each other with. AMP is a bi-directional protocol,
    so both the proxy and the MUD use the same commands and protocol.

    AMP specifies responder methods here and connect them to
    amp.Command subclasses that specify the datatypes of the
    input/output of these methods.

    """

    # helper methods

    def __init__(self, *args, **kwargs):
        """
        Initialize protocol with some things that need to be in place
        already before connecting both on portal and server.

        """
        self.send_batch_counter = 0
        self.send_reset_time = time.time()
        self.send_mode = True
        self.send_task = None

    def connectionMade(self):
        """
        This is called when an AMP connection is (re-)established
        between server and portal. AMP calls it on both sides, so we
        need to make sure to only trigger resync from the portal side.

        """
        # this makes for a factor x10 faster sends across the wire
        self.transport.setTcpNoDelay(True)

        if hasattr(self.factory, "portal"):
            # only the portal has the 'portal' property, so we know we are
            # on the portal side and can initialize the connection.
            sessdata = self.factory.portal.sessions.get_all_sync_data()
            self.send_AdminPortal2Server(DUMMYSESSION,
                                         PSYNC,
                                         sessiondata=sessdata)
            self.factory.portal.sessions.at_server_connection()
            if hasattr(self.factory, "server_restart_mode"):
                del self.factory.server_restart_mode

    def connectionLost(self, reason):
        """
        We swallow connection errors here. The reason is that during a
        normal reload/shutdown there will almost always be cases where
        either the portal or server shuts down before a message has
        returned its (empty) return, triggering a connectionLost error
        that is irrelevant. If a true connection error happens, the
        portal will continuously try to reconnect, showing the problem
        that way.
        """
        pass

    # Error handling

    def errback(self, e, info):
        """
        Error callback.
        Handles errors to avoid dropping connections on server tracebacks.

        Args:
            e (Failure): Deferred error instance.
            info (str): Error string.

        """
        e.trap(Exception)
        logger.log_err("AMP Error for %(info)s: %(e)s" % {'info': info,
                                                          'e': e.getErrorMessage()})

    def send_data(self, command, sessid, **kwargs):
        """
        Send data across the wire.

        Args:
            command (AMP Command): A protocol send command.
            sessid (int): A unique Session id.

        Returns:
            deferred (deferred or None): A deferred with an errback.

        Notes:
            Data will be sent across the wire pickled as a tuple
            (sessid, kwargs).

        """
        return self.callRemote(command,
                               packed_data=dumps((sessid, kwargs))
                               ).addErrback(self.errback, command.key)

    # Message definition + helper methods to call/create each message type

    # Portal -> Server Msg

    @MsgPortal2Server.responder
    def server_receive_msgportal2server(self, packed_data):
        """
        Receives message arriving to server. This method is executed
        on the Server.

        Args:
            packed_data (str): Data to receive (a pickled tuple (sessid,kwargs))

        """
        sessid, kwargs = loads(packed_data)
        session = self.factory.server.sessions.get(sessid, None)
        if session:
            self.factory.server.sessions.data_in(session, **kwargs)
        return {}

    def send_MsgPortal2Server(self, session, **kwargs):
        """
        Access method called by the Portal and executed on the Portal.

        Args:
            session (session): Session
            kwargs (any, optional): Optional data.

        Returns:
            deferred (Deferred): Asynchronous return.

        """
        return self.send_data(MsgPortal2Server, session.sessid, **kwargs)

    # Server -> Portal message

    @MsgServer2Portal.responder
    def portal_receive_server2portal(self, packed_data):
        """
        Receives message arriving to Portal from Server.
        This method is executed on the Portal.

        Args:
            packed_data (str): Pickled data (sessid, kwargs) coming over the wire.
        """
        sessid, kwargs = loads(packed_data)
        session = self.factory.portal.sessions.get(sessid, None)
        if session:
            self.factory.portal.sessions.data_out(session, **kwargs)
        return {}

    def send_MsgServer2Portal(self, session, **kwargs):
        """
        Access method - executed on the Server for sending data
            to Portal.

        Args:
            session (Session): Unique Session.
            kwargs (any, optiona): Extra data.

        """
        return self.send_data(MsgServer2Portal, session.sessid, **kwargs)

    # Server administration from the Portal side
    @AdminPortal2Server.responder
    def server_receive_adminportal2server(self, packed_data):
        """
        Receives admin data from the Portal (allows the portal to
        perform admin operations on the server). This is executed on
        the Server.

        Args:
            packed_data (str): Incoming, pickled data.

        """
        sessid, kwargs = loads(packed_data)
        operation = kwargs.pop("operation", "")
        server_sessionhandler = self.factory.server.sessions

        if operation == PCONN:  # portal_session_connect
            # create a new session and sync it
            server_sessionhandler.portal_connect(kwargs.get("sessiondata"))

        elif operation == PCONNSYNC:  # portal_session_sync
            server_sessionhandler.portal_session_sync(kwargs.get("sessiondata"))

        elif operation == PDISCONN:  # portal_session_disconnect
            # session closed from portal sid
            session = server_sessionhandler.get(sessid)
            if session:
                server_sessionhandler.portal_disconnect(session)

        elif operation == PDISCONNALL:  # portal_disconnect_all
            # portal orders all sessions to close
            server_sessionhandler.portal_disconnect_all()

        elif operation == PSYNC:  # portal_session_sync
            # force a resync of sessions when portal reconnects to
            # server (e.g. after a server reboot) the data kwarg
            # contains a dict {sessid: {arg1:val1,...}}
            # representing the attributes to sync for each
            # session.
            server_sessionhandler.portal_sessions_sync(kwargs.get("sessiondata"))
        else:
            raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}

    def send_AdminPortal2Server(self, session, operation="", **kwargs):
        """
        Send Admin instructions from the Portal to the Server.
        Executed
        on the Portal.

        Args:
            session (Session): Session.
            operation (char, optional): Identifier for the server operation, as defined by the
                global variables in `evennia/server/amp.py`.
            data (str or dict, optional): Data used in the administrative operation.

        """
        return self.send_data(AdminPortal2Server, session.sessid, operation=operation, **kwargs)

    # Portal administration from the Server side

    @AdminServer2Portal.responder
    def portal_receive_adminserver2portal(self, packed_data):
        """

        Receives and handles admin operations sent to the Portal
        This is executed on the Portal.

        Args:
            packed_data (str): Data received, a pickled tuple (sessid, kwargs).

        """
        sessid, kwargs = loads(packed_data)
        operation = kwargs.pop("operation")
        portal_sessionhandler = self.factory.portal.sessions

        if operation == SLOGIN:  # server_session_login
            # a session has authenticated; sync it.
            session = portal_sessionhandler.get(sessid)
            if session:
                portal_sessionhandler.server_logged_in(session, kwargs.get("sessiondata"))

        elif operation == SDISCONN:  # server_session_disconnect
            # the server is ordering to disconnect the session
            session = portal_sessionhandler.get(sessid)
            if session:
                portal_sessionhandler.server_disconnect(session, reason=kwargs.get("reason"))

        elif operation == SDISCONNALL:  # server_session_disconnect_all
            # server orders all sessions to disconnect
            portal_sessionhandler.server_disconnect_all(reason=kwargs.get("reason"))

        elif operation == SSHUTD:  # server_shutdown
            # the server orders the portal to shut down
            self.factory.portal.shutdown(restart=False)

        elif operation == SSYNC:  # server_session_sync
            # server wants to save session data to the portal,
            # maybe because it's about to shut down.
            portal_sessionhandler.server_session_sync(kwargs.get("sessiondata"),
                                                      kwargs.get("clean", True))
            # set a flag in case we are about to shut down soon
            self.factory.server_restart_mode = True

        elif operation == SCONN:  # server_force_connection (for irc/etc)
            portal_sessionhandler.server_connect(**kwargs)

        else:
            raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}

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
        return self.send_data(AdminServer2Portal, session.sessid, operation=operation, **kwargs)

    # Extra functions

    @FunctionCall.responder
    def receive_functioncall(self, module, function, func_args, func_kwargs):
        """
        This allows Portal- and Server-process to call an arbitrary
        function in the other process. It is intended for use by
        plugin modules.

        Args:
            module (str or module): The module containing the
                `function` to call.
            function (str): The name of the function to call in
                `module`.
            func_args (str): Pickled args tuple for use in `function` call.
            func_kwargs (str): Pickled kwargs dict for use in `function` call.

        """
        args = loads(func_args)
        kwargs = loads(func_kwargs)

        # call the function (don't catch tracebacks here)
        result = variable_from_module(module, function)(*args, **kwargs)

        if isinstance(result, Deferred):
            # if result is a deferred, attach handler to properly
            # wrap the return value
            result.addCallback(lambda r: {"result": dumps(r)})
            return result
        else:
            return {'result': dumps(result)}

    def send_FunctionCall(self, modulepath, functionname, *args, **kwargs):
        """
        Access method called by either process. This will call an arbitrary
        function on the other process (On Portal if calling from Server and
        vice versa).

        Inputs:
            modulepath (str) - python path to module holding function to call
            functionname (str) - name of function in given module
            *args, **kwargs will be used as arguments/keyword args for the
                            remote function call
        Returns:
            A deferred that fires with the return value of the remote
            function call

        """
        return self.callRemote(FunctionCall,
                               module=modulepath,
                               function=functionname,
                               args=dumps(args),
                               kwargs=dumps(kwargs)).addCallback(
            lambda r: loads(r["result"])).addErrback(self.errback, "FunctionCall")
