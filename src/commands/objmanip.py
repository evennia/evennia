"""
These commands typically are to do with building or modifying Objects.
"""
from django.contrib.auth.models import Permission, Group
from src.objects.models import Object, Attribute
# We'll import this as the full path to avoid local variable clashes.
import src.flags
from src import locks
from src import ansi
from src.cmdtable import GLOBAL_CMD_TABLE
from src import defines_global
from src.ansi import ANSITable

def cmd_teleport(command):
    """
    teleport

    Usage:
      teleport/switch [<object> = <location>]

    Switches:
      quiet  - don't inform the source and target
               locations about the move. 
              
    Teleports an object somewhere. If no object is
    given we are teleporting ourselves. 
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @teleport[/switches] [<obj> =] <target_loc>|home")
        return

    eq_args = command.command_argument.split('=', 1)
    
    # The quiet switch suppresses leaving and arrival messages.
    if "quiet" in command.command_switches:
        tel_quietly = True
    else:
        tel_quietly = False

    # If we have more than one entry in our '=' delimited argument list,
    # then we're doing a @tel <victim>=<location>. If not, we're doing
    # a direct teleport, @tel <destination>.
    if len(eq_args) > 1:
        # Equal sign teleport.
        victim = source_object.search_for_object(eq_args[0])
        # Use search_for_object to handle duplicate/nonexistant results.
        if not victim:
            return

        destination = source_object.search_for_object(eq_args[1])
        # Use search_for_object to handle duplicate/nonexistant results.
        if not destination:
            return

        if victim.is_room():
            source_object.emit_to("You can't teleport a room.")
            return

        if victim == destination:
            source_object.emit_to("You can't teleport an object inside of itself!")
            return
        source_object.emit_to("Teleported.")
        victim.move_to(destination, quiet=tel_quietly)
    else:
        # Direct teleport (no equal sign)
        target_obj = source_object.search_for_object(command.command_argument)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if target_obj == source_object:
            source_object.emit_to("You can't teleport inside yourself!")
            return
        source_object.emit_to("Teleported.")
            
        source_object.move_to(target_obj, quiet=tel_quietly)
GLOBAL_CMD_TABLE.add_command("@teleport", cmd_teleport,
                             priv_tuple=("objects.teleport",), help_category="Building")

def cmd_alias(command):
    """
    @alias

    Usage:
      @alias <player> = <alias>

    Assigns an alias to a player object for ease of paging, etc.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @alias <player = <alias>")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("Alias missing.")
        return
    
    target_string = eq_args[0]
    new_alias = eq_args[1]
    
    # An Object instance for the victim.
    target = source_object.search_for_object(target_string)
    # Use search_for_object to handle duplicate/nonexistant results.
    if not target:
        source_object.emit_to("I can't find that player.")
        return
    
    if not new_alias.isalnum():
        source_object.emit_to("Aliases must be alphanumeric.")
        return
  
    old_alias = target.get_attribute_value('ALIAS', default='')
    #print "ALIAS", old_alias
    duplicates = Object.objects.player_alias_search(source_object, new_alias)
    if not duplicates or old_alias.lower() == new_alias.lower():
        # Either no duplicates or just changing the case of existing alias.
        if source_object.controls_other(target):
            target.set_attribute('ALIAS', new_alias)
            source_object.emit_to("Alias '%s' set for %s." % (new_alias, 
                                                    target.get_name()))
        else:
            source_object.emit_to("You do not have access to set an alias for %s." % 
                                                   (target.get_name(),))
    else:
        # Duplicates were found.
        source_object.emit_to("Alias '%s' is already in use." % (new_alias,))
        return
GLOBAL_CMD_TABLE.add_command("@alias", cmd_alias)

def cmd_wipe(command):
    """
    @wipe - clears attributes

    Usage:
      @wipe <object> [/attribute-wildcard]

    Example:
      @wipe box 
      @wipe box/colour

    Wipes all of an object's attributes, or optionally only those
    matching the given attribute-wildcard search string. 
    """
    source_object = command.source_object
    attr_search = False

    if not command.command_argument:    
        source_object.emit_to("Usage: @wipe <object>[/attribute-wildcard]")
        return

    # Look for a slash in the input, indicating an attribute wipe.
    attr_split = command.command_argument.split("/", 1)

    # If the splitting by the "/" character returns a list with more than 1
    # entry, it's an attribute match.
    if len(attr_split) > 1:
        attr_search = True
        # Strip the object search string from the input with the
        # object/attribute pair.
        searchstr = attr_split[1]
    else:
        searchstr = command.command_argument

    target_obj = source_object.search_for_object(attr_split[0])
    # Use search_for_object to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if attr_search:
        # User has passed an attribute wild-card string. Search for name matches
        # and wipe.
        attr_matches = target_obj.attribute_namesearch(searchstr, 
                                                       exclude_noset=True)
        if attr_matches:
            for attr in attr_matches:
                target_obj.clear_attribute(attr.get_name())
            source_object.emit_to("%s - %d attributes wiped." % (
                                                        target_obj.get_name(), 
                                                        len(attr_matches)))
        else:
            source_object.emit_to("No matching attributes found.")
    else:
        # User didn't specify a wild-card string, wipe entire object.
        attr_matches = target_obj.attribute_namesearch("*", exclude_noset=True)
        for attr in attr_matches:
            target_obj.clear_attribute(attr.get_name())
        source_object.emit_to("%s - %d attributes wiped." % (target_obj.get_name(), 
                                                   len(attr_matches)))
GLOBAL_CMD_TABLE.add_command("@wipe", cmd_wipe,priv_tuple=("objects.wipe",),
                             help_category="Building")

