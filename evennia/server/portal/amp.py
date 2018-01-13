"""
The AMP (Asynchronous Message Protocol)-communication commands and constants used by Evennia.

This module acts as a central place for AMP-servers and -clients to get commands to use.

"""
from __future__ import print_function
from functools import wraps
import time
from twisted.protocols import amp
from collections import defaultdict, namedtuple
from cStringIO import StringIO
from itertools import count
import zlib  # Used in Compressed class
try:
    import cPickle as pickle
except ImportError:
    import pickle

from twisted.internet.defer import DeferredList, Deferred
from evennia.utils.utils import to_str, variable_from_module

# delayed import
_LOGGER = None

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
SRELOAD = chr(14)      # server reloading (have portal start a new server)
SSTART = chr(15)       # server start (portal must already be running anyway)
PSHUTD = chr(16)       # portal (+server) shutdown
SSHUTD = chr(17)       # server-only shutdown
PSTATUS = chr(18)      # ping server or portal status

AMP_MAXLEN = amp.MAX_VALUE_LENGTH    # max allowed data length in AMP protocol (cannot be changed)
BATCH_RATE = 250     # max commands/sec before switching to batch-sending
BATCH_TIMEOUT = 0.5  # how often to poll to empty batch queue, in seconds

# buffers
_SENDBATCH = defaultdict(list)
_MSGBUFFER = defaultdict(list)

# resources

DUMMYSESSION = namedtuple('DummySession', ['sessid'])(0)


_HTTP_WARNING = """
HTTP/1.1 200 OK
Content-Type: text/html

<html><body>
This is Evennia's interal AMP port. It handles communication
between Evennia's different processes.<h3><p>This port should NOT be
publicly visible.</p></h3>
</body></html>""".strip()


# Helper functions for pickling.

def dumps(data):
    return to_str(pickle.dumps(to_str(data), pickle.HIGHEST_PROTOCOL))


def loads(data):
    return pickle.loads(to_str(data))


@wraps
def catch_traceback(func):
    "Helper decorator"
    def decorator(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            global _LOGGER
            if not _LOGGER:
                from evennia.utils import logger as _LOGGER
            _LOGGER.log_trace()
            raise  # make sure the error is visible on the other side of the connection too
    return decorator


# AMP Communication Command types

class Compressed(amp.String):
    """
    This is a custom AMP command Argument that both handles too-long
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


class MsgLauncher2Portal(amp.Command):
    """
    Message Launcher -> Portal

    """
    key = "MsgLauncher2Portal"
    arguments = [('operation', amp.String()),
                 ('arguments', amp.String())]
    errors = {Exception: 'EXCEPTION'}
    response = [('result', amp.String())]


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


class MsgStatus(amp.Command):
    """
    Check Status between AMP services

    """
    key = "MsgStatus"
    arguments = [('status', amp.String())]
    errors = {Exception: 'EXCEPTION'}
    response = [('status', amp.String())]


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


# -------------------------------------------------------------
# Core AMP protocol for communication Server <-> Portal
# -------------------------------------------------------------

class AMPMultiConnectionProtocol(amp.AMP):
    """
    AMP protocol that safely handle multiple connections to the same
    server without dropping old ones - new clients will receive
    all server returns (broadcast). Will also correctly handle
    erroneous HTTP requests on the port and return a HTTP error response.

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

    def dataReceived(self, data):
        """
        Handle non-AMP messages, such as HTTP communication.
        """
        if data[0] != b'\0':
            self.transport.write(_HTTP_WARNING)
            self.transport.loseConnection()
        else:
            super(AMPMultiConnectionProtocol, self).dataReceived(data)

    def connectionMade(self):
        """
        This is called when an AMP connection is (re-)established AMP calls it on both sides.

        """
        self.factory.broadcasts.append(self)

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
        self.factory.broadcasts.remove(self)

    # Error handling

    def errback(self, e, info):
        """
        Error callback.
        Handles errors to avoid dropping connections on server tracebacks.

        Args:
            e (Failure): Deferred error instance.
            info (str): Error string.

        """
        global _LOGGER
        if not _LOGGER:
            from evennia.utils import logger as _LOGGER
        e.trap(Exception)
        _LOGGER.log_err("AMP Error for %(info)s: %(e)s" % {'info': info,
                                                           'e': e.getErrorMessage()})

    def data_in(self, packed_data):
        """
        Process incoming packed data.

        Args:
            packed_data (bytes): Zip-packed data.
        Returns:
            unpaced_data (any): Unpacked package

        """
        return loads(packed_data)

    def data_out(self, command, sessid, **kwargs):
        """
        Send data across the wire. Always use this to send.

        Args:
            command (AMP Command): A protocol send command.
            sessid (int): A unique Session id.

        Returns:
            deferred (deferred or None): A deferred with an errback.

        Notes:
            Data will be sent across the wire pickled as a tuple
            (sessid, kwargs).

        """
        deferreds = []
        for protcl in self.factory.broadcasts:
            deferreds.append(protcl.callRemote(command,
                                               packed_data=dumps((sessid, kwargs))).addErrback(
                                                    self.errback, command.key))
        return DeferredList(deferreds)

    # generic function send/recvs

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

    @FunctionCall.responder
    @catch_traceback
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
