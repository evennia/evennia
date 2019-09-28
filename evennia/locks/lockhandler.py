"""
A *lock* defines access to a particular subsystem or property of
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
           return desired_perm in accessing_obj.permissions.all()
       return False

Lock functions should most often be pretty general and ideally possible to
re-use and combine in various ways to build clever locks.



Lock definition ("Lock string")

A lock definition is a string with a special syntax. It is added to
each object's lockhandler, making that lock available from then on.

The lock definition looks like this:

 'access_type:[NOT] func1(args)[ AND|OR][NOT] func2() ...'

That is, the access_type, a colon followed by calls to lock functions
combined with AND or OR. NOT negates the result of the following call.

Example:

 We want to limit who may edit a particular object (let's call this access_type
for 'edit', it depends on what the command is looking for). We want this to
only work for those with the Permission 'Builder'. So we use our lock
function above and define it like this:

  'edit:perm(Builder)'

Here, the lock-function perm() will be called with the string
'Builder' (accessing_obj and accessed_obj are added automatically,
you only need to add the args/kwargs, if any).

If we wanted to make sure the accessing object was BOTH a Builder and a
GoodGuy, we could use AND:

  'edit:perm(Builder) AND perm(GoodGuy)'

To allow EITHER Builder and GoodGuys, we replace AND with OR. perm() is just
one example, the lock function can do anything and compare any properties of
the calling object to decide if the lock is passed or not.

  'lift:attrib(very_strong) AND NOT attrib(bad_back)'

To make these work, add the string to the lockhandler of the object you want
to apply the lock to:

  obj.lockhandler.add('edit:perm(Builder)')

From then on, a command that wants to check for 'edit' access on this
object would do something like this:

  if not target_obj.lockhandler.has_perm(caller, 'edit'):
      caller.msg("Sorry, you cannot edit that.")

All objects also has a shortcut called 'access' that is recommended to
use instead:

  if not target_obj.access(caller, 'edit'):
      caller.msg("Sorry, you cannot edit that.")


Permissions

Permissions are just text strings stored in a comma-separated list on
typeclassed objects. The default perm() lock function uses them,
taking into account settings.PERMISSION_HIERARCHY. Also, the
restricted @perm command sets them, but otherwise they are identical
to any other identifier you can use.

"""

import re
from django.conf import settings
from evennia.utils import logger, utils
from django.utils.translation import ugettext as _

__all__ = ("LockHandler", "LockException")

WARNING_LOG = settings.LOCKWARNING_LOG_FILE
_LOCK_HANDLER = None


#
# Exception class. This will be raised
# by errors in lock definitions.
#


class LockException(Exception):
    """
    Raised during an error in a lock.
    """

    pass


#
# Cached lock functions
#

_LOCKFUNCS = {}


