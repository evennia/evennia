"""

Handling storage of prototypes, both database-based ones (DBPrototypes) and those defined in modules
(Read-only prototypes).

"""

from django.conf import settings
from evennia.scripts.scripts import DefaultScript
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_script
from evennia.utils.utils import all_from_module, make_iter, callables_from_module, is_iter
from evennia.locks.lockhandler import validate_lockstring, check_lockstring
from evennia.utils import logger


_MODULE_PROTOTYPE_MODULES = {}
_MODULE_PROTOTYPES = {}


class ValidationError(RuntimeError):
    """
    Raised on prototype validation errors
    """
    pass


# module-based prototypes

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


# Db-based prototypes


class DbPrototype(DefaultScript):
    """
    This stores a single prototype, in an Attribute `prototype`.
    """
    def at_script_creation(self):
        self.key = "empty prototype"  # prototype_key
        self.desc = "A prototype"     # prototype_desc
        self.db.prototype = {}        # actual prototype


# General prototype functions


def check_permission(prototype_key, action, default=True):
    """
    Helper function to check access to actions on given prototype.

    Args:
        prototype_key (str): The prototype to affect.
        action (str): One of "spawn" or "edit".
        default (str): If action is unknown or prototype has no locks

    Returns:
        passes (bool): If permission for action is granted or not.

    """
    if action == 'edit':
        if prototype_key in _MODULE_PROTOTYPES:
            mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key, "N/A")
            logger.log_err("{} is a read-only prototype "
                           "(defined as code in {}).".format(prototype_key, mod))
            return False

    prototype = search_prototype(key=prototype_key)
    if not prototype:
        logger.log_err("Prototype {} not found.".format(prototype_key))
        return False

    lockstring = prototype.get("prototype_locks")

    if lockstring:
        return check_lockstring(None, lockstring, default=default, access_type=action)
    return default


def create_prototype(**kwargs):
    """
    Store a prototype persistently.

    Kwargs:
        prototype_key (str): This is required for any storage.
        All other kwargs are considered part of the new prototype dict.

    Returns:
        prototype (dict or None): The prototype stored using the given kwargs, None if deleting.

    Raises:
        prototypes.ValidationError: If prototype does not validate.

    Note:
        No edit/spawn locks will be checked here - if this function is called the caller
        is expected to have valid permissions.

    """

    def _to_batchtuple(inp, *args):
        "build tuple suitable for batch-creation"
        if is_iter(inp):
            # already a tuple/list, use as-is
            return inp
        return (inp, ) + args

    prototype_key = kwargs.get("prototype_key")
    if not prototype_key:
        raise ValidationError("Prototype requires a prototype_key")

    prototype_key = str(prototype_key).lower()

    # we can't edit a prototype defined in a module
    if prototype_key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(prototype_key, mod))

    # want to create- or edit
    prototype = kwargs

    # make sure meta properties are included with defaults
    prototype['prototype_desc'] = prototype.get('prototype_desc', '')
    locks = prototype.get('prototype_locks', "spawn:all();edit:perm(Admin)")
    is_valid, err = validate_lockstring(locks)
    if not is_valid:
        raise ValidationError("Lock error: {}".format(err))
    prototype["prototype_locks"] = locks
    prototype["prototype_tags"] = [
        _to_batchtuple(tag, "db_prototype")
        for tag in make_iter(prototype.get("prototype_tags", []))]

    stored_prototype = DbPrototype.objects.filter(db_key=prototype_key)

    if stored_prototype:
        # edit existing prototype
        stored_prototype = stored_prototype[0]

        stored_prototype.desc = prototype['prototype_desc']
        stored_prototype.tags.batch_add(*prototype['prototype_tags'])
        stored_prototype.locks.add(prototype['prototype_locks'])
        stored_prototype.attributes.add('prototype', prototype)
    else:
        # create a new prototype
        stored_prototype = create_script(
            DbPrototype, key=prototype_key, desc=prototype['prototype_desc'], persistent=True,
            locks=locks, tags=prototype['prototype_tags'], attributes=[("prototype", prototype)])
    return stored_prototype


