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
    session = command.session
    pobject = session.get_pobject()
    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) != 2:
        session.msg("Incorrect number of arguments.")
        return
    
    oldpass = eq_args[0]
    newpass = eq_args[1]
    
    if len(oldpass) == 0:    
        session.msg("You must provide your old password.")
    elif len(newpass) == 0:
        session.msg("You must provide your new password.")
    else:
        uaccount = pobject.get_user_account()
        
        if not uaccount.check_password(oldpass):
            session.msg("The specified old password isn't correct.")
        elif len(newpass) < 3:
            session.msg("Passwords must be at least three characters long.")
            return
        else:
            uaccount.set_password(newpass)
            uaccount.save()
            session.msg("Password changed.")

def cmd_pemit(command):        
    """
    Emits something to a player.
    """
    # TODO: Implement cmd_pemit

def cmd_emit(command):        
    """
    Emits something to your location.
    """
    session = command.session
    pobject = session.get_pobject()
    message = command.command_argument
    
    if message:
        pobject.get_location().emit_to_contents(message)
    else:
        session.msg("Emit what?")

def cmd_wall(command):
    """
    Announces a message to all connected players.
    """
    session = command.session
    wallstring = command.command_argument
    pobject = session.get_pobject()
        
    if not wallstring:
        session.msg("Announce what?")
        return
        
    message = "%s shouts \"%s\"" % (session.get_pobject().get_name(show_dbref=False), wallstring)
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
    session = command.session
    pobject = session.get_pobject()
    session.msg("You are carrying:")
    
    for item in pobject.get_contents():
        session.msg(" %s" % (item.get_name(),))
        
    money = int(pobject.get_attribute_value("MONEY", default=0))
    if money == 1:
        money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_SINGULAR")
    else:
        money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_PLURAL")

    session.msg("You have %d %s." % (money,money_name))

def cmd_look(command):
    """
    Handle looking at objects.
    """
    session = command.session
    pobject = session.get_pobject()
    
    # If an argument is provided with the command, search for the object.
    # else look at the current room. 
    if command.command_argument:    
        target_obj = Object.objects.standard_plr_objsearch(session, 
                                                    command.command_argument)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return
    else:
        target_obj = pobject.get_location()
    
    # SCRIPT: Get the item's appearance from the scriptlink.
    session.msg(target_obj.scriptlink.return_appearance({
        "target_obj": target_obj,
        "pobject": pobject
    }))
            
    # SCRIPT: Call the object's script's a_desc() method.
    target_obj.scriptlink.a_desc({
        "target_obj": pobject
    })
            
def cmd_get(command):
    """
    Get an object and put it in a player's inventory.
    """
    session = command.session
    pobject = session.get_pobject()
    plr_is_staff = pobject.is_staff()

    if not command.command_argument:    
        session.msg("Get what?")
        return
    else:
        target_obj = Object.objects.standard_plr_objsearch(session, 
                                                command.command_argument, 
                                                search_contents=False)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

    if pobject == target_obj:
        session.msg("You can't get yourself.")
        return
    
    if not plr_is_staff and (target_obj.is_player() or target_obj.is_exit()):
        session.msg("You can't get that.")
        return
        
    if target_obj.is_room() or target_obj.is_garbage() or target_obj.is_going():
        session.msg("You can't get that.")
        return
        
    target_obj.move_to(pobject, quiet=True)
    session.msg("You pick up %s." % (target_obj.get_name(),))
    pobject.get_location().emit_to_contents("%s picks up %s." % 
                                    (pobject.get_name(), 
                                     target_obj.get_name()), 
                                     exclude=pobject)
    
    # SCRIPT: Call the object's script's a_get() method.
    target_obj.scriptlink.a_get({
        "pobject": pobject
    })
            
def cmd_drop(command):
    """
    Drop an object from a player's inventory into their current location.
    """
    session = command.session
    pobject = session.get_pobject()
    plr_is_staff = pobject.is_staff()

    if not command.command_argument:    
        session.msg("Drop what?")
        return
    else:
        target_obj = Object.objects.standard_plr_objsearch(session, 
                                                command.command_argument, 
                                                search_location=False)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return

    if not pobject == target_obj.get_location():
        session.msg("You don't appear to be carrying that.")
        return
        
    target_obj.move_to(pobject.get_location(), quiet=True)
    session.msg("You drop %s." % (target_obj.get_name(),))
    pobject.get_location().emit_to_contents("%s drops %s." % 
                                            (pobject.get_name(), 
                                             target_obj.get_name()), 
                                             exclude=pobject)

    # SCRIPT: Call the object's script's a_drop() method.
    target_obj.scriptlink.a_drop({
        "pobject": pobject
    })
            
