"""
Bots are a special child typeclasses of
Player that are  controlled by the server.

"""

from django.conf import settings
from evennia.players.players import DefaultPlayer
from evennia.scripts.scripts import DefaultScript
from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from evennia.utils import search

_IDLE_TIMEOUT = settings.IDLE_TIMEOUT

_SESSIONS = None


# Bot helper utilities

class BotStarter(DefaultScript):
    """
    This non-repeating script has the
    sole purpose of kicking its bot
    into gear when it is initialized.
    """
    def at_script_creation(self):
        self.key = "botstarter"
        self.desc = "bot start/keepalive"
        self.persistent = True
        self.db.started = False
        if _IDLE_TIMEOUT > 0:
            # call before idle_timeout triggers
            self.interval = int(max(60, _IDLE_TIMEOUT * 0.90))
            self.start_delay = True

    def at_start(self):
        "Kick bot into gear"
        if not self.db.started:
            self.player.start()
            self.db.started = True

    def at_repeat(self):
        """
        Called self.interval seconds to keep connection. We cannot use
        the IDLE command from inside the game since the system will
        not catch it (commands executed from the server side usually
        has no sessions). So we update the idle counter manually here
        instead. This keeps the bot getting hit by IDLE_TIMEOUT.
        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        for session in _SESSIONS.sessions_from_player(self.player):
            session.update_session_counters(idle=True)

    def at_server_reload(self):
        """
        If server reloads we don't need to reconnect the protocol
        again, this is handled by the portal reconnect mechanism.
        """
        self.db.started = True

    def at_server_shutdown(self):
        "Make sure we are shutdown"
        self.db.started = False


class CmdBotListen(Command):
    """
    This is a command that absorbs input
    aimed specifically at the bot. The session
    must prepend its data with bot_data_in for
    this to trigger.
    """
    key = "bot_data_in"
    def func(self):
        "Relay to typeclass"
        self.obj.execute_cmd(self.args.strip(), sessid=self.sessid)

class BotCmdSet(CmdSet):
    "Holds the BotListen command"
    key = "botcmdset"
    def at_cmdset_creation(self):
        self.add(CmdBotListen())


# Bot base class

class Bot(DefaultPlayer):
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
        lockstring = "examine:perm(Wizards);edit:perm(Wizards);delete:perm(Wizards);boot:perm(Wizards);msg:false()"
        self.locks.add(lockstring)
        # set the basics of being a bot
        self.cmdset.add_default(BotCmdSet)
        script_key = "%s" % self.key
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
        super(Bot, self).msg(text=text, from_obj=from_obj, sessid=sessid, **kwargs)

    def execute_cmd(self, raw_string, sessid=None):
        """
        Incoming protocol -> Evennia
        """
        super(Bot, self).msg(raw_string, sessid=sessid)

    def at_server_shutdown(self):
        "We need to handle this case manually since the shutdown may be a reset"
        print "bots at_server_shutdown called"
        for session in self.get_all_sessions():
            session.sessionhandler.disconnect(session)


# Bot implementations

# IRC

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
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS

        # if keywords are given, store (the BotStarter script
        # will not give any keywords, so this should normally only
        # happen at initialization)
        if irc_botname:
            self.db.irc_botname = irc_botname
        elif not self.db.irc_botname:
            self.db.irc_botname = self.key
        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError("Evennia Channel '%s' not found." % ev_channel)
            channel = channel[0]
            channel.connect(self)
            self.db.ev_channel = channel
        if irc_channel:
            self.db.irc_channel = irc_channel
        if irc_network:
            self.db.irc_network = irc_network
        if irc_port:
            self.db.irc_port = irc_port

        # instruct the server and portal to create a new session with
        # the stored configuration
        configdict = {"uid":self.dbid,
                      "botname": self.db.irc_botname,
                      "channel": self.db.irc_channel ,
                      "network": self.db.irc_network,
                      "port": self.db.irc_port}
        _SESSIONS.start_bot_session("evennia.server.portal.irc.IRCBotFactory", configdict)

    def msg(self, text=None, **kwargs):
        """
        Takes text from connected channel (only)
        """
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if "from_channel" in kwargs and text and self.ndb.ev_channel.dbid == kwargs["from_channel"]:
            if "from_obj" not in kwargs or kwargs["from_obj"] != [self.id]:
                text = "bot_data_out %s" % text
                super(IRCBot, self).msg(text=text)

    def execute_cmd(self, text=None, sessid=None):
        """
        Take incoming data and send it to connected channel. This is triggered
        by the CmdListen command in the BotCmdSet.
        """
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if self.ndb.ev_channel:
            self.ndb.ev_channel.msg(text, senders=self.id)

# RSS

class RSSBot(Bot):
    """
    An RSS relayer. The RSS protocol itself runs a ticker to update its feed at regular
    intervals.
    """
    def start(self, ev_channel=None, rss_url=None, rss_rate=None):
        """
        Start by telling the portal to start a new RSS session

        ev_channel - key of the Evennia channel to connect to
        rss_url - full URL to the RSS feed to subscribe to
        rss_update_rate - how often for the feedreader to update
        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS

        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError("Evennia Channel '%s' not found." % ev_channel)
            channel = channel[0]
            self.db.ev_channel = channel
        if rss_url:
            self.db.rss_url = rss_url
        if rss_rate:
            self.db.rss_rate = rss_rate
        # instruct the server and portal to create a new session with
        # the stored configuration
        configdict = {"uid": self.dbid,
                      "url": self.db.rss_url,
                      "rate": self.db.rss_rate}
        _SESSIONS.start_bot_session("evennia.server.portal.rss.RSSBotFactory", configdict)

    def execute_cmd(self, text=None, sessid=None):
        """
        Echo RSS input to connected channel
        """
        print "execute_cmd rss:", text
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if self.ndb.ev_channel:
            self.ndb.ev_channel.msg(text, senders=self.id)

