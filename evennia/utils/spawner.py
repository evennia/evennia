"""
Spawner

The spawner takes input files containing object definitions in
dictionary forms. These use a prototype architecture to define
unique objects without having to make a Typeclass for each.

The main function is `spawn(*prototype)`, where the `prototype`
is a dictionary like this:

```python
GOBLIN = {
 "typeclass": "types.objects.Monster",
 "key": "goblin grunt",
 "health": lambda: randint(20,30),
 "resists": ["cold", "poison"],
 "attacks": ["fists"],
 "weaknesses": ["fire", "light"]
 "tags": ["mob", "evil", ('greenskin','mob')]
 "args": [("weapon", "sword")]
 }
```

Possible keywords are:
    prototype_key (str):  name of this prototype. This is used when storing prototypes and should
        be unique. This should always be defined but for prototypes defined in modules, the
        variable holding the prototype dict will become the prototype_key if it's not explicitly
        given.
    prototype_desc (str, optional): describes prototype in listings
    prototype_locks (str, optional): locks for restricting access to this prototype. Locktypes
        supported are 'edit' and 'use'.
    prototype_tags(list, optional): List of tags or tuples (tag, category) used to group prototype
        in listings

    prototype (str or callable, optional): bame (prototype_key) of eventual parent prototype
    typeclass (str or callable, optional): if not set, will use typeclass of parent prototype or use
        `settings.BASE_OBJECT_TYPECLASS`
    key (str or callable, optional): the name of the spawned object. If not given this will set to a
        random hash
    location (obj, str or callable, optional): location of the object - a valid object or #dbref
    home (obj, str or callable, optional): valid object or #dbref
    destination (obj, str or callable, optional): only valid for exits (object or #dbref)

    permissions (str, list or callable, optional): which permissions for spawned object to have
    locks (str or callable, optional): lock-string for the spawned object
    aliases (str, list or callable, optional): Aliases for the spawned object
    exec (str or callable, optional): this is a string of python code to execute or a list of such
        codes.  This can be used e.g. to trigger custom handlers on the object. The execution
        namespace contains 'evennia' for the library and 'obj'. All default spawn commands limit
        this functionality to Developer/superusers. Usually it's better to use callables or
        prototypefuncs instead of this.
    tags (str, tuple, list or callable, optional): string or list of strings or tuples
        `(tagstr, category)`. Plain strings will be result in tags with no category (default tags).
    attrs (tuple, list or callable, optional): tuple or list of tuples of Attributes to add. This
        form allows more complex Attributes to be set. Tuples at least specify `(key, value)`
        but can also specify up to `(key, value, category, lockstring)`. If you want to specify a
        lockstring but not a category, set the category to `None`.
    ndb_<name> (any): value of a nattribute (ndb_ is stripped)
    other (any): any other name is interpreted as the key of an Attribute with
        its value. Such Attributes have no categories.

Each value can also be a callable that takes no arguments. It should
return the value to enter into the field and will be called every time
the prototype is used to spawn an object. Note, if you want to store
a callable in an Attribute, embed it in a tuple to the `args` keyword.

By specifying the "prototype" key, the prototype becomes a child of
that prototype, inheritng all prototype slots it does not explicitly
define itself, while overloading those that it does specify.

```python
import random


GOBLIN_WIZARD = {
 "prototype": GOBLIN,
 "key": "goblin wizard",
 "spells": ["fire ball", "lighting bolt"]
 }

GOBLIN_ARCHER = {
 "prototype": GOBLIN,
 "key": "goblin archer",
 "attack_skill": (random, (5, 10))"
 "attacks": ["short bow"]
}
```

One can also have multiple prototypes. These are inherited from the
left, with the ones further to the right taking precedence.

```python
ARCHWIZARD = {
 "attack": ["archwizard staff", "eye of doom"]

GOBLIN_ARCHWIZARD = {
 "key" : "goblin archwizard"
 "prototype": (GOBLIN_WIZARD, ARCHWIZARD),
}
```

The *goblin archwizard* will have some different attacks, but will
otherwise have the same spells as a *goblin wizard* who in turn shares
many traits with a normal *goblin*.


Storage mechanism:

This sets up a central storage for prototypes. The idea is to make these
available in a repository for buildiers to use. Each prototype is stored
in a Script so that it can be tagged for quick sorting/finding and locked for limiting
access.

This system also takes into consideration prototypes defined and stored in modules.
Such prototypes are considered 'read-only' to the system and can only be modified
in code. To replace a default prototype, add the same-name prototype in a
custom module read later in the settings.PROTOTYPE_MODULES list. To remove a default
prototype, override its name with an empty dict.


"""
from __future__ import print_function

import copy
import hashlib
import time
from ast import literal_eval
from django.conf import settings
from random import randint
import evennia
from evennia.objects.models import ObjectDB
from evennia.utils.utils import (
    make_iter, all_from_module, callables_from_module, dbid_to_obj,
    is_iter, crop, get_all_typeclasses)
from evennia.utils import inlinefuncs

from evennia.scripts.scripts import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.evtable import EvTable
from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils.ansi import strip_ansi


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")
_NON_CREATE_KWARGS = _CREATE_OBJECT_KWARGS + _PROTOTYPE_META_NAMES
_MODULE_PROTOTYPES = {}
_MODULE_PROTOTYPE_MODULES = {}
_PROTOTYPEFUNCS = {}
_MENU_CROP_WIDTH = 15
_PROTOTYPE_TAG_CATEGORY = "spawned_by_prototype"

_MENU_ATTR_LITERAL_EVAL_ERROR = (
    "|rCritical Python syntax error in your value. Only primitive Python structures are allowed.\n"
    "You also need to use correct Python syntax. Remember especially to put quotes around all "
    "strings inside lists and dicts.|n")


class PermissionError(RuntimeError):
    pass


# load resources


for mod in settings.PROTOTYPE_MODULES:
    # to remove a default prototype, override it with an empty dict.
    # internally we store as (key, desc, locks, tags, prototype_dict)
    prots = [(prototype_key, prot) for prototype_key, prot in all_from_module(mod).items()
             if prot and isinstance(prot, dict)]
    # assign module path to each prototype_key for easy reference
    _MODULE_PROTOTYPE_MODULES.update({prototype_key: mod for prototype_key, _ in prots})
    # make sure the prototype contains all meta info
    for prototype_key, prot in prots:
        actual_prot_key = prot.get('prototype_key', prototype_key).lower()
        prot.update({
          "prototype_key": actual_prot_key,
          "prototype_desc": prot['prototype_desc'] if 'prototype_desc' in prot else mod,
          "prototype_locks": (prot['prototype_locks']
                              if 'prototype_locks' in prot else "use:all();edit:false()"),
          "prototype_tags": list(set(make_iter(prot.get('prototype_tags', [])) + ["module"]))})
        _MODULE_PROTOTYPES[actual_prot_key] = prot


