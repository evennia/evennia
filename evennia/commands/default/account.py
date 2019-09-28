"""
Account (OOC) commands. These are stored on the Account object
and self.caller is thus always an Account, not an Object/Character.

These commands go in the AccountCmdset and are accessible also
when puppeting a Character (although with lower priority)

These commands use the account_caller property which tells the command
parent (MuxCommand, usually) to setup caller correctly. They use
self.account to make sure to always use the account object rather than
self.caller (which change depending on the level you are calling from)
The property self.character can be used to access the character when
these commands are triggered with a connected character (such as the
case of the `ooc` command), it is None if we are OOC.

Note that under MULTISESSION_MODE > 2, Account commands should use
self.msg() and similar methods to reroute returns to the correct
method. Otherwise all text will be returned to all connected sessions.

"""
import time
from codecs import lookup as codecs_lookup
from django.conf import settings
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import utils, create, logger, search

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS
_MULTISESSION_MODE = settings.MULTISESSION_MODE

# limit symbol import for API
__all__ = (
    "CmdOOCLook",
    "CmdIC",
    "CmdOOC",
    "CmdPassword",
    "CmdQuit",
    "CmdCharCreate",
    "CmdOption",
    "CmdSessions",
    "CmdWho",
    "CmdColorTest",
    "CmdQuell",
    "CmdCharDelete",
    "CmdStyle",
)


class MuxAccountLookCommand(COMMAND_DEFAULT_CLASS):
    """
    Custom parent (only) parsing for OOC looking, sets a "playable"
    property on the command based on the parsing.

    """

    def parse(self):
        """Custom parsing"""

        super().parse()

        if _MULTISESSION_MODE < 2:
            # only one character allowed - not used in this mode
            self.playable = None
            return

        playable = self.account.db._playable_characters
        if playable is not None:
            # clean up list if character object was deleted in between
            if None in playable:
                playable = [character for character in playable if character]
                self.account.db._playable_characters = playable
        # store playable property
        if self.args:
            self.playable = dict((utils.to_str(char.key.lower()), char) for char in playable).get(
                self.args.lower(), None
            )
        else:
            self.playable = playable


# Obs - these are all intended to be stored on the Account, and as such,
# use self.account instead of self.caller, just to be sure. Also self.msg()
# is used to make sure returns go to the right session

# note that this is inheriting from MuxAccountLookCommand,
# and has the .playable property.
class CmdOOCLook(MuxAccountLookCommand):
    """
    look while out-of-character

    Usage:
      look

    Look in the ooc state.
    """

    # This is an OOC version of the look command. Since a
    # Account doesn't have an in-game existence, there is no
    # concept of location or "self". If we are controlling
    # a character, pass control over to normal look.

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """implement the ooc look command"""

        if _MULTISESSION_MODE < 2:
            # only one character allowed
            self.msg("You are out-of-character (OOC).\nUse |wic|n to get back into the game.")
            return

        # call on-account look helper method
        self.msg(self.account.at_look(target=self.playable, session=self.session))


class CmdCharCreate(COMMAND_DEFAULT_CLASS):
    """
    create a new character

    Usage:
      charcreate <charname> [= desc]

    Create a new character, optionally giving it a description. You
    may use upper-case letters in the name - you will nevertheless
    always be able to access your character using lower-case letters
    if you want.
    """

    key = "charcreate"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """create the new character"""
        account = self.account
        if not self.args:
            self.msg("Usage: charcreate <charname> [= description]")
            return
        key = self.lhs
        desc = self.rhs

        charmax = _MAX_NR_CHARACTERS

        if not account.is_superuser and (
            account.db._playable_characters and len(account.db._playable_characters) >= charmax
        ):
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
        permissions = settings.PERMISSION_ACCOUNT_DEFAULT
        new_character = create.create_object(
            typeclass, key=key, location=start_location, home=default_home, permissions=permissions
        )
        # only allow creator (and developers) to puppet this char
        new_character.locks.add(
            "puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer);delete:id(%i) or perm(Admin)"
            % (new_character.id, account.id, account.id)
        )
        account.db._playable_characters.append(new_character)
        if desc:
            new_character.db.desc = desc
        elif not new_character.db.desc:
            new_character.db.desc = "This is a character."
        self.msg(
            "Created new character %s. Use |wic %s|n to enter the game as this character."
            % (new_character.key, new_character.key)
        )
        logger.log_sec(
            "Character Created: %s (Caller: %s, IP: %s)."
            % (new_character, account, self.session.address)
        )


