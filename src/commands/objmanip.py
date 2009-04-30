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
        source_object.emit_to("Teleport where/what?")
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
        source_object.emit_to("Alias whom?")
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
    print "ALIAS", old_alias
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
        source_object.emit_to("Wipe what?")
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

    if not command.command_argument:
        source_object.emit_to("Set what?")
        return
  
    # Break into target and value by the equal sign.
    eq_args = command.command_argument.split('=', 1)
    if len(eq_args) < 2:
        # Equal signs are not optional for @set.
        source_object.emit_to("Set what?")
        return
    
    victim = source_object.search_for_object(eq_args[0])
    # Use search_for_object to handle duplicate/nonexistant results.
    if not victim:
        return

    if not source_object.controls_other(victim):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return

    attrib_args = eq_args[1].split(':', 1)
    if len(attrib_args) > 1:
        # We're dealing with an attribute/value pair.
        attrib_name = attrib_args[0]
        splicenum = eq_args[1].find(':') + 1
        attrib_value = (eq_args[1][splicenum:]).strip()
        
        # In global_defines.py, see NOSET_ATTRIBS for protected attribute names.
        if not Attribute.objects.is_modifiable_attrib(attrib_name):
            source_object.emit_to("You can't modify that attribute.")
            return
        
        if attrib_value:
            # An attribute value was specified, create or set the attribute.
            verb = 'set'
            victim.set_attribute(attrib_name, attrib_value)
        else:
            # No value was given, this means we delete the attribute.
            ok = victim.clear_attribute(attrib_name)
            if ok: verb = 'attribute cleared'
            else: verb = 'is not a known attribute. If it is a flag, use !flag to clear it'

            victim.clear_attribute(attrib_name)
        source_object.emit_to("%s - %s %s." % (victim.get_name(), attrib_name, verb))
    else:
        # Flag manipulation form.
        flag_list = eq_args[1].split()
        
        for flag in flag_list:
            flag = flag.upper()
            if flag[0] == '!':
                # We're un-setting the flag.
                flag = flag[1:]
                if not src.flags.is_modifiable_flag(flag):
                    source_object.emit_to("You can't set/unset the flag - %s." % (flag,))
                else:
                    source_object.emit_to('%s - %s cleared.' % (victim.get_name(), 
                                                                flag.upper(),))
                    victim.set_flag(flag, False)
            else:
                # We're setting the flag.
                if not src.flags.is_modifiable_flag(flag):
                    source_object.emit_to("You can't set/unset the flag - %s." % flag)
                else:
                    source_object.emit_to('%s - %s set.' % (victim.get_name(), 
                                                            flag.upper(),))
                    victim.set_flag(flag, True)
GLOBAL_CMD_TABLE.add_command("@set", cmd_set)

def cmd_find(command):
    """
    Searches for an object of a particular name.
    """
    source_object = command.source_object
    can_find = source_object.has_perm("genperms.builder")

    if not command.command_argument:
        source_object.emit_to("No search pattern given.")
        return
    
    searchstring = command.command_argument
    results = Object.objects.global_object_name_search(searchstring)

    if len(results) > 0:
        source_object.emit_to("Name matches for: %s" % (searchstring,))
        for result in results:
            source_object.emit_to(" %s" % (result.get_name(fullname=True),))
        source_object.emit_to("%d matches returned." % (len(results),))
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
    have a correct parent object defined in parents/examples/red_button.py, you could
    load create a new object inheriting from this parent like this:
       @create button:examples.red_button       
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("You must supply a name!")
        return
    
    eq_args = command.command_argument.split(':', 1)
    target_name = eq_args[0]
    
    # Create and set the object up.
    # TODO: This dictionary stuff is silly. Feex.
    odat = {"name": target_name, 
            "type": defines_global.OTYPE_THING, 
            "location": source_object, 
            "owner": source_object}
    new_object = Object.objects.create_object(odat)

    if len(eq_args)>1:
        parent_str = eq_args[1]
        if parent_str and new_object.set_script_parent(parent_str):
            source_object.emit_to("You create %s as a child of %s." %
                                  (new_object, parent_str))
        else:                
            source_object.emit_to("'%s' is not a valid parent. Using default." %
                                  parent_str)
    else:        
        source_object.emit_to("You create a new thing: %s" % (new_object,))

    # Trigger stuff to happen after said object is created.
    new_object.scriptlink.at_object_creation()

GLOBAL_CMD_TABLE.add_command("@create", cmd_create,
                             priv_tuple=("genperms.builder"),auto_help=True)
    
