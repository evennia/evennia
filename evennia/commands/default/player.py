"""
Player (OOC) commands. These are stored on the Player object
and self.caller is thus always a Player, not an Object/Character.

These commands go in the PlayerCmdset and are accessible also
when puppeting a Character (although with lower priority)

These commands use the player_caller property which tells the command
parent (MuxCommand, usually) to setup caller correctly. They use
self.player to make sure to always use the player object rather than
self.caller (which change depending on the level you are calling from)
The property self.character can be used to access the character when
these commands are triggered with a connected character (such as the
case of the @ooc command), it is None if we are OOC.

Note that under MULTISESSION_MODE > 2, Player commands should use
self.msg() and similar methods to reroute returns to the correct
method. Otherwise all text will be returned to all connected sessions.

"""
from builtins import range

import time
from django.conf import settings
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import utils, create, search, evtable

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS
_MULTISESSION_MODE = settings.MULTISESSION_MODE

# limit symbol import for API
__all__ = ("CmdOOCLook", "CmdIC", "CmdOOC", "CmdPassword", "CmdQuit",
           "CmdCharCreate", "CmdOption", "CmdSessions", "CmdWho",
           "CmdColorTest", "CmdQuell")


class MuxPlayerLookCommand(COMMAND_DEFAULT_CLASS):
    """
    Custom parent (only) parsing for OOC looking, sets a "playable"
    property on the command based on the parsing.

    """

    def parse(self):
        """Custom parsing"""

        super(MuxPlayerLookCommand, self).parse()

        if _MULTISESSION_MODE < 2:
            # only one character allowed - not used in this mode
            self.playable = None
            return

        playable = self.player.db._playable_characters
        if playable is not None:
            # clean up list if character object was deleted in between
            if None in playable:
                playable = [character for character in playable if character]
                self.player.db._playable_characters = playable
        # store playable property
        if self.args:
            self.playable = dict((utils.to_str(char.key.lower()), char)
                                 for char in playable).get(self.args.lower(), None)
        else:
            self.playable = playable


# Obs - these are all intended to be stored on the Player, and as such,
# use self.player instead of self.caller, just to be sure. Also self.msg()
# is used to make sure returns go to the right session

# note that this is inheriting from MuxPlayerLookCommand,
# and has the .playable property.
class CmdOOCLook(MuxPlayerLookCommand):
    """
    look while out-of-character

    Usage:
      look

    Look in the ooc state.
    """

    # This is an OOC version of the look command. Since a
    # Player doesn't have an in-game existence, there is no
    # concept of location or "self". If we are controlling
    # a character, pass control over to normal look.

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def func(self):
        """implement the ooc look command"""

        if _MULTISESSION_MODE < 2:
            # only one character allowed
            self.msg("You are out-of-character (OOC).\nUse |w@ic|n to get back into the game.")
            return

        # call on-player look helper method
        self.msg(self.player.at_look(target=self.playable, session=self.session))


class CmdCharCreate(COMMAND_DEFAULT_CLASS):
    """
    create a new character

    Usage:
      @charcreate <charname> [= desc]

    Create a new character, optionally giving it a description. You
    may use upper-case letters in the name - you will nevertheless
    always be able to access your character using lower-case letters
    if you want.
    """
    key = "@charcreate"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def func(self):
        """create the new character"""
        player = self.player
        if not self.args:
            self.msg("Usage: @charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs

        charmax = _MAX_NR_CHARACTERS if _MULTISESSION_MODE > 1 else 1

        if not player.is_superuser and \
                (player.db._playable_characters and
                 len(player.db._playable_characters) >= charmax):
            self.msg("You may only create a maximum of %i characters." % charmax)
            return
        from evennia.objects.models import ObjectDB
        typeclass = settings.BASE_CHARACTER_TYPECLASS

        if ObjectDB.objects.filter(db_typeclass_path=typeclass, db_key__iexact=key):
            # check if this Character already exists. Note that we are only
            # searching the base character typeclass here, not any child
            # classes.
            self.msg("|rA character named '|w%s|r' already exists.|n" % key)
            return

        # create the character
        start_location = ObjectDB.objects.get_id(settings.START_LOCATION)
        default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
        permissions = settings.PERMISSION_PLAYER_DEFAULT
        new_character = create.create_object(typeclass, key=key,
                                             location=start_location,
                                             home=default_home,
                                             permissions=permissions)
        # only allow creator (and developers) to puppet this char
        new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer)" %
                                (new_character.id, player.id))
        player.db._playable_characters.append(new_character)
        if desc:
            new_character.db.desc = desc
        elif not new_character.db.desc:
            new_character.db.desc = "This is a Player."
        self.msg("Created new character %s. Use |w@ic %s|n to enter the game as this character."
                 % (new_character.key, new_character.key))


