"""
This defines the the parent for all subprocess children.

Inherit from this to define a new type of subprocess.

"""

from twisted.python import log
from twisted.internet import error
from twisted.protocols import amp
from contrib.procpools.ampoule.commands import Echo, Shutdown, Ping

class AMPChild(amp.AMP):
    def __init__(self):
        super(AMPChild, self).__init__(self)
        self.shutdown = False

    def connectionLost(self, reason):
        amp.AMP.connectionLost(self, reason)
        from twisted.internet import reactor
        try:
            reactor.stop()
        except error.ReactorNotRunning:
            # woa, this means that something bad happened,
            # most probably we received a SIGINT. Now this is only
            # a problem when you use Ctrl+C to stop the main process
            # because it would send the SIGINT to child processes too.
            # In all other cases receiving a SIGINT here would be an
            # error condition and correctly restarted. maybe we should
            # use sigprocmask?
            pass
        if not self.shutdown:
            # if the shutdown wasn't explicit we presume that it's an
            # error condition and thus we return a -1 error returncode.
            import os
            os._exit(-1)

    def shutdown(self):
        """
        This method is needed to shutdown the child gently without
        generating an exception.
        """
        #log.msg("Shutdown message received, goodbye.")
        self.shutdown = True
        return {}
    Shutdown.responder(shutdown)

    def ping(self):
        """
        Ping the child and return an answer
        """
        return {'response': "pong"}
    Ping.responder(ping)

    def echo(self, data):
        """
        Echo some data through the child.
        """
        return {'response': data}
    Echo.responder(echo)