for mod in settings.PROTOTYPEFUNC_MODULES:
    try:
        _PROTOTYPEFUNCS.update(callables_from_module(mod))
    except ImportError:
        pass


# Helper functions


def olcfunc_parser(value, available_functions=None, **kwargs):
    """
    This is intended to be used by the in-game olc mechanism. It will parse the prototype
    value for function tokens like `$olcfunc(arg, arg, ...)`. These functions behave all the
    parameters of `inlinefuncs` but they are *not* passed a Session since this is not guaranteed to
    be available at the time of spawning. They may also return other structures than strings.

    Available olcfuncs are specified as callables in one of the modules of
    `settings.PROTOTYPEFUNC_MODULES`, or specified on the command line.

    Args:
        value (string): The value to test for a parseable olcfunc.
        available_functions (dict, optional): Mapping of name:olcfunction to use for this parsing.

    Kwargs:
        any (any): Passed on to the inlinefunc.

    Returns:
        any (any): A structure to replace the string on the prototype level. If this is a
            callable or a (callable, (args,)) structure, it will be executed as if one had supplied
            it to the prototype directly.

    """
    if not isinstance(basestring, value):
        return value
    available_functions = _PROTOTYPEFUNCS if available_functions is None else available_functions
    return inlinefuncs.parse_inlinefunc(value, _available_funcs=available_functions)


def _to_obj(value, force=True):
    return dbid_to_obj(value, ObjectDB)


def _to_obj_or_any(value):
    obj = dbid_to_obj(value, ObjectDB)
    return obj if obj is not None else value


def validate_spawn_value(value, validator=None):
    """
    Analyze the value and produce a value for use at the point of spawning.

    Args:
        value (any): This can be:j
            callable - will be called as callable()
            (callable, (args,)) - will be called as callable(*args)
            other - will be assigned depending on the variable type
            validator (callable, optional): If given, this will be called with the value to
                check and guarantee the outcome is of a given type.

    Returns:
        any (any): The (potentially pre-processed value to use for this prototype key)

    """
    validator = validator if validator else lambda o: o
    if callable(value):
        return validator(value())
    elif value and is_iter(value) and callable(value[0]):
        # a structure (callable, (args, ))
        args = value[1:]
        return validator(value[0](*make_iter(args)))
    else:
        return validator(value)


# Prototype storage mechanisms


class DbPrototype(DefaultScript):
    """
    This stores a single prototype
    """
    def at_script_creation(self):
        self.key = "empty prototype"  # prototype_key
        self.desc = "A prototype"     # prototype_desc


def save_db_prototype(caller, prototype, key=None, desc=None, tags=None, locks="", delete=False):
    """
    Store a prototype persistently.

    Args:
        caller (Account or Object): Caller aiming to store prototype. At this point
            the caller should have permission to 'add' new prototypes, but to edit
            an existing prototype, the 'edit' lock must be passed on that prototype.
        prototype (dict): Prototype dict.
        key (str): Name of prototype to store. Will be inserted as `prototype_key` in the prototype.
        desc (str, optional): Description of prototype, to use in listing. Will be inserted
            as `prototype_desc` in the prototype.
        tags (list, optional): Tag-strings to apply to prototype. These are always
            applied with the 'db_prototype' category. Will be inserted as `prototype_tags`.
        locks (str, optional): Locks to apply to this prototype. Used locks
            are 'use' and 'edit'. Will be inserted as `prototype_locks` in the prototype.
        delete (bool, optional): Delete an existing prototype identified by 'key'.
            This requires `caller` to pass the 'edit' lock of the prototype.
    Returns:
        stored (StoredPrototype or None): The resulting prototype (new or edited),
            or None if deleting.
    Raises:
        PermissionError: If edit lock was not passed by caller.


    """
    key_orig = key or prototype.get('prototype_key', None)
    if not key_orig:
        caller.msg("This prototype requires a prototype_key.")
        return False
    key = str(key).lower()

    # we can't edit a prototype defined in a module
    if key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(key_orig, mod))

    prototype['prototype_key'] = key

    if desc:
        desc = prototype['prototype_desc'] = desc
    else:
        desc = prototype.get('prototype_desc', '')

    # set up locks and check they are on a valid form
    locks = locks or prototype.get(
        "prototype_locks", "use:all();edit:id({}) or perm(Admin)".format(caller.id))
    prototype['prototype_locks'] = locks

    is_valid, err = caller.locks.validate(locks)
    if not is_valid:
        caller.msg("Lock error: {}".format(err))
        return False

    if tags:
        tags = [(tag, "db_prototype") for tag in make_iter(tags)]
    else:
        tags = prototype.get('prototype_tags', [])
    prototype['prototype_tags'] = tags

    stored_prototype = DbPrototype.objects.filter(db_key=key)

    if stored_prototype:
        # edit existing prototype
        stored_prototype = stored_prototype[0]
        if not stored_prototype.access(caller, 'edit'):
            raise PermissionError("{} does not have permission to "
                                  "edit prototype {}.".format(caller, key))

        if delete:
            # delete prototype
            stored_prototype.delete()
            return True

        if desc:
            stored_prototype.desc = desc
        if tags:
            stored_prototype.tags.batch_add(*tags)
        if locks:
            stored_prototype.locks.add(locks)
        if prototype:
            stored_prototype.attributes.add("prototype", prototype)
    elif delete:
        # didn't find what to delete
        return False
    else:
        # create a new prototype
        stored_prototype = create_script(
            DbPrototype, key=key, desc=desc, persistent=True,
            locks=locks, tags=tags, attributes=[("prototype", prototype)])
    return stored_prototype


def delete_db_prototype(caller, key):
    """
    Delete a stored prototype

    Args:
        caller (Account or Object): Caller aiming to delete a prototype.
        key (str): The persistent prototype to delete.
    Returns:
        success (bool): If deletion worked or not.
    Raises:
        PermissionError: If 'edit' lock was not passed.

    """
    return save_db_prototype(caller, key, None, delete=True)


