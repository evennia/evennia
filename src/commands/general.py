"""
Generic command module. Pretty much every command should go here for
now.
"""
import time

from django.conf import settings

from src.config.models import ConfigValue
from src.helpsys.models import HelpEntry
from src.objects.models import Object
from src import defines_global
from src import session_mgr
from src import ansi
from src.util import functions_general

def cmd_password(command):
    """
    Changes your own password.
    
    @password <Oldpass>=<Newpass>
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("This command requires arguments.")
        return
    
    if not source_object.is_player():
        source_object.emit_to("This is only applicable for players.")
        return
    
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) != 2:
        source_object.emit_to("Incorrect number of arguments.")
        return
    
    oldpass = eq_args[0]
    newpass = eq_args[1]
    
    if len(oldpass) == 0:    
        source_object.emit_to("You must provide your old password.")
    elif len(newpass) == 0:
        source_object.emit_to("You must provide your new password.")
    else:
        uaccount = source_object.get_user_account()
        
        if not uaccount.check_password(oldpass):
            source_object.emit_to("The specified old password isn't correct.")
        elif len(newpass) < 3:
            source_object.emit_to("Passwords must be at least three characters long.")
            return
        else:
            uaccount.set_password(newpass)
            uaccount.save()
            source_object.emit_to("Password changed.")

def cmd_pemit(command):        
    """
    Emits something to a player.
    """
    # TODO: Implement cmd_pemit

def cmd_emit(command):        
    """
    Emits something to your location.
    """
    message = command.command_argument
    
    if message:
        command.source_object.get_location().emit_to_contents(message)
    else:
        command.source_object.emit_to("Emit what?")

def cmd_wall(command):
    """
    Announces a message to all connected players.
    """
    wallstring = command.command_argument
        
    if not wallstring:
        command.source_object.emit_to("Announce what?")
        return
        
    message = "%s shouts \"%s\"" % (
            command.source_object.get_name(show_dbref=False), wallstring)
    session_mgr.announce_all(message)

def cmd_idle(command):
    """
    Returns nothing, this lets the player set an idle timer without spamming
    his screen.
    """
    pass
    
def cmd_inventory(command):
    """
    Shows a player's inventory.
    """
    source_object = command.source_object
    source_object.emit_to("You are carrying:")
    
    for item in source_object.get_contents():
        source_object.emit_to(" %s" % (item.get_name(),))
        
    money = int(source_object.get_attribute_value("MONEY", default=0))
    if money == 1:
        money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_SINGULAR")
    else:
        money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_PLURAL")

    source_object.emit_to("You have %d %s." % (money, money_name))

def cmd_look(command):
    """
    Handle looking at objects.
    """
    source_object = command.source_object
    
    # If an argument is provided with the command, search for the object.
    # else look at the current room. 
    if command.command_argument:    
        target_obj = source_object.search_for_object(command.command_argument)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return
    else:
        target_obj = source_object.get_location()
    
    # SCRIPT: Get the item's appearance from the scriptlink.
    source_object.emit_to(target_obj.scriptlink.return_appearance({
        "target_obj": target_obj,
        "pobject": source_object
    }))
            
    # SCRIPT: Call the object's script's a_desc() method.
    target_obj.scriptlink.a_desc({
        "target_obj": source_object
    })
            
def cmd_get(command):
    """
    Get an object and put it in a player's inventory.
    """
    source_object = command.source_object
    obj_is_staff = source_object.is_staff()

    if not command.command_argument:    
        source_object.emit_to("Get what?")
        return
    else:
        target_obj = source_object.search_for_object(command.command_argument, 
                                                     search_contents=False)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

    if source_object == target_obj:
        source_object.emit_to("You can't get yourself.")
        return
    
    if not obj_is_staff and (target_obj.is_player() or target_obj.is_exit()):
        source_object.emit_to("You can't get that.")
        return
        
    if target_obj.is_room() or target_obj.is_garbage() or target_obj.is_going():
        source_object.emit_to("You can't get that.")
        return
        
    target_obj.move_to(source_object, quiet=True)
    source_object.emit_to("You pick up %s." % (target_obj.get_name(show_dbref=False),))
    source_object.get_location().emit_to_contents("%s picks up %s." % 
                                    (source_object.get_name(show_dbref=False), 
                                     target_obj.get_name(show_dbref=False)), 
                                     exclude=source_object)
    
    # SCRIPT: Call the object's script's a_get() method.
    target_obj.scriptlink.a_get({
        "pobject": source_object
    })
            
def cmd_drop(command):
    """
    Drop an object from a player's inventory into their current location.
    """
    source_object = command.source_object
    obj_is_staff = source_object.is_staff()

    if not command.command_argument:    
        source_object.emit_to("Drop what?")
        return
    else:
        target_obj = source_object.search_for_object(command.command_argument, 
                                                     search_location=False)
        # Use search_for_object to handle duplicate/nonexistant results.
        if not target_obj:
            return

    if not source_object == target_obj.get_location():
        source_object.emit_to("You don't appear to be carrying that.")
        return
        
    target_obj.move_to(source_object.get_location(), quiet=True)
    source_object.emit_to("You drop %s." % (target_obj.get_name(show_dbref=False),))
    source_object.get_location().emit_to_contents("%s drops %s." % 
                                            (source_object.get_name(show_dbref=False), 
                                             target_obj.get_name(show_dbref=False)), 
                                             exclude=source_object)

    # SCRIPT: Call the object's script's a_drop() method.
    target_obj.scriptlink.a_drop({
        "pobject": source_object
    })
            
def cmd_examine(command):
    """
    Detailed object examine command
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
        """
        Player did something like: examine me/* or examine me/TE*. Return
        each matching attribute with its value.
        """
        attr_matches = target_obj.attribute_namesearch(attr_searchstr)
        if attr_matches:
            for attribute in attr_matches:
                source_object.emit_to(attribute.get_attrline())
        else:
            source_object.emit_to("No matching attributes found.")
    else:
        """
        Player is examining an object. Return a full readout of attributes,
        along with detailed information about said object.
        """
        # Format the examine header area with general flag/type info.
        source_object.emit_to(target_obj.get_name(fullname=True))
        source_object.emit_to("Type: %s Flags: %s" % (target_obj.get_type(), 
                                            target_obj.get_flags()))
        source_object.emit_to("Desc: %s" % target_obj.get_description(no_parsing=True))
        source_object.emit_to("Owner: %s " % (target_obj.get_owner(),))
        source_object.emit_to("Zone: %s" % (target_obj.get_zone(),))
        
        parent_str = target_obj.script_parent
        if parent_str and parent_str != '':
            source_object.emit_to("Parent: %s " % (parent_str,))
        
        for attribute in target_obj.get_all_attributes():
            source_object.emit_to(attribute.get_attrline())
        
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
        
        # Render Contents display.
        if con_players or con_things:
            source_object.emit_to("%sContents:%s" % (ansi.ansi["hilite"], 
                                                  ansi.ansi["normal"],))
            for player in con_players:
                source_object.emit_to('%s' % (player.get_name(fullname=True),))
            for thing in con_things:
                source_object.emit_to('%s' % (thing.get_name(fullname=True),))
                
        # Render Exists display.
        if con_exits:
            source_object.emit_to("%sExits:%s" % (ansi.ansi["hilite"], 
                                        ansi.ansi["normal"],))
            for exit in con_exits:
                source_object.emit_to('%s' %(exit.get_name(fullname=True),))
        
        # Render the object's home or destination (for exits).
        if not target_obj.is_room():
            if target_obj.is_exit():
                # The Home attribute on an exit is really its destination.
                source_object.emit_to("Destination: %s" % (target_obj.get_home(),))
            else:
                # For everything else, home is home.
                source_object.emit_to("Home: %s" % (target_obj.get_home(),))
            # This obviously isn't valid for rooms.    
            source_object.emit_to("Location: %s" % (target_obj.get_location(),))
    
