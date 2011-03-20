"""

Building and world design commands

"""

from django.conf import settings 
from src.objects.models import ObjectDB, ObjAttribute
from src.utils import create, utils, debug 
from src.commands.default.muxcommand import MuxCommand

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
    are simpler and appear in combinations

        objname/attr/attr/attr, objname/attr, ...             

    Stores four new attributes with the parsed data. 

    """
    #OBS - this is just a parent - it's not intended to 
    #actually be included in a commandset on its own!
    
    def parse(self):
        """
        We need to expand the default parsing to get all 
        the cases, see the module doc.         
        """
        # get all the normal parsing done (switches etc)
        super(ObjManipCommand, self).parse()

        lhs_objs = []
        rhs_objs = []

        #first, we deal with the left hand side of an eventual =
        for objdef in self.lhslist:
            #lhslist is already split by ','
            aliases, option = [], None
            if ':' in objdef:
                objdef, option = [str(part).strip() 
                                     for part in objdef.rsplit(':', 1)]
            if ';' in objdef:
                objdef, aliases = [str(part).strip() 
                                   for part in objdef.split(';', 1)]
                aliases = [str(alias).strip() 
                           for alias in aliases.split(';') if alias.strip()]
            lhs_objs.append({"name":objdef, 
                             'option': option, 'aliases': aliases})

        #next, the right hand side of =
        for objdef in self.rhslist:
            #rhslist is already split by ','
            aliases, option = [], None
            if ':' in objdef:
                objdef, option = [str(part).strip() 
                                     for part in objdef.rsplit(':', 1)]
            if ';' in objdef:
                objdef, aliases = [str(part).strip() 
                                   for part in objdef.split(';', 1)]
                aliases = [str(alias).strip() 
                           for alias in aliases.split(';') if alias.strip()]
            rhs_objs.append({"name":objdef, 'option': option, 'aliases': aliases})
        
        # We make a second sweep to handle attributes-on-objects 
        lhs_objattr = []
        rhs_objattr = []
        
        # first left hand side
        for objdef in self.lhslist:
            attrs = []
            if '/' in objdef:
                objdef, attrs = [str(part).strip() 
                                 for part in objdef.split('/', 1)] 
                attrs = [str(part).strip().lower() 
                         for part in attrs.split('/') if part.strip()]
            lhs_objattr.append({"name":objdef, 'attrs':attrs})
        # right hand side
        for objdef in self.rhslist:
            attrs = []
            if '/' in objdef:
                objdef, attrs = [str(part).strip() 
                                 for part in objdef.split('/', 1)] 
                attrs = [str(part).strip().lower() 
                         for part in attrs.split('/') if part.strip()]
            rhs_objattr.append({"name":objdef, 'attrs':attrs})
            
        self.lhs_objs = lhs_objs
        self.rhs_objs = rhs_objs
        self.lhs_objattr = lhs_objattr
        self.rhs_objattr = rhs_objattr 


class CmdSetObjAlias(MuxCommand):   
    """
    Adding permanent aliases

    Usage:
      @alias <obj> = [alias[,alias,alias,...]]

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
        objname, aliases = self.lhs, self.rhslist
        if not objname:
            caller.msg("Usage: @alias <obj> = <alias>,<alias>,...")
            return        
        # Find the object to receive aliases
        obj = caller.search(objname, global_search=True)
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
        if not aliases or not aliases[0]:
            # we have given an empty =, so delete aliases
            old_aliases = obj.aliases
            if old_aliases:
                caller.msg("Cleared aliases from %s: %s" % (obj.key, ", ".join(old_aliases)))
                del obj.dbobj.aliases # TODO: del does not understand indirect typeclass reference!
            else:
                caller.msg("No aliases to clear.")
            return 
        # merge the old and new aliases (if any)
        old_aliases = obj.aliases
        new_aliases = [str(alias).strip().lower() 
                       for alias in aliases if alias.strip()]
        # make the aliases only appear once 
        old_aliases.extend(new_aliases)
        aliases = list(set(old_aliases))        
        # save back to object.
        obj.aliases = aliases 
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
            caller.msg("Usage: @copy <obj> [=new_name[;alias;alias..]][:new_location]") 
            return
    
        if not self.rhs:
            # this has no target =, so an identical new object is created. 
            from_obj_name = self.args            
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return             
            to_obj_name = "%s_copy" % from_obj_name
            to_obj_aliases = from_obj.aliases 
            to_obj_location = from_obj.location            
            copiedobj = ObjectDB.objects.copy_object(from_obj, to_obj_name, 
                                                     to_obj_location, to_obj_aliases) 
            if copiedobj:
                string = "Identical copy of %s, named '%s' was created." % (to_obj_name, to_obj_name)
            else:
                string = "There was an error copying %s."
        else:
            # we have specified =. This might mean many object targets 
            from_obj_name = self.lhs_objs[0]['name']
            from_obj = caller.search(from_obj_name)
            if not from_obj:
                return             
            for objdef in self.lhs_objs:                
                # loop through all possible copy-to targets                
                to_obj_name = objdef['name']
                to_obj_aliases = objdef['aliases']
                to_obj_location = objdef['option']
                copiedobj = ObjectDB.objects.copy_object(from_obj, to_obj_name, 
                                                         to_obj_location, to_obj_aliases)                 
                if copiedobj:
                    string = "Copied %s to '%s' (aliases: %s)." % (from_obj_name, to_obj_name,
                                                                 to_obj_aliases)
                else:
                    string = "There was an error copying %s to '%s'." % (from_obj_name, 
                                                                         to_obj_name)
        # we are done, echo to user
        caller.msg(string)

