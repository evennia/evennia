"""
Commands that are available from the connect screen.
"""
import re
import traceback
from django.conf import settings
from django.contrib.auth.models import User
from src.players.models import PlayerDB
from src.objects.models import ObjectDB
from src.server.models import ServerConfig
from src.comms.models import Channel

from src.utils import create, logger, utils, ansi
from src.commands.default.muxcommand import MuxCommand
from src.commands.cmdhandler import CMD_LOGINSTART

# limit symbol import for API
__all__ = ("CmdUnconnectedConnect", "CmdUnconnectedCreate", "CmdUnconnectedQuit", "CmdUnconnectedLook", "CmdUnconnectedHelp")

CONNECTION_SCREEN_MODULE = settings.CONNECTION_SCREEN_MODULE
CONNECTION_SCREEN = ""
try:
    CONNECTION_SCREEN = ansi.parse_ansi(utils.string_from_module(CONNECTION_SCREEN_MODULE))
except Exception:
    pass
if not CONNECTION_SCREEN:
    CONNECTION_SCREEN = "\nEvennia: Error in CONNECTION_SCREEN MODULE (randomly picked connection screen variable is not a string). \nEnter 'help' for aid."

class CmdUnconnectedConnect(MuxCommand):
    """
    Connect to the game.

    Usage (at login screen):
      connect playername password
      connect "player name" "pass word"

    Use the create command to first create an account before logging in.

    If you have spaces in your name, enclose it in quotes.
    """
    key = "connect"
    aliases = ["conn", "con", "co"]
    locks = "cmd:all()" # not really needed

    def func(self):
        """
        Uses the Django admin api. Note that unlogged-in commands
        have a unique position in that their func() receives
        a session object instead of a source_object like all
        other types of logged-in commands (this is because
        there is no object yet before the player has logged in)
        """

        session = self.caller
        args = self.args
        # extract quoted parts
        parts = [part.strip() for part in re.split(r"\"|\'", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no quotes being found
            parts = parts[0].split(None, 1)
        if len(parts) != 2:
            session.msg("\n\r Usage (without <>): connect <name> <password>")
            return
        playername, password = parts

        # Match account name and check password
        player = PlayerDB.objects.get_player_from_name(playername)
        pswd = None
        if player:
            pswd = player.user.check_password(password)

        if not (player and pswd):
        # No playername or password match
            string = "Wrong login information given.\nIf you have spaces in your name or "
            string += "password, don't forget to enclose it in quotes. Also capitalization matters."
            string += "\nIf you are new you should first create a new account "
            string += "using the 'create' command."
            session.msg(string)
            return

        # Check IP and/or name bans
        bans = ServerConfig.objects.conf("server_bans")
        if bans and (any(tup[0]==player.name for tup in bans)
                     or
                     any(tup[2].match(session.address[0]) for tup in bans if tup[2])):
            # this is a banned IP or name!
            string = "{rYou have been banned and cannot continue from here."
            string += "\nIf you feel this ban is in error, please email an admin.{x"
            session.msg(string)
            session.execute_cmd("quit")
            return

        # actually do the login. This will call all other hooks:
        #   session.at_init()
        #   if character:
        #      at_first_login()  # only once
        #      at_pre_login()
        #   player.at_post_login()     - calls look if no character is set
        #   character.at_post_login()  - this calls look command by default
        session.session_login(player)

class CmdUnconnectedCreate(MuxCommand):
    """
    Create a new account.

    Usage (at login screen):
      create <playername> <password>
      create "player name" "pass word"

    This creates a new player account.

    If you have spaces in your name, enclose it in quotes.
    """
    key = "create"
    aliases = ["cre", "cr"]
    locks = "cmd:all()"

    def func(self):
        "Do checks and create account"

        session = self.caller
        args = self.args.strip()

        # extract quoted parts
        parts = [part.strip() for part in re.split(r"\"|\'", args) if part.strip()]
        if len(parts) == 1:
            # this was (hopefully) due to no quotes being found
            parts = parts[0].split(None, 1)
        if len(parts) != 2:
            string = "\n Usage (without <>): create <name> <password>"
            string += "\nIf <name> or <password> contains spaces, enclose it in quotes."
            session.msg(string)
            return
        playername, password = parts

        # sanity checks
        if not re.findall('^[\w. @+-]+$', playername) or not (0 < len(playername) <= 30):
            # this echoes the restrictions made by django's auth module (except not
            # allowing spaces, for convenience of logging in).
            string = "\n\r Playername can max be 30 characters or fewer. Letters, spaces, digits and @/./+/-/_ only."
            session.msg(string)
            return
        # strip excessive spaces in playername
        playername = re.sub(r"\s+", " ", playername).strip()
        if PlayerDB.objects.filter(user__username__iexact=playername) or User.objects.filter(username__iexact=playername):
            # player already exists (we also ignore capitalization here)
            session.msg("Sorry, there is already a player with the name '%s'." % playername)
            return
        if not re.findall('^[\w. @+-]+$', password) or not (3 < len(password)):
            string = "\n\r Password should be longer than 3 characers. Letters, spaces, digits and @\.\+\-\_ only."
            string += "\nFor best security, make it longer than 8 characters. You can also use a phrase of"
            string += "\nmany words if you enclose the password in quotes."
            session.msg(string)
            return

        # everything's ok. Create the new player account.
        try:
            default_home = ObjectDB.objects.get_id(settings.CHARACTER_DEFAULT_HOME)

            typeclass = settings.BASE_CHARACTER_TYPECLASS
            permissions = settings.PERMISSION_PLAYER_DEFAULT

            try:
                new_character = create.create_player(playername, None, password,
                                                     permissions=permissions,
                                                     character_typeclass=typeclass,
                                                     character_location=default_home,
                                                     character_home=default_home)
            except Exception:
                session.msg("There was an error creating the default Character/Player:\n%s\n If this problem persists, contact an admin.")
                return
            new_player = new_character.player

            # This needs to be called so the engine knows this player is logging in for the first time.
            # (so it knows to call the right hooks during login later)
            utils.init_new_player(new_player)

            # join the new player to the public channel
            pchanneldef = settings.CHANNEL_PUBLIC
            if pchanneldef:
                pchannel = Channel.objects.get_channel(pchanneldef[0])
                if not pchannel.connect_to(new_player):
                    string = "New player '%s' could not connect to public channel!" % new_player.key
                    logger.log_errmsg(string)

            # allow only the character itself and the player to puppet this character (and Immortals).
            new_character.locks.add("puppet:id(%i) or pid(%i) or perm(Immortals) or pperm(Immortals)" %
                                    (new_character.id, new_player.id))


            # If no description is set, set a default description
            if not new_character.db.desc:
                new_character.db.desc = "This is a Player."

            # tell the caller everything went well.
            string = "A new account '%s' was created. Welcome!"
            if " " in playername:
                string += "\n\nYou can now log in with the command 'connect \"%s\" <your password>'."
            else:
                string += "\n\nYou can now log with the command 'connect %s <your password>'."
            session.msg(string % (playername, playername))

        except Exception:
            # We are in the middle between logged in and -not, so we have to handle tracebacks
            # ourselves at this point. If we don't, we won't see any errors at all.
            string = "%s\nThis is a bug. Please e-mail an admin if the problem persists."
            session.msg(string % (traceback.format_exc()))
            logger.log_errmsg(traceback.format_exc())

class CmdUnconnectedQuit(MuxCommand):
    """
    We maintain a different version of the quit command
    here for unconnected players for the sake of simplicity. The logged in
    version is a bit more complicated.
    """
    key = "quit"
    aliases = ["q", "qu"]
    locks = "cmd:all()"

    def func(self):
        "Simply close the connection."
        session = self.caller
        session.msg("Good bye! Disconnecting ...")
        session.session_disconnect()

class CmdUnconnectedLook(MuxCommand):
    """
    This is an unconnected version of the look command for simplicity.

    This is called by the server and kicks everything in gear.
    All it does is display the connect screen.
    """
    key = CMD_LOGINSTART
    aliases = ["look", "l"]
    locks = "cmd:all()"

    def func(self):
        "Show the connect screen."
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
        "Shows help"

        string = \
            """
You are not yet logged into the game. Commands available at this point:
  {wcreate, connect, look, help, quit{n

To login to the system, you need to do one of the following:

{w1){n If you have no previous account, you need to use the 'create'
   command.

     {wcreate Anna c67jHL8p{n

   Note that if you use spaces in your name, you have to enclose in quotes.

     {wcreate "Anna the Barbarian"  c67jHL8p{n

   It's always a good idea (not only here, but everywhere on the net)
   to not use a regular word for your password. Make it longer than
   6 characters or write a passphrase.

{w2){n If you have an account already, either because you just created
   one in {w1){n above or you are returning, use the 'connect' command:

     {wconnect Anna c67jHL8p{n

   (Again, if there are spaces in the name you have to enclose it in quotes).
   This should log you in. Run {whelp{n again once you're logged in
   to get more aid. Hope you enjoy your stay!

You can use the {wlook{n command if you want to see the connect screen again.
"""
        self.caller.msg(string)