def cmd_quit(command):
    """
    Gracefully disconnect the user as per his own request.
    """
    if command.session:
        session = command.session
        session.msg("Quitting!")
        session.handle_close()
    
def cmd_who(command):
    """
    Generic WHO command.
    """
    session_list = session_mgr.get_session_list()
    source_object = command.source_object
    
    # In the case of the DOING command, don't show session data regardless.
    if command.extra_vars and command.extra_vars.get("show_session_data", None) == False:
        show_session_data = False
    else:
        show_session_data = source_object.has_perm("genperms.see_session_data")

    # Only those with the see_session_data or superuser status can see
    # session details.
    if show_session_data:
        retval = "Player Name               On For Idle   Room    Cmds   Host\n\r"
    else:
        retval = "Player Name               On For Idle\n\r"
        
    for player in session_list:
        if not player.logged_in:
            continue
        delta_cmd = time.time() - player.cmd_last_visible
        delta_conn = time.time() - player.conn_time
        plr_pobject = player.get_pobject()

        if show_session_data:
            retval += '%-31s%9s %4s%-3s#%-6d%5d%3s%-25s\r\n' % \
                (plr_pobject.get_name(show_dbref=True, show_flags=False)[:25], \
                # On-time
                functions_general.time_format(delta_conn,0), \
                # Idle time
                functions_general.time_format(delta_cmd,1), \
                # Flags
                '', \
                # Location
                plr_pobject.get_location().id, \
                player.cmd_total, \
                # More flags?
                '', \
                player.address[0])
        else:
            retval += '%-31s%9s %4s%-3s\r\n' % \
                (plr_pobject.get_name(show_dbref=False)[:25], \
                # On-time
                functions_general.time_format(delta_conn,0), \
                # Idle time
                functions_general.time_format(delta_cmd,1), \
                # Flags
                '')
    retval += '%d Players logged in.' % (len(session_list),)
    
    source_object.emit_to(retval)