def search_db_prototype(key=None, tags=None, return_queryset=False):
    """
    Find persistent (database-stored) prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.
        return_queryset (bool, optional): Return the database queryset.
    Return:
        matches (queryset or list): All found DbPrototypes. If `return_queryset`
            is not set, this is a list of prototype dicts.

    Note:
        This does not include read-only prototypes defined in modules; use
        `search_module_prototype` for those.

    """
    if tags:
        # exact match on tag(s)
        tags = make_iter(tags)
        tag_categories = ["db_prototype" for _ in tags]
        matches = DbPrototype.objects.get_by_tag(tags, tag_categories)
    else:
        matches = DbPrototype.objects.all()
    if key:
        # exact or partial match on key
        matches = matches.filter(db_key=key) or matches.filter(db_key__icontains=key)
    if not return_queryset:
        # return prototype
        matches = [dict(dbprot.attributes.get("prototype", {})) for dbprot in matches]
    return matches


def search_module_prototype(key=None, tags=None):
    """
    Find read-only prototypes, defined in modules.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key to query for.

    Return:
        matches (list): List of prototypes matching the search criterion.

    """
    matches = {}
    if tags:
        # use tags to limit selection
        tagset = set(tags)
        matches = {prototype_key: prototype
                   for prototype_key, prototype in _MODULE_PROTOTYPES.items()
                   if tagset.intersection(prototype.get("prototype_tags", []))}
    else:
        matches = _MODULE_PROTOTYPES

    if key:
        if key in matches:
            # exact match
            return [matches[key]]
        else:
            # fuzzy matching
            return [prototype for prototype_key, prototype in matches.items()
                    if key in prototype_key]
    else:
        return [match for match in matches.values()]


def search_prototype(key=None, tags=None):
    """
    Find prototypes based on key and/or tags, or all prototypes.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.

    Return:
        matches (list): All found prototype dicts. If no keys
            or tags are given, all available prototypes will be returned.

    Note:
        The available prototypes is a combination of those supplied in
        PROTOTYPE_MODULES and those stored from in-game. For the latter,
        this will use the tags to make a subselection before attempting
        to match on the key. So if key/tags don't match up nothing will
        be found.

    """
    module_prototypes = search_module_prototype(key, tags)
    db_prototypes = search_db_prototype(key, tags)

    matches = db_prototypes + module_prototypes
    if len(matches) > 1 and key:
        key = key.lower()
        # avoid duplicates if an exact match exist between the two types
        filter_matches = [mta for mta in matches
                          if mta.get('prototype_key') and mta['prototype_key'] == key]
        if filter_matches and len(filter_matches) < len(matches):
            matches = filter_matches

    return matches


def search_objects_with_prototype(prototype_key):
    """
    Retrieve all object instances created by a given prototype.

    Args:
        prototype_key (str): The exact (and unique) prototype identifier to query for.

    Returns:
        matches (Queryset): All matching objects spawned from this prototype.

    """
    return ObjectDB.objects.get_by_tag(key=prototype_key, category=_PROTOTYPE_TAG_CATEGORY)


def get_protparent_dict():
    """
    Get prototype parents.

    Returns:
        parent_dict (dict): A mapping {prototype_key: prototype} for all available prototypes.

    """
    return {prototype['prototype_key']: prototype for prototype in search_prototype()}


def list_prototypes(caller, key=None, tags=None, show_non_use=False, show_non_edit=True):
    """
    Collate a list of found prototypes based on search criteria and access.

    Args:
        caller (Account or Object): The object requesting the list.
        key (str, optional): Exact or partial prototype key to query for.
        tags (str or list, optional): Tag key or keys to query for.
        show_non_use (bool, optional): Show also prototypes the caller may not use.
        show_non_edit (bool, optional): Show also prototypes the caller may not edit.
    Returns:
        table (EvTable or None): An EvTable representation of the prototypes. None
            if no prototypes were found.

    """
    # this allows us to pass lists of empty strings
    tags = [tag for tag in make_iter(tags) if tag]

    # get prototypes for readonly and db-based prototypes
    prototypes = search_prototype(key, tags)

    # get use-permissions of readonly attributes (edit is always False)
    display_tuples = []
    for prototype in sorted(prototypes, key=lambda d: d.get('prototype_key', '')):
        lock_use = caller.locks.check_lockstring(
            caller, prototype.get('prototype_locks', ''), access_type='use')
        if not show_non_use and not lock_use:
            continue
        if prototype.get('prototype_key', '') in _MODULE_PROTOTYPES:
            lock_edit = False
        else:
            lock_edit = caller.locks.check_lockstring(
                caller, prototype.get('prototype_locks', ''), access_type='edit')
        if not show_non_edit and not lock_edit:
            continue
        ptags = []
        for ptag in prototype.get('prototype_tags', []):
            if is_iter(ptag):
                if len(ptag) > 1:
                    ptags.append("{} (category: {}".format(ptag[0], ptag[1]))
                else:
                    ptags.append(ptag[0])
            else:
                ptags.append(str(ptag))

        display_tuples.append(
            (prototype.get('prototype_key', '<unset>'),
             prototype.get('prototype_desc', '<unset>'),
             "{}/{}".format('Y' if lock_use else 'N', 'Y' if lock_edit else 'N'),
             ",".join(ptags)))

    if not display_tuples:
        return None

    table = []
    width = 78
    for i in range(len(display_tuples[0])):
        table.append([str(display_tuple[i]) for display_tuple in display_tuples])
    table = EvTable("Key", "Desc", "Use/Edit", "Tags", table=table, crop=True, width=width)
    table.reformat_column(0, width=22)
    table.reformat_column(1, width=29)
    table.reformat_column(2, width=11, align='c')
    table.reformat_column(3, width=16)
    return table


def prototype_to_str(prototype):
    """
    Format a prototype to a nice string representation.

    Args:
        prototype (dict): The prototype.
    """

    header = (
        "|cprototype key:|n {}, |ctags:|n {}, |clocks:|n {} \n"
        "|cdesc:|n {} \n|cprototype:|n ".format(
           prototype['prototype_key'],
           ", ".join(prototype['prototype_tags']),
           prototype['prototype_locks'],
           prototype['prototype_desc']))
    proto = ("{{\n  {} \n}}".format(
        "\n  ".join(
            "{!r}: {!r},".format(key, value) for key, value in
             sorted(prototype.items()) if key not in _PROTOTYPE_META_NAMES)).rstrip(","))
    return header + proto


