"""
This implements resources for twisted webservers using the wsgi
interface of django. This alleviates the need of running e.g. an
apache server to serve Evennia's web presence (although you could do
that too if desired).

The actual servers are started inside server.py as part of the Evennia
application.

(Lots of thanks to http://githup.com/clemensha/twisted-wsgi-django for
a great example/aid on how to do this.)

"""
import urlparse
from urllib import quote as urlquote
from twisted.web import resource, http, server
from twisted.internet import reactor
from twisted.application import internet
from twisted.web.proxy import ReverseProxyResource
from twisted.web.server import NOT_DONE_YET

from twisted.web.wsgi import WSGIResource
from django.conf import settings
from django.core.handlers.wsgi import WSGIHandler

_UPSTREAM_IPS = settings.UPSTREAM_IPS
_DEBUG = settings.DEBUG

#
# X-Forwarded-For Handler
#

class HTTPChannelWithXForwardedFor(http.HTTPChannel):
    """
    HTTP xforward class

    """
    def allHeadersReceived(self):
        """
        Check to see if this is a reverse proxied connection.

        """
        CLIENT = 0
        http.HTTPChannel.allHeadersReceived(self)
        req = self.requests[-1]
        client_ip, port = self.transport.client
        proxy_chain = req.getHeader('X-FORWARDED-FOR')
        if proxy_chain and client_ip in _UPSTREAM_IPS:
            forwarded = proxy_chain.split(', ', 1)[CLIENT]
            self.transport.client = (forwarded, port)


# Monkey-patch Twisted to handle X-Forwarded-For.

http.HTTPFactory.protocol = HTTPChannelWithXForwardedFor


class EvenniaReverseProxyResource(ReverseProxyResource):
    def getChild(self, path, request):
        """
        Create and return a proxy resource with the same proxy configuration
        as this one, except that its path also contains the segment given by
        path at the end.

        Args:
            path (str): Url path.
            request (Request object): Incoming request.

        Return:
            resource (EvenniaReverseProxyResource): A proxy resource.

        """
        return EvenniaReverseProxyResource(
            self.host, self.port, self.path + '/' + urlquote(path, safe=""),
            self.reactor)

    def render(self, request):
        """
        Render a request by forwarding it to the proxied server.

        Args:
            request (Request): Incoming request.

        Returns:
            not_done (char): Indicator to note request not yet finished.

        """
        # RFC 2616 tells us that we can omit the port if it's the default port,
        # but we have to provide it otherwise
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path
        clientFactory = self.proxyClientFactoryClass(
            request.method, rest, request.clientproto,
            request.getAllHeaders(), request.content.read(), request)
        self.reactor.connectTCP(self.host, self.port, clientFactory)
        return NOT_DONE_YET


#
# Website server resource
#


class DjangoWebRoot(resource.Resource):
    """
    This creates a web root (/) that Django
    understands by tweaking the way
    child instancee ars recognized.
    """
    def __init__(self, pool):
        """
        Setup the django+twisted resource.

        Args:
            pool (ThreadPool): The twisted threadpool.

        """
        resource.Resource.__init__(self)
        self.wsgi_resource = WSGIResource(reactor, pool, WSGIHandler())

    def getChild(self, path, request):
        """
        To make things work we nudge the url tree to make this the
        root.

        Args:
            path (str): Url path.
            request (Request object): Incoming request.

        """
        path0 = request.prepath.pop(0)
        request.postpath.insert(0, path0)
        return self.wsgi_resource

#
# Site with deactivateable logging
#

class NonLoggingSite(server.Site):
    """
    This class will only log http requests if settings.DEBUG is True.
    """
    def log(self, request):
        "Conditional logging"
        if _DEBUG:
            server.Site.log(self, request)

#
# Threaded Webserver
#

class WSGIWebServer(internet.TCPServer):
    """
    This is a WSGI webserver. It makes sure to start
    the threadpool after the service itself started,
    so as to register correctly with the twisted daemon.

    call with WSGIWebServer(threadpool, port, wsgi_resource)

    """
    def __init__(self, pool, *args, **kwargs):
        """
        This just stores the threadpool.

        Args:
            pool (ThreadPool): The twisted threadpool.
            args, kwargs (any): Passed on to the TCPServer.

        """
        self.pool = pool
        internet.TCPServer.__init__(self, *args, **kwargs)

    def startService(self):
        """
        Start the pool after the service starts.

        """
        internet.TCPServer.startService(self)
        self.pool.start()

    def stopService(self):
        """
        Safely stop the pool after the service stops.

        """
        internet.TCPServer.stopService(self)
        self.pool.stop()
