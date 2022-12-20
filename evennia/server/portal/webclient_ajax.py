"""
AJAX/COMET fallback webclient

The AJAX/COMET web client consists of two components running on
twisted and django. They are both a part of the Evennia website url
tree (so the testing website might be located on
http://localhost:4001/, whereas the webclient can be found on
http://localhost:4001/webclient.)

/webclient - this url is handled through django's template
             system and serves the html page for the client
             itself along with its javascript chat program.
/webclientdata - this url is called by the ajax chat using
                 POST requests (long-polling when necessary)
                 The WebClient resource in this module will
                 handle these requests and act as a gateway
                 to sessions connected over the webclient.

"""
import html
import json
import re
import time

from django.conf import settings
from django.utils.functional import Promise
from twisted.internet.task import LoopingCall
from twisted.web import resource, server

from evennia.server import session
from evennia.utils import utils
from evennia.utils.ansi import parse_ansi
from evennia.utils.text2html import parse_html
from evennia.utils.utils import to_bytes

_CLIENT_SESSIONS = utils.mod_import(settings.SESSION_ENGINE).SessionStore
_RE_SCREENREADER_REGEX = re.compile(
    r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)
_SERVERNAME = settings.SERVERNAME
_KEEPALIVE = 30  # how often to check keepalive


# defining a simple json encoder for returning
# django data to the client. Might need to
# extend this if one wants to send more
# complex database objects too.


class LazyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return str(obj)
        return super().default(obj)


def jsonify(obj):
    return to_bytes(json.dumps(obj, ensure_ascii=False, cls=LazyEncoder))


#
# AjaxWebClient resource - this is called by the ajax client
# using POST requests to /webclientdata.
#


