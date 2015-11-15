"""
Menu-driven login system

Contribution - Griatch 2011


This is an alternative login system for Evennia, using the
contrib.menusystem module. As opposed to the default system it doesn't
use emails for authentication and also don't auto-creates a Character
with the same name as the Player (instead assuming some sort of
character-creation to come next).


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
from django.conf import settings
from evennia import managers
from evennia import utils, logger, create_player
from evennia import ObjectDB
from evennia import Command, CmdSet
from evennia import syscmdkeys
from evennia.server.models import ServerConfig

from evennia.contrib.menusystem import MenuNode, MenuTree

CMD_LOGINSTART = syscmdkeys.CMD_LOGINSTART
CMD_NOINPUT = syscmdkeys.CMD_NOINPUT
CMD_NOMATCH = syscmdkeys.CMD_NOMATCH

MULTISESSION_MODE = settings.MULTISESSION_MODE
CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE


# Commands run on the unloggedin screen. Note that this is not using
# settings.UNLOGGEDIN_CMDSET but the menu system, which is why some are
# named for the numbers in the menu.
#
# Also note that the menu system will automatically assign all
# commands used in its structure a property "menutree" holding a reference
# back to the menutree. This allows the commands to do direct manipulation
# for example by triggering a conditional jump to another node.
#

# Menu entry 1a - Entering a Username

class CmdBackToStart(Command):
    """
    Step back to node0
    """
    key = CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        self.menutree.goto("START")


class CmdUsernameSelect(Command):
    """
    Handles the entering of a username and
    checks if it exists.
    """
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        player = managers.players.get_player_from_name(self.args)
        if not player:
            self.caller.msg("{rThis account name couldn't be found. Did you create it? If you did, make sure you spelled it right (case doesn't matter).{n")
            self.menutree.goto("node1a")
        else:
            # store the player so next step can find it
            self.menutree.player = player
            self.caller.msg(echo=False)
            self.menutree.goto("node1b")


# Menu entry 1b - Entering a Password

class CmdPasswordSelectBack(Command):
    """
    Steps back from the Password selection
    """
    key = CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        self.menutree.goto("node1a")
        self.caller.msg(echo=True)


class CmdPasswordSelect(Command):
    """
    Handles the entering of a password and logs into the game.
    """
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        self.caller.msg(echo=True)
        if not hasattr(self.menutree, "player"):
            self.caller.msg("{rSomething went wrong! The player was not remembered from last step!{n")
            self.menutree.goto("node1a")
            return
        player = self.menutree.player
        if not player.check_password(self.args):
            self.caller.msg("{rIncorrect password.{n")
            self.menutree.goto("node1b")
            return

        # before going on, check eventual bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (any(tup[0]==player.name.lower() for tup in bans)
                     or
                     any(tup[2].match(self.caller.address) for tup in bans if tup[2])):
            # this is a banned IP or name!
            string = "{rYou have been banned and cannot continue from here."
            string += "\nIf you feel this ban is in error, please email an admin.{x"
            self.caller.msg(string)
            self.caller.sessionhandler.disconnect(self.caller, "Good bye! Disconnecting...")
            return

        # we are ok, log us in.
        self.caller.msg("{gWelcome %s! Logging in ...{n" % player.key)
        #self.caller.session_login(player)
        self.caller.sessionhandler.login(self.caller, player)

        # abort menu, do cleanup.
        self.menutree.goto("END")


# Menu entry 2a - Creating a Username

class CmdUsernameCreate(Command):
    """
    Handle the creation of a valid username
    """
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        playername = self.args

        # sanity check on the name
        if not re.findall('^[\w. @+-]+$', playername) or not (3 <= len(playername) <= 30):
            self.caller.msg("\n\r {rAccount name should be between 3 and 30 characters. Letters, spaces, dig\
its and @/./+/-/_ only.{n") # this echoes the restrictions made by django's auth module.
            self.menutree.goto("node2a")
            return
        if managers.players.get_player_from_name(playername):
            self.caller.msg("\n\r {rAccount name %s already exists.{n" % playername)
            self.menutree.goto("node2a")
            return
        # store the name for the next step
        self.menutree.playername = playername
        self.caller.msg(echo=False)
        self.menutree.goto("node2b")


# Menu entry 2b - Creating a Password

class CmdPasswordCreateBack(Command):
    "Step back from the password creation"
    key = CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        self.caller.msg(echo=True)
        self.menutree.goto("node2a")


class CmdPasswordCreate(Command):
    "Handle the creation of a password. This also creates the actual Player/User object."
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute  the command"
        password = self.args
        self.caller.msg(echo=False)
        if not hasattr(self.menutree, 'playername'):
            self.caller.msg("{rSomething went wrong! Playername not remembered from previous step!{n")
            self.menutree.goto("node2a")
            return
        playername = self.menutree.playername
        if len(password) < 3:
            # too short password
            string = "{rYour password must be at least 3 characters or longer."
            string += "\n\rFor best security, make it at least 8 characters "
            string += "long, avoid making it a real word and mix numbers "
            string += "into it.{n"
            self.caller.msg(string)
            self.menutree.goto("node2b")
            return
        # everything's ok. Create the new player account and possibly the character
        # depending on the multisession mode

        from evennia.commands.default import unloggedin
        # we make use of the helper functions from the default set here.
        try:
            permissions = settings.PERMISSION_PLAYER_DEFAULT
            typeclass = settings.BASE_CHARACTER_TYPECLASS
            new_player = unloggedin._create_player(self.caller, playername,
                                               password, permissions)
            if new_player:
                if MULTISESSION_MODE < 2:
                    default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                    unloggedin._create_character(self.caller, new_player, typeclass,
                                                 default_home, permissions)
            # tell the caller everything went well.
            string = "{gA new account '%s' was created. Now go log in from the menu!{n"
            self.caller.msg(string % (playername))
            self.menutree.goto("START")
        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't, we
            # won't see any errors at all.
            self.caller.msg("An error occurred. Please e-mail an admin if the problem persists.")
            logger.log_trace()


# Menu entry 3 - help screen

LOGIN_SCREEN_HELP = \
    """
    Welcome to %s!

    To login you need to first create an account. This is easy and
    free to do: Choose option {w(1){n in the menu and enter an account
    name and password when prompted.  Obs- the account name is {wnot{n
    the name of the Character you will play in the game!

    It's always a good idea (not only here, but everywhere on the net)
    to not use a regular word for your password. Make it longer than 3
    characters (ideally 6 or more) and mix numbers and capitalization
    into it. The password also handles whitespace, so why not make it
    a small sentence - easy to remember, hard for a computer to crack.

    Once you have an account, use option {w(2){n to log in using the
    account name and password you specified.

    Use the {whelp{n command once you're logged in to get more
    aid. Hope you enjoy your stay!


    (return to go back)""" % settings.SERVERNAME


# Menu entry 4

class CmdUnloggedinQuit(Command):
    """
    We maintain a different version of the quit command
    here for unconnected players for the sake of simplicity. The logged in
    version is a bit more complicated.
    """
    key = "4"
    aliases = ["quit", "qu", "q"]
    locks = "cmd:all()"

    def func(self):
        "Simply close the connection."
        self.menutree.goto("END")
        self.caller.sessionhandler.disconnect(self.caller, "Good bye! Disconnecting...")


# The login menu tree, using the commands above

START = MenuNode("START", text=utils.random_string_from_module(CONNECTION_SCREEN_MODULE),
                 links=["node1a", "node2a", "node3", "END"],
                 linktexts=["Log in with an existing account",
                            "Create a new account",
                            "Help",
                            "Quit"],
                 selectcmds=[None, None, None, CmdUnloggedinQuit])

node1a = MenuNode("node1a", text="Please enter your account name (empty to abort).",
                  links=["START", "node1b"],
                  helptext=["Enter the account name you previously registered with."],
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdBackToStart, CmdUsernameSelect])
node1b = MenuNode("node1b", text="Please enter your password (empty to go back).",
                  links=["node1a", "END"],
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdPasswordSelectBack, CmdPasswordSelect])
node2a = MenuNode("node2a", text="Please enter your desired account name (empty to abort).",
                  links=["START", "node2b"],
                  helptext="Account name can max be 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.",
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdBackToStart, CmdUsernameCreate])
node2b = MenuNode("node2b", text="Please enter your password (empty to go back).",
                  links=["node2a", "START"],
                  helptext="Try to pick a long and hard-to-guess password.",
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdPasswordCreateBack, CmdPasswordCreate])
node3 = MenuNode("node3", text=LOGIN_SCREEN_HELP,
                 links=["START"],
                 helptext="",
                 keywords=[CMD_NOINPUT],
                 selectcmds=[CmdBackToStart])


# access commands

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
    key = CMD_LOGINSTART
    # obs, this should NOT have aliases for look or l, this will clash with the menu version!
    locks = "cmd:all()"
    arg_regex = r"^$"

    def func(self):
        "Execute the menu"
        menu = MenuTree(self.caller, nodes=(START, node1a, node1b,
                                            node2a, node2b, node3),
                                            exec_end=None)
        menu.start()