class CmdCharDelete(COMMAND_DEFAULT_CLASS):
    """
    delete a character - this cannot be undone!

    Usage:
        @chardelete <charname>

    Permanently deletes one of your characters.
    """
    key = "@chardelete"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """delete the character"""
        player = self.player

        if not self.args:
            self.msg("Usage: @chardelete <charactername>")
            return

        # use the playable_characters list to search
        match = [char for char in utils.make_iter(player.db._playable_characters)
                 if char.key.lower() == self.args.lower()]
        if not match:
            self.msg("You have no such character to delete.")
            return
        elif len(match) > 1:
            self.msg("Aborting - there are two characters with the same name. Ask an admin to delete the right one.")
            return
        else:  # one match
            from evennia.utils.evmenu import get_input

            def _callback(caller, callback_prompt, result):
                if result.lower() == "yes":
                    # only take action
                    delobj = caller.ndb._char_to_delete
                    key = delobj.key
                    caller.db._playable_characters = [pc for pc in caller.db._playable_characters if pc != delobj]
                    delobj.delete()
                    self.msg("Character '%s' was permanently deleted." % key)
                else:
                    self.msg("Deletion was aborted.")
                del caller.ndb._char_to_delete

            match = match[0]
            player.ndb._char_to_delete = match
            prompt = "|rThis will permanently destroy '%s'. This cannot be undone.|n Continue yes/[no]?"
            get_input(player, prompt % match.key, _callback)