class CmdCharDelete(COMMAND_DEFAULT_CLASS):
    """
    delete a character - this cannot be undone!

    Usage:
        chardelete <charname>

    Permanently deletes one of your characters.
    """

    key = "chardelete"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """delete the character"""
        account = self.account

        if not self.args:
            self.msg("Usage: chardelete <charactername>")
            return

        # use the playable_characters list to search
        match = [
            char
            for char in utils.make_iter(account.db._playable_characters)
            if char.key.lower() == self.args.lower()
        ]
        if not match:
            self.msg("You have no such character to delete.")
            return
        elif len(match) > 1:
            self.msg(
                "Aborting - there are two characters with the same name. Ask an admin to delete the right one."
            )
            return
        else:  # one match
            from evennia.utils.evmenu import get_input

            def _callback(caller, callback_prompt, result):
                if result.lower() == "yes":
                    # only take action
                    delobj = caller.ndb._char_to_delete
                    key = delobj.key
                    caller.db._playable_characters = [
                        pc for pc in caller.db._playable_characters if pc != delobj
                    ]
                    delobj.delete()
                    self.msg("Character '%s' was permanently deleted." % key)
                    logger.log_sec(
                        "Character Deleted: %s (Caller: %s, IP: %s)."
                        % (key, account, self.session.address)
                    )
                else:
                    self.msg("Deletion was aborted.")
                del caller.ndb._char_to_delete

            match = match[0]
            account.ndb._char_to_delete = match

            # Return if caller has no permission to delete this
            if not match.access(account, "delete"):
                self.msg("You do not have permission to delete this character.")
                return

            prompt = (
                "|rThis will permanently destroy '%s'. This cannot be undone.|n Continue yes/[no]?"
            )
            get_input(account, prompt % match.key, _callback)


class CmdIC(COMMAND_DEFAULT_CLASS):
    """
    control an object you have permission to puppet

    Usage:
      ic <character>

    Go in-character (IC) as a given Character.

    This will attempt to "become" a different object assuming you have
    the right to do so. Note that it's the ACCOUNT character that puppets
    characters/objects and which needs to have the correct permission!

    You cannot become an object that is already controlled by another
    account. In principle <character> can be any in-game object as long
    as you the account have access right to puppet it.
    """

    key = "ic"
    # lock must be all() for different puppeted objects to access it.
    locks = "cmd:all()"
    aliases = "puppet"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """
        Main puppet method
        """
        account = self.account
        session = self.session

        new_character = None
        if not self.args:
            new_character = account.db._last_puppet
            if not new_character:
                self.msg("Usage: ic <character>")
                return
        if not new_character:
            # search for a matching character
            new_character = [
                char for char in search.object_search(self.args) if char.access(account, "puppet")
            ]
            if not new_character:
                self.msg("That is not a valid character choice.")
                return
            if len(new_character) > 1:
                self.msg(
                    "Multiple targets with the same name:\n %s"
                    % ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in new_character)
                )
                return
            else:
                new_character = new_character[0]
        try:
            account.puppet_object(session, new_character)
            account.db._last_puppet = new_character
            logger.log_sec(
                "Puppet Success: (Caller: %s, Target: %s, IP: %s)."
                % (account, new_character, self.session.address)
            )
        except RuntimeError as exc:
            self.msg("|rYou cannot become |C%s|n: %s" % (new_character.name, exc))
            logger.log_sec(
                "Puppet Failed: %s (Caller: %s, Target: %s, IP: %s)."
                % (exc, account, new_character, self.session.address)
            )


