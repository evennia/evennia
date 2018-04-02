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
from evennia.utils.utils import (
    make_iter, all_from_module, dbid_to_obj, is_iter, crop, get_all_typeclasses)

from collections import namedtuple
from evennia.scripts.scripts import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.evtable import EvTable
from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils.ansi import strip_ansi


_CREATE_OBJECT_KWARGS = ("key", "location", "home", "destination")
_MODULE_PROTOTYPES = {}
_MODULE_PROTOTYPE_MODULES = {}
_MENU_CROP_WIDTH = 15


class PermissionError(RuntimeError):
    pass

# storage of meta info about the prototype
MetaProto = namedtuple('MetaProto', ['key', 'desc', 'locks', 'tags', 'prototype'])

for mod in settings.PROTOTYPE_MODULES:
    # to remove a default prototype, override it with an empty dict.
    # internally we store as (key, desc, locks, tags, prototype_dict)
    prots = [(key, prot) for key, prot in all_from_module(mod).items()
             if prot and isinstance(prot, dict)]
    _MODULE_PROTOTYPES.update(
        {key.lower(): MetaProto(
            key.lower(),
            prot['prototype_desc'] if 'prototype_desc' in prot else mod,
            prot['prototype_lock'] if 'prototype_lock' in prot else "use:all()",
            set(make_iter(
                prot['prototype_tags']) if 'prototype_tags' in prot else ["base-prototype"]),
            prot)
         for key, prot in prots})
    _MODULE_PROTOTYPE_MODULES.update({tup[0]: mod for tup in prots})

# Prototype storage mechanisms


class DbPrototype(DefaultScript):
    """
    This stores a single prototype
    """
    def at_script_creation(self):
        self.key = "empty prototype"
        self.desc = "A prototype"


def build_metaproto(key='', desc='', locks='', tags=None, prototype=None):
    """
    Create a metaproto from combinant parts.

    """
    if locks:
        locks = (";".join(locks) if is_iter(locks) else locks)
    else:
        locks = []
    prototype = dict(prototype) if prototype else {}
    return MetaProto(key, desc, locks, tags, dict(prototype))


def save_db_prototype(caller, key, prototype, desc="", tags=None, locks="", delete=False):
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
            applied with the 'db_prototype' category.
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

    is_valid, err = caller.locks.validate(locks)
    if not is_valid:
        caller.msg("Lock error: {}".format(err))
        return False

    tags = [(tag, "db_prototype") for tag in make_iter(tags)]

    if key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(key_orig, mod))

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


def search_db_prototype(key=None, tags=None, return_metaprotos=False):
    """
    Find persistent (database-stored) prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.
        return_metaproto (bool): Return results as metaprotos.
    Return:
        matches (queryset or list): All found DbPrototypes. If `return_metaprotos`
            is set, return a list of MetaProtos.

    Note:
        This will not include read-only prototypes defined in modules.

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
    if return_metaprotos:
        return [build_metaproto(match.key, match.desc, match.locks.all(),
                                match.tags.get(category="db_prototype", return_list=True),
                                match.attributes.get("prototype"))
                for match in matches]
    return matches


def search_module_prototype(key=None, tags=None):
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
        matches = {key: metaproto for key, metaproto in _MODULE_PROTOTYPES.items()
                   if tagset.intersection(metaproto.tags)}
    else:
        matches = _MODULE_PROTOTYPES

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
    Find prototypes based on key and/or tags, or all prototypes.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.
        return_meta (bool): If False, only return prototype dicts, if True
            return MetaProto namedtuples including prototype meta info

    Return:
        matches (list): All found prototype dicts or MetaProtos. If no keys
            or tags are given, all available prototypes/MetaProtos will be returned.

    Note:
        The available prototypes is a combination of those supplied in
        PROTOTYPE_MODULES and those stored from in-game. For the latter,
        this will use the tags to make a subselection before attempting
        to match on the key. So if key/tags don't match up nothing will
        be found.

    """
    module_prototypes = search_module_prototype(key, tags)
    db_prototypes = search_db_prototype(key, tags, return_metaprotos=True)

    matches = db_prototypes + module_prototypes
    if len(matches) > 1 and key:
        key = key.lower()
        # avoid duplicates if an exact match exist between the two types
        filter_matches = [mta for mta in matches if mta.key == key]
        if filter_matches and len(filter_matches) < len(matches):
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


