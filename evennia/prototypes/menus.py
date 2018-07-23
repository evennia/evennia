"""

OLC Prototype menu nodes

"""

import json
from random import choice
from django.conf import settings
from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils import evmore
from evennia.utils.ansi import strip_ansi
from evennia.utils import utils
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
    "strings inside lists and dicts.|n")


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
        prop = prototype.get(prop, '')

    out = prop
    if callable(prop):
        if hasattr(prop, '__name__'):
            out = "<{}>".format(prop.__name__)
        else:
            out = repr(prop)
    if utils.is_iter(prop):
        out = ", ".join(str(pr) for pr in prop)
    if not out and required:
        out = "|rrequired"
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
    next_node = kwargs.get("next_node", "node_index")

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
            out.append(" |g(Example-)value when parsed ({}):|n {}".format(
                type(parsed_value), parsed_value))
        else:
            out.append(" |gNo change when parsed.")

    caller.msg("\n".join(out))

    return next_node


def _wizard_options(curr_node, prev_node, next_node, color="|W"):
    """Creates default navigation options available in the wizard."""
    options = []
    if prev_node:
        options.append({"key": ("|wB|Wack", "b"),
                        "desc": "{color}({node})|n".format(
                            color=color, node=prev_node.replace("_", "-")),
                        "goto": "node_{}".format(prev_node)})
    if next_node:
        options.append({"key": ("|wF|Worward", "f"),
                        "desc": "{color}({node})|n".format(
                            color=color, node=next_node.replace("_", "-")),
                        "goto": "node_{}".format(next_node)})

    if "index" not in (prev_node, next_node):
        options.append({"key": ("|wI|Wndex", "i"),
                        "goto": "node_index"})

    if curr_node:
        options.append({"key": ("|wV|Walidate prototype", "validate", "v"),
                        "goto": ("node_validate_prototype", {"back": curr_node})})

    return options


def _path_cropper(pythonpath):
    "Crop path to only the last component"
    return pythonpath.split('.')[-1]


def _validate_prototype(prototype):
    """Run validation on prototype"""

    txt = protlib.prototype_to_str(prototype)
    errors = "\n\n|g No validation errors found.|n (but errors could still happen at spawn-time)"
    err = False
    try:
        # validate, don't spawn
        spawner.spawn(prototype, only_validate=True)
    except RuntimeError as err:
        errors = "\n\n|r{}|n".format(err)
        err = True
    except RuntimeWarning as err:
        errors = "\n\n|y{}|n".format(err)
        err = True

    text = (txt + errors)
    return err, text


def _format_protfuncs():
    out = []
    sorted_funcs = [(key, func) for key, func in
                    sorted(protlib.PROT_FUNCS.items(), key=lambda tup: tup[0])]
    for protfunc_name, protfunc in sorted_funcs:
        out.append("- |c${name}|n - |W{docs}".format(
            name=protfunc_name,
            docs=utils.justify(protfunc.__doc__.strip(), align='l', indent=10).strip()))
    return "\n       ".join(out)


# Menu nodes ------------------------------


# main index (start page) node


