"""

Handling storage of prototypes, both database-based ones (DBPrototypes) and those defined in modules
(Read-only prototypes). Also contains utility functions, formatters and manager functions.

"""

import hashlib
import time

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _

from evennia.locks.lockhandler import check_lockstring, validate_lockstring
from evennia.objects.models import ObjectDB
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import Attribute
from evennia.utils import dbserialize, logger
from evennia.utils.create import create_script
from evennia.utils.evmore import EvMore
from evennia.utils.evtable import EvTable
from evennia.utils.funcparser import FuncParser
from evennia.utils.utils import (
    all_from_module,
    class_from_module,
    dbid_to_obj,
    is_iter,
    justify,
    make_iter,
    variable_from_module,
)

_MODULE_PROTOTYPE_MODULES = {}
_MODULE_PROTOTYPES = {}
_PROTOTYPE_META_NAMES = (
    "prototype_key",
    "prototype_desc",
    "prototype_tags",
    "prototype_locks",
    "prototype_parent",
)
_PROTOTYPE_RESERVED_KEYS = _PROTOTYPE_META_NAMES + (
    "key",
    "aliases",
    "typeclass",
    "location",
    "home",
    "destination",
    "permissions",
    "locks",
    "tags",
    "attrs",
)
_ERRSTR = _("Error")
_WARNSTR = _("Warning")
PROTOTYPE_TAG_CATEGORY = "from_prototype"
_PROTOTYPE_TAG_META_CATEGORY = "db_prototype"

_PROTOTYPE_FALLBACK_LOCK = "spawn:all();edit:all()"

# the protfunc parser
FUNC_PARSER = FuncParser(settings.PROT_FUNC_MODULES)


class PermissionError(RuntimeError):
    pass


class ValidationError(RuntimeError):
    """
    Raised on prototype validation errors
    """

    pass


def homogenize_prototype(prototype, custom_keys=None):
    """
    Homogenize the more free-form prototype supported pre Evennia 0.7 into the stricter form.

    Args:
        prototype (dict): Prototype.
        custom_keys (list, optional): Custom keys which should not be interpreted as attrs, beyond
            the default reserved keys.

    Returns:
        homogenized (dict): Prototype where all non-identified keys grouped as attributes and other
            homogenizations like adding missing prototype_keys and setting a default typeclass.

    """
    if not prototype or isinstance(prototype, str):
        return prototype

    reserved = _PROTOTYPE_RESERVED_KEYS + (custom_keys or ())

    # correct cases of setting None for certain values
    for protkey in prototype:
        if prototype[protkey] is None:
            if protkey in ("attrs", "tags", "prototype_tags"):
                prototype[protkey] = []
            elif protkey in ("prototype_key", "prototype_desc"):
                prototype[protkey] = ""

    homogenized = {}
    homogenized_tags = []
    homogenized_attrs = []
    homogenized_parents = []

    for key, val in prototype.items():
        if key in reserved:
            # check all reserved keys
            if key == "tags":
                # tags must be on form [(tag, category, data), ...]
                tags = make_iter(prototype.get("tags", []))
                for tag in tags:
                    if not is_iter(tag):
                        homogenized_tags.append((tag, None, None))
                    elif tag:
                        ntag = len(tag)
                        if ntag == 1:
                            homogenized_tags.append((tag[0], None, None))
                        elif ntag == 2:
                            homogenized_tags.append((tag[0], tag[1], None))
                        else:
                            homogenized_tags.append(tag[:3])

            elif key == "attrs":
                attrs = list(prototype.get("attrs", []))  # break reference
                for attr in attrs:
                    # attrs must be on form [(key, value, category, lockstr)]
                    if not is_iter(attr):
                        logger.log_error(
                            f"Prototype's 'attr' field must be a list of tuples: {prototype}"
                        )
                    elif attr:
                        nattr = len(attr)
                        if nattr == 1:
                            # we assume a None-value
                            homogenized_attrs.append((attr[0], None, None, ""))
                        elif nattr == 2:
                            homogenized_attrs.append((attr[0], attr[1], None, ""))
                        elif nattr == 3:
                            homogenized_attrs.append((attr[0], attr[1], attr[2], ""))
                        else:
                            homogenized_attrs.append(attr[:4])

            elif key == "prototype_parent":
                # homogenize any prototype-parents embedded directly as dicts
                protparents = prototype.get("prototype_parent", [])
                if isinstance(protparents, dict):
                    protparents = [protparents]
                for parent in make_iter(protparents):
                    if isinstance(parent, dict):
                        # recursively homogenize directly embedded prototype parents
                        homogenized_parents.append(
                            homogenize_prototype(parent, custom_keys=custom_keys)
                        )
                    else:
                        # normal prototype-parent names are added as-is
                        homogenized_parents.append(parent)

            else:
                # another reserved key
                homogenized[key] = val
        else:
            # unreserved keys -> attrs
            homogenized_attrs.append((key, val, None, ""))
    if homogenized_attrs:
        homogenized["attrs"] = homogenized_attrs
    if homogenized_tags:
        homogenized["tags"] = homogenized_tags
    if homogenized_parents:
        homogenized["prototype_parent"] = homogenized_parents

    # add required missing parts that had defaults before

    homogenized["prototype_key"] = homogenized.get(
        "prototype_key",
        # assign a random hash as key
        "prototype-{}".format(hashlib.md5(bytes(str(time.time()), "utf-8")).hexdigest()[:7]),
    )
    homogenized["prototype_tags"] = homogenized.get("prototype_tags", [])
    homogenized["prototype_locks"] = homogenized.get("prototype_lock", _PROTOTYPE_FALLBACK_LOCK)
    homogenized["prototype_desc"] = homogenized.get("prototype_desc", "")
    if "typeclass" not in prototype and "prototype_parent" not in prototype:
        homogenized["typeclass"] = settings.BASE_OBJECT_TYPECLASS

    return homogenized


