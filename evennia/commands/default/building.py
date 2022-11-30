"""
Building and world design commands
"""
import re

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Max, Min, Q

from evennia import InterruptCommand
from evennia.commands.cmdhandler import get_and_merge_cmdsets
from evennia.locks.lockhandler import LockException
from evennia.objects.models import ObjectDB
from evennia.prototypes import menus as olc_menus
from evennia.prototypes import prototypes as protlib
from evennia.prototypes import spawner
from evennia.scripts.models import ScriptDB
from evennia.utils import create, funcparser, logger, search, utils
from evennia.utils.ansi import raw as ansi_raw
from evennia.utils.dbserialize import deserialize
from evennia.utils.eveditor import EvEditor
from evennia.utils.evmore import EvMore
from evennia.utils.evtable import EvTable
from evennia.utils.utils import (
    class_from_module,
    crop,
    dbref,
    display_len,
    format_grid,
    get_all_typeclasses,
    inherits_from,
    interactive,
    list_to_string,
    variable_from_module,
)

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

_FUNCPARSER = None
_ATTRFUNCPARSER = None

_KEY_REGEX = re.compile(r"(?P<attr>.*?)(?P<key>(\[.*\]\ *)+)?$")

# limit symbol import for API
__all__ = (
    "ObjManipCommand",
    "CmdSetObjAlias",
    "CmdCopy",
    "CmdCpAttr",
    "CmdMvAttr",
    "CmdCreate",
    "CmdDesc",
    "CmdDestroy",
    "CmdDig",
    "CmdTunnel",
    "CmdLink",
    "CmdUnLink",
    "CmdSetHome",
    "CmdListCmdSets",
    "CmdName",
    "CmdOpen",
    "CmdSetAttribute",
    "CmdTypeclass",
    "CmdWipe",
    "CmdLock",
    "CmdExamine",
    "CmdFind",
    "CmdTeleport",
    "CmdScripts",
    "CmdObjects",
    "CmdTag",
    "CmdSpawn",
)

# used by set
from ast import literal_eval as _LITERAL_EVAL

LIST_APPEND_CHAR = "+"

# used by find
CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS
ROOM_TYPECLASS = settings.BASE_ROOM_TYPECLASS
EXIT_TYPECLASS = settings.BASE_EXIT_TYPECLASS
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

_PROTOTYPE_PARENTS = None


class ObjManipCommand(COMMAND_DEFAULT_CLASS):
    """
    This is a parent class for some of the defining objmanip commands
    since they tend to have some more variables to define new objects.

    Each object definition can have several components. First is
    always a name, followed by an optional alias list and finally an
    some optional data, such as a typeclass or a location. A comma ','
    separates different objects. Like this:

        name1;alias;alias;alias:option, name2;alias;alias ...

    Spaces between all components are stripped.

    A second situation is attribute manipulation. Such commands
    are simpler and offer combinations

        objname/attr/attr/attr, objname/attr, ...

    """

    # OBS - this is just a parent - it's not intended to actually be
    # included in a commandset on its own!

    def parse(self):
        """
        We need to expand the default parsing to get all
        the cases, see the module doc.
        """
        # get all the normal parsing done (switches etc)
        super().parse()

        obj_defs = ([], [])  # stores left- and right-hand side of '='
        obj_attrs = ([], [])  # "

        for iside, arglist in enumerate((self.lhslist, self.rhslist)):
            # lhslist/rhslist is already split by ',' at this point
            for objdef in arglist:
                aliases, option, attrs = [], None, []
                if ":" in objdef:
                    objdef, option = [part.strip() for part in objdef.rsplit(":", 1)]
                if ";" in objdef:
                    objdef, aliases = [part.strip() for part in objdef.split(";", 1)]
                    aliases = [alias.strip() for alias in aliases.split(";") if alias.strip()]
                if "/" in objdef:
                    objdef, attrs = [part.strip() for part in objdef.split("/", 1)]
                    _attrs = []

                    # Should an attribute key is specified, ie. we're working
                    # on a dict, what we want is to lowercase attribute name
                    # as usual but to preserve dict key case as one would
                    # expect:
                    #
                    # set box/MyAttr = {'FooBar': 1}
                    # Created attribute box/myattr [category:None] = {'FooBar': 1}
                    # set box/MyAttr['FooBar'] = 2
                    # Modified attribute box/myattr [category:None] = {'FooBar': 2}
                    for match in (
                        match
                        for part in map(str.strip, attrs.split("/"))
                        if part and (match := _KEY_REGEX.match(part.strip()))
                    ):
                        attr = match.group("attr").lower()
                        # reappend untouched key, if present
                        if match.group("key"):
                            attr += match.group("key")
                        _attrs.append(attr)
                    attrs = _attrs
                # store data
                obj_defs[iside].append({"name": objdef, "option": option, "aliases": aliases})
                obj_attrs[iside].append({"name": objdef, "attrs": attrs})

        # store for future access
        self.lhs_objs = obj_defs[0]
        self.rhs_objs = obj_defs[1]
        self.lhs_objattr = obj_attrs[0]
        self.rhs_objattr = obj_attrs[1]


class CmdSetObjAlias(COMMAND_DEFAULT_CLASS):
    """
    adding permanent aliases for object

    Usage:
      alias <obj> [= [alias[,alias,alias,...]]]
      alias <obj> =
      alias/category <obj> = [alias[,alias,...]:<category>

    Switches:
      category - requires ending input with :category, to store the
        given aliases with the given category.

    Assigns aliases to an object so it can be referenced by more
    than one name. Assign empty to remove all aliases from object. If
    assigning a category, all aliases given will be using this category.

    Observe that this is not the same thing as personal aliases
    created with the 'nick' command! Aliases set with alias are
    changing the object in question, making those aliases usable
    by everyone.
    """

    key = "@alias"
    aliases = "setobjalias"
    switch_options = ("category",)
    locks = "cmd:perm(setobjalias) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Set the aliases."""

        caller = self.caller

        if not self.lhs:
            string = "Usage: alias <obj> [= [alias[,alias ...]]]"
            self.caller.msg(string)
            return
        objname = self.lhs

        # Find the object to receive aliases
        obj = caller.search(objname)
        if not obj:
            return
        if self.rhs is None:
            # no =, so we just list aliases on object.
            aliases = obj.aliases.all(return_key_and_category=True)
            if aliases:
                caller.msg(
                    "Aliases for %s: %s"
                    % (
                        obj.get_display_name(caller),
                        ", ".join(
                            "'%s'%s"
                            % (alias, "" if category is None else "[category:'%s']" % category)
                            for (alias, category) in aliases
                        ),
                    )
                )
            else:
                caller.msg(f"No aliases exist for '{obj.get_display_name(caller)}'.")
            return

        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You don't have permission to do that.")
            return

        if not self.rhs:
            # we have given an empty =, so delete aliases
            old_aliases = obj.aliases.all()
            if old_aliases:
                caller.msg(
                    "Cleared aliases from %s: %s"
                    % (obj.get_display_name(caller), ", ".join(old_aliases))
                )
                obj.aliases.clear()
            else:
                caller.msg("No aliases to clear.")
            return

        category = None
        if "category" in self.switches:
            if ":" in self.rhs:
                rhs, category = self.rhs.rsplit(":", 1)
                category = category.strip()
            else:
                caller.msg(
                    "If specifying the /category switch, the category must be given "
                    "as :category at the end."
                )
        else:
            rhs = self.rhs

        # merge the old and new aliases (if any)
        old_aliases = obj.aliases.get(category=category, return_list=True)
        new_aliases = [alias.strip().lower() for alias in rhs.split(",") if alias.strip()]

        # make the aliases only appear once
        old_aliases.extend(new_aliases)
        aliases = list(set(old_aliases))

        # save back to object.
        obj.aliases.add(aliases, category=category)

        # we need to trigger this here, since this will force
        # (default) Exits to rebuild their Exit commands with the new
        # aliases
        obj.at_cmdset_get(force_init=True)

        # report all aliases on the object
        caller.msg(
            "Alias(es) for '%s' set to '%s'%s."
            % (
                obj.get_display_name(caller),
                str(obj.aliases),
                " (category: '%s')" % category if category else "",
            )
        )


class CmdCopy(ObjManipCommand):
    """
    copy an object and its properties

    Usage:
      copy <original obj> [= <new_name>][;alias;alias..]
      [:<new_location>] [,<new_name2> ...]

    Create one or more copies of an object. If you don't supply any targets,
    one exact copy of the original object will be created with the name *_copy.
    """

    key = "@copy"
    locks = "cmd:perm(copy) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Uses ObjManipCommand.parse()"""

        caller = self.caller
        args = self.args
        if not args:
            caller.msg(
                "Usage: copy <obj> [=<new_name>[;alias;alias..]]"
                "[:<new_location>] [, <new_name2>...]"
            )
            return

        if not self.rhs:
            # this has no target =, so an identical new object is created.
            from_obj_name = self.args
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return
            to_obj_name = "%s_copy" % from_obj_name
            to_obj_aliases = ["%s_copy" % alias for alias in from_obj.aliases.all()]
            copiedobj = ObjectDB.objects.copy_object(
                from_obj, new_key=to_obj_name, new_aliases=to_obj_aliases
            )
            if copiedobj:
                string = "Identical copy of %s, named '%s' was created." % (
                    from_obj_name,
                    to_obj_name,
                )
            else:
                string = "There was an error copying %s."
        else:
            # we have specified =. This might mean many object targets
            from_obj_name = self.lhs_objs[0]["name"]
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return
            for objdef in self.rhs_objs:
                # loop through all possible copy-to targets
                to_obj_name = objdef["name"]
                to_obj_aliases = objdef["aliases"]
                to_obj_location = objdef["option"]
                if to_obj_location:
                    to_obj_location = caller.search(to_obj_location, global_search=True)
                    if not to_obj_location:
                        return

                copiedobj = ObjectDB.objects.copy_object(
                    from_obj,
                    new_key=to_obj_name,
                    new_location=to_obj_location,
                    new_aliases=to_obj_aliases,
                )
                if copiedobj:
                    string = (
                        f"Copied {from_obj_name} to '{to_obj_name}' (aliases: {to_obj_aliases})."
                    )
                else:
                    string = f"There was an error copying {from_obj_name} to '{to_obj_name}'."
        # we are done, echo to user
        caller.msg(string)


class CmdCpAttr(ObjManipCommand):
    """
    copy attributes between objects

    Usage:
      cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      move - delete the attribute from the source object after copying.

    Example:
      cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
      ->
      copies the coolness attribute (defined on yourself), to attributes
      on Anna and Tom.

    Copy the attribute one object to one or more attributes on another object.
    If you don't supply a source object, yourself is used.
    """

    key = "@cpattr"
    switch_options = ("move",)
    locks = "cmd:perm(cpattr) or perm(Builder)"
    help_category = "Building"

    def check_from_attr(self, obj, attr, clear=False):
        """
        Hook for overriding on subclassed commands. Checks to make sure a
        caller can copy the attr from the object in question. If not, return a
        false value and the command will abort. An error message should be
        provided by this function.

        If clear is True, user is attempting to move the attribute.
        """
        return True

    def check_to_attr(self, obj, attr):
        """
        Hook for overriding on subclassed commands. Checks to make sure a
        caller can write to the specified attribute on the specified object.
        If not, return a false value and the attribute will be skipped. An
        error message should be provided by this function.
        """
        return True

    def check_has_attr(self, obj, attr):
        """
        Hook for overriding on subclassed commands. Do any preprocessing
        required and verify an object has an attribute.
        """
        if not obj.attributes.has(attr):
            self.caller.msg(f"{obj.name} doesn't have an attribute {attr}.")
            return False
        return True

    def get_attr(self, obj, attr):
        """
        Hook for overriding on subclassed commands. Do any preprocessing
        required and get the attribute from the object.
        """
        return obj.attributes.get(attr)

    def func(self):
        """
        Do the copying.
        """
        caller = self.caller

        if not self.rhs:
            string = """Usage:
            cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
            cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]"""
            caller.msg(string)
            return

        lhs_objattr = self.lhs_objattr
        to_objs = self.rhs_objattr
        from_obj_name = lhs_objattr[0]["name"]
        from_obj_attrs = lhs_objattr[0]["attrs"]

        if not from_obj_attrs:
            # this means the from_obj_name is actually an attribute
            # name on self.
            from_obj_attrs = [from_obj_name]
            from_obj = self.caller
        else:
            from_obj = caller.search(from_obj_name)
        if not from_obj or not to_objs:
            caller.msg("You have to supply both source object and target(s).")
            return
        # copy to all to_obj:ects
        if "move" in self.switches:
            clear = True
        else:
            clear = False
        if not self.check_from_attr(from_obj, from_obj_attrs[0], clear=clear):
            return

        for attr in from_obj_attrs:
            if not self.check_has_attr(from_obj, attr):
                return

        if (len(from_obj_attrs) != len(set(from_obj_attrs))) and clear:
            self.caller.msg("|RCannot have duplicate source names when moving!")
            return

        result = []

        for to_obj in to_objs:
            to_obj_name = to_obj["name"]
            to_obj_attrs = to_obj["attrs"]
            to_obj = caller.search(to_obj_name)
            if not to_obj:
                result.append(f"\nCould not find object '{to_obj_name}'")
                continue
            for inum, from_attr in enumerate(from_obj_attrs):
                try:
                    to_attr = to_obj_attrs[inum]
                except IndexError:
                    # if there are too few attributes given
                    # on the to_obj, we copy the original name instead.
                    to_attr = from_attr
                if not self.check_to_attr(to_obj, to_attr):
                    continue
                value = self.get_attr(from_obj, from_attr)
                to_obj.attributes.add(to_attr, value)
                if clear and not (from_obj == to_obj and from_attr == to_attr):
                    from_obj.attributes.remove(from_attr)
                    result.append(
                        f"\nMoved {from_obj.name}.{from_attr} -> {to_obj_name}.{to_attr}. (value:"
                        f" {repr(value)})"
                    )
                else:
                    result.append(
                        f"\nCopied {from_obj.name}.{from_attr} -> {to_obj.name}.{to_attr}. (value:"
                        f" {repr(value)})"
                    )
        caller.msg("".join(result))


