"""
Web client server resource.

The Evennia web client consists of two components running
on twisted and django. They are both a part of the Evennia
website url tree (so the testing website might be located
on http://localhost:8000/, whereas the webclient can be
found on http://localhost:8000/webclient.)

/webclient - this url is handled through django's template
             system and serves the html page for the client
             itself along with its javascript chat program.
/webclientdata - this url is called by the ajax chat using
                 POST requests (long-polling when necessary)
                 The WebClient resource in this module will
                 handle these requests and act as a gateway
                 to sessions connected over the webclient.
"""
import time
import json

from hashlib import md5

from twisted.web import server, resource

from django.utils.functional import Promise
from django.utils.encoding import force_unicode
from django.conf import settings
from evennia.utils import utils, logger
from evennia.utils.text2html import parse_html
from evennia.server import session

SERVERNAME = settings.SERVERNAME
ENCODINGS = settings.ENCODINGS

# defining a simple json encoder for returning
# django data to the client. Might need to
# extend this if one wants to send more
# complex database objects too.

class LazyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return super(LazyEncoder, self).default(obj)


def jsonify(obj):
    return utils.to_str(json.dumps(obj, ensure_ascii=False, cls=LazyEncoder))


#
# WebClient resource - this is called by the ajax client
# using POST requests to /webclientdata.
#

class WebClient(resource.Resource):
    """
    An ajax/comet long-polling transport

    """
    isLeaf = True
    allowedMethods = ('POST',)

    def __init__(self):
        self.requests = {}
        self.databuffer = {}

    #def getChild(self, path, request):
    #    """
    #    This is the place to put dynamic content.
    #    """
    #    return self

    def _responseFailed(self, failure, suid, request):
        "callback if a request is lost/timed out"
        try:
            del self.requests[suid]
        except KeyError:
            pass

    def lineSend(self, suid, string, data=None):
        """
        This adds the data to the buffer and/or sends it to the client
        as soon as possible.

        Args:
            suid (int): Session id.
            string (str): The text to send.
            data (dict): Optional data.

        Notes:
            The `data` keyword is deprecated.

        """
        request = self.requests.get(suid)
        if request:
            # we have a request waiting. Return immediately.
            request.write(jsonify({'msg': string, 'data': data}))
            request.finish()
            del self.requests[suid]
        else:
            # no waiting request. Store data in buffer
            dataentries = self.databuffer.get(suid, [])
            dataentries.append(jsonify({'msg': string, 'data': data}))
            self.databuffer[suid] = dataentries

    def client_disconnect(self, suid):
        """
        Disconnect session with given suid.

        Args:
            suid (int): Session id.

        """
        if suid in self.requests:
            self.requests[suid].finish()
            del self.requests[suid]
        if suid in self.databuffer:
            del self.databuffer[suid]

    def mode_init(self, request):
        """
        This is called by render_POST when the client requests an init
        mode operation (at startup)

        Args:
            request (Request): Incoming request.

        """
        #csess = request.getSession() # obs, this is a cookie, not
                                      # an evennia session!
        #csees.expireCallbacks.append(lambda : )
        suid = request.args.get('suid', ['0'])[0]

        remote_addr = request.getClientIP()
        host_string = "%s (%s:%s)" % (SERVERNAME, request.getRequestHostname(), request.getHost().port)
        if suid == '0':
            # creating a unique id hash string
            suid = md5(str(time.time())).hexdigest()
            self.databuffer[suid] = []

            sess = WebClientSession()
            sess.client = self
            sess.init_session("webclient", remote_addr, self.sessionhandler)
            sess.suid = suid
            sess.sessionhandler.connect(sess)
        return jsonify({'msg': host_string, 'suid': suid})

    def mode_input(self, request):
        """
        This is called by render_POST when the client
        is sending data to the server.

        Args:
            request (Request): Incoming request.

        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':
            return ''
        sess = self.sessionhandler.session_from_suid(suid)
        if sess:
            sess = sess[0]
            text = request.args.get('msg', [''])[0]
            data = request.args.get('data', [None])[0]
            sess.sessionhandler.data_in(sess, text, data=data)
        return ''

    def mode_receive(self, request):
        """
        This is called by render_POST when the client is telling us
        that it is ready to receive data as soon as it is available.
        This is the basis of a long-polling (comet) mechanism: the
        server will wait to reply until data is available.

        Args:
            request (Request): Incoming request.

        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':
            return ''

        dataentries = self.databuffer.get(suid, [])
        if dataentries:
            return dataentries.pop(0)
        request.notifyFinish().addErrback(self._responseFailed, suid, request)
        if suid in self.requests:
            self.requests[suid].finish()  # Clear any stale request.
        self.requests[suid] = request
        return server.NOT_DONE_YET

    def mode_close(self, request):
        """
        This is called by render_POST when the client is signalling
        that it is about to be closed.

        Args:
            request (Request): Incoming request.

        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':
            self.client_disconnect(suid)
        else:
            try:
                sess = self.sessionhandler.session_from_suid(suid)[0]
                sess.sessionhandler.disconnect(sess)
            except IndexError:
                self.client_disconnect(suid)
                pass
        return ''

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
        dmode = request.args.get('mode', [None])[0]
        if dmode == 'init':
            # startup. Setup the server.
            return self.mode_init(request)
        elif dmode == 'input':
            # input from the client to the server
            return self.mode_input(request)
        elif dmode == 'receive':
            # the client is waiting to receive data.
            return self.mode_receive(request)
        elif dmode == 'close':
            # the client is closing
            return self.mode_close(request)
        else:
            # this should not happen if client sends valid data.
            return ''


#
# A session type handling communication over the
# web client interface.
#

class WebClientSession(session.Session):
    """
    This represents a session running in a webclient.
    """

    def disconnect(self, reason=None):
        """
        Disconnect from server.

        Args:
            reason (str): Motivation for the disconnect.
        """
        if reason:
            self.client.lineSend(self.suid, reason)
        self.client.client_disconnect(self.suid)

    def data_out(self, text=None, **kwargs):
        """
        Data Evennia -> User access hook.

        Kwargs:
            raw (bool): No parsing at all (leave ansi-to-html markers unparsed).
            nomarkup (bool): Clean out all ansi/html markers and tokens.

        """
        # string handling is similar to telnet
        try:
            text = utils.to_str(text if text else "", encoding=self.encoding)
            raw = kwargs.get("raw", False)
            nomarkup = kwargs.get("nomarkup", False)
            if raw:
                self.client.lineSend(self.suid, text)
            else:
                self.client.lineSend(self.suid,
                                     parse_html(text, strip_ansi=nomarkup))
            return
        except Exception:
            logger.log_trace()