# module/dict-based prototypes


def load_module_prototypes(*mod_or_prototypes, override=True):
    """
    Load module prototypes. Also prototype-dicts passed directly to this function are considered
    'module' prototypes (they are impossible to change) but will have a module of None.

    Args:
        *mod_or_prototypes (module or dict): Each arg should be a separate module or
            prototype-dict to load. If none are given, `settings.PROTOTYPE_MODULES` will be used.
        override (bool, optional): If prototypes should override existing ones already loaded.
            Disabling this can allow for injecting prototypes into the system dynamically while
            still allowing same prototype-keys to be overridden from settings (even though settings
            is usually loaded before dynamic loading).

    Note:
        This is called (without arguments) by `evennia.__init__` as Evennia initializes. It's
        important to do this late so as to not interfere with evennia initialization. But it can
        also be used later to add more prototypes to the library on the fly. This is requried
        before a module-based prototype can be accessed by prototype-key.

    """
    global _MODULE_PROTOTYPE_MODULES, _MODULE_PROTOTYPES

    def _prototypes_from_module(mod):
        """
        Load prototypes from a module, first by looking for a global list PROTOTYPE_LIST (a list of
        dict-prototypes), and if not found, assuming all global-level dicts in the module are
        prototypes.

        Args:
            mod (module): The module to load from.evennia

        Returns:
            list: A list of tuples `(prototype_key, prototype-dict)` where the prototype
                has been homogenized.

        """
        prots = []
        prototype_list = variable_from_module(mod, "PROTOTYPE_LIST")
        if prototype_list:
            # found mod.PROTOTYPE_LIST - this should be a list of valid
            # prototype dicts that must have 'prototype_key' set.
            for prot in prototype_list:
                if not isinstance(prot, dict):
                    logger.log_err(
                        f"Prototype read from {mod}.PROTOTYPE_LIST is not a dict (skipping): {prot}"
                    )
                    continue
                elif "prototype_key" not in prot:
                    logger.log_err(
                        f"Prototype read from {mod}.PROTOTYPE_LIST "
                        f"is missing the 'prototype_key' (skipping): {prot}"
                    )
                    continue
                prots.append((prot["prototype_key"], homogenize_prototype(prot)))
        else:
            # load all global dicts in module as prototypes. If the prototype_key
            # is not given, the variable name will be used.
            for variable_name, prot in all_from_module(mod).items():
                if isinstance(prot, dict):
                    if "prototype_key" not in prot:
                        prot["prototype_key"] = variable_name.lower()
                    prots.append((prot["prototype_key"], homogenize_prototype(prot)))
        return prots

    def _cleanup_prototype(prototype_key, prototype, mod=None):
        """
        We need to handle externally determined prototype-keys and to make sure
        the prototype contains all needed meta information.

        Args:
            prototype_key (str): The determined name of the prototype.
            prototype (dict): The prototype itself.
            mod (module, optional): The module the prototype was loaded from, if any.

        Returns:
            dict: The cleaned up prototype.

        """
        actual_prot_key = prototype.get("prototype_key", prototype_key).lower()
        prototype.update(
            {
                "prototype_key": actual_prot_key,
                "prototype_desc": (
                    prototype["prototype_desc"] if "prototype_desc" in prototype else (mod or "N/A")
                ),
                "prototype_locks": (
                    prototype["prototype_locks"]
                    if "prototype_locks" in prototype
                    else "use:all();edit:false()"
                ),
                "prototype_tags": list(
                    set(list(make_iter(prototype.get("prototype_tags", []))) + ["module"])
                ),
            }
        )
        return prototype

    if not mod_or_prototypes:
        # in principle this means PROTOTYPE_MODULES could also contain prototypes, but that is
        # rarely useful ...
        mod_or_prototypes = settings.PROTOTYPE_MODULES

    for mod_or_dict in mod_or_prototypes:

        if isinstance(mod_or_dict, dict):
            # a single prototype; we must make sure it has its key
            prototype_key = mod_or_dict.get("prototype_key")
            if not prototype_key:
                raise ValidationError(
                    f"The prototype {mod_or_dict} does not contain a 'prototype_key'"
                )
            prots = [(prototype_key, mod_or_dict)]
            mod = None
        else:
            # a module (or path to module). This can contain many prototypes; they can be keyed by
            # variable-name too
            prots = _prototypes_from_module(mod_or_dict)
            mod = repr(mod_or_dict)

        # store all found prototypes
        for prototype_key, prot in prots:
            prototype = _cleanup_prototype(prototype_key, prot, mod=mod)
            # the key can change since in-proto key is given prio over variable-name-based keys
            actual_prototype_key = prototype["prototype_key"]

            if actual_prototype_key in _MODULE_PROTOTYPES and not override:
                # don't override - useful to still let settings replace dynamic inserts
                continue

            # make sure the prototype contains all meta info
            _MODULE_PROTOTYPES[actual_prototype_key] = prototype
            # track module path for display purposes
            _MODULE_PROTOTYPE_MODULES[actual_prototype_key.lower()] = mod


