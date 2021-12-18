"""
Email-based login system

Evennia contrib - Griatch 2012


This is a variant of the login system that requires an email-address
instead of a username to login.

This used to be the default Evennia login before replacing it with a
more standard username + password system (having to supply an email
for some reason caused a lot of confusion when people wanted to expand
on it. The email is not strictly needed internally, nor is any
confirmation email sent out anyway).


Installation is simple:

To your settings file, add/edit the line:

```python
CMDSET_UNLOGGEDIN = "contrib.email_login.UnloggedinCmdSet"
```

That's it. Reload the server and try to log in to see it.

The initial login "graphic" will still not mention email addresses
after this change. The login splashscreen is taken from strings in
the module given by settings.CONNECTION_SCREEN_MODULE.

"""
import re
from django.conf import settings
from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.server.models import ServerConfig

from evennia.commands.cmdset import CmdSet
from evennia.utils import logger, utils, ansi
from evennia.commands.default.muxcommand import MuxCommand
from evennia.commands.cmdhandler import CMD_LOGINSTART
from evennia.commands.default import (
    unloggedin as default_unloggedin,
)  # Used in CmdUnconnectedCreate

# limit symbol import for API
__all__ = (
    "CmdUnconnectedConnect",
    "CmdUnconnectedCreate",
    "CmdUnconnectedQuit",
    "CmdUnconnectedLook",
    "CmdUnconnectedHelp",
)

MULTISESSION_MODE = settings.MULTISESSION_MODE
CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE
CONNECTION_SCREEN = ""
try:
    CONNECTION_SCREEN = ansi.parse_ansi(utils.random_string_from_module(CONNECTION_SCREEN_MODULE))
except Exception:
    # malformed connection screen or no screen given
    pass
if not CONNECTION_SCREEN:
    CONNECTION_SCREEN = (
        "\nEvennia: Error in CONNECTION_SCREEN MODULE"
        " (randomly picked connection screen variable is not a string). \nEnter 'help' for aid."
    )


class CmdUnconnectedConnect(MuxCommand):
    """
    Connect to the game.

    Usage (at login screen):
        connect <email> <password>

    Use the create command to first create an account before logging in.
    """

    key = "connect"
    aliases = ["conn", "con", "co"]
    locks = "cmd:all()"  # not really needed

    def func(self):
        """
        Uses the Django admin api. Note that unlogged-in commands
        have a unique position in that their `func()` receives
        a session object instead of a `source_object` like all
        other types of logged-in commands (this is because
        there is no object yet before the account has logged in)
        """

        session = self.caller
        arglist = self.arglist

        if not arglist or len(arglist) < 2:
            session.msg("\n\r Usage (without <>): connect <email> <password>")
            return
        email = arglist[0]
        password = arglist[1]

        # Match an email address to an account.
        account = AccountDB.objects.get_account_from_email(email)
        # No accountname match
        if not account:
            string = "The email '%s' does not match any accounts." % email
            string += "\n\r\n\rIf you are new you should first create a new account "
            string += "using the 'create' command."
            session.msg(string)
            return
        # We have at least one result, so we can check the password.
        if not account[0].check_password(password):
            session.msg("Incorrect password.")
            return

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (
            any(tup[0] == account.name for tup in bans)
            or any(tup[2].match(session.address[0]) for tup in bans if tup[2])
        ):
            # this is a banned IP or name!
            string = "|rYou have been banned and cannot continue from here."
            string += "\nIf you feel this ban is in error, please email an admin.|x"
            session.msg(string)
            session.execute_cmd("quit")
            return

        # actually do the login. This will call all hooks.
        session.sessionhandler.login(session, account)


