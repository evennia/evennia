"""
IMC2 client module. Handles connecting to and communicating with an IMC2 server.
"""

from time import time
from twisted.application import internet
from twisted.internet import protocol
from twisted.conch import telnet
from django.conf import settings

from src.utils import logger, create, search, utils
from src.server.sessionhandler import SESSIONS
from src.scripts.scripts import Script
from src.comms.models import Channel, ExternalChannelConnection
from src.comms.imc2lib import imc2_packets as pck
from src.comms.imc2lib.imc2_trackers import IMC2MudList, IMC2ChanList
from src.comms.imc2lib.imc2_listeners import handle_whois_reply


# channel to send info to
INFOCHANNEL = Channel.objects.channel_search(settings.CHANNEL_MUDINFO[0])
# all linked channel connections
IMC2_CONNECTIONS = []
# IMC2 debug mode 
IMC2_DEBUG = False
# Use this instance to keep track of the other games on the network.
IMC2_MUDLIST = IMC2MudList()
# Tracks the list of available channels on the network.
IMC2_CHANLIST = IMC2ChanList()

#
# Helper method
#

def msg_info(message):
    """
    Send info to default info channel
    """
    message = '[%s][IMC2]: %s' % (INFOCHANNEL[0].key, message)
    try:
        INFOCHANNEL[0].msg(message)
    except AttributeError:
        logger.log_infomsg("MUDinfo (imc2): %s" % message)

#
# Regular scripts 
#

class Send_IsAlive(Script):
    """
    Sends periodic keepalives to network neighbors. This lets the other
    games know that our game is still up and connected to the network. Also
    provides some useful information about the client game.
    """
    def at_script_creation(self):
        self.key = 'IMC2_Send_IsAlive'
        self.interval = 900
        self.desc = "Send an IMC2 is-alive packet"
        self.persistent = True 
    def at_repeat(self):
        for channel in IMC2_CONNECTIONS:
            channel.send_packet(pck.IMC2PacketIsAlive())
    def is_valid(self):
        "Is only valid as long as there are channels to update"
        return any(service for service in SESSIONS.server.services if service.name.startswith("IMC2:"))

class Send_Keepalive_Request(Script):
    """
    Event: Sends a keepalive-request to connected games in order to see who
    is connected.
    """
    def at_script_creation(self):
        self.key = "IMC2_Send_Keepalive_Request"
        self.interval = 3500
        self.desc = "Send an IMC2 keepalive-request packet"
        self.persistent = True 
    def at_repeat(self):
        for channel in IMC2_CONNECTIONS:
            channel.send_packet(pck.IMC2PacketKeepAliveRequest())
    def is_valid(self):
        "Is only valid as long as there are channels to update"
        return any(service for service in SESSIONS.server.services if service.name.startswith("IMC2:"))

class Prune_Inactive_Muds(Script):
    """
    Prunes games that have not sent is-alive packets for a while. If
    we haven't heard from them, they're probably not connected or don't
    implement the protocol correctly. In either case, good riddance to them.
    """
    def at_script_creation(self):
        self.key = "IMC2_Prune_Inactive_Muds"
        self.interval = 1800
        self.desc = "Check IMC2 list for inactive games"
        self.persistent = True 
        self.inactive_threshold = 3599
    def at_repeat(self):
        for name, mudinfo in IMC2_MUDLIST.mud_list.items():
            if time() - mudinfo.last_updated > self.inactive_threshold:
                del IMC2_MUDLIST.mud_list[name]
    def is_valid(self):
        "Is only valid as long as there are channels to update"
        return any(service for service in SESSIONS.server.services if service.name.startswith("IMC2:"))
    
class Sync_Server_Channel_List(Script):
    """
    Re-syncs the network's channel list. This will
    cause a cascade of reply packets of a certain type
    from the network. These are handled by the protocol,
    gradually updating the channel cache.
    """
    def at_script_creation(self):
        self.key = "IMC2_Sync_Server_Channel_List"
        self.interval = 24 * 3600 # once every day 
        self.desc = "Re-sync IMC2 network channel list"
        self.persistent = True 
    def at_repeat(self):
        checked_networks = []
        for channel in self.IMC2_CONNECTIONS: 
            network = channel.factory.network
            if not network in checked_networks:
                channel.send_packet(pkg.IMC2PacketIceRefresh())
                checked_networks.append(network)
    def is_valid(self):
        return any(service for service in SESSIONS.server.services if service.name.startswith("IMC2:"))
