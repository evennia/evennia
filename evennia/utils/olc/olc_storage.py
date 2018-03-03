"""
OLC storage and sharing mechanism.

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

from collections import namedtuple
from django.conf import settings
from evennia.scripts.scripts import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.utils import make_iter, all_from_module
from evennia.utils.evtable import EvTable

# prepare the available prototypes defined in modules

_READONLY_PROTOTYPES = {}
_READONLY_PROTOTYPE_MODULES = {}

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


class PersistentPrototype(DefaultScript):
    """
    This stores a single prototype
    """
    def at_script_creation(self):
        self.key = "empty prototype"
        self.desc = "A prototype"


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
    locks = locks if locks else "use:all();edit:id({}) or edit:perm(Admin)".format(caller.id)
    tags = [(tag, "persistent_prototype") for tag in make_iter(tags)]

    if key in _READONLY_PROTOTYPES:
        mod = _READONLY_PROTOTYPE_MODULES.get(key, "N/A")
        raise PermissionError("{} is a read-only prototype "
                              "(defined as code in {}).".format(key_orig, mod))

    stored_prototype = PersistentPrototype.objects.filter(db_key=key)

    if stored_prototype:
        stored_prototype = stored_prototype[0]
        if not stored_prototype.access(caller, 'edit'):
            raise PermissionError("{} does not have permission to "
                                  "edit prototype {}".format(caller, key))

        if delete:
            stored_prototype.delete()
            return

        if desc:
            stored_prototype.desc = desc
        if tags:
            stored_prototype.tags.batch_add(*tags)
        if locks:
            stored_prototype.locks.add(locks)
        if prototype:
            stored_prototype.attributes.add("prototype", prototype)
    else:
        stored_prototype = create_script(
            PersistentPrototype, key=key, desc=desc, persistent=True,
            locks=locks, tags=tags, attributes=[("prototype", prototype)])
    return stored_prototype


def search_persistent_prototype(key=None, tags=None):
    """
    Find persistent (database-stored) prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'persistent_protototype'
            tag category.
    Return:
        matches (queryset): All found PersistentPrototypes

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
        # partial match on key
        matches = matches.filter(db_key=key) or matches.filter(db_key__icontains=key)
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


def search_prototype(key=None, tags=None):
    """
    Find prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'persistent_protototype'
            tag category.
    Return:
        matches (list): All found prototype dicts.

    Note:
        The available prototypes is a combination of those supplied in
        PROTOTYPE_MODULES and those stored from in-game. For the latter,
        this will use the tags to make a subselection before attempting
        to match on the key. So if key/tags don't match up nothing will
        be found.

    """
    matches = []
    if key and key in _READONLY_PROTOTYPES:
        matches.append(_READONLY_PROTOTYPES[key][3])
    else:
        matches.extend([prot.attributes.get("prototype")
                        for prot in search_persistent_prototype(key, tags)])
    return matches


def get_prototype_list(caller, key=None, tags=None, show_non_use=False, show_non_edit=True):
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
    # handle read-only prototypes separately
    readonly_prototypes = search_readonly_prototype(key, tags)

    # get use-permissions of readonly attributes (edit is always False)
    readonly_prototypes = [
        (metaproto.key,
         metaproto.desc,
         ("{}/N".format('Y'
          if caller.locks.check_lockstring(caller, metaproto.locks, access_type='use') else 'N')),
         ",".join(metaproto.tags))
        for metaproto in sorted(readonly_prototypes, key=lambda o: o.key)]

    # next, handle db-stored prototypes
    prototypes = search_persistent_prototype(key, tags)

    # gather access permissions as (key, desc, tags, can_use, can_edit)
    prototypes = [(prototype.key, prototype.desc,
                   "{}/{}".format('Y' if prototype.access(caller, "use") else 'N',
                                  'Y' if prototype.access(caller, "edit") else 'N'),
                   ",".join(prototype.tags.get(category="persistent_prototype")))
                  for prototype in sorted(prototypes, key=lambda o: o.key)]

    prototypes = prototypes + readonly_prototypes

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