# Db-based prototypes


class DBPrototypeCache:
    """
    Cache DB-stored prototypes; it can still be slow to initially load 1000s of
    prototypes, due to having to deserialize all prototype-dicts, but after the
    first time the cache will be populated and things will be fast.

    """

    def __init__(self):
        self._cache = {}

    def get(self, db_prot_id):
        return self._cache.get(db_prot_id, None)

    def add(self, db_prot_id, prototype):
        self._cache[db_prot_id] = prototype

    def remove(self, db_prot_id):
        self._cache.pop(db_prot_id, None)

    def clear(self):
        self._cache = {}

    def replace(self, all_data):
        self._cache = all_data


DB_PROTOTYPE_CACHE = DBPrototypeCache()


class DbPrototype(DefaultScript):
    """
    This stores a single prototype, in an Attribute `prototype`.

    """

    def at_script_creation(self):
        self.key = "empty prototype"  # prototype_key
        self.desc = "A prototype"  # prototype_desc (.tags are used for prototype_tags)
        self.db.prototype = {}  # actual prototype

    @property
    def prototype(self):
        "Make sure to decouple from db!"
        return dbserialize.deserialize(self.attributes.get("prototype", {}))

    @prototype.setter
    def prototype(self, prototype):
        self.attributes.add("prototype", prototype)


# Prototype manager functions


def save_prototype(prototype):
    """
    Create/Store a prototype persistently.

    Args:
        prototype (dict): The prototype to save. A `prototype_key` key is
            required.

    Returns:
        prototype (dict or None): The prototype stored using the given kwargs, None if deleting.

    Raises:
        prototypes.ValidationError: If prototype does not validate.

    Note:
        No edit/spawn locks will be checked here - if this function is called the caller
        is expected to have valid permissions.

    """
    in_prototype = prototype
    in_prototype = homogenize_prototype(in_prototype)

    def _to_batchtuple(inp, *args):
        "build tuple suitable for batch-creation"
        if is_iter(inp):
            # already a tuple/list, use as-is
            return inp
        return (inp,) + args

    prototype_key = in_prototype.get("prototype_key")
    if not prototype_key:
        raise ValidationError(_("Prototype requires a prototype_key"))

    prototype_key = str(prototype_key).lower()

    # we can't edit a prototype defined in a module
    if prototype_key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key)
        if mod:
            err = _("{protkey} is a read-only prototype (defined as code in {module}).")
        else:
            err = _("{protkey} is a read-only prototype (passed directly as a dict).")
        raise PermissionError(err.format(protkey=prototype_key, module=mod))

    # make sure meta properties are included with defaults
    in_prototype["prototype_desc"] = in_prototype.get(
        "prototype_desc", prototype.get("prototype_desc", "")
    )
    prototype_locks = in_prototype.get(
        "prototype_locks", prototype.get("prototype_locks", _PROTOTYPE_FALLBACK_LOCK)
    )
    is_valid, err = validate_lockstring(prototype_locks)
    if not is_valid:
        raise ValidationError("Lock error: {}".format(err))
    in_prototype["prototype_locks"] = prototype_locks

    prototype_tags = [
        _to_batchtuple(tag, _PROTOTYPE_TAG_META_CATEGORY)
        for tag in make_iter(
            in_prototype.get("prototype_tags", prototype.get("prototype_tags", []))
        )
    ]
    in_prototype["prototype_tags"] = prototype_tags

    stored_prototype = DbPrototype.objects.filter(db_key=prototype_key)
    if stored_prototype:
        # edit existing prototype
        stored_prototype = stored_prototype[0]
        stored_prototype.desc = in_prototype["prototype_desc"]
        if prototype_tags:
            stored_prototype.tags.clear(category=PROTOTYPE_TAG_CATEGORY)
            stored_prototype.tags.batch_add(*in_prototype["prototype_tags"])
        stored_prototype.locks.add(in_prototype["prototype_locks"])
        stored_prototype.attributes.add("prototype", in_prototype)
    else:
        # create a new prototype
        stored_prototype = create_script(
            DbPrototype,
            key=prototype_key,
            desc=in_prototype["prototype_desc"],
            persistent=True,
            locks=prototype_locks,
            tags=in_prototype["prototype_tags"],
            attributes=[("prototype", in_prototype)],
        )
    DB_PROTOTYPE_CACHE.add(stored_prototype.id, stored_prototype.prototype)
    return stored_prototype.prototype