def node_index(caller):
    prototype = _get_menu_prototype(caller)

    text = """
       |c --- Prototype wizard --- |n

       A |cprototype|n is a 'template' for |wspawning|n an in-game entity. A field of the prototype
       can be hard-coded or scripted using |w$protfuncs|n - for example to randomize the value
       every time the prototype is used to spawn a new entity.

       The prototype fields named 'prototype_*' are not used to create the entity itself but for
       organizing the template when saving it for you (and maybe others) to use later.

       Select prototype field to edit. If you are unsure, start from [|w1|n]. At any time you can
       [|wV|n]alidate that the prototype works correctly and use it to [|wSP|n]awn a new entity. You
       can also [|wSA|n]ve|n your work or [|wLO|n]oad an existing prototype to use as a base. Use
       [|wL|n]ook to re-show a menu node. [|wQ|n]uit will always exit the menu and [|wH|n]elp will
       show context-sensitive help.
       """
    helptxt = """
       |c- prototypes |n

       A prototype is really just a Python dictionary. When spawning, this dictionary is essentially
       passed into `|wevennia.utils.create.create_object(**prototype)|n` to create a new object. By
       using different prototypes you can customize instances of objects without having to do code
       changes to their typeclass (something which requires code access). The classical example is
       to spawn goblins with different names, looks, equipment and skill, each based on the same
       `Goblin` typeclass.

       |c- $protfuncs |n

       Prototype-functions (protfuncs) allow for limited scripting within a prototype. These are
       entered as a string $funcname(arg, arg, ...) and are evaluated |wat the time of spawning|n only.
       They can also be nested for combined effects.

       {pfuncs}
       """.format(pfuncs=_format_protfuncs())

    text = (text, helptxt)

    options = []
    options.append(
        {"desc": "|WPrototype-Key|n|n{}".format(
            _format_option_value("Key", "prototype_key" not in prototype, prototype, None)),
         "goto": "node_prototype_key"})
    for key in ('Typeclass', 'Prototype-parent', 'Key', 'Aliases', 'Attrs', 'Tags', 'Locks',
                'Permissions', 'Location', 'Home', 'Destination'):
        required = False
        cropper = None
        if key in ("Prototype-parent", "Typeclass"):
            required = ("prototype_parent" not in prototype) and ("typeclass" not in prototype)
        if key == 'Typeclass':
            cropper = _path_cropper
        options.append(
            {"desc": "|w{}|n{}".format(
                key.replace("_", "-"),
                _format_option_value(key, required, prototype, cropper=cropper)),
             "goto": "node_{}".format(key.lower())})
    required = False
    for key in ('Desc', 'Tags', 'Locks'):
        options.append(
            {"desc": "|WPrototype-{}|n|n{}".format(
                key, _format_option_value(key, required, prototype, None)),
             "goto": "node_prototype_{}".format(key.lower())})

    options.extend((
            {"key": ("|wV|Walidate prototype", "validate", "v"),
             "goto": "node_validate_prototype"},
            {"key": ("|wSA|Wve prototype", "save", "sa"),
             "goto": "node_prototype_save"},
            {"key": ("|wSP|Wawn prototype", "spawn", "sp"),
             "goto": "node_prototype_spawn"},
            {"key": ("|wLO|Wad prototype", "load", "lo"),
             "goto": "node_prototype_load"}))

    return text, options


# validate prototype (available as option from all nodes)

def node_validate_prototype(caller, raw_string, **kwargs):
    """General node to view and validate a protototype"""
    prototype = _get_menu_prototype(caller)
    prev_node = kwargs.get("back", "index")

    _, text = _validate_prototype(prototype)

    helptext = """
    The validator checks if the prototype's various values are on the expected form. It also tests
    any $protfuncs.

    """

    text = (text, helptext)

    options = _wizard_options(None, prev_node, None)

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
                caller, old_prototype['prototype_locks'], access_type='edit'):
            # return to the node_prototype_key to try another key
            caller.msg("Prototype '{key}' already exists and you don't "
                       "have permission to edit it.".format(key=key))
            return "node_prototype_key"
        elif olc_new:
            # we are selecting an existing prototype to edit. Reset to index.
            del caller.ndb._menutree.olc_new
            caller.ndb._menutree.olc_prototype = old_prototype
            caller.msg("Prototype already exists. Reloading.")
            return "node_index"

    return _set_property(caller, key, prop='prototype_key', next_node="node_prototype_parent")


def node_prototype_key(caller):
    prototype = _get_menu_prototype(caller)
    text = """
        The |cPrototype-Key|n uniquely identifies the prototype and is |wmandatory|n. It is used to
        find and use the prototype to spawn new entities. It is not case sensitive.

        {current}"""
    helptext = """
        The prototype-key is not itself used when spawnng the new object, but is only used for
        managing, storing and loading the prototype. It must be globally unique, so existing keys
        will be checked before a new key is accepted. If an existing key is picked, the existing
        prototype will be loaded.
        """

    old_key = prototype.get('prototype_key', None)
    if old_key:
        text = text.format(current="Currently set to '|w{key}|n'".format(key=old_key))
    else:
        text = text.format(current="Currently |runset|n (required).")

    options = _wizard_options("prototype_key", "index", "prototype_parent")
    options.append({"key": "_default",
                    "goto": _check_prototype_key})

    text = (text, helptext)
    return text, options


