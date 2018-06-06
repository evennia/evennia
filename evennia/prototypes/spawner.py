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

    parent (str, tuple or callable, optional): name (prototype_key) of eventual parent prototype, or
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
 "parent": GOBLIN,
 "key": "goblin wizard",
 "spells": ["fire ball", "lighting bolt"]
 }

GOBLIN_ARCHER = {
 "parent": GOBLIN,
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
 "parent": (GOBLIN_WIZARD, ARCHWIZARD),
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
    make_iter, dbid_to_obj,
    is_iter, crop, get_all_typeclasses)

from evennia.utils.evtable import EvTable


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")
_NON_CREATE_KWARGS = _CREATE_OBJECT_KWARGS + _PROTOTYPE_META_NAMES
_MENU_CROP_WIDTH = 15
_PROTOTYPE_TAG_CATEGORY = "spawned_by_prototype"

_MENU_ATTR_LITERAL_EVAL_ERROR = (
    "|rCritical Python syntax error in your value. Only primitive Python structures are allowed.\n"
    "You also need to use correct Python syntax. Remember especially to put quotes around all "
    "strings inside lists and dicts.|n")


# Helper functions

def _to_obj(value, force=True):
    return dbid_to_obj(value, ObjectDB)


def _to_obj_or_any(value):
    obj = dbid_to_obj(value, ObjectDB)
    return obj if obj is not None else value


def validate_spawn_value(value, validator=None):
    """
    Analyze the value and produce a value for use at the point of spawning.

    Args:
        value (any): This can be:
            callable - will be called as callable()
            (callable, (args,)) - will be called as callable(*args)
            other - will be assigned depending on the variable type
            validator (callable, optional): If given, this will be called with the value to
                check and guarantee the outcome is of a given type.

    Returns:
        any (any): The (potentially pre-processed value to use for this prototype key)

    """
    value = protfunc_parser(value)
    validator = validator if validator else lambda o: o
    if callable(value):
        return validator(value())
    elif value and is_iter(value) and callable(value[0]):
        # a structure (callable, (args, ))
        args = value[1:]
        return validator(value[0](*make_iter(args)))
    else:
        return validator(value)

# Spawner mechanism


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
    protparents = {prot['prototype_key']: prot for prot in search_prototype()}

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
        nattribute = dict((key.split("_", 1)[1], validate_spawn_value(val, _to_obj))
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