# NOT YET INCLUDED IN SET.
class CmdCpAttr(MuxCommand):
    """
    @cpattr - copy attributes

    Usage:    
      @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
      @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
      @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]

    Example:
      @cpattr coolness = Anna/chillout, Anna/nicety, Tom/nicety
      ->
      copies the coolness attribute (defined on yourself), to attributes
      on Anna and Tom. 

    Copy the attribute one object to one or more attributes on another object.
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
            @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
            @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
            @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]"""
            caller.msg(string)
            return

        lhs_objattr = self.lhs_objattr
        to_objs = self.rhs_objattr
        from_obj_name = lhs_objattr[0]['name']
        from_obj_attrs = lhs_objattr[0]['attrs']

        if not from_obj_attrs:
            # this means the from_obj_name is actually an attribute name on self.
            from_obj_attrs = [from_obj_name]
            from_obj = self
            from_obj_name = self.name
        else:
            from_obj = caller.search(from_obj_name)
        if not from_obj or not to_objs:
            caller.msg("Have to supply both source object and target(s).")
            return 
        srcvalue = from_obj.attr(from_obj_attrs[0])

        #copy to all to_obj:ects
        string = "Copying %s=%s (with value %s) ..." % (from_obj_name,
                                                        from_obj_attrs[0], srcvalue)
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
                to_obj.attr(to_attr, srcvalue)            
                string += "\nCopied %s.%s -> %s.%s." % (from_obj.name, from_attr,
                                                        to_obj_name, to_attr)
        caller.msg(string)