# prototype_parents node


def _all_prototype_parents(caller):
    """Return prototype_key of all available prototypes for listing in menu"""
    return [prototype["prototype_key"]
            for prototype in protlib.search_prototype() if "prototype_key" in prototype]


def _prototype_parent_examine(caller, prototype_name):
    """Convert prototype to a string representation for closer inspection"""
    prototypes = protlib.search_prototype(key=prototype_name)
    if prototypes:
        ret = protlib.prototype_to_str(prototypes[0])
        caller.msg(ret)
        return ret
    else:
        caller.msg("Prototype not registered.")


def _prototype_parent_select(caller, prototype):
    ret = _set_property(caller, "",
                        prop="prototype_parent", processor=str, next_node="node_key")
    caller.msg("Selected prototype |y{}|n. Removed any set typeclass parent.".format(prototype))
    return ret


@list_node(_all_prototype_parents, _prototype_parent_select)
def node_prototype_parent(caller):
    prototype = _get_menu_prototype(caller)

    prot_parent_key = prototype.get('prototype')

    text = """
        The |cPrototype Parent|n allows you to |winherit|n prototype values from another named
        prototype (given as that prototype's |wprototype_key|).  If not changing these values in the
        current prototype, the parent's value will be used. Pick the available prototypes below.

        Note that somewhere in the prototype's parentage, a |ctypeclass|n must be specified. If no
        parent is given, this prototype must define the typeclass (next menu node).

        {current}
        """
    helptext = """
        Prototypes can inherit from one another. Changes in the child replace any values set in a
        parent. The |wtypeclass|n key must exist |wsomewhere|n in the parent chain for the
        prototype to be valid.
        """

    if prot_parent_key:
        prot_parent = protlib.search_prototype(prot_parent_key)
        if prot_parent:
            text.format(
                current="Current parent prototype is {}:\n{}".format(
                    protlib.prototype_to_str(prot_parent)))
        else:
            text.format(
                current="Current parent prototype |r{prototype}|n "
                        "does not appear to exist.".format(prot_parent_key))
    else:
        text.format(current="Parent prototype is not set")
    text = (text, helptext)

    options = _wizard_options("prototype_parent", "prototype_key", "typeclass", color="|W")
    options.append({"key": "_default",
                    "goto": _prototype_parent_examine})

    return text, options


# typeclasses node

def _all_typeclasses(caller):
    """Get name of available typeclasses."""
    return list(name for name in
                sorted(utils.get_all_typeclasses("evennia.objects.models.ObjectDB").keys())
                if name != "evennia.objects.models.ObjectDB")


def _typeclass_examine(caller, typeclass_path):
    """Show info (docstring) about given typeclass."""
    if typeclass_path is None:
        # this means we are exiting the listing
        return "node_key"

    typeclass = utils.get_all_typeclasses().get(typeclass_path)
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
    caller.msg(txt)
    return txt


def _typeclass_select(caller, typeclass):
    """Select typeclass from list and add it to prototype. Return next node to go to."""
    ret = _set_property(caller, typeclass, prop='typeclass', processor=str, next_node="node_key")
    caller.msg("Selected typeclass |y{}|n.".format(typeclass))
    return ret


@list_node(_all_typeclasses, _typeclass_select)
def node_typeclass(caller):
    prototype = _get_menu_prototype(caller)
    typeclass = prototype.get("typeclass")

    text = """
        The |cTypeclass|n defines what 'type' of object this is - the actual working code to use.

        All spawned objects must have a typeclass. If not given here, the typeclass must be set in
        one of the prototype's |cparents|n.

        {current}
    """
    helptext = """
        A |nTypeclass|n is specified by the actual python-path to the class definition in the
        Evennia code structure.

        Which |cAttributes|n, |cLocks|n and other properties have special
        effects or expects certain values depend greatly on the code in play.
    """

    if typeclass:
        text.format(
            current="Current typeclass is |y{typeclass}|n.".format(typeclass=typeclass))
    else:
        text.format(
            current="Using default typeclass {typeclass}.".format(
                typeclass=settings.BASE_OBJECT_TYPECLASS))

    text = (text, helptext)

    options = _wizard_options("typeclass", "prototype_parent", "key", color="|W")
    options.append({"key": "_default",
                    "goto": _typeclass_examine})
    return text, options


