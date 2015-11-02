"""
IMC2 client module. Handles connecting to and communicating with an IMC2 server.
"""
from builtins import object
from future.utils import listitems

from time import time
from twisted.internet import task
from twisted.application import internet
from twisted.internet import protocol
from twisted.conch import telnet

from evennia.server.session import Session
from evennia.utils import logger, utils
from evennia.server.portal.imc2lib import imc2_ansi
from evennia.server.portal.imc2lib import imc2_packets as pck

from django.utils.translation import ugettext as _


# storage containers for IMC2 muds and channels

class IMC2Mud(object):
    """
    Stores information about other games connected to our current IMC2 network.

    """
    def __init__(self, packet):
        self.name = packet.origin
        self.versionid = packet.optional_data.get('versionid', None)
        self.networkname = packet.optional_data.get('networkname', None)
        self.url = packet.optional_data.get('url', None)
        self.host = packet.optional_data.get('host', None)
        self.port = packet.optional_data.get('port', None)
        self.sha256 = packet.optional_data.get('sha256', None)
        # This is used to determine when a Mud has fallen into inactive status.
        self.last_updated = time()


class IMC2MudList(dict):
    """
    Keeps track of other MUDs connected to the IMC network.

    """
    def get_mud_list(self):
        """
        Returns a sorted list of connected Muds.
        """
        muds = listitems(self)
        muds.sort()
        return [value for key, value in muds]

    def update_mud_from_packet(self, packet):
        """
        This grabs relevant info from the packet and stuffs it in the
        Mud list for later retrieval.

        Args:
            packet (Packet): incoming packet.

        """
        mud = IMC2Mud(packet)
        self[mud.name] = mud

    def remove_mud_from_packet(self, packet):
        """
        Removes a mud from the Mud list when given a packet.

        Args:
            packet (Packet): Incoming packet.

        """
        mud = IMC2Mud(packet)
        try:
            del self[mud.name]
        except KeyError:
            # No matching entry, no big deal.
            pass


class IMC2Channel(object):
    """
    Stores information about channels available on the network.
    """
    def __init__(self, packet):
        "Initialize channel."
        self.localname = packet.optional_data.get('localname', None)
        self.name = packet.optional_data.get('channel', None)
        self.level = packet.optional_data.get('level', None)
        self.owner = packet.optional_data.get('owner', None)
        self.policy = packet.optional_data.get('policy', None)
        self.last_updated = time()


class IMC2ChanList(dict):
    """
    Keeps track of Channels on the IMC network.
    """

    def get_channel_list(self):
        """
        Returns a sorted list of cached channels.

        """
        channels = listitems(self)
        channels.sort()
        return [value for key, value in channels]

    def update_channel_from_packet(self, packet):
        """
        This grabs relevant info from the packet and stuffs it in the
        channel list for later retrieval.

        Args:
            packet (Packet): incoming packet.

        """
        channel = IMC2Channel(packet)
        self[channel.name] = channel

    def remove_channel_from_packet(self, packet):
        """
        Removes a channel from the Channel list when given a packet.

        Args:
            packet (Packet): incoming packet.

        """
        channel = IMC2Channel(packet)
        try:
            del self[channel.name]
        except KeyError:
            # No matching entry, no big deal.
            pass


#
# IMC2 protocol
#

