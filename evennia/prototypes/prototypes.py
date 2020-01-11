"""

Handling storage of prototypes, both database-based ones (DBPrototypes) and those defined in modules
(Read-only prototypes). Also contains utility functions, formatters and manager functions.

"""

import hashlib
import time
from ast import literal_eval
from django.conf import settings
from evennia.scripts.scripts import DefaultScript
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_script
from evennia.utils.utils import (
    all_from_module,
    make_iter,
    is_iter,
    dbid_to_obj,
    callables_from_module,
    get_all_typeclasses,
    to_str,
    dbref,
    justify,
    class_from_module,
)
from evennia.locks.lockhandler import validate_lockstring, check_lockstring
from evennia.utils import logger
from evennia.utils import inlinefuncs, dbserialize
from evennia.utils.evtable import EvTable


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
    "exec",
    "tags",
    "attrs",
)
_PROTOTYPE_TAG_CATEGORY = "from_prototype"
_PROTOTYPE_TAG_META_CATEGORY = "db_prototype"
PROT_FUNCS = {}


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
    reserved = _PROTOTYPE_RESERVED_KEYS + (custom_keys or ())

    attrs = list(prototype.get("attrs", []))  # break reference
    tags = make_iter(prototype.get("tags", []))
    homogenized_tags = []

    homogenized = {}
    for key, val in prototype.items():
        if key in reserved:
            if key == "tags":
                for tag in tags:
                    if not is_iter(tag):
                        homogenized_tags.append((tag, None, None))
                    else:
                        homogenized_tags.append(tag)
            else:
                homogenized[key] = val
        else:
            # unassigned keys -> attrs
            attrs.append((key, val, None, ""))
    if attrs:
        homogenized["attrs"] = attrs
    if homogenized_tags:
        homogenized["tags"] = homogenized_tags

    # add required missing parts that had defaults before

    if "prototype_key" not in prototype:
        # assign a random hash as key
        homogenized["prototype_key"] = "prototype-{}".format(
            hashlib.md5(bytes(str(time.time()), "utf-8")).hexdigest()[:7]
        )

    if "typeclass" not in prototype and "prototype_parent" not in prototype:
        homogenized["typeclass"] = settings.BASE_OBJECT_TYPECLASS

    return homogenized


# module-based prototypes

for mod in settings.PROTOTYPE_MODULES:
    # to remove a default prototype, override it with an empty dict.
    # internally we store as (key, desc, locks, tags, prototype_dict)
    prots = []
    for variable_name, prot in all_from_module(mod).items():
        if isinstance(prot, dict):
            if "prototype_key" not in prot:
                prot["prototype_key"] = variable_name.lower()
            prots.append((prot["prototype_key"], homogenize_prototype(prot)))
    # assign module path to each prototype_key for easy reference
    _MODULE_PROTOTYPE_MODULES.update({prototype_key.lower(): mod for prototype_key, _ in prots})
    # make sure the prototype contains all meta info
    for prototype_key, prot in prots:
        actual_prot_key = prot.get("prototype_key", prototype_key).lower()
        prot.update(
            {
                "prototype_key": actual_prot_key,
                "prototype_desc": prot["prototype_desc"] if "prototype_desc" in prot else mod,
                "prototype_locks": (
                    prot["prototype_locks"]
                    if "prototype_locks" in prot
                    else "use:all();edit:false()"
                ),
                "prototype_tags": list(set(make_iter(prot.get("prototype_tags", [])) + ["module"])),
            }
        )
        _MODULE_PROTOTYPES[actual_prot_key] = prot