# key node


def node_key(caller):
    prototype = _get_menu_prototype(caller)
    key = prototype.get("key")

    text = """
        The |cKey|n is the given name of the object to spawn. This will retain the given case.

        {current}
    """
    helptext = """
        The key should often not be identical for every spawned object. Using a randomising
        $protfunc can be used, for example |c$choice(Alan, Tom, John)|n will give one of the three
        names every time an object of this prototype is spawned.

        |c$protfuncs|n
        {pfuncs}
    """.format(pfuncs=_format_protfuncs())

    if key:
        text.format(current="Current key is '{key}'.".format(key=key))
    else:
        text.format(current="The key is currently unset.")

    text = (text, helptext)

    options = _wizard_options("key", "typeclass", "aliases")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="key",
                                  processor=lambda s: s.strip(),
                                  next_node="node_aliases"))})
    return text, options


# aliases node


def node_aliases(caller):
    prototype = _get_menu_prototype(caller)
    aliases = prototype.get("aliases")

    text = """
        |cAliases|n are alternative ways to address an object, next to its |cKey|n.  Aliases are not
        case sensitive.

        Add multiple aliases separating with commas.

        {current}
    """
    helptext = """
        Aliases are fixed alternative identifiers and are stored with the new object.

        |c$protfuncs|n

        {pfuncs}
    """.format(pfuncs=_format_protfuncs())

    if aliases:
        text.format(current="Current aliases are '|c{aliases}|n'.".format(aliases=aliases))
    else:
        text.format(current="No aliases are set.")

    text = (text, helptext)

    options = _wizard_options("aliases", "key", "attrs")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="aliases",
                                  processor=lambda s: [part.strip() for part in s.split(",")],
                                  next_node="node_attrs"))})
    return text, options


# attributes node


def _caller_attrs(caller):
    prototype = _get_menu_prototype(caller)
    attrs = prototype.get("attrs", [])
    return attrs


def _display_attribute(attr_tuple):
    """Pretty-print attribute tuple"""
    attrkey, value, category, locks = attr_tuple
    value = protlib.protfunc_parser(value)
    typ = type(value)
    out = ("Attribute key: '{attrkey}' (category: {category}, "
           "locks: {locks})\n"
           "Value (parsed to {typ}): {value}").format(
                   attrkey=attrkey,
                   category=category, locks=locks,
                   typ=typ, value=value)
    return out


def _add_attr(caller, attr_string, **kwargs):
    """
    Add new attrubute, parsing input.
    attr is entered on these forms
        attr = value
        attr;category = value
        attr;category;lockstring = value

    """
    attrname = ''
    category = None
    locks = ''

    if '=' in attr_string:
        attrname, value = (part.strip() for part in attr_string.split('=', 1))
        attrname = attrname.lower()
        nameparts = attrname.split(";", 2)
        nparts = len(nameparts)
        if nparts == 2:
            attrname, category = nameparts
        elif nparts > 2:
            attrname, category, locks = nameparts
    attr_tuple = (attrname, value, category, locks)

    if attrname:
        prot = _get_menu_prototype(caller)
        attrs = prot.get('attrs', [])

        try:
            # replace existing attribute with the same name in the prototype
            ind = [tup[0] for tup in attrs].index(attrname)
            attrs[ind] = attr_tuple
        except ValueError:
            attrs.append(attr_tuple)

        _set_prototype_value(caller, "attrs", attrs)

        text = kwargs.get('text')
        if not text:
            if 'edit' in kwargs:
                text = "Edited " + _display_attribute(attr_tuple)
            else:
                text = "Added " + _display_attribute(attr_tuple)
    else:
        text = "Attribute must be given as 'attrname[;category;locks] = <value>'."

    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_attr(caller, attrname, new_value, **kwargs):

    attr_string = "{}={}".format(attrname, new_value)

    return _add_attr(caller, attr_string, edit=True)


def _examine_attr(caller, selection):
    prot = _get_menu_prototype(caller)
    ind = [part[0] for part in prot['attrs']].index(selection)
    attr_tuple = prot['attrs'][ind]
    return _display_attribute(attr_tuple)