def cmd_set(command):
    """
    @set - set attributes and flags

    Usage:
      @set <obj> = <flag>
      @set <obj> = <attr> : <value>
      @set <obj> = !<flag>
      @set <obj> = <attr> : 
    
    Sets flags or attributes on objects. The two last forms
    above unsets the flag and clears the attribute, respectively.
    """
    source_object = command.source_object    
    args = command.command_argument
    if not args:        
        source_object.emit_to("Usage: @set obj=attr:value or @set obj=flag. Use empty value or !flag to clear.")
        return
    
    # Break into target and value by the equal sign.
    eq_args = args.split('=')
    if len(eq_args) < 2 or not eq_args[1]:
        # Equal signs are not optional for @set.
        source_object.emit_to("Set what?")
        return
    target_name = eq_args[0].strip()
    target = source_object.search_for_object(target_name)
    # Use search_for_object to handle duplicate/nonexistant results.
    if not target:
        return

    #check permission.
    if not source_object.controls_other(target):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return
    
    attrib_args = eq_args[1].split(':', 1)
    if len(attrib_args) > 1:
        # We're dealing with an attribute/value pair.
        attrib_name = attrib_args[0].strip()
        splicenum = eq_args[1].find(':') + 1
        attrib_value = (eq_args[1][splicenum:]).strip()
    
        if not attrib_name:
            source_object.emit_to("Cannot set an empty attribute name.")
            return                
        if not Attribute.objects.is_modifiable_attrib(attrib_name):
            # In global_defines.py, see NOSET_ATTRIBS for protected attribute names.
            source_object.emit_to("You can't modify that attribute.")
            return
        if attrib_value:
            # An attribute value was specified, create or set the attribute.
            target.set_attribute(attrib_name, attrib_value)
            s = "Attribute %s=%s set to '%s'" % (target_name, attrib_name, attrib_value)
        else:
            # No value was given, this means we delete the attribute.
            ok = target.clear_attribute(attrib_name)
            if ok:
                s = 'Attribute %s=%s deleted.' % (target_name,attrib_name)
            else:
                s = "Attribute %s=%s not found, so not cleared. \nIf it is a flag, use '@set %s:!%s' to clear it." % \
                (target_name, attrib_name, target_name, attrib_name)
        source_object.emit_to(s)
    else:
        # Flag manipulation form.
        flag_list = eq_args[1].split()
        s = ""
        for flag in flag_list:
            flag = flag.upper().strip()
            if flag[0] == '!':
                # We're un-setting the flag.
                flag = flag[1:]
                if not src.flags.is_modifiable_flag(flag):
                    s += "\nYou can't set/unset the flag %s." % flag
                    continue
                if not target.has_flag(flag):
                    s += "\nFlag %s=%s already cleared." % (target_name,flag)
                    continue
                s += "\nFlag %s=%s cleared." % (target_name, flag.upper())
                target.unset_flag(flag)
            else:
                # We're setting the flag.
                if not src.flags.is_modifiable_flag(flag):
                    s += "\nYou can't set/unset the flag %s." % flag
                    continue
                if target.has_flag(flag):
                    s += "\nFlag %s=%s already set." % (target_name, flag)
                    continue
                else:
                    s += '\nFlag %s=%s set.' % (target_name, flag.upper())
                target.set_flag(flag, True)
        source_object.emit_to(s[1:])
GLOBAL_CMD_TABLE.add_command("@set", cmd_set, priv_tuple=("objects.modify_attributes",),
                             help_category="Building")

def cmd_cpattr(command):
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
    source_object = command.source_object
    args = command.command_argument
    if not args or not '=' in args:
        s = """Usage:
        @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
        @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
        @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
        @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]"""
        source_object.emit_to(s)
        return
    arg1, arg2 = args.split("=")

    #parsing arg1 (left of =)
    if not arg1:
        source_object.emit_to("You must specify <obj> or <obj>/<attr>.")
        return
    if '/' in arg1:
        from_objname, from_attr = arg1.split('/',1)
        from_attr = from_attr.strip()
        from_obj = source_object.search_for_object(from_objname.strip())
    else:
        from_attr = arg1.strip()
        from_obj = source_object
        from_objname = from_obj.get_name(show_dbref=False)        
    if not from_obj:
        source_object.emit_to("Source object not found.")
        return
    from_value = from_obj.get_attribute_value(from_attr)
    if from_value==None:
        source_object.emit_to("Attribute %s=%s not found." % \
                              (from_objname,from_attr))
        return 
        
    #parsing arg2 (right of =)
    if not arg2:
        source_object.emit_to("You must specify target objects and attributes.")
        return 
    pairlist = arg2.split(',')
    pairdict = {}
    for pair in pairlist:
        if '/' in pair:
            objname, attrname = pair.split("/",1)
            pairdict[objname.strip()] = attrname.strip()
        else:
            pairdict[pair.strip()] = None

    #copy to all targets
    s = "Copying %s=%s (with value %s) ..." % (from_objname,
                                               from_attr,from_value)
    for to_objname, to_attr in pairdict.items():
        to_obj = source_object.search_for_object(to_objname.strip())
        if not to_obj:
            s += "\nCould not find object '%s'" % to_objname
            continue
        if not source_object.controls_other(to_obj):
            s += "\n You cannot modify object '%s'" % to_objname
            return 
        if to_attr == None:
            to_attr = from_attr
        if not to_attr:            
            s += "\nCan not copy to %s= (empty attribute name)" % to_objname
            continue
        if not Attribute.objects.is_modifiable_attrib(to_attr):
            s += "\nCan not copy to %s=%s (cannot be modified)" % (to_objname,
                                                                   to_attr)
            continue 
        to_obj.set_attribute(to_attr, from_value)
        s += "\nCopied %s=%s -> %s=%s" % (from_objname,from_attr,
                                          to_objname, to_attr)
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("@cpattr", cmd_cpattr,
                             priv_tuple=("objects.modify_attributes",), help_category="Building")

        
