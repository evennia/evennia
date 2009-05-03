"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.conf import settings
from src.config.models import ConfigValue
from src.helpsys.models import HelpEntry
from src.objects.models import Object
from src.ansi import ANSITable
from src import defines_global
from src import session_mgr
from src import ansi
from src.util import functions_general
import src.helpsys.management.commands.edit_helpfiles as edit_help
from src.cmdtable import GLOBAL_CMD_TABLE

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
GLOBAL_CMD_TABLE.add_command("@password", cmd_password)

def cmd_pemit(command):        
    """
    Emits something to a player.
    """
    # TODO: Implement cmd_pemit
#GLOBAL_CMD_TABLE.add_command("@pemit", cmd_pemit)

def cmd_emit(command):        
    """
    Emits something to your location.
    """
    message = command.command_argument
    
    if message:
        command.source_object.get_location().emit_to_contents(message)
    else:
        command.source_object.emit_to("Emit what?")
GLOBAL_CMD_TABLE.add_command("@emit", cmd_emit,
                             priv_tuple=("genperms.announce")),

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
GLOBAL_CMD_TABLE.add_command("@wall", cmd_wall,
                             priv_tuple=("genperms.announce"))

def cmd_idle(command):
    """
    Returns nothing, this lets the player set an idle timer without spamming
    his screen.
    """
    pass
GLOBAL_CMD_TABLE.add_command("idle", cmd_idle)
    
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
GLOBAL_CMD_TABLE.add_command("inventory", cmd_inventory)

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
    source_object.emit_to(target_obj.scriptlink.return_appearance(pobject=source_object))
            
    # SCRIPT: Call the object's script's at_desc() method.
    target_obj.scriptlink.at_desc(pobject=source_object)
GLOBAL_CMD_TABLE.add_command("look", cmd_look)
            
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
    target_obj.scriptlink.at_get(source_object)
GLOBAL_CMD_TABLE.add_command("get", cmd_get)    
            
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
    target_obj.scriptlink.at_drop(source_object)
GLOBAL_CMD_TABLE.add_command("drop", cmd_drop),
            
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
        s = ""        
        newl = "\r\n"
        # Format the examine header area with general flag/type info.
        
        s += str(target_obj.get_name(fullname=True)) + newl
        s += str("Type: %s Flags: %s" % (target_obj.get_type(), 
                                         target_obj.get_flags())) + newl
        #s += str("Desc: %s" % target_obj.get_attribute_value('desc')) + newl
        s += str("Owner: %s " % target_obj.get_owner()) + newl
        s += str("Zone: %s" % target_obj.get_zone()) + newl
        s += str("Parent: %s " % target_obj.get_script_parent()) + newl
        
        for attribute in target_obj.get_all_attributes():            
            s += str(attribute.get_attrline()) + newl
        
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
            s += str("%sContents:%s" % (ANSITable.ansi["hilite"], 
                                                  ANSITable.ansi["normal"])) + newl
            for player in con_players:
                s += str(' %s' % player.get_name(fullname=True)) + newl
            for thing in con_things:
                s += str(' %s' % thing.get_name(fullname=True)) + newl
                
        # Render Exists display.
        if con_exits:
            s += str("%sExits:%s" % (ANSITable.ansi["hilite"], 
                                        ANSITable.ansi["normal"])) + newl
            for exit in con_exits:
                s += str(' %s' % exit.get_name(fullname=True)) + newl
        
        # Render the object's home or destination (for exits).
        if not target_obj.is_room():
            if target_obj.is_exit():
                # The Home attribute on an exit is really its destination.
                s += str("Destination: %s" % target_obj.get_home()) + newl
            else:
                # For everything else, home is home.
                s += str("Home: %s" % target_obj.get_home()) + newl
            # This obviously isn't valid for rooms.    
            s += str("Location: %s" % target_obj.get_location()) + newl
        source_object.emit_to(s)
            
GLOBAL_CMD_TABLE.add_command("examine", cmd_examine)
    
def cmd_quit(command):
    """
    Gracefully disconnect the user as per his own request.
    """
    if command.session:
        session = command.session
        session.msg("Quitting!")
        session.handle_close()
GLOBAL_CMD_TABLE.add_command("quit", cmd_quit)
    
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
GLOBAL_CMD_TABLE.add_command("doing", cmd_who, 
                             extra_vals={"show_session_data": False})
GLOBAL_CMD_TABLE.add_command("who", cmd_who)

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
    source_object.emit_to("You say, '%s%s'" % (speech,
                                               ANSITable.ansi['normal']))
    
    # Build the string to emit to neighbors.
    emit_string = "%s says, '%s'" % (source_object.get_name(show_dbref=False), 
                                     speech)
    
    source_object.get_location().emit_to_contents(emit_string, 
                                                  exclude=source_object)
GLOBAL_CMD_TABLE.add_command("say", cmd_say)

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
GLOBAL_CMD_TABLE.add_command("pose", cmd_pose)