@list_node(_caller_attrs)
def node_attrs(caller):
    prot = _get_menu_prototype(caller)
    attrs = prot.get("attrs")

    text = ["Set the prototype's |yAttributes|n. Enter attributes on one of these forms:\n"
            " attrname=value\n attrname;category=value\n attrname;category;lockstring=value\n"
            "To give an attribute without a category but with a lockstring, leave that spot empty "
            "(attrname;;lockstring=value)."
            "Separate multiple attrs with commas. Use quotes to escape inputs with commas and "
            "semi-colon."]
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


# tags node


def _caller_tags(caller):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get("tags", [])
    return tags


def _display_tag(tag_tuple):
    """Pretty-print attribute tuple"""
    tagkey, category, data = tag_tuple
    out = ("Tag: '{tagkey}' (category: {category}{dat})".format(
           tagkey=tagkey, category=category, dat=", data: {}".format(data) if data else ""))
    return out


def _add_tag(caller, tag, **kwargs):
    """
    Add tags to the system, parsing  this syntax:
        tagname
        tagname;category
        tagname;category;data

    """

    tag = tag.strip().lower()
    category = None
    data = ""

    tagtuple = tag.split(";", 2)
    ntuple = len(tagtuple)

    if ntuple == 2:
        tag, category = tagtuple
    elif ntuple > 2:
        tag, category, data = tagtuple

    tag_tuple = (tag, category, data)

    if tag:
        prot = _get_menu_prototype(caller)
        tags = prot.get('tags', [])

        old_tag = kwargs.get("edit", None)

        if not old_tag:
            # a fresh, new tag
            tags.append(tag_tuple)
        else:
            # old tag exists; editing a tag means removing the old and replacing with new
            try:
                ind = [tup[0] for tup in tags].index(old_tag)
                del tags[ind]
                if tags:
                    tags.insert(ind, tag_tuple)
                else:
                    tags = [tag_tuple]
            except IndexError:
                pass

        _set_prototype_value(caller, "tags", tags)

        text = kwargs.get('text')
        if not text:
            if 'edit' in kwargs:
                text = "Edited " + _display_tag(tag_tuple)
            else:
                text = "Added " + _display_tag(tag_tuple)
    else:
        text = "Tag must be given as 'tag[;category;data]."

    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_tag(caller, old_tag, new_tag, **kwargs):
    return _add_tag(caller, new_tag, edit=old_tag)


@list_node(_caller_tags)
def node_tags(caller):
    text = ("Set the prototype's |yTags|n. Enter tags on one of the following forms:\n"
            " tag\n tag;category\n tag;category;data\n"
            "Note that 'data' is not commonly used.")
    options = _wizard_options("tags", "attrs", "locks")
    return text, options


# locks node


def node_locks(caller):
    prototype = _get_menu_prototype(caller)
    locks = prototype.get("locks")

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


# permissions node


def node_permissions(caller):
    prototype = _get_menu_prototype(caller)
    permissions = prototype.get("permissions")

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


# location node


def node_location(caller):
    prototype = _get_menu_prototype(caller)
    location = prototype.get("location")

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


# home node


def node_home(caller):
    prototype = _get_menu_prototype(caller)
    home = prototype.get("home")

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


# destination node


def node_destination(caller):
    prototype = _get_menu_prototype(caller)
    dest = prototype.get("dest")

    text = ["Set the prototype's |yDestination|n. This is usually only used for Exits."]
    if dest:
        text.append("Current destination is |y{dest}|n.".format(dest=dest))
    else:
        text.append("No destination is set (default).")
    text = "\n\n".join(text)
    options = _wizard_options("destination", "home", "prototype_desc")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="dest",
                                  processor=lambda s: s.strip(),
                                  next_node="node_prototype_desc"))})
    return text, options


# prototype_desc node


def node_prototype_desc(caller):

    prototype = _get_menu_prototype(caller)
    text = ["The |wPrototype-Description|n briefly describes the prototype for "
            "viewing in listings."]
    desc = prototype.get("prototype_desc", None)

    if desc:
        text.append("The current meta desc is:\n\"|w{desc}|n\"".format(desc=desc))
    else:
        text.append("Description is currently unset.")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_desc", "prototype_key", "prototype_tags")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop='prototype_desc',
                                  processor=lambda s: s.strip(),
                                  next_node="node_prototype_tags"))})

    return text, options


