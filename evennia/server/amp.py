"""
Contains the protocols, commands, and client factory needed for the Server
and Portal to communicate with each other, letting Portal work as a proxy.
Both sides use this same protocol.

The separation works like this:

Portal - (AMP client) handles protocols. It contains a list of connected
         sessions in a dictionary for identifying the respective player
         connected. If it looses the AMP connection it will automatically
         try to reconnect.

Server - (AMP server) Handles all mud operations. The server holds its own list
         of sessions tied to player objects. This is synced against the portal
         at startup and when a session connects/disconnects

"""

# imports needed on both server and portal side
import os
from time import time
from collections import defaultdict
try:
    import cPickle as pickle
except ImportError:
    import pickle
from twisted.protocols import amp
from twisted.internet import protocol, task
from twisted.internet.defer import Deferred
from evennia.utils.utils import to_str, variable_from_module

# communication bits

PCONN = chr(1)        # portal session connect
PDISCONN = chr(2)     # portal session disconnect
PSYNC = chr(3)        # portal session sync
SLOGIN = chr(4)       # server session login
SDISCONN = chr(5)     # server session disconnect
SDISCONNALL = chr(6)  # server session disconnect all
SSHUTD = chr(7)       # server shutdown
SSYNC = chr(8)        # server session sync
SCONN = chr(9)        # server creating new connection (for irc/imc2 bots etc)
PCONNSYNC = chr(10)   # portal post-syncing a session
AMP_MAXLEN = 65535    # max allowed data length in AMP protocol (cannot be changed)

BATCH_RATE = 500    # max commands/sec before switching to batch-sending
BATCH_TIMEOUT = 1.0 # how often to poll to empty batch queue, in seconds

# buffers
_SENDBATCH = defaultdict(list)
_MSGBUFFER = defaultdict(list)

def get_restart_mode(restart_file):
    """
    Parse the server/portal restart status
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
    def __init__(self, server):
        """
        server: The Evennia server service instance
        protocol: The protocol the factory creates instances of.
        """
        self.server = server
        self.protocol = AMPProtocol

    def buildProtocol(self, addr):
        """
        Start a new connection, and store it on the service object
        """
        #print "Evennia Server connected to Portal at %s." % addr
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

    def __init__(self, portal):
        self.portal = portal
        self.protocol = AMPProtocol

    def startedConnecting(self, connector):
        """
        Called when starting to try to connect to the MUD server.
        """
        pass
        #print 'AMP started to connect:', connector

    def buildProtocol(self, addr):
        """
        Creates an AMPProtocol instance when connecting to the server.
        """
        #print "Portal connected to Evennia server at %s." % addr
        self.resetDelay()
        self.portal.amp_protocol = AMPProtocol()
        self.portal.amp_protocol.factory = self
        return self.portal.amp_protocol

    def clientConnectionLost(self, connector, reason):
        """
        Called when the AMP connection to the MUD server is lost.
        """
        if hasattr(self, "server_restart_mode"):
            self.maxDelay = 1
        else:
            # Don't translate this; avoid loading django on portal side.
            self.maxDelay = 10
            self.portal.sessions.announce_all(" ... Portal lost connection to Server.")
        protocol.ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when an AMP connection attempt to the MUD server fails.
        """
        if hasattr(self, "server_restart_mode"):
            self.maxDelay = 1
        else:
            self.maxDelay = 10
        self.portal.sessions.announce_all(" ...")
        protocol.ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


# AMP Communication Command types

class MsgPortal2Server(amp.Command):
    """
    Message portal -> server
    """
    key = "MsgPortal2Server"
    arguments = [('hashid', amp.String()),
                 ('data', amp.String()),
                 ('ipart', amp.Integer()),
                 ('nparts', amp.Integer())]
    errors = [(Exception, 'EXCEPTION')]
    response = []


class MsgServer2Portal(amp.Command):
    """
    Message server -> portal
    """
    key = "MsgServer2Portal"
    arguments = [('hashid', amp.String()),
                 ('data', amp.String()),
                 ('ipart', amp.Integer()),
                 ('nparts', amp.Integer())]
    errors = [(Exception, 'EXCEPTION')]
    response = []