create_prototype = save_prototype  # alias


def delete_prototype(prototype_key, caller=None):
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
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key)
        if mod:
            err = _("{protkey} is a read-only prototype (defined as code in {module}).")
        else:
            err = _("{protkey} is a read-only prototype (passed directly as a dict).")
        raise PermissionError(err.format(protkey=prototype_key, module=mod))

    stored_prototype = DbPrototype.objects.filter(db_key__iexact=prototype_key)

    if not stored_prototype:
        raise PermissionError(
            _("Prototype {prototype_key} was not found.").format(prototype_key=prototype_key)
        )

    stored_prototype = stored_prototype[0]
    if caller:
        if not stored_prototype.access(caller, "edit"):
            raise PermissionError(
                _(
                    "{caller} needs explicit 'edit' permissions to "
                    "delete prototype {prototype_key}."
                ).format(caller=caller, prototype_key=prototype_key)
            )
    DB_PROTOTYPE_CACHE.remove(stored_prototype.id)
    stored_prototype.delete()
    return True


def search_prototype(
    key=None,
    tags=None,
    require_single=False,
    return_iterators=False,
    no_db=False,
):
    """
    Find prototypes based on key and/or tags, or all prototypes.

    Keyword Args:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.
        require_single (bool): If set, raise KeyError if the result
            was not found or if there are multiple matches.
        return_iterators (bool): Optimized return for large numbers of db-prototypes.
            If set, separate returns of module based prototypes and paginate
            the db-prototype return.
        no_db (bool): Optimization. If set, skip querying for database-generated prototypes and only
            include module-based prototypes. This can lead to a dramatic speedup since
            module-prototypes are static and require no db-lookup.

    Return:
        matches (list): Default return, all found prototype dicts. Empty list if
            no match was found. Note that if neither `key` nor `tags`
            were given, *all* available prototypes will be returned.
        list, queryset: If `return_iterators` are found, this is a list of
            module-based prototypes followed by a queryset of
            db-prototypes.

    Raises:
        KeyError: If `require_single` is True and there are 0 or >1 matches.

    Note:
        The available prototypes is a combination of those supplied in
        PROTOTYPE_MODULES and those stored in the database. Note that if
        tags are given and the prototype has no tags defined, it will not
        be found as a match.

    """

    def _search_module_based_prototypes(key, tags):
        """
        Helper function to load module-based prots.

        """
        # This will load the prototypes the first time they are searched
        loaded = getattr(load_module_prototypes, "_LOADED", False)
        if not loaded:
            load_module_prototypes()
            setattr(load_module_prototypes, "_LOADED", True)

        # search module prototypes

        mod_matches = {}
        if tags:
            # use tags to limit selection
            tagset = set(tags)
            mod_matches = {
                prototype_key: prototype
                for prototype_key, prototype in _MODULE_PROTOTYPES.items()
                if tagset.intersection(prototype.get("prototype_tags", []))
            }
        else:
            mod_matches = _MODULE_PROTOTYPES

        fuzzy_match_db = True
        if key:
            if key in mod_matches:
                # exact match
                module_prototypes = [mod_matches[key].copy()]
                fuzzy_match_db = False
            else:
                # fuzzy matching
                module_prototypes = [
                    prototype
                    for prototype_key, prototype in mod_matches.items()
                    if key in prototype_key
                ]
        else:
            # note - we return a copy of the prototype dict, otherwise using this with e.g.
            # prototype_from_object will modify the base prototype for every object
            module_prototypes = [match.copy() for match in mod_matches.values()]

        return module_prototypes, fuzzy_match_db

    def _search_db_based_prototypes(key, tags, fuzzy_matching):
        """
        Helper function for loading db-based prots.

        """
        # search db-stored prototypes
        if tags:
            # exact match on tag(s)
            tags = make_iter(tags)
            tag_categories = ["db_prototype" for _ in tags]
            query = DbPrototype.objects.get_by_tag(tags, tag_categories)
        else:
            query = DbPrototype.objects.all()

        if key:
            # exact or partial match on key
            exact_match = query.filter(Q(db_key__iexact=key))
            if not exact_match and fuzzy_matching:
                # try with partial match instead
                query = query.filter(Q(db_key__icontains=key))
            else:
                query = exact_match

        # convert to prototype, cached or from db

        db_matches = []
        not_found = []
        for db_id in query.values_list("id", flat=True).order_by("db_key"):
            prot = DB_PROTOTYPE_CACHE.get(db_id)
            if prot:
                db_matches.append(prot)
            else:
                not_found.append(db_id)

        if not_found:
            new_db_matches = (
                Attribute.objects.filter(scriptdb__pk__in=not_found, db_key="prototype")
                .values_list("db_value", flat=True)
                .order_by("scriptdb__db_key")
            )
            for db_id, prot in zip(not_found, new_db_matches):
                DB_PROTOTYPE_CACHE.add(db_id, prot)
            db_matches.extend(list(new_db_matches))

        return db_matches

    if key:
        key = key.lower()

    module_prototypes, fuzzy_match_db = _search_module_based_prototypes(key, tags)

    db_prototypes = [] if no_db else _search_db_based_prototypes(key, tags, fuzzy_match_db)

    if key and require_single:
        num = len(module_prototypes) + len(db_prototypes)
        if num != 1:
            raise KeyError(_(f"Found {num} matching prototypes."))

    if return_iterators:
        # trying to get the entire set of prototypes - we must paginate
        # the result instead of trying to fetch the entire set at once
        return db_prototypes, module_prototypes
    else:
        # full fetch, no pagination (compatibility mode)
        return list(db_prototypes) + module_prototypes


