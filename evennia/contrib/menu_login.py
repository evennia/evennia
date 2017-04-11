"""
A login menu using EvMenu.

Contribution - Vincent-lg 2016

This module contains the functions (nodes) of the EvMenu, with the
CmdSet and UnloggedCommand called when a user logs in.  In other
words, instead of using the 'connect' or 'create' commands once on the
login screen, players navigates through a simple menu asking them to
enter their username followed by password, or to type 'new' to create
a new one. You will need to change update your login screen if you use
this system.

In order to install, to your settings file, add/edit the line:

CMDSET_UNLOGGEDIN = "contrib.menu_login.UnloggedinCmdSet"

When you'll reload the server, new sessions will connect to the new
login system, where they will be able to:

* Enter their username, assuming they have an existing player.
* Enter 'NEW' to create a new player.

The top-level functions in this file are menu nodes (as described in
evennia.utils.evmenu.py). Each one of these functions is responsible
for prompting the user for a specific piece of information (username,
password and so on). At the bottom of the file is defined the CmdSet
for Unlogging users. This adds a new command that is called just after
a new session has been created, in order to create the menu.  See the
specific documentation on functions (nodes) to see what each one
should do.

"""

import re
from textwrap import dedent

from django.conf import settings

from evennia import Command, CmdSet
from evennia import logger
from evennia import managers
from evennia import ObjectDB
from evennia.server.models import ServerConfig
from evennia import syscmdkeys
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import random_string_from_module

# Constants
RE_VALID_USERNAME = re.compile(r"^[a-z]{3,}$", re.I)
LEN_PASSWD = 6
CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE

# Menu notes (top-level functions)


def start(caller):
    """The user should enter his/her username or NEW to create one.

    This node is called at the very beginning of the menu, when
    a session has been created OR if an error occurs further
    down the menu tree.  From there, users can either enter a
    username (if this username exists) or type NEW (capitalized
    or not) to create a new player.

    """
    text = random_string_from_module(CONNECTION_SCREEN_MODULE)
    text += "\n\nEnter your username or |yNEW|n to create a new account."
    options = (
        {"key": "",
         "goto": "start"},
        {"key": "new",
         "goto": "create_account"},
        {"key": "quit",
         "goto": "quit"},
        {"key": "_default",
         "goto": "username"})
    return text, options


def username(caller, string_input):
    """Check that the username leads to an existing player.

    Check that the specified username exists.  If the username doesn't
    exist, display an error message and ask the user to try again.  If
    entering an empty string, return to start node.  If user exists,
    move to the next node (enter password).

    """
    string_input = string_input.strip()
    player = managers.players.get_player_from_name(string_input)
    if player is None:
        text = dedent("""
            |rThe username '{}' doesn't exist. Have you created it?|n
            Try another name or leave empty to go back.
        """.strip("\n")).format(string_input)
        options = (
            {"key": "",
             "goto": "start"},
            {"key": "_default",
             "goto": "username"})
    else:
        caller.ndb._menutree.player = player
        text = "Enter the password for the {} account.".format(player.name)
        # Disables echo for the password
        caller.msg("", options={"echo": False})
        options = (
            {"key": "",
             "exec": lambda caller: caller.msg("", options={"echo": True}),
             "goto": "start"},
            {"key": "_default",
             "goto": "ask_password"})

    return text, options


def ask_password(caller, string_input):
    """Ask the user to enter the password to this player.

    This is assuming the user exists (see 'create_username' and
    'create_password').  This node "loops" if needed:  if the
    user specifies a wrong password, offers the user to try
    again or to go back by entering 'b'.
    If the password is correct, then login.

    """
    menutree = caller.ndb._menutree
    string_input = string_input.strip()

    # Check the password and login is correct; also check for bans

    player = menutree.player
    password_attempts = menutree.password_attempts \
        if hasattr(menutree, "password_attempts") else 0
    bans = ServerConfig.objects.conf("server_bans")
    banned = bans and (any(tup[0] == player.name.lower() for tup in bans) or
                       any(tup[2].match(caller.address) for tup in bans if tup[2]))

    if not player.check_password(string_input):
        # Didn't enter a correct password
        password_attempts += 1
        if password_attempts > 2:
            # Too many tries
            caller.sessionhandler.disconnect(
                caller, "|rToo many failed attempts. Disconnecting.|n")
            text = ""
            options = {}
        else:
            menutree.password_attempts = password_attempts
            text = dedent("""
                |rIncorrect password.|n
                Try again or leave empty to go back.
            """.strip("\n"))
            # Loops on the same node
            options = (
                {"key": "",
                 "exec": lambda caller: caller.msg("", options={"echo": True}),
                 "goto": "start"},
                {"key": "_default",
                 "goto": "ask_password"})
    elif banned:
        # This is a banned IP or name!
        string = dedent("""
            |rYou have been banned and cannot continue from here.
            If you feel this ban is in error, please email an admin.|n
            Disconnecting.
        """.strip("\n"))
        caller.sessionhandler.disconnect(caller, string)
        text = ""
        options = {}
    else:
        # We are OK, log us in.
        text = ""
        options = {}
        caller.msg("", options={"echo": True})
        caller.sessionhandler.login(caller, player)

    return text, options