def cmd_examine(command):
    """
    Detailed object examine command
    """
    session = command.session
    pobject = session.get_pobject()
    attr_search = False
    
    if not command.command_argument:    
        # If no arguments are provided, examine the invoker's location.
        target_obj = pobject.get_location()
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
                session.msg('No attribute name provided.')
                return
        else:
            # No slash in argument, just examine an object.
            obj_searchstr = command.command_argument

        # Resolve the target object.
        target_obj = Object.objects.standard_plr_objsearch(session, 
                                                           obj_searchstr)
        # Use standard_plr_objsearch to handle duplicate/nonexistant results.
        if not target_obj:
            return
            
    if attr_search:
        """
        Player did something like: examine me/* or examine me/TE*. Return
        each matching attribute with its value.
        """
        attr_matches = target_obj.attribute_namesearch(attr_searchstr)
        if attr_matches:
            for attribute in attr_matches:
                session.msg(attribute.get_attrline())
        else:
            session.msg("No matching attributes found.")
    else:
        """
        Player is examining an object. Return a full readout of attributes,
        along with detailed information about said object.
        """
        # Format the examine header area with general flag/type info.
        session.msg("%s\r\n%s" % (
            target_obj.get_name(fullname=True),
            target_obj.get_description(no_parsing=True),
        ))
        session.msg("Type: %s Flags: %s" % (target_obj.get_type(), 
                                            target_obj.get_flags()))
        session.msg("Owner: %s " % (target_obj.get_owner(),))
        session.msg("Zone: %s" % (target_obj.get_zone(),))
        
        for attribute in target_obj.get_all_attributes():
            session.msg(attribute.get_attrline())
        
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
            session.msg("%sContents:%s" % (ansi.ansi["hilite"], 
                                           ansi.ansi["normal"],))
            for player in con_players:
                session.msg('%s' % (player.get_name(fullname=True),))
            for thing in con_things:
                session.msg('%s' % (thing.get_name(fullname=True),))
                
        # Render Exists display.
        if con_exits:
            session.msg("%sExits:%s" % (ansi.ansi["hilite"], 
                                        ansi.ansi["normal"],))
            for exit in con_exits:
                session.msg('%s' %(exit.get_name(fullname=True),))
        
        # Render the object's home or destination (for exits).
        if not target_obj.is_room():
            if target_obj.is_exit():
                # The Home attribute on an exit is really its destination.
                session.msg("Destination: %s" % (target_obj.get_home(),))
            else:
                # For everything else, home is home.
                session.msg("Home: %s" % (target_obj.get_home(),))
            # This obviously isn't valid for rooms.    
            session.msg("Location: %s" % (target_obj.get_location(),))
    
def cmd_quit(command):
    """
    Gracefully disconnect the user as per his own request.
    """
    session = command.session
    session.msg("Quitting!")
    session.handle_close()
    
def cmd_who(command):
    """
    Generic WHO command.
    """
    session_list = session_mgr.get_session_list()
    session = command.session
    pobject = session.get_pobject()
    show_session_data = pobject.user_has_perm("genperms.see_session_data")

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
            retval += '%-16s%9s %4s%-3s#%-6d%5d%3s%-25s\r\n' % \
                (plr_pobject.get_name(show_dbref=False)[:25].ljust(27), \
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
            retval += '%-16s%9s %4s%-3s\r\n' % \
                (plr_pobject.get_name(show_dbref=False)[:25].ljust(27), \
                # On-time
                functions_general.time_format(delta_conn,0), \
                # Idle time
                functions_general.time_format(delta_cmd,1), \
                # Flags
                '')
    retval += '%d Players logged in.' % (len(session_list),)
    
    session.msg(retval)

def cmd_say(command):
    """
    Room-based speech command.
    """
    session = command.session

    if not command.command_argument:
        session.msg("Say what?")
        return
    
    session_list = session_mgr.get_session_list()
    pobject = session.get_pobject()
    speech = command.command_argument
    
    players_present = [player for player in session_list if player.get_pobject().get_location() == session.get_pobject().get_location() and player != session]
    
    retval = "You say, '%s'" % (speech,)
    for player in players_present:
        player.msg("%s says, '%s'" % (pobject.get_name(show_dbref=False), speech,))
    
    session.msg(retval)

def cmd_pose(command):
    """
    Pose/emote command.
    """
    session = command.session
    pobject = session.get_pobject()

    if not command.command_argument: 
        session.msg("Do what?")
        return
    
    session_list = session_mgr.get_session_list()
    speech = command.command_argument
    
    if "nospace" in command.command_switches:
        # Output without a space between the player name and the emote.
        sent_msg = "%s%s" % (pobject.get_name(show_dbref=False), speech)
    else:
        # No switches, default.
        sent_msg = "%s %s" % (pobject.get_name(show_dbref=False), speech)
    
    players_present = [player for player in session_list if player.get_pobject().get_location() == session.get_pobject().get_location()]
    
    for player in players_present:
        player.msg(sent_msg)
    
def cmd_help(command):
    """
    Help system commands.
    """
    session = command.session
    pobject = session.get_pobject()
    topicstr = command.command_argument
    
    if not command.command_argument:
        topicstr = "Help Index"    
    elif len(topicstr) < 2 and not topicstr.isdigit():
        session.msg("Your search query is too short. It must be at least three letters long.")
        return
        
    topics = HelpEntry.objects.find_topicmatch(pobject, topicstr)        
        
    if len(topics) == 0:
        session.msg("No matching topics found, please refine your search.")
        suggestions = HelpEntry.objects.find_topicsuggestions(pobject, topicstr)
        if len(suggestions) > 0:
            session.msg("Matching similarly named topics:")
            for result in suggestions:
                session.msg(" %s" % (result,))
                session.msg("You may type 'help <#>' to see any of these topics.")
    elif len(topics) > 1:
        session.msg("More than one match found:")
        for result in topics:
            session.msg("%3d. %s" % (result.id, result.get_topicname()))
        session.msg("You may type 'help <#>' to see any of these topics.")
    else:    
        topic = topics[0]
        session.msg("\r\n%s%s%s" % (ansi.ansi["hilite"], topic.get_topicname(), ansi.ansi["normal"]))
        session.msg(topic.get_entrytext_ingame())
