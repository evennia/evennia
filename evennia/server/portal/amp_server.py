"""
The Evennia Portal service acts as an AMP-server, handling AMP
communication to the AMP clients connecting to it (by default
these are the Evennia Server and the evennia launcher).

"""
import os
import sys
from twisted.internet import protocol
from evennia.server.portal import amp
from subprocess import Popen, STDOUT, PIPE
from evennia.utils import logger


def getenv():
    """
    Get current environment and add PYTHONPATH.

    Returns:
        env (dict): Environment global dict.

    """
    sep = ";" if os.name == 'nt' else ":"
    env = os.environ.copy()
    env['PYTHONPATH'] = sep.join(sys.path)
    return env


class AMPServerFactory(protocol.ServerFactory):

    """
    This factory creates AMP Server connection. This acts as the 'Portal'-side communication to the
    'Server' process.

    """
    noisy = False

    def logPrefix(self):
        "How this is named in logs"
        return "AMP"

    def __init__(self, portal):
        """
        Initialize the factory. This is called as the Portal service starts.

        Args:
            portal (Portal): The Evennia Portal service instance.
            protocol (Protocol): The protocol the factory creates
                instances of.

        """
        self.portal = portal
        self.protocol = AMPServerProtocol
        self.broadcasts = []
        self.server_connection = None
        self.server_info_dict = None
        self.launcher_connection = None
        self.disconnect_callbacks = {}
        self.server_connect_callbacks = []

    def buildProtocol(self, addr):
        """
        Start a new connection, and store it on the service object.

        Args:
            addr (str): Connection address. Not used.

        Returns:
            protocol (Protocol): The created protocol.

        """
        self.portal.amp_protocol = AMPServerProtocol()
        self.portal.amp_protocol.factory = self
        return self.portal.amp_protocol


