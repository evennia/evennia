"""
Locks

A lock defines access to a particular subsystem or property of
Evennia. For example, the "owner" property can be impmemented as a
lock. Or the disability to lift an object or to ban users.

A lock consists of three parts:

 - access_type - this defines what kind of access this lock regulates. This
   just a string.
 - function call - this is one or many calls to functions that will determine
   if the lock is passed or not.
 - lock function(s). These are regular python functions with a special
   set of allowed arguments. They should always return a boolean depending
   on if they allow access or not.

# Lock function

A lock function is defined by existing in one of the modules
listed by settings.LOCK_FUNC_MODULES. It should also always
take four arguments looking like this:

   funcname(accessing_obj, accessed_obj, *args, **kwargs):
        [...]

The accessing object is the object wanting to gain access.
The accessed object is the object this lock resides on
args and kwargs will hold optional arguments and/or keyword arguments
to the function as a list and a dictionary respectively.

Example:

   perm(accessing_obj, accessed_obj, *args, **kwargs):
       "Checking if the object has a particular, desired permission"
       if args:
           desired_perm = args[0]
           return desired_perm in accessing_obj.permissions
       return False

Lock functions should most often be pretty general and ideally possible to
re-use and combine in various ways to build clever locks.


# Lock definition ("Lock string")

A lock definition is a string with a special syntax. It is added to
each object's lockhandler, making that lock available from then on.

The lock definition looks like this:

 'access_type:[NOT] func1(args)[ AND|OR][NOT] func2() ...'

That is, the access_type, a colon followed by calls to lock functions
combined with AND or OR. NOT negates the result of the following call.

Example:

 We want to limit who may edit a particular object (let's call this access_type
for 'edit', it depends on what the command is looking for). We want this to
only work for those with the Permission 'Builders'. So we use our lock
function above and define it like this:

  'edit:perm(Builders)'

Here, the lock-function perm() will be called with the string
'Builders' (accessing_obj and accessed_obj are added automatically,
you only need to add the args/kwargs, if any).

If we wanted to make sure the accessing object was BOTH a Builders and a GoodGuy, we
could use AND:

  'edit:perm(Builders) AND perm(GoodGuy)'

To allow EITHER Builders and GoodGuys, we replace AND with OR. perm() is just one example,
the lock function can do anything and compare any properties of the calling object to
decide if the lock is passed or not.

  'lift:attrib(very_strong) AND NOT attrib(bad_back)'

To make these work, add the string to the lockhandler of the object you want
to apply the lock to:

  obj.lockhandler.add('edit:perm(Builders)')

From then on, a command that wants to check for 'edit' access on this
object would do something like this:

  if not target_obj.lockhandler.has_perm(caller, 'edit'):
      caller.msg("Sorry, you cannot edit that.")

All objects also has a shortcut called 'access' that is recommended to use instead:

  if not target_obj.access(caller, 'edit'):
      caller.msg("Sorry, you cannot edit that.")

# Permissions

Permissions are just text strings stored in a comma-separated list on
typeclassed objects. The default perm() lock function uses them,
taking into account settings.PERMISSION_HIERARCHY. Also, the
restricted @perm command sets them, but otherwise they are identical
to any other identifier you can use.

"""

import re, inspect
from django.conf import settings
from src.utils import logger, utils
from django.utils.translation import ugettext as _

__all__ = ("LockHandler", "LockException")

#
# Exception class
#

class LockException(Exception):
    "raised during an error in a lock."
    pass

#
# Cached lock functions
#

_LOCKFUNCS = {}
def _cache_lockfuncs():
    "Updates the cache."
    global _LOCKFUNCS
    _LOCKFUNCS = {}
    for modulepath in settings.LOCK_FUNC_MODULES:
        modulepath = utils.pypath_to_realpath(modulepath)
        mod = utils.mod_import(modulepath)
        if mod:
            for tup in (tup for tup in inspect.getmembers(mod) if callable(tup[1])):
                _LOCKFUNCS[tup[0]] = tup[1]
        else:
            logger.log_errmsg("Couldn't load %s from PERMISSION_FUNC_MODULES." % modulepath)

