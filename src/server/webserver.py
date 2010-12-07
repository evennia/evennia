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
from twisted.web import resource
from twisted.python import threadpool
from twisted.internet import reactor

from twisted.web.wsgi import WSGIResource
from django.core.handlers.wsgi import WSGIHandler

#
# Website server resource
#

class DjangoWebRoot(resource.Resource):
    """
    This creates a web root (/) that Django
    understands by tweaking the way the 
    child instancee are recognized. 
    """

    def __init__(self):
        """
        Setup the django+twisted resource
        """
        resource.Resource.__init__(self)
        self.wsgi_resource = self._wsgi_resource()

    def _wsgi_resource(self):
        """
        Sets up a threaded webserver resource by tying
        django and twisted together.        
        """
        # Start the threading
        pool = threadpool.ThreadPool()
        pool.start()
        # Set it up so the pool stops after e.g. Ctrl-C kills the server 
        reactor.addSystemEventTrigger('after', 'shutdown', pool.stop)
        # combine twisted's wsgi resource with django's wsgi handler
        wsgi_resource = WSGIResource(reactor, pool, WSGIHandler())
        return wsgi_resource 

    def getChild(self, path, request):
        """
        To make things work we nudge the 
        url tree to make this the root.
        """
        path0 = request.prepath.pop(0)
        request.postpath.insert(0, path0)
        return self.wsgi_resource
