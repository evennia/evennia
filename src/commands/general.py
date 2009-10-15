"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.contrib.auth.models import User
from src.objects.models import Object
from src.config.models import ConfigValue
from src.helpsys.models import HelpEntry
from src.ansi import ANSITable
from src import session_mgr
from src.util import functions_general
from src.helpsys import helpsystem
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_password(command):
    """
    @password - set your password

    Usage:
      @paassword <old password> = <new password>

    Changes your password. Make sure to pick a safe one.
    """
    source_object = command.source_object
    
    if not command.command_argument:
        source_object.emit_to("Usage: @password <oldpass> = <newpass>")
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
GLOBAL_CMD_TABLE.add_command("@password", cmd_password, help_category="System")

def cmd_pemit(command):        
    """
    @pemit
    
    Emits something to a player.

    (Not yet implemented)
    """
    # TODO: Implement cmd_pemit
#GLOBAL_CMD_TABLE.add_command("@pemit", cmd_pemit)

def cmd_emit(command):        
    """
    @emit

    Usage:
      @emit[/switches] [<obj>, <obj>, ... =] <message>
      
    Switches:
      room : limit emits to rooms only 
      contents : send to the contents of objects
      
    Emits a message to the selected objects or to
    your immediate surroundings. If the object is a room,
    send to its contents. @pemit and @remit are
    restricted aliases to this main command. 
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches
    if not args:
        source_object.emit_to("Usage: @emit/switches [<obj>, <obj>, ... =] <message>")
        return 
    if '=' in args:
        args, message = [arg.strip() for arg in args.split('=',1)]
        targets = [arg.strip() for arg in args.split(',')]        
    else:
        targets = [source_object.get_location().dbref()]
        message = args.strip()
    # we now have a text to send and a list of target names.
    # perform a global search for actual objects
    tobjects = []
    for target in targets:
        if target in ['here']:
            results = [source_object.get_location()]
        elif target in ['me','my']:
            results = [source_object]
        else:
            results = Object.objects.global_object_name_search(target)
        if not results:
            source_object.emit_to("No matches found for '%s'." % target)
            return 
        if len(results) > 1:
            string = "There are multiple matches. Please use #dbref to be more specific."
            for result in results:
                string += "\n %s" % results.get_name(show_dbref=True)
            source_object.emit_to(string)
            return
        tobjects.append(results[0])
    if not tobjects:
        return
    
    # sort the objects into categories
    players = [obj for obj in tobjects if obj.is_player()]
    rooms = [obj for obj in tobjects if obj.is_room()]
    exits = [obj for obj in tobjects if obj.is_exit()]
    things = [obj for obj in tobjects if obj.is_thing()]

    # send differently depending on flags
    if "room" in switches or "rooms" in switches:
        # send to rooms only
        norooms = players + exits + things
        if norooms:            
            source_object.emit_to("These are not rooms: %s" %
                                  ", ".join([r.get_name() for r in norooms]))
            return
        for room in rooms:
            room.emit_to_contents(message, exclude=source_object)
    elif "contents" in switches:
        # send to contents of objects
        allobj = players + rooms + exits + things
        for obj in allobj:
            if not source_object.controls_other(obj):
                source_object.emit_to("Cannot emit to %s (you don's control it)" % obj.get_name())
                continue
            obj.emit_to_contents(message)
    else:
        # assume reasonable defaults depending on object type
        for obj in players:
            obj.emit_to(message)
        for obj in rooms:
            obj.emit_to_contents(message)
        for obj in exits: #send to destination
            obj.get_home().emit_to_contents(message)
        for obj in things:
            if not source_object.controls_other(obj):
                source_object.emit_to("Cannot emit to %s (you don's control it)" % obj.get_name())
                continue
            obj. emit_to_contents(message)
    allobj = players + rooms + exits + things
    string = ", ".join([obj.get_name() for obj in allobj])
    source_object.emit_to("Emitted message to: %s." % string)
GLOBAL_CMD_TABLE.add_command("@emit", cmd_emit,
                             priv_tuple=("genperms.announce",),help_category="Comms")

def cmd_remit(command):
    """
    @remit - emit to a room

    Usage:
      @remit <room> [<room2>,<room3>,...] = <message>

    Emits message to the contents of the room. 
    """
    if not command.command_argument:
        command.source_object.emit_to("Usage: @remit <room>[,<room2>,<room3>,...] = <message>")
        return 
    command.command_switches = ["room"]
    cmd_emit(command)
GLOBAL_CMD_TABLE.add_command("@remit", cmd_remit,
                             priv_tuple=("genperms.announce",),help_category="Comms")

def cmd_pemit(command):
    """
    @pemit - emit to an object or player

    Usage:
      @pemit[/switch] <obj> [,<obj2>, <obj3>, ...] = <message>

    Switches:
      contents : emit to the contents of each object (only if you own it)

    Emits message to objects or the contents of objects.
    """
    if not command.command_argument:
        command.source_object.emit_to("Usage: @pemit <obj>[,<obj2>,<obj3>,...] = <message>")
        return 
    command.command_switches = [switch for switch in command.command_switches
                                if switch == 'contents']
    cmd_emit(command)
GLOBAL_CMD_TABLE.add_command("@pemit", cmd_pemit,
                             priv_tuple=("genperms.announce",),help_category="Comms")


def cmd_wall(command):
    """
    @wall

    Usage:
      @wall <message>
      
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
                             priv_tuple=("genperms.announce",),help_category="Comms")

