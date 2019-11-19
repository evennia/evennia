"""
Building and world design commands
"""
import re
from django.conf import settings
from django.db.models import Q
from evennia.objects.models import ObjectDB
from evennia.locks.lockhandler import LockException
from evennia.commands.cmdhandler import get_and_merge_cmdsets
from evennia.utils import create, utils, search
from evennia.utils.utils import (
    inherits_from,
    class_from_module,
    get_all_typeclasses,
    variable_from_module,
)
from evennia.utils.eveditor import EvEditor
from evennia.utils.evmore import EvMore
from evennia.prototypes import spawner, prototypes as protlib, menus as olc_menus
from evennia.utils.ansi import raw

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

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
    "CmdScript",
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
                    attrs = [part.strip().lower() for part in attrs.split("/") if part.strip()]
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

    key = "alias"
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
                caller.msg("No aliases exist for '%s'." % obj.get_display_name(caller))
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
      copy[/reset] <original obj> [= <new_name>][;alias;alias..]
      [:<new_location>] [,<new_name2> ...]

    switch:
      reset - make a 'clean' copy off the object, thus
              removing any changes that might have been made to the original
              since it was first created.

    Create one or more copies of an object. If you don't supply any targets,
    one exact copy of the original object will be created with the name *_copy.
    """

    key = "copy"
    switch_options = ("reset",)
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
                    string = "Copied %s to '%s' (aliases: %s)." % (
                        from_obj_name,
                        to_obj_name,
                        to_obj_aliases,
                    )
                else:
                    string = "There was an error copying %s to '%s'." % (from_obj_name, to_obj_name)
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

    key = "cpattr"
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
            self.caller.msg("%s doesn't have an attribute %s." % (obj.name, attr))
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
                result.append("\nCould not find object '%s'" % to_obj_name)
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
                        "\nMoved %s.%s -> %s.%s. (value: %s)"
                        % (from_obj.name, from_attr, to_obj_name, to_attr, repr(value))
                    )
                else:
                    result.append(
                        "\nCopied %s.%s -> %s.%s. (value: %s)"
                        % (from_obj.name, from_attr, to_obj_name, to_attr, repr(value))
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

    key = "mvattr"
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

    key = "create"
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
                string = "You create a new %s: %s (aliases: %s)."
                string = string % (obj.typename, obj.name, ", ".join(aliases))
            else:
                string = "You create a new %s: %s."
                string = string % (obj.typename, obj.name)
            # set a default desc
            if not obj.db.desc:
                obj.db.desc = "You see nothing special."
            if "drop" in self.switches:
                if caller.location:
                    obj.home = caller.location
                    obj.move_to(caller.location, quiet=True)
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

    key = "desc"
    aliases = "describe"
    switch_options = ("edit",)
    locks = "cmd:perm(desc) or perm(Builder)"
    help_category = "Building"

    def edit_handler(self):
        if self.rhs:
            self.msg("|rYou may specify a value, or use the edit switch, " "but not both.|n")
            return
        if self.args:
            obj = self.caller.search(self.args)
        else:
            obj = self.caller.location or self.msg("|rYou can't describe oblivion.|n")
        if not obj:
            return

        if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
            self.caller.msg("You don't have permission to edit the description of %s." % obj.key)

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
            obj = caller.location or self.msg("|rYou can't describe oblivion.|n")
            if not obj:
                return
            desc = self.args
        if obj.access(self.caller, "control") or obj.access(self.caller, "edit"):
            obj.db.desc = desc
            caller.msg("The description was set on %s." % obj.get_display_name(caller))
        else:
            caller.msg("You don't have permission to edit the description of %s." % obj.key)


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

    key = "destroy"
    aliases = ["delete", "del"]
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
                string = "\nObject %s was already deleted." % obj.db_key
            else:
                objname = obj.name
                if not (obj.access(caller, "control") or obj.access(caller, "delete")):
                    return "\nYou don't have permission to delete %s." % objname
                if obj.account and "override" not in self.switches:
                    return (
                        "\nObject %s is controlled by an active account. Use /override to delete anyway."
                        % objname
                    )
                if obj.dbid == int(settings.DEFAULT_HOME.lstrip("#")):
                    return (
                        "\nYou are trying to delete |c%s|n, which is set as DEFAULT_HOME. "
                        "Re-point settings.DEFAULT_HOME to another "
                        "object before continuing." % objname
                    )

                had_exits = hasattr(obj, "exits") and obj.exits
                had_objs = hasattr(obj, "contents") and any(
                    obj
                    for obj in obj.contents
                    if not (hasattr(obj, "exits") and obj not in obj.exits)
                )
                # do the deletion
                okay = obj.delete()
                if not okay:
                    string += (
                        "\nERROR: %s not deleted, probably because delete() returned False."
                        % objname
                    )
                else:
                    string += "\n%s was destroyed." % objname
                    if had_exits:
                        string += " Exits to and from %s were destroyed as well." % objname
                    if had_objs:
                        string += " Objects inside %s were moved to their homes." % objname
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

    key = "dig"
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
            string = "Usage: dig[/teleport] <roomname>[;alias;alias...]" "[:parent] [= <exit_there>"
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
        room_string = "Created room %s(%s)%s of type %s." % (
            new_room,
            new_room.dbref,
            alias_string,
            typeclass,
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
                exit_to_string = "\nCreated Exit from %s to %s: %s(%s)%s."
                exit_to_string = exit_to_string % (
                    location.name,
                    new_room.name,
                    new_to_exit,
                    new_to_exit.dbref,
                    alias_string,
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
                exit_back_string = "\nCreated Exit back from %s to %s: %s(%s)%s."
                exit_back_string = exit_back_string % (
                    new_room.name,
                    location.name,
                    new_back_exit,
                    new_back_exit.dbref,
                    alias_string,
                )
        caller.msg("%s%s%s" % (room_string, exit_to_string, exit_back_string))
        if new_room and "teleport" in self.switches:
            caller.move_to(new_room)


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

    key = "tunnel"
    aliases = ["tun"]
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

        # if we recieved a typeclass for the exit, add it to the alias(short name)
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
            backstring = ", %s;%s" % (backname, backshort)

        # build the string we will use to call dig
        digstring = "dig%s %s = %s;%s%s" % (telswitch, roomname, exitname, exitshort, backstring)
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

    key = "link"
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
            note = "Note: %s(%s) did not have a destination set before. Make sure you linked the right thing."
            if not obj.destination:
                string = note % (obj.name, obj.dbref)
            if "twoway" in self.switches:
                if not (target.location and obj.location):
                    string = "To create a two-way link, %s and %s must both have a location" % (
                        obj,
                        target,
                    )
                    string += " (i.e. they cannot be rooms, but should be exits)."
                    self.caller.msg(string)
                    return
                if not target.destination:
                    string += note % (target.name, target.dbref)
                obj.destination = target.location
                target.destination = obj.location
                string += "\nLink created %s (in %s) <-> %s (in %s) (two-way)." % (
                    obj.name,
                    obj.location,
                    target.name,
                    target.location,
                )
            else:
                obj.destination = target
                string += "\nLink created %s -> %s (one way)." % (obj.name, target)

        elif self.rhs is None:
            # this means that no = was given (otherwise rhs
            # would have been an empty string). So we inspect
            # the home/destination on object
            dest = obj.destination
            if dest:
                string = "%s is an exit to %s." % (obj.name, dest.name)
            else:
                string = "%s is not an exit. Its home location is %s." % (obj.name, obj.home)

        else:
            # We gave the command link 'obj = ' which means we want to
            # clear destination.
            if obj.destination:
                obj.destination = None
                string = "Former exit %s no longer links anywhere." % obj.name
            else:
                string = "%s had no destination to unlink." % obj.name
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

    key = "sethome"
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
                string = "%s's current home is %s(%s)." % (obj, home, home.dbref)
        else:
            # set a home location
            new_home = self.caller.search(self.rhs, global_search=True)
            if not new_home:
                return
            old_home = obj.home
            obj.home = new_home
            if old_home:
                string = "Home location of %s was changed from %s(%s) to %s(%s)." % (
                    obj,
                    old_home,
                    old_home.dbref,
                    new_home,
                    new_home.dbref,
                )
            else:
                string = "Home location of %s was set to %s(%s)." % (obj, new_home, new_home.dbref)
        self.caller.msg(string)


class CmdListCmdSets(COMMAND_DEFAULT_CLASS):
    """
    list command sets defined on an object

    Usage:
      cmdsets <obj>

    This displays all cmdsets assigned
    to a user. Defaults to yourself.
    """

    key = "cmdsets"
    aliases = "listcmsets"
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
        string = "%s" % obj.cmdset
        caller.msg(string)


class CmdName(ObjManipCommand):
    """
    change the name and/or aliases of an object

    Usage:
      name <obj> = <newname>;alias1;alias2

    Rename an object to something new. Use *obj to
    rename an account.

    """

    key = "name"
    aliases = ["rename"]
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
                        caller.msg("You don't have right to edit this account %s." % obj)
                        return
                    obj.username = newname
                    obj.save()
                    caller.msg("Account's name changed to '%s'." % newname)
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
            caller.msg("You don't have the right to edit %s." % obj)
            return
        # change the name and set aliases:
        if newname:
            obj.name = newname
        astring = ""
        if aliases:
            [obj.aliases.add(alias) for alias in aliases]
            astring = " (%s)" % (", ".join(aliases))
        # fix for exits - we need their exit-command to change name too
        if obj.destination:
            obj.flush_from_cache(force=True)
        caller.msg("Object's name changed to '%s'%s." % (newname, astring))


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

    key = "open"
    locks = "cmd:perm(open) or perm(Builder)"
    help_category = "Building"

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
                string = "'%s' already exists and is not an exit!\nIf you want to convert it "
                string += (
                    "to an exit, you must assign an object to the 'destination' property first."
                )
                caller.msg(string % exit_name)
                return None
            # we are re-linking an old exit.
            old_destination = exit_obj.destination
            if old_destination:
                string = "Exit %s already exists." % exit_name
                if old_destination.id != destination.id:
                    # reroute the old exit.
                    exit_obj.destination = destination
                    if exit_aliases:
                        [exit_obj.aliases.add(alias) for alias in exit_aliases]
                    string += " Rerouted its old destination '%s' to '%s' and changed aliases." % (
                        old_destination.name,
                        destination.name,
                    )
                else:
                    string += " It already points to the correct place."

        else:
            # exit does not exist before. Create a new one.
            if not typeclass:
                typeclass = settings.BASE_EXIT_TYPECLASS
            exit_obj = create.create_object(
                typeclass, key=exit_name, location=location, aliases=exit_aliases, report_to=caller
            )
            if exit_obj:
                # storing a destination is what makes it an exit!
                exit_obj.destination = destination
                string = (
                    ""
                    if not exit_aliases
                    else " (aliases: %s)" % (", ".join([str(e) for e in exit_aliases]))
                )
                string = "Created new Exit '%s' from %s to %s%s." % (
                    exit_name,
                    location.name,
                    destination.name,
                    string,
                )
            else:
                string = "Error: Exit '%s' not created." % exit_name
        # emit results
        caller.msg(string)
        return exit_obj

    def func(self):
        """
        This is where the processing starts.
        Uses the ObjManipCommand.parser() for pre-processing
        as well as the self.create_exit() method.
        """
        caller = self.caller

        if not self.args or not self.rhs:
            string = "Usage: open <new exit>[;alias...][:typeclass][,<return exit>[;alias..][:typeclass]]] "
            string += "= <destination>"
            caller.msg(string)
            return

        # We must have a location to open an exit
        location = caller.location
        if not location:
            caller.msg("You cannot create an exit from a None-location.")
            return

        # obtain needed info from cmdline

        exit_name = self.lhs_objs[0]["name"]
        exit_aliases = self.lhs_objs[0]["aliases"]
        exit_typeclass = self.lhs_objs[0]["option"]
        dest_name = self.rhs

        # first, check so the destination exists.
        destination = caller.search(dest_name, global_search=True)
        if not destination:
            return

        # Create exit
        ok = self.create_exit(exit_name, location, destination, exit_aliases, exit_typeclass)
        if not ok:
            # an error; the exit was not created, so we quit.
            return
        # Create back exit, if any
        if len(self.lhs_objs) > 1:
            back_exit_name = self.lhs_objs[1]["name"]
            back_exit_aliases = self.lhs_objs[1]["aliases"]
            back_exit_typeclass = self.lhs_objs[1]["option"]
            self.create_exit(
                back_exit_name, destination, location, back_exit_aliases, back_exit_typeclass
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
            '|RNote: name "|r%s|R" was converted to a string. '
            "Make sure this is acceptable." % strobj
        )
        cmd.caller.msg(string)
        return strobj
    except Exception as err:
        string = "|RUnknown error in evaluating Attribute: {}".format(err)
        return string


class CmdSetAttribute(ObjManipCommand):
    """
    set attribute on an object or account

    Usage:
      set <obj>/<attr> = <value>
      set <obj>/<attr> =
      set <obj>/<attr>
      set *<account>/<attr> = <value>

    Switch:
        edit: Open the line editor (string values only)
        script: If we're trying to set an attribute on a script
        channel: If we're trying to set an attribute on a channel
        account: If we're trying to set an attribute on an account
        room: Setting an attribute on a room (global search)
        exit: Setting an attribute on an exit (global search)
        char: Setting an attribute on a character (global search)
        character: Alias for char, as above.

    Sets attributes on objects. The second example form above clears a
    previously set attribute while the third form inspects the current value of
    the attribute (if any). The last one (with the star) is a shortcut for
    operating on a player Account rather than an Object.

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

    key = "set"
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

    def check_attr(self, obj, attr_name):
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
        For performance, this is biased to the deepest match, but allows compatability
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

    def view_attr(self, obj, attr):
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
                    return "\nAttribute %s/%s = %s" % (obj.name, attr, val)
        error = "\n%s has no attribute '%s'." % (obj.name, attr)
        if nested:
            error += " (Nested lookups attempted)"
        return error

    def rm_attr(self, obj, attr):
        """
        Remove an attribute from the object, or a nested data structure, and report back.
        """
        nested = False
        for key, nested_keys in self.split_nested_attr(attr):
            nested = True
            if obj.attributes.has(key):
                if nested_keys:
                    del_key = nested_keys[-1]
                    val = obj.attributes.get(key)
                    deep = self.do_nested_lookup(val, *nested_keys[:-1])
                    if deep is not self.not_found:
                        try:
                            del deep[del_key]
                        except (IndexError, KeyError, TypeError):
                            continue
                    return "\nDeleted attribute '%s' (= nested) from %s." % (attr, obj.name)
                else:
                    exists = obj.attributes.has(key)
                    obj.attributes.remove(attr)
                    return "\nDeleted attribute '%s' (= %s) from %s." % (attr, exists, obj.name)
        error = "\n%s has no attribute '%s'." % (obj.name, attr)
        if nested:
            error += " (Nested lookups attempted)"
        return error

    def set_attr(self, obj, attr, value):
        done = False
        for key, nested_keys in self.split_nested_attr(attr):
            if obj.attributes.has(key) and nested_keys:
                acc_key = nested_keys[-1]
                lookup_value = obj.attributes.get(key)
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
                        return "\n%s - %s" % (err, deep)

                    value = lookup_value
                    attr = key
                    done = True
                    break

        verb = "Modified" if obj.attributes.has(attr) else "Created"
        try:
            if not done:
                obj.attributes.add(attr, value)
            return "\n%s attribute %s/%s = %s" % (verb, obj.name, attr, repr(value))
        except SyntaxError:
            # this means literal_eval tried to parse a faulty string
            return (
                "\n|RCritical Python syntax error in your value. Only "
                "primitive Python structures are allowed.\nYou also "
                "need to use correct Python syntax. Remember especially "
                "to put quotes around all strings inside lists and "
                "dicts.|n"
            )

    def edit_handler(self, obj, attr):
        """Activate the line editor"""

        def load(caller):
            """Called for the editor to load the buffer"""
            old_value = obj.attributes.get(attr)
            if old_value is not None and not isinstance(old_value, str):
                typ = type(old_value).__name__
                self.caller.msg(
                    "|RWARNING! Saving this buffer will overwrite the "
                    "current attribute (of type %s) with a string!|n" % typ
                )
                return str(old_value)
            return old_value

        def save(caller, buf):
            """Called when editor saves its buffer."""
            obj.attributes.add(attr, buf)
            caller.msg("Saved Attribute %s." % attr)

        # start the editor
        EvEditor(self.caller, load, save, key="%s/%s" % (obj, attr))

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
            caller.msg("Usage: set obj/attr = value. Use empty value to clear.")
            return

        # get values prepared by the parser
        value = self.rhs
        objname = self.lhs_objattr[0]["name"]
        attrs = self.lhs_objattr[0]["attrs"]

        obj = self.search_for_obj(objname)
        if not obj:
            return

        if not self.check_obj(obj):
            return

        result = []
        if "edit" in self.switches:
            # edit in the line editor
            if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                caller.msg("You don't have permission to edit %s." % obj.key)
                return

            if len(attrs) > 1:
                caller.msg("The Line editor can only be applied " "to one attribute at a time.")
                return
            self.edit_handler(obj, attrs[0])
            return
        if not value:
            if self.rhs is None:
                # no = means we inspect the attribute(s)
                if not attrs:
                    attrs = [attr.key for attr in obj.attributes.all()]
                for attr in attrs:
                    if not self.check_attr(obj, attr):
                        continue
                    result.append(self.view_attr(obj, attr))
                # we view it without parsing markup.
                self.caller.msg("".join(result).strip(), options={"raw": True})
                return
            else:
                # deleting the attribute(s)
                if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                    caller.msg("You don't have permission to edit %s." % obj.key)
                    return
                for attr in attrs:
                    if not self.check_attr(obj, attr):
                        continue
                    result.append(self.rm_attr(obj, attr))
        else:
            # setting attribute(s). Make sure to convert to real Python type before saving.
            if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
                caller.msg("You don't have permission to edit %s." % obj.key)
                return
            for attr in attrs:
                if not self.check_attr(obj, attr):
                    continue
                value = _convert_from_string(self, value)
                result.append(self.set_attr(obj, attr, value))
        # send feedback
        caller.msg("".join(result).strip("\n"))


