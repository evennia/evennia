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
    prototype - string parent prototype
    key - string, the main object identifier
    typeclass - string, if not set, will use `settings.BASE_OBJECT_TYPECLASS`
    location - this should be a valid object or #dbref
    home - valid object or #dbref
    destination - only valid for exits (object or dbref)

    permissions - string or list of permission strings
    locks - a lock-string
    aliases - string or list of strings
    exec - this is a string of python code to execute or a list of such codes.
        This can be used e.g. to trigger custom handlers on the object. The
        execution namespace contains 'evennia' for the library and 'obj'
    tags - string or list of strings or tuples `(tagstr, category)`. Plain
        strings will be result in tags with no category (default tags).
    attrs - tuple or list of tuples of Attributes to add. This form allows
    more complex Attributes to be set. Tuples at least specify `(key, value)`
        but can also specify up to `(key, value, category, lockstring)`. If
        you want to specify a lockstring but not a category, set the category
        to `None`.
    ndb_<name> - value of a nattribute (ndb_ is stripped)
    other - any other name is interpreted as the key of an Attribute with
        its value. Such Attributes have no categories.

Each value can also be a callable that takes no arguments. It should
return the value to enter into the field and will be called every time
the prototype is used to spawn an object. Note, if you want to store
a callable in an Attribute, embed it in a tuple to the `args` keyword.

By specifying the "prototype" key, the prototype becomes a child of
that prototype, inheritng all prototype slots it does not explicitly
define itself, while overloading those that it does specify.

