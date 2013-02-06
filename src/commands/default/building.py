"""

Building and world design commands

"""
from django.conf import settings
from src.objects.models import ObjectDB, ObjAttribute
from src.players.models import PlayerAttribute
from src.utils import create, utils, debug
from src.utils.ansi import raw
from src.commands.default.muxcommand import MuxCommand
from src.commands.cmdhandler import get_and_merge_cmdsets

# limit symbol import for API
__all__ = ("ObjManipCommand", "CmdSetObjAlias", "CmdCopy",
           "CmdCpAttr", "CmdMvAttr", "CmdCreate", "CmdDebug",
           "CmdDesc", "CmdDestroy", "CmdDig", "CmdTunnel", "CmdLink",
           "CmdUnLink", "CmdSetHome", "CmdListCmdSets", "CmdName",
           "CmdOpen", "CmdSetAttribute", "CmdTypeclass", "CmdWipe",
           "CmdLock", "CmdExamine", "CmdFind", "CmdTeleport",
           "CmdScript")

try:
    # used by @set
    from ast import literal_eval as _LITERAL_EVAL
except ImportError:
    # literal_eval is not available before Python 2.6
    _LITERAL_EVAL = None

# used by @find
CHAR_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS

class ObjManipCommand(MuxCommand):
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
        super(ObjManipCommand, self).parse()

        obj_defs = ([],[])    # stores left- and right-hand side of '='
        obj_attrs = ([], [])  #                   "

        for iside, arglist in enumerate((self.lhslist, self.rhslist)):
            # lhslist/rhslist is already split by ',' at this point
            for objdef in arglist:
                aliases, option, attrs = [], None, []
                if ':' in objdef:
                    objdef, option = [part.strip() for part in objdef.rsplit(':', 1)]
                if ';' in objdef:
                    objdef, aliases = [part.strip() for part in objdef.split(';', 1)]
                    aliases = [alias.strip() for alias in aliases.split(';') if alias.strip()]
                if '/' in objdef:
                    objdef, attrs = [part.strip() for part in objdef.split('/', 1)]
                    attrs = [part.strip().lower() for part in attrs.split('/') if part.strip()]
                # store data
                obj_defs[iside].append({"name":objdef, 'option':option, 'aliases':aliases})
                obj_attrs[iside].append({"name":objdef, 'attrs':attrs})

        # store for future access
        self.lhs_objs = obj_defs[0]
        self.rhs_objs = obj_defs[1]
        self.lhs_objattr = obj_attrs[0]
        self.rhs_objattr = obj_attrs[1]


class CmdSetObjAlias(MuxCommand):
    """
    Adding permanent aliases

    Usage:
      @alias <obj> [= [alias[,alias,alias,...]]]

    Assigns aliases to an object so it can be referenced by more
    than one name. Assign empty to remove all aliases from object.
    Observe that this is not the same thing as aliases
    created with the 'alias' command! Aliases set with @alias are
    changing the object in question, making those aliases usable
    by everyone.
    """

    key  = "@alias"
    aliases = "@setobjalias"
    locks = "cmd:perm(setobjalias) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Set the aliases."

        caller = self.caller

        if not self.lhs:
            string = "Usage: @alias <obj> [= [alias[,alias ...]]]"
            self.caller.msg(string)
            return
        objname = self.lhs

        # Find the object to receive aliases
        obj = caller.search(objname)
        if not obj:
            return
        if self.rhs == None:
            # no =, so we just list aliases on object.
            aliases = obj.aliases
            if aliases:
                caller.msg("Aliases for '%s': %s" % (obj.key, ", ".join(aliases)))
            else:
                caller.msg("No aliases exist for '%s'." % obj.key)
            return

        if not obj.access(caller, 'edit'):
            caller.msg("You don't have permission to do that.")
            return

        if not self.rhs:
            # we have given an empty =, so delete aliases
            old_aliases = obj.aliases
            if old_aliases:
                caller.msg("Cleared aliases from %s: %s" % (obj.key, ", ".join(old_aliases)))
                del obj.dbobj.aliases
            else:
                caller.msg("No aliases to clear.")
            return

        # merge the old and new aliases (if any)
        old_aliases = obj.aliases
        new_aliases = [alias.strip().lower() for alias in self.rhs.split(',') if alias.strip()]
        # make the aliases only appear once
        old_aliases.extend(new_aliases)
        aliases = list(set(old_aliases))
        # save back to object.
        obj.aliases = aliases
        # we treat this as a re-caching (relevant for exits to re-build their exit commands with the correct aliases)
        caller.msg("Aliases for '%s' are now set to %s." % (obj.key, ", ".join(obj.aliases)))

class CmdCopy(ObjManipCommand):
    """
    @copy - copy objects

    Usage:
      @copy[/reset] <original obj> [= new_name][;alias;alias..][:new_location] [,new_name2 ...]

    switch:
      reset - make a 'clean' copy off the object, thus
              removing any changes that might have been made to the original
              since it was first created.

    Create one or more copies of an object. If you don't supply any targets, one exact copy
    of the original object will be created with the name *_copy.
    """

    key = "@copy"
    locks = "cmd:perm(copy) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Uses ObjManipCommand.parse()"

        caller = self.caller
        args = self.args
        if not args:
            caller.msg("Usage: @copy <obj> [=new_name[;alias;alias..]][:new_location] [, new_name2...]")
            return

        if not self.rhs:
            # this has no target =, so an identical new object is created.
            from_obj_name = self.args
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return
            to_obj_name = "%s_copy" % from_obj_name
            to_obj_aliases = ["%s_copy" % alias for alias in from_obj.aliases]
            copiedobj = ObjectDB.objects.copy_object(from_obj, new_key=to_obj_name,
                                                     new_aliases=to_obj_aliases)
            if copiedobj:
                string = "Identical copy of %s, named '%s' was created." % (from_obj_name, to_obj_name)
            else:
                string = "There was an error copying %s."
        else:
            # we have specified =. This might mean many object targets
            from_obj_name = self.lhs_objs[0]['name']
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return
            for objdef in self.rhs_objs:
                # loop through all possible copy-to targets
                to_obj_name = objdef['name']
                to_obj_aliases = objdef['aliases']
                to_obj_location = objdef['option']
                if to_obj_location:
                    to_obj_location = caller.search(to_obj_location, global_search=True)
                    if not to_obj_location:
                        return

                copiedobj = ObjectDB.objects.copy_object(from_obj, new_key=to_obj_name,
                                                         new_location=to_obj_location, new_aliases=to_obj_aliases)
                if copiedobj:
                    string = "Copied %s to '%s' (aliases: %s)." % (from_obj_name, to_obj_name,
                                                                   to_obj_aliases)
                else:
                    string = "There was an error copying %s to '%s'." % (from_obj_name,
                                                                         to_obj_name)
        # we are done, echo to user
        caller.msg(string)

