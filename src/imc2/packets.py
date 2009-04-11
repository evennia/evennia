"""
IMC2 packets. These are pretty well documented at:
http://www.mudbytes.net/index.php?a=articles&s=imc2_protocol
"""
from django.conf import settings

class IMC2Packet(object):
    """
    Base IMC2 packet class. This should never be used directly. Sub-class
    and profit.
    """
    # The following fields are all according to the basic packet format of:
    # <sender>@<origin> <sequence> <route> <packet-type> <target>@<destination> <data...> 
    sender = None
    origin = settings.IMC2_MUDNAME
    sequence = None
    route = settings.IMC2_MUDNAME
    packet_type = None
    target = None
    destination = None
    # Optional data.
    optional_data = []
    # Reference to the IMC2Protocol object doing the sending.
    imc2_protocol = None
    
    def _get_optional_data_string(self):
        """
        Generates the optional data string to tack on to the end of the packet.
        """
        if self.optional_data:
            data_string = ''
            for value in self.optional_data:
                data_string += '%s=%s ' % (value[0], value[1])
            return data_string.strip()
        else:
            return ''
    
    def _get_sender_name(self):
        """
        Calculates the sender name to be sent with the packet.
        """
        if self.sender == '*':
            # Some packets have no sender.
            return '*'
        elif self.sender:
            # Player object.
            name = self.sender.get_name(fullname=False, show_dbref=False, 
                                        show_flags=False,
                                        no_ansi=True)
            # IMC2 does not allow for spaces.
            return name.strip().replace(' ', '_')
        else:
            # None value. Do something or other.
            return 'Unknown'
    
    def assemble(self):
        """
        Assembles the packet and returns the ready-to-send string.
        """
        self.sequence = self.imc2_protocol.sequence
        packet = "%s@%s %s %s %s %s@%s %s\n" % (
                 self._get_sender_name(),
                 self.origin,
                 self.sequence,
                 self.route,
                 self.packet_type,
                 self.target,
                 self.destination,
                 self._get_optional_data_string())
        return packet.strip()
    
class IMC2PacketWhois(IMC2Packet):
    """
    Description:
    Sends a request to the network for the location of the specified player.
    
    Data:
    level=<int>  The permission level of the person making the request.
    
    Example:
    You@YourMUD 1234567890 YourMUD whois dude@* level=5  
    """
    def __init__(self, pobject, whois_target):
        self.sender = pobject
        self.packet_type = 'whois'
        self.target = whois_target
        self.destination = '*'
        self.optional_data = [('level', '5')]
        
class IMC2PacketIsAlive(IMC2Packet):
    """
    Description:
    This packet is the reply to a keepalive-request packet. It is responsible 
    for filling a client's mudlist with the information about other MUDs on the
    network.
    
    Data:
    versionid=<string> 
    Where <string> is the text version ID of the client. ("IMC2 4.5 MUD-Net")
    
    url=<string>      
    Where <string> is the proper URL of the client. (http://www.domain.com)
    
    host=<string>      
    Where <string> is the telnet address of the MUD. (telnet://domain.com)
    
    port=<int>        
    Where <int> is the telnet port of the MUD.
    
    (These data fields are not sent by the MUD, they are added by the server.)
    networkname=<string> 
    Where <string> is the network name that the MUD/server is on. ("MyNetwork")
    
    sha256=<int>
    This is an optional tag that denotes the SHA-256 capabilities of a 
    MUD or server.
    
    Example of a received is-alive:
    *@SomeMUD 1234567890 SomeMUD!Hub2 is-alive *@YourMUD versionid="IMC2 4.5 MUD-Net" url="http://www.domain.com" networkname="MyNetwork" sha256=1 host=domain.com port=5500
    
    Example of a sent is-alive:
    *@YourMUD 1234567890 YourMUD is-alive *@* versionid="IMC2 4.5 MUD-Net" url="http://www.domain.com" host=domain.com port=5500   
    """
    def __init__(self):
        self.sender = '*'
        self.packet_type = 'is-alive'
        self.target = '*'
        self.destination = '*'
        self.optional_data = [('versionid', '"Evennia IMC2"'),
                              ('url', '"http://evennia.com"'),
                              ('host', 'test.com'),
                              ('port', '5555')]

class IMC2PacketAuthPlaintext(object):
    """
    IMC2 plain-text authentication packet. Auth packets are strangely
    formatted, so this does not sub-class IMC2Packet. The SHA and plain text
    auth packets are the two only non-conformers.
    
    CLIENT Sends: 
    PW <mudname> <clientpw> version=<version#> autosetup <serverpw> (SHA256)
    
    Optional Arguments( required if using the specified authentication method:
    (SHA256)    The literal string: SHA256. This is sent to notify the server 
                that the MUD is SHA256-Enabled. All future logins from this 
                client will be expected in SHA256-AUTH format if the server 
                supports it. 
    """    
    def assemble(self):
        """
        This is one of two strange packets, just assemble the packet manually
        and go.
        """
        return 'PW %s %s version=%s autosetup %s\n' %(
                                                settings.IMC2_MUDNAME, 
                                                settings.IMC2_CLIENT_PW, 
                                                settings.IMC2_PROTOCOL_VERSION,
                                                settings.IMC2_SERVER_PW)