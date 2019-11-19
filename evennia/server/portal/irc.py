"""
This connects to an IRC network/channel and launches an 'bot' onto it.
The bot then pipes what is being said between the IRC channel and one or
more Evennia channels.
"""

import re
from twisted.application import internet
from twisted.words.protocols import irc
from twisted.internet import protocol, reactor
from evennia.server.session import Session
from evennia.utils import logger, utils, ansi


# IRC colors

IRC_BOLD = "\002"
IRC_COLOR = "\003"
IRC_RESET = "\017"
IRC_ITALIC = "\026"
IRC_INVERT = "\x16"
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
IRC_GREY = "15"

# obsolete test:

# test evennia->irc:
# |rred |ggreen |yyellow |bblue |mmagenta |ccyan |wwhite |xdgrey
# |Rdred |Gdgreen |Ydyellow |Bdblue |Mdmagenta |Cdcyan |Wlgrey |Xblack
# |[rredbg |[ggreenbg |[yyellowbg |[bbluebg |[mmagentabg |[ccyanbg |[wlgreybg |[xblackbg

# test irc->evennia
# Use Ctrl+C <num> to produce mIRC colors in e.g. irssi

IRC_COLOR_MAP = dict(
    (
        (r"|n", IRC_COLOR + IRC_NORMAL),  # normal mode
        (r"|H", IRC_RESET),  # un-highlight
        (r"|/", "\n"),  # line break
        (r"|t", "    "),  # tab
        (r"|-", "    "),  # fixed tab
        (r"|_", " "),  # space
        (r"|*", IRC_INVERT),  # invert
        (r"|^", ""),  # blinking text
        (r"|h", IRC_BOLD),  # highlight, use bold instead
        (r"|r", IRC_COLOR + IRC_RED),
        (r"|g", IRC_COLOR + IRC_GREEN),
        (r"|y", IRC_COLOR + IRC_YELLOW),
        (r"|b", IRC_COLOR + IRC_BLUE),
        (r"|m", IRC_COLOR + IRC_MAGENTA),
        (r"|c", IRC_COLOR + IRC_CYAN),
        (r"|w", IRC_COLOR + IRC_WHITE),  # pure white
        (r"|x", IRC_COLOR + IRC_DGREY),  # dark grey
        (r"|R", IRC_COLOR + IRC_DRED),
        (r"|G", IRC_COLOR + IRC_DGREEN),
        (r"|Y", IRC_COLOR + IRC_DYELLOW),
        (r"|B", IRC_COLOR + IRC_DBLUE),
        (r"|M", IRC_COLOR + IRC_DMAGENTA),
        (r"|C", IRC_COLOR + IRC_DCYAN),
        (r"|W", IRC_COLOR + IRC_GREY),  # light grey
        (r"|X", IRC_COLOR + IRC_BLACK),  # pure black
        (r"|[r", IRC_COLOR + IRC_NORMAL + "," + IRC_DRED),
        (r"|[g", IRC_COLOR + IRC_NORMAL + "," + IRC_DGREEN),
        (r"|[y", IRC_COLOR + IRC_NORMAL + "," + IRC_DYELLOW),
        (r"|[b", IRC_COLOR + IRC_NORMAL + "," + IRC_DBLUE),
        (r"|[m", IRC_COLOR + IRC_NORMAL + "," + IRC_DMAGENTA),
        (r"|[c", IRC_COLOR + IRC_NORMAL + "," + IRC_DCYAN),
        (r"|[w", IRC_COLOR + IRC_NORMAL + "," + IRC_GREY),  # light grey background
        (r"|[x", IRC_COLOR + IRC_NORMAL + "," + IRC_BLACK),  # pure black background
    )
)
# ansi->irc
RE_ANSI_COLOR = re.compile(r"|".join([re.escape(key) for key in IRC_COLOR_MAP.keys()]), re.DOTALL)
RE_MXP = re.compile(r"\|lc(.*?)\|lt(.*?)\|le", re.DOTALL)
RE_ANSI_ESCAPES = re.compile(r"(%s)" % "|".join(("{{", "%%", "\\\\")), re.DOTALL)
# irc->ansi
_CLR_LIST = [
    re.escape(val) for val in sorted(IRC_COLOR_MAP.values(), key=len, reverse=True) if val.strip()
]
_CLR_LIST = _CLR_LIST[-2:] + _CLR_LIST[:-2]
RE_IRC_COLOR = re.compile(r"|".join(_CLR_LIST), re.DOTALL)
ANSI_COLOR_MAP = dict((tup[1], tup[0]) for tup in IRC_COLOR_MAP.items() if tup[1].strip())