#
# pre-compiled regular expressions
#

_RE_FUNCS = re.compile(r"\w+\([^)]*\)")
_RE_SEPS = re.compile(r"(?<=[ )])AND(?=\s)|(?<=[ )])OR(?=\s)|(?<=[ )])NOT(?=\s)")
_RE_OK = re.compile(r"%s|and|or|not")


#
#
# Lock handler
#
#

class LockHandler(object):
    """
    This handler should be attached to all objects implementing
    permission checks, under the property 'lockhandler'.
    """

    def __init__(self, obj):
        """
        Loads and pre-caches all relevant locks and their
        functions.
        """
        if not _LOCKFUNCS:
            _cache_lockfuncs()
        self.obj = obj
        self.locks = {}
        self.log_obj = None
        self.reset_flag = False
        self._cache_locks(self.obj.lock_storage)
        # we handle bypass checks already here for efficiency. We need to grant access to superusers and
        # to protocol instances where the superuser status cannot be determined (can happen at
        # some rare cases during login).
        self.lock_bypass = ((hasattr(obj, "is_superuser") and obj.is_superuser)
                            or (hasattr(obj, "player") and hasattr(obj.player, "is_superuser") and obj.player.is_superuser)
                            or (hasattr(obj, "get_player") and (not obj.get_player() or obj.get_player().is_superuser)))
    def __str__(self):
        return ";".join(self.locks[key][2] for key in sorted(self.locks))

    def _log_error(self, message):
        "Try to log errors back to object"
        if self.log_obj and hasattr(self.log_obj, 'msg'):
            self.log_obj.msg(message)
        elif hasattr(self.obj, 'msg'):
            self.obj.msg(message)
        else:
            logger.log_errmsg("%s: %s" % (self.obj, message))

    def _parse_lockstring(self, storage_lockstring):
        """
        Helper function. This is normally only called when the
        lockstring is cached and does preliminary checking.  locks are
        stored as a string 'atype:[NOT] lock()[[ AND|OR [NOT] lock()[...]];atype...

        """
        locks = {}
        if not storage_lockstring:
            return locks
        duplicates = 0
        elist = [] # errors
        wlist = [] # warnings
        for raw_lockstring in storage_lockstring.split(';'):
            lock_funcs = []
            try:
                access_type, rhs = (part.strip() for part in raw_lockstring.split(':', 1))
            except ValueError:
                logger.log_trace()
                return locks

            # parse the lock functions and separators
            funclist = _RE_FUNCS.findall(rhs)
            evalstring = rhs
            for pattern in ('AND', 'OR', 'NOT'):
                evalstring = re.sub(r"\b%s\b" % pattern, pattern.lower(), evalstring)
            nfuncs = len(funclist)
            for funcstring in funclist:
                funcname, rest = (part.strip().strip(')') for part in funcstring.split('(', 1))
                func = _LOCKFUNCS.get(funcname, None)
                if not callable(func):
                    elist.append(_("Lock: function '%s' is not available.") % funcstring)
                    continue
                args = list(arg.strip() for arg in rest.split(',') if arg and not '=' in arg)
                kwargs = dict([arg.split('=', 1) for arg in rest.split(',') if arg and '=' in arg])
                lock_funcs.append((func, args, kwargs))
                evalstring = evalstring.replace(funcstring, '%s')
            if len(lock_funcs) < nfuncs:
                continue
            try:
                # purge the eval string of any superfluous items, then test it
                evalstring = " ".join(_RE_OK.findall(evalstring))
                eval(evalstring % tuple(True for func in funclist), {}, {})
            except Exception:
                elist.append(_("Lock: definition '%s' has syntax errors.") % raw_lockstring)
                continue
            if access_type in locks:
                duplicates += 1
                wlist.append(_("Lock: access type '%(access_type)s' changed from '%(source)s' to '%(goal)s' " % \
                                 {"access_type":access_type, "source":locks[access_type][2], "goal":raw_lockstring}))
            locks[access_type] = (evalstring, tuple(lock_funcs), raw_lockstring)
        if wlist and self.log_obj:
            # a warning text was set, it's not an error, so only report if log_obj is available.
            self._log_error("\n".join(wlist))
        if elist:
            # an error text was set, raise exception.
            raise LockException("\n".join(elist))
        # return the gathered locks in an easily executable form
        return locks

    def _cache_locks(self, storage_lockstring):
        """Store data"""
        self.locks = self._parse_lockstring(storage_lockstring)

    def _save_locks(self):
        "Store locks to obj"
        self.obj.lock_storage = ";".join([tup[2] for tup in self.locks.values()])

    def add(self, lockstring, log_obj=None):
        """
        Add a new lockstring on the form '<access_type>:<functions>'. Multiple
        access types should be separated by semicolon (;).

        If log_obj is given, it will be fed error information.
        """
        if log_obj:
            self.log_obj = log_obj
        # sanity checks
        for lockdef in lockstring.split(';'):
            if not ':' in lockstring:
                self._log_error(_("Lock: '%s' contains no colon (:).") % lockdef)
                return False
            access_type, rhs = [part.strip() for part in lockdef.split(':', 1)]
            if not access_type:
                self._log_error(_("Lock: '%s' has no access_type (left-side of colon is empty).") % lockdef)
                return False
            if rhs.count('(') != rhs.count(')'):
                self._log_error(_("Lock: '%s' has mismatched parentheses.") % lockdef)
                return False
            if not _RE_FUNCS.findall(rhs):
                self._log_error(_("Lock: '%s' has no valid lock functions.") % lockdef)
                return False
        # get the lock string
        storage_lockstring = self.obj.lock_storage
        if storage_lockstring:
            storage_lockstring = storage_lockstring + ";" + lockstring
        else:
            storage_lockstring = lockstring
        # cache the locks will get rid of eventual doublets
        self._cache_locks(storage_lockstring)
        self._save_locks()
        self.log_obj = None
        return True

    def replace(self, lockstring, log_obj=None):
        "Replaces the lockstring entirely."
        old_lockstring = str(self)
        self.clear()
        try:
            return self.add(lockstring, log_obj)
        except LockException:
            self.add(old_lockstring, log_obj)
            raise

    def get(self, access_type=None):
        "get the full lockstring or the lockstring of a particular access type."
        if access_type:
            return self.locks.get(access_type, ["","",""])[2]
        return str(self)

    def delete(self, access_type):
        "Remove a lock from the handler"
        if access_type in self.locks:
            del self.locks[access_type]
            self._save_locks()
            return True
        return False

    def clear(self):
        "Remove all locks"
        self.locks = {}
        self.lock_storage = ""

    def reset(self):
        """
        Set the reset flag, so the the lock will be re-cached at next checking.
        This is usually set by @reload.
        """
        self.reset_flag = True

    def check(self, accessing_obj, access_type, default=False, no_superuser_bypass=False):
        """
        Checks a lock of the correct type by passing execution
        off to the lock function(s).

        accessing_obj - the object seeking access
        access_type - the type of access wanted
        default - if no suitable lock type is found, use this
        no_superuser_bypass - don't use this unless you really, really need to,
                              it makes supersusers susceptible to the lock check.

        A lock is executed in the follwoing way:

        Parsing the lockstring, we (during cache) extract the valid
        lock functions and store their function objects in the right
        order along with their args/kwargs. These are now executed in
        sequence, creating a list of True/False values. This is put
        into the evalstring, which is a string of AND/OR/NOT entries
        separated by placeholders where each function result should
        go. We just put those results in and evaluate the string to
        get a final, combined True/False value for the lockstring.

        The important bit with this solution is that the full
        lockstring is never blindly evaluated, and thus there (should
        be) no way to sneak in malign code in it. Only "safe" lock
        functions (as defined by your settings) are executed.

        """
        if self.reset_flag:
            # on-demand cache rebuild
            self._cache_locks(self.obj.lock_storage)
            self.reset_flag = False

        try:
            # check if the lock should be bypassed (e.g. superuser status)
            if accessing_obj.locks.lock_bypass and not no_superuser_bypass:
                return True
        except AttributeError:
            # happens before session is initiated.
            if not no_superuser_bypass and ((hasattr(accessing_obj, 'is_superuser') and accessing_obj.is_superuser)
             or (hasattr(accessing_obj, 'player') and hasattr(accessing_obj.player, 'is_superuser') and accessing_obj.player.is_superuser)
             or (hasattr(accessing_obj, 'get_player') and (not accessing_obj.get_player() or accessing_obj.get_player().is_superuser))):
                return True

        # no superuser or bypass -> normal lock operation
        if access_type in self.locks:
            # we have a lock, test it.
            evalstring, func_tup, raw_string = self.locks[access_type]
            # execute all lock funcs in the correct order, producing a tuple of True/False results.
            true_false = tuple(bool(tup[0](accessing_obj, self.obj, *tup[1], **tup[2])) for tup in func_tup)
            # the True/False tuple goes into evalstring, which combines them
            # with AND/OR/NOT in order to get the final result.
            return eval(evalstring % true_false)
        else:
            return default

    def check_lockstring(self, accessing_obj, lockstring, no_superuser_bypass=False):
        """
        Do a direct check against a lockstring ('atype:func()..'), without any
        intermediary storage on the accessed object (this can be left
        to None if the lock functions called don't access it). atype can also be
        put to a dummy value since no lock selection is made.
        """
        try:
            if accessing_obj.locks.lock_bypass and not no_superuser_bypass:
                return True
        except AttributeError:
            if no_superuser_bypass and ((hasattr(accessing_obj, 'is_superuser') and accessing_obj.is_superuser)
             or (hasattr(accessing_obj, 'player') and hasattr(accessing_obj.player, 'is_superuser') and accessing_obj.player.is_superuser)
             or (hasattr(accessing_obj, 'get_player') and (not accessing_obj.get_player() or accessing_obj.get_player().is_superuser))):
                return True

        locks = self._parse_lockstring(lockstring)
        for access_type in locks:
            evalstring, func_tup, raw_string = locks[access_type]
            true_false = tuple(tup[0](accessing_obj, self.obj, *tup[1], **tup[2]) for tup in func_tup)
            return eval(evalstring % true_false)

def _test():
    # testing

    class TestObj(object):
        pass

    import pdb
    obj1 = TestObj()
    obj2 = TestObj()

    #obj1.lock_storage = "owner:dbref(#4);edit:dbref(#5) or perm(Wizards);examine:perm(Builders);delete:perm(Wizards);get:all()"
    #obj1.lock_storage = "cmd:all();admin:id(1);listen:all();send:all()"
    obj1.lock_storage = "listen:perm(Immortals)"

    pdb.set_trace()
    obj1.locks = LockHandler(obj1)
    obj2.permissions = ["Immortals"]
    obj2.id = 4

    #obj1.locks.add("edit:attr(test)")

    print "comparing obj2.permissions (%s) vs obj1.locks (%s)" % (obj2.permissions, obj1.locks)
    print obj1.locks.check(obj2, 'owner')
    print obj1.locks.check(obj2, 'edit')
    print obj1.locks.check(obj2, 'examine')
    print obj1.locks.check(obj2, 'delete')
    print obj1.locks.check(obj2, 'get')
    print obj1.locks.check(obj2, 'listen')
