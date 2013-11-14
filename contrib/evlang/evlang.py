"""

EVLANG

A mini-language for online coding of Evennia

Evennia contribution - Griatch 2012

WARNING:
 Restricted python execution is a tricky art, and this module -is-
 partly based on blacklisting techniques, which might be vulnerable to
 new venues of attack opening up in the future (or existing ones we've
 missed). Whereas I/we know of no obvious exploits to this, it is no
 guarantee. If you are paranoid about security, consider also using
 secondary defences on the OS level such as a jail and highly
 restricted execution abilities for the twisted process. So in short,
 this should work fine, but use it at your own risk. You have been
 warned.

This module offers a highly restricted execution environment for users
to script objects in an almost-Python language. It's not really a true
sandbox but based on a very stunted version of Python. This not only
restricts obvious things like import statements and other builins, but
also pre-parses the AST tree to completely kill whole families of
functionality. The result is a subset of Python that -should- keep an
untrusted, malicious user from doing bad things to the server.

An important limitation with this this implementation is a lack of a
timeout check - inside Twisted (and in Python in general) it's very
hard to safely kill a thread with arbitrary code once it's running. So
instead we restrict the most common DOS-attack vectors, such as while
loops, huge power-law assignments as well as function definitions. A
better way would probably be to spawn the runner into a separate
process but that stunts much of the work a user might want to do with
objects (since the current in-memory state of an object has potential
importance in Evennia). If you want to try the subprocess route, you
might want to look into hacking the Evlang handler (below) onto code
from the pysandbox project (https://github.com/haypo/pysandbox). Note
however, that one would probably need to rewrite that to use Twisted's
non-blocking subprocess mechanisms instead.


The module holds the "Evlang" handler, which is intended to be the
entry point for adding scripting support anywhere in Evennia.

By default the execution environment makes the following objects
available (some or all of these may be None depending on how the
code was launched):
  caller - a reference to the object triggering the code
  scripter - the original creator of the code
  self - the object on which the code is defined
  here - shortcut to self.location, if applicable

There is finally a variable "evl" which is a holder object for safe
functions to execute. This object is initiated with the objects above,
to make sure the user does not try to forge the input arguments. See
below the default safe methods defined on it.

You can add new safe symbols to the execution context by adding
EVLANG_SAFE_CONTEXT to your settings file. This should be a dictionary
with {"name":object} pairs.

You can also add new safe methods to the evl object. You add them as a
dictionary on the same form to settings.EVLANG_SAFE_METHODS.  Remember
that such meethods must be defined properly to be a class method
(notably "self" must be be the first argument on the argument list).

You can finally define settings.EVLANG_UNALLOWED_SYMBOLS as a list of
python symbol names you specifically want to lock. This will lock both
functions of that name as well as trying to access attributes on
objects with that name (note that these "attributes" have nothing to
do with Evennia's in-database "Attribute" system!).

"""

import sys, os, time
import __builtin__
import inspect, ast, _ast
from twisted.internet import reactor, threads, task
from twisted.internet.defer import inlineCallbacks

# set up django, if necessary
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from game import settings
try:
    from django.conf import settings as settings2
    settings2.configure()
except RuntimeError:
    pass
finally:
    del settings2

_LOGGER = None

#------------------------------------------------------------
# Evennia-specific blocks
#------------------------------------------------------------

# specifically forbidden symbols
_EV_UNALLOWED_SYMBOLS = ["attr", "attributes", "delete"]
try:
    _EV_UNALLOWED_SYMBOLS.expand(settings.EVLANG_UNALLOWED_SYMBOLS)
except AttributeError:
    pass

# safe methods (including self in args) to make available on
# the evl object
_EV_SAFE_METHODS = {}
try:
    _EV_SAFE_METHODS.update(settings.EVLANG_SAFE_METHODS)
except AttributeError:
    pass

# symbols to make available directly in code
_EV_SAFE_CONTEXT = {"testvar": "This is a safe var!"}
try:
    _EV_SAFE_CONTEXT.update(settings.EVLANG_SAFE_CONTEXT)
except AttributeError:
    pass


#------------------------------------------------------------
# Holder object for "safe" function access
#------------------------------------------------------------

