"""
Commands that are available from the connect screen.

"""
import datetime
import re
from codecs import lookup as codecs_lookup

from django.conf import settings

from evennia.commands.cmdhandler import CMD_LOGINSTART
from evennia.comms.models import ChannelDB
from evennia.server.sessionhandler import SESSIONS
from evennia.utils import class_from_module, create, gametime, logger, utils

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

# limit symbol import for API
__all__ = (
    "CmdUnconnectedConnect",
    "CmdUnconnectedCreate",
    "CmdUnconnectedQuit",
    "CmdUnconnectedLook",
    "CmdUnconnectedHelp",
    "CmdUnconnectedEncoding",
    "CmdUnconnectedInfo",
    "CmdUnconnectedScreenreader",
)

CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE


def create_guest_account(session):
    """
    Creates a guest account/character for this session, if one is available.

    Args:
        session (Session): the session which will use the guest account/character.

    Returns:
        GUEST_ENABLED (boolean), account (Account):
            the boolean is whether guest accounts are enabled at all.
            the Account which was created from an available guest name.
    """
    enabled = settings.GUEST_ENABLED
    address = session.address

    # Get account class
    Guest = class_from_module(settings.BASE_GUEST_TYPECLASS)

    # Get an available guest account
    # authenticate() handles its own throttling
    account, errors = Guest.authenticate(ip=address)
    if account:
        return enabled, account
    else:
        session.msg("|R%s|n" % "\n".join(errors))
        return enabled, None


def create_normal_account(session, name, password):
    """
    Creates an account with the given name and password.

    Args:
        session (Session): the session which is requesting to create an account.
        name (str): the name that the account wants to use for login.
        password (str): the password desired by this account, for login.

    Returns:
        account (Account): the account which was created from the name and password.
    """
    # Get account class
    Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

    address = session.address

    # Match account name and check password
    # authenticate() handles all its own throttling
    account, errors = Account.authenticate(
        username=name, password=password, ip=address, session=session
    )
    if not account:
        # No accountname or password match
        session.msg("|R%s|n" % "\n".join(errors))
        return None

    return account


class CmdUnconnectedConnect(COMMAND_DEFAULT_CLASS):
    """
    connect to the game

    Usage (at login screen):
      connect accountname password
      connect "account name" "pass word"

    Use the create command to first create an account before logging in.

    If you have spaces in your name, enclose it in double quotes.
    """

    key = "connect"
    aliases = ["conn", "con", "co"]
    locks = "cmd:all()"  # not really needed
    arg_regex = r"\s.*?|$"

    def func(self):
        """
        Uses the Django admin api. Note that unlogged-in commands
        have a unique position in that their func() receives
        a session object instead of a source_object like all
        other types of logged-in commands (this is because
        there is no object yet before the account has logged in)
        """
        session = self.caller
        address = session.address

        args = self.args
        # extract double quote parts
        parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no double quotes being found, or a guest login
            parts = parts[0].split(None, 1)

            # Guest login
            if len(parts) == 1 and parts[0].lower() == "guest":
                # Get Guest typeclass
                Guest = class_from_module(settings.BASE_GUEST_TYPECLASS)

                account, errors = Guest.authenticate(ip=address)
                if account:
                    session.sessionhandler.login(session, account)
                    return
                else:
                    session.msg("|R%s|n" % "\n".join(errors))
                    return

        if len(parts) != 2:
            session.msg("\n\r Usage (without <>): connect <name> <password>")
            return

        # Get account class
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        name, password = parts
        account, errors = Account.authenticate(
            username=name, password=password, ip=address, session=session
        )
        if account:
            session.sessionhandler.login(session, account)
        else:
            session.msg("|R%s|n" % "\n".join(errors))


