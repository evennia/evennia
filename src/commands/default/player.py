"""
Player (OOC) commands. These are stored on the Player object
and self.caller is thus always a Player, not an Object/Character.

These commands go in the PlayerCmdset and are accessible also
when puppeting a Character (although with lower priority)

These commands use the MuxCommandOOC parent that makes sure
to setup caller correctly. They use self.player to make sure
to always use the player object rather than self.caller (which
change depending on the level you are calling from)
The property self.character can be used to
access the character when these commands are triggered with
a connected character (such as the case of the @ooc command), it
is None if we are OOC.

Note that under MULTISESSION_MODE=2, Player- commands should use
self.msg() and similar methods to reroute returns to the correct
method. Otherwise all text will be returned to all connected sessions.

"""
import time
from django.conf import settings
from src.server.sessionhandler import SESSIONS
from src.commands.default.muxcommand import MuxPlayerCommand
from src.utils import utils, create, search, prettytable

from settings import MAX_NR_CHARACTERS, MULTISESSION_MODE
# limit symbol import for API
__all__ = ("CmdOOCLook", "CmdIC", "CmdOOC", "CmdPassword", "CmdQuit",
           "CmdCharCreate", "CmdEncoding", "CmdSessions", "CmdWho",
           "CmdColorTest", "CmdQuell")

# force max nr chars to 1 if mode is 0 or 1
MAX_NR_CHARACTERS = MULTISESSION_MODE < 2 and 1 or MAX_NR_CHARACTERS
BASE_PLAYER_TYPECLASS = settings.BASE_PLAYER_TYPECLASS

PERMISSION_HIERARCHY = settings.PERMISSION_HIERARCHY
PERMISSION_HIERARCHY_LOWER = [perm.lower() for perm in PERMISSION_HIERARCHY]