class AMPServerProtocol(amp.AMPMultiConnectionProtocol):
    """
    Protocol subclass for the AMP-server run by the Portal.

    """
    def connectionLost(self, reason):
        """
        Set up a simple callback mechanism to let the amp-server wait for a connection to close.

        """
        # wipe broadcast and data memory
        super(AMPServerProtocol, self).connectionLost(reason)
        if self.factory.server_connection == self:
            self.factory.server_connection = None
            self.factory.server_info_dict = None
        if self.factory.launcher_connection == self:
            self.factory.launcher_connection = None

        callback, args, kwargs = self.factory.disconnect_callbacks.pop(self, (None, None, None))
        if callback:
            try:
                callback(*args, **kwargs)
            except Exception:
                logger.log_trace()

    def get_status(self):
        """
        Return status for the Evennia infrastructure.

        Returns:
            status (tuple): The portal/server status and pids
                (portal_live, server_live, portal_PID, server_PID).

        """
        server_connected = bool(self.factory.server_connection and
                                self.factory.server_connection.transport.connected)
        portal_info_dict = self.factory.portal.get_info_dict()
        server_info_dict = self.factory.server_info_dict
        server_pid = self.factory.portal.server_process_id
        portal_pid = os.getpid()
        return (True, server_connected, portal_pid, server_pid, portal_info_dict, server_info_dict)

    def data_to_server(self, command, sessid, **kwargs):
        """
        Send data across the wire to the Server.

        Args:
            command (AMP Command): A protocol send command.
            sessid (int): A unique Session id.

        Returns:
            deferred (deferred or None): A deferred with an errback.

        Notes:
            Data will be sent across the wire pickled as a tuple
            (sessid, kwargs).

        """
        if self.factory.server_connection:
            return self.factory.server_connection.callRemote(
                        command, packed_data=amp.dumps((sessid, kwargs))).addErrback(
                            self.errback, command.key)
        else:
            # if no server connection is available, broadcast
            return self.broadcast(command, sessid, packed_data=amp.dumps((sessid, kwargs)))

    def start_server(self, server_twistd_cmd):
        """
        (Re-)Launch the Evennia server.

        Args:
            server_twisted_cmd (list): The server start instruction
                to pass to POpen to start the server.

        """
        # start the Server
        try:
            process = Popen(server_twistd_cmd, env=getenv(), bufsize=-1, stdout=PIPE, stderr=STDOUT)
        except Exception:
            self.factory.portal.server_process_id = None
            logger.log_trace()
            return 0
        # there is a short window before the server logger is up where we must
        # catch the stdout of the Server or eventual tracebacks will be lost.
        with process.stdout as out:
            logger.log_server(out.read())

        # store the pid and launch argument for future reference
        self.factory.portal.server_process_id = process.pid
        self.factory.portal.server_twistd_cmd = server_twistd_cmd
        return process.pid

    def wait_for_disconnect(self, callback, *args, **kwargs):
        """
        Add a callback for when this connection is lost.

        Args:
            callback (callable): Will be called with *args, **kwargs
                once this protocol is disconnected.

        """
        self.factory.disconnect_callbacks[self] = (callback, args, kwargs)

    def wait_for_server_connect(self, callback, *args, **kwargs):
        """
        Add a callback for when the Server is sure to have connected.

        Args:
            callback (callable): Will be called with *args, **kwargs
                once the Server handshake with Portal is complete.

        """
        self.factory.server_connect_callbacks.append((callback, args, kwargs))

    def stop_server(self, mode='shutdown'):
        """
        Shut down server in one or more modes.

        Args:
            mode (str): One of 'shutdown', 'reload' or 'reset'.

        """
        if mode == 'reload':
            self.send_AdminPortal2Server(amp.DUMMYSESSION, operation=amp.SRELOAD)
        elif mode == 'reset':
            self.send_AdminPortal2Server(amp.DUMMYSESSION, operation=amp.SRESET)
        elif mode == 'shutdown':
            self.send_AdminPortal2Server(amp.DUMMYSESSION, operation=amp.SSHUTD)

    # sending amp data

    def send_Status2Launcher(self):
        """
        Send a status stanza to the launcher.

        """
        if self.factory.launcher_connection:
            self.factory.launcher_connection.callRemote(
                    amp.MsgStatus,
                    status=amp.dumps(self.get_status())).addErrback(
                            self.errback, amp.MsgStatus.key)

    def send_MsgPortal2Server(self, session, **kwargs):
        """
        Access method called by the Portal and executed on the Portal.

        Args:
            session (session): Session
            kwargs (any, optional): Optional data.

        Returns:
            deferred (Deferred): Asynchronous return.

        """
        return self.data_to_server(amp.MsgPortal2Server, session.sessid, **kwargs)

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
        return self.data_to_server(amp.AdminPortal2Server, session.sessid,
                                   operation=operation, **kwargs)

    # receive amp data

    @amp.MsgStatus.responder
    @amp.catch_traceback
    def portal_receive_status(self, status):
        """
        Returns run-status for the server/portal.

        Args:
            status (str): Not used.
        Returns:
            status (dict): The status is a tuple
                (portal_running, server_running, portal_pid, server_pid).

        """
        return {"status": amp.dumps(self.get_status())}

    @amp.MsgLauncher2Portal.responder
    @amp.catch_traceback
    def portal_receive_launcher2portal(self, operation, arguments):
        """
        Receives message arriving from evennia_launcher.
        This method is executed on the Portal.

        Args:
            operation (str): The action to perform.
            arguments (str): Possible argument to the instruction, or the empty string.

        Returns:
            result (dict): The result back to the launcher.

        Notes:
            This is the entrypoint for controlling the entire Evennia system from the evennia
            launcher. It can obviously only accessed when the Portal is already up and running.

        """
        self.factory.launcher_connection = self

        _, server_connected, _, _, _, _ = self.get_status()

        # logger.log_msg("Evennia Launcher->Portal operation %s received" % (ord(operation)))

        if operation == amp.SSTART:   # portal start  #15
            # first, check if server is already running
            if not server_connected:
                self.wait_for_server_connect(self.send_Status2Launcher)
                self.start_server(amp.loads(arguments))

        elif operation == amp.SRELOAD:  # reload server #14
            if server_connected:
                # We let the launcher restart us once they get the signal
                self.factory.server_connection.wait_for_disconnect(
                    self.send_Status2Launcher)
                self.stop_server(mode='reload')
            else:
                self.wait_for_server_connect(self.send_Status2Launcher)
                self.start_server(amp.loads(arguments))

        elif operation == amp.SRESET:  # reload server #19
            if server_connected:
                self.factory.server_connection.wait_for_disconnect(
                    self.send_Status2Launcher)
                self.stop_server(mode='reset')
            else:
                self.wait_for_server_connect(self.send_Status2Launcher)
                self.start_server(amp.loads(arguments))

        elif operation == amp.SSHUTD:  # server-only shutdown #17
            if server_connected:
                self.factory.server_connection.wait_for_disconnect(
                    self.send_Status2Launcher)
                self.stop_server(mode='shutdown')

        elif operation == amp.PSHUTD:  # portal + server shutdown  #16
            if server_connected:
                self.factory.server_connection.wait_for_disconnect(
                    self.factory.portal.shutdown, restart=False)
            else:
                self.factory.portal.shutdown(restart=False)

        else:
            raise Exception("operation %(op)s not recognized." % {'op': operation})

        return {}

    @amp.MsgServer2Portal.responder
    @amp.catch_traceback
    def portal_receive_server2portal(self, packed_data):
        """
        Receives message arriving to Portal from Server.
        This method is executed on the Portal.

        Args:
            packed_data (str): Pickled data (sessid, kwargs) coming over the wire.

        """
        sessid, kwargs = self.data_in(packed_data)
        session = self.factory.portal.sessions.get(sessid, None)
        if session:
            self.factory.portal.sessions.data_out(session, **kwargs)
        return {}

    @amp.AdminServer2Portal.responder
    @amp.catch_traceback
    def portal_receive_adminserver2portal(self, packed_data):
        """

        Receives and handles admin operations sent to the Portal
        This is executed on the Portal.

        Args:
            packed_data (str): Data received, a pickled tuple (sessid, kwargs).

        """
        self.factory.server_connection = self

        sessid, kwargs = self.data_in(packed_data)
        operation = kwargs.pop("operation")
        portal_sessionhandler = self.factory.portal.sessions

        if operation == amp.SLOGIN:  # server_session_login
            # a session has authenticated; sync it.
            session = portal_sessionhandler.get(sessid)
            if session:
                portal_sessionhandler.server_logged_in(session, kwargs.get("sessiondata"))

        elif operation == amp.SDISCONN:  # server_session_disconnect
            # the server is ordering to disconnect the session
            session = portal_sessionhandler.get(sessid)
            if session:
                portal_sessionhandler.server_disconnect(session, reason=kwargs.get("reason"))

        elif operation == amp.SDISCONNALL:  # server_session_disconnect_all
            # server orders all sessions to disconnect
            portal_sessionhandler.server_disconnect_all(reason=kwargs.get("reason"))

        elif operation == amp.SRELOAD:  # server reload
                self.factory.server_connection.wait_for_disconnect(
                    self.start_server, self.factory.portal.server_twistd_cmd)
                self.stop_server(mode='reload')

        elif operation == amp.SRESET:  # server reset
                self.factory.server_connection.wait_for_disconnect(
                    self.start_server, self.factory.portal.server_twistd_cmd)
                self.stop_server(mode='reset')

        elif operation == amp.SSHUTD:  # server-only shutdown
            self.stop_server(mode='shutdown')

        elif operation == amp.PSHUTD:  # full server+server shutdown
            self.factory.server_connection.wait_for_disconnect(
                self.factory.portal.shutdown, restart=False)
            self.stop_server(mode='shutdown')

        elif operation == amp.PSYNC:  # portal sync
            # Server has (re-)connected and wants the session data from portal
            self.factory.server_info_dict = kwargs.get("info_dict", {})
            sessdata = self.factory.portal.sessions.get_all_sync_data()
            self.send_AdminPortal2Server(amp.DUMMYSESSION,
                                         amp.PSYNC,
                                         sessiondata=sessdata)
            self.factory.portal.sessions.at_server_connection()

            if self.factory.server_connection:
                # this is an indication the server has successfully connected, so
                # we trigger any callbacks (usually to tell the launcher server is up)
                for callback, args, kwargs in self.factory.server_connect_callbacks:
                    try:
                        callback(*args, **kwargs)
                    except Exception:
                        logger.log_trace()
                self.factory.server_connect_callbacks = []

        elif operation == amp.SSYNC:  # server_session_sync
            # server wants to save session data to the portal,
            # maybe because it's about to shut down.
            portal_sessionhandler.server_session_sync(kwargs.get("sessiondata"),
                                                      kwargs.get("clean", True))

            # set a flag in case we are about to shut down soon
            self.factory.server_restart_mode = True

        elif operation == amp.SCONN:  # server_force_connection (for irc/etc)
            portal_sessionhandler.server_connect(**kwargs)

        else:
            raise Exception("operation %(op)s not recognized." % {'op': operation})
        return {}