# Spawner mechanism


def validate_prototype(prototype, protkey=None, protparents=None, _visited=None):
    """
    Run validation on a prototype, checking for inifinite regress.

    Args:
        prototype (dict): Prototype to validate.
        protkey (str, optional): The name of the prototype definition. If not given, the prototype
            dict needs to have the `prototype_key` field set.
        protpartents (dict, optional): The available prototype parent library. If
            note given this will be determined from settings/database.
        _visited (list, optional): This is an internal work array and should not be set manually.
    Raises:
        RuntimeError: If prototype has invalid structure.

    """
    if not protparents:
        protparents = get_protparent_dict()
    if _visited is None:
        _visited = []

    protkey = protkey and protkey.lower() or prototype.get('prototype_key', None)

    assert isinstance(prototype, dict)

    if id(prototype) in _visited:
        raise RuntimeError("%s has infinite nesting of prototypes." % protkey or prototype)

    _visited.append(id(prototype))
    protstrings = prototype.get("prototype")

    if protstrings:
        for protstring in make_iter(protstrings):
            protstring = protstring.lower()
            if protkey is not None and protstring == protkey:
                raise RuntimeError("%s tries to prototype itself." % protkey or prototype)
            protparent = protparents.get(protstring)
            if not protparent:
                raise RuntimeError(
                    "%s's prototype '%s' was not found." % (protkey or prototype, protstring))
            validate_prototype(protparent, protstring, protparents, _visited)


def _get_prototype(dic, prot, protparents):
    """
    Recursively traverse a prototype dictionary, including multiple
    inheritance. Use validate_prototype before this, we don't check
    for infinite recursion here.

    """
    if "prototype" in dic:
        # move backwards through the inheritance
        for prototype in make_iter(dic["prototype"]):
            # Build the prot dictionary in reverse order, overloading
            new_prot = _get_prototype(protparents.get(prototype.lower(), {}), prot, protparents)
            prot.update(new_prot)
    prot.update(dic)
    prot.pop("prototype", None)  # we don't need this anymore
    return prot


def _batch_create_object(*objparams):
    """
    This is a cut-down version of the create_object() function,
    optimized for speed. It does NOT check and convert various input
    so make sure the spawned Typeclass works before using this!

    Args:
        objsparams (tuple): Each paremter tuple will create one object instance using the parameters within.
            The parameters should be given in the following order:
                - `create_kwargs` (dict): For use as new_obj = `ObjectDB(**create_kwargs)`.
                - `permissions` (str): Permission string used with `new_obj.batch_add(permission)`.
                - `lockstring` (str): Lockstring used with `new_obj.locks.add(lockstring)`.
                - `aliases` (list): A list of alias strings for
                    adding with `new_object.aliases.batch_add(*aliases)`.
                - `nattributes` (list): list of tuples `(key, value)` to be loop-added to
                    add with `new_obj.nattributes.add(*tuple)`.
                - `attributes` (list): list of tuples `(key, value[,category[,lockstring]])` for
                    adding with `new_obj.attributes.batch_add(*attributes)`.
                - `tags` (list): list of tuples `(key, category)` for adding
                    with `new_obj.tags.batch_add(*tags)`.
                - `execs` (list): Code strings to execute together with the creation
                    of each object. They will be executed with `evennia` and `obj`
                        (the newly created object) available in the namespace. Execution
                        will happend after all other properties have been assigned and
                        is intended for calling custom handlers etc.

    Returns:
        objects (list): A list of created objects

    Notes:
        The `exec` list will execute arbitrary python code so don't allow this to be available to
        unprivileged users!

    """

    # bulk create all objects in one go

    # unfortunately this doesn't work since bulk_create doesn't creates pks;
    # the result would be duplicate objects at the next stage, so we comment
    # it out for now:
    #  dbobjs = _ObjectDB.objects.bulk_create(dbobjs)

    dbobjs = [ObjectDB(**objparam[0]) for objparam in objparams]
    objs = []
    for iobj, obj in enumerate(dbobjs):
        # call all setup hooks on each object
        objparam = objparams[iobj]
        # setup
        obj._createdict = {"permissions": make_iter(objparam[1]),
                           "locks": objparam[2],
                           "aliases": make_iter(objparam[3]),
                           "nattributes": objparam[4],
                           "attributes": objparam[5],
                           "tags": make_iter(objparam[6])}
        # this triggers all hooks
        obj.save()
        # run eventual extra code
        for code in objparam[7]:
            if code:
                exec(code, {}, {"evennia": evennia, "obj": obj})
        objs.append(obj)
    return objs