# IMC2

class IMC2Bot(Bot):
    """
    IMC2 Bot
    """
    def start(self, ev_channel=None, imc2_network=None, imc2_mudname=None,
              imc2_port=None, imc2_client_pwd=None, imc2_server_pwd=None):
        """
        Start by telling the portal to start a new session
        ev_channel - key of the Evennia channel to connect to
        imc2_network - IMC2 network name
        imc2_mudname - registered mudname (if not given, use settings.SERVERNAME)
        imc2_port - port number of IMC2 network
        imc2_client_pwd - client password registered with IMC2 network
        imc2_server_pwd - server password registered with IMC2 network
        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        if ev_channel:
            # connect to Evennia channel
            channel = search.channel_search(ev_channel)
            if not channel:
                raise RuntimeError("Evennia Channel '%s' not found." % ev_channel)
            channel = channel[0]
            channel.connect(self)
            self.db.ev_channel = channel
        if imc2_network:
            self.db.imc2_network = imc2_network
        if imc2_port:
            self.db.imc2_port = imc2_port
        if imc2_mudname:
            self.db.imc2_mudname = imc2_mudname
        elif not self.db.imc2_mudname:
            self.db.imc2_mudname = settings.SERVERNAME
        # storing imc2 passwords in attributes - a possible
        # security issue?
        if imc2_server_pwd:
            self.db.imc2_server_pwd = imc2_server_pwd
        if imc2_client_pwd:
            self.db.imc2_client_pwd = imc2_client_pwd

        configdict = {"uid": self.dbid,
                      "mudname": self.db.imc2_mudname,
                      "network": self.db.imc2_network,
                      "port": self.db.imc2_port,
                      "client_pwd": self.db.client_pwd,
                      "server_pwd": self.db.server_pwd}

        _SESSIONS.start_bot_session("evennia.server.portal.imc2.IMC2BotFactory", configdict)

    def msg(self, text=None, **kwargs):
        """
        Takes text from connected channel (only)
        """
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if "from_channel" in kwargs and text and self.ndb.ev_channel.dbid == kwargs["from_channel"]:
            if "from_obj" not in kwargs or kwargs["from_obj"] != [self.id]:
                text = "bot_data_out %s" % text
                self.msg(text=text)

    def execute_cmd(self, text=None, sessid=None):
        """
        Relay incoming data to connected channel.
        """
        if not self.ndb.ev_channel and self.db.ev_channel:
            # cache channel lookup
            self.ndb.ev_channel = self.db.ev_channel
        if self.ndb.ev_channel:
            self.ndb.ev_channel.msg(text, senders=self.id)