class CmdIC(COMMAND_DEFAULT_CLASS):
    """
    control an object you have permission to puppet

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
    # lock must be all() for different puppeted objects to access it.
    locks = "cmd:all()"
    aliases = "@puppet"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def func(self):
        """
        Main puppet method
        """
        player = self.player
        session = self.session

        new_character = None
        if not self.args:
            new_character = player.db._last_puppet
            if not new_character:
                self.msg("Usage: @ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = [char for char in search.object_search(self.args) if char.access(player, "puppet")]
            if not new_character:
                self.msg("That is not a valid character choice.")
                return
            if len(new_character) > 1:
                self.msg("Multiple targets with the same name:\n %s"
                         % ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in new_character))
                return
            else:
                new_character = new_character[0]
        try:
            player.puppet_object(session, new_character)
            player.db._last_puppet = new_character
        except RuntimeError as exc:
            self.msg("|rYou cannot become |C%s|n: %s" % (new_character.name, exc))


# note that this is inheriting from MuxPlayerLookCommand,
# and as such has the .playable property.
class CmdOOC(MuxPlayerLookCommand):
    """
    stop puppeting and go ooc

    Usage:
      @ooc

    Go out-of-character (OOC).

    This will leave your current character and put you in a incorporeal OOC state.
    """

    key = "@ooc"
    locks = "cmd:pperm(Player)"
    aliases = "@unpuppet"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def func(self):
        """Implement function"""

        player = self.player
        session = self.session

        old_char = player.get_puppet(session)
        if not old_char:
            string = "You are already OOC."
            self.msg(string)
            return

        player.db._last_puppet = old_char

        # disconnect
        try:
            player.unpuppet_object(session)
            self.msg("\n|GYou go OOC.|n\n")

            if _MULTISESSION_MODE < 2:
                # only one character allowed
                self.msg("You are out-of-character (OOC).\nUse |w@ic|n to get back into the game.")
                return

            self.msg(player.at_look(target=self.playable, session=session))

        except RuntimeError as exc:
            self.msg("|rCould not unpuppet from |c%s|n: %s" % (old_char, exc))


class CmdSessions(COMMAND_DEFAULT_CLASS):
    """
    check your connected session(s)

    Usage:
      @sessions

    Lists the sessions currently connected to your account.

    """
    key = "@sessions"
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def func(self):
        """Implement function"""
        player = self.player
        sessions = player.sessions.all()
        table = evtable.EvTable("|wsessid",
                                "|wprotocol",
                                "|whost",
                                "|wpuppet/character",
                                "|wlocation")
        for sess in sorted(sessions, key=lambda x: x.sessid):
            char = player.get_puppet(sess)
            table.add_row(str(sess.sessid), str(sess.protocol_key),
                          type(sess.address) == tuple and sess.address[0] or sess.address,
                          char and str(char) or "None",
                          char and str(char.location) or "N/A")
            self.msg("|wYour current session(s):|n\n%s" % table)


class CmdWho(COMMAND_DEFAULT_CLASS):
    """
    list who is currently online

    Usage:
      who
      doing

    Shows who is currently online. Doing is an alias that limits info
    also for those with all permissions.
    """

    key = "who"
    aliases = "doing"
    locks = "cmd:all()"

    # this is used by the parent
    player_caller = True

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
            show_session_data = player.check_permstring("Developer") or player.check_permstring("Admins")

        nplayers = (SESSIONS.player_count())
        if show_session_data:
            # privileged info
            table = evtable.EvTable("|wPlayer Name",
                                    "|wOn for",
                                    "|wIdle",
                                    "|wPuppeting",
                                    "|wRoom",
                                    "|wCmds",
                                    "|wProtocol",
                                    "|wHost")
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                player = session.get_player()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "None"
                table.add_row(utils.crop(player.name, width=25),
                              utils.time_format(delta_conn, 0),
                              utils.time_format(delta_cmd, 1),
                              utils.crop(puppet.key if puppet else "None", width=25),
                              utils.crop(location, width=25),
                              session.cmd_total,
                              session.protocol_key,
                              isinstance(session.address, tuple) and session.address[0] or session.address)
        else:
            # unprivileged
            table = evtable.EvTable("|wPlayer name", "|wOn for", "|wIdle")
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                player = session.get_player()
                table.add_row(utils.crop(player.key, width=25),
                              utils.time_format(delta_conn, 0),
                              utils.time_format(delta_cmd, 1))
        is_one = nplayers == 1
        self.msg("|wPlayers:|n\n%s\n%s unique account%s logged in."
                 % (table, "One" if is_one else nplayers, "" if is_one else "s"))


class CmdOption(COMMAND_DEFAULT_CLASS):
    """
    Set an account option

    Usage:
      @option[/save] [name = value]

    Switch:
      save - Save the current option settings for future logins.
      clear - Clear the saved options.

    This command allows for viewing and setting client interface
    settings. Note that saved options may not be able to be used if
    later connecting with a client with different capabilities.


    """
    key = "@option"
    aliases = "@options"
    locks = "cmd:all()"

    # this is used by the parent
    player_caller = True

    def func(self):
        """
        Implements the command
        """
        if self.session is None:
            return

        flags = self.session.protocol_flags

        # Display current options
        if not self.args:
            # list the option settings

            if "save" in self.switches:
                # save all options
                self.caller.db._saved_protocol_flags = flags
                self.msg("|gSaved all options. Use @option/clear to remove.|n")
            if "clear" in self.switches:
                # clear all saves
                self.caller.db._saved_protocol_flags = {}
                self.msg("|gCleared all saved options.")

            options = dict(flags)  # make a copy of the flag dict
            saved_options = dict(self.caller.attributes.get("_saved_protocol_flags", default={}))

            if "SCREENWIDTH" in options:
                if len(options["SCREENWIDTH"]) == 1:
                    options["SCREENWIDTH"] = options["SCREENWIDTH"][0]
                else:
                    options["SCREENWIDTH"] = "  \n".join("%s : %s" % (screenid, size)
                                                         for screenid, size in options["SCREENWIDTH"].iteritems())
            if "SCREENHEIGHT" in options:
                if len(options["SCREENHEIGHT"]) == 1:
                    options["SCREENHEIGHT"] = options["SCREENHEIGHT"][0]
                else:
                    options["SCREENHEIGHT"] = "  \n".join("%s : %s" % (screenid, size)
                        for screenid, size in options["SCREENHEIGHT"].iteritems())
            options.pop("TTYPE", None)

            header = ("Name", "Value", "Saved") if saved_options else ("Name", "Value")
            table = evtable.EvTable(*header)
            for key in sorted(options):
                row = [key, options[key]]
                if saved_options:
                    saved = " |YYes|n" if key in saved_options else ""
                    changed = "|y*|n" if key in saved_options and flags[key] != saved_options[key] else ""
                    row.append("%s%s" % (saved, changed))
                table.add_row(*row)
            self.msg("|wClient settings (%s):|n\n%s|n" % (self.session.protocol_key, table))

            return

        if not self.rhs:
            self.msg("Usage: @option [name = [value]]")
            return

        # Try to assign new values

        def validate_encoding(new_encoding):
            # helper: change encoding
            try:
                utils.to_str(utils.to_unicode("test-string"), encoding=new_encoding)
            except LookupError:
                raise RuntimeError("The encoding '|w%s|n' is invalid. " % new_encoding)
            return val

        def validate_size(new_size):
            return {0: int(new_size)}

        def validate_bool(new_bool):
            return True if new_bool.lower() in ("true", "on", "1") else False

        def update(new_name, new_val, validator):
            # helper: update property and report errors
            try:
                old_val = flags.get(new_name, False)
                new_val = validator(new_val)
                flags[new_name] = new_val
                self.msg("Option |w%s|n was changed from '|w%s|n' to '|w%s|n'." % (new_name, old_val, new_val))
                return {new_name: new_val}
            except Exception, err:
                self.msg("|rCould not set option |w%s|r:|n %s" % (new_name, err))
                return False

        validators = {"ANSI": validate_bool,
                      "CLIENTNAME": utils.to_str,
                      "ENCODING": validate_encoding,
                      "MCCP": validate_bool,
                      "NOGOAHEAD": validate_bool,
                      "MXP": validate_bool,
                      "NOCOLOR": validate_bool,
                      "NOPKEEPALIVE": validate_bool,
                      "OOB": validate_bool,
                      "RAW": validate_bool,
                      "SCREENHEIGHT": validate_size,
                      "SCREENWIDTH": validate_size,
                      "SCREENREADER": validate_bool,
                      "TERM": utils.to_str,
                      "UTF-8": validate_bool,
                      "XTERM256": validate_bool,
                      "INPUTDEBUG": validate_bool}

        name = self.lhs.upper()
        val = self.rhs.strip()
        optiondict = False
        if val and name in validators:
            optiondict = update(name,  val, validators[name])
        else:
            self.msg("|rNo option named '|w%s|r'." % name)
        if optiondict:
            # a valid setting
            if "save" in self.switches:
                # save this option only
                saved_options = self.player.attributes.get("_saved_protocol_flags", default={})
                saved_options.update(optiondict)
                self.player.attributes.add("_saved_protocol_flags", saved_options)
                for key in optiondict:
                    self.msg("|gSaved option %s.|n" % key)
            if "clear" in self.switches:
                # clear this save
                for key in optiondict:
                    self.player.attributes.get("_saved_protocol_flags", {}).pop(key, None)
                    self.msg("|gCleared saved %s." % key)
            self.session.update_flags(**optiondict)


class CmdPassword(COMMAND_DEFAULT_CLASS):
    """
    change your password

    Usage:
      @password <old password> = <new password>

    Changes your password. Make sure to pick a safe one.
    """
    key = "@password"
    locks = "cmd:pperm(Player)"

    # this is used by the parent
    player_caller = True

    def func(self):
        """hook function."""

        player = self.player
        if not self.rhs:
            self.msg("Usage: @password <oldpass> = <newpass>")
            return
        oldpass = self.lhslist[0]  # Both of these are
        newpass = self.rhslist[0]  # already stripped by parse()
        if not player.check_password(oldpass):
            self.msg("The specified old password isn't correct.")
        elif len(newpass) < 3:
            self.msg("Passwords must be at least three characters long.")
        else:
            player.set_password(newpass)
            player.save()
            self.msg("Password changed.")


class CmdQuit(COMMAND_DEFAULT_CLASS):
    """
    quit the game

    Usage:
      @quit

    Switch:
      all - disconnect all connected sessions

    Gracefully disconnect your current session from the
    game. Use the /all switch to disconnect from all sessions.
    """
    key = "@quit"
    locks = "cmd:all()"

    # this is used by the parent
    player_caller = True

    def func(self):
        """hook function"""
        player = self.player

        if 'all' in self.switches:
            player.msg("|RQuitting|n all sessions. Hope to see you soon again.", session=self.session)
            for session in player.sessions.all():
                player.disconnect_session_from_player(session)
        else:
            nsess = len(player.sessions.all())
            if nsess == 2:
                player.msg("|RQuitting|n. One session is still connected.", session=self.session)
            elif nsess > 2:
                player.msg("|RQuitting|n. %i sessions are still connected." % (nsess-1), session=self.session)
            else:
                # we are quitting the last available session
                player.msg("|RQuitting|n. Hope to see you again, soon.", session=self.session)
            player.disconnect_session_from_player(self.session)


class CmdColorTest(COMMAND_DEFAULT_CLASS):
    """
    testing which colors your client support

    Usage:
      @color ansi||xterm256

    Prints a color map along with in-mud color codes to use to produce
    them.  It also tests what is supported in your client. Choices are
    16-color ansi (supported in most muds) or the 256-color xterm256
    standard. No checking is done to determine your client supports
    color - if not you will see rubbish appear.
    """
    key = "@color"
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    player_caller = True

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
            ftable.append([str(col[irow]).ljust(max_widths[icol]) + " " *
                           extra_space for icol, col in enumerate(table)])
        return ftable

    def func(self):
        """Show color tables"""

        if self.args.startswith("a"):
            # show ansi 16-color table
            from evennia.utils import ansi
            ap = ansi.ANSI_PARSER
            # ansi colors
            # show all ansi color-related codes
            col1 = ["%s%s|n" % (code, code.replace("|", "||")) for code, _ in ap.ext_ansi_map[48:56]]
            col2 = ["%s%s|n" % (code, code.replace("|", "||")) for code, _ in ap.ext_ansi_map[56:64]]
            col3 = ["%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                    for code, _ in ap.ext_ansi_map[-8:]]
            col4 = ["%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                    for code, _ in ap.ansi_bright_bgs[-8:]]
            col2.extend(["" for _ in range(len(col1)-len(col2))])
            table = utils.format_table([col1, col2, col4, col3])
            string = "ANSI colors:"
            for row in table:
                string += "\n " + " ".join(row)
            self.msg(string)
            self.msg("||X : black. ||/ : return, ||- : tab, ||_ : space, ||* : invert, ||u : underline\n"
                     "To combine background and foreground, add background marker last, e.g. ||r||[B.\n"
                     "Note: bright backgrounds like ||[r requires your client handling Xterm256 colors.")

        elif self.args.startswith("x"):
            # show xterm256 table
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ir in range(6):
                for ig in range(6):
                    for ib in range(6):
                        # foreground table
                        table[ir].append("|%i%i%i%s|n" % (ir, ig, ib, "||%i%i%i" % (ir, ig, ib)))
                        # background table
                        table[6+ir].append("|%i%i%i|[%i%i%i%s|n"
                                           % (5 - ir, 5 - ig, 5 - ib, ir, ig, ib, "||[%i%i%i" % (ir, ig, ib)))
            table = self.table_format(table)
            string = "Xterm256 colors (if not all hues show, your client might not report that it can handle xterm256):"
            string += "\n" + "\n".join("".join(row) for row in table)
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ibatch in range(4):
                for igray in range(6):
                    letter = chr(97 + (ibatch*6 + igray))
                    inverse = chr(122 - (ibatch*6 + igray))
                    table[0 + igray].append("|=%s%s |n" % (letter, "||=%s" % letter))
                    table[6 + igray].append("|=%s|[=%s%s |n" % (inverse, letter, "||[=%s" % letter))
            for igray in range(6):
                # the last row (y, z) has empty columns
                if igray < 2:
                    letter = chr(121 + igray)
                    inverse = chr(98 - igray)
                    fg = "|=%s%s |n" % (letter, "||=%s" % letter)
                    bg = "|=%s|[=%s%s |n" % (inverse, letter, "||[=%s" % letter)
                else:
                    fg, bg = " ", " "
                table[0 + igray].append(fg)
                table[6 + igray].append(bg)
            table = self.table_format(table)
            string += "\n" + "\n".join("".join(row) for row in table)
            self.msg(string)
        else:
            # malformed input
            self.msg("Usage: @color ansi||xterm256")


class CmdQuell(COMMAND_DEFAULT_CLASS):
    """
    use character's permissions instead of player's

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
    locks = "cmd:pperm(Player)"
    help_category = "General"

    # this is used by the parent
    player_caller = True

    def _recache_locks(self, player):
        """Helper method to reset the lockhandler on an already puppeted object"""
        if self.session:
            char = self.session.puppet
            if char:
                # we are already puppeting an object. We need to reset
                # the lock caches (otherwise the superuser status change
                # won't be visible until repuppet)
                char.locks.reset()
        player.locks.reset()

    def func(self):
        """Perform the command"""
        player = self.player
        permstr = player.is_superuser and " (superuser)" or "(%s)" % (", ".join(player.permissions.all()))
        if self.cmdstring == '@unquell':
            if not player.attributes.get('_quell'):
                self.msg("Already using normal Player permissions %s." % permstr)
            else:
                player.attributes.remove('_quell')
                self.msg("Player permissions %s restored." % permstr)
        else:
            if player.attributes.get('_quell'):
                self.msg("Already quelling Player %s permissions." % permstr)
                return
            player.attributes.add('_quell', True)
            puppet = self.session.puppet
            if puppet:
                cpermstr = "(%s)" % ", ".join(puppet.permissions.all())
                cpermstr = "Quelling to current puppet's permissions %s." % cpermstr
                cpermstr += "\n(Note: If this is higher than Player permissions %s," \
                            " the lowest of the two will be used.)" % permstr
                cpermstr += "\nUse @unquell to return to normal permission usage."
                self.msg(cpermstr)
            else:
                self.msg("Quelling Player permissions%s. Use @unquell to get them back." % permstr)
        self._recache_locks(player)
