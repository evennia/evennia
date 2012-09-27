import os
import sys
import imp
import itertools

from zope.interface import implements

from twisted.internet import reactor, protocol, defer, error
from twisted.python import log, util, reflect
from twisted.protocols import amp
from twisted.python import runtime
from twisted.python.compat import set

from contrib.procpools.ampoule import iampoule

gen = itertools.count()

if runtime.platform.isWindows():
    IS_WINDOWS = True
    TO_CHILD = 0
    FROM_CHILD = 1
else:
    IS_WINDOWS = False
    TO_CHILD = 3
    FROM_CHILD = 4

class AMPConnector(protocol.ProcessProtocol):
    """
    A L{ProcessProtocol} subclass that can understand and speak AMP.

    @ivar amp: the children AMP process
    @type amp: L{amp.AMP}

    @ivar finished: a deferred triggered when the process dies.
    @type finished: L{defer.Deferred}

    @ivar name: Unique name for the connector, much like a pid.
    @type name: int
    """

    def __init__(self, proto, name=None):
        """
        @param proto: An instance or subclass of L{amp.AMP}
        @type proto: L{amp.AMP}

        @param name: optional name of the subprocess.
        @type name: int
        """
        self.finished = defer.Deferred()
        self.amp = proto
        self.name = name
        if name is None:
            self.name = gen.next()

    def signalProcess(self, signalID):
        """
        Send the signal signalID to the child process

        @param signalID: The signal ID that you want to send to the
                        corresponding child
        @type signalID: C{str} or C{int}
        """
        return self.transport.signalProcess(signalID)

    def connectionMade(self):
        #log.msg("Subprocess %s started." % (self.name,))
        self.amp.makeConnection(self)

    # Transport
    disconnecting = False

    def write(self, data):
        if IS_WINDOWS:
            self.transport.write(data)
        else:
            self.transport.writeToChild(TO_CHILD, data)

    def loseConnection(self):
        self.transport.closeChildFD(TO_CHILD)
        self.transport.closeChildFD(FROM_CHILD)
        self.transport.loseConnection()

    def getPeer(self):
        return ('subprocess %i' % self.name,)

    def getHost(self):
        return ('Evennia Server',)

    def childDataReceived(self, childFD, data):
        if childFD == FROM_CHILD:
            self.amp.dataReceived(data)
            return
        self.errReceived(data)

    def errReceived(self, data):
        for line in data.strip().splitlines():
            log.msg("FROM %s: %s" % (self.name, line))

    def processEnded(self, status):
        #log.msg("Process: %s ended" % (self.name,))
        self.amp.connectionLost(status)
        if status.check(error.ProcessDone):
            self.finished.callback('')
            return
        self.finished.errback(status)

BOOTSTRAP = """\
import sys

def main(reactor, ampChildPath):
    from twisted.application import reactors
    reactors.installReactor(reactor)

    from twisted.python import log
    %s

    from twisted.internet import reactor, stdio
    from twisted.python import reflect, runtime

    ampChild = reflect.namedAny(ampChildPath)
    ampChildInstance = ampChild(*sys.argv[1:-2])
    if runtime.platform.isWindows():
        stdio.StandardIO(ampChildInstance)
    else:
        stdio.StandardIO(ampChildInstance, %s, %s)
    enter = getattr(ampChildInstance, '__enter__', None)
    if enter is not None:
        enter()
    try:
        reactor.run()
    except:
        if enter is not None:
            info = sys.exc_info()
            if not ampChildInstance.__exit__(*info):
                raise
        else:
            raise
    else:
        if enter is not None:
            ampChildInstance.__exit__(None, None, None)

main(sys.argv[-2], sys.argv[-1])
""" % ('%s', TO_CHILD, FROM_CHILD)

# in the first spot above, either insert an empty string or
# 'log.startLogging(sys.stderr)'
# to start logging