def spawn(*prototypes, **kwargs):
    """
    Spawn a number of prototyped objects.

    Args:
        prototypes (dict): Each argument should be a prototype
            dictionary.
    Kwargs:
        prototype_modules (str or list): A python-path to a prototype
            module, or a list of such paths. These will be used to build
            the global protparents dictionary accessible by the input
            prototypes. If not given, it will instead look for modules
            defined by settings.PROTOTYPE_MODULES.
        prototype_parents (dict): A dictionary holding a custom
            prototype-parent dictionary. Will overload same-named
            prototypes from prototype_modules.
        return_prototypes (bool): Only return a list of the
            prototype-parents (no object creation happens)

    Returns:
        object (Object): Spawned object.

    """
    # get available protparents
    protparents = get_protparent_dict()

    # overload module's protparents with specifically given protparents
    protparents.update(kwargs.get("prototype_parents", {}))
    for key, prototype in protparents.items():
        validate_prototype(prototype, key.lower(), protparents)

    if "return_prototypes" in kwargs:
        # only return the parents
        return copy.deepcopy(protparents)

    objsparams = []
    for prototype in prototypes:

        validate_prototype(prototype, None, protparents)
        prot = _get_prototype(prototype, {}, protparents)
        if not prot:
            continue

        # extract the keyword args we need to create the object itself. If we get a callable,
        # call that to get the value (don't catch errors)
        create_kwargs = {}
        # we must always add a key, so if not given we use a shortened md5 hash. There is a (small)
        # chance this is not unique but it should usually not be a problem.
        val = prot.pop("key", "Spawned-{}".format(
            hashlib.md5(str(time.time())).hexdigest()[:6]))
        create_kwargs["db_key"] = validate_spawn_value(val, str)

        val = prot.pop("location", None)
        create_kwargs["db_location"] = validate_spawn_value(val, _to_obj)

        val = prot.pop("home", settings.DEFAULT_HOME)
        create_kwargs["db_home"] = validate_spawn_value(val, _to_obj)

        val = prot.pop("destination", None)
        create_kwargs["db_destination"] = validate_spawn_value(val, _to_obj)

        val = prot.pop("typeclass", settings.BASE_OBJECT_TYPECLASS)
        create_kwargs["db_typeclass_path"] = validate_spawn_value(val, str)

        # extract calls to handlers
        val = prot.pop("permissions", [])
        permission_string = validate_spawn_value(val, make_iter)
        val = prot.pop("locks", "")
        lock_string = validate_spawn_value(val, str)
        val = prot.pop("aliases", [])
        alias_string = validate_spawn_value(val, make_iter)

        val = prot.pop("tags", [])
        tags = validate_spawn_value(val, make_iter)

        prototype_key = prototype.get('prototype_key', None)
        if prototype_key:
            # we make sure to add a tag identifying which prototype created this object
            tags.append((prototype_key, _PROTOTYPE_TAG_CATEGORY))

        val = prot.pop("exec", "")
        execs = validate_spawn_value(val, make_iter)

        # extract ndb assignments
        nattributes = dict((key.split("_", 1)[1], validate_spawn_value(val, _to_obj))
                           for key, val in prot.items() if key.startswith("ndb_"))

        # the rest are attributes
        val = prot.pop("attrs", [])
        attributes = validate_spawn_value(val, list)

        simple_attributes = []
        for key, value in ((key, value) for key, value in prot.items()
                           if not (key.startswith("ndb_"))):
            if is_iter(value) and len(value) > 1:
                # (value, category)
                simple_attributes.append((key,
                                          validate_spawn_value(value[0], _to_obj_or_any),
                                          validate_spawn_value(value[1], str)))
            else:
                simple_attributes.append((key,
                                          validate_spawn_value(value, _to_obj_or_any)))

        attributes = attributes + simple_attributes
        attributes = [tup for tup in attributes if not tup[0] in _NON_CREATE_KWARGS]

        # pack for call into _batch_create_object
        objsparams.append((create_kwargs, permission_string, lock_string,
                           alias_string, nattributes, attributes, tags, execs))

    return _batch_create_object(*objsparams)


# ------------------------------------------------------------
#
# OLC Prototype design menu
#
# ------------------------------------------------------------

# Helper functions

def _get_menu_prototype(caller):

    prototype = None
    if hasattr(caller.ndb._menutree, "olc_prototype"):
        prototype = caller.ndb._menutree.olc_prototype
    if not prototype:
        caller.ndb._menutree.olc_prototype = prototype = {}
        caller.ndb._menutree.olc_new = True
    return prototype


def _is_new_prototype(caller):
    return hasattr(caller.ndb._menutree, "olc_new")


def _set_menu_prototype(caller, field, value):
    prototype = _get_menu_prototype(caller)
    prototype[field] = value
    caller.ndb._menutree.olc_prototype = prototype


def _format_property(prop, required=False, prototype=None, cropper=None):

    if prototype is not None:
        prop = prototype.get(prop, '')

    out = prop
    if callable(prop):
        if hasattr(prop, '__name__'):
            out = "<{}>".format(prop.__name__)
        else:
            out = repr(prop)
    if is_iter(prop):
        out = ", ".join(str(pr) for pr in prop)
    if not out and required:
        out = "|rrequired"
    return " ({}|n)".format(cropper(out) if cropper else crop(out, _MENU_CROP_WIDTH))


def _set_property(caller, raw_string, **kwargs):
    """
    Update a property. To be called by the 'goto' option variable.

    Args:
        caller (Object, Account): The user of the wizard.
        raw_string (str): Input from user on given node - the new value to set.
    Kwargs:
        prop (str): Property name to edit with `raw_string`.
        processor (callable): Converts `raw_string` to a form suitable for saving.
        next_node (str): Where to redirect to after this has run.
    Returns:
        next_node (str): Next node to go to.

    """
    prop = kwargs.get("prop", "prototype_key")
    processor = kwargs.get("processor", None)
    next_node = kwargs.get("next_node", "node_index")

    propname_low = prop.strip().lower()

    if callable(processor):
        try:
            value = processor(raw_string)
        except Exception as err:
            caller.msg("Could not set {prop} to {value} ({err})".format(
                       prop=prop.replace("_", "-").capitalize(), value=raw_string, err=str(err)))
            # this means we'll re-run the current node.
            return None
    else:
        value = raw_string

    if not value:
        return next_node

    prototype = _get_menu_prototype(caller)

    # typeclass and prototype can't co-exist
    if propname_low == "typeclass":
        prototype.pop("prototype", None)
    if propname_low == "prototype":
        prototype.pop("typeclass", None)

    caller.ndb._menutree.olc_prototype = prototype

    caller.msg("Set {prop} to '{value}'.".format(prop, value=str(value)))

    return next_node


def _wizard_options(curr_node, prev_node, next_node, color="|W"):
    options = []
    if prev_node:
        options.append({"key": ("|wb|Wack", "b"),
                        "desc": "{color}({node})|n".format(
                            color=color, node=prev_node.replace("_", "-")),
                        "goto": "node_{}".format(prev_node)})
    if next_node:
        options.append({"key": ("|wf|Worward", "f"),
                        "desc": "{color}({node})|n".format(
                            color=color, node=next_node.replace("_", "-")),
                        "goto": "node_{}".format(next_node)})

    if "index" not in (prev_node, next_node):
        options.append({"key": ("|wi|Wndex", "i"),
                        "goto": "node_index"})

    if curr_node:
        options.append({"key": ("|wv|Walidate prototype", "v"),
                        "goto": ("node_validate_prototype", {"back": curr_node})})

    return options


def _path_cropper(pythonpath):
    "Crop path to only the last component"
    return pythonpath.split('.')[-1]


# Menu nodes