def parse_ansi_to_irc(string):
    """
    Parse |-type syntax and replace with IRC color markers

    Args:
        string (str): String to parse for ANSI colors.

    Returns:
        parsed_string (str): String with replaced ANSI colors.

    """

    def _sub_to_irc(ansi_match):
        return IRC_COLOR_MAP.get(ansi_match.group(), "")

    in_string = utils.to_str(string)
    parsed_string = []
    parts = RE_ANSI_ESCAPES.split(in_string) + [" "]
    for part, sep in zip(parts[::2], parts[1::2]):
        pstring = RE_ANSI_COLOR.sub(_sub_to_irc, part)
        parsed_string.append("%s%s" % (pstring, sep[0].strip()))
    # strip mxp
    parsed_string = RE_MXP.sub(r"\2", "".join(parsed_string))
    return parsed_string


def parse_irc_to_ansi(string):
    """
    Parse IRC mIRC color syntax and replace with Evennia ANSI color markers

    Args:
        string (str): String to parse for IRC colors.

    Returns:
        parsed_string (str): String with replaced IRC colors.

    """

    def _sub_to_ansi(irc_match):
        return ANSI_COLOR_MAP.get(irc_match.group(), "")

    in_string = utils.to_str(string)
    pstring = RE_IRC_COLOR.sub(_sub_to_ansi, in_string)
    return pstring


# IRC bot


