"""
Permissions

Evennia's permission system can be as coarse or fine-grained as desired.

**Note: Django's in-built permission checking is still used for web-related access
to the admin site etc. This uses the normal django permission
strings of the form 'appname.permstring' and automatically adds three of them
for each model - for src/object this would be for example
 'object.create', 'object.admin' and 'object.edit'. Checking and permissions
 are done completely separate from the present mud permission system, see
 Django manuals. **


                              
Almost all engine elements (Commands, Players, Objects, Scripts,
Channels) have a field or variable called 'permissions' - this holds a
list or a comma-separated string of 'permission strings'. 

Whenever a permission is to be checked there is always an
'Accessing object' and an 'Accessed object'. The 'permissions' field
on the two objects are matched against each other. A permission field
can contain one of two types of strings - 'keys' and 'locks' and the 
accessing object's keys are matched against the accessing object's locks 
depending on which type of access is required. The check function 
has_perm (in this module) is used to handle the check.

access_obj.permissions (keys)    ---> |            |
                       lock_type ---> | has_perm() | ---> False/True 
accessed_obj.permissions (locks) ---> |            |

If there are no locks (of the right type) available on accessed_obj, access is 
granted by  default. You can however give an argument to has_perm() to reverse 
this policy to one where default is no access until explicitly granted.


- Keys

Keys are simple strings that can contain any alphanumerical symbol and
be of any length. They are case-sensitive. Only whitespace, colons(:) and 
commas (,) are not allowed in keys. 

examples: 
  myperm 
  look_perm
  Builders
  obj.create (this is what a general Django key looks like)


- Locks

A lock always consists of two parts separated by a colon (:). A lock must nowhere
contain commas (,) since these are used as separators between different locks and keys
during storage. 
 
  -type header-         -lock body- 
type1 type2 FLAG:string1 string2 string3()

type header

  The first part is the 'type' of lock, i.e. what kind of functionality
  this lock regulates. The function has_perm() takes this as an argument and uses it to sort
  out which locks are checked (if any).
  A type name is not case sensitive but may not contain any whitespace (or colons). Use   
  whitespaces to expand the number of types this lock represents. 
  The last word in the type header may be a special flag that regulates how the second 
  part of the lock is handled, especially if the second part is a space-separated list 
  of permissions: 
  - OR or ANY (or none, default) - ANY one match in list means that the entire lock is passed. 
  - AND or ALL - ALL permissions in list must be matched by accessing obj for lock to pass
  - NOT - inverses the lock. A matched lock means False and vice versa.
 
lock body
      
  The second part, after the comma, is the function body of the lock. The function body
  can look in several ways:
  - it could be a permission string, to be matched directly with a key
  - it could be a function call to a function defined in a safe module (this returns True/False)
  - it could be a space-separated list of any combination of the above.
  - it could be one of the non-passable keywords FALSE, LOCK or IMPASSABLE (can be put in a 
    list too, but the list will then always return False, so they are usually
    used on their own). 
    
examples:

  look:look_perm
 
   this lock is of type 'look' and simply checks if the accessing_obj has 
   they key look_perm or not. 

  add edit:Builders

   this lock regulates two lock types, 'add' and 'edit'. In both cases, 
   having the key 'Builders' will pass the lock.

  add edit:Builders Admin

    this is like above, but it is passed if the accessing object has either
    the key Builders or the key Admin (or both)

  system NOT: Untrusted
   
   this lock of type 'system' is passed if the accessing object does NOT have 
   the key 'Untrusted', since the NOT flag inverses the lock result.

  delete:FALSE 

   this lock, of type 'delete' can never be passed since the keyword FALSE
   is always False (same with LOCK and IMPASSABLE). 

  open:

    this lock has an empty lock body and is an always passable lock. Unless you 
    change how has_perm() behaves you can usually just completely skip defining 
    this lock to get the same effect.

  enter:has_key()

   this 'enter'-type lock might for example be placed on a door. The lock body
   is a function has_key() defined in a module set in the settings. See below 
   for more info on lock functions. It is up the admin to create
   these lock functions ahead of time as needed for the game. 

  unlock:has_pickpocket_lvl(4,difficulty=7)

   function locks can even take arguments, in this case it calls a function
   has_pick() with info on how hard the lock is. 

  delete AND: Builders can_delete has_credits()

   Since the keyword AND is set (ALL would also work), the 
   accessing object must have both the 'Builders', 'can_delete' 
   *and* the function lock 'has_credits()' in order to pass the lock. 

- More on functional locks

A function lock goes into the second part of a lock definition (after the colon). 

Syntax:
  funcname(arg3, arg4, ...)
  arg1 == always accessing_obj
  arg2 == always accessed_obj

A function lock is called just like any Python function and should be defined in
the same way. The system searches for the first matching function in one of the 
modules defined by settings.PERMISSION_FUNC_MODULES and executes it. 

Accessing_object and Accessed_object are always passed, followed by the arguments
and keywords supplied in the permission. The function should return a boolean and 
must make sure to handle any possible type of objects being passed in 
the first two arguments (such as Command objects, Scripts or whatever). There is a 
convenience function available in this module (get_types) for doing just that.

examples: 
  'is_stronger_than(40)'
  'is_suitably_dressed()'
  'has_lockpick_higher_than(24, difficulty=4)'
  'has_attr_value('mood', 'happy')


- Permissions string

As mentioned, keys and locks are stored together on an object in a string 
called 'permissions'. You are most likely to come into contact with this 
when defining new Commands. 

This is a comma-separated string (which is why commas
are not allowed in keys nor in locks). Keys and Locks can appear in any 
order in the permission string, they are easily separated by the colon 
appearing only in locks. 

example:

  'call ALL:can_edit Builders'

    this might be a Command permission and has only one lock on it (a command usually have no need
    for keys of its own) but two requirements to be able to call it: The accessing object
    (probably a player) must have both the can_edit and Builders keys (one is not enough
    since the ALL flag is set). 

  'Builders, edit_channels, control:has_id(45)'
    
    this permission string could sit on a Character object. It has two keys and one lock. 
    The keys tell us Character is a Builder and also has the edit_channels permission. 
    The lock is checked when someone tries to gain 'control' over this object (whatever 
    this means in your game). This lock calls the function has_id() with the argument 45. 
    We can't see here what has_id() actually does, but a likely implementation would 
    be to return True only if the accessing object actually has an id of 45.


- Reserved Server lock types 
 
The Evennia server (i.e. everything in /src) tries to 'outsource' as many permission checks 
as possible to what the admin can customize in /game. All the admin needs to do is import
has_perm() from this module to use the system. As seen above, the actual syntax of 
locks and keys above gives the admin much freedom in designing their own system. 

That said, there are a few actions that cannot be outsourced due to technical reasons. 
In these situations the server must hard-code its permission checks. What this means 
is that it always calls has_perm() with a specific lock-type keyword that you cannot change. For 
example it always checks if a command may be accessed by matching the calling player's 
keys against command-locks of type 'call'. Below you will find all hard-coded lock types
the server checks and when it does it. 

locktype        entity     situation

call            Command    when a player tries to call a
                           command. Determines if the command is available
                           at all. Also determines if command will be
                           visible in help lists etc.

chan_send       Channels
chan_listen       "

traverse        Exits 



"""

