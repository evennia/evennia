"""
IMC2 client module. Handles connecting to and communicating with an IMC2 server.
"""
import telnetlib
import time
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, task
from twisted.conch.telnet import StatefulTelnetProtocol
from django.conf import settings
from src.imc2.packets import *

# The active instance of IMC2Protocol. Set at server startup.
IMC2_PROTOCOL_INSTANCE = None

class IMC2Protocol(StatefulTelnetProtocol):
    """
    Provides the abstraction for the IMC2 protocol. Handles connection,
    authentication, and all necessary packets.
    """
    def __init__(self):
        print "IMC2: Client connecting to %s:%s..." % (settings.IMC2_SERVER_ADDRESS,
                                                       settings.IMC2_SERVER_PORT)
        global IMC2_PROTOCOL_INSTANCE
        IMC2_PROTOCOL_INSTANCE = self
        self.is_authenticated = False
        self.auth_type = None
        self.network_name = None
        self.sequence = None
           
    def connectionMade(self):
        """
        Triggered after connecting to the IMC2 network.
        """
        print "IMC2: Connected to network server."
        self.auth_type = "plaintext"
        print "IMC2: Sending authentication packet."
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
        packet_str = packet.assemble()
        print "IMC2: SENT> %s" % packet_str
        self.sendLine(packet_str)
        
    def _parse_auth_response(self, line):
        """
        Parses the IMC2 network authentication packet.
        """
        if self.auth_type == "plaintext":
            """
            SERVER Sends: PW <servername> <serverpw> version=<version#> <networkname> 
            """
            if line[:2] == "PW":
                line_split = line.split(' ')
                self.network_name = line_split[4]
                self.is_authenticated = True
                self.sequence = time.time()
                print "IMC2: Successfully authenticated to the '%s' network." % self.network_name

    def lineReceived(self, line):
        """
        Triggered when text is received from the IMC2 network. Figures out
        what to do with the packet.
        """
        if not self.is_authenticated:
            self._parse_auth_response(line)
        else:
            split_line = line.split(' ')
            packet_type = split_line[3]
            if packet_type == "is-alive":
                pass
            elif packet_type == "user-cache":
                pass
            else:
                print "receive:", line

class IMC2ClientFactory(ClientFactory):
    """
    Creates instances of the IMC2Protocol. Should really only ever create one
    in our particular instance. Tied in via src/server.py.
    """
    protocol = IMC2Protocol

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed:', reason.getErrorMessage()

    def clientConnectionLost(self, connector, reason):
        print 'connection lost:', reason.getErrorMessage()