def cmd_cpattr(command):
    """
    Copies a given attribute to another object.

    @cpattr <obj>/<attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <obj>/<attr> = <obj1> [,<obj2>,<obj3>,...]
    @cpattr <attr> = <obj1>/<attr1> [,<obj2>/<attr2>,<obj3>/<attr3>,...]
    @cpattr <attr> = <obj1>[,<obj2>,<obj3>,...]
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("What do you want to copy?")
        return

    # Split up source and target[s] via the equals sign.
    eq_args = command.command_argument.split('=', 1)

    if len(eq_args) < 2:
        # There must be both a source and a target pair for cpattr
        source_object.emit_to("You have not supplied both a source and a target(s).")
        return

    # Check that the source object and attribute exists, by splitting the eq_args 'source' entry with '/'
    source = eq_args[0].split('/', 1)
    source_string = source[0].strip()
    source_attr_string = source[1].strip().upper()

    # Check whether src_obj exists
    src_obj = source_object.search_for_object(source_string)
    
    if not src_obj:
        source_object.emit_to("Source object does not exist.")
        return
        
    # Check whether src_obj has src_attr
    src_attr = src_obj.attribute_namesearch(source_attr_string)
    
    if not src_attr:
        source_object.emit_to("Source object does not have attribute: %s" + source_attr_string)
        return
    
    # For each target object, check it exists
    # Remove leading '' from the targets list.
    targets = eq_args[1].strip().split(',')

    for target in targets:
        tar = target.split('/', 1)
        tar_string = tar[0].strip()
        tar_attr_string = tar[1].strip().upper()

        tar_obj = source_object.search_for_object(tar_string)

        # Does target exist?
        if not tar_obj:
            source_object.emit_to("Target object does not exist: " + tar_string)
            # Continue if target does not exist, but give error on this item
            continue

        # If target attribute is not given, use source_attr_string for name
        if tar_attr_string == '':
            tar_attr_string = source_attr_string

        # Set or update the new attribute on the target object
        src_attr_contents = src_obj.get_attribute_value(source_attr_string)
        tar_obj.set_attribute(tar_attr_string, src_attr_contents)
        source_object.emit_to("%s - %s set." % (tar_obj.get_name(), 
                                                tar_attr_string))
GLOBAL_CMD_TABLE.add_command("@cpattr", cmd_cpattr,
                             priv_tuple=("genperms.builder"))

def cmd_nextfree(command):
    """
    Returns the next free object number.
    """   
    nextfree = Object.objects.get_nextfree_dbnum()
    command.source_object.emit_to("Next free object number: #%s" % nextfree)
GLOBAL_CMD_TABLE.add_command("@nextfree", cmd_nextfree,
                             priv_tuple=("genperms.builder"))
    
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
        source_object.emit_to("Open an exit to where?")
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

        odat = {"name": exit_name, 
                "type": defines_global.OTYPE_EXIT, 
                "location": source_object.get_location(), 
                "owner": source_object, 
                "home": destination}
        new_object = Object.objects.create_object(odat)

        source_object.emit_to("You open the an exit - %s to %s" % (
                                                        new_object.get_name(),
                                                        destination.get_name()))
        if len(comma_split) > 1:
            second_exit_name = ','.join(comma_split[1:])
            odat = {"name": second_exit_name, 
                    "type": defines_global.OTYPE_EXIT, 
                    "location": destination, 
                    "owner": source_object, 
                    "home": source_object.get_location()}
            new_object = Object.objects.create_object(odat)
            source_object.emit_to("You open the an exit - %s to %s" % (
                                            new_object.get_name(),
                                            source_object.get_location().get_name()))

    else:
        # Create an un-linked exit.
        odat = {"name": exit_name, 
                "type": defines_global.OTYPE_EXIT, 
                "location": source_object.get_location(), 
                "owner": source_object, 
                "home": None}
        new_object = Object.objects.create_object(odat)

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
        source_object.emit_to("Change the ownership of what?")
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
        source_object.emit_to("Change the zone of what?")
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
        source_object.emit_to("Link what?")
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
        source_object.emit_to("Unlink what?")
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
    Creates a new room object.
    
    @dig[/teleport] roomname [:parent] [=exitthere,exithere]
   
    """
    source_object = command.source_object
    
    args = command.command_argument
    switches = command.command_switches

    parent = ''
    exits = []

    #handle arguments
    if ':' in args:
        roomname, args = args.split(':',1)
        if '=' in args:
            parent, args = args.split('=',1)
            if ',' in args:
                exits = args.split(',',1)
            else:
                exits = args
        else:
            parent = args
    elif '=' in args:
        roomname, args = args.split('=',1)
        if ',' in args:
            exits = args.split(',',1)
        else:
            exits = [args]
    else:
        roomname = args
            
    if not roomname:
        source_object.emit_to("You must supply a new room name.")
    else:
        # Create and set the object up.
        odat = {"name": roomname, 
                "type": defines_global.OTYPE_ROOM, 
                "location": None, 
                "owner": source_object}
        new_room = Object.objects.create_object(odat)
        source_object.emit_to("Created a new room '%s'." % (new_room,))
        
        if parent:
            #(try to) set the script parent
            if not new_room.set_script_parent(parent):
                source_object.emit_to("%s is not a valid parent. Used default room." % parent)
        if exits:
            #create exits to (and possibly back from) the new room)
            destination = new_room #search_for_object(roomname)
            
            if destination and not destination.is_exit():
                location = source_object.get_location()

                #create an exit from here to the new room. 
                odat = {"name": exits[0].strip(), 
                        "type": defines_global.OTYPE_EXIT, 
                        "location": location, 
                        "owner": source_object, 
                        "home": destination}
                new_object = Object.objects.create_object(odat)
                source_object.emit_to("Created exit from %s to %s named '%s'." % (location,destination,new_object))

                if len(exits)>1:
                    #create exit back to this room
                    odat = {"name": exits[1].strip(), 
                            "type": defines_global.OTYPE_EXIT, 
                            "location": destination, 
                            "owner": source_object, 
                            "home": location}
                    new_object = Object.objects.create_object(odat)
                    source_object.emit_to("Created exit back from %s to %s named '%s'" % (destination, location, new_object))
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
        source_object.emit_to("What do you want to name?")
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
    
    if not command.command_argument:    
        source_object.emit_to("What do you want to describe?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        source_object.emit_to("How would you like to describe that object?")
        return

    target_obj = source_object.search_for_object(eq_args[0])
    # Use search_for_object to handle duplicate/nonexistant results.
    if not target_obj:
        return

    if not source_object.controls_other(target_obj):
        source_object.emit_to(defines_global.NOCONTROL_MSG)
        return

    new_desc = eq_args[1]
    if new_desc == '':
        source_object.emit_to("%s - DESCRIPTION cleared." % target_obj)
        target_obj.set_description(None)
    else:
        source_object.emit_to("%s - DESCRIPTION set." % target_obj)
        target_obj.set_description(new_desc)
GLOBAL_CMD_TABLE.add_command("@describe", cmd_description)

def cmd_recover(command):
    """
    @recover 

    Recovers @destroyed non-player objects.

    Usage:
       @recover [dbref [,dbref2, etc]] 

    switches:
       ROOM - recover as ROOM type instead of THING
       EXIT - recover as EXIT type instead of THING

    If no argument is given, a list of all recoverable objects will be given. 
    
    Objects scheduled for destruction with the @destroy command is cleaned out
    by the game at regular intervals. Up until the time of the next cleanup you can
    recover the object using this command (use @ps to check when the next cleanup is due).
    Note that exits and objects in @destroyed rooms will not be automatically recovered
    to its former state, you have to @recover those objects manually.

    The object type is forgotten, so the object is returned as type ITEM if not the
    switches /ROOM or /EXIT is given. Note that recovering an item as the wrong type will
    most likely make it nonfunctional. 
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
                             priv_tuple=("genperms.builder"),auto_help=True,staff_only=True)

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
       instant  - Destroy the object immediately, without delay. 

    The objects are set to GOING and will be permanently destroyed next time the system
    does cleanup. Until then non-player objects can still be saved  by using the
    @recover command. The contents of a room will be moved out before it is destroyed,
    but its exits will also be destroyed. Note that player objects can not be recovered. 
    """

    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args:    
        source_object.emit_to("Destroy what?")
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

        if 'instant' in switches:
            #sets to GARBAGE right away (makes dbref available)
            target_obj.delete()
            source_object.emit_to("You destroy %s." % target_obj.get_name())
        else:
            source_object.emit_to("You schedule %s for destruction." % target_obj.get_name())
        
GLOBAL_CMD_TABLE.add_command("@destroy", cmd_destroy,
                             priv_tuple=("genperms.builder"),auto_help=True,staff_only=True)