# prototype_tags node


def node_prototype_tags(caller):
    prototype = _get_menu_prototype(caller)
    text = ["|wPrototype-Tags|n can be used to classify and find prototypes. "
            "Tags are case-insensitive. "
            "Separate multiple by tags by commas."]
    tags = prototype.get('prototype_tags', [])

    if tags:
        text.append("The current tags are:\n|w{tags}|n".format(tags=tags))
    else:
        text.append("No tags are currently set.")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_tags", "prototype_desc", "prototype_locks")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="prototype_tags",
                                  processor=lambda s: [
                                    str(part.strip().lower()) for part in s.split(",")],
                                  next_node="node_prototype_locks"))})
    return text, options


# prototype_locks node


def node_prototype_locks(caller):
    prototype = _get_menu_prototype(caller)
    text = ["Set |wPrototype-Locks|n on the prototype. There are two valid lock types: "
            "'edit' (who can edit the prototype) and 'spawn' (who can spawn new objects with this "
            "prototype)\n(If you are unsure, leave as default.)"]
    locks = prototype.get('prototype_locks', '')
    if locks:
        text.append("Current lock is |w'{lockstring}'|n".format(lockstring=locks))
    else:
        text.append("Lock unset - if not changed the default lockstring will be set as\n"
                    "   |w'spawn:all(); edit:id({dbref}) or perm(Admin)'|n".format(dbref=caller.id))
    text = "\n\n".join(text)
    options = _wizard_options("prototype_locks", "prototype_tags", "index")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="prototype_locks",
                                  processor=lambda s: s.strip().lower(),
                                  next_node="node_index"))})
    return text, options


# update existing objects node


def _update_spawned(caller, **kwargs):
    """update existing objects"""
    prototype = kwargs['prototype']
    objects = kwargs['objects']
    back_node = kwargs['back_node']
    diff = kwargs.get('diff', None)
    num_changed = spawner.batch_update_objects_with_prototype(prototype, diff=diff, objects=objects)
    caller.msg("|g{num} objects were updated successfully.|n".format(num=num_changed))
    return back_node


def _keep_diff(caller, **kwargs):
    key = kwargs['key']
    diff = kwargs['diff']
    diff[key] = "KEEP"


def node_update_objects(caller, **kwargs):
    """Offer options for updating objects"""

    def _keep_option(keyname, prototype, obj, obj_prototype, diff, objects, back_node):
        """helper returning an option dict"""
        options = {"desc": "Keep {} as-is".format(keyname),
                   "goto": (_keep_diff,
                            {"key": keyname, "prototype": prototype,
                             "obj": obj, "obj_prototype": obj_prototype,
                             "diff": diff, "objects": objects, "back_node": back_node})}
        return options

    prototype = kwargs.get("prototype", None)
    update_objects = kwargs.get("objects", None)
    back_node = kwargs.get("back_node", "node_index")
    obj_prototype = kwargs.get("obj_prototype", None)
    diff = kwargs.get("diff", None)

    if not update_objects:
        text = "There are no existing objects to update."
        options = {"key": "_default",
                   "goto": back_node}
        return text, options

    if not diff:
        # use one random object as a reference to calculate a diff
        obj = choice(update_objects)
        diff, obj_prototype = spawner.prototype_diff_from_object(prototype, obj)

    text = ["Suggested changes to {} objects".format(len(update_objects)),
            "Showing random example obj to change: {name} (#{dbref}))\n".format(obj.key, obj.dbref)]
    options = []
    io = 0
    for (key, inst) in sorted(((key, val) for key, val in diff.items()), key=lambda tup: tup[0]):
        line = "{iopt}  |w{key}|n: {old}{sep}{new} {change}"
        old_val = utils.crop(str(obj_prototype[key]), width=20)

        if inst == "KEEP":
            text.append(line.format(iopt='', key=key, old=old_val, sep=" ", new='', change=inst))
            continue

        new_val = utils.crop(str(spawner.init_spawn_value(prototype[key])), width=20)
        io += 1
        if inst in ("UPDATE", "REPLACE"):
            text.append(line.format(iopt=io, key=key, old=old_val,
                        sep=" |y->|n ", new=new_val, change=inst))
            options.append(_keep_option(key, prototype,
                           obj, obj_prototype, diff, update_objects, back_node))
        elif inst == "REMOVE":
            text.append(line.format(iopt=io, key=key, old=old_val,
                        sep=" |r->|n ", new='', change=inst))
            options.append(_keep_option(key, prototype,
                           obj, obj_prototype, diff, update_objects, back_node))
        options.extend(
            [{"key": ("|wu|r update {} objects".format(len(update_objects)), "update", "u"),
              "goto": (_update_spawned, {"prototype": prototype, "objects": update_objects,
                                         "back_node": back_node, "diff": diff})},
             {"key": ("|wr|neset changes", "reset", "r"),
              "goto": ("node_update_objects", {"prototype": prototype, "back_node": back_node,
                                               "objects": update_objects})},
             {"key": "|wb|rack ({})".format(back_node[5:], 'b'),
              "goto": back_node}])

        return text, options


