"""
OLC storage and sharing mechanism.

This sets up a central storage for prototypes. The idea is to make these
available in a repository for buildiers to use. Each prototype is stored
in a Script so that it can be tagged for quick sorting/finding and locked for limiting
access.

"""

from evennia.scripts.scripts import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.utils import make_iter
from evennia.utils.evtable import EvTable


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
    key = key.lower()
    locks = locks if locks else "use:all();edit:id({}) or edit:perm(Admin)".format(caller.id)
    tags = [(tag, "persistent_prototype") for tag in make_iter(tags)]

    stored_prototype = PersistentPrototype.objects.filter(db_key=key)

    if stored_prototype:
        stored_prototype = stored_prototype[0]
        if not stored_prototype.access(caller, 'edit'):
            PermissionError("{} does not have permission to edit prototype {}".format(caller, key))

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


def search_prototype(key=None, tags=None):
    """
    Find prototypes based on key and/or tags.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'persistent_protototype'
            tag category.
    Return:
        matches (queryset): All found PersistentPrototypes. This will
        be all prototypes if no arguments are given.

    Note:
        This will use the tags to make a subselection before attempting
        to match on the key. So if key/tags don't match up nothing will
        be found.

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
    prototypes = search_prototype(key, tags)

    if not prototypes:
        return None

    # gather access permissions as (key, desc, can_use, can_edit)
    prototypes = [(prototype.key, prototype.desc,
                   prototype.access(caller, "use"), prototype.access(caller, "edit"))
                  for prototype in prototypes]

    if not show_non_use:
        prototypes = [tup for tup in prototypes if tup[2]]
    if not show_non_edit:
        prototypes = [tup for tup in prototypes if tup[3]]

    if not prototypes:
        return None

    table = []
    for i in range(len(prototypes[0])):
        table.append([str(tup[i]) for tup in prototypes])
    table = EvTable("Key", "Desc", "Use", "Edit", table=table, crop=True, width=78)
    table.reformat_column(0, width=28)
    table.reformat_column(1, width=40)
    table.reformat_column(2, width=5)
    table.reformat_column(3, width=5)
    return table