#
# IMC2 protocol 
#

class IMC2Protocol(telnet.StatefulTelnetProtocol):
    """
    Provides the abstraction for the IMC2 protocol. Handles connection,
    authentication, and all necessary packets.
    """
    def __init__(self):
        global IMC2_CONNECTIONS
        IMC2_CONNECTIONS.append(self)
        self.is_authenticated = False
        self.auth_type = None
        self.server_name = None
        self.network_name = None
        self.sequence = None

           
    def connectionMade(self):
        """
        Triggered after connecting to the IMC2 network.
        """
        self.auth_type = "plaintext"
        logger.log_infomsg("IMC2: Connected to network server.")
        logger.log_infomsg("IMC2: Sending authentication packet.")
        self.send_packet(pck.IMC2PacketAuthPlaintext())
                                                              
    def connectionLost(self, reason=None):
        """
        This is executed when the connection is lost for 
        whatever reason. 
        """
        pass # we don't need to do anything, it's cleaned up automatically.

    def send_packet(self, packet):
        """
        Given a sub-class of IMC2Packet, assemble the packet and send it
        on its way to the IMC2 server.

        Evennia -> IMC2
        """
        if self.sequence:
            # This gets incremented with every command.
            self.sequence += 1
        packet.imc2_protocol = self
        packet_str = utils.to_str(packet.assemble(self.factory.mudname, self.factory.client_pwd, self.factory.server_pwd))
        if IMC2_DEBUG and not (hasattr(packet, 'packet_type') and packet.packet_type == "is-alive"):
            logger.log_infomsg("IMC2: SENT> %s" % packet_str)
            logger.log_infomsg(str(packet))
        self.sendLine(packet_str)
        
    def _parse_auth_response(self, line):
        """
        Parses the IMC2 network authentication packet.
        """
        if self.auth_type == "plaintext":
            # Plain text passwords. 
            # SERVER Sends: PW <servername> <serverpw> version=<version#> <networkname> 

            if IMC2_DEBUG:
                logger.log_infomsg("IMC2: AUTH< %s" % line)

            line_split = line.split(' ')
            pw_present = line_split[0] == 'PW'
            autosetup_present = line_split[0] == 'autosetup'

            if "reject" in line_split:
                auth_message = "IMC2 server rejected connection."
                logger.log_infomsg(auth_message)
                msg_info(auth_message)
                return 
                
            if pw_present:
                self.server_name = line_split[1]
                self.network_name = line_split[4]
            elif autosetup_present:
                logger.log_infomsg("IMC2: Autosetup response found.")
                self.server_name = line_split[1]
                self.network_name = line_split[3]                    
            self.is_authenticated = True
            self.sequence = int(time())
            
            # Log to stdout and notify over MUDInfo.
            auth_message = "Successfully authenticated to the '%s' network." % self.network_name            
            logger.log_infomsg('IMC2: %s' % auth_message)
            msg_info(auth_message)
            
            # Ask to see what other MUDs are connected.
            self.send_packet(pck.IMC2PacketKeepAliveRequest())
            # IMC2 protocol states that KeepAliveRequests should be followed
            # up by the requester sending an IsAlive packet.
            self.send_packet(pck.IMC2PacketIsAlive())
            # Get a listing of channels.
            self.send_packet(pck.IMC2PacketIceRefresh())
                
    def _msg_evennia(self, packet):
        """
        Handle the sending of packet data to Evennia channel
        (Message from IMC2 -> Evennia)
        """
        conn_name = packet.optional_data.get('channel', None)

        # If the packet lacks the 'echo' key, don't bother with it.
        if not conn_name or not packet.optional_data.get('echo', None):        
            return 

        chan_name = conn_name.split(':', 1)[1]
        if not chan_name in self.factory.channel:
            # we are not listening to this channel.
            return 

        key = "imc2_%s" % conn_name            
        # Look for matching IMC2 channel maps.
        conns = ExternalChannelConnection.objects.filter(db_external_key=self.factory.key)
        if not conns:
            return 
            
        # Format the message to send to local channel.
        message = '[%s] %s@%s: %s' % (self.factory.evennia_channel, packet.sender, packet.origin, packet.optional_data.get('text'))
        for conn in (conn for conn in conns if conn.channel):
            conn.to_channel(message)
 
    def _format_tell(self, packet):
        """
        Handle tells over IMC2 by formatting the text properly 
        """
        return "{c%s@%s{n {wpages (over IMC):{n %s" % (packet.sender, packet.origin,
                                                        packet.optional_data.get('text', 'ERROR: No text provided.'))

    def lineReceived(self, line):
        """
        Triggered when text is received from the IMC2 network. Figures out
        what to do with the packet.
        IMC2 -> Evennia 
        """
        line = line.strip()

        if not self.is_authenticated:
            self._parse_auth_response(line)
        else:
            if IMC2_DEBUG and not 'is-alive' in line:
                # if IMC2_DEBUG mode is on, print the contents of the packet
                # to stdout.                
                logger.log_infomsg("IMC2: RECV> %s" % line)
                
            # Parse the packet and encapsulate it for easy access
            packet = pck.IMC2Packet(self.factory.mudname, packet_str=line)
            
            if IMC2_DEBUG and packet.packet_type not in ('is-alive', 'keepalive-request'):
                # Print the parsed packet's __str__ representation.
                # is-alive and keepalive-requests happen pretty frequently.
                # Don't bore us with them in stdout.
                logger.log_infomsg(str(packet))
                            
            # Figure out what kind of packet we're dealing with and hand it
            # off to the correct handler.

            if packet.packet_type == 'is-alive':
                IMC2_MUDLIST.update_mud_from_packet(packet)
            elif packet.packet_type == 'keepalive-request':
                # Don't need to check the destination, we only receive these
                # packets when they are intended for us.
                self.send_packet(pck.IMC2PacketIsAlive())
            elif packet.packet_type == 'ice-msg-b':
                self._msg_evennia(packet)
            elif packet.packet_type == 'whois-reply':
                handle_whois_reply(packet)
            elif packet.packet_type == 'close-notify':
                IMC2_MUDLIST.remove_mud_from_packet(packet)
            elif packet.packet_type == 'ice-update':
                IMC2_CHANLIST.update_channel_from_packet(packet)
            elif packet.packet_type == 'ice-destroy':
                IMC2_CHANLIST.remove_channel_from_packet(packet)
            elif packet.packet_type == 'tell':
                player = search.players(packet.target)
                if not player:
                    return 
                player[0].msg(self._format_tell(packet))
        
    def msg_imc2(self, message, from_obj=None, packet_type="imcbroadcast", data=None):
        """
        Called by Evennia to send a message through the imc2 connection
        """
        conns = ExternalChannelConnection.objects.filter(db_external_key=self.factory.key)
        if not conns:
            return
        if from_obj:
            if hasattr(from_obj, 'key'):
                from_name = from_obj.key
            else:
                from_name = from_obj
        else:
            from_name = self.factory.mudname

        if packet_type == "imcbroadcast":
            # send the packet 
            self.send_packet(pck.IMC2PacketIceMsgBroadcasted(self.factory.servername, self.factory.channel[0],
                                                             from_name, message))
        elif packet_type == "imctell":
            # send a tell 
            if type(data) == dict:
                target = data.get("target", "Unknown")
                destination = data.get("destination", "Unknown")
                self.send_packet(pck.IMC2PacketTell(from_name, target, destination, message))
            
        elif packet_type == "imcwhois":
            # send a whois request 
            if type(data) == dict:
                target = data.get("target", "Unknown")
                self.send_packet(pck.IMC2PacketWhois(from_obj.id, target))
                         