# prototype save node


def node_prototype_save(caller, **kwargs):
    """Save prototype to disk """
    # these are only set if we selected 'yes' to save on a previous pass
    prototype = kwargs.get("prototype", None)
    accept_save = kwargs.get("accept_save", False)

    if accept_save and prototype:
        # we already validated and accepted the save, so this node acts as a goto callback and
        # should now only return the next node
        prototype_key = prototype.get("prototype_key")
        protlib.save_prototype(**prototype)

        spawned_objects = protlib.search_objects_with_prototype(prototype_key)
        nspawned = spawned_objects.count()

        if nspawned:
            text = ("Do you want to update {} object(s) "
                    "already using this prototype?".format(nspawned))
            options = (
                {"key": ("|wY|Wes|n", "yes", "y"),
                 "goto": ("node_update_objects",
                          {"accept_update": True, "objects": spawned_objects,
                           "prototype": prototype, "back_node": "node_prototype_save"})},
                {"key": ("[|wN|Wo|n]", "n"),
                 "goto": "node_spawn"},
                {"key": "_default",
                 "goto": "node_spawn"})
        else:
            text = "|gPrototype saved.|n"
            options = {"key": "_default",
                       "goto": "node_spawn"}

        return text, options

    # not validated yet
    prototype = _get_menu_prototype(caller)
    error, text = _validate_prototype(prototype)

    text = [text]

    if error:
        # abort save
        text.append(
            "Validation errors were found. They need to be corrected before this prototype "
            "can be saved (or used to spawn).")
        options = _wizard_options("prototype_save", "prototype_locks", "index")
        return "\n".join(text),  options

    prototype_key = prototype['prototype_key']
    if protlib.search_prototype(prototype_key):
        text.append("Do you want to save/overwrite the existing prototype '{name}'?".format(
            name=prototype_key))
    else:
        text.append("Do you want to save the prototype as '{name}'?".format(prototype_key))

    options = (
        {"key": ("[|wY|Wes|n]", "yes", "y"),
         "goto": ("node_prototype_save",
                  {"accept": True, "prototype": prototype})},
        {"key": ("|wN|Wo|n", "n"),
         "goto": "node_spawn"},
        {"key": "_default",
         "goto": ("node_prototype_save",
                  {"accept": True, "prototype": prototype})})

    return "\n".join(text),  options


# spawning node


def _spawn(caller, **kwargs):
    """Spawn prototype"""
    prototype = kwargs["prototype"].copy()
    new_location = kwargs.get('location', None)
    if new_location:
        prototype['location'] = new_location

    obj = spawner.spawn(prototype)
    if obj:
        obj = obj[0]
        caller.msg("|gNew instance|n {key} ({dbref}) |gspawned.|n".format(
            key=obj.key, dbref=obj.dbref))
    else:
        caller.msg("|rError: Spawner did not return a new instance.|n")
    return obj


