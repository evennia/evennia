"""
Player (OOC) commands. These are stored on the Player object
and self.caller is thus always a Player, not an Object/Character.

These commands go in the PlayerCmdset and are accessible also
when puppeting a Character (although with lower priority)

These commands use the MuxCommandOOC parent that makes sure
to setup caller correctly. The self.character can be used to
access the character when these commands are triggered with
a connected character (such as the case of the @ooc command), it
is None if we are OOC.

"""
import time
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.commands.default.muxcommand import MuxPlayerCommand
from src.utils import utils, create, search

from settings import MAX_NR_CHARACTERS, MULTISESSION_MODE
# limit symbol import for API
__all__ = ("CmdOOCLook", "CmdIC", "CmdOOC", "CmdPassword", "CmdQuit", "CmdEncoding", "CmdWho", "CmdColorTest")

# force max nr chars to 1 if mode is 0 or 1
MAX_NR_CHARACTERS = MULTISESSION_MODE < 2 and 1 or MAX_NR_CHARACTERS
BASE_PLAYER_TYPECLASS = settings.BASE_PLAYER_TYPECLASS

class CmdOOCLook(MuxPlayerCommand):
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
        player = self.caller
        key = self.args.lower()
        chars = dict((utils.to_str(char.key.lower()), char) for char in player.db._playable_characters)
        looktarget = chars.get(key)
        if looktarget:
            self.msg(looktarget.return_appearance(player))
        else:
            self.msg("No such character.")
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
        string = "You are logged in as {g%s{n%s." % (player.key, sessidstr)

        string += "\n\nSession(s) connected:"
        for sess in sessions:
            csessid = sess.sessid
            string += "\n %s %s" % (sessid == csessid and "{w%i{n" % csessid or csessid, sess.address)
        string += "\n\nUse {w@ic <character>{n to enter the game, {w@occ{n to get back here."
        if not characters:
            string += "\nYou don't have any character yet. Use {w@charcreate <name> [=description]{n to create one."
        elif len(characters) < MAX_NR_CHARACTERS:
            string += "\nUse {w@charcreate <name> [=description]{n to create a new character (max %i)" % MAX_NR_CHARACTERS
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

class CmdCharCreate(MuxPlayerCommand):
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
            self.msg("Usage: @charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs
        if player.db._playable_characters and len(player.db._playable_characters) >= MAX_NR_CHARACTERS:
            self.msg("You may only create a maximum of %i characters." % MAX_NR_CHARACTERS)
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


class CmdIC(MuxPlayerCommand):
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
        Main puppet method
        """
        player = self.caller
        sessid = self.sessid

        new_character = None
        if not self.args:
            new_character = player.db._last_puppet
            if not new_character:
                self.msg("Usage: @ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = search.objects(self.args, player)
            if new_character:
                new_character = new_character[0]
            else:
                self.msg("That is not a valid character choice.")
                return
        # permission checks
        if player.get_puppet(sessid) == new_character:
            self.msg("{RYou already act as {c%s{n." % new_character.name)
            return
        if new_character.player:
            # may not puppet an already puppeted character
            if new_character.sessid and new_character.player == player:
                self.msg("{RYou already act as {c%s{n in another session." % new_character.name)
                return
            elif new_character.player != player and new_character.player.is_connected:
                self.msg("{c%s{r is already acted by another player.{n" % new_character.name)
                return
        if not new_character.access(player, "puppet"):
            # main acccess check
            self.msg("{rYou may not become %s.{n" % new_character.name)
            return
        if player.puppet_object(sessid, new_character):
            self.msg("\n{gYou become {c%s{n.\n" % new_character.name)
            player.db._last_puppet = new_character
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
            self.msg("{rYou cannot become {C%s{n." % new_character.name)

class CmdOOC(MuxPlayerCommand):
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

        player = self.caller
        sessid = self.sessid

        old_char = player.get_puppet(sessid)
        if not old_char:
            string = "You are already OOC."
            self.msg(string)
            return

        player.db._last_puppet = old_char
        # save location as if we were disconnecting from the game entirely.
        if old_char.location:
            old_char.location.msg_contents("%s has left the game." % old_char.key, exclude=[old_char])
            old_char.db.prelogout_location = old_char.location
            old_char.location = None

        # disconnect
        if player.unpuppet_object(sessid):
            self.msg("\n{GYou go OOC.{n\n")
            player.execute_cmd("look")
        else:
            raise RuntimeError("Could not unpuppet!")

class CmdWho(MuxPlayerCommand):
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
            plr_pobject = session.get_puppet()
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

class CmdEncoding(MuxPlayerCommand):
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

class CmdPassword(MuxPlayerCommand):
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

class CmdQuit(MuxPlayerCommand):
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
        # always operate on the player
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



class CmdColorTest(MuxPlayerCommand):
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
            #print string
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


