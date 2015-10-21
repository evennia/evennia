"""
EvMenu-driven login system

Contribution - Ahmed Charles 2015

This is heavily influenced by the previous menu login by Griatch.

This is an alternative login system for Evennia, using the
utils.evmenu module. As opposed to the default system it doesn't
auto-create a Character with the same name as the Player
(instead assuming some sort of character-creation to come next).


Install is simple:

To your settings file, add/edit the line:

CMDSET_UNLOGGEDIN = "contrib.menu_login.UnloggedinCmdSet"

That's it. Reload the server and try to log in to see it.

You will want to change the login "graphic", which defaults to give
information about commands which are not used in this version of the
login. You can change the screen used by editing
`$GAME_DIR/server/conf/connection_screens.py`.

"""

import re
import traceback
import sys
from django.conf import settings
from evennia import managers
from evennia import utils, logger, create_player
from evennia import ObjectDB
from evennia import Command, CmdSet
from evennia import syscmdkeys
from evennia.server.models import ServerConfig

from evennia.utils.evmenu import EvMenu

_CMD_LOGINSTART = syscmdkeys.CMD_LOGINSTART
_CMD_NOINPUT = syscmdkeys.CMD_NOINPUT
_CMD_NOMATCH = syscmdkeys.CMD_NOMATCH

_MULTISESSION_MODE = settings.MULTISESSION_MODE
_CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE


def save_login_name(caller, raw_string):
    caller.ndb._menutree._login_name = raw_string


def save_login_password(caller, raw_string):
    caller.ndb._menutree._login_password = raw_string


def save_create_account(caller):
    caller.ndb._menutree._create_account = True


def start(caller):
    text = utils.random_string_from_module(_CONNECTION_SCREEN_MODULE)
    text += "\n\nEnter an option or your account name to continue."
    options = ({"desc": "Log in with an existing account.",
                "goto": "login_node"},
               {"desc": "Create a new account.",
                "exec": save_create_account,
                "goto": "create_account_node"},
               {"desc": "Quit.",
                "goto": "quit_node"},
               {"key": "",
                "desc": "",
                "goto": "start"},
               {"key": "_default",
                "exec": save_login_name,
                "goto": "login_name_node"})
    return text, options


def quit_node(caller):
    return "", None


def login_node(caller):
    text = "Please enter your account name:"
    options = {"key": "_default",
               "exec": save_login_name,
               "goto": "login_name_node"}
    return text, options


def login_name_node(caller):
    text = "Please enter your password:"
    options = {"key": "_default",
               "exec": save_login_password,
               "goto": "login_password_node"}
    return text, options


def login_password_node(caller):
    if menu_quit(caller, caller.ndb._menutree):
        return "", None
    return "Something went wrong, press enter to continue.", options


def create_account_node(caller):
    text = "Please enter your desired account name:"
    options = {"key": "_default",
               "exec": save_login_name,
               "goto": "create_account_name_node"}
    return text, options


def create_account_name_node(caller):
    text = "Please enter your desired account password:"
    options = {"key": "_default",
               "exec": save_login_password,
               "goto": "create_account_password_node"}
    return text, options


def create_account_password_node(caller):
    return "", None

def menu_quit(caller, menutree):
    if not hasattr(menutree, "_login_name") or not hasattr(menutree, "_login_password"):
        caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
        return
    if hasattr(menutree, "_create_account") and menutree._create_account:
        login_name = menutree._login_name
        login_password = menutree._login_password
        # sanity check on the name
        if not re.findall('^[\w. @+-]+$', login_name) or not (3 <= len(login_name) <= 30):
            # this echoes the restrictions made by django's auth module.
            string = "{rAccount name should be between 3 and 30 characters. "
            string += "Letters, spaces, digits and @/./+/-/_ only.{n"
            caller.msg(string)
            caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
            return
        if managers.players.get_player_from_name(login_name):
            caller.msg("{rAccount name '%s' already exists.{n" % login_name)
            caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
            return
        if len(login_password) < 8:
            # too short password
            caller.msg("{rYour password must be at least 8 characters or longer.{n")
            caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
            return

        # everything's ok. Create the new player account and possibly the character
        # depending on the multisession mode

        from evennia.commands.default import unloggedin
        # we make use of the helper functions from the default set here.
        try:
            permissions = settings.PERMISSION_PLAYER_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            new_player = unloggedin._create_player(caller, login_name,
                                                   login_password, permissions)
            if new_player:
                if _MULTISESSION_MODE < 2:
                    default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                    unloggedin._create_character(caller, new_player, typeclass,
                                                 default_home, permissions)
            caller.msg("{gA new account '%s' was created.{n" % (login_name))
            caller.sessionhandler.login(caller, new_player)
        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't, we
            # won't see any errors at all.
            self.caller.msg("An error occurred. Please e-mail an admin if the problem persists.")
            logger.log_trace()

    else:
        player = managers.players.get_player_from_name(menutree._login_name)
        if not player or not player.check_password(menutree._login_password):
            caller.msg("{rIncorrect account name or password.{n")
            caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
            return

        # before going on, check eventual bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (any(tup[0]==player.name.lower() for tup in bans)
                     or
                     any(tup[2].match(caller.address) for tup in bans if tup[2])):
            # this is a banned IP or name!
            string = "{rYou have been banned and cannot continue from here."
            string += "\nIf you feel this ban is in error, please email an admin.{x"
            caller.msg(string)
            caller.sessionhandler.disconnect(caller, "Good bye! Disconnecting...")
            return

        # we are ok, log us in.
        caller.msg("{gWelcome %s! Logging in ...{n" % player.key)
        caller.sessionhandler.login(caller, player)


class CmdUnloggedinLook(Command):
    """
    An unloggedin version of the look command. This is called by the server
    when the player first connects. It sets up the menu before handing off
    to the menu's own look command.
    """
    key = _CMD_LOGINSTART
    locks = "cmd:all()"
    arg_regex = r"^$"

    def func(self):
        "Execute the menu"
        EvMenu(self.caller, sys.modules[__name__], cmd_on_quit=menu_quit)


class UnloggedinCmdSet(CmdSet):
    "Cmdset for the unloggedin state"
    key = "DefaultUnloggedin"
    priority = 0

    def at_cmdset_creation(self):
        "Called when cmdset is first created."
        self.add(CmdUnloggedinLook())
