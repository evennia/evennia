"""
Webclient based on websockets.

This implements a webclient with WebSockets (http://en.wikipedia.org/wiki/WebSocket)
by use of the autobahn-python package's implementation (https://github.com/crossbario/autobahn-python).
It is used together with evennia/web/media/javascript/evennia_websocket_webclient.js.

All data coming into the webclient is in the form of valid JSON on the form

`["inputfunc_name", [args], {kwarg}]`

which represents an "inputfunc" to be called on the Evennia side with *args, **kwargs.
The most common inputfunc is "text", which takes just the text input
from the command line and interprets it as an Evennia Command: `["text", ["look"], {}]`

"""
import html
import json
import re

from autobahn.exception import Disconnected
from autobahn.twisted.websocket import WebSocketServerProtocol
from django.conf import settings

from evennia.utils.ansi import parse_ansi
from evennia.utils.text2html import parse_html
from evennia.utils.utils import class_from_module, mod_import

_RE_SCREENREADER_REGEX = re.compile(
    r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)
_CLIENT_SESSIONS = mod_import(settings.SESSION_ENGINE).SessionStore
_UPSTREAM_IPS = settings.UPSTREAM_IPS

# Status Code 1000: Normal Closure
#   called when the connection was closed through JavaScript
CLOSE_NORMAL = WebSocketServerProtocol.CLOSE_STATUS_CODE_NORMAL

# Status Code 1001: Going Away
#   called when the browser is navigating away from the page
GOING_AWAY = WebSocketServerProtocol.CLOSE_STATUS_CODE_GOING_AWAY

_BASE_SESSION_CLASS = class_from_module(settings.BASE_SESSION_CLASS)


class WebSocketClient(WebSocketServerProtocol, _BASE_SESSION_CLASS):
    """
    Implements the server-side of the Websocket connection.

    """

    # nonce value, used to prevent the webclient from erasing the
    # webclient_authenticated_uid value of csession on disconnect
    nonce = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.protocol_key = "webclient/websocket"
        self.browserstr = ""

    def get_client_session(self):
        """
        Get the Client browser session (used for auto-login based on browser session)

        Returns:
            csession (ClientSession): This is a django-specific internal representation
                of the browser session.

        """
        try:
            # client will connect with wsurl?csessid&browserid
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

        self.csessid, *browserstr = webarg.split("&", 1)
        if browserstr:
            self.browserstr = str(browserstr[0])

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

        browserstr = f":{self.browserstr}" if self.browserstr else ""
        self.protocol_flags["CLIENTNAME"] = f"Evennia Webclient (websocket{browserstr})"
        self.protocol_flags["UTF-8"] = True
        self.protocol_flags["OOB"] = True

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

        Args:
            payload (bytes): The WebSocket message received.
            isBinary (bool): Flag indicating whether payload is binary or
                             UTF-8 encoded text.

        """
        cmdarray = json.loads(str(payload, "utf-8"))
        if cmdarray:
            self.data_in(**{cmdarray[0]: [cmdarray[1], cmdarray[2]]})

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
        Send text data. This will pre-process the text for
        color-replacement, conversion to html etc.

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
                - nocolor (bool): Clean out all color.
                - screenreader (bool): Use Screenreader mode.
                - send_prompt (bool): Send a prompt with parsed html

        """
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

        if screenreader:
            # screenreader mode cleans up output
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)
        cmd = "prompt" if prompt else "text"
        if raw:
            if client_raw:
                args[0] = text
            else:
                args[0] = html.escape(text)  # escape html!
        else:
            args[0] = parse_html(text, strip_ansi=nocolor)

        # send to client on required form [cmdname, args, kwargs]
        self.sendLine(json.dumps([cmd, args, kwargs]))

    def send_prompt(self, *args, **kwargs):
        kwargs["options"].update({"send_prompt": True})
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
        if not cmdname == "options":
            self.sendLine(json.dumps([cmdname, args, kwargs]))
