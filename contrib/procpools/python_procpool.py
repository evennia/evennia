"""
Python ProcPool

Evennia Contribution - Griatch 2012

The ProcPool is used to execute code on a separate process. This allows for
true asynchronous operation. Process communication happens over AMP and is
thus fully asynchronous as far as Evennia is concerned.

The process pool is implemented using a slightly modified version of
the Ampoule package (included).

The python_process pool is a service activated with the instructions
in python_procpool_plugin.py.

To use, import run_async from this module and use instead of the
in-process version found in src.utils.utils. Note that this is a much
more complex function than the default run_async, so make sure to read
the header carefully.

To test it works, make sure to activate the process pool, then try the
following as superuser:

@py from contrib.procpools.python_procpool import run_async;run_async("_return('Wohoo!')", at_return=self.msg, at_err=self.msg)

You can also try to import time and do time.sleep(5) before the
_return statement, to test it really is asynchronous.

"""

from twisted.protocols import amp
from twisted.internet import threads
from contrib.procpools.ampoule.child import AMPChild
from src.utils.utils import to_pickle, from_pickle, clean_object_caches, to_str
from src.utils import logger
from src import PROC_MODIFIED_OBJS

#
# Multiprocess command for communication Server<->Client, relaying
# data for remote Python execution
#

class ExecuteCode(amp.Command):
    """
    Executes python code in the python process,
    returning result when ready.

    source - a compileable Python source code string
    environment - a pickled dictionary of Python
                  data. Each key will become the name
                  of a variable available to the source
                  code. Database objects are stored on
                  the form ((app, modelname), id) allowing
                  the receiver to easily rebuild them on
                  this side.
    errors - an all-encompassing error handler
    response - a string or a pickled string

    """
    arguments = [('source', amp.String()),
                 ('environment', amp.String())]
    errors = [(Exception, 'EXCEPTION')]
    response = [('response', amp.String()),
                ('recached', amp.String())]

#
# Multiprocess AMP client-side factory, for executing remote Python code
#

class PythonProcPoolChild(AMPChild):
    """
    This is describing what happens on the subprocess side.

    This already supports Echo, Shutdown and Ping.

    Methods:
    executecode - a remote code execution environment

    """
    def executecode(self, source, environment):
        """
        Remote code execution

        source - Python code snippet
        environment - pickled dictionary of environment
                      variables. They are stored in
                      two keys "normal" and "objs" where
                      normal holds a dictionary of
                      normally pickled python objects
                      wheras objs points to a dictionary
                      of database represenations ((app,key),id).

        The environment's entries will be made available as
        local variables during the execution. Normal eval
        results will be returned as-is. For more complex
        code snippets (run by exec), the _return function
        is available: All data sent to _return(retval) will
        be returned from this system whenever the system
        finishes. Multiple calls to _return will result in
        a list being return. The return value is pickled
        and thus allows for returning any pickleable data.

        """

        class Ret(object):
            "Helper class for holding returns from exec"
            def __init__(self):
                self.returns = []
            def __call__(self, *args, **kwargs):
                self.returns.extend(list(args))
            def get_returns(self):
                lr = len(self.returns)
                if lr == 0:
                    return ""
                elif lr == 1:
                    return to_pickle(self.returns[0], emptypickle=False) or ""
                else:
                    return to_pickle(self.returns, emptypickle=False) or ""
        _return = Ret()


        available_vars = {'_return':_return}
        if environment:
            # load environment
            try:
                environment = from_pickle(environment)
                available_vars.update(environment)
            except Exception:
                logger.log_trace()
        # try to execute with eval first
        try:
            ret = eval(source, {}, available_vars)
            ret = _return.get_returns() or to_pickle(ret, emptypickle=False) or ""
        except Exception:
            # use exec instead
            exec source in available_vars
            ret = _return.get_returns()
        # get the list of affected objects to recache
        objs = list(set(PROC_MODIFIED_OBJS))
        # we need to include the locations too, to update their content caches
        objs = objs + list(set([o.location for o in objs if hasattr(o, "location") and o.location]))
        #print "objs:", objs
        #print "to_pickle", to_pickle(objs, emptypickle=False, do_pickle=False)
        to_recache = to_pickle(objs, emptypickle=False) or ""
        # empty the list without loosing memory reference
        PROC_MODIFIED_OBJS[:] = []
        return {'response': ret,
                'recached': to_recache}
    ExecuteCode.responder(executecode)


#
# Procpool run_async - Server-side access function for executing code in another process
#

_PPOOL = None
_SESSIONS = None
_PROC_ERR = "A process has ended with a probable error condition: process ended by signal 9."

