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

CMDSET_UNLOGGEDIN = "contrib.menu_login.UnloggedInCmdSet"

That's it. Reload the server and try to log in to see it.

The initial login "graphic" is taken from strings in the module given
by settings.CONNECTION_SCREEN_MODULE. You will want to copy the
template file in game/gamesrc/conf/examples up one level and re-point
the settings file to this custom module. you can then edit the string
in that module (at least comment out the default string that mentions
commands that are not available) and add something more suitable for
the initial splash screen.

"""

import re
import traceback
from django.conf import settings
from ev import managers
from ev import utils, logger, create_player
from ev import Command, CmdSet
from ev import syscmdkeys
from src.server.models import ServerConfig

from contrib.menusystem import MenuNode, MenuTree

CMD_LOGINSTART = syscmdkeys.CMD_LOGINSTART
CMD_NOINPUT = syscmdkeys.CMD_NOINPUT
CMD_NOMATCH = syscmdkeys.CMD_NOMATCH

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


class CmdPasswordSelect(Command):
    """
    Handles the entering of a password and logs into the game.
    """
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
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

        # we are logged in. Look around.
        character = player.character
        if character:
            character.execute_cmd("look")
        else:
            # we have no character yet; use player's look, if it exists
            player.execute_cmd("look")


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
        self.menutree.goto("node2b")


# Menu entry 2b - Creating a Password

class CmdPasswordCreateBack(Command):
    "Step back from the password creation"
    key = CMD_NOINPUT
    locks = "cmd:all()"

    def func(self):
        "Execute the command"
        self.menutree.goto("node2a")


class CmdPasswordCreate(Command):
    "Handle the creation of a password. This also creates the actual Player/User object."
    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        "Execute  the command"
        password = self.args
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
        # everything's ok. Create the new player account. Don't create
        # a Character here.
        try:
            permissions = settings.PERMISSION_PLAYER_DEFAULT
            typeclass = settings.BASE_PLAYER_TYPECLASS
            new_player = create_player(playername, None, password,
                                       typeclass=typeclass,
                                       permissions=permissions)
            if not new_player:
                self.msg("There was an error creating the Player. This error was logged. Contact an admin.")
                self.menutree.goto("START")
                return
            utils.init_new_player(new_player)

            # join the new player to the public channel
            pchanneldef = settings.CHANNEL_PUBLIC
            if pchanneldef:
                pchannel = managers.channels.get_channel(pchanneldef[0])
                if not pchannel.connect_to(new_player):
                    string = "New player '%s' could not connect to public channel!" % new_player.key
                    logger.log_errmsg(string)

            # tell the caller everything went well.
            string = "{gA new account '%s' was created. Now go log in from the menu!{n"
            self.caller.msg(string % (playername))
            self.menutree.goto("START")
        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't, we
            # won't see any errors at all.
            string = "%s\nThis is a bug. Please e-mail an admin if the problem persists."
            self.caller.msg(string % (traceback.format_exc()))
            logger.log_errmsg(traceback.format_exc())


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

START = MenuNode("START", text=utils.string_from_module(CONNECTION_SCREEN_MODULE),
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
                  selectcmds=[CmdBackToStart, CmdUsernameSelect],
                  nodefaultcmds=True) # if we don't, default help/look will be triggered by names starting with l/h ...
node1b = MenuNode("node1b", text="Please enter your password (empty to go back).",
                  links=["node1a", "END"],
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdPasswordSelectBack, CmdPasswordSelect],
                  nodefaultcmds=True)

node2a = MenuNode("node2a", text="Please enter your desired account name (empty to abort).",
                  links=["START", "node2b"],
                  helptext="Account name can max be 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only.",
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdBackToStart, CmdUsernameCreate],
                  nodefaultcmds=True)
node2b = MenuNode("node2b", text="Please enter your password (empty to go back).",
                  links=["node2a", "START"],
                  helptext="Your password cannot contain any characters.",
                  keywords=[CMD_NOINPUT, CMD_NOMATCH],
                  selectcmds=[CmdPasswordCreateBack, CmdPasswordCreate],
                  nodefaultcmds=True)
node3 = MenuNode("node3", text=LOGIN_SCREEN_HELP,
                 links=["START"],
                 helptext="",
                 keywords=[CMD_NOINPUT],
                 selectcmds=[CmdBackToStart])


# access commands

class UnloggedInCmdSet(CmdSet):
    "Cmdset for the unloggedin state"
    key = "UnloggedinState"
    priority = 0

    def at_cmdset_creation(self):
        "Called when cmdset is first  created"
        self.add(CmdUnloggedinLook())


class CmdUnloggedinLook(Command):
    """
    An unloggedin version of the look command. This is called by the server
    when the player first connects. It sets up the menu before handing off
    to the menu's own look command..
    """
    key = CMD_LOGINSTART
    locks = "cmd:all()"

    def func(self):
        "Execute the menu"
        menu = MenuTree(self.caller, nodes=(START, node1a, node1b,
                                            node2a, node2b, node3),
                                            exec_end=None)
        menu.start()