def delete_prototype(key, caller=None):
    """
    Delete a stored prototype

    Args:
        key (str): The persistent prototype to delete.
        caller (Account or Object, optionsl): Caller aiming to delete a prototype.
            Note that no locks will be checked if`caller` is not passed.
    Returns:
        success (bool): If deletion worked or not.
    Raises:
        PermissionError: If 'edit' lock was not passed or deletion failed for some other reason.

    """
    if prototype_key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(prototype_key, mod))

    stored_prototype = DbPrototype.objects.filter(db_key=prototype_key)

    if not stored_prototype:
        raise PermissionError("Prototype {} was not found.".format(prototype_key))
    if caller:
        if not stored_prototype.access(caller, 'edit'):
            raise PermissionError("{} does not have permission to "
                                  "delete prototype {}.".format(caller, prototype_key))
    stored_prototype.delete()
    return True


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
        PROTOTYPE_MODULES and those stored in the database. Note that if
        tags are given and the prototype has no tags defined, it will not
        be found as a match.

    """
    # search module prototypes

    mod_matches = {}
    if tags:
        # use tags to limit selection
        tagset = set(tags)
        mod_matches = {prototype_key: prototype
                       for prototype_key, prototype in _MODULE_PROTOTYPES.items()
                       if tagset.intersection(prototype.get("prototype_tags", []))}
    else:
        mod_matches = _MODULE_PROTOTYPES
    if key:
        if key in mod_matches:
            # exact match
            module_prototypes = [mod_matches[key]]
        else:
            # fuzzy matching
            module_prototypes = [prototype for prototype_key, prototype in mod_matches.items()
                                 if key in prototype_key]
    else:
        module_prototypes = [match for match in mod_matches.values()]

    # search db-stored prototypes

    if tags:
        # exact match on tag(s)
        tags = make_iter(tags)
        tag_categories = ["db_prototype" for _ in tags]
        db_matches = DbPrototype.objects.get_by_tag(tags, tag_categories)
    else:
        db_matches = DbPrototype.objects.all()
    if key:
        # exact or partial match on key
        db_matches = db_matches.filter(db_key=key) or db_matches.filter(db_key__icontains=key)
        # return prototype
    db_prototypes = [dict(dbprot.attributes.get("prototype", {})) for dbprot in db_matches]

    matches = db_prototypes + module_prototypes
    nmatches = len(matches)
    if nmatches > 1 and key:
        key = key.lower()
        # avoid duplicates if an exact match exist between the two types
        filter_matches = [mta for mta in matches
                          if mta.get('prototype_key') and mta['prototype_key'] == key]
        if filter_matches and len(filter_matches) < nmatches:
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
    prot = search_prototype(prot)
    if not prot or len(prot) > 1:
        # no unambiguous prototype found - build new prototype
        prot = {}
        prot['prototype_key'] = "From-Object-{}-{}".format(
                obj.key, hashlib.md5(str(time.time())).hexdigest()[:6])
        prot['prototype_desc'] = "Built from {}".format(str(obj))
        prot['prototype_locks'] = "spawn:all();edit:all()"

    prot['key'] = obj.db_key or hashlib.md5(str(time.time())).hexdigest()[:6]
    prot['location'] = obj.db_location
    prot['home'] = obj.db_home
    prot['destination'] = obj.db_destination
    prot['typeclass'] = obj.db_typeclass_path
    prot['locks'] = obj.locks.all()
    prot['permissions'] = obj.permissions.get()
    prot['aliases'] = obj.aliases.get()
    prot['tags'] = [(tag.key, tag.category, tag.data)
                    for tag in obj.tags.get(return_tagobj=True, return_list=True)]
    prot['attrs'] = [(attr.key, attr.value, attr.category, attr.locks)
                     for attr in obj.attributes.get(return_obj=True, return_list=True)]

    return prot


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
            caller, prototype.get('prototype_locks', ''), access_type='spawn')
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
    table = EvTable("Key", "Desc", "Spawn/Edit", "Tags", table=table, crop=True, width=width)
    table.reformat_column(0, width=22)
    table.reformat_column(1, width=29)
    table.reformat_column(2, width=11, align='c')
    table.reformat_column(3, width=16)
    return table



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
    prototype_key = prototype if isinstance(prototype, basestring) else prototype['prototype_key']
    prototype_obj = search_db_prototype(prototype_key, return_queryset=True)
    prototype_obj = prototype_obj[0] if prototype_obj else None
    new_prototype = prototype_obj.db.prototype
    objs = ObjectDB.objects.get_by_tag(prototype_key, category=_PROTOTYPE_TAG_CATEGORY)

    if not objs:
        return 0

    if not diff:
        diff = prototype_diff_from_object(new_prototype, objs[0])

    changed = 0
    for obj in objs:
        do_save = False
        for key, directive in diff.items():
            val = new_prototype[key]
            if directive in ('UPDATE', 'REPLACE'):
                do_save = True
                if key == 'key':
                    obj.db_key = validate_spawn_value(val, str)
                elif key == 'typeclass':
                    obj.db_typeclass_path = validate_spawn_value(val, str)
                elif key == 'location':
                    obj.db_location = validate_spawn_value(val, _to_obj)
                elif key == 'home':
                    obj.db_home = validate_spawn_value(val, _to_obj)
                elif key == 'destination':
                    obj.db_destination = validate_spawn_value(val, _to_obj)
                elif key == 'locks':
                    if directive == 'REPLACE':
                        obj.locks.clear()
                    obj.locks.add(validate_spawn_value(val, str))
                elif key == 'permissions':
                    if directive == 'REPLACE':
                        obj.permissions.clear()
                    obj.permissions.batch_add(validate_spawn_value(val, make_iter))
                elif key == 'aliases':
                    if directive == 'REPLACE':
                        obj.aliases.clear()
                    obj.aliases.batch_add(validate_spawn_value(val, make_iter))
                elif key == 'tags':
                    if directive == 'REPLACE':
                        obj.tags.clear()
                    obj.tags.batch_add(validate_spawn_value(val, make_iter))
                elif key == 'attrs':
                    if directive == 'REPLACE':
                        obj.attributes.clear()
                    obj.attributes.batch_add(validate_spawn_value(val, make_iter))
                elif key == 'exec':
                    # we don't auto-rerun exec statements, it would be huge security risk!
                    pass
                else:
                    obj.attributes.add(key, validate_spawn_value(val, _to_obj))
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
