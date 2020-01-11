"""
Spawner

The spawner takes input files containing object definitions in
dictionary forms. These use a prototype architecture to define
unique objects without having to make a Typeclass for each.

There  main function is `spawn(*prototype)`, where the `prototype`
is a dictionary like this:

```python
from evennia.prototypes import prototypes

prot = {
 "prototype_key": "goblin",
 "typeclass": "types.objects.Monster",
 "key": "goblin grunt",
 "health": lambda: randint(20,30),
 "resists": ["cold", "poison"],
 "attacks": ["fists"],
 "weaknesses": ["fire", "light"]
 "tags": ["mob", "evil", ('greenskin','mob')]
 "attrs": [("weapon", "sword")]
}

prot = prototypes.create_prototype(prot)

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
    ndb_<name> (any): value of a nattribute (ndb_ is stripped) - this is of limited use.
    other (any): any other name is interpreted as the key of an Attribute with
        its value. Such Attributes have no categories.

Each value can also be a callable that takes no arguments. It should
return the value to enter into the field and will be called every time
the prototype is used to spawn an object. Note, if you want to store
a callable in an Attribute, embed it in a tuple to the `args` keyword.

By specifying the "prototype_parent" key, the prototype becomes a child of
the given prototype, inheritng all prototype slots it does not explicitly
define itself, while overloading those that it does specify.

```python
import random


{
 "prototype_key": "goblin_wizard",
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


import copy
import hashlib
import time

from django.conf import settings

import evennia
from evennia.objects.models import ObjectDB
from evennia.utils.utils import make_iter, is_iter
from evennia.prototypes import prototypes as protlib
from evennia.prototypes.prototypes import (
    value_to_obj,
    value_to_obj_or_any,
    init_spawn_value,
    _PROTOTYPE_TAG_CATEGORY,
)


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")
_PROTOTYPE_ROOT_NAMES = (
    "typeclass",
    "key",
    "aliases",
    "attrs",
    "tags",
    "locks",
    "permissions",
    "location",
    "home",
    "destination",
)
_NON_CREATE_KWARGS = _CREATE_OBJECT_KWARGS + _PROTOTYPE_META_NAMES


# Helper


def _get_prototype(inprot, protparents, uninherited=None, _workprot=None):
    """
    Recursively traverse a prototype dictionary, including multiple
    inheritance. Use validate_prototype before this, we don't check
    for infinite recursion here.

    Args:
        inprot (dict): Prototype dict (the individual prototype, with no inheritance included).
        protparents (dict): Available protparents, keyed by prototype_key.
        uninherited (dict): Parts of prototype to not inherit.
        _workprot (dict, optional): Work dict for the recursive algorithm.

    Returns:
        merged (dict): A prototype where parent's have been merged as needed (the
            `prototype_parent` key is removed).

    """

    def _inherit_tags(old_tags, new_tags):
        old = {(tup[0], tup[1]): tup for tup in old_tags}
        new = {(tup[0], tup[1]): tup for tup in new_tags}
        old.update(new)
        return list(old.values())

    def _inherit_attrs(old_attrs, new_attrs):
        old = {(tup[0], tup[2]): tup for tup in old_attrs}
        new = {(tup[0], tup[2]): tup for tup in new_attrs}
        old.update(new)
        return list(old.values())

    _workprot = {} if _workprot is None else _workprot
    if "prototype_parent" in inprot:
        # move backwards through the inheritance
        for prototype in make_iter(inprot["prototype_parent"]):
            # Build the prot dictionary in reverse order, overloading
            new_prot = _get_prototype(
                protparents.get(prototype.lower(), {}), protparents, _workprot=_workprot
            )

            # attrs, tags have internal structure that should be inherited separately
            new_prot["attrs"] = _inherit_attrs(
                _workprot.get("attrs", {}), new_prot.get("attrs", {})
            )
            new_prot["tags"] = _inherit_tags(_workprot.get("tags", {}), new_prot.get("tags", {}))

            _workprot.update(new_prot)
    # the inprot represents a higher level (a child prot), which should override parents

    inprot["attrs"] = _inherit_attrs(_workprot.get("attrs", {}), inprot.get("attrs", {}))
    inprot["tags"] = _inherit_tags(_workprot.get("tags", {}), inprot.get("tags", {}))
    _workprot.update(inprot)
    if uninherited:
        # put back the parts that should not be inherited
        _workprot.update(uninherited)
    _workprot.pop("prototype_parent", None)  # we don't need this for spawning
    return _workprot


def flatten_prototype(prototype, validate=False):
    """
    Produce a 'flattened' prototype, where all prototype parents in the inheritance tree have been
    merged into a final prototype.

    Args:
        prototype (dict): Prototype to flatten. Its `prototype_parent` field will be parsed.
        validate (bool, optional): Validate for valid keys etc.

    Returns:
        flattened (dict): The final, flattened prototype.

    """

    if prototype:
        prototype = protlib.homogenize_prototype(prototype)
        protparents = {prot["prototype_key"].lower(): prot for prot in protlib.search_prototype()}
        protlib.validate_prototype(
            prototype, None, protparents, is_prototype_base=validate, strict=validate
        )
        return _get_prototype(
            prototype, protparents, uninherited={"prototype_key": prototype.get("prototype_key")}
        )
    return {}


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
        prot["prototype_key"] = "From-Object-{}-{}".format(
            obj.key, hashlib.md5(bytes(str(time.time()), "utf-8")).hexdigest()[:7]
        )
        prot["prototype_desc"] = "Built from {}".format(str(obj))
        prot["prototype_locks"] = "spawn:all();edit:all()"
        prot["prototype_tags"] = []
    else:
        prot = prot[0]

    prot["key"] = obj.db_key or hashlib.md5(bytes(str(time.time()), "utf-8")).hexdigest()[:6]
    prot["typeclass"] = obj.db_typeclass_path

    location = obj.db_location
    if location:
        prot["location"] = location.dbref
    home = obj.db_home
    if home:
        prot["home"] = home.dbref
    destination = obj.db_destination
    if destination:
        prot["destination"] = destination.dbref
    locks = obj.locks.all()
    if locks:
        prot["locks"] = ";".join(locks)
    perms = obj.permissions.get(return_list=True)
    if perms:
        prot["permissions"] = make_iter(perms)
    aliases = obj.aliases.get(return_list=True)
    if aliases:
        prot["aliases"] = aliases
    tags = sorted(
        [(tag.db_key, tag.db_category, tag.db_data) for tag in obj.tags.all(return_objs=True)]
    )
    if tags:
        prot["tags"] = tags
    attrs = sorted(
        [
            (attr.key, attr.value, attr.category, ";".join(attr.locks.all()))
            for attr in obj.attributes.all()
        ]
    )
    if attrs:
        prot["attrs"] = attrs

    return prot


def prototype_diff(prototype1, prototype2, maxdepth=2):
    """
    A 'detailed' diff specifies differences down to individual sub-sectiions
    of the prototype, like individual attributes, permissions etc. It is used
    by the menu to allow a user to customize what should be kept.

    Args:
        prototype1 (dict): Original prototype.
        prototype2 (dict): Comparison prototype.
        maxdepth (int, optional): The maximum depth into the diff we go before treating the elements
            of iterables as individual entities to compare. This is important since a single
            attr/tag (for example) are represented by a tuple.

    Returns:
        diff (dict): A structure detailing how to convert prototype1 to prototype2. All
            nested structures are dicts with keys matching either the prototype's matching
            key or the first element in the tuple describing the prototype value (so for
            a tag tuple `(tagname, category)` the second-level key in the diff would be tagname).
            The the bottom level of the diff consist of tuples `(old, new, instruction)`, where
            instruction can be one of "REMOVE", "ADD", "UPDATE" or "KEEP".

    """

    def _recursive_diff(old, new, depth=0):

        old_type = type(old)
        new_type = type(new)

        if old_type != new_type:
            if old and not new:
                if depth < maxdepth and old_type == dict:
                    return {key: (part, None, "REMOVE") for key, part in old.items()}
                elif depth < maxdepth and is_iter(old):
                    return {
                        part[0] if is_iter(part) else part: (part, None, "REMOVE") for part in old
                    }
                return (old, new, "REMOVE")
            elif not old and new:
                if depth < maxdepth and new_type == dict:
                    return {key: (None, part, "ADD") for key, part in new.items()}
                elif depth < maxdepth and is_iter(new):
                    return {part[0] if is_iter(part) else part: (None, part, "ADD") for part in new}
                return (old, new, "ADD")
            else:
                # this condition should not occur in a standard diff
                return (old, new, "UPDATE")
        elif depth < maxdepth and new_type == dict:
            all_keys = set(list(old.keys()) + list(new.keys()))
            return {
                key: _recursive_diff(old.get(key), new.get(key), depth=depth + 1)
                for key in all_keys
            }
        elif depth < maxdepth and is_iter(new):
            old_map = {part[0] if is_iter(part) else part: part for part in old}
            new_map = {part[0] if is_iter(part) else part: part for part in new}
            all_keys = set(list(old_map.keys()) + list(new_map.keys()))
            return {
                key: _recursive_diff(old_map.get(key), new_map.get(key), depth=depth + 1)
                for key in all_keys
            }
        elif old != new:
            return (old, new, "UPDATE")
        else:
            return (old, new, "KEEP")

    diff = _recursive_diff(prototype1, prototype2)

    return diff


def flatten_diff(diff):
    """
    For spawning, a 'detailed' diff is not necessary, rather we just want instructions on how to
    handle each root key.

    Args:
        diff (dict): Diff produced by `prototype_diff` and
            possibly modified by the user. Note that also a pre-flattened diff will come out
            unchanged by this function.

    Returns:
        flattened_diff (dict): A flat structure detailing how to operate on each
            root component of the prototype.

    Notes:
        The flattened diff has the following possible instructions:
            UPDATE, REPLACE, REMOVE
        Many of the detailed diff's values can hold nested structures with their own
        individual instructions. A detailed diff can have the following instructions:
            REMOVE, ADD, UPDATE, KEEP
        Here's how they are translated:
            - All REMOVE -> REMOVE
            - All ADD|UPDATE -> UPDATE
            - All KEEP -> KEEP
            - Mix KEEP, UPDATE, ADD -> UPDATE
            - Mix REMOVE, KEEP, UPDATE, ADD -> REPLACE
    """

    valid_instructions = ("KEEP", "REMOVE", "ADD", "UPDATE")

    def _get_all_nested_diff_instructions(diffpart):
        "Started for each root key, returns all instructions nested under it"
        out = []
        typ = type(diffpart)
        if typ == tuple and len(diffpart) == 3 and diffpart[2] in valid_instructions:
            out = [diffpart[2]]
        elif typ == dict:
            # all other are dicts
            for val in diffpart.values():
                out.extend(_get_all_nested_diff_instructions(val))
        else:
            raise RuntimeError(
                "Diff contains non-dicts that are not on the "
                "form (old, new, inst): {}".format(diffpart)
            )
        return out

    flat_diff = {}

    # flatten diff based on rules
    for rootkey, diffpart in diff.items():
        insts = _get_all_nested_diff_instructions(diffpart)
        if all(inst == "KEEP" for inst in insts):
            rootinst = "KEEP"
        elif all(inst in ("ADD", "UPDATE") for inst in insts):
            rootinst = "UPDATE"
        elif all(inst == "REMOVE" for inst in insts):
            rootinst = "REMOVE"
        elif "REMOVE" in insts:
            rootinst = "REPLACE"
        else:
            rootinst = "UPDATE"

        flat_diff[rootkey] = rootinst

    return flat_diff


def prototype_diff_from_object(prototype, obj):
    """
    Get a simple diff for a prototype compared to an object which may or may not already have a
    prototype (or has one but changed locally). For more complex migratations a manual diff may be
    needed.

    Args:
        prototype (dict): New prototype.
        obj (Object): Object to compare prototype against.

    Returns:
        diff (dict): Mapping for every prototype key: {"keyname": "REMOVE|UPDATE|KEEP", ...}
        obj_prototype (dict): The prototype calculated for the given object. The diff is how to
            convert this prototype into the new prototype.

    Notes:
        The `diff` is on the following form:

            {"key": (old, new, "KEEP|REPLACE|UPDATE|REMOVE"),
                "attrs": {"attrkey": (old, new, "KEEP|REPLACE|UPDATE|REMOVE"),
                          "attrkey": (old, new, "KEEP|REPLACE|UPDATE|REMOVE"), ...},
                "aliases": {"aliasname": (old, new, "KEEP...", ...},
                ... }

    """
    obj_prototype = prototype_from_object(obj)
    diff = prototype_diff(obj_prototype, protlib.homogenize_prototype(prototype))
    return diff, obj_prototype


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
    prototype = protlib.homogenize_prototype(prototype)

    if isinstance(prototype, str):
        new_prototype = protlib.search_prototype(prototype)
    else:
        new_prototype = prototype

    prototype_key = new_prototype["prototype_key"]

    if not objects:
        objects = ObjectDB.objects.get_by_tag(prototype_key, category=_PROTOTYPE_TAG_CATEGORY)

    if not objects:
        return 0

    if not diff:
        diff, _ = prototype_diff_from_object(new_prototype, objects[0])

    # make sure the diff is flattened
    diff = flatten_diff(diff)
    changed = 0
    for obj in objects:
        do_save = False

        old_prot_key = obj.tags.get(category=_PROTOTYPE_TAG_CATEGORY, return_list=True)
        old_prot_key = old_prot_key[0] if old_prot_key else None
        if prototype_key != old_prot_key:
            obj.tags.clear(category=_PROTOTYPE_TAG_CATEGORY)
            obj.tags.add(prototype_key, category=_PROTOTYPE_TAG_CATEGORY)

        for key, directive in diff.items():
            if directive in ("UPDATE", "REPLACE"):

                if key in _PROTOTYPE_META_NAMES:
                    # prototype meta keys are not stored on-object
                    continue

                val = new_prototype[key]
                do_save = True

                if key == "key":
                    obj.db_key = init_spawn_value(val, str)
                elif key == "typeclass":
                    obj.db_typeclass_path = init_spawn_value(val, str)
                elif key == "location":
                    obj.db_location = init_spawn_value(val, value_to_obj)
                elif key == "home":
                    obj.db_home = init_spawn_value(val, value_to_obj)
                elif key == "destination":
                    obj.db_destination = init_spawn_value(val, value_to_obj)
                elif key == "locks":
                    if directive == "REPLACE":
                        obj.locks.clear()
                    obj.locks.add(init_spawn_value(val, str))
                elif key == "permissions":
                    if directive == "REPLACE":
                        obj.permissions.clear()
                    obj.permissions.batch_add(*(init_spawn_value(perm, str) for perm in val))
                elif key == "aliases":
                    if directive == "REPLACE":
                        obj.aliases.clear()
                    obj.aliases.batch_add(*(init_spawn_value(alias, str) for alias in val))
                elif key == "tags":
                    if directive == "REPLACE":
                        obj.tags.clear()
                    obj.tags.batch_add(
                        *(
                            (init_spawn_value(ttag, str), tcategory, tdata)
                            for ttag, tcategory, tdata in val
                        )
                    )
                elif key == "attrs":
                    if directive == "REPLACE":
                        obj.attributes.clear()
                    obj.attributes.batch_add(
                        *(
                            (
                                init_spawn_value(akey, str),
                                init_spawn_value(aval, value_to_obj),
                                acategory,
                                alocks,
                            )
                            for akey, aval, acategory, alocks in val
                        )
                    )
                elif key == "exec":
                    # we don't auto-rerun exec statements, it would be huge security risk!
                    pass
                else:
                    obj.attributes.add(key, init_spawn_value(val, value_to_obj))
            elif directive == "REMOVE":
                do_save = True
                if key == "key":
                    obj.db_key = ""
                elif key == "typeclass":
                    # fall back to default
                    obj.db_typeclass_path = settings.BASE_OBJECT_TYPECLASS
                elif key == "location":
                    obj.db_location = None
                elif key == "home":
                    obj.db_home = None
                elif key == "destination":
                    obj.db_destination = None
                elif key == "locks":
                    obj.locks.clear()
                elif key == "permissions":
                    obj.permissions.clear()
                elif key == "aliases":
                    obj.aliases.clear()
                elif key == "tags":
                    obj.tags.clear()
                elif key == "attrs":
                    obj.attributes.clear()
                elif key == "exec":
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

    objs = []
    for objparam in objparams:

        obj = ObjectDB(**objparam[0])

        # setup
        obj._createdict = {
            "permissions": make_iter(objparam[1]),
            "locks": objparam[2],
            "aliases": make_iter(objparam[3]),
            "nattributes": objparam[4],
            "attributes": objparam[5],
            "tags": make_iter(objparam[6]),
        }
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
        prototypes (str or dict): Each argument should either be a
            prototype_key (will be used to find the prototype) or a full prototype
            dictionary. These will be batched-spawned as one object each. 
    Kwargs:
        prototype_modules (str or list): A python-path to a prototype
            module, or a list of such paths. These will be used to build
            the global protparents dictionary accessible by the input
            prototypes. If not given, it will instead look for modules
            defined by settings.PROTOTYPE_MODULES.
        prototype_parents (dict): A dictionary holding a custom
            prototype-parent dictionary. Will overload same-named
            prototypes from prototype_modules.
        return_parents (bool): Return a dict of the entire prototype-parent tree
            available to this prototype (no object creation happens). This is a
            merged result between the globally found protparents and whatever
            custom `prototype_parents` are given to this function.
        only_validate (bool): Only run validation of prototype/parents
            (no object creation) and return the create-kwargs.

    Returns:
        object (Object, dict or list): Spawned object(s). If `only_validate` is given, return
            a list of the creation kwargs to build the object(s) without actually creating it. If
            `return_parents` is set, instead return dict of prototype parents.

    """
    # search string (=prototype_key) from input
    prototypes = [
        protlib.search_prototype(prot, require_single=True)[0] if isinstance(prot, str) else prot
        for prot in prototypes
    ]

    # get available protparents
    protparents = {prot["prototype_key"].lower(): prot for prot in protlib.search_prototype()}

    if not kwargs.get("only_validate"):
        # homogenization to be more lenient about prototype format when entering the prototype manually
        prototypes = [protlib.homogenize_prototype(prot) for prot in prototypes]

    # overload module's protparents with specifically given protparents
    # we allow prototype_key to be the key of the protparent dict, to allow for module-level
    # prototype imports. We need to insert prototype_key in this case
    for key, protparent in kwargs.get("prototype_parents", {}).items():
        key = str(key).lower()
        protparent["prototype_key"] = str(protparent.get("prototype_key", key)).lower()
        protparents[key] = protparent

    if "return_parents" in kwargs:
        # only return the parents
        return copy.deepcopy(protparents)

    objsparams = []
    for prototype in prototypes:

        protlib.validate_prototype(prototype, None, protparents, is_prototype_base=True)
        prot = _get_prototype(
            prototype, protparents, uninherited={"prototype_key": prototype.get("prototype_key")}
        )
        if not prot:
            continue

        # extract the keyword args we need to create the object itself. If we get a callable,
        # call that to get the value (don't catch errors)
        create_kwargs = {}
        # we must always add a key, so if not given we use a shortened md5 hash. There is a (small)
        # chance this is not unique but it should usually not be a problem.
        val = prot.pop(
            "key",
            "Spawned-{}".format(hashlib.md5(bytes(str(time.time()), "utf-8")).hexdigest()[:6]),
        )
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
        tags = []
        for (tag, category, data) in val:
            tags.append((init_spawn_value(tag, str), category, data))

        prototype_key = prototype.get("prototype_key", None)
        if prototype_key:
            # we make sure to add a tag identifying which prototype created this object
            tags.append((prototype_key, _PROTOTYPE_TAG_CATEGORY))

        val = prot.pop("exec", "")
        execs = init_spawn_value(val, make_iter)

        # extract ndb assignments
        nattributes = dict(
            (key.split("_", 1)[1], init_spawn_value(val, value_to_obj))
            for key, val in prot.items()
            if key.startswith("ndb_")
        )

        # the rest are attribute tuples (attrname, value, category, locks)
        val = make_iter(prot.pop("attrs", []))
        attributes = []
        for (attrname, value, category, locks) in val:
            attributes.append((attrname, init_spawn_value(value), category, locks))

        simple_attributes = []
        for key, value in (
            (key, value) for key, value in prot.items() if not (key.startswith("ndb_"))
        ):
            # we don't support categories, nor locks for simple attributes
            if key in _PROTOTYPE_META_NAMES:
                continue
            else:
                simple_attributes.append(
                    (key, init_spawn_value(value, value_to_obj_or_any), None, None)
                )

        attributes = attributes + simple_attributes
        attributes = [tup for tup in attributes if not tup[0] in _NON_CREATE_KWARGS]

        # pack for call into _batch_create_object
        objsparams.append(
            (
                create_kwargs,
                permission_string,
                lock_string,
                alias_string,
                nattributes,
                attributes,
                tags,
                execs,
            )
        )

    if kwargs.get("only_validate"):
        return objsparams
    return batch_create_object(*objsparams)
