"""
Webclient based on websockets with MUD Standards subprotocol support.

This implements a webclient with WebSockets (http://en.wikipedia.org/wiki/WebSocket)
by use of the autobahn-python package's implementation (https://github.com/crossbario/autobahn-python).
It is used together with evennia/web/media/javascript/evennia_websocket_webclient.js.

Subprotocol Negotiation (RFC 6455 Sec-WebSocket-Protocol):
    When a client connects, it may offer one or more WebSocket subprotocols
    via the Sec-WebSocket-Protocol header. This module negotiates the best
    match from the server's supported list (configured via
    settings.WEBSOCKET_SUBPROTOCOLS) and selects the appropriate wire format
    codec for the connection's lifetime.

    Supported subprotocols (per https://mudstandards.org/websocket/):
        - v1.evennia.com: Evennia's legacy JSON array format
        - json.mudstandards.org: MUD Standards JSON envelope format
        - gmcp.mudstandards.org: GMCP over WebSocket
        - terminal.mudstandards.org: Raw ANSI terminal over WebSocket

    If no subprotocol is negotiated (legacy client with no header),
    the v1.evennia.com format is used as the default.

All data coming into the webclient via the v1.evennia.com format is in the
form of valid JSON on the form

`["inputfunc_name", [args], {kwarg}]`

which represents an "inputfunc" to be called on the Evennia side with *args, **kwargs.
The most common inputfunc is "text", which takes just the text input
from the command line and interprets it as an Evennia Command: `["text", ["look"], {}]`

"""

import json

from autobahn.exception import Disconnected
from autobahn.twisted.websocket import WebSocketServerProtocol
from django.conf import settings

from evennia.utils.utils import class_from_module, mod_import

_CLIENT_SESSIONS = mod_import(settings.SESSION_ENGINE).SessionStore
_UPSTREAM_IPS = settings.UPSTREAM_IPS

# Status Code 1000: Normal Closure
#   called when the connection was closed through JavaScript
CLOSE_NORMAL = WebSocketServerProtocol.CLOSE_STATUS_CODE_NORMAL

# Status Code 1001: Going Away
#   called when the browser is navigating away from the page
GOING_AWAY = WebSocketServerProtocol.CLOSE_STATUS_CODE_GOING_AWAY

_BASE_SESSION_CLASS = class_from_module(settings.BASE_SESSION_CLASS)

# --- Wire format support ---
# Import wire formats lazily to avoid circular imports at module level.
# The WIRE_FORMATS dict and format instances are created on first use.
_wire_formats = None


def _get_wire_formats():
    """
    Lazily load and return the wire format registry.

    Returns:
        dict: Mapping of subprotocol name -> WireFormat instance.

    """
    global _wire_formats
    if _wire_formats is None:
        try:
            from evennia.server.portal.wire_formats import WIRE_FORMATS

            _wire_formats = WIRE_FORMATS
        except Exception:
            from evennia.utils import logger

            logger.log_trace("Failed to load wire format registry")
            _wire_formats = {}
    return _wire_formats


def _get_supported_subprotocols():
    """
    Get the ordered list of supported subprotocol names from settings.

    Falls back to all available wire formats if the setting is not defined.

    Returns:
        list: Ordered list of subprotocol name strings.

    """
    configured = getattr(settings, "WEBSOCKET_SUBPROTOCOLS", None)
    if configured is None:
        # No explicit configuration; advertise all known wire formats.
        return list(_get_wire_formats().keys())

    # Allow a single string (common misconfiguration) by coercing to a list.
    if isinstance(configured, str):
        protos = [configured]
    else:
        try:
            protos = list(configured)
        except TypeError as err:
            raise TypeError(
                "settings.WEBSOCKET_SUBPROTOCOLS must be a string or an iterable "
                "of strings (e.g. list/tuple); got %r" % (configured,)
            ) from err

    # Warn about any configured names that don't match a known wire format.
    # Unknown names are harmlessly skipped during negotiation (onConnect only
    # selects protocols present in both the client's offer and the registry),
    # but a typo here is almost certainly unintentional.
    wire_formats = _get_wire_formats()
    unknown = [name for name in protos if name not in wire_formats]
    if unknown:
        from evennia.utils import logger

        logger.log_warn(
            "WEBSOCKET_SUBPROTOCOLS contains unknown protocol name(s): %s. "
            "Known protocols: %s"
            % (", ".join(repr(n) for n in unknown), ", ".join(repr(n) for n in wire_formats))
        )

    return protos


