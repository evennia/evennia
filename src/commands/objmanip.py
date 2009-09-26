"""
These commands typically are to do with building or modifying Objects.
"""
from src.objects.models import Object, Attribute
# We'll import this as the full path to avoid local variable clashes.
import src.flags
from src import ansi
from src.cmdtable import GLOBAL_CMD_TABLE
from src import defines_global

def cmd_teleport(command):
    """
    Teleports an object somewhere.
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
                             priv_tuple=("genperms.builder"))

def cmd_alias(command):
    """
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
    Wipes an object's attributes, or optionally only those matching a search
    string.
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
GLOBAL_CMD_TABLE.add_command("@wipe", cmd_wipe)

def cmd_set(command):
    """
    Sets flags or attributes on objects.
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
    target_name = eq_args[0]
    target = source_object.search_for_object(eq_args[0])
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
        attrib_name = attrib_args[0]
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
            flag = flag.upper()
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
GLOBAL_CMD_TABLE.add_command("@set", cmd_set)

def cmd_cpattr(command):
    """
    copy an attribute to another object
    
    @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
    @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]
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
                             priv_tuple=("genperms.builder",))

        
def cmd_mvattr(command):
    """
    @mvattr <object>=<old>,<new>[,<copy1>[, <copy2 ...]]

    Move attributes around on an object
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
                             priv_tuple=("genperms.builder",))

def cmd_find(command):
    """
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
                             priv_tuple=("genperms.builder"))

def cmd_create(command):
    """
    @create

    Usage: @create objname [:parent]

    Creates a new object. If parent is given, the object is created as a child of this
    parent. The parent script is assumed to be located under game/gamesrc/parents
    and any further directory structure is given in Python notation. So if you
    have a correct parent object defined in parents/examples/red_button.py, you would
    load create a new object inheriting from this parent like this:
       @create button:examples.red_button       
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Usage: @create <newname> [:path_to_script_parent]")
        return
    
    eq_args = command.command_argument.split(':', 1)
    target_name = eq_args[0]

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

GLOBAL_CMD_TABLE.add_command("@create", cmd_create,
                             priv_tuple=("genperms.builder"),auto_help=True)
    

def cmd_nextfree(command):
    """Usage:
       @nextfree 

    Returns the next free object number.
    """   
    nextfree = Object.objects.get_nextfree_dbnum()
    command.source_object.emit_to("Next free object number: #%s" % nextfree)
GLOBAL_CMD_TABLE.add_command("@nextfree", cmd_nextfree,
                             priv_tuple=("genperms.builder"),auto_help=True)
    
def cmd_open(command):
    """
    Handle the opening of exits.
    
    Forms:
    @open <Name>
    @open <Name>=<Dbref>
    @open <Name>=<Dbref>,<Name>
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Usage: @open <name> [=dbref [,<name>]]")
        return
        
    eq_args = command.command_argument.split('=', 1)
    exit_name = eq_args[0]
    
    if len(exit_name) == 0:
        source_object.emit_to("You must supply an exit name.")
        return
        
    # If we have more than one entry in our '=' delimited argument list,
    # then we're doing a @open <Name>=<Dbref>[,<Name>]. If not, we're doing
    # an un-linked exit, @open <Name>.
    if len(eq_args) > 1:
        # Opening an exit to another location via @open <Name>=<Dbref>[,<Name>].
        comma_split = eq_args[1].split(',', 1)
        # Use search_for_object to handle duplicate/nonexistant results.
        destination = source_object.search_for_object(comma_split[0])
        if not destination:
            return

        if destination.is_exit():
            source_object.emit_to("You can't open an exit to an exit!")
            return

        new_object = Object.objects.create_object(exit_name,
                                                  defines_global.OTYPE_EXIT,
                                                  source_object.get_location(),
                                                  source_object,
                                                  destination)

        source_object.emit_to("You open the an exit - %s to %s" % (
                                                        new_object.get_name(),
                                                        destination.get_name()))
        if len(comma_split) > 1:
            second_exit_name = ','.join(comma_split[1:])
            #odat = {"name": second_exit_name, 
            #        "type": defines_global.OTYPE_EXIT, 
            #        "location": destination, 
            #        "owner": source_object, 
            #        "home": source_object.get_location()}
            new_object = Object.objects.create_object(second_exit_name,
                                                      defines_global.OTYPE_EXIT,
                                                      destination,
                                                      source_object,
                                                      source_object.get_location())
            source_object.emit_to("You open the an exit - %s to %s" % (
                                            new_object.get_name(),
                                            source_object.get_location().get_name()))

    else:
        # Create an un-linked exit.
        new_object = Object.objects.create_object(exit_name,
                                                  defines_global.OTYPE_EXIT,
                                                  source_object.get_location(),
                                                  source_object,
                                                  None)
        source_object.emit_to("You open an unlinked exit - %s" % new_object)
GLOBAL_CMD_TABLE.add_command("@open", cmd_open,
                             priv_tuple=("genperms.builder"))
        
def cmd_chown(command):
    """
    Changes the ownership of an object. The new owner specified must be a
    player object.

    Forms:
    @chown <Object>=<NewOwner>
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

        if not source_object.controls_other(target_obj):
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
GLOBAL_CMD_TABLE.add_command("@chown", cmd_chown)
    
def cmd_chzone(command):
    """
    Changes an object's zone. The specified zone may be of any object type, but
    will typically be a THING.

    Forms:
    @chzone <Object>=<NewZone>
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
GLOBAL_CMD_TABLE.add_command("@chzone", cmd_chzone)

