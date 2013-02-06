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
from twisted.web import resource, http
from twisted.python import threadpool
from twisted.internet import reactor
from twisted.application import service, internet

from twisted.web.wsgi import WSGIResource
from django.core.handlers.wsgi import WSGIHandler

from settings import UPSTREAM_IPS

#
# X-Forwarded-For Handler
#

class HTTPChannelWithXForwardedFor(http.HTTPChannel):
    def allHeadersReceived(self):
        """
        Check to see if this is a reverse proxied connection.
        """
        CLIENT = 0
        http.HTTPChannel.allHeadersReceived(self)
        req = self.requests[-1]
        client_ip, port = self.transport.client
        proxy_chain = req.getHeader('X-FORWARDED-FOR')
        if proxy_chain and client_ip in UPSTREAM_IPS:
            forwarded = proxy_chain.split(', ', 1)[CLIENT]
            self.transport.client = (forwarded, port) 


# Monkey-patch Twisted to handle X-Forwarded-For.

http.HTTPFactory.protocol = HTTPChannelWithXForwardedFor

#
# Website server resource
#

class DjangoWebRoot(resource.Resource):
    """
    This creates a web root (/) that Django
    understands by tweaking the way the
    child instancee are recognized.
    """
    def __init__(self, pool):
        """
        Setup the django+twisted resource
        """
        resource.Resource.__init__(self)
        self.wsgi_resource = WSGIResource(reactor, pool , WSGIHandler())

    def getChild(self, path, request):
        """
        To make things work we nudge the
        url tree to make this the root.
        """
        path0 = request.prepath.pop(0)
        request.postpath.insert(0, path0)
        return self.wsgi_resource
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
    def __init__(self, pool, *args, **kwargs ):
        "This just stores the threadpool"
        self.pool = pool
        internet.TCPServer.__init__(self, *args, **kwargs)
    def startService(self):
        "Start the pool after the service"
        internet.TCPServer.startService(self)
        self.pool.start()
    def stopService(self):
        "Safely stop the pool after service stop."
        internet.TCPServer.stopService(self)
        self.pool.stop()