from django.conf import settings
from src.permissions.models import PermissionGroup
from src.utils import logger 
from src.utils.utils import is_iter

IMPASSABLE = ['FALSE', 'LOCK', 'IMPASSABLE']
ORFLAGS = ['OR', 'ANY']
ANDFLAGS = ['AND', 'ALL']
NOTFLAGS = ['NOT']

LOCK_FUNC_PATHS = settings.PERMISSION_FUNC_MODULES
CACHED_FUNC_MODULES = []

PARENTS = {
    "command":"src.commands.command.Command",
    "msg":"src.comms.models.Msg",
    "channel":"src.comms.models.Channel",
    "help":"src.help.models.HelpEntry",
    "typeclass":"src.typeclasses.typeclass.TypeClass",
    "script":"src.scripts.models.ScriptDB",
    "object":"src.objects.models.ObjectDB",
    "player":"src.players.models.Player"}

#
# Utility functions for handling permissions
#
    
def perm_to_list(permissions):
    """
    Process a permstring and return a list

    permissions - can be a list of permissions, a permission string
           or a comma-separated string of permissions.    
    """
    if not permissions:
        return []
    if not is_iter(permissions):
        # convert input to a list
        permissions = str(permissions)
        if ',' in permissions:
            permissions = permissions.split(',')
        else:
            permissions = [permissions]
    p_nested = []
    for nested_perm in (p for p in permissions if ',' in p):
        # handling eventual weird nested comma-separated
        # permissions inside lists
        p_nested.extend(nested_perm.split(','))
    permissions.extend(p_nested)

    # merge units with unmatched parenthesis (so e.g. '(a,b,c,d)' are not
    # split by comma separation (this allows for functional locks with
    # multiple arguments, like 'has_attr(attrname, attrvalue)'). This
    # also removes all whitespace in the parentheses to avoid confusion later. 

    lparents = 0
    rparents = 0
    in_block = False 
    perm_list = []
    for perm in permissions:
        lparents += perm.count('(')
        rparents += perm.count(')')
        if lparents > rparents:
            # unmatched left-parenthesis - trigger block preservation
            if not in_block:
                # beginning of block
                in_block = True
                perm_list.append(perm)                
            else:
                # in block
                block = perm_list.pop()
                perm_list.append(",".join([block.strip(), perm.strip()]))       
        elif in_block:
            # parentheses match again - end the block 
            in_block = False
            block = perm_list.pop()
            perm_list.append(",".join([block.strip(), perm.strip()]))                       
        else:
            # no parenthesis/block 
            perm_list.append(perm.strip())
    return perm_list 

