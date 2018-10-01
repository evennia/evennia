"""
Commands that are available from the connect screen.
"""
import re
import datetime
from codecs import lookup as codecs_lookup
from random import getrandbits
from django.conf import settings
from django.contrib.auth import authenticate
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.server.models import ServerConfig
from evennia.server.throttle import Throttle
from evennia.comms.models import ChannelDB
from evennia.server.sessionhandler import SESSIONS

from evennia.utils import create, logger, utils, gametime
from evennia.commands.cmdhandler import CMD_LOGINSTART

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

# limit symbol import for API
__all__ = ("CmdUnconnectedConnect", "CmdUnconnectedCreate",
           "CmdUnconnectedQuit", "CmdUnconnectedLook", "CmdUnconnectedHelp")

MULTISESSION_MODE = settings.MULTISESSION_MODE
CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE

# Create throttles for too many connections, account-creations and login attempts
CONNECTION_THROTTLE = Throttle(limit=5, timeout=1 * 60)
CREATION_THROTTLE = Throttle(limit=2, timeout=10 * 60)
LOGIN_THROTTLE = Throttle(limit=5, timeout=5 * 60)


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
    # check if guests are enabled.
    if not settings.GUEST_ENABLED:
        return False, None

    # Check IP bans.
    bans = ServerConfig.objects.conf("server_bans")
    if bans and any(tup[2].match(session.address) for tup in bans if tup[2]):
        # this is a banned IP!
        string = "|rYou have been banned and cannot continue from here." \
                 "\nIf you feel this ban is in error, please email an admin.|x"
        session.msg(string)
        session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")
        return True, None

    try:
        # Find an available guest name.
        accountname = None
        for name in settings.GUEST_LIST:
            if not AccountDB.objects.filter(username__iexact=accountname).count():
                accountname = name
                break
        if not accountname:
            session.msg("All guest accounts are in use. Please try again later.")
            return True, None
        else:
            # build a new account with the found guest accountname
            password = "%016x" % getrandbits(64)
            home = ObjectDB.objects.get_id(settings.GUEST_HOME)
            permissions = settings.PERMISSION_GUEST_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            ptypeclass = settings.BASE_GUEST_TYPECLASS
            new_account = _create_account(session, accountname, password, permissions, ptypeclass)
            if new_account:
                _create_character(session, new_account, typeclass, home, permissions)
            return True, new_account

    except Exception:
        # We are in the middle between logged in and -not, so we have
        # to handle tracebacks ourselves at this point. If we don't,
        # we won't see any errors at all.
        session.msg("An error occurred. Please e-mail an admin if the problem persists.")
        logger.log_trace()
        raise


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
    # check for too many login errors too quick.
    address = session.address
    if isinstance(address, tuple):
        address = address[0]

    if LOGIN_THROTTLE.check(address):
        session.msg("|RYou made too many connection attempts. Try again in a few minutes.|n")
        return None

    # Match account name and check password
    account = authenticate(username=name, password=password)

    if not account:
        # No accountname or password match
        session.msg("Incorrect login information given.")
        # this just updates the throttle
        LOGIN_THROTTLE.update(address)
        # calls account hook for a failed login if possible.
        account = AccountDB.objects.get_account_from_name(name)
        if account:
            account.at_failed_login(session)
        return None

    # Check IP and/or name bans
    bans = ServerConfig.objects.conf("server_bans")
    if bans and (any(tup[0] == account.name.lower() for tup in bans) or
                 any(tup[2].match(session.address) for tup in bans if tup[2])):
        # this is a banned IP or name!
        string = "|rYou have been banned and cannot continue from here." \
                 "\nIf you feel this ban is in error, please email an admin.|x"
        session.msg(string)
        session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")
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

        # check for too many login errors too quick.
        address = session.address
        if isinstance(address, tuple):
            address = address[0]
        if CONNECTION_THROTTLE.check(address):
            # timeout is 5 minutes.
            session.msg("|RYou made too many connection attempts. Try again in a few minutes.|n")
            return

        args = self.args
        # extract double quote parts
        parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no double quotes being found, or a guest login
            parts = parts[0].split(None, 1)
            # Guest login
            if len(parts) == 1 and parts[0].lower() == "guest":
                enabled, new_account = create_guest_account(session)
                if new_account:
                    session.sessionhandler.login(session, new_account)
                if enabled:
                    return

        if len(parts) != 2:
            session.msg("\n\r Usage (without <>): connect <name> <password>")
            return

        CONNECTION_THROTTLE.update(address)
        name, password = parts
        account = create_normal_account(session, name, password)
        if account:
            session.sessionhandler.login(session, account)


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

        # Rate-limit account creation.
        address = session.address

        if isinstance(address, tuple):
            address = address[0]
        if CREATION_THROTTLE.check(address):
            session.msg("|RYou are creating too many accounts. Try again in a few minutes.|n")
            return

        # extract double quoted parts
        parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no quotes being found
            parts = parts[0].split(None, 1)
        if len(parts) != 2:
            string = "\n Usage (without <>): create <name> <password>" \
                     "\nIf <name> or <password> contains spaces, enclose it in double quotes."
            session.msg(string)
            return
        accountname, password = parts

        # sanity checks
        if not re.findall(r"^[\w. @+\-']+$", accountname) or not (0 < len(accountname) <= 30):
            # this echoes the restrictions made by django's auth
            # module (except not allowing spaces, for convenience of
            # logging in).
            string = "\n\r Accountname can max be 30 characters or fewer. Letters, spaces, digits and @/./+/-/_/' only."
            session.msg(string)
            return
        # strip excessive spaces in accountname
        accountname = re.sub(r"\s+", " ", accountname).strip()
        if AccountDB.objects.filter(username__iexact=accountname):
            # account already exists (we also ignore capitalization here)
            session.msg("Sorry, there is already an account with the name '%s'." % accountname)
            return
        # Reserve accountnames found in GUEST_LIST
        if settings.GUEST_LIST and accountname.lower() in (guest.lower() for guest in settings.GUEST_LIST):
            string = "\n\r That name is reserved. Please choose another Accountname."
            session.msg(string)
            return

        # Validate password
        Account = utils.class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        # Have to create a dummy Account object to check username similarity
        valid, error = Account.validate_password(password, account=Account(username=accountname))
        if error:
            errors = [e for suberror in error.messages for e in error.messages]
            string = "\n".join(errors)
            session.msg(string)
            return

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (any(tup[0] == accountname.lower() for tup in bans) or

                     any(tup[2].match(session.address) for tup in bans if tup[2])):
            # this is a banned IP or name!
            string = "|rYou have been banned and cannot continue from here." \
                     "\nIf you feel this ban is in error, please email an admin.|x"
            session.msg(string)
            session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")
            return

        # everything's ok. Create the new account account.
        try:
            permissions = settings.PERMISSION_ACCOUNT_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            new_account = _create_account(session, accountname, password, permissions)
            if new_account:
                if MULTISESSION_MODE < 2:
                    default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                    _create_character(session, new_account, typeclass, default_home, permissions)

                # Update the throttle to indicate a new account was created from this IP
                CREATION_THROTTLE.update(address)

                # tell the caller everything went well.
                string = "A new account '%s' was created. Welcome!"
                if " " in accountname:
                    string += "\n\nYou can now log in with the command 'connect \"%s\" <your password>'."
                else:
                    string += "\n\nYou can now log with the command 'connect %s <your password>'."
                session.msg(string % (accountname, accountname))

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            session.msg("An error occurred. Please e-mail an admin if the problem persists.")
            logger.log_trace()


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

        string = \
            """
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
    aliases = ("@encoding", "@encode")
    locks = "cmd:all()"

    def func(self):
        """
        Sets the encoding.
        """

        if self.session is None:
            return

        sync = False
        if 'clear' in self.switches:
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
                string += "Default encoding: |g%s|n (change with |w@encoding <encoding>|n)" % pencoding
            encodings = settings.ENCODINGS
            if encodings:
                string += "\nServer's alternative encodings (tested in this order):\n   |g%s|n" % ", ".join(encodings)
            if not string:
                string = "No encodings found."
        else:
            # change encoding
            old_encoding = self.session.protocol_flags.get("ENCODING", None)
            encoding = self.args
            try:
                codecs_lookup(encoding)
            except LookupError:
                string = "|rThe encoding '|w%s|r' is invalid. Keeping the previous encoding '|w%s|r'.|n"\
                         % (encoding, old_encoding)
            else:
                self.session.protocol_flags["ENCODING"] = encoding
                string = "Your custom text encoding was changed from '|w%s|n' to '|w%s|n'." % (old_encoding, encoding)
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
    logged in, use @option screenreader on).
    """
    key = "screenreader"
    aliases = "@screenreader"

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
        self.caller.msg("## BEGIN INFO 1.1\nName: %s\nUptime: %s\nConnected: %d\nVersion: Evennia %s\n## END INFO" % (
                        settings.SERVERNAME,
                        datetime.datetime.fromtimestamp(gametime.SERVER_START_TIME).ctime(),
                        SESSIONS.account_count(), utils.get_evennia_version()))


def _create_account(session, accountname, password, permissions, typeclass=None, email=None):
    """
    Helper function, creates an account of the specified typeclass.
    """
    try:
        new_account = create.create_account(accountname, email, password, permissions=permissions, typeclass=typeclass)

    except Exception as e:
        session.msg("There was an error creating the Account:\n%s\n If this problem persists, contact an admin." % e)
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
    This is meant for Guest and MULTISESSION_MODE < 2 situations.
    """
    try:
        new_character = create.create_object(typeclass, key=new_account.key, home=home, permissions=permissions)
        # set playable character list
        new_account.db._playable_characters.append(new_character)

        # allow only the character itself and the account to puppet this character (and Developers).
        new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Developer) or pperm(Developer)" %
                                (new_character.id, new_account.id))

        # If no description is set, set a default description
        if not new_character.db.desc:
            new_character.db.desc = "This is a character."
        # We need to set this to have @ic auto-connect to this character
        new_account.db._last_puppet = new_character
    except Exception as e:
        session.msg("There was an error creating the Character:\n%s\n If this problem persists, contact an admin." % e)
        logger.log_trace()
