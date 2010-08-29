"""
This connects to an IRC network/channel and launches an 'bot' onto it.
The bot then pipes what is being said between the IRC channel and one or
more Evennia channels.
"""
# TODO: This is deprecated!

from twisted.words.protocols import irc
from twisted.internet import protocol
from twisted.internet import reactor
from django.conf import settings
from src.irc.models import IRCChannelMapping
#from src import comsys
from src.utils import logger 

#store all irc channels
IRC_CHANNELS = []

def cemit_info(message):
    """
    Send info to default info channel
    """
    comsys.send_cmessage(settings.COMMCHAN_IRC_INFO, 'IRC: %s' % message)

class IRC_Bot(irc.IRCClient):
    
    def _get_nickname(self):
        "required for correct nickname setting"
        return self.factory.nickname
    nickname = property(_get_nickname)
    
    def signedOn(self):        
        global IRC_CHANNELS
        self.join(self.factory.channel)

        # This is the first point the protocol is instantiated.
        # add this protocol instance to the global list so we
        # can access it later to send data. 
        IRC_CHANNELS.append(self)        
        cemit_info("Client connecting to %s.'" % (self.factory.channel))
                 
    def joined(self, channel):
        msg = "Joined %s/%s as '%s'." % (self.factory.network,channel,self.factory.nickname)
        cemit_info(msg)
        logger.log_infomsg(msg)

    def privmsg(self, user, irc_channel, msg):
        "Someone has written something in channel. Echo it to the evennia channel"

        try:
            #find irc->evennia channel mappings
            mappings = IRCChannelMapping.objects.filter(irc_channel_name=irc_channel)
            if not mappings:
                return 
            #format message: 
            user = user.split("!")[0]
            if user:
                user.strip()
            else:
                user = "Unknown"
                
            msg = "%s@%s: %s" % (user,irc_channel,msg.strip())
            #logger.log_infomsg("<IRC: " + msg)            
            
            for mapping in mappings:
                if mapping.channel:
                    comsys.send_cmessage(mapping.channel, msg, from_external="IRC")

        except IRCChannelMapping.DoesNotExist:
            #no mappings found. Ignore.
            pass
        
    def send_msg(self,msg):
        "Called by evennia when sending something to mapped IRC channel"
        self.msg(self.factory.channel, msg)
        #logger.log_infomsg(">IRC: " + msg)


class IRC_BotFactory(protocol.ClientFactory):
    protocol = IRC_Bot
    def __init__(self, channel, network, nickname):
        self.network = network
        self.channel = channel
        self.nickname = nickname                
    def clientConnectionLost(self, connector, reason):        
        from twisted.internet.error import ConnectionDone
        if type(reason.type) == type(ConnectionDone):
            cemit_info("Connection closed.")
        else:
            cemit_info("Lost connection (%s), reconnecting." % reason)
            connector.connect()
    def clientConnectionFailed(self, connector, reason):
        msg = "Could not connect: %s" % reason
        cemit_info(msg)
        logger.log_errmsg(msg)        
        
def connect_to_IRC(irc_network,irc_port,irc_channel,irc_bot_nick ):   
    "Create the bot instance and connect to the IRC network and channel."        
    connect = reactor.connectTCP(irc_network, irc_port,
                                 IRC_BotFactory(irc_channel,irc_network,irc_bot_nick))