def set_perm(obj, new_perms, replace=True):
    """
    Set a permission string on an object. 
    The permissions given by default replace the old one.
    If 'replace' is unset, the new one will be appended to 
    the old ones. 
    
    obj - object to receive permission. must have field/variable
          named 'permissions' for this to work. 
    new_perms - a permission string, a list of permission strings
           or a comma-separated string of permissions
    replace - clear and replace old permission completely

    Note - this is also how you add an entity to a group
    """
    try:
        # get the old permissions if possible 
        obj_perms = perm_to_list(obj.permissions)
    except AttributeError:
        # this object cannot get a permission 
        return False
    new_perms = perm_to_list(new_perms)
    if replace:
        # replace permissions completely 
        obj_perms = new_perms
    else:
        # extend the old permissions with the new ones
        for newperm in (perm for perm in new_perms if perm not in obj_perms):
            obj_perms.append(newperm)
    # set on object as comma-separated list.
    obj.permissions = ",".join(str(perm).strip() for perm in obj_perms)
    try:
        # E.g. Commands are not db-connected and cannot save,
        # so we ignore errors here. 
        obj.save()
    except Exception:
        pass
    return True 

def add_perm(obj, add_perms):
    """
    Convenience function to add a permission to an entity.
    """
    return set_perm(obj, add_perms, replace=False)

def del_perm(obj, del_perms):
    """
    Remove permission from object (if possible)
    """
    try:
        obj_perms = perm_to_list(obj.permissions)
    except AttributeError:
        return False
    del_perms = perm_to_list(del_perms)
    obj_perms = [perm for perm in obj_perms if perm not in del_perms]
    obj.permissions = ",".join(str(perm) for perm in obj_perms)
    try:
        obj.save()
    except Exception:
        pass 
    return True 
        
def get_types(accessing_obj, accessed_obj):
    """
    A convenience function for determining what type the objects are. 
    This is intended for easy importing into the modules
    defined in LOCK_FUNC_PATHS.
    """

    def has_parent(basepath, obj):
        "Checks if basepath is somewhere is objs parent tree."
        return any(cls for cls in obj.__class__.mro()
                   if basepath == "%s.%s" % (cls.__module__, cls.__name__))

    checking_type = None
    checked_type = None 
    try:
        checking_type = [parent for parent, path in PARENTS.items()
                         if has_parent(path, accessing_obj)][0]
        if checking_type == 'typeclass':
            checking_type = [parent for parent, path in PARENTS.items()
                             if has_parent(path, accessing_obj.db)][0]
    except IndexError:
        logger.log_trace("LockFunc: %s is not of a valid type."
                         % accessing_obj)
        raise
    try:
        checked_type = [parent for parent, path in PARENTS.items()
                        if has_parent(path, accessed_obj)][0]
        if checking_type == 'typeclass':
            checked_type = [parent for parent, path in PARENTS.items()
                            if has_parent(path, accessed_obj.db)][0]
    except IndexError:
        logger.log_trace("LockFunc: %s is not of a valid type."
                         % accessed_obj)
        raise 
    return (checking_type, checked_type)