class Evl(object):
    """
    This is a wrapper object for storing safe functions
    in a secure way, while offering a few properties for
    them to access. This will be made available as the
    "evl" property in code.
    """

    def __init__(self, obj=None, caller=None, scripter=None, **kwargs):
        "Populate the object with safe properties"
        self.obj = obj
        self.caller = caller
        self.scripter = scripter
        self.locatiton = None
        if obj and hasattr(obj, "location"):
            self.location = obj.location
        for key, val in _EV_SAFE_METHODS.items():
            setattr(self.__class__, name, val)
        for key, val in kwargs.items():
            setattr(self.__class__, name, val)

    def list(self):
        """
         list()

         returns a string listing all methods on the evl object, including doc strings."
        """
        # must do it this way since __dict__ is restricted
        members = [mtup for mtup in inspect.getmembers(Evl, predicate=inspect.ismethod)
                                        if not mtup[0].startswith("_")]
        string = "\n".join(["{w%s{n\n %s" % (mtup[0], mtup[1].func_doc.strip())
                                                        for mtup in members])
        return string

    def msg(self, string, obj=None):
        """
         msg(string, obj=None)

         Sends message to obj or to caller if obj is not defined..
        """
        if not obj:
            obj = self.caller
        obj.msg(string)
        return True

    def msg_contents(self, string, obj=None):
        """
         msg_contents(string, obj=None):

         Sends message to the contents of obj, or to content of self if obj is not defined.
        """
        if not obj:
            obj = self.obj
        obj.msg_contents(string, exclude=[obj])
        return True

    def msg_here(self, string, obj=None):
        """
         msg_here(string, obj=None)

         Sends to contents of obj.location, or to self.location if obj is not defined.
        """
        if obj and hasattr(obj, "location"):
            here = obj.location
        else:
            here = self.location
        if here:
            here.msg_contents(string)

    def delay(self, seconds, function, *args, **kwargs):
        """
         delay(seconds, function, *args, **kwargs):

         Delay execution of function(*args, **kwargs) for up to 120 seconds.

         Error messages are relayed to caller unless a specific keyword
         'errobj' is supplied pointing to another object to receiver errors.
        """
        # handle the special error-reporting object
        errobj = self.caller
        if "errobj" in kwargs:
            errobj = kwargs["errobj"]
            del kwargs["errobj"]
        # set up some callbacks for delayed execution

        def errback(f, errobj):
            "error callback"
            if errobj:
                try:
                    f = f.getErrorMessage()
                except:
                    pass
                errobj.msg("EVLANG delay error: " + str(f))

        def runfunc(func, *args, **kwargs):
            "threaded callback"
            threads.deferToThread(func, *args, **kwargs).addErrback(errback, errobj)
        # get things going
        if seconds <= 120:
            task.deferLater(reactor, seconds, runfunc, function, *args, **kwargs).addErrback(errback, errobj)
        else:
            raise EvlangError("delay() can only delay for a maximum of 120 seconds (got %ss)." % seconds)
        return True

    def attr(self, obj, attrname=None, value=None, delete=False):
        """
         attr(obj, attrname=None, value=None, delete=False)

        Access and edit database Attributes on obj. if only obj
        is given, return list of Attributes on obj. If attrname
        is given, return that Attribute's value only. If also
        value is given, set the attribute to that value. The
        delete flag will delete the given attrname from the object.

        Access is checked for all operations. The method will return
        the attribute value or True if the operation was a success,
        None otherwise.
        """
        print obj, hasattr(obj, "secure_attr")
        if hasattr(obj, "secure_attr"):
            return obj.secure_attr(self.caller, attrname, value, delete=False,
                                   default_access_read=True, default_access_edit=False,
                                   default_access_create=True)
        return False


#------------------------------------------------------------
# Evlang class handler
#------------------------------------------------------------

class EvlangError(Exception):
    "Error for evlang handler"
    pass