class CmdUnconnectedCreate(MuxCommand):
    """
    Create a new account.

    Usage (at login screen):
        create \"accountname\" <email> <password>

    This creates a new account account.

    """

    key = "create"
    aliases = ["cre", "cr"]
    locks = "cmd:all()"

    def parse(self):
        """
        The parser must handle the multiple-word account
        name enclosed in quotes:
            connect "Long name with many words" my@myserv.com mypassw
        """
        super().parse()

        self.accountinfo = []
        if len(self.arglist) < 3:
            return
        if len(self.arglist) > 3:
            # this means we have a multi_word accountname. pop from the back.
            password = self.arglist.pop()
            email = self.arglist.pop()
            # what remains is the accountname.
            accountname = " ".join(self.arglist)
        else:
            accountname, email, password = self.arglist

        accountname = accountname.replace('"', "")  # remove "
        accountname = accountname.replace("'", "")
        self.accountinfo = (accountname, email, password)

    def func(self):
        """Do checks and create account"""

        session = self.caller
        try:
            accountname, email, password = self.accountinfo
        except ValueError:
            string = '\n\r Usage (without <>): create "<accountname>" <email> <password>'
            session.msg(string)
            return
        if not email or not password:
            session.msg("\n\r You have to supply an e-mail address followed by a password.")
            return
        if not utils.validate_email_address(email):
            # check so the email at least looks ok.
            session.msg("'%s' is not a valid e-mail address." % email)
            return
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
        if AccountDB.objects.get_account_from_email(email):
            # email already set on an account
            session.msg("Sorry, there is already an account with that email address.")
            return
        # Reserve accountnames found in GUEST_LIST
        if settings.GUEST_LIST and accountname.lower() in (
            guest.lower() for guest in settings.GUEST_LIST
        ):
            string = "\n\r That name is reserved. Please choose another Accountname."
            session.msg(string)
            return
        if not re.findall(r"^[\w. @+\-']+$", password) or not (3 < len(password)):
            string = (
                "\n\r Password should be longer than 3 characters. Letters, spaces, digits and @/./+/-/_/' only."
                "\nFor best security, make it longer than 8 characters. You can also use a phrase of"
                "\nmany words if you enclose the password in double quotes."
            )
            session.msg(string)
            return

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (
            any(tup[0] == accountname.lower() for tup in bans)
            or any(tup[2].match(session.address) for tup in bans if tup[2])
        ):
            # this is a banned IP or name!
            string = (
                "|rYou have been banned and cannot continue from here."
                "\nIf you feel this ban is in error, please email an admin.|x"
            )
            session.msg(string)
            session.sessionhandler.disconnect(session, "Good bye! Disconnecting.")
            return

        # everything's ok. Create the new player account.
        try:
            permissions = settings.PERMISSION_ACCOUNT_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            new_account = default_unloggedin._create_account(
                session, accountname, password, permissions, email=email
            )
            if new_account:
                if MULTISESSION_MODE < 2:
                    default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                    default_unloggedin._create_character(
                        session, new_account, typeclass, default_home, permissions
                    )
                # tell the caller everything went well.
                string = "A new account '%s' was created. Welcome!"
                if " " in accountname:
                    string += (
                        "\n\nYou can now log in with the command 'connect \"%s\" <your password>'."
                    )
                else:
                    string += "\n\nYou can now log with the command 'connect %s <your password>'."
                session.msg(string % (accountname, email))

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            session.msg("An error occurred. Please e-mail an admin if the problem persists.")
            logger.log_trace()
            raise


class CmdUnconnectedQuit(MuxCommand):
    """
    We maintain a different version of the `quit` command
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


class CmdUnconnectedLook(MuxCommand):
    """
    This is an unconnected version of the `look` command for simplicity.

    This is called by the server and kicks everything in gear.
    All it does is display the connect screen.
    """

    key = CMD_LOGINSTART
    aliases = ["look", "l"]
    locks = "cmd:all()"

    def func(self):
        """Show the connect screen."""
        self.caller.msg(CONNECTION_SCREEN)


class CmdUnconnectedHelp(MuxCommand):
    """
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
  |wcreate, connect, look, help, quit|n

To login to the system, you need to do one of the following:

|w1)|n If you have no previous account, you need to use the 'create'
   command like this:

     |wcreate "Anna the Barbarian" anna@myemail.com c67jHL8p|n

   It's always a good idea (not only here, but everywhere on the net)
   to not use a regular word for your password. Make it longer than
   3 characters (ideally 6 or more) and mix numbers and capitalization
   into it.

|w2)|n If you have an account already, either because you just created
   one in |w1)|n above or you are returning, use the 'connect' command:

     |wconnect anna@myemail.com c67jHL8p|n

   This should log you in. Run |whelp|n again once you're logged in
   to get more aid. Hope you enjoy your stay!

You can use the |wlook|n command if you want to see the connect screen again.
"""
        self.caller.msg(string)


# command set for the mux-like login


class UnloggedinCmdSet(CmdSet):
    """
    Sets up the unlogged cmdset.
    """

    key = "Unloggedin"
    priority = 0

    def at_cmdset_creation(self):
        """Populate the cmdset"""
        self.add(CmdUnconnectedConnect())
        self.add(CmdUnconnectedCreate())
        self.add(CmdUnconnectedQuit())
        self.add(CmdUnconnectedLook())
        self.add(CmdUnconnectedHelp())