```python
GOBLIN_WIZARD = {
 "prototype": GOBLIN,
 "key": "goblin wizard",
 "spells": ["fire ball", "lighting bolt"]
 }

GOBLIN_ARCHER = {
 "prototype": GOBLIN,
 "key": "goblin archer",
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
from django.conf import settings
from random import randint
import evennia
from evennia.objects.models import ObjectDB
from evennia.utils.utils import make_iter, all_from_module, dbid_to_obj

from collections import namedtuple, defaultdict
from evennia.scripts.scripts import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.evtable import EvTable


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_READONLY_PROTOTYPES = {}
_READONLY_PROTOTYPE_MODULES = {}


class PermissionError(RuntimeError):
    pass

# storage of meta info about the prototype
MetaProto = namedtuple('MetaProto', ['key', 'desc', 'locks', 'tags', 'prototype'])

for mod in settings.PROTOTYPE_MODULES:
    # to remove a default prototype, override it with an empty dict.
    # internally we store as (key, desc, locks, tags, prototype_dict)
    prots = [(key, prot) for key, prot in all_from_module(mod).items()
             if prot and isinstance(prot, dict)]
    _READONLY_PROTOTYPES.update(
        {key.lower(): MetaProto(
            key.lower(),
            prot['prototype_desc'] if 'prototype_desc' in prot else mod,
            prot['prototype_lock'] if 'prototype_lock' in prot else "use:all()",
            set(make_iter(
                prot['prototype_tags']) if 'prototype_tags' in prot else ["base-prototype"]),
            prot)
         for key, prot in prots})
    _READONLY_PROTOTYPE_MODULES.update({tup[0]: mod for tup in prots})

# Prototype storage mechanisms


class PersistentPrototype(DefaultScript):
    """
    This stores a single prototype
    """
    def at_script_creation(self):
        self.key = "empty prototype"
        self.desc = "A prototype"


def build_metaproto(key, desc, locks, tags, prototype):
    """
    Create a metaproto from combinant parts.

    """
    return MetaProto(key, desc, make_iter(locks), tags, dict(prototype))


def store_prototype(caller, key, prototype, desc="", tags=None, locks="", delete=False):
    """
    Store a prototype persistently.

    Args:
        caller (Account or Object): Caller aiming to store prototype. At this point
            the caller should have permission to 'add' new prototypes, but to edit
            an existing prototype, the 'edit' lock must be passed on that prototype.
        key (str): Name of prototype to store.
        prototype (dict): Prototype dict.
        desc (str, optional): Description of prototype, to use in listing.
        tags (list, optional): Tag-strings to apply to prototype. These are always
            applied with the 'persistent_prototype' category.
        locks (str, optional): Locks to apply to this prototype. Used locks
            are 'use' and 'edit'
        delete (bool, optional): Delete an existing prototype identified by 'key'.
            This requires `caller` to pass the 'edit' lock of the prototype.
    Returns:
        stored (StoredPrototype or None): The resulting prototype (new or edited),
            or None if deleting.
    Raises:
        PermissionError: If edit lock was not passed by caller.


    """
    key_orig = key
    key = key.lower()
    locks = locks if locks else "use:all();edit:id({}) or perm(Admin)".format(caller.id)
    tags = [(tag, "persistent_prototype") for tag in make_iter(tags)]

    if key in _READONLY_PROTOTYPES:
        mod = _READONLY_PROTOTYPE_MODULES.get(key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(key_orig, mod))

    stored_prototype = PersistentPrototype.objects.filter(db_key=key)

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
            PersistentPrototype, key=key, desc=desc, persistent=True,
            locks=locks, tags=tags, attributes=[("prototype", prototype)])
    return stored_prototype


def delete_prototype(caller, key):
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
    return store_prototype(caller, key, None, delete=True)


def search_persistent_prototype(key=None, tags=None, return_metaprotos=False):
    """
    Find persistent (database-stored) prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'persistent_protototype'
            tag category.
        return_metaproto (bool): Return results as metaprotos.
    Return:
        matches (queryset or list): All found PersistentPrototypes. If `return_metaprotos`
            is set, return a list of MetaProtos.

    Note:
        This will not include read-only prototypes defined in modules.

    """
    if tags:
        # exact match on tag(s)
        tags = make_iter(tags)
        tag_categories = ["persistent_prototype" for _ in tags]
        matches = PersistentPrototype.objects.get_by_tag(tags, tag_categories)
    else:
        matches = PersistentPrototype.objects.all()
    if key:
        # exact or partial match on key
        matches = matches.filter(db_key=key) or matches.filter(db_key__icontains=key)
    if return_metaprotos:
        return [build_metaproto(match.key, match.desc, match.locks.all(),
                                match.tags.get(category="persistent_prototype", return_list=True),
                                match.attributes.get("prototype"))
                for match in matches]
    return matches


def search_readonly_prototype(key=None, tags=None):
    """
    Find read-only prototypes, defined in modules.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key to query for.

    Return:
        matches (list): List of MetaProto tuples that includes
            prototype metadata,

    """
    matches = {}
    if tags:
        # use tags to limit selection
        tagset = set(tags)
        matches = {key: metaproto for key, metaproto in _READONLY_PROTOTYPES.items()
                   if tagset.intersection(metaproto.tags)}
    else:
        matches = _READONLY_PROTOTYPES

    if key:
        if key in matches:
            # exact match
            return [matches[key]]
        else:
            # fuzzy matching
            return [metaproto for pkey, metaproto in matches.items() if key in pkey]
    else:
        return [match for match in matches.values()]


def search_prototype(key=None, tags=None, return_meta=True):
    """
    Find prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'persistent_protototype'
            tag category.
        return_meta (bool): If False, only return prototype dicts, if True
            return MetaProto namedtuples including prototype meta info

    Return:
        matches (list): All found prototype dicts or MetaProtos

    Note:
        The available prototypes is a combination of those supplied in
        PROTOTYPE_MODULES and those stored from in-game. For the latter,
        this will use the tags to make a subselection before attempting
        to match on the key. So if key/tags don't match up nothing will
        be found.

    """
    readonly_prototypes = search_readonly_prototype(key, tags)
    persistent_prototypes = search_persistent_prototype(key, tags, return_metaprotos=True)

    matches = persistent_prototypes + readonly_prototypes
    if len(matches) > 1 and key:
        key = key.lower()
        # avoid duplicates if an exact match exist between the two types
        filter_matches = [mta for mta in matches if mta.key == key]
        if len(filter_matches) < len(matches):
            matches = filter_matches

    if not return_meta:
        matches = [mta.prototype for mta in matches]

    return matches


def get_protparents():
    """
    Get prototype parents. These are a combination of meta-key and prototype-dict and are used when
    a prototype refers to another parent-prototype.

    """
    # get all prototypes
    metaprotos = search_prototype(return_meta=True)
    # organize by key
    return {metaproto.key: metaproto.prototype for metaproto in metaprotos}


def list_prototypes(caller, key=None, tags=None, show_non_use=False,
                    show_non_edit=True, sort_tree=True):
    """
    Collate a list of found prototypes based on search criteria and access.

    Args:
        caller (Account or Object): The object requesting the list.
        key (str, optional): Exact or partial key to query for.
        tags (str or list, optional): Tag key or keys to query for.
        show_non_use (bool, optional): Show also prototypes the caller may not use.
        show_non_edit (bool, optional): Show also prototypes the caller may not edit.
        sort_tree (bool, optional): Order prototypes by inheritance tree.
    Returns:
        table (EvTable or None): An EvTable representation of the prototypes. None
            if no prototypes were found.

    """
    # get metaprotos for readonly and db-based prototypes
    metaprotos = search_readonly_prototype(key, tags)
    metaprotos += search_persistent_prototype(key, tags, return_metaprotos=True)

    # get use-permissions of readonly attributes (edit is always False)
    prototypes = [
        (metaproto.key,
         metaproto.desc,
         ("{}/N".format('Y'
          if caller.locks.check_lockstring(caller, metaproto.locks, access_type='use') else 'N')),
         ",".join(metaproto.tags))
        for metaproto in sorted(metaprotos, key=lambda o: o.key)]

    if not prototypes:
        return None

    if not show_non_use:
        prototypes = [metaproto for metaproto in prototypes if metaproto[2].split("/", 1)[0] == 'Y']
    if not show_non_edit:
        prototypes = [metaproto for metaproto in prototypes if metaproto[2].split("/", 1)[1] == 'Y']

    if not prototypes:
        return None

    table = []
    for i in range(len(prototypes[0])):
        table.append([str(metaproto[i]) for metaproto in prototypes])
    table = EvTable("Key", "Desc", "Use/Edit", "Tags", table=table, crop=True, width=78)
    table.reformat_column(0, width=28)
    table.reformat_column(1, width=40)
    table.reformat_column(2, width=11, align='r')
    table.reformat_column(3, width=20)
    return table

# Spawner mechanism


def _handle_dbref(inp):
    return dbid_to_obj(inp, ObjectDB)


def validate_prototype(prototype, protkey=None, protparents=None, _visited=None):
    """
    Run validation on a prototype, checking for inifinite regress.

    Args:
        prototype (dict): Prototype to validate.
        protkey (str, optional): The name of the prototype definition, if any.
        protpartents (dict, optional): The available prototype parent library. If
            note given this will be determined from settings/database.
        _visited (list, optional): This is an internal work array and should not be set manually.
    Raises:
        RuntimeError: If prototype has invalid structure.

    """
    if not protparents:
        protparents = get_protparents()
    if _visited is None:
        _visited = []
    protkey = protkey.lower() if protkey is not None else None

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
        objsparams (tuple): Parameters for the respective creation/add
            handlers in the following order:
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
            for the respective creation/add handlers in the following
            order: (create_kwargs, permissions, locks, aliases, nattributes,
            attributes, tags, execs)

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

    """
    # get available protparents
    protparents = get_protparents()

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
        keyval = prot.pop("key", "Spawned Object %06i" % randint(1, 100000))
        create_kwargs["db_key"] = keyval() if callable(keyval) else keyval

        locval = prot.pop("location", None)
        create_kwargs["db_location"] = locval() if callable(locval) else _handle_dbref(locval)

        homval = prot.pop("home", settings.DEFAULT_HOME)
        create_kwargs["db_home"] = homval() if callable(homval) else _handle_dbref(homval)

        destval = prot.pop("destination", None)
        create_kwargs["db_destination"] = destval() if callable(destval) else _handle_dbref(destval)

        typval = prot.pop("typeclass", settings.BASE_OBJECT_TYPECLASS)
        create_kwargs["db_typeclass_path"] = typval() if callable(typval) else typval

        # extract calls to handlers
        permval = prot.pop("permissions", [])
        permission_string = permval() if callable(permval) else permval
        lockval = prot.pop("locks", "")
        lock_string = lockval() if callable(lockval) else lockval
        aliasval = prot.pop("aliases", "")
        alias_string = aliasval() if callable(aliasval) else aliasval
        tagval = prot.pop("tags", [])
        tags = tagval() if callable(tagval) else tagval
        attrval = prot.pop("attrs", [])
        attributes = attrval() if callable(tagval) else attrval

        exval = prot.pop("exec", "")
        execs = make_iter(exval() if callable(exval) else exval)

        # extract ndb assignments
        nattributes = dict((key.split("_", 1)[1], value() if callable(value) else value)
                           for key, value in prot.items() if key.startswith("ndb_"))

        # the rest are attributes
        simple_attributes = [(key, value()) if callable(value) else (key, value)
                             for key, value in prot.items() if not key.startswith("ndb_")]
        attributes = attributes + simple_attributes
        attributes = [tup for tup in attributes if not tup[0] in _CREATE_OBJECT_KWARGS]

        # pack for call into _batch_create_object
        objsparams.append((create_kwargs, permission_string, lock_string,
                           alias_string, nattributes, attributes, tags, execs))

    return _batch_create_object(*objsparams)



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