class AjaxWebClient(resource.Resource):
    """
    An ajax/comet long-polling transport

    """

    isLeaf = True
    allowedMethods = ("POST",)

    def __init__(self):
        self.requests = {}
        self.databuffer = {}

        self.last_alive = {}
        self.keep_alive = None

    def _responseFailed(self, failure, csessid, request):
        "callback if a request is lost/timed out"
        try:
            del self.requests[csessid]
        except KeyError:
            # nothing left to delete
            pass

    def _keepalive(self):
        """
        Callback for checking the connection is still alive.
        """
        now = time.time()
        to_remove = []
        keep_alives = (
            (csessid, remove)
            for csessid, (t, remove) in self.last_alive.items()
            if now - t > _KEEPALIVE
        )
        for csessid, remove in keep_alives:
            if remove:
                # keepalive timeout. Line is dead.
                to_remove.append(csessid)
            else:
                # normal timeout - send keepalive
                self.last_alive[csessid] = (now, True)
                self.lineSend(csessid, ["ajax_keepalive", [], {}])
        # remove timed-out sessions
        for csessid in to_remove:
            sessions = self.sessionhandler.sessions_from_csessid(csessid)
            for sess in sessions:
                sess.disconnect()
            self.last_alive.pop(csessid, None)
            if not self.last_alive:
                # no more ajax clients. Stop the keepalive
                self.keep_alive.stop()
                self.keep_alive = None

    def get_client_sessid(self, request):
        """
        Helper to get the client session id out of the request.

        Args:
            request (Request): Incoming request object.
        Returns:
            csessid (int): The client-session id.

        """
        return html.escape(request.args[b"csessid"][0].decode("utf-8"))

    def get_browserstr(self, request):
        """
        Get browser-string out of the request.

        Args:
            request (Request): Incoming request object.
        Returns:
            str: The browser name.


        """
        return html.escape(request.args[b"browserstr"][0].decode("utf-8"))

    def at_login(self):
        """
        Called when this session gets authenticated by the server.
        """
        pass

    def lineSend(self, csessid, data):
        """
        This adds the data to the buffer and/or sends it to the client
        as soon as possible.

        Args:
            csessid (int): Session id.
            data (list): A send structure [cmdname, [args], {kwargs}].

        """
        request = self.requests.get(csessid)
        if request:
            # we have a request waiting. Return immediately.
            request.write(jsonify(data))
            request.finish()
            del self.requests[csessid]
        else:
            # no waiting request. Store data in buffer
            dataentries = self.databuffer.get(csessid, [])
            dataentries.append(jsonify(data))
            self.databuffer[csessid] = dataentries

    def client_disconnect(self, csessid):
        """
        Disconnect session with given csessid.

        Args:
            csessid (int): Session id.

        """
        if csessid in self.requests:
            self.requests[csessid].finish()
            del self.requests[csessid]
        if csessid in self.databuffer:
            del self.databuffer[csessid]

    def mode_init(self, request):
        """
        This is called by render_POST when the client requests an init
        mode operation (at startup)

        Args:
            request (Request): Incoming request.

        """
        csessid = self.get_client_sessid(request)
        browserstr = self.get_browserstr(request)

        remote_addr = request.getClientIP()

        if remote_addr in settings.UPSTREAM_IPS and request.getHeader("x-forwarded-for"):
            addresses = [x.strip() for x in request.getHeader("x-forwarded-for").split(",")]
            addresses.reverse()

            for addr in addresses:
                if addr not in settings.UPSTREAM_IPS:
                    remote_addr = addr
                    break

        host_string = "%s (%s:%s)" % (
            _SERVERNAME,
            request.getRequestHostname(),
            request.getHost().port,
        )

        sess = AjaxWebClientSession()
        sess.client = self
        sess.init_session("ajax/comet", remote_addr, self.sessionhandler)

        sess.csessid = csessid
        sess.browserstr = browserstr
        csession = _CLIENT_SESSIONS(session_key=sess.csessid)
        uid = csession and csession.get("webclient_authenticated_uid", False)
        if uid:
            # the client session is already logged in
            sess.uid = uid
            sess.logged_in = True

        # watch for dead links
        self.last_alive[csessid] = (time.time(), False)
        if not self.keep_alive:
            # the keepalive is not running; start it.
            self.keep_alive = LoopingCall(self._keepalive)
            self.keep_alive.start(_KEEPALIVE, now=False)

        browserstr = f":{browserstr}" if browserstr else ""
        sess.protocol_flags["CLIENTNAME"] = f"Evennia Webclient (ajax{browserstr})"
        sess.protocol_flags["UTF-8"] = True
        sess.protocol_flags["OOB"] = True

        # actually do the connection
        sess.sessionhandler.connect(sess)

        return jsonify({"msg": host_string, "csessid": csessid})

    def mode_keepalive(self, request):
        """
        This is called by render_POST when the
        client is replying to the keepalive.

        Args:
            request (Request): Incoming request.

        """
        csessid = self.get_client_sessid(request)
        self.last_alive[csessid] = (time.time(), False)
        return b'""'

    def mode_input(self, request):
        """
        This is called by render_POST when the client
        is sending data to the server.

        Args:
            request (Request): Incoming request.

        """
        csessid = self.get_client_sessid(request)
        self.last_alive[csessid] = (time.time(), False)
        cmdarray = json.loads(request.args.get(b"data")[0])
        for sess in self.sessionhandler.sessions_from_csessid(csessid):
            sess.data_in(**{cmdarray[0]: [cmdarray[1], cmdarray[2]]})
        return b'""'

    def mode_receive(self, request):
        """
        This is called by render_POST when the client is telling us
        that it is ready to receive data as soon as it is available.
        This is the basis of a long-polling (comet) mechanism: the
        server will wait to reply until data is available.

        Args:
            request (Request): Incoming request.

        """
        csessid = html.escape(request.args[b"csessid"][0].decode("utf-8"))
        self.last_alive[csessid] = (time.time(), False)

        dataentries = self.databuffer.get(csessid)
        if dataentries:
            # we have data that could not be sent earlier (because client was not
            # ready to receive it). Return this buffered data immediately
            return dataentries.pop(0)
        else:
            # we have no data to send. End the old request and start
            # a new long-polling one
            request.notifyFinish().addErrback(self._responseFailed, csessid, request)
            if csessid in self.requests:
                self.requests[csessid].finish()  # Clear any stale request.
            self.requests[csessid] = request
            return server.NOT_DONE_YET

    def mode_close(self, request):
        """
        This is called by render_POST when the client is signalling
        that it is about to be closed.

        Args:
            request (Request): Incoming request.

        """
        csessid = self.get_client_sessid(request)
        try:
            sess = self.sessionhandler.sessions_from_csessid(csessid)[0]
            sess.sessionhandler.disconnect(sess)
        except IndexError:
            self.client_disconnect(csessid)
        return b'""'

    def render_POST(self, request):
        """
        This function is what Twisted calls with POST requests coming
        in from the ajax client. The requests should be tagged with
        different modes depending on what needs to be done, such as
        initializing or sending/receving data through the request. It
        uses a long-polling mechanism to avoid sending data unless
        there is actual data available.

        Args:
            request (Request): Incoming request.

        """
        dmode = request.args.get(b"mode", [b"None"])[0].decode("utf-8")

        if dmode == "init":
            # startup. Setup the server.
            return self.mode_init(request)
        elif dmode == "input":
            # input from the client to the server
            return self.mode_input(request)
        elif dmode == "receive":
            # the client is waiting to receive data.
            return self.mode_receive(request)
        elif dmode == "close":
            # the client is closing
            return self.mode_close(request)
        elif dmode == "keepalive":
            # A reply to our keepalive request - all is well
            return self.mode_keepalive(request)
        else:
            # This should not happen if client sends valid data.
            return b'""'


