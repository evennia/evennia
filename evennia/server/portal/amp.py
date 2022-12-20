"""
The AMP (Asynchronous Message Protocol)-communication commands and constants used by Evennia.

This module acts as a central place for AMP-servers and -clients to get commands to use.

"""

import pickle
import time
import zlib  # Used in Compressed class
from collections import defaultdict, namedtuple
from functools import wraps
from io import BytesIO
from itertools import count

from twisted.internet.defer import Deferred, DeferredList
from twisted.protocols import amp

from evennia.utils.utils import variable_from_module

# delayed import
_LOGGER = None

# communication bits
# (chr(9) and chr(10) are \t and \n, so skipping them)

PCONN = chr(1)  # portal session connect
PDISCONN = chr(2)  # portal session disconnect
PSYNC = chr(3)  # portal session sync
SLOGIN = chr(4)  # server session login
SDISCONN = chr(5)  # server session disconnect
SDISCONNALL = chr(6)  # server session disconnect all
SSHUTD = chr(7)  # server shutdown
SSYNC = chr(8)  # server session sync
SCONN = chr(11)  # server creating new connection (for irc bots and etc)
PCONNSYNC = chr(12)  # portal post-syncing a session
PDISCONNALL = chr(13)  # portal session disconnect all
SRELOAD = chr(14)  # server shutdown in reload mode
SSTART = chr(15)  # server start (portal must already be running anyway)
PSHUTD = chr(16)  # portal (+server) shutdown
SSHUTD = chr(17)  # server shutdown
PSTATUS = chr(18)  # ping server or portal status
SRESET = chr(19)  # server shutdown in reset mode

NUL = b"\x00"
NULNUL = b"\x00\x00"

AMP_MAXLEN = amp.MAX_VALUE_LENGTH  # max allowed data length in AMP protocol (cannot be changed)

# amp internal
ASK = b"_ask"
ANSWER = b"_answer"
ERROR = b"_error"
ERROR_CODE = b"_error_code"
ERROR_DESCRIPTION = b"_error_description"
UNKNOWN_ERROR_CODE = b"UNKNOWN"

# buffers
_SENDBATCH = defaultdict(list)
_MSGBUFFER = defaultdict(list)

# resources

DUMMYSESSION = namedtuple("DummySession", ["sessid"])(0)


_HTTP_WARNING = bytes(
    """
HTTP/1.1 200 OK
Content-Type: text/html

<html>
  <body>
    This is Evennia's internal AMP port. It handles communication
    between Evennia's different processes.
    <p>
        <h3>This port should NOT be publicly visible.</h3>
    </p>
  </body>
</html>""".strip(),
    "utf-8",
)


# Helper functions for pickling.


def dumps(data):
    return pickle.dumps(data, pickle.HIGHEST_PROTOCOL)


def loads(data):
    return pickle.loads(data)


def _get_logger():
    """
    Delay import of logger until absolutely necessary

    """
    global _LOGGER
    if not _LOGGER:
        from evennia.utils import logger as _LOGGER
    return _LOGGER


