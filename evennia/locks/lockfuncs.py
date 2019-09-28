"""
This module provides a set of permission lock functions for use
with Evennia's permissions system.

To call these locks, make sure this module is included in the
settings tuple `PERMISSION_FUNC_MODULES` then define a lock on the form
'<access_type>:func(args)' and add it to the object's lockhandler.
Run the `access()` method of the handler to execute the lock check.

Note that `accessing_obj` and `accessed_obj` can be any object type
with a lock variable/field, so be careful to not expect
a certain object type.


**Appendix: MUX locks**

Below is a list nicked from the MUX help file on the locks available
in standard MUX. Most of these are not relevant to core Evennia since
locks in Evennia are considerably more flexible and can be implemented
on an individual command/typeclass basis rather than as globally
available like the MUX ones. So many of these are not available in
basic Evennia, but could all be implemented easily if needed for the
individual game.

```
MUX Name:      Affects:        Effect:
----------------------------------------------------------------------
DefaultLock:   Exits:          controls who may traverse the exit to
                               its destination.
                                 Evennia: "traverse:<lockfunc()>"
               Rooms:          controls whether the account sees the
                               SUCC or FAIL message for the room
                               following the room description when
                               looking at the room.
                                 Evennia: Custom typeclass
               Accounts/Things: controls who may GET the object.
                                 Evennia: "get:<lockfunc()"
 EnterLock:    Accounts/Things: controls who may ENTER the object
                                 Evennia:
 GetFromLock:  All but Exits:  controls who may gets things from a
                               given location.
                                 Evennia:
 GiveLock:     Accounts/Things: controls who may give the object.
                                 Evennia:
 LeaveLock:    Accounts/Things: controls who may LEAVE the object.
                                 Evennia:
 LinkLock:     All but Exits:  controls who may link to the location
                               if the location is LINK_OK (for linking
                               exits or setting drop-tos) or ABODE (for
                               setting homes)
                                 Evennia:
 MailLock:     Accounts:        controls who may @mail the account.
                               Evennia:
 OpenLock:     All but Exits:  controls who may open an exit.
                                 Evennia:
 PageLock:     Accounts:        controls who may page the account.
                                 Evennia: "send:<lockfunc()>"
 ParentLock:   All:            controls who may make @parent links to
                               the object.
                                 Evennia: Typeclasses and
                               "puppet:<lockstring()>"
 ReceiveLock:  Accounts/Things: controls who may give things to the
                               object.
                                 Evennia:
 SpeechLock:   All but Exits:  controls who may speak in that location
                                 Evennia:
 TeloutLock:   All but Exits:  controls who may teleport out of the
                               location.
                                 Evennia:
 TportLock:    Rooms/Things:   controls who may teleport there
                                 Evennia:
 UseLock:      All but Exits:  controls who may USE the object, GIVE
                               the object money and have the PAY
                               attributes run, have their messages
                               heard and possibly acted on by LISTEN
                               and AxHEAR, and invoke $-commands
                               stored on the object.
                                 Evennia: Commands and Cmdsets.
 DropLock:     All but rooms:  controls who may drop that object.
                                 Evennia:
 VisibleLock:  All:            Controls object visibility when the
                               object is not dark and the looker
                               passes the lock. In DARK locations, the
                               object must also be set LIGHT and the
                               viewer must pass the VisibleLock.
                                 Evennia: Room typeclass with
                                          Dark/light script
```
"""


from ast import literal_eval
from django.conf import settings
from evennia.utils import utils

_PERMISSION_HIERARCHY = [pe.lower() for pe in settings.PERMISSION_HIERARCHY]
# also accept different plural forms
_PERMISSION_HIERARCHY_PLURAL = [
    pe + "s" if not pe.endswith("s") else pe for pe in _PERMISSION_HIERARCHY
]


def _to_account(accessing_obj):
    "Helper function. Makes sure an accessing object is an account object"
    if utils.inherits_from(accessing_obj, "evennia.objects.objects.DefaultObject"):
        # an object. Convert to account.
        accessing_obj = accessing_obj.account
    return accessing_obj


# lock functions


def true(*args, **kwargs):
    "Always returns True."
    return True


def all(*args, **kwargs):
    return True


def false(*args, **kwargs):
    "Always returns False"
    return False


def none(*args, **kwargs):
    return False


