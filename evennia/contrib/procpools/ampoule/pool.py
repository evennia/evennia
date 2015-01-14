import time
import random
import heapq
import itertools
import signal
choice = random.choice
now = time.time
count = itertools.count().next
pop = heapq.heappop

from twisted.internet import defer, task, error
from twisted.python import log, failure

from contrib.procpools.ampoule import commands, main

try:
    DIE = signal.SIGKILL
except AttributeError:
    # Windows doesn't have SIGKILL, let's just use SIGTERM then
    DIE = signal.SIGTERM

class ProcessPool(object):
    """
    This class generalizes the functionality of a pool of
    processes to which work can be dispatched.

    @ivar finished: Boolean flag, L{True} when the pool is finished.

    @ivar started: Boolean flag, L{True} when the pool is started.

    @ivar name: Optional name for the process pool

    @ivar min: Minimum number of subprocesses to set up

    @ivar max: Maximum number of subprocesses to set up

    @ivar maxIdle: Maximum number of seconds of indleness in a child

    @ivar starter: A process starter instance that provides
                    L{iampoule.IStarter}.

    @ivar recycleAfter: Maximum number of calls before restarting a
                        subprocess, 0 to not recycle.

    @ivar ampChild: The child AMP protocol subclass with the commands
                    that the child should implement.

    @ivar ampParent: The parent AMP protocol subclass with the commands
                    that the parent should implement.

    @ivar timeout: The general timeout (in seconds) for every child
                    process call.
    """

    finished = False
    started = False
    name = None

    def __init__(self, ampChild=None, ampParent=None, min=5, max=20,
                 name=None, maxIdle=20, recycleAfter=500, starter=None,
                 timeout=None, timeout_signal=DIE, ampChildArgs=()):
        self.starter = starter
        self.ampChildArgs = tuple(ampChildArgs)
        if starter is None:
            self.starter = main.ProcessStarter(packages=("twisted", "ampoule"))
        self.ampParent = ampParent
        self.ampChild = ampChild
        if ampChild is None:
            from contrib.procpools.ampoule.child import AMPChild
            self.ampChild = AMPChild
        self.min = min
        self.max = max
        self.name = name
        self.maxIdle = maxIdle
        self.recycleAfter = recycleAfter
        self.timeout = timeout
        self.timeout_signal = timeout_signal
        self._queue = []

        self.processes = set()
        self.ready = set()
        self.busy = set()
        self._finishCallbacks = {}
        self._lastUsage = {}
        self._calls = {}
        self.looping = task.LoopingCall(self._pruneProcesses)
        self.looping.start(maxIdle, now=False)

    def start(self, ampChild=None):
        """
        Starts the ProcessPool with a given child protocol.

        @param ampChild: a L{ampoule.child.AMPChild} subclass.
        @type ampChild: L{ampoule.child.AMPChild} subclass
        """
        if ampChild is not None and not self.started:
            self.ampChild = ampChild
        self.finished = False
        self.started = True
        return self.adjustPoolSize()

    def _pruneProcesses(self):
        """
        Remove idle processes from the pool.
        """
        n = now()
        d = []
        for child, lastUse in self._lastUsage.iteritems():
            if len(self.processes) > self.min and (n - lastUse) > self.maxIdle:
                # we are setting lastUse when processing finishes, it
                # might be processing right now
                if child not in self.busy:
                    # we need to remove this child from the ready set
                    # and the processes set because otherwise it might
                    # get calls from doWork
                    self.ready.discard(child)
                    self.processes.discard(child)
                    d.append(self.stopAWorker(child))
        return defer.DeferredList(d)

    def _pruneProcess(self, child):
        """
        Remove every trace of the process from this instance.
        """
        self.processes.discard(child)
        self.ready.discard(child)
        self.busy.discard(child)
        self._lastUsage.pop(child, None)
        self._calls.pop(child, None)
        self._finishCallbacks.pop(child, None)

    def _addProcess(self, child, finished):
        """
        Adds the newly created child process to the pool.
        """
        def restart(child, reason):
            #log.msg("FATAL: Restarting after %s" % (reason,))
            self._pruneProcess(child)
            return self.startAWorker()

        def dieGently(data, child):
            #log.msg("STOPPING: '%s'" % (data,))
            self._pruneProcess(child)

        self.processes.add(child)
        self.ready.add(child)
        finished.addCallback(dieGently, child
               ).addErrback(lambda reason: restart(child, reason))
        self._finishCallbacks[child] = finished
        self._lastUsage[child] = now()
        self._calls[child] = 0
        self._catchUp()

    def _catchUp(self):
        """
        If there are queued items in the list then run them.
        """
        if self._queue:
            _, (d, command, kwargs) = pop(self._queue)
            self._cb_doWork(command, **kwargs).chainDeferred(d)

    def _handleTimeout(self, child):
        """
        One of the children went timeout, we need to deal with it

        @param child: The child process
        @type child: L{child.AMPChild}
        """
        try:
            child.transport.signalProcess(self.timeout_signal)
        except error.ProcessExitedAlready:
            # don't do anything then... we are too late
            # or we were too early to call
            pass

    def startAWorker(self):
        """
        Start a worker and set it up in the system.
        """
        if self.finished:
            # this is a race condition: basically if we call self.stop()
            # while a process is being recycled what happens is that the
            # process will be created anyway. By putting a check for
            # self.finished here we make sure that in no way we are creating
            # processes when the pool is stopped.
            # The race condition comes from the fact that:
            # stopAWorker() is asynchronous while stop() is synchronous.
            # so if you call:
            # pp.stopAWorker(child).addCallback(lambda _: pp.startAWorker())
            # pp.stop()
            # You might end up with a dirty reactor due to the stop()
            # returning before the new process is created.
            return
        startAMPProcess = self.starter.startAMPProcess
        child, finished = startAMPProcess(self.ampChild,
                                          ampParent=self.ampParent,
                                          ampChildArgs=self.ampChildArgs)
        return self._addProcess(child, finished)

    def _cb_doWork(self, command, _timeout=None, _deadline=None,
                   **kwargs):
        """
        Go and call the command.

        @param command: The L{amp.Command} to be executed in the child
        @type command: L{amp.Command}

        @param _d: The deferred for the calling code.
        @type _d: L{defer.Deferred}

        @param _timeout: The timeout for this call only
        @type _timeout: C{int}
        @param _deadline: The deadline for this call only
        @type _deadline: C{int}
        """
        timeoutCall = None
        deadlineCall = None

        def _returned(result, child, is_error=False):
            def cancelCall(call):
                if call is not None and call.active():
                    call.cancel()
            cancelCall(timeoutCall)
            cancelCall(deadlineCall)
            self.busy.discard(child)
            if not die:
                # we are not marked to be removed, so add us back to
                # the ready set and let's see if there's some catching
                # up to do
                self.ready.add(child)
                self._catchUp()
            else:
                # We should die and we do, then we start a new worker
                # to pick up stuff from the queue otherwise we end up
                # without workers and the queue will remain there.
                self.stopAWorker(child).addCallback(lambda _: self.startAWorker())
            self._lastUsage[child] = now()
            # we can't do recycling here because it's too late and
            # the process might have received tons of calls already
            # which would make it run more calls than what is
            # configured to do.
            return result

        die = False
        child = self.ready.pop()
        self.busy.add(child)
        self._calls[child] += 1

        # Let's see if this call goes over the recycling barrier
        if self.recycleAfter and self._calls[child] >= self.recycleAfter:
            # it does so mark this child, using a closure, to be
            # removed at the end of the call.
            die = True

        # If the command doesn't require a response then callRemote
        # returns nothing, so we prepare for that too.
        # We also need to guard against timeout errors for child
        # and local timeout parameter overrides the global one
        if _timeout == 0:
            timeout = _timeout
        else:
            timeout = _timeout or self.timeout

        if timeout is not None:
            from twisted.internet import reactor
            timeoutCall = reactor.callLater(timeout, self._handleTimeout, child)

        if _deadline is not None:
            from twisted.internet import reactor
            delay = max(0, _deadline - reactor.seconds())
            deadlineCall = reactor.callLater(delay, self._handleTimeout,
                                             child)

        return defer.maybeDeferred(child.callRemote, command, **kwargs
            ).addCallback(_returned, child
            ).addErrback(_returned, child, is_error=True)

    def callRemote(self, *args, **kwargs):
        """
        Proxy call to keep the API homogeneous across twisted's RPCs
        """
        return self.doWork(*args, **kwargs)

    def doWork(self, command, **kwargs):
        """
        Sends the command to one child.

        @param command: an L{amp.Command} type object.
        @type command: L{amp.Command}

        @param kwargs: dictionary containing the arguments for the command.
        """
        if self.ready: # there are unused processes, let's use them
            return self._cb_doWork(command, **kwargs)
        else:
            if len(self.processes) < self.max:
                # no unused but we can start some new ones
                # since startAWorker is synchronous we won't have a
                # race condition here in case of multiple calls to
                # doWork, so we will end up in the else clause in case
                # of such calls:
                # Process pool with min=1, max=1, recycle_after=1
                # [call(Command) for x in xrange(BIG_NUMBER)]
                self.startAWorker()
                return self._cb_doWork(command, **kwargs)
            else:
                # No one is free... just queue up and wait for a process
                # to start and pick up the first item in the queue.
                d = defer.Deferred()
                self._queue.append((count(), (d, command, kwargs)))
                return d

    def stopAWorker(self, child=None):
        """
        Gently stop a child so that it's not restarted anymore

        @param command: an L{ampoule.child.AmpChild} type object.
        @type command: L{ampoule.child.AmpChild} or None

        """
        if child is None:
            if self.ready:
                child = self.ready.pop()
            else:
                child = choice(list(self.processes))
        child.callRemote(commands.Shutdown
            # This is needed for timeout handling, the reason is pretty hard
            # to explain but I'll try to:
            # There's another small race condition in the system. If the
            # child process is shut down by a signal and you try to stop
            # the process pool immediately afterwards, like tests would do,
            # the child AMP object would still be in the system and trying
            # to call the command Shutdown on it would result in the same
            # errback that we got originally, for this reason we need to
            # trap it now so that it doesn't raise by not being handled.
            # Does this even make sense to you?
            ).addErrback(lambda reason: reason.trap(error.ProcessTerminated))
        return self._finishCallbacks[child]

    def _startSomeWorkers(self):
        """
        Start a bunch of workers until we reach the max number of them.
        """
        if len(self.processes) < self.max:
            self.startAWorker()

    def adjustPoolSize(self, min=None, max=None):
        """
        Change the pool size to be at least min and less than max,
        useful when you change the values of max and min in the instance
        and you want the pool to adapt to them.
        """
        if min is None:
            min = self.min
        if max is None:
            max = self.max

        assert min >= 0, 'minimum is negative'
        assert min <= max, 'minimum is greater than maximum'

        self.min = min
        self.max = max

        l = []
        if self.started:

            for i in xrange(len(self.processes)-self.max):
                l.append(self.stopAWorker())
            while len(self.processes) < self.min:
                self.startAWorker()

        return defer.DeferredList(l)#.addCallback(lambda _: self.dumpStats())

    def stop(self):
        """
        Stops the process protocol.
        """
        self.finished = True
        l = [self.stopAWorker(process) for process in self.processes]
        def _cb(_):
            if self.looping.running:
                self.looping.stop()

        return defer.DeferredList(l).addCallback(_cb)

    def dumpStats(self):
        log.msg("ProcessPool stats:")
        log.msg('\tworkers: %s' % len(self.processes))
        log.msg('\ttimeout: %s' % (self.timeout))
        log.msg('\tparent: %r' % (self.ampParent,))
        log.msg('\tchild: %r' % (self.ampChild,))
        log.msg('\tmax idle: %r' % (self.maxIdle,))
        log.msg('\trecycle after: %r' % (self.recycleAfter,))
        log.msg('\tProcessStarter:')
        log.msg('\t\t%r' % (self.starter,))

pp = None

def deferToAMPProcess(command, **kwargs):
    """
    Helper function that sends a command to the default process pool
    and returns a deferred that fires when the result of the
    subprocess computation is ready.

    @param command: an L{amp.Command} subclass
    @param kwargs: dictionary containing the arguments for the command.

    @return: a L{defer.Deferred} with the data from the subprocess.
    """
    global pp
    if pp is None:
        pp = ProcessPool()
        return pp.start().addCallback(lambda _: pp.doWork(command, **kwargs))
    return pp.doWork(command, **kwargs)