class Evlang(object):
    """
    This is a handler for launching limited execution Python scripts.

    Normally this handler is stored on an object and will then give
    access to basic operations on the object. It can however also be
    run stand-alone.

    If running on an object, it should normally be initiated in the
    object's at_server_start() method and assigned to a property
    "evlang" (or similar) for easy access. It will then use the object
    for storing a dictionary of available evlang scripts (default name
    of this attribute is "evlang_scripts").

    Note: This handler knows nothing about access control. To get that
    one needs to append a LockHandler as "lockhandler" at creation
    time, as well as arrange for commands to do access checks of
    suitable type. Once methods on this handler are called, access is
    assumed to be granted.

    """
    def __init__(self, obj=None, scripts=None, storage_attr="evlang_scripts",
                 safe_context=None, safe_timeout=2):
        """
        Setup of the Evlang handler.

        Input:
          obj - a reference to the object this handler is defined on. If not
                set, handler will operate stand-alone.
          scripts = dictionary {scriptname, (codestring, callerobj), ...}
                    where callerobj can be Noneevlang_storage_attr - if obj
                    is given, will look for a dictionary
                      {scriptname, (codestring, callerobj)...}
                    stored in this given attribute name on that object.
          safe_funcs - dictionary of {funcname:funcobj, ...} to make available
                       for the execution environment
          safe_timeout - the time we let a script run. If it exceeds this
                         time, it will be blocked from running again.

        """
        self.obj = obj
        self.evlang_scripts = {}
        self.safe_timeout = safe_timeout
        self.evlang_storage_attr = storage_attr
        if scripts:
            self.evlang_scripts.update(scripts)
        if self.obj:
            self.evlang_scripts.update(obj.attributes.get(storage_attr))
        self.safe_context = _EV_SAFE_CONTEXT  # set by default + settings
        if safe_context:
            self.safe_context.update(safe_context)
        self.timedout_codestrings = []

    def msg(self, string, scripter=None, caller=None):
        """
        Try to send string to a receiver. Returns False
        if no receiver was found.
        """
        if scripter:
            scripter.msg(string)
        elif caller:
            caller.msg(string)
        elif self.obj:
            self.obj.msg(string)
        else:
            return False
        return True

    def start_timer(self, timeout, codestring, caller, scripter):
        """
        Start a timer to check how long an execution has lasted.
        Returns a deferred, which should be cancelled when the
        code does finish.
        """
        def alarm(codestring):
            "store the code of too-long-running scripts"
            global _LOGGER
            if not _LOGGER:
                from src.utils import logger as _LOGGER
            self.timedout_codestrings.append(codestring)
            err = "Evlang code '%s' exceeded allowed execution time (>%ss)." % (codestring, timeout)
            _LOGGER.log_errmsg("EVLANG time exceeded: caller: %s, scripter: %s, code: %s" % (caller, scripter, codestring))
            if not self.msg(err, scripter, caller):
                raise EvlangError(err)

        def errback(f):
            "We need an empty errback, to catch the traceback of defer.cancel()"
            pass
        return task.deferLater(reactor, timeout, alarm, codestring).addErrback(errback)

    def stop_timer(self, _, deferred):
        """Callback for stopping a previously started timer.
        Cancels the given deferred.
        """
        deferred.cancel()

    @inlineCallbacks
    def run(self, codestring, caller=None, scripter=None):
        """
        run a given code string.

        codestring - the actual code to execute.
        scripter - the creator of the script. Preferentially sees error messages
        caller - the object triggering the script - sees error messages if
        no scripter is given
        """

        # catching previously detected long-running code
        if codestring in self.timedout_codestrings:
            err = "Code '%s' previously failed with a timeout. Please rewrite code." % codestring
            if not self.msg(err, scripter, caller):
                raise EvlangError(err)
            return

        # dynamically setup context, then overload with custom additions
        location = None
        if self.obj:
           location = self.obj.location
        context = {"self":self.obj,
                   "caller":caller,
                   "scripter": scripter,
                   "here": location,
                   "evl": Evl(self.obj, caller, scripter)}
        context.update(self.safe_context)

        # launch the runner in a separate thread, tracking how long it runs.
        timer = self.start_timer(self.safe_timeout, codestring, scripter, caller)
        try:
            yield threads.deferToThread(limited_exec, codestring, context=context,
                                        timeout_secs=self.safe_timeout).addCallback(self.stop_timer, timer)
        except Exception, e:
            self.stop_timer(None, timer)
            if not self.msg(e, scripter, caller):
                raise e

    def run_by_name(self, scriptname, caller=None, quiet=True):
        """
        Run a script previously stored on the handler, identified by scriptname.

        scriptname - identifier of the stored script
        caller - optional reference to the object triggering the script.
        quiet - will not raise error if scriptname is not found.

        All scripts run will have access to the self, caller and here variables.
        """
        scripter = None
        try:
            codestring, scripter = self.evlang_scripts[scriptname]
        except KeyError:
            if quiet:
                return
            errmsg = "Found no script with the name '%s'." % scriptname
            if not self.msg(errmsg, scripter=None, caller=caller):
                raise EvlangError(errmsg)
            return
        # execute code
        self.run(codestring, caller, scripter)

    def add(self, scriptname, codestring, scripter=None):
        """
        Add a new script to the handler. This will also save the
        script properly. This is used also to update scripts when
        debugging.
        """
        self.evlang_scripts[scriptname] = (codestring, scripter)
        if self.obj:
            # save to database
            self.obj.attributes.add(self.evlang_storage_attr,
                                    self.evlang_scripts)

    def delete(self, scriptname):
        """
        Permanently remove script from object.
        """
        if scriptname in self.evlang_scripts:
            del self.evlang_scripts[scriptname]
        if self.obj:
            # update change to database
            self.obj.attributes.add(self.evlang_storage_attr,
                                    self.evlang_scripts)