def node_index(caller):
    prototype = _get_menu_prototype(caller)

    text = ("|c --- Prototype wizard --- |n\n\n"
            "Define the |yproperties|n of the prototype. All prototype values can be "
            "over-ridden at the time of spawning an instance of the prototype, but some are "
            "required.\n\n'|wMeta'-properties|n are not used in the prototype itself but are used "
            "to organize and list prototypes. The 'Meta-Key' uniquely identifies the prototype "
            "and allows you to edit an existing prototype or save a new one for use by you or "
            "others later.\n\n(make choice; q to abort. If unsure, start from 1.)")

    options = []
    options.append(
        {"desc": "|WPrototype-Key|n|n{}".format(_format_property("Key", True, prototype, None)),
         "goto": "node_prototype_key"})
    for key in ('Prototype', 'Typeclass', 'Key', 'Aliases', 'Attrs', 'Tags', 'Locks',
                'Permissions', 'Location', 'Home', 'Destination'):
        required = False
        cropper = None
        if key in ("Prototype", "Typeclass"):
            required = "prototype" not in prototype and "typeclass" not in prototype
        if key == 'Typeclass':
            cropper = _path_cropper
        options.append(
            {"desc": "|w{}|n{}".format(
                key, _format_property(key, required, prototype, cropper=cropper)),
             "goto": "node_{}".format(key.lower())})
    required = False
    for key in ('Desc', 'Tags', 'Locks'):
        options.append(
            {"desc": "|WPrototype-{}|n|n{}".format(key, _format_property(key, required, prototype, None)),
             "goto": "node_prototype_{}".format(key.lower())})

    return text, options


def node_validate_prototype(caller, raw_string, **kwargs):
    prototype = _get_menu_prototype(caller)

    txt = prototype_to_str(prototype)
    errors = "\n\n|g No validation errors found.|n (but errors could still happen at spawn-time)"
    try:
        # validate, don't spawn
        spawn(prototype, return_prototypes=True)
    except RuntimeError as err:
        errors = "\n\n|rError: {}|n".format(err)
    text = (txt + errors)

    options = _wizard_options(None, kwargs.get("back"), None)

    return text, options


def _check_prototype_key(caller, key):
    old_prototype = search_prototype(key)
    olc_new = _is_new_prototype(caller)
    key = key.strip().lower()
    if old_prototype:
        # we are starting a new prototype that matches an existing
        if not caller.locks.check_lockstring(
                caller, old_prototype['prototype_locks'], access_type='edit'):
            # return to the node_prototype_key to try another key
            caller.msg("Prototype '{key}' already exists and you don't "
                       "have permission to edit it.".format(key=key))
            return "node_prototype_key"
        elif olc_new:
            # we are selecting an existing prototype to edit. Reset to index.
            del caller.ndb._menutree.olc_new
            caller.ndb._menutree.olc_prototype = old_prototype
            caller.msg("Prototype already exists. Reloading.")
            return "node_index"

    return _set_property(caller, key, prop='prototype_key', next_node="node_prototype")


def node_prototype_key(caller):
    prototype = _get_menu_prototype(caller)
    text = ["The prototype name, or |wMeta-Key|n, uniquely identifies the prototype. "
            "It is used to find and use the prototype to spawn new entities. "
            "It is not case sensitive."]
    old_key = prototype.get('prototype_key', None)
    if old_key:
        text.append("Current key is '|w{key}|n'".format(key=old_key))
    else:
        text.append("The key is currently unset.")
    text.append("Enter text or make a choice (q for quit)")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_key", "index", "prototype")
    options.append({"key": "_default",
                    "goto": _check_prototype_key})
    return text, options


def _all_prototypes(caller):
    return [prototype["prototype_key"]
            for prototype in search_prototype() if "prototype_key" in prototype]


def _prototype_examine(caller, prototype_name):
    prototypes = search_prototype(key=prototype_name)
    if prototypes:
        caller.msg(prototype_to_str(prototypes[0]))
    caller.msg("Prototype not registered.")
    return None


def _prototype_select(caller, prototype):
    ret = _set_property(caller, prototype, prop="prototype", processor=str, next_node="node_key")
    caller.msg("Selected prototype |y{}|n. Removed any set typeclass parent.".format(prototype))
    return ret


@list_node(_all_prototypes, _prototype_select)
def node_prototype(caller):
    prototype = _get_menu_prototype(caller)

    prot_parent_key = prototype.get('prototype')

    text = ["Set the prototype's |yParent Prototype|n. If this is unset, Typeclass will be used."]
    if prot_parent_key:
        prot_parent = search_prototype(prot_parent_key)
        if prot_parent:
            text.append("Current parent prototype is {}:\n{}".format(prototype_to_str(prot_parent)))
        else:
            text.append("Current parent prototype |r{prototype}|n "
                        "does not appear to exist.".format(prot_parent_key))
    else:
        text.append("Parent prototype is not set")
    text = "\n\n".join(text)
    options = _wizard_options("prototype", "prototype_key", "typeclass", color="|W")
    options.append({"key": "_default",
                    "goto": _prototype_examine})

    return text, options


def _all_typeclasses(caller):
    return list(sorted(get_all_typeclasses().keys()))


def _typeclass_examine(caller, typeclass_path):
    if typeclass_path is None:
        # this means we are exiting the listing
        return "node_key"

    typeclass = get_all_typeclasses().get(typeclass_path)
    if typeclass:
        docstr = []
        for line in typeclass.__doc__.split("\n"):
            if line.strip():
                docstr.append(line)
            elif docstr:
                break
        docstr = '\n'.join(docstr) if docstr else "<empty>"
        txt = "Typeclass |y{typeclass_path}|n; First paragraph of docstring:\n\n{docstring}".format(
                typeclass_path=typeclass_path, docstring=docstr)
    else:
        txt = "This is typeclass |y{}|n.".format(typeclass)
    caller.msg(txt)
    return None


def _typeclass_select(caller, typeclass):
    ret = _set_property(caller, typeclass, prop='typeclass', processor=str, next_node="node_key")
    caller.msg("Selected typeclass |y{}|n. Removed any set prototype parent.".format(typeclass))
    return ret


@list_node(_all_typeclasses, _typeclass_select)
def node_typeclass(caller):
    prototype = _get_menu_prototype(caller)
    typeclass = prototype.get("typeclass")

    text = ["Set the typeclass's parent |yTypeclass|n."]
    if typeclass:
        text.append("Current typeclass is |y{typeclass}|n.".format(typeclass=typeclass))
    else:
        text.append("Using default typeclass {typeclass}.".format(
            typeclass=settings.BASE_OBJECT_TYPECLASS))
    text = "\n\n".join(text)
    options = _wizard_options("typeclass", "prototype", "key", color="|W")
    options.append({"key": "_default",
                    "goto": _typeclass_examine})
    return text, options


