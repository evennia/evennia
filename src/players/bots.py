"""
Bots are a special child typeclasses of
Player that are  controlled by the server.

"""

from src.players.player import Player
from src.scripts.script import Script
from src.commands.command import Command
from src.commands.cmdset import CmdSet
from src.commands.cmdhandler import CMD_NOMATCH

_SESSIONS = None

class BotStarter(Script):
    """
    This non-repeating script has the
    sole purpose of kicking its bot
    into gear when it is initialized.
    """
    def at_script_creation(self):
        self.key = "botstarter"
        self.desc = "kickstarts bot"
        self.persistent = True
        self.db.started = False

    def at_start(self):
        "Kick bot into gear"
        if not self.db.started:
            self.obj.start()
            self.db.started = False

    def at_server_reload(self):
        """
        If server reloads we don't need to start the bot again,
        the Portal resync will do that for us.
        """
        self.db.started = True

    def at_server_shutdown(self):
        "Make sure we are shutdown"
        self.db.started = False


class CmdBotListen(Command):
    """
    This is a catch-all command that absorbs
    all input coming into the bot through its
    session and pipes it into its execute_cmd
    method.
    """
    key = CMD_NOMATCH

    def func(self):
        text = self.cmdname + self.args
        self.obj.execute_cmd(text, sessid=self.sessid)


class BotCmdSet(CmdSet):
    "Holds the BotListen command"
    key = "botcmdset"
    def at_cmdset_creation(self):
        self.add(CmdBotListen())


class Bot(Player):
    """
    A Bot will start itself when the server
    starts (it will generally not do so
    on a reload - that will be handled by the
    normal Portal session resync)
    """
    def at_player_creation(self):
        """
        Called when the bot is first created. It sets
        up the cmdset and the botstarter script
        """
        self.cmdset.add_default(BotCmdSet)
        script_key = "botstarter_%s" % self.key
        self.scripts.add(BotStarter, key=script_key)
        self.is_bot = True

    def start(self):
        """
        This starts the bot, usually by connecting
        to a protocol.
        """
        pass

    def msg(self, text=None, from_obj=None, sessid=None, **kwargs):
        """
        Evennia -> outgoing protocol
        """
        pass

    def execute_cmd(self, raw_string, sessid=None):
        """
        Incoming protocol -> Evennia
        """
        pass


class IRCBot(Bot):
    """
    Bot for handling IRC connections
    """
    def start(self):
        "Start by telling the portal to start a new session"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        # instruct the server and portal to create a new session
        _SESSIONS.start_bot_session("src.server.portal.irc.IRCClient", self.id)

    def connect_to_channel(self, channelname):
        """
        Connect the bot to an Evennia channel
        """
        pass

    def msg(self, text=None, **kwargs):
        """
        Takes text from connected channel (only)
        """
        if "from_channel" in kwargs and text:
            # a channel receive. This is the only one we deal with
            channel = kwargs.pop("from_channel")
            ckey = channel.key
            text = "[%s] %s" % (ckey, text)
            self.dbobj.msg(text=text)


    def execute_cmd(
