"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.conf import settings
from src.server import sessionhandler
from src.permissions.models import PermissionGroup
from src.permissions.permissions import has_perm, has_perm_string
from src.objects.models import HANDLE_SEARCH_ERRORS
from src.utils import utils

from game.gamesrc.commands.default.muxcommand import MuxCommand

class CmdHome(MuxCommand):
    """
    home

    Usage:
      home 

    Teleports the player to their home.
    """
    
    key = "home"
    permissions = "cmd:home"

    def func(self):
        "Implement the command"
        caller = self.caller        
        home = caller.home
        if not home:
            caller.msg("You have no home set.")
        else:
            caller.move_to(home)
            caller.msg("There's no place like home ...")

class CmdLook(MuxCommand):
    """
    look

    Usage:
      look
      look <obj> 

    Observes your location or objects in your vicinity. 
    """
    key = "look"
    aliases = ["l"]

    def func(self):
        """
        Handle the looking. 
        """
        caller = self.caller
        args = self.args        # caller.msg(inp)

        if args:
            # Use search to handle duplicate/nonexistant results.
            looking_at_obj = caller.search(args)
            if not looking_at_obj:
                return
        else:
            looking_at_obj = caller.location
            if not looking_at_obj:
                caller.msg("Location: None")
                return
        # get object's appearance
        caller.msg(looking_at_obj.return_appearance(caller))
        # the object's at_desc() method.
        looking_at_obj.at_desc(looker=caller)

class CmdPassword(MuxCommand):
    """
    @password - set your password

    Usage:
      @password <old password> = <new password>

    Changes your password. Make sure to pick a safe one.
    """    
    key = "@password"    

    def func(self):
        "hook function."

        caller = self.caller 

        if not self.rhs:
            caller.msg("Usage: @password <oldpass> = <newpass>")
            return
        oldpass = self.lhslist[0] # this is already stripped by parse()
        newpass = self.rhslist[0] #               ''
        try:
            uaccount = caller.player.user
        except AttributeError:
            caller.msg("This is only applicable for players.")
            return
        if not uaccount.check_password(oldpass):
            caller.msg("The specified old password isn't correct.")
        elif len(newpass) < 3:
            caller.msg("Passwords must be at least three characters long.")
        else:
            uaccount.set_password(newpass)
            uaccount.save()
            caller.msg("Password changed.")

class CmdNick(MuxCommand):
    """
    Define a personal alias/nick

    Usage:
      alias[/switches] <alias> = [<string>]
      nick             ''

    Switches:      obj      - alias an object
      player   - alias a player 
      clearall - clear all your aliases
      list     - show all defined aliases 
      
    If no switch is given, a command/channel alias is created, used
    to replace strings before sending the command. 
      
    Creates a personal nick for some in-game object or
    string. When you enter that string, it will be replaced
    with the alternate string. The switches dictate in what
    situations the nick is checked and substituted. If string
    is None, the alias (if it exists) will be cleared.
    Obs - no objects are actually changed with this command,
    if you want to change the inherent aliases of an object,
    use the @alias command instead. 
    """
    key = "nickname"
    aliases = ["nick, @nick, alias"]
    
    def func(self):
        "Create the nickname"
        
        caller = self.caller
        switches = self.switches

        if 'list' in switches:
            string = "{wAliases:{n \n"
            string = string + "\n\r".join(["%s = %s" % (alias, replace)
                                           for alias, replace
                                           in caller.nicks.items()])
            caller.msg(string)
            return
        if 'clearall' in switches:
            del caller.nicks
            caller.msg("Cleared all aliases.")
            return 
        
        if not self.args or not self.lhs:
            caller.msg("Usage: alias[/switches] string = [alias]")
            return                        

        alias = self.lhs
        rstring = self.rhs 
        err = None 
        if rstring == alias:
            err = "No point in setting alias same as the string to replace..."            
            caller.msg(err)
            return 
        elif 'obj' in switches:
            # object alias, for adressing objects
            # (including user-controlled ones)  
            err = caller.set_nick("_obj:%s" % alias, rstring)
            atype = "Object"
        elif 'player' in switches:
            # player alias, used for messaging
            err = caller.set_nick("_player:%s" % alias, rstring)            
            atype = "Player "
        else:
            # a command/channel alias - these are replaced if
            # they begin a command string.            
            caller.msg(rstring)
            caller.msg("going in: %s %s" % (alias, rstring))
            err = caller.set_nick(alias, rstring)
            atype = "Command/channel "
        if err:
            if rstring:                
                err = "%salias %s changed from '%s' to '%s'." % (atype, alias, err, rstring)
            else:
                err = "Cleared %salias '%s'(='%s')." % (atype, alias, err)
        else:
            err = "Set %salias '%s' = '%s'" % (atype, alias, rstring)
        caller.msg(err.capitalize())


