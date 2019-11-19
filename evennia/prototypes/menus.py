"""

OLC Prototype menu nodes

"""

import json
import re
from random import choice
from django.db.models import Q
from django.conf import settings
from evennia.objects.models import ObjectDB
from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils import evmore
from evennia.utils.ansi import strip_ansi
from evennia.utils import utils
from evennia.locks.lockhandler import get_all_lockfuncs
from evennia.prototypes import prototypes as protlib
from evennia.prototypes import spawner

# ------------------------------------------------------------
#
# OLC Prototype design menu
#
# ------------------------------------------------------------

_MENU_CROP_WIDTH = 15
_MENU_ATTR_LITERAL_EVAL_ERROR = (
    "|rCritical Python syntax error in your value. Only primitive Python structures are allowed.\n"
    "You also need to use correct Python syntax. Remember especially to put quotes around all "
    "strings inside lists and dicts.|n"
)


# Helper functions


def _get_menu_prototype(caller):
    """Return currently active menu prototype."""
    prototype = None
    if hasattr(caller.ndb._menutree, "olc_prototype"):
        prototype = caller.ndb._menutree.olc_prototype
    if not prototype:
        caller.ndb._menutree.olc_prototype = prototype = {}
        caller.ndb._menutree.olc_new = True
    return prototype


def _get_flat_menu_prototype(caller, refresh=False, validate=False):
    """Return prototype where parent values are included"""
    flat_prototype = None
    if not refresh and hasattr(caller.ndb._menutree, "olc_flat_prototype"):
        flat_prototype = caller.ndb._menutree.olc_flat_prototype
    if not flat_prototype:
        prot = _get_menu_prototype(caller)
        caller.ndb._menutree.olc_flat_prototype = flat_prototype = spawner.flatten_prototype(
            prot, validate=validate
        )
    return flat_prototype


def _get_unchanged_inherited(caller, protname):
    """Return prototype values inherited from parent(s), which are not replaced in child"""
    prototype = _get_menu_prototype(caller)
    if protname in prototype:
        return protname[protname], False
    else:
        flattened = _get_flat_menu_prototype(caller)
        if protname in flattened:
            return protname[protname], True
    return None, False


def _set_menu_prototype(caller, prototype):
    """Set the prototype with existing one"""
    caller.ndb._menutree.olc_prototype = prototype
    caller.ndb._menutree.olc_new = False
    return prototype


def _is_new_prototype(caller):
    """Check if prototype is marked as new or was loaded from a saved one."""
    return hasattr(caller.ndb._menutree, "olc_new")


def _format_option_value(prop, required=False, prototype=None, cropper=None):
    """
    Format wizard option values.

    Args:
        prop (str): Name or value to format.
        required (bool, optional): The option is required.
        prototype (dict, optional): If given, `prop` will be considered a key in this prototype.
        cropper (callable, optional): A function to crop the value to a certain width.

    Returns:
        value (str): The formatted value.
    """
    if prototype is not None:
        prop = prototype.get(prop, "")

    out = prop
    if callable(prop):
        if hasattr(prop, "__name__"):
            out = "<{}>".format(prop.__name__)
        else:
            out = repr(prop)
    if utils.is_iter(prop):
        out = ", ".join(str(pr) for pr in prop)
    if not out and required:
        out = "|runset"
    if out:
        return " ({}|n)".format(cropper(out) if cropper else utils.crop(out, _MENU_CROP_WIDTH))
    return ""


def _set_prototype_value(caller, field, value, parse=True):
    """Set prototype's field in a safe way."""
    prototype = _get_menu_prototype(caller)
    prototype[field] = value
    caller.ndb._menutree.olc_prototype = prototype
    return prototype


def _set_property(caller, raw_string, **kwargs):
    """
    Add or update a property. To be called by the 'goto' option variable.

    Args:
        caller (Object, Account): The user of the wizard.
        raw_string (str): Input from user on given node - the new value to set.

    Kwargs:
        test_parse (bool): If set (default True), parse raw_string for protfuncs and obj-refs and
            try to run result through literal_eval. The parser will be run in 'testing' mode and any
            parsing errors will shown to the user. Note that this is just for testing, the original
            given string will be what is inserted.
        prop (str): Property name to edit with `raw_string`.
        processor (callable): Converts `raw_string` to a form suitable for saving.
        next_node (str): Where to redirect to after this has run.

    Returns:
        next_node (str): Next node to go to.

    """
    prop = kwargs.get("prop", "prototype_key")
    processor = kwargs.get("processor", None)
    next_node = kwargs.get("next_node", None)

    if callable(processor):
        try:
            value = processor(raw_string)
        except Exception as err:
            caller.msg(
                "Could not set {prop} to {value} ({err})".format(
                    prop=prop.replace("_", "-").capitalize(), value=raw_string, err=str(err)
                )
            )
            # this means we'll re-run the current node.
            return None
    else:
        value = raw_string

    if not value:
        return next_node

    prototype = _set_prototype_value(caller, prop, value)
    caller.ndb._menutree.olc_prototype = prototype

    try:
        # TODO simple way to get rid of the u'' markers in list reprs, remove this when on py3.
        repr_value = json.dumps(value)
    except Exception:
        repr_value = value

    out = [" Set {prop} to {value} ({typ}).".format(prop=prop, value=repr_value, typ=type(value))]

    if kwargs.get("test_parse", True):
        out.append(" Simulating prototype-func parsing ...")
        err, parsed_value = protlib.protfunc_parser(value, testing=True)
        if err:
            out.append(" |yPython `literal_eval` warning: {}|n".format(err))
        if parsed_value != value:
            out.append(
                " |g(Example-)value when parsed ({}):|n {}".format(type(parsed_value), parsed_value)
            )
        else:
            out.append(" |gNo change when parsed.")

    caller.msg("\n".join(out))

    return next_node


def _wizard_options(curr_node, prev_node, next_node, color="|W", search=False):
    """Creates default navigation options available in the wizard."""
    options = []
    if prev_node:
        options.append(
            {
                "key": ("|wB|Wack", "b"),
                "desc": "{color}({node})|n".format(color=color, node=prev_node.replace("_", "-")),
                "goto": "node_{}".format(prev_node),
            }
        )
    if next_node:
        options.append(
            {
                "key": ("|wF|Worward", "f"),
                "desc": "{color}({node})|n".format(color=color, node=next_node.replace("_", "-")),
                "goto": "node_{}".format(next_node),
            }
        )

    options.append({"key": ("|wI|Wndex", "i"), "goto": "node_index"})

    if curr_node:
        options.append(
            {
                "key": ("|wV|Walidate prototype", "validate", "v"),
                "goto": ("node_validate_prototype", {"back": curr_node}),
            }
        )
        if search:
            options.append(
                {
                    "key": ("|wSE|Warch objects", "search object", "search", "se"),
                    "goto": ("node_search_object", {"back": curr_node}),
                }
            )

    return options


def _set_actioninfo(caller, string):
    caller.ndb._menutree.actioninfo = string


def _path_cropper(pythonpath):
    "Crop path to only the last component"
    return pythonpath.split(".")[-1]


def _validate_prototype(prototype):
    """Run validation on prototype"""

    txt = protlib.prototype_to_str(prototype)
    errors = "\n\n|g No validation errors found.|n (but errors could still happen at spawn-time)"
    err = False
    try:
        # validate, don't spawn
        spawner.spawn(prototype, only_validate=True)
    except RuntimeError as exc:
        errors = "\n\n|r{}|n".format(exc)
        err = True
    except RuntimeWarning as exc:
        errors = "\n\n|y{}|n".format(exc)
        err = True

    text = txt + errors
    return err, text


def _format_protfuncs():
    out = []
    sorted_funcs = [
        (key, func) for key, func in sorted(protlib.PROT_FUNCS.items(), key=lambda tup: tup[0])
    ]
    for protfunc_name, protfunc in sorted_funcs:
        out.append(
            "- |c${name}|n - |W{docs}".format(
                name=protfunc_name,
                docs=utils.justify(protfunc.__doc__.strip(), align="l", indent=10).strip(),
            )
        )
    return "\n       ".join(out)


def _format_lockfuncs():
    out = []
    sorted_funcs = [
        (key, func) for key, func in sorted(get_all_lockfuncs().items(), key=lambda tup: tup[0])
    ]
    for lockfunc_name, lockfunc in sorted_funcs:
        doc = (lockfunc.__doc__ or "").strip()
        out.append(
            "- |c${name}|n - |W{docs}".format(
                name=lockfunc_name, docs=utils.justify(doc, align="l", indent=10).strip()
            )
        )
    return "\n".join(out)


def _format_list_actions(*args, **kwargs):
    """Create footer text for nodes with extra list actions

    Args:
        actions (str): Available actions. The first letter of the action name will be assumed
            to be a shortcut.
    Kwargs:
        prefix (str): Default prefix to use.
    Returns:
        string (str): Formatted footer for adding to the node text.

    """
    actions = []
    prefix = kwargs.get("prefix", "|WSelect with |w<num>|W. Other actions:|n ")
    for action in args:
        actions.append("|w{}|n|W{} |w<num>|n".format(action[0], action[1:]))
    return prefix + " |W|||n ".join(actions)


