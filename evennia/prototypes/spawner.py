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
 "attrs": [("weapon", "sword")]
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

    prototype_parent (str, tuple or callable, optional): name (prototype_key) of eventual parent prototype, or
        a list of parents, for multiple left-to-right inheritance.
    prototype: Deprecated. Same meaning as 'parent'.
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
 "prototype_parent": GOBLIN,
 "key": "goblin wizard",
 "spells": ["fire ball", "lighting bolt"]
 }

GOBLIN_ARCHER = {
 "prototype_parent": GOBLIN,
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
 "prototype_parent": (GOBLIN_WIZARD, ARCHWIZARD),
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

from django.conf import settings
import evennia
from evennia.objects.models import ObjectDB
from evennia.utils.utils import make_iter, is_iter
from evennia.prototypes import prototypes as protlib
from evennia.prototypes.prototypes import (
    value_to_obj, value_to_obj_or_any, init_spawn_value, _PROTOTYPE_TAG_CATEGORY)


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")
_NON_CREATE_KWARGS = _CREATE_OBJECT_KWARGS + _PROTOTYPE_META_NAMES


# Helper

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


# obj-related prototype functions

def prototype_from_object(obj):
    """
    Guess a minimal prototype from an existing object.

    Args:
        obj (Object): An object to analyze.

    Returns:
        prototype (dict): A prototype estimating the current state of the object.

    """
    # first, check if this object already has a prototype

    prot = obj.tags.get(category=_PROTOTYPE_TAG_CATEGORY, return_list=True)
    if prot:
        prot = protlib.search_prototype(prot[0])
    if not prot or len(prot) > 1:
        # no unambiguous prototype found - build new prototype
        prot = {}
        prot['prototype_key'] = "From-Object-{}-{}".format(
                obj.key, hashlib.md5(str(time.time())).hexdigest()[:7])
        prot['prototype_desc'] = "Built from {}".format(str(obj))
        prot['prototype_locks'] = "spawn:all();edit:all()"
        prot['prototype_tags'] = []

    prot['key'] = obj.db_key or hashlib.md5(str(time.time())).hexdigest()[:6]
    prot['typeclass'] = obj.db_typeclass_path

    location = obj.db_location
    if location:
        prot['location'] = location
    home = obj.db_home
    if home:
        prot['home'] = home
    destination = obj.db_destination
    if destination:
        prot['destination'] = destination
    locks = obj.locks.all()
    if locks:
        prot['locks'] = locks
    perms = obj.permissions.get()
    if perms:
        prot['permissions'] = perms
    aliases = obj.aliases.get()
    if aliases:
        prot['aliases'] = aliases
    tags = [(tag.db_key, tag.db_category, tag.db_data)
            for tag in obj.tags.get(return_tagobj=True, return_list=True) if tag]
    if tags:
        prot['tags'] = tags
    attrs = [(attr.key, attr.value, attr.category, attr.locks.all())
             for attr in obj.attributes.get(return_obj=True, return_list=True) if attr]
    if attrs:
        prot['attrs'] = attrs

    return prot


def prototype_diff_from_object(prototype, obj):
    """
    Get a simple diff for a prototype compared to an object which may or may not already have a
    prototype (or has one but changed locally). For more complex migratations a manual diff may be
    needed.

    Args:
        prototype (dict): Prototype.
        obj (Object): Object to

    Returns:
        diff (dict): Mapping for every prototype key: {"keyname": "REMOVE|UPDATE|KEEP", ...}

    """
    prot1 = prototype
    prot2 = prototype_from_object(obj)

    diff = {}
    for key, value in prot1.items():
        diff[key] = "KEEP"
        if key in prot2:
            if callable(prot2[key]) or value != prot2[key]:
                if key in ('attrs', 'tags', 'permissions', 'locks', 'aliases'):
                    diff[key] = 'REPLACE'
                else:
                    diff[key] = "UPDATE"
        elif key not in prot2:
            diff[key] = "UPDATE"
    for key in prot2:
        if key not in diff and key not in prot1:
            diff[key] = "REMOVE"

    return diff


def batch_update_objects_with_prototype(prototype, diff=None, objects=None):
    """
    Update existing objects with the latest version of the prototype.

    Args:
        prototype (str or dict): Either the `prototype_key` to use or the
            prototype dict itself.
        diff (dict, optional): This a diff structure that describes how to update the protototype.
            If not given this will be constructed from the first object found.
        objects (list, optional): List of objects to update. If not given, query for these
            objects using the prototype's `prototype_key`.
    Returns:
        changed (int): The number of objects that had changes applied to them.

    """
    if isinstance(prototype, basestring):
        new_prototype = protlib.search_prototype(prototype)
    else:
        new_prototype = prototype

    prototype_key = new_prototype['prototype_key']

    if not objects:
        objects = ObjectDB.objects.get_by_tag(prototype_key, category=_PROTOTYPE_TAG_CATEGORY)

    if not objects:
        return 0

    if not diff:
        diff = prototype_diff_from_object(new_prototype, objects[0])

    changed = 0
    for obj in objects:
        do_save = False

        old_prot_key = obj.tags.get(category=_PROTOTYPE_TAG_CATEGORY, return_list=True)
        old_prot_key = old_prot_key[0] if old_prot_key else None
        if prototype_key != old_prot_key:
            obj.tags.clear(category=_PROTOTYPE_TAG_CATEGORY)
            obj.tags.add(prototype_key, category=_PROTOTYPE_TAG_CATEGORY)

        for key, directive in diff.items():
            if directive in ('UPDATE', 'REPLACE'):

                if key in _PROTOTYPE_META_NAMES:
                    # prototype meta keys are not stored on-object
                    continue

                val = new_prototype[key]
                do_save = True

                if key == 'key':
                    obj.db_key = init_spawn_value(val, str)
                elif key == 'typeclass':
                    obj.db_typeclass_path = init_spawn_value(val, str)
                elif key == 'location':
                    obj.db_location = init_spawn_value(val, value_to_obj)
                elif key == 'home':
                    obj.db_home = init_spawn_value(val, value_to_obj)
                elif key == 'destination':
                    obj.db_destination = init_spawn_value(val, value_to_obj)
                elif key == 'locks':
                    if directive == 'REPLACE':
                        obj.locks.clear()
                    obj.locks.add(init_spawn_value(val, str))
                elif key == 'permissions':
                    if directive == 'REPLACE':
                        obj.permissions.clear()
                    obj.permissions.batch_add(*init_spawn_value(val, make_iter))
                elif key == 'aliases':
                    if directive == 'REPLACE':
                        obj.aliases.clear()
                    obj.aliases.batch_add(*init_spawn_value(val, make_iter))
                elif key == 'tags':
                    if directive == 'REPLACE':
                        obj.tags.clear()
                    obj.tags.batch_add(*init_spawn_value(val, make_iter))
                elif key == 'attrs':
                    if directive == 'REPLACE':
                        obj.attributes.clear()
                    obj.attributes.batch_add(*init_spawn_value(val, make_iter))
                elif key == 'exec':
                    # we don't auto-rerun exec statements, it would be huge security risk!
                    pass
                else:
                    obj.attributes.add(key, init_spawn_value(val, value_to_obj))
            elif directive == 'REMOVE':
                do_save = True
                if key == 'key':
                    obj.db_key = ''
                elif key == 'typeclass':
                    # fall back to default
                    obj.db_typeclass_path = settings.BASE_OBJECT_TYPECLASS
                elif key == 'location':
                    obj.db_location = None
                elif key == 'home':
                    obj.db_home = None
                elif key == 'destination':
                    obj.db_destination = None
                elif key == 'locks':
                    obj.locks.clear()
                elif key == 'permissions':
                    obj.permissions.clear()
                elif key == 'aliases':
                    obj.aliases.clear()
                elif key == 'tags':
                    obj.tags.clear()
                elif key == 'attrs':
                    obj.attributes.clear()
                elif key == 'exec':
                    # we don't auto-rerun exec statements, it would be huge security risk!
                    pass
                else:
                    obj.attributes.remove(key)
        if do_save:
            changed += 1
            obj.save()

    return changed


def batch_create_object(*objparams):
    """
    This is a cut-down version of the create_object() function,
    optimized for speed. It does NOT check and convert various input
    so make sure the spawned Typeclass works before using this!

    Args:
        objsparams (tuple): Each paremter tuple will create one object instance using the parameters
            within.
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


# Spawner mechanism

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
        return_parents (bool): Only return a dict of the
            prototype-parents (no object creation happens)
        only_validate (bool): Only run validation of prototype/parents
            (no object creation) and return the create-kwargs.

    Returns:
        object (Object, dict or list): Spawned object. If `only_validate` is given, return
            a list of the creation kwargs to build the object(s) without actually creating it. If
            `return_parents` is set, return dict of prototype parents.

    """
    # get available protparents
    protparents = {prot['prototype_key'].lower(): prot for prot in protlib.search_prototype()}

    # overload module's protparents with specifically given protparents
    protparents.update(
        {key.lower(): value for key, value in kwargs.get("prototype_parents", {}).items()})

    if "return_parents" in kwargs:
        # only return the parents
        return copy.deepcopy(protparents)

    objsparams = []
    for prototype in prototypes:

        protlib.validate_prototype(prototype, None, protparents, is_prototype_base=True)
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
        create_kwargs["db_key"] = init_spawn_value(val, str)

        val = prot.pop("location", None)
        create_kwargs["db_location"] = init_spawn_value(val, value_to_obj)

        val = prot.pop("home", settings.DEFAULT_HOME)
        create_kwargs["db_home"] = init_spawn_value(val, value_to_obj)

        val = prot.pop("destination", None)
        create_kwargs["db_destination"] = init_spawn_value(val, value_to_obj)

        val = prot.pop("typeclass", settings.BASE_OBJECT_TYPECLASS)
        create_kwargs["db_typeclass_path"] = init_spawn_value(val, str)

        # extract calls to handlers
        val = prot.pop("permissions", [])
        permission_string = init_spawn_value(val, make_iter)
        val = prot.pop("locks", "")
        lock_string = init_spawn_value(val, str)
        val = prot.pop("aliases", [])
        alias_string = init_spawn_value(val, make_iter)

        val = prot.pop("tags", [])
        tags = init_spawn_value(val, make_iter)

        prototype_key = prototype.get('prototype_key', None)
        if prototype_key:
            # we make sure to add a tag identifying which prototype created this object
            tags.append((prototype_key, _PROTOTYPE_TAG_CATEGORY))

        val = prot.pop("exec", "")
        execs = init_spawn_value(val, make_iter)

        # extract ndb assignments
        nattributes = dict((key.split("_", 1)[1], init_spawn_value(val, value_to_obj))
                           for key, val in prot.items() if key.startswith("ndb_"))

        # the rest are attributes
        val = prot.pop("attrs", [])
        attributes = init_spawn_value(val, list)

        simple_attributes = []
        for key, value in ((key, value) for key, value in prot.items()
                           if not (key.startswith("ndb_"))):
            if is_iter(value) and len(value) > 1:
                # (value, category)
                simple_attributes.append((key,
                                          init_spawn_value(value[0], value_to_obj_or_any),
                                          init_spawn_value(value[1], str)))
            else:
                simple_attributes.append((key,
                                          init_spawn_value(value, value_to_obj_or_any)))

        attributes = attributes + simple_attributes
        attributes = [tup for tup in attributes if not tup[0] in _NON_CREATE_KWARGS]

        # pack for call into _batch_create_object
        objsparams.append((create_kwargs, permission_string, lock_string,
                           alias_string, nattributes, attributes, tags, execs))

    if kwargs.get("only_validate"):
        return objsparams
    return batch_create_object(*objsparams)
