"""
Generic command module. Pretty much every command should go here for
now.
"""
import time
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.utils import utils, search
from src.objects.models import ObjectNick as Nick
from src.commands.default.muxcommand import MuxCommand, MuxCommandOOC

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

    Gracefully disconnect from the game.
    """
    key = "@quit"
    locks = "cmd:all()"

    def func(self):
        "hook function"
        for session in self.caller.sessions:
            session.msg("{RQuitting{n. Hope to see you soon again.")
            session.session_disconnect()

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

# OOC commands

class CmdOOCLook(MuxCommandOOC, CmdLook):
    """
    ooc look

    Usage:
      look

    This is an OOC version of the look command. Since a
    Player doesn't have an in-game existence, there is no
    concept of location or "self". If we are controlling
    a character, pass control over to normal look.

    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "implement the ooc look command"

        if not self.character:
            string = "You are out-of-character (OOC). "
            string += "Use {w@ic{n to get back to the game, {whelp{n for more info."
            self.caller.msg(string)
        else:
            self.caller = self.character # we have to put this back for normal look to work.
            super(CmdOOCLook, self).func()

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
        old_character = self.character

        new_character = None
        if not self.args:
            new_character = caller.db.last_puppet
            if not new_character:
                caller.msg("Usage: @ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = search.objects(self.args, caller)
            if new_character:
                new_character = new_character[0]
            else:
                # the search method handles error messages etc.
                return
        if new_character.player:
            if new_character.player == caller:
                caller.msg("{RYou already are {c%s{n." % new_character.name)
            else:
                caller.msg("{c%s{r is already acted by another player.{n" % new_character.name)
            return
        if not new_character.access(caller, "puppet"):
            caller.msg("{rYou may not become %s.{n" % new_character.name)
            return
        if caller.swap_character(new_character):
            new_character.msg("\n{gYou become {c%s{n.\n" % new_character.name)
            caller.db.last_puppet = old_character
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
            caller.msg("{rYou cannot become {C%s{n." % new_character.name)

class CmdOOC(MuxCommandOOC):
    """
    @ooc - go ooc

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

        if utils.inherits_from(caller, "src.objects.objects.Object"):
            caller = self.caller.player

        if not caller.character:
            string = "You are already OOC."
            caller.msg(string)
            return

        caller.db.last_puppet = caller.character
        # save location as if we were disconnecting from the game entirely.
        if caller.character.location:
            caller.character.location.msg_contents("%s has left the game." % caller.character.key, exclude=[caller.character])
            caller.character.db.prelogout_location = caller.character.location
            caller.character.location = None

        # disconnect
        caller.character.player = None
        caller.character = None

        caller.msg("\n{GYou go OOC.{n\n")
        caller.execute_cmd("look")

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