class CmdInventory(MuxCommand):
    """
    inventory

    Usage:
      inventory
      inv
      
    Shows a player's inventory.
    """    
    key = "inventory"
    aliases = ["inv", "i"]

    def func(self):
        "hook function"
        string = "You are carrying:"
        for item in self.caller.contents:
            string += "\n %s" % item.name
        self.caller.msg(string)

    ## money = int(caller.MONEY)
    ## if money == 1:
    ##     money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_SINGULAR")
    ## else:
    ##     money_name = ConfigValue.objects.get_configvalue("MONEY_NAME_PLURAL")
    ##caller.msg("You have %d %s." % (money, money_name))


class CmdGet(MuxCommand):            
    """
    get

    Usage:
      get <obj>
      
    Picks up an object from your location and puts it in
    your inventory.
    """
    key = "get"
    aliases = "grab"
    
    def func(self):
        "implements the command."

        caller = self.caller

        if not self.args:
            caller.msg("Get what?")
            return
        obj = caller.search(self.args)
        if not obj:
            return
        if caller == obj:
            caller.msg("You can't get yourself.")
            return
        if obj.player or obj.db._destination: 
            # don't allow picking up player objects, nor exits.
            caller.msg("You can't get that.")
            return
        if not has_perm(caller, obj, 'get'):
            if obj.db.get_err_msg:
                caller.msg(obj.db.get_err_msg)
            else:
                caller.msg("You can't get that.")
            return

        obj.move_to(caller, quiet=True)
        caller.msg("You pick up %s." % obj.name)
        caller.location.msg_contents("%s picks up %s." % 
                                        (caller.name, 
                                         obj.name), 
                                         exclude=caller)
        # calling hook method
        obj.at_get(caller)
        

class CmdDrop(MuxCommand):
    """
    drop

    Usage:
      drop <obj>
      
    Lets you drop an object from your inventory into the 
    location you are currently in.
    """
    
    key = "drop"
    
    def func(self):
        "Implement command"

        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        results = caller.search(self.args, ignore_errors=True)
        # we process the results ourselves since we want to sift out only 
        # those in our inventory. 
        results = [obj for obj in results if obj in caller.contents]
        # now we send it into the handler.
        obj = HANDLE_SEARCH_ERRORS(caller, self.args, results, False)
        if not obj:
            return 
        
        obj.move_to(caller.location, quiet=True)
        caller.msg("You drop %s." % (obj.name,))
        caller.location.msg_contents("%s drops %s." % 
                                         (caller.name, obj.name),
                                         exclude=caller)
        # Call the object script's at_drop() method.
        obj.at_drop(caller)


class CmdQuit(MuxCommand):
    """
    quit

    Usage:
      @quit 

    Gracefully disconnect from the game.
    """
    key = "@quit"
    
    def func(self):
        "hook function"  
        sessions = self.caller.sessions
        for session in sessions:
            session.msg("Quitting. Hope to see you soon again.")
            session.handle_close()

class CmdWho(MuxCommand):
    """
    who

    Usage:
      who 
      doing 

    Shows who is currently online. Doing is an 
    alias that limits info also for those with 
    all permissions.
    """

    key = "who"
    aliases = "doing" 

    def func(self):
        """
        Get all connected players by polling session.
        """

        caller = self.caller
        session_list = sessionhandler.get_sessions()

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = has_perm_string(caller, "Immortals,Wizards")

        if show_session_data:
            retval = "Player Name                        On For Idle   Room    Cmds   Host\n\r"
        else:
            retval = "Player Name                        On For Idle\n\r"

        for session in session_list:
            if not session.logged_in:
                continue
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            plr_pobject = session.get_character()

            if show_session_data:
                retval += '%-31s%9s %4s%-3s#%-6d%5d%3s%-25s\r\n' % \
                    (plr_pobject.name[:25], \
                    # On-time
                    utils.time_format(delta_conn,0), \
                    # Idle time
                    utils.time_format(delta_cmd,1), \
                    # Flags
                    '', \
                    # Location
                    plr_pobject.location.id, \
                    session.cmd_total, \
                    # More flags?
                    '', \
                    session.address[0])
            else:
                retval += '%-31s%9s %4s%-3s\r\n' % \
                    (plr_pobject.name[:25], \
                    # On-time
                    utils.time_format(delta_conn,0), \
                    # Idle time
                    utils.time_format(delta_cmd,1), \
                    # Flags
                    '')
        retval += '%d Players logged in.' % (len(session_list),)

        caller.msg(retval)