# Obs - these are all intended to be stored on the Player, and as such,
# use self.player instead of self.caller, just to be sure. Also self.msg()
# is used to make sure returns go to the right session

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
        player = self.player
        key = self.args.lower()
        chars = dict((utils.to_str(char.key.lower()), char)
                       for char in player.db._playable_characters)
        looktarget = chars.get(key)
        if looktarget:
            self.msg(looktarget.return_appearance(player))
        else:
            self.msg("No such character.")
        return

    def no_look_target(self):
        "Hook method for default look without a specified target"
        # caller is always a player at this point.
        player = self.player
        sessid = self.sessid
        # get all our characters and sessions
        characters = player.db._playable_characters
        sessions = player.get_all_sessions()
        is_su = player.is_superuser

        # text shown when looking in the ooc area
        string = "Account {g%s{n (you are Out-of-Character)" % (player.key)

        nsess = len(sessions)
        string += nsess == 1 and "\n\n{wConnected session:{n" or "\n\n{wConnected sessions (%i):{n" % nsess
        for isess, sess in enumerate(sessions):
            csessid = sess.sessid
            addr = "%s (%s)" % (sess.protocol_key, isinstance(sess.address, tuple) and str(sess.address[0]) or str(sess.address))
            string += "\n %s %s" % (sessid == csessid and "{w%s{n" % (isess + 1) or (isess + 1), addr)
        string += "\n\n {whelp{n - more commands"
        string += "\n {wooc <Text>{n - talk on public channel"

        if is_su or len(characters) < MAX_NR_CHARACTERS:
            if not characters:
                string += "\n\n You don't have any characters yet. See {whelp @charcreate{n for creating one."
            else:
                string += "\n {w@charcreate <name> [=description]{n - create new character"

        if characters:
            string_s_ending = len(characters) > 1 and "s" or ""
            string += "\n {w@ic <character>{n - enter the game ({w@ooc{n to get back here)"
            if is_su:
                string += "\n\nAvailable character%s (%i/unlimited):" % (string_s_ending, len(characters))
            else:
                string += "\n\nAvailable character%s%s:"  % (string_s_ending,
                         MAX_NR_CHARACTERS > 1 and " (%i/%i)" % (len(characters), MAX_NR_CHARACTERS) or "")

            for char in characters:
                csessid = char.sessid
                if csessid:
                    # character is already puppeted
                    sess = player.get_session(csessid)
                    sid = sess in sessions and sessions.index(sess) + 1
                    if sess and sid:
                        string += "\n - {G%s{n [%s] (played by you in session %i)" % (char.key, ", ".join(char.permissions.all()), sid)
                    else:
                        string += "\n - {R%s{n [%s] (played by someone else)" % (char.key, ", ".join(char.permissions.all()))
                else:
                    # character is "free to puppet"
                    string += "\n - %s [%s]" % (char.key, ", ".join(char.permissions.all()))
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

    Create a new character, optionally giving it a description. You
    may use upper-case letters in the name - you will nevertheless
    always be able to access your character using lower-case letters
    if you want.
    """
    key = "@charcreate"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        "create the new character"
        player = self.player
        if not self.args:
            self.msg("Usage: @charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs
        if not player.is_superuser and \
            (player.db._playable_characters and
                len(player.db._playable_characters) >= MAX_NR_CHARACTERS):
            self.msg("You may only create a maximum of %i characters." % MAX_NR_CHARACTERS)
            return
        # create the character
        from src.objects.models import ObjectDB

        default_home = ObjectDB.objects.get_id(settings.CHARACTER_DEFAULT_HOME)
        typeclass = settings.BASE_CHARACTER_TYPECLASS
        permissions = settings.PERMISSION_PLAYER_DEFAULT

        new_character = create.create_object(typeclass, key=key,
                                             location=default_home,
                                             home=default_home,
                                             permissions=permissions)
        # only allow creator (and immortals) to puppet this char
        new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Immortals) or pperm(Immortals)" %
                                (new_character.id, player.id))
        player.db._playable_characters.append(new_character)
        if desc:
            new_character.db.desc = desc
        else:
            new_character.db.desc = "This is a Player."
        self.msg("Created new character %s. Use {w@ic %s{n to enter the game as this character." % (new_character.key, new_character.key))


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
    # lockmust be all() for different puppeted objects to access it.
    locks = "cmd:all()"
    aliases = "@puppet"
    help_category = "General"

    def func(self):
        """
        Main puppet method
        """
        player = self.player
        sessid = self.sessid

        new_character = None
        if not self.args:
            new_character = player.db._last_puppet
            if not new_character:
                self.msg("Usage: @ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = search.object_search(self.args)
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
                # as a safeguard we allow "taking over chars from
                # your own sessions.
                player.msg("{c%s{n{R is now acted from another of your sessions.{n" % (new_character.name), sessid=new_character.sessid)
                player.unpuppet_object(new_character.sessid)
                self.msg("Taking over {c%s{n from another of your sessions." % new_character.name)
            elif new_character.player != player and new_character.player.is_connected:
                self.msg("{c%s{r is already acted by another player.{n" % new_character.name)
                return
        if not new_character.access(player, "puppet"):
            # main acccess check
            self.msg("{rYou may not become %s.{n" % new_character.name)
            return
        if player.puppet_object(sessid, new_character):
            player.db._last_puppet = new_character
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
    # lock must be all(), for different puppeted objects to access it.
    locks = "cmd:all()"
    aliases = "@unpuppet"
    help_category = "General"

    def func(self):
        "Implement function"

        player = self.player
        sessid = self.sessid

        old_char = player.get_puppet(sessid)
        if not old_char:
            string = "You are already OOC."
            self.msg(string)
            return

        player.db._last_puppet = old_char

        # disconnect
        if player.unpuppet_object(sessid):
            self.msg("\n{GYou go OOC.{n\n")
            player.execute_cmd("look", sessid=sessid)
        else:
            raise RuntimeError("Could not unpuppet!")

class CmdSessions(MuxPlayerCommand):
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
        player = self.player
        sessions = player.get_all_sessions()

        table = prettytable.PrettyTable(["{wsessid",
                                         "{wprotocol",
                                         "{whost",
                                         "{wpuppet/character",
                                         "{wlocation"])
        for sess in sorted(sessions, key=lambda x: x.sessid):
            sessid = sess.sessid
            char = player.get_puppet(sessid)
            table.add_row([str(sessid), str(sess.protocol_key),
                           type(sess.address) == tuple and sess.address[0] or sess.address,
                           char and str(char) or "None",
                           char and str(char.location) or "N/A"])
        string = "{wYour current session(s):{n\n%s" % table
        self.msg(string)


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

        player = self.player
        session_list = SESSIONS.get_sessions()

        session_list = sorted(session_list, key=lambda o: o.player.key)

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = player.check_permstring("Immortals") or player.check_permstring("Wizards")

        nplayers = (SESSIONS.player_count())
        if show_session_data:
            table = prettytable.PrettyTable(["{wPlayer Name",
                                             "{wOn for",
                                             "{wIdle",
                                             "{wRoom",
                                             "{wCmds",
                                             "{wProtocol",
                                             "{wHost"])
            for session in session_list:
                if not session.logged_in: continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                plr_pobject = session.get_puppet()
                plr_pobject = plr_pobject or session.get_player()
                table.add_row([utils.crop(plr_pobject.name, width=25),
                               utils.time_format(delta_conn, 0),
                               utils.time_format(delta_cmd, 1),
                               hasattr(plr_pobject, "location") and plr_pobject.location.key or "None",
                               session.cmd_total,
                               session.protocol_key,
                               isinstance(session.address, tuple) and session.address[0] or session.address])
        else:
            table = prettytable.PrettyTable(["{wPlayer name", "{wOn for", "{wIdle"])
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                plr_pobject = session.get_puppet()
                plr_pobject = plr_pobject or session.get_player()
                table.add_row([utils.crop(plr_pobject.name, width=25),
                               utils.time_format(delta_conn, 0),
                               utils.time_format(delta_cmd, 1)])

        isone = nplayers == 1
        string = "{wPlayers:{n\n%s\n%s unique account%s logged in." % (table, "One" if isone else nplayers, "" if isone else "s")
        self.msg(string)


class CmdEncoding(MuxPlayerCommand):
    """
    encoding - set a custom text encoding

    Usage:
      @encoding/switches [<encoding>]

    Switches:
      clear - clear your custom encoding


    This sets the text encoding for communicating with Evennia. This is mostly
    an issue only if you want to use non-ASCII characters (i.e. letters/symbols
    not found in English). If you see that your characters look strange (or you
    get encoding errors), you should use this command to set the server
    encoding to be the same used in your client program.

    Common encodings are utf-8 (default), latin-1, ISO-8859-1 etc.

    If you don't submit an encoding, the current encoding will be displayed
    instead.
  """

    key = "@encoding"
    aliases = "@encode"
    locks = "cmd:all()"

    def func(self):
        """
        Sets the encoding.
        """
        player = self.player

        if 'clear' in self.switches:
            # remove customization
            old_encoding = player.db.encoding
            if old_encoding:
                string = "Your custom text encoding ('%s') was cleared." % old_encoding
            else:
                string = "No custom encoding was set."
            del player.db.encoding
        elif not self.args:
            # just list the encodings supported
            pencoding = player.db.encoding
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
            old_encoding = player.db.encoding
            encoding = self.args
            player.db.encoding = encoding
            string = "Your custom text encoding was changed from '%s' to '%s'." % (old_encoding, encoding)
        self.msg(string.strip())


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

        player = self.player
        if not self.rhs:
            self.msg("Usage: @password <oldpass> = <newpass>")
            return
        oldpass = self.lhslist[0]  # this is already stripped by parse()
        newpass = self.rhslist[0]  #               ''
        if not player.check_password(oldpass):
            self.msg("The specified old password isn't correct.")
        elif len(newpass) < 3:
            self.msg("Passwords must be at least three characters long.")
        else:
            player.set_password(newpass)
            player.save()
            self.msg("Password changed.")


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
        player = self.player

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

    Prints a color map along with in-mud color codes to use to produce
    them.  It also tests what is supported in your client. Choices are
    16-color ansi (supported in most muds) or the 256-color xterm256
    standard. No checking is done to determine your client supports
    color - if not you will see rubbish appear.
    """
    key = "@color"
    aliases = "color"
    locks = "cmd:all()"
    help_category = "General"

    def table_format(self, table):
       """
       Helper method to format the ansi/xterm256 tables.
       Takes a table of columns [[val,val,...],[val,val,...],...]
       """
       if not table:
           return [[]]

       extra_space = 1
       max_widths = [max([len(str(val)) for val in col]) for col in table]
       ftable = []
       for irow in range(len(table[0])):
           ftable.append([str(col[irow]).ljust(max_widths[icol]) + " " * extra_space
                          for icol, col in enumerate(table)])
       return ftable

    def func(self):
        "Show color tables"

        if self.args.startswith("a"):
            # show ansi 16-color table
            from src.utils import ansi
            ap = ansi.ANSI_PARSER
            # ansi colors
            # show all ansi color-related codes
            col1 = ["%s%s{n" % (code, code.replace("{", "{{")) for code, _ in ap.ext_ansi_map[6:14]]
            col2 = ["%s%s{n" % (code, code.replace("{", "{{")) for code, _ in ap.ext_ansi_map[14:22]]
            col3 = ["%s%s{n" % (code.replace("\\",""), code.replace("{", "{{").replace("\\", "")) for code, _ in ap.ext_ansi_map[-8:]]
            col2.extend(["" for i in range(len(col1)-len(col2))])
            #hi = "%ch"
            #col2 = ["%s%s{n" % (code, code.replace("%", "%%")) for code, _ in ap.mux_ansi_map[6:]]
            #col3 = ["%s%s{n" % (hi + code, (hi + code).replace("%", "%%")) for code, _ in ap.mux_ansi_map[3:-2]]
            table = utils.format_table([col1, col2, col3])
            string = "ANSI colors:"
            for row in table:
                string += "\n " + " ".join(row)
            #print string
            self.msg(string)
            self.msg("{{X : black. {{\ : return, {{- : tab, {{_ : space, {{* : invert")
            self.msg("To combine background and foreground, add background marker last, e.g. {{r{{[b.")

        elif self.args.startswith("x"):
            # show xterm256 table
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ir in range(6):
                for ig in range(6):
                    for ib in range(6):
                        # foreground table
                        table[ir].append("{%i%i%i%s{n" % (ir, ig, ib, "{{%i%i%i" % (ir, ig, ib)))
                        # background table
                        table[6+ir].append("{[%i%i%i{%i%i%i%s{n" % (ir, ig, ib,
                                                            5 - ir, 5 - ig, 5 - ib,
                                                        "{{[%i%i%i" % (ir, ig, ib)))
            table = self.table_format(table)
            string = "Xterm256 colors (if not all hues show, your client might not report that it can handle xterm256):"
            for row in table:
                string += "\n" + "".join(row)
            self.msg(string)
            #self.msg("(e.g. %%123 and %%[123 also work)")
        else:
            # malformed input
            self.msg("Usage: @color ansi|xterm256")