def node_key(caller):
    prototype = _get_menu_prototype(caller)
    key = prototype.get("key")

    text = ["Set the prototype's |yKey|n. This will retain case sensitivity."]
    if key:
        text.append("Current key value is '|y{key}|n'.".format(key=key))
    else:
        text.append("Key is currently unset.")
    text = "\n\n".join(text)
    options = _wizard_options("key", "typeclass", "aliases")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="key",
                                  processor=lambda s: s.strip(),
                                  next_node="node_aliases"))})
    return text, options


def node_aliases(caller):
    prototype = _get_menu_prototype(caller)
    aliases = prototype.get("aliases")

    text = ["Set the prototype's |yAliases|n. Separate multiple aliases with commas. "
            "ill retain case sensitivity."]
    if aliases:
        text.append("Current aliases are '|y{aliases}|n'.".format(aliases=aliases))
    else:
        text.append("No aliases are set.")
    text = "\n\n".join(text)
    options = _wizard_options("aliases", "key", "attrs")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="aliases",
                                  processor=lambda s: [part.strip() for part in s.split(",")],
                                  next_node="node_attrs"))})
    return text, options


def _caller_attrs(caller):
    prototype = _get_menu_prototype(caller)
    attrs = prototype.get("attrs", [])
    return attrs


def _attrparse(caller, attr_string):
    "attr is entering on the form 'attr = value'"

    if '=' in attr_string:
        attrname, value = (part.strip() for part in attr_string.split('=', 1))
        attrname = attrname.lower()
    if attrname:
        try:
            value = literal_eval(value)
        except SyntaxError:
            caller.msg(_MENU_ATTR_LITERAL_EVAL_ERROR)
        else:
            return attrname, value
    else:
        return None, None


def _add_attr(caller, attr_string, **kwargs):
    attrname, value = _attrparse(caller, attr_string)
    if attrname:
        prot = _get_menu_prototype(caller)
        prot['attrs'][attrname] = value
        _set_menu_prototype(caller, "prototype", prot)
        text = "Added"
    else:
        text = "Attribute must be given as 'attrname = <value>' where <value> uses valid Python."
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_attr(caller, attrname, new_value, **kwargs):
    attrname, value = _attrparse("{}={}".format(caller, attrname, new_value))
    if attrname:
        prot = _get_menu_prototype(caller)
        prot['attrs'][attrname] = value
        text = "Edited Attribute {} = {}".format(attrname, value)
    else:
        text = "Attribute value must be valid Python."
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _examine_attr(caller, selection):
    prot = _get_menu_prototype(caller)
    value = prot['attrs'][selection]
    return "Attribute {} = {}".format(selection, value)


@list_node(_caller_attrs)
def node_attrs(caller):
    prot = _get_menu_prototype(caller)
    attrs = prot.get("attrs")

    text = ["Set the prototype's |yAttributes|n. Separate multiple attrs with commas. "
            "Will retain case sensitivity."]
    if attrs:
        text.append("Current attrs are '|y{attrs}|n'.".format(attrs=attrs))
    else:
        text.append("No attrs are set.")
    text = "\n\n".join(text)
    options = _wizard_options("attrs", "aliases", "tags")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="attrs",
                                  processor=lambda s: [part.strip() for part in s.split(",")],
                                  next_node="node_tags"))})
    return text, options


def _caller_tags(caller):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get("tags")
    return tags


def _add_tag(caller, tag, **kwargs):
    tag = tag.strip().lower()
    prototype = _get_menu_prototype(caller)
    tags = prototype.get('tags', [])
    if tags:
        if tag not in tags:
            tags.append(tag)
    else:
        tags = [tag]
    prot['tags'] = tags
    _set_menu_prototype(caller, "prototype", prot)
    text = kwargs.get("text")
    if not text:
        text = "Added tag {}. (return to continue)".format(tag)
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_tag(caller, old_tag, new_tag, **kwargs):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get('tags', [])

    old_tag = old_tag.strip().lower()
    new_tag = new_tag.strip().lower()
    tags[tags.index(old_tag)] = new_tag
    prototype['tags'] = tags
    _set_menu_prototype(caller, 'prototype', prototype)

    text = kwargs.get('text')
    if not text:
        text = "Changed tag {} to {}.".format(old_tag, new_tag)
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


@list_node(_caller_tags)
def node_tags(caller):
    text = "Set the prototype's |yTags|n."
    options = _wizard_options("tags", "attrs", "locks")
    return text, options


def node_locks(caller):
    prototype = _get_menu_prototype(caller)
    locks = prototype.get("locks")

    text = ["Set the prototype's |yLock string|n. Separate multiple locks with semi-colons. "
            "Will retain case sensitivity."]
    if locks:
        text.append("Current locks are '|y{locks}|n'.".format(locks=locks))
    else:
        text.append("No locks are set.")
    text = "\n\n".join(text)
    options = _wizard_options("locks", "tags", "permissions")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="locks",
                                  processor=lambda s: s.strip(),
                                  next_node="node_permissions"))})
    return text, options


def node_permissions(caller):
    prototype = _get_menu_prototype(caller)
    permissions = prototype.get("permissions")

    text = ["Set the prototype's |yPermissions|n. Separate multiple permissions with commas. "
            "Will retain case sensitivity."]
    if permissions:
        text.append("Current permissions are '|y{permissions}|n'.".format(permissions=permissions))
    else:
        text.append("No permissions are set.")
    text = "\n\n".join(text)
    options = _wizard_options("permissions", "destination", "location")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="permissions",
                                  processor=lambda s: [part.strip() for part in s.split(",")],
                                  next_node="node_location"))})
    return text, options


def node_location(caller):
    prototype = _get_menu_prototype(caller)
    location = prototype.get("location")

    text = ["Set the prototype's |yLocation|n"]
    if location:
        text.append("Current location is |y{location}|n.".format(location=location))
    else:
        text.append("Default location is {}'s inventory.".format(caller))
    text = "\n\n".join(text)
    options = _wizard_options("location", "permissions", "home")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="location",
                                  processor=lambda s: s.strip(),
                                  next_node="node_home"))})
    return text, options