class CmdCreate(ObjManipCommand):
    """
    @create - create new objects

    Usage:
      @create[/drop] objname[;alias;alias...][:typeclass], objname...

    switch:
       drop - automatically drop the new object into your current location (this is not echoed)

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
            
            # analyze typeclass. If it starts at the evennia basedir,
            # (i.e. starts with game or src) we let it be, otherwise we 
            # add a base path as defined in settings
            if typeclass and not (typeclass.startswith('src.') or 
                                  typeclass.startswith('game.')):
                typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                       typeclass)
                
            # create object (if not a valid typeclass, the default
            # object typeclass will automatically be used)

            lockstring = "owner:id(%s);examine:perm(Builders);delete:id(%s) or perm(Wizards);get:all()" % (caller.id, caller.id)
            obj = create.create_object(typeclass, name, caller, 
                                       home=caller, aliases=aliases, locks=lockstring)
            if not obj:
                string = "Error when creating object."
                continue
            if aliases: 
                string = "You create a new %s: %s (aliases: %s)."
                string = string % (obj.typeclass, obj.name, ", ".join(aliases))
            else:
                string = "You create a new %s: %s."
                string = string % (obj.typeclass, obj.name)
            # set a default desc
            if not obj.db.desc:
                obj.db.desc = "You see nothing special."
            if 'drop' in self.switches:    
                if caller.location:
                    obj.move_to(caller.location, quiet=True)
        caller.msg(string)


#TODO: make @debug more clever with arbitrary hooks? 
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
    It creates the given object and runs tests on its hooks. You can 
    supply both full paths (starting from the evennia base directory),
    otherwise the system will start from the defined root directory
    for scripts and objects respectively (defined in settings file). 

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
            # analyze path. If it starts at the evennia basedir,
            # (i.e. starts with game or src) we let it be, otherwise we 
            # add a base path as defined in settings
            if path and not (path.startswith('src.') or 
                                  path.startswith('game.')):
                path = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                       path)

            # create and debug the object
            self.caller.msg(debug.debug_object(path, self.caller))
            self.caller.msg(debug.debug_object_scripts(path, self.caller))

        elif 'script' in self.switches:
            # analyze path. If it starts at the evennia basedir,
            # (i.e. starts with game or src) we let it be, otherwise we 
            # add a base path as defined in settings
            if path and not (path.startswith('src.') or 
                                  path.startswith('game.')):
                path = "%s.%s" % (settings.BASE_SCRIPT_PATH, 
                                       path)
            
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
            obj = caller
            desc = self.args
        # storing the description
        obj.db.desc = desc 
        caller.msg("The description was set on %s." % obj.key)


class CmdDestroy(MuxCommand):
    """
    @destroy - remove objects from the game
    
    Usage: 
       @destroy[/<switches>] obj [,obj2, obj3, ...]
       @delete             '' 

    switches:
       override - The @destroy command will usually avoid accidentally destroying
                  player objects. This switch overrides this safety.            

    Destroys one or many objects. 
    """

    key = "@destroy"
    aliases = "@delete"
    locks = "cmd:perm(destroy) or perm(Builders)"
    help_category = "Building"

    def func(self):
        "Implements the command."

        caller = self.caller

        if not self.args or not self.lhslist:
            caller.msg("Usage: @destroy[/switches] obj [,obj2, obj3, ...]")
            return    

        string = ""
        for objname in self.lhslist:
            obj = caller.search(objname)
            if not obj:                
                continue
            objname = obj.name
            if obj.player and not 'override' in self.switches:
                string = "Object %s is a player object. Use /override to delete anyway." % objname
                continue 
            if not obj.access(caller, 'delete'):
                string = "You don't have permission to delete %s." % objname
                continue
            # do the deletion
            okay = obj.delete()
            if not okay:
                string = "ERROR: %s NOT deleted, probably because at_obj_delete() returned False." % objname
            else:
                string = "%s was deleted." % objname
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
       teleport - move yourself to the new room

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

        # analyze typeclass path. If it starts at the evennia basedir,
        # (i.e. starts with game or src) we let it be, otherwise we 
        # add a base path as defined in settings
        if typeclass and not (typeclass.startswith('src.') or 
                              typeclass.startswith('game.')):
            typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                   typeclass)
          
        new_room = create.create_object(typeclass, room["name"],
                                        aliases=room["aliases"])
        room_string = "Created room '%s' of type %s." % (new_room.name, typeclass)

        exit_to_string = ""
        exit_back_string = ""
                
        if self.rhs_objs:
            to_exit = self.rhs_objs[0]             
            if not to_exit["name"]:
                exit_to_string = \
                    "\nYou didn't give a name for the exit to the new room."
            elif not location:
                exit_to_string = \
                  "\nYou cannot create an exit from a None-location."    
            else:
                # Build the exit to the new room from the current one
                typeclass = to_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS                            
                # analyze typeclass. If it starts at the evennia basedir,
                # (i.e. starts with game or src) we let it be, otherwise we 
                # add a base path as defined in settings
                if typeclass and not (typeclass.startswith('src.') or 
                                      typeclass.startswith('game.')):
                    typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                           typeclass)
                new_to_exit = create.create_object(typeclass, to_exit["name"],
                                                   location,
                                                   aliases=to_exit["aliases"])
                new_to_exit.db._destination = new_room
                exit_to_string = "\nCreated new Exit to new room:  %s (aliases: %s)."
                exit_to_string = exit_to_string % (new_to_exit.name,
                                                   new_to_exit.aliases)
                
        if len(self.rhs_objs) > 1:
            # Building the exit back to the current room 
            back_exit = self.rhs_objs[1]
            if not back_exit["name"]:
                exit_back_string = \
                    "\nYou didn't give a name for the exit back here."            
            elif not location:
                exit_back_string = \
                   "\nYou cannot create an exit back to a None-location." 
            else:
                typeclass = back_exit["option"]
                if not typeclass:
                    typeclass = settings.BASE_EXIT_TYPECLASS
                # analyze typeclass. If it starts at the evennia basedir,
                # (i.e. starts with game or src) we let it be, otherwise we 
                # add a base path as defined in settings
                if typeclass and not (typeclass.startswith('src.') or 
                                      typeclass.startswith('game.')):
                    typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                           typeclass)
                new_back_exit = create.create_object(typeclass, back_exit["name"],
                                                     new_room,
                                                     aliases=back_exit["aliases"])
                new_back_exit.db._destination = location
                exit_back_string = "\nExit back from new room: %s (aliases: %s)." 
                exit_back_string = exit_back_string % (new_back_exit.name,
                                                       new_back_exit.aliases)
        caller.msg("%s%s%s" % (room_string, exit_to_string, exit_back_string))
        if new_room and 'teleport' in self.switches:
            caller.move_to(new_room)


class CmdLink(MuxCommand):    
    """
    @link - connect objects

    Usage:
      @link[/switches] <object> = <target>
      @link[/switches] <object> = 
      @link[/switches] <object> 
      
    Switches:
      twoway  - this is only useful when both <object> 
                and <target> are Exits. If so, a link back
                from <target> to <object> will also be created.      


    If <object> is an exit, set its destination. For all other object types, this
    command sets the object's Home. 
    The second form sets the destination/home to None and the third form inspects
    the current value of destination/home on <object>.
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
            # if obj is an exit (has db attribute _destination),
            # set that, otherwise set home.
            if obj.db._destination: 
                obj.db._destination = target
                if "twoway" in self.switches:                    
                    if target.db._destination:
                        target.db._destination = obj                        
                        string = "Link created %s <-> %s (two-way)." % (obj.name, target.name)
                    else:
                        string = "Cannot create two-way link to non-exit."
                        string += " Link created %s -> %s (one way)." % (obj.name, target.name)
                else:
                    string = "Link created %s -> %s (one way)." % (obj.name, target.name)
            else:
                # obj is not an exit (has not attribute _destination), 
                # so set home instead
                obj.home = target 
                string = "Set %s's home to %s." % (obj.name, target.name) 

        elif self.rhs == None:
            # this means that no = was given (otherwise rhs 
            # would have been an empty string). So we inspect
            # the home/destination on object
            dest = obj.db._destination
            if dest:
                "%s is an exit to %s." % (obj.name, dest.name)
            else:
                string = "%s has home %s." % (obj.name, obj.home)
        else:
            # We gave the command @link 'obj = ' which means we want to
            # clear _destination or set home to None.             
            if obj.db._destination:
                obj.db._destination = "None" # it can't be None, or _destination would 
                                             # be deleted and obj cease being an exit!
                string = "Exit %s no longer links anywhere." % obj.name
            else:
                obj.home = None
                string = "%s no longer has a home." % obj.name
        # give feedback
        caller.msg(string)

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