def cmd_mvattr(command):
    """
    @mvattr - move attributes

    Usage:
      @mvattr <object>=<old>,<new>[,<copy1>[, <copy2 ...]]

    Move attributes around on the same object.
    """
    source_object = command.source_object
    arg = command.command_argument
    #split arguments
    if not arg or not '=' in arg:
        source_object.emit_to("Usage: @mvattr <object>=<old>,<new>[,<copy1>[, copy2 ...]]")
        return
    objname,attrs = arg.split('=')            
    attrs = attrs.split(",")
    oldattr = attrs[0].strip()
    if len(attrs)<2:
        source_object.emit_to("You must give both the old- and new name of the attribute.")
        return
    #find target object
    target_obj = source_object.search_for_object(objname)
    if not target_obj:
        source_object.emit_to("Object '%s' not found." % objname)
        return
    #check so old attribute exists.
    value = target_obj.get_attribute_value(oldattr)
    if value == None:
        source_object.emit_to("Attribute '%s' does not exist." % oldattr)
        return 
    #check permission to modify object
    if not source_object.controls_other(target_obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return            
    #we should now be good to go. Start the copying. 
    s = "Moving %s=%s (with value %s) ..." % (objname,oldattr,value)
    delete_original = True
    for attr in attrs[1:]:
        attr = attr.strip()
        if not attr:
            s += "\nCan not copy to empty attribute name."
            continue
        if not Attribute.objects.is_modifiable_attrib(attr):
            s += "\nDid not copy to '%s' (cannot be modified)" % attr
            continue 
        if attr == oldattr:
            s += "\nKept '%s' (moved into itself)" % attr
            delete_original = False
            continue
        target_obj.set_attribute(attr, value)
        s += "\nCopied %s -> %s" % (oldattr,attr)
    #if we can, delete the old attribute
    if not Attribute.objects.is_modifiable_attrib(oldattr):
        s += "\nCould not remove old attribute '%s' (cannot be modified)" % oldattr
    elif delete_original:
        target_obj.clear_attribute(oldattr)
        s += "\nRemoved '%s'." % (oldattr)
    
    source_object.emit_to(s)

GLOBAL_CMD_TABLE.add_command("@mvattr", cmd_mvattr,
                             priv_tuple=("objects.modify_attributes",),
                             help_category="Building")

def cmd_find(command):
    """
    find

    Usage:
      find <searchname>

    Searches for an object of a particular name.
    """
    source_object = command.source_object
    can_find = source_object.has_perm("genperms.builder")

    if not command.command_argument:
        source_object.emit_to("Usage: @find <name>")
        return
    
    searchstring = command.command_argument
    results = Object.objects.global_object_name_search(searchstring)

    if len(results) > 0:
        source_object.emit_to("Name matches for: %s" % (searchstring,))
        s = ""
        for result in results:
            s += " %s\n\r" % (result.get_name(fullname=True),)
        s += "%d matches returned." % (len(results),)
        source_object.emit_to(s)
    else:
        source_object.emit_to("No name matches found for: %s" % (searchstring,))
GLOBAL_CMD_TABLE.add_command("@find", cmd_find,
                             priv_tuple=("objects.info",), help_category="Building")

def cmd_create(command):
    """
    @create - create new objects

    Usage:
      @create[/drop] objname[;alias;alias...] [:parent]

    switch:
       drop - automatically drop the new object into your current location (this is not echoed)

    Creates a new object. If parent is given, the object is created as a child of this
    parent. The parent script is assumed to be located under game/gamesrc/parents
    and any further directory structure is given in Python notation. So if you
    have a correct parent object defined in parents/examples/red_button.py, you would
    load create a new object inheriting from this parent like this:
       @create button:examples.red_button       

    (See also @destroy, @dig and @open.)
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Usage: @create[/drop] <newname>[;alias;alias...] [:path_to_script_parent]")
        return
    
    eq_args = command.command_argument.split(':', 1)
    target_name = eq_args[0].strip()

    #check if we want to set a custom parent
    script_parent = None
    if len(eq_args) > 1:
        script_parent = eq_args[1].strip()
            
    # Create and set the object up.
    new_object = Object.objects.create_object(target_name,
                                              defines_global.OTYPE_THING,
                                              source_object,
                                              source_object,
                                              script_parent=script_parent)    
    if script_parent:
        if new_object.get_script_parent() == script_parent:        
            source_object.emit_to("You create %s as a child of %s." %
                                  (new_object, script_parent))
        else:                
            source_object.emit_to("'%s' is not a valid parent. Using default." %
                                  script_parent)
    else:        
        source_object.emit_to("You create a new thing: %s" % (new_object,))

    if "drop" in command.command_switches:
        new_object.move_to(source_object.get_location(),quiet=True)



GLOBAL_CMD_TABLE.add_command("@create", cmd_create,
                             priv_tuple=("objects.create",),
                             help_category="Building")
    
def cmd_copy(command):
    """
    @copy - copy objects
    
    Usage:
      @copy[/reset] <original obj> [new_name][;alias...] [, new_location]

    switch:
      reset - make a 'clean' copy off the object's script parent, thus
              removing any changes that might have been made to the original
              since it was first created. 

    Create an identical copy of an object. For every ; after your new name
    you can add an alias for the object. 
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches
    if not args:
        source_object.emit_to("Usage: @copy <obj> [=new_name] [, new_location]") 
        return
    reset = False
    if "reset" in switches:
        reset = True        

    objname = None
    new_objname = None
    new_location = None
    new_location_name = None
    
    arglist = args.split("=",1)
    if len(arglist) == 1:
        objname = args.strip()
    else:
        objname, args = arglist[0].strip(), arglist[1]
    arglist = args.split(",",1)
    if len(arglist) == 1:
        new_objname = args.strip() 
    else:
        new_objname, new_location_name = arglist[0].strip(), arglist[1].strip()
    original_object = source_object.search_for_object(objname)
    if not original_object:
        return 
    if new_location_name: 
        new_location = source_object.search_for_object(new_location_name)
        if not new_location:
            return 
    if original_object.is_player():
        source_object.emit_to("You cannot copy a player.")
        return
    if not source_object.controls_other(original_object,builder_override=True):
        source_object.emit_to("You don't have permission to do that.")
        return
    
    #we are good to go, perform the copying. 
    new_object = Object.objects.copy_object(original_object, new_name=new_objname,
                                            new_location=new_location, reset=reset)            
    name_text = ""
    if new_objname:
        name_text = " to '%s'" % new_objname            
    loc_text = ""
    if new_location:
        loc_text = " in %s" % new_location_name
    reset_text = ""
    if reset:
        reset_text = " (using default attrs/flags)"
    source_object.emit_to("Copied object '%s'%s%s%s." % (objname,name_text,loc_text,reset_text))
GLOBAL_CMD_TABLE.add_command("@copy", cmd_copy,
                             priv_tuple=("objects.create",), help_category="Building")
        
def cmd_nextfree(command):
    """
    @nextfree
    
    Usage:
       @nextfree 

    Returns the next free object number.
    """   
    nextfree = Object.objects.get_nextfree_dbnum()
    command.source_object.emit_to("Next free object number: #%s" % nextfree)
GLOBAL_CMD_TABLE.add_command("@nextfree", cmd_nextfree,
                             priv_tuple=("objects.info",), help_category="Building")
    
def cmd_open(command):
    """    
    @open - create new exit
    
    Usage:
      @open <new exit>[;alias;alias...] [:parent] [= <destination> [,<return exit>[;alias;alias...] [:parent]]]  

    Handles the creation of exits. If a destination is given, the exit
    will point there. The <return exit> argument sets up an exit at the
    destination leading back to the current room. Destination name
    can be given both as a #dbref and a name, if that name is globally
    unique. 

    (See also @create, @dig and @link.)
    """
    source_object = command.source_object    
    args = command.command_argument
    if not args:
        source_object.emit_to("Usage: @open <new exit> [:parent] [= <destination> [,<return exit> [:parent]]]")
        return        
    dest_name = "" 
    return_exit = ""
    exit_parent = None
    return_exit_parent = None
    # handle all arguments
    arglist = args.split('=', 1)
    #left side of =
    largs = arglist[0].split(':')
    if len(largs) > 1:        
        exit_name, exit_parent = largs[0].strip(), largs[1].strip()
    else:
        exit_name = largs[0].strip()    
    if len(arglist) > 1:
        # right side of =         
        rargs = arglist[1].split(',',1)
        if len(rargs) > 1:
            dest_name, rargs = rargs[0].strip(),rargs[1].strip()
            rargs = rargs.split(":")
            if len(rargs) > 1:
                return_exit, return_exit_parent = rargs[0].strip(), rargs[1].strip()
            else:
                return_exit = rargs[0].strip()
        else:
            dest_name = rargs[0].strip()
    
    # sanity checking
    if not exit_name:
        source_object.emit_to("You must supply an exit name.")
        return

    if not dest_name:
        # we want an unlinked exit.
        new_object = Object.objects.create_object(exit_name,
                                                  defines_global.OTYPE_EXIT,
                                                  source_object.get_location(),
                                                  source_object,
                                                  None,
                                                  script_parent=exit_parent)                
        ptext = ""
        if exit_parent:
            if new_object.get_script_parent() == exit_parent:        
                ptext += " of type %s" % exit_parent
            else:
                ptext += " of default type (parent '%s' failed!)" % exit_parent
        source_object.emit_to("Created unlinked exit%s named '%s'." % (ptext,new_object))

    else: 
        # We have the name of a destination. Try to find it.        
        destination = Object.objects.global_object_name_search(dest_name)
        if not destination:
            source_object.emit_to("No matches found for '%s'." % dest_name)
            return 
        if len(destination) > 1:
            s = "There are multiple matches. Please use #dbref to be more specific."
            for d in destination:
                s += "\n %s" % destination.get_name()
            source_object.emit_to(s)
            return
        destination = destination[0]
        
        if destination.is_exit():
            source_object.emit_to("You can't open an exit to an exit!")
            return

        #build the exit from here to destination
        new_object = Object.objects.create_object(exit_name,
                                                  defines_global.OTYPE_EXIT,
                                                  source_object.get_location(),
                                                  source_object,
                                                  destination,
                                                  script_parent=exit_parent)
        ptext = ""
        if exit_parent:
            if new_object.get_script_parent() == exit_parent:        
                ptext += " of type %s" % exit_parent
            else:
                ptext += " of default type (parent '%s' failed!)" % exit_parent
        source_object.emit_to("Created exit%s to %s named '%s'." % (ptext,destination,new_object))

        if return_exit: 
            new_object = Object.objects.create_object(return_exit,
                                                      defines_global.OTYPE_EXIT,
                                                      destination,
                                                      source_object,
                                                      source_object.get_location(),
                                                      script_parent=return_exit_parent)
            ptext = ""
            if return_exit_parent:                
                if new_object.get_script_parent() == return_exit_parent:        
                    ptext += " of type %s" % return_exit_parent
                else:
                    ptext += " of default type (parent '%s' failed!)" % return_exit_parent
            source_object.emit_to("Created exit%s back from %s named %s." % \
                                  (ptext, destination, new_object))
GLOBAL_CMD_TABLE.add_command("@open", cmd_open,
                             priv_tuple=("objects.dig",), help_category="Building")
        
def cmd_chown(command):
    """
    @chown - change ownerships

    Usage:
      @chown <Object> = <NewOwner>  
    
    Changes the ownership of an object. The new owner specified must be a
    player object.    
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @chown <object> = <newowner>")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    owner_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("Change the ownership of what?")
        return

    if len(eq_args) > 1:
        target_obj = source_object.search_for_object(target_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj) and not source_object.has_perm("objects.admin_ownership"):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        owner_obj = source_object.search_for_object(owner_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not owner_obj:
            return
        if not owner_obj.is_player():
            source_object.emit_to("Only players may own objects.")
            return
        if target_obj.is_player():
            source_object.emit_to("You may not change the ownership of player objects.")
            return

        target_obj.set_owner(owner_obj)
        source_object.emit_to("%s now owns %s." % (owner_obj, target_obj))
    else:
        # We haven't provided a target.
        source_object.emit_to("Who should be the new owner of the object?")
        return
GLOBAL_CMD_TABLE.add_command("@chown", cmd_chown, priv_tuple=("objects.modify_attributes",
                                                              "objects.admin_ownership"),
                             help_category="Building" )
    
def cmd_chzone(command):
    """
    @chzone - set zones

    Usage:
      @chzone <Object> = <NewZone>

    Changes an object's zone. The specified zone may be of any object type, but
    will typically be a THING.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @chzone <object> = <newzone>")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    zone_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("Change the zone of what?")
        return

    if len(eq_args) > 1:
        target_obj = source_object.search_for_object(target_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # Allow the clearing of a zone
        if zone_name.lower() == "none":
            target_obj.set_zone(None)
            source_object.emit_to("%s is no longer zoned." % (target_obj))
            return
        
        zone_obj = source_object.search_for_object(zone_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not zone_obj:
            return

        target_obj.set_zone(zone_obj)
        source_object.emit_to("%s is now in zone %s." % (target_obj, zone_obj))

    else:
        # We haven't provided a target zone.
        source_object.emit_to("What should the object's zone be set to?")
        return
GLOBAL_CMD_TABLE.add_command("@chzone", cmd_chzone, priv_tuple=("objects.dig",),
                             help_category="Building" )

def cmd_link(command):
    """
    @link - connect objects

    Usage:
      @link <object> = <target>
      @link <object> = 
      @link <object> 

    If <object> is an exit, set its destination. For all other object types, this
    command sets the object's Home. 
    The second form sets the destination/home to None and the third form inspects
    the current value of destination/home on <object>.

    (See also @create, @dig and @open)
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Usage: @link <object> = <target>")
        return
    dest_name = ""
    arglist = command.command_argument.split('=', 1)
    if len(arglist) > 1:
        obj_name, dest_name = arglist[0].strip(), arglist[1].strip()
    else:
        obj_name = arglist[0].strip()

    # sanity checks
    if not obj_name:
        source_object.emit_to("What do you want to link?")
        return

    # Use search_for_object to handle duplicate/nonexistant results.
    obj = source_object.search_for_object(obj_name)    
    if not obj:
        return
    otype = obj.get_type()
    
    if not dest_name:
        # We haven't provided a target.
        if len(arglist) > 1:
            # the command looks like '@link obj =', this means we unlink the 
            if not source_object.controls_other(obj):
                source_object.emit_to(defines_global.NOCONTROL_MSG)
                return
            oldhome = obj.get_home()
            ohome_text = ""
            if oldhome:
                ohome_text = " (was %s)" % oldhome
            obj.set_home(None)            
            if otype == "EXIT":
                source_object.emit_to("You have unlinked %s%s." % (obj,ohome_text))
            else:
                source_object.emit_to("You removed %s's home setting%s." % (obj,ohome_text))
            return
        else:
            # the command looks like '@link obj', we just inspect the object.
            if otype == "EXIT":
                source_object.emit_to("%s currently links to %s." % (obj.get_name(), obj.get_home()))
            else:
                source_object.emit_to("%s's current home is %s." % (obj.get_name(), obj.get_home()))
            return 
    else:
        # we have a destination, search for it globally. 
        if not source_object.controls_other(obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return    
        destination = Object.objects.global_object_name_search(dest_name)
        if not destination:
            source_object.emit_to("No matches found for '%s'." % dest_name)
            return 
        if len(destination) > 1:
            s = "There are multiple matches. Please use #dbref to be more specific."
            for d in destination:
                s += "\n %s" % destination.get_name(show_dbref=True)
            source_object.emit_to(s)
            return
        destination = destination[0]

        # do the link.
        oldhome = obj.get_home()
        ohome_text = ""        
        if oldhome:
            ohome_text = " (was %s)" % oldhome
        obj.set_home(destination)
        if otype == "EXIT":
            source_object.emit_to("You link %s to %s%s." % (obj, destination, ohome_text))
        else:
            source_object.emit_to("You set the home location of %s to %s%s." % (obj, destination, ohome_text))      
GLOBAL_CMD_TABLE.add_command("@link", cmd_link,
                             priv_tuple=("objects.dig",), help_category="Building")

def cmd_unlink(command):
    """
    @unlink - unconnect objects

    Usage:
      @unlink <Object>

    Unlinks an object, for example an exit, disconnecting
    it from whatever it was connected to.
    """
    source_object = command.source_object
    
    if not command.command_argument:    
        source_object.emit_to("Usage: @unlink <object>")
        return
    else:
        target_obj = source_object.search_for_object(command.command_argument)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        target_obj.set_home(None)
        source_object.emit_to("You have unlinked %s." % target_obj.get_name())
GLOBAL_CMD_TABLE.add_command("@unlink", cmd_unlink,
                             priv_tuple=("objects.dig",), help_category="Building")

def cmd_dig(command):
    """
    @dig - build and connect new rooms

    Usage: 
      @dig[/switches] roomname[;alias;alias...] [:parent] [= exit_to_there[;alias] [: parent]] [, exit_to_here[;alias] [: parent]] 

    Switches:
       teleport - move yourself to the new room

    Example:
       @dig kitchen = north; n, south; s

    This command is a convenient way to build rooms quickly; it creates the new room and you can optionally
    set up exits back and forth between your current room and the new one. You can add as many aliases as you
    like to the name of the room and the exits in question; an example would be 'north;no;n'.
    
    (See also @create, @open and @link.) 
    """
    source_object = command.source_object    
    args = command.command_argument
    switches = command.command_switches

    if not args:
        source_object.emit_to("Usage: @dig[/teleport] roomname [:parent][= exit_to_there [:parent] [;alias]] [, exit_to_here [:parent] [;alias]]")
        return

    room_name = None
    room_parent = None    
    exit_names = [None,None]
    exit_parents = [None,None]
    
    #deal with arguments 
    arg_list = args.split("=",1)
    if len(arg_list) < 2:
        #just create a room, no exits
        room_name = arg_list[0].strip()
    else:
        #deal with args left of =
        larg = arg_list[0]
        try:
            room_name, room_parent = [s.strip() for s in larg.split(":",1)]
        except ValueError:
            room_name = larg.strip()
            
        #deal with args right of =
        rarg = arg_list[1]
        exits = rarg.split(",",1)        
        for ie, exi in enumerate(exits):
            try:
                exit_names[ie], exit_parents[ie] = [s.strip() for s in exi.split(":",1)]
            except ValueError:
                exit_names[ie] = exi.strip()

    #start creating things. 
    if not room_name:
        source_object.emit_to("You must supply a new room name.")            
        return
    
    new_room = Object.objects.create_object(room_name,
                                            defines_global.OTYPE_ROOM,
                                            None,
                                            source_object,
                                            script_parent=room_parent)
    ptext = ""
    if room_parent:
        if new_room.get_script_parent() == room_parent:        
            ptext += " of type '%s'" % room_parent
        else:
            ptext += " of default type (parent '%s' failed!)" % room_parent            
    source_object.emit_to("Created a new room '%s'%s." % (new_room, ptext))
    
    if exit_names[0] != None: 
        #create exits to the new room
        destination = new_room 
            
        if destination and not destination.is_exit():
            #create an exit from this room
            location = source_object.get_location()
            new_object = Object.objects.create_object(exit_names[0],
                                                      defines_global.OTYPE_EXIT,
                                                      location,
                                                      source_object,
                                                      destination,
                                                      script_parent=exit_parents[0])
            ptext = ""
            if exit_parents[0]:
                script_parent = exit_parents[0]
                if new_object.get_script_parent() == script_parent:        
                    ptext += " of type %s" % script_parent
                else:
                    ptext += " of default type (parent '%s' failed!)" % script_parent
            source_object.emit_to("Created exit%s from %s to %s named '%s'." % (ptext,location,destination,new_object))                       
        if len(exit_names) > 1 and exit_names[1] != None:
            #create exit back from new room to this one.
            new_object = Object.objects.create_object(exit_names[1],
                                                      defines_global.OTYPE_EXIT,
                                                      destination,
                                                      source_object,
                                                      location,
                                                      script_parent=exit_parents[1])
            ptext = ""
            if exit_parents[1]:
                script_parent = exit_parents[1]
                if new_object.get_script_parent() == script_parent:        
                    ptext += " of type %s" % script_parent
                else:
                    ptext += " of default type (parent '%s' failed!)" % script_parent
            source_object.emit_to("Created exit%s back from %s to %s named '%s'." % \
                                  (ptext, destination, location, new_object))
 
        if 'teleport' in switches:
            source_object.move_to(new_room)
               
GLOBAL_CMD_TABLE.add_command("@dig", cmd_dig,
                             priv_tuple=("objects.dig",), help_category="Building")

def cmd_name(command):
    """
    @name - name objects

    Usage:
      @name <object> = <newname>[;alias;alias...]
 
    Handle naming an object.
    """
    source_object = command.source_object
    
    if not command.command_argument:    
        source_object.emit_to("Usage: <object> = <newname>")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("Name it what?")
        return
    
    # Only strip spaces from right side in case they want to be silly and
    # have a left-padded object name.
    new_name = eq_args[1].rstrip()
    
    if len(eq_args) < 2 or eq_args[1] == '':
        source_object.emit_to("What would you like to name that object?")
    else:
        target_obj = source_object.search_for_object(eq_args[0])
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return
        
        ansi_name = ansi.parse_ansi(new_name, strip_formatting=True)
        
        if Object.objects.filter(name__iexact=new_name, 
                                 type=defines_global.OTYPE_PLAYER):
            source_object.emit_to("There is already a player with that name.")
            return
        
        source_object.emit_to("You have renamed %s to %s." % (target_obj, 
                                                              ansi_name))
        target_obj.set_name(new_name)
GLOBAL_CMD_TABLE.add_command("@name", cmd_name, priv_tuple=("objects.create",),
                             help_category="Building")

def cmd_description(command):
    """
    @desc

    Usage:
      @desc [obj =] <descriptive text>

    Set an object's description.
    """
    source_object = command.source_object
    args = command.command_argument

    if not args:
        source_object.emit_to("Usage: @desc [obj=] <descriptive text>")
        return
    
    if not '=' in args:
        target_obj = source_object.get_location()
        if not target_obj:
            return        
        new_desc = args.strip() 
    else:
        eq_args = command.command_argument.split('=', 1)    
        target_obj = source_object.search_for_object(eq_args[0].strip())
        if not target_obj: 
            source_object.emit_to("'%s' was not found." % eq_args[0])
            return 
        if len(eq_args) < 2:
            source_object.emit_to("You must supply a description too.")
            return
        new_desc = eq_args[1].strip()
        
    if not source_object.controls_other(target_obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return
    
    if not new_desc:
        source_object.emit_to("%s - description cleared." % target_obj)
        target_obj.set_attribute('desc', 'Nothing special.')
    else:
        source_object.emit_to("%s - description set." % target_obj)
        target_obj.set_attribute('desc', new_desc)
GLOBAL_CMD_TABLE.add_command("@describe", cmd_description, priv_tuple=("objects.create",),
                             help_category="Building")

def cmd_recover(command):
    """
    @recover - undo object deletion

    Usage:
      @recover[/switches] [obj [,obj2, ...]] 

    switches:
      ROOM - recover as ROOM type instead of THING
      EXIT - recover as EXIT type instead of THING

    Recovers @destroyed non-player objects.

    If no argument is given, a list of all recoverable objects will be given. 
    
    Objects scheduled for destruction with the @destroy command are cleaned out
    by the game at regular intervals. Up until the time of the next cleanup you can
    recover the object using this command (use @ps to check when the next cleanup is due).
    Note that exits linked to @destroyed rooms will not be automatically recovered
    to its former state, you have to @recover those manually.

    Objects are returned as type THING if the object type is not explicitly set using the 
    switches. Note that recovering an item as the wrong type will most likely make it
    nonfunctional. 
    """

    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches
    going_objects = Object.objects.filter(type__exact=defines_global.OTYPE_GOING)

    if not args:     
        s = " Objects scheduled for destruction:"
        if going_objects:
            for o in going_objects:
                s += '\n     %s' % o
        else:
            s += "  None."
        source_object.emit_to(s)
        return

    if ',' in args:
        objlist = args.split(',')
    else:
        objlist = [args]
    
    for objname in objlist:
        obj = Object.objects.list_search_object_namestr(going_objects, objname)
        if len(obj) == 1:
            if 'ROOM' in switches:
                obj[0].type = defines_global.OTYPE_ROOM
                source_object.emit_to("%s recovered as type ROOM." % obj[0])
            elif 'EXIT' in switches:                        
                obj[0].type = defines_global.OTYPE_EXIT
                source_object.emit_to("%s recovered as type EXIT." % obj[0])
            else:
                obj[0].type = defines_global.OTYPE_THING
                source_object.emit_to("%s recovered as type THING." % obj[0])
            obj[0].save()
        else:
            source_object.emit_to("No (or multiple) matches for %s." % objname)


GLOBAL_CMD_TABLE.add_command("@recover", cmd_recover,
                             priv_tuple=("objects.create",), help_category="Building")

def cmd_destroy(command):
    """
    @destroy - send objects to trashbin
    
    Usage: 
       @destroy[/<switches>] obj [,obj2, obj3, ...]

    switches:
       override - The @destroy command will usually avoid accidentally destroying
                  player objects as well as objects with the SAFE flag. This
                  switch overrides this safety.     
       instant|now  - Destroy the object immediately, without delay. 

    Destroys one or many objects. 
    The objects are set to GOING and will be permanently destroyed next time the system
    does cleanup. Until then non-player objects can still be saved  by using the
    @recover command. The contents of a room will be moved out before it is destroyed,
    and all exits leading to and fro the room will also be destroyed. Note that destroyed
    player objects can not be recovered by the @recover command.

    (See also @create and @open.)
    """

    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:    
        source_object.emit_to("Usage: @destroy[/switches] obj [,obj2, obj3, ...]")
        return    
    if ',' in args:
        targetlist = args.split(',')
    else:
        targetlist = [args]
    
    # Safety feature. Switch required to delete players and SAFE objects.
    switch_override = False
    if "override" in switches:
        switch_override = True

    for targetname in targetlist:
        target_obj = source_object.search_for_object(targetname)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return
        if target_obj.is_player() or target_obj.has_flag('SAFE'):
            if source_object.id == target_obj.id:
                source_object.emit_to("You can't destroy yourself.")
                return
            if not switch_override:
                source_object.emit_to("You must use @destroy/override on Players and objects with the SAFE flag set.")
                return
            if target_obj.is_superuser():
                source_object.emit_to("You can't destroy a superuser.")
                return
        elif target_obj.is_garbage():
            source_object.emit_to("That object is already destroyed.")
            return
        elif target_obj.is_going() and 'instant' not in switches:
            source_object.emit_to("That object is already scheduled for destruction.") 
            return
        
        # Run any scripted things that happen before destruction.
        target_obj.scriptlink.at_object_destruction(pobject=source_object)
        
        #destroy the object (sets it to GOING)
        target_obj.destroy()

        if 'instant' in switches or 'now' in switches:
            #sets to GARBAGE right away (makes dbref available)
            target_obj.delete()
            source_object.emit_to("You destroy %s." % target_obj.get_name())
        else:
            source_object.emit_to("You schedule %s for destruction." % target_obj.get_name())
        
GLOBAL_CMD_TABLE.add_command("@destroy", cmd_destroy,
                             priv_tuple=("objects.create",), help_category="Building")

def cmd_lock(command):
    """
    @lock - limit use of objects

    Usage:
      @lock[/switch] <obj> [:type] [= <key>[,key2,key3,...]]    

    Switches:
      add    - add a lock (default) from object 
      del    - remove a lock from object  
      list   - view all locks on object (default)
    type:
      DefaultLock  - the default lock type (default)
      UseLock      - prevents usage of objects' commands
      EnterLock    - blocking objects from entering the object
      
    Locks an object for everyone except those matching the keys.
    The keys can be of the following types (and searched in this order):
       - a user #dbref (#2, #45 etc)
       - a Group name (Builder, Immortal etc, case sensitive)
       - a Permission string (genperms.get, etc)
       - a Function():return_value pair. (ex: alliance():Red). The
           function() is called on the locked object (if it exists) and
           if its return value matches the Key is passed. If no
           return_value is given, matches against True.
        - an Attribute:return_value pair (ex: key:yellow_key). The
          Attribute is the name of an attribute defined on the locked
          object. If this attribute has a value matching return_value,
          the lock is passed. If no return_value is given, both
          attributes and flags will be searched, requiring a True
          value.
        
    If no keys at all are given, the object is locked for everyone.

    When the lock blocks a user, you may customize which error is given by
    storing error messages in an attribute. For DefaultLocks, UseLocks and
    EnterLocks, these attributes are called lock_msg, use_lock_msg and
    enter_lock_msg respectively.
    <<TOPIC:lock types>>
    Lock types:

    Name:          Affects:        Effect:  
    -----------------------------------------------------------------------
    DefaultLock:   Exits:          controls who may traverse the exit to
                                   its destination.
                   Rooms:          controls whether the player sees a failure
                                   message after the room description when
                                   looking at the room.
                   Players/Things: controls who may 'get' the object.

     UseLock:      All but Exits:  controls who may use commands defined on
                                   the locked object.

     EnterLock:    Players/Things: controls who may enter/teleport into
                                   the object.      

    Fail messages echoed to the player are stored in the attributes 'lock_msg',
    'use_lock_msg' and 'enter_lock_msg' on the locked object in question. If no
    such message is stored, a default will be used (or none at all in some cases). 
    """

    source_object = command.source_object
    arg = command.command_argument
    switches = command.command_switches
    
    if not arg:
        source_object.emit_to("Usage: @lock[/switch] <obj> [:type] [= <key>[,key2,key3,...]]")        
        return
    keys = "" 
    #deal with all possible arguments. 
    try: 
        lside, keys = arg.split("=",1)
    except ValueError:
        lside = arg    
    lside, keys = lside.strip(), keys.strip()
    try:
        obj_name, ltype = lside.split(":",1)
    except:
        obj_name = lside
        ltype = "DefaultLock"
    obj_name, ltype = obj_name.strip(), ltype.strip()

    if ltype not in ["DefaultLock","UseLock","EnterLock"]: 
        source_object.emit_to("Lock type '%s' not recognized." % ltype)
        return    

    obj = source_object.search_for_object(obj_name)
    if not obj:
        return    

    obj_locks = obj.get_attribute_value("LOCKS")    

    if "list" in switches or not switches:        
        if not obj_locks:
            s = "There are no locks on %s." % obj.get_name()
        else:
            s = "Locks on %s:" % obj.get_name()
            s += obj_locks.show()
        source_object.emit_to(s)        
        return
    
    # we are trying to change things. Check permissions.
    if not source_object.controls_other(obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return
    
    if "del" in switches:
        # clear a lock
        if obj_locks:
            if not obj_locks.has_type(ltype):
                source_object.emit_to("No %s set on this object." % ltype)
            else:
                obj_locks.del_type(ltype)
                obj.set_attribute("LOCKS", obj_locks)
                source_object.emit_to("Cleared lock %s on %s." % (ltype, obj.get_name()))
        else:
            source_object.emit_to("No %s set on this object." % ltype)
        return     
    else:
        #try to add a lock
        if not obj_locks:
            obj_locks = locks.Locks()
        if not keys:
            #add an impassable lock
            obj_locks.add_type(ltype, locks.Key())            
            source_object.emit_to("Added impassable '%s' lock to %s." % (ltype, obj.get_name()))
        else: 
            keys = [k.strip() for k in keys.split(",")]
            obj_keys, group_keys, perm_keys = [], [], []
            func_keys, attr_keys, flag_keys = [], [], []
            allgroups = [g.name for g in Group.objects.all()]
            allperms = ["%s.%s" % (p.content_type.app_label, p.codename)
                        for p in Permission.objects.all()]
            for key in keys:
                #differentiate different type of keys
                if Object.objects.is_dbref(key):
                    # this is an object key, like #2, #6 etc
                    obj_keys.append(key)
                elif key in allgroups:
                    # a group key 
                    group_keys.append(key)
                elif key in allperms:
                    # a permission string 
                    perm_keys.append(key)
                elif '()' in key:                    
                    # a function()[:returnvalue] tuple.
                    # Check if we also request a return value 
                    funcname, rvalue = [k.strip() for k in key.split('()',1)]
                    if not funcname:
                        funcname = "lock_func"
                    rvalue = rvalue.lstrip(':')
                    if not rvalue:
                        rvalue = True
                    # pack for later adding.
                    func_keys.append((funcname, rvalue))
                elif ':' in key: 
                    # an attribute/flag[:returnvalue] tuple.
                    attr_name, rvalue = [k.strip() for k in key.split(':',1)]
                    if not rvalue:
                        # if return value is not set, also search for a key. 
                        rvalue = True
                        flag_keys.append(attr_name)
                    # pack for later adding
                    attr_keys.append((attr_name, rvalue))
                else:
                    source_object.emit_to("Key '%s' is not recognized as a valid dbref, group or permission." % key)
                    return 
            # Create actual key objects from the respective lists
            keys = []
            if obj_keys:
                keys.append(locks.ObjKey(obj_keys))
            if group_keys:
                keys.append(locks.GroupKey(group_keys))
            if perm_keys:
                keys.append(locks.PermKey(perm_keys))
            if func_keys: 
                keys.append(locks.FuncKey(func_keys, obj.dbref()))
            if attr_keys:
                keys.append(locks.AttrKey(attr_keys))
            if flag_keys:
                keys.append(locks.FlagKey(flag_keys))
                
            #store the keys in the lock
            obj_locks.add_type(ltype, keys)            
            kstring = " "
            for key in keys:
                kstring += " %s," % key 
            kstring = kstring[:-1]
            source_object.emit_to("Added lock '%s' to %s with keys%s." % (ltype, obj.get_name(), kstring))

        obj.set_attribute("LOCKS",obj_locks)
GLOBAL_CMD_TABLE.add_command("@lock", cmd_lock, priv_tuple=("objects.create",), help_category="Building")

def cmd_examine(command):
    """    
    examine - detailed info on objects

    Usage: 
      examine [<object>]

    The examine command shows detailed game info about an
    object; which attributes/flags it has and what it
    contains. If object is not specified, the current
    location is examined. 
    """
    source_object = command.source_object
    attr_search = False
    
    if not command.command_argument:    
        # If no arguments are provided, examine the invoker's location.
        target_obj = source_object.get_location()
    else:
        # Look for a slash in the input, indicating an attribute search.
        attr_split = command.command_argument.split("/", 1)
        
        # If the splitting by the "/" character returns a list with more than 1
        # entry, it's an attribute match.
        if len(attr_split) > 1:
            attr_search = True
            # Strip the object search string from the input with the
            # object/attribute pair.
            obj_searchstr = attr_split[0]
            attr_searchstr = attr_split[1].strip()
            
            # Protect against stuff like: ex me/
            if attr_searchstr == '':
                source_object.emit_to('No attribute name provided.')
                return
        else:
            # No slash in argument, just examine an object.
            obj_searchstr = command.command_argument

        # Resolve the target object.
        target_obj = source_object.search_for_object(obj_searchstr)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return
        
    # If the user doesn't control the object, just look at it instead.
    if not source_object.controls_other(target_obj, builder_override=True):
        command.command_string = 'look'
        cmd_look(command)
        return
            
    if attr_search:
        # Player did something like: examine me/* or examine me/TE*. Return
        # each matching attribute with its value.        
        attr_matches = target_obj.attribute_namesearch(attr_searchstr)
        if attr_matches:
            for attribute in attr_matches:
                source_object.emit_to(attribute.get_attrline())
        else:
            source_object.emit_to("No matching attributes found.")
    else:
        
        # Player is examining an object. Return a full readout of attributes,
        # along with detailed information about said object.
         
        string = ""        
        newl = "\r\n"
        # Format the examine header area with general flag/type info.
        
        string += str(target_obj.get_name(fullname=True)) + newl
        string += str("Type: %s Flags: %s" % (target_obj.get_type(), 
                                         target_obj.get_flags())) + newl        
        string += str("Owner: %s " % target_obj.get_owner()) + newl
        string += str("Zone: %s" % target_obj.get_zone()) + newl
        string += str("Parent: %s " % target_obj.get_script_parent()) + newl

        locks = target_obj.get_attribute_value("LOCKS")
        if locks and "%s" % locks:
            string += str("Locks: %s" % locks) + newl
               
        # Contents container lists for sorting by type.
        con_players = []
        con_things = []
        con_exits = []
        
        # Break each object out into their own list.
        for obj in target_obj.get_contents():
            if obj.is_player():
                con_players.append(obj)  
            elif obj.is_exit():
                con_exits.append(obj)
            elif obj.is_thing():
                con_things.append(obj)
        
        # Render the object's home or destination (for exits).
        if not target_obj.is_room():
            if target_obj.is_exit():
                # The Home attribute on an exit is really its destination.
                string += str("Destination: %s" % target_obj.get_home()) + newl
            else:
                # For everything else, home is home.
                string += str("Home: %s" % target_obj.get_home()) + newl
            # This obviously isn't valid for rooms.    
            string += str("Location: %s" % target_obj.get_location()) + newl

        # Render other attributes
        for attribute in target_obj.get_all_attributes():            
            string += str(attribute.get_attrline()) + newl

        # Render Contents display.
        if con_players or con_things:
            string += str("%sContents:%s" % (ANSITable.ansi["hilite"], 
                                        ANSITable.ansi["normal"]))
            for player in con_players:
                string += str(' %s' % newl + player.get_name(fullname=True))
            for thing in con_things:
                string += str(' %s' % newl + thing.get_name(fullname=True))
                
        # Render Exists display.
        if con_exits:
            string += str("%sExits:%s" % (newl + ANSITable.ansi["hilite"], 
                                     ANSITable.ansi["normal"]))
            for exit in con_exits:
                string += str(' %s' % newl + exit.get_name(fullname=True))

        # Send it all
        source_object.emit_to(string)
            
GLOBAL_CMD_TABLE.add_command("examine", cmd_examine, priv_tuple=("objects.info",))