class CmdUnconnectedCreate(COMMAND_DEFAULT_CLASS):
    """
    create a new account account

    Usage (at login screen):
      create <accountname> <password>
      create "account name" "pass word"

    This creates a new account account.

    If you have spaces in your name, enclose it in double quotes.
    """

    key = "create"
    aliases = ["cre", "cr"]
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        """Do checks and create account"""

        session = self.caller
        args = self.args.strip()

        address = session.address

        # Get account class
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        # extract double quoted parts
        parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no quotes being found
            parts = parts[0].split(None, 1)
        if len(parts) != 2:
            string = (
                "\n Usage (without <>): create <name> <password>"
                "\nIf <name> or <password> contains spaces, enclose it in double quotes."
            )
            session.msg(string)
            return

        username, password = parts

        # pre-normalize username so the user know what they get
        non_normalized_username = username
        username = Account.normalize_username(username)
        if non_normalized_username != username:
            session.msg(
                "Note: your username was normalized to strip spaces and remove characters "
                "that could be visually confusing."
            )

        # have the user verify their new account was what they intended
        answer = yield (
            f"You want to create an account '{username}' with password '{password}'."
            "\nIs this what you intended? [Y]/N?"
        )
        if answer.lower() in ("n", "no"):
            session.msg("Aborted. If your user name contains spaces, surround it by quotes.")
            return

        # everything's ok. Create the new player account.
        account, errors = Account.create(
            username=username, password=password, ip=address, session=session
        )
        if account:
            # tell the caller everything went well.
            string = "A new account '%s' was created. Welcome!"
            if " " in username:
                string += (
                    "\n\nYou can now log in with the command 'connect \"%s\" <your password>'."
                )
            else:
                string += "\n\nYou can now log with the command 'connect %s <your password>'."
            session.msg(string % (username, username))
        else:
            session.msg("|R%s|n" % "\n".join(errors))


class CmdUnconnectedQuit(COMMAND_DEFAULT_CLASS):
    """
    quit when in unlogged-in state

    Usage:
      quit

    We maintain a different version of the quit command
    here for unconnected accounts for the sake of simplicity. The logged in
    version is a bit more complicated.
    """

    key = "quit"
    aliases = ["q", "qu"]
    locks = "cmd:all()"

    def func(self):
        """Simply close the connection."""
        session = self.caller
        session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")


class CmdUnconnectedLook(COMMAND_DEFAULT_CLASS):
    """
    look when in unlogged-in state

    Usage:
      look

    This is an unconnected version of the look command for simplicity.

    This is called by the server and kicks everything in gear.
    All it does is display the connect screen.
    """

    key = CMD_LOGINSTART
    aliases = ["look", "l"]
    locks = "cmd:all()"

    def func(self):
        """Show the connect screen."""

        callables = utils.callables_from_module(CONNECTION_SCREEN_MODULE)
        if "connection_screen" in callables:
            connection_screen = callables["connection_screen"]()
        else:
            connection_screen = utils.random_string_from_module(CONNECTION_SCREEN_MODULE)
            if not connection_screen:
                connection_screen = "No connection screen found. Please contact an admin."
        self.caller.msg(connection_screen)


class CmdUnconnectedHelp(COMMAND_DEFAULT_CLASS):
    """
    get help when in unconnected-in state

    Usage:
      help

    This is an unconnected version of the help command,
    for simplicity. It shows a pane of info.
    """

    key = "help"
    aliases = ["h", "?"]
    locks = "cmd:all()"

    def func(self):
        """Shows help"""

        string = """
You are not yet logged into the game. Commands available at this point:

  |wcreate|n - create a new account
  |wconnect|n - connect with an existing account
  |wlook|n - re-show the connection screen
  |whelp|n - show this help
  |wencoding|n - change the text encoding to match your client
  |wscreenreader|n - make the server more suitable for use with screen readers
  |wquit|n - abort the connection

First create an account e.g. with |wcreate Anna c67jHL8p|n
(If you have spaces in your name, use double quotes: |wcreate "Anna the Barbarian" c67jHL8p|n
Next you can connect to the game: |wconnect Anna c67jHL8p|n

You can use the |wlook|n command if you want to see the connect screen again.

"""

        if settings.STAFF_CONTACT_EMAIL:
            string += "For support, please contact: %s" % settings.STAFF_CONTACT_EMAIL
        self.caller.msg(string)