class CmdMvAttr(ObjManipCommand):
    """
    move attributes between objects

    Usage:
      mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      copy - Don't delete the original after moving.

    Move an attribute from one object to one or more attributes on another
    object. If you don't supply a source object, yourself is used.
    """

    key = "@mvattr"
    switch_options = ("copy",)
    locks = "cmd:perm(mvattr) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """
        Do the moving
        """
        if not self.rhs:
            string = """Usage:
      mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]"""
            self.caller.msg(string)
            return

        # simply use cpattr for all the functionality
        if "copy" in self.switches:
            self.execute_cmd("cpattr %s" % self.args)
        else:
            self.execute_cmd("cpattr/move %s" % self.args)


class CmdCreate(ObjManipCommand):
    """
    create new objects

    Usage:
      create[/drop] <objname>[;alias;alias...][:typeclass], <objname>...

    switch:
       drop - automatically drop the new object into your current
              location (this is not echoed). This also sets the new
              object's home to the current location rather than to you.

    Creates one or more new objects. If typeclass is given, the object
    is created as a child of this typeclass. The typeclass script is
    assumed to be located under types/ and any further
    directory structure is given in Python notation. So if you have a
    correct typeclass 'RedButton' defined in
    types/examples/red_button.py, you could create a new
    object of this type like this:

       create/drop button;red : examples.red_button.RedButton

    """

    key = "@create"
    switch_options = ("drop",)
    locks = "cmd:perm(create) or perm(Builder)"
    help_category = "Building"

    # lockstring of newly created objects, for easy overloading.
    # Will be formatted with the {id} of the creating object.
    new_obj_lockstring = "control:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"

    def func(self):
        """
        Creates the object.
        """

        caller = self.caller

        if not self.args:
            string = "Usage: create[/drop] <newname>[;alias;alias...] [:typeclass.path]"
            caller.msg(string)
            return

        # create the objects
        for objdef in self.lhs_objs:
            string = ""
            name = objdef["name"]
            aliases = objdef["aliases"]
            typeclass = objdef["option"]

            # create object (if not a valid typeclass, the default
            # object typeclass will automatically be used)
            lockstring = self.new_obj_lockstring.format(id=caller.id)
            obj = create.create_object(
                typeclass,
                name,
                caller,
                home=caller,
                aliases=aliases,
                locks=lockstring,
                report_to=caller,
            )
            if not obj:
                continue
            if aliases:
                string = (
                    f"You create a new {obj.typename}: {obj.name} (aliases: {', '.join(aliases)})."
                )
            else:
                string = f"You create a new {obj.typename}: {obj.name}."
            # set a default desc
            if not obj.db.desc:
                obj.db.desc = "You see nothing special."
            if "drop" in self.switches:
                if caller.location:
                    obj.home = caller.location
                    obj.move_to(caller.location, quiet=True, move_type="drop")
        if string:
            caller.msg(string)


def _desc_load(caller):
    return caller.db.evmenu_target.db.desc or ""


def _desc_save(caller, buf):
    """
    Save line buffer to the desc prop. This should
    return True if successful and also report its status to the user.
    """
    caller.db.evmenu_target.db.desc = buf
    caller.msg("Saved.")
    return True


def _desc_quit(caller):
    caller.attributes.remove("evmenu_target")
    caller.msg("Exited editor.")


class CmdDesc(COMMAND_DEFAULT_CLASS):
    """
    describe an object or the current room.

    Usage:
      desc [<obj> =] <description>

    Switches:
      edit - Open up a line editor for more advanced editing.

    Sets the "desc" attribute on an object. If an object is not given,
    describe the current room.
    """

    key = "@desc"
    switch_options = ("edit",)
    locks = "cmd:perm(desc) or perm(Builder)"
    help_category = "Building"

    def edit_handler(self):
        if self.rhs:
            self.msg("|rYou may specify a value, or use the edit switch, but not both.|n")
            return
        if self.args:
            obj = self.caller.search(self.args)
        else:
            obj = self.caller.location or self.msg("|rYou can't describe oblivion.|n")
        if not obj:
            return

        if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
            self.caller.msg(f"You don't have permission to edit the description of {obj.key}.")
            return

        self.caller.db.evmenu_target = obj
        # launch the editor
        EvEditor(
            self.caller,
            loadfunc=_desc_load,
            savefunc=_desc_save,
            quitfunc=_desc_quit,
            key="desc",
            persistent=True,
        )
        return

    def func(self):
        """Define command"""

        caller = self.caller
        if not self.args and "edit" not in self.switches:
            caller.msg("Usage: desc [<obj> =] <description>")
            return

        if "edit" in self.switches:
            self.edit_handler()
            return

        if "=" in self.args:
            # We have an =
            obj = caller.search(self.lhs)
            if not obj:
                return
            desc = self.rhs or ""
        else:
            obj = caller.location or self.msg("|rYou don't have a location to describe.|n")
            if not obj:
                return
            desc = self.args
        if obj.access(self.caller, "control") or obj.access(self.caller, "edit"):
            obj.db.desc = desc
            caller.msg(f"The description was set on {obj.get_display_name(caller)}.")
        else:
            caller.msg(f"You don't have permission to edit the description of {obj.key}.")


class CmdDestroy(COMMAND_DEFAULT_CLASS):
    """
    permanently delete objects

    Usage:
       destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]

    Switches:
       override - The destroy command will usually avoid accidentally
                  destroying account objects. This switch overrides this safety.
       force - destroy without confirmation.
    Examples:
       destroy house, roof, door, 44-78
       destroy 5-10, flower, 45
       destroy/force north

    Destroys one or many objects. If dbrefs are used, a range to delete can be
    given, e.g. 4-10. Also the end points will be deleted. This command
    displays a confirmation before destroying, to make sure of your choice.
    You can specify the /force switch to bypass this confirmation.
    """

    key = "@destroy"
    aliases = ["@delete", "@del"]
    switch_options = ("override", "force")
    locks = "cmd:perm(destroy) or perm(Builder)"
    help_category = "Building"

    confirm = True  # set to False to always bypass confirmation
    default_confirm = "yes"  # what to assume if just pressing enter (yes/no)

    def func(self):
        """Implements the command."""

        caller = self.caller
        delete = True

        if not self.args or not self.lhslist:
            caller.msg("Usage: destroy[/switches] [obj, obj2, obj3, [dbref-dbref],...]")
            delete = False

        def delobj(obj):
            # helper function for deleting a single object
            string = ""
            if not obj.pk:
                string = f"\nObject {obj.db_key} was already deleted."
            else:
                objname = obj.name
                if not (obj.access(caller, "control") or obj.access(caller, "delete")):
                    return f"\nYou don't have permission to delete {objname}."
                if obj.account and "override" not in self.switches:
                    return (
                        f"\nObject {objname} is controlled by an active account. Use /override to"
                        " delete anyway."
                    )
                if obj.dbid == int(settings.DEFAULT_HOME.lstrip("#")):
                    return (
                        f"\nYou are trying to delete |c{objname}|n, which is set as DEFAULT_HOME. "
                        "Re-point settings.DEFAULT_HOME to another "
                        "object before continuing."
                    )

                # check if object to delete had exits or objects inside it
                obj_exits = obj.exits if hasattr(obj, "exits") else ()
                obj_contents = obj.contents if hasattr(obj, "contents") else ()
                had_exits = bool(obj_exits)
                had_objs = any(entity for entity in obj_contents if entity not in obj_exits)

                # do the deletion
                okay = obj.delete()
                if not okay:
                    string += (
                        f"\nERROR: {objname} not deleted, probably because delete() returned False."
                    )
                else:
                    string += f"\n{objname} was destroyed."
                    if had_exits:
                        string += f" Exits to and from {objname} were destroyed as well."
                    if had_objs:
                        string += f" Objects inside {objname} were moved to their homes."
            return string

        objs = []
        for objname in self.lhslist:
            if not delete:
                continue

            if "-" in objname:
                # might be a range of dbrefs
                dmin, dmax = [utils.dbref(part, reqhash=False) for part in objname.split("-", 1)]
                if dmin and dmax:
                    for dbref in range(int(dmin), int(dmax + 1)):
                        obj = caller.search("#" + str(dbref))
                        if obj:
                            objs.append(obj)
                    continue
                else:
                    obj = caller.search(objname)
            else:
                obj = caller.search(objname)

            if obj is None:
                self.caller.msg(
                    " (Objects to destroy must either be local or specified with a unique #dbref.)"
                )
            elif obj not in objs:
                objs.append(obj)

        if objs and ("force" not in self.switches and type(self).confirm):
            confirm = "Are you sure you want to destroy "
            if len(objs) == 1:
                confirm += objs[0].get_display_name(caller)
            elif len(objs) < 5:
                confirm += ", ".join([obj.get_display_name(caller) for obj in objs])
            else:
                confirm += ", ".join(["#{}".format(obj.id) for obj in objs])
            confirm += " [yes]/no?" if self.default_confirm == "yes" else " yes/[no]"
            answer = ""
            answer = yield (confirm)
            answer = self.default_confirm if answer == "" else answer

            if answer and answer not in ("yes", "y", "no", "n"):
                caller.msg(
                    "Canceled: Either accept the default by pressing return or specify yes/no."
                )
                delete = False
            elif answer.strip().lower() in ("n", "no"):
                caller.msg("Canceled: No object was destroyed.")
                delete = False

        if delete:
            results = []
            for obj in objs:
                results.append(delobj(obj))

            if results:
                caller.msg("".join(results).strip())


class CmdDig(ObjManipCommand):
    """
    build new rooms and connect them to the current location

    Usage:
      dig[/switches] <roomname>[;alias;alias...][:typeclass]
            [= <exit_to_there>[;alias][:typeclass]]
               [, <exit_to_here>[;alias][:typeclass]]

    Switches:
       tel or teleport - move yourself to the new room

    Examples:
       dig kitchen = north;n, south;s
       dig house:myrooms.MyHouseTypeclass
       dig sheer cliff;cliff;sheer = climb up, climb down

    This command is a convenient way to build rooms quickly; it creates the
    new room and you can optionally set up exits back and forth between your
    current room and the new one. You can add as many aliases as you
    like to the name of the room and the exits in question; an example
    would be 'north;no;n'.
    """

    key = "@dig"
    switch_options = ("teleport",)
    locks = "cmd:perm(dig) or perm(Builder)"
    help_category = "Building"

    # lockstring of newly created rooms, for easy overloading.
    # Will be formatted with the {id} of the creating object.
    new_room_lockstring = (
        "control:id({id}) or perm(Admin); "
        "delete:id({id}) or perm(Admin); "
        "edit:id({id}) or perm(Admin)"
    )

    def func(self):
        """Do the digging. Inherits variables from ObjManipCommand.parse()"""

        caller = self.caller

        if not self.lhs:
            string = "Usage: dig[/teleport] <roomname>[;alias;alias...][:parent] [= <exit_there>"
            string += "[;alias;alias..][:parent]] "
            string += "[, <exit_back_here>[;alias;alias..][:parent]]"
            caller.msg(string)
            return

        room = self.lhs_objs[0]

        if not room["name"]:
            caller.msg("You must supply a new room name.")
            return
        location = caller.location

        # Create the new room
        typeclass = room["option"]
        if not typeclass:
            typeclass = settings.BASE_ROOM_TYPECLASS

        # create room
        new_room = create.create_object(
            typeclass, room["name"], aliases=room["aliases"], report_to=caller
        )
        lockstring = self.new_room_lockstring.format(id=caller.id)
        new_room.locks.add(lockstring)
        alias_string = ""
        if new_room.aliases.all():
            alias_string = " (%s)" % ", ".join(new_room.aliases.all())
        room_string = (
            f"Created room {new_room}({new_room.dbref}){alias_string} of type {typeclass}."
        )

        # create exit to room

        exit_to_string = ""
        exit_back_string = ""

        if self.rhs_objs:
            to_exit = self.rhs_objs[0]
            if not to_exit["name"]:
                exit_to_string = "\nNo exit created to new room."
            elif not location:
                exit_to_string = "\nYou cannot create an exit from a None-location."
            else:
                # Build the exit to the new room from the current one
                typeclass = to_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS

                new_to_exit = create.create_object(
                    typeclass,
                    to_exit["name"],
                    location,
                    aliases=to_exit["aliases"],
                    locks=lockstring,
                    destination=new_room,
                    report_to=caller,
                )
                alias_string = ""
                if new_to_exit.aliases.all():
                    alias_string = " (%s)" % ", ".join(new_to_exit.aliases.all())
                exit_to_string = (
                    f"\nCreated Exit from {location.name} to {new_room.name}:"
                    f" {new_to_exit}({new_to_exit.dbref}){alias_string}."
                )

        # Create exit back from new room

        if len(self.rhs_objs) > 1:
            # Building the exit back to the current room
            back_exit = self.rhs_objs[1]
            if not back_exit["name"]:
                exit_back_string = "\nNo back exit created."
            elif not location:
                exit_back_string = "\nYou cannot create an exit back to a None-location."
            else:
                typeclass = back_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS
                new_back_exit = create.create_object(
                    typeclass,
                    back_exit["name"],
                    new_room,
                    aliases=back_exit["aliases"],
                    locks=lockstring,
                    destination=location,
                    report_to=caller,
                )
                alias_string = ""
                if new_back_exit.aliases.all():
                    alias_string = " (%s)" % ", ".join(new_back_exit.aliases.all())
                exit_back_string = (
                    f"\nCreated Exit back from {new_room.name} to {location.name}:"
                    f" {new_back_exit}({new_back_exit.dbref}){alias_string}."
                )
        caller.msg(f"{room_string}{exit_to_string}{exit_back_string}")
        if new_room and "teleport" in self.switches:
            caller.move_to(new_room, move_type="teleport")


class CmdTunnel(COMMAND_DEFAULT_CLASS):
    """
    create new rooms in cardinal directions only

    Usage:
      tunnel[/switch] <direction>[:typeclass] [= <roomname>[;alias;alias;...][:typeclass]]

    Switches:
      oneway - do not create an exit back to the current location
      tel - teleport to the newly created room

    Example:
      tunnel n
      tunnel n = house;mike's place;green building

    This is a simple way to build using pre-defined directions:
     |wn,ne,e,se,s,sw,w,nw|n (north, northeast etc)
     |wu,d|n (up and down)
     |wi,o|n (in and out)
    The full names (north, in, southwest, etc) will always be put as
    main name for the exit, using the abbreviation as an alias (so an
    exit will always be able to be used with both "north" as well as
    "n" for example). Opposite directions will automatically be
    created back from the new room unless the /oneway switch is given.
    For more flexibility and power in creating rooms, use dig.
    """

    key = "@tunnel"
    aliases = ["@tun"]
    switch_options = ("oneway", "tel")
    locks = "cmd: perm(tunnel) or perm(Builder)"
    help_category = "Building"

    # store the direction, full name and its opposite
    directions = {
        "n": ("north", "s"),
        "ne": ("northeast", "sw"),
        "e": ("east", "w"),
        "se": ("southeast", "nw"),
        "s": ("south", "n"),
        "sw": ("southwest", "ne"),
        "w": ("west", "e"),
        "nw": ("northwest", "se"),
        "u": ("up", "d"),
        "d": ("down", "u"),
        "i": ("in", "o"),
        "o": ("out", "i"),
    }

    def func(self):
        """Implements the tunnel command"""

        if not self.args or not self.lhs:
            string = (
                "Usage: tunnel[/switch] <direction>[:typeclass] [= <roomname>"
                "[;alias;alias;...][:typeclass]]"
            )
            self.caller.msg(string)
            return

        # If we get a typeclass, we need to get just the exitname
        exitshort = self.lhs.split(":")[0]

        if exitshort not in self.directions:
            string = "tunnel can only understand the following directions: %s." % ",".join(
                sorted(self.directions.keys())
            )
            string += "\n(use dig for more freedom)"
            self.caller.msg(string)
            return

        # retrieve all input and parse it
        exitname, backshort = self.directions[exitshort]
        backname = self.directions[backshort][0]

        # if we received a typeclass for the exit, add it to the alias(short name)
        if ":" in self.lhs:
            # limit to only the first : character
            exit_typeclass = ":" + self.lhs.split(":", 1)[-1]
            # exitshort and backshort are the last part of the exit strings,
            # so we add our typeclass argument after
            exitshort += exit_typeclass
            backshort += exit_typeclass

        roomname = "Some place"
        if self.rhs:
            roomname = self.rhs  # this may include aliases; that's fine.

        telswitch = ""
        if "tel" in self.switches:
            telswitch = "/teleport"
        backstring = ""
        if "oneway" not in self.switches:
            backstring = f", {backname};{backshort}"

        # build the string we will use to call dig
        digstring = f"dig{telswitch} {roomname} = {exitname};{exitshort}{backstring}"
        self.execute_cmd(digstring)


class CmdLink(COMMAND_DEFAULT_CLASS):
    """
    link existing rooms together with exits

    Usage:
      link[/switches] <object> = <target>
      link[/switches] <object> =
      link[/switches] <object>

    Switch:
      twoway - connect two exits. For this to work, BOTH <object>
               and <target> must be exit objects.

    If <object> is an exit, set its destination to <target>. Two-way operation
    instead sets the destination to the *locations* of the respective given
    arguments.
    The second form (a lone =) sets the destination to None (same as
    the unlink command) and the third form (without =) just shows the
    currently set destination.
    """

    key = "@link"
    locks = "cmd:perm(link) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Perform the link"""
        caller = self.caller

        if not self.args:
            caller.msg("Usage: link[/twoway] <object> = <target>")
            return

        object_name = self.lhs

        # try to search locally first
        results = caller.search(object_name, quiet=True)
        if len(results) > 1:  # local results was a multimatch. Inform them to be more specific
            _AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
            return _AT_SEARCH_RESULT(results, caller, query=object_name)
        elif len(results) == 1:  # A unique local match
            obj = results[0]
        else:  # No matches. Search globally
            obj = caller.search(object_name, global_search=True)
            if not obj:
                return

        if self.rhs:
            # this means a target name was given
            target = caller.search(self.rhs, global_search=True)
            if not target:
                return

            if target == obj:
                self.caller.msg("Cannot link an object to itself.")
                return

            string = ""
            note = (
                "Note: %s(%s) did not have a destination set before. Make sure you linked the right"
                " thing."
            )
            if not obj.destination:
                string = note % (obj.name, obj.dbref)
            if "twoway" in self.switches:
                if not (target.location and obj.location):
                    string = (
                        f"To create a two-way link, {obj} and {target} must both have a location"
                    )
                    string += " (i.e. they cannot be rooms, but should be exits)."
                    self.caller.msg(string)
                    return
                if not target.destination:
                    string += note % (target.name, target.dbref)
                obj.destination = target.location
                target.destination = obj.location
                string += (
                    f"\nLink created {obj.name} (in {obj.location}) <-> {target.name} (in"
                    f" {target.location}) (two-way)."
                )
            else:
                obj.destination = target
                string += f"\nLink created {obj.name} -> {target} (one way)."

        elif self.rhs is None:
            # this means that no = was given (otherwise rhs
            # would have been an empty string). So we inspect
            # the home/destination on object
            dest = obj.destination
            if dest:
                string = f"{obj.name} is an exit to {dest.name}."
            else:
                string = f"{obj.name} is not an exit. Its home location is {obj.home}."

        else:
            # We gave the command link 'obj = ' which means we want to
            # clear destination.
            if obj.destination:
                obj.destination = None
                string = f"Former exit {obj.name} no longer links anywhere."
            else:
                string = f"{obj.name} had no destination to unlink."
        # give feedback
        caller.msg(string.strip())