def search_objects_with_prototype(prototype_key):
    """
    Retrieve all object instances created by a given prototype.

    Args:
        prototype_key (str): The exact (and unique) prototype identifier to query for.

    Returns:
        matches (Queryset): All matching objects spawned from this prototype.

    """
    return ObjectDB.objects.get_by_tag(key=prototype_key, category=PROTOTYPE_TAG_CATEGORY)


class PrototypeEvMore(EvMore):
    """
    Listing 1000+ prototypes can be very slow. So we customize EvMore to
    display an EvTable per paginated page rather than to try creating an
    EvTable for the entire dataset and then paginate it.

    """

    def __init__(self, caller, *args, session=None, **kwargs):
        """
        Store some extra properties on the EvMore class

        """
        self.show_non_use = kwargs.pop("show_non_use", False)
        self.show_non_edit = kwargs.pop("show_non_edit", False)
        super().__init__(caller, *args, session=session, **kwargs)

    def init_pages(self, inp):
        """
        This will be initialized with a tuple (mod_prototype_list, paginated_db_query)
        and we must handle these separately since they cannot be paginated in the same
        way. We will build the prototypes so that the db-prototypes come first (they
        are likely the most volatile), followed by the mod-prototypes.

        """
        dbprot_query, modprot_list = inp
        # set the number of entries per page to half the reported height of the screen
        # to account for long descs etc
        dbprot_paged = Paginator(dbprot_query, max(1, int(self.height / 2)))

        # we separate the different types of data, so we track how many pages there are
        # of each.
        n_mod = len(modprot_list)
        self._npages_mod = n_mod // self.height + (0 if n_mod % self.height == 0 else 1)
        self._db_count = dbprot_paged.count if dbprot_paged else 0
        self._npages_db = dbprot_paged.num_pages if self._db_count > 0 else 0
        # total number of pages
        self._npages = self._npages_mod + self._npages_db
        self._data = (dbprot_paged, modprot_list)
        self._paginator = self.prototype_paginator

    def prototype_paginator(self, pageno):
        """
        The listing is separated in db/mod prototypes, so we need to figure out which
        one to pick based on the page number. Also, pageno starts from 0.

        """
        dbprot_pages, modprot_list = self._data

        if self._db_count and pageno < self._npages_db:
            return dbprot_pages.page(pageno + 1)
        else:
            # get the correct slice, adjusted for the db-prototypes
            pageno = max(0, pageno - self._npages_db)
            return modprot_list[pageno * self.height : pageno * self.height + self.height]

    def page_formatter(self, page):
        """
        Input is a queryset page from django.Paginator

        """
        caller = self._caller

        # get use-permissions of readonly attributes (edit is always False)
        table = EvTable(
            "|wKey|n",
            "|wSpawn/Edit|n",
            "|wTags|n",
            "|wDesc|n",
            border="tablecols",
            crop=True,
            width=self.width,
        )

        for prototype in page:
            lock_use = caller.locks.check_lockstring(
                caller, prototype.get("prototype_locks", ""), access_type="spawn", default=True
            )
            if not self.show_non_use and not lock_use:
                continue
            if prototype.get("prototype_key", "") in _MODULE_PROTOTYPES:
                lock_edit = False
            else:
                lock_edit = caller.locks.check_lockstring(
                    caller, prototype.get("prototype_locks", ""), access_type="edit", default=True
                )
            if not self.show_non_edit and not lock_edit:
                continue
            ptags = []
            for ptag in prototype.get("prototype_tags", []):
                if is_iter(ptag):
                    if len(ptag) > 1:
                        ptags.append("{}".format(ptag[0]))
                    else:
                        ptags.append(ptag[0])
                else:
                    ptags.append(str(ptag))

            table.add_row(
                prototype.get("prototype_key", "<unset>"),
                "{}/{}".format("Y" if lock_use else "N", "Y" if lock_edit else "N"),
                ", ".join(list(set(ptags))),
                prototype.get("prototype_desc", "<unset>"),
            )

        return str(table)


