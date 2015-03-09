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

    ndb_<name> - value of a nattribute (ndb_ is stripped)
    any other keywords are interpreted as Attributes and their values.

Each value can also be a callable that takes no arguments. It should
return the value to enter into the field and will be called every time
the prototype is used to spawn an object.

By specifying a prototype, the child will inherit all prototype slots
it does not explicitly define itself, while overloading those that it
does specify.

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

"""

import copy
#TODO
#sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
#os.environ['DJANGO_SETTINGS_MODULE'] = 'game.settings'

from django.conf import settings
from random import randint
from evennia.objects.models import ObjectDB
from evennia.utils.utils import make_iter, all_from_module, dbid_to_obj

_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")

_handle_dbref = lambda inp: dbid_to_obj(inp, ObjectDB)


def _validate_prototype(key, prototype, protparents, visited):
    "Run validation on a prototype, checking for inifinite regress"
    assert isinstance(prototype, dict)
    if id(prototype) in visited:
        raise RuntimeError("%s has infinite nesting of prototypes." % key or prototype)
    visited.append(id(prototype))
    protstrings = prototype.get("prototype")
    if protstrings:
        for protstring in make_iter(protstrings):
            if key is not None and protstring == key:
                raise RuntimeError("%s tries to prototype itself." % key or prototype)
            protparent = protparents.get(protstring)
            if not protparent:
                raise RuntimeError("%s's prototype '%s' was not found." % (key or prototype, protstring))
            _validate_prototype(protstring, protparent, protparents, visited)


def _get_prototype(dic, prot, protparents):
    """
    Recursively traverse a prototype dictionary,
    including multiple inheritance. Use _validate_prototype
    before this, we don't check for infinite recursion here.
    """
    if "prototype" in dic:
        # move backwards through the inheritance
        for prototype in make_iter(dic["prototype"]):
            # Build the prot dictionary in reverse order, overloading
            new_prot = _get_prototype(protparents.get(prototype, {}), prot, protparents)
            prot.update(new_prot)
    prot.update(dic)
    prot.pop("prototype", None) # we don't need this anymore
    return prot

def _batch_create_object(*objparams):
    """
    This is a cut-down version of the create_object() function,
    optimized for speed. It does NOT check and convert various input
    so make sure the spawned Typeclass works before using this!

    Input:
    objsparams - each argument should be a tuple of arguments for the respective
                 creation/add handlers in the following order:
                    (create, permissions, locks, aliases, nattributes, attributes)
    Returns:
        objects (list): A list of created objects

    """

    # bulk create all objects in one go

    # unfortunately this doesn't work since bulk_create doesn't creates pks;
    # the result are double objects at the next stage
    #dbobjs = _ObjectDB.objects.bulk_create(dbobjs)

    dbobjs = [ObjectDB(**objparam[0]) for objparam in objparams]
    objs = []
    for iobj, obj in enumerate(dbobjs):
        # call all setup hooks on each object
        objparam = objparams[iobj]
        # setup
        obj._createdict = {"permissions": objparam[1],
                           "locks": objparam[2],
                           "aliases": objparam[3],
                           "nattributes": objparam[4],
                           "attributes": objparam[5]}
        # this triggers all hooks
        obj.save()
        objs.append(obj)
    return objs


def spawn(*prototypes, **kwargs):
    """
    Spawn a number of prototyped objects. Each argument should be a
    prototype dictionary.

    keyword args:
        prototype_modules - a python-path to a
            prototype module, or a list of such paths. These will be used
            to build the global protparents dictionary accessible by the
            input prototypes. If not given, it will instead look for modules
            defined by settings.PROTOTYPE_MODULES.
        prototype_parents - a dictionary holding a custom prototype-parent dictionary. Will
                      overload same-named prototypes from prototype_modules.
        return_prototypes - only return a list of the prototype-parents
                            (no object creation happens)
    """

    protparents = {}
    protmodules = make_iter(kwargs.get("prototype_modules", []))
    if not protmodules and hasattr(settings, "PROTOTYPE_MODULES"):
        protmodules = make_iter(settings.PROTOTYPE_MODULES)
    for prototype_module in protmodules:
        protparents.update(dict((key, val)
                for key, val in all_from_module(prototype_module).items() if isinstance(val, dict)))
    #overload module's protparents with specifically given protparents
    protparents.update(kwargs.get("prototype_parents", {}))
    for key, prototype in protparents.items():
        _validate_prototype(key, prototype, protparents, [])

    if "return_prototypes" in kwargs:
        # only return the parents
        return copy.deepcopy(protparents)

    objsparams = []
    for prototype in prototypes:

        _validate_prototype(None, prototype, protparents, [])
        prot = _get_prototype(prototype, {}, protparents)
        if not prot:
            continue

        # extract the keyword args we need to create the object itself
        create_kwargs = {}
        create_kwargs["db_key"] = prot.pop("key", "Spawned Object %06i" % randint(1,100000))
        create_kwargs["db_location"] = _handle_dbref(prot.pop("location", None))
        create_kwargs["db_home"] = _handle_dbref(prot.pop("home", settings.DEFAULT_HOME))
        create_kwargs["db_destination"] = _handle_dbref(prot.pop("destination", None))
        create_kwargs["db_typeclass_path"] = prot.pop("typeclass", settings.BASE_OBJECT_TYPECLASS)

        # extract calls to handlers
        permission_string = prot.pop("permissions", "")
        lock_string = prot.pop("locks", "")
        alias_string = prot.pop("aliases", "")

        # extract ndb assignments
        nattributes = dict((key.split("_", 1)[1], value if callable(value) else value)
                            for key, value in prot.items() if key.startswith("ndb_"))

        # the rest are attributes
        attributes = dict((key, value() if callable(value) else value)
                           for key, value in prot.items()
                           if not (key in _CREATE_OBJECT_KWARGS or key in nattributes))

        # pack for call into _batch_create_object
        objsparams.append( (create_kwargs, permission_string, lock_string,
                            alias_string, nattributes, attributes) )

    return _batch_create_object(*objsparams)


if __name__ == "__main__":
    # testing

    protparents = {
            "NOBODY": {},
            #"INFINITE" : {
            #    "prototype":"INFINITE"
            #},
            "GOBLIN" : {
             "key": "goblin grunt",
             "health": lambda: randint(20,30),
             "resists": ["cold", "poison"],
             "attacks": ["fists"],
             "weaknesses": ["fire", "light"]
             },
            "GOBLIN_WIZARD" : {
             "prototype": "GOBLIN",
             "key": "goblin wizard",
             "spells": ["fire ball", "lighting bolt"]
             },
            "GOBLIN_ARCHER" : {
             "prototype": "GOBLIN",
             "key": "goblin archer",
             "attacks": ["short bow"]
            },
            "ARCHWIZARD" : {
             "attacks": ["archwizard staff"],
            },
            "GOBLIN_ARCHWIZARD" : {
             "key": "goblin archwizard",
             "prototype" : ("GOBLIN_WIZARD", "ARCHWIZARD")
            }
        }
    # test
    print [o.key for o in spawn(protparents["GOBLIN"], protparents["GOBLIN_ARCHWIZARD"], prototype_parents=protparents)]