class CmdTypeclass(COMMAND_DEFAULT_CLASS):
    """
    set or change an object's typeclass

    Usage:
      typeclass[/switch] <object> [= typeclass.path]
      type                     ''
      parent                   ''
      typeclass/list/show [typeclass.path]
      swap - this is a shorthand for using /force/reset flags.
      update - this is a shorthand for using the /force/reload flag.

    Switch:
      show, examine - display the current typeclass of object (default) or, if
            given a typeclass path, show the docstring of that typeclass.
      update - *only* re-run at_object_creation on this object
              meaning locks or other properties set later may remain.
      reset - clean out *all* the attributes and properties on the
              object - basically making this a new clean object.
      force - change to the typeclass also if the object
              already has a typeclass of the same name.
      list - show available typeclasses. Only typeclasses in modules actually
             imported or used from somewhere in the code will show up here
             (those typeclasses are still available if you know the path)

    Example:
      type button = examples.red_button.RedButton

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

    key = "typeclass"
    aliases = ["type", "parent", "swap", "update"]
    switch_options = ("show", "examine", "update", "reset", "force", "list")
    locks = "cmd:perm(typeclass) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Implements command"""

        caller = self.caller

        if "list" in self.switches:
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
                    caller.msg("No object or typeclass path found to match '{}'".format(oquery))
                else:
                    # one match found
                    caller.msg(
                        "Docstring for typeclass '{}':\n{}".format(oquery, matches[0][1].__doc__)
                    )
            else:
                # do the search again to get the error handling in case of multi-match
                obj = caller.search(oquery)
                if not obj:
                    return
                caller.msg(
                    "{}'s current typeclass is '{}.{}'".format(
                        obj.name, obj.__class__.__module__, obj.__class__.__name__
                    )
                )
            return

        # get object to swap on
        obj = caller.search(self.lhs)
        if not obj:
            return

        if not hasattr(obj, "__dbclass__"):
            string = "%s is not a typed object." % obj.name
            caller.msg(string)
            return

        new_typeclass = self.rhs or obj.path

        if "show" in self.switches or "examine" in self.switches:
            string = "%s's current typeclass is %s." % (obj.name, obj.__class__)
            caller.msg(string)
            return

        if self.cmdstring == "swap":
            self.switches.append("force")
            self.switches.append("reset")
        elif self.cmdstring == "update":
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
            string = "%s already has the typeclass '%s'. Use /force to override." % (
                obj.name,
                new_typeclass,
            )
        else:
            update = "update" in self.switches
            reset = "reset" in self.switches
            hooks = "at_object_creation" if update else "all"
            old_typeclass_path = obj.typeclass_path

            # we let this raise exception if needed
            obj.swap_typeclass(
                new_typeclass, clean_attributes=reset, clean_cmdsets=reset, run_start_hooks=hooks
            )

            if is_same:
                string = "%s updated its existing typeclass (%s).\n" % (obj.name, obj.path)
            else:
                string = "%s changed typeclass from %s to %s.\n" % (
                    obj.name,
                    old_typeclass_path,
                    obj.typeclass_path,
                )
            if update:
                string += "Only the at_object_creation hook was run (update mode)."
            else:
                string += "All object creation hooks were run."
            if reset:
                string += " All old attributes where deleted before the swap."
            else:
                string += " Attributes set before swap were not removed."

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

    key = "wipe"
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
            string = "Wiped all attributes on %s." % obj.name
        else:
            for attrname in attrs:
                obj.attributes.remove(attrname)
            string = "Wiped attributes %s on %s."
            string = string % (",".join(attrs), obj.name)
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

    key = "lock"
    aliases = ["locks"]
    locks = "cmd: perm(locks) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Sets up the command"""

        caller = self.caller
        if not self.args:
            string = (
                "Usage: lock <object>[ = <lockstring>] or lock[/switch] " "<object>/<access_type>"
            )
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
                string = "%s has no lock of access type '%s'." % (obj, access_type)
            caller.msg(string)
            return

        if self.rhs:
            # we have a = separator, so we are assigning a new lock
            if self.switches:
                swi = ", ".join(self.switches)
                caller.msg(
                    "Switch(es) |w%s|n can not be used with a "
                    "lock assignment. Use e.g. "
                    "|wlock/del objname/locktype|n instead." % swi
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
                caller.msg("Added lock '%s' to %s." % (lockdef, obj))
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

    The examine command shows detailed game info about an
    object and optionally a specific attribute on it.
    If object is not specified, the current location is examined.

    Append a * before the search string to examine an account.

    """

    key = "examine"
    aliases = ["ex", "exam"]
    locks = "cmd:perm(examine) or perm(Builder)"
    help_category = "Building"
    arg_regex = r"(/\w+?(\s|$))|\s|$"

    account_mode = False

    def list_attribute(self, crop, attr, category, value):
        """
        Formats a single attribute line.
        """
        if crop:
            if not isinstance(value, str):
                value = utils.to_str(value)
            value = utils.crop(value)
        if category:
            string = "\n %s[%s] = %s" % (attr, category, value)
        else:
            string = "\n %s = %s" % (attr, value)
        string = raw(string)
        return string

    def format_attributes(self, obj, attrname=None, crop=True):
        """
        Helper function that returns info about attributes and/or
        non-persistent data stored on object
        """

        if attrname:
            db_attr = [(attrname, obj.attributes.get(attrname), None)]
            try:
                ndb_attr = [(attrname, object.__getattribute__(obj.ndb, attrname))]
            except Exception:
                ndb_attr = None
        else:
            db_attr = [(attr.key, attr.value, attr.category) for attr in obj.db_attributes.all()]
            try:
                ndb_attr = obj.nattributes.all(return_tuples=True)
            except Exception:
                ndb_attr = None
        string = ""
        if db_attr and db_attr[0]:
            string += "\n|wPersistent attributes|n:"
            for attr, value, category in db_attr:
                string += self.list_attribute(crop, attr, category, value)
        if ndb_attr and ndb_attr[0]:
            string += "\n|wNon-Persistent attributes|n:"
            for attr, value in ndb_attr:
                string += self.list_attribute(crop, attr, None, value)
        return string

    def format_output(self, obj, avail_cmdset):
        """
        Helper function that creates a nice report about an object.

        returns a string.
        """
        string = "\n|wName/key|n: |c%s|n (%s)" % (obj.name, obj.dbref)
        if hasattr(obj, "aliases") and obj.aliases.all():
            string += "\n|wAliases|n: %s" % (", ".join(utils.make_iter(str(obj.aliases))))
        if hasattr(obj, "sessions") and obj.sessions.all():
            string += "\n|wSession id(s)|n: %s" % (
                ", ".join("#%i" % sess.sessid for sess in obj.sessions.all())
            )
        if hasattr(obj, "email") and obj.email:
            string += "\n|wEmail|n: |c%s|n" % obj.email
        if hasattr(obj, "has_account") and obj.has_account:
            string += "\n|wAccount|n: |c%s|n" % obj.account.name
            perms = obj.account.permissions.all()
            if obj.account.is_superuser:
                perms = ["<Superuser>"]
            elif not perms:
                perms = ["<None>"]
            string += "\n|wAccount Perms|n: %s" % (", ".join(perms))
            if obj.account.attributes.has("_quell"):
                string += " |r(quelled)|n"
        string += "\n|wTypeclass|n: %s (%s)" % (obj.typename, obj.typeclass_path)
        if hasattr(obj, "location"):
            string += "\n|wLocation|n: %s" % obj.location
            if obj.location:
                string += " (#%s)" % obj.location.id
        if hasattr(obj, "home"):
            string += "\n|wHome|n: %s" % obj.home
            if obj.home:
                string += " (#%s)" % obj.home.id
        if hasattr(obj, "destination") and obj.destination:
            string += "\n|wDestination|n: %s" % obj.destination
            if obj.destination:
                string += " (#%s)" % obj.destination.id
        perms = obj.permissions.all()
        if perms:
            perms_string = ", ".join(perms)
        else:
            perms_string = "<None>"
        if obj.is_superuser:
            perms_string += " [Superuser]"

        string += "\n|wPermissions|n: %s" % perms_string

        locks = str(obj.locks)
        if locks:
            locks_string = utils.fill("; ".join([lock for lock in locks.split(";")]), indent=6)
        else:
            locks_string = " Default"
        string += "\n|wLocks|n:%s" % locks_string

        if not (len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "_EMPTY_CMDSET"):
            # all() returns a 'stack', so make a copy to sort.
            stored_cmdsets = sorted(obj.cmdset.all(), key=lambda x: x.priority, reverse=True)
            string += "\n|wStored Cmdset(s)|n:\n %s" % (
                "\n ".join(
                    "%s [%s] (%s, prio %s)"
                    % (cmdset.path, cmdset.key, cmdset.mergetype, cmdset.priority)
                    for cmdset in stored_cmdsets
                    if cmdset.key != "_EMPTY_CMDSET"
                )
            )

            # this gets all components of the currently merged set
            all_cmdsets = [(cmdset.key, cmdset) for cmdset in avail_cmdset.merged_from]
            # we always at least try to add account- and session sets since these are ignored
            # if we merge on the object level.
            if hasattr(obj, "account") and obj.account:
                all_cmdsets.extend([(cmdset.key, cmdset) for cmdset in obj.account.cmdset.all()])
                if obj.sessions.count():
                    # if there are more sessions than one on objects it's because of multisession mode 3.
                    # we only show the first session's cmdset here (it is -in principle- possible that
                    # different sessions have different cmdsets but for admins who want such madness
                    # it is better that they overload with their own CmdExamine to handle it).
                    all_cmdsets.extend(
                        [
                            (cmdset.key, cmdset)
                            for cmdset in obj.account.sessions.all()[0].cmdset.all()
                        ]
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
            string += "\n|wMerged Cmdset(s)|n:\n %s" % (
                "\n ".join(
                    "%s [%s] (%s, prio %s)"
                    % (cmdset.path, cmdset.key, cmdset.mergetype, cmdset.priority)
                    for cmdset in all_cmdsets
                )
            )

            # list the commands available to this object
            avail_cmdset = sorted([cmd.key for cmd in avail_cmdset if cmd.access(obj, "cmd")])

            cmdsetstr = utils.fill(", ".join(avail_cmdset), indent=2)
            string += "\n|wCommands available to %s (result of Merged CmdSets)|n:\n %s" % (
                obj.key,
                cmdsetstr,
            )

        if hasattr(obj, "scripts") and hasattr(obj.scripts, "all") and obj.scripts.all():
            string += "\n|wScripts|n:\n %s" % obj.scripts
        # add the attributes
        string += self.format_attributes(obj)

        # display Tags
        tags_string = utils.fill(
            ", ".join(
                "%s[%s]" % (tag, category)
                for tag, category in obj.tags.all(return_key_and_category=True)
            ),
            indent=5,
        )
        if tags_string:
            string += "\n|wTags[category]|n: %s" % tags_string.strip()

        # add the contents
        exits = []
        pobjs = []
        things = []
        if hasattr(obj, "contents"):
            for content in obj.contents:
                if content.destination:
                    exits.append(content)
                elif content.account:
                    pobjs.append(content)
                else:
                    things.append(content)
            if exits:
                string += "\n|wExits|n: %s" % ", ".join(
                    ["%s(%s)" % (exit.name, exit.dbref) for exit in exits]
                )
            if pobjs:
                string += "\n|wCharacters|n: %s" % ", ".join(
                    ["|c%s|n(%s)" % (pobj.name, pobj.dbref) for pobj in pobjs]
                )
            if things:
                string += "\n|wContents|n: %s" % ", ".join(
                    [
                        "%s(%s)" % (cont.name, cont.dbref)
                        for cont in obj.contents
                        if cont not in exits and cont not in pobjs
                    ]
                )
        separator = "-" * _DEFAULT_WIDTH
        # output info
        return "%s\n%s\n%s" % (separator, string.strip(), separator)

    def func(self):
        """Process command"""
        caller = self.caller

        def get_cmdset_callback(cmdset):
            """
            We make use of the cmdhandeler.get_and_merge_cmdsets below. This
            is an asynchronous function, returning a Twisted deferred.
            So in order to properly use this we need use this callback;
            it is called with the result of get_and_merge_cmdsets, whenever
            that function finishes. Taking the resulting cmdset, we continue
            to format and output the result.
            """
            string = self.format_output(obj, cmdset)
            self.msg(string.strip())

        if not self.args:
            # If no arguments are provided, examine the invoker's location.
            if hasattr(caller, "location"):
                obj = caller.location
                if not obj.access(caller, "examine"):
                    # If we don't have special info access, just look at the object instead.
                    self.msg(caller.at_look(obj))
                    return
                obj_session = obj.sessions.get()[0] if obj.sessions.count() else None

                # using callback for printing result whenever function returns.
                get_and_merge_cmdsets(
                    obj, obj_session, self.account, obj, "object", self.raw_string
                ).addCallback(get_cmdset_callback)
            else:
                self.msg("You need to supply a target to examine.")
            return

        # we have given a specific target object
        for objdef in self.lhs_objattr:

            obj = None
            obj_name = objdef["name"]
            obj_attrs = objdef["attrs"]

            self.account_mode = (
                utils.inherits_from(caller, "evennia.accounts.accounts.DefaultAccount")
                or "account" in self.switches
                or obj_name.startswith("*")
            )
            if self.account_mode:
                try:
                    obj = caller.search_account(obj_name.lstrip("*"))
                except AttributeError:
                    # this means we are calling examine from an account object
                    obj = caller.search(
                        obj_name.lstrip("*"), search_object="object" in self.switches
                    )
            else:
                obj = caller.search(obj_name)
            if not obj:
                continue

            if not obj.access(caller, "examine"):
                # If we don't have special info access, just look
                # at the object instead.
                self.msg(caller.at_look(obj))
                continue

            if obj_attrs:
                for attrname in obj_attrs:
                    # we are only interested in specific attributes
                    caller.msg(self.format_attributes(obj, attrname, crop=False))
            else:
                session = None
                if obj.sessions.count():
                    mergemode = "session"
                    session = obj.sessions.get()[0]
                elif self.account_mode:
                    mergemode = "account"
                else:
                    mergemode = "object"

                account = None
                objct = None
                if self.account_mode:
                    account = obj
                else:
                    account = obj.account
                    objct = obj

                # using callback to print results whenever function returns.
                get_and_merge_cmdsets(
                    obj, session, account, objct, mergemode, self.raw_string
                ).addCallback(get_cmdset_callback)


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

    key = "find"
    aliases = "search, locate"
    switch_options = ("room", "exit", "char", "exact", "loc", "startswith")
    locks = "cmd:perm(find) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Search functionality"""
        caller = self.caller
        switches = self.switches

        if not self.args:
            caller.msg("Usage: find <string> [= low [-high]]")
            return

        if "locate" in self.cmdstring:  # Use option /loc as a default for locate command alias
            switches.append("loc")

        searchstring = self.lhs
        low, high = 1, ObjectDB.objects.all().order_by("-id")[0].id
        if self.rhs:
            if "-" in self.rhs:
                # also support low-high syntax
                limlist = [part.lstrip("#").strip() for part in self.rhs.split("-", 1)]
            else:
                # otherwise split by space
                limlist = [part.lstrip("#") for part in self.rhs.split(None, 1)]
            if limlist and limlist[0].isdigit():
                low = max(low, int(limlist[0]))
            if len(limlist) > 1 and limlist[1].isdigit():
                high = min(high, int(limlist[1]))
        low = min(low, high)
        high = max(low, high)

        is_dbref = utils.dbref(searchstring)
        is_account = searchstring.startswith("*")

        restrictions = ""
        if self.switches:
            restrictions = ", %s" % (", ".join(self.switches))

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
                string += "\n   |RNo match found for '%s' in #dbref interval.|n" % searchstring
            else:
                result = result[0]
                string += "\n|g   %s - %s|n" % (result.get_display_name(caller), result.path)
                if "loc" in self.switches and not is_account and result.location:
                    string += " (|wlocation|n: |g{}|n)".format(
                        result.location.get_display_name(caller)
                    )
        else:
            # Not an account/dbref search but a wider search; build a queryset.
            # Searchs for key and aliases
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

            results = ObjectDB.objects.filter(keyquery | aliasquery).distinct()
            nresults = results.count()

            if nresults:
                # convert result to typeclasses.
                results = [result for result in results]
                if "room" in switches:
                    results = [obj for obj in results if inherits_from(obj, ROOM_TYPECLASS)]
                if "exit" in switches:
                    results = [obj for obj in results if inherits_from(obj, EXIT_TYPECLASS)]
                if "char" in switches:
                    results = [obj for obj in results if inherits_from(obj, CHAR_TYPECLASS)]
                nresults = len(results)

            # still results after type filtering?
            if nresults:
                if nresults > 1:
                    string = "|w%i Matches|n(#%i-#%i%s):" % (nresults, low, high, restrictions)
                    for res in results:
                        string += "\n   |g%s - %s|n" % (res.get_display_name(caller), res.path)
                else:
                    string = "|wOne Match|n(#%i-#%i%s):" % (low, high, restrictions)
                    string += "\n   |g%s - %s|n" % (
                        results[0].get_display_name(caller),
                        results[0].path,
                    )
                    if "loc" in self.switches and nresults == 1 and results[0].location:
                        string += " (|wlocation|n: |g{}|n)".format(
                            results[0].location.get_display_name(caller)
                        )
            else:
                string = "|wMatch|n(#%i-#%i%s):" % (low, high, restrictions)
                string += "\n   |RNo matches found for '%s'|n" % searchstring

        # send result
        caller.msg(string.strip())


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

    Teleports an object somewhere. If no object is given, you yourself
    is teleported to the target location.
    """

    key = "tel"
    aliases = "teleport"
    switch_options = ("quiet", "intoexit", "tonone", "loc")
    rhs_split = ("=", " to ")  # Prefer = delimiter, but allow " to " usage.
    locks = "cmd:perm(teleport) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Performs the teleport"""

        caller = self.caller
        args = self.args
        lhs, rhs = self.lhs, self.rhs
        switches = self.switches

        # setting switches
        tel_quietly = "quiet" in switches
        to_none = "tonone" in switches
        to_loc = "loc" in switches

        if to_none:
            # teleporting to None
            if not args:
                obj_to_teleport = caller
            else:
                obj_to_teleport = caller.search(lhs, global_search=True)
                if not obj_to_teleport:
                    caller.msg("Did not find object to teleport.")
                    return
            if obj_to_teleport.has_account:
                caller.msg(
                    "Cannot teleport a puppeted object "
                    "(%s, puppeted by %s) to a None-location."
                    % (obj_to_teleport.key, obj_to_teleport.account)
                )
                return
            caller.msg("Teleported %s -> None-location." % obj_to_teleport)
            if obj_to_teleport.location and not tel_quietly:
                obj_to_teleport.location.msg_contents(
                    "%s teleported %s into nothingness." % (caller, obj_to_teleport), exclude=caller
                )
            obj_to_teleport.location = None
            return

        # not teleporting to None location
        if not args and not to_none:
            caller.msg("Usage: teleport[/switches] [<obj> =] <target_loc>||home")
            return

        if rhs:
            obj_to_teleport = caller.search(lhs, global_search=True)
            destination = caller.search(rhs, global_search=True)
        else:
            obj_to_teleport = caller
            destination = caller.search(lhs, global_search=True)
        if not obj_to_teleport:
            caller.msg("Did not find object to teleport.")
            return

        if not destination:
            caller.msg("Destination not found.")
            return
        if to_loc:
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
            caller.msg("%s is already at %s." % (obj_to_teleport, destination))
            return
        use_destination = True
        if "intoexit" in self.switches:
            use_destination = False

        # try the teleport
        if obj_to_teleport.move_to(
            destination, quiet=tel_quietly, emit_to_obj=caller, use_destination=use_destination
        ):
            if obj_to_teleport == caller:
                caller.msg("Teleported to %s." % destination)
            else:
                caller.msg("Teleported %s -> %s." % (obj_to_teleport, destination))


class CmdScript(COMMAND_DEFAULT_CLASS):
    """
    attach a script to an object

    Usage:
      script[/switch] <obj> [= script_path or <scriptkey>]

    Switches:
      start - start all non-running scripts on object, or a given script only
      stop - stop all scripts on objects, or a given script only

    If no script path/key is given, lists all scripts active on the given
    object.
    Script path can be given from the base location for scripts as given in
    settings. If adding a new script, it will be started automatically
    (no /start switch is needed). Using the /start or /stop switches on an
    object without specifying a script key/path will start/stop ALL scripts on
    the object.
    """

    key = "script"
    aliases = "addscript"
    switch_options = ("start", "stop")
    locks = "cmd:perm(script) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """Do stuff"""

        caller = self.caller

        if not self.args:
            string = "Usage: script[/switch] <obj> [= script_path or <script key>]"
            caller.msg(string)
            return

        if not self.lhs:
            caller.msg("To create a global script you need |wscripts/add <typeclass>|n.")
            return

        obj = caller.search(self.lhs)
        if not obj:
            return

        result = []
        if not self.rhs:
            # no rhs means we want to operate on all scripts
            scripts = obj.scripts.all()
            if not scripts:
                result.append("No scripts defined on %s." % obj.get_display_name(caller))
            elif not self.switches:
                # view all scripts
                from evennia.commands.default.system import format_script_list

                result.append(format_script_list(scripts))
            elif "start" in self.switches:
                num = sum([obj.scripts.start(script.key) for script in scripts])
                result.append("%s scripts started on %s." % (num, obj.get_display_name(caller)))
            elif "stop" in self.switches:
                for script in scripts:
                    result.append(
                        "Stopping script %s on %s."
                        % (script.get_display_name(caller), obj.get_display_name(caller))
                    )
                    script.stop()
            obj.scripts.validate()
        else:  # rhs exists
            if not self.switches:
                # adding a new script, and starting it
                ok = obj.scripts.add(self.rhs, autostart=True)
                if not ok:
                    result.append(
                        "\nScript %s could not be added and/or started on %s."
                        % (self.rhs, obj.get_display_name(caller))
                    )
                else:
                    result.append(
                        "Script |w%s|n successfully added and started on %s."
                        % (self.rhs, obj.get_display_name(caller))
                    )

            else:
                paths = [self.rhs] + [
                    "%s.%s" % (prefix, self.rhs) for prefix in settings.TYPECLASS_PATHS
                ]
                if "stop" in self.switches:
                    # we are stopping an already existing script
                    for path in paths:
                        ok = obj.scripts.stop(path)
                        if not ok:
                            result.append("\nScript %s could not be stopped. Does it exist?" % path)
                        else:
                            result = ["Script stopped and removed from object."]
                            break
                if "start" in self.switches:
                    # we are starting an already existing script
                    for path in paths:
                        ok = obj.scripts.start(path)
                        if not ok:
                            result.append("\nScript %s could not be (re)started." % path)
                        else:
                            result = ["Script started successfully."]
                            break
        caller.msg("".join(result).strip())


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

    key = "tag"
    aliases = ["tags"]
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
            obj = self.caller.search(self.lhs, global_search=True)
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
            obj = self.caller.search(self.args, global_search=True)
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
                string = "No tags attached to %s." % obj
            self.caller.msg(string)


class CmdSpawn(COMMAND_DEFAULT_CLASS):
    """
    spawn objects from prototype

    Usage:
      spawn[/noloc] <prototype_key>
      spawn[/noloc] <prototype_dict>

      spawn/search [prototype_keykey][;tag[,tag]]
      spawn/list [tag, tag, ...]
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
      save - save a prototype to the database. It will be listable by /list.
      delete - remove a prototype from database, if allowed to.
      update - find existing objects with the same prototype_key and update
               them with latest version of given prototype. If given with /save,
               will auto-update all objects with the old version of the prototype
               without asking first.
      edit, olc - create/manipulate prototype in a menu interface.

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

    key = "spawn"
    aliases = ["olc"]
    switch_options = (
        "noloc",
        "search",
        "list",
        "show",
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

    def func(self):
        """Implements the spawner"""

        def _parse_prototype(inp, expect=dict):
            err = None
            try:
                prototype = _LITERAL_EVAL(inp)
            except (SyntaxError, ValueError) as err:
                # treat as string
                prototype = utils.to_str(inp)
            finally:
                if not isinstance(prototype, expect):
                    if err:
                        string = (
                            "{}\n|RCritical Python syntax error in argument. Only primitive "
                            "Python structures are allowed. \nYou also need to use correct "
                            "Python syntax. Remember especially to put quotes around all "
                            "strings inside lists and dicts.|n For more advanced uses, embed "
                            "inline functions in the strings.".format(err)
                        )
                    else:
                        string = "Expected {}, got {}.".format(expect, type(prototype))
                    self.caller.msg(string)
                    return None
            if expect == dict:
                # an actual prototype. We need to make sure it's safe. Don't allow exec
                if "exec" in prototype and not self.caller.check_permstring("Developer"):
                    self.caller.msg(
                        "Spawn aborted: You are not allowed to " "use the 'exec' prototype key."
                    )
                    return None
                try:
                    # we homogenize first, to be more lenient
                    protlib.validate_prototype(protlib.homogenize_prototype(prototype))
                except RuntimeError as err:
                    self.caller.msg(str(err))
                    return
            return prototype

        def _search_show_prototype(query, prototypes=None):
            # prototype detail
            if not prototypes:
                prototypes = protlib.search_prototype(key=query)
            if prototypes:
                return "\n".join(protlib.prototype_to_str(prot) for prot in prototypes)
            else:
                return False

        caller = self.caller

        if (
            self.cmdstring == "olc"
            or "menu" in self.switches
            or "olc" in self.switches
            or "edit" in self.switches
        ):
            # OLC menu mode
            prototype = None
            if self.lhs:
                key = self.lhs
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
                    caller.msg("No prototype '{}' was found.".format(key))
                    return
            olc_menus.start_olc(caller, session=self.session, prototype=prototype)
            return

        if "search" in self.switches:
            # query for a key match
            if not self.args:
                self.switches.append("list")
            else:
                key, tags = self.args.strip(), None
                if ";" in self.args:
                    key, tags = (part.strip().lower() for part in self.args.split(";", 1))
                    tags = [tag.strip() for tag in tags.split(",")] if tags else None
                EvMore(
                    caller,
                    str(protlib.list_prototypes(caller, key=key, tags=tags)),
                    exit_on_lastpage=True,
                )
                return

        if "show" in self.switches or "examine" in self.switches:
            # the argument is a key in this case (may be a partial key)
            if not self.args:
                self.switches.append("list")
            else:
                matchstring = _search_show_prototype(self.args)
                if matchstring:
                    caller.msg(matchstring)
                else:
                    caller.msg("No prototype '{}' was found.".format(self.args))
                return

        if "list" in self.switches:
            # for list, all optional arguments are tags
            # import pudb; pudb.set_trace()

            EvMore(
                caller,
                str(protlib.list_prototypes(caller, tags=self.lhslist)),
                exit_on_lastpage=True,
                justify_kwargs=False,
            )
            return

        if "save" in self.switches:
            # store a prototype to the database store
            if not self.args:
                caller.msg(
                    "Usage: spawn/save <key>[;desc[;tag,tag[,...][;lockstring]]] = <prototype_dict>"
                )
                return

            # handle rhs:
            prototype = _parse_prototype(self.lhs.strip())
            if not prototype:
                return

            # present prototype to save
            new_matchstring = _search_show_prototype("", prototypes=[prototype])
            string = "|yCreating new prototype:|n\n{}".format(new_matchstring)
            question = "\nDo you want to continue saving? [Y]/N"

            prototype_key = prototype.get("prototype_key")
            if not prototype_key:
                caller.msg("\n|yTo save a prototype it must have the 'prototype_key' set.")
                return

            # check for existing prototype,
            old_matchstring = _search_show_prototype(prototype_key)

            if old_matchstring:
                string += "\n|yExisting saved prototype found:|n\n{}".format(old_matchstring)
                question = "\n|yDo you want to replace the existing prototype?|n [Y]/N"

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
            existing_objects = protlib.search_objects_with_prototype(prototype_key)
            if existing_objects:
                if "update" not in self.switches:
                    n_existing = len(existing_objects)
                    slow = " (note that this may be slow)" if n_existing > 10 else ""
                    string = (
                        "There are {} objects already created with an older version "
                        "of prototype {}. Should it be re-applied to them{}? [Y]/N".format(
                            n_existing, prototype_key, slow
                        )
                    )
                    answer = yield (string)
                    if answer.lower() in ["n", "no"]:
                        caller.msg(
                            "|rNo update was done of existing objects. "
                            "Use spawn/update <key> to apply later as needed.|n"
                        )
                        return
                n_updated = spawner.batch_update_objects_with_prototype(existing_objects, key)
                caller.msg("{} objects were updated.".format(n_updated))
            return

        if not self.args:
            ncount = len(protlib.search_prototype())
            caller.msg(
                "Usage: spawn <prototype-key> or {{key: value, ...}}"
                "\n ({} existing prototypes. Use /list to inspect)".format(ncount)
            )
            return

        if "delete" in self.switches:
            # remove db-based prototype
            matchstring = _search_show_prototype(self.args)
            if matchstring:
                string = "|rDeleting prototype:|n\n{}".format(matchstring)
                question = "\nDo you want to continue deleting? [Y]/N"
                answer = yield (string + question)
                if answer.lower() in ["n", "no"]:
                    caller.msg("|rDeletion cancelled.|n")
                    return
                try:
                    success = protlib.delete_prototype(self.args)
                except protlib.PermissionError as err:
                    caller.msg("|rError deleting:|R {}|n".format(err))
                caller.msg(
                    "Deletion {}.".format(
                        "successful" if success else "failed (does the prototype exist?)"
                    )
                )
                return
            else:
                caller.msg("Could not find prototype '{}'".format(key))

        if "update" in self.switches:
            # update existing prototypes
            key = self.args.strip().lower()
            existing_objects = protlib.search_objects_with_prototype(key)
            if existing_objects:
                n_existing = len(existing_objects)
                slow = " (note that this may be slow)" if n_existing > 10 else ""
                string = (
                    "There are {} objects already created with an older version "
                    "of prototype {}. Should it be re-applied to them{}? [Y]/N".format(
                        n_existing, key, slow
                    )
                )
                answer = yield (string)
                if answer.lower() in ["n", "no"]:
                    caller.msg("|rUpdate cancelled.")
                    return
                n_updated = spawner.batch_update_objects_with_prototype(existing_objects, key)
                caller.msg("{} objects were updated.".format(n_updated))

        # A direct creation of an object from a given prototype

        prototype = _parse_prototype(
            self.args, expect=dict if self.args.strip().startswith("{") else str
        )
        if not prototype:
            # this will only let through dicts or strings
            return

        key = "<unnamed>"
        if isinstance(prototype, str):
            # A prototype key we are looking to apply
            key = prototype
            prototypes = protlib.search_prototype(prototype)
            nprots = len(prototypes)
            if not prototypes:
                caller.msg("No prototype named '%s'." % prototype)
                return
            elif nprots > 1:
                caller.msg(
                    "Found {} prototypes matching '{}':\n  {}".format(
                        nprots,
                        prototype,
                        ", ".join(proto.get("prototype_key", "") for proto in prototypes),
                    )
                )
                return
            # we have a prototype, check access
            prototype = prototypes[0]
            if not caller.locks.check_lockstring(
                caller, prototype.get("prototype_locks", ""), access_type="spawn", default=True
            ):
                caller.msg("You don't have access to use this prototype.")
                return

        if "noloc" not in self.switches and "location" not in prototype:
            prototype["location"] = self.caller.location

        # proceed to spawning
        try:
            for obj in spawner.spawn(prototype):
                self.caller.msg("Spawned %s." % obj.get_display_name(self.caller))
        except RuntimeError as err:
            caller.msg(err)