def _cache_lockfuncs():
    """
    Updates the cache.
    """
    global _LOCKFUNCS
    _LOCKFUNCS = {}
    for modulepath in settings.LOCK_FUNC_MODULES:
        _LOCKFUNCS.update(utils.callables_from_module(modulepath))


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
        Loads and pre-caches all relevant locks and their functions.

        Args:
            obj (object): The object on which the lockhandler is
            defined.

        """
        if not _LOCKFUNCS:
            _cache_lockfuncs()
        self.obj = obj
        self.locks = {}
        try:
            self.reset()
        except LockException as err:
            logger.log_trace(err)

    def __str__(self):
        return ";".join(self.locks[key][2] for key in sorted(self.locks))

    def _log_error(self, message):
        "Try to log errors back to object"
        raise LockException(message)

    def _parse_lockstring(self, storage_lockstring):
        """
        Helper function. This is normally only called when the
        lockstring is cached and does preliminary checking.  locks are
        stored as a string

            atype:[NOT] lock()[[ AND|OR [NOT] lock()[...]];atype...

        Args:
            storage_locksring (str): The lockstring to parse.

        """
        locks = {}
        if not storage_lockstring:
            return locks
        duplicates = 0
        elist = []  # errors
        wlist = []  # warnings
        for raw_lockstring in storage_lockstring.split(";"):
            if not raw_lockstring:
                continue
            lock_funcs = []
            try:
                access_type, rhs = (part.strip() for part in raw_lockstring.split(":", 1))
            except ValueError:
                logger.log_trace()
                return locks

            # parse the lock functions and separators
            funclist = _RE_FUNCS.findall(rhs)
            evalstring = rhs
            for pattern in ("AND", "OR", "NOT"):
                evalstring = re.sub(r"\b%s\b" % pattern, pattern.lower(), evalstring)
            nfuncs = len(funclist)
            for funcstring in funclist:
                funcname, rest = (part.strip().strip(")") for part in funcstring.split("(", 1))
                func = _LOCKFUNCS.get(funcname, None)
                if not callable(func):
                    elist.append(_("Lock: lock-function '%s' is not available.") % funcstring)
                    continue
                args = list(arg.strip() for arg in rest.split(",") if arg and "=" not in arg)
                kwargs = dict([arg.split("=", 1) for arg in rest.split(",") if arg and "=" in arg])
                lock_funcs.append((func, args, kwargs))
                evalstring = evalstring.replace(funcstring, "%s")
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
                wlist.append(
                    _(
                        "LockHandler on %(obj)s: access type '%(access_type)s' changed from '%(source)s' to '%(goal)s' "
                        % {
                            "obj": self.obj,
                            "access_type": access_type,
                            "source": locks[access_type][2],
                            "goal": raw_lockstring,
                        }
                    )
                )
            locks[access_type] = (evalstring, tuple(lock_funcs), raw_lockstring)
        if wlist and WARNING_LOG:
            # a warning text was set, it's not an error, so only report
            logger.log_file("\n".join(wlist), WARNING_LOG)
        if elist:
            # an error text was set, raise exception.
            raise LockException("\n".join(elist))
        # return the gathered locks in an easily executable form
        return locks

    def _cache_locks(self, storage_lockstring):
        """
        Store data
        """
        self.locks = self._parse_lockstring(storage_lockstring)

    def _save_locks(self):
        """
        Store locks to obj
        """
        self.obj.lock_storage = ";".join([tup[2] for tup in self.locks.values()])

    def cache_lock_bypass(self, obj):
        """
        We cache superuser bypass checks here for efficiency. This
        needs to be re-run when an account is assigned to a character.
        We need to grant access to superusers. We need to check both
        directly on the object (accounts), through obj.account and using
        the get_account() method (this sits on serversessions, in some
        rare cases where a check is done before the login process has
        yet been fully finalized)

        Args:
            obj (object): This is checked for the `is_superuser` property.

        """
        self.lock_bypass = hasattr(obj, "is_superuser") and obj.is_superuser

    def add(self, lockstring, validate_only=False):
        """
        Add a new lockstring to handler.

        Args:
            lockstring (str or list): A string on the form
                `"<access_type>:<functions>"`.  Multiple access types
                should be separated by semicolon (`;`). Alternatively,
                a list with lockstrings.
            validate_only (bool, optional): If True, validate the lockstring but
                don't actually store it.
        Returns:
            success (bool): The outcome of the addition, `False` on
                error. If `validate_only` is True, this will be a tuple
                (bool, error), for pass/fail and a string error.

        """
        if isinstance(lockstring, str):
            lockdefs = lockstring.split(";")
        else:
            lockdefs = [lockdef for locks in lockstring for lockdef in locks.split(";")]
            lockstring = ";".join(lockdefs)

        err = ""
        # sanity checks
        for lockdef in lockdefs:
            if ":" not in lockdef:
                err = _("Lock: '{lockdef}' contains no colon (:).").format(lockdef=lockdef)
                if validate_only:
                    return False, err
                else:
                    self._log_error(err)
                    return False
            access_type, rhs = [part.strip() for part in lockdef.split(":", 1)]
            if not access_type:
                err = _(
                    "Lock: '{lockdef}' has no access_type " "(left-side of colon is empty)."
                ).format(lockdef=lockdef)
                if validate_only:
                    return False, err
                else:
                    self._log_error(err)
                    return False
            if rhs.count("(") != rhs.count(")"):
                err = _("Lock: '{lockdef}' has mismatched parentheses.").format(lockdef=lockdef)
                if validate_only:
                    return False, err
                else:
                    self._log_error(err)
                    return False
            if not _RE_FUNCS.findall(rhs):
                err = _("Lock: '{lockdef}' has no valid lock functions.").format(lockdef=lockdef)
                if validate_only:
                    return False, err
                else:
                    self._log_error(err)
                    return False
        if validate_only:
            return True, None
        # get the lock string
        storage_lockstring = self.obj.lock_storage
        if storage_lockstring:
            storage_lockstring = storage_lockstring + ";" + lockstring
        else:
            storage_lockstring = lockstring
        # cache the locks will get rid of eventual doublets
        self._cache_locks(storage_lockstring)
        self._save_locks()
        return True

    def validate(self, lockstring):
        """
        Validate lockstring syntactically, without saving it.

        Args:
            lockstring (str): Lockstring to validate.
        Returns:
            valid (bool): If validation passed or not.

        """
        return self.add(lockstring, validate_only=True)

    def replace(self, lockstring):
        """
        Replaces the lockstring entirely.

        Args:
            lockstring (str): The new lock definition.

        Return:
            success (bool): False if an error occurred.

        Raises:
            LockException: If a critical error occurred.
                If so, the old string is recovered.

        """
        old_lockstring = str(self)
        self.clear()
        try:
            return self.add(lockstring)
        except LockException:
            self.add(old_lockstring)
            raise

    def get(self, access_type=None):
        """
        Get the full lockstring or the lockstring of a particular
        access type.

        Args:
            access_type (str, optional):

        Returns:
            lockstring (str): The matched lockstring, or the full
                lockstring if no access_type was given.
        """

        if access_type:
            return self.locks.get(access_type, ["", "", ""])[2]
        return str(self)

    def all(self):
        """
        Return all lockstrings

        Returns:
            lockstrings (list): All separate lockstrings

        """
        return str(self).split(";")

    def remove(self, access_type):
        """
        Remove a particular lock from the handler

        Args:
            access_type (str): The type of lock to remove.

        Returns:
            success (bool): If the access_type was not found
                in the lock, this returns `False`.

        """
        if access_type in self.locks:
            del self.locks[access_type]
            self._save_locks()
            return True
        return False

    delete = remove  # alias for historical reasons

    def clear(self):
        """
        Remove all locks in the handler.

        """
        self.locks = {}
        self.lock_storage = ""
        self._save_locks()

    def reset(self):
        """
        Set the reset flag, so the the lock will be re-cached at next
        checking.  This is usually called by @reload.

        """
        self._cache_locks(self.obj.lock_storage)
        self.cache_lock_bypass(self.obj)

    def append(self, access_type, lockstring, op="or"):
        """
        Append a lock definition to access_type if it doesn't already exist.

        Args:
            access_type (str): Access type.
            lockstring (str): A valid lockstring, without the operator to
                link it to an eventual existing lockstring.
            op (str): An operator 'and', 'or', 'and not', 'or not' used
                for appending the lockstring to an existing access-type.
        Note:
            The most common use of this method is for use in commands where
            the user can specify their own lockstrings. This method allows
            the system to auto-add things like Admin-override access.

        """
        old_lockstring = self.get(access_type)
        if not lockstring.strip().lower() in old_lockstring.lower():
            lockstring = "{old} {op} {new}".format(
                old=old_lockstring, op=op, new=lockstring.strip()
            )
            self.add(lockstring)

    def check(self, accessing_obj, access_type, default=False, no_superuser_bypass=False):
        """
        Checks a lock of the correct type by passing execution off to
        the lock function(s).

        Args:
            accessing_obj (object): The object seeking access.
            access_type (str): The type of access wanted.
            default (bool, optional): If no suitable lock type is
                found, default to this result.
            no_superuser_bypass (bool): Don't use this unless you
                really, really need to, it makes supersusers susceptible
                to the lock check.

        Notes:
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
        try:
            # check if the lock should be bypassed (e.g. superuser status)
            if accessing_obj.locks.lock_bypass and not no_superuser_bypass:
                return True
        except AttributeError:
            # happens before session is initiated.
            if not no_superuser_bypass and (
                (hasattr(accessing_obj, "is_superuser") and accessing_obj.is_superuser)
                or (
                    hasattr(accessing_obj, "account")
                    and hasattr(accessing_obj.account, "is_superuser")
                    and accessing_obj.account.is_superuser
                )
                or (
                    hasattr(accessing_obj, "get_account")
                    and (
                        not accessing_obj.get_account() or accessing_obj.get_account().is_superuser
                    )
                )
            ):
                return True

        # no superuser or bypass -> normal lock operation
        if access_type in self.locks:
            # we have a lock, test it.
            evalstring, func_tup, raw_string = self.locks[access_type]
            # execute all lock funcs in the correct order, producing a tuple of True/False results.
            true_false = tuple(
                bool(tup[0](accessing_obj, self.obj, *tup[1], **tup[2])) for tup in func_tup
            )
            # the True/False tuple goes into evalstring, which combines them
            # with AND/OR/NOT in order to get the final result.
            return eval(evalstring % true_false)
        else:
            return default

    def _eval_access_type(self, accessing_obj, locks, access_type):
        """
        Helper method for evaluating the access type using eval().

        Args:
            accessing_obj (object): Object seeking access.
            locks (dict): The pre-parsed representation of all access-types.
            access_type (str): An access-type key to evaluate.

        """
        evalstring, func_tup, raw_string = locks[access_type]
        true_false = tuple(tup[0](accessing_obj, self.obj, *tup[1], **tup[2]) for tup in func_tup)
        return eval(evalstring % true_false)

    def check_lockstring(
        self, accessing_obj, lockstring, no_superuser_bypass=False, default=False, access_type=None
    ):
        """
        Do a direct check against a lockstring ('atype:func()..'),
        without any intermediary storage on the accessed object.

        Args:
            accessing_obj (object or None): The object seeking access.
                Importantly, this can be left unset if the lock functions
                don't access it, no updating or storage of locks are made
                against this object in this method.
            lockstring (str): Lock string to check, on the form
                `"access_type:lock_definition"` where the `access_type`
                part can potentially be set to a dummy value to just check
                a lock condition.
            no_superuser_bypass  (bool, optional): Force superusers to heed lock.
            default (bool, optional): Fallback result to use if `access_type` is set
                but no such `access_type` is found in the given `lockstring`.
            access_type (str, bool): If set, only this access_type will be looked up
                among the locks defined by `lockstring`.

        Return:
            access (bool): If check is passed or not.

        """
        try:
            if accessing_obj.locks.lock_bypass and not no_superuser_bypass:
                return True
        except AttributeError:
            if no_superuser_bypass and (
                (hasattr(accessing_obj, "is_superuser") and accessing_obj.is_superuser)
                or (
                    hasattr(accessing_obj, "account")
                    and hasattr(accessing_obj.account, "is_superuser")
                    and accessing_obj.account.is_superuser
                )
                or (
                    hasattr(accessing_obj, "get_account")
                    and (
                        not accessing_obj.get_account() or accessing_obj.get_account().is_superuser
                    )
                )
            ):
                return True
        if ":" not in lockstring:
            lockstring = "%s:%s" % ("_dummy", lockstring)

        locks = self._parse_lockstring(lockstring)

        if access_type:
            if access_type not in locks:
                return default
            else:
                return self._eval_access_type(accessing_obj, locks, access_type)
        else:
            # if no access types was given and multiple locks were
            # embedded in the lockstring we assume all must be true
            return all(
                self._eval_access_type(accessing_obj, locks, access_type) for access_type in locks
            )


# convenience access function

# dummy to be able to call check_lockstring from the outside


class _ObjDummy:
    lock_storage = ""


def check_lockstring(
    accessing_obj, lockstring, no_superuser_bypass=False, default=False, access_type=None
):
    """
    Do a direct check against a lockstring ('atype:func()..'),
    without any intermediary storage on the accessed object.

    Args:
        accessing_obj (object or None): The object seeking access.
            Importantly, this can be left unset if the lock functions
            don't access it, no updating or storage of locks are made
            against this object in this method.
        lockstring (str): Lock string to check, on the form
            `"access_type:lock_definition"` where the `access_type`
            part can potentially be set to a dummy value to just check
            a lock condition.
        no_superuser_bypass  (bool, optional): Force superusers to heed lock.
        default (bool, optional): Fallback result to use if `access_type` is set
            but no such `access_type` is found in the given `lockstring`.
        access_type (str, bool): If set, only this access_type will be looked up
            among the locks defined by `lockstring`.

    Return:
        access (bool): If check is passed or not.

    """
    global _LOCK_HANDLER
    if not _LOCK_HANDLER:
        _LOCK_HANDLER = LockHandler(_ObjDummy())
    return _LOCK_HANDLER.check_lockstring(
        accessing_obj,
        lockstring,
        no_superuser_bypass=no_superuser_bypass,
        default=default,
        access_type=access_type,
    )


def validate_lockstring(lockstring):
    """
    Validate so lockstring is on a valid form.

    Args:
        lockstring (str): Lockstring to validate.

    Returns:
        is_valid (bool): If the lockstring is valid or not.
        error (str or None): A string describing the error, or None
            if no error was found.

    """
    global _LOCK_HANDLER
    if not _LOCK_HANDLER:
        _LOCK_HANDLER = LockHandler(_ObjDummy())
    return _LOCK_HANDLER.validate(lockstring)


def get_all_lockfuncs():
    """
    Get a dict of available lock funcs.

    Returns:
        lockfuncs (dict): Mapping {lockfuncname:func}.

    """
    if not _LOCKFUNCS:
        _cache_lockfuncs()
    return _LOCKFUNCS


def _test():
    # testing

    class TestObj(object):
        pass

    import pdb

    obj1 = TestObj()
    obj2 = TestObj()

    # obj1.lock_storage = "owner:dbref(#4);edit:dbref(#5) or perm(Admin);examine:perm(Builder);delete:perm(Admin);get:all()"
    # obj1.lock_storage = "cmd:all();admin:id(1);listen:all();send:all()"
    obj1.lock_storage = "listen:perm(Developer)"

    pdb.set_trace()
    obj1.locks = LockHandler(obj1)
    obj2.permissions.add("Developer")
    obj2.id = 4

    # obj1.locks.add("edit:attr(test)")

    print("comparing obj2.permissions (%s) vs obj1.locks (%s)" % (obj2.permissions, obj1.locks))
    print(obj1.locks.check(obj2, "owner"))
    print(obj1.locks.check(obj2, "edit"))
    print(obj1.locks.check(obj2, "examine"))
    print(obj1.locks.check(obj2, "delete"))
    print(obj1.locks.check(obj2, "get"))
    print(obj1.locks.check(obj2, "listen"))