def run_async(to_execute, *args, **kwargs):
    """
    Runs a function or executes a code snippet asynchronously.

    Inputs:
    to_execute (callable) - if this is a callable, it will
            be executed with *args and non-reserver *kwargs as
            arguments.
            The callable will be executed using ProcPool, or in
            a thread if ProcPool is not available.
    to_execute (string) - this is only available is ProcPool is
            running. If a string, to_execute this will be treated as a code
            snippet to execute asynchronously. *args are then not used
            and non-reserverd *kwargs are used to define the execution
            environment made available to the code.

    reserved kwargs:
        'use_thread' (bool) - this only works with callables (not code).
                     It forces the code to run in a thread instead
                     of using the Process Pool, even if the latter
                     is available. This could be useful if you want
                     to make sure to not get out of sync with the
                     main process (such as accessing in-memory global
                     properties)
        'proc_timeout' (int) - only used if ProcPool is available. Sets a
                     max time for execution. This alters the value set
                     by settings.PROCPOOL_TIMEOUT
        'at_return' -should point to a callable with one argument.
                    It will be called with the return value from
                    to_execute.
        'at_return_kwargs' - this dictionary which be used as keyword
                             arguments to the at_return callback.
        'at_err' - this will be called with a Failure instance if
                       there is an error in to_execute.
        'at_err_kwargs' - this dictionary will be used as keyword
                          arguments to the at_err errback.
        'procpool_name' - the Service name of the procpool to use.
                          Default is PythonProcPool.

    *args   - if to_execute is a callable, these args will be used
              as arguments for that function. If to_execute is a string
              *args are not used.
    *kwargs - if to_execute is a callable, these kwargs will be used
              as keyword arguments in that function. If a string, they
              instead are used to define the executable environment
              that should be available to execute the code in to_execute.

    run_async will either relay the code to a thread or to a processPool
    depending on input and what is available in the system. To activate
    Process pooling, settings.PROCPOOL_ENABLE must be set.

    to_execute in string form should handle all imports needed. kwargs
    can be used to send objects and properties. Such properties will
    be pickled, except Database Objects which will be sent across
    on a special format and re-loaded on the other side.

    To get a return value from your code snippet, Use the _return()
    function: Every call to this function from your snippet will
    append the argument to an internal list of returns. This return value
    (or a list) will be the first argument to the at_return callback.

    Use this function with restrain and only for features/commands
    that you know has no influence on the cause-and-effect order of your
    game (commands given after the async function might be executed before
    it has finished). Accessing the same property from different threads/processes
    can lead to unpredicted behaviour if you are not careful (this is called a
    "race condition").

    Also note that some databases, notably sqlite3, don't support access from
    multiple threads simultaneously, so if you do heavy database access from
    your to_execute under sqlite3 you will probably run very slow or even get
    tracebacks.

    """
    # handle all global imports.
    global _PPOOL, _SESSIONS

    # get the procpool name, if set in kwargs
    procpool_name = kwargs.get("procpool_name", "PythonProcPool")

    if _PPOOL == None:
        # Try to load process Pool
        from src.server.sessionhandler import SESSIONS as _SESSIONS
        try:
            _PPOOL = _SESSIONS.server.services.namedServices.get(procpool_name).pool
        except AttributeError:
            _PPOOL = False

    use_timeout = kwargs.pop("proc_timeout", _PPOOL.timeout)

    # helper converters for callbacks/errbacks
    def convert_return(f):
        def func(ret, *args, **kwargs):
            rval = ret["response"] and from_pickle(ret["response"])
            reca = ret["recached"] and from_pickle(ret["recached"])
            # recache all indicated objects
            [clean_object_caches(obj) for obj in reca]
            if f: return f(rval, *args, **kwargs)
            else: return rval
        return func
    def convert_err(f):
        def func(err, *args, **kwargs):
            err.trap(Exception)
            err = err.getErrorMessage()
            if use_timeout and err == _PROC_ERR:
                err = "Process took longer than %ss and timed out." % use_timeout
            if f:
                return f(err, *args, **kwargs)
            else:
                err = "Error reported from subprocess: '%s'" % err
                logger.log_errmsg(err)
        return func

    # handle special reserved input kwargs
    use_thread = kwargs.pop("use_thread", False)
    callback = convert_return(kwargs.pop("at_return", None))
    errback = convert_err(kwargs.pop("at_err", None))
    callback_kwargs = kwargs.pop("at_return_kwargs", {})
    errback_kwargs = kwargs.pop("at_err_kwargs", {})

    if _PPOOL and not use_thread:
        # process pool is running
        if isinstance(to_execute, basestring):
            # run source code in process pool
            cmdargs = {"_timeout":use_timeout}
            cmdargs["source"] = to_str(to_execute)
            cmdargs["environment"] = to_pickle(kwargs, emptypickle=False) or ""
            # defer to process pool
            deferred = _PPOOL.doWork(ExecuteCode, **cmdargs)
        elif callable(to_execute):
            # execute callable in process
            callname = to_execute.__name__
            cmdargs = {"_timeout":use_timeout}
            cmdargs["source"] = "_return(%s(*args,**kwargs))" % callname
            cmdargs["environment"] = to_pickle({callname:to_execute, "args":args, "kwargs":kwargs})
            deferred = _PPOOL.doWork(ExecuteCode, **cmdargs)
        else:
            raise RuntimeError("'%s' could not be handled by the process pool" % to_execute)
    elif callable(to_execute):
        # no process pool available, fall back to old deferToThread mechanism.
        deferred = threads.deferToThread(to_execute, *args, **kwargs)
    else:
        # no appropriate input for this server setup
        raise RuntimeError("'%s' could not be handled by run_async - no valid input or no process pool." % to_execute)

    # attach callbacks
    if callback:
        deferred.addCallback(callback, **callback_kwargs)
    deferred.addErrback(errback, **errback_kwargs)