def list_prototypes(
    caller, key=None, tags=None, show_non_use=False, show_non_edit=True, session=None
):
    """
    Collate a list of found prototypes based on search criteria and access.

    Args:
        caller (Account or Object): The object requesting the list.
        key (str, optional): Exact or partial prototype key to query for.
        tags (str or list, optional): Tag key or keys to query for.
        show_non_use (bool, optional): Show also prototypes the caller may not use.
        show_non_edit (bool, optional): Show also prototypes the caller may not edit.
        session (Session, optional): If given, this is used for display formatting.
    Returns:
        PrototypeEvMore: An EvMore subclass optimized for prototype listings.
        None: If no matches were found. In this case the caller has already been notified.

    """
    # this allows us to pass lists of empty strings
    tags = [tag for tag in make_iter(tags) if tag]

    dbprot_query, modprot_list = search_prototype(key, tags, return_iterators=True)

    if not dbprot_query and not modprot_list:
        caller.msg(_("No prototypes found."), session=session)
        return None

    # get specific prototype (one value or exception)
    return PrototypeEvMore(
        caller,
        (dbprot_query, modprot_list),
        session=session,
        show_non_use=show_non_use,
        show_non_edit=show_non_edit,
    )


def validate_prototype(
    prototype, protkey=None, protparents=None, is_prototype_base=True, strict=True, _flags=None
):
    """
    Run validation on a prototype, checking for inifinite regress.

    Args:
        prototype (dict): Prototype to validate.
        protkey (str, optional): The name of the prototype definition. If not given, the prototype
            dict needs to have the `prototype_key` field set.
        protparents (dict, optional): Additional prototype-parents, supposedly provided specifically
            for this prototype. If given, matching parents will first be taken from this
            dict rather than from the global set of prototypes found via settings/database.
        is_prototype_base (bool, optional): We are trying to create a new object *based on this
            object*. This means we can't allow 'mixin'-style prototypes without typeclass/parent
            etc.
        strict (bool, optional): If unset, don't require needed keys, only check against infinite
            recursion etc.
        _flags (dict, optional): Internal work dict that should not be set externally.
    Raises:
        RuntimeError: If prototype has invalid structure.
        RuntimeWarning: If prototype has issues that would make it unsuitable to build an object
            with (it may still be useful as a mix-in prototype).

    """
    assert isinstance(prototype, dict)
    protparents = {} if protparents is None else protparents

    if _flags is None:
        _flags = {"visited": [], "depth": 0, "typeclass": False, "errors": [], "warnings": []}

    protkey = protkey and protkey.lower() or prototype.get("prototype_key", None)

    if strict and not bool(protkey):
        _flags["errors"].append(_("Prototype lacks a 'prototype_key'."))
        protkey = "[UNSET]"

    typeclass = prototype.get("typeclass")
    prototype_parent = prototype.get("prototype_parent", [])

    if strict and not (typeclass or prototype_parent):
        if is_prototype_base:
            _flags["errors"].append(
                _("Prototype {protkey} requires `typeclass` or 'prototype_parent'.").format(
                    protkey=protkey
                )
            )
        else:
            _flags["warnings"].append(
                _(
                    "Prototype {protkey} can only be used as a mixin since it lacks "
                    "'typeclass' or 'prototype_parent' keys."
                ).format(protkey=protkey)
            )

    if strict and typeclass:
        try:
            class_from_module(typeclass)
        except ImportError as err:
            _flags["errors"].append(
                _(
                    "{err}: Prototype {protkey} is based on typeclass {typeclass}, "
                    "which could not be imported!"
                ).format(err=err, protkey=protkey, typeclass=typeclass)
            )

    if prototype_parent and isinstance(prototype_parent, dict):
        # the protparent is already embedded as a dict;
        prototype_parent = [prototype_parent]

    # recursively traverse prototype_parent chain
    for protstring in make_iter(prototype_parent):
        if isinstance(protstring, dict):
            # an already embedded prototype_parent
            protparent = protstring
            protstring = None
        else:
            protstring = protstring.lower()
            if protkey is not None and protstring == protkey:
                _flags["errors"].append(
                    _("Prototype {protkey} tries to parent itself.").format(protkey=protkey)
                )

            # get prototype parent, first try custom set, then search globally
            protparent = protparents.get(protstring)
            if not protparent:
                protparent = search_prototype(key=protstring, require_single=True)
                if protparent:
                    protparent = protparent[0]
                else:
                    _flags["errors"].append(
                        _(
                            "Prototype {protkey}'s `prototype_parent` (named '{parent}') was not"
                            " found."
                        ).format(protkey=protkey, parent=protstring)
                    )

        # check for infinite recursion
        if id(prototype) in _flags["visited"]:
            _flags["errors"].append(
                _("{protkey} has infinite nesting of prototypes.").format(
                    protkey=protkey or prototype
                )
            )

        if _flags["errors"]:
            raise RuntimeError(f"{_ERRSTR}: " + f"\n{_ERRSTR}: ".join(_flags["errors"]))
        _flags["visited"].append(id(prototype))
        _flags["depth"] += 1

        # next step of recursive validation
        validate_prototype(
            protparent,
            protkey=protstring,
            protparents=protparents,
            is_prototype_base=is_prototype_base,
            _flags=_flags,
        )

        _flags["visited"].pop()
        _flags["depth"] -= 1

    if typeclass and not _flags["typeclass"]:
        _flags["typeclass"] = typeclass

    # if we get back to the current level without a typeclass it's an error.
    if strict and is_prototype_base and _flags["depth"] <= 0 and not _flags["typeclass"]:
        _flags["errors"].append(
            _(
                "Prototype {protkey} has no `typeclass` defined anywhere in its parent\n "
                "chain. Add `typeclass`, or a `prototype_parent` pointing to a "
                "prototype with a typeclass."
            ).format(protkey=protkey)
        )

    if _flags["depth"] <= 0:
        if _flags["errors"]:
            raise RuntimeError(f"{_ERRSTR}:_" + f"\n{_ERRSTR}: ".join(_flags["errors"]))
        if _flags["warnings"]:
            raise RuntimeWarning(f"{_WARNSTR}: " + f"\n{_WARNSTR}: ".join(_flags["warnings"]))

    # make sure prototype_locks are set to defaults
    prototype_locks = [
        lstring.split(":", 1)
        for lstring in prototype.get("prototype_locks", "").split(";")
        if ":" in lstring
    ]
    locktypes = [tup[0].strip() for tup in prototype_locks]
    if "spawn" not in locktypes:
        prototype_locks.append(("spawn", "all()"))
    if "edit" not in locktypes:
        prototype_locks.append(("edit", "all()"))
    prototype_locks = ";".join(":".join(tup) for tup in prototype_locks)
    prototype["prototype_locks"] = prototype_locks


