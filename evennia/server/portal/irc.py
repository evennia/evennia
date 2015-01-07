"""
This connects to an IRC network/channel and launches an 'bot' onto it.
The bot then pipes what is being said between the IRC channel and one or
more Evennia channels.
"""

from twisted.application import internet
from twisted.words.protocols import irc
from twisted.internet import protocol
from src.server.session import Session
from src.utils import logger


# IRC bot

class IRCBot(irc.IRCClient, Session):
    """
    An IRC bot that tracks actitivity in a channel as well
    as sends text to it when prompted
    """
    lineRate = 1

    # assigned by factory at creation

    nickname = None
    logger = None
    factory = None
    channel = None

    def signedOn(self):
        """
        This is called when we successfully connect to
        the network. We make sure to now register with
        the game as a full session.
        """
        self.join(self.channel)
        self.stopping = False
        self.factory.bot = self
        address = "%s@%s" % (self.channel, self.network)
        self.init_session("ircbot", address, self.factory.sessionhandler)
        # we link back to our bot and log in
        self.uid = int(self.factory.uid)
        self.logged_in = True
        self.factory.sessionhandler.connect(self)
        logger.log_infomsg("IRC bot '%s' connected to %s at %s:%s." % (self.nickname, self.channel,
                                                                              self.network, self.port))

    def disconnect(self, reason=None):
        """
        Called by sessionhandler to disconnect this protocol
        """
        print "irc disconnect called!"
        self.sessionhandler.disconnect(self)
        self.stopping = True
        self.transport.loseConnection()

    def privmsg(self, user, channel, msg):
        "A message was sent to channel"
        if not msg.startswith('***'):
            user = user.split('!', 1)[0]
            self.data_in("bot_data_in %s@%s: %s" % (user, channel, msg))

    def action(self, user, channel, msg):
        "An action was done in channel"
        if not msg.startswith('**'):
            user = user.split('!', 1)[0]
            self.data_in("bot_data_in %s@%s %s" % (user, channel, msg))

    def data_in(self, text=None, **kwargs):
        "Data IRC -> Server"
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        "Data from server-> IRC"
        if text.startswith("bot_data_out"):
            text = text.split(" ", 1)[1]
            self.say(self.channel, text)


class IRCBotFactory(protocol.ReconnectingClientFactory):
    """
    Creates instances of AnnounceBot, connecting with
    a staggered increase in delay
    """
    # scaling reconnect time
    initialDelay = 1
    factor = 1.5
    maxDelay = 60

    def __init__(self, sessionhandler, uid=None, botname=None, channel=None, network=None, port=None):
        "Storing some important protocol properties"
        self.sessionhandler = sessionhandler
        self.uid = uid
        self.nickname = str(botname)
        self.channel = str(channel)
        self.network = str(network)
        self.port = port
        self.bot = None

    def buildProtocol(self, addr):
        "Build the protocol and assign it some properties"
        protocol = IRCBot()
        protocol.factory = self
        protocol.nickname = self.nickname
        protocol.channel = self.channel
        protocol.network = self.network
        protocol.port = self.port
        return protocol

    def startedConnecting(self, connector):
        "Tracks reconnections for debugging"
        logger.log_infomsg("(re)connecting to %s" % self.channel)

    def clientConnectionFailed(self, connector, reason):
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        if not self.bot.stopping:
            self.retry(connector)

    def start(self):
        "Connect session to sessionhandler"
        if self.port:
            service = internet.TCPClient(self.network, int(self.port), self)
            self.sessionhandler.portal.services.addService(service)