class CmdMvAttr(ObjManipCommand):
    """
    @mvattr - move attributes

    Usage:
      @mvattr <srcobject>/attr[/attr/attr...] = <targetobject>[/attr/attr/...]

    Moves attributes around. If the target object's attribute names are given,
    the source attributes will be moved into those attributes instead. The
    old attribute(s) will be deleted from the source object (unless source
    and target are the same, in which case this is like a copy operation)
    """
    key = "@mvattr"
    locks = "cmd:perm(mvattr) or perm(Builders)"
    help_category = "Building"
    
    def func(self):
        "We use the parsed values from ObjManipCommand.parse()."

        caller = self.caller
        
        if not self.lhs or not self.rhs:
            caller.msg("Usage: @mvattr <src>/attr[/attr/..] = <target>[/attr/attr..]")
            return 

        from_obj_name = self.lhs_objattr[0]['name']
        from_obj_attrs = self.lhs_objattr[0]['attrs']
        to_obj_name = self.rhs_objattr[0]['name']
        to_obj_attrs = self.rhs_objattr[0]['name']
        
        # find from-object
        from_obj = caller.search(from_obj_name)
        if not from_obj:
            return 
        #find to-object
        to_obj = caller.search_for_object(to_obj_name)
        if not to_obj:
            return

        # if we copy on the same object, we have to 
        # be more careful. 
        same_object = to_obj == from_obj

        #do the moving
        string = ""
        for inum, from_attr in enumerate(from_obj_attrs):
            from_value = from_obj.attr(from_attr)
            if not from_value:
                string += "\nAttribute '%s' not found on source object %s." 
                string = string % (from_attr, from_obj.name)
            else:
                try:
                    to_attr = to_obj_attrs[inum]
                except KeyError:
                    # too few attributes on the target, so we add the
                    # source attrname instead
                    if same_object:
                        # we can't do that on the same object though,
                        # it would be just copying to itself.
                        string += "\nToo few attribute names on target, and "
                        string += "can't copy same-named attribute to itself."
                        continue 
                    to_attr = from_attr
                # Do the move
                to_obj.attr(to_attr, from_value)
                from_obj.attr(from_attr, delete=True)
                string += "\nMoved %s.%s -> %s.%s." % (from_obj_name, from_attr,
                                                       to_obj_name, to_attr)
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
        caller.msg("Object's name changed to '%s'%s." % (newname, astring))


