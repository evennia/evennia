"""
IMC2 client module. Handles connecting to and communicating with an IMC2 server.
"""
import telnetlib
from time import time
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, task
from twisted.conch.telnet import StatefulTelnetProtocol
from django.conf import settings
from src import logger
from src import session_mgr
from src.imc2.packets import *
from src.imc2.trackers import *
from src.imc2 import reply_listener
from src.imc2.models import IMC2ChannelMapping
from src import comsys

# The active instance of IMC2Protocol. Set at server startup.
IMC2_PROTOCOL_INSTANCE = None

class IMC2Protocol(StatefulTelnetProtocol):
    """
    Provides the abstraction for the IMC2 protocol. Handles connection,
    authentication, and all necessary packets.
    """
    def __init__(self):
        logger.log_infomsg("IMC2: Client connecting to %s:%s..." % (
                                                    settings.IMC2_SERVER_ADDRESS,
                                                    settings.IMC2_SERVER_PORT))
        global IMC2_PROTOCOL_INSTANCE
        IMC2_PROTOCOL_INSTANCE = self
        self.is_authenticated = False
        self.auth_type = None
        self.server_name = None
        self.network_name = None
        self.sequence = None
           
    def connectionMade(self):
        """
        Triggered after connecting to the IMC2 network.
        """
        logger.log_infomsg("IMC2: Connected to network server.")
        self.auth_type = "plaintext"
        logger.log_infomsg("IMC2: Sending authentication packet.")
        self.send_packet(IMC2PacketAuthPlaintext())
        
    def send_packet(self, packet):
        """
        Given a sub-class of IMC2Packet, assemble the packet and send it
        on its way.
        """
        if self.sequence:
            # This gets incremented with every command.
            self.sequence += 1
            
        packet.imc2_protocol = self
        packet_str = str(packet.assemble())
        logger.log_infomsg("IMC2: SENT> %s" % packet_str)
        self.sendLine(packet_str)
        
    def _parse_auth_response(self, line):
        """
        Parses the IMC2 network authentication packet.
        """
        if self.auth_type == "plaintext":
            """
            SERVER Sends: PW <servername> <serverpw> version=<version#> <networkname> 
            """
            line_split = line.split(' ')
            pw_present = line_split[0] == 'PW'
            autosetup_present = line_split[0] == 'autosetup'
            
            if pw_present:
                self.server_name = line_split[1]
                self.network_name = line_split[4]
            elif autosetup_present:
                logger.log_infomsg("IMC2: Autosetup response found.")
                self.server_name = line_split[1]
                self.network_name = line_split[3]                    
            self.is_authenticated = True
            self.sequence = int(time())
            logger.log_infomsg("IMC2: Successfully authenticated to the '%s' network." % self.network_name)
            # Ask to see what other MUDs are connected.
            self.send_packet(IMC2PacketKeepAliveRequest())
            # IMC2 protocol states that KeepAliveRequests should be followed
            # up by the requester sending an IsAlive packet.
            self.send_packet(IMC2PacketIsAlive())
                
    def _handle_channel_mappings(self, packet):
        """
        Received a message. Look for an IMC2 channel mapping and
        route it accordingly.
        """
        chan_name = packet.optional_data.get('channel', None)
        # If the packet lacks the 'echo' key, don't bother with it.
        has_echo = packet.optional_data.get('echo', None)
        if chan_name and has_echo:
            # The second half of this is the channel name: Server:Channel
            chan_name = chan_name.split(':', 1)[1]
            try:
                # Look for matching IMC2 channel maps.
                mapping = IMC2ChannelMapping.objects.get(imc2_channel_name=chan_name)
                ingame_chan_name = mapping.channel.name
                # Format the message to cemit to the local channel.
                message = '[%s] %s@%s: %s' % (ingame_chan_name,
                                          packet.sender, 
                                          packet.origin,
                                          packet.optional_data.get('text'))
                # Bombs away.
                comsys.send_cmessage(ingame_chan_name, message)
            except IMC2ChannelMapping.DoesNotExist:
                # No channel mapping found for this message, ignore it.
                pass

    def lineReceived(self, line):
        """
        Triggered when text is received from the IMC2 network. Figures out
        what to do with the packet.
        """
        if not self.is_authenticated:
            self._parse_auth_response(line)
        else:
            if 'is-alive' not in line:
                logger.log_infomsg("PACKET: %s" % line)
            packet = IMC2Packet(packet_str = line)
            if packet.packet_type not in ['is-alive', 'keepalive-request']:
                logger.log_infomsg(packet)
            if packet.packet_type == 'is-alive':
                IMC2_MUDLIST.update_mud_from_packet(packet)
            elif packet.packet_type == 'ice-msg-b':
                self._handle_channel_mappings(packet)
            elif packet.packet_type == 'whois-reply':
                reply_listener.handle_whois_reply(packet)
            elif packet.packet_type == 'close-notify':
                IMC2_MUDLIST.remove_mud_from_packet(packet)
            elif packet.packet_type == 'tell':
                sessions = session_mgr.find_sessions_from_username(packet.target)
                for session in sessions:
                    session.msg("%s@%s IMC tells: %s" %
                                (packet.sender,
                                 packet.origin,
                                 packet.optional_data.get('text', 
                                                          'ERROR: No text provided.')))

class IMC2ClientFactory(ClientFactory):
    """
    Creates instances of the IMC2Protocol. Should really only ever create one
    in our particular instance. Tied in via src/server.py.
    """
    protocol = IMC2Protocol

    def clientConnectionFailed(self, connector, reason):
        logger.log_errmsg('connection failed: %s' % reason.getErrorMessage())

    def clientConnectionLost(self, connector, reason):
        logger.log_errmsg('connection lost: %s' % reason.getErrorMessage())