class CmdCpAttr(ObjManipCommand):
    """
    @cpattr - copy attributes

    Usage:
      @cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      @cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      move - delete the attribute from the source object after copying.

    Example:
      @cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
      ->
      copies the coolness attribute (defined on yourself), to attributes
      on Anna and Tom.

    Copy the attribute one object to one or more attributes on another object. If
    you don't supply a source object, yourself is used.
    """
    key = "@cpattr"
    locks = "cmd:perm(cpattr) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        Do the copying.
        """
        caller = self.caller

        if not self.rhs:
            string = """Usage:
            @cpattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            @cpattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
            @cpattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            @cpattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]"""
            caller.msg(string)
            return

        lhs_objattr = self.lhs_objattr
        to_objs = self.rhs_objattr
        from_obj_name = lhs_objattr[0]['name']
        from_obj_attrs = lhs_objattr[0]['attrs']

        if not from_obj_attrs:
            # this means the from_obj_name is actually an attribute name on self.
            from_obj_attrs = [from_obj_name]
            from_obj = self.caller
            from_obj_name = self.caller.name
        else:
            from_obj = caller.search(from_obj_name)
        if not from_obj or not to_objs:
            caller.msg("You have to supply both source object and target(s).")
            return
        if not from_obj.has_attribute(from_obj_attrs[0]):
            caller.msg("%s doesn't have an attribute %s." % (from_obj_name, from_obj_attrs[0]))
            return
        srcvalue = from_obj.get_attribute(from_obj_attrs[0])

        #copy to all to_obj:ects
        if "move" in self.switches:
            string = "Moving "
        else:
            string = "Copying "
        string += "%s/%s (with value %s) ..." % (from_obj_name, from_obj_attrs[0], srcvalue)

        for to_obj in to_objs:
            to_obj_name = to_obj['name']
            to_obj_attrs = to_obj['attrs']
            to_obj = caller.search(to_obj_name)
            if not to_obj:
                string += "\nCould not find object '%s'" % to_obj_name
                continue
            for inum, from_attr in enumerate(from_obj_attrs):
                try:
                    to_attr = to_obj_attrs[inum]
                except IndexError:
                    # if there are too few attributes given
                    # on the to_obj, we copy the original name instead.
                    to_attr = from_attr
                to_obj.set_attribute(to_attr, srcvalue)
                if "move" in self.switches and not (from_obj == to_obj and from_attr == to_attr):
                    from_obj.del_attribute(from_attr)
                    string += "\nMoved %s.%s -> %s.%s." % (from_obj.name, from_attr,
                                                           to_obj_name, to_attr)
                else:
                    string += "\nCopied %s.%s -> %s.%s." % (from_obj.name, from_attr,
                                                            to_obj_name, to_attr)
        caller.msg(string)

class CmdMvAttr(ObjManipCommand):
    """
    @mvattr - move attributes

    Usage:
      @mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      @mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]

    Switches:
      copy - Don't delete the original after moving.

    Move an attribute from one object to one or more attributes on another object. If
    you don't supply a source object, yourself is used.
    """
    key = "@mvattr"
    locks = "cmd:perm(mvattr) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        Do the moving
        """
        if not self.rhs:
            string = """Usage:
      @mvattr[/switch] <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @mvattr[/switch] <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      @mvattr[/switch] <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @mvattr[/switch] <attr> = <obj1>[,<obj2>,<obj3>,...]"""
            self.caller.msg(string)
            return

        # simply use @cpattr for all the functionality
        if "copy" in self.switches:
            self.caller.execute_cmd("@cpattr %s" % self.args)
        else:
            self.caller.execute_cmd("@cpattr/move %s" % self.args)