class IMC2Factory(protocol.ClientFactory):
    """
    Creates instances of the IMC2Protocol. Should really only ever create one
    in our particular instance. Tied in via src/server.py.
    """
    protocol = IMC2Protocol

    def __init__(self, key, channel, network, port, mudname, client_pwd, server_pwd, evennia_channel):
        self.key = key
        self.mudname = mudname
        self.channel = channel
        self.pretty_key = "%s:%s/%s (%s)" % (network, port, channel, mudname)
        self.network = network
        sname, host = network.split(".", 1)
        self.servername = sname.strip()
        self.protocol_version = '2'
        self.client_pwd = client_pwd
        self.server_pwd = server_pwd 
        self.evennia_channel = evennia_channel 
    

    def clientConnectionFailed(self, connector, reason):        
        message = 'Connection failed: %s' % reason.getErrorMessage()
        msg_info(message)
        logger.log_errmsg('IMC2: %s' % message)

    def clientConnectionLost(self, connector, reason):
        message = 'Connection lost: %s' % reason.getErrorMessage()
        msg_info(message)
        logger.log_errmsg('IMC2: %s' % message)


def build_connection_key(channel, imc2_network, imc2_port, imc2_mudname):
    "Build an id hash for the connection"
    if hasattr(channel, 'key'):
        channel = channel.key
    return "imc2_%s:%s(%s)<>%s" % (imc2_network, imc2_port, imc2_mudname, channel)