#----------------------------------------------------------------------

# Limited Python evaluation.

# Based on PD recipe by Babar K. Zafar
# http://code.activestate.com/recipes/496746/

# Expanded specifically for Evennia by Griatch
# - some renaming/cleanup
# - limited size of power expressions
# - removed print (use msg() instead)
# - blocking certain function calls
# - removed assignment of properties - this is too big of a security risk.
#     One needs to us a safe function to change propertes.
# - removed thread-based check for execution time - it doesn't work
#     embedded in twisted/python.
# - removed while, since it's night impossible to properly check compile
#     time in an embedded Python thread (or rather, it's possible, but
#     there is no way to cancel the thread anyway). while is an easy way
#     to create an infinite loop.
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Module globals.
#----------------------------------------------------------------------

# Toggle module level debugging mode.
DEBUG = False

# List of all AST node classes in _ast.py.
ALL_AST_NODES = \
    set([name for (name, obj) in inspect.getmembers(_ast)
     if inspect.isclass(obj) and issubclass(obj, _ast.AST)])

# List of all builtin functions and types (ignoring exception classes).
ALL_BUILTINS = \
    set([name for (name, obj) in inspect.getmembers(__builtin__)
     if (inspect.isbuiltin(obj) or name in ('True', 'False', 'None') or
        (inspect.isclass(obj) and not issubclass(obj, BaseException)))])

#----------------------------------------------------------------------
# Utilties.
#----------------------------------------------------------------------

def classname(obj):
    return obj.__class__.__name__

def is_valid_ast_node(name):
    return name in ALL_AST_NODES

def is_valid_builtin(name):
    return name in ALL_BUILTINS

def get_node_lineno(node):
    return (node.lineno) and node.lineno or 0


#----------------------------------------------------------------------
# Restricted AST nodes & builtins.
#----------------------------------------------------------------------

# Deny evaluation of code if the AST contain any of the following nodes:
UNALLOWED_AST_NODES = set([
#   'Add', 'And',
#    'AssList',
#    'AssName',
#   'AssTuple',
#   'Assert', 'Assign', 'AugAssign',
#   'Bitand', 'Bitor', 'Bitxor', 'Break',
#   'CallFunc', 'Class', 'Compare', 'Const', 'Continue',
#   'Decorators', 'Dict', 'Discard', 'Div',
#   'Ellipsis', 'EmptyNode',
    'Exec',
#   'Expression', 'FloorDiv',
#   'For',
    'FunctionDef',
#   'GenExpr', 'GenExprFor', 'GenExprIf', 'GenExprInner',
#   'Getattr', 'Global', 'If',
    'Import',
    'ImportFrom',
#   'Invert',
#   'Keyword', 'Lambda', 'LeftShift',
#   'List', 'ListComp', 'ListCompFor', 'ListCompIf', 'Mod',
#   'Module',
#   'Mul', 'Name', 'Node', 'Not', 'Or', 'Pass', 'Power',
    'Print',
    'Raise',
#    'Return', 'RightShift', 'Slice', 'Sliceobj',
#   'Stmt', 'Sub', 'Subscript',
   'TryExcept', 'TryFinally',
#   'Tuple', 'UnaryAdd', 'UnarySub',
   'While',
#   'Yield'
])