# Db-based prototypes


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
        raise ValidationError("Prototype requires a prototype_key")

    prototype_key = str(prototype_key).lower()

    # we can't edit a prototype defined in a module
    if prototype_key in _MODULE_PROTOTYPES:
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key, "N/A")
        raise PermissionError(
            "{} is a read-only prototype " "(defined as code in {}).".format(prototype_key, mod)
        )

    # make sure meta properties are included with defaults
    stored_prototype = DbPrototype.objects.filter(db_key=prototype_key)
    prototype = stored_prototype[0].prototype if stored_prototype else {}

    in_prototype["prototype_desc"] = in_prototype.get(
        "prototype_desc", prototype.get("prototype_desc", "")
    )
    prototype_locks = in_prototype.get(
        "prototype_locks", prototype.get("prototype_locks", "spawn:all();edit:perm(Admin)")
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

    prototype.update(in_prototype)

    if stored_prototype:
        # edit existing prototype
        stored_prototype = stored_prototype[0]
        stored_prototype.desc = prototype["prototype_desc"]
        if prototype_tags:
            stored_prototype.tags.clear(category=_PROTOTYPE_TAG_CATEGORY)
            stored_prototype.tags.batch_add(*prototype["prototype_tags"])
        stored_prototype.locks.add(prototype["prototype_locks"])
        stored_prototype.attributes.add("prototype", prototype)
    else:
        # create a new prototype
        stored_prototype = create_script(
            DbPrototype,
            key=prototype_key,
            desc=prototype["prototype_desc"],
            persistent=True,
            locks=prototype_locks,
            tags=prototype["prototype_tags"],
            attributes=[("prototype", prototype)],
        )
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
        mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key.lower(), "N/A")
        raise PermissionError(
            "{} is a read-only prototype " "(defined as code in {}).".format(prototype_key, mod)
        )

    stored_prototype = DbPrototype.objects.filter(db_key__iexact=prototype_key)

    if not stored_prototype:
        raise PermissionError("Prototype {} was not found.".format(prototype_key))

    stored_prototype = stored_prototype[0]
    if caller:
        if not stored_prototype.access(caller, "edit"):
            raise PermissionError(
                "{} needs explicit 'edit' permissions to "
                "delete prototype {}.".format(caller, prototype_key)
            )
    stored_prototype.delete()
    return True


