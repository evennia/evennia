"""
This connects to an IRC network/channel and launches an 'bot' onto it.
The bot then pipes what is being said between the IRC channel and one or
more Evennia channels.
"""
from __future__ import print_function
from future.utils import viewkeys

import re
from twisted.application import internet
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from evennia.server.session import Session
from evennia.utils import logger, utils


# IRC colors

IRC_BOLD = "\002"
IRC_COLOR = "\003"
IRC_RESET = "\017"
IRC_ITALIC = "\026"
IRC_NORMAL = "99"
IRC_UNDERLINE = "37"

IRC_WHITE = "0"
IRC_BLACK = "1"
IRC_DBLUE = "2"
IRC_DGREEN = "3"
IRC_RED = "4"
IRC_DRED = "5"
IRC_DMAGENTA = "6"
IRC_DYELLOW = "7"
IRC_YELLOW = "8"
IRC_GREEN = "9"
IRC_DCYAN = "10"
IRC_CYAN = "11"
IRC_BLUE = "12"
IRC_MAGENTA = "13"
IRC_DGREY = "14"
IRC_GRAY = "15"

# test:
# {rred {ggreen {yyellow {bblue {mmagenta {ccyan {wwhite {xdgrey
# {Rdred {Gdgreen {Ydyellow {Bdblue {Mdmagenta {Cdcyan {Wlgrey {Xblack
# {[rredbg {[ggreenbg {[yyellowbg {[bbluebg {[mmagentabg {[ccyanbg {[wlgreybg {[xblackbg

IRC_COLOR_MAP = dict([
    (r'{n', IRC_RESET),                # reset
    (r'{/', ""),          # line break
    (r'{-', " "),             # tab
    (r'{_', " "),           # space
    (r'{*', ""),        # invert
    (r'{^', ""),          # blinking text

    (r'{r', IRC_COLOR + IRC_RED),
    (r'{g', IRC_COLOR + IRC_GREEN),
    (r'{y', IRC_COLOR + IRC_YELLOW),
    (r'{b', IRC_COLOR + IRC_BLUE),
    (r'{m', IRC_COLOR + IRC_MAGENTA),
    (r'{c', IRC_COLOR + IRC_CYAN),
    (r'{w', IRC_COLOR + IRC_WHITE),  # pure white
    (r'{x', IRC_COLOR + IRC_DGREY),  # dark grey

    (r'{R', IRC_COLOR + IRC_DRED),
    (r'{G', IRC_COLOR + IRC_DGREEN),
    (r'{Y', IRC_COLOR + IRC_DYELLOW),
    (r'{B', IRC_COLOR + IRC_DBLUE),
    (r'{M', IRC_COLOR + IRC_DMAGENTA),
    (r'{C', IRC_COLOR + IRC_DCYAN),
    (r'{W', IRC_COLOR + IRC_GRAY),  # light grey
    (r'{X', IRC_COLOR + IRC_BLACK),  # pure black

    (r'{[r', IRC_COLOR + IRC_NORMAL + "," + IRC_DRED),
    (r'{[g', IRC_COLOR + IRC_NORMAL + "," + IRC_DGREEN),
    (r'{[y', IRC_COLOR + IRC_NORMAL + "," + IRC_DYELLOW),
    (r'{[b', IRC_COLOR + IRC_NORMAL + "," + IRC_DBLUE),
    (r'{[m', IRC_COLOR + IRC_NORMAL + "," + IRC_DMAGENTA),
    (r'{[c', IRC_COLOR + IRC_NORMAL + "," + IRC_DCYAN),
    (r'{[w', IRC_COLOR + IRC_NORMAL + "," + IRC_GRAY),    # light grey background
    (r'{[x', IRC_COLOR + IRC_NORMAL + "," + IRC_BLACK)     # pure black background
    ])
RE_IRC_COLOR = re.compile(r"|".join([re.escape(key) for key in viewkeys(IRC_COLOR_MAP)]), re.DOTALL)
RE_MXP = re.compile(r'\{lc(.*?)\{lt(.*?)\{le', re.DOTALL)
RE_ANSI_ESCAPES = re.compile(r"(%s)" % "|".join(("{{", "%%", "\\\\")), re.DOTALL)

def sub_irc(ircmatch):
    """
    Substitute irc color info. Used by re.sub.

    Args:
        ircmatch (Match): The match from regex.

    Returns:
        colored (str): A string with converted IRC colors.

    """
    return IRC_COLOR_MAP.get(ircmatch.group(), "")