# Deny evaluation of code if it tries to access any of the following builtins:
UNALLOWED_BUILTINS = set([
    '__import__',
#   'abs', 'apply', 'basestring', 'bool', 'buffer',
#   'callable', 'chr', 'classmethod', 'cmp', 'coerce',
    'compile',
#   'complex',
    'delattr',
#   'dict',
    'dir',
#   'divmod', 'enumerate',
    'eval', 'execfile', 'file',
#   'filter', 'float', 'frozenset',
    'getattr', 'globals', 'hasattr',
#    'hash', 'hex', 'id',
    'input',
#   'int',
    'intern',
#   'isinstance', 'issubclass', 'iter',
#   'len', 'list',
    'locals',
#   'long', 'map', 'max',
    'memoryview',
#   'min', 'object', 'oct',
    'open',
#   'ord', 'pow', 'property', 'range',
    'raw_input',
#   'reduce',
    'reload',
#   'repr', 'reversed', 'round', 'set',
    'setattr',
#   'slice', 'sorted', 'staticmethod',  'str', 'sum',
    'super',
#   'tuple',
    'type',
#   'unichr', 'unicode',
    'vars',
#    'xrange', 'zip'
])

# extra validation whitelist-style to avoid new versions of Python creeping
# in with new unsafe things
SAFE_BUILTINS = set([
     'False', 'None', 'True', 'abs', 'all', 'any', 'apply', 'basestring',
     'bin', 'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr',
     'classmethod',
     'cmp', 'coerce', 'complex', 'dict', 'divmod', 'enumerate', 'filter',
     'float', 'format', 'frozenset', 'hash', 'hex', 'id', 'int',
     'isinstance', 'issubclass', 'iter', 'len', 'list', 'long', 'map',
     'max', 'min',
     'next', 'object', 'oct', 'ord', 'pow', 'print', 'property', 'range',
     'reduce',
     'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'staticmethod',
     'str',
     'sum', 'tuple', 'unichr', 'unicode', 'xrange', 'zip'])

for ast_name in UNALLOWED_AST_NODES:
    assert(is_valid_ast_node(ast_name))
for name in UNALLOWED_BUILTINS:
    assert(is_valid_builtin(name))


def _cross_match_whitelist():
    "check the whitelist's completeness"
    available = ALL_BUILTINS - UNALLOWED_BUILTINS
    diff = available.difference(SAFE_BUILTINS)
    assert not diff, diff  # check so everything not disallowed is in safe
    diff = SAFE_BUILTINS.difference(available)
    assert not diff, diff  # check so everything in safe is in not-disallowed
_cross_match_whitelist()

def is_unallowed_ast_node(kind):
    return kind in UNALLOWED_AST_NODES

def is_unallowed_builtin(name):
    return name in UNALLOWED_BUILTINS

#----------------------------------------------------------------------
# Restricted attributes.
#----------------------------------------------------------------------

# In addition to these we deny access to all lowlevel attrs (__xxx__).
UNALLOWED_ATTR = [
    'im_class', 'im_func', 'im_self',
    'func_code', 'func_defaults', 'func_globals', 'func_name',
    'tb_frame', 'tb_next',
    'f_back', 'f_builtins', 'f_code', 'f_exc_traceback',
    'f_exc_type', 'f_exc_value', 'f_globals', 'f_locals']
UNALLOWED_ATTR.extend(_EV_UNALLOWED_SYMBOLS)


def is_unallowed_attr(name):
    return (name[:2] == '__' and name[-2:] == '__') or \
           (name in UNALLOWED_ATTR)


#----------------------------------------------------------------------
# LimitedExecVisitor.
#----------------------------------------------------------------------

class LimitedExecError(object):
    """
    Base class for all which occur while walking the AST.

    Attributes:
      errmsg = short decription about the nature of the error
      lineno = line offset to where error occured in source code
    """
    def __init__(self, errmsg, lineno):
        self.errmsg, self.lineno = errmsg, lineno

    def __str__(self):
        return "line %d : %s" % (self.lineno, self.errmsg)


class LimitedExecASTNodeError(LimitedExecError):
    "Expression/statement in AST evaluates to a restricted AST node type."
    pass


class LimitedExecBuiltinError(LimitedExecError):
    "Expression/statement in tried to access a restricted builtin."
    pass


class LimitedExecAttrError(LimitedExecError):
    "Expression/statement in tried to access a restricted attribute."
    pass