def create_account(caller):
    """Create a new account.

    This node simply prompts the user to entere a username.
    The input is redirected to 'create_username'.

    """
    text = "Enter your new account name."
    options = (
        {"key": "_default",
         "goto": "create_username"},)
    return text, options


def create_username(caller, string_input):
    """Prompt to enter a valid username (one that doesnt exist).

    'string_input' contains the new username.  If it exists, prompt
    the username to retry or go back to the login screen.

    """
    menutree = caller.ndb._menutree
    string_input = string_input.strip()
    player = managers.players.get_player_from_name(string_input)

    # If a player with that name exists, a new one will not be created
    if player:
        text = dedent("""
            |rThe account {} already exists.|n
            Enter another username or leave blank to go back.
        """.strip("\n")).format(string_input)
        # Loops on the same node
        options = (
            {"key": "",
             "goto": "start"},
            {"key": "_default",
             "goto": "create_username"})
    elif not RE_VALID_USERNAME.search(string_input):
        text = dedent("""
            |rThis username isn't valid.|n
            Only letters are accepted, without special characters.
            The username must be at least 3 characters long.
            Enter another username or leave blank to go back.
        """.strip("\n"))
        options = (
            {"key": "",
             "goto": "start"},
            {"key": "_default",
             "goto": "create_username"})
    else:
        # a valid username - continue getting the password
        menutree.playername = string_input
        # Disables echo for entering password
        caller.msg("", options={"echo": False})
        # Redirects to the creation of a password
        text = "Enter this account's new password."
        options = (
            {"key": "_default",
             "goto": "create_password"},)

    return text, options


def create_password(caller, string_input):
    """Ask the user to create a password.

    This node is at the end of the menu for account creation.  If
    a proper MULTI_SESSION is configured, a character is also
    created with the same name (we try to login into it).

    """
    menutree = caller.ndb._menutree
    text = ""
    options = (
        {"key": "",
         "exec": lambda caller: caller.msg("", options={"echo": True}),
         "goto": "start"},
        {"key": "_default",
         "goto": "create_password"})

    password = string_input.strip()
    playername = menutree.playername

    if len(password) < LEN_PASSWD:
        # The password is too short
        text = dedent("""
            |rYour password must be at least {} characters long.|n
            Enter another password or leave it empty to go back.
        """.strip("\n")).format(LEN_PASSWD)
    else:
        # Everything's OK.  Create the new player account and
        # possibly the character, depending on the multisession mode
        from evennia.commands.default import unloggedin
        # We make use of the helper functions from the default set here.
        try:
            permissions = settings.PERMISSION_PLAYER_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            new_player = unloggedin._create_player(caller, playername,
                                                   password, permissions)
            if new_player:
                if settings.MULTISESSION_MODE < 2:
                    default_home = ObjectDB.objects.get_id(
                        settings.DEFAULT_HOME)
                    unloggedin._create_character(caller, new_player,
                                                 typeclass, default_home, permissions)
        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't, we
            # won't see any errors at all.
            caller.msg(dedent("""
                |rAn error occurred.|n  Please e-mail an admin if
                the problem persists. Try another password or leave
                it empty to go back to the login screen.
            """.strip("\n")))
            logger.log_trace()
        else:
            text = ""
            caller.msg("|gWelcome, your new account has been created!|n")
            caller.msg("", options={"echo": True})
            caller.sessionhandler.login(caller, new_player)

    return text, options


def quit(caller):
    caller.sessionhandler.disconnect(caller, "Goodbye! Logging off.")
    return "", {}

# Other functions


def _formatter(nodetext, optionstext, caller=None):
    """Do not display the options, only the text.

    This function is used by EvMenu to format the text of nodes.
    Options are not displayed for this menu, where it doesn't often
    make much sense to do so.  Thus, only the node text is displayed.

    """
    return nodetext


# Commands and CmdSets

class UnloggedinCmdSet(CmdSet):
    "Cmdset for the unloggedin state"
    key = "DefaultUnloggedin"
    priority = 0

    def at_cmdset_creation(self):
        "Called when cmdset is first created."
        self.add(CmdUnloggedinLook())


class CmdUnloggedinLook(Command):
    """
    An unloggedin version of the look command. This is called by the server
    when the player first connects. It sets up the menu before handing off
    to the menu's own look command.
    """
    key = syscmdkeys.CMD_LOGINSTART
    locks = "cmd:all()"
    arg_regex = r"^$"

    def func(self):
        "Execute the menu"
        EvMenu(self.caller, "evennia.contrib.menu_login",
               startnode="start", auto_look=False, auto_quit=False,
               cmd_on_exit=None, node_formatter=_formatter)