class WebSocketClient(WebSocketServerProtocol, _BASE_SESSION_CLASS):
    """
    Implements the server-side of the Websocket connection.

    Supports multiple wire formats via RFC 6455 subprotocol negotiation.
    The wire format is selected during the WebSocket handshake in onConnect()
    and determines how all subsequent messages are encoded and decoded.

    Attributes:
        wire_format (WireFormat): The selected wire format codec for this
            connection. Set during onConnect().

    """

    # nonce value, used to prevent the webclient from erasing the
    # webclient_authenticated_uid value of csession on disconnect
    nonce = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "webclient/websocket"
        self.browserstr = ""
        self.wire_format = None

    def onConnect(self, request):
        """
        Called during the WebSocket opening handshake, before onOpen().

        This is where we negotiate the WebSocket subprotocol. The client
        sends a list of subprotocols it supports via Sec-WebSocket-Protocol.
        We select the best match from our supported list.

        Args:
            request (ConnectionRequest): The WebSocket connection request,
                containing request.protocols (list of offered subprotocols).

        Returns:
            str or None: The selected subprotocol name to echo back in the
                Sec-WebSocket-Protocol response header, or None if no
                subprotocol was negotiated (legacy client with no header,
                or client offered protocols that don't match).

        """
        wire_formats = _get_wire_formats()
        supported = _get_supported_subprotocols()

        if request.protocols:
            # Client offered subprotocols — pick the first one we support
            # (order follows the server's preference from settings)
            for proto_name in supported:
                if proto_name in request.protocols and proto_name in wire_formats:
                    self.wire_format = wire_formats[proto_name]
                    return proto_name

            # Client offered protocols but none matched. Per RFC 6455, if we
            # don't echo a subprotocol, a well-behaved client should close the
            # connection. We still set a wire format so the connection doesn't
            # crash if the client proceeds anyway.
            from evennia.utils import logger

            logger.log_warn(
                "WebSocket client offered subprotocols %r but none match "
                "server's supported list %r. Falling back to v1 format."
                % (request.protocols, supported)
            )
            if "v1.evennia.com" in wire_formats:
                self.wire_format = wire_formats["v1.evennia.com"]
            elif wire_formats:
                self.wire_format = next(iter(wire_formats.values()))
            return None

        # No Sec-WebSocket-Protocol header at all — legacy client.
        # Always use v1 format regardless of WEBSOCKET_SUBPROTOCOLS.
        if "v1.evennia.com" in wire_formats:
            self.wire_format = wire_formats["v1.evennia.com"]
        elif wire_formats:
            self.wire_format = next(iter(wire_formats.values()))

        return None

    def get_client_session(self):
        """
        Get the Client browser session (used for auto-login based on browser session)

        Returns:
            csession (ClientSession): This is a django-specific internal representation
                of the browser session.

        """
        try:
            # client will connect with wsurl?csessid&page_id&browserid
            webarg = self.http_request_uri.split("?", 1)[1]
        except IndexError:
            # this may happen for custom webclients not caring for the
            # browser session.
            self.csessid = None
            return None
        except AttributeError:
            from evennia.utils import logger

            self.csessid = None
            logger.log_trace(str(self))
            return None

        self.csessid, *cargs = webarg.split("&", 2)
        if len(cargs) == 1:
            self.browserstr = str(cargs[0])
        elif len(cargs) == 2:
            self.page_id = str(cargs[0])
            self.browserstr = str(cargs[1])

        if self.csessid:
            return _CLIENT_SESSIONS(session_key=self.csessid)

    def onOpen(self):
        """
        This is called when the WebSocket connection is fully established.

        """
        client_address = self.transport.client
        client_address = client_address[0] if client_address else None

        if client_address in _UPSTREAM_IPS and "x-forwarded-for" in self.http_headers:
            addresses = [x.strip() for x in self.http_headers["x-forwarded-for"].split(",")]
            addresses.reverse()

            for addr in addresses:
                if addr not in _UPSTREAM_IPS:
                    client_address = addr
                    break

        self.init_session("websocket", client_address, self.factory.sessionhandler)

        csession = self.get_client_session()  # this sets self.csessid
        csessid = self.csessid
        uid = csession and csession.get("webclient_authenticated_uid", None)
        nonce = csession and csession.get("webclient_authenticated_nonce", 0)
        if uid:
            # the client session is already logged in.
            self.uid = uid
            self.nonce = nonce
            self.logged_in = True

            for old_session in self.sessionhandler.sessions_from_csessid(csessid):
                if (
                    hasattr(old_session, "websocket_close_code")
                    and old_session.websocket_close_code != CLOSE_NORMAL
                ):
                    # if we have old sessions with the same csession, they are remnants
                    self.sessid = old_session.sessid
                    self.sessionhandler.disconnect(old_session)

        # Ensure wire_format is set (it should be from onConnect, but
        # in testing scenarios onConnect may not have been called)
        if self.wire_format is None:
            wire_formats = _get_wire_formats()
            self.wire_format = wire_formats.get(
                "v1.evennia.com", next(iter(wire_formats.values()), None)
            )

        if self.wire_format is None:
            from evennia.utils import logger

            logger.log_err("WebSocketClient: No wire formats available. " "Closing connection.")
            self.sendClose(CLOSE_NORMAL, "No wire formats available")
            return

        browserstr = f":{self.browserstr}" if self.browserstr else ""
        proto_name = self.wire_format.name
        self.protocol_flags["CLIENTNAME"] = (
            f"Evennia Webclient (websocket{browserstr} [{proto_name}])"
        )
        self.protocol_flags["UTF-8"] = True
        self.protocol_flags["OOB"] = self.wire_format.supports_oob
        self.protocol_flags["TRUECOLOR"] = True
        self.protocol_flags["XTERM256"] = True
        self.protocol_flags["ANSI"] = True

        # watch for dead links
        self.transport.setTcpKeepAlive(1)
        # actually do the connection
        self.sessionhandler.connect(self)

    def disconnect(self, reason=None):
        """
        Generic hook for the engine to call in order to
        disconnect this protocol.

        Args:
            reason (str or None): Motivation for the disconnection.

        """
        csession = self.get_client_session()

        if csession:
            # if the nonce is different, webclient_authenticated_uid has been
            # set *before* this disconnect (disconnect called after a new client
            # connects, which occurs in some 'fast' browsers like Google Chrome
            # and Mobile Safari)
            if csession.get("webclient_authenticated_nonce", 0) == self.nonce:
                csession["webclient_authenticated_uid"] = None
                csession["webclient_authenticated_nonce"] = 0
                csession.save()
            self.logged_in = False

        self.sessionhandler.disconnect(self)
        # autobahn-python:
        # 1000 for a normal close, 1001 if the browser window is closed,
        # 3000-4999 for app. specific,
        # in case anyone wants to expose this functionality later.
        #
        # sendClose() under autobahn/websocket/interfaces.py
        self.sendClose(CLOSE_NORMAL, reason)

    def onClose(self, wasClean, code=None, reason=None):
        """
        This is executed when the connection is lost for whatever
        reason. it can also be called directly, from the disconnect
        method.

        Args:
            wasClean (bool): ``True`` if the WebSocket was closed cleanly.
            code (int or None): Close status as sent by the WebSocket peer.
            reason (str or None): Close reason as sent by the WebSocket peer.

        """
        if code == CLOSE_NORMAL or code == GOING_AWAY:
            self.disconnect(reason)
        else:
            self.websocket_close_code = code

    def onMessage(self, payload, isBinary):
        """
        Callback fired when a complete WebSocket message was received.

        Delegates to the active wire format's decode_incoming() method
        to parse the message into kwargs for data_in().

        Args:
            payload (bytes): The WebSocket message received.
            isBinary (bool): Flag indicating whether payload is binary or
                             UTF-8 encoded text.

        """
        if self.wire_format:
            kwargs = self.wire_format.decode_incoming(
                payload, isBinary, protocol_flags=self.protocol_flags
            )
            if kwargs:
                self.data_in(**kwargs)
        else:
            # Fallback: try legacy JSON parsing
            try:
                cmdarray = json.loads(str(payload, "utf-8"))
                if cmdarray:
                    self.data_in(**{cmdarray[0]: [cmdarray[1], cmdarray[2]]})
            except (json.JSONDecodeError, UnicodeDecodeError, IndexError):
                pass

    def sendLine(self, line):
        """
        Send data to client.

        Args:
            line (str): Text to send.

        """
        try:
            return self.sendMessage(line.encode())
        except Disconnected:
            # this can happen on an unclean close of certain browsers.
            # it means this link is actually already closed.
            self.disconnect(reason="Browser already closed.")

    def sendEncoded(self, data, is_binary=False):
        """
        Send pre-encoded data to the client.

        This is used by wire formats that return raw bytes with a
        binary/text frame indicator.

        Args:
            data (bytes): The encoded data to send.
            is_binary (bool): If True, send as a BINARY frame.
                If False, send as a TEXT frame.

        """
        try:
            return self.sendMessage(data, isBinary=is_binary)
        except Disconnected:
            self.disconnect(reason="Browser already closed.")

    def at_login(self):
        csession = self.get_client_session()
        if csession:
            csession["webclient_authenticated_uid"] = self.uid
            csession.save()

    def data_in(self, **kwargs):
        """
        Data User > Evennia.

        Args:
            text (str): Incoming text.
            kwargs (any): Options from protocol.

        Notes:
            At initilization, the client will send the special
            'csessid' command to identify its browser session hash
            with the Evennia side.

            The websocket client will also pass 'websocket_close' command
            to report that the client has been closed and that the
            session should be disconnected.

            Both those commands are parsed and extracted already at
            this point.

        """
        if "websocket_close" in kwargs:
            self.disconnect()
            return

        self.sessionhandler.data_in(self, **kwargs)

    def send_text(self, *args, **kwargs):
        """
        Send text data. Delegates to the active wire format's encode_text()
        method, which handles ANSI processing and framing. The exact output
        depends on the negotiated subprotocol (e.g., HTML for v1.evennia.com,
        raw ANSI for MUD Standards formats).

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - raw (bool): No parsing at all (leave ansi markers unparsed).
                - nocolor (bool): Clean out all color.
                - screenreader (bool): Use Screenreader mode.
                - send_prompt (bool): Send as a prompt instead of regular text.

        """
        if self.wire_format:
            result = self.wire_format.encode_text(
                *args, protocol_flags=self.protocol_flags, **kwargs
            )
            if result is not None:
                data, is_binary = result
                self.sendEncoded(data, is_binary=is_binary)
        else:
            # Fallback: legacy behavior
            self._send_text_legacy(*args, **kwargs)

    def _send_text_legacy(self, *args, **kwargs):
        """
        Legacy send_text fallback for when no wire format is set.

        Performs the original Evennia HTML conversion (parse_html) and
        sends a JSON array ``["text", [html_string], {}]`` via sendLine.

        """
        import html as html_lib
        import re

        from evennia.utils.ansi import parse_ansi
        from evennia.utils.text2html import parse_html

        if args:
            args = list(args)
            text = args[0]
            if text is None:
                return
        else:
            return
        flags = self.protocol_flags
        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        client_raw = options.get("client_raw", False)
        nocolor = options.get("nocolor", flags.get("NOCOLOR", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        prompt = options.get("send_prompt", False)
        _RE = re.compile(r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE)
        if screenreader:
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE.sub("", text)
        cmd = "prompt" if prompt else "text"
        if raw:
            if client_raw:
                args[0] = text
            else:
                args[0] = html_lib.escape(text)
        else:
            args[0] = parse_html(text, strip_ansi=nocolor)
        self.sendLine(json.dumps([cmd, args, kwargs]))

    def send_prompt(self, *args, **kwargs):
        """
        Send a prompt to the client.

        Prompts are handled separately from regular text because some
        wire formats (e.g. json.mudstandards.org) send prompts as a
        distinct message type that the client can render differently.

        Args:
            *args: Prompt text as first arg.

        Keyword Args:
            options (dict): Same options as send_text.

        """
        if self.wire_format:
            result = self.wire_format.encode_prompt(
                *args, protocol_flags=self.protocol_flags, **kwargs
            )
            if result is not None:
                data, is_binary = result
                self.sendEncoded(data, is_binary=is_binary)
        else:
            kwargs.setdefault("options", {}).update({"send_prompt": True})
            self.send_text(*args, **kwargs)

    def send_default(self, cmdname, *args, **kwargs):
        """
        Data Evennia -> User.

        Args:
            cmdname (str): The first argument will always be the oob cmd name.
            *args (any): Remaining args will be arguments for `cmd`.

        Keyword Args:
            options (dict): These are ignored for oob commands. Use command
                arguments (which can hold dicts) to send instructions to the
                client instead.

        """
        if self.wire_format:
            result = self.wire_format.encode_default(
                cmdname, *args, protocol_flags=self.protocol_flags, **kwargs
            )
            if result is not None:
                data, is_binary = result
                self.sendEncoded(data, is_binary=is_binary)
        else:
            # Fallback: legacy behavior
            if not cmdname == "options":
                self.sendLine(json.dumps([cmdname, args, kwargs]))