@wraps
def catch_traceback(func):
    """
    Helper decorator

    """

    def decorator(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as err:
            _get_logger().log_trace()
            raise  # make sure the error is visible on the other side of the connection too
            print(err)

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
        Converts from box string representation to python. We read back too-long batched data and
        put it back together here.

        """

        value = BytesIO()
        value.write(self.fromStringProto(strings.get(name), proto))
        for counter in count(2):
            # count from 2 upwards
            chunk = strings.get(b"%s.%d" % (name, counter))
            if chunk is None:
                break
            value.write(self.fromStringProto(chunk, proto))
        objects[str(name, "utf-8")] = value.getvalue()

    def toBox(self, name, strings, objects, proto):
        """
        Convert from python object to string box representation.
        we break up too-long data snippets into multiple batches here.

        """

        # print("toBox: name={}, strings={}, objects={}, proto{}".format(name, strings, objects, proto))

        value = BytesIO(objects[str(name, "utf-8")])
        strings[name] = self.toStringProto(value.read(AMP_MAXLEN), proto)

        # print("toBox strings[name] = {}".format(strings[name]))

        for counter in count(2):
            chunk = value.read(AMP_MAXLEN)
            if not chunk:
                break
            strings[b"%s.%d" % (name, counter)] = self.toStringProto(chunk, proto)

    def toString(self, inObject):
        """
        Convert to send as a bytestring on the wire, with compression.

        Note: In Py3 this is really a byte stream.

        """
        return zlib.compress(super().toString(inObject), 9)

    def fromString(self, inString):
        """
        Convert (decompress) from the string-representation on the wire to Python.

        """
        return super().fromString(zlib.decompress(inString))


class MsgLauncher2Portal(amp.Command):
    """
    Message Launcher -> Portal

    """

    key = "MsgLauncher2Portal"
    arguments = [(b"operation", amp.String()), (b"arguments", amp.String())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class MsgPortal2Server(amp.Command):
    """
    Message Portal -> Server

    """

    key = b"MsgPortal2Server"
    arguments = [(b"packed_data", Compressed())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class MsgServer2Portal(amp.Command):
    """
    Message Server -> Portal

    """

    key = "MsgServer2Portal"
    arguments = [(b"packed_data", Compressed())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class AdminPortal2Server(amp.Command):
    """
    Administration Portal -> Server

    Sent when the portal needs to perform admin operations on the
    server, such as when a new session connects or resyncs

    """

    key = "AdminPortal2Server"
    arguments = [(b"packed_data", Compressed())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class AdminServer2Portal(amp.Command):
    """
    Administration Server -> Portal

    Sent when the server needs to perform admin operations on the
    portal.

    """

    key = "AdminServer2Portal"
    arguments = [(b"packed_data", Compressed())]
    errors = {Exception: b"EXCEPTION"}
    response = []


class MsgStatus(amp.Command):
    """
    Check Status between AMP services

    """

    key = "MsgStatus"
    arguments = [(b"status", amp.String())]
    errors = {Exception: b"EXCEPTION"}
    response = [(b"status", amp.String())]


class FunctionCall(amp.Command):
    """
    Bidirectional Server <-> Portal

    Sent when either process needs to call an arbitrary function in
    the other. This does not use the batch-send functionality.

    """

    key = "FunctionCall"
    arguments = [
        (b"module", amp.String()),
        (b"function", amp.String()),
        (b"args", amp.String()),
        (b"kwargs", amp.String()),
    ]
    errors = {Exception: b"EXCEPTION"}
    response = [(b"result", amp.String())]


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
        self.multibatches = 0
        # later twisted amp has its own __init__
        super().__init__(*args, **kwargs)

    def _commandReceived(self, box):
        """
        This overrides the default Twisted AMP error handling which is not
        passing enough of the traceback through to the other side. Instead we
        add a specific log of the problem on the erroring side.

        """

        def formatAnswer(answerBox):
            answerBox[ANSWER] = box[ASK]
            return answerBox

        def formatError(error):
            if error.check(amp.RemoteAmpError):
                code = error.value.errorCode
                desc = error.value.description

                # Evennia extra logging
                desc += " (error logged on other side)"
                _get_logger().log_err(f"AMP caught exception ({desc}):\n{error.value}")

                if isinstance(desc, str):
                    desc = desc.encode("utf-8", "replace")
                if error.value.fatal:
                    errorBox = amp.QuitBox()
                else:
                    errorBox = amp.AmpBox()
            else:
                errorBox = amp.QuitBox()
                _get_logger().log_err(error)  # server-side logging if unhandled error
                code = UNKNOWN_ERROR_CODE
                desc = b"Unknown Error"
            errorBox[ERROR] = box[ASK]
            errorBox[ERROR_DESCRIPTION] = desc
            errorBox[ERROR_CODE] = code
            return errorBox

        deferred = self.dispatchCommand(box)
        if ASK in box:
            deferred.addCallbacks(formatAnswer, formatError)
            deferred.addCallback(self._safeEmit)
        deferred.addErrback(self.unhandledError)

    def stringReceived(self, string):
        """
        Overrides the base stringReceived of twisted in order to handle
        the strange error reported in https://github.com/evennia/evennia/issues/2053,
        which can lead to the amp connection locking up.

        Args:
            string (str): the data coming in.

        Notes:

            To test, add the following code to the beginning of
            `evennia.server.amp_client.AMPServerClientProtocol.data_to_portal`, then
            run multiple commands until the error trigger:
            ::

                import random
                from twisted.protocols.amp import AmpBox
                always_fail = False
                if always_fail or random.random() < 0.05:
                    breaker = AmpBox()
                    breaker['_answer'.encode()]='13541'.encode()
                    self.transport.write(breaker.serialize())

        """
        try:
            pto = "proto_" + self.state
            statehandler = getattr(self, pto)
        except AttributeError:
            log.msg("callback", self.state, "not found")
        else:
            try:
                # make sure to catch a KeyError cleanly here
                self.state = statehandler(string)
                if self.state == "done":
                    self.transport.loseConnection()
            except KeyError as err:
                _get_logger().log_err(
                    f"AMP error (KeyError: {err}). Discarded data (see "
                    "https://github.com/evennia/evennia/issues/2053)"
                )

    def dataReceived(self, data):
        """
        Handle non-AMP messages, such as HTTP communication.

        """
        # print("dataReceived: {}".format(data))
        if data[:1] == NUL:
            # an AMP communication
            if data[-2:] != NULNUL:
                # an incomplete AMP box means more batches are forthcoming.
                self.multibatches += 1
            try:
                super().dataReceived(data)
            except KeyError:
                _get_logger().log_trace(
                    "Discarded incoming partial (packed) data (len {})".format(len(data))
                )
        elif self.multibatches:
            # invalid AMP, but we have a pending multi-batch that is not yet complete
            if data[-2:] == NULNUL:
                # end of existing multibatch
                self.multibatches = max(0, self.multibatches - 1)
            try:
                super().dataReceived(data)
            except KeyError:
                _get_logger().log_trace(
                    "Discarded incoming multi-batch (packed) data (len {})".format(len(data))
                )
        else:
            # not an AMP communication, return warning
            self.transport.write(_HTTP_WARNING)
            self.transport.loseConnection()
            print("HTTP received (the AMP port should not receive http, only AMP!) %s" % data)

    def makeConnection(self, transport):
        """
        Swallow connection log message here. Copied from original
        in the amp protocol.

        """
        # copied from original, removing the log message
        if not self._ampInitialized:
            amp.AMP.__init__(self)
        self._transportPeer = transport.getPeer()
        self._transportHost = transport.getHost()
        amp.BinaryBoxProtocol.makeConnection(self, transport)

    def connectionMade(self):
        """
        This is called when an AMP connection is (re-)established. AMP calls it on both sides.

        """
        # print("connectionMade: {}".format(self))
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
        # print("ConnectionLost: {}: {}".format(self, reason))
        try:
            self.factory.broadcasts.remove(self)
        except ValueError:
            pass

    # Error handling

    def errback(self, err, info):
        """
        Error callback.
        Handles errors to avoid dropping connections on server tracebacks.

        Args:
            err (Failure): Deferred error instance.
            info (str): Error string.

        """
        err.trap(Exception)
        _get_logger().log_err(
            "AMP Error from {info}: {trcbck} {err}".format(
                info=info, trcbck=err.getTraceback(), err=err.getErrorMessage()
            )
        )

    def data_in(self, packed_data):
        """
        Process incoming packed data.

        Args:
            packed_data (bytes): Pickled data.
        Returns:
            unpaced_data (any): Unpickled package

        """
        msg = loads(packed_data)
        return msg

    def broadcast(self, command, sessid, **kwargs):
        """
        Send data across the wire to all connections.

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
        # print("broadcast: {} {}: {}".format(command, sessid, kwargs))

        for protcl in self.factory.broadcasts:
            deferreds.append(
                protcl.callRemote(command, **kwargs).addErrback(self.errback, command.key)
            )

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
        return (
            self.callRemote(
                FunctionCall,
                module=modulepath,
                function=functionname,
                args=dumps(args),
                kwargs=dumps(kwargs),
            )
            .addCallback(lambda r: loads(r["result"]))
            .addErrback(self.errback, "FunctionCall")
        )

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
            return {"result": dumps(result)}
