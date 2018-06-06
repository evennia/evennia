"""

Prototype utilities

"""


class PermissionError(RuntimeError):
    pass





def get_protparent_dict():
    """
    Get prototype parents.

    Returns:
        parent_dict (dict): A mapping {prototype_key: prototype} for all available prototypes.

    """
    return {prototype['prototype_key']: prototype for prototype in search_prototype()}


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
            caller, prototype.get('prototype_locks', ''), access_type='use')
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
    table = EvTable("Key", "Desc", "Use/Edit", "Tags", table=table, crop=True, width=width)
    table.reformat_column(0, width=22)
    table.reformat_column(1, width=29)
    table.reformat_column(2, width=11, align='c')
    table.reformat_column(3, width=16)
    return table


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
        prot['prototype_locks'] = "use:all();edit:all()"

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