def list_prototypes(caller, key=None, tags=None, show_non_use=False, show_non_edit=True):
    """
    Collate a list of found prototypes based on search criteria and access.

    Args:
        caller (Account or Object): The object requesting the list.
        key (str, optional): Exact or partial key to query for.
        tags (str or list, optional): Tag key or keys to query for.
        show_non_use (bool, optional): Show also prototypes the caller may not use.
        show_non_edit (bool, optional): Show also prototypes the caller may not edit.
    Returns:
        table (EvTable or None): An EvTable representation of the prototypes. None
            if no prototypes were found.

    """
    # this allows us to pass lists of empty strings
    tags = [tag for tag in make_iter(tags) if tag]

    # get metaprotos for readonly and db-based prototypes
    metaprotos = search_module_prototype(key, tags)
    metaprotos += search_db_prototype(key, tags, return_metaprotos=True)

    # get use-permissions of readonly attributes (edit is always False)
    prototypes = [
        (metaproto.key,
         metaproto.desc,
         ("{}/N".format('Y'
          if caller.locks.check_lockstring(
            caller,
            metaproto.locks,
            access_type='use') else 'N')),
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


def metaproto_to_str(metaproto):
    """
    Format a metaproto to a nice string representation.

    Args:
        metaproto (NamedTuple): Represents the prototype.
    """
    header = (
        "|cprototype key:|n {}, |ctags:|n {}, |clocks:|n {} \n"
        "|cdesc:|n {} \n|cprototype:|n ".format(
           metaproto.key, ", ".join(metaproto.tags),
           metaproto.locks, metaproto.desc))
    prototype = ("{{\n  {} \n}}".format("\n  ".join("{!r}: {!r},".format(key, value)
                 for key, value in
                 sorted(metaproto.prototype.items())).rstrip(",")))
    return header + prototype


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


# ------------------------------------------------------------
#
# OLC Prototype design menu
#
# ------------------------------------------------------------

# Helper functions

def _get_menu_metaprot(caller):

    metaproto = None
    if hasattr(caller.ndb._menutree, "olc_metaprot"):
        metaproto = caller.ndb._menutree.olc_metaprot
    if not metaproto:
        metaproto = build_metaproto(None, '', [], [], None)
        caller.ndb._menutree.olc_metaprot = metaproto
        caller.ndb._menutree.olc_new = True
    return metaproto


def _is_new_prototype(caller):
    return hasattr(caller.ndb._menutree, "olc_new")


def _set_menu_metaprot(caller, field, value):
    metaprot = _get_menu_metaprot(caller)
    kwargs = dict(metaprot.__dict__)
    kwargs[field] = value
    caller.ndb._menutree.olc_metaprot = build_metaproto(**kwargs)


def _format_property(key, required=False, metaprot=None, prototype=None, cropper=None):
    key = key.lower()
    if metaprot is not None:
        prop = getattr(metaprot, key) or ''
    elif prototype is not None:
        prop = prototype.get(key, '')

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
    prop = kwargs.get("prop", "meta_key")
    processor = kwargs.get("processor", None)
    next_node = kwargs.get("next_node", "node_index")

    propname_low = prop.strip().lower()
    meta = propname_low.startswith("meta_")
    if meta:
        propname_low = propname_low[5:]

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

    if meta:
        _set_menu_metaprot(caller, propname_low, value)
    else:
        metaprot = _get_menu_metaprot(caller)
        prototype = metaprot.prototype
        prototype[propname_low] = value

        # typeclass and prototype can't co-exist
        if propname_low == "typeclass":
            prototype.pop("prototype", None)
        if propname_low == "prototype":
            prototype.pop("typeclass", None)

        _set_menu_metaprot(caller, "prototype", prototype)

    caller.msg("Set {prop} to '{value}'.".format(
        prop=prop.replace("_", "-").capitalize(), value=str(value)))

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
    metaprot = _get_menu_metaprot(caller)
    prototype = metaprot.prototype

    text = ("|c --- Prototype wizard --- |n\n\n"
            "Define the |yproperties|n of the prototype. All prototype values can be "
            "over-ridden at the time of spawning an instance of the prototype, but some are "
            "required.\n\n'|wMeta'-properties|n are not used in the prototype itself but are used "
            "to organize and list prototypes. The 'Meta-Key' uniquely identifies the prototype "
            "and allows you to edit an existing prototype or save a new one for use by you or "
            "others later.\n\n(make choice; q to abort. If unsure, start from 1.)")

    options = []
    # The meta-key goes first
    options.append(
        {"desc": "|WMeta-Key|n|n{}".format(_format_property("Key", True, metaprot, None)),
         "goto": "node_meta_key"})
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
                key, _format_property(key, required, None, prototype, cropper=cropper)),
             "goto": "node_{}".format(key.lower())})
    required = False
    for key in ('Desc', 'Tags', 'Locks'):
        options.append(
            {"desc": "|WMeta-{}|n|n{}".format(key, _format_property(key, required, metaprot, None)),
             "goto": "node_meta_{}".format(key.lower())})

    return text, options