def cmd_idle(command):
    """
    idle

    Usage:
      idle 

    Returns and does nothing. You can use this to send idle
    messages to the game, in order to avoid getting timed out.
    """
    pass
GLOBAL_CMD_TABLE.add_command("idle", cmd_idle, help_category="System")
    
def cmd_inventory(command):
    """
    inventory

    Usage:
      inventory
      inv
      
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
    look

    Usage:
      look
      look <obj> 

    Observers your location or objects in your vicinity. 
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
    get

    Usage:
      get <obj>
      
    Picks up an object from your location and puts it in
    your inventory.
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

    if not target_obj.scriptlink.default_lock(source_object):
        lock_msg = target_obj.get_attribute_value("lock_msg")
        if lock_msg:
            source_object.emit_to(lock_msg)
        else:
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
    drop

    Usage:
      drop <obj>
      
    Has you drop an object from your inventory into the 
    location you are currently in.
    """
    source_object = command.source_object
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

    # SCRIPT: Call the object script's a_drop() method.
    target_obj.scriptlink.at_drop(source_object)
GLOBAL_CMD_TABLE.add_command("drop", cmd_drop),
                
def cmd_quit(command):
    """
    quit

    Usage:
      quit 

    Gracefully disconnect from the game.
    """
    if command.session:
        session = command.session
        session.msg("Quitting. Hope to see you soon again.")
        session.handle_close()
GLOBAL_CMD_TABLE.add_command("quit", cmd_quit, help_category="System")
    
def cmd_who(command):
    """
    who

    Usage:
      who 

    Shows who is currently online. 
    """
    session_list = session_mgr.get_session_list()
    source_object = command.source_object
    
    # In the case of the DOING command, don't show session data regardless.
    if command.extra_vars and \
           command.extra_vars.get("show_session_data", None) == False:
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
                             extra_vals={"show_session_data": False}, help_category="System")
GLOBAL_CMD_TABLE.add_command("who", cmd_who,help_category="System")