class IRCBot(irc.IRCClient, Session):
    """
    An IRC bot that tracks activity in a channel as well
    as sends text to it when prompted

    """

    lineRate = 1

    # assigned by factory at creation

    nickname = None
    logger = None
    factory = None
    channel = None
    sourceURL = "http://code.evennia.com"

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
        logger.log_info(
            "IRC bot '%s' connected to %s at %s:%s."
            % (self.nickname, self.channel, self.network, self.port)
        )

    def disconnect(self, reason=""):
        """
        Called by sessionhandler to disconnect this protocol.

        Args:
            reason (str): Motivation for the disconnect.

        """
        self.sessionhandler.disconnect(self)
        self.stopping = True
        self.transport.loseConnection()

    def at_login(self):
        pass

    def privmsg(self, user, channel, msg):
        """
        Called when the connected channel receives a message.

        Args:
            user (str): User name sending the message.
            channel (str): Channel name seeing the message.
            msg (str): The message arriving from channel.

        """
        if channel == self.nickname:
            # private message
            user = user.split("!", 1)[0]
            self.data_in(text=msg, type="privmsg", user=user, channel=channel)
        elif not msg.startswith("***"):
            # channel message
            user = user.split("!", 1)[0]
            user = ansi.raw(user)
            self.data_in(text=msg, type="msg", user=user, channel=channel)

    def action(self, user, channel, msg):
        """
        Called when an action is detected in channel.

        Args:
            user (str): User name sending the message.
            channel (str): Channel name seeing the message.
            msg (str): The message arriving from channel.

        """
        if not msg.startswith("**"):
            user = user.split("!", 1)[0]
            self.data_in(text=msg, type="action", user=user, channel=channel)

    def get_nicklist(self):
        """
        Retrieve name list from the channel. The return
        is handled by the catch methods below.

        """
        if not self.nicklist:
            self.sendLine("NAMES %s" % self.channel)

    def irc_RPL_NAMREPLY(self, prefix, params):
        """"Handles IRC NAME request returns (nicklist)"""
        channel = params[2].lower()
        if channel != self.channel.lower():
            return
        self.nicklist += params[3].split(" ")

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        """Called when the nicklist has finished being returned."""
        channel = params[1].lower()
        if channel != self.channel.lower():
            return
        self.data_in(
            text="", type="nicklist", user="server", channel=channel, nicklist=self.nicklist
        )
        self.nicklist = []

    def pong(self, user, time):
        """
        Called with the return timing from a PING.

        Args:
            user (str): Name of user
            time (float): Ping time in secs.

        """
        self.data_in(text="", type="ping", user="server", channel=self.channel, timing=time)

    def data_in(self, text=None, **kwargs):
        """
        Data IRC -> Server.

        Kwargs:
            text (str): Ingoing text.
            kwargs (any): Other data from protocol.

        """
        self.sessionhandler.data_in(self, bot_data_in=[parse_irc_to_ansi(text), kwargs])

    def send_channel(self, *args, **kwargs):
        """
        Send channel text to IRC channel (visible to all). Note that
        we don't handle the "text" send (it's rerouted to send_default
        which does nothing) - this is because the IRC bot is a normal
        session and would otherwise report anything that happens to it
        to the IRC channel (such as it seeing server reload messages).

        Args:
            text (str): Outgoing text

        """
        text = args[0] if args else ""
        if text:
            text = parse_ansi_to_irc(text)
            self.say(self.channel, text)

    def send_privmsg(self, *args, **kwargs):
        """
        Send message only to specific user.

        Args:
            text (str): Outgoing text.

        Kwargs:
            user (str): the nick to send
                privately to.

        """
        text = args[0] if args else ""
        user = kwargs.get("user", None)
        if text and user:
            text = parse_ansi_to_irc(text)
            self.msg(user, text)

    def send_request_nicklist(self, *args, **kwargs):
        """
        Send a request for the channel nicklist. The return (handled
        by `self.irc_RPL_ENDOFNAMES`) will be sent back as a message
        with type `nicklist'.
        """
        self.get_nicklist()

    def send_ping(self, *args, **kwargs):
        """
        Send a ping. The return (handled by `self.pong`) will be sent
        back as a message of type 'ping'.
        """
        self.ping(self.nickname)

    def send_reconnect(self, *args, **kwargs):
        """
        The server instructs us to rebuild the connection by force,
        probably because the client silently lost connection.
        """
        self.factory.reconnect()

    def send_default(self, *args, **kwargs):
        """
        Ignore other types of sends.

        """
        pass


class IRCBotFactory(protocol.ReconnectingClientFactory):
    """
    Creates instances of IRCBot, connecting with a staggered
    increase in delay

    """

    # scaling reconnect time
    initialDelay = 1
    factor = 1.5
    maxDelay = 60

    def __init__(
        self,
        sessionhandler,
        uid=None,
        botname=None,
        channel=None,
        network=None,
        port=None,
        ssl=None,
    ):
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
        self.nicklists = {}

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
        protocol.nicklist = []
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
        Called when Client loses connection.

        Args:
            connector (Connection): Represents the connection.
            reason (str): The reason for the failure.

        """
        if not (self.bot or (self.bot and self.bot.stopping)):
            self.retry(connector)

    def reconnect(self):
        """
        Force a reconnection of the bot protocol. This requires
        de-registering the session and then reattaching a new one,
        otherwise you end up with an ever growing number of bot
        sessions.

        """
        self.bot.stopping = True
        self.bot.transport.loseConnection()
        self.sessionhandler.server_disconnect(self.bot)
        self.start()

    def start(self):
        """
        Connect session to sessionhandler.

        """
        if self.port:
            if self.ssl:
                try:
                    from twisted.internet import ssl

                    service = reactor.connectSSL(
                        self.network, int(self.port), self, ssl.ClientContextFactory()
                    )
                except ImportError:
                    logger.log_err("To use SSL, the PyOpenSSL module must be installed.")
            else:
                service = internet.TCPClient(self.network, int(self.port), self)
            self.sessionhandler.portal.services.addService(service)