def protfunc_parser(
    value,
    available_functions=None,
    testing=False,
    stacktrace=False,
    caller=None,
    raise_errors=True,
    **kwargs,
):
    """
    Parse a prototype value string for a protfunc and process it.

    Available protfuncs are specified as callables in one of the modules of
    `settings.PROTFUNC_MODULES`, or specified on the command line.

    Args:
        value (any): The value to test for a parseable protfunc. Only strings will be parsed for
            protfuncs, all other types are returned as-is.
        available_functions (dict, optional): Mapping of name:protfunction to use for this parsing.
            If not set, use default sources.
        stacktrace (bool, optional): If set, print the stack parsing process of the protfunc-parser.
        raise_errors (bool, optional): Raise explicit errors from malformed/not found protfunc
            calls.

    Keyword Args:
        session (Session): Passed to protfunc. Session of the entity spawning the prototype.
        protototype (dict): Passed to protfunc. The dict this protfunc is a part of.
        current_key(str): Passed to protfunc. The key in the prototype that will hold this value.
        caller (Object or Account): This is necessary for certain protfuncs that perform object
            searches and have to check permissions.
        any (any): Passed on to the protfunc.

    Returns:
        any: A structure to replace the string on the prototype leve.  Note
        that FunctionParser functions $funcname(*args, **kwargs) can return any
        data type to insert into the prototype.

    """
    if not isinstance(value, str):
        return value

    result = FUNC_PARSER.parse_to_any(value, raise_errors=raise_errors, caller=caller, **kwargs)

    return result


# Various prototype utilities


def format_available_protfuncs():
    """
    Get all protfuncs in a pretty-formatted form.

    Args:
        clr (str, optional): What coloration tag to use.
    """
    out = []
    for protfunc_name, protfunc in FUNC_PARSER.callables.items():
        out.append(
            "- |c${name}|n - |W{docs}".format(
                name=protfunc_name, docs=protfunc.__doc__.strip().replace("\n", "")
            )
        )
    return justify("\n".join(out), indent=8)