def node_validate_prototype(caller, raw_string, **kwargs):
    metaprot = _get_menu_metaprot(caller)

    txt = metaproto_to_str(metaprot)
    errors = "\n\n|g No validation errors found.|n (but errors could still happen at spawn-time)"
    try:
        # validate, don't spawn
        spawn(metaprot.prototype, return_prototypes=True)
    except RuntimeError as err:
        errors = "\n\n|rError: {}|n".format(err)
    text = (txt + errors)

    options = _wizard_options(None, kwargs.get("back"), None)

    return text, options


def _check_meta_key(caller, key):
    old_metaprot = search_prototype(key)
    olc_new = _is_new_prototype(caller)
    key = key.strip().lower()
    if old_metaprot:
        # we are starting a new prototype that matches an existing
        if not caller.locks.check_lockstring(caller, old_metaprot.locks, access_type='edit'):
            # return to the node_meta_key to try another key
            caller.msg("Prototype '{key}' already exists and you don't "
                       "have permission to edit it.".format(key=key))
            return "node_meta_key"
        elif olc_new:
            # we are selecting an existing prototype to edit. Reset to index.
            del caller.ndb._menutree.olc_new
            caller.ndb._menutree.olc_metaprot = old_metaprot
            caller.msg("Prototype already exists. Reloading.")
            return "node_index"

    return _set_property(caller, key, prop='meta_key', next_node="node_prototype")


def node_meta_key(caller):
    metaprot = _get_menu_metaprot(caller)
    text = ["The prototype name, or |wMeta-Key|n, uniquely identifies the prototype. "
            "It is used to find and use the prototype to spawn new entities. "
            "It is not case sensitive."]
    old_key = metaprot.key
    if old_key:
        text.append("Current key is '|w{key}|n'".format(key=old_key))
    else:
        text.append("The key is currently unset.")
    text.append("Enter text or make a choice (q for quit)")
    text = "\n\n".join(text)
    options = _wizard_options("meta_key", "index", "prototype")
    options.append({"key": "_default",
                    "goto": _check_meta_key})
    return text, options


def _all_prototypes():
    return [mproto.key for mproto in search_prototype()]


def _prototype_examine(caller, prototype_name):
    metaprot = search_prototype(key=prototype_name)
    if metaprot:
        return metaproto_to_str(metaprot[0])
    return "Prototype not registered."


def _prototype_select(caller, prototype):
    ret = _set_property(caller, prototype, prop="prototype", processor=str, next_node="node_key")
    caller.msg("Selected prototype |y{}|n. Removed any set typeclass parent.".format(prototype))
    return ret