def self(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Check if accessing_obj is the same as accessed_obj

    Usage:
       self()

    This can be used to lock specifically only to
    the same object that the lock is defined on.
    """
    return accessing_obj == accessed_obj


def perm(accessing_obj, accessed_obj, *args, **kwargs):
    """
    The basic permission-checker. Ignores case.

    Usage:
       perm(<permission>)

    where <permission> is the permission accessing_obj must
    have in order to pass the lock.

    If the given permission is part of settings.PERMISSION_HIERARCHY,
    permission is also granted to all ranks higher up in the hierarchy.

    If accessing_object is an Object controlled by an Account, the
    permissions of the Account is used unless the Attribute _quell
    is set to True on the Object. In this case however, the
    LOWEST hieararcy-permission of the Account/Object-pair will be used
    (this is order to avoid Accounts potentially escalating their own permissions
    by use of a higher-level Object)

    """
    # this allows the perm_above lockfunc to make use of this function too
    try:
        permission = args[0].lower()
        perms_object = accessing_obj.permissions.all()
    except (AttributeError, IndexError):
        return False

    gtmode = kwargs.pop("_greater_than", False)
    is_quell = False

    account = (
        utils.inherits_from(accessing_obj, "evennia.objects.objects.DefaultObject")
        and accessing_obj.account
    )
    # check object perms (note that accessing_obj could be an Account too)
    perms_account = []
    if account:
        perms_account = account.permissions.all()
        is_quell = account.attributes.get("_quell")

    # Check hirarchy matches; handle both singular/plural forms in hierarchy
    hpos_target = None
    if permission in _PERMISSION_HIERARCHY:
        hpos_target = _PERMISSION_HIERARCHY.index(permission)
    if permission.endswith("s") and permission[:-1] in _PERMISSION_HIERARCHY:
        hpos_target = _PERMISSION_HIERARCHY.index(permission[:-1])
    if hpos_target is not None:
        # hieratchy match
        hpos_account = -1
        hpos_object = -1

        if account:
            # we have an account puppeting this object. We must check what perms it has
            perms_account_single = [p[:-1] if p.endswith("s") else p for p in perms_account]
            hpos_account = [
                hpos
                for hpos, hperm in enumerate(_PERMISSION_HIERARCHY)
                if hperm in perms_account_single
            ]
            hpos_account = hpos_account and hpos_account[-1] or -1

        if not account or is_quell:
            # only get the object-level perms if there is no account or quelling
            perms_object_single = [p[:-1] if p.endswith("s") else p for p in perms_object]
            hpos_object = [
                hpos
                for hpos, hperm in enumerate(_PERMISSION_HIERARCHY)
                if hperm in perms_object_single
            ]
            hpos_object = hpos_object and hpos_object[-1] or -1

        if account and is_quell:
            # quell mode: use smallest perm from account and object
            if gtmode:
                return hpos_target < min(hpos_account, hpos_object)
            else:
                return hpos_target <= min(hpos_account, hpos_object)
        elif account:
            # use account perm
            if gtmode:
                return hpos_target < hpos_account
            else:
                return hpos_target <= hpos_account
        else:
            # use object perm
            if gtmode:
                return hpos_target < hpos_object
            else:
                return hpos_target <= hpos_object
    else:
        # no hierarchy match - check direct matches
        if account:
            # account exists, check it first unless quelled
            if is_quell and permission in perms_object:
                return True
            elif permission in perms_account:
                return True
        elif permission in perms_object:
            return True

    return False


def perm_above(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only allow objects with a permission *higher* in the permission
    hierarchy than the one given. If there is no such higher rank,
    it's assumed we refer to superuser. If no hierarchy is defined,
    this function has no meaning and returns False.
    """
    kwargs["_greater_than"] = True
    return perm(accessing_obj, accessed_obj, *args, **kwargs)


def pperm(accessing_obj, accessed_obj, *args, **kwargs):
    """
    The basic permission-checker only for Account objects. Ignores case.

    Usage:
       pperm(<permission>)

    where <permission> is the permission accessing_obj must
    have in order to pass the lock. If the given permission
    is part of _PERMISSION_HIERARCHY, permission is also granted
    to all ranks higher up in the hierarchy.
    """
    return perm(_to_account(accessing_obj), accessed_obj, *args, **kwargs)


def pperm_above(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only allow Account objects with a permission *higher* in the permission
    hierarchy than the one given. If there is no such higher rank,
    it's assumed we refer to superuser. If no hierarchy is defined,
    this function has no meaning and returns False.
    """
    return perm_above(_to_account(accessing_obj), accessed_obj, *args, **kwargs)


def dbref(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      dbref(3)

    This lock type checks if the checking object
    has a particular dbref. Note that this only
    works for checking objects that are stored
    in the database (e.g. not for commands)
    """
    if not args:
        return False
    try:
        dbr = int(args[0].strip().strip("#"))
    except ValueError:
        return False
    if hasattr(accessing_obj, "dbid"):
        return dbr == accessing_obj.dbid
    return False


def pdbref(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Same as dbref, but making sure accessing_obj is an account.
    """
    return dbref(_to_account(accessing_obj), accessed_obj, *args, **kwargs)


def id(accessing_obj, accessed_obj, *args, **kwargs):
    "Alias to dbref"
    return dbref(accessing_obj, accessed_obj, *args, **kwargs)


def pid(accessing_obj, accessed_obj, *args, **kwargs):
    "Alias to dbref, for Accounts"
    return dbref(_to_account(accessing_obj), accessed_obj, *args, **kwargs)


# this is more efficient than multiple if ... elif statments
CF_MAPPING = {
    "eq": lambda val1, val2: val1 == val2 or str(val1) == str(val2) or float(val1) == float(val2),
    "gt": lambda val1, val2: float(val1) > float(val2),
    "lt": lambda val1, val2: float(val1) < float(val2),
    "ge": lambda val1, val2: float(val1) >= float(val2),
    "le": lambda val1, val2: float(val1) <= float(val2),
    "ne": lambda val1, val2: float(val1) != float(val2),
    "default": lambda val1, val2: False,
}


def attr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      attr(attrname)
      attr(attrname, value)
      attr(attrname, value, compare=type)

    where compare's type is one of (eq,gt,lt,ge,le,ne) and signifies
    how the value should be compared with one on accessing_obj (so
    compare=gt means the accessing_obj must have a value greater than
    the one given).

    Searches attributes *and* properties stored on the accessing_obj.
    if accessing_obj has a property "obj", then this is used as
    accessing_obj (this makes this usable for Commands too)

    The first form works like a flag - if the attribute/property
    exists on the object, the value is checked for True/False. The
    second form also requires that the value of the attribute/property
    matches. Note that all retrieved values will be converted to
    strings before doing the comparison.
    """
    # deal with arguments
    if not args:
        return False
    attrname = args[0].strip()
    value = None
    if len(args) > 1:
        value = args[1].strip()
    compare = "eq"
    if kwargs:
        compare = kwargs.get("compare", "eq")

    def valcompare(val1, val2, typ="eq"):
        "compare based on type"
        try:
            return CF_MAPPING.get(typ, CF_MAPPING["default"])(val1, val2)
        except Exception:
            # this might happen if we try to compare two things that
            # cannot be compared
            return False

    if hasattr(accessing_obj, "obj"):
        # NOTE: this is relevant for Commands. It may clash with scripts
        # (they have Attributes and .obj) , but are scripts really
        # used so that one ever wants to check the property on the
        # Script rather than on its owner?
        accessing_obj = accessing_obj.obj

    # first, look for normal properties on the object trying to gain access
    if hasattr(accessing_obj, attrname):
        if value:
            return valcompare(str(getattr(accessing_obj, attrname)), value, compare)
        # will return Fail on False value etc
        return bool(getattr(accessing_obj, attrname))
    # check attributes, if they exist
    if hasattr(accessing_obj, "attributes") and accessing_obj.attributes.has(attrname):
        if value:
            return hasattr(accessing_obj, "attributes") and valcompare(
                accessing_obj.attributes.get(attrname), value, compare
            )
        # fails on False/None values
        return bool(accessing_obj.attributes.get(attrname))
    return False


def objattr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      objattr(attrname)
      objattr(attrname, value)
      objattr(attrname, value, compare=type)

    Works like attr, except it looks for an attribute on
    accessed_obj instead.

    """
    return attr(accessed_obj, accessed_obj, *args, **kwargs)


def locattr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      locattr(attrname)
      locattr(attrname, value)
      locattr(attrname, value, compare=type)

    Works like attr, except it looks for an attribute on
    accessing_obj.location, if such an entity exists.

    if accessing_obj has a property ".obj" (such as is the case for a
    Command), then accessing_obj.obj.location is used instead.

    """
    if hasattr(accessing_obj, "obj"):
        accessing_obj = accessing_obj.obj
    if hasattr(accessing_obj, "location"):
        return attr(accessing_obj.location, accessed_obj, *args, **kwargs)
    return False


def objlocattr(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      locattr(attrname)
      locattr(attrname, value)
      locattr(attrname, value, compare=type)

    Works like attr, except it looks for an attribute on
    accessed_obj.location, if such an entity exists.

    if accessed_obj has a property ".obj" (such as is the case for a
    Command), then accessing_obj.obj.location is used instead.

    """
    if hasattr(accessed_obj, "obj"):
        accessed_obj = accessed_obj.obj
    if hasattr(accessed_obj, "location"):
        return attr(accessed_obj.location, accessed_obj, *args, **kwargs)
    return False


def attr_eq(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)
    """
    return attr(accessing_obj, accessed_obj, *args, **kwargs)


def attr_gt(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)

    Only true if access_obj's attribute > the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{"compare": "gt"})


def attr_ge(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)

    Only true if access_obj's attribute >= the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{"compare": "ge"})


def attr_lt(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)

    Only true if access_obj's attribute < the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{"compare": "lt"})


def attr_le(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)

    Only true if access_obj's attribute <= the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{"compare": "le"})


def attr_ne(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       attr_gt(attrname, 54)

    Only true if access_obj's attribute != the value given.
    """
    return attr(accessing_obj, accessed_obj, *args, **{"compare": "ne"})


def tag(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
        tag(tagkey)
        tag(tagkey, category)

    Only true if accessing_obj has the specified tag and optional
    category.
    If accessing_obj has the ".obj" property (such as is the case for
    a command), then accessing_obj.obj is used instead.
    """
    if hasattr(accessing_obj, "obj"):
        accessing_obj = accessing_obj.obj
    tagkey = args[0] if args else None
    category = args[1] if len(args) > 1 else None
    return bool(accessing_obj.tags.get(tagkey, category=category))


def objtag(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
        objtag(tagkey)
        objtag(tagkey, category)

    Only true if accessed_obj has the specified tag and optional
    category.
    """
    return bool(accessed_obj.tags.get(*args))


def inside(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
       inside()

    Only true if accessing_obj is "inside" accessed_obj
    """
    return accessing_obj.location == accessed_obj


def holds(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Usage:
      holds()            checks if accessed_obj or accessed_obj.obj
                         is held by accessing_obj
      holds(key/dbref)   checks if accessing_obj holds an object
                          with given key/dbref
      holds(attrname, value)   checks if accessing_obj holds an
                               object with the given attrname and value

    This is passed if accessed_obj is carried by accessing_obj (that is,
    accessed_obj.location == accessing_obj), or if accessing_obj itself holds
    an object matching the given key.
    """
    try:
        # commands and scripts don't have contents, so we are usually looking
        # for the contents of their .obj property instead (i.e. the object the
        # command/script is attached to).
        contents = accessing_obj.contents
    except AttributeError:
        try:
            contents = accessing_obj.obj.contents
        except AttributeError:
            return False

    def check_holds(objid):
        # helper function. Compares both dbrefs and keys/aliases.
        objid = str(objid)
        dbref = utils.dbref(objid, reqhash=False)
        if dbref and any((True for obj in contents if obj.dbid == dbref)):
            return True
        objid = objid.lower()
        return any(
            (
                True
                for obj in contents
                if obj.key.lower() == objid or objid in [al.lower() for al in obj.aliases.all()]
            )
        )

    if not args:
        # holds() - check if accessed_obj or accessed_obj.obj is held by accessing_obj
        try:
            if check_holds(accessed_obj.dbid):
                return True
        except Exception:
            # we need to catch any trouble here
            pass
        return hasattr(accessed_obj, "obj") and check_holds(accessed_obj.obj.dbid)
    if len(args) == 1:
        # command is holds(dbref/key) - check if given objname/dbref is held by accessing_ob
        return check_holds(args[0])
    elif len(args=2):
        # command is holds(attrname, value) check if any held object has the given attribute and value
        for obj in contents:
            if obj.attributes.get(args[0]) == args[1]:
                return True
    return False


def superuser(*args, **kwargs):
    """
    Only accepts an accesing_obj that is superuser (e.g. user #1)

    Since a superuser would not ever reach this check (superusers
    bypass the lock entirely), any user who gets this far cannot be a
    superuser, hence we just return False. :)
    """
    return False


def has_account(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only returns true if accessing_obj has_account is true, that is,
    this is an account-controlled object. It fails on actual accounts!

    This is a useful lock for traverse-locking Exits to restrain NPC
    mobiles from moving outside their areas.
    """
    return hasattr(accessing_obj, "has_account") and accessing_obj.has_account


def serversetting(accessing_obj, accessed_obj, *args, **kwargs):
    """
    Only returns true if the Evennia settings exists, alternatively has
    a certain value.

    Usage:
      serversetting(IRC_ENABLED)
      serversetting(BASE_SCRIPT_PATH, ['types'])

    A given True/False or integers will be converted properly. Note that
    everything will enter this function as strings, so they have to be
    unpacked to their real value. We only support basic properties.
    """
    if not args or not args[0]:
        return False
    if len(args) < 2:
        setting = args[0]
        val = "True"
    else:
        setting, val = args[0], args[1]
    # convert
    try:
        val = literal_eval(val)
    except Exception:
        # we swallow errors here, lockfuncs has noone to report to
        return False

    if setting in settings._wrapped.__dict__:
        return settings._wrapped.__dict__[setting] == val
    return False