class CmdQuell(MuxPlayerCommand):
    """
    Quelling permissions

    Usage:
      quell
      unquell

    Normally the permission level of the Player is used when puppeting a
    Character/Object to determine access. This command will switch the lock
    system to make use of the puppeted Object's permissions instead. This is
    useful mainly for testing.
    Hierarchical permission quelling only work downwards, thus a Player cannot
    use a higher-permission Character to escalate their permission level.
    Use the unquell command to revert back to normal operation.
    """

    key = "@quell"
    aliases = ["@unquell"]
    locks = "cmd:all()"
    help_category = "General"

    def _recache_locks(self, player):
        "Helper method to reset the lockhandler on an already puppeted object"
        if self.sessid:
            char = player.get_puppet(self.sessid)
            if char:
                # we are already puppeting an object. We need to reset
                # the lock caches (otherwise the superuser status change
                # won't be visible until repuppet)
                char.locks.reset()
        player.locks.reset()

    def func(self):
        "Perform the command"
        player = self.player
        permstr = player.is_superuser and " (superuser)" or " (%s)" % (", ".join(player.permissions.all()))
        if self.cmdstring == '@unquell':
            if not player.attributes.get('_quell'):
                self.msg("Already using normal Player permissions%s." % permstr)
            else:
                player.attributes.remove('_quell')
                self.msg("Player permissions%s restored." % permstr)
        else:
            if player.attributes.get('_quell'):
                self.msg("Already quelling Player%s permissions." % permstr)
                return
            player.attributes.add('_quell', True)
            puppet = player.get_puppet(self.sessid)
            if puppet:
                cpermstr = " (%s)" % ", ".join(puppet.permissions.all())
                cpermstr = "Quelling to current puppet's permissions%s." % cpermstr
                cpermstr += "\n(Note: If this is higher than Player permissions%s, the lowest of the two will be used.)" % permstr
                cpermstr += "\nUse @unquell to return to normal permission usage."
                self.msg(cpermstr)
            else:
                self.msg("Quelling Player permissions%s. Use @unquell to get them back." % permstr)
        self._recache_locks(player)