class LimitedExecVisitor(object):
    """
    Data-driven visitor which walks the AST for some code and makes
    sure it doesn't contain any expression/statements which are
    declared as restricted in 'UNALLOWED_AST_NODES'. We'll also make
    sure that there aren't any attempts to access/lookup restricted
    builtin declared in 'UNALLOWED_BUILTINS'. By default we also won't
    allow access to lowlevel stuff which can be used to dynamically
    access non-local envrioments.

    Interface:
      walk(ast) = validate AST and return True if AST is 'safe'

    Attributes:
      errors = list of LimitedExecError if walk() returned False

    Implementation:

    The visitor will automatically generate methods for all of the
    available AST node types and redirect them to self.ok or self.fail
    reflecting the configuration in 'UNALLOWED_AST_NODES'. While
    walking the AST we simply forward the validating step to each of
    node callbacks which take care of reporting errors.
    """

    def __init__(self):
        "Initialize visitor by generating callbacks for all AST node types."
        self.errors = []
        for ast_name in ALL_AST_NODES:
            # Don't reset any overridden callbacks.
            if getattr(self, 'visit' + ast_name, None):
                continue
            if is_unallowed_ast_node(ast_name):
                setattr(self, 'visit' + ast_name, self.fail)
            else:
                setattr(self, 'visit' + ast_name, self.ok)

    def walk(self, astnode):
        "Validate each node in AST and return True if AST is 'safe'."
        self.visit(ast)
        return self.errors == []

    def visit(self, node, *args):
        "Recursively validate node and all of its children."
        fn = getattr(self, 'visit' + classname(node))
        if DEBUG:
            self.trace(node)
        fn(node, *args)
        for child in node.getChildNodes():
            self.visit(child, *args)

    def visitName(self, node, *args):
        "Disallow any attempts to access a restricted builtin/attr."
        name = node.getChildren()[0]
        lineno = get_node_lineno(node)
        if is_unallowed_builtin(name):
            self.errors.append(LimitedExecBuiltinError(
                "access to builtin '%s' is denied" % name, lineno))
        elif is_unallowed_attr(name):
            self.errors.append(LimitedExecAttrError(
                "access to attribute '%s' is denied" % name, lineno))

    def visitGetattr(self, node, *args):
        "Disallow any attempts to access a restricted attribute."
        attrname = node.attrname
        try:
            name = node.getChildren()[0].name
        except Exception:
            name = ""
        lineno = get_node_lineno(node)
        if attrname == 'attr' and name == 'evl':
            pass
        elif is_unallowed_attr(attrname):
            self.errors.append(LimitedExecAttrError(
                "access to attribute '%s' is denied" % attrname, lineno))

    def visitAssName(self, node, *args):
        "Disallow attempts to delete an attribute  or name"
        if node.flags == 'OP_DELETE':
            self.fail(node, *args)

    def visitPower(self, node, *args):
        "Make sure power-of operations don't get too big"
        if node.left.value > 1000000 or node.right.value > 10:
            lineno = get_node_lineno(node)
            self.errors.append(LimitedExecAttrError(
              "power law solution too big - restricted", lineno))

    def ok(self, node, *args):
        "Default callback for 'harmless' AST nodes."
        pass

    def fail(self, node, *args):
        "Default callback for unallowed AST nodes."
        lineno = get_node_lineno(node)
        self.errors.append(LimitedExecASTNodeError(
            "execution of '%s' statements is denied" % classname(node),
            lineno))

    def trace(self, node):
        "Debugging utility for tracing the validation of AST nodes."
        print classname(node)
        for attr in dir(node):
            if attr[:2] != '__':
                print ' ' * 4, "%-15.15s" % attr, getattr(node, attr)


#----------------------------------------------------------------------
# Safe 'eval' replacement.
#----------------------------------------------------------------------

class LimitedExecException(Exception):
    "Base class for all safe-eval related errors."
    pass


class LimitedExecCodeException(LimitedExecException):
    """
    Exception class for reporting all errors which occured while
    validating AST for source code in limited_exec().

    Attributes:
      code   = raw source code which failed to validate
      errors = list of LimitedExecError
    """
    def __init__(self, code, errors):
        self.code, self.errors = code, errors
    def __str__(self):
        return '\n'.join([str(err) for err in self.errors])


class LimitedExecContextException(LimitedExecException):
    """
    Exception class for reporting unallowed objects found in the dict
    intended to be used as the local enviroment in safe_eval().

    Attributes:
      keys   = list of keys of the unallowed objects
      errors = list of strings describing the nature of the error
               for each key in 'keys'
    """
    def __init__(self, keys, errors):
        self.keys, self.errors = keys, errors
    def __str__(self):
        return '\n'.join([str(err) for err in self.errors])