class IMC2Bot(telnet.StatefulTelnetProtocol, Session):
    """
    Provides the abstraction for the IMC2 protocol. Handles connection,
    authentication, and all necessary packets.

    """
    def __init__(self):
        "Initialize bot."
        self.is_authenticated = False
        # only support plaintext passwords
        self.auth_type = "plaintext"
        self.sequence = None
        self.imc2_mudlist = IMC2MudList()
        self.imc2_chanlist = IMC2ChanList()

    def _send_packet(self, packet):
        """
        Helper function to send packets across the wire.

        Args:
            packet (Packet): Outgoing packet.

        """
        packet.imc2_protocol = self
        packet_str = utils.to_str(packet.assemble(self.factory.mudname,
                         self.factory.client_pwd, self.factory.server_pwd))
        self.sendLine(packet_str)

    def _isalive(self):
        "Send an isalive packet."
        self._send_packet(pck.IMC2PacketIsAlive())

    def _keepalive(self):
        "Send a keepalive packet."
        # send to channel?
        self._send_packet(pck.IMC2PacketKeepAliveRequest())

    def _channellist(self):
        "Sync the network channel list."
        checked_networks = []
        if not self.network in checked_networks:
            self._send_packet(pck.IMC2PacketIceRefresh())
            checked_networks.append(self.network)

    def _prune(self):
        "Prune active channel list."
        t0 = time()
        for name, mudinfo in self.imc2_mudlist.items():
            if t0 - mudinfo.last_updated > 3599:
                del self.imc2_mudlist[name]

    def _whois_reply(self, packet):
        """
        Handle reply from server from an imcwhois request.

        Args:
            packet (Packet): Data packet.

        """
        # packet.target potentially contains the id of an character to target
        # not using that here
        response_text = imc2_ansi.parse_ansi(packet.optional_data.get('text', 'Unknown'))
        string = _('Whois reply from %(origin)s: %(msg)s') % {"origin":packet.origin, "msg":response_text}
        # somehow pass reply on to a given player, for now we just send to channel
        self.data_in(string)

    def _format_tell(self, packet):
        """
        Handle tells over IMC2 by formatting the text properly

        Args:
            packet (Packet): Data packet.

        """
        return _("{c%(sender)s@%(origin)s{n {wpages (over IMC):{n %(msg)s") % {"sender": packet.sender,
                                                        "origin": packet.origin,
                                                        "msg": packet.optional_data.get('text', 'ERROR: No text provided.')}

    def _imc_login(self, line):
        """
        Connect and identify to imc network as per the
        `self.auth_type` setting.

        Args:
            line (str): Incoming text.

        """

        if self.auth_type == "plaintext":
            # Only support Plain text passwords.
            # SERVER Sends: PW <servername> <serverpw> version=<version#> <networkname>

            logger.log_info("IMC2: AUTH< %s" % line)

            line_split = line.split(' ')
            pw_present = line_split[0] == 'PW'
            autosetup_present = line_split[0] == 'autosetup'

            if "reject" in line_split:
                auth_message = _("IMC2 server rejected connection.")
                logger.log_info(auth_message)
                return

            if pw_present:
                self.server_name = line_split[1]
                self.network_name = line_split[4]
            elif autosetup_present:
                logger.log_info(_("IMC2: Autosetup response found."))
                self.server_name = line_split[1]
                self.network_name = line_split[3]
            self.is_authenticated = True
            self.sequence = int(time())

            # Log to stdout and notify over MUDInfo.
            logger.log_info('IMC2: Authenticated to %s' % self.factory.network)

            # Ask to see what other MUDs are connected.
            self._send_packet(pck.IMC2PacketKeepAliveRequest())
            # IMC2 protocol states that KeepAliveRequests should be followed
            # up by the requester sending an IsAlive packet.
            self._send_packet(pck.IMC2PacketIsAlive())
            # Get a listing of channels.
            self._send_packet(pck.IMC2PacketIceRefresh())

    def connectionMade(self):
        """
        Triggered after connecting to the IMC2 network.

        """

        self.stopping = False
        self.factory.bot = self
        address = "%s@%s" % (self.mudname, self.network)
        self.init_session("ircbot", address, self.factory.sessionhandler)
        # link back and log in
        self.uid = int(self.factory.uid)
        self.logged_in = True
        self.factory.sessionhandler.connect(self)
        logger.log_info("IMC2 bot connected to %s." % self.network)
        # Send authentication packet. The reply will be caught by lineReceived
        self._send_packet(pck.IMC2PacketAuthPlaintext())

    def lineReceived(self, line):
        """
        IMC2 -> Evennia

        Triggered when text is received from the IMC2 network. Figures out
        what to do with the packet. This deals with the following

        Args:
            line (str): Incoming text.

        """
        line = line.strip()

        if not self.is_authenticated:
            # we are not authenticated yet. Deal with this.
            self._imc_login(line)
            return

        # Parse the packet and encapsulate it for easy access
        packet = pck.IMC2Packet(self.mudname, packet_str=line)

        # Figure out what kind of packet we're dealing with and hand it
        # off to the correct handler.

        if packet.packet_type == 'is-alive':
            self.imc2_mudlist.update_mud_from_packet(packet)
        elif packet.packet_type == 'keepalive-request':
            # Don't need to check the destination, we only receive these
            # packets when they are intended for us.
            self.send_packet(pck.IMC2PacketIsAlive())
        elif packet.packet_type == 'ice-msg-b':
            self.data_out(text=line, packettype="broadcast")
        elif packet.packet_type == 'whois-reply':
            # handle eventual whois reply
            self._whois_reply(packet)
        elif packet.packet_type == 'close-notify':
            self.imc2_mudlist.remove_mud_from_packet(packet)
        elif packet.packet_type == 'ice-update':
            self.imc2_chanlist.update_channel_from_packet(packet)
        elif packet.packet_type == 'ice-destroy':
            self.imc2_chanlist.remove_channel_from_packet(packet)
        elif packet.packet_type == 'tell':
            # send message to identified player
            pass

    def data_in(self, text=None, **kwargs):
        """
        Data IMC2 -> Evennia.

        Kwargs:
            text (str): Incoming text.
            kwargs (any): Other data from protocol.

        """
        text = "bot_data_in " + text
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        """
        Evennia -> IMC2.

        Kwargs:
           text (str): Outgoing text.
           packet_type (str):
                - broadcast: Send to everyone on IMC channel.
                - tell: Send a tell (see target keyword).
                - whois: Get whois information (see target keyword).
           sender (str): Used by tell to identify the mud sending.
           target (str): Key identifier of target to tells or whois. If not
               given "Unknown" will be used.
          destination (str): Used by tell to specify mud
            destination to send to.

        """

        if self.sequence:
            # This gets incremented with every command.
            self.sequence += 1

        packet_type = kwargs.get("packet_type", "imcbroadcast")

        if packet_type == "broadcast":
            # broadcast to everyone on IMC channel

            if text.startswith("bot_data_out"):
                text = text.split(" ", 1)[1]
            else:
                return

            # we remove the extra channel info since imc2 supplies this anyway
            if ":" in text:
                header, message = [part.strip() for part in text.split(":", 1)]
            # Create imc2packet and send it
            self._send_packet(pck.IMC2PacketIceMsgBroadcasted(self.servername,
                                                        self.channel,
                                                        header, text))
        elif packet_type == "tell":
            # send an IMC2 tell
            sender = kwargs.get("sender", self.mudname)
            target = kwargs.get("target", "Unknown")
            destination = kwargs.get("destination", "Unknown")
            self._send_packet(pck.IMC2PacketTell(sender, target, destination, text))

        elif packet_type == "whois":
            # send a whois request
            sender = kwargs.get("sender", self.mudname)
            target = kwargs.get("target", "Unknown")
            self._send_packet(pck.IMC2PacketWhois(sender, target))


