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
    optional_data = {}
    # Reference to the IMC2Protocol object doing the sending.
    imc2_protocol = None
    
    def _get_optional_data_string(self):
        """
        Generates the optional data string to tack on to the end of the packet.
        """
        if self.optional_data:
            data_string = ''
            for key, value in self.optional_data.items():
                self.data_string += '%s=%s ' % (key, value)
            return data_string.strip()
        else:
            return ''
    
    def _get_sender_name(self):
        """
        Calculates the sender name to be sent with the packet.
        """
        if self.sender:
            name = self.sender.get_name(fullname=False, show_dbref=False, 
                                        show_flags=False,
                                        no_ansi=True)
            # IMC2 does not allow for spaces.
            return name.strip().replace(' ', '_')
        else:
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
        self.data = {'level': '5'}

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