def node_prototype_spawn(caller, **kwargs):
    """Submenu for spawning the prototype"""

    prototype = _get_menu_prototype(caller)
    error, text = _validate_prototype(prototype)

    text = [text]

    if error:
        text.append("|rPrototype validation failed. Correct the errors before spawning.|n")
        options = _wizard_options("prototype_spawn", "prototype_locks", "index")
        return "\n".join(text), options

    # show spawn submenu options
    options = []
    prototype_key = prototype['prototype_key']
    location = prototype.get('location', None)

    if location:
        options.append(
            {"desc": "Spawn in prototype's defined location ({loc})".format(loc=location),
             "goto": (_spawn,
                      dict(prototype=prototype))})
    caller_loc = caller.location
    if location != caller_loc:
        options.append(
            {"desc": "Spawn in {caller}'s location ({loc})".format(
                caller=caller, loc=caller_loc),
             "goto": (_spawn,
                      dict(prototype=prototype, location=caller_loc))})
    if location != caller_loc != caller:
        options.append(
            {"desc": "Spawn in {caller}'s inventory".format(caller=caller),
             "goto": (_spawn,
                      dict(prototype=prototype, location=caller))})

    spawned_objects = protlib.search_objects_with_prototype(prototype_key)
    nspawned = spawned_objects.count()
    if spawned_objects:
        options.append(
           {"desc": "Update {num} existing objects with this prototype".format(num=nspawned),
            "goto": ("node_update_objects",
                     dict(prototype=prototype, opjects=spawned_objects,
                          back_node="node_prototype_spawn"))})
    options.extend(_wizard_options("prototype_spawn", "prototype_save", "index"))
    return text, options


# prototype load node


def _prototype_load_select(caller, prototype_key):
    matches = protlib.search_prototype(key=prototype_key)
    if matches:
        prototype = matches[0]
        _set_menu_prototype(caller, prototype)
        caller.msg("|gLoaded prototype '{}'.".format(prototype_key))
        return "node_index"
    else:
        caller.msg("|rFailed to load prototype '{}'.".format(prototype_key))
        return None


@list_node(_all_prototype_parents, _prototype_load_select)
def node_prototype_load(caller, **kwargs):
    text = ["Select a prototype to load. This will replace any currently edited prototype."]
    options = _wizard_options("prototype_load", "prototype_save", "index")
    options.append({"key": "_default",
                    "goto": _prototype_parent_examine})
    return "\n".join(text), options


# EvMenu definition, formatting and access functions


class OLCMenu(EvMenu):
    """
    A custom EvMenu with a different formatting for the options.

    """
    def options_formatter(self, optionlist):
        """
        Split the options into two blocks - olc options and normal options

        """
        olc_keys = ("index", "forward", "back", "previous", "next", "validate prototype",
                    "save prototype", "load prototype", "spawn prototype")
        olc_options = []
        other_options = []
        for key, desc in optionlist:
            raw_key = strip_ansi(key).lower()
            if raw_key in olc_keys:
                desc = " {}".format(desc) if desc else ""
                olc_options.append("|lc{}|lt{}|le{}".format(raw_key, key, desc))
            else:
                other_options.append((key, desc))

        olc_options = " | ".join(olc_options) + " | " + "|wQ|Wuit" if olc_options else ""
        other_options = super(OLCMenu, self).options_formatter(other_options)
        sep = "\n\n" if olc_options and other_options else ""

        return "{}{}{}".format(olc_options, sep, other_options)

    def helptext_formatter(self, helptext):
        """
        Show help text
        """
        return "|c --- Help ---|n\n" + helptext

    def display_helptext(self):
        evmore.msg(self.caller, self.helptext, session=self._session)


def start_olc(caller, session=None, prototype=None):
    """
    Start menu-driven olc system for prototypes.

    Args:
        caller (Object or Account): The entity starting the menu.
        session (Session, optional): The individual session to get data.
        prototype (dict, optional): Given when editing an existing
            prototype rather than creating a new one.

    """
    menudata = {"node_index": node_index,
                "node_validate_prototype": node_validate_prototype,
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
                "node_update_objects": node_update_objects,
                "node_prototype_desc": node_prototype_desc,
                "node_prototype_tags": node_prototype_tags,
                "node_prototype_locks": node_prototype_locks,
                "node_prototype_load": node_prototype_load,
                "node_prototype_save": node_prototype_save,
                "node_prototype_spawn": node_prototype_spawn
                }
    OLCMenu(caller, menudata, startnode='node_index', session=session, olc_prototype=prototype)