@list_node(_all_prototypes, _prototype_select, examine=_prototype_examine)
def node_prototype(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    prototype = prot.get("prototype")

    text = ["Set the prototype's parent |yPrototype|n. If this is unset, Typeclass will be used."]
    if prototype:
        text.append("Current prototype is |y{prototype}|n.".format(prototype=prototype))
    else:
        text.append("Parent prototype is not set")
    text = "\n\n".join(text)
    options = _wizard_options("prototype", "meta_key", "typeclass", color="|W")
    return text, options


def _all_typeclasses():
    return list(sorted(get_all_typeclasses().keys()))
    # return list(sorted(get_all_typeclasses(parent="evennia.objects.objects.DefaultObject").keys()))


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
    return txt


def _typeclass_select(caller, typeclass):
    ret = _set_property(caller, typeclass, prop='typeclass', processor=str, next_node="node_key")
    caller.msg("Selected typeclass |y{}|n. Removed any set prototype parent.".format(typeclass))
    return ret


@list_node(_all_typeclasses, _typeclass_select, examine=_typeclass_examine)
def node_typeclass(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    typeclass = prot.get("typeclass")

    text = ["Set the typeclass's parent |yTypeclass|n."]
    if typeclass:
        text.append("Current typeclass is |y{typeclass}|n.".format(typeclass=typeclass))
    else:
        text.append("Using default typeclass {typeclass}.".format(
            typeclass=settings.BASE_OBJECT_TYPECLASS))
    text = "\n\n".join(text)
    options = _wizard_options("typeclass", "prototype", "key", color="|W")
    return text, options


def node_key(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    key = prot.get("key")

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
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    aliases = prot.get("aliases")

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


def node_attrs(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
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


def node_tags(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    tags = prot.get("tags")

    text = ["Set the prototype's |yTags|n. Separate multiple tags with commas. "
            "Will retain case sensitivity."]
    if tags:
        text.append("Current tags are '|y{tags}|n'.".format(tags=tags))
    else:
        text.append("No tags are set.")
    text = "\n\n".join(text)
    options = _wizard_options("tags", "attrs", "locks")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="tags",
                                  processor=lambda s: [part.strip() for part in s.split(",")],
                                  next_node="node_locks"))})
    return text, options


def node_locks(caller):
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    locks = prot.get("locks")

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
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    permissions = prot.get("permissions")

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
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    location = prot.get("location")

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
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    home = prot.get("home")

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
    metaprot = _get_menu_metaprot(caller)
    prot = metaprot.prototype
    dest = prot.get("dest")

    text = ["Set the prototype's |yDestination|n. This is usually only used for Exits."]
    if dest:
        text.append("Current destination is |y{dest}|n.".format(dest=dest))
    else:
        text.append("No destination is set (default).")
    text = "\n\n".join(text)
    options = _wizard_options("destination", "home", "meta_desc")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="dest",
                                  processor=lambda s: s.strip(),
                                  next_node="node_meta_desc"))})
    return text, options


def node_meta_desc(caller):

    metaprot = _get_menu_metaprot(caller)
    text = ["The |wMeta-Description|n briefly describes the prototype for viewing in listings."]
    desc = metaprot.desc

    if desc:
        text.append("The current meta desc is:\n\"|w{desc}|n\"".format(desc=desc))
    else:
        text.append("Description is currently unset.")
    text = "\n\n".join(text)
    options = _wizard_options("meta_desc", "meta_key", "meta_tags")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop='meta_desc',
                                  processor=lambda s: s.strip(),
                                  next_node="node_meta_tags"))})

    return text, options


def node_meta_tags(caller):
    metaprot = _get_menu_metaprot(caller)
    text = ["|wMeta-Tags|n can be used to classify and find prototypes. Tags are case-insensitive. "
            "Separate multiple by tags by commas."]
    tags = metaprot.tags

    if tags:
        text.append("The current tags are:\n|w{tags}|n".format(tags=tags))
    else:
        text.append("No tags are currently set.")
    text = "\n\n".join(text)
    options = _wizard_options("meta_tags", "meta_desc", "meta_locks")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="meta_tags",
                                  processor=lambda s: [
                                    str(part.strip().lower()) for part in s.split(",")],
                                  next_node="node_meta_locks"))})
    return text, options


def node_meta_locks(caller):
    metaprot = _get_menu_metaprot(caller)
    text = ["Set |wMeta-Locks|n on the prototype. There are two valid lock types: "
            "'edit' (who can edit the prototype) and 'use' (who can apply the prototype)\n"
            "(If you are unsure, leave as default.)"]
    locks = metaprot.locks
    if locks:
        text.append("Current lock is |w'{lockstring}'|n".format(lockstring=locks))
    else:
        text.append("Lock unset - if not changed the default lockstring will be set as\n"
                    "   |w'use:all(); edit:id({dbref}) or perm(Admin)'|n".format(dbref=caller.id))
    text = "\n\n".join(text)
    options = _wizard_options("meta_locks", "meta_tags", "index")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="meta_locks",
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


def start_olc(caller, session=None, metaproto=None):
    """
    Start menu-driven olc system for prototypes.

    Args:
        caller (Object or Account): The entity starting the menu.
        session (Session, optional): The individual session to get data.
        metaproto (MetaProto, optional): Given when editing an existing
            prototype rather than creating a new one.

    """
    menudata = {"node_index": node_index,
                "node_validate_prototype": node_validate_prototype,
                "node_meta_key": node_meta_key,
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
                "node_meta_desc": node_meta_desc,
                "node_meta_tags": node_meta_tags,
                "node_meta_locks": node_meta_locks,
                }
    OLCMenu(caller, menudata, startnode='node_index', session=session, olc_metaprot=metaproto)


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