def cmd_link(command):
    """
    Sets an object's home or an exit's destination.

    Forms:
    @link <Object>=<Target>
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: @link <object> = <target>")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    dest_name = eq_args[1]    

    if len(target_name) == 0:
        source_object.emit_to("What do you want to link?")
        return

    if len(eq_args) > 1:
        target_obj = source_object.search_for_object(target_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not source_object.controls_other(target_obj):
            source_object.emit_to(defines_global.NOCONTROL_MSG)
            return

        # If we do something like "@link blah=", we unlink the object.
        if len(dest_name) == 0:
            target_obj.set_home(None)
            source_object.emit_to("You have unlinked %s." % (target_obj,))
            return

        destination = source_object.search_for_object(dest_name)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not destination:
            return

        target_obj.set_home(destination)
        source_object.emit_to("You link %s to %s." % (target_obj, destination))

    else:
        # We haven't provided a target.
        source_object.emit_to("You must provide a destination to link to.")
        return
GLOBAL_CMD_TABLE.add_command("@link", cmd_link,
                             priv_tuple=("genperms.builder"))

def cmd_unlink(command):
    """
    Unlinks an object.
    
    @unlink <Object>
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
                             priv_tuple=("genperms.builder"))

def cmd_dig(command):
    """
    Creates a new room object and optionally connects it to
    where you are.
    
    Usage: 
       @dig[/switches] roomname [:parent] [= exitthere [: parent][;alias]] [, exithere [: parent][;alias]] 

    switches:
       teleport - move yourself to the new room

    example:
       @dig kitchen = north; n, south; s

    
    """
    source_object = command.source_object    
    args = command.command_argument
    switches = command.command_switches

    if not args:
        source_object.emit_to("Usage[/teleport]: @dig roomname [:parent][= exitthere [:parent] [;alias]] [, exithere [:parent] [;alias]]")
        return

    room_name = None
    room_parent = None    
    exit_names = [None,None]
    exit_parents = [None,None]
    exit_aliases = [[], []]
    
    #deal with arguments 
    arg_list = args.split("=",1)
    if len(arg_list) < 2:
        #just create a room, no exits
        room_name = largs[0].strip()
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
            aliaslist = exi.split(";")
            name_and_parent = aliaslist.pop(0) #pops the first index
            exit_aliases[ie] = aliaslist #what remains are the aliases
            try:
                exit_names[ie], exit_parents[ie] = [s.strip() for s in name_and_parent.split(":",1)]
            except ValueError:
                exit_names[ie] = name_and_parent.strip()

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
                                                      destination)
            ptext = ""
            if exit_parents[0]:
                script_parent = exit_parents[0]
                if new_object.get_script_parent() == script_parent:        
                    ptext += " of type %s" % script_parent
                else:
                    ptext += " of default type (parent '%s' failed!)" % script_parent
            source_object.emit_to("Created exit%s from %s to %s named '%s'." % (ptext,location,destination,new_object))
            #the ALIAS mechanism only works with one ALIAS at this time.
            try:
                new_object.set_attribute("ALIAS", exit_aliases[0][0])
            except IndexError:
                pass
                                
        if len(exit_names) > 1 and exit_names[1] != None:
            #create exit back from new room to this one.
            new_object = Object.objects.create_object(exit_names[1],
                                                      defines_global.OTYPE_EXIT,
                                                      destination,
                                                      source_object,
                                                      location)
            ptext = ""
            if exit_parents[1]:
                script_parent = exit_parents[1]
                if new_object.get_script_parent() == script_parent:        
                    ptext += " of type %s" % script_parent
                else:
                    ptext += " of default type (parent '%s' failed!)" % script_parent
            source_object.emit_to("Created exit%s back from %s to %s named '%s'." % \
                                  (ptext, destination, location, new_object))
            #the ALIAS mechanism only works with one ALIAS at this time.
            try:
                new_object.set_attribute("ALIAS", exit_aliases[1][0])
            except IndexError:
                pass

        if 'teleport' in switches:
            source_object.move_to(new_room)
               
GLOBAL_CMD_TABLE.add_command("@dig", cmd_dig,
                             priv_tuple=("genperms.builder"),)

def cmd_name(command):
    """
    Handle naming an object.
    
    @name <Object>=<Value>
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
GLOBAL_CMD_TABLE.add_command("@name", cmd_name)

def cmd_description(command):
    """
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
GLOBAL_CMD_TABLE.add_command("@describe", cmd_description)

def cmd_recover(command):
    """
    @recover 

    Recovers @destroyed non-player objects.

    Usage:
       @recover[/switches] [obj [,obj2, ...]] 

    switches:
       ROOM - recover as ROOM type instead of THING
       EXIT - recover as EXIT type instead of THING

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
                             priv_tuple=("genperms.builder"),auto_help=True,staff_help=True)

def cmd_destroy(command):
    """
    @destroy

    Destroys one or many objects. 

    Usage: 
       @destroy[/<switches>] obj [,obj2, obj3, ...]

    switches:
       override - The @destroy command will usually avoid accidentally destroying
                  player objects as well as objects with the SAFE flag. This
                  switch overrides this safety.     
       instant|now  - Destroy the object immediately, without delay. 

    The objects are set to GOING and will be permanently destroyed next time the system
    does cleanup. Until then non-player objects can still be saved  by using the
    @recover command. The contents of a room will be moved out before it is destroyed,
    and all exits leading to and fro the room will also be destroyed. Note that destroyed
    player objects can not be recovered by the @recover command.
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
                             priv_tuple=("genperms.builder"),auto_help=True,staff_help=True)
