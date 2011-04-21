"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.objects.models import HANDLE_SEARCH_ERRORS
from src.utils import utils
from src.objects.models import Nick
from src.commands.default.muxcommand import MuxCommand

class CmdHome(MuxCommand):
    """
    home

    Usage:
      home 

    Teleports the player to their home.
    """
    
    key = "home"
    locks = "cmd:perm(home) or perm(Builders)"    

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
      look *<player>

    Observes your location or objects in your vicinity.
    """
    key = "look"
    aliases = ["l"]
    locks = "cmd:all()"

    def func(self):
        """
        Handle the looking. 
        """
        caller = self.caller
        args = self.args        # caller.msg(inp)

        if args:
            # Use search to handle duplicate/nonexistant results.
            looking_at_obj = caller.search(args, use_nicks=True)
            if not looking_at_obj:
                return
        else:
            looking_at_obj = caller.location
            if not looking_at_obj:
                caller.msg("Location: None")
                return
        if not hasattr(looking_at_obj, 'return_appearance'):
            # this is likely due to us having a player instead
            looking_at_obj = looking_at_obj.character    
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
    locks = "cmd:all()"

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
      nick[/switches] <nickname> = [<string>]
      alias             ''

    Switches:      
      object   - alias an object
      player   - alias a player 
      clearall - clear all your aliases
      list     - show all defined aliases 
      
    If no switch is given, a command alias is created, used
    to replace strings before sending the command. Give an empty
    right-hand side to clear the nick
      
    Creates a personal nick for some in-game object or
    string. When you enter that string, it will be replaced
    with the alternate string. The switches dictate in what
    situations the nick is checked and substituted. If string
    is None, the alias (if it exists) will be cleared.
    Obs - no objects are actually changed with this command,
    if you want to change the inherent aliases of an object,
    use the @alias command instead. 
    """
    key = "nick"
    aliases = ["nickname", "nicks", "@nick", "alias"]
    locks = "cmd:all()"    

    def func(self):
        "Create the nickname"
        
        caller = self.caller
        switches = self.switches

        nicks = Nick.objects.filter(db_obj=caller.dbobj).exclude(db_type="channel")
        if 'list' in switches or self.cmdstring == "nicks":
            string = "{wDefined Nicks:{n"
            cols = [["Type"],["Nickname"],["Translates-to"] ]
            for nick in nicks:
                cols[0].append(nick.db_type)
                cols[1].append(nick.db_nick)
                cols[2].append(nick.db_real)
            for ir, row in enumerate(utils.format_table(cols)):
                if ir == 0:
                    string += "\n{w" + "".join(row) + "{n"
                else:
                    string += "\n" + "".join(row)
            caller.msg(string)
            return
        if 'clearall' in switches:
            nicks.delete()
            caller.msg("Cleared all aliases.")
            return         
        if not self.args or not self.lhs:
            caller.msg("Usage: nick[/switches] nickname = [realname]")
            return                        
        nick = self.lhs
        real = self.rhs     

        if real == nick:
            caller.msg("No point in setting nick same as the string to replace...")
            return 
        
        # check so we have a suitable nick type
        if not any(True for switch in switches if switch in ("object", "player", "inputline")):
            switches = ["inputline"] 
        string = ""
        for switch in switches:
            oldnick = Nick.objects.filter(db_obj=caller.dbobj, db_nick__iexact=nick, db_type__iexact=switch)
            if not real:
                # removal of nick
                if oldnick:
                    # clear the alias
                    string += "\nNick '%s' (= '%s') was cleared." % (nick, oldnick[0].db_real)
                    caller.nicks.delete(nick, nick_type=switch)
                else:
                    string += "\nNo nick '%s' found, so it could not be removed." % nick
            else:
                # creating new nick 
                if oldnick:
                    string += "\nNick %s changed from '%s' to '%s'." % (nick, oldnick[0].db_real, real)
                else:
                    string += "\nNick set: '%s' = '%s'." % (nick, real)
                caller.nicks.add(nick, real, nick_type=switch)            
        caller.msg(string)
        
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
    locks = "cmd:all()"

    def func(self):
        "check inventory"
        items = self.caller.contents
        if not items:
            string = "You are not carrying anything."
        else:
            # format item list into nice collumns
            cols = [[],[]]
            for item in items:
                cols[0].append(item.name)
                desc = utils.crop(item.db.desc)                
                if not desc:
                    desc = ""
                cols[1].append(desc)
            # auto-format the columns to make them evenly wide
            ftable = utils.format_table(cols)
            string = "You are carrying:"
            for row in ftable:
                string += "\n " + "{C%s{n - %s" % (row[0], row[1])
        self.caller.msg(string)

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
    locks = "cmd:all()"    

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
        if obj.player or obj.destination: 
            # don't allow picking up player objects, nor exits.
            caller.msg("You can't get that.")
            return
        if not obj.access(caller, 'get'):
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
    locks = "cmd:all()"
    
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
    locks = "cmd:all()"    

    def func(self):
        "hook function"  
        for session in self.caller.sessions:
            session.msg("Quitting. Hope to see you soon again.")
            session.session_disconnect()
            
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
        session_list = SESSIONS.get_sessions()

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = caller.check_permstring("Immortals") or caller.check_permstring("Wizards")

        if show_session_data:
            table = [["Player Name"], ["On for"], ["Idle"], ["Room"], ["Cmds"], ["Host"]]
        else:
            table = [["Player Name"], ["On for"], ["Idle"]]
            
        for session in session_list:
            if not session.logged_in:
                continue
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            plr_pobject = session.get_character()
            if show_session_data:
                table[0].append(plr_pobject.name[:25])
                table[1].append(utils.time_format(delta_conn, 0))
                table[2].append(utils.time_format(delta_cmd, 1))                     
                table[3].append(plr_pobject.location.id)
                table[4].append(session.cmd_total)
                table[5].append(session.address[0])
            else:
                table[0].append(plr_pobject.name[:25])
                table[1].append(utils.time_format(delta_conn,0))
                table[2].append(utils.time_format(delta_cmd,1))
        stable = []
        for row in table: # prettify values
            stable.append([str(val).strip() for val in row])
        ftable = utils.format_table(stable, 5)
        string = ""
        for ir, row in enumerate(ftable):
            if ir == 0:
                string += "\n" + "{w%s{n" % ("".join(row))
            else:
                string += "\n" + "".join(row)
        nplayers = (SESSIONS.player_count())
        if nplayers == 1:            
            string += '\nOne player logged in.'
        else:
            string += '\n%d players logged in.' % nplayers

        caller.msg(string)