class LimitedExecTimeoutException(LimitedExecException):
    """
    Exception class for reporting that code evaluation execeeded
    the given timelimit.

    Attributes:
      timeout = time limit in seconds
    """
    def __init__(self, timeout):
        self.timeout = timeout
    def __str__(self):
        return "Timeout limit execeeded (%s secs) during exec" % self.timeout


def validate_context(context):
    "Checks a supplied context for dangerous content"
    ctx_errkeys, ctx_errors = [], []
    for (key, obj) in context.items():
        if inspect.isbuiltin(obj):
            ctx_errkeys.append(key)
            ctx_errors.append("key '%s' : unallowed builtin %s" % (key, obj))
        if inspect.ismodule(obj):
            ctx_errkeys.append(key)
            ctx_errors.append("key '%s' : unallowed module %s" % (key, obj))

    if ctx_errors:
        raise LimitedExecContextException(ctx_errkeys, ctx_errors)
    return True


def validate_code(codestring):
    "validate a code string"
    # prepare the code tree for checking
    astnode = ast.parse(codestring)
    checker = LimitedExecVisitor()

    # check code tree, then execute in a time-restricted environment
    if not checker.walk(astnode):
        raise LimitedExecCodeException(codestring, checker.errors)
    return True


def limited_exec(code, context = {}, timeout_secs=2, retobj=None, procpool_async=None):
    """
    Validate source code and make sure it contains no unauthorized
    expression/statements as configured via 'UNALLOWED_AST_NODES' and
    'UNALLOWED_BUILTINS'. By default this means that code is not
    allowed import modules or access dangerous builtins like 'open' or
    'eval'.

    code - code to execute. Will be evaluated for safety
    context - if code is deemed safe, code will execute with this environment
    time_out_secs - only used if procpool_async is given. Sets timeout
                    for remote code execution
    retobj - only used if procpool_async is also given. Defines an Object
             (which must define a msg() method), for receiving returns from
             the execution.
    procpool_async - a run_async function alternative to the one in
                     src.utils.utils. This must accept the keywords
                        proc_timeout (will be set to timeout_secs
                        at_return - a callback
                        at_err - an errback
                     If retobj is given, at_return/at_err will be created and
                     set to msg callbacks and errors to that object.
    Tracebacks:
        LimitedExecContextException
        LimitedExecCodeException
    """
    if validate_context(context) and validate_code(code):
        # run code only after validation has completed
        if procpool_async:
            # custom run_async
            if retobj:
                callback = lambda r: retobj.msg(r)
                errback = lambda e: retobj.msg(e)
                procpool_async(code, *context,
                               proc_timeout=timeout_secs,
                               at_return=callback,
                               at_err=errback)
            else:
                procpool_async(code, *context, proc_timeout=timeout_secs)
        else:
            # run in-process
            exec code in context


#----------------------------------------------------------------------
# Basic tests.
#----------------------------------------------------------------------

import unittest

class TestLimitedExec(unittest.TestCase):
    def test_builtin(self):
        # attempt to access a unsafe builtin
        self.assertRaises(LimitedExecException,
            limited_exec, "open('test.txt', 'w')")

    def test_getattr(self):
        # attempt to get arround direct attr access
        self.assertRaises(LimitedExecException,
            limited_exec, "getattr(int, '__abs__')")

    def test_func_globals(self):
        # attempt to access global enviroment where fun was defined
        self.assertRaises(LimitedExecException,
            limited_exec, "def x(): pass; print x.func_globals")

    def test_lowlevel(self):
        # lowlevel tricks to access 'object'
        self.assertRaises(LimitedExecException,
            limited_exec, "().__class__.mro()[1].__subclasses__()")

    def test_timeout_ok(self):
        # attempt to exectute 'slow' code which finishes within timelimit
        def test(): time.sleep(2)
        env = {'test': test}
        limited_exec("test()", env, timeout_secs=5)

    def test_timeout_exceed(self):
        # attempt to exectute code which never teminates
        self.assertRaises(LimitedExecException,
            limited_exec, "while 1: pass")

    def test_invalid_context(self):
        # can't pass an enviroment with modules or builtins
        env = {'f': __builtins__.open, 'g': time}
        self.assertRaises(LimitedExecException,
            limited_exec, "print 1", env)

    def test_callback(self):
        # modify local variable via callback
        self.value = 0
        def test(): self.value = 1
        env = {'test': test}
        limited_exec("test()", env)
        self.assertEqual(self.value, 1)

if __name__ == "__main__":
    unittest.main()