def _get_current_value(caller, keyname, comparer=None, formatter=str, only_inherit=False):
    """
    Return current value, marking if value comes from parent or set in this prototype.

    Args:
        keyname (str): Name of prototoype key to get current value of.
        comparer (callable, optional): This will be called as comparer(prototype_value,
            flattened_value) and is expected to return the value to show as the current
            or inherited one. If not given, a straight comparison is used and what is returned
            depends on the only_inherit setting.
        formatter (callable, optional)): This will be called with the result of comparer.
        only_inherit (bool, optional): If a current value should only be shown if all
            the values are inherited from the prototype parent (otherwise, show an empty string).
    Returns:
        current (str): The current value.

    """

    def _default_comparer(protval, flatval):
        if only_inherit:
            return "" if protval else flatval
        else:
            return protval if protval else flatval

    if not callable(comparer):
        comparer = _default_comparer

    prot = _get_menu_prototype(caller)
    flat_prot = _get_flat_menu_prototype(caller)

    out = ""
    if keyname in prot:
        if keyname in flat_prot:
            out = formatter(comparer(prot[keyname], flat_prot[keyname]))
            if only_inherit:
                if str(out).strip():
                    return "|WCurrent|n {} |W(|binherited|W):|n {}".format(keyname, out)
                return ""
            else:
                if out:
                    return "|WCurrent|n {}|W:|n {}".format(keyname, out)
                return "|W[No {} set]|n".format(keyname)
        elif only_inherit:
            return ""
        else:
            out = formatter(prot[keyname])
            return "|WCurrent|n {}|W:|n {}".format(keyname, out)
    elif keyname in flat_prot:
        out = formatter(flat_prot[keyname])
        if out:
            return "|WCurrent|n {} |W(|n|binherited|W):|n {}".format(keyname, out)
        else:
            return ""
    elif only_inherit:
        return ""
    else:
        return "|W[No {} set]|n".format(keyname)


def _default_parse(raw_inp, choices, *args):
    """
    Helper to parse default input to a node decorated with the node_list decorator on
    the form l1, l 2, look 1, etc. Spaces are ignored, as is case.

    Args:
        raw_inp (str): Input from the user.
        choices (list): List of available options on the node listing (list of strings).
        args (tuples): The available actions, each specifed as a tuple (name, alias, ...)
    Returns:
        choice (str): A choice among the choices, or None if no match was found.
        action (str): The action operating on the choice, or None.

    """
    raw_inp = raw_inp.lower().strip()
    mapping = {t.lower(): tup[0] for tup in args for t in tup}
    match = re.match(r"(%s)\s*?(\d+)$" % "|".join(mapping.keys()), raw_inp)
    if match:
        action = mapping.get(match.group(1), None)
        num = int(match.group(2)) - 1
        num = num if 0 <= num < len(choices) else None
        if action is not None and num is not None:
            return choices[num], action
    return None, None


# Menu nodes ------------------------------

# helper nodes

# validate prototype (available as option from all nodes)


def node_validate_prototype(caller, raw_string, **kwargs):
    """General node to view and validate a protototype"""
    prototype = _get_flat_menu_prototype(caller, refresh=True, validate=False)
    prev_node = kwargs.get("back", "index")

    _, text = _validate_prototype(prototype)

    helptext = """
    The validator checks if the prototype's various values are on the expected form. It also tests
    any $protfuncs.

    """

    text = (text, helptext)

    options = _wizard_options(None, prev_node, None)
    options.append({"key": "_default", "goto": "node_" + prev_node})

    return text, options


# node examine_entity


def node_examine_entity(caller, raw_string, **kwargs):
    """
    General node to view a text and then return to previous node.  Kwargs should contain "text" for
    the text to show and 'back" pointing to the node to return to.
    """
    text = kwargs.get("text", "Nothing was found here.")
    helptext = "Use |wback|n to return to the previous node."
    prev_node = kwargs.get("back", "index")

    text = (text, helptext)

    options = _wizard_options(None, prev_node, None)
    options.append({"key": "_default", "goto": "node_" + prev_node})

    return text, options


# node object_search


def _search_object(caller):
    "update search term based on query stored on menu; store match too"
    try:
        searchstring = caller.ndb._menutree.olc_search_object_term.strip()
        caller.ndb._menutree.olc_search_object_matches = []
    except AttributeError:
        return []

    if not searchstring:
        caller.msg("Must specify a search criterion.")
        return []

    is_dbref = utils.dbref(searchstring)
    is_account = searchstring.startswith("*")

    if is_dbref or is_account:

        if is_dbref:
            # a dbref search
            results = caller.search(searchstring, global_search=True, quiet=True)
        else:
            # an account search
            searchstring = searchstring.lstrip("*")
            results = caller.search_account(searchstring, quiet=True)
    else:
        keyquery = Q(db_key__istartswith=searchstring)
        aliasquery = Q(
            db_tags__db_key__istartswith=searchstring, db_tags__db_tagtype__iexact="alias"
        )
        results = ObjectDB.objects.filter(keyquery | aliasquery).distinct()

    caller.msg("Searching for '{}' ...".format(searchstring))
    caller.ndb._menutree.olc_search_object_matches = results
    return ["{}(#{})".format(obj.key, obj.id) for obj in results]


def _object_search_select(caller, obj_entry, **kwargs):
    choices = kwargs["available_choices"]
    num = choices.index(obj_entry)
    matches = caller.ndb._menutree.olc_search_object_matches
    obj = matches[num]

    if not obj.access(caller, "examine"):
        caller.msg("|rYou don't have 'examine' access on this object.|n")
        del caller.ndb._menutree.olc_search_object_term
        return "node_search_object"

    prot = spawner.prototype_from_object(obj)
    txt = protlib.prototype_to_str(prot)
    return "node_examine_entity", {"text": txt, "back": "search_object"}


def _object_search_actions(caller, raw_inp, **kwargs):
    "All this does is to queue a search query"
    choices = kwargs["available_choices"]
    obj_entry, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("create prototype from object", "create", "c")
    )

    raw_inp = raw_inp.strip()

    if obj_entry:

        num = choices.index(obj_entry)
        matches = caller.ndb._menutree.olc_search_object_matches
        obj = matches[num]
        prot = spawner.prototype_from_object(obj)

        if action == "examine":

            if not obj.access(caller, "examine"):
                caller.msg("\n|rYou don't have 'examine' access on this object.|n")
                del caller.ndb._menutree.olc_search_object_term
                return "node_search_object"

            txt = protlib.prototype_to_str(prot)
            return "node_examine_entity", {"text": txt, "back": "search_object"}
        else:
            # load prototype

            if not obj.access(caller, "edit"):
                caller.msg("|rYou don't have access to do this with this object.|n")
                del caller.ndb._menutree.olc_search_object_term
                return "node_search_object"

            _set_menu_prototype(caller, prot)
            caller.msg("Created prototype from object.")
            return "node_index"
    elif raw_inp:
        caller.ndb._menutree.olc_search_object_term = raw_inp
        return "node_search_object", kwargs
    else:
        # empty input - exit back to previous node
        prev_node = "node_" + kwargs.get("back", "index")
        return prev_node


@list_node(_search_object, _object_search_select)
def node_search_object(caller, raw_inp, **kwargs):
    """
    Node for searching for an existing object.
    """
    try:
        matches = caller.ndb._menutree.olc_search_object_matches
    except AttributeError:
        matches = []
    nmatches = len(matches)
    prev_node = kwargs.get("back", "index")

    if matches:
        text = """
        Found {num} match{post}.

         (|RWarning: creating a prototype will |roverwrite|r |Rthe current prototype!)|n""".format(
            num=nmatches, post="es" if nmatches > 1 else ""
        )
        _set_actioninfo(
            caller,
            _format_list_actions("examine", "create prototype from object", prefix="Actions: "),
        )
    else:
        text = "Enter search criterion."

    helptext = """
        You can search objects by specifying partial key, alias or its exact #dbref. Use *query to
        search for an Account instead.

        Once having found any matches you can choose to examine it or use |ccreate prototype from
        object|n. If doing the latter, a prototype will be calculated from the selected object and
        loaded as the new 'current' prototype. This is useful for having a base to build from but be
        careful you are not throwing away any existing, unsaved, prototype work!
        """

    text = (text, helptext)

    options = _wizard_options(None, prev_node, None)
    options.append({"key": "_default", "goto": (_object_search_actions, {"back": prev_node})})

    return text, options


# main index (start page) node


def node_index(caller):
    prototype = _get_menu_prototype(caller)

    text = """
       |c --- Prototype wizard --- |n
       %s

       A |cprototype|n is a 'template' for |wspawning|n an in-game entity. A field of the prototype
       can either be hard-coded, left empty or scripted using |w$protfuncs|n - for example to
       randomize the value every time a new entity is spawned. The fields whose names start with
       'Prototype-' are not fields on the object itself but are used for prototype-inheritance, or
       when saving and loading.

       Select prototype field to edit. If you are unsure, start from [|w1|n]. Enter [|wh|n]elp at
       any menu node for more info.

       """
    helptxt = """
       |c- prototypes |n

       A prototype is really just a Python dictionary. When spawning, this dictionary is essentially
       passed into `|wevennia.utils.create.create_object(**prototype)|n` to create a new object. By
       using different prototypes you can customize instances of objects without having to do code
       changes to their typeclass (something which requires code access). The classical example is
       to spawn goblins with different names, looks, equipment and skill, each based on the same
       `Goblin` typeclass.

       At any time you can [|wV|n]alidate that the prototype works correctly and use it to
       [|wSP|n]awn a new entity. You can also [|wSA|n]ve|n your work, [|wLO|n]oad an existing
       prototype to [|wSE|n]arch for existing objects to use as a base. Use [|wL|n]ook to re-show a
       menu node. [|wQ|n]uit will always exit the menu and [|wH|n]elp will show context-sensitive
       help.


       |c- $protfuncs |n

       Prototype-functions (protfuncs) allow for limited scripting within a prototype. These are
       entered as a string $funcname(arg, arg, ...) and are evaluated |wat the time of spawning|n
       only.  They can also be nested for combined effects.

       {pfuncs}
       """.format(
        pfuncs=_format_protfuncs()
    )

    # If a prototype is being edited, show its key and
    # prototype_key under the title
    loaded_prototype = ""
    if "prototype_key" in prototype or "key" in prototype:
        loaded_prototype = " --- Editing: |y{}({})|n --- ".format(
            prototype.get("key", ""), prototype.get("prototype_key", "")
        )
    text = text % (loaded_prototype)

    text = (text, helptxt)

    options = []
    options.append(
        {
            "desc": "|WPrototype-Key|n|n{}".format(
                _format_option_value("Key", "prototype_key" not in prototype, prototype, None)
            ),
            "goto": "node_prototype_key",
        }
    )
    for key in (
        "Prototype_Parent",
        "Typeclass",
        "Key",
        "Aliases",
        "Attrs",
        "Tags",
        "Locks",
        "Permissions",
        "Location",
        "Home",
        "Destination",
    ):
        required = False
        cropper = None
        if key in ("Prototype_Parent", "Typeclass"):
            required = ("prototype_parent" not in prototype) and ("typeclass" not in prototype)
        if key == "Typeclass":
            cropper = _path_cropper
        options.append(
            {
                "desc": "{}{}|n{}".format(
                    "|W" if key == "Prototype_Parent" else "|w",
                    key.replace("_", "-"),
                    _format_option_value(key, required, prototype, cropper=cropper),
                ),
                "goto": "node_{}".format(key.lower()),
            }
        )
    required = False
    for key in ("Desc", "Tags", "Locks"):
        options.append(
            {
                "desc": "|WPrototype-{}|n|n{}".format(
                    key, _format_option_value(key, required, prototype, None)
                ),
                "goto": "node_prototype_{}".format(key.lower()),
            }
        )

    options.extend(
        (
            {"key": ("|wV|Walidate prototype", "validate", "v"), "goto": "node_validate_prototype"},
            {"key": ("|wSA|Wve prototype", "save", "sa"), "goto": "node_prototype_save"},
            {"key": ("|wSP|Wawn prototype", "spawn", "sp"), "goto": "node_prototype_spawn"},
            {"key": ("|wLO|Wad prototype", "load", "lo"), "goto": "node_prototype_load"},
            {"key": ("|wSE|Warch objects|n", "search", "se"), "goto": "node_search_object"},
        )
    )

    return text, options