#
# helper functions for has_perm()
#


def append_group_permissions(keylist):
    """
    Step through keylist and discover if
    one the keys match a permission group name
    (case sensitive). In that case, go into
    that group and add its permissions to
    the keylist.
    """
    groups = []
    for match_key in keylist:
        try:
            groups.append(PermissionGroup.objects.get(db_key=match_key))
        except Exception: 
            pass    
    for group in groups:
        keylist.extend(perm_to_list(group.group_permissions))
    return list(set(keylist)) # set makes elements of keylist unique

def try_impassable(lockdefs):
    """
    Test if this list of lockdefs is impassable.    
    """
    return any(True for lockdef in lockdefs if lockdef in IMPASSABLE)

def try_key_lock(iflag, keylist, lockdefs):
    """
    Test a direct-comparison match between keys and lockstrings. 
    Returns the number of matches found.
    """
    if iflag in ANDFLAGS:
        return len([True for key in keylist if key in lockdefs])
    elif iflag in NOTFLAGS:
        return not any(True for key in keylist if key in lockdefs)
    else:
        return any(True for key in keylist if key in lockdefs)

def try_functional_lock(lflag, lockdefs, accessing_obj, accessed_obj):
    """
    Functional lock

    lockdefs is a list of permission strings (called by check_lock)
    """
    global CACHED_FUNC_MODULES

    if not CACHED_FUNC_MODULES:         
        # Cache the imported func module(s) once and for all
        # so we don't have to re-import them for every call.
        # We allow for LOCK_FUNC_PATHS to be a tuple of
        # paths as well. 
        CACHED_FUNC_MODULES = []
        try:
            module_paths = list(LOCK_FUNC_PATHS)
        except Exception:
            module_paths = [LOCK_FUNC_PATHS]
        for path in module_paths: 
            try:
                CACHED_FUNC_MODULES.append(__import__(path, fromlist=[True]))
            except ImportError:
                logger.log_trace("lock func: import error for '%s'" % path)
                continue
        
    # try to execute functions, if they exist 
    #print "locklist:", locklist
    passed_locks = 0
    for lockstring in lockdefs:
        if not lockstring \
                or not ('(' in lockstring and ')' in lockstring) \
                or not (lockstring.find('(') < lockstring.find(')')):
            # must be a valid function() call
            continue
        funcname, args = (str(part).strip() for part in lockstring.split('(', 1))
        args = args.rstrip(')').split(',')
        kwargs = [kwarg for kwarg in args if '=' in kwarg]
        args = tuple([arg for arg in args if arg not in kwargs])        
        kwargs = dict([(key.strip(), value.strip()) for key, value in [kwarg.split('=', 1) for kwarg in kwargs]])
        #print "%s '%s'" % (funcname, args)        
        for module in CACHED_FUNC_MODULES:
            # step through all safe modules, executing the first one that matches
            lockfunc = module.__dict__.get(funcname, None)
            if callable(lockfunc):
                try:            
                    # try the lockfunction.
                    if lockfunc(accessing_obj, accessed_obj, *args, **kwargs):
                        if lflag in ANDFLAGS:
                            passed_locks += 1  
                        elif lflag in NOTFLAGS:
                            return False
                        else:
                            return True 
                except Exception:
                    continue 
    return passed_locks


#------------------------------------------------------------
# has_perm & has_perm_string : main access functions
#------------------------------------------------------------