class CmdOpen(ObjManipCommand):            
    """    
    @open - create new exit
    
    Usage:
      @open <new exit>[;alias;alias..][:typeclass] = <destination> [,<return exit>[;alias;..][:typeclass]]]  

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
            if not exit_obj.db._destination:
                # we are trying to link a non-exit
                string = "'%s' already exists and is not an exit!\nIf you want to convert it "
                string += "to an exit, you must assign it an attribute '_destination' first."
                caller.msg(string % exit_name)
                return None
            # we are re-linking an old exit.
            old_destination = exit_obj.db._destination
            if old_destination:
                string = "Exit %s already exists." % exit_name
                if old_destination.id != destination.id:
                    # reroute the old exit.
                    exit_obj.db._destination = destination
                    exit_obj.aliases = exit_aliases
                    string += " Rerouted its old destination '%s' to '%s' and changed aliases." % \
                        (old_destination.name, destination.name)                
                else:
                    string += " It already points to the correct place."

        else:
            # exit does not exist before. Create a new one.            
            exit_obj = create.create_object(typeclass, key=exit_name,
                                            location=location,
                                            aliases=exit_aliases)
            if exit_obj:  
                # storing an attribute _destination is what makes it an exit!
                exit_obj.db._destination = destination
                string = "Created new Exit '%s' to %s (aliases: %s)." % (exit_name,
                                                                         destination.name,
                                                                         exit_aliases)
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
            string = "Usage: @open <new exit>[;alias;alias...][:typeclass] "
            string += "= <destination [,<return exit>[;alias..][:typeclass]]]"
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

        # analyze typeclass. If it starts at the evennia basedir,
        # (i.e. starts with game or src) we let it be, otherwise we 
        # add a base path as defined in settings
        if exit_typeclass and not (exit_typeclass.startswith('src.') or 
                                   exit_typeclass.startswith('game.')):
            exit_typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                        exit_typeclass)
 
        dest_name = self.rhs_objs[0]['name']
        
        # first, check so the destination exists.
        destination = caller.search(dest_name, global_search=True)
        if not destination:
            return 

        # Create exit
        
        ok = self.create_exit(exit_name, location, destination, exit_aliases, exit_typeclass)
        if not ok:
            # an error; the exit was not created, so we quit.
            return 

        # We are done with exit creation. Check if we want a return-exit too.

        if len(self.rhs_objs) > 1:            
            back_exit_name = self.rhs_objs[1]['name']
            back_exit_aliases = self.rhs_objs[1]['name']
            back_exit_typeclass = self.rhs_objs[1]['option']

            # analyze typeclass. If it starts at the evennia basedir,
            # (i.e. starts with game or src) we let it be, otherwise we 
            # add a base path as defined in settings
            if back_exit_typeclass and not (back_exit_typeclass.startswith('src.') or 
                                            back_exit_typeclass.startswith('game.')):
                back_exit_typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                                 back_exit_typeclass)            
            # Create the back-exit
            self.create_exit(back_exit_name, destination, location, 
                             back_exit_aliases, back_exit_typeclass)


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
    """

    key = "@set"
    locks = "cmd:perm(set) or perm(Builders)"
    help_category = "Building"
    
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
                for attr in attrs:
                    if obj.has_attribute(attr):
                        string += "\nAttribute %s/%s = %s" % (obj.name, attr, obj.get_attribute(attr))
                    else:
                        string += "\n%s has no attribute '%s'." % (obj.name, attr)
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
            # setting attribute(s)
            for attr in attrs:
                obj.set_attribute(attr, value)
                string += "\nCreated attribute %s/%s = %s" % (obj.name, attr, value)
        # send feedback
        caller.msg(string.strip('\n')) 