class CmdUnconnectedEncoding(COMMAND_DEFAULT_CLASS):
    """
    set which text encoding to use in unconnected-in state

    Usage:
      encoding/switches [<encoding>]

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

    key = "encoding"
    aliases = "encode"
    locks = "cmd:all()"

    def func(self):
        """
        Sets the encoding.
        """

        if self.session is None:
            return

        sync = False
        if "clear" in self.switches:
            # remove customization
            old_encoding = self.session.protocol_flags.get("ENCODING", None)
            if old_encoding:
                string = "Your custom text encoding ('%s') was cleared." % old_encoding
            else:
                string = "No custom encoding was set."
            self.session.protocol_flags["ENCODING"] = "utf-8"
            sync = True
        elif not self.args:
            # just list the encodings supported
            pencoding = self.session.protocol_flags.get("ENCODING", None)
            string = ""
            if pencoding:
                string += (
                    "Default encoding: |g%s|n (change with |wencoding <encoding>|n)" % pencoding
                )
            encodings = settings.ENCODINGS
            if encodings:
                string += (
                    "\nServer's alternative encodings (tested in this order):\n   |g%s|n"
                    % ", ".join(encodings)
                )
            if not string:
                string = "No encodings found."
        else:
            # change encoding
            old_encoding = self.session.protocol_flags.get("ENCODING", None)
            encoding = self.args
            try:
                codecs_lookup(encoding)
            except LookupError:
                string = (
                    "|rThe encoding '|w%s|r' is invalid. Keeping the previous encoding '|w%s|r'.|n"
                    % (encoding, old_encoding)
                )
            else:
                self.session.protocol_flags["ENCODING"] = encoding
                string = "Your custom text encoding was changed from '|w%s|n' to '|w%s|n'." % (
                    old_encoding,
                    encoding,
                )
                sync = True
        if sync:
            self.session.sessionhandler.session_portal_sync(self.session)
        self.caller.msg(string.strip())


class CmdUnconnectedScreenreader(COMMAND_DEFAULT_CLASS):
    """
    Activate screenreader mode.

    Usage:
        screenreader

    Used to flip screenreader mode on and off before logging in (when
    logged in, use option screenreader on).
    """

    key = "screenreader"

    def func(self):
        """Flips screenreader setting."""
        new_setting = not self.session.protocol_flags.get("SCREENREADER", False)
        self.session.protocol_flags["SCREENREADER"] = new_setting
        string = "Screenreader mode turned |w%s|n." % ("on" if new_setting else "off")
        self.caller.msg(string)
        self.session.sessionhandler.session_portal_sync(self.session)


class CmdUnconnectedInfo(COMMAND_DEFAULT_CLASS):
    """
    Provides MUDINFO output, so that Evennia games can be added to Mudconnector
    and Mudstats.  Sadly, the MUDINFO specification seems to have dropped off the
    face of the net, but it is still used by some crawlers.  This implementation
    was created by looking at the MUDINFO implementation in MUX2, TinyMUSH, Rhost,
    and PennMUSH.
    """

    key = "info"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg(
            "## BEGIN INFO 1.1\nName: %s\nUptime: %s\nConnected: %d\nVersion: Evennia %s\n## END"
            " INFO"
            % (
                settings.SERVERNAME,
                datetime.datetime.fromtimestamp(gametime.SERVER_START_TIME).ctime(),
                SESSIONS.account_count(),
                utils.get_evennia_version(),
            )
        )


def _create_account(session, accountname, password, permissions, typeclass=None, email=None):
    """
    Helper function, creates an account of the specified typeclass.
    """
    try:
        new_account = create.create_account(
            accountname, email, password, permissions=permissions, typeclass=typeclass
        )

    except Exception as e:
        session.msg(
            "There was an error creating the Account:\n%s\n If this problem persists, contact an"
            " admin." % e
        )
        logger.log_trace()
        return False

    # This needs to be set so the engine knows this account is
    # logging in for the first time. (so it knows to call the right
    # hooks during login later)
    new_account.db.FIRST_LOGIN = True

    # join the new account to the public channel
    pchannel = ChannelDB.objects.get_channel(settings.DEFAULT_CHANNELS[0]["key"])
    if not pchannel or not pchannel.connect(new_account):
        string = "New account '%s' could not connect to public channel!" % new_account.key
        logger.log_err(string)
    return new_account


def _create_character(session, new_account, typeclass, home, permissions):
    """
    Helper function, creates a character based on an account's name.
    This is meant for Guest and AUTO_CREATRE_CHARACTER_WITH_ACCOUNT=True situations.
    """
    try:
        new_character = create.create_object(
            typeclass, key=new_account.key, home=home, permissions=permissions
        )
        # set playable character list
        new_account.db._playable_characters.append(new_character)

        # allow only the character itself and the account to puppet this character (and Developers).
        new_character.locks.add(
            "puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer)"
            % (new_character.id, new_account.id)
        )

        # If no description is set, set a default description
        if not new_character.db.desc:
            new_character.db.desc = "This is a character."
        # We need to set this to have ic auto-connect to this character
        new_account.db._last_puppet = new_character
    except Exception as e:
        session.msg(
            "There was an error creating the Character:\n%s\n If this problem persists, contact an"
            " admin." % e
        )
        logger.log_trace()