# prototype_key node


def _check_prototype_key(caller, key):
    old_prototype = protlib.search_prototype(key)
    olc_new = _is_new_prototype(caller)
    key = key.strip().lower()
    if old_prototype:
        old_prototype = old_prototype[0]
        # we are starting a new prototype that matches an existing
        if not caller.locks.check_lockstring(
            caller, old_prototype["prototype_locks"], access_type="edit"
        ):
            # return to the node_prototype_key to try another key
            caller.msg(
                "Prototype '{key}' already exists and you don't "
                "have permission to edit it.".format(key=key)
            )
            return "node_prototype_key"
        elif olc_new:
            # we are selecting an existing prototype to edit. Reset to index.
            del caller.ndb._menutree.olc_new
            caller.ndb._menutree.olc_prototype = old_prototype
            caller.msg("Prototype already exists. Reloading.")
            return "node_index"

    return _set_property(caller, key, prop="prototype_key")


def node_prototype_key(caller):

    text = """
        The |cPrototype-Key|n uniquely identifies the prototype and is |wmandatory|n. It is used to
        find and use the prototype to spawn new entities. It is not case sensitive.

        (To set a new value, just write it and press enter)

        {current}""".format(
        current=_get_current_value(caller, "prototype_key")
    )

    helptext = """
        The prototype-key is not itself used when spawnng the new object, but is only used for
        managing, storing and loading the prototype. It must be globally unique, so existing keys
        will be checked before a new key is accepted. If an existing key is picked, the existing
        prototype will be loaded.
        """

    options = _wizard_options("prototype_key", "index", "prototype_parent")
    options.append({"key": "_default", "goto": _check_prototype_key})

    text = (text, helptext)
    return text, options


# prototype_parents node


def _all_prototype_parents(caller):
    """Return prototype_key of all available prototypes for listing in menu"""
    return [
        prototype["prototype_key"]
        for prototype in protlib.search_prototype()
        if "prototype_key" in prototype
    ]


def _prototype_parent_actions(caller, raw_inp, **kwargs):
    """Parse the default Convert prototype to a string representation for closer inspection"""
    choices = kwargs.get("available_choices", [])
    prototype_parent, action = _default_parse(
        raw_inp, choices, ("examine", "e", "l"), ("add", "a"), ("remove", "r", "delete", "d")
    )

    if prototype_parent:
        # a selection of parent was made
        prototype_parent = protlib.search_prototype(key=prototype_parent)[0]
        prototype_parent_key = prototype_parent["prototype_key"]

        # which action to apply on the selection
        if action == "examine":
            # examine the prototype
            txt = protlib.prototype_to_str(prototype_parent)
            kwargs["text"] = txt
            kwargs["back"] = "prototype_parent"
            return "node_examine_entity", kwargs
        elif action == "add":
            # add/append parent
            prot = _get_menu_prototype(caller)
            current_prot_parent = prot.get("prototype_parent", None)
            if current_prot_parent:
                current_prot_parent = utils.make_iter(current_prot_parent)
                if prototype_parent_key in current_prot_parent:
                    caller.msg("Prototype_parent {} is already used.".format(prototype_parent_key))
                    return "node_prototype_parent"
                else:
                    current_prot_parent.append(prototype_parent_key)
                    caller.msg("Add prototype parent for multi-inheritance.")
            else:
                current_prot_parent = prototype_parent_key
            try:
                if prototype_parent:
                    spawner.flatten_prototype(prototype_parent, validate=True)
                else:
                    raise RuntimeError("Not found.")
            except RuntimeError as err:
                caller.msg(
                    "Selected prototype-parent {} "
                    "caused Error(s):\n|r{}|n".format(prototype_parent, err)
                )
                return "node_prototype_parent"
            _set_prototype_value(caller, "prototype_parent", current_prot_parent)
            _get_flat_menu_prototype(caller, refresh=True)
        elif action == "remove":
            # remove prototype parent
            prot = _get_menu_prototype(caller)
            current_prot_parent = prot.get("prototype_parent", None)
            if current_prot_parent:
                current_prot_parent = utils.make_iter(current_prot_parent)
                try:
                    current_prot_parent.remove(prototype_parent_key)
                    _set_prototype_value(caller, "prototype_parent", current_prot_parent)
                    _get_flat_menu_prototype(caller, refresh=True)
                    caller.msg("Removed prototype parent {}.".format(prototype_parent_key))
                except ValueError:
                    caller.msg(
                        "|rPrototype-parent {} could not be removed.".format(prototype_parent_key)
                    )
        return "node_prototype_parent"


def _prototype_parent_select(caller, new_parent):

    ret = None
    prototype_parent = protlib.search_prototype(new_parent)
    try:
        if prototype_parent:
            spawner.flatten_prototype(prototype_parent[0], validate=True)
        else:
            raise RuntimeError("Not found.")
    except RuntimeError as err:
        caller.msg(
            "Selected prototype-parent {} " "caused Error(s):\n|r{}|n".format(new_parent, err)
        )
    else:
        ret = _set_property(
            caller,
            new_parent,
            prop="prototype_parent",
            processor=str,
            next_node="node_prototype_parent",
        )
        _get_flat_menu_prototype(caller, refresh=True)
        caller.msg("Selected prototype parent |c{}|n.".format(new_parent))
    return ret


@list_node(_all_prototype_parents, _prototype_parent_select)
def node_prototype_parent(caller):
    prototype = _get_menu_prototype(caller)

    prot_parent_keys = prototype.get("prototype_parent")

    text = """
        The |cPrototype Parent|n allows you to |winherit|n prototype values from another named
        prototype (given as that prototype's |wprototype_key|n).  If not changing these values in
        the current prototype, the parent's value will be used. Pick the available prototypes below.

        Note that somewhere in the prototype's parentage, a |ctypeclass|n must be specified. If no
        parent is given, this prototype must define the typeclass (next menu node).

        {current}
        """
    helptext = """
        Prototypes can inherit from one another. Changes in the child replace any values set in a
        parent. The |wtypeclass|n key must exist |wsomewhere|n in the parent chain for the
        prototype to be valid.
        """

    _set_actioninfo(caller, _format_list_actions("examine", "add", "remove"))

    ptexts = []
    if prot_parent_keys:
        for pkey in utils.make_iter(prot_parent_keys):
            prot_parent = protlib.search_prototype(pkey)
            if prot_parent:
                prot_parent = prot_parent[0]
                ptexts.append(
                    "|c -- {pkey} -- |n\n{prot}".format(
                        pkey=pkey, prot=protlib.prototype_to_str(prot_parent)
                    )
                )
            else:
                ptexts.append("Prototype parent |r{pkey} was not found.".format(pkey=pkey))

    if not ptexts:
        ptexts.append("[No prototype_parent set]")

    text = text.format(current="\n\n".join(ptexts))

    text = (text, helptext)

    options = _wizard_options("prototype_parent", "prototype_key", "typeclass", color="|W")
    options.append({"key": "_default", "goto": _prototype_parent_actions})

    return text, options


# typeclasses node


def _all_typeclasses(caller):
    """Get name of available typeclasses."""
    return list(
        name
        for name in sorted(utils.get_all_typeclasses("evennia.objects.models.ObjectDB").keys())
        if name != "evennia.objects.models.ObjectDB"
    )


def _typeclass_actions(caller, raw_inp, **kwargs):
    """Parse actions for typeclass listing"""

    choices = kwargs.get("available_choices", [])
    typeclass_path, action = _default_parse(
        raw_inp, choices, ("examine", "e", "l"), ("remove", "r", "delete", "d")
    )

    if typeclass_path:
        if action == "examine":
            typeclass = utils.get_all_typeclasses().get(typeclass_path)
            if typeclass:
                docstr = []
                for line in typeclass.__doc__.split("\n"):
                    if line.strip():
                        docstr.append(line)
                    elif docstr:
                        break
                docstr = "\n".join(docstr) if docstr else "<empty>"
                txt = (
                    "Typeclass |c{typeclass_path}|n; "
                    "First paragraph of docstring:\n\n{docstring}".format(
                        typeclass_path=typeclass_path, docstring=docstr
                    )
                )
            else:
                txt = "This is typeclass |y{}|n.".format(typeclass)
            return "node_examine_entity", {"text": txt, "back": "typeclass"}
        elif action == "remove":
            prototype = _get_menu_prototype(caller)
            old_typeclass = prototype.pop("typeclass", None)
            if old_typeclass:
                _set_menu_prototype(caller, prototype)
                caller.msg("Cleared typeclass {}.".format(old_typeclass))
            else:
                caller.msg("No typeclass to remove.")
        return "node_typeclass"