def has_perm(accessing_obj, accessed_obj, lock_type, default_deny=False):
    """
    The main access method of the permission system. Note that
    this will not perform checks against django's in-built permission
    system, that is assumed to be done in the calling function
    after this method returns False. 

    accessing_obj - the object trying to gain access
    accessed_obj - the object being checked for access
    lock_type - Only locks of this type 'lock_type:permissionstring'
                  will be considered for a match. 
    default_deny - Normally, if no suitable locks are found on the object, access
                   is granted by default. This switch changes security policy to
                   instead lock down the object unless access is explicitly given. 
    """

    # Get the list of locks of the accessed_object 
    
    try: 
        locklist = [lock for lock in perm_to_list(accessed_obj.permissions) if ':' in lock]
    except AttributeError: 
        # This is not a valid permissable object at all
        logger.log_trace()
        return False        
                               
    # filter the locks to find only those of the correct lock_type. This creates
    # a list with elements being tuples (flag, [lockdef, lockdef, ...])                          

    lock_type = lock_type.lower()
    locklist = [(typelist[-1].strip(), [lo.strip() for lo in lock.split(None)]) 
                for typelist, lock in [(ltype.split(None), lock) 
                                       for ltype, lock in [lock.split(':', 1) 
                                                           for lock in locklist]] 
                if typelist and lock_type in typelist]

    if not locklist or not any(locklist):
        # No locks; use default security policy
        return not default_deny 

    # we have locks of the right type. Set default flag OR on all that 
    # don't explictly specify a flag (AND, OR, NOT). These flags determine
    # how the permstrings in the lock definition should relate to one another.
    locktemp = []
    for ltype, lock in locklist:
        if ltype not in ANDFLAGS and ltype not in NOTFLAGS:
            ltype = 'OR'
        locktemp.append((ltype, lock))
    locklist = locktemp
   
    # Get the list of keys of the accessing_object 

    keylist = []

    #print "testing %s" % accessing_obj.__class__
    if hasattr(accessing_obj, 'is_superuser') and accessing_obj.is_superuser:
        # superusers always have access.
        return True 

    # try to add permissions from connected player
    if hasattr(accessing_obj, 'has_player') and accessing_obj.has_player:
        # accessing_obj has a valid, connected player. We start with 
        # those permissions. 
        player = accessing_obj.player        
        if player.is_superuser:
            # superuser always has access
            return True        
        try:
            keylist.extend([perm for perm in perm_to_list(player.permissions) 
                            if not ':' in perm])
        except Exception:
            pass            

    # next we get the permissions directly from accessing_obj. 
    try:
        keylist.extend([perm for perm in perm_to_list(accessing_obj.permissions) 
                        if not ':' in perm])
    except Exception:
        # not a valid permissable object
        return False             
    # expand also with group permissions, if any
    keylist = append_group_permissions(keylist)

    #print "keylist: %s" % keylist


    # Test permissions against the locks


    for lflag, lockdefs in locklist:        

        # impassable locks normally shuts down the entire operation right away.
        if try_impassable(lockdefs):
            return lflag in NOTFLAGS

        # test direct key-lock comparison and functional locks
        if lflag in ANDFLAGS:
            # with the AND flag, we have to match all lockdefs to pass the lock
            passed_locks = try_key_lock(lflag, keylist, lockdefs)
            passed_locks += try_functional_lock(lflag, lockdefs, accessing_obj, accessed_obj)
            if passed_locks == len(lockdefs):
                return True 
        else:
            # normal operation; any match passes the lock
            if try_key_lock(lflag, keylist, lockdefs):
                return True 
            if try_functional_lock(lflag, lockdefs, accessing_obj, accessed_obj):
                return True 
    # If we fall through to here, we don't have access
    return False 

def has_perm_string(accessing_obj, lock_list, default_deny=False):
    """
    This tests the given accessing object against the
    given string rather than a particular accessing object.

    OBS: Be careful if supplying function locks to this method since
    there is no meaningful accessed_obj present (the one fed to
    the function is just a dummy). 

    accessing_obj - the object being checked for permissions
    lock_list - a list or a comma-separated string of lock definitions.
    default_deny - Normally, if no suitable locks are found on the object, access
                   is granted by default. This switch changes security policy to
                   instead lock down the object unless access is explicitly given. 
    """

    # prepare the permissions we want, so it's properly stripped etc.
    class Dummy(object):
        "Dummy object"
        def __init__(self, permissions):
            self.permissions = permissions

    if not is_iter(lock_list):        
        lock_list = [perm for perm in lock_list.split(',')]
    lockstring = ",".join(["dummy:%s" % perm.strip() for perm in lock_list if perm.strip()])

    # prepare a dummy object with the permissions
    accessed_obj = Dummy(lockstring)
    # call has_perm normally with the dummy object.
    return has_perm(accessing_obj, accessed_obj, 'dummy', default_deny)