class ServerAdmin(amp.Command):
    """
    Portal -> Server

    Sent when the portal needs to perform admin
     operations on the server, such as when a new
     session connects or resyncs
    """
    key = "ServerAdmin"
    arguments = [('hashid', amp.String()),
                 ('data', amp.String()),
                 ('ipart', amp.Integer()),
                 ('nparts', amp.Integer())]
    errors = [(Exception, 'EXCEPTION')]
    response = []


class PortalAdmin(amp.Command):
    """
    Server -> Portal

    Sent when the server needs to perform admin
     operations on the portal.
    """
    key = "PortalAdmin"
    arguments = [('hashid', amp.String()),
                 ('data', amp.String()),
                 ('ipart', amp.Integer()),
                 ('nparts', amp.Integer())]
    errors = [(Exception, 'EXCEPTION')]
    response = []


class FunctionCall(amp.Command):
    """
    Bidirectional

    Sent when either process needs to call an
    arbitrary function in the other. This does
    not use the batch-send functionality.
    """
    key = "FunctionCall"
    arguments = [('module', amp.String()),
                 ('function', amp.String()),
                 ('args', amp.String()),
                 ('kwargs', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = [('result', amp.String())]


# Helper functions

dumps = lambda data: to_str(pickle.dumps(to_str(data), pickle.HIGHEST_PROTOCOL))
loads = lambda data: pickle.loads(to_str(data))


#------------------------------------------------------------
# Core AMP protocol for communication Server <-> Portal
#------------------------------------------------------------

class AMPProtocol(amp.AMP):
    """
    This is the protocol that the MUD server and the proxy server
    communicate to each other with. AMP is a bi-directional protocol, so
    both the proxy and the MUD use the same commands and protocol.

    AMP specifies responder methods here and connect them to amp.Command
    subclasses that specify the datatypes of the input/output of these methods.
    """

    # helper methods

    def __init__(self, *args, **kwargs):
        """
        Initialize protocol with some things that need to be
        in place already before connecting both on portal and server.
        """
        self.min_batch_step = 1.0 / BATCH_RATE
        self.lastsend = time()
        self.task = task.LoopingCall(self.batch_send, None, None)
        self.task.start(BATCH_TIMEOUT)


    def connectionMade(self):
        """
        This is called when a connection is established
        between server and portal. AMP calls it on both sides,
        so we need to make sure to only trigger resync from the
        portal side.
        """
        if hasattr(self.factory, "portal"):
            # only the portal has the 'portal' property, so we know we are
            # on the portal side and can initialize the connection.
            sessdata = self.factory.portal.sessions.get_all_sync_data()
            self.call_remote_ServerAdmin(0,
                                         PSYNC,
                                         data=sessdata)
            self.factory.portal.sessions.at_server_connection()
            if hasattr(self.factory, "server_restart_mode"):
                del self.factory.server_restart_mode

    # Error handling

    def errback(self, e, info):
        "error handler, to avoid dropping connections on server tracebacks."
        e.trap(Exception)
        print "AMP Error for %(info)s: %(e)s" % {'info': info,
                                                 'e': e.getErrorMessage()}

    def batch_send(self, command, sessid, **kwargs):
        """
        This will batch data together to send fewer, large batches.

        Kwargs:
            force_direct: send direct
        """
        #print "batch_send 1:", command, sessid
        global _SENDBATCH
        if command is None:
            # called by the automatic cleanup mechanism
            commands = [cmd for cmd in (MsgPortal2Server, MsgServer2Portal, ServerAdmin, PortalAdmin)
                        if _SENDBATCH.get(cmd, False)]
            if not commands:
                return
        else:
            # called to send right away
            commands = [command]
            _SENDBATCH[command].append((sessid, kwargs))

        force_direct = kwargs.pop("force_direct", False)
        now = time()
        #print "batch_send 2:", now, self.lastsend, self.min_batch_step, now-self.lastsend > self.min_batch_step

        if force_direct or now - self.lastsend > self.min_batch_step:
            for command in commands:
                batch = dumps(_SENDBATCH[command])
                _SENDBATCH[command] = []
                # split in parts small enough to fit in AMP MAXLEN
                to_send = [batch[i:i+AMP_MAXLEN] for i in range(0, len(batch), AMP_MAXLEN)]
                nparts = len(to_send)
                # tag this batch
                hashid = "%s-%s" % (id(batch), now)
                if nparts == 1:
                    deferreds = [self.callRemote(command,
                                           hashid=hashid,
                                           data=batch,
                                           ipart=0,
                                           nparts=1).addErrback(self.errback, command.key)]
                else:
                    deferreds = []
                    for ipart, part in enumerate(to_send):
                        deferred = self.callRemote(command,
                                                   hashid=hashid,
                                                   data=part,
                                                   ipart=ipart,
                                                   nparts=nparts)
                        deferred.addErrback(self.errback, "%s part %i/%i" % (command.key, ipart, part))
                        deferreds.append(deferred)
                self.lastsend = time() # don't use now here, keep it as up-to-date as possible
                return deferreds


    def batch_recv(self, hashid, data, ipart, nparts):
        """
        This will receive and unpack data sent as a batch. This both
        handles too-long data as well as batch-sending very fast-
        arriving commands.
        """
        global _MSGBUFFER
        if nparts == 1:
            # most common case
            return loads(data)
        else:
            if ipart < nparts-1:
                # not yet complete
                _MSGBUFFER[hashid].append(data)
                return []
            else:
                # all parts in place - deserialize it
                return loads(_MSGBUFFER.pop(hashid) + data)


    # Message definition + helper methods to call/create each message type

    # Portal -> Server Msg

    def amp_msg_portal2server(self, hashid, data, ipart, nparts):
        """
        Relays message to server. This method is executed on the Server.

        Since AMP has a limit of 65355 bytes per message, it's possible the
        data comes in multiple chunks; if so (nparts>1) we buffer the data
        and wait for the remaining parts to arrive before continuing.
        """
        batch = self.batch_recv(hashid, data, ipart, nparts)
        for (sessid, kwargs) in batch:
            #print "msg portal -> server (server side):", sessid, msg, loads(ret["data"])
            self.factory.server.sessions.data_in(sessid,
                                             text=kwargs["msg"],
                                             data=kwargs["data"])
        return {}
    MsgPortal2Server.responder(amp_msg_portal2server)

    def call_remote_MsgPortal2Server(self, sessid, msg, data=""):
        """
        Access method called by the Portal and executed on the Portal.
        """
        #print "msg portal->server (portal side):", sessid, msg, data
        return self.batch_send(MsgPortal2Server, sessid,
                               msg=msg if msg is not None else "",
                               data=data)

    # Server -> Portal message

    def amp_msg_server2portal(self, hashid, data, ipart, nparts):
        """
        Relays message to Portal. This method is executed on the Portal.
        """
        batch = self.batch_recv(hashid, data, ipart, nparts)
        for (sessid, kwargs) in batch:
            #print "msg server->portal (portal side):", sessid, ret["text"], loads(ret["data"])
            self.factory.portal.sessions.data_out(sessid,
                                                  text=kwargs["msg"],
                                                  data=kwargs["data"])
        return {}
    MsgServer2Portal.responder(amp_msg_server2portal)

    def amp_batch_server2portal(self, hashid, data, ipart, nparts):
        """
        Relays batch data to Portal. This method is executed on the Portal.
        """
        batch = self.batch_recv(hashid, data, ipart, nparts)
        if batch is not None:
            for (sessid, kwargs) in batch:
                self.factory.portal.sessions.data_out(sessid,
                                                      text=kwargs["msg"],
                                                      **kwargs["data"])
        return {}
    MsgServer2Portal.responder(amp_batch_server2portal)

    def call_remote_MsgServer2Portal(self, sessid, msg, data=""):
        """
        Access method called by the Server and executed on the Server.
        """
        #print "msg server->portal (server side):", sessid, msg, data
        return self.batch_send(MsgServer2Portal, sessid, msg=msg, data=data)

    # Server administration from the Portal side
    def amp_server_admin(self, hashid, data, ipart, nparts):
        """
        This allows the portal to perform admin
        operations on the server.  This is executed on the Server.

        """
        #print "serveradmin (server side):", hashid, ipart, nparts
        batch = self.batch_recv(hashid, data, ipart, nparts)

        for (sessid, kwargs) in batch:
            operation = kwargs["operation"]
            data = kwargs["data"]
            server_sessionhandler = self.factory.server.sessions

            #print "serveradmin (server side):", sessid, ord(operation), data

            if operation == PCONN:  # portal_session_connect
                # create a new session and sync it
                server_sessionhandler.portal_connect(data)

            elif operation == PCONNSYNC: #portal_session_sync
                server_sessionhandler.portal_session_sync(data)

            elif operation == PDISCONN:  # portal_session_disconnect
                # session closed from portal side
                self.factory.server.sessions.portal_disconnect(sessid)

            elif operation == PSYNC:  # portal_session_sync
                # force a resync of sessions when portal reconnects to
                # server (e.g. after a server reboot) the data kwarg
                # contains a dict {sessid: {arg1:val1,...}}
                # representing the attributes to sync for each
                # session.
                server_sessionhandler.portal_sessions_sync(data)
            else:
                raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}
    ServerAdmin.responder(amp_server_admin)

    def call_remote_ServerAdmin(self, sessid, operation="", data=""):
        """
        Access method called by the Portal and Executed on the Portal.
        """
        #print "serveradmin (portal side):", sessid, ord(operation), data
        if hasattr(self.factory, "server_restart_mode"):
            return self.batch_send(ServerAdmin, sessid, force_direct=True, operation=operation, data=data)
        return self.batch_send(ServerAdmin, sessid, operation=operation, data=data)

    # Portal administraton from the Server side

    def amp_portal_admin(self, hashid, data, ipart, nparts):
        """
        This allows the server to perform admin
        operations on the portal. This is executed on the Portal.
        """
        #print "portaladmin (portal side):", sessid, ord(operation), data
        batch = self.batch_recv(hashid, data, ipart, nparts)
        for (sessid, kwargs) in batch:
            operation = kwargs["operation"]
            data = kwargs["data"]
            portal_sessionhandler = self.factory.portal.sessions

            if operation == SLOGIN:  # server_session_login
                # a session has authenticated; sync it.
                portal_sessionhandler.server_logged_in(sessid, data)

            elif operation == SDISCONN:  # server_session_disconnect
                # the server is ordering to disconnect the session
                portal_sessionhandler.server_disconnect(sessid, reason=data)

            elif operation == SDISCONNALL:  # server_session_disconnect_all
                # server orders all sessions to disconnect
                portal_sessionhandler.server_disconnect_all(reason=data)

            elif operation == SSHUTD:  # server_shutdown
                # the server orders the portal to shut down
                self.factory.portal.shutdown(restart=False)

            elif operation == SSYNC:  # server_session_sync
                # server wants to save session data to the portal,
                # maybe because it's about to shut down.
                portal_sessionhandler.server_session_sync(data)
                # set a flag in case we are about to shut down soon
                self.factory.server_restart_mode = True

            elif operation == SCONN: # server_force_connection (for irc/imc2 etc)
                portal_sessionhandler.server_connect(**data)

            else:
                raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}
    PortalAdmin.responder(amp_portal_admin)

    def call_remote_PortalAdmin(self, sessid, operation="", data=""):
        """
        Access method called by the server side.
        """
        if operation == SSYNC:
            return self.batch_send(PortalAdmin, sessid, force_direct=True, operation=operation, data=data)
        return self.batch_send(PortalAdmin, sessid, operation=operation, data=data)

    # Extra functions

    def amp_function_call(self, module, function, args, **kwargs):
        """
        This allows Portal- and Server-process to call an arbitrary function
        in the other process. It is intended for use by plugin modules.
        """
        args = loads(args)
        kwargs = loads(kwargs)

        # call the function (don't catch tracebacks here)
        result = variable_from_module(module, function)(*args, **kwargs)

        if isinstance(result, Deferred):
            # if result is a deferred, attach handler to properly
            # wrap the return value
            result.addCallback(lambda r: {"result": dumps(r)})
            return result
        else:
            return {'result': dumps(result)}
    FunctionCall.responder(amp_function_call)

    def call_remote_FunctionCall(self, modulepath, functionname, *args, **kwargs):
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
                               kwargs=dumps(kwargs)).addCallback(lambda r: loads(r["result"])).addErrback(self.errback, "FunctionCall")
