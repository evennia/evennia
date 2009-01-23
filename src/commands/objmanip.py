"""
These commands typically are to do with building or modifying Objects.
"""
from src.objects.models import Object, Attribute
# We'll import this as the full path to avoid local variable clashes.
import src.flags
from src import ansi
from src import session_mgr

def cmd_teleport(command):
    """
    Teleports an object somewhere.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Teleport where/what?")
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
        victim = Object.objects.standard_plr_objsearch(session, eq_args[0])
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not victim:
            return

        destination = Object.objects.standard_plr_objsearch(session, eq_args[1])
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        if victim.is_room():
            session.msg("You can't teleport a room.")
            return

        if victim == destination:
            session.msg("You can't teleport an object inside of itself!")
            return
        session.msg("Teleported.")
        victim.move_to(destination, quiet=tel_quietly)
    else:
        # Direct teleport (no equal sign)
        target_obj = Object.objects.standard_plr_objsearch(session, 
                                                    command.command_argument)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if target_obj == pobject:
            session.msg("You can't teleport inside yourself!")
            return
        session.msg("Teleported.")
            
        pobject.move_to(target_obj, quiet=tel_quietly)

def cmd_stats(command):
    """
    Shows stats about the database.
    4012 objects = 144 rooms, 212 exits, 613 things, 1878 players. (1165 garbage)
    """
    session = command.session
    stats_dict = Object.objects.object_totals()
    session.msg("%d objects = %d rooms, %d exits, %d things, %d players. (%d garbage)" % 
       (stats_dict["objects"],
        stats_dict["rooms"],
        stats_dict["exits"],
        stats_dict["things"],
        stats_dict["players"],
        stats_dict["garbage"]))

def cmd_alias(command):
    """
    Assigns an alias to a player object for ease of paging, etc.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Alias whom?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2:
        session.msg("Alias missing.")
        return
    
    target_string = eq_args[0]
    new_alias = eq_args[1]
    
    # An Object instance for the victim.
    target = Object.objects.standard_plr_objsearch(session, target_string)
    # Use standard_plr_objsearch to handle duplicate/nonexistant results.
    if not target:
        session.msg("I can't find that player.")
        return
  
    old_alias = target.get_attribute_value('ALIAS')
    duplicates = Object.objects.player_alias_search(pobject, new_alias)
    if not duplicates or old_alias.lower() == new_alias.lower():
        # Either no duplicates or just changing the case of existing alias.
        if pobject.controls_other(target):
            target.set_attribute('ALIAS', new_alias)
            session.msg("Alias '%s' set for %s." % (new_alias, 
                                                    target.get_name()))
        else:
            session.msg("You do not have access to set an alias for %s." % 
                                                   (target.get_name(),))
    else:
        # Duplicates were found.
        session.msg("Alias '%s' is already in use." % (new_alias,))
        return

def cmd_wipe(command):
    """
    Wipes an object's attributes, or optionally only those matching a search
    string.
    """
    session = command.session
    pobject = session.get_pobject()
    attr_search = False

    if not command.command_argument:    
        session.msg("Wipe what?")
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

    target_obj = Object.objects.standard_plr_objsearch(session, attr_split[0])
    # Use standard_plr_objsearch to handle duplicate/nonexistant results.
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
            session.msg("%s - %d attributes wiped." % (target_obj.get_name(), 
                                                       len(attr_matches)))
        else:
            session.msg("No matching attributes found.")
    else:
        # User didn't specify a wild-card string, wipe entire object.
        attr_matches = target_obj.attribute_namesearch("*", exclude_noset=True)
        for attr in attr_matches:
            target_obj.clear_attribute(attr.get_name())
        session.msg("%s - %d attributes wiped." % (target_obj.get_name(), 
                                                   len(attr_matches)))