class CmdTypeclass(MuxCommand):
    """
    @typeclass - set object typeclass 

    Usage:     
      @typclass[/switch] <object> [= <typeclass path>]
      @type           ''
      @parent         ''

    Switch:
      reset - clean out *all* the attributes on the object - 
              basically making this a new clean object. 
      force - change to the typeclass also if the object
              already has a typeclass of the same name.      
    Example:
      @type button = examples.red_button.RedButton
      
    Sets an object's typeclass. The typeclass must be identified
    by its location using python dot-notation pointing to the correct
    module and class. If no typeclass is given (or a wrong typeclass
    is given), the object will be set to the default typeclass.
    The location of the typeclass module is searched from
    the default typeclass directory, as defined in the server settings.

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
                string = "%s's current typeclass is '%s'." % (obj.name, obj.typeclass)
            else:
                string = "%s is not a typed object." % obj.name
            caller.msg(string)
            return 

        # we have an =, a typeclass was supplied.
        typeclass = self.rhs

        # analyze typeclass. If it starts at the evennia basedir,
        # (i.e. starts with game or src) we let it be, otherwise we 
        # add a base path as defined in settings
        if typeclass and not (typeclass.startswith('src.') or 
                              typeclass.startswith('game.')):
            typeclass = "%s.%s" % (settings.BASE_TYPECLASS_PATH, 
                                   typeclass)

        if not obj.access(caller, 'edit'):
            caller.msg("You are not allowed to do that.")
            return 

        if not hasattr(obj, 'swap_typeclass') or not hasattr(obj, 'typeclass'):
            caller.msg("This object cannot have a type at all!")
            return 

        reset = "reset" in self.switches
        
        old_typeclass = obj.typeclass_path
        if old_typeclass == typeclass and not 'force' in self.switches:
            string = "%s already has the typeclass '%s'." % (obj.name, typeclass)
        else:
            obj.swap_typeclass(typeclass, clean_attributes=reset)        
            new_typeclass = obj.typeclass
            string = "%s's type is now %s (instead of %s).\n" % (obj.name, 
                                                                   new_typeclass, 
                                                                   old_typeclass)            
            if reset:
                string += "All attributes where reset."                                                               
            else:    
                string += "Note that the new class type could have overwritten "
                string += "same-named attributes on the existing object."            
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
                string = lockdef[2]
                if 'del' in self.switches:
                    if not obj.access(caller, 'control'):
                        caller.msg("You are not allowed to do that.")
                        return 
                    obj.locks.delete(access_type)
                    string = "deleted lock %s" % string 
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

    The examine command shows detailed game info about an
    object and optionally a specific attribute on it. 
    If object is not specified, the current location is examined. 
    """
    key = "@examine"
    aliases = ["@ex","ex", "exam"]
    locks = "cmd:perm(examine) or perm(Builders)"
    help_category = "Building"

    def crop_line(self, text, heading="", line_width=79):
        """
        Crops a line of text, adding [...] if doing so.

        heading + text + eventual [...] will not exceed line_width.
        """
        headlen = len(str(heading))
        textlen = len(str(text))
        if  textlen > (line_width - headlen):
            text = "%s[...]" % text[:line_width - headlen - 5]                    
        return text

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
            db_attr = [(attr.key, attr.value) for attr in ObjAttribute.objects.filter(db_obj=obj)]
            try:
                ndb_attr = [(aname, avalue) for aname, avalue in obj.ndb.__dict__.items()]
            except Exception:
                ndb_attr = None
        string = ""
        if db_attr and db_attr[0]:
            #self.caller.msg(db_attr)
            string += "\n{wPersistent attributes{n:"
            for attr, value in db_attr:
                if crop:
                    value = self.crop_line(value, attr)
                string += "\n %s = %s" % (attr, value)
        if ndb_attr and ndb_attr[0]:
            string += "\n{wNon-persistent attributes{n:"
            for attr, value in ndb_attr:
                if crop:
                    value = self.crop_line(value, attr)
                string += "\n %s = %s" % (attr, value)
        return string 
    
    def format_output(self, obj):
        """
        Helper function that creates a nice report about an object.

        returns a string.
        """

        string = "\n{wName/key{n: %s (#%i)" % (obj.name, obj.id)        
        if obj.aliases:
            string += "\n{wAliases{n: %s" % (", ".join(obj.aliases))
        if obj.has_player:
            string += "\n{wPlayer{n: %s" % obj.player.name
            perms = obj.player.permissions
            if obj.player.is_superuser:
                perms = ["<Superuser>"]
            elif not perms:
                perms = ["<None>"]                
            string += "\n{wPlayer Perms/Locks{n: %s" % (", ".join(perms))
         
        string += "\n{wTypeclass{n: %s (%s)" % (obj.typeclass, obj.typeclass_path)
        string += "\n{wLocation{n: %s" % obj.location
        perms = obj.permissions
        if perms:            
            string += "\n{wPermissions{n: %s" % (", ".join(perms)) 
        locks = str(obj.locks)
        if locks:
            string += "\n{wLocks{n: %s" % ("; ".join([lock for lock in locks.split(';')]))
        if not (len(obj.cmdset.all()) == 1 and obj.cmdset.current.key == "Empty"):            
            string += "\n{wCurrent Cmdset (before permission checks){n:\n %s" % obj.cmdset
        if obj.scripts.all():
            string += "\n{wScripts{n:\n %s" % obj.scripts
        # add the attributes                    
        string += self.format_attributes(obj)
        # add the contents                     
        exits = []
        pobjs = []
        things = []
        for content in obj.contents:
            if content.db._destination: 
                # an exit
                exits.append(content)
            elif content.player:
                pobjs.append(content)
            else:
                things.append(content)
        if exits:
            string += "\n{wExits{n: " + ", ".join([exit.name for exit in exits]) 
        if pobjs:
            string += "\n{wCharacters{n: " + ", ".join(["{c%s{n" % pobj.name for pobj in pobjs])
        if things:
            string += "\n{wContents{n: " + ", ".join([cont.name for cont in obj.contents 
                                                      if cont not in exits and cont not in pobjs])
        #output info
        return "-"*50 + '\n' + string.strip() + "\n" + '-'*50 
    
    def func(self):
        "Process command"
        caller = self.caller
                                                        
        if not self.args:
            # If no arguments are provided, examine the invoker's location.
            obj = caller.location
            if not obj.access(caller, 'examine'):
            #If we don't have special info access, just look at the object instead.
                caller.execute_cmd('look %s' % obj.name)
                return              
            string = self.format_output(obj)

        else:
            # we have given a specific target object 

            string = ""

            for objdef in self.lhs_objattr:

                obj_name = objdef['name']
                obj_attrs = objdef['attrs']
                
                obj = caller.search(obj_name)                
                if not obj:
                    continue

                if not obj.access(caller, 'examine'):
                    #If we don't have special info access, just look at the object instead.
                    caller.execute_cmd('look %s' % obj_name)
                    continue

                if obj_attrs:
                    for attrname in obj_attrs:
                        # we are only interested in specific attributes                    
                        string += self.format_attributes(obj, attrname, crop=False)                        
                else:
                    string += self.format_output(obj)        
        string = string.strip()
        # Send it all
        if string:
            caller.msg(string.strip())


