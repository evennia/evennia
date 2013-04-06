"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.utils import utils, search, create
from src.objects.models import ObjectNick as Nick
from src.commands.default.muxcommand import MuxCommand, MuxCommandOOC

from settings import MAX_NR_CHARACTERS, MULTISESSION_MODE
# force max nr chars to 1 if mode is 0 or 1
MAX_NR_CHARACTERS = MULTISESSION_MODE < 2 and 1 or MAX_NR_CHARACTERS

# limit symbol import for API
__all__ = ("CmdHome", "CmdLook", "CmdPassword", "CmdNick",
           "CmdInventory", "CmdGet", "CmdDrop", "CmdGive", "CmdQuit", "CmdWho",
           "CmdSay", "CmdPose", "CmdEncoding", "CmdAccess",
           "CmdOOCLook", "CmdIC", "CmdOOC", "CmdColorTest")

AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
BASE_PLAYER_TYPECLASS = settings.BASE_PLAYER_TYPECLASS

class CmdHome(MuxCommand):
    """
    home

    Usage:
      home

    Teleports you to your home location.
    """

    key = "home"
    locks = "cmd:perm(home) or perm(Builders)"

    def func(self):
        "Implement the command"
        caller = self.caller
        home = caller.home
        if not home:
            caller.msg("You have no home!")
        elif home == caller.location:
            caller.msg("You are already home!")
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
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        args = self.args
        if args:
            # Use search to handle duplicate/nonexistant results.
            looking_at_obj = caller.search(args, use_nicks=True)
            if not looking_at_obj:
                return
        else:
            looking_at_obj = caller.location
            if not looking_at_obj:
                caller.msg("You have no location to look at!")
                return

        if not hasattr(looking_at_obj, 'return_appearance'):
            # this is likely due to us having a player instead
            looking_at_obj = looking_at_obj.character
        if not looking_at_obj.access(caller, "view"):
            caller.msg("Could not find '%s'." % args)
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
    locks = "cmd:all()"

    def func(self):
        "hook function."

        caller = self.caller
        if hasattr(caller, "player"):
            caller = caller.player

        if not self.rhs:
            caller.msg("Usage: @password <oldpass> = <newpass>")
            return
        oldpass = self.lhslist[0] # this is already stripped by parse()
        newpass = self.rhslist[0] #               ''
        try:
            uaccount = caller.user
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
      list     - show all defined aliases (also "nicks" works)

    Examples:
      nick hi = say Hello, I'm Sarah!
      nick/object tom = the tall man

    A 'nick' is a personal shortcut you create for your own use. When
    you enter the nick, the alternative string will be sent instead.
    The switches control in which situations the substitution will
    happen. The default is that it will happen when you enter a
    command. The 'object' and 'player' nick-types kick in only when
    you use commands that requires an object or player as a target -
    you can then use the nick to refer to them.

    Note that no objects are actually renamed or changed by this
    command - the nick is only available to you. If you want to
    permanently add keywords to an object for everyone to use, you
    need build privileges and to use the @alias command.
    """
    key = "nick"
    aliases = ["nickname", "nicks", "@nick", "alias"]
    locks = "cmd:all()"

    def func(self):
        "Create the nickname"

        caller = self.caller
        switches = self.switches

        nicks = Nick.objects.filter(db_obj=caller.dbobj).exclude(db_type="channel")
        if 'list' in switches:
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

    Shows your inventory.
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
                desc = item.db.desc
                if not desc:
                    desc = ""
                cols[1].append(utils.crop(str(desc)))
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
        obj = caller.search(self.args, location=caller.location)
        if not obj:
            return
        if caller == obj:
            caller.msg("You can't get yourself.")
            return
        #print obj, obj.location, caller, caller==obj.location
        if caller == obj.location:
            caller.msg("You already hold that.")
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

        # Because the DROP command by definition looks for items
        # in inventory, call the search function using location = caller
        results = caller.search(self.args, location=caller, ignore_errors=True)

        # now we send it into the error handler (this will output consistent
        # error messages if there are problems).
        obj = AT_SEARCH_RESULT(caller, self.args, results, False,
                              nofound_string="You don't carry %s." % self.args,
                              multimatch_string="You carry more than one %s:" % self.args)
        if not obj:
            return

        obj.move_to(caller.location, quiet=True)
        caller.msg("You drop %s." % (obj.name,))
        caller.location.msg_contents("%s drops %s." %
                                         (caller.name, obj.name),
                                         exclude=caller)
        # Call the object script's at_drop() method.
        obj.at_drop(caller)


class CmdGive(MuxCommand):
    """
    give away things

    Usage:
      give <inventory obj> = <target>

    Gives an items from your inventory to another character,
    placing it in their inventory.
    """
    key = "give"
    locks = "cmd:all()"

    def func(self):
        "Implement give"

        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: give <inventory object> = <target>")
            return
        to_give = caller.search(self.lhs)
        target = caller.search(self.rhs)
        if not (to_give and target):
            return
        if target == caller:
            caller.msg("You keep %s to yourself." % to_give.key)
            return
        if not to_give.location == caller:
            caller.msg("You are not holding %s." % to_give.key)
            return
        # give object
        to_give.location = target
        caller.msg("You give %s to %s." % (to_give.key, target.key))
        target.msg("%s gives you %s." % (caller.key, to_give.key))


class CmdQuit(MuxCommand):
    """
    quit

    Usage:
      @quit

    Switch:
      all - disconnect all connected sessions

    Gracefully disconnect your current session from the
    game. Use the /all switch to disconnect from all sessions.
    """
    key = "@quit"
    locks = "cmd:all()"

    def func(self):
        "hook function"
        if hasattr(self.caller, "player"):
            player = self.caller.player
        else:
            player = self.caller

        if 'all' in self.switches:
            player.msg("{RQuitting{n all sessions. Hope to see you soon again.", sessid=self.sessid)
            for session in player.get_all_sessions():
                player.disconnect_session_from_player(session.sessid)
        else:
            nsess = len(player.get_all_sessions())
            if nsess == 2:
                player.msg("{RQuitting{n. One session is still connected.", sessid=self.sessid)
            elif nsess > 2:
                player.msg("{RQuitting{n. %i session are still connected." % (nsess-1), sessid=self.sessid)
            else:
                # we are quitting the last available session
                player.msg("{RQuitting{n. Hope to see you soon again.", sessid=self.sessid)
            player.disconnect_session_from_player(self.sessid)

class CmdWho(MuxCommand):
    """
    who

    Usage:
      who
      doing

    Shows who is currently online. Doing is an alias that limits info
    also for those with all permissions.
    """

    key = "who"
    aliases = "doing"
    locks = "cmd:all()"

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
            if not plr_pobject:
                plr_pobject = session.get_player()
                show_session_data = False
                table = [["Player Name"], ["On for"], ["Idle"]]
            if show_session_data:
                table[0].append(plr_pobject.name[:25])
                table[1].append(utils.time_format(delta_conn, 0))
                table[2].append(utils.time_format(delta_cmd, 1))
                table[3].append(plr_pobject.location and plr_pobject.location.id or "None")
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
    aliases = ['"', "'"]
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
class CmdSessions(MuxCommand):
    """
    check connected session(s)

    Usage:
      @sessions

    Lists the sessions currently connected to your account.

    """
    key = "@sessions"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "Implement function"

        # make sure we work on the player, not on the character
        player = self.caller
        if hasattr(player, "player"):
            player = player.player

        sessions = player.get_all_sessions()

        table = [["sessid"], ["host"], ["character"], ["location"]]
        for sess in sorted(sessions, key=lambda x:x.sessid):
            sessid = sess.sessid
            char = player.get_character(sessid)
            table[0].append(str(sess.sessid))
            table[1].append(str(sess.address[0]))
            table[2].append(char and str(char) or "None")
            table[3].append(char and str(char.location) or "N/A")
        ftable = utils.format_table(table, 5)
        string = ""
        for ir, row in enumerate(ftable):
            if ir == 0:
                string += "\n" + "{w%s{n" % ("".join(row))
            else:
                string += "\n" + "".join(row)
        self.msg(string)


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

    Describe an action being taken. The pose text will
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
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        "Hook function"
        if not self.args:
            msg = "What do you want to do?"
            self.caller.msg(msg)
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
        if hasattr(caller, 'player'):
            caller = caller.player

        if 'clear' in self.switches:
            # remove customization
            old_encoding = caller.db.encoding
            if old_encoding:
                string = "Your custom text encoding ('%s') was cleared." % old_encoding
            else:
                string = "No custom encoding was set."
            del caller.db.encoding
        elif not self.args:
            # just list the encodings supported
            pencoding = caller.db.encoding
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
            old_encoding = caller.db.encoding
            encoding = self.args
            caller.db.encoding = encoding
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
        #hierarchy = [p.lower() for p in hierarchy_full]

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

class CmdColorTest(MuxCommand):
    """
    testing colors

    Usage:
      @color ansi|xterm256

    Print a color map along with in-mud color codes, while testing what is supported in your client.
    Choices are 16-color ansi (supported in most muds) or the 256-color xterm256 standard.
    No checking is done to determine your client supports color - if not you will
    see rubbish appear.
    """
    key = "@color"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "Show color tables"

        if not self.args or not self.args in ("ansi", "xterm256"):
            self.caller.msg("Usage: @color ansi|xterm256")
            return

        if self.args == "ansi":
            from src.utils import ansi
            ap = ansi.ANSI_PARSER
            # ansi colors
            # show all ansi color-related codes
            col1 = ["%s%s{n" % (code, code.replace("{","{{")) for code, _ in ap.ext_ansi_map[:-1]]
            hi = "%ch"
            col2 = ["%s%s{n" % (code, code.replace("%", "%%")) for code, _ in ap.mux_ansi_map[:-2]]
            col3 = ["%s%s{n" % (hi+code, (hi+code).replace("%", "%%")) for code, _ in ap.mux_ansi_map[:-2]]
            table = utils.format_table([col1, col2, col3], extra_space=1)
            string = "ANSI colors:"
            for row in table:
                string += "\n" + "".join(row)
            print string
            self.caller.msg(string)
            self.caller.msg("{{X and %%cx are black-on-black)")
        elif self.args == "xterm256":
            table = [[],[],[],[],[],[],[],[],[],[],[],[]]
            for ir in range(6):
                for ig in range(6):
                    for ib in range(6):
                        # foreground table
                        table[ir].append("%%c%i%i%i%s{n" % (ir,ig,ib, "{{%i%i%i" % (ir,ig,ib)))
                        # background table
                        table[6+ir].append("%%cb%i%i%i%%c%i%i%i%s{n" % (ir,ig,ib,
                                                                        5-ir,5-ig,5-ib,
                                                                        "{{b%i%i%i" % (ir,ig,ib)))
            table = utils.format_table(table)
            string = "Xterm256 colors:"
            for row in table:
                string += "\n" + "".join(row)
            self.caller.msg(string)
            self.caller.msg("(e.g. %%c123 and %%cb123 also work)")


#------------------------------------------------------------
# OOC commands
#
# Note that in  commands inheriting from MuxCommandOOC,
# self.caller is always the Player object, not the Character.
# A property self.character can be used to access the
# connecter character (this can be None if no character is
# currently controlled by the Player).
#------------------------------------------------------------

class CmdOOCLook(MuxCommandOOC, CmdLook):
    """
    ooc look

    Usage:
      look

    Look in the ooc state.
    """

    #This is an OOC version of the look command. Since a
    #Player doesn't have an in-game existence, there is no
    #concept of location or "self". If we are controlling
    #a character, pass control over to normal look.

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_category = "General"

    def look_target(self):
        "Hook method for when an argument is given."
        # caller is assumed to be a player object here.
        caller = self.caller
        key = self.args.lower()
        chars = dict((utils.to_str(char.key.lower()), char) for char in caller.db._playable_characters)
        looktarget = chars.get(key)
        if looktarget:
            caller.msg(looktarget.return_appearance(caller))
        else:
            caller.msg("No such character.")
        return

    def no_look_target(self):
        "Hook method for default look without a specified target"
        # caller is always a player at this point.
        player = self.caller
        sessid = self.sessid
        # get all our characters and sessions
        characters = player.db._playable_characters
        sessions = player.get_all_sessions()

        sessidstr = sessid and " (session id %i)" % sessid or ""
        string = "%sYou are logged in as {g%s{n%s." % (" "*10,player.key, sessidstr)

        string += "\n\nSession(s) connected:"
        for sess in sessions:
            csessid = sess.sessid
            string += "\n %s %s" % (sessid == csessid and "{w%i{n" % csessid or csessid, sess.address)
        string += "\n\nUse {w@ic <character>{n to enter the game, {w@occ{n to get back here."
        if characters:
            string += "\n\nAvailable character%s%s:"  % (len(characters) > 1 and "s" or "",
                                                         MAX_NR_CHARACTERS > 1 and " (out of a maximum of %i)" % MAX_NR_CHARACTERS or "")
            for char in characters:
                csessid = char.sessid
                if csessid:
                    # character is already puppeted
                    sess = player.get_session(csessid)
                    if hasattr(char.locks, "lock_bypass") and char.locks.lock_bypass:
                        string += "\n - {G%s{n [superuser character] (played by you from session with id %i)" % (char.key, sess.sessid)
                    elif sess:
                        string += "\n - {G%s{n [%s] (played by you session id %i)" % (char.key, ", ".join(char.permissions), sess.sessid)
                    else:
                        string += "\n - {R%s{n [%s] (played by someone else)" % (char.key, ", ".join(char.permissions))
                else:
                    # character is "free to puppet"
                    if player.is_superuser and char.get_attribute("_superuser_character"):
                        string += "\n - %s [Superuser character]" % (char.key)
                    else:
                        string += "\n - %s [%s]" % (char.key, ", ".join(char.permissions))
        string = ("-" * 68) + "\n" + string + "\n" + ("-" * 68)
        self.msg(string)

    def func(self):
        "implement the ooc look command"

        if MULTISESSION_MODE < 2:
            # only one character allowed
            string = "You are out-of-character (OOC).\nUse {w@ic{n to get back into the game."
            self.msg(string)
            return
        if utils.inherits_from(self.caller, "src.objects.objects.Object"):
            # An object of some type is calling. Use default look instead.
            super(CmdOOCLook, self).func()
        elif self.args:
            self.look_target()
        else:
            self.no_look_target()

class CmdCharCreate(MuxCommandOOC):
    """
    Create a character

    Usage:
      @charcreate <charname> [= desc]

    Create a new character, optionally giving it a description.
    """
    key = "@charcreate"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "create the new character"
        player = self.caller
        if not self.args:
            player.msg("Usage: @charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs
        if player.db._playable_characters and len(player.db._playable_characters) >= self.MAX_NR_CHARACTERS:
            self.msg("You may only create a maximum of %i characters." % self.MAX_NR_CHARACTERS)
            return
        # create the character
        from src.objects.models import ObjectDB

        default_home = ObjectDB.objects.get_id(settings.CHARACTER_DEFAULT_HOME)
        typeclass = settings.BASE_CHARACTER_TYPECLASS
        permissions = settings.PERMISSION_PLAYER_DEFAULT

        new_character = create.create_object(typeclass, key=key, location=default_home,
                                             home=default_home, permissions=permissions)
        # only allow creator (and immortals) to puppet this char
        new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Immortals) or pperm(Immortals)" %
                                (new_character.id, player.id))
        player.db._playable_characters.append(new_character)
        if desc:
            new_character.db.desc = desc
        else:
            new_character.db.desc = "This is a Player."
        self.msg("Created new character %s." % new_character.key)


class CmdIC(MuxCommandOOC):
    """
    Switch control to an object

    Usage:
      @ic <character>

    Go in-character (IC) as a given Character.

    This will attempt to "become" a different object assuming you have
    the right to do so. Note that it's the PLAYER character that puppets
    characters/objects and which needs to have the correct permission!

    You cannot become an object that is already controlled by another
    player. In principle <character> can be any in-game object as long
    as you the player have access right to puppet it.
    """

    key = "@ic"
    locks = "cmd:all()" # must be all() or different puppeted objects won't be able to access it.
    aliases = "@puppet"
    help_category = "General"

    def func(self):
        """
        Simple puppet method
        """
        caller = self.caller
        sessid = self.sessid
        old_character = self.character

        new_character = None
        if not self.args:
            new_character = caller.db._last_puppet
            if not new_character:
                self.msg("Usage: @ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = search.objects(self.args, caller)
            if new_character:
                new_character = new_character[0]
            else:
                self.msg("That is not a valid character choice.")
                return
        # permission checks
        if caller.get_character(sessid=sessid, character=new_character):
            self.msg("{RYou already act as {c%s{n." % new_character.name)
            return
        if new_character.player:
            if new_character.sessid == sessid:
                self.msg("{RYou already act as {c%s{n." % new_character.name)
                return
            elif new_character.player == caller:
                self.msg("{RYou already act as {c%s{n in another session." % new_character.name)
                return
            elif not caller.get_character(character=new_character):
                self.msg("{c%s{r is already acted by another player.{n" % new_character.name)
                return
        if not new_character.access(caller, "puppet"):
            self.msg("{rYou may not become %s.{n" % new_character.name)
            return
        if caller.connect_character(new_character, sessid=sessid):
            self.msg("\n{gYou become {c%s{n.\n" % new_character.name)
            caller.db._last_puppet = old_character
            if not new_character.location:
                # this might be due to being hidden away at logout; check
                loc = new_character.db.prelogout_location
                if not loc: # still no location; use home
                    loc = new_character.home
                new_character.location = loc
                if new_character.location:
                    new_character.location.msg_contents("%s has entered the game." % new_character.key, exclude=[new_character])
                    new_character.location.at_object_receive(new_character, new_character.location)
            new_character.execute_cmd("look")
        else:
            msg.msg("{rYou cannot become {C%s{n." % new_character.name)

class CmdOOC(MuxCommandOOC):
    """
    go ooc

    Usage:
      @ooc

    Go out-of-character (OOC).

    This will leave your current character and put you in a incorporeal OOC state.
    """

    key = "@ooc"
    locks = "cmd:all()" # this must be all(), or different puppeted objects won't be able to access it.
    aliases = "@unpuppet"
    help_category = "General"

    def func(self):
        "Implement function"

        caller = self.caller

        old_char = caller.get_character(sessid=self.sessid)
        if not old_char:
            string = "You are already OOC."
            self.msg(string)
            return

        caller.db._last_puppet = old_char
        # save location as if we were disconnecting from the game entirely.
        if old_char.location:
            old_char.location.msg_contents("%s has left the game." % old_char.key, exclude=[old_char])
            old_char.db.prelogout_location = old_char.location
            old_char.location = None

        # disconnect
        err = caller.disconnect_character(self.character)
        self.msg("\n{GYou go OOC.{n\n")
        caller.execute_cmd("look")