class CmdSay(MuxCommand):
    """
    say

    Usage:
      say <message>
      
    Talk to those in your current location. 
    """
    
    key = "say"
    aliases = ['"']
    locks = "cmd:all()"
    
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
    locks = "cmd:all()"

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
    locks = "cmd:all()"

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
            pencoding = caller.player.db.encoding                        
            string = ""
            if pencoding: 
                string += "Default encoding: {g%s{n (change with {w@encoding <encoding>{n)" % pencoding                
            encodings = settings.ENCODINGS
            if encodings:
                string += "\nServer's alternative encodings (tested in this order):\n   {g%s{n" % ", ".join(encodings)            
            if not string:
                string = "No encodings found."
        else:            
            # change encoding 
            old_encoding = caller.player.db.encoding
            encoding = self.args
            caller.player.db.encoding = encoding
            string = "Your custom text encoding was changed from '%s' to '%s'." % (old_encoding, encoding)
        caller.msg(string.strip())                    

class CmdAccess(MuxCommand):
    """
    access - show access groups

    Usage:
      access

    This command shows you the permission hierarchy and 
    which permission groups you are a member of.
    """
    key = "access"
    aliases = ["groups", "hierarchy"]
    locks = "cmd:all()"

    def func(self):
        "Load the permission groups"

        caller = self.caller
        hierarchy_full = settings.PERMISSION_HIERARCHY
        string = "\n{wPermission Hierarchy{n (climbing):\n %s" % ", ".join(hierarchy_full)        
        hierarchy = [p.lower() for p in hierarchy_full]

        if self.caller.player.is_superuser:
            cperms = "<Superuser>"
            pperms = "<Superuser>"
        else:
            cperms = ", ".join(caller.permissions)
            pperms = ", ".join(caller.player.permissions)

        string += "\n{wYour access{n:"
        string += "\nCharacter {c%s{n: %s" % (caller.key, cperms)
        if hasattr(caller, 'player'):
            string += "\nPlayer {c%s{n: %s" % (caller.player.key, pperms)
        caller.msg(string)