class CmdFind(MuxCommand):
    """
    find objects

    Usage:
      @find <searchname>

    Searches for an object of a particular name.
    """
    
    key = "@find"
    aliases = "@locate, find, locate"
    locks = "cmd:perm(find) or perm(Builders)"
    help_category = "Building"
            
    def func(self):
        "Search functionality"            
        caller = self.caller
        arglist = self.arglist

        if not arglist:
            caller.msg("Usage: @find <name>")# [,low [,high]]")
            return        
        searchstring = arglist[0]
        if len(arglist) > 1:
            low = arglist[1]
        if len(arglist) > 2:
            high = arglist[2]
        #TODO: Implement efficient db search with limits
        result = caller.search(searchstring, global_search=True)
        if not result:
            return
        string = "%s(#%s) - %s" % (result.name, result.id, result)
        caller.msg(string)


class CmdTeleport(MuxCommand):
    """
    teleport

    Usage:
      @tel/switch [<object> =] <location>

    Switches:
      quiet  - don't inform the source and target
               locations about the move. 
              
    Teleports an object somewhere. If no object is
    given we are teleporting ourselves. 
    """
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

        if not args:
            caller.msg("Usage: teleport[/switches] [<obj> =] <target_loc>|home")
            return    
        # The quiet switch suppresses leaving and arrival messages.
        if "quiet" in switches:
            tel_quietly = True
        else:
            tel_quietly = False

        if rhs:
            obj_to_teleport = caller.search(lhs, global_search=True)
            destination = caller.search(rhs, global_search=True)
        else:
            obj_to_teleport = caller
            destination = caller.search(args, global_search=True)
        if not obj_to_teleport:
            caller.msg("Did not find object to teleport.")
            return
        if not destination:
            caller.msg("Destination not found.")
            return
        if obj_to_teleport == destination:
            caller.msg("You can't teleport an object inside of itself!")
            return
        # try the teleport 
        if obj_to_teleport.move_to(destination, quiet=tel_quietly,
                                   emit_to_obj=caller):
            caller.msg("Teleported.")