# note that this is inheriting from MuxAccountLookCommand,
# and as such has the .playable property.
class CmdOOC(MuxAccountLookCommand):
    """
    stop puppeting and go ooc

    Usage:
      ooc

    Go out-of-character (OOC).

    This will leave your current character and put you in a incorporeal OOC state.
    """

    key = "ooc"
    locks = "cmd:pperm(Player)"
    aliases = "unpuppet"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """Implement function"""

        account = self.account
        session = self.session

        old_char = account.get_puppet(session)
        if not old_char:
            string = "You are already OOC."
            self.msg(string)
            return

        account.db._last_puppet = old_char

        # disconnect
        try:
            account.unpuppet_object(session)
            self.msg("\n|GYou go OOC.|n\n")

            if _MULTISESSION_MODE < 2:
                # only one character allowed
                self.msg("You are out-of-character (OOC).\nUse |wic|n to get back into the game.")
                return

            self.msg(account.at_look(target=self.playable, session=session))

        except RuntimeError as exc:
            self.msg("|rCould not unpuppet from |c%s|n: %s" % (old_char, exc))


class CmdSessions(COMMAND_DEFAULT_CLASS):
    """
    check your connected session(s)

    Usage:
      sessions

    Lists the sessions currently connected to your account.

    """

    key = "sessions"
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """Implement function"""
        account = self.account
        sessions = account.sessions.all()
        table = self.styled_table(
            "|wsessid", "|wprotocol", "|whost", "|wpuppet/character", "|wlocation"
        )
        for sess in sorted(sessions, key=lambda x: x.sessid):
            char = account.get_puppet(sess)
            table.add_row(
                str(sess.sessid),
                str(sess.protocol_key),
                isinstance(sess.address, tuple) and sess.address[0] or sess.address,
                char and str(char) or "None",
                char and str(char.location) or "N/A",
            )
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
    account_caller = True

    def func(self):
        """
        Get all connected accounts by polling session.
        """

        account = self.account
        session_list = SESSIONS.get_sessions()

        session_list = sorted(session_list, key=lambda o: o.account.key)

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = account.check_permstring("Developer") or account.check_permstring(
                "Admins"
            )

        naccounts = SESSIONS.account_count()
        if show_session_data:
            # privileged info
            table = self.styled_table(
                "|wAccount Name",
                "|wOn for",
                "|wIdle",
                "|wPuppeting",
                "|wRoom",
                "|wCmds",
                "|wProtocol",
                "|wHost",
            )
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                account = session.get_account()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "None"
                table.add_row(
                    utils.crop(account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                    utils.crop(puppet.get_display_name(account) if puppet else "None", width=25),
                    utils.crop(location, width=25),
                    session.cmd_total,
                    session.protocol_key,
                    isinstance(session.address, tuple) and session.address[0] or session.address,
                )
        else:
            # unprivileged
            table = self.styled_table("|wAccount name", "|wOn for", "|wIdle")
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                account = session.get_account()
                table.add_row(
                    utils.crop(account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                )
        is_one = naccounts == 1
        self.msg(
            "|wAccounts:|n\n%s\n%s unique account%s logged in."
            % (table, "One" if is_one else naccounts, "" if is_one else "s")
        )


class CmdOption(COMMAND_DEFAULT_CLASS):
    """
    Set an account option

    Usage:
      option[/save] [name = value]

    Switches:
      save - Save the current option settings for future logins.
      clear - Clear the saved options.

    This command allows for viewing and setting client interface
    settings. Note that saved options may not be able to be used if
    later connecting with a client with different capabilities.


    """

    key = "option"
    aliases = "options"
    switch_options = ("save", "clear")
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

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
                self.msg("|gSaved all options. Use option/clear to remove.|n")
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
                    options["SCREENWIDTH"] = "  \n".join(
                        "%s : %s" % (screenid, size)
                        for screenid, size in options["SCREENWIDTH"].items()
                    )
            if "SCREENHEIGHT" in options:
                if len(options["SCREENHEIGHT"]) == 1:
                    options["SCREENHEIGHT"] = options["SCREENHEIGHT"][0]
                else:
                    options["SCREENHEIGHT"] = "  \n".join(
                        "%s : %s" % (screenid, size)
                        for screenid, size in options["SCREENHEIGHT"].items()
                    )
            options.pop("TTYPE", None)

            header = ("Name", "Value", "Saved") if saved_options else ("Name", "Value")
            table = self.styled_table(*header)
            for key in sorted(options):
                row = [key, options[key]]
                if saved_options:
                    saved = " |YYes|n" if key in saved_options else ""
                    changed = (
                        "|y*|n" if key in saved_options and flags[key] != saved_options[key] else ""
                    )
                    row.append("%s%s" % (saved, changed))
                table.add_row(*row)
            self.msg("|wClient settings (%s):|n\n%s|n" % (self.session.protocol_key, table))

            return

        if not self.rhs:
            self.msg("Usage: option [name = [value]]")
            return

        # Try to assign new values

        def validate_encoding(new_encoding):
            # helper: change encoding
            try:
                codecs_lookup(new_encoding)
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
                if old_val == new_val:
                    self.msg("Option |w%s|n was kept as '|w%s|n'." % (new_name, old_val))
                else:
                    flags[new_name] = new_val
                    self.msg(
                        "Option |w%s|n was changed from '|w%s|n' to '|w%s|n'."
                        % (new_name, old_val, new_val)
                    )
                return {new_name: new_val}
            except Exception as err:
                self.msg("|rCould not set option |w%s|r:|n %s" % (new_name, err))
                return False

        validators = {
            "ANSI": validate_bool,
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
            "INPUTDEBUG": validate_bool,
            "FORCEDENDLINE": validate_bool,
        }

        name = self.lhs.upper()
        val = self.rhs.strip()
        optiondict = False
        if val and name in validators:
            optiondict = update(name, val, validators[name])
        else:
            self.msg("|rNo option named '|w%s|r'." % name)
        if optiondict:
            # a valid setting
            if "save" in self.switches:
                # save this option only
                saved_options = self.account.attributes.get("_saved_protocol_flags", default={})
                saved_options.update(optiondict)
                self.account.attributes.add("_saved_protocol_flags", saved_options)
                for key in optiondict:
                    self.msg("|gSaved option %s.|n" % key)
            if "clear" in self.switches:
                # clear this save
                for key in optiondict:
                    self.account.attributes.get("_saved_protocol_flags", {}).pop(key, None)
                    self.msg("|gCleared saved %s." % key)
            self.session.update_flags(**optiondict)


class CmdPassword(COMMAND_DEFAULT_CLASS):
    """
    change your password

    Usage:
      password <old password> = <new password>

    Changes your password. Make sure to pick a safe one.
    """

    key = "password"
    locks = "cmd:pperm(Player)"

    # this is used by the parent
    account_caller = True

    def func(self):
        """hook function."""

        account = self.account
        if not self.rhs:
            self.msg("Usage: password <oldpass> = <newpass>")
            return
        oldpass = self.lhslist[0]  # Both of these are
        newpass = self.rhslist[0]  # already stripped by parse()

        # Validate password
        validated, error = account.validate_password(newpass)

        if not account.check_password(oldpass):
            self.msg("The specified old password isn't correct.")
        elif not validated:
            errors = [e for suberror in error.messages for e in error.messages]
            string = "\n".join(errors)
            self.msg(string)
        else:
            account.set_password(newpass)
            account.save()
            self.msg("Password changed.")
            logger.log_sec(
                "Password Changed: %s (Caller: %s, IP: %s)."
                % (account, account, self.session.address)
            )


class CmdQuit(COMMAND_DEFAULT_CLASS):
    """
    quit the game

    Usage:
      quit

    Switch:
      all - disconnect all connected sessions

    Gracefully disconnect your current session from the
    game. Use the /all switch to disconnect from all sessions.
    """

    key = "quit"
    switch_options = ("all",)
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    def func(self):
        """hook function"""
        account = self.account

        if "all" in self.switches:
            account.msg(
                "|RQuitting|n all sessions. Hope to see you soon again.", session=self.session
            )
            reason = "quit/all"
            for session in account.sessions.all():
                account.disconnect_session_from_account(session, reason)
        else:
            nsess = len(account.sessions.all())
            reason = "quit"
            if nsess == 2:
                account.msg("|RQuitting|n. One session is still connected.", session=self.session)
            elif nsess > 2:
                account.msg(
                    "|RQuitting|n. %i sessions are still connected." % (nsess - 1),
                    session=self.session,
                )
            else:
                # we are quitting the last available session
                account.msg("|RQuitting|n. Hope to see you again, soon.", session=self.session)
            account.disconnect_session_from_account(self.session, reason)


class CmdColorTest(COMMAND_DEFAULT_CLASS):
    """
    testing which colors your client support

    Usage:
      color ansi||xterm256

    Prints a color map along with in-mud color codes to use to produce
    them.  It also tests what is supported in your client. Choices are
    16-color ansi (supported in most muds) or the 256-color xterm256
    standard. No checking is done to determine your client supports
    color - if not you will see rubbish appear.
    """

    key = "color"
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    # the slices of the ANSI_PARSER lists to use for retrieving the
    # relevant color tags to display. Replace if using another schema.
    # This command can only show one set of markup.
    slice_bright_fg = slice(7, 15)  # from ANSI_PARSER.ansi_map
    slice_dark_fg = slice(15, 23)  # from ANSI_PARSER.ansi_map
    slice_dark_bg = slice(-8, None)  # from ANSI_PARSER.ansi_map
    slice_bright_bg = slice(None, None)  # from ANSI_PARSER.ansi_xterm256_bright_bg_map

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
            ftable.append(
                [
                    str(col[irow]).ljust(max_widths[icol]) + " " * extra_space
                    for icol, col in enumerate(table)
                ]
            )
        return ftable

    def func(self):
        """Show color tables"""

        if self.args.startswith("a"):
            # show ansi 16-color table
            from evennia.utils import ansi

            ap = ansi.ANSI_PARSER
            # ansi colors
            # show all ansi color-related codes
            bright_fg = [
                "%s%s|n" % (code, code.replace("|", "||"))
                for code, _ in ap.ansi_map[self.slice_bright_fg]
            ]
            dark_fg = [
                "%s%s|n" % (code, code.replace("|", "||"))
                for code, _ in ap.ansi_map[self.slice_dark_fg]
            ]
            dark_bg = [
                "%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                for code, _ in ap.ansi_map[self.slice_dark_bg]
            ]
            bright_bg = [
                "%s%s|n" % (code.replace("\\", ""), code.replace("|", "||").replace("\\", ""))
                for code, _ in ap.ansi_xterm256_bright_bg_map[self.slice_bright_bg]
            ]
            dark_fg.extend(["" for _ in range(len(bright_fg) - len(dark_fg))])
            table = utils.format_table([bright_fg, dark_fg, bright_bg, dark_bg])
            string = "ANSI colors:"
            for row in table:
                string += "\n " + " ".join(row)
            self.msg(string)
            self.msg(
                "||X : black. ||/ : return, ||- : tab, ||_ : space, ||* : invert, ||u : underline\n"
                "To combine background and foreground, add background marker last, e.g. ||r||[B.\n"
                "Note: bright backgrounds like ||[r requires your client handling Xterm256 colors."
            )

        elif self.args.startswith("x"):
            # show xterm256 table
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ir in range(6):
                for ig in range(6):
                    for ib in range(6):
                        # foreground table
                        table[ir].append("|%i%i%i%s|n" % (ir, ig, ib, "||%i%i%i" % (ir, ig, ib)))
                        # background table
                        table[6 + ir].append(
                            "|%i%i%i|[%i%i%i%s|n"
                            % (5 - ir, 5 - ig, 5 - ib, ir, ig, ib, "||[%i%i%i" % (ir, ig, ib))
                        )
            table = self.table_format(table)
            string = "Xterm256 colors (if not all hues show, your client might not report that it can handle xterm256):"
            string += "\n" + "\n".join("".join(row) for row in table)
            table = [[], [], [], [], [], [], [], [], [], [], [], []]
            for ibatch in range(4):
                for igray in range(6):
                    letter = chr(97 + (ibatch * 6 + igray))
                    inverse = chr(122 - (ibatch * 6 + igray))
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
            self.msg("Usage: color ansi||xterm256")


class CmdQuell(COMMAND_DEFAULT_CLASS):
    """
    use character's permissions instead of account's

    Usage:
      quell
      unquell

    Normally the permission level of the Account is used when puppeting a
    Character/Object to determine access. This command will switch the lock
    system to make use of the puppeted Object's permissions instead. This is
    useful mainly for testing.
    Hierarchical permission quelling only work downwards, thus an Account cannot
    use a higher-permission Character to escalate their permission level.
    Use the unquell command to revert back to normal operation.
    """

    key = "quell"
    aliases = ["unquell"]
    locks = "cmd:pperm(Player)"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def _recache_locks(self, account):
        """Helper method to reset the lockhandler on an already puppeted object"""
        if self.session:
            char = self.session.puppet
            if char:
                # we are already puppeting an object. We need to reset
                # the lock caches (otherwise the superuser status change
                # won't be visible until repuppet)
                char.locks.reset()
        account.locks.reset()

    def func(self):
        """Perform the command"""
        account = self.account
        permstr = (
            account.is_superuser
            and " (superuser)"
            or "(%s)" % (", ".join(account.permissions.all()))
        )
        if self.cmdstring in ("unquell", "unquell"):
            if not account.attributes.get("_quell"):
                self.msg("Already using normal Account permissions %s." % permstr)
            else:
                account.attributes.remove("_quell")
                self.msg("Account permissions %s restored." % permstr)
        else:
            if account.attributes.get("_quell"):
                self.msg("Already quelling Account %s permissions." % permstr)
                return
            account.attributes.add("_quell", True)
            puppet = self.session.puppet
            if puppet:
                cpermstr = "(%s)" % ", ".join(puppet.permissions.all())
                cpermstr = "Quelling to current puppet's permissions %s." % cpermstr
                cpermstr += (
                    "\n(Note: If this is higher than Account permissions %s,"
                    " the lowest of the two will be used.)" % permstr
                )
                cpermstr += "\nUse unquell to return to normal permission usage."
                self.msg(cpermstr)
            else:
                self.msg("Quelling Account permissions%s. Use unquell to get them back." % permstr)
        self._recache_locks(account)


class CmdStyle(COMMAND_DEFAULT_CLASS):
    """
    In-game style options

    Usage:
      style
      style <option> = <value>

    Configure stylings for in-game display elements like table borders, help
    entriest etc. Use without arguments to see all available options.

    """

    key = "style"
    switch_options = ["clear"]

    def func(self):
        if not self.args:
            self.list_styles()
            return
        self.set()

    def list_styles(self):
        table = self.styled_table("Option", "Description", "Type", "Value", width=78)
        for op_key in self.account.options.options_dict.keys():
            op_found = self.account.options.get(op_key, return_obj=True)
            table.add_row(
                op_key, op_found.description, op_found.__class__.__name__, op_found.display()
            )
        self.msg(str(table))

    def set(self):
        try:
            result = self.account.options.set(self.lhs, self.rhs)
        except ValueError as e:
            self.msg(str(e))
            return
        self.msg("Style %s set to %s" % (self.lhs, result))
