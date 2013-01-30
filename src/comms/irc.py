"""
This connects to an IRC network/channel and launches an 'bot' onto it.
The bot then pipes what is being said between the IRC channel and one or
more Evennia channels.
"""
from twisted.application import internet
from twisted.words.protocols import irc
from twisted.internet import protocol
from django.conf import settings
from src.comms.models import ExternalChannelConnection, Channel
from src.utils import logger, utils
from src.server.sessionhandler import SESSIONS

from django.utils.translation import ugettext as _

INFOCHANNEL = Channel.objects.channel_search(settings.CHANNEL_MUDINFO[0])
IRC_CHANNELS = []

def msg_info(message):
    """
    Send info to default info channel
    """
    message = '[%s][IRC]: %s' % (INFOCHANNEL[0].key, message)
    try:
        INFOCHANNEL[0].msg(message)
    except AttributeError:
        logger.log_infomsg("MUDinfo (irc): %s" % message)

class IRC_Bot(irc.IRCClient):
    """
    This defines an IRC bot that connects to an IRC channel
    and relays data to and from an evennia game.
    """

    def _get_nickname(self):
        "required for correct nickname setting"
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        # This is the first point the protocol is instantiated.
        # add this protocol instance to the global list so we
        # can access it later to send data.
        global IRC_CHANNELS
        self.join(self.factory.channel)

        IRC_CHANNELS.append(self)
        #msg_info("Client connecting to %s.'" % (self.factory.channel))

    def joined(self, channel):
        msg = _("joined %s.") % self.factory.pretty_key
        msg_info(msg)
        logger.log_infomsg(msg)


    def privmsg(self, user, irc_channel, msg):
        "Someone has written something in irc channel. Echo it to the evennia channel"
        #find irc->evennia channel mappings
        conns = ExternalChannelConnection.objects.filter(db_external_key=self.factory.key)
        if not conns:
            return
        #format message:
        user = user.split("!")[0]
        if user:
            user.strip()
        else:
            user = _("Unknown")
        msg = "[%s] %s@%s: %s" % (self.factory.evennia_channel, user, irc_channel, msg.strip())
        #logger.log_infomsg("<IRC: " + msg)
        for conn in conns:
            if conn.channel:
                conn.to_channel(msg)
    def action(self, user, irc_channel, msg):
        "Someone has performed an action, e.g. using /me <pose>"
        #find irc->evennia channel mappings
        conns = ExternalChannelConnection.objects.filter(db_external_key=self.factory.key)
        if not conns:
            return
        #format message:
        user = user.split("!")[0]
        if user:
            user.strip()
        else:
            user = _("Unknown")
        msg = "[%s] *%s@%s %s*" % (self.factory.evennia_channel, user, irc_channel, msg.strip())
        #logger.log_infomsg("<IRC: " + msg)
        for conn in conns:
            if conn.channel:
                conn.to_channel(msg)

    def msg_irc(self, msg, senders=None):
        """
        Called by evennia when sending something to mapped IRC channel.

        Note that this cannot simply be called msg() since that's the
        name of of the twisted irc hook as well, this leads to some
        initialization messages to be sent without checks, causing loops.
        """
        self.msg(utils.to_str(self.factory.channel), utils.to_str(msg))

class IRCbotFactory(protocol.ClientFactory):
    protocol = IRC_Bot
    def __init__(self, key, channel, network, port, nickname, evennia_channel):
        self.key = key
        self.pretty_key = "%s:%s%s ('%s')" % (network, port, channel, nickname)
        self.network = network
        self.port = port
        self.channel = channel
        self.nickname = nickname
        self.evennia_channel = evennia_channel

    def clientConnectionLost(self, connector, reason):
        from twisted.internet.error import ConnectionDone
        if type(reason.type) == type(ConnectionDone):
            msg_info(_("Connection closed."))
        else:
            msg_info(_("Lost connection %(key)s. Reason: '%(reason)s'. Reconnecting.") % {"key":self.pretty_key, "reason":reason})
            connector.connect()
    def clientConnectionFailed(self, connector, reason):
        msg = _("Could not connect %(key)s Reason: '%(reason)s'") % {"key":self.pretty_key, "reason":reason}
        msg_info(msg)
        logger.log_errmsg(msg)

def build_connection_key(channel, irc_network, irc_port, irc_channel, irc_bot_nick):
    "Build an id hash for the connection"
    if hasattr(channel, 'key'):
        channel = channel.key
    return "irc_%s:%s%s(%s)<>%s" % (irc_network, irc_port, irc_channel, irc_bot_nick, channel)

def build_service_key(key):
    return "IRCbot:%s" % key

def create_connection(channel, irc_network, irc_port, irc_channel, irc_bot_nick):
    """
    This will create a new IRC<->channel connection.
    """
    if not type(channel) == Channel:
        new_channel = Channel.objects.filter(db_key=channel)
        if not new_channel:
            logger.log_errmsg(_("Cannot attach IRC<->Evennia: Evennia Channel '%s' not found") % channel)
            return False
        channel = new_channel[0]
    key = build_connection_key(channel, irc_network, irc_port, irc_channel, irc_bot_nick)

    old_conns = ExternalChannelConnection.objects.filter(db_external_key=key)
    if old_conns:
        return False
    config = "%s|%s|%s|%s" % (irc_network, irc_port, irc_channel, irc_bot_nick)
    # how the channel will be able to contact this protocol
    send_code =  "from src.comms.irc import IRC_CHANNELS\n"
    send_code += "matched_ircs = [irc for irc in IRC_CHANNELS if irc.factory.key == '%s']\n" % key
    send_code += "[irc.msg_irc(message, senders=[self]) for irc in matched_ircs]\n"
    conn = ExternalChannelConnection(db_channel=channel, db_external_key=key, db_external_send_code=send_code,
                                     db_external_config=config)
    conn.save()

    # connect
    connect_to_irc(conn)
    return True

def delete_connection(channel, irc_network, irc_port, irc_channel, irc_bot_nick):
    "Destroy a connection"
    if hasattr(channel, 'key'):
        channel = channel.key

    key = build_connection_key(channel, irc_network, irc_port, irc_channel, irc_bot_nick)
    service_key = build_service_key(key)
    try:
        conn = ExternalChannelConnection.objects.get(db_external_key=key)
    except Exception:
        return False
    conn.delete()

    try:
        service = SESSIONS.server.services.getServiceNamed(service_key)
    except Exception:
        return True
    if service.running:
        SESSIONS.server.services.removeService(service)
    return True

def connect_to_irc(connection):
    "Create the bot instance and connect to the IRC network and channel."
    # get config
    key = utils.to_str(connection.external_key)
    service_key = build_service_key(key)
    irc_network, irc_port, irc_channel, irc_bot_nick = [utils.to_str(conf) for conf in connection.external_config.split('|')]
    # connect
    bot = internet.TCPClient(irc_network, int(irc_port), IRCbotFactory(key, irc_channel, irc_network, irc_port, irc_bot_nick,
                                                                     connection.channel.key))
    bot.setName(service_key)
    SESSIONS.server.services.addService(bot)

def connect_all():
    """
    Activate all irc bots.
    """
    for connection in ExternalChannelConnection.objects.filter(db_external_key__startswith='irc_'):
        connect_to_irc(connection)