def _typeclass_select(caller, typeclass):
    """Select typeclass from list and add it to prototype. Return next node to go to."""
    ret = _set_property(caller, typeclass, prop="typeclass", processor=str)
    caller.msg("Selected typeclass |c{}|n.".format(typeclass))
    return ret


@list_node(_all_typeclasses, _typeclass_select)
def node_typeclass(caller):
    text = """
        The |cTypeclass|n defines what 'type' of object this is - the actual working code to use.

        All spawned objects must have a typeclass. If not given here, the typeclass must be set in
        one of the prototype's |cparents|n.

        {current}
    """.format(
        current=_get_current_value(caller, "typeclass"),
        actions="|WSelect with |w<num>|W. Other actions: "
        "|we|Wxamine |w<num>|W, |wr|Wemove selection",
    )

    helptext = """
        A |nTypeclass|n is specified by the actual python-path to the class definition in the
        Evennia code structure.

        Which |cAttributes|n, |cLocks|n and other properties have special
        effects or expects certain values depend greatly on the code in play.
    """

    text = (text, helptext)

    options = _wizard_options("typeclass", "prototype_parent", "key", color="|W")
    options.append({"key": "_default", "goto": _typeclass_actions})
    return text, options


# key node


def node_key(caller):
    text = """
        The |cKey|n is the given name of the object to spawn. This will retain the given case.

        {current}
    """.format(
        current=_get_current_value(caller, "key")
    )

    helptext = """
        The key should often not be identical for every spawned object. Using a randomising
        $protfunc can be used, for example |c$choice(Alan, Tom, John)|n will give one of the three
        names every time an object of this prototype is spawned.

        |c$protfuncs|n
        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("key", "typeclass", "aliases")
    options.append(
        {
            "key": "_default",
            "goto": (_set_property, dict(prop="key", processor=lambda s: s.strip())),
        }
    )
    return text, options


# aliases node


def _all_aliases(caller):
    "Get aliases in prototype"
    prototype = _get_menu_prototype(caller)
    return prototype.get("aliases", [])


def _aliases_select(caller, alias):
    "Add numbers as aliases"
    aliases = _all_aliases(caller)
    try:
        ind = str(aliases.index(alias) + 1)
        if ind not in aliases:
            aliases.append(ind)
            _set_prototype_value(caller, "aliases", aliases)
            caller.msg("Added alias '{}'.".format(ind))
    except (IndexError, ValueError) as err:
        caller.msg("Error: {}".format(err))

    return "node_aliases"


def _aliases_actions(caller, raw_inp, **kwargs):
    """Parse actions for aliases listing"""
    choices = kwargs.get("available_choices", [])
    alias, action = _default_parse(raw_inp, choices, ("remove", "r", "delete", "d"))

    aliases = _all_aliases(caller)
    if alias and action == "remove":
        try:
            aliases.remove(alias)
            _set_prototype_value(caller, "aliases", aliases)
            caller.msg("Removed alias '{}'.".format(alias))
        except ValueError:
            caller.msg("No matching alias found to remove.")
    else:
        # if not a valid remove, add as a new alias
        alias = raw_inp.lower().strip()
        if alias and alias not in aliases:
            aliases.append(alias)
            _set_prototype_value(caller, "aliases", aliases)
            caller.msg("Added alias '{}'.".format(alias))
        else:
            caller.msg("Alias '{}' was already set.".format(alias))
    return "node_aliases"


@list_node(_all_aliases, _aliases_select)
def node_aliases(caller):

    text = """
        |cAliases|n are alternative ways to address an object, next to its |cKey|n.  Aliases are not
        case sensitive.

        {current}
    """.format(
        current=_get_current_value(
            caller,
            "aliases",
            comparer=lambda propval, flatval: [al for al in flatval if al not in propval],
            formatter=lambda lst: "\n" + ", ".join(lst),
            only_inherit=True,
        )
    )
    _set_actioninfo(
        caller, _format_list_actions("remove", prefix="|w<text>|W to add new alias. Other action: ")
    )

    helptext = """
        Aliases are fixed alternative identifiers and are stored with the new object.

        |c$protfuncs|n

        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("aliases", "key", "attrs")
    options.append({"key": "_default", "goto": _aliases_actions})
    return text, options


# attributes node


def _caller_attrs(caller):
    prototype = _get_menu_prototype(caller)
    attrs = [
        "{}={}".format(tup[0], utils.crop(utils.to_str(tup[1]), width=10))
        for tup in prototype.get("attrs", [])
    ]
    return attrs


def _get_tup_by_attrname(caller, attrname):
    prototype = _get_menu_prototype(caller)
    attrs = prototype.get("attrs", [])
    try:
        inp = [tup[0] for tup in attrs].index(attrname)
        return attrs[inp]
    except ValueError:
        return None


def _display_attribute(attr_tuple):
    """Pretty-print attribute tuple"""
    attrkey, value, category, locks = attr_tuple
    value = protlib.protfunc_parser(value)
    typ = type(value)
    out = "{attrkey} |c=|n {value} |W({typ}{category}{locks})|n".format(
        attrkey=attrkey,
        value=value,
        typ=typ,
        category=", category={}".format(category) if category else "",
        locks=", locks={}".format(";".join(locks)) if any(locks) else "",
    )

    return out


def _add_attr(caller, attr_string, **kwargs):
    """
    Add new attribute, parsing input.

    Args:
        caller (Object): Caller of menu.
        attr_string (str): Input from user
            attr is entered on these forms
                attr = value
                attr;category = value
                attr;category;lockstring = value
    Kwargs:
        delete (str): If this is set, attr_string is
            considered the name of the attribute to delete and
            no further parsing happens.
    Returns:
        result (str): Result string of action.
    """
    attrname = ""
    value = ""
    category = None
    locks = ""

    if "delete" in kwargs:
        attrname = attr_string.lower().strip()
    elif "=" in attr_string:
        attrname, value = (part.strip() for part in attr_string.split("=", 1))
        attrname = attrname.lower()
        nameparts = attrname.split(";", 2)
        nparts = len(nameparts)
        if nparts == 2:
            attrname, category = nameparts
        elif nparts > 2:
            attrname, category, locks = nameparts
    attr_tuple = (attrname, value, category, str(locks))

    if attrname:
        prot = _get_menu_prototype(caller)
        attrs = prot.get("attrs", [])

        if "delete" in kwargs:
            try:
                ind = [tup[0] for tup in attrs].index(attrname)
                del attrs[ind]
                _set_prototype_value(caller, "attrs", attrs)
                return "Removed Attribute '{}'".format(attrname)
            except IndexError:
                return "Attribute to delete not found."

        try:
            # replace existing attribute with the same name in the prototype
            ind = [tup[0] for tup in attrs].index(attrname)
            attrs[ind] = attr_tuple
            text = "Edited Attribute '{}'.".format(attrname)
        except ValueError:
            attrs.append(attr_tuple)
            text = "Added Attribute " + _display_attribute(attr_tuple)

        _set_prototype_value(caller, "attrs", attrs)
    else:
        text = "Attribute must be given as 'attrname[;category;locks] = <value>'."

    return text


def _attr_select(caller, attrstr):
    attrname, _ = attrstr.split("=", 1)
    attrname = attrname.strip()

    attr_tup = _get_tup_by_attrname(caller, attrname)
    if attr_tup:
        return "node_examine_entity", {"text": _display_attribute(attr_tup), "back": "attrs"}
    else:
        caller.msg("Attribute not found.")
        return "node_attrs"


def _attrs_actions(caller, raw_inp, **kwargs):
    """Parse actions for attribute listing"""
    choices = kwargs.get("available_choices", [])
    attrstr, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("remove", "r", "delete", "d")
    )
    if attrstr is None:
        attrstr = raw_inp
    try:
        attrname, _ = attrstr.split("=", 1)
    except ValueError:
        caller.msg("|rNeed to enter the attribute on the form attrname=value.|n")
        return "node_attrs"

    attrname = attrname.strip()
    attr_tup = _get_tup_by_attrname(caller, attrname)

    if action and attr_tup:
        if action == "examine":
            return "node_examine_entity", {"text": _display_attribute(attr_tup), "back": "attrs"}
        elif action == "remove":
            res = _add_attr(caller, attrname, delete=True)
            caller.msg(res)
    else:
        res = _add_attr(caller, raw_inp)
        caller.msg(res)
    return "node_attrs"