def cmd_help(command):
    """
    Help command
    Usage: help <topic>

    Examples: help index
              help topic              
              help 2
              
    Shows the available help on <topic>. Use without <topic> to
    get the help index. If more than one topic match your query, you will get a
    list of topics to choose between. You can also supply a help entry number
    directly if you know it.
                                
    <<TOPIC:STAFF:help_staff>>
    Help command extra functions for staff: 
    
    help index         - the normal index
    help index_staff   - show only help files unique to staff
    help index_player  - show only help files visible to all players

    The help command has a range of staff-only switches for manipulating the
    help data base:
    
     help/add <topic>:<text>    - add/replace help topic with text (staff only)
     help/append <topic>:<text> - add text to the end of a topic (staff only)
                                  (use the /newline switch to add a new paragraph
                                   to your help entry.)
     help/delete <topic>        - delete help topic (staff only)
     
    Note: further switches are /force and /staff. /force is used together with /add to
    always create a help entry, also when they partially match a previous entry. /staff
    makes the help file visible to staff only. The /append switch can be used to change the
    /staff setting of an existing help file if required.

    The <text> entry supports markup to automatically divide the help text into 
    sub-entries. These are started by the markup < <TOPIC:MyTopic> > (with no spaces
    between the << >>), which will create a new subsectioned entry 'MyTopic' for all
    text to follow it. All subsections to be added this way are automatically
    referred to in the footer of each help entry. Normally the subsections inherit the
    staff_only flag from the main entry (so if this is a staff-only help, all subentries
    will also be staff-only and vice versa). You can override this behaviour using the
    alternate forms < <TOPIC:STAFF:MyTopic> > and < <TOPIC:ALL:MyTopic> >. 
     
    """
    
    source_object = command.source_object
    topicstr = command.command_argument
    switches = command.command_switches
    
    if not command.command_argument:
        #display topic index if just help command is given
        if not switches:
            topicstr = "topic"
        else:
            #avoid applying things to "topic" by mistake
            source_object.emit_to("You have to supply a topic.")
            return
        
    elif len(topicstr) < 2 and not topicstr.isdigit():
        #check valid query
        source_object.emit_to("Your search query must be at least two letters long.")
        return

    #speciel help index names. These entries are dynamically
    #created upon request. 
    if topicstr == 'index':
        #the normal index, affected by permissions
        edit_help.get_help_index(source_object)
        return
    elif topicstr == 'index_staff':
        #allows staff to view only staff-specific help
        edit_help.get_help_index(source_object,filter='staff')
        return
    elif topicstr == 'index_player':
        #allows staff to view only the help files a player sees 
        edit_help.get_help_index(source_object,filter='player')
        return
    
    #handle special switches

    force_create = 'for' in switches or 'force' in switches
    staff_only = 'sta' in switches or 'staff' in switches

    if 'add' in switches:
        #try to add/replace help text for a command        
        if not source_object.is_staff():
            source_object.emit_to("Only staff can add new help entries.")
            return         
        spl = (topicstr.split(':',1))
        if len(spl) != 2:
            source_object.emit_to("Format is help/add <topic>:<helptext>")
            return        
        topicstr = spl[0]
        text = spl[1]
        topics = edit_help.add_help(topicstr,text,staff_only,force_create,source_object)
        if not topics:
            source_object.emit_to("No topic(s) added due to errors. Check syntax and that you don't have duplicate subtopics with the same name defined.")
            return 
        elif len(topics)>1:
            source_object.emit_to("Added or replaced multiple help entries.")
        else:
            source_object.emit_to("Added or replaced help entry for %s." % topicstr )

    elif 'append' in switches or 'app' in switches:
        #append text to a help entry
        if not source_object.is_staff():
            source_object.emit_to("Only staff can append to help entries.")
            return         
        spl = (topicstr.split(':',1))
        if len(spl) != 2:
            source_object.emit_to("""Format is help/append <topic>:<text to add>
                                     Use the /newline switch to make a new paragraph.""")
            return        
        topicstr = spl[0]
        text = spl[1]
        topics = HelpEntry.objects.find_topicmatch(source_object, topicstr)        
        if len(topics) == 1:
            newtext = topics[0].get_entrytext_ingame()
            if 'newl' in switches or 'newline' in switches:
                newtext += "\n\r\n\r%s" % text
            else:
                newtext += "\n\r%s" % text
            topics = edit_help.add_help(topicstr,newtext,staff_only,force_create,source_object)
            if topics:
                source_object.emit_to("Appended text to help entry for %s." % topicstr)
                           
    elif 'del' in switches or 'delete' in switches:
        #delete a help entry
        if not source_object.is_staff():
            source_object.emit_to("Only staff can add delete help entries.")
            return                
        topics = edit_help.del_help(source_object,topicstr)
        if type(topics) != type(list()):
            source_object.emit_to("Help entry '%s' deleted." % topicstr)
            return

    else:
        #no switch; just try to get the help as normal
        topics = HelpEntry.objects.find_topicmatch(source_object, topicstr)        
        
    #display help entry or handle no/multiple matches 

    if len(topics) == 0:
        source_object.emit_to("No matching topics found, please refine your search.")
        suggestions = HelpEntry.objects.find_topicsuggestions(source_object, 
                                                              topicstr)
        if len(suggestions) > 0:
            source_object.emit_to("Matching similarly named topics:")
            for result in suggestions:
                source_object.emit_to("  %s" % (result,))
            source_object.emit_to("You may type 'help <#>' to see any of these topics.")
    elif len(topics) > 1:
        source_object.emit_to("More than one match found:")
        for result in topics:
            source_object.emit_to("  %3d. %s" % (result.id, result.get_topicname()))
        source_object.emit_to("You may type 'help <#>' to see any of these topics.")
    else:    
        topic = topics[0]
        source_object.emit_to("\n\r "+ topic.get_entrytext_ingame())
GLOBAL_CMD_TABLE.add_command("help", cmd_help, auto_help=True)
