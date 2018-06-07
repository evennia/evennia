"""

Handling storage of prototypes, both database-based ones (DBPrototypes) and those defined in modules
(Read-only prototypes).

"""

from django.conf import settings

from evennia.scripts.scripts import DefaultScript
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_script
from evennia.utils.utils import (
    all_from_module, make_iter, is_iter, dbid_to_obj)
from evennia.locks.lockhandler import validate_lockstring, check_lockstring
from evennia.utils import logger
from evennia.utils.evtable import EvTable
from evennia.utils.prototypes.protfuncs import protfunc_parser


_MODULE_PROTOTYPE_MODULES = {}
_MODULE_PROTOTYPES = {}
_PROTOTYPE_META_NAMES = ("prototype_key", "prototype_desc", "prototype_tags", "prototype_locks")
_PROTOTYPE_TAG_CATEGORY = "spawned_by_prototype"


class PermissionError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    """
    Raised on prototype validation errors
    """
    pass


# helper functions

def value_to_obj(value, force=True):
    return dbid_to_obj(value, ObjectDB)


def value_to_obj_or_any(value):
    obj = dbid_to_obj(value, ObjectDB)
    return obj if obj is not None else value


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


def init_spawn_value(value, validator=None):
    """
    Analyze the prototype value and produce a value useful at the point of spawning.

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


# Prototype manager functions


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