class CmdUnLink(CmdLink):
    """
    remove exit-connections between rooms

    Usage:
      unlink <Object>

    Unlinks an object, for example an exit, disconnecting
    it from whatever it was connected to.
    """

    # this is just a child of CmdLink

    key = "unlink"
    locks = "cmd:perm(unlink) or perm(Builder)"
    help_key = "Building"

    def func(self):
        """
        All we need to do here is to set the right command
        and call func in CmdLink
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: unlink <object>")
            return

        # This mimics 'link <obj> = ' which is the same as unlink
        self.rhs = ""

        # call the link functionality
        super().func()


class CmdSetHome(CmdLink):
    """
    set an object's home location

    Usage:
      sethome <obj> [= <home_location>]
      sethom <obj>

    The "home" location is a "safety" location for objects; they
    will be moved there if their current location ceases to exist. All
    objects should always have a home location for this reason.
    It is also a convenient target of the "home" command.

    If no location is given, just view the object's home location.
    """

    key = "@sethome"
    locks = "cmd:perm(sethome) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """implement the command"""
        if not self.args:
            string = "Usage: sethome <obj> [= <home_location>]"
            self.caller.msg(string)
            return

        obj = self.caller.search(self.lhs, global_search=True)
        if not obj:
            return
        if not self.rhs:
            # just view
            home = obj.home
            if not home:
                string = "This object has no home location set!"
            else:
                string = f"{obj}'s current home is {home}({home.dbref})."
        else:
            # set a home location
            new_home = self.caller.search(self.rhs, global_search=True)
            if not new_home:
                return
            old_home = obj.home
            obj.home = new_home
            if old_home:
                string = (
                    f"Home location of {obj} was changed from {old_home}({old_home.dbref} to"
                    f" {new_home}({new_home.dbref})."
                )
            else:
                string = f"Home location of {obj} was set to {new_home}({new_home.dbref})."
        self.caller.msg(string)


class CmdListCmdSets(COMMAND_DEFAULT_CLASS):
    """
    list command sets defined on an object

    Usage:
      cmdsets <obj>

    This displays all cmdsets assigned
    to a user. Defaults to yourself.
    """

    key = "@cmdsets"
    locks = "cmd:perm(listcmdsets) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """list the cmdsets"""

        caller = self.caller
        if self.arglist:
            obj = caller.search(self.arglist[0])
            if not obj:
                return
        else:
            obj = caller
        string = f"{obj.cmdset}"
        caller.msg(string)


class CmdName(ObjManipCommand):
    """
    change the name and/or aliases of an object

    Usage:
      name <obj> = <newname>;alias1;alias2

    Rename an object to something new. Use *obj to
    rename an account.

    """

    key = "@name"
    aliases = ["@rename"]
    locks = "cmd:perm(rename) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """change the name"""

        caller = self.caller
        if not self.args:
            caller.msg("Usage: name <obj> = <newname>[;alias;alias;...]")
            return

        obj = None
        if self.lhs_objs:
            objname = self.lhs_objs[0]["name"]
            if objname.startswith("*"):
                # account mode
                obj = caller.account.search(objname.lstrip("*"))
                if obj:
                    if self.rhs_objs[0]["aliases"]:
                        caller.msg("Accounts can't have aliases.")
                        return
                    newname = self.rhs
                    if not newname:
                        caller.msg("No name defined!")
                        return
                    if not (obj.access(caller, "control") or obj.access(caller, "edit")):
                        caller.msg(f"You don't have right to edit this account {obj}.")
                        return
                    obj.username = newname
                    obj.save()
                    caller.msg(f"Account's name changed to '{newname}'.")
                    return
            # object search, also with *
            obj = caller.search(objname)
            if not obj:
                return
        if self.rhs_objs:
            newname = self.rhs_objs[0]["name"]
            aliases = self.rhs_objs[0]["aliases"]
        else:
            newname = self.rhs
            aliases = None
        if not newname and not aliases:
            caller.msg("No names or aliases defined!")
            return
        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg(f"You don't have the right to edit {obj}.")
            return
        # change the name and set aliases:
        if newname:
            obj.key = newname
        astring = ""
        if aliases:
            [obj.aliases.add(alias) for alias in aliases]
            astring = " (%s)" % ", ".join(aliases)
        # fix for exits - we need their exit-command to change name too
        if obj.destination:
            obj.flush_from_cache(force=True)
        caller.msg(f"Object's name changed to '{newname}'{astring}.")


class CmdOpen(ObjManipCommand):
    """
    open a new exit from the current room

    Usage:
      open <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>

    Handles the creation of exits. If a destination is given, the exit
    will point there. The <return exit> argument sets up an exit at the
    destination leading back to the current room. Destination name
    can be given both as a #dbref and a name, if that name is globally
    unique.

    """

    key = "@open"
    locks = "cmd:perm(open) or perm(Builder)"
    help_category = "Building"

    new_obj_lockstring = "control:id({id}) or perm(Admin);delete:id({id}) or perm(Admin)"
    # a custom member method to chug out exits and do checks
    def create_exit(self, exit_name, location, destination, exit_aliases=None, typeclass=None):
        """
        Helper function to avoid code duplication.
        At this point we know destination is a valid location

        """
        caller = self.caller
        string = ""
        # check if this exit object already exists at the location.
        # we need to ignore errors (so no automatic feedback)since we
        # have to know the result of the search to decide what to do.
        exit_obj = caller.search(exit_name, location=location, quiet=True, exact=True)
        if len(exit_obj) > 1:
            # give error message and return
            caller.search(exit_name, location=location, exact=True)
            return None
        if exit_obj:
            exit_obj = exit_obj[0]
            if not exit_obj.destination:
                # we are trying to link a non-exit
                caller.msg(
                    f"'{exit_name}' already exists and is not an exit!\nIf you want to convert it "
                    "to an exit, you must assign an object to the 'destination' property first."
                )
                return None
            # we are re-linking an old exit.
            old_destination = exit_obj.destination
            if old_destination:
                string = f"Exit {exit_name} already exists."
                if old_destination.id != destination.id:
                    # reroute the old exit.
                    exit_obj.destination = destination
                    if exit_aliases:
                        [exit_obj.aliases.add(alias) for alias in exit_aliases]
                    string += (
                        f" Rerouted its old destination '{old_destination.name}' to"
                        f" '{destination.name}' and changed aliases."
                    )
                else:
                    string += " It already points to the correct place."

        else:
            # exit does not exist before. Create a new one.
            lockstring = self.new_obj_lockstring.format(id=caller.id)
            if not typeclass:
                typeclass = settings.BASE_EXIT_TYPECLASS
            exit_obj = create.create_object(
                typeclass,
                key=exit_name,
                location=location,
                aliases=exit_aliases,
                locks=lockstring,
                report_to=caller,
            )
            if exit_obj:
                # storing a destination is what makes it an exit!
                exit_obj.destination = destination
                string = (
                    ""
                    if not exit_aliases
                    else " (aliases: %s)" % ", ".join([str(e) for e in exit_aliases])
                )
                string = (
                    f"Created new Exit '{exit_name}' from {location.name} to"
                    f" {destination.name}{string}."
                )
            else:
                string = f"Error: Exit '{exit.name}' not created."
        # emit results
        caller.msg(string)
        return exit_obj

    def parse(self):
        super().parse()
        self.location = self.caller.location
        if not self.args or not self.rhs:
            self.caller.msg(
                "Usage: open <new exit>[;alias...][:typeclass]"
                "[,<return exit>[;alias..][:typeclass]]] "
                "= <destination>"
            )
            raise InterruptCommand
        if not self.location:
            self.caller.msg("You cannot create an exit from a None-location.")
            raise InterruptCommand
        self.destination = self.caller.search(self.rhs, global_search=True)
        if not self.destination:
            raise InterruptCommand
        self.exit_name = self.lhs_objs[0]["name"]
        self.exit_aliases = self.lhs_objs[0]["aliases"]
        self.exit_typeclass = self.lhs_objs[0]["option"]

    def func(self):
        """
        This is where the processing starts.
        Uses the ObjManipCommand.parser() for pre-processing
        as well as the self.create_exit() method.
        """
        # Create exit
        ok = self.create_exit(
            self.exit_name, self.location, self.destination, self.exit_aliases, self.exit_typeclass
        )
        if not ok:
            # an error; the exit was not created, so we quit.
            return
        # Create back exit, if any
        if len(self.lhs_objs) > 1:
            back_exit_name = self.lhs_objs[1]["name"]
            back_exit_aliases = self.lhs_objs[1]["aliases"]
            back_exit_typeclass = self.lhs_objs[1]["option"]
            self.create_exit(
                back_exit_name,
                self.destination,
                self.location,
                back_exit_aliases,
                back_exit_typeclass,
            )


def _convert_from_string(cmd, strobj):
    """
    Converts a single object in *string form* to its equivalent python
    type.

     Python earlier than 2.6:
    Handles floats, ints, and limited nested lists and dicts
    (can't handle lists in a dict, for example, this is mainly due to
    the complexity of parsing this rather than any technical difficulty -
    if there is a need for set-ing such complex structures on the
    command line we might consider adding it).
     Python 2.6 and later:
    Supports all Python structures through literal_eval as long as they
    are valid Python syntax. If they are not (such as [test, test2], ie
    without the quotes around the strings), the entire structure will
    be converted to a string and a warning will be given.

    We need to convert like this since all data being sent over the
    telnet connection by the Account is text - but we will want to
    store it as the "real" python type so we can do convenient
    comparisons later (e.g.  obj.db.value = 2, if value is stored as a
    string this will always fail).
    """

    # Use literal_eval to parse python structure exactly.
    try:
        return _LITERAL_EVAL(strobj)
    except (SyntaxError, ValueError):
        # treat as string
        strobj = utils.to_str(strobj)
        string = (
            f'|RNote: name "|r{strobj}|R" was converted to a string. Make sure this is acceptable.'
        )
        cmd.caller.msg(string)
        return strobj
    except Exception as err:
        string = f"|RUnknown error in evaluating Attribute: {err}"
        return string


class CmdSetAttribute(ObjManipCommand):
    """
    set attribute on an object or account

    Usage:
      set[/switch] <obj>/<attr>[:category] = <value>
      set[/switch] <obj>/<attr>[:category] =                  # delete attribute
      set[/switch] <obj>/<attr>[:category]                    # view attribute
      set[/switch] *<account>/<attr>[:category] = <value>

    Switch:
        edit: Open the line editor (string values only)
        script: If we're trying to set an attribute on a script
        channel: If we're trying to set an attribute on a channel
        account: If we're trying to set an attribute on an account
        room: Setting an attribute on a room (global search)
        exit: Setting an attribute on an exit (global search)
        char: Setting an attribute on a character (global search)
        character: Alias for char, as above.

    Example:
        set self/foo = "bar"
        set/delete self/foo
        set self/foo = $dbref(#53)

    Sets attributes on objects. The second example form above clears a
    previously set attribute while the third form inspects the current value of
    the attribute (if any). The last one (with the star) is a shortcut for
    operating on a player Account rather than an Object.

    If you want <value> to be an object, use $dbef(#dbref) or
    $search(key) to assign it. You need control or edit access to
    the object you are adding.

    The most common data to save with this command are strings and
    numbers. You can however also set Python primitives such as lists,
    dictionaries and tuples on objects (this might be important for
    the functionality of certain custom objects).  This is indicated
    by you starting your value with one of |c'|n, |c"|n, |c(|n, |c[|n
    or |c{ |n.

    Once you have stored a Python primitive as noted above, you can include
    |c[<key>]|n in <attr> to reference nested values in e.g. a list or dict.

    Remember that if you use Python primitives like this, you must
    write proper Python syntax too - notably you must include quotes
    around your strings or you will get an error.

    """

    key = "@set"
    locks = "cmd:perm(set) or perm(Builder)"
    help_category = "Building"
    nested_re = re.compile(r"\[.*?\]")
    not_found = object()

    def check_obj(self, obj):
        """
        This may be overridden by subclasses in case restrictions need to be
        placed on whether certain objects can have attributes set by certain
        accounts.

        This function is expected to display its own error message.

        Returning False will abort the command.
        """
        return True

    def check_attr(self, obj, attr_name, category):
        """
        This may be overridden by subclasses in case restrictions need to be
        placed on what attributes can be set by who beyond the normal lock.

        This functions is expected to display its own error message. It is
        run once for every attribute that is checked, blocking only those
        attributes which are not permitted and letting the others through.
        """
        return attr_name

    def split_nested_attr(self, attr):
        """
        Yields tuples of (possible attr name, nested keys on that attr).
        For performance, this is biased to the deepest match, but allows compatibility
        with older attrs that might have been named with `[]`'s.

        > list(split_nested_attr("nested['asdf'][0]"))
        [
            ('nested', ['asdf', 0]),
            ("nested['asdf']", [0]),
            ("nested['asdf'][0]", []),
        ]
        """
        quotes = "\"'"

        def clean_key(val):
            val = val.strip("[]")
            if val[0] in quotes:
                return val.strip(quotes)
            if val[0] == LIST_APPEND_CHAR:
                # List insert/append syntax
                return val
            try:
                return int(val)
            except ValueError:
                return val

        parts = self.nested_re.findall(attr)

        base_attr = ""
        if parts:
            base_attr = attr[: attr.find(parts[0])]
        for index, part in enumerate(parts):
            yield (base_attr, [clean_key(p) for p in parts[index:]])
            base_attr += part
        yield (attr, [])

    def do_nested_lookup(self, value, *keys):
        result = value
        for key in keys:
            try:
                result = result.__getitem__(key)
            except (IndexError, KeyError, TypeError):
                return self.not_found
        return result

    def view_attr(self, obj, attr, category):
        """
        Look up the value of an attribute and return a string displaying it.
        """
        nested = False
        for key, nested_keys in self.split_nested_attr(attr):
            nested = True
            if obj.attributes.has(key):
                val = obj.attributes.get(key)
                val = self.do_nested_lookup(val, *nested_keys)
                if val is not self.not_found:
                    return f"\nAttribute {obj.name}/|w{attr}|n [category:{category}] = {val}"
        error = f"\nAttribute {obj.name}/|w{attr} [category:{category}] does not exist."
        if nested:
            error += " (Nested lookups attempted)"
        return error

    def rm_attr(self, obj, attr, category):
        """
        Remove an attribute from the object, or a nested data structure, and report back.
        """
        nested = False
        for key, nested_keys in self.split_nested_attr(attr):
            nested = True
            if obj.attributes.has(key, category):
                if nested_keys:
                    del_key = nested_keys[-1]
                    val = obj.attributes.get(key, category=category)
                    deep = self.do_nested_lookup(val, *nested_keys[:-1])
                    if deep is not self.not_found:
                        try:
                            del deep[del_key]
                        except (IndexError, KeyError, TypeError):
                            continue
                    return f"\nDeleted attribute {obj.name}/|w{attr}|n [category:{category}]."
                else:
                    exists = obj.attributes.has(key, category)
                    if exists:
                        obj.attributes.remove(attr, category=category)
                        return f"\nDeleted attribute {obj.name}/|w{attr}|n [category:{category}]."
                    else:
                        return (
                            f"\nNo attribute {obj.name}/|w{attr}|n [category: {category}] "
                            "was found to delete."
                        )
        error = f"\nNo attribute {obj.name}/|w{attr}|n [category: {category}] was found to delete."
        if nested:
            error += " (Nested lookups attempted)"
        return error

    def set_attr(self, obj, attr, value, category):
        done = False
        for key, nested_keys in self.split_nested_attr(attr):
            if obj.attributes.has(key, category) and nested_keys:
                acc_key = nested_keys[-1]
                lookup_value = obj.attributes.get(key, category)
                deep = self.do_nested_lookup(lookup_value, *nested_keys[:-1])
                if deep is not self.not_found:
                    # To support appending and inserting to lists
                    # a key that starts with LIST_APPEND_CHAR will insert a new item at that
                    # location, and move the other elements down.
                    # Using LIST_APPEND_CHAR alone will append to the list
                    if isinstance(acc_key, str) and acc_key[0] == LIST_APPEND_CHAR:
                        try:
                            if len(acc_key) > 1:
                                where = int(acc_key[1:])
                                deep.insert(where, value)
                            else:
                                deep.append(value)
                        except (ValueError, AttributeError):
                            pass
                        else:
                            value = lookup_value
                            attr = key
                            done = True
                            break

                    # List magic failed, just use like a key/index
                    try:
                        deep[acc_key] = value
                    except TypeError as err:
                        # Tuples can't be modified
                        return f"\n{err} - {deep}"

                    value = lookup_value
                    attr = key
                    done = True
                    break

        verb = "Modified" if obj.attributes.has(attr) else "Created"
        try:
            if not done:
                obj.attributes.add(attr, value, category)
            return f"\n{verb} attribute {obj.name}/|w{attr}|n [category:{category}] = {value}"
        except SyntaxError:
            # this means literal_eval tried to parse a faulty string
            return (
                "\n|RCritical Python syntax error in your value. Only "
                "primitive Python structures are allowed.\nYou also "
                "need to use correct Python syntax. Remember especially "
                "to put quotes around all strings inside lists and "
                "dicts.|n"
            )

    @interactive
    def edit_handler(self, obj, attr, caller):
        """Activate the line editor"""

        def load(caller):
            """Called for the editor to load the buffer"""

            try:
                old_value = obj.attributes.get(attr, raise_exception=True)
            except AttributeError:
                # we set empty buffer on nonexisting Attribute because otherwise
                # we'd always have the string "None" in the buffer to start with
                old_value = ""
            return str(old_value)  # we already confirmed we are ok with this

        def save(caller, buf):
            """Called when editor saves its buffer."""
            obj.attributes.add(attr, buf)
            caller.msg(f"Saved Attribute {attr}.")

        # check non-strings before activating editor
        try:
            old_value = obj.attributes.get(attr, raise_exception=True)
            if not isinstance(old_value, str):
                answer = yield (
                    f"|rWarning: Attribute |w{attr}|r is of type |w{type(old_value).__name__}|r. "
                    "\nTo continue editing, it must be converted to (and saved as) a string. "
                    "Continue? [Y]/N?"
                )
                if answer.lower() in ("n", "no"):
                    self.caller.msg("Aborted edit.")
                    return
        except AttributeError:
            pass

        # start the editor
        EvEditor(self.caller, load, save, key=f"{obj}/{attr}")

    def search_for_obj(self, objname):
        """
        Searches for an object matching objname. The object may be of different typeclasses.
        Args:
            objname: Name of the object we're looking for

        Returns:
            A typeclassed object, or None if nothing is found.
        """
        from evennia.utils.utils import variable_from_module

        _AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
        caller = self.caller
        if objname.startswith("*") or "account" in self.switches:
            found_obj = caller.search_account(objname.lstrip("*"))
        elif "script" in self.switches:
            found_obj = _AT_SEARCH_RESULT(search.search_script(objname), caller)
        elif "channel" in self.switches:
            found_obj = _AT_SEARCH_RESULT(search.search_channel(objname), caller)
        else:
            global_search = True
            if "char" in self.switches or "character" in self.switches:
                typeclass = settings.BASE_CHARACTER_TYPECLASS
            elif "room" in self.switches:
                typeclass = settings.BASE_ROOM_TYPECLASS
            elif "exit" in self.switches:
                typeclass = settings.BASE_EXIT_TYPECLASS
            else:
                global_search = False
                typeclass = None
            found_obj = caller.search(objname, global_search=global_search, typeclass=typeclass)
        return found_obj

    def func(self):
        """Implement the set attribute - a limited form of py."""

        caller = self.caller
        if not self.args:
            caller.msg("Usage: set obj/attr[:category] = value. Use empty value to clear.")
            return

        # get values prepared by the parser
        value = self.rhs
        objname = self.lhs_objattr[0]["name"]
        attrs = self.lhs_objattr[0]["attrs"]
        category = self.lhs_objs[0].get("option")  # None if unset

        obj = self.search_for_obj(objname)
        if not obj:
            return

        if not self.check_obj(obj):
            return

        result = []
        if "edit" in self.switches:
            # edit in the line editor
            if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                caller.msg(f"You don't have permission to edit {obj.key}.")
                return

            if len(attrs) > 1:
                caller.msg("The Line editor can only be applied to one attribute at a time.")
                return
            if not attrs:
                caller.msg(
                    "Use `set/edit <objname>/<attr>` to define the Attribute to edit.\nTo "
                    "edit the current room description, use `set/edit here/desc` (or "
                    "use the `desc` command)."
                )
                return
            self.edit_handler(obj, attrs[0], caller)
            return
        if not value:
            if self.rhs is None:
                # no = means we inspect the attribute(s)
                if not attrs:
                    attrs = [
                        attr.key
                        for attr in obj.attributes.get(
                            category=None, return_obj=True, return_list=True
                        )
                    ]
                for attr in attrs:
                    if not self.check_attr(obj, attr, category):
                        continue
                    result.append(self.view_attr(obj, attr, category))
            else:
                # deleting the attribute(s)
                if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                    caller.msg(f"You don't have permission to edit {obj.key}.")
                    return
                for attr in attrs:
                    if not self.check_attr(obj, attr, category):
                        continue
                    result.append(self.rm_attr(obj, attr, category))
        else:
            # setting attribute(s). Make sure to convert to real Python type before saving.
            # add support for $dbref() and $search() in set argument
            global _ATTRFUNCPARSER
            if not _ATTRFUNCPARSER:
                _ATTRFUNCPARSER = funcparser.FuncParser(
                    {
                        "dbref": funcparser.funcparser_callable_search,
                        "search": funcparser.funcparser_callable_search,
                    }
                )

            if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                caller.msg(f"You don't have permission to edit {obj.key}.")
                return
            for attr in attrs:
                if not self.check_attr(obj, attr, category):
                    continue
                # from evennia import set_trace;set_trace()
                parsed_value = _ATTRFUNCPARSER.parse(value, return_str=False, caller=caller)
                if hasattr(parsed_value, "access"):
                    # if this is an object we must have the right to read it, if so,
                    # we will not convert it to a string
                    if not (
                        parsed_value.access(caller, "control")
                        or parsed_value.access(self.caller, "edit")
                    ):
                        caller.msg(
                            f"You don't have permission to set object with identifier '{value}'."
                        )
                        continue
                    value = parsed_value
                else:
                    value = _convert_from_string(self, value)
                result.append(self.set_attr(obj, attr, value, category))
        # check if anything was done
        if not result:
            caller.msg(
                "No valid attributes were found. Usage: set obj/attr[:category] = value. Use empty"
                " value to clear."
            )
        else:
            # send feedback
            caller.msg("".join(result).strip("\n"))


class CmdTypeclass(COMMAND_DEFAULT_CLASS):
    """
    set or change an object's typeclass

    Usage:
      typeclass[/switch] <object> [= typeclass.path]
      typeclass/prototype <object> = prototype_key

      typeclasses or typeclass/list/show [typeclass.path]
      swap - this is a shorthand for using /force/reset flags.
      update - this is a shorthand for using the /force/reload flag.

    Switch:
      show, examine - display the current typeclass of object (default) or, if
            given a typeclass path, show the docstring of that typeclass.
      update - *only* re-run at_object_creation on this object
              meaning locks or other properties set later may remain.
      reset - clean out *all* the attributes and properties on the
              object - basically making this a new clean object. This will also
              reset cmdsets!
      force - change to the typeclass also if the object
              already has a typeclass of the same name.
      list - show available typeclasses. Only typeclasses in modules actually
             imported or used from somewhere in the code will show up here
             (those typeclasses are still available if you know the path)
      prototype - clean and overwrite the object with the specified
               prototype key - effectively making a whole new object.

    Example:
      type button = examples.red_button.RedButton
      type/prototype button=a red button

    If the typeclass_path is not given, the current object's typeclass is
    assumed.

    View or set an object's typeclass. If setting, the creation hooks of the
    new typeclass will be run on the object. If you have clashing properties on
    the old class, use /reset. By default you are protected from changing to a
    typeclass of the same name as the one you already have - use /force to
    override this protection.

    The given typeclass must be identified by its location using python
    dot-notation pointing to the correct module and class. If no typeclass is
    given (or a wrong typeclass is given). Errors in the path or new typeclass
    will lead to the old typeclass being kept. The location of the typeclass
    module is searched from the default typeclass directory, as defined in the
    server settings.

    """

    key = "@typeclass"
    aliases = ["@type", "@parent", "@swap", "@update", "@typeclasses"]
    switch_options = ("show", "examine", "update", "reset", "force", "list", "prototype")
    locks = "cmd:perm(typeclass) or perm(Builder)"
    help_category = "Building"

    def _generic_search(self, query, typeclass_path):

        caller = self.caller
        if typeclass_path:
            # make sure we search the right database table
            try:
                new_typeclass = class_from_module(typeclass_path)
            except ImportError:
                # this could be a prototype and not a typeclass at all
                return caller.search(query)

            dbclass = new_typeclass.__dbclass__

            if caller.__dbclass__ == dbclass:
                # object or account match
                obj = caller.search(query)
                if not obj:
                    return
            elif self.account and self.account.__dbclass__ == dbclass:
                # applying account while caller is object
                caller.msg(f"Trying to search {new_typeclass} with query '{self.lhs}'.")
                obj = self.account.search(query)
                if not obj:
                    return
            elif hasattr(caller, "puppet") and caller.puppet.__dbclass__ == dbclass:
                # applying object while caller is account
                caller.msg(f"Trying to search {new_typeclass} with query '{self.lhs}'.")
                obj = caller.puppet.search(query)
                if not obj:
                    return
            else:
                # other mismatch between caller and specified typeclass
                caller.msg(f"Trying to search {new_typeclass} with query '{self.lhs}'.")
                obj = new_typeclass.search(query)
                if not obj:
                    if isinstance(obj, list):
                        caller.msg(f"Could not find {new_typeclass} with query '{self.lhs}'.")
                    return
        else:
            # no rhs, use caller's typeclass
            obj = caller.search(query)
            if not obj:
                return

        return obj

    def func(self):
        """Implements command"""

        caller = self.caller

        if "list" in self.switches or self.cmdname in ("typeclasses", "@typeclasses"):
            tclasses = get_all_typeclasses()
            contribs = [key for key in sorted(tclasses) if key.startswith("evennia.contrib")] or [
                "<None loaded>"
            ]
            core = [
                key for key in sorted(tclasses) if key.startswith("evennia") and key not in contribs
            ] or ["<None loaded>"]
            game = [key for key in sorted(tclasses) if not key.startswith("evennia")] or [
                "<None loaded>"
            ]
            string = (
                "|wCore typeclasses|n\n"
                "    {core}\n"
                "|wLoaded Contrib typeclasses|n\n"
                "    {contrib}\n"
                "|wGame-dir typeclasses|n\n"
                "    {game}"
            ).format(
                core="\n    ".join(core), contrib="\n    ".join(contribs), game="\n    ".join(game)
            )
            EvMore(caller, string, exit_on_lastpage=True)
            return

        if not self.args:
            caller.msg("Usage: %s <object> [= typeclass]" % self.cmdstring)
            return

        if "show" in self.switches or "examine" in self.switches:
            oquery = self.lhs
            obj = caller.search(oquery, quiet=True)
            if not obj:
                # no object found to examine, see if it's a typeclass-path instead
                tclasses = get_all_typeclasses()
                matches = [
                    (key, tclass) for key, tclass in tclasses.items() if key.endswith(oquery)
                ]
                nmatches = len(matches)
                if nmatches > 1:
                    caller.msg(
                        "Multiple typeclasses found matching {}:\n  {}".format(
                            oquery, "\n  ".join(tup[0] for tup in matches)
                        )
                    )
                elif not matches:
                    caller.msg(f"No object or typeclass path found to match '{oquery}'")
                else:
                    # one match found
                    caller.msg(f"Docstring for typeclass '{oquery}': \n{matches[0][1].__doc__}")
            else:
                # do the search again to get the error handling in case of multi-match
                obj = caller.search(oquery)
                if not obj:
                    return
                caller.msg(
                    f"{obj.name}'s current typeclass is"
                    f" '{obj.__class__.__module__}.{obj.__class__.__name__}'"
                )
            return

        obj = self._generic_search(self.lhs, self.rhs)
        if not obj:
            return

        if not hasattr(obj, "__dbclass__"):
            string = "%s is not a typed object." % obj.name
            caller.msg(string)
            return

        new_typeclass = self.rhs or obj.path

        prototype = None
        if "prototype" in self.switches:
            key = self.rhs
            prototype = protlib.search_prototype(key=key)
            if len(prototype) > 1:
                caller.msg(
                    "More than one match for {}:\n{}".format(
                        key, "\n".join(proto.get("prototype_key", "") for proto in prototype)
                    )
                )
                return
            elif prototype:
                # one match
                prototype = prototype[0]
            else:
                # no match
                caller.msg(f"No prototype '{key}' was found.")
                return
            new_typeclass = prototype["typeclass"]
            self.switches.append("force")

        if "show" in self.switches or "examine" in self.switches:
            caller.msg(f"{obj.name}'s current typeclass is '{obj.__class__}'")
            return

        if self.cmdstring in ("swap", "@swap"):
            self.switches.append("force")
            self.switches.append("reset")
        elif self.cmdstring in ("update", "@update"):
            self.switches.append("force")
            self.switches.append("update")

        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You are not allowed to do that.")
            return

        if not hasattr(obj, "swap_typeclass"):
            caller.msg("This object cannot have a type at all!")
            return

        is_same = obj.is_typeclass(new_typeclass, exact=True)
        if is_same and "force" not in self.switches:
            string = (
                f"{obj.name} already has the typeclass '{new_typeclass}'. Use /force to override."
            )
        else:
            reset = "reset" in self.switches
            update = "update" in self.switches or not reset  # default to update

            hooks = "at_object_creation" if update and not reset else "all"
            old_typeclass_path = obj.typeclass_path

            if reset:
                answer = yield (
                    "|yNote that this will reset the object back to its typeclass' default state,"
                    " removing any custom locks/perms/attributes etc that may have been added by an"
                    " explicit create_object call. Use `update` or type/force instead in order to"
                    " keep such data. Continue [Y]/N?|n"
                )
                if answer.upper() in ("N", "NO"):
                    caller.msg("Aborted.")
                    return

            # special prompt for the user in cases where we want
            # to confirm changes.
            if "prototype" in self.switches:
                diff, _ = spawner.prototype_diff_from_object(prototype, obj)
                txt = spawner.format_diff(diff)
                prompt = (
                    f"Applying prototype '{prototype['key']}' over '{obj.name}' will cause the"
                    f" follow changes:\n{txt}\n"
                )
                if not reset:
                    prompt += (
                        "\n|yWARNING:|n Use the /reset switch to apply the prototype over a blank"
                        " state."
                    )
                prompt += "\nAre you sure you want to apply these changes [yes]/no?"
                answer = yield (prompt)
                if answer and answer in ("no", "n"):
                    caller.msg("Canceled: No changes were applied.")
                    return

            # we let this raise exception if needed
            obj.swap_typeclass(
                new_typeclass, clean_attributes=reset, clean_cmdsets=reset, run_start_hooks=hooks
            )

            if "prototype" in self.switches:
                modified = spawner.batch_update_objects_with_prototype(
                    prototype, objects=[obj], caller=self.caller
                )
                prototype_success = modified > 0
                if not prototype_success:
                    caller.msg(f"Prototype {prototype['key']} failed to apply.")

            if is_same:
                string = f"{obj.name} updated its existing typeclass ({obj.path}).\n"
            else:
                string = (
                    f"{obj.name} changed typeclass from {old_typeclass_path} to"
                    f" {obj.typeclass_path}.\n"
                )
            if update:
                string += "Only the at_object_creation hook was run (update mode)."
            else:
                string += "All object creation hooks were run."
            if reset:
                string += " All old attributes where deleted before the swap."
            else:
                string += (
                    " Attributes set before swap were not removed\n(use `swap` or `type/reset` to"
                    " clear all)."
                )
            if "prototype" in self.switches and prototype_success:
                string += (
                    f" Prototype '{prototype['key']}' was successfully applied over the object"
                    " type."
                )

        caller.msg(string)


class CmdWipe(ObjManipCommand):
    """
    clear all attributes from an object

    Usage:
      wipe <object>[/<attr>[/<attr>...]]

    Example:
      wipe box
      wipe box/colour

    Wipes all of an object's attributes, or optionally only those
    matching the given attribute-wildcard search string.
    """

    key = "@wipe"
    locks = "cmd:perm(wipe) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """
        inp is the dict produced in ObjManipCommand.parse()
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: wipe <object>[/<attr>/<attr>...]")
            return

        # get the attributes set by our custom parser
        objname = self.lhs_objattr[0]["name"]
        attrs = self.lhs_objattr[0]["attrs"]

        obj = caller.search(objname)
        if not obj:
            return
        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You are not allowed to do that.")
            return
        if not attrs:
            # wipe everything
            obj.attributes.clear()
            string = f"Wiped all attributes on {obj.name}."
        else:
            for attrname in attrs:
                obj.attributes.remove(attrname)
            string = f"Wiped attributes {','.join(attrs)} on {obj.name}."
        caller.msg(string)


class CmdLock(ObjManipCommand):
    """
    assign a lock definition to an object

    Usage:
      lock <object or *account>[ = <lockstring>]
      or
      lock[/switch] <object or *account>/<access_type>

    Switch:
      del - delete given access type
      view - view lock associated with given access type (default)

    If no lockstring is given, shows all locks on
    object.

    Lockstring is of the form
       access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
    Where func1, func2 ... valid lockfuncs with or without arguments.
    Separator expressions need not be capitalized.

    For example:
       'get: id(25) or perm(Admin)'
    The 'get' lock access_type is checked e.g. by the 'get' command.
    An object locked with this example lock will only be possible to pick up
    by Admins or by an object with id=25.

    You can add several access_types after one another by separating
    them by ';', i.e:
       'get:id(25); delete:perm(Builder)'
    """

    key = "@lock"
    aliases = ["@locks"]
    locks = "cmd: perm(locks) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Sets up the command"""

        caller = self.caller
        if not self.args:
            string = "Usage: lock <object>[ = <lockstring>] or lock[/switch] <object>/<access_type>"
            caller.msg(string)
            return

        if "/" in self.lhs:
            # call of the form lock obj/access_type
            objname, access_type = [p.strip() for p in self.lhs.split("/", 1)]
            obj = None
            if objname.startswith("*"):
                obj = caller.search_account(objname.lstrip("*"))
            if not obj:
                obj = caller.search(objname)
                if not obj:
                    return
            has_control_access = obj.access(caller, "control")
            if access_type == "control" and not has_control_access:
                # only allow to change 'control' access if you have 'control' access already
                caller.msg("You need 'control' access to change this type of lock.")
                return

            if not (has_control_access or obj.access(caller, "edit")):
                caller.msg("You are not allowed to do that.")
                return

            lockdef = obj.locks.get(access_type)

            if lockdef:
                if "del" in self.switches:
                    obj.locks.delete(access_type)
                    string = "deleted lock %s" % lockdef
                else:
                    string = lockdef
            else:
                string = f"{obj} has no lock of access type '{access_type}'."
            caller.msg(string)
            return

        if self.rhs:
            # we have a = separator, so we are assigning a new lock
            if self.switches:
                swi = ", ".join(self.switches)
                caller.msg(
                    f"Switch(es) |w{swi}|n can not be used with a "
                    "lock assignment. Use e.g. "
                    "|wlock/del objname/locktype|n instead."
                )
                return

            objname, lockdef = self.lhs, self.rhs
            obj = None
            if objname.startswith("*"):
                obj = caller.search_account(objname.lstrip("*"))
            if not obj:
                obj = caller.search(objname)
                if not obj:
                    return
            if not (obj.access(caller, "control") or obj.access(caller, "edit")):
                caller.msg("You are not allowed to do that.")
                return
            ok = False
            lockdef = re.sub(r"\'|\"", "", lockdef)
            try:
                ok = obj.locks.add(lockdef)
            except LockException as e:
                caller.msg(str(e))
            if "cmd" in lockdef.lower() and inherits_from(
                obj, "evennia.objects.objects.DefaultExit"
            ):
                # special fix to update Exits since "cmd"-type locks won't
                # update on them unless their cmdsets are rebuilt.
                obj.at_init()
            if ok:
                caller.msg(f"Added lock '{lockdef}' to {obj}.")
            return

        # if we get here, we are just viewing all locks on obj
        obj = None
        if self.lhs.startswith("*"):
            obj = caller.search_account(self.lhs.lstrip("*"))
        if not obj:
            obj = caller.search(self.lhs)
        if not obj:
            return
        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You are not allowed to do that.")
            return
        caller.msg("\n".join(obj.locks.all()))


class CmdExamine(ObjManipCommand):
    """
    get detailed information about an object

    Usage:
      examine [<object>[/attrname]]
      examine [*<account>[/attrname]]

    Switch:
      account - examine an Account (same as adding *)
      object - examine an Object (useful when OOC)
      script - examine a Script
      channel - examine a Channel

    The examine command shows detailed game info about an
    object and optionally a specific attribute on it.
    If object is not specified, the current location is examined.

    Append a * before the search string to examine an account.

    """

    key = "@examine"
    aliases = ["@ex", "@exam"]
    locks = "cmd:perm(examine) or perm(Builder)"
    help_category = "Building"
    arg_regex = r"(/\w+?(\s|$))|\s|$"
    switch_options = ["account", "object", "script", "channel"]

    object_type = "object"

    detail_color = "|c"
    header_color = "|w"
    quell_color = "|r"
    separator = "-"

    def msg(self, text):
        """
        Central point for sending messages to the caller. This tags
        the message as 'examine' for eventual custom markup in the client.

        Attributes:
            text (str): The text to send.

        """
        self.caller.msg(text=(text, {"type": "examine"}))

    def format_key(self, obj):
        return f"{obj.name} ({obj.dbref})"

    def format_aliases(self, obj):
        if hasattr(obj, "aliases") and obj.aliases.all():
            return ", ".join(utils.make_iter(str(obj.aliases)))

    def format_typeclass(self, obj):
        if hasattr(obj, "typeclass_path"):
            return f"{obj.typename} ({obj.typeclass_path})"

    def format_sessions(self, obj):
        if hasattr(obj, "sessions"):
            sessions = obj.sessions.all()
            if sessions:
                return ", ".join(f"#{sess.sessid}" for sess in obj.sessions.all())

    def format_email(self, obj):
        if hasattr(obj, "email") and obj.email:
            return f"{self.detail_color}{obj.email}|n"

    def format_account_key(self, account):
        return f"{self.detail_color}{account.name}|n ({account.dbref})"

    def format_account_typeclass(self, account):
        return f"{account.typename} ({account.typeclass_path})"

    def format_account_permissions(self, account):
        perms = account.permissions.all()
        if account.is_superuser:
            perms = ["<Superuser>"]
        elif not perms:
            perms = ["<None>"]
        perms = ", ".join(perms)
        if account.attributes.has("_quell"):
            perms += f" {self.quell_color}(quelled)|n"
        return perms

    def format_location(self, obj):
        if hasattr(obj, "location") and obj.location:
            return f"{obj.location.key} (#{obj.location.id})"

    def format_home(self, obj):
        if hasattr(obj, "home") and obj.home:
            return f"{obj.home.key} (#{obj.home.id})"

    def format_destination(self, obj):
        if hasattr(obj, "destination") and obj.destination:
            return f"{obj.destination.key} (#{obj.destination.id})"

    def format_permissions(self, obj):
        perms = obj.permissions.all()
        if perms:
            perms_string = ", ".join(perms)
            if obj.is_superuser:
                perms_string += " <Superuser>"
            return perms_string

    def format_locks(self, obj):
        locks = str(obj.locks)
        if locks:
            return utils.fill("; ".join([lock for lock in locks.split(";")]), indent=2)
        return "Default"

    def format_scripts(self, obj):
        if hasattr(obj, "scripts") and hasattr(obj.scripts, "all") and obj.scripts.all():
            return f"{obj.scripts}"

    def format_single_tag(self, tag):
        if tag.db_category:
            return f"{tag.db_key}[{tag.db_category}]"
        else:
            return f"{tag.db_key}"

    def format_tags(self, obj):
        if hasattr(obj, "tags"):
            tags = sorted(obj.tags.all(return_objs=True))
            if tags:
                formatted_tags = [self.format_single_tag(tag) for tag in tags]
                return utils.fill(", ".join(formatted_tags), indent=2)

    def format_single_cmdset_options(self, cmdset):
        def _truefalse(string, value):
            if value is None:
                return ""
            if value:
                return f"{string}: T"
            return f"{string}: F"

        txt = ", ".join(
            _truefalse(opt, getattr(cmdset, opt))
            for opt in ("no_exits", "no_objs", "no_channels", "duplicates")
            if getattr(cmdset, opt) is not None
        )
        return ", " + txt if txt else ""

    def format_single_cmdset(self, cmdset):
        options = self.format_single_cmdset_options(cmdset)
        return f"{cmdset.path} [{cmdset.key}] ({cmdset.mergetype}, prio {cmdset.priority}{options})"

    def format_stored_cmdsets(self, obj):
        if hasattr(obj, "cmdset"):
            stored_cmdset_strings = []
            stored_cmdsets = sorted(obj.cmdset.all(), key=lambda x: x.priority, reverse=True)
            for cmdset in stored_cmdsets:
                if cmdset.key != "_EMPTY_CMDSET":
                    stored_cmdset_strings.append(self.format_single_cmdset(cmdset))
            return "\n  " + "\n  ".join(stored_cmdset_strings)

    def format_merged_cmdsets(self, obj, current_cmdset):
        if not hasattr(obj, "cmdset"):
            return None

        all_cmdsets = [(cmdset.key, cmdset) for cmdset in current_cmdset.merged_from]
        # we always at least try to add account- and session sets since these are ignored
        # if we merge on the object level.
        if hasattr(obj, "account") and obj.account:
            # get Attribute-cmdsets if they exist
            all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.account.cmdset.all()])
            if obj.sessions.count():
                # if there are more sessions than one on objects it's because of multisession mode
                # we only show the first session's cmdset here (it is -in principle- possible
                # that different sessions have different cmdsets but for admins who want such
                # madness it is better that they overload with their own CmdExamine to handle it).
                all_cmdsets.extend(
                    [(cmdset.key, cmdset) for cmdset in obj.account.sessions.all()[0].cmdset.all()]
                )
        else:
            try:
                # we have to protect this since many objects don't have sessions.
                all_cmdsets.extend(
                    [
                        (cmdset.key, cmdset)
                        for cmdset in obj.get_session(obj.sessions.get()).cmdset.all()
                    ]
                )
            except (TypeError, AttributeError):
                # an error means we are merging an object without a session
                pass
        all_cmdsets = [cmdset for cmdset in dict(all_cmdsets).values()]
        all_cmdsets.sort(key=lambda x: x.priority, reverse=True)

        merged_cmdset_strings = []
        for cmdset in all_cmdsets:
            if cmdset.key != "_EMPTY_CMDSET":
                merged_cmdset_strings.append(self.format_single_cmdset(cmdset))
        return "\n  " + "\n  ".join(merged_cmdset_strings)

    def format_current_cmds(self, obj, current_cmdset):
        current_commands = sorted([cmd.key for cmd in current_cmdset if cmd.access(obj, "cmd")])
        return "\n" + utils.fill(", ".join(current_commands), indent=2)

    def _get_attribute_value_type(self, attrvalue):
        typ = ""
        if not isinstance(attrvalue, str):
            try:
                name = attrvalue.__class__.__name__
            except AttributeError:
                try:
                    name = attrvalue.__name__
                except AttributeError:
                    name = attrvalue
            if str(name).startswith("_Saver"):
                try:
                    typ = str(type(deserialize(attrvalue)))
                except Exception:
                    typ = str(type(deserialize(attrvalue)))
            else:
                typ = str(type(attrvalue))
        return typ

    def format_single_attribute_detail(self, obj, attr):
        global _FUNCPARSER
        if not _FUNCPARSER:
            _FUNCPARSER = funcparser.FuncParser(settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES)

        key, category, value = attr.db_key, attr.db_category, attr.value
        typ = self._get_attribute_value_type(value)
        typ = f" |B[type: {typ}]|n" if typ else ""
        value = utils.to_str(value)
        value = _FUNCPARSER.parse(ansi_raw(value), escape=True)
        return (
            f"Attribute {obj.name}/{self.header_color}{key}|n "
            f"[category={category}]{typ}:\n\n{value}"
        )

    def format_single_attribute(self, attr):
        global _FUNCPARSER
        if not _FUNCPARSER:
            _FUNCPARSER = funcparser.FuncParser(settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES)

        key, category, value = attr.db_key, attr.db_category, attr.value
        typ = self._get_attribute_value_type(value)
        typ = f" |B[type: {typ}]|n" if typ else ""
        value = utils.to_str(value)
        value = _FUNCPARSER.parse(ansi_raw(value), escape=True)
        value = utils.crop(value)
        if category:
            return f"{self.header_color}{key}|n[{category}]={value}{typ}"
        else:
            return f"{self.header_color}{key}|n={value}{typ}"

    def format_attributes(self, obj):
        output = "\n  " + "\n  ".join(
            sorted(self.format_single_attribute(attr) for attr in obj.db_attributes.all())
        )
        if output.strip():
            # we don't want just an empty line
            return output

    def format_nattributes(self, obj):
        try:
            ndb_attr = obj.nattributes.all()
        except Exception:
            return

        if ndb_attr and ndb_attr[0]:
            return "\n  " + "\n  ".join(
                sorted(self.format_single_attribute(attr) for attr in ndb_attr)
            )

    def format_exits(self, obj):
        if hasattr(obj, "exits"):
            exits = ", ".join(f"{exit.name}({exit.dbref})" for exit in obj.exits)
            return exits if exits else None

    def format_chars(self, obj):
        if hasattr(obj, "contents"):
            chars = ", ".join(f"{obj.name}({obj.dbref})" for obj in obj.contents if obj.account)
            return chars if chars else None

    def format_things(self, obj):
        if hasattr(obj, "contents"):
            things = ", ".join(
                f"{obj.name}({obj.dbref})"
                for obj in obj.contents
                if not obj.account and not obj.destination
            )
            return things if things else None

    def format_script_desc(self, obj):
        if hasattr(obj, "db_desc") and obj.db_desc:
            return crop(obj.db_desc, 20)

    def format_script_is_persistent(self, obj):
        if hasattr(obj, "db_persistent"):
            return "T" if obj.db_persistent else "F"

    def format_script_timer_data(self, obj):
        if hasattr(obj, "db_interval") and obj.db_interval > 0:
            start_delay = "T" if obj.db_start_delay else "F"
            next_repeat = obj.time_until_next_repeat()
            active = "|grunning|n" if obj.db_is_active and next_repeat else "|rinactive|n"
            interval = obj.db_interval
            next_repeat = "N/A" if next_repeat is None else f"{next_repeat}s"
            repeats = ""
            if obj.db_repeats:
                remaining_repeats = obj.remaining_repeats()
                remaining_repeats = 0 if remaining_repeats is None else remaining_repeats
                repeats = f" - {remaining_repeats}/{obj.db_repeats} remain"
            return (
                f"{active} - interval: {interval}s "
                f"(next: {next_repeat}{repeats}, start_delay: {start_delay})"
            )

    def format_channel_sub_totals(self, obj):
        if hasattr(obj, "db_account_subscriptions"):
            account_subs = obj.db_account_subscriptions.all()
            object_subs = obj.db_object_subscriptions.all()
            online = len(obj.subscriptions.online())
            ntotal = account_subs.count() + object_subs.count()
            return f"{ntotal} ({online} online)"

    def format_channel_account_subs(self, obj):
        if hasattr(obj, "db_account_subscriptions"):
            account_subs = obj.db_account_subscriptions.all()
            if account_subs:
                return "\n  " + "\n  ".join(
                    format_grid([sub.key for sub in account_subs], sep=" ", width=_DEFAULT_WIDTH)
                )

    def format_channel_object_subs(self, obj):
        if hasattr(obj, "db_object_subscriptions"):
            object_subs = obj.db_object_subscriptions.all()
            if object_subs:
                return "\n  " + "\n  ".join(
                    format_grid([sub.key for sub in object_subs], sep=" ", width=_DEFAULT_WIDTH)
                )

    def get_formatted_obj_data(self, obj, current_cmdset):
        """
        Calls all other `format_*` methods.

        """
        objdata = {}
        objdata["Name/key"] = self.format_key(obj)
        objdata["Aliases"] = self.format_aliases(obj)
        objdata["Typeclass"] = self.format_typeclass(obj)
        objdata["Sessions"] = self.format_sessions(obj)
        objdata["Email"] = self.format_email(obj)
        if hasattr(obj, "has_account") and obj.has_account:
            objdata["Account"] = self.format_account_key(obj.account)
            objdata["  Account Typeclass"] = self.format_account_typeclass(obj.account)
            objdata["  Account Permissions"] = self.format_account_permissions(obj.account)
        objdata["Location"] = self.format_location(obj)
        objdata["Home"] = self.format_home(obj)
        objdata["Destination"] = self.format_destination(obj)
        objdata["Permissions"] = self.format_permissions(obj)
        objdata["Locks"] = self.format_locks(obj)
        if current_cmdset and not (
            len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "_EMPTY_CMDSET"
        ):
            objdata["Stored Cmdset(s)"] = self.format_stored_cmdsets(obj)
            objdata["Merged Cmdset(s)"] = self.format_merged_cmdsets(obj, current_cmdset)
            objdata[
                f"Commands available to {obj.key} (result of Merged Cmdset(s))"
            ] = self.format_current_cmds(obj, current_cmdset)
        if self.object_type == "script":
            objdata["Description"] = self.format_script_desc(obj)
            objdata["Persistent"] = self.format_script_is_persistent(obj)
            objdata["Script Repeat"] = self.format_script_timer_data(obj)
        objdata["Scripts"] = self.format_scripts(obj)
        objdata["Tags"] = self.format_tags(obj)
        objdata["Persistent Attributes"] = self.format_attributes(obj)
        objdata["Non-Persistent Attributes"] = self.format_nattributes(obj)
        objdata["Exits"] = self.format_exits(obj)
        objdata["Characters"] = self.format_chars(obj)
        objdata["Content"] = self.format_things(obj)
        if self.object_type == "channel":
            objdata["Subscription Totals"] = self.format_channel_sub_totals(obj)
            objdata["Account Subscriptions"] = self.format_channel_account_subs(obj)
            objdata["Object Subscriptions"] = self.format_channel_object_subs(obj)

        return objdata

    def format_output(self, obj, current_cmdset):
        """
        Formats the full examine page return.

        """
        objdata = self.get_formatted_obj_data(obj, current_cmdset)

        # format output
        main_str = []
        max_width = -1
        for header, block in objdata.items():
            if block is not None:
                blockstr = f"{self.header_color}{header}|n: {block}"
                max_width = max(max_width, max(display_len(line) for line in blockstr.split("\n")))
                main_str.append(blockstr)
        main_str = "\n".join(main_str)

        max_width = max(0, min(self.client_width(), max_width))
        sep = self.separator * max_width

        return f"{sep}\n{main_str}\n{sep}"

    def _search_by_object_type(self, obj_name, objtype):
        """
        Route to different search functions depending on the object type being
        examined. This also handles error reporting for multimatches/no matches.

        Args:
            obj_name (str): The search query.
            objtype (str): One of 'object', 'account', 'script' or 'channel'.
        Returns:
            any: `None` if no match or multimatch, otherwise a single result.

        """
        obj = None

        if objtype == "object":
            obj = self.caller.search(obj_name)
        elif objtype == "account":
            try:
                obj = self.caller.search_account(obj_name.lstrip("*"))
            except AttributeError:
                # this means we are calling examine from an account object
                obj = self.caller.search(
                    obj_name.lstrip("*"), search_object="object" in self.switches
                )
        else:
            obj = getattr(search, f"search_{objtype}")(obj_name)
            if not obj:
                self.caller.msg(f"No {objtype} found with key {obj_name}.")
                obj = None
            elif len(obj) > 1:
                err = "Multiple {objtype} found with key {obj_name}:\n{matches}"
                self.caller.msg(
                    err.format(
                        obj_name=obj_name, matches=", ".join(f"{ob.key}(#{ob.id})" for ob in obj)
                    )
                )
                obj = None
            else:
                obj = obj[0]
        return obj

    def parse(self):
        super().parse()

        self.examine_objs = []

        if not self.args:
            # If no arguments are provided, examine the invoker's location.
            if hasattr(self.caller, "location"):
                self.examine_objs.append((self.caller.location, None))
            else:
                self.msg("You need to supply a target to examine.")
                raise InterruptCommand
        else:
            for objdef in self.lhs_objattr:
                # note that we check the objtype for every repeat; this will always
                # be the same result, but it makes for a cleaner code and multi-examine
                # is not so common anyway.

                obj = None
                obj_name = objdef["name"]  # name
                obj_attrs = objdef["attrs"]  # /attrs

                # identify object type, in prio account - script - channel
                object_type = "object"
                if (
                    utils.inherits_from(self.caller, "evennia.accounts.accounts.DefaultAccount")
                    or "account" in self.switches
                    or obj_name.startswith("*")
                ):
                    object_type = "account"
                elif "script" in self.switches:
                    object_type = "script"
                elif "channel" in self.switches:
                    object_type = "channel"

                self.object_type = object_type
                obj = self._search_by_object_type(obj_name, object_type)

                if obj:
                    self.examine_objs.append((obj, obj_attrs))

    def func(self):
        """Process command"""
        for obj, obj_attrs in self.examine_objs:
            # these are parsed out in .parse already

            if not obj.access(self.caller, "examine"):
                # If we don't have special info access, just look
                # at the object instead.
                self.msg(self.caller.at_look(obj))
                continue

            if obj_attrs:
                # we are only interested in specific attributes
                attrs = [attr for attr in obj.db_attributes.all() if attr.db_key in obj_attrs]
                if not attrs:
                    self.msg(f"No attributes found on {obj.name}.")
                else:
                    out_strings = []
                    for attr in attrs:
                        out_strings.append(self.format_single_attribute_detail(obj, attr))
                    out_str = "\n".join(out_strings)
                    max_width = max(display_len(line) for line in out_strings)
                    max_width = max(0, min(max_width, self.client_width()))
                    sep = self.separator * max_width
                    self.msg(f"{sep}\n{out_str}")
                return

            # examine the obj itself

            if self.object_type in ("object", "account"):
                # for objects and accounts we need to set up an asynchronous
                # fetch of the cmdset and not proceed with the examine display
                # until the fetch is complete
                session = None
                if obj.sessions.count():
                    mergemode = "session"
                    session = obj.sessions.get()[0]
                elif self.object_type == "account":
                    mergemode = "account"
                else:
                    mergemode = "object"

                account = None
                objct = None
                if self.object_type == "account":
                    account = obj
                else:
                    account = obj.account
                    objct = obj

                # this is usually handled when a command runs, but when we examine
                # we may have leftover inherited cmdsets directly after a move etc.
                obj.cmdset.update()
                # using callback to print results whenever function returns.

                def _get_cmdset_callback(current_cmdset):
                    self.msg(self.format_output(obj, current_cmdset).strip())

                get_and_merge_cmdsets(
                    obj, session, account, objct, mergemode, self.raw_string
                ).addCallback(_get_cmdset_callback)

            else:
                # for objects without cmdsets we can proceed to examine immediately
                self.msg(self.format_output(obj, None).strip())


class CmdFind(COMMAND_DEFAULT_CLASS):
    """
    search the database for objects

    Usage:
      find[/switches] <name or dbref or *account> [= dbrefmin[-dbrefmax]]
      locate - this is a shorthand for using the /loc switch.

    Switches:
      room       - only look for rooms (location=None)
      exit       - only look for exits (destination!=None)
      char       - only look for characters (BASE_CHARACTER_TYPECLASS)
      exact      - only exact matches are returned.
      loc        - display object location if exists and match has one result
      startswith - search for names starting with the string, rather than containing

    Searches the database for an object of a particular name or exact #dbref.
    Use *accountname to search for an account. The switches allows for
    limiting object matches to certain game entities. Dbrefmin and dbrefmax
    limits matches to within the given dbrefs range, or above/below if only
    one is given.
    """

    key = "@find"
    aliases = ["@search", "@locate"]
    switch_options = ("room", "exit", "char", "exact", "loc", "startswith")
    locks = "cmd:perm(find) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Search functionality"""
        caller = self.caller
        switches = self.switches

        if not self.args or (not self.lhs and not self.rhs):
            caller.msg("Usage: find <string> [= low [-high]]")
            return

        if "locate" in self.cmdstring:  # Use option /loc as a default for locate command alias
            switches.append("loc")

        searchstring = self.lhs

        try:
            # Try grabbing the actual min/max id values by database aggregation
            qs = ObjectDB.objects.values("id").aggregate(low=Min("id"), high=Max("id"))
            low, high = sorted(qs.values())
            if not (low and high):
                raise ValueError(
                    f"{self.__class__.__name__}: Min and max ID not returned by aggregation;"
                    " falling back to queryset slicing."
                )
        except Exception as e:
            logger.log_trace(e)
            # If that doesn't work for some reason (empty DB?), guess the lower
            # bound and do a less-efficient query to find the upper.
            low, high = 1, ObjectDB.objects.all().order_by("-id").first().id

        if self.rhs:
            try:
                # Check that rhs is either a valid dbref or dbref range
                bounds = tuple(
                    sorted(dbref(x, False) for x in re.split("[-\s]+", self.rhs.strip()))
                )

                # dbref() will return either a valid int or None
                assert bounds
                # None should not exist in the bounds list
                assert None not in bounds

                low = bounds[0]
                if len(bounds) > 1:
                    high = bounds[-1]

            except AssertionError:
                caller.msg("Invalid dbref range provided (not a number).")
                return
            except IndexError as e:
                logger.log_err(
                    f"{self.__class__.__name__}: Error parsing upper and lower bounds of query."
                )
                logger.log_trace(e)

        low = min(low, high)
        high = max(low, high)

        is_dbref = utils.dbref(searchstring)
        is_account = searchstring.startswith("*")

        restrictions = ""
        if self.switches:
            restrictions = ", %s" % ", ".join(self.switches)

        if is_dbref or is_account:
            if is_dbref:
                # a dbref search
                result = caller.search(searchstring, global_search=True, quiet=True)
                string = "|wExact dbref match|n(#%i-#%i%s):" % (low, high, restrictions)
            else:
                # an account search
                searchstring = searchstring.lstrip("*")
                result = caller.search_account(searchstring, quiet=True)
                string = "|wMatch|n(#%i-#%i%s):" % (low, high, restrictions)

            if "room" in switches:
                result = result if inherits_from(result, ROOM_TYPECLASS) else None
            if "exit" in switches:
                result = result if inherits_from(result, EXIT_TYPECLASS) else None
            if "char" in switches:
                result = result if inherits_from(result, CHAR_TYPECLASS) else None

            if not result:
                string += "\n   |RNo match found.|n"
            elif not low <= int(result[0].id) <= high:
                string += f"\n   |RNo match found for '{searchstring}' in #dbref interval.|n"
            else:
                result = result[0]
                string += f"\n|g   {result.get_display_name(caller)} - {result.path}|n"
                if "loc" in self.switches and not is_account and result.location:
                    string += f" (|wlocation|n: |g{result.location.get_display_name(caller)}|n)"
        else:
            # Not an account/dbref search but a wider search; build a queryset.
            # Searches for key and aliases
            if "exact" in switches:
                keyquery = Q(db_key__iexact=searchstring, id__gte=low, id__lte=high)
                aliasquery = Q(
                    db_tags__db_key__iexact=searchstring,
                    db_tags__db_tagtype__iexact="alias",
                    id__gte=low,
                    id__lte=high,
                )
            elif "startswith" in switches:
                keyquery = Q(db_key__istartswith=searchstring, id__gte=low, id__lte=high)
                aliasquery = Q(
                    db_tags__db_key__istartswith=searchstring,
                    db_tags__db_tagtype__iexact="alias",
                    id__gte=low,
                    id__lte=high,
                )
            else:
                keyquery = Q(db_key__icontains=searchstring, id__gte=low, id__lte=high)
                aliasquery = Q(
                    db_tags__db_key__icontains=searchstring,
                    db_tags__db_tagtype__iexact="alias",
                    id__gte=low,
                    id__lte=high,
                )

            # Keep the initial queryset handy for later reuse
            result_qs = ObjectDB.objects.filter(keyquery | aliasquery).distinct()
            nresults = result_qs.count()

            # Use iterator to minimize memory ballooning on large result sets
            results = result_qs.iterator()

            # Check and see if type filtering was requested; skip it if not
            if any(x in switches for x in ("room", "exit", "char")):
                obj_ids = set()
                for obj in results:
                    if (
                        ("room" in switches and inherits_from(obj, ROOM_TYPECLASS))
                        or ("exit" in switches and inherits_from(obj, EXIT_TYPECLASS))
                        or ("char" in switches and inherits_from(obj, CHAR_TYPECLASS))
                    ):
                        obj_ids.add(obj.id)

                # Filter previous queryset instead of requesting another
                filtered_qs = result_qs.filter(id__in=obj_ids).distinct()
                nresults = filtered_qs.count()

                # Use iterator again to minimize memory ballooning
                results = filtered_qs.iterator()

            # still results after type filtering?
            if nresults:
                if nresults > 1:
                    header = f"{nresults} Matches"
                else:
                    header = "One Match"

                string = f"|w{header}|n(#{low}-#{high}{restrictions}):"
                res = None
                for res in results:
                    string += f"\n   |g{res.get_display_name(caller)} - {res.path}|n"
                if (
                    "loc" in self.switches
                    and nresults == 1
                    and res
                    and getattr(res, "location", None)
                ):
                    string += f" (|wlocation|n: |g{res.location.get_display_name(caller)}|n)"
            else:
                string = f"|wNo Matches|n(#{low}-#{high}{restrictions}):"
                string += f"\n   |RNo matches found for '{searchstring}'|n"

        # send result
        caller.msg(string.strip())


class ScriptEvMore(EvMore):
    """
    Listing 1000+ Scripts can be very slow and memory-consuming. So
    we use this custom EvMore child to build en EvTable only for
    each page of the list.

    """

    def init_pages(self, scripts):
        """Prepare the script list pagination"""
        script_pages = Paginator(scripts, max(1, int(self.height / 2)))
        super().init_pages(script_pages)

    def page_formatter(self, scripts):
        """Takes a page of scripts and formats the output
        into an EvTable."""

        if not scripts:
            return "<No scripts>"

        table = EvTable(
            "|wdbref|n",
            "|wobj|n",
            "|wkey|n",
            "|wintval|n",
            "|wnext|n",
            "|wrept|n",
            "|wtypeclass|n",
            "|wdesc|n",
            align="r",
            border="tablecols",
            width=self.width,
        )

        for script in scripts:

            nextrep = script.time_until_next_repeat()
            if nextrep is None:
                nextrep = script.db._paused_time
                nextrep = f"PAUSED {int(nextrep)}s" if nextrep else "--"
            else:
                nextrep = f"{nextrep}s"

            maxrepeat = script.repeats
            remaining = script.remaining_repeats() or 0
            if maxrepeat:
                rept = "%i/%i" % (maxrepeat - remaining, maxrepeat)
            else:
                rept = "-/-"

            table.add_row(
                f"#{script.id}",
                f"{script.obj.key}({script.obj.dbref})"
                if (hasattr(script, "obj") and script.obj)
                else "<Global>",
                script.key,
                script.interval if script.interval > 0 else "--",
                nextrep,
                rept,
                script.typeclass_path.rsplit(".", 1)[-1],
                crop(script.desc, width=20),
            )

        return str(table)


class CmdScripts(COMMAND_DEFAULT_CLASS):
    """
    List and manage all running scripts. Allows for creating new global
    scripts.

    Usage:
      script[/switches] [script-#dbref, key, script.path or <obj>]
      script[/start||stop] <obj> = <script.path or script-key>

    Switches:
      start - start/unpause an existing script's timer.
      stop - stops an existing script's timer
      pause - pause a script's timer
      delete - deletes script. This will also stop the timer as needed

    Examples:
        script                         - list scripts
        script myobj                   - list all scripts on object
        script foo.bar.Script          - create a new global Script
        script scriptname              - examine named existing global script
        script myobj = foo.bar.Script  - create and assign script to object
        script/stop myobj = scriptname - stop script on object
        script/pause foo.Bar.Script    - pause global script
        script/delete myobj            - delete ALL scripts on object
        script/delete #dbref[-#dbref]  - delete script or range by dbref

    When given with an `<obj>` as left-hand-side, this creates and
    assigns a new script to that object. Without an `<obj>`, this
    manages and inspects global scripts

    If no switches are given, this command just views all active
    scripts. The argument can be either an object, at which point it
    will be searched for all scripts defined on it, or a script name
    or #dbref. For using the /stop switch, a unique script #dbref is
    required since whole classes of scripts often have the same name.

    Use the `script` build-level command for managing scripts attached to
    objects.

    """

    key = "@scripts"
    aliases = ["@script"]
    switch_options = ("create", "start", "stop", "pause", "delete")
    locks = "cmd:perm(scripts) or perm(Builder)"
    help_category = "System"

    excluded_typeclass_paths = ["evennia.prototypes.prototypes.DbPrototype"]

    switch_mapping = {
        "create": "|gCreated|n",
        "start": "|gStarted|n",
        "stop": "|RStopped|n",
        "pause": "|Paused|n",
        "delete": "|rDeleted|n",
    }
    # never show these script types
    hide_script_paths = ("evennia.prototypes.prototypes.DbPrototype",)

    def _search_script(self, args):
        # test first if this is a script match
        scripts = ScriptDB.objects.get_all_scripts(key=args).exclude(
            db_typeclass_path__in=self.hide_script_paths
        )
        if scripts:
            return scripts
        # try typeclass path
        scripts = (
            ScriptDB.objects.filter(db_typeclass_path__iendswith=args)
            .exclude(db_typeclass_path__in=self.hide_script_paths)
            .order_by("id")
        )
        if scripts:
            return scripts
        if "-" in args:
            # may be a dbref-range
            val1, val2 = (dbref(part.strip()) for part in args.split("-", 1))
            if val1 and val2:
                scripts = (
                    ScriptDB.objects.filter(id__in=(range(val1, val2 + 1)))
                    .exclude(db_typeclass_path__in=self.hide_script_paths)
                    .order_by("id")
                )
                if scripts:
                    return scripts

    def func(self):
        """implement method"""

        caller = self.caller

        if not self.args:
            # show all scripts
            scripts = ScriptDB.objects.all().exclude(db_typeclass_path__in=self.hide_script_paths)
            if not scripts:
                caller.msg("No scripts found.")
                return
            ScriptEvMore(caller, scripts.order_by("id"), session=self.session)
            return

        # find script or object to operate on
        scripts, obj = None, None
        if self.rhs:
            obj_query = self.lhs
            script_query = self.rhs
        else:
            obj_query = script_query = self.args

        scripts = self._search_script(script_query)
        objects = caller.search(obj_query, quiet=True)
        obj = objects[0] if objects else None

        if not self.switches:
            # creation / view mode
            if obj:
                # we have an object
                if self.rhs:
                    # creation mode
                    if obj.scripts.add(self.rhs, autostart=True):
                        caller.msg(
                            f"Script |w{self.rhs}|n successfully added and "
                            f"started on {obj.get_display_name(caller)}."
                        )
                    else:
                        caller.msg(
                            f"Script {self.rhs} could not be added and/or started "
                            f"on {obj.get_display_name(caller)} (or it started and "
                            "immediately shut down)."
                        )
                else:
                    # just show all scripts on object
                    scripts = ScriptDB.objects.filter(db_obj=obj).exclude(
                        db_typeclass_path__in=self.hide_script_paths
                    )
                    if scripts:
                        ScriptEvMore(caller, scripts.order_by("id"), session=self.session)
                    else:
                        caller.msg(f"No scripts defined on {obj}")

            elif scripts:
                # show found script(s)
                ScriptEvMore(caller, scripts.order_by("id"), session=self.session)

            else:
                # create global script
                try:
                    new_script = create.create_script(self.args)
                except ImportError:
                    logger.log_trace()
                    new_script = None

                if new_script:
                    caller.msg(
                        f"Global Script Created - {new_script.key} ({new_script.typeclass_path})"
                    )
                    ScriptEvMore(caller, [new_script], session=self.session)
                else:
                    caller.msg(
                        f"Global Script |rNOT|n Created |r(see log)|n - arguments: {self.args}"
                    )

        elif scripts or obj:
            # modification switches - must operate on existing scripts

            if not scripts:
                scripts = ScriptDB.objects.filter(db_obj=obj).exclude(
                    db_typeclass_path__in=self.hide_script_paths
                )

            if scripts.count() > 1:
                ret = yield (
                    f"Multiple scripts found: {scripts}. Are you sure you want to "
                    "operate on all of them? [Y]/N? "
                )
                if ret.lower() in ("n", "no"):
                    caller.msg("Aborted.")
                    return

            for script in scripts:
                script_key = script.key
                script_typeclass_path = script.typeclass_path
                scripttype = f"Script on {obj}" if obj else "Global Script"

                for switch in self.switches:
                    verb = self.switch_mapping[switch]
                    msgs = []
                    try:
                        getattr(script, switch)()
                    except Exception:
                        logger.log_trace()
                        msgs.append(
                            f"{scripttype} |rNOT|n {verb} |r(see log)|n - "
                            f"{script_key} ({script_typeclass_path})|n"
                        )
                    else:
                        msgs.append(f"{scripttype} {verb} - {script_key} ({script_typeclass_path})")
                caller.msg("\n".join(msgs))
                if "delete" not in self.switches:
                    if script and script.pk:
                        ScriptEvMore(caller, [script], session=self.session)
                    else:
                        caller.msg("Script was deleted automatically.")
        else:
            caller.msg("No scripts found.")


class CmdObjects(COMMAND_DEFAULT_CLASS):
    """
    statistics on objects in the database

    Usage:
      objects [<nr>]

    Gives statictics on objects in database as well as
    a list of <nr> latest objects in database. If not
    given, <nr> defaults to 10.
    """

    key = "@objects"
    locks = "cmd:perm(listobjects) or perm(Builder)"
    help_category = "System"

    def func(self):
        """Implement the command"""

        caller = self.caller
        nlim = int(self.args) if self.args and self.args.isdigit() else 10
        nobjs = ObjectDB.objects.count()
        Character = class_from_module(settings.BASE_CHARACTER_TYPECLASS)
        nchars = Character.objects.all_family().count()
        Room = class_from_module(settings.BASE_ROOM_TYPECLASS)
        nrooms = Room.objects.all_family().count()
        Exit = class_from_module(settings.BASE_EXIT_TYPECLASS)
        nexits = Exit.objects.all_family().count()
        nother = nobjs - nchars - nrooms - nexits
        nobjs = nobjs or 1  # fix zero-div error with empty database

        # total object sum table
        totaltable = self.styled_table(
            "|wtype|n", "|wcomment|n", "|wcount|n", "|w%|n", border="table", align="l"
        )
        totaltable.align = "l"
        totaltable.add_row(
            "Characters",
            "(BASE_CHARACTER_TYPECLASS + children)",
            nchars,
            "%.2f" % ((float(nchars) / nobjs) * 100),
        )
        totaltable.add_row(
            "Rooms",
            "(BASE_ROOM_TYPECLASS + children)",
            nrooms,
            "%.2f" % ((float(nrooms) / nobjs) * 100),
        )
        totaltable.add_row(
            "Exits",
            "(BASE_EXIT_TYPECLASS + children)",
            nexits,
            "%.2f" % ((float(nexits) / nobjs) * 100),
        )
        totaltable.add_row("Other", "", nother, "%.2f" % ((float(nother) / nobjs) * 100))

        # typeclass table
        typetable = self.styled_table(
            "|wtypeclass|n", "|wcount|n", "|w%|n", border="table", align="l"
        )
        typetable.align = "l"
        dbtotals = ObjectDB.objects.get_typeclass_totals()
        for stat in dbtotals:
            typetable.add_row(
                stat.get("typeclass", "<error>"),
                stat.get("count", -1),
                "%.2f" % stat.get("percent", -1),
            )

        # last N table
        objs = ObjectDB.objects.all().order_by("db_date_created")[max(0, nobjs - nlim) :]
        latesttable = self.styled_table(
            "|wcreated|n", "|wdbref|n", "|wname|n", "|wtypeclass|n", align="l", border="table"
        )
        latesttable.align = "l"
        for obj in objs:
            latesttable.add_row(
                utils.datetime_format(obj.date_created), obj.dbref, obj.key, obj.path
            )

        string = "\n|wObject subtype totals (out of %i Objects):|n\n%s" % (nobjs, totaltable)
        string += "\n|wObject typeclass distribution:|n\n%s" % typetable
        string += "\n|wLast %s Objects created:|n\n%s" % (min(nobjs, nlim), latesttable)
        caller.msg(string)


class CmdTeleport(COMMAND_DEFAULT_CLASS):
    """
    teleport object to another location

    Usage:
      tel/switch [<object> to||=] <target location>

    Examples:
      tel Limbo
      tel/quiet box = Limbo
      tel/tonone box

    Switches:
      quiet  - don't echo leave/arrive messages to the source/target
               locations for the move.
      intoexit - if target is an exit, teleport INTO
                 the exit object instead of to its destination
      tonone - if set, teleport the object to a None-location. If this
               switch is set, <target location> is ignored.
               Note that the only way to retrieve
               an object from a None location is by direct #dbref
               reference. A puppeted object cannot be moved to None.
      loc - teleport object to the target's location instead of its contents

    Teleports an object somewhere. If no object is given, you yourself are
    teleported to the target location.

    To lock an object from being teleported, set its `teleport` lock, it will be
    checked with the caller. To block
    a destination from being teleported to, set the destination's `teleport_here`
    lock - it will be checked with the thing being teleported. Admins and
    higher permissions can always teleport.

    """

    key = "@teleport"
    aliases = "@tel"
    switch_options = ("quiet", "intoexit", "tonone", "loc")
    rhs_split = ("=", " to ")  # Prefer = delimiter, but allow " to " usage.
    locks = "cmd:perm(teleport) or perm(Builder)"
    help_category = "Building"

    def parse(self):
        """
        Breaking out searching here to make this easier to override.

        """
        super().parse()
        self.obj_to_teleport = self.caller
        self.destination = None
        if self.rhs:
            self.obj_to_teleport = self.caller.search(self.lhs, global_search=True)
            if not self.obj_to_teleport:
                self.caller.msg("Did not find object to teleport.")
                raise InterruptCommand
            self.destination = self.caller.search(self.rhs, global_search=True)
        elif self.lhs:
            self.destination = self.caller.search(self.lhs, global_search=True)

    def func(self):
        """Performs the teleport"""

        caller = self.caller
        obj_to_teleport = self.obj_to_teleport
        destination = self.destination

        if "tonone" in self.switches:
            # teleporting to None

            if destination:
                # in this case lhs is always the object to teleport
                obj_to_teleport = destination

            if obj_to_teleport.has_account:
                caller.msg(
                    f"Cannot teleport a puppeted object ({obj_to_teleport.key}, puppeted by"
                    f" {obj_to_teleport.account}) to a None-location."
                )
                return
            caller.msg(f"Teleported {obj_to_teleport} -> None-location.")
            if obj_to_teleport.location and "quiet" not in self.switches:
                obj_to_teleport.location.msg_contents(
                    f"{caller} teleported {obj_to_teleport} into nothingness.", exclude=caller
                )
            obj_to_teleport.location = None
            return

        if not self.args:
            caller.msg("Usage: teleport[/switches] [<obj> =] <target or (X,Y,Z)>||home")
            return

        if not destination:
            caller.msg("Destination not found.")
            return

        if "loc" in self.switches:
            destination = destination.location
            if not destination:
                caller.msg("Destination has no location.")
                return

        if obj_to_teleport == destination:
            caller.msg("You can't teleport an object inside of itself!")
            return

        if obj_to_teleport == destination.location:
            caller.msg("You can't teleport an object inside something it holds!")
            return

        if obj_to_teleport.location and obj_to_teleport.location == destination:
            caller.msg(f"{obj_to_teleport} is already at {destination}.")
            return

        # check any locks
        if not (caller.permissions.check("Admin") or obj_to_teleport.access(caller, "teleport")):
            caller.msg(
                f"{obj_to_teleport} 'teleport'-lock blocks you from teleporting it anywhere."
            )
            return

        if not (
            caller.permissions.check("Admin")
            or destination.access(obj_to_teleport, "teleport_here")
        ):
            caller.msg(
                f"{destination} 'teleport_here'-lock blocks {obj_to_teleport} from moving there."
            )
            return

        # try the teleport
        if not obj_to_teleport.location:
            # teleporting from none-location
            obj_to_teleport.location = destination
            caller.msg(f"Teleported {obj_to_teleport} None -> {destination}")
        elif obj_to_teleport.move_to(
            destination,
            quiet="quiet" in self.switches,
            emit_to_obj=caller,
            use_destination="intoexit" not in self.switches,
            move_type="teleport",
        ):

            if obj_to_teleport == caller:
                caller.msg(f"Teleported to {destination}.")
            else:
                caller.msg(f"Teleported {obj_to_teleport} -> {destination}.")
        else:
            caller.msg("Teleportation failed.")


class CmdTag(COMMAND_DEFAULT_CLASS):
    """
    handles the tags of an object

    Usage:
      tag[/del] <obj> [= <tag>[:<category>]]
      tag/search <tag>[:<category]

    Switches:
      search - return all objects with a given Tag
      del - remove the given tag. If no tag is specified,
            clear all tags on object.

    Manipulates and lists tags on objects. Tags allow for quick
    grouping of and searching for objects.  If only <obj> is given,
    list all tags on the object.  If /search is used, list objects
    with the given tag.
    The category can be used for grouping tags themselves, but it
    should be used with restrain - tags on their own are usually
    enough to for most grouping schemes.
    """

    key = "@tag"
    aliases = ["@tags"]
    options = ("search", "del")
    locks = "cmd:perm(tag) or perm(Builder)"
    help_category = "Building"
    arg_regex = r"(/\w+?(\s|$))|\s|$"

    def func(self):
        """Implement the tag functionality"""

        if not self.args:
            self.caller.msg("Usage: tag[/switches] <obj> [= <tag>[:<category>]]")
            return
        if "search" in self.switches:
            # search by tag
            tag = self.args
            category = None
            if ":" in tag:
                tag, category = [part.strip() for part in tag.split(":", 1)]
            objs = search.search_tag(tag, category=category)
            nobjs = len(objs)
            if nobjs > 0:
                catstr = (
                    " (category: '|w%s|n')" % category
                    if category
                    else ("" if nobjs == 1 else " (may have different tag categories)")
                )
                matchstr = ", ".join(o.get_display_name(self.caller) for o in objs)

                string = "Found |w%i|n object%s with tag '|w%s|n'%s:\n %s" % (
                    nobjs,
                    "s" if nobjs > 1 else "",
                    tag,
                    catstr,
                    matchstr,
                )
            else:
                string = "No objects found with tag '%s%s'." % (
                    tag,
                    " (category: %s)" % category if category else "",
                )
            self.caller.msg(string)
            return
        if "del" in self.switches:
            # remove one or all tags
            obj = self.caller.search(self.lhs, global_search=True)
            if not obj:
                return
            if self.rhs:
                # remove individual tag
                tag = self.rhs
                category = None
                if ":" in tag:
                    tag, category = [part.strip() for part in tag.split(":", 1)]
                if obj.tags.get(tag, category=category):
                    obj.tags.remove(tag, category=category)
                    string = "Removed tag '%s'%s from %s." % (
                        tag,
                        " (category: %s)" % category if category else "",
                        obj,
                    )
                else:
                    string = "No tag '%s'%s to delete on %s." % (
                        tag,
                        " (category: %s)" % category if category else "",
                        obj,
                    )
            else:
                # no tag specified, clear all tags
                old_tags = [
                    "%s%s" % (tag, " (category: %s)" % category if category else "")
                    for tag, category in obj.tags.all(return_key_and_category=True)
                ]
                if old_tags:
                    obj.tags.clear()
                    string = "Cleared all tags from %s: %s" % (obj, ", ".join(sorted(old_tags)))
                else:
                    string = "No Tags to clear on %s." % obj
            self.caller.msg(string)
            return
        # no search/deletion
        if self.rhs:
            # = is found; command args are of the form obj = tag
            # first search locally, then global
            obj = self.caller.search(self.lhs, quiet=True)
            if not obj:
                obj = self.caller.search(self.lhs, global_search=True)
            else:
                obj = obj[0]
            if not obj:
                return
            tag = self.rhs
            category = None
            if ":" in tag:
                tag, category = [part.strip() for part in tag.split(":", 1)]
            # create the tag
            obj.tags.add(tag, category=category)
            string = "Added tag '%s'%s to %s." % (
                tag,
                " (category: %s)" % category if category else "",
                obj,
            )
            self.caller.msg(string)
        else:
            # no = found - list tags on object
            # first search locally, then global
            obj = self.caller.search(self.args, quiet=True)
            if not obj:
                obj = self.caller.search(self.args, global_search=True)
            else:
                obj = obj[0]
            if not obj:
                return
            tagtuples = obj.tags.all(return_key_and_category=True)
            ntags = len(tagtuples)
            tags = [tup[0] for tup in tagtuples]
            categories = [" (category: %s)" % tup[1] if tup[1] else "" for tup in tagtuples]
            if ntags:
                string = "Tag%s on %s: %s" % (
                    "s" if ntags > 1 else "",
                    obj,
                    ", ".join(sorted("'%s'%s" % (tags[i], categories[i]) for i in range(ntags))),
                )
            else:
                string = f"No tags attached to {obj}."
            self.caller.msg(string)


# helper functions for spawn


class CmdSpawn(COMMAND_DEFAULT_CLASS):
    """
    spawn objects from prototype

    Usage:
      spawn[/noloc] <prototype_key>
      spawn[/noloc] <prototype_dict>

      spawn/search [prototype_keykey][;tag[,tag]]
      spawn/list [tag, tag, ...]
      spawn/list modules    - list only module-based prototypes
      spawn/show [<prototype_key>]
      spawn/update <prototype_key>

      spawn/save <prototype_dict>
      spawn/edit [<prototype_key>]
      olc     - equivalent to spawn/edit

    Switches:
      noloc - allow location to be None if not specified explicitly. Otherwise,
              location will default to caller's current location.
      search - search prototype by name or tags.
      list - list available prototypes, optionally limit by tags.
      show, examine - inspect prototype by key. If not given, acts like list.
      raw - show the raw dict of the prototype as a one-line string for manual editing.
      save - save a prototype to the database. It will be listable by /list.
      delete - remove a prototype from database, if allowed to.
      update - find existing objects with the same prototype_key and update
               them with latest version of given prototype. If given with /save,
               will auto-update all objects with the old version of the prototype
               without asking first.
      edit, menu, olc - create/manipulate prototype in a menu interface.

    Example:
      spawn GOBLIN
      spawn {"key":"goblin", "typeclass":"monster.Monster", "location":"#2"}
      spawn/save {"key": "grunt", prototype: "goblin"};;mobs;edit:all()
    \f
    Dictionary keys:
      |wprototype_parent  |n - name of parent prototype to use. Required if typeclass is
                        not set. Can be a path or a list for multiple inheritance (inherits
                        left to right). If set one of the parents must have a typeclass.
      |wtypeclass  |n - string. Required if prototype_parent is not set.
      |wkey        |n - string, the main object identifier
      |wlocation   |n - this should be a valid object or #dbref
      |whome       |n - valid object or #dbref
      |wdestination|n - only valid for exits (object or dbref)
      |wpermissions|n - string or list of permission strings
      |wlocks      |n - a lock-string
      |waliases    |n - string or list of strings.
      |wndb_|n<name>  - value of a nattribute (ndb_ is stripped)

      |wprototype_key|n   - name of this prototype. Unique. Used to store/retrieve from db
                            and update existing prototyped objects if desired.
      |wprototype_desc|n  - desc of this prototype. Used in listings
      |wprototype_locks|n - locks of this prototype. Limits who may use prototype
      |wprototype_tags|n  - tags of this prototype. Used to find prototype

      any other keywords are interpreted as Attributes and their values.

    The available prototypes are defined globally in modules set in
    settings.PROTOTYPE_MODULES. If spawn is used without arguments it
    displays a list of available prototypes.

    """

    key = "@spawn"
    aliases = ["@olc"]
    switch_options = (
        "noloc",
        "search",
        "list",
        "show",
        "raw",
        "examine",
        "save",
        "delete",
        "menu",
        "olc",
        "update",
        "edit",
    )
    locks = "cmd:perm(spawn) or perm(Builder)"
    help_category = "Building"

    def _search_prototype(self, prototype_key, quiet=False):
        """
        Search for prototype and handle no/multi-match and access.

        Returns a single found prototype or None - in the
        case, the caller has already been informed of the
        search error we need not do any further action.

        """
        prototypes = protlib.search_prototype(prototype_key)
        nprots = len(prototypes)

        # handle the search result
        err = None
        if not prototypes:
            err = f"No prototype named '{prototype_key}' was found."
        elif nprots > 1:
            err = "Found {} prototypes matching '{}':\n  {}".format(
                nprots,
                prototype_key,
                ", ".join(proto.get("prototype_key", "") for proto in prototypes),
            )
        else:
            # we have a single prototype, check access
            prototype = prototypes[0]
            if not self.caller.locks.check_lockstring(
                self.caller, prototype.get("prototype_locks", ""), access_type="spawn", default=True
            ):
                err = "You don't have access to use this prototype."

        if err:
            # return None on any error
            if not quiet:
                self.caller.msg(err)
            return
        return prototype

    def _parse_prototype(self, inp, expect=dict):
        """
        Parse a prototype dict or key from the input and convert it safely
        into a dict if appropriate.

        Args:
            inp (str): The input from user.
            expect (type, optional):
        Returns:
            prototype (dict, str or None): The parsed prototype. If None, the error
                was already reported.

        """
        eval_err = None
        try:
            prototype = _LITERAL_EVAL(inp)
        except (SyntaxError, ValueError) as err:
            # treat as string
            eval_err = err
            prototype = utils.to_str(inp)
        finally:
            # it's possible that the input was a prototype-key, in which case
            # it's okay for the LITERAL_EVAL to fail. Only if the result does not
            # match the expected type do we have a problem.
            if not isinstance(prototype, expect):
                if eval_err:
                    string = (
                        f"{inp}\n{eval_err}\n|RCritical Python syntax error in argument. Only"
                        " primitive Python structures are allowed. \nMake sure to use correct"
                        " Python syntax. Remember especially to put quotes around all strings"
                        " inside lists and dicts.|n For more advanced uses, embed funcparser"
                        " callables ($funcs) in the strings."
                    )
                else:
                    string = f"Expected {expect}, got {type(prototype)}."
                self.caller.msg(string)
                return

        if expect == dict:
            # an actual prototype. We need to make sure it's safe,
            # so don't allow exec.
            # TODO: Exec support is deprecated. Remove completely for 1.0.
            if "exec" in prototype and not self.caller.check_permstring("Developer"):
                self.caller.msg(
                    "Spawn aborted: You are not allowed to use the 'exec' prototype key."
                )
                return
            try:
                # we homogenize the prototype first, to be more lenient with free-form
                protlib.validate_prototype(protlib.homogenize_prototype(prototype))
            except RuntimeError as err:
                self.caller.msg(str(err))
                return
        return prototype

    def _get_prototype_detail(self, query=None, prototypes=None):
        """
        Display the detailed specs of one or more prototypes.

        Args:
            query (str, optional): If this is given and `prototypes` is not, search for
                the prototype(s) by this query. This may be a partial query which
                may lead to multiple matches, all being displayed.
            prototypes (list, optional): If given, ignore `query` and only show these
                prototype-details.
        Returns:
            display (str, None): A formatted string of one or more prototype details.
                If None, the caller was already informed of the error.


        """
        if not prototypes:
            # we need to query. Note that if query is None, all prototypes will
            # be returned.
            prototypes = protlib.search_prototype(key=query)
        if prototypes:
            return "\n".join(protlib.prototype_to_str(prot) for prot in prototypes)
        elif query:
            self.caller.msg(f"No prototype named '{query}' was found.")
        else:
            self.caller.msg("No prototypes found.")

    def _list_prototypes(self, key=None, tags=None):
        """Display prototypes as a list, optionally limited by key/tags."""
        protlib.list_prototypes(self.caller, key=key, tags=tags, session=self.session)

    @interactive
    def _update_existing_objects(self, caller, prototype_key, quiet=False):
        """
        Update existing objects (if any) with this prototype-key to the latest
        prototype version.

        Args:
            caller (Object): This is necessary for @interactive to work.
            prototype_key (str): The prototype to update.
            quiet (bool, optional): If set, don't report to user if no
                old objects were found to update.
        Returns:
            n_updated (int): Number of updated objects.

        """
        prototype = self._search_prototype(prototype_key)
        if not prototype:
            return

        existing_objects = protlib.search_objects_with_prototype(prototype_key)
        if not existing_objects:
            if not quiet:
                caller.msg("No existing objects found with an older version of this prototype.")
            return

        if existing_objects:
            n_existing = len(existing_objects)
            slow = " (note that this may be slow)" if n_existing > 10 else ""
            string = (
                f"There are {n_existing} existing object(s) with an older version "
                f"of prototype '{prototype_key}'. Should it be re-applied to them{slow}? [Y]/N"
            )
            answer = yield (string)
            if answer.lower() in ["n", "no"]:
                caller.msg(
                    "|rNo update was done of existing objects. "
                    "Use spawn/update <key> to apply later as needed.|n"
                )
                return
            try:
                n_updated = spawner.batch_update_objects_with_prototype(
                    prototype,
                    objects=existing_objects,
                    caller=caller,
                )
            except Exception:
                logger.log_trace()
            caller.msg(f"{n_updated} objects were updated.")
        return

    def _parse_key_desc_tags(self, argstring, desc=True):
        """
        Parse ;-separated input list.
        """
        key, desc, tags = "", "", []
        if ";" in argstring:
            parts = [part.strip().lower() for part in argstring.split(";")]
            if len(parts) > 1 and desc:
                key = parts[0]
                desc = parts[1]
                tags = parts[2:]
            else:
                key = parts[0]
                tags = parts[1:]
        else:
            key = argstring.strip().lower()
        return key, desc, tags

    def func(self):
        """Implements the spawner"""

        caller = self.caller
        noloc = "noloc" in self.switches

        # run the menu/olc
        if (
            self.cmdstring == "olc"
            or "menu" in self.switches
            or "olc" in self.switches
            or "edit" in self.switches
        ):
            # OLC menu mode
            prototype = None
            if self.lhs:
                prototype_key = self.lhs
                prototype = self._search_prototype(prototype_key)
                if not prototype:
                    return
            olc_menus.start_olc(caller, session=self.session, prototype=prototype)
            return

        if "search" in self.switches:
            # query for a key match. The arg is a search query or nothing.

            if not self.args:
                # an empty search returns the full list
                self._list_prototypes()
                return

            # search for key;tag combinations
            key, _, tags = self._parse_key_desc_tags(self.args, desc=False)
            self._list_prototypes(key, tags)
            return

        if "raw" in self.switches:
            # query for key match and return the prototype as a safe one-liner string.
            if not self.args:
                caller.msg("You need to specify a prototype-key to get the raw data for.")
            prototype = self._search_prototype(self.args)
            if not prototype:
                return
            caller.msg(str(prototype))
            return

        if "show" in self.switches or "examine" in self.switches:
            # show a specific prot detail. The argument is a search query or empty.
            if not self.args:
                # we don't show the list of all details, that's too spammy.
                caller.msg("You need to specify a prototype-key to show.")
                return

            detail_string = self._get_prototype_detail(self.args)
            if not detail_string:
                return
            caller.msg(detail_string)
            return

        if "list" in self.switches:
            # for list, all optional arguments are tags.
            tags = self.lhslist
            err = self._list_prototypes(tags=tags)
            if err:
                caller.msg(
                    "No prototypes found with prototype-tag(s): {}".format(
                        list_to_string(tags, "or")
                    )
                )
            return

        if "save" in self.switches:
            # store a prototype to the database store
            if not self.args:
                caller.msg(
                    "Usage: spawn/save [<key>[;desc[;tag,tag[,...][;lockstring]]]] ="
                    " <prototype_dict>"
                )
                return
            if self.rhs:
                # input on the form key = prototype
                prototype_key, prototype_desc, prototype_tags = self._parse_key_desc_tags(self.lhs)
                prototype_key = None if not prototype_key else prototype_key
                prototype_desc = None if not prototype_desc else prototype_desc
                prototype_tags = None if not prototype_tags else prototype_tags
                prototype_input = self.rhs.strip()
            else:
                prototype_key = prototype_desc = None
                prototype_tags = None
                prototype_input = self.lhs.strip()

            # handle parsing
            prototype = self._parse_prototype(prototype_input)
            if not prototype:
                return

            prot_prototype_key = prototype.get("prototype_key")

            if not (prototype_key or prot_prototype_key):
                caller.msg(
                    "A prototype_key must be given, either as `prototype_key = <prototype>` "
                    "or as a key 'prototype_key' inside the prototype structure."
                )
                return

            if prototype_key is None:
                prototype_key = prot_prototype_key

            if prot_prototype_key != prototype_key:
                caller.msg("(Replacing `prototype_key` in prototype with given key.)")
                prototype["prototype_key"] = prototype_key

            if prototype_desc is not None and prot_prototype_key != prototype_desc:
                caller.msg("(Replacing `prototype_desc` in prototype with given desc.)")
                prototype["prototype_desc"] = prototype_desc
            if prototype_tags is not None and prototype.get("prototype_tags") != prototype_tags:
                caller.msg("(Replacing `prototype_tags` in prototype with given tag(s))")
                prototype["prototype_tags"] = prototype_tags

            string = ""
            # check for existing prototype (exact match)
            old_prototype = self._search_prototype(prototype_key, quiet=True)

            diff = spawner.prototype_diff(old_prototype, prototype, homogenize=True)
            diffstr = spawner.format_diff(diff)
            new_prototype_detail = self._get_prototype_detail(prototypes=[prototype])

            if old_prototype:
                if not diffstr:
                    string = f"|yAlready existing Prototype:|n\n{new_prototype_detail}\n"
                    question = (
                        "\nThere seems to be no changes. Do you still want to (re)save? [Y]/N"
                    )
                else:
                    string = (
                        f'|yExisting prototype "{prototype_key}" found. Change:|n\n{diffstr}\n'
                        f"|yNew changed prototype:|n\n{new_prototype_detail}"
                    )
                    question = (
                        "\n|yDo you want to apply the change to the existing prototype?|n [Y]/N"
                    )
            else:
                string = f"|yCreating new prototype:|n\n{new_prototype_detail}"
                question = "\nDo you want to continue saving? [Y]/N"

            answer = yield (string + question)
            if answer.lower() in ["n", "no"]:
                caller.msg("|rSave cancelled.|n")
                return

            # all seems ok. Try to save.
            try:
                prot = protlib.save_prototype(prototype)
                if not prot:
                    caller.msg("|rError saving:|R {}.|n".format(prototype_key))
                    return
            except protlib.PermissionError as err:
                caller.msg("|rError saving:|R {}|n".format(err))
                return
            caller.msg("|gSaved prototype:|n {}".format(prototype_key))

            # check if we want to update existing objects

            self._update_existing_objects(self.caller, prototype_key, quiet=True)
            return

        if not self.args:
            # all switches beyond this point gets a common non-arg return
            ncount = len(protlib.search_prototype())
            caller.msg(
                "Usage: spawn <prototype-key> or {{key: value, ...}}"
                f"\n ({ncount} existing prototypes. Use /list to inspect)"
            )
            return

        if "delete" in self.switches:
            # remove db-based prototype
            prototype_detail = self._get_prototype_detail(self.args)
            if not prototype_detail:
                return

            string = f"|rDeleting prototype:|n\n{prototype_detail}"
            question = "\nDo you want to continue deleting? [Y]/N"
            answer = yield (string + question)
            if answer.lower() in ["n", "no"]:
                caller.msg("|rDeletion cancelled.|n")
                return

            try:
                success = protlib.delete_prototype(self.args)
            except protlib.PermissionError as err:
                retmsg = f"|rError deleting:|R {err}|n"
            else:
                retmsg = (
                    "Deletion successful"
                    if success
                    else "Deletion failed (does the prototype exist?)"
                )
            caller.msg(retmsg)
            return

        if "update" in self.switches:
            # update existing prototypes
            prototype_key = self.args.strip().lower()
            self._update_existing_objects(self.caller, prototype_key)
            return

        # If we get to this point, we use not switches but are trying a
        # direct creation of an object from a given prototype or -key

        prototype = self._parse_prototype(
            self.args, expect=dict if self.args.strip().startswith("{") else str
        )
        if not prototype:
            # this will only let through dicts or strings
            return

        key = "<unnamed>"
        if isinstance(prototype, str):
            # A prototype key we are looking to apply
            prototype_key = prototype
            prototype = self._search_prototype(prototype_key)

            if not prototype:
                return

        # proceed to spawning
        try:
            for obj in spawner.spawn(prototype, caller=self.caller):
                self.caller.msg("Spawned %s." % obj.get_display_name(self.caller))
                if not prototype.get("location") and not noloc:
                    # we don't hardcode the location in the prototype (unless the user
                    # did so manually) - that would lead to it having to be 'removed' every
                    # time we try to update objects with this prototype in the future.
                    obj.location = caller.location
        except RuntimeError as err:
            caller.msg(err)
