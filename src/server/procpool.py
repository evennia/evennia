"""
ProcPool

This module implements and handles processes running under the AMPoule
pool. The ProcPool can accept data from processes and runs them in a
dynamically changing pool of processes, talking to them over AMP. This
offers full asynchronous operation (Python threading does not work as
well for this).

The ExecuteCode command found here is used by src.utils.utils.run_async()
to launch snippets of code on the process pool. The pool itself is a
service named "Process Pool" and is controlled from src/server/server.py.
It can be customized via settings.PROCPOOL_*

"""

from twisted.protocols import amp
from src.utils.ampoule.child import AMPChild
from src.utils.utils import to_pickle, from_pickle

# handle global setups
_LOGGER = None

# Evennia multiprocess command

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
    response = [('response', amp.String())]


# Evennia multiprocess child process template

class ProcPoolChild(AMPChild):
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
        import ev, utils
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

        available_vars = {'ev':ev,
                          'inherits_from':utils.inherits_from,
                          '_return':_return}
        if environment:
            # load environment
            try:
                environment = from_pickle(environment)
            except Exception:
                global _LOGGER
                if not _LOGGER:
                    from src.utils.logger import logger as _LOGGER
                _LOGGER.log_trace("Could not find remote object")
            available_vars.update(environment)
        try:
            ret = eval(source, {}, available_vars)
            if ret != None:
                return {'response':to_pickle(ret, emptypickle=False) or ""}
        except Exception:
            # use exec instead
            exec source in available_vars
        return {'response': _return.get_returns()}
    ExecuteCode.responder(executecode)

