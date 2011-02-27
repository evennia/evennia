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
from hashlib import md5

from twisted.web import server, resource
from twisted.internet import defer, reactor

from django.utils import simplejson
from django.utils.functional import Promise
from django.utils.encoding import force_unicode
from django.conf import settings 
from src.utils import utils
from src.utils.text2html import parse_html
from src.config.models import ConnectScreen
from src.server import session
from src.server.sessionhandler import SESSIONS

SERVERNAME = settings.SERVERNAME
ENCODINGS = settings.ENCODINGS

# defining a simple json encoder for returning
# django data to the client. Might need to 
# extend this if one wants to send more
# complex database objects too.

class LazyEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_unicode(obj)
        return super(LazyEncoder, self).default(obj)
def jsonify(obj):
    return utils.to_str(simplejson.dumps(obj, ensure_ascii=False, cls=LazyEncoder))


#
# WebClient resource - this is called by the ajax client
# using POST requests to /webclientdata.
#
    
class WebClient(resource.Resource):
    """
    An ajax/comet long-polling transport protocol for 
    """
    isLeaf = True 
    allowedMethods = ('POST',)

    def __init__(self):
        self.requests = {}
        self.databuffer = {}
        
    def getChild(self, path, request):
        """
        This is the place to put dynamic content.
        """
        return self                 
    
    def _responseFailed(self, failure, suid, request):
        "callback if a request is lost/timed out"                        
        try:
            self.requests.get(suid, []).remove(request)
        except ValueError:
            pass 
        
    def lineSend(self, suid, string, data=None):
        """
        This adds the data to the buffer and/or sends it to
        the client as soon as possible.
        """    
        requests = self.requests.get(suid, None)
        if requests:
            request = requests.pop(0)
            # we have a request waiting. Return immediately.
            request.write(jsonify({'msg':string, 'data':data}))
            request.finish()
            self.requests[suid] = requests
        else:            
            # no waiting request. Store data in buffer
            dataentries = self.databuffer.get(suid, [])
            dataentries.append(jsonify({'msg':string, 'data':data}))
            self.databuffer[suid] = dataentries
    
    def disconnect(self, suid, step=1):
        """
        Disconnect session with given suid.

        step 1 : call session_disconnect()
        step 2 : finalize disconnection        
        """        

        if step == 1:
            sess = SESSIONS.session_from_suid(suid)
            sess[0].session_disconnect()
        else:
            if self.requests.has_key(suid):
                for request in self.requests.get(suid, []):
                    request.finish()
                    del self.requests[suid]
            if self.databuffer.has_key(suid):
                del self.databuffer[suid]                

    def mode_init(self, request):
        """
        This is called by render_POST when the client
        requests an init mode operation (at startup)
        """
        #csess = request.getSession() # obs, this is a cookie, not an evennia session!
        #csees.expireCallbacks.append(lambda : )
        suid = request.args.get('suid', ['0'])[0]

        remote_addr = request.getClientIP()
        host_string = "%s (%s:%s)" % (SERVERNAME, request.getRequestHostname(), request.getHost().port)
        if suid == '0':
            # creating a unique id hash string
            suid = md5(str(time.time())).hexdigest()
            self.requests[suid] = []
            self.databuffer[suid] = []        

            sess = WebClientSession()
            sess.client = self        
            sess.session_connect(remote_addr, suid)            
        return jsonify({'msg':host_string, 'suid':suid})

    def mode_input(self, request):
        """
        This is called by render_POST when the client
        is sending data to the server.
        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':
            return ''
        sess = SESSIONS.session_from_suid(suid)
        if sess:
            string = request.args.get('msg', [''])[0]
            data = request.args.get('data', [None])[0]
            sess[0].at_data_in(string, data)
        return ''

    def mode_receive(self, request):
        """
        This is called by render_POST when the client is telling us
        that it is ready to receive data as soon as it is
        available. This is the basis of a long-polling (comet)
        mechanism: the server will wait to reply until data is
        available.
        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':            
            return ''
        
        dataentries = self.databuffer.get(suid, [])
        if dataentries:
            return dataentries.pop(0)
        reqlist = self.requests.get(suid, [])
        request.notifyFinish().addErrback(self._responseFailed, suid, request)
        reqlist.append(request)                
        self.requests[suid] = reqlist
        return server.NOT_DONE_YET

    def mode_close(self, request):
        """
        This is called by render_POST when the client is signalling
        that it is about to be closed. 
        """
        suid = request.args.get('suid', ['0'])[0]
        if suid == '0':
            self.disconnect(suid)
        return ''

    def render_POST(self, request):
        """
        This function is what Twisted calls with POST requests coming
        in from the ajax client. The requests should be tagged with
        different modes depending on what needs to be done, such as
        initializing or sending/receving data through the request. It
        uses a long-polling mechanism to avoid sending data unless
        there is actual data available.
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
    
    def at_connect(self):
        """
        Show the banner screen. Grab from the 'connect_screen'
        config directive. If more than one connect screen is
        defined in the ConnectScreen attribute, it will be
        random which screen is used. 
        """
        # show screen 
        screen = ConnectScreen.objects.get_random_connect_screen()
        #string = parse_html(screen.text)
        self.at_data_out(screen.text)
        
    def at_login(self, player):
        """
        Called after authentication. self.logged_in=True at this point.
        """
        if player.has_attribute('telnet_markup'):
            self.telnet_markup = player.get_attribute("telnet_markup")
        else:
            self.telnet_markup = True             

    def at_disconnect(self, reason=None):
        """
        Disconnect from server
        """                        
        if reason:
            self.lineSend(self.suid, reason)
        self.client.disconnect(self.suid, step=2)

    def at_data_out(self, string='', data=None):
        """
        Data Evennia -> Player access hook. 

        data argument may be used depending on
        the client-server implementation. 
        """
        
        if data:
            # treat data?
            pass

        # string handling is similar to telnet
        if self.encoding:
            try:
                string = utils.to_str(string, encoding=self.encoding)                
                self.client.lineSend(self.suid, parse_html(string))
                return 
            except Exception:
                pass
        # malformed/wrong encoding defined on player - try some defaults
        for encoding in ENCODINGS:
            try:
                string = utils.to_str(string, encoding=encoding)
                err = None
                break 
            except Exception, e:
                err = str(e)                
                continue
        if err:
            self.client.lineSend(self.suid, err)
        else:
            #self.client.lineSend(self.suid, ansi.parse_ansi(string, strip_ansi=True))
            self.client.lineSend(self.suid, parse_html(string))
    def at_data_in(self, string, data=None):
        """
        Input from Player -> Evennia (called by client protocol). 
        Use of 'data' is up to the client - server implementation.
        """
        
        # treat data?
        if data:
            pass

        # the string part is identical to telnet
        if self.encoding:
            try:            
                string = utils.to_unicode(string, encoding=self.encoding)
                self.execute_cmd(string)
                return 
            except Exception, e:
                err = str(e)
                print err
        # malformed/wrong encoding defined on player - try some defaults 
        for encoding in ENCODINGS:
            try:
                string = utils.to_unicode(string, encoding=encoding)
                err = None
                break             
            except Exception, e:
                err = str(e)
                continue         
        self.execute_cmd(string)