def build_service_key(key):
    return "IMC2:%s" % key

def start_scripts(validate=False):
    """
    Start all the needed scripts
    """

    if validate:         
        from src.utils import reloads
        reloads.reload_scripts()
        return 
    if not search.scripts("IMC2_Send_IsAlive"):
        create.create_script(Send_IsAlive)
    if not search.scripts("IMC2_Send_Keepalive_Request"):
        create.create_script(Send_Keepalive_Request)
    if not search.scripts("IMC2_Prune_Inactive_Muds"):
        create.create_script(Prune_Inactive_Muds)
    if not search.scripts("IMC2_Sync_Server_Channel_List"):
        create.create_script(Sync_Server_Channel_List)        

def create_connection(channel, imc2_network, imc2_port, imc2_channel, imc2_mudname, imc2_client_pwd, imc2_server_pwd):
    """
    This will create a new IMC2<->channel connection.
    """
    if not type(channel) == Channel:
        new_channel = Channel.objects.filter(db_key=channel)
        if not new_channel:
            logger.log_errmsg("Cannot attach IMC2<->Evennia: Evennia Channel '%s' not found" % channel)
            return False
        channel = new_channel[0]
    key = build_connection_key(channel, imc2_network, imc2_port, imc2_mudname)

    old_conns = ExternalChannelConnection.objects.filter(db_external_key=key)
    if old_conns:
        # connection already exists. We try to only connect a new channel
        old_config = old_conns[0].db_external_config.split('|',5)
        old_chan_subs = old_config[2].split(',')
        if imc2_channel in old_chan_subs:
            return False # we already listen to this channel
        else:
            # We add thew new channel to the connection instead of creating a new connection.
            old_chan_subs.append(imc2_channel)
            old_chan_subs = ",".join(old_chan_subs)
            old_config[2] = old_chan_subs # add a channel subscription to old config 
            old_conns[0].db_external_config = "|".join(old_config)
            old_conns[0].save()            
            return True

    # new connection 
    config = "%s|%s|%s|%s|%s|%s" % (imc2_network, imc2_port, imc2_channel, imc2_mudname, imc2_client_pwd, imc2_server_pwd)
    # how the channel will be able to contact this protocol
    send_code =  "from src.comms.imc2 import IMC2_CONNECTIONS\n"     
    send_code += "matched_imc2s = [imc2 for imc2 in IMC2_CONNECTIONS if imc2.factory.key == '%s']\n" % key
    send_code += "[imc2.msg_imc2(message, from_obj=from_obj) for imc2 in matched_imc2s]\n"
    conn = ExternalChannelConnection(db_channel=channel, db_external_key=key, db_external_send_code=send_code, 
                                     db_external_config=config)    
    conn.save()

    # connect 
    connect_to_imc2(conn)
    # start scripts (if needed)
    start_scripts()
    return True 

def delete_connection(channel, imc2_network, imc2_port, mudname):
    "Destroy a connection"
    if hasattr(channel, 'key'):
        channel = channel.key

    key = build_connection_key(channel, imc2_network, imc2_port, mudname)    
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
    # validate scripts
    start_scripts(validate=True)
    return True 

def connect_to_imc2(connection):
    "Create the imc instance and connect to the IMC2 network and channel."        

    # get config
    key = utils.to_str(connection.external_key)
    service_key = build_service_key(key)
    imc2_network, imc2_port, imc2_channel, imc2_mudname, imc2_client_pwd, imc2_server_pwd = \
        [utils.to_str(conf) for conf in connection.external_config.split('|')]
    imc2_channel = imc2_channel.split(",")
    # connect 
    imc = internet.TCPClient(imc2_network, int(imc2_port), IMC2Factory(key, imc2_channel, imc2_network, imc2_port, imc2_mudname, 
                                                                       imc2_client_pwd, imc2_server_pwd, connection.channel.key))        
    imc.setName(service_key)    
    SESSIONS.server.services.addService(imc)

def connect_all():
    """
    Activate all imc2 bots. 
    
    Returns a list of (key, TCPClient) tuples for server to properly set services. 
    """
    connections = ExternalChannelConnection.objects.filter(db_external_key__startswith='imc2_')
    for connection in connections:
        connect_to_imc2(connection)
    if connections:
        start_scripts()
