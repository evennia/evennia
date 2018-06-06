"""

OLC Prototype menu nodes

"""

from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils.ansi import strip_ansi

# ------------------------------------------------------------
#
# OLC Prototype design menu
#
# ------------------------------------------------------------

# Helper functions


def _get_menu_prototype(caller):

    prototype = None
    if hasattr(caller.ndb._menutree, "olc_prototype"):
        prototype = caller.ndb._menutree.olc_prototype
    if not prototype:
        caller.ndb._menutree.olc_prototype = prototype = {}
        caller.ndb._menutree.olc_new = True
    return prototype


def _is_new_prototype(caller):
    return hasattr(caller.ndb._menutree, "olc_new")


def _set_menu_prototype(caller, field, value):
    prototype = _get_menu_prototype(caller)
    prototype[field] = value
    caller.ndb._menutree.olc_prototype = prototype


def _format_property(prop, required=False, prototype=None, cropper=None):

    if prototype is not None:
        prop = prototype.get(prop, '')

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
    prop = kwargs.get("prop", "prototype_key")
    processor = kwargs.get("processor", None)
    next_node = kwargs.get("next_node", "node_index")

    propname_low = prop.strip().lower()

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

    prototype = _get_menu_prototype(caller)

    # typeclass and prototype can't co-exist
    if propname_low == "typeclass":
        prototype.pop("prototype", None)
    if propname_low == "prototype":
        prototype.pop("typeclass", None)

    caller.ndb._menutree.olc_prototype = prototype

    caller.msg("Set {prop} to '{value}'.".format(prop, value=str(value)))

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
    prototype = _get_menu_prototype(caller)

    text = ("|c --- Prototype wizard --- |n\n\n"
            "Define the |yproperties|n of the prototype. All prototype values can be "
            "over-ridden at the time of spawning an instance of the prototype, but some are "
            "required.\n\n'|wMeta'-properties|n are not used in the prototype itself but are used "
            "to organize and list prototypes. The 'Meta-Key' uniquely identifies the prototype "
            "and allows you to edit an existing prototype or save a new one for use by you or "
            "others later.\n\n(make choice; q to abort. If unsure, start from 1.)")

    options = []
    options.append(
        {"desc": "|WPrototype-Key|n|n{}".format(_format_property("Key", True, prototype, None)),
         "goto": "node_prototype_key"})
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
                key, _format_property(key, required, prototype, cropper=cropper)),
             "goto": "node_{}".format(key.lower())})
    required = False
    for key in ('Desc', 'Tags', 'Locks'):
        options.append(
            {"desc": "|WPrototype-{}|n|n{}".format(key, _format_property(key, required, prototype, None)),
             "goto": "node_prototype_{}".format(key.lower())})

    return text, options


def node_validate_prototype(caller, raw_string, **kwargs):
    prototype = _get_menu_prototype(caller)

    txt = prototype_to_str(prototype)
    errors = "\n\n|g No validation errors found.|n (but errors could still happen at spawn-time)"
    try:
        # validate, don't spawn
        spawn(prototype, return_prototypes=True)
    except RuntimeError as err:
        errors = "\n\n|rError: {}|n".format(err)
    text = (txt + errors)

    options = _wizard_options(None, kwargs.get("back"), None)

    return text, options


def _check_prototype_key(caller, key):
    old_prototype = search_prototype(key)
    olc_new = _is_new_prototype(caller)
    key = key.strip().lower()
    if old_prototype:
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

    return _set_property(caller, key, prop='prototype_key', next_node="node_prototype")


def node_prototype_key(caller):
    prototype = _get_menu_prototype(caller)
    text = ["The prototype name, or |wMeta-Key|n, uniquely identifies the prototype. "
            "It is used to find and use the prototype to spawn new entities. "
            "It is not case sensitive."]
    old_key = prototype.get('prototype_key', None)
    if old_key:
        text.append("Current key is '|w{key}|n'".format(key=old_key))
    else:
        text.append("The key is currently unset.")
    text.append("Enter text or make a choice (q for quit)")
    text = "\n\n".join(text)
    options = _wizard_options("prototype_key", "index", "prototype")
    options.append({"key": "_default",
                    "goto": _check_prototype_key})
    return text, options


def _all_prototypes(caller):
    return [prototype["prototype_key"]
            for prototype in search_prototype() if "prototype_key" in prototype]


def _prototype_examine(caller, prototype_name):
    prototypes = search_prototype(key=prototype_name)
    if prototypes:
        caller.msg(prototype_to_str(prototypes[0]))
    caller.msg("Prototype not registered.")
    return None


def _prototype_select(caller, prototype):
    ret = _set_property(caller, prototype, prop="prototype", processor=str, next_node="node_key")
    caller.msg("Selected prototype |y{}|n. Removed any set typeclass parent.".format(prototype))
    return ret


@list_node(_all_prototypes, _prototype_select)
def node_prototype(caller):
    prototype = _get_menu_prototype(caller)

    prot_parent_key = prototype.get('prototype')

    text = ["Set the prototype's |yParent Prototype|n. If this is unset, Typeclass will be used."]
    if prot_parent_key:
        prot_parent = search_prototype(prot_parent_key)
        if prot_parent:
            text.append("Current parent prototype is {}:\n{}".format(prototype_to_str(prot_parent)))
        else:
            text.append("Current parent prototype |r{prototype}|n "
                        "does not appear to exist.".format(prot_parent_key))
    else:
        text.append("Parent prototype is not set")
    text = "\n\n".join(text)
    options = _wizard_options("prototype", "prototype_key", "typeclass", color="|W")
    options.append({"key": "_default",
                    "goto": _prototype_examine})

    return text, options


