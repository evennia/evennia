import os

from twisted.application import service
from twisted.internet.protocol import ServerFactory

def makeService(options):
    """
    Create the service for the application
    """
    ms = service.MultiService()

    from contrib.procpools.ampoule.pool import ProcessPool
    from contrib.procpools.ampoule.main import ProcessStarter
    name = options['name']
    ampport = options['ampport']
    ampinterface = options['ampinterface']
    child = options['child']
    parent = options['parent']
    min = options['min']
    max = options['max']
    maxIdle = options['max_idle']
    recycle = options['recycle']
    childReactor = options['reactor']
    timeout = options['timeout']

    starter = ProcessStarter(packages=("twisted", "ampoule"), childReactor=childReactor)
    pp = ProcessPool(child, parent, min, max, name, maxIdle, recycle, starter, timeout)
    svc = AMPouleService(pp, child, ampport, ampinterface)
    svc.setServiceParent(ms)

    return ms

class AMPouleService(service.Service):
    def __init__(self, pool, child, port, interface):
        self.pool = pool
        self.port = port
        self.child = child
        self.interface = interface
        self.server = None

    def startService(self):
        """
        Before reactor.run() is called we setup the system.
        """
        service.Service.startService(self)
        from contrib.procpools.ampoule import rpool
        from twisted.internet import reactor

        try:
            factory = ServerFactory()
            factory.protocol = lambda: rpool.AMPProxy(wrapped=self.pool.doWork,
                                                      child=self.child)
            self.server = reactor.listenTCP(self.port,
                                            factory,
                                            interface=self.interface)
            # this is synchronous when it's the startup, even though
            # it returns a deferred. But we need to run it after the
            # first cycle in order to wait for signal handlers to be
            # installed.
            reactor.callLater(0, self.pool.start)
        except:
            import traceback
            print traceback.format_exc()

    def stopService(self):
        service.Service.stopService(self)
        if self.server is not None:
            self.server.stopListening()
        return self.pool.stop()