def cmd_say(command):
    """
    say

    Usage:
      say <message>
      
    Talk to those in your current location. 
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

def cmd_fsay(command):
    """
    @fsay - make an object say something

    Usage:
      @fsay <obj> = <text to say>
      
    Make an object talk to its current location.
    """
    source_object = command.source_object
    args = command.command_argument

    if not args or not "=" in args: 
        source_object.emit_to("Usage: @fsay <obj> = <text to say>")
        return
    target, speech = [arg.strip() for arg in args.split("=",1)]

    # find object
    if target in ['here']:
        results = [source_object.get_location()]
    elif target in ['me','my']:
        results = [source_object]
    else:
        results = Object.objects.global_object_name_search(target)
    if not results:
        source_object.emit_to("No matches found for '%s'." % target)
        return 
    if len(results) > 1:
        string = "There are multiple matches. Please use #dbref to be more specific."
        for result in results:
            string += "\n %s" % results.get_name(show_dbref=True)
        source_object.emit_to(string)
        return
    target = results[0]

    # permission check
    if not source_object.controls_other(target):
        source_object.emit_to("Cannot pose %s (you don's control it)" % obj.get_name())
        return
        
    # Feedback for the object doing the talking.
    source_object.emit_to("%s says, '%s%s'" % (target.get_name(show_dbref=False),
                                               speech,
                                               ANSITable.ansi['normal']))
    
    # Build the string to emit to neighbors.
    emit_string = "%s says, '%s'" % (target.get_name(show_dbref=False), 
                                     speech)    
    target.get_location().emit_to_contents(emit_string, 
                                                  exclude=source_object)
GLOBAL_CMD_TABLE.add_command("@fsay", cmd_fsay)


def cmd_pose(command):
    """
    pose - strike a pose

    Usage:
      pose[/switches] <pose text>

    Switches:
      /nospace : put no space between your name
                 and the start of the pose.

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
     Tom is standing by the wall, smiling.    

    Describe an action being taken. The pose text will
    automatically begin with your name. 
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

def cmd_fpose(command):
    """
    @fpose - force an object to pose

    Usage:
      @fpose[/switches] <obj> = <pose text>
      
    Switches:
      nospace : put no text between the object's name
                and the start of the pose.

    Describe an action being taken as performed by obj.
    The pose text will automatically begin with the name
    of the object. 
    """
    source_object = command.source_object
    args = command.command_argument

    if not args or not "=" in args: 
        source_object.emit_to("Usage: @fpose <obj> = <pose text>")
        return
    target, pose_string = [arg.strip() for arg in args.split("=",1)]
    # find object
    if target in ['here']:
        results = [source_object.get_location()]
    elif target in ['me','my']:
        results = [source_object]
    else:
        results = Object.objects.global_object_name_search(target)
    if not results:
        source_object.emit_to("No matches found for '%s'." % target)
        return 
    if len(results) > 1:
        string = "There are multiple matches. Please use #dbref to be more specific."
        for result in results:
            string += "\n %s" % results.get_name(show_dbref=True)
        source_object.emit_to(string)
        return
    target = results[0]

    # permission check
    if not source_object.controls_other(target):
        source_object.emit_to("Cannot pose %s (you don's control it)" % obj.get_name())
        return
    
    if "nospace" in command.command_switches:
        # Output without a space between the player name and the emote.
        sent_msg = "%s%s" % (target.get_name(show_dbref=False), 
                             pose_string)
    else:
        # No switches, default.
        sent_msg = "%s %s" % (target.get_name(show_dbref=False), 
                              pose_string)
    
    source_object.get_location().emit_to_contents(sent_msg)
GLOBAL_CMD_TABLE.add_command("@fpose", cmd_fpose)





def cmd_group(command):
    """
    @group - show your groups

    Usage:
      @group

    This command shows you which user permission groups
    you are a member of, if any. 
    """
    source_object = command.source_object    
    user = User.objects.get(username=source_object.get_name(show_dbref=False, no_ansi=True))    
    string = ""
    if source_object.is_superuser():
        string += "\n  This is a SUPERUSER account! Group membership does not matter."
    if not user.is_active:
        string += "\n  ACCOUNT NOT ACTIVE."
    for group in user.groups.all():
        string += "\n -- %s" % group 
        for perm in group.permissions.all():
            string += "\n   --- %s" % perm.name        
    if not string:
        string = "You are not a member of any groups." % source_object.get_name(show_dbref=False)
    else: 
        string = "\nYour (%s's) group memberships: %s" % (source_object.get_name(show_dbref=False), string)     
    source_object.emit_to(string)
