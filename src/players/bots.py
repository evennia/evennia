"""
Bots are a special child typeclasses of
Player that are  controlled by the server.

"""

from src.players.player import Player
from src.scripts.script import Script
from src.commands.command import Command
from src.commands.cmdset import CmdSet
from src.commands.cmdhandler import CMD_NOMATCH
from src.utils import search

_SESSIONS = None


# Bot helper utilities

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


# Bot base class

class Bot(Player):
    """
    A Bot will start itself when the server
    starts (it will generally not do so
    on a reload - that will be handled by the
    normal Portal session resync)
    """

    def basetype_setup(self):
        """
        This sets up the basic properties for the bot.
        """
        # the text encoding to use.
        self.db.encoding = "utf-8"
        # A basic security setup
        lockstring = "examine:perm(Wizards);edit:perm(Wizards);delete:perm(Wizards);boot:perm(Wizards);msg:all()"
        self.locks.add(lockstring)
        # set the basics of being a bot
        self.cmdset.add_default(BotCmdSet)
        script_key = "botstarter_%s" % self.key
        self.scripts.add(BotStarter, key=script_key)
        self.is_bot = True

    def start(self, **kwargs):
        """
        This starts the bot, whatever that may mean.
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


# Bot implementations

class IRCBot(Bot):
    """
    Bot for handling IRC connections.
    """
    def start(self, ev_channel=None, irc_botname=None, irc_channel=None, irc_network=None, irc_port=None):
        """
        Start by telling the portal to start a new session.

        ev_channel - key of the Evennia channel to connect to
        irc_botname - name of bot to connect to irc channel. If not set, use self.key
        irc_channel - name of channel on the form #channelname
        irc_network - url of network, like irc.freenode.net
        irc_port - port number of irc network, like 6667
        """
        global _SESSIONS, _CHANNELDB
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS

        # if keywords are given, store (the BotStarter script
        # will not give any keywords, so this should normally only
        # happen at initialization)
        self.db.irc_botname = irc_botname if irc_botname else self.key
        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError("Evennia Channel '%s' not found." % ev_channel)
            channel.connect(self)
            self.db.ev_channel = channel
        if irc_channel:
            self.db.irc_channel = irc_channel
        if irc_network:
            self.db.irc_network = irc_network
        if irc_port:
            self.db.irc_port = irc_port

        # cache channel
        self.ndb.ev_channel = self.db.ev_channel

        # instruct the server and portal to create a new session with
        # the stored configuration
        configdict = {"botname": self.db.irc_botname,
                      "channel": self.db.irc_channel ,
                      "network": self.db.irc_network,
                      "port": self.db.irc_port}
        _SESSIONS.start_bot_session("src.server.portal.irc.IRCClient", self.id, configdict)

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

    def execute_cmd(self, text=None, sessid=None):
        """
        Take incoming data and send it to connected channel. This is triggered
        by the CmdListen command in the BotCmdSet.
        """
        if self.ndb.channel:
            self.ndb.channel.msg(text)