def node_home(caller):
    prototype = _get_menu_prototype(caller)
    home = prototype.get("home")

    text = ["Set the prototype's |yHome location|n"]
    if home:
        text.append("Current home location is |y{home}|n.".format(home=home))
    else:
        text.append("Default home location (|y{home}|n) used.".format(home=settings.DEFAULT_HOME))
    text = "\n\n".join(text)
    options = _wizard_options("home", "aliases", "destination")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="home",
                                  processor=lambda s: s.strip(),
                                  next_node="node_destination"))})
    return text, options


def node_destination(caller):
    prototype = _get_menu_prototype(caller)
    dest = prototype.get("dest")

    text = ["Set the prototype's |yDestination|n. This is usually only used for Exits."]
    if dest:
        text.append("Current destination is |y{dest}|n.".format(dest=dest))
    else:
        text.append("No destination is set (default).")
    text = "\n\n".join(text)
    options = _wizard_options("destination", "home", "prototype_desc")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="dest",
                                  processor=lambda s: s.strip(),
                                  next_node="node_prototype_desc"))})
    return text, options


def node_prototype_desc(caller):

    prototype = _get_menu_prototype(caller)
    text = ["The |wMeta-Description|n briefly describes the prototype for viewing in listings."]
    desc = prototype.get("prototype_desc", None)

    if desc:
        text.append("The current meta desc is:\n\"|w{desc}|n\"".format(desc=desc))
    else:
        text.append("Description is currently unset.")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_desc", "prototype_key", "prototype_tags")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop='prototype_desc',
                                  processor=lambda s: s.strip(),
                                  next_node="node_prototype_tags"))})

    return text, options


def node_prototype_tags(caller):
    prototype = _get_menu_prototype(caller)
    text = ["|wMeta-Tags|n can be used to classify and find prototypes. Tags are case-insensitive. "
            "Separate multiple by tags by commas."]
    tags = prototype.get('prototype_tags', [])

    if tags:
        text.append("The current tags are:\n|w{tags}|n".format(tags=tags))
    else:
        text.append("No tags are currently set.")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_tags", "prototype_desc", "prototype_locks")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="prototype_tags",
                                  processor=lambda s: [
                                    str(part.strip().lower()) for part in s.split(",")],
                                  next_node="node_prototype_locks"))})
    return text, options


def node_prototype_locks(caller):
    prototype = _get_menu_prototype(caller)
    text = ["Set |wMeta-Locks|n on the prototype. There are two valid lock types: "
            "'edit' (who can edit the prototype) and 'use' (who can apply the prototype)\n"
            "(If you are unsure, leave as default.)"]
    locks = prototype.get('prototype_locks', '')
    if locks:
        text.append("Current lock is |w'{lockstring}'|n".format(lockstring=locks))
    else:
        text.append("Lock unset - if not changed the default lockstring will be set as\n"
                    "   |w'use:all(); edit:id({dbref}) or perm(Admin)'|n".format(dbref=caller.id))
    text = "\n\n".join(text)
    options = _wizard_options("prototype_locks", "prototype_tags", "index")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="prototype_locks",
                                  processor=lambda s: s.strip().lower(),
                                  next_node="node_index"))})
    return text, options


class OLCMenu(EvMenu):
    """
    A custom EvMenu with a different formatting for the options.

    """
    def options_formatter(self, optionlist):
        """
        Split the options into two blocks - olc options and normal options

        """
        olc_keys = ("index", "forward", "back", "previous", "next", "validate prototype")
        olc_options = []
        other_options = []
        for key, desc in optionlist:
            raw_key = strip_ansi(key)
            if raw_key in olc_keys:
                desc = " {}".format(desc) if desc else ""
                olc_options.append("|lc{}|lt{}|le{}".format(raw_key, key, desc))
            else:
                other_options.append((key, desc))

        olc_options = " | ".join(olc_options) + " | " + "|wq|Wuit" if olc_options else ""
        other_options = super(OLCMenu, self).options_formatter(other_options)
        sep = "\n\n" if olc_options and other_options else ""

        return "{}{}{}".format(olc_options, sep, other_options)


def start_olc(caller, session=None, prototype=None):
    """
    Start menu-driven olc system for prototypes.

    Args:
        caller (Object or Account): The entity starting the menu.
        session (Session, optional): The individual session to get data.
        prototype (dict, optional): Given when editing an existing
            prototype rather than creating a new one.

    """
    menudata = {"node_index": node_index,
                "node_validate_prototype": node_validate_prototype,
                "node_prototype_key": node_prototype_key,
                "node_prototype": node_prototype,
                "node_typeclass": node_typeclass,
                "node_key": node_key,
                "node_aliases": node_aliases,
                "node_attrs": node_attrs,
                "node_tags": node_tags,
                "node_locks": node_locks,
                "node_permissions": node_permissions,
                "node_location": node_location,
                "node_home": node_home,
                "node_destination": node_destination,
                "node_prototype_desc": node_prototype_desc,
                "node_prototype_tags": node_prototype_tags,
                "node_prototype_locks": node_prototype_locks,
                }
    OLCMenu(caller, menudata, startnode='node_index', session=session, olc_prototype=prototype)


# Testing

if __name__ == "__main__":
    protparents = {
        "NOBODY": {},
        # "INFINITE" : {
        #     "prototype":"INFINITE"
        # },
        "GOBLIN": {
            "key": "goblin grunt",
            "health": lambda: randint(20, 30),
            "resists": ["cold", "poison"],
            "attacks": ["fists"],
            "weaknesses": ["fire", "light"]
        },
        "GOBLIN_WIZARD": {
            "prototype": "GOBLIN",
            "key": "goblin wizard",
            "spells": ["fire ball", "lighting bolt"]
        },
        "GOBLIN_ARCHER": {
            "prototype": "GOBLIN",
            "key": "goblin archer",
            "attacks": ["short bow"]
        },
        "ARCHWIZARD": {
            "attacks": ["archwizard staff"],
        },
        "GOBLIN_ARCHWIZARD": {
            "key": "goblin archwizard",
            "prototype": ("GOBLIN_WIZARD", "ARCHWIZARD")
        }
    }
    # test
    print([o.key for o in spawn(protparents["GOBLIN"],
                                protparents["GOBLIN_ARCHWIZARD"],
                                prototype_parents=protparents)])