def cmd_set(command):
    """
    Sets flags or attributes on objects.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Set what?")
        return
  
    # Break into target and value by the equal sign.
    eq_args = command.command_argument.split('=', 1)
    if len(eq_args) < 2:
        # Equal signs are not optional for @set.
        session.msg("Set what?")
        return
    
    victim = Object.objects.standard_plr_objsearch(session, eq_args[0])
    # Use standard_plr_objsearch to handle duplicate/nonexistant results.
    if not victim:
        return

    if not pobject.controls_other(victim):
        session.msg(defines_global.NOCONTROL_MSG)
        return

    attrib_args = eq_args[1].split(':', 1)
    if len(attrib_args) > 1:
        # We're dealing with an attribute/value pair.
        attrib_name = attrib_args[0].upper()
        splicenum = eq_args[1].find(':') + 1
        attrib_value = eq_args[1][splicenum:]
        
        # In global_defines.py, see NOSET_ATTRIBS for protected attribute names.
        if not Attribute.objects.is_modifiable_attrib(attrib_name) and not pobject.is_superuser():
            session.msg("You can't modify that attribute.")
            return
        
        if attrib_value:
            # An attribute value was specified, create or set the attribute.
            verb = 'set'
            victim.set_attribute(attrib_name, attrib_value)
        else:
            # No value was given, this means we delete the attribute.
            verb = 'cleared'
            victim.clear_attribute(attrib_name)
        session.msg("%s - %s %s." % (victim.get_name(), attrib_name, verb))
    else:
        # Flag manipulation form.
        flag_list = eq_args[1].split()
        
        for flag in flag_list:
            flag = flag.upper()
            if flag[0] == '!':
                # We're un-setting the flag.
                flag = flag[1:]
                if not src.flags.is_modifiable_flag(flag):
                    session.msg("You can't set/unset the flag - %s." % (flag,))
                else:
                    session.msg('%s - %s cleared.' % (victim.get_name(), 
                                                      flag.upper(),))
                    victim.set_flag(flag, False)
            else:
                # We're setting the flag.
                if not src.flags.is_modifiable_flag(flag):
                    session.msg("You can't set/unset the flag - %s." % (flag,))
                else:
                    session.msg('%s - %s set.' % (victim.get_name(), 
                                                  flag.upper(),))
                    victim.set_flag(flag, True)

def cmd_find(command):
    """
    Searches for an object of a particular name.
    """
    session = command.session
    pobject = session.get_pobject()
    can_find = pobject.user_has_perm("genperms.builder")

    if not command.command_argument:
        session.msg("No search pattern given.")
        return
    
    searchstring = command.command_argument
    results = Object.objects.global_object_name_search(searchstring)

    if len(results) > 0:
        session.msg("Name matches for: %s" % (searchstring,))
        for result in results:
            session.msg(" %s" % (result.get_name(fullname=True),))
        session.msg("%d matches returned." % (len(results),))
    else:
        session.msg("No name matches found for: %s" % (searchstring,))

def cmd_create(command):
    """
    Creates a new object of type 'THING'.
    """
    session = command.session
    pobject = session.get_pobject()
    
    if not command.command_argument:
        session.msg("You must supply a name!")
    else:
        # Create and set the object up.
        # TODO: This dictionary stuff is silly. Feex.
        odat = {"name": command.command_argument, 
                "type": 3, 
                "location": pobject, 
                "owner": pobject}
        new_object = Object.objects.create_object(odat)
        
        session.msg("You create a new thing: %s" % (new_object,))
    
def cmd_cpattr(command):
    """
    Copies a given attribute to another object.

    @cpattr <source object>/<attribute> = <target1>/[<attrname>] <target n>/[<attrname n>]
    """

    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("What do you want to copy?")
        return

    # Split up source and target[s] via the equals sign.
    eq_args = command.command_argument.split('=', 1)

    if len(eq_args) < 2:
        # There must be both a source and a target pair for cpattr
        session.msg("You have not supplied both a source and a target[s]")
        return

    # Check that the source object and attribute exists, by splitting the eq_args 'source' entry with '/'
    source = eq_args[0].split('/', 1)
    source_string = source[0].strip()
    source_attr_string = source[1].strip().upper()

    # Check whether src_obj exists
    src_obj = Object.objects.standard_plr_objsearch(session, source_string)
    
    if not src_obj:
        session.msg("Source object does not exist")
        return
        
    # Check whether src_obj has src_attr
    src_attr = src_obj.attribute_namesearch(source_attr_string)
    
    if not src_attr:
        session.msg("Source object does not have attribute " + source[1].strip())
	return
    
    # For each target object, check it exists
    # Remove leading '' from the targets list.
    targets = eq_args[1].split(' ')[1:]

    for target in targets:
        tar = target.split('/', 1)
	tar_string = tar[0].strip()
	tar_attr_string = tar[1].strip().upper()

	tar_obj = Object.objects.standard_plr_objsearch(session, tar_string)

        # Does target exist?
	if not tar_obj:
            session.msg("Target object does not exist: " + tar_string)

        # If target attribute is not given, use source_attr_string for name
	if tar_attr_string == '':
            src_attr_contents = src_obj.get_attribute_value(source_attr_string)
            tar_obj.set_attribute(source_attr_string, src_attr_contents)
	    continue

	# If however, the target attribute is given, check it exists and update accordingly

        # Does target attribute exist?

	tar_attr = tar_obj.attribute_namesearch(tar_attr_string)

        # If the target object does not have the given attribute, make a new attr
	if not tar_attr:
	    src_attr_contents = src_obj.get_attribute_value(source_attr_string)
	    tar_obj.set_attribute(tar_attr_string, src_attr_contents)
            continue

        # If target has attribute, update its contents
        src_attr_contents = src_obj.get_attribute_value(source_attr_string)
        tar_obj.set_attribute(tar_attr_string, src_attr_contents)
	continue

def cmd_nextfree(command):
    """
    Returns the next free object number.
    """
    session = command.session
    
    nextfree = Object.objects.get_nextfree_dbnum()
    session.msg("Next free object number: #%s" % (nextfree,))
    
def cmd_open(command):
    """
    Handle the opening of exits.
    
    Forms:
    @open <Name>
    @open <Name>=<Dbref>
    @open <Name>=<Dbref>,<Name>
    """
    session = command.session
    pobject = session.get_pobject()
    
    if not command.command_argument:
        session.msg("Open an exit to where?")
        return
        
    eq_args = command.command_argument.split('=', 1)
    exit_name = eq_args[0]
    
    if len(exit_name) == 0:
        session.msg("You must supply an exit name.")
        return
        
    # If we have more than one entry in our '=' delimited argument list,
    # then we're doing a @open <Name>=<Dbref>[,<Name>]. If not, we're doing
    # an un-linked exit, @open <Name>.
    if len(eq_args) > 1:
        # Opening an exit to another location via @open <Name>=<Dbref>[,<Name>].
        comma_split = eq_args[1].split(',', 1)
        destination = Object.objects.standard_plr_objsearch(session, 
                                                            comma_split[0])
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        if destination.is_exit():
            session.msg("You can't open an exit to an exit!")
            return

        odat = {"name": exit_name, 
                "type": 4, 
                "location": pobject.get_location(), 
                "owner": pobject, 
                "home":destination}
        new_object = Object.objects.create_object(odat)

        session.msg("You open the an exit - %s to %s" % (new_object.get_name(),
                                                         destination.get_name()))
        if len(comma_split) > 1:
            second_exit_name = ','.join(comma_split[1:])
            odat = {"name": second_exit_name, 
                    "type": 4, 
                    "location": destination, 
                    "owner": pobject, 
                    "home": pobject.get_location()}
            new_object = Object.objects.create_object(odat)
            session.msg("You open the an exit - %s to %s" % (
                                            new_object.get_name(),
                                            pobject.get_location().get_name()))

    else:
        # Create an un-linked exit.
        odat = {"name": exit_name, 
                "type": 4, 
                "location": pobject.get_location(), 
                "owner": pobject, 
                "home":None}
        new_object = Object.objects.create_object(odat)

        session.msg("You open an unlinked exit - %s" % (new_object,))
        
def cmd_chown(command):
    """
    Changes the ownership of an object. The new owner specified must be a
    player object.

    Forms:
    @chown <Object>=<NewOwner>
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Change the ownership of what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    owner_name = eq_args[1]    

    if len(target_name) == 0:
        session.msg("Change the ownership of what?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_plr_objsearch(session, target_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not pobject.controls_other(target_obj):
            session.msg(defines_global.NOCONTROL_MSG)
            return

        owner_obj = Object.objects.standard_plr_objsearch(session, owner_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not owner_obj:
            return
        
        if not owner_obj.is_player():
            session.msg("Only players may own objects.")
            return
        if target_obj.is_player():
            session.msg("You may not change the ownership of player objects.")
            return

        target_obj.set_owner(owner_obj)
        session.msg("%s now owns %s." % (owner_obj, target_obj))

    else:
        # We haven't provided a target.
        session.msg("Who should be the new owner of the object?")
        return
    
def cmd_chzone(command):
    """
    Changes an object's zone. The specified zone may be of any object type, but
    will typically be a THING.

    Forms:
    @chzone <Object>=<NewZone>
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Change the zone of what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    zone_name = eq_args[1]    

    if len(target_name) == 0:
        session.msg("Change the zone of what?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_plr_objsearch(session, target_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not pobject.controls_other(target_obj):
            session.msg(defines_global.NOCONTROL_MSG)
            return

        # Allow the clearing of a zone
        if zone_name.lower() == "none":
            target_obj.set_zone(None)
            session.msg("%s is no longer zoned." % (target_obj))
            return
        
        zone_obj = Object.objects.standard_plr_objsearch(session, zone_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not zone_obj:
            return

        target_obj.set_zone(zone_obj)
        session.msg("%s is now in zone %s." % (target_obj, zone_obj))

    else:
        # We haven't provided a target zone.
        session.msg("What should the object's zone be set to?")
        return

def cmd_link(command):
    """
    Sets an object's home or an exit's destination.

    Forms:
    @link <Object>=<Target>
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument:
        session.msg("Link what?")
        return

    eq_args = command.command_argument.split('=', 1)
    target_name = eq_args[0]
    dest_name = eq_args[1]    

    if len(target_name) == 0:
        session.msg("What do you want to link?")
        return

    if len(eq_args) > 1:
        target_obj = Object.objects.standard_plr_objsearch(session, target_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not pobject.controls_other(target_obj):
            session.msg(defines_global.NOCONTROL_MSG)
            return

        # If we do something like "@link blah=", we unlink the object.
        if len(dest_name) == 0:
            target_obj.set_home(None)
            session.msg("You have unlinked %s." % (target_obj,))
            return

        destination = Object.objects.standard_plr_objsearch(session, dest_name)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not destination:
            return

        target_obj.set_home(destination)
        session.msg("You link %s to %s." % (target_obj,destination))

    else:
        # We haven't provided a target.
        session.msg("You must provide a destination to link to.")
        return

def cmd_unlink(command):
    """
    Unlinks an object.
    
    @unlink <Object>
    """
    session = command.session
    pobject = session.get_pobject()
    
    if not command.command_argument:    
        session.msg("Unlink what?")
        return
    else:
        target_obj = Object.objects.standard_plr_objsearch(session,
                                                      command.command_argument)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not pobject.controls_other(target_obj):
            session.msg(defines_global.NOCONTROL_MSG)
            return

        target_obj.set_home(None)
        session.msg("You have unlinked %s." % (target_obj.get_name(),))

def cmd_dig(command):
    """
    Creates a new object of type 'ROOM'.
    
    @dig <Name>
    """
    session = command.session
    pobject = session.get_pobject()
    roomname = command.command_argument
    
    if not roomname:
        session.msg("You must supply a name!")
    else:
        # Create and set the object up.
        odat = {"name": roomname, 
                "type": 2, 
                "location": None, 
                "owner": pobject}
        new_object = Object.objects.create_object(odat)
        
        session.msg("You create a new room: %s" % (new_object,))

def cmd_name(command):
    """
    Handle naming an object.
    
    @name <Object>=<Value>
    """
    session = command.session
    pobject = session.get_pobject()
    
    if not command.command_argument:    
        session.msg("What do you want to name?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    # Only strip spaces from right side in case they want to be silly and
    # have a left-padded object name.
    new_name = eq_args[1].rstrip()
    
    if len(eq_args) < 2 or eq_args[1] == '':
        session.msg("What would you like to name that object?")
    else:
        target_obj = Object.objects.standard_plr_objsearch(session, eq_args[0])
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return
        
        ansi_name = ansi.parse_ansi(new_name, strip_formatting=True)
        session.msg("You have renamed %s to %s." % (target_obj, ansi_name))
        target_obj.set_name(new_name)

def cmd_description(command):
    """
    Set an object's description.
    """
    session = command.session
    pobject = session.get_pobject()
    
    if not command.command_argument:    
        session.msg("What do you want to describe?")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) < 2 or eq_args[1] == '':
        session.msg("How would you like to describe that object?")
    else:
        target_obj = Object.objects.standard_plr_objsearch(session, eq_args[0])
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

        if not pobject.controls_other(target_obj):
            session.msg(defines_global.NOCONTROL_MSG)
            return

        new_desc = eq_args[1]
        session.msg("%s - DESCRIPTION set." % (target_obj,))
        target_obj.set_description(new_desc)

def cmd_destroy(command):
    """
    Destroy an object.
    """
    session = command.session
    pobject = session.get_pobject()
    switch_override = False
       
    if not command.command_argument:    
        session.msg("Destroy what?")
        return
    
    # Safety feature. Switch required to delete players and SAFE objects.
    if "override" in command.command_switches:
        switch_override = True
        
    target_obj = Object.objects.standard_plr_objsearch(session,
                                                       command.command_argument)
    # Use standard_plr_objsearch to handle duplicate/nonexistant results.
    if not target_obj:
        return
    
    if target_obj.is_player():
        if pobject.id == target_obj.id:
            session.msg("You can't destroy yourself.")
            return
        if not switch_override:
            session.msg("You must use @destroy/override on players.")
            return
        if target_obj.is_superuser():
            session.msg("You can't destroy a superuser.")
            return
    elif target_obj.is_going() or target_obj.is_garbage():
        session.msg("That object is already destroyed.")
        return
    
    session.msg("You destroy %s." % (target_obj.get_name(),))
    target_obj.destroy()