def parse_irc_colors(string):
    """
    Parse {-type syntax and replace with IRC color markers

    Args:
        string (str): String to parse for IRC colors.

    Returns:
        parsed_string (str): String with replaced IRC colors.

    """
    in_string = utils.to_str(string)
    parsed_string = ""
    parts = RE_ANSI_ESCAPES.split(in_string) + [" "]
    for part, sep in zip(parts[::2], parts[1::2]):
        pstring = RE_IRC_COLOR.sub(sub_irc, part)
        parsed_string += "%s%s" % (pstring, sep[0].strip())
    # strip mxp
    parsed_string = RE_MXP.sub(r'\2', parsed_string)
    return parsed_string

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
        This is called when we successfully connect to the network. We
        make sure to now register with the game as a full session.

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
        logger.log_info("IRC bot '%s' connected to %s at %s:%s." % (self.nickname, self.channel,
                                                                    self.network, self.port))

    def disconnect(self, reason=None):
        """
        Called by sessionhandler to disconnect this protocol.

        Args:
            reason (str): Motivation for the disconnect.

        """
        self.sessionhandler.disconnect(self)
        self.stopping = True
        self.transport.loseConnection()

    def privmsg(self, user, channel, msg):
        """
        Called when the connected channel receives a message.

        Args:
            user (str): User name sending the message.
            channel (str): Channel name seeing the message.
            msg (str): The message arriving from channel.

        """
        if not msg.startswith('***'):
            user = user.split('!', 1)[0]
            self.data_in("bot_data_in %s@%s: %s" % (user, channel, msg))

    def action(self, user, channel, msg):
        """
        Called when an action is detected in channel.

        Args:
            user (str): User name sending the message.
            channel (str): Channel name seeing the message.
            msg (str): The message arriving from channel.

        """
        if not msg.startswith('**'):
            user = user.split('!', 1)[0]
            self.data_in("bot_data_in %s@%s %s" % (user, channel, msg))

    def data_in(self, text=None, **kwargs):
        """
        Data IRC -> Server.

        Kwargs:
            text (str): Ingoing text.
            kwargs (any): Other data from protocol.

        """
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        """
        Data from server-> IRC.

        Kwargs:
            text (str): Outgoing text.
            kwargs (any): Other data to protocol.

        """
        if text.startswith("bot_data_out"):
            text = text.split(" ", 1)[1]
            text = parse_irc_colors(text)
            self.say(self.channel, text)


class IRCBotFactory(protocol.ReconnectingClientFactory):
    """
    Creates instances of AnnounceBot, connecting with a staggered
    increase in delay

    """
    # scaling reconnect time
    initialDelay = 1
    factor = 1.5
    maxDelay = 60

    def __init__(self, sessionhandler, uid=None, botname=None, channel=None, network=None, port=None, ssl=None):
        """
        Storing some important protocol properties.

        Args:
            sessionhandler (SessionHandler): Reference to the main Sessionhandler.

        Kwargs:
            uid (int): Bot user id.
            botname (str): Bot name (seen in IRC channel).
            channel (str): IRC channel to connect to.
            network (str): Network address to connect to.
            port (str): Port of the network.
            ssl (bool): Indicates SSL connection.

        """
        self.sessionhandler = sessionhandler
        self.uid = uid
        self.nickname = str(botname)
        self.channel = str(channel)
        self.network = str(network)
        self.port = port
        self.ssl = ssl
        self.bot = None

    def buildProtocol(self, addr):
        """
        Build the protocol and assign it some properties.

        Args:
            addr (str): Not used; using factory data.

        """
        protocol = IRCBot()
        protocol.factory = self
        protocol.nickname = self.nickname
        protocol.channel = self.channel
        protocol.network = self.network
        protocol.port = self.port
        protocol.ssl = self.ssl
        return protocol

    def startedConnecting(self, connector):
        """
        Tracks reconnections for debugging.

        Args:
            connector (Connector): Represents the connection.

        """
        logger.log_info("(re)connecting to %s" % self.channel)

    def clientConnectionFailed(self, connector, reason):
        """
        Called when Client failed to connect.

        Args:
            connector (Connection): Represents the connection.
            reason (str): The reason for the failure.

        """
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        """
        Called when Client looses connection.

        Args:
            connector (Connection): Represents the connection.
            reason (str): The reason for the failure.

        """
        if not self.bot.stopping:
            self.retry(connector)

    def start(self):
        """
        Connect session to sessionhandler.

        """
        if self.port:
            if self.ssl:
                try:
                    from twisted.internet import ssl
                    service = reactor.connectSSL(self.network, int(self.port), self, ssl.ClientContextFactory())
                except ImportError:
                    self.caller.msg("To use SSL, the PyOpenSSL module must be installed.")
            else:
                service = internet.TCPClient(self.network, int(self.port), self)
            self.sessionhandler.portal.services.addService(service)