def prototype_to_str(prototype):
    """
    Format a prototype to a nice string representation.

    Args:
        prototype (dict): The prototype.
    """

    prototype = homogenize_prototype(prototype)

    header = """
|cprototype-key:|n {prototype_key}, |c-tags:|n {prototype_tags}, |c-locks:|n {prototype_locks}|n
|c-desc|n: {prototype_desc}
|cprototype-parent:|n {prototype_parent}
    \n""".format(
        prototype_key=prototype.get("prototype_key", "|r[UNSET](required)|n"),
        prototype_tags=prototype.get("prototype_tags", "|wNone|n"),
        prototype_locks=prototype.get("prototype_locks", "|wNone|n"),
        prototype_desc=prototype.get("prototype_desc", "|wNone|n"),
        prototype_parent=prototype.get("prototype_parent", "|wNone|n"),
    )
    key = aliases = attrs = tags = locks = permissions = location = home = destination = ""
    if "key" in prototype:
        key = prototype["key"]
        key = "|ckey:|n {key}".format(key=key)
    if "aliases" in prototype:
        aliases = prototype["aliases"]
        aliases = "|caliases:|n {aliases}".format(aliases=", ".join(aliases))
    if "attrs" in prototype:
        attrs = prototype["attrs"]
        out = []
        for (attrkey, value, category, locks) in attrs:
            locks = locks if isinstance(locks, str) else ", ".join(lock for lock in locks if lock)
            category = "|ccategory:|n {}".format(category) if category else ""
            cat_locks = ""
            if category or locks:
                cat_locks = " (|ccategory:|n {category}, ".format(
                    category=category if category else "|wNone|n"
                )
            out.append(
                "{attrkey}{cat_locks}{locks} |c=|n {value}".format(
                    attrkey=attrkey,
                    cat_locks=cat_locks,
                    locks=" |w(locks:|n {locks})".format(locks=locks) if locks else "",
                    value=value,
                )
            )
        attrs = "|cattrs:|n\n {attrs}".format(attrs="\n ".join(out))
    if "tags" in prototype:
        tags = prototype["tags"]
        out = []
        for (tagkey, category, data) in tags:
            out.append(
                "{tagkey} (category: {category}{dat})".format(
                    tagkey=tagkey, category=category, dat=", data: {}".format(data) if data else ""
                )
            )
        tags = "|ctags:|n\n {tags}".format(tags=", ".join(out))
    if "locks" in prototype:
        locks = prototype["locks"]
        locks = "|clocks:|n\n {locks}".format(locks=locks)
    if "permissions" in prototype:
        permissions = prototype["permissions"]
        permissions = "|cpermissions:|n {perms}".format(perms=", ".join(permissions))
    if "location" in prototype:
        location = prototype["location"]
        location = "|clocation:|n {location}".format(location=location)
    if "home" in prototype:
        home = prototype["home"]
        home = "|chome:|n {home}".format(home=home)
    if "destination" in prototype:
        destination = prototype["destination"]
        destination = "|cdestination:|n {destination}".format(destination=destination)

    body = "\n".join(
        part
        for part in (key, aliases, attrs, tags, locks, permissions, location, home, destination)
        if part
    )

    return header.lstrip() + body.strip()


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
    if action == "edit":
        if prototype_key in _MODULE_PROTOTYPES:
            mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key)
            if mod:
                err = _("{protkey} is a read-only prototype (defined as code in {module}).")
            else:
                err = _("{protkey} is a read-only prototype (passed directly as a dict).")
            logger.log_err(err.format(protkey=prototype_key, module=mod))
            return False

    prototype = search_prototype(key=prototype_key, require_single=True)
    if prototype:
        prototype = prototype[0]
    else:
        logger.log_err("Prototype {} not found.".format(prototype_key))
        return False

    lockstring = prototype.get("prototype_locks")

    if lockstring:
        return check_lockstring(None, lockstring, default=default, access_type=action)
    return default


def init_spawn_value(
    value, validator=None, caller=None, prototype=None, protfunc_raise_errors=True
):
    """
    Analyze the prototype value and produce a value useful at the point of spawning.

    Args:
        value (any): This can be:
            callable - will be called as callable()
            (callable, (args,)) - will be called as callable(*args)
            other - will be assigned depending on the variable type
            validator (callable, optional): If given, this will be called with the value to
                check and guarantee the outcome is of a given type.
            caller (Object or Account): This is necessary for certain protfuncs that perform object
                searches and have to check permissions.
            prototype (dict): Prototype this is to be used for. Necessary for certain protfuncs.

    Returns:
        any (any): The (potentially pre-processed value to use for this prototype key)

    """
    validator = validator if validator else lambda o: o
    if callable(value):
        value = validator(value())
    elif value and isinstance(value, (list, tuple)) and callable(value[0]):
        # a structure (callable, (args, ))
        args = value[1:]
        value = validator(value[0](*make_iter(args)))
    else:
        value = validator(value)
    result = protfunc_parser(
        value, caller=caller, prototype=prototype, raise_errors=protfunc_raise_errors
    )
    if result != value:
        return validator(result)
    return result


def value_to_obj_or_any(value):
    "Convert value(s) to Object if possible, otherwise keep original value"
    stype = type(value)
    if is_iter(value):
        if stype == dict:
            return {
                value_to_obj_or_any(key): value_to_obj_or_any(val) for key, val in value.items()
            }
        else:
            return stype([value_to_obj_or_any(val) for val in value])
    obj = dbid_to_obj(value, ObjectDB)
    return obj if obj is not None else value


def value_to_obj(value, force=True):
    "Always convert value(s) to Object, or None"
    stype = type(value)
    if is_iter(value):
        if stype == dict:
            return {
                value_to_obj_or_any(key): value_to_obj_or_any(val) for key, val in value.items()
            }
        else:
            return stype([value_to_obj_or_any(val) for val in value])
    return dbid_to_obj(value, ObjectDB)