@list_node(_caller_attrs, _attr_select)
def node_attrs(caller):
    def _currentcmp(propval, flatval):
        "match by key + category"
        cmp1 = [(tup[0].lower(), tup[2].lower() if tup[2] else None) for tup in propval]
        return [
            tup
            for tup in flatval
            if (tup[0].lower(), tup[2].lower() if tup[2] else None) not in cmp1
        ]

    text = """
        |cAttributes|n are custom properties of the object. Enter attributes on one of these forms:

        attrname=value
        attrname;category=value
        attrname;category;lockstring=value

        To give an attribute without a category but with a lockstring, leave that spot empty
        (attrname;;lockstring=value). Attribute values can have embedded $protfuncs.

        {current}
    """.format(
        current=_get_current_value(
            caller,
            "attrs",
            comparer=_currentcmp,
            formatter=lambda lst: "\n" + "\n".join(_display_attribute(tup) for tup in lst),
            only_inherit=True,
        )
    )
    _set_actioninfo(caller, _format_list_actions("examine", "remove", prefix="Actions: "))

    helptext = """
        Most commonly, Attributes don't need any categories or locks. If using locks, the lock-types
        'attredit' and 'attrread' are used to limit editing and viewing of the Attribute. Putting
        the lock-type `attrcreate` in the |clocks|n prototype key can be used to restrict builders
        from adding new Attributes.

        |c$protfuncs

        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("attrs", "aliases", "tags")
    options.append({"key": "_default", "goto": _attrs_actions})
    return text, options


# tags node


def _caller_tags(caller):
    prototype = _get_menu_prototype(caller)
    tags = [tup[0] for tup in prototype.get("tags", [])]
    return tags


def _get_tup_by_tagname(caller, tagname):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get("tags", [])
    try:
        inp = [tup[0] for tup in tags].index(tagname)
        return tags[inp]
    except ValueError:
        return None


def _display_tag(tag_tuple):
    """Pretty-print tag tuple"""
    tagkey, category, data = tag_tuple
    out = "Tag: '{tagkey}' (category: {category}{dat})".format(
        tagkey=tagkey, category=category, dat=", data: {}".format(data) if data else ""
    )
    return out


def _add_tag(caller, tag_string, **kwargs):
    """
    Add tags to the system, parsing input

    Args:
        caller (Object): Caller of menu.
        tag_string (str): Input from user on one of these forms
            tagname
            tagname;category
            tagname;category;data

    Kwargs:
        delete (str): If this is set, tag_string is considered
            the name of the tag to delete.

    Returns:
        result (str): Result string of action.

    """
    tag = tag_string.strip().lower()
    category = None
    data = ""

    if "delete" in kwargs:
        tag = tag_string.lower().strip()
    else:
        nameparts = tag.split(";", 2)
        ntuple = len(nameparts)
        if ntuple == 2:
            tag, category = nameparts
        elif ntuple > 2:
            tag, category, data = nameparts[:3]

    tag_tuple = (tag.lower(), category.lower() if category else None, data)

    if tag:
        prot = _get_menu_prototype(caller)
        tags = prot.get("tags", [])

        old_tag = _get_tup_by_tagname(caller, tag)

        if "delete" in kwargs:

            if old_tag:
                tags.pop(tags.index(old_tag))
                text = "Removed Tag '{}'.".format(tag)
            else:
                text = "Found no Tag to remove."
        elif not old_tag:
            # a fresh, new tag
            tags.append(tag_tuple)
            text = "Added Tag '{}'".format(tag)
        else:
            # old tag exists; editing a tag means replacing old with new
            ind = tags.index(old_tag)
            tags[ind] = tag_tuple
            text = "Edited Tag '{}'".format(tag)

        _set_prototype_value(caller, "tags", tags)
    else:
        text = "Tag must be given as 'tag[;category;data]'."

    return text


def _tag_select(caller, tagname):
    tag_tup = _get_tup_by_tagname(caller, tagname)
    if tag_tup:
        return "node_examine_entity", {"text": _display_tag(tag_tup), "back": "attrs"}
    else:
        caller.msg("Tag not found.")
        return "node_attrs"


def _tags_actions(caller, raw_inp, **kwargs):
    """Parse actions for tags listing"""
    choices = kwargs.get("available_choices", [])
    tagname, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("remove", "r", "delete", "d")
    )

    if tagname is None:
        tagname = raw_inp.lower().strip()

    tag_tup = _get_tup_by_tagname(caller, tagname)

    if tag_tup:
        if action == "examine":
            return "node_examine_entity", {"text": _display_tag(tag_tup), "back": "tags"}
        elif action == "remove":
            res = _add_tag(caller, tagname, delete=True)
            caller.msg(res)
    else:
        res = _add_tag(caller, raw_inp)
        caller.msg(res)
    return "node_tags"


@list_node(_caller_tags, _tag_select)
def node_tags(caller):
    def _currentcmp(propval, flatval):
        "match by key + category"
        cmp1 = [(tup[0].lower(), tup[1].lower() if tup[2] else None) for tup in propval]
        return [
            tup
            for tup in flatval
            if (tup[0].lower(), tup[1].lower() if tup[1] else None) not in cmp1
        ]

    text = """
        |cTags|n are used to group objects so they can quickly be found later. Enter tags on one of
        the following forms:
            tagname
            tagname;category
            tagname;category;data

        {current}
    """.format(
        current=_get_current_value(
            caller,
            "tags",
            comparer=_currentcmp,
            formatter=lambda lst: "\n" + "\n".join(_display_tag(tup) for tup in lst),
            only_inherit=True,
        )
    )
    _set_actioninfo(caller, _format_list_actions("examine", "remove", prefix="Actions: "))

    helptext = """
        Tags are shared between all objects with that tag. So the 'data' field (which is not
        commonly used) can only hold eventual info about the Tag itself, not about the individual
        object on which it sits.

        All objects created with this prototype will automatically get assigned a tag named the same
        as the |cprototype_key|n and with a category "{tag_category}". This allows the spawner to
        optionally update previously spawned objects when their prototype changes.
    """.format(
        tag_category=protlib._PROTOTYPE_TAG_CATEGORY
    )

    text = (text, helptext)
    options = _wizard_options("tags", "attrs", "locks")
    options.append({"key": "_default", "goto": _tags_actions})
    return text, options


# locks node


def _caller_locks(caller):
    locks = _get_menu_prototype(caller).get("locks", "")
    return [lck for lck in locks.split(";") if lck]


def _locks_display(caller, lock):
    return lock


def _lock_select(caller, lockstr):
    return "node_examine_entity", {"text": _locks_display(caller, lockstr), "back": "locks"}


def _lock_add(caller, lock, **kwargs):
    locks = _caller_locks(caller)

    try:
        locktype, lockdef = lock.split(":", 1)
    except ValueError:
        return "Lockstring lacks ':'."

    locktype = locktype.strip().lower()

    if "delete" in kwargs:
        try:
            ind = locks.index(lock)
            locks.pop(ind)
            _set_prototype_value(caller, "locks", ";".join(locks), parse=False)
            ret = "Lock {} deleted.".format(lock)
        except ValueError:
            ret = "No lock found to delete."
        return ret
    try:
        locktypes = [lck.split(":", 1)[0].strip().lower() for lck in locks]
        ind = locktypes.index(locktype)
        locks[ind] = lock
        ret = "Lock with locktype '{}' updated.".format(locktype)
    except ValueError:
        locks.append(lock)
        ret = "Added lock '{}'.".format(lock)
    _set_prototype_value(caller, "locks", ";".join(locks))
    return ret


def _locks_actions(caller, raw_inp, **kwargs):
    choices = kwargs.get("available_choices", [])
    lock, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("remove", "r", "delete", "d")
    )

    if lock:
        if action == "examine":
            return "node_examine_entity", {"text": _locks_display(caller, lock), "back": "locks"}
        elif action == "remove":
            ret = _lock_add(caller, lock, delete=True)
            caller.msg(ret)
    else:
        ret = _lock_add(caller, raw_inp)
        caller.msg(ret)

    return "node_locks"


@list_node(_caller_locks, _lock_select)
def node_locks(caller):
    def _currentcmp(propval, flatval):
        "match by locktype"
        cmp1 = [lck.split(":", 1)[0] for lck in propval.split(";")]
        return ";".join(lstr for lstr in flatval.split(";") if lstr.split(":", 1)[0] not in cmp1)

    text = """
        The |cLock string|n defines limitations for accessing various properties of the object once
        it's spawned. The string should be on one of the following forms:

            locktype:[NOT] lockfunc(args)
            locktype: [NOT] lockfunc(args) [AND|OR|NOT] lockfunc(args) [AND|OR|NOT] ...

        {current}{action}
        """.format(
        current=_get_current_value(
            caller,
            "locks",
            comparer=_currentcmp,
            formatter=lambda lockstr: "\n".join(
                _locks_display(caller, lstr) for lstr in lockstr.split(";")
            ),
            only_inherit=True,
        ),
        action=_format_list_actions("examine", "remove", prefix="Actions: "),
    )

    helptext = """
        Here is an example of two lock strings:

            edit:false()
            call:tag(Foo) OR perm(Builder)

        Above locks limit two things, 'edit' and 'call'. Which lock types are actually checked
        depend on the typeclass of the object being spawned. Here 'edit' is never allowed by anyone
        while 'call' is allowed to all accessors with a |ctag|n 'Foo' OR which has the
        |cPermission|n 'Builder'.

        |cAvailable lockfuncs:|n

        {lfuncs}
    """.format(
        lfuncs=_format_lockfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("locks", "tags", "permissions")
    options.append({"key": "_default", "goto": _locks_actions})

    return text, options


# permissions node


def _caller_permissions(caller):
    prototype = _get_menu_prototype(caller)
    perms = prototype.get("permissions", [])
    return perms


def _display_perm(caller, permission, only_hierarchy=False):
    hierarchy = settings.PERMISSION_HIERARCHY
    perm_low = permission.lower()
    txt = ""
    if perm_low in [prm.lower() for prm in hierarchy]:
        txt = "Permission (in hieararchy): {}".format(
            ", ".join(
                [
                    "|w[{}]|n".format(prm) if prm.lower() == perm_low else "|W{}|n".format(prm)
                    for prm in hierarchy
                ]
            )
        )
    elif not only_hierarchy:
        txt = "Permission: '{}'".format(permission)
    return txt


def _permission_select(caller, permission, **kwargs):
    return "node_examine_entity", {"text": _display_perm(caller, permission), "back": "permissions"}


def _add_perm(caller, perm, **kwargs):
    if perm:
        perm_low = perm.lower()
        perms = _caller_permissions(caller)
        perms_low = [prm.lower() for prm in perms]
        if "delete" in kwargs:
            try:
                ind = perms_low.index(perm_low)
                del perms[ind]
                text = "Removed Permission '{}'.".format(perm)
            except ValueError:
                text = "Found no Permission to remove."
        else:
            if perm_low in perms_low:
                text = "Permission already set."
            else:
                perms.append(perm)
                _set_prototype_value(caller, "permissions", perms)
                text = "Added Permission '{}'".format(perm)
        return text


def _permissions_actions(caller, raw_inp, **kwargs):
    """Parse actions for permission listing"""
    choices = kwargs.get("available_choices", [])
    perm, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("remove", "r", "delete", "d")
    )

    if perm:
        if action == "examine":
            return (
                "node_examine_entity",
                {"text": _display_perm(caller, perm), "back": "permissions"},
            )
        elif action == "remove":
            res = _add_perm(caller, perm, delete=True)
            caller.msg(res)
    else:
        res = _add_perm(caller, raw_inp.strip())
        caller.msg(res)
    return "node_permissions"


@list_node(_caller_permissions, _permission_select)
def node_permissions(caller):
    def _currentcmp(pval, fval):
        cmp1 = [perm.lower() for perm in pval]
        return [perm for perm in fval if perm.lower() not in cmp1]

    text = """
        |cPermissions|n are simple strings used to grant access to this object. A permission is used
        when a |clock|n is checked that contains the |wperm|n or |wpperm|n lock functions. Certain
        permissions belong in the |cpermission hierarchy|n together with the |Wperm()|n lock
        function.

        {current}
    """.format(
        current=_get_current_value(
            caller,
            "permissions",
            comparer=_currentcmp,
            formatter=lambda lst: "\n" + "\n".join(prm for prm in lst),
            only_inherit=True,
        )
    )
    _set_actioninfo(caller, _format_list_actions("examine", "remove", prefix="Actions: "))

    helptext = """
        Any string can act as a permission as long as a lock is set to look for it. Depending on the
        lock, having a permission could even be negative (i.e. the lock is only passed if you
        |wdon't|n have the 'permission'). The most common permissions are the hierarchical
        permissions:

            {permissions}.

        For example, a |clock|n string like "edit:perm(Builder)" will grant access to accessors
        having the |cpermission|n "Builder" or higher.
    """.format(
        permissions=", ".join(settings.PERMISSION_HIERARCHY)
    )

    text = (text, helptext)

    options = _wizard_options("permissions", "locks", "location")
    options.append({"key": "_default", "goto": _permissions_actions})

    return text, options


# location node


def node_location(caller):

    text = """
        The |cLocation|n of this object in the world. If not given, the object will spawn in the
        inventory of |c{caller}|n by default.

        {current}
    """.format(
        caller=caller.key, current=_get_current_value(caller, "location")
    )

    helptext = """
        You get the most control by not specifying the location - you can then teleport the spawned
        objects as needed later. Setting the location may be useful for quickly populating a given
        location. One could also consider randomizing the location using a $protfunc.

        |c$protfuncs|n
        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("location", "permissions", "home", search=True)
    options.append(
        {
            "key": "_default",
            "goto": (_set_property, dict(prop="location", processor=lambda s: s.strip())),
        }
    )
    return text, options


# home node


def node_home(caller):

    text = """
        The |cHome|n location of an object is often only used as a backup - this is where the object
        will be moved to if its location is deleted. The home location can also be used as an actual
        home for characters to quickly move back to.

        If unset, the global home default (|w{default}|n) will be used.

        {current}
        """.format(
        default=settings.DEFAULT_HOME, current=_get_current_value(caller, "home")
    )
    helptext = """
        The home can be given as a #dbref but can also be specified using the protfunc
        '$obj(name)'. Use |wSE|nearch to find objects in the database.

        The home location is commonly not used except as a backup; using the global default is often
        enough.

        |c$protfuncs|n
        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("home", "location", "destination", search=True)
    options.append(
        {
            "key": "_default",
            "goto": (_set_property, dict(prop="home", processor=lambda s: s.strip())),
        }
    )
    return text, options


# destination node


def node_destination(caller):

    text = """
        The object's |cDestination|n is generally only used by Exit-like objects to designate where
        the exit 'leads to'. It's usually unset for all other types of objects.

        {current}
    """.format(
        current=_get_current_value(caller, "destination")
    )

    helptext = """
        The destination can be given as a #dbref but can also be specified using the protfunc
        '$obj(name)'. Use |wSEearch to find objects in the database.

        |c$protfuncs|n
        {pfuncs}
    """.format(
        pfuncs=_format_protfuncs()
    )

    text = (text, helptext)

    options = _wizard_options("destination", "home", "prototype_desc", search=True)
    options.append(
        {
            "key": "_default",
            "goto": (_set_property, dict(prop="destination", processor=lambda s: s.strip())),
        }
    )
    return text, options


# prototype_desc node


def node_prototype_desc(caller):

    text = """
        The |cPrototype-Description|n briefly describes the prototype when it's viewed in listings.

        {current}
        """.format(
        current=_get_current_value(caller, "prototype_desc")
    )

    helptext = """
        Giving a brief description helps you and others to locate the prototype for use later.
    """

    text = (text, helptext)

    options = _wizard_options("prototype_desc", "prototype_key", "prototype_tags")
    options.append(
        {
            "key": "_default",
            "goto": (
                _set_property,
                dict(
                    prop="prototype_desc",
                    processor=lambda s: s.strip(),
                    next_node="node_prototype_desc",
                ),
            ),
        }
    )

    return text, options


# prototype_tags node


def _caller_prototype_tags(caller):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get("prototype_tags", [])
    tags = [tag[0] if isinstance(tag, tuple) else tag for tag in tags]
    return tags


def _add_prototype_tag(caller, tag_string, **kwargs):
    """
    Add prototype_tags to the system. We only support straight tags, no
    categories (category is assigned automatically).

    Args:
        caller (Object): Caller of menu.
        tag_string (str): Input from user - only tagname

    Kwargs:
        delete (str): If this is set, tag_string is considered
            the name of the tag to delete.

    Returns:
        result (str): Result string of action.

    """
    tag = tag_string.strip().lower()

    if tag:
        tags = _caller_prototype_tags(caller)
        exists = tag in tags

        if "delete" in kwargs:
            if exists:
                tags.pop(tags.index(tag))
                text = "Removed Prototype-Tag '{}'.".format(tag)
            else:
                text = "Found no Prototype-Tag to remove."
        elif not exists:
            # a fresh, new tag
            tags.append(tag)
            text = "Added Prototype-Tag '{}'.".format(tag)
        else:
            text = "Prototype-Tag already added."

        _set_prototype_value(caller, "prototype_tags", tags)
    else:
        text = "No Prototype-Tag specified."

    return text


def _prototype_tag_select(caller, tagname):
    caller.msg("Prototype-Tag: {}".format(tagname))
    return "node_prototype_tags"


def _prototype_tags_actions(caller, raw_inp, **kwargs):
    """Parse actions for tags listing"""
    choices = kwargs.get("available_choices", [])
    tagname, action = _default_parse(raw_inp, choices, ("remove", "r", "delete", "d"))

    if tagname:
        if action == "remove":
            res = _add_prototype_tag(caller, tagname, delete=True)
            caller.msg(res)
    else:
        res = _add_prototype_tag(caller, raw_inp.lower().strip())
        caller.msg(res)
    return "node_prototype_tags"


@list_node(_caller_prototype_tags, _prototype_tag_select)
def node_prototype_tags(caller):

    text = """
        |cPrototype-Tags|n can be used to classify and find prototypes in listings Tag names are not
        case-sensitive and can have not have a custom category.

        {current}
        """.format(
        current=_get_current_value(
            caller,
            "prototype_tags",
            formatter=lambda lst: ", ".join(tg for tg in lst),
            only_inherit=True,
        )
    )
    _set_actioninfo(
        caller, _format_list_actions("remove", prefix="|w<text>|n|W to add Tag. Other Action:|n ")
    )
    helptext = """
        Using prototype-tags is a good way to organize and group large numbers of prototypes by
        genre, type etc. Under the hood, prototypes' tags will all be stored with the category
        '{tagmetacategory}'.
    """.format(
        tagmetacategory=protlib._PROTOTYPE_TAG_META_CATEGORY
    )

    text = (text, helptext)

    options = _wizard_options("prototype_tags", "prototype_desc", "prototype_locks")
    options.append({"key": "_default", "goto": _prototype_tags_actions})

    return text, options


# prototype_locks node


def _caller_prototype_locks(caller):
    locks = _get_menu_prototype(caller).get("prototype_locks", "")
    return [lck for lck in locks.split(";") if lck]


def _prototype_lock_select(caller, lockstr):
    return (
        "node_examine_entity",
        {"text": _locks_display(caller, lockstr), "back": "prototype_locks"},
    )


def _prototype_lock_add(caller, lock, **kwargs):
    locks = _caller_prototype_locks(caller)

    try:
        locktype, lockdef = lock.split(":", 1)
    except ValueError:
        return "Lockstring lacks ':'."

    locktype = locktype.strip().lower()

    if "delete" in kwargs:
        try:
            ind = locks.index(lock)
            locks.pop(ind)
            _set_prototype_value(caller, "prototype_locks", ";".join(locks), parse=False)
            ret = "Prototype-lock {} deleted.".format(lock)
        except ValueError:
            ret = "No Prototype-lock found to delete."
        return ret
    try:
        locktypes = [lck.split(":", 1)[0].strip().lower() for lck in locks]
        ind = locktypes.index(locktype)
        locks[ind] = lock
        ret = "Prototype-lock with locktype '{}' updated.".format(locktype)
    except ValueError:
        locks.append(lock)
        ret = "Added Prototype-lock '{}'.".format(lock)
    _set_prototype_value(caller, "prototype_locks", ";".join(locks))
    return ret


def _prototype_locks_actions(caller, raw_inp, **kwargs):
    choices = kwargs.get("available_choices", [])
    lock, action = _default_parse(
        raw_inp, choices, ("examine", "e"), ("remove", "r", "delete", "d")
    )

    if lock:
        if action == "examine":
            return "node_examine_entity", {"text": _locks_display(caller, lock), "back": "locks"}
        elif action == "remove":
            ret = _prototype_lock_add(caller, lock.strip(), delete=True)
            caller.msg(ret)
    else:
        ret = _prototype_lock_add(caller, raw_inp.strip())
        caller.msg(ret)

    return "node_prototype_locks"


@list_node(_caller_prototype_locks, _prototype_lock_select)
def node_prototype_locks(caller):

    text = """
        |cPrototype-Locks|n are used to limit access to this prototype when someone else is trying
        to access it. By default any prototype can be edited only by the creator and by Admins while
        they can be used by anyone with access to the spawn command. There are two valid lock types
        the prototype access tools look for:

            - 'edit': Who can edit the prototype.
            - 'spawn': Who can spawn new objects with this prototype.

        If unsure, keep the open defaults.

        {current}
    """.format(
        current=_get_current_value(
            caller,
            "prototype_locks",
            formatter=lambda lstring: "\n".join(
                _locks_display(caller, lstr) for lstr in lstring.split(";")
            ),
            only_inherit=True,
        )
    )
    _set_actioninfo(caller, _format_list_actions("examine", "remove", prefix="Actions: "))

    helptext = """
        Prototype locks can be used to vary access for different tiers of builders. It also allows
        developers to produce 'base prototypes' only meant for builders to inherit and expand on
        rather than tweak in-place.
        """

    text = (text, helptext)

    options = _wizard_options("prototype_locks", "prototype_tags", "index")
    options.append({"key": "_default", "goto": _prototype_locks_actions})

    return text, options


# update existing objects node


def _apply_diff(caller, **kwargs):
    """update existing objects"""
    prototype = kwargs["prototype"]
    objects = kwargs["objects"]
    back_node = kwargs["back_node"]
    diff = kwargs.get("diff", None)
    num_changed = spawner.batch_update_objects_with_prototype(prototype, diff=diff, objects=objects)
    caller.msg("|g{num} objects were updated successfully.|n".format(num=num_changed))
    return back_node


def _keep_diff(caller, **kwargs):
    """Change to KEEP setting for a given section of a diff"""
    # from evennia import set_trace;set_trace(term_size=(182, 50))
    path = kwargs["path"]
    diff = kwargs["diff"]
    tmp = diff
    for key in path[:-1]:
        tmp = tmp[key]
    tmp[path[-1]] = tuple(list(tmp[path[-1]][:-1]) + ["KEEP"])


def _format_diff_text_and_options(diff, **kwargs):
    """
    Reformat the diff in a way suitable for the olc menu.

    Args:
        diff (dict): A diff as produced by `prototype_diff`.

    Kwargs:
        any (any): Forwarded into the generated options as arguments to the callable.

    Returns:
        texts (list): List of texts.
        options (list): List of options dict.

    """
    valid_instructions = ("KEEP", "REMOVE", "ADD", "UPDATE")

    def _visualize(obj, rootname, get_name=False):
        if utils.is_iter(obj):
            if get_name:
                return obj[0] if obj[0] else "<unset>"
            if rootname == "attrs":
                return "{} |W=|n {} |W(category:|n {}|W, locks:|n {}|W)|n".format(*obj)
            elif rootname == "tags":
                return "{} |W(category:|n {}|W)|n".format(obj[0], obj[1])
        return "{}".format(obj)

    def _parse_diffpart(diffpart, optnum, *args):
        typ = type(diffpart)
        texts = []
        options = []
        if typ == tuple and len(diffpart) == 3 and diffpart[2] in valid_instructions:
            rootname = args[0]
            old, new, instruction = diffpart
            if instruction == "KEEP":
                texts.append("   |gKEEP|W:|n {old}".format(old=_visualize(old, rootname)))
            else:
                vold = _visualize(old, rootname)
                vnew = _visualize(new, rootname)
                vsep = "" if len(vold) < 78 else "\n"
                vinst = "|rREMOVE|n" if instruction == "REMOVE" else "|y{}|n".format(instruction)
                texts.append(
                    "   |c[{num}] {inst}|W:|n {old} |W->|n{sep} {new}".format(
                        inst=vinst, num=optnum, old=vold, sep=vsep, new=vnew
                    )
                )
                options.append(
                    {
                        "key": str(optnum),
                        "desc": "|gKEEP|n ({}) {}".format(
                            rootname, _visualize(old, args[-1], get_name=True)
                        ),
                        "goto": (_keep_diff, dict((("path", args), ("diff", diff)), **kwargs)),
                    }
                )
                optnum += 1
        else:
            for key in sorted(list(diffpart.keys())):
                subdiffpart = diffpart[key]
                text, option, optnum = _parse_diffpart(subdiffpart, optnum, *(args + (key,)))
                texts.extend(text)
                options.extend(option)
        return texts, options, optnum

    texts = []
    options = []
    # we use this to allow for skipping full KEEP instructions
    optnum = 1

    for root_key in sorted(diff):
        diffpart = diff[root_key]
        text, option, optnum = _parse_diffpart(diffpart, optnum, root_key)

        heading = "- |w{}:|n ".format(root_key)
        if root_key in ("attrs", "tags", "permissions"):
            texts.append(heading)
        elif text:
            text = [heading + text[0]] + text[1:]
        else:
            text = [heading]

        texts.extend(text)
        options.extend(option)

    return texts, options


def node_apply_diff(caller, **kwargs):
    """Offer options for updating objects"""

    def _keep_option(keyname, prototype, base_obj, obj_prototype, diff, objects, back_node):
        """helper returning an option dict"""
        options = {
            "desc": "Keep {} as-is".format(keyname),
            "goto": (
                _keep_diff,
                {
                    "key": keyname,
                    "prototype": prototype,
                    "base_obj": base_obj,
                    "obj_prototype": obj_prototype,
                    "diff": diff,
                    "objects": objects,
                    "back_node": back_node,
                },
            ),
        }
        return options

    prototype = kwargs.get("prototype", None)
    update_objects = kwargs.get("objects", None)
    back_node = kwargs.get("back_node", "node_index")
    obj_prototype = kwargs.get("obj_prototype", None)
    base_obj = kwargs.get("base_obj", None)
    diff = kwargs.get("diff", None)
    custom_location = kwargs.get("custom_location", None)

    if not update_objects:
        text = "There are no existing objects to update."
        options = {"key": "_default", "goto": back_node}
        return text, options

    if not diff:
        # use one random object as a reference to calculate a diff
        base_obj = choice(update_objects)

        diff, obj_prototype = spawner.prototype_diff_from_object(prototype, base_obj)

    helptext = """
        This will go through all existing objects and apply the changes you accept.

        Be careful with this operation! The upgrade mechanism will try to automatically estimate
        what changes need to be applied. But the estimate is |wonly based on the analysis of one
        randomly selected object|n among all objects spawned by this prototype. If that object
        happens to be unusual in some way the estimate will be off and may lead to unexpected
        results for other objects. Always test your objects carefully after an upgrade and consider
        being conservative (switch to KEEP) for things you are unsure of. For complex upgrades it
        may be better to get help from an administrator with access to the `@py` command for doing
        this manually.

        Note that the `location` will never be auto-adjusted because it's so rare to want to
        homogenize the location of all object instances."""

    if not custom_location:
        diff.pop("location", None)

    txt, options = _format_diff_text_and_options(diff, objects=update_objects, base_obj=base_obj)

    if options:
        text = [
            "Suggested changes to {} objects. ".format(len(update_objects)),
            "Showing random example obj to change: {name} ({dbref}))\n".format(
                name=base_obj.key, dbref=base_obj.dbref
            ),
        ] + txt
        options.extend(
            [
                {
                    "key": ("|wu|Wpdate {} objects".format(len(update_objects)), "update", "u"),
                    "desc": "Update {} objects".format(len(update_objects)),
                    "goto": (
                        _apply_diff,
                        {
                            "prototype": prototype,
                            "objects": update_objects,
                            "back_node": back_node,
                            "diff": diff,
                            "base_obj": base_obj,
                        },
                    ),
                },
                {
                    "key": ("|wr|Weset changes", "reset", "r"),
                    "goto": (
                        "node_apply_diff",
                        {"prototype": prototype, "back_node": back_node, "objects": update_objects},
                    ),
                },
            ]
        )
    else:
        text = [
            "Analyzed a random sample object (out of {}) - "
            "found no changes to apply.".format(len(update_objects))
        ]

    options.extend(_wizard_options("update_objects", back_node[5:], None))
    options.append({"key": "_default", "goto": back_node})

    text = "\n".join(text)
    text = (text, helptext)

    return text, options


# prototype save node


def node_prototype_save(caller, **kwargs):
    """Save prototype to disk """
    # these are only set if we selected 'yes' to save on a previous pass
    prototype = kwargs.get("prototype", None)
    # set to True/False if answered, None if first pass
    accept_save = kwargs.get("accept_save", None)

    if accept_save and prototype:
        # we already validated and accepted the save, so this node acts as a goto callback and
        # should now only return the next node
        prototype_key = prototype.get("prototype_key")
        try:
            protlib.save_prototype(prototype)
        except Exception as exc:
            text = "|rCould not save:|n {}\n(press Return to continue)".format(exc)
            options = {"key": "_default", "goto": "node_index"}
            return text, options

        spawned_objects = protlib.search_objects_with_prototype(prototype_key)
        nspawned = spawned_objects.count()

        text = ["|gPrototype saved.|n"]

        if nspawned:
            text.append(
                "\nDo you want to update {} object(s) "
                "already using this prototype?".format(nspawned)
            )
            options = (
                {
                    "key": ("|wY|Wes|n", "yes", "y"),
                    "desc": "Go to updating screen",
                    "goto": (
                        "node_apply_diff",
                        {
                            "accept_update": True,
                            "objects": spawned_objects,
                            "prototype": prototype,
                            "back_node": "node_prototype_save",
                        },
                    ),
                },
                {"key": ("[|wN|Wo|n]", "n"), "desc": "Return to index", "goto": "node_index"},
                {"key": "_default", "goto": "node_index"},
            )
        else:
            text.append("(press Return to continue)")
            options = {"key": "_default", "goto": "node_index"}

        text = "\n".join(text)

        helptext = """
        Updating objects means that the spawner will find all objects previously created by this
        prototype. You will be presented with a list of the changes the system will try to apply to
        each of these objects and you can choose to customize that change if needed. If you have
        done a lot of manual changes to your objects after spawning, you might want to update those
        objects manually instead.
        """

        text = (text, helptext)

        return text, options

    # not validated yet
    prototype = _get_menu_prototype(caller)
    error, text = _validate_prototype(prototype)

    text = [text]

    if error:
        # abort save
        text.append(
            "\n|yValidation errors were found. They need to be corrected before this prototype "
            "can be saved (or used to spawn).|n"
        )
        options = _wizard_options("prototype_save", "index", None)
        options.append({"key": "_default", "goto": "node_index"})
        return "\n".join(text), options

    prototype_key = prototype["prototype_key"]
    if protlib.search_prototype(prototype_key):
        text.append(
            "\nDo you want to save/overwrite the existing prototype '{name}'?".format(
                name=prototype_key
            )
        )
    else:
        text.append("\nDo you want to save the prototype as '{name}'?".format(name=prototype_key))

    text = "\n".join(text)

    helptext = """
        Saving the prototype makes it available for use later. It can also be used to inherit from,
        by name.  Depending on |cprototype-locks|n it also makes the prototype usable and/or
        editable by others. Consider setting good |cPrototype-tags|n and to give a useful, brief
        |cPrototype-desc|n to make the prototype easy to find later.

    """

    text = (text, helptext)

    options = (
        {
            "key": ("[|wY|Wes|n]", "yes", "y"),
            "desc": "Save prototype",
            "goto": ("node_prototype_save", {"accept_save": True, "prototype": prototype}),
        },
        {"key": ("|wN|Wo|n", "n"), "desc": "Abort and return to Index", "goto": "node_index"},
        {
            "key": "_default",
            "goto": ("node_prototype_save", {"accept_save": True, "prototype": prototype}),
        },
    )

    return text, options


# spawning node


def _spawn(caller, **kwargs):
    """Spawn prototype"""
    prototype = kwargs["prototype"].copy()
    new_location = kwargs.get("location", None)
    if new_location:
        prototype["location"] = new_location
    if not prototype.get("location"):
        prototype["location"] = caller

    obj = spawner.spawn(prototype)
    if obj:
        obj = obj[0]
        text = "|gNew instance|n {key} ({dbref}) |gspawned at location |n{loc}|n|g.|n".format(
            key=obj.key, dbref=obj.dbref, loc=prototype["location"]
        )
    else:
        text = "|rError: Spawner did not return a new instance.|n"
    return "node_examine_entity", {"text": text, "back": "prototype_spawn"}


def node_prototype_spawn(caller, **kwargs):
    """Submenu for spawning the prototype"""

    prototype = _get_menu_prototype(caller)

    already_validated = kwargs.get("already_validated", False)

    if already_validated:
        error, text = None, []
    else:
        error, text = _validate_prototype(prototype)
        text = [text]

    if error:
        text.append("\n|rPrototype validation failed. Correct the errors before spawning.|n")
        options = _wizard_options("prototype_spawn", "index", None)
        return "\n".join(text), options

    text = "\n".join(text)

    helptext = """
        Spawning is the act of instantiating a prototype into an actual object. As a new object is
        spawned, every $protfunc in the prototype is called anew. Since this is a common thing to
        do, you may also temporarily change the |clocation|n of this prototype to bypass whatever
        value is set in the prototype.

    """
    text = (text, helptext)

    # show spawn submenu options
    options = []
    prototype_key = prototype["prototype_key"]
    location = prototype.get("location", None)

    if location:
        options.append(
            {
                "desc": "Spawn in prototype's defined location ({loc})".format(loc=location),
                "goto": (
                    _spawn,
                    dict(prototype=prototype, location=location, custom_location=True),
                ),
            }
        )
    caller_loc = caller.location
    if location != caller_loc:
        options.append(
            {
                "desc": "Spawn in {caller}'s location ({loc})".format(
                    caller=caller, loc=caller_loc
                ),
                "goto": (_spawn, dict(prototype=prototype, location=caller_loc)),
            }
        )
    if location != caller_loc != caller:
        options.append(
            {
                "desc": "Spawn in {caller}'s inventory".format(caller=caller),
                "goto": (_spawn, dict(prototype=prototype, location=caller)),
            }
        )

    spawned_objects = protlib.search_objects_with_prototype(prototype_key)
    nspawned = spawned_objects.count()
    if spawned_objects:
        options.append(
            {
                "desc": "Update {num} existing objects with this prototype".format(num=nspawned),
                "goto": (
                    "node_apply_diff",
                    {
                        "objects": list(spawned_objects),
                        "prototype": prototype,
                        "back_node": "node_prototype_spawn",
                    },
                ),
            }
        )
    options.extend(_wizard_options("prototype_spawn", "index", None))
    options.append({"key": "_default", "goto": "node_index"})

    return text, options


# prototype load node


def _prototype_load_select(caller, prototype_key):
    matches = protlib.search_prototype(key=prototype_key)
    if matches:
        prototype = matches[0]
        _set_menu_prototype(caller, prototype)
        return (
            "node_examine_entity",
            {
                "text": "|gLoaded prototype {}.|n".format(prototype["prototype_key"]),
                "back": "index",
            },
        )
    else:
        caller.msg("|rFailed to load prototype '{}'.".format(prototype_key))
        return None


def _prototype_load_actions(caller, raw_inp, **kwargs):
    """Parse the default Convert prototype to a string representation for closer inspection"""
    choices = kwargs.get("available_choices", [])
    prototype, action = _default_parse(
        raw_inp, choices, ("examine", "e", "l"), ("delete", "del", "d")
    )

    if prototype:

        # which action to apply on the selection
        if action == "examine":
            # examine the prototype
            prototype = protlib.search_prototype(key=prototype)[0]
            txt = protlib.prototype_to_str(prototype)
            return "node_examine_entity", {"text": txt, "back": "prototype_load"}
        elif action == "delete":
            # delete prototype from disk
            try:
                protlib.delete_prototype(prototype, caller=caller)
            except protlib.PermissionError as err:
                txt = "|rDeletion error:|n {}".format(err)
            else:
                txt = "|gPrototype {} was deleted.|n".format(prototype)
            return "node_examine_entity", {"text": txt, "back": "prototype_load"}

    return "node_prototype_load"


@list_node(_all_prototype_parents, _prototype_load_select)
def node_prototype_load(caller, **kwargs):
    """Load prototype"""

    text = """
        Select a prototype to load. This will replace any prototype currently being edited!
    """
    _set_actioninfo(caller, _format_list_actions("examine", "delete"))

    helptext = """
        Loading a prototype will load it and return you to the main index. It can be a good idea
        to examine the prototype before loading it.
    """

    text = (text, helptext)

    options = _wizard_options("prototype_load", "index", None)
    options.append({"key": "_default", "goto": _prototype_load_actions})

    return text, options


# EvMenu definition, formatting and access functions


class OLCMenu(EvMenu):
    """
    A custom EvMenu with a different formatting for the options.

    """

    def nodetext_formatter(self, nodetext):
        """
        Format the node text itself.

        """
        return super(OLCMenu, self).nodetext_formatter(nodetext)

    def options_formatter(self, optionlist):
        """
        Split the options into two blocks - olc options and normal options

        """
        olc_keys = (
            "index",
            "forward",
            "back",
            "previous",
            "next",
            "validate prototype",
            "save prototype",
            "load prototype",
            "spawn prototype",
            "search objects",
        )
        actioninfo = self.actioninfo + "\n" if hasattr(self, "actioninfo") else ""
        self.actioninfo = ""  # important, or this could bleed over to other nodes
        olc_options = []
        other_options = []
        for key, desc in optionlist:
            raw_key = strip_ansi(key).lower()
            if raw_key in olc_keys:
                desc = " {}".format(desc) if desc else ""
                olc_options.append("|lc{}|lt{}|le{}".format(raw_key, key, desc))
            else:
                other_options.append((key, desc))

        olc_options = (
            actioninfo + " |W|||n ".join(olc_options) + " |W|||n " + "|wQ|Wuit"
            if olc_options
            else ""
        )
        other_options = super(OLCMenu, self).options_formatter(other_options)
        sep = "\n\n" if olc_options and other_options else ""

        return "{}{}{}".format(olc_options, sep, other_options)

    def helptext_formatter(self, helptext):
        """
        Show help text
        """
        return "|c --- Help ---|n\n" + utils.dedent(helptext)

    def display_helptext(self):
        evmore.msg(self.caller, self.helptext, session=self._session, exit_cmd="look")


def start_olc(caller, session=None, prototype=None):
    """
    Start menu-driven olc system for prototypes.

    Args:
        caller (Object or Account): The entity starting the menu.
        session (Session, optional): The individual session to get data.
        prototype (dict, optional): Given when editing an existing
            prototype rather than creating a new one.

    """
    menudata = {
        "node_index": node_index,
        "node_validate_prototype": node_validate_prototype,
        "node_examine_entity": node_examine_entity,
        "node_search_object": node_search_object,
        "node_prototype_key": node_prototype_key,
        "node_prototype_parent": node_prototype_parent,
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
        "node_apply_diff": node_apply_diff,
        "node_prototype_desc": node_prototype_desc,
        "node_prototype_tags": node_prototype_tags,
        "node_prototype_locks": node_prototype_locks,
        "node_prototype_load": node_prototype_load,
        "node_prototype_save": node_prototype_save,
        "node_prototype_spawn": node_prototype_spawn,
    }
    OLCMenu(
        caller,
        menudata,
        startnode="node_index",
        session=session,
        olc_prototype=prototype,
        debug=True,
    )