class CmdScript(MuxCommand):
    """
    attach scripts

    Usage:
      @script[/switch] <obj> = <script.path or scriptkey>
    
    Switches:
      start - start a previously added script
      stop - stop a previously added script

    Attaches the given script to the object and starts it. Script path can be given
    from the base location for scripts as given in settings. 
    If stopping/starting an already existing script, the script's key
    can be given instead (if giving a path, *all* scripts with this path 
    on <obj> will be affected).
    """
    
    key = "@script"
    aliases = "@addscript"
    locks = "cmd:perm(script) or perm(Wizards)"
    help_category = "Building"

    def func(self):
        "Do stuff"

        caller = self.caller

        if not self.rhs:
            string = "Usage: @script[/switch] <obj> = <script.path or script key>"
            caller.msg(string)
            return 
        
        inp = self.rhs
        if not inp.startswith('src.') and not inp.startswith('game.'):
            # append the default path.
            inp = "%s.%s" % (settings.BASE_SCRIPT_PATH, inp)
        
        obj = caller.search(self.lhs)
        if not obj:
            return
        string = ""
        if "stop" in self.switches:
            # we are stopping an already existing script
            ok = obj.scripts.stop(inp)        
            if not ok:
                string = "Script %s could not be stopped. Does it exist?" % inp
            else:
                string = "Script stopped and removed from object."
        if "start" in self.switches:
            # we are starting an already existing script 
            ok = obj.scripts.start(inp)
            if not ok:
                string = "Script %s could not be (re)started." % inp
            else:
                string = "Script started successfully."
        if not self.switches:
            # adding a new script, and starting it
            ok = obj.scripts.add(inp, autostart=True)
            if not ok:
                string = "Script %s could not be added." % inp
            else:
                string = "Script successfully added and started."
        caller.msg(string)
