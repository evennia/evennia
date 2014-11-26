import time, re
import traceback
from django.conf import settings
from src.players.models import PlayerDB
from src.objects.models import ObjectDB
from src.server.models import ServerConfig
from src.utils import create, logger, utils, ansi
from src.commands.default.muxcommand import MuxCommand
from src.commands.cmdhandler import CMD_LOGINSTART
from src.commands.default.unloggedin import CmdUnconnectedConnect as OldUnConnect
from .. lib.IPLog.models import Login


class CmdUnconnectedConnect(OldUnConnect):
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
        super(CmdUnconnectedConnect, self).func()
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
            pswd = player.check_password(password)

        if not (player and pswd):
        # No playername or password match
            string = "Wrong login information given.\nIf you have spaces in your name or "
            string += "password, don't forget to enclose it in quotes. Also capitalization matters."
            string += "\nIf you are new you should first create a new account "
            string += "using the 'create' command."
            if player:
                logip = Login(pid=player.dbobj,type=session.protocol_key,ip=isinstance(session.address, tuple) and session.address[0] or session.address,result="invalid password")
                logip.save()
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
            logip = Login(pid=player.dbobj,type=session.protocol_key,ip=isinstance(session.address, tuple) and session.address[0] or session.address,result="banned")
            logip.save()
            session.execute_cmd("quit")
            return

        # actually do the login. This will call all other hooks:
        #   session.at_login()
        #   player.at_init()         # always called when object is loaded from disk
        #   player.at_pre_login()
        #   player.at_first_login()  # only once
        #   player.at_post_login(sessid=sessid)
        logip = Login(pid=player.dbobj,type=session.protocol_key,ip=isinstance(session.address, tuple) and session.address[0] or session.address,result="success")
        logip.save()
        session.sessionhandler.login(session, player)