class IMC2BotFactory(protocol.ReconnectingClientFactory):
    """
    Creates instances of the IMC2Protocol. Should really only ever
    need to create one connection. Tied in via evennia/server.py.

    """
    initialDelay = 1
    factor = 1.5
    maxDelay = 60

    def __init__(self, sessionhandler, uid=None, network=None, channel=None,
                 port=None, mudname=None, client_pwd=None, server_pwd=None):
        "Initialize the bot factory."
        self.uid = uid
        self.network = network
        sname, host = network.split(".", 1)
        self.servername = sname.strip()
        self.channel = channel
        self.port = port
        self.mudname = mudname
        self.protocol_version = '2'
        self.client_pwd = client_pwd
        self.server_pwd = server_pwd
        self.bot = None
        self.task_isalive = None
        self.task_keepalive = None
        self.task_prune = None
        self.task_channellist = None

    def buildProtocol(self, addr):
        """
        Build the protocol.

        Args:
            addr (str): Protocl address.

        Returns:
            protocol (Protocol): The new protocol.

        """
        protocol = IMC2Bot()
        protocol.factory = self
        protocol.network = self.network
        protocol.servername = self.servername
        protocol.channel = self.channel
        protocol.mudname = self.mudname
        protocol.port = self.port
        return protocol

    def clientConnectionFailed(self, connector, reason):
        """
        Called when Client could not connect.

        Args:
            connector (Connector): Reprsents the connection.
            reason (str): Reason for the failure.
        """
        self.retry(connector)

    def clientConnectionLost(self, connector, reason):
        """
        Called when Client looses connection.

        Args:
            connector (Connector): Reprsents the connection.
            reason (str): Reason for the failure.
        """
        if not self.bot.stopping:
            self.retry(connector)

    def start(self):
        "Connect session to sessionhandler"
        def errback(fail):
            logger.log_err(fail.value)

        if self.port:
            service = internet.TCPClient(self.network, int(self.port), self)
            self.sessionhandler.portal.services.addService(service)
        # start tasks
        self.task_isalive = task.LoopingCall(self.bot._isalive)
        self.task_keepalive = task.LoopingCall(self.bot._keepalive)
        self.task_prune = task.LoopingCall(self.bot._prune)
        self.task_channellist = task.LoopingCall(self.bot._channellist)
        self.task_isalive.start(900, now=False)
        self.task_keepalive.start(3500, now=False)
        self.task_prune.start(1800, now=False)
        self.task_channellist.start(3600 * 24, now=False)