def search_prototype(key=None, tags=None, require_single=False):
    """
    Find prototypes based on key and/or tags, or all prototypes.

    Kwargs:
        key (str): An exact or partial key to query for.
        tags (str or list): Tag key or keys to query for. These
            will always be applied with the 'db_protototype'
            tag category.
        require_single (bool): If set, raise KeyError if the result
            was not found or if there are multiple matches.

    Return:
        matches (list): All found prototype dicts. Empty list if
            no match was found. Note that if neither `key` nor `tags`
            were given, *all* available prototypes will be returned.

    Raises:
        KeyError: If `require_single` is True and there are 0 or >1 matches.

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
        mod_matches = {
            prototype_key: prototype
            for prototype_key, prototype in _MODULE_PROTOTYPES.items()
            if tagset.intersection(prototype.get("prototype_tags", []))
        }
    else:
        mod_matches = _MODULE_PROTOTYPES

    if key:
        if key in mod_matches:
            # exact match
            module_prototypes = [mod_matches[key]]
        else:
            # fuzzy matching
            module_prototypes = [
                prototype
                for prototype_key, prototype in mod_matches.items()
                if key in prototype_key
            ]
    else:
        module_prototypes = [match for match in mod_matches.values()]

    # search db-stored prototypes

    if tags:
        # exact match on tag(s)
        tags = make_iter(tags)
        tag_categories = ["db_prototype" for _ in tags]
        db_matches = DbPrototype.objects.get_by_tag(tags, tag_categories)
    else:
        db_matches = DbPrototype.objects.all().order_by("id")
    if key:
        # exact or partial match on key
        db_matches = (
            db_matches.filter(db_key=key) or db_matches.filter(db_key__icontains=key)
        ).order_by("id")
        # return prototype
    db_prototypes = [dbprot.prototype for dbprot in db_matches]

    matches = db_prototypes + module_prototypes
    nmatches = len(matches)
    if nmatches > 1 and key:
        key = key.lower()
        # avoid duplicates if an exact match exist between the two types
        filter_matches = [
            mta for mta in matches if mta.get("prototype_key") and mta["prototype_key"] == key
        ]
        if filter_matches and len(filter_matches) < nmatches:
            matches = filter_matches

    nmatches = len(matches)
    if nmatches != 1 and require_single:
        raise KeyError("Found {} matching prototypes.".format(nmatches))

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
    for prototype in sorted(prototypes, key=lambda d: d.get("prototype_key", "")):
        lock_use = caller.locks.check_lockstring(
            caller, prototype.get("prototype_locks", ""), access_type="spawn", default=True
        )
        if not show_non_use and not lock_use:
            continue
        if prototype.get("prototype_key", "") in _MODULE_PROTOTYPES:
            lock_edit = False
        else:
            lock_edit = caller.locks.check_lockstring(
                caller, prototype.get("prototype_locks", ""), access_type="edit", default=True
            )
        if not show_non_edit and not lock_edit:
            continue
        ptags = []
        for ptag in prototype.get("prototype_tags", []):
            if is_iter(ptag):
                if len(ptag) > 1:
                    ptags.append("{} (category: {}".format(ptag[0], ptag[1]))
                else:
                    ptags.append(ptag[0])
            else:
                ptags.append(str(ptag))

        display_tuples.append(
            (
                prototype.get("prototype_key", "<unset>"),
                prototype.get("prototype_desc", "<unset>"),
                "{}/{}".format("Y" if lock_use else "N", "Y" if lock_edit else "N"),
                ",".join(ptags),
            )
        )

    if not display_tuples:
        return ""

    table = []
    width = 78
    for i in range(len(display_tuples[0])):
        table.append([str(display_tuple[i]) for display_tuple in display_tuples])
    table = EvTable("Key", "Desc", "Spawn/Edit", "Tags", table=table, crop=True, width=width)
    table.reformat_column(0, width=22)
    table.reformat_column(1, width=29)
    table.reformat_column(2, width=11, align="c")
    table.reformat_column(3, width=16)
    return table


def validate_prototype(
    prototype, protkey=None, protparents=None, is_prototype_base=True, strict=True, _flags=None
):
    """
    Run validation on a prototype, checking for inifinite regress.

    Args:
        prototype (dict): Prototype to validate.
        protkey (str, optional): The name of the prototype definition. If not given, the prototype
            dict needs to have the `prototype_key` field set.
        protpartents (dict, optional): The available prototype parent library. If
            note given this will be determined from settings/database.
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

    if _flags is None:
        _flags = {"visited": [], "depth": 0, "typeclass": False, "errors": [], "warnings": []}

    if not protparents:
        protparents = {
            prototype.get("prototype_key", "").lower(): prototype
            for prototype in search_prototype()
        }

    protkey = protkey and protkey.lower() or prototype.get("prototype_key", None)

    if strict and not bool(protkey):
        _flags["errors"].append("Prototype lacks a `prototype_key`.")
        protkey = "[UNSET]"

    typeclass = prototype.get("typeclass")
    prototype_parent = prototype.get("prototype_parent", [])

    if strict and not (typeclass or prototype_parent):
        if is_prototype_base:
            _flags["errors"].append(
                "Prototype {} requires `typeclass` " "or 'prototype_parent'.".format(protkey)
            )
        else:
            _flags["warnings"].append(
                "Prototype {} can only be used as a mixin since it lacks "
                "a typeclass or a prototype_parent.".format(protkey)
            )

    if strict and typeclass:
        try:
            class_from_module(typeclass)
        except ImportError as err:
            _flags["errors"].append(
                "{}: Prototype {} is based on typeclass {}, which could not be imported!".format(
                    err, protkey, typeclass
                )
            )

    # recursively traverese prototype_parent chain

    for protstring in make_iter(prototype_parent):
        protstring = protstring.lower()
        if protkey is not None and protstring == protkey:
            _flags["errors"].append("Prototype {} tries to parent itself.".format(protkey))
        protparent = protparents.get(protstring)
        if not protparent:
            _flags["errors"].append(
                "Prototype {}'s prototype_parent '{}' was not found.".format((protkey, protstring))
            )
        if id(prototype) in _flags["visited"]:
            _flags["errors"].append(
                "{} has infinite nesting of prototypes.".format(protkey or prototype)
            )

        if _flags["errors"]:
            raise RuntimeError("Error: " + "\nError: ".join(_flags["errors"]))
        _flags["visited"].append(id(prototype))
        _flags["depth"] += 1
        validate_prototype(
            protparent, protstring, protparents, is_prototype_base=is_prototype_base, _flags=_flags
        )
        _flags["visited"].pop()
        _flags["depth"] -= 1

    if typeclass and not _flags["typeclass"]:
        _flags["typeclass"] = typeclass

    # if we get back to the current level without a typeclass it's an error.
    if strict and is_prototype_base and _flags["depth"] <= 0 and not _flags["typeclass"]:
        _flags["errors"].append(
            "Prototype {} has no `typeclass` defined anywhere in its parent\n "
            "chain. Add `typeclass`, or a `prototype_parent` pointing to a "
            "prototype with a typeclass.".format(protkey)
        )

    if _flags["depth"] <= 0:
        if _flags["errors"]:
            raise RuntimeError("Error: " + "\nError: ".join(_flags["errors"]))
        if _flags["warnings"]:
            raise RuntimeWarning("Warning: " + "\nWarning: ".join(_flags["warnings"]))

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


# Protfunc parsing (in-prototype functions)

for mod in settings.PROT_FUNC_MODULES:
    try:
        callables = callables_from_module(mod)
        PROT_FUNCS.update(callables)
    except ImportError:
        logger.log_trace()
        raise