def cmd_say(command):
    """
    Room-based speech command.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Say what?")
        return
    
    speech = command.command_argument
        
    # Feedback for the object doing the talking.
    source_object.emit_to("You say, '%s'" % (speech,))
    
    # Build the string to emit to neighbors.
    emit_string = "%s says, '%s'" % (source_object.get_name(show_dbref=False), 
                                     speech)
    
    source_object.get_location().emit_to_contents(emit_string, 
                                                  exclude=source_object)

def cmd_pose(command):
    """
    Pose/emote command.
    """
    source_object = command.source_object

    if not command.command_argument: 
        source_object.emit_to("Do what?")
        return
    
    pose_string = command.command_argument
    
    if "nospace" in command.command_switches:
        # Output without a space between the player name and the emote.
        sent_msg = "%s%s" % (source_object.get_name(show_dbref=False), 
                             pose_string)
    else:
        # No switches, default.
        sent_msg = "%s %s" % (source_object.get_name(show_dbref=False), 
                              pose_string)
    
    source_object.get_location().emit_to_contents(sent_msg)
    
def cmd_help(command):
    """
    Help system commands.
    """
    source_object = command.source_object
    topicstr = command.command_argument
    
    if not command.command_argument:
        topicstr = "Help Index"    
    elif len(topicstr) < 2 and not topicstr.isdigit():
        source_object.emit_to("Your search query is too short. It must be at least three letters long.")
        return
        
    topics = HelpEntry.objects.find_topicmatch(source_object, topicstr)        
        
    if len(topics) == 0:
        source_object.emit_to("No matching topics found, please refine your search.")
        suggestions = HelpEntry.objects.find_topicsuggestions(source_object, 
                                                              topicstr)
        if len(suggestions) > 0:
            source_object.emit_to("Matching similarly named topics:")
            for result in suggestions:
                source_object.emit_to(" %s" % (result,))
                source_object.emit_to("You may type 'help <#>' to see any of these topics.")
    elif len(topics) > 1:
        source_object.emit_to("More than one match found:")
        for result in topics:
            source_object.emit_to("%3d. %s" % (result.id, result.get_topicname()))
        source_object.emit_to("You may type 'help <#>' to see any of these topics.")
    else:    
        topic = topics[0]
        source_object.emit_to("\n\r"+ topic.get_entrytext_ingame())
