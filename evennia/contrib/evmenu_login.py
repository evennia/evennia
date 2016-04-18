"""
A login menu using EvMenu.

Contribution - Vincent-lg 2016

This module defines a simple login system, similar to the one
defined in 'menu_login.py".  This present menu system, however,
uses EvMenu (hence the name).  This module contains the
functions (nodes) of the menu, with the CmdSet and
UnloggedCommand called when a user logs in.  In other words,
instead of using the 'connect' or 'create' commands once on the
login screen, players have to navigate through a simple menu
asking them to enter their username (then password), or to type
'new' to create one.  You may want to update your login screen
if you use this system.

In order to install, to your settings file, add/edit the line:

CMDSET_UNLOGGEDIN = "contrib.evmenu_login.UnloggedinCmdSet"

When you'll reload the server, new sessions will connect to the
new login system, where they will be able to:

* Enter their username, assuming they have an existing player.
* Enter 'NEW' to create a new player.

The top-level functions in this file are menu nodes (as
described in EvMenu).  Each one of these functions is
responsible for prompting the user with a specific information
(username, password and so on).  At the bottom of the file are
defined the CmdSet for Unlogging users, which adds a new command
(defined below) that is called just after a new session has been
created, in order to create the menu.  See the specific
documentation on functions (nodes) to see what each one should
do.

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

## Constants
RE_VALID_USERNAME = re.compile(r"^[a-z]{3,}$", re.I)
LEN_PASSWD = 6
CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE

## Menu notes (top-level functions)

def start(caller):
    """The user should enter his/her username or NEW to create one.

    This node is called at the very beginning of the menu, when
    a session has been created OR if an error occurs further
    down the menu tree.  From there, users can either enter a
    username (if this username exists) or type NEW (capitalized
    or not) to create a new player.

    """
    text = random_string_from_module(CONNECTION_SCREEN_MODULE)
    text += "\n\nEnter your username or |yNEW|n to create one."
    options = (
        {
            "key": "new",
            "desc": "Create a new character.",
            "goto": "create_username",
        },
        {
            "key": "_default",
            "desc": "Login to a valid username.",
            "goto": "username",
        },
    )
    return text, options

def username(caller, input):
    """Check that the username leads to an existing player.

    This is a temporary node.  If the username doesn't exist,
    go to the first node.  If it does exist, move to the next
    node (enter password).

    """
    input = input.strip()
    player = managers.players.get_player_from_name(input)
    if not player:
        string = dedent("""
            |rThe username {} doesn't exist yet.  Have you created it?|n
        """.strip("\n")).format(input)
        caller.msg(string)

        # Return to the first node
        return start(caller)
    else:
        # Saves the player in the menutree
        caller.ndb._menutree.player = player
        # Disables echo for the password
        caller.msg(echo=False)
        # Redirects to the password's node
        return password(caller, None)

def password(caller, input):
    """Ask the password to enter the password to this player.

    This is assuming the user exists (see 'create_username' and
    'create_password').  This node "loops" if needed:  if the
    user specifies a wrong password, the user doesn't leave this
    menu and is prompted again for the password (you might like
    to do more checks here, perhaps send warnings or add delays).

    """
    menutree = caller.ndb._menutree
    if input is None:
        text = "Enter this account's password :"
    else:
        caller.msg(echo=True)
        input = input.strip()
        # Check the password and login if correct
        if not hasattr(menutree, "player"):
            caller.msg(dedent("""
                |rSomething went wrong!  The player was not remembered
                from last step!|n
            """.strip("\n")))
            # Redirects to the first node
            return start(caller)

        player = menutree.player
        if not player.check_password(input):
            caller.msg(echo=False)
            caller.msg("|rIncorrect password.|n")
            # Loops on the same node
            return password(caller, None)

        # Before going on, check eventual bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (any(tup[0] == player.name.lower() for tup in bans) or \
                any(tup[2].match(caller.address) for tup in bans if tup[2])):
            # This is a banned IP or name!
            string = dedent("""
                |rYou have been banned and cannot continue from here.
                If you feel this ban is in error, please email an admin.|x
            """.strip("\n"))
            caller.msg(string)
            caller.sessionhandler.disconnect(
                    caller, "Good bye! Disconnecting...")
            # This is not necessary, since the player is disconnected,
            # but it seems to raise an error if simply returning None, None
            return password(caller, None)

        # We are OK, log us in.
        text = ""
        caller.sessionhandler.login(caller, player)

    options = (
        {
            "key": "_default",
            "desc": "Enter your password.",
            "goto": "password",
        },
    )
    return text, options

def create_username(caller, input):
    """Prompt to enter a valid username (one that doesnt exist).

    This node is called when the user enters 'NEW' after connecting.
    This node also "loops":  as long as the user doesn't enter a
    valid username, the menu repeats itself.

    """
    menutree = caller.ndb._menutree
    if input and input.lower().strip() == "new":
        # If the user just entered 'NEW', assumes it's the
        # begginning of the node
        input = None

    if input is None:
        text = "Enter the name of the character you would like to create."
    else:
        input = input.strip()
        player = managers.players.get_player_from_name(input)

        # If a player with that name exists, a new one will not be created
        if player:
            caller.msg(dedent("""
                |rThe account {} already exists, try another one.|n
            """.strip("\n")).format(input))
            # Loops on the same node
            return create_username(caller, None)
        elif not RE_VALID_USERNAME.search(input):
            caller.msg(dedent("""
                |rThis username isn't valid.|n  Only letters are accepted,
                without special characters.  The username must be
                at least 3 characters long.
            """.strip("\n")))
            return create_username(caller, None)
        else:
            menutree.playername = input
            # Disables echo for entering password
            caller.msg(echo=False)
            # Redirects to the creation of a password
            return create_password(caller, None)

    options = (
        {
            "key": "_default",
            "desc": "Enter your new account's name.",
            "goto": "create_username",
        },
    )
    return text, options

def create_password(caller, input):
    """Asks the user to create a password.

    This node is at the end of the menu for account creation.  If
    a proper MULTI_SESSION is configured, a character is also
    created with the same name (we try to login into it).

    """
    menutree = caller.ndb._menutree
    text = ""
    if input is None:
        text = "Enter this account's new password."
    else:
        caller.msg(echo=True)
        password = input.strip()

        if not hasattr(menutree, 'playername'):
            caller.msg(dedent("""
                |rSomething went wrong! Playername not remembered
                from previous step!{n
            """.strip("\n")))
            # Redirects to the starting node
            return start(caller)

        playername = menutree.playername
        if len(password) < LEN_PASSWD:
            caller.msg(echo=False)
            # The password is too short password
            string = dedent("""
                |rYour password must be at least {} characters long.|n
            """.strip("\n").format(LEN_PASSWD))
            caller.msg(string)
            # Loops on the same node
            return create_password(caller, None)

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
                    unloggedin._create_character(caller, new_player, typeclass,
                            default_home, permissions)
        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't, we
            # won't see any errors at all.
            caller.msg(dedent("""
                |rAn error occurred.|n  Please e-mail an admin if
                the problem persists.
            """.strip("\n")))
            logger.log_trace()
        else:
            text = ""
            caller.msg("Welcome, you're new account has been created!")
            caller.sessionhandler.login(caller, new_player)

    options = (
        {
            "key": "_default",
            "desc": "Enter your new password.",
            "goto": "create_password",
        },
    )
    return text, options

## Other functions

def _formatter(nodetext, optionstext, caller=None):
    """Do not display the options, only the text.

    This function is used by EvMenu to format the text of nodes.
    Options are not displayed for this menu, where it doesn't often
    make much sense to do so.  Thus, only the node text is displayed.

    """
    return nodetext

## Commands and CmdSets

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
        menu = EvMenu(self.caller, "evennia.contrib.evmenu_login",
                startnode="start", auto_quit=False, node_formatter=_formatter)