GLOBAL_CMD_TABLE.add_command("@group", cmd_group)    
GLOBAL_CMD_TABLE.add_command("@groups", cmd_group, help_category="System")    

def cmd_help(command):
    """
    help - view help database

    Usage:
      help <topic>

    Examples: help index
              help topic              
              help 345
              
    Shows the available help on <topic>. Use without <topic> to get the help
    index. If more than one topic match your query, you will get a
    list of topics to choose between. You can also supply a help entry number
    directly if you know it.
    """
                                   
    source_object = command.source_object
    topicstr = command.command_argument    
    
    if not command.command_argument:
        #display topic index if just help command is given
        topicstr = "index"        

    if len(topicstr) < 2 and not topicstr.isdigit():
        #check valid query
        source_object.emit_to("Your search query must be at least two letters long.")
        return

    # speciel help index names. These entries are dynamically
    # created upon request. 
    if topicstr in ['topic','topics']:
        # the full index, affected by permissions        
        text = helpsystem.viewhelp.index_full(source_object)
        text = " \nHELP TOPICS (By Category):\n\r%s" % text
        source_object.emit_to(text)
        return

    elif 'index' in topicstr:
        # view the category index
        text = helpsystem.viewhelp.index_categories()
        text = " \nHELP CATEGORIES (try 'help <category>' or 'help topics'):\n\r\n\r%s" % text
        source_object.emit_to(text)
        return

    # not a special help index entry. Do a search for the help entry.
    topics = HelpEntry.objects.find_topicmatch(source_object, topicstr)

    # display help entry or handle no/multiple matches 

    string = ""
    if not topics:
        # no matches.

        # try to see if it is matching the name of a category. If so,
        # show the topics for this category.
        text = helpsystem.viewhelp.index_category(source_object, topicstr)
        if text:
            # We have category matches, display the index and exit.            
            string = "\n%s%s%s\n\r\n\r%s" % ("---", " Help topics in category %s: " % \
                                       topicstr.capitalize(), "-"* (30-len(topicstr)), text)
            source_object.emit_to(string)
            return 

        # at this point we just give a not-found error and give suggestions.
        topics = HelpEntry.objects.find_topicsuggestions(source_object, 
                                                         topicstr)         
        if topics: 
            if len(topics) > 3:
                topics = topics[:3]
            string += "\n\rMatching similarly named topics (use name or number to refine search):"
            for entry in topics: 
                string += "\n  %i.%s" % (entry.id, entry.topicname)
        else:
            string += "No matching topics found, please refine your search."        

            
    elif len(topics) > 1:
        # multiple matches found
        string += "More than one match found:"        
        for result in topics:
            string += "  %3d. %s" % (result.id, result.get_topicname())

    else:    
        # a single match found
        topic = topics[0]
        header = "--- Help entry for '%s' (%s category) " % (topic.get_topicname(),
                                                 topic.get_category())
        header = "%s%s" % (header, "-" * (80-len(header)))
        string += "\n\r%s\n\r\n\r%s" % (header, topic.get_entrytext_ingame())

        # add the 'See also:' footer
        topics = HelpEntry.objects.find_topicsuggestions(source_object, 
                                                         topicstr)         
        if topics: 
            if len(topics) > 5:
                topics = topics[:5]
            topics = [str(topic.topicname) for topic in topics ]
            string +=  "\n\r\n\r" + " " * helpsystem.viewhelp.indent + \
                      "See also: " + ", ".join(topics)        

    source_object.emit_to(string)
GLOBAL_CMD_TABLE.add_command("help", cmd_help)