class CmdSay(MuxCommand):
    """
    say

    Usage:
      say <message>
      
    Talk to those in your current location. 
    """
    
    key = "say"
    aliases = ['"']
    
    def func(self):
        "Run the say command"

        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args

        # calling the speech hook on the location
        speech = caller.location.at_say(caller, speech)

        # Feedback for the object doing the talking.
        caller.msg('You say, "%s{n"' % speech)
        
        # Build the string to emit to neighbors.
        emit_string = '{c%s{n says, "%s{n"' % (caller.name, 
                                               speech)
        caller.location.msg_contents(emit_string, 
                                         exclude=caller)

## def cmd_fsay(command):
##     """
##     @fsay - make an object say something

##     Usage:
##       @fsay <obj> = <text to say>
      
##     Make an object talk to its current location.
##     """
##     caller = command.caller
##     args = command.command_argument

##     if not args or not "=" in args: 
##         caller.msg("Usage: @fsay <obj> = <text to say>")
##         return
##     target, speech = [arg.strip() for arg in args.split("=",1)]

##     # find object
##     if target in ['here']:
##         results = [caller.location]
##     elif target in ['me','my']:
##         results = [caller]
##     else:
##         results = Object.objects.global_object_name_search(target)
##     if not results:
##         caller.msg("No matches found for '%s'." % target)
##         return 
##     if len(results) > 1:
##         string = "There are multiple matches. Please use #dbref to be more specific."
##         for result in results:
##             string += "\n %s" % results.name
##         caller.msg(string)
##         return
##     target = results[0]

##     # permission check
##     if not caller.controls_other(target):
##         caller.msg("Cannot pose %s (you don's control it)" % target.name)
##         return
        
##     # Feedback for the object doing the talking.
##     caller.msg("%s says, '%s%s'" % (target.name,
##                                                speech,
##                                                ANSITable.ansi['normal']))
    
##     # Build the string to emit to neighbors.
##     emit_string = "%s says, '%s'" % (target.name, 
##                                      speech)    
##     target.location.msg_contents(emit_string, 
##                                                   exclude=caller)
## GLOBAL_CMD_TABLE.add_command("@fsay", cmd_fsay)

class CmdPose(MuxCommand):
    """
    pose - strike a pose

    Usage:
      pose <pose text>
      pose's <pose text>

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
     Tom is standing by the wall, smiling.    

    Describe an script being taken. The pose text will
    automatically begin with your name. 
    """
    key = "pose"
    aliases = [":", "emote"]    

    def parse(self):
        """
        Custom parse the cases where the emote
        starts with some special letter, such
        as 's, at which we don't want to separate
        the caller's name and the emote with a 
        space.
        """
        args = self.args
        if args and not args[0] in ["'", ",", ":"]:
            args = " %s" % args
        self.args = args

    def func(self):
        "Hook function"        
        if not self.args:
            msg = "Do what?"
        else:
            msg = "%s%s" % (self.caller.name, self.args)
        self.caller.location.msg_contents(msg)
        
## def cmd_fpose(command):
##     """
##     @fpose - force an object to pose

##     Usage:
##       @fpose[/switches] <obj> = <pose text>
      
##     Switches:
##       nospace : put no text between the object's name
##                 and the start of the pose.

##     Describe an action being taken as performed by obj.
##     The pose text will automatically begin with the name
##     of the object. 
##     """
##     caller = command.caller
##     args = command.command_argument