def protfunc_parser(value, available_functions=None, testing=False, stacktrace=False, **kwargs):
    """
    Parse a prototype value string for a protfunc and process it.

    Available protfuncs are specified as callables in one of the modules of
    `settings.PROTFUNC_MODULES`, or specified on the command line.

    Args:
        value (any): The value to test for a parseable protfunc. Only strings will be parsed for
            protfuncs, all other types are returned as-is.
        available_functions (dict, optional): Mapping of name:protfunction to use for this parsing.
            If not set, use default sources.
        testing (bool, optional): Passed to protfunc. If in a testing mode, some protfuncs may
            behave differently.
        stacktrace (bool, optional): If set, print the stack parsing process of the protfunc-parser.

    Kwargs:
        session (Session): Passed to protfunc. Session of the entity spawning the prototype.
        protototype (dict): Passed to protfunc. The dict this protfunc is a part of.
        current_key(str): Passed to protfunc. The key in the prototype that will hold this value.
        any (any): Passed on to the protfunc.

    Returns:
        testresult (tuple): If `testing` is set, returns a tuple (error, result) where error is
            either None or a string detailing the error from protfunc_parser or seen when trying to
            run `literal_eval` on the parsed string.
        any (any): A structure to replace the string on the prototype level. If this is a
            callable or a (callable, (args,)) structure, it will be executed as if one had supplied
            it to the prototype directly. This structure is also passed through literal_eval so one
            can get actual Python primitives out of it (not just strings). It will also identify
            eventual object #dbrefs in the output from the protfunc.

    """
    if not isinstance(value, str):
        return value

    available_functions = PROT_FUNCS if available_functions is None else available_functions

    result = inlinefuncs.parse_inlinefunc(
        value, available_funcs=available_functions, stacktrace=stacktrace, testing=testing, **kwargs
    )

    err = None
    try:
        result = literal_eval(result)
    except ValueError:
        pass
    except Exception as exc:
        err = str(exc)
    if testing:
        return err, result
    return result


# Various prototype utilities


def format_available_protfuncs():
    """
    Get all protfuncs in a pretty-formatted form.

    Args:
        clr (str, optional): What coloration tag to use.
    """
    out = []
    for protfunc_name, protfunc in PROT_FUNCS.items():
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

    key = prototype.get("key", "")
    if key:
        key = "|ckey:|n {key}".format(key=key)
    aliases = prototype.get("aliases", "")
    if aliases:
        aliases = "|caliases:|n {aliases}".format(aliases=", ".join(aliases))
    attrs = prototype.get("attrs", "")
    if attrs:
        out = []
        for (attrkey, value, category, locks) in attrs:
            locks = ", ".join(lock for lock in locks if lock)
            category = "|ccategory:|n {}".format(category) if category else ""
            cat_locks = ""
            if category or locks:
                cat_locks = " (|ccategory:|n {category}, ".format(
                    category=category if category else "|wNone|n"
                )
            out.append(
                "{attrkey}{cat_locks} |c=|n {value}".format(
                    attrkey=attrkey,
                    cat_locks=cat_locks,
                    locks=locks if locks else "|wNone|n",
                    value=value,
                )
            )
        attrs = "|cattrs:|n\n {attrs}".format(attrs="\n ".join(out))
    tags = prototype.get("tags", "")
    if tags:
        out = []
        for (tagkey, category, data) in tags:
            out.append(
                "{tagkey} (category: {category}{dat})".format(
                    tagkey=tagkey, category=category, dat=", data: {}".format(data) if data else ""
                )
            )
        tags = "|ctags:|n\n {tags}".format(tags=", ".join(out))
    locks = prototype.get("locks", "")
    if locks:
        locks = "|clocks:|n\n {locks}".format(locks=locks)
    permissions = prototype.get("permissions", "")
    if permissions:
        permissions = "|cpermissions:|n {perms}".format(perms=", ".join(permissions))
    location = prototype.get("location", "")
    if location:
        location = "|clocation:|n {location}".format(location=location)
    home = prototype.get("home", "")
    if home:
        home = "|chome:|n {home}".format(home=home)
    destination = prototype.get("destination", "")
    if destination:
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
            mod = _MODULE_PROTOTYPE_MODULES.get(prototype_key, "N/A")
            logger.log_err(
                "{} is a read-only prototype " "(defined as code in {}).".format(prototype_key, mod)
            )
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
    validator = validator if validator else lambda o: o
    if callable(value):
        value = validator(value())
    elif value and isinstance(value, (list, tuple)) and callable(value[0]):
        # a structure (callable, (args, ))
        args = value[1:]
        value = validator(value[0](*make_iter(args)))
    else:
        value = validator(value)
    return protfunc_parser(value)


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
            return {value_to_obj_or_any(key): value_to_obj_or_any(val) for key, val in value.iter()}
        else:
            return stype([value_to_obj_or_any(val) for val in value])
    return dbid_to_obj(value, ObjectDB)