class ProcessStarter(object):

    implements(iampoule.IStarter)

    connectorFactory = AMPConnector
    def __init__(self, bootstrap=BOOTSTRAP, args=(), env={},
                 path=None, uid=None, gid=None, usePTY=0,
                 packages=(), childReactor="select"):
        """
        @param bootstrap: Startup code for the child process
        @type  bootstrap: C{str}

        @param args: Arguments that should be supplied to every child
                     created.
        @type args: C{tuple} of C{str}

        @param env: Environment variables that should be present in the
                    child environment
        @type env: C{dict}

        @param path: Path in which to run the child
        @type path: C{str}

        @param uid: if defined, the uid used to run the new process.
        @type uid: C{int}

        @param gid: if defined, the gid used to run the new process.
        @type gid: C{int}

        @param usePTY: Should the child processes use PTY processes
        @type usePTY: 0 or 1

        @param packages: A tuple of packages that should be guaranteed
                         to be importable in the child processes
        @type packages: C{tuple} of C{str}

        @param childReactor: a string that sets the reactor for child
                             processes
        @type childReactor: C{str}
        """
        self.bootstrap = bootstrap
        self.args = args
        self.env = env
        self.path = path
        self.uid = uid
        self.gid = gid
        self.usePTY = usePTY
        self.packages = ("ampoule",) + packages
        self.packages = packages
        self.childReactor = childReactor

    def __repr__(self):
        """
        Represent the ProcessStarter with a string.
        """
        return """ProcessStarter(bootstrap=%r,
                                 args=%r,
                                 env=%r,
                                 path=%r,
                                 uid=%r,
                                 gid=%r,
                                 usePTY=%r,
                                 packages=%r,
                                 childReactor=%r)""" % (self.bootstrap,
                                                        self.args,
                                                        self.env,
                                                        self.path,
                                                        self.uid,
                                                        self.gid,
                                                        self.usePTY,
                                                        self.packages,
                                                        self.childReactor)

    def _checkRoundTrip(self, obj):
        """
        Make sure that an object will properly round-trip through 'qual' and
        'namedAny'.

        Raise a L{RuntimeError} if they aren't.
        """
        tripped = reflect.namedAny(reflect.qual(obj))
        if tripped is not obj:
            raise RuntimeError("importing %r is not the same as %r" %
                               (reflect.qual(obj), obj))

    def startAMPProcess(self, ampChild, ampParent=None, ampChildArgs=()):
        """
        @param ampChild: a L{ampoule.child.AMPChild} subclass.
        @type ampChild: L{ampoule.child.AMPChild}

        @param ampParent: an L{amp.AMP} subclass that implements the parent
                          protocol for this process pool
        @type ampParent: L{amp.AMP}
        """
        self._checkRoundTrip(ampChild)
        fullPath = reflect.qual(ampChild)
        if ampParent is None:
            ampParent = amp.AMP
        prot = self.connectorFactory(ampParent())
        args = ampChildArgs + (self.childReactor, fullPath)
        return self.startPythonProcess(prot, *args)


    def startPythonProcess(self, prot, *args):
        """
        @param prot: a L{protocol.ProcessProtocol} subclass
        @type prot: L{protocol.ProcessProtocol}

        @param args: a tuple of arguments that will be added after the
                     ones in L{self.args} to start the child process.

        @return: a tuple of the child process and the deferred finished.
                 finished triggers when the subprocess dies for any reason.
        """
        spawnProcess(prot, self.bootstrap, self.args+args, env=self.env,
                     path=self.path, uid=self.uid, gid=self.gid,
                     usePTY=self.usePTY, packages=self.packages)

        # XXX: we could wait for startup here, but ... is there really any
        # reason to?  the pipe should be ready for writing.  The subprocess
        # might not start up properly, but then, a subprocess might shut down
        # at any point too. So we just return amp and have this piece to be
        # synchronous.
        return prot.amp, prot.finished

def spawnProcess(processProtocol, bootstrap, args=(), env={},
                 path=None, uid=None, gid=None, usePTY=0,
                 packages=()):
    env = env.copy()

    pythonpath = []
    for pkg in packages:
        pkg_path, name = os.path.split(pkg)
        p = os.path.split(imp.find_module(name, [pkg_path] if pkg_path else None)[1])[0]
        if p.startswith(os.path.join(sys.prefix, 'lib')):
            continue
        pythonpath.append(p)
    pythonpath = list(set(pythonpath))
    pythonpath.extend(env.get('PYTHONPATH', '').split(os.pathsep))
    env['PYTHONPATH'] = os.pathsep.join(pythonpath)
    args = (sys.executable, '-c', bootstrap) + args
    # childFDs variable is needed because sometimes child processes
    # misbehave and use stdout to output stuff that should really go
    # to stderr. Of course child process might even use the wrong FDs
    # that I'm using here, 3 and 4, so we are going to fix all these
    # issues when I add support for the configuration object that can
    # fix this stuff in a more configurable way.
    if IS_WINDOWS:
        return reactor.spawnProcess(processProtocol, sys.executable, args,
                                    env, path, uid, gid, usePTY)
    else:
        return reactor.spawnProcess(processProtocol, sys.executable, args,
                                    env, path, uid, gid, usePTY,
                                    childFDs={0:"w", 1:"r", 2:"r", 3:"w", 4:"r"})
