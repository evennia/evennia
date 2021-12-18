"""
A login menu using EvMenu.

Contribution - Vincent-lg 2016, Griatch 2019 (rework for modern EvMenu)

This changes the Evennia login to ask for the account name and password in
sequence instead of requiring you to enter both at once. 

To install, add this line to the settings file (`mygame/server/conf/settings.py`):

    CMDSET_UNLOGGEDIN = "evennia.contrib.menu_login.UnloggedinCmdSet"

Reload the server and the new connection method will be active. Note that you must
independently change the connection screen to match this login style, by editing 
`mygame/server/conf/connection_screens.py`.

This uses Evennia's menu system EvMenu and is triggered by a command that is 
called automatically when a new user connects.

"""

from django.conf import settings

from evennia import Command, CmdSet
from evennia import syscmdkeys
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import random_string_from_module, class_from_module, callables_from_module

_CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE
_GUEST_ENABLED = settings.GUEST_ENABLED
_ACCOUNT = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
_GUEST = class_from_module(settings.BASE_GUEST_TYPECLASS)

_ACCOUNT_HELP = (
    "Enter the name you used to log into the game before, " "or a new account-name if you are new."
)
_PASSWORD_HELP = (
    "Password should be a minimum of 8 characters (preferably longer) and "
    "can contain a mix of letters, spaces, digits and @/./+/-/_/'/, only."
)

# Menu nodes


def _show_help(caller, raw_string, **kwargs):
    """Echo help message, then re-run node that triggered it"""
    help_entry = kwargs["help_entry"]
    caller.msg(help_entry)
    return None  # re-run calling node


def node_enter_username(caller, raw_text, **kwargs):
    """
    Start node of menu
    Start login by displaying the connection screen and ask for a user name.

    """

    def _check_input(caller, username, **kwargs):
        """
        'Goto-callable', set up to be called from the _default option below.

        Called when user enters a username string. Check if this username already exists and set the flag
        'new_user' if not. Will also directly login if the username is 'guest'
        and GUEST_ENABLED is True.

        The return from this goto-callable determines which node we go to next
        and what kwarg it will be called with.

        """
        username = username.rstrip("\n")

        if username == "guest" and _GUEST_ENABLED:
            # do an immediate guest login
            session = caller
            address = session.address
            account, errors = _GUEST.authenticate(ip=address)
            if account:
                return "node_quit_or_login", {"login": True, "account": account}
            else:
                session.msg("|R{}|n".format("\n".join(errors)))
                return None  # re-run the username node

        try:
            _ACCOUNT.objects.get(username__iexact=username)
        except _ACCOUNT.DoesNotExist:
            new_user = True
        else:
            new_user = False

        # pass username/new_user into next node as kwargs
        return "node_enter_password", {"new_user": new_user, "username": username}

    callables = callables_from_module(_CONNECTION_SCREEN_MODULE)
    if "connection_screen" in callables:
        connection_screen = callables["connection_screen"]()
    else:
        connection_screen = random_string_from_module(_CONNECTION_SCREEN_MODULE)

    if _GUEST_ENABLED:
        text = "Enter a new or existing user name to login (write 'guest' for a guest login):"
    else:
        text = "Enter a new or existing user name to login:"
    text = "{}\n\n{}".format(connection_screen, text)

    options = (
        {"key": "", "goto": "node_enter_username"},
        {"key": ("quit", "q"), "goto": "node_quit_or_login"},
        {"key": ("help", "h"), "goto": (_show_help, {"help_entry": _ACCOUNT_HELP, **kwargs})},
        {"key": "_default", "goto": _check_input},
    )
    return text, options


def node_enter_password(caller, raw_string, **kwargs):
    """
    Handle password input.

    """

    def _check_input(caller, password, **kwargs):
        """
        'Goto-callable', set up to be called from the _default option below.

        Called when user enters a password string. Check username + password
        viability. If it passes, the account will have been created and login
        will be initiated.

        The return from this goto-callable determines which node we go to next
        and what kwarg it will be called with.

        """
        # these flags were set by the goto-callable
        username = kwargs["username"]
        new_user = kwargs["new_user"]
        password = password.rstrip("\n")

        session = caller
        address = session.address
        if new_user:
            # create a new account
            account, errors = _ACCOUNT.create(
                username=username, password=password, ip=address, session=session
            )
        else:
            # check password against existing account
            account, errors = _ACCOUNT.authenticate(
                username=username, password=password, ip=address, session=session
            )

        if account:
            if new_user:
                session.msg("|gA new account |c{}|g was created. Welcome!|n".format(username))
            # pass login info to login node
            return "node_quit_or_login", {"login": True, "account": account}
        else:
            # restart due to errors
            session.msg("|R{}".format("\n".join(errors)))
            kwargs["retry_password"] = True
            return "node_enter_password", kwargs

    def _restart_login(caller, *args, **kwargs):
        caller.msg("|yCancelled login.|n")
        return "node_enter_username"

    username = kwargs["username"]
    if kwargs["new_user"]:

        if kwargs.get("retry_password"):
            # Attempting to fix password
            text = "Enter a new password:"
        else:
            text = "Creating a new account |c{}|n. " "Enter a password (empty to abort):".format(
                username
            )
    else:
        text = "Enter the password for account |c{}|n (empty to abort):".format(username)
    options = (
        {"key": "", "goto": _restart_login},
        {"key": ("quit", "q"), "goto": "node_quit_or_login"},
        {"key": ("help", "h"), "goto": (_show_help, {"help_entry": _PASSWORD_HELP, **kwargs})},
        {"key": "_default", "goto": (_check_input, kwargs)},
    )
    return text, options


def node_quit_or_login(caller, raw_text, **kwargs):
    """
    Exit menu, either by disconnecting or logging in.

    """
    session = caller
    if kwargs.get("login"):
        account = kwargs.get("account")
        session.msg("|gLogging in ...|n")
        session.sessionhandler.login(session, account)
    else:
        session.sessionhandler.disconnect(session, "Goodbye! Logging off.")
    return "", {}


# EvMenu helper function


def _node_formatter(nodetext, optionstext, caller=None):
    """Do not display the options, only the text.

    This function is used by EvMenu to format the text of nodes. The menu login
    is just a series of prompts so we disable all automatic display decoration
    and let the nodes handle everything on their own.

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
    when the account first connects. It sets up the menu before handing off
    to the menu's own look command.

    """

    key = syscmdkeys.CMD_LOGINSTART
    locks = "cmd:all()"
    arg_regex = r"^$"

    def func(self):
        """
        Run the menu using the nodes in this module.

        """
        EvMenu(
            self.caller,
            "evennia.contrib.menu_login",
            startnode="node_enter_username",
            auto_look=False,
            auto_quit=False,
            cmd_on_exit=None,
            node_formatter=_node_formatter,
        )