def _all_typeclasses(caller):
    return list(sorted(get_all_typeclasses().keys()))


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
    caller.msg(txt)
    return None


def _typeclass_select(caller, typeclass):
    ret = _set_property(caller, typeclass, prop='typeclass', processor=str, next_node="node_key")
    caller.msg("Selected typeclass |y{}|n. Removed any set prototype parent.".format(typeclass))
    return ret


@list_node(_all_typeclasses, _typeclass_select)
def node_typeclass(caller):
    prototype = _get_menu_prototype(caller)
    typeclass = prototype.get("typeclass")

    text = ["Set the typeclass's parent |yTypeclass|n."]
    if typeclass:
        text.append("Current typeclass is |y{typeclass}|n.".format(typeclass=typeclass))
    else:
        text.append("Using default typeclass {typeclass}.".format(
            typeclass=settings.BASE_OBJECT_TYPECLASS))
    text = "\n\n".join(text)
    options = _wizard_options("typeclass", "prototype", "key", color="|W")
    options.append({"key": "_default",
                    "goto": _typeclass_examine})
    return text, options


def node_key(caller):
    prototype = _get_menu_prototype(caller)
    key = prototype.get("key")

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
    prototype = _get_menu_prototype(caller)
    aliases = prototype.get("aliases")

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


def _caller_attrs(caller):
    prototype = _get_menu_prototype(caller)
    attrs = prototype.get("attrs", [])
    return attrs


def _attrparse(caller, attr_string):
    "attr is entering on the form 'attr = value'"

    if '=' in attr_string:
        attrname, value = (part.strip() for part in attr_string.split('=', 1))
        attrname = attrname.lower()
    if attrname:
        try:
            value = literal_eval(value)
        except SyntaxError:
            caller.msg(_MENU_ATTR_LITERAL_EVAL_ERROR)
        else:
            return attrname, value
    else:
        return None, None


def _add_attr(caller, attr_string, **kwargs):
    attrname, value = _attrparse(caller, attr_string)
    if attrname:
        prot = _get_menu_prototype(caller)
        prot['attrs'][attrname] = value
        _set_menu_prototype(caller, "prototype", prot)
        text = "Added"
    else:
        text = "Attribute must be given as 'attrname = <value>' where <value> uses valid Python."
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_attr(caller, attrname, new_value, **kwargs):
    attrname, value = _attrparse("{}={}".format(caller, attrname, new_value))
    if attrname:
        prot = _get_menu_prototype(caller)
        prot['attrs'][attrname] = value
        text = "Edited Attribute {} = {}".format(attrname, value)
    else:
        text = "Attribute value must be valid Python."
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _examine_attr(caller, selection):
    prot = _get_menu_prototype(caller)
    value = prot['attrs'][selection]
    return "Attribute {} = {}".format(selection, value)


@list_node(_caller_attrs)
def node_attrs(caller):
    prot = _get_menu_prototype(caller)
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


def _caller_tags(caller):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get("tags")
    return tags


def _add_tag(caller, tag, **kwargs):
    tag = tag.strip().lower()
    prototype = _get_menu_prototype(caller)
    tags = prototype.get('tags', [])
    if tags:
        if tag not in tags:
            tags.append(tag)
    else:
        tags = [tag]
    prot['tags'] = tags
    _set_menu_prototype(caller, "prototype", prot)
    text = kwargs.get("text")
    if not text:
        text = "Added tag {}. (return to continue)".format(tag)
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


def _edit_tag(caller, old_tag, new_tag, **kwargs):
    prototype = _get_menu_prototype(caller)
    tags = prototype.get('tags', [])

    old_tag = old_tag.strip().lower()
    new_tag = new_tag.strip().lower()
    tags[tags.index(old_tag)] = new_tag
    prototype['tags'] = tags
    _set_menu_prototype(caller, 'prototype', prototype)

    text = kwargs.get('text')
    if not text:
        text = "Changed tag {} to {}.".format(old_tag, new_tag)
    options = {"key": "_default",
               "goto": lambda caller: None}
    return text, options


@list_node(_caller_tags)
def node_tags(caller):
    text = "Set the prototype's |yTags|n."
    options = _wizard_options("tags", "attrs", "locks")
    return text, options


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


def node_prototype_desc(caller):

    prototype = _get_menu_prototype(caller)
    text = ["The |wMeta-Description|n briefly describes the prototype for viewing in listings."]
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


def node_prototype_tags(caller):
    prototype = _get_menu_prototype(caller)
    text = ["|wMeta-Tags|n can be used to classify and find prototypes. Tags are case-insensitive. "
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


def node_prototype_locks(caller):
    prototype = _get_menu_prototype(caller)
    text = ["Set |wMeta-Locks|n on the prototype. There are two valid lock types: "
            "'edit' (who can edit the prototype) and 'use' (who can apply the prototype)\n"
            "(If you are unsure, leave as default.)"]
    locks = prototype.get('prototype_locks', '')
    if locks:
        text.append("Current lock is |w'{lockstring}'|n".format(lockstring=locks))
    else:
        text.append("Lock unset - if not changed the default lockstring will be set as\n"
                    "   |w'use:all(); edit:id({dbref}) or perm(Admin)'|n".format(dbref=caller.id))
    text = "\n\n".join(text)
    options = _wizard_options("prototype_locks", "prototype_tags", "index")
    options.append({"key": "_default",
                    "goto": (_set_property,
                             dict(prop="prototype_locks",
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
                "node_prototype_desc": node_prototype_desc,
                "node_prototype_tags": node_prototype_tags,
                "node_prototype_locks": node_prototype_locks,
                }
    OLCMenu(caller, menudata, startnode='node_index', session=session, olc_prototype=prototype)