class CmdCreate(ObjManipCommand):
    """
    @create - create new objects

    Usage:
      @create[/drop] objname[;alias;alias...][:typeclass], objname...

    switch:
       drop - automatically drop the new object into your current location (this is not echoed)
              this also sets the new object's home to the current location rather than to you.

    Creates one or more new objects. If typeclass is given, the object
    is created as a child of this typeclass. The typeclass script is
    assumed to be located under game/gamesrc/types and any further
    directory structure is given in Python notation. So if you have a
    correct typeclass object defined in
    game/gamesrc/types/examples/red_button.py, you could create a new
    object of this type like this:

       @create button;red : examples.red_button.RedButton

    """

    key = "@create"
    locks = "cmd:perm(create) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        Creates the object.
        """

        caller = self.caller

        if not self.args:
            string = "Usage: @create[/drop] <newname>[;alias;alias...] [:typeclass_path]"
            caller.msg(string)
            return

        # create the objects
        for objdef in self.lhs_objs:
            string = ""
            name = objdef['name']
            aliases = objdef['aliases']
            typeclass = objdef['option']

            # create object (if not a valid typeclass, the default
            # object typeclass will automatically be used)
            lockstring = "control:id(%s);examine:perm(Builders);delete:id(%s) or perm(Wizards);get:all()" % (caller.id, caller.id)
            obj = create.create_object(typeclass, name, caller,
                                       home=caller, aliases=aliases, locks=lockstring, report_to=caller)
            if not obj:
                continue
            if aliases:
                string = "You create a new %s: %s (aliases: %s)."
                string = string % (obj.typeclass.typename, obj.name, ", ".join(aliases))
            else:
                string = "You create a new %s: %s."
                string = string % (obj.typeclass.typename, obj.name)
            # set a default desc
            if not obj.db.desc:
                obj.db.desc = "You see nothing special."
            if 'drop' in self.switches:
                if caller.location:
                    obj.home = caller.location
                    obj.move_to(caller.location, quiet=True)
        if string:
           caller.msg(string)


class CmdDebug(MuxCommand):
    """
    Debug game entities

    Usage:
      @debug[/switch] <path to code>

    Switches:
      obj - debug an object
      script - debug a script

    Examples:
      @debug/script game.gamesrc.scripts.myscript.MyScript
      @debug/script myscript.MyScript
      @debug/obj examples.red_button.RedButton

    This command helps when debugging the codes of objects and scripts.
    It creates the given object and runs tests on its hooks.
    """

    key = "@debug"
    locks = "cmd:perm(debug) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Running the debug"

        if not self.args or not self.switches:
            self.caller.msg("Usage: @debug[/obj][/script] <path>")
            return

        path = self.args

        if 'obj' in self.switches or 'object' in self.switches:
            # create and debug the object
            self.caller.msg(debug.debug_object(path, self.caller))
            self.caller.msg(debug.debug_object_scripts(path, self.caller))

        elif 'script' in self.switches:
            self.caller.msg(debug.debug_syntax_script(path))


class CmdDesc(MuxCommand):
    """
    @desc - describe an object or room

    Usage:
      @desc [<obj> =] >description>

    Setts the "desc" attribute on an
    object. If an object is not given,
    describe the current room.
    """
    key = "@desc"
    aliases = "@describe"
    locks = "cmd:perm(desc) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Define command"

        caller = self.caller
        if not self.args:
            caller.msg("Usage: @desc [<obj> =] >description>")
            return

        if self.rhs:
            # We have an =
            obj = caller.search(self.lhs)
            if not obj:
                return
            desc = self.rhs
        else:
            obj = caller.location
            desc = self.args
        # storing the description
        obj.db.desc = desc
        caller.msg("The description was set on %s." % obj.key)


class CmdDestroy(MuxCommand):
    """
    @destroy - remove objects from the game

    Usage:
       @destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]

    switches:
       override - The @destroy command will usually avoid accidentally destroying
                  player objects. This switch overrides this safety.
    examples:
       @destroy house, roof, door, 44-78
       @destroy 5-10, flower, 45

    Destroys one or many objects. If dbrefs are used, a range to delete can be
    given, e.g. 4-10. Also the end points will be deleted.
    """

    key = "@destroy"
    aliases = ["@delete", "@del"]
    locks = "cmd:perm(destroy) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Implements the command."

        caller = self.caller

        if not self.args or not self.lhslist:
            caller.msg("Usage: @destroy[/switches] [obj, obj2, obj3, [dbref-dbref],...]")
            return ""

        def delobj(objname, byref=False):
            # helper function for deleting a single object
            string = ""
            obj = caller.search(objname, global_dbref=byref)
            if not obj:
                self.caller.msg(" (Objects to destroy must either be local or specified with a unique dbref.)")
                return ""
            if not "override" in self.switches and obj.dbid == int(settings.CHARACTER_DEFAULT_HOME.lstrip("#")):
                return "\nYou are trying to delete CHARACTER_DEFAULT_HOME. If you want to do this, use the /override switch."
            objname = obj.name
            if not obj.access(caller, 'delete'):
                return "\nYou don't have permission to delete %s." % objname
            if obj.player and not 'override' in self.switches:
                return "\nObject %s is controlled by an active player. Use /override to delete anyway." % objname

            had_exits = hasattr(obj, "exits") and obj.exits
            had_objs = hasattr(obj, "contents") and any(obj for obj in obj.contents
                                                        if not (hasattr(obj, "exits") and obj not in obj.exits))
            # do the deletion
            okay = obj.delete()
            if not okay:
                string += "\nERROR: %s not deleted, probably because at_obj_delete() returned False." % objname
            else:
                string += "\n%s was destroyed." % objname
                if had_exits:
                    string += " Exits to and from %s were destroyed as well." % objname
                if had_objs:
                    string += " Objects inside %s were moved to their homes." % objname
            return string

        string = ""
        for objname in self.lhslist:
            if '-' in objname:
                # might be a range of dbrefs
                dmin, dmax = [utils.dbref(part, reqhash=False) for part in objname.split('-', 1)]
                if dmin and dmax:
                    for dbref in range(int(dmin),int(dmax+1)):
                        string += delobj("#" + str(dbref), True)
                else:
                    string += delobj(objname)
            else:
                string += delobj(objname, True)
        if string:
            caller.msg(string.strip())


class CmdDig(ObjManipCommand):
    """
    @dig - build and connect new rooms to the current one

    Usage:
      @dig[/switches] roomname[;alias;alias...][:typeclass]
            [= exit_to_there[;alias][:typeclass]]
               [, exit_to_here[;alias][:typeclass]]

    Switches:
       tel or teleport - move yourself to the new room

    Examples:
       @dig kitchen = north;n, south;s
       @dig house:myrooms.MyHouseTypeclass
       @dig sheer cliff;cliff;sheer = climb up, climb down

    This command is a convenient way to build rooms quickly; it creates the new room and you can optionally
    set up exits back and forth between your current room and the new one. You can add as many aliases as you
    like to the name of the room and the exits in question; an example would be 'north;no;n'.
    """
    key = "@dig"
    locks = "cmd:perm(dig) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Do the digging. Inherits variables from ObjManipCommand.parse()"

        caller = self.caller

        if not self.lhs:
            string = "Usage: @dig[/teleport] roomname[;alias;alias...][:parent] [= exit_there"
            string += "[;alias;alias..][:parent]] "
            string += "[, exit_back_here[;alias;alias..][:parent]]"
            caller.msg(string)
            return

        room = self.lhs_objs[0]

        if not room["name"]:
            caller.msg("You must supply a new room name.")
            return
        location = caller.location

        # Create the new room
        typeclass = room['option']
        if not typeclass:
            typeclass = settings.BASE_ROOM_TYPECLASS

        # create room
        lockstring = "control:id(%s) or perm(Immortals); delete:id(%s) or perm(Wizards); edit:id(%s) or perm(Wizards)"
        lockstring = lockstring % (caller.dbref, caller.dbref, caller.dbref)

        new_room = create.create_object(typeclass, room["name"],
                                        aliases=room["aliases"], report_to=caller)
        new_room.locks.add(lockstring)
        alias_string = ""
        if new_room.aliases:
            alias_string = " (%s)" % ", ".join(new_room.aliases)
        room_string = "Created room %s(%s)%s of type %s." % (new_room, new_room.dbref, alias_string, typeclass)


        # create exit to room

        exit_to_string = ""
        exit_back_string = ""

        if self.rhs_objs:
            to_exit = self.rhs_objs[0]
            if not to_exit["name"]:
                exit_to_string = \
                    "\nNo exit created to new room."
            elif not location:
                exit_to_string = \
                  "\nYou cannot create an exit from a None-location."
            else:
                # Build the exit to the new room from the current one
                typeclass = to_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS

                print typeclass, to_exit["name"], location, to_exit["aliases"],lockstring, new_room, caller
                new_to_exit = create.create_object(typeclass, to_exit["name"], location,
                                                   aliases=to_exit["aliases"],
                                                   locks=lockstring, destination=new_room, report_to=caller)
                alias_string = ""
                if new_to_exit.aliases:
                    alias_string = " (%s)" % ", ".join(new_to_exit.aliases)
                exit_to_string = "\nCreated Exit from %s to %s: %s(%s)%s."
                exit_to_string = exit_to_string % (location.name, new_room.name, new_to_exit,
                                                   new_to_exit.dbref, alias_string)

        # Create exit back from new room

        if len(self.rhs_objs) > 1:
            # Building the exit back to the current room
            back_exit = self.rhs_objs[1]
            if not back_exit["name"]:
                exit_back_string = \
                    "\nNo back exit created."
            elif not location:
                exit_back_string = \
                   "\nYou cannot create an exit back to a None-location."
            else:
                typeclass = back_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS
                new_back_exit = create.create_object(typeclass, back_exit["name"],
                                                     new_room, aliases=back_exit["aliases"],
                                                     locks=lockstring, destination=location, report_to=caller)
                alias_string = ""
                if new_back_exit.aliases:
                    alias_string = " (%s)" % ", ".join(new_back_exit.aliases)
                exit_back_string = "\nCreated Exit back from %s to %s: %s(%s)%s."
                exit_back_string = exit_back_string % (new_room.name, location.name,
                                                       new_back_exit, new_back_exit.dbref, alias_string)
        caller.msg("%s%s%s" % (room_string, exit_to_string, exit_back_string))
        if new_room and ('teleport' in self.switches or "tel" in self.switches):
            caller.move_to(new_room)

class CmdTunnel(MuxCommand):
    """
    dig in often-used directions

    Usage:
      @tunnel[/switch] <direction> [= roomname[;alias;alias;...][:typeclass]]

    Switches:
      oneway - do not create an exit back to the current location
      tel - teleport to the newly created room

    Example:
      @tunnel n
      @tunnel n = house;mike's place;green building

    This is a simple way to build using pre-defined directions:
     {wn,ne,e,se,s,sw,w,nw{n (north, northeast etc)
     {wu,d{n (up and down)
     {wi,o{n (in and out)
    The full names (north, in, southwest, etc) will always be put as
    main name for the exit, using the abbreviation as an alias (so an
    exit will always be able to be used with both "north" as well as
    "n" for example). Opposite directions will automatically be
    created back from the new room unless the /oneway switch is given.
    For more flexibility and power in creating rooms, use @dig.
    """

    key = "@tunnel"
    aliases = ["@tun"]
    locks = "cmd: perm(tunnel) or perm(Builders)"
    help_category = "Building"

    # store the direction, full name and its opposite
    directions = {"n" : ("north", "s"),
                  "ne": ("northeast", "sw"),
                  "e" : ("east", "w"),
                  "se": ("southeast", "nw"),
                  "s" : ("south", "n"),
                  "sw": ("southwest", "ne"),
                  "w" : ("west", "e"),
                  "nw": ("northwest", "se"),
                  "u" : ("up", "d"),
                  "d" : ("down", "u"),
                  "i" : ("in", "o"),
                  "o" : ("out", "i")}

    def func(self):
        "Implements the tunnel command"

        if not self.args or not self.lhs:
            string = "Usage: @tunnel[/switch] <direction> [= roomname[;alias;alias;...][:typeclass]]"
            self.caller.msg(string)
            return
        if self.lhs not in self.directions:
            string = "@tunnel can only understand the following directions: %s." % ",".join(sorted(self.directions.keys()))
            string += "\n(use @dig for more freedom)"
            self.caller.msg(string)
            return
        # retrieve all input and parse it
        exitshort = self.lhs
        exitname, backshort = self.directions[exitshort]
        backname = self.directions[backshort][0]

        roomname = "Some place"
        if self.rhs:
            roomname = self.rhs # this may include aliases; that's fine.

        telswitch = ""
        if "tel" in self.switches:
            telswitch = "/teleport"
        backstring = ""
        if not "oneway" in self.switches:
            backstring = ", %s;%s" % (backname, backshort)

        # build the string we will use to call @dig
        digstring = "@dig%s %s = %s;%s%s" % (telswitch, roomname, exitname, exitshort, backstring)
        self.caller.execute_cmd(digstring)

class CmdLink(MuxCommand):
    """
    @link - connect objects

    Usage:
      @link[/switches] <object> = <target>
      @link[/switches] <object> =
      @link[/switches] <object>

    Switch:
      twoway - connect two exits. For this to work, BOTH <object>
               and <target> must be exit objects.

    If <object> is an exit, set its destination to <target>. Two-way operation
    instead sets the destination to the *locations* of the respective given
    arguments.
    The second form (a lone =) sets the destination to None (same as the @unlink command)
    and the third form (without =) just shows the currently set destination.
    """

    key = "@link"
    locks = "cmd:perm(link) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Perform the link"
        caller = self.caller

        if not self.args:
            caller.msg("Usage: @link[/twoway] <object> = <target>")
            return

        object_name = self.lhs

        # get object
        obj = caller.search(object_name, global_search=True)
        if not obj:
            return

        string = ""
        if self.rhs:
            # this means a target name was given
            target = caller.search(self.rhs, global_search=True)
            if not target:
                return

            string = ""
            if not obj.destination:
                string += "Note: %s(%s) did not have a destination set before. Make sure you linked the right thing." % (obj.name,obj.dbref)
            if "twoway" in self.switches:
                if not (target.location and obj.location):
                    string = "To create a two-way link, %s and %s must both have a location" % (obj, target)
                    string += " (i.e. they cannot be rooms, but should be exits)."
                    self.caller.msg(string)
                    return
                if not target.destination:
                    string += "\nNote: %s(%s) did not have a destination set before. Make sure you linked the right thing." % (target.name, target.dbref)
                obj.destination = target.location
                target.destination = obj.location
                string += "\nLink created %s (in %s) <-> %s (in %s) (two-way)." % (obj.name, obj.location, target.name, target.location)
            else:
                obj.destination = target
                string += "\nLink created %s -> %s (one way)." % (obj.name, target)

        elif self.rhs == None:
            # this means that no = was given (otherwise rhs
            # would have been an empty string). So we inspect
            # the home/destination on object
            dest = obj.destination
            if dest:
                string = "%s is an exit to %s." % (obj.name, dest.name)
            else:
                string = "%s is not an exit. Its home location is %s." % (obj.name, obj.home)

        else:
            # We gave the command @link 'obj = ' which means we want to
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
    @unlink - unconnect objects

    Usage:
      @unlink <Object>

    Unlinks an object, for example an exit, disconnecting
    it from whatever it was connected to.
    """
    # this is just a child of CmdLink

    key = "@unlink"
    locks = "cmd:perm(unlink) or perm(Builders)"
    help_key = "Building"

    def func(self):
        """
        All we need to do here is to set the right command
        and call func in CmdLink
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: @unlink <object>")
            return

        # This mimics '@link <obj> = ' which is the same as @unlink
        self.rhs = ""

        # call the @link functionality
        super(CmdUnLink, self).func()

class CmdSetHome(CmdLink):
    """
    @home - control an object's home location

    Usage:
      @home <obj> [= home_location]

    The "home" location is a "safety" location for objects; they
    will be moved there if their current location ceases to exist. All
    objects should always have a home location for this reason.
    It is also a convenient target of the "home" command.

    If no location is given, just view the object's home location.
    """

    key = "@home"
    aliases = "@sethome"
    locks = "cmd:perm(@home) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "implement the command"
        if not self.args:
            string = "Usage: @home <obj> [= home_location]"
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
                string = "%s's home location was changed from %s(%s) to %s(%s)." % (obj, old_home, old_home.dbref, new_home, new_home.dbref)
            else:
                string = "%s' home location was set to %s(%s)." % (obj, new_home, new_home.dbref)
        self.caller.msg(string)

class CmdListCmdSets(MuxCommand):
    """
    list command sets on an object

    Usage:
      @cmdsets [obj]

    This displays all cmdsets assigned
    to a user. Defaults to yourself.
    """
    key = "@cmdsets"
    aliases = "@listcmsets"
    locks = "cmd:perm(listcmdsets) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "list the cmdsets"

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
    cname - change the name and/or aliases of an object

    Usage:
      @name obj = name;alias1;alias2

    Rename an object to something new.

    """

    key = "@name"
    aliases = ["@rename"]
    locks = "cmd:perm(rename) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "change the name"

        caller = self.caller
        if not self.args:
            string = "Usage: @name <obj> = <newname>[;alias;alias;...]"
            caller.msg(string)
            return

        if self.lhs_objs:
            objname = self.lhs_objs[0]['name']
            obj = caller.search(objname)
            if not obj:
                return
        if self.rhs_objs:
            newname = self.rhs_objs[0]['name']
            aliases = self.rhs_objs[0]['aliases']
        else:
            newname = self.rhs
            aliases = None
        if not newname and not aliases:
            caller.msg("No names or aliases defined!")
            return
        # change the name and set aliases:
        if newname:
            obj.name = newname
        astring = ""
        if aliases:
            obj.aliases = aliases
            astring = " (%s)" % (", ".join(aliases))
        # fix for exits - we need their exit-command to change name too
        if obj.destination:
            obj.flush_from_cache()
        caller.msg("Object's name changed to '%s'%s." % (newname, astring))


class CmdOpen(ObjManipCommand):
    """
    @open - create new exit

    Usage:
      @open <new exit>[;alias;alias..][:typeclass] [,<return exit>[;alias;..][:typeclass]]] = <destination>

    Handles the creation of exits. If a destination is given, the exit
    will point there. The <return exit> argument sets up an exit at the
    destination leading back to the current room. Destination name
    can be given both as a #dbref and a name, if that name is globally
    unique.

    """
    key = "@open"
    locks = "cmd:perm(open) or perm(Builders)"
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
        exit_obj = caller.search(exit_name, location=location, ignore_errors=True)
        if len(exit_obj) > 1:
            # give error message and return
            caller.search(exit_name, location=location)
            return
        if exit_obj:
            exit_obj = exit_obj[0]
            if not exit_obj.destination:
                # we are trying to link a non-exit
                string = "'%s' already exists and is not an exit!\nIf you want to convert it "
                string += "to an exit, you must assign an object to the 'destination' property first."
                caller.msg(string % exit_name)
                return None
            # we are re-linking an old exit.
            old_destination = exit_obj.destination
            if old_destination:
                string = "Exit %s already exists." % exit_name
                if old_destination.id != destination.id:
                    # reroute the old exit.
                    exit_obj.destination = destination
                    exit_obj.aliases = exit_aliases
                    string += " Rerouted its old destination '%s' to '%s' and changed aliases." % \
                        (old_destination.name, destination.name)
                else:
                    string += " It already points to the correct place."

        else:
            # exit does not exist before. Create a new one.
            if not typeclass:
                typeclass = settings.BASE_EXIT_TYPECLASS
            exit_obj = create.create_object(typeclass, key=exit_name,
                                            location=location,
                                            aliases=exit_aliases, report_to=caller)
            if exit_obj:
                # storing a destination is what makes it an exit!
                exit_obj.destination = destination
                string = "Created new Exit '%s' from %s to %s (aliases: %s)." % (exit_name,location.name,
                                                                                 destination.name,
                                                                                 ", ".join([str(e) for e in exit_aliases]))
            else:
                string = "Error: Exit '%s' not created." % (exit_name)
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
            string = "Usage: @open <new exit>[;alias...][:typeclass][,<return exit>[;alias..][:typeclass]]] "
            string += "= <destination>"
            caller.msg(string)
            return

        # We must have a location to open an exit
        location = caller.location
        if not location:
            caller.msg("You cannot create an exit from a None-location.")
            return

        # obtain needed info from cmdline

        exit_name = self.lhs_objs[0]['name']
        exit_aliases = self.lhs_objs[0]['aliases']
        exit_typeclass = self.lhs_objs[0]['option']
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
            back_exit_name = self.lhs_objs[1]['name']
            back_exit_aliases = self.lhs_objs[1]['aliases']
            back_exit_typeclass = self.lhs_objs[1]['option']
            ok = self.create_exit(back_exit_name, destination, location, back_exit_aliases, back_exit_typeclass)


class CmdSetAttribute(ObjManipCommand):
    """
    @set - set attributes

    Usage:
      @set <obj>/<attr> = <value>
      @set <obj>/<attr> =
      @set <obj>/<attr>

    Sets attributes on objects. The second form clears
    a previously set attribute while the last form
    inspects the current value of the attribute
    (if any).

    The most common data to save with this command are strings and
    numbers. You can however also set Python primities such as lists,
    dictionaries and tuples on objects (this might be important for
    the functionality of certain custom objects).  This is indicated
    by you starting your value with one of {c'{n, {c"{n, {c({n, {c[{n  or {c{ {n.
    Note that you should leave a space after starting a dictionary ('{ ')
    so as to not confuse the dictionary start with a colour code like \{g.
    Remember that if you use Python primitives like this, you must
    write proper Python syntax too - notably you must include quotes
    around your strings or you will get an error.

    """

    key = "@set"
    locks = "cmd:perm(set) or perm(Builders)"
    help_category = "Building"

    def convert_from_string(self, strobj):
        """
        Converts a single object in *string form* to its equivalent python
        type.

         Python earlier than 2.6:
        Handles floats, ints, and limited nested lists and dicts
        (can't handle lists in a dict, for example, this is mainly due to
        the complexity of parsing this rather than any technical difficulty -
        if there is a need for @set-ing such complex structures on the
        command line we might consider adding it).
         Python 2.6 and later:
        Supports all Python structures through literal_eval as long as they
        are valid Python syntax. If they are not (such as [test, test2], ie
        withtout the quotes around the strings), the entire structure will
        be converted to a string and a warning will be given.

        We need to convert like this since all data being sent over the
        telnet connection by the Player is text - but we will want to
        store it as the "real" python type so we can do convenient
        comparisons later (e.g.  obj.db.value = 2, if value is stored as a
        string this will always fail).
        """

        def rec_convert(obj):
            """
            Helper function of recursive conversion calls. This is only
            used for Python <=2.5. After that literal_eval is available.
            """
            # simple types
            try: return int(obj)
            except ValueError: pass
            try: return float(obj)
            except ValueError: pass
            # iterables
            if obj.startswith('[') and obj.endswith(']'):
                "A list. Traverse recursively."
                return [rec_convert(val) for val in obj[1:-1].split(',')]
            if obj.startswith('(') and obj.endswith(')'):
                "A tuple. Traverse recursively."
                return tuple([rec_convert(val) for val in obj[1:-1].split(',')])
            if obj.startswith('{') and obj.endswith('}') and ':' in obj:
                "A dict. Traverse recursively."
                return dict([(rec_convert(pair.split(":",1)[0]), rec_convert(pair.split(":",1)[1]))
                             for pair in obj[1:-1].split(',') if ":" in pair])
            # if nothing matches, return as-is
            return obj

        if _LITERAL_EVAL:
            # Use literal_eval to parse python structure exactly.
            try:
                return _LITERAL_EVAL(strobj)
            except (SyntaxError, ValueError):
                # treat as string
                string = "{RNote: Value was converted to string. If you don't want this, "
                string += "use proper Python syntax, like enclosing strings in quotes.{n"
                self.caller.msg(string)
                return utils.to_str(strobj)
        else:
            # fall back to old recursive solution (does not support nested lists/dicts)
            return rec_convert(strobj.strip())

    def func(self):
        "Implement the set attribute - a limited form of @py."

        caller = self.caller
        if not self.args:
            caller.msg("Usage: @set obj/attr = value. Use empty value to clear.")
            return

        # get values prepared by the parser
        value = self.rhs
        objname = self.lhs_objattr[0]['name']
        attrs = self.lhs_objattr[0]['attrs']

        obj = caller.search(objname)
        if not obj:
            return

        string = ""
        if not value:
            if self.rhs == None:
                # no = means we inspect the attribute(s)
                if not attrs:
                    attrs = [attr.key for attr in obj.get_all_attributes()]
                for attr in attrs:
                    if obj.has_attribute(attr):
                        string += "\nAttribute %s/%s = %s" % (obj.name, attr, obj.get_attribute(attr))
                    else:
                        string += "\n%s has no attribute '%s'." % (obj.name, attr)
                    # we view it without parsing markup.
                self.caller.msg(string.strip(), data={"raw":True})
                return
            else:
                # deleting the attribute(s)
                for attr in attrs:
                    if obj.has_attribute(attr):
                        val = obj.get_attribute(attr)
                        obj.del_attribute(attr)
                        string += "\nDeleted attribute '%s' (= %s) from %s." % (attr, val, obj.name)
                    else:
                        string += "\n%s has no attribute '%s'." % (obj.name, attr)
        else:
            # setting attribute(s). Make sure to convert to real Python type before saving.
             for attr in attrs:
                try:
                    obj.set_attribute(attr, self.convert_from_string(value))
                    string += "\nCreated attribute %s/%s = %s" % (obj.name, attr, value)
                except SyntaxError:
                    # this means literal_eval tried to parse a faulty string
                    string = "{RCritical Python syntax error in your value. Only primitive Python structures"
                    string += "\nare allowed. You also need to use correct Python syntax. Remember especially"
                    string += "\nto put quotes around all strings inside lists and dicts.{n"
        # send feedback
        caller.msg(string.strip('\n'))


class CmdTypeclass(MuxCommand):
    """
    @typeclass - set object typeclass

    Usage:
      @typclass[/switch] <object> [= <typeclass.path>]
      @type                     ''
      @parent                   ''

    Switch:
      reset - clean out *all* the attributes on the object -
              basically making this a new clean object.
      force - change to the typeclass also if the object
              already has a typeclass of the same name.
    Example:
      @type button = examples.red_button.RedButton

    View or set an object's typeclass. If setting, the creation hooks
    of the new typeclass will be run on the object. If you have
    clashing properties on the old class, use /reset. By default you
    are protected from changing to a typeclass of the same name as the
    one you already have, use /force to override this protection.

    The given typeclass must be identified by its location using
    python dot-notation pointing to the correct module and class. If
    no typeclass is given (or a wrong typeclass is given). Errors in
    the path or new typeclass will lead to the old typeclass being
    kept. The location of the typeclass module is searched from the
    default typeclass directory, as defined in the server settings.

    """

    key = "@typeclass"
    aliases = "@type, @parent"
    locks = "cmd:perm(typeclass) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Implements command"

        caller = self.caller

        if not self.args:
            caller.msg("Usage: @type <object> [=<typeclass]")
            return

        # get object to swap on
        obj = caller.search(self.lhs)
        if not obj:
            return

        if not self.rhs:
            # we did not supply a new typeclass, view the
            # current one instead.
            if hasattr(obj, "typeclass"):
                string = "%s's current typeclass is '%s' (%s)." % (obj.name, obj.typeclass.typename, obj.typeclass.path)
            else:
                string = "%s is not a typed object." % obj.name
            caller.msg(string)
            return

        # we have an =, a typeclass was supplied.
        typeclass = self.rhs

        if not obj.access(caller, 'edit'):
            caller.msg("You are not allowed to do that.")
            return

        if not hasattr(obj, 'swap_typeclass') or not hasattr(obj, 'typeclass'):
            caller.msg("This object cannot have a type at all!")
            return

        is_same = obj.is_typeclass(typeclass)
        if is_same and not 'force' in self.switches:
            string = "%s already has the typeclass '%s'. Use /force to override." % (obj.name, typeclass)
        else:
            reset = "reset" in self.switches
            old_typeclass_path = obj.typeclass.path
            ok = obj.swap_typeclass(typeclass, clean_attributes=reset)
            if ok:
                if is_same:
                    string = "%s updated its existing typeclass (%s).\n" % (obj.name, obj.typeclass.path)
                else:
                    string = "%s's changed typeclass from %s to %s.\n" % (obj.name,
                                                                         old_typeclass_path,
                                                                         obj.typeclass.path)
                string += "Creation hooks were run."
                if reset:
                    string += " All old attributes where deleted before the swap."
                else:
                    string += " Note that the typeclassed object could have ended up with a mixture of old"
                    string += "\nand new attributes. Use /reset to remove old attributes if you don't want this."
            else:
                string = obj.typeclass_last_errmsg
                string += "\nCould not swap '%s' (%s) to typeclass '%s'." % (obj.name,
                                                                          old_typeclass_path,
                                                                          typeclass)

        caller.msg(string)


class CmdWipe(ObjManipCommand):
    """
    @wipe - clears attributes

    Usage:
      @wipe <object>[/attribute[/attribute...]]

    Example:
      @wipe box
      @wipe box/colour

    Wipes all of an object's attributes, or optionally only those
    matching the given attribute-wildcard search string.
    """
    key = "@wipe"
    locks = "cmd:perm(wipe) or perm(Builders)"
    help_category = "Building"

    def func(self):
        """
        inp is the dict produced in ObjManipCommand.parse()
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: @wipe <object>[/attribute/attribute...]")
            return

        # get the attributes set by our custom parser
        objname = self.lhs_objattr[0]['name']
        attrs = self.lhs_objattr[0]['attrs']

        obj = caller.search(objname)
        if not obj:
            return
        if not obj.access(caller, 'edit'):
            caller.msg("You are not allowed to do that.")
            return
        if not attrs:
            # wipe everything
            for attr in obj.get_all_attributes():
                attr.delete()
            string = "Wiped all attributes on %s." % obj.name
        else:
            for attrname in attrs:
                obj.attr(attrname, delete=True )
            string = "Wiped attributes %s on %s."
            string = string % (",".join(attrs), obj.name)
        caller.msg(string)

class CmdLock(ObjManipCommand):
    """
    lock - assign a lock definition to an object

    Usage:
      @lock <object>[ = <lockstring>]
      or
      @lock[/switch] object/<access_type>

    Switch:
      del - delete given access type
      view - view lock associated with given access type (default)

    If no lockstring is given, shows all locks on
    object.

    Lockstring is on the form
       'access_type:[NOT] func1(args)[ AND|OR][ NOT] func2(args) ...]
    Where func1, func2 ... valid lockfuncs with or without arguments.
    Separator expressions need not be capitalized.

    For example:
       'get: id(25) or perm(Wizards)'
    The 'get' access_type is checked by the get command and will
    an object locked with this string will only be possible to
    pick up by Wizards or by object with id 25.

    You can add several access_types after oneanother by separating
    them by ';', i.e:
       'get:id(25);delete:perm(Builders)'
    """
    key = "@lock"
    aliases = ["@locks", "lock", "locks"]
    locks = "cmd: perm(@locks) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Sets up the command"

        caller = self.caller
        if not self.args:
            string = "@lock <object>[ = <lockstring>] or @lock[/switch] object/<access_type>"
            caller.msg(string)
            return
        if '/' in self.lhs:
            # call on the form @lock obj/access_type
            objname, access_type = [p.strip() for p in self.lhs.split('/', 1)]
            obj = caller.search(objname)
            if not obj:
                return
            lockdef = obj.locks.get(access_type)
            if lockdef:
                if 'del' in self.switches:
                    if not obj.access(caller, 'control'):
                        caller.msg("You are not allowed to do that.")
                        return
                    obj.locks.delete(access_type)
                    string = "deleted lock %s" % lockdef
            else:
                string = "%s has no lock of access type '%s'." % (obj, access_type)
            caller.msg(string)
            return

        if self.rhs:
            # we have a = separator, so we are assigning a new lock
            objname, lockdef = self.lhs, self.rhs
            obj = caller.search(objname)
            if not obj:
                return
            if not obj.access(caller, 'control'):
                caller.msg("You are not allowed to do that.")
                return
            ok = obj.locks.add(lockdef, caller)
            if ok:
                caller.msg("Added lock '%s' to %s." % (lockdef, obj))
            return

        # if we get here, we are just viewing all locks
        obj = caller.search(self.lhs)
        if not obj:
            return
        caller.msg(obj.locks)

class CmdExamine(ObjManipCommand):
    """
    examine - detailed info on objects

    Usage:
      examine [<object>[/attrname]]
      examine [*<player>[/attrname]]

    Switch:
      player - examine a Player (same as adding *)

    The examine command shows detailed game info about an
    object and optionally a specific attribute on it.
    If object is not specified, the current location is examined.

    Append a * before the search string to examine a player.

    """
    key = "@examine"
    aliases = ["@ex","ex", "exam", "examine"]
    locks = "cmd:perm(examine) or perm(Builders)"
    help_category = "Building"
    arg_regex = r"(/\w+?(\s|$))|\s|$"

    player_mode = False

    def list_attribute(self, crop, attr, value):
        """
        Formats a single attribute line.
        """
        if crop and isinstance(value, basestring):
            value = utils.crop(value)
            value = repr(value)
        string = "\n %s = %s" % (attr, value)
        string = raw(string)
        return string

    def format_attributes(self, obj, attrname=None, crop=True):
        """
        Helper function that returns info about attributes and/or
        non-persistent data stored on object
        """

        if attrname:
            db_attr = [(attrname, obj.attr(attrname))]
            try:
                ndb_attr = [(attrname, object.__getattribute__(obj.ndb, attrname))]
            except Exception:
                ndb_attr = None
        else:
            if self.player_mode:
                db_attr = [(attr.key, attr.value) for attr in PlayerAttribute.objects.filter(db_obj=obj)]
            else:
                db_attr = [(attr.key, attr.value) for attr in ObjAttribute.objects.filter(db_obj=obj)]
            try:
                ndb_attr = [(aname, avalue) for aname, avalue in obj.ndb.__dict__.items() if not aname.startswith("_")]
            except Exception:
                ndb_attr = None
        string = ""
        if db_attr and db_attr[0]:
            string += "\n{wPersistent attributes{n:"
            for attr, value in db_attr:
                string += self.list_attribute(crop, attr, value)
        if ndb_attr and ndb_attr[0]:
            string += "\n{wNon-Persistent attributes{n:"
            for attr, value in ndb_attr:
                string += self.list_attribute(crop, attr, value)
        return string

    def format_output(self, obj, avail_cmdset):
        """
        Helper function that creates a nice report about an object.

        returns a string.
        """

        string = "\n{wName/key{n: {c%s{n (%s)" % (obj.name, obj.dbref)
        if hasattr(obj, "aliases") and obj.aliases:
            string += "\n{wAliases{n: %s" % (", ".join(utils.make_iter(obj.aliases)))
        if hasattr(obj, "has_player") and obj.has_player:
            string += "\n{wPlayer{n: {c%s{n" % obj.player.name
            perms = obj.player.permissions
            if obj.player.is_superuser:
                perms = ["<Superuser>"]
            elif not perms:
                perms = ["<None>"]
            string += "\n{wPlayer Perms{n: %s" % (", ".join(perms))
        string += "\n{wTypeclass{n: %s (%s)" % (obj.typeclass.typename, obj.typeclass_path)
        if hasattr(obj, "location"):
            string += "\n{wLocation{n: %s" % obj.location
            if obj.location:
                string += " (#%s)" % obj.location.id
        if hasattr(obj, "destination"):
            string += "\n{wDestination{n: %s" % obj.destination
            if obj.destination:
                string += " (#%s)" % obj.destination.id
        perms = obj.permissions
        if perms:
            perms_string = (", ".join(perms))
        else:
            perms_string = "Default"
        string += "\n{wPermissions{n: %s" % perms_string
        locks = str(obj.locks)
        if locks:
            locks_string = utils.fill("; ".join([lock for lock in locks.split(';')]), indent=6)
        else:
            locks_string = " Default"
        string += "\n{wLocks{n:%s" % locks_string

        if not (len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "Empty"):
            # list the current cmdsets
            all_cmdsets = obj.cmdset.all() + (hasattr(obj, "player") and obj.player and obj.player.cmdset.all() or [])
            all_cmdsets.sort(key=lambda x:x.priority, reverse=True)
            string += "\n{wCurrent Cmdset(s){n:\n %s" % ("\n ".join("%s (prio %s)" % (cmdset.path, cmdset.priority) for cmdset in all_cmdsets))

            # list the commands available to this object
            avail_cmdset = sorted([cmd.key for cmd in avail_cmdset if cmd.access(obj, "cmd")])

            cmdsetstr = utils.fill(", ".join(avail_cmdset), indent=2)
            string += "\n{wCommands available to %s (all cmdsets + exits and external cmds){n:\n %s" % (obj.key, cmdsetstr)

        if hasattr(obj, "scripts") and hasattr(obj.scripts, "all") and obj.scripts.all():
            string += "\n{wScripts{n:\n %s" % obj.scripts
        # add the attributes
        string += self.format_attributes(obj)
        # add the contents
        exits = []
        pobjs = []
        things = []
        if hasattr(obj, "contents"):
            for content in obj.contents:
                if content.destination:
                    exits.append(content)
                elif content.player:
                    pobjs.append(content)
                else:
                    things.append(content)
            if exits:
                string += "\n{wExits{n: %s" % ", ".join([exit.name for exit in exits])
            if pobjs:
                string += "\n{wCharacters{n: %s" % ", ".join(["{c%s{n" % pobj.name for pobj in pobjs])
            if things:
                string += "\n{wContents{n: %s" % ", ".join([cont.name for cont in obj.contents
                                                           if cont not in exits and cont not in pobjs])
        separater = "="*78
        #output info
        return '%s\n%s\n%s' % ( separater, string.strip(), separater )

    def func(self):
        "Process command"
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
            caller.msg(string.strip())

        if not self.args:
            # If no arguments are provided, examine the invoker's location.
            obj = caller.location
            if not obj.access(caller, 'examine'):
            #If we don't have special info access, just look at the object instead.
                caller.execute_cmd('look %s' % obj.name)
                return
            # using callback for printing result whenever function returns.
            get_and_merge_cmdsets(obj).addCallback(get_cmdset_callback)
            return

        # we have given a specific target object
        for objdef in self.lhs_objattr:

            obj_name = objdef['name']
            obj_attrs = objdef['attrs']


            self.player_mode = "player" in self.switches or obj_name.startswith('*')

            obj = caller.search(obj_name, player=self.player_mode, global_dbref=True)
            if not obj:
                continue

            if not obj.access(caller, 'examine'):
                #If we don't have special info access, just look at the object instead.
                caller.execute_cmd('look %s' % obj_name)
                continue

            if obj_attrs:
                for attrname in obj_attrs:
                    # we are only interested in specific attributes
                    caller.msg(self.format_attributes(obj, attrname, crop=False))
            else:
                # using callback to print results whenever function returns.
                get_and_merge_cmdsets(obj).addCallback(get_cmdset_callback)


class CmdFind(MuxCommand):
    """
    find objects

    Usage:
      @find[/switches] <name or dbref or *player> [= dbrefmin[-dbrefmax]]

    Switches:
      room - only look for rooms (location=None)
      exit - only look for exits (destination!=None)
      char - only look for characters (BASE_CHARACTER_TYPECLASS)

    Searches the database for an object of a particular name or dbref.
    Use *playername to search for a player. The switches allows for
    limiting object matches to certain game entities. Dbrefmin and dbrefmax
    limits matches to within the given dbrefs, or above/below if only one is given.
    """

    key = "@find"
    aliases = "find, @search, search, @locate, locate"
    locks = "cmd:perm(find) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Search functionality"
        caller = self.caller
        switches = self.switches

        if not self.args:
            caller.msg("Usage: @find <string> [= low [-high]]")
            return

        searchstring = self.lhs
        low, high = 1, ObjectDB.objects.all().order_by("-id")[0].id
        if self.rhs:
            if "-" in self.rhs:
                # also support low-high syntax
                limlist = [part.strip() for part in self.rhs.split("-", 1)]
            else:
                # otherwise split by space
                limlist = self.rhs.split(None, 1)
            if limlist and limlist[0].isdigit():
                low = max(low, int(limlist[0]))
            if len(limlist) > 1 and limlist[1].isdigit():
                high = min(high, int(limlist[1]))
        low = min(low, high)
        high = max(low, high)

        if searchstring.startswith("*") or utils.dbref(searchstring):
            # A player/dbref search.
            # run a normal player- or dbref search. This should be unique.

            string = "{wMatch{n(#%i-#%i):" % (low, high)

            result = caller.search(searchstring, global_search=True)
            if not result:
                return
            if not low <= int(result.id) <= high:
                string += "\n   {RNo match found for '%s' within the given dbref limits.{n" % searchstring
            else:
                string += "\n{g   %s(%s) - %s{n" % (result.key, result.dbref, result.typeclass.path)
        else:
            # Not a player/dbref search but a wider search; build a queryset.

            results = ObjectDB.objects.filter(db_key__istartswith=searchstring, id__gte=low, id__lte=high)
            if "room" in switches:
                results = results.filter(db_location__isnull=True)
            if "exit" in switches:
                results = results.filter(db_destination__isnull=False)
            if "char" in switches:
                results = results.filter(db_typeclass_path=CHAR_TYPECLASS)
            nresults = results.count()
            if not nresults:
                # no matches on the keys. Try aliases instead.
                results = results = ObjectDB.alias_set.related.model.objects.filter(db_key=searchstring)
                if "room" in switches:
                    results = results.filter(db_obj__db_location__isnull=True)
                if "exit" in switches:
                    results = results.filter(db_obj__db_destination__isnull=False)
                if "char" in switches:
                    results = results.filter(db_obj__db_typeclass_path=CHAR_TYPECLASS)
                # we have to parse alias -> real object here
                results = [result.db_obj for result in results]
                nresults = len(results)

            restrictions = ""
            if self.switches:
                restrictions = ", %s" % (",".join(self.switches))
            if nresults:
                # convert result to typeclasses.
                results = [result.typeclass for result in results]
                if nresults > 1:
                    string = "{w%i Matches{n(#%i-#%i%s):" % (nresults, low, high, restrictions)
                    for res in results:
                        string += "\n   {g%s(%s) - %s{n" % (res.key, res.dbref, res.path)
                else:
                    string = "{wOne Match{n(#%i-#%i%s):" % (low, high, restrictions)
                    string += "\n   {g%s(%s) - %s{n" % (results[0].key, results[0].dbref, results[0].path)
            else:
                string = "{wMatch{n(#%i-#%i%s):" % (low, high, restrictions)
                string += "\n   {RNo matches found for '%s'{n" % searchstring

        # send result
        caller.msg(string.strip())


class CmdTeleport(MuxCommand):
    """
    teleport object to another location

    Usage:
      @tel/switch [<object> =] <target location>

    Examples:
      @tel Limbo
      @tel/quiet box Limbo
      @tel/tonone box

    Switches:
      quiet  - don't echo leave/arrive messages to the source/target
               locations for the move.
      intoexit - if target is an exit, teleport INTO
                 the exit object instead of to its destination
      tonone - if set, teleport the object to a None-location. If this
               switch is set, <target location> is ignored.
               Note that the only way to retrieve
               an object from a None location is by direct #dbref
               reference.

    Teleports an object somewhere. If no object is given, you yourself
    is teleported to the target location.     """
    key = "@tel"
    aliases = "@teleport"
    locks = "cmd:perm(teleport) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Performs the teleport"

        caller = self.caller
        args = self.args
        lhs, rhs = self.lhs, self.rhs
        switches = self.switches

        # setting switches
        tel_quietly = "quiet" in switches
        to_none = "tonone" in switches

        if to_none:
            # teleporting to None
            if not args:
                obj_to_teleport = caller
                caller.msg("Teleported to None-location.")
                if caller.location and not tel_quietly:
                    caller.location.msg_contents("%s teleported into nothingness." % caller, exclude=caller)
            else:
                obj_to_teleport = caller.search(lhs, global_search=True)
                if not obj_to_teleport:
                    caller.msg("Did not find object to teleport.")
                    return
                caller.msg("Teleported %s -> None-location." % obj_to_teleport)
                if obj_to_teleport.location and not tel_quietly:
                    obj_to_teleport.location.msg_contents("%s teleported %s into nothingness."
                                                          % (caller, obj_to_teleport),
                                                          exclude=caller)
            obj_to_teleport.location=None
            return

        # not teleporting to None location
        if not args and not to_none:
            caller.msg("Usage: teleport[/switches] [<obj> =] <target_loc>|home")
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
        if obj_to_teleport == destination:
            caller.msg("You can't teleport an object inside of itself!")
            return
        if obj_to_teleport.location and obj_to_teleport.location == destination:
            caller.msg("%s is already at %s." % (obj_to_teleport, destination))
            return
        use_destination = True
        if "intoexit" in self.switches:
            use_destination = False

        # try the teleport
        if obj_to_teleport.move_to(destination, quiet=tel_quietly, emit_to_obj=caller,
                                   use_destination=use_destination):
            if obj_to_teleport == caller:
                caller.msg("Teleported to %s." % destination)
            else:
                caller.msg("Teleported %s -> %s." % (obj_to_teleport, destination))


class CmdScript(MuxCommand):
    """
    attach scripts

    Usage:
      @script[/switch] <obj> [= <script.path or scriptkey>]

    Switches:
      start - start all non-running scripts on object, or a given script only
      stop - stop all scripts on objects, or a given script only

    If no script path/key is given, lists all scripts active on the given
    object.
    Script path can be given from the base location for scripts as given in
    settings. If adding a new script, it will be started automatically (no /start
    switch is needed). Using the /start or /stop switches on an object without
    specifying a script key/path will start/stop ALL scripts on the object.
    """

    key = "@script"
    aliases = "@addscript"
    locks = "cmd:perm(script) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Do stuff"

        caller = self.caller

        if not self.args:
            string = "Usage: @script[/switch] <obj> [= <script.path or script key>]"
            caller.msg(string)
            return

        obj = caller.search(self.lhs)
        if not obj:
            return

        string = ""
        if not self.rhs:
            # no rhs means we want to operate on all scripts
            scripts = obj.scripts.all()
            if not scripts:
                string += "No scripts defined on %s." % obj.key
            elif not self.switches:
                # view all scripts
                from src.commands.default.system import format_script_list
                string += format_script_list(scripts)
            elif "start" in self.switches:
                num = sum([obj.scripts.start(script.key) for script in scripts])
                string += "%s scripts started on %s." % (num, obj.key)
            elif "stop" in self.switches:
                for script in scripts:
                    string += "Stopping script %s on %s." % (script.key, obj.key)
                    script.stop()
                string = string.strip()
            obj.scripts.validate()
        else: # rhs exists
            if not self.switches:
                # adding a new script, and starting it
                ok = obj.scripts.add(self.rhs, autostart=True)
                if not ok:
                    string += "\nScript %s could not be added and/or started on %s." % (self.rhs, obj.key)
                else:
                    string = "Script {w%s{n successfully added and started on %s." % (self.rhs, obj.key)

            else:
                paths = [self.rhs] + ["%s.%s" % (prefix, self.rhs)
                                      for prefix in settings.SCRIPT_TYPECLASS_PATHS]
                if "stop" in self.switches:
                    # we are stopping an already existing script
                    for path in paths:
                        ok = obj.scripts.stop(path)
                        if not ok:
                            string += "\nScript %s could not be stopped. Does it exist?" % path
                        else:
                            string = "Script stopped and removed from object."
                            break
                if "start" in self.switches:
                    # we are starting an already existing script
                    for path in paths:
                        ok = obj.scripts.start(path)
                        if not ok:
                            string += "\nScript %s could not be (re)started." % path
                        else:
                            string = "Script started successfully."
                            break
        caller.msg(string.strip())