#
# A session type handling communication over the
# web client interface.
#


class AjaxWebClientSession(session.Session):
    """
    This represents a session running in an AjaxWebclient.
    """

    def __init__(self, *args, **kwargs):
        self.protocol_key = "webclient/ajax"
        super().__init__(*args, **kwargs)

    def get_client_session(self):
        """
        Get the Client browser session (used for auto-login based on browser session)

        Returns:
            csession (ClientSession): This is a django-specific internal representation
                of the browser session.

        """
        if self.csessid:
            return _CLIENT_SESSIONS(session_key=self.csessid)

    def disconnect(self, reason="Server disconnected."):
        """
        Disconnect from server.

        Args:
            reason (str): Motivation for the disconnect.
        """
        csession = self.get_client_session()

        if csession:
            csession["webclient_authenticated_uid"] = None
            csession.save()
            self.logged_in = False
        self.client.lineSend(self.csessid, ["connection_close", [reason], {}])
        self.client.client_disconnect(self.csessid)
        self.sessionhandler.disconnect(self)

    def at_login(self):
        csession = self.get_client_session()
        if csession:
            csession["webclient_authenticated_uid"] = self.uid
            csession.save()

    def data_in(self, **kwargs):
        """
        Data User -> Evennia

        Keyword Args:
            kwargs (any): Incoming data.

        """
        self.sessionhandler.data_in(self, **kwargs)

    def data_out(self, **kwargs):
        """
        Data Evennia -> User

        Keyword Args:
            kwargs (any): Options to the protocol
        """
        self.sessionhandler.data_out(self, **kwargs)

    def send_text(self, *args, **kwargs):
        """
        Send text data. This will pre-process the text for
        color-replacement, conversion to html etc.

        Args:
            text (str): Text to send.

        Keyword Args:
            options (dict): Options-dict with the following keys understood:
                - raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
                - nocolor (bool): Remove all color.
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
        text = utils.to_str(text)

        options = kwargs.pop("options", {})
        raw = options.get("raw", flags.get("RAW", False))
        xterm256 = options.get("xterm256", flags.get("XTERM256", True))
        useansi = options.get("ansi", flags.get("ANSI", True))
        nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))
        prompt = options.get("send_prompt", False)

        if screenreader:
            # screenreader mode cleans up output
            text = parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)
        cmd = "prompt" if prompt else "text"
        if raw:
            args[0] = text
        else:
            args[0] = parse_html(text, strip_ansi=nocolor)

        # send to client on required form [cmdname, args, kwargs]
        self.client.lineSend(self.csessid, [cmd, args, kwargs])

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
            self.client.lineSend(self.csessid, [cmdname, args, kwargs])