##     if not args or not "=" in args: 
##         caller.msg("Usage: @fpose <obj> = <pose text>")
##         return
##     target, pose_string = [arg.strip() for arg in args.split("=",1)]
##     # find object
##     if target in ['here']:
##         results = [caller.location]
##     elif target in ['me','my']:
##         results = [caller]
##     else:
##         results = Object.objects.global_object_name_search(target)
##     if not results:
##         caller.msg("No matches found for '%s'." % target)
##         return 
##     if len(results) > 1:
##         string = "There are multiple matches. Please use #dbref to be more specific."
##         for result in results:
##             string += "\n %s" % results.name
##         caller.msg(string)
##         return
##     target = results[0]

##     # permission check
##     if not caller.controls_other(target):
##         caller.msg("Cannot pose %s (you don's control it)" % target.name)
##         return
    
##     if "nospace" in command.command_switches:
##         # Output without a space between the player name and the emote.
##         sent_msg = "%s%s" % (target.name, 
##                              pose_string)
##     else:
##         # No switches, default.
##         sent_msg = "%s %s" % (target.name, 
##                               pose_string)
    
##     caller.location.msg_contents(sent_msg)
## GLOBAL_CMD_TABLE.add_command("@fpose", cmd_fpose)


class CmdEncoding(MuxCommand):
    """
    encoding - set a custom text encoding

    Usage: 
      @encoding/switches [<encoding>]

    Switches:
      clear - clear your custom encoding

           
    This sets the text encoding for communicating with Evennia. This is mostly an issue only if 
    you want to use non-ASCII characters (i.e. letters/symbols not found in English). If you see
    that your characters look strange (or you get encoding errors), you should use this command
    to set the server encoding to be the same used in your client program. 
    
    Common encodings are utf-8 (default), latin-1, ISO-8859-1 etc.
    
    If you don't submit an encoding, the current encoding will be displayed instead. 
    """

    key = "@encoding"
    aliases = "@encode"

    def func(self):
        """
        Sets the encoding.
        """
        caller = self.caller
        if 'clear' in self.switches:
            # remove customization
            old_encoding = caller.player.db.encoding
            if old_encoding:
                string = "Your custom text encoding ('%s') was cleared." % old_encoding
            else:
                string = "No custom encoding was set."
            del caller.player.db.encoding
        elif not self.args:
            # just list the encodings supported
            encodings = []
            encoding = caller.player.db.encoding            
            string = "Supported encodings "
            if encoding: 
                encodings.append(encoding)
                string += "(the first one you can change with {w@encoding <encoding>{n)"
            encodings.extend(settings.ENCODINGS)
            string += ":\n  " + ", ".join(encodings)
        else:            
            # change encoding 
            old_encoding = caller.player.db.encoding
            encoding = self.args
            caller.player.db.encoding = encoding
            string = "Your custom text encoding was changed from '%s' to '%s'." % (old_encoding, encoding)
        caller.msg(string)                    

class CmdGroup(MuxCommand):
    """
    group - show your groups

    Usage:
      group

    This command shows you which user permission groups
    you are a member of, if any. 
    """
    key = "access"
    aliases = "groups"    

    def func(self):
        "Load the permission groups"

        caller = self.caller

        string = ""
        if caller.player and caller.player.is_superuser:
            string += "\n  This is a SUPERUSER account! Group membership does not matter."
        else:            
            # get permissions and determine if they are groups
            perms = list(set(caller.permissions + caller.player.permissions))

            for group in [group for group in PermissionGroup.objects.all() 
                          if group.key in perms]:
                string += "\n {w%s{n\n%s" % (group.key, ", ".join(group.group_permissions))
            if string:        
                string = "\nGroup memberships for you (Player %s + Character %s): %s" % (caller.player.name, 
                                                                                         caller.name, string)     
            else:
                string = "\nYou are not not a member of any groups."
        caller.msg(string)

## def cmd_apropos(command):
##     """    
##     apropos - show rough help matches

##     Usage:
##       apropos <text>
##       or
##       suggest <text>
    
##     This presents a list of topics very loosely matching your
##     search text. Use this command when you are searching for
##     help on a certain concept but don't know any exact
##     command names. You can also use the normal help command
##     with the /apropos switch to get the same functionality. 
##     """
##     arg = command.command_argument    
##     command.caller.execute_cmd("help/apropos %s" % arg)
## GLOBAL_CMD_TABLE.add_command("apropos", cmd_apropos)
## GLOBAL_CMD_TABLE.add_command("suggest", cmd_apropos)
