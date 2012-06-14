"""
IMC2 packets. These are pretty well documented at:
http://www.mudbytes.net/index.php?a=articles&s=imc2_protocol

"""
import shlex
from django.conf import settings

class Lexxer(shlex.shlex):
    """
    A lexical parser for interpreting IMC2 packets.
    """
    def __init__(self, packet_str, posix=True):
        shlex.shlex.__init__(self, packet_str, posix=True)
        # Single-quotes are notably not present. This is important!
        self.quotes = '"'
        self.commenters = ''
        # This helps denote what constitutes a continuous token.
        self.wordchars += "~`!@#$%^&*()-_+=[{]}|\\;:',<.>/?"

class IMC2Packet(object):
    """
    Base IMC2 packet class. This is generally sub-classed, aside from using it
    to parse incoming packets from the IMC2 network server.
    """
    def __init__(self, mudname=None, packet_str=None):
        """
        Optionally, parse a packet and load it up.
        """
        # The following fields are all according to the basic packet format of:
        # <sender>@<origin> <sequence> <route> <packet-type> <target>@<destination> <data...>
        self.sender = None
        if not mudname:
            mudname = settings.SERVERNAME
        self.origin = mudname
        self.sequence = None
        self.route = mudname
        self.packet_type = None
        self.target = None
        self.destination = None
        # Optional data.
        self.optional_data = {}
        # Reference to the IMC2Protocol object doing the sending.
        self.imc2_protocol = None

        if packet_str:
            # The lexxer handles the double quotes correctly, unlike just
            # splitting. Spaces throw things off, so shlex handles it
            # gracefully, ala POSIX shell-style parsing.
            lex = Lexxer(packet_str)

            # Token counter.
            counter = 0
            for token in lex:
                if counter == 0:
                    # This is the sender@origin token.
                    sender_origin = token
                    split_sender_origin = sender_origin.split('@')
                    self.sender = split_sender_origin[0].strip()
                    self.origin = split_sender_origin[1]
                elif counter == 1:
                    # Numeric time-based sequence.
                    self.sequence = token
                elif counter == 2:
                    # Packet routing info.
                    self.route = token
                elif counter == 3:
                    # Packet type string.
                    self.packet_type = token
                elif counter == 4:
                    # Get values for the target and destination attributes.
                    target_destination = token
                    split_target_destination = target_destination.split('@')
                    self.target = split_target_destination[0]
                    try:
                        self.destination = split_target_destination[1]
                    except IndexError:
                        # There is only one element to the target@dest segment
                        # of the packet. Wipe the target and move the captured
                        # value to the destination attrib.
                        self.target = '*'
                        self.destination = split_target_destination[0]
                elif counter > 4:
                    # Populate optional data.
                    try:
                        key, value = token.split('=', 1)
                        self.optional_data[key] = value
                    except ValueError:
                        # Failed to split on equal sign, disregard.
                        pass
                # Increment and continue to the next token (if applicable)
                counter += 1

    def __str__(self):
        retval =  """
        --IMC2 package (%s)
        Sender:   %s
        Origin:   %s
        Sequence: %s
        Route:    %s
        Type:     %s
        Target:   %s
        Dest.:    %s
        Data:
         %s
       ------------------------""" % (self.packet_type, self.sender,
                                      self.origin, self.sequence,
                                      self.route, self.packet_type,
                                      self.target, self.destination,
                                      "\n         ".join(["%s: %s" % items for items in self.optional_data.items()]))
        return retval.strip()

    def _get_optional_data_string(self):
        """
        Generates the optional data string to tack on to the end of the packet.
        """
        if self.optional_data:
            data_string = ''
            for key, value in self.optional_data.items():
                # Determine the number of words in this value.
                words = len(str(value).split(' '))
                # Anything over 1 word needs double quotes.
                if words > 1:
                    value = '"%s"' % (value,)
                data_string += '%s=%s ' % (key, value)
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
        elif str(self.sender).isdigit():
            return self.sender
        elif type(self.sender) in [type(u""),type(str())]:
            #this is used by e.g. IRC where no user object is present.
            return self.sender.strip().replace(' ', '_')
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

    def assemble(self, mudname=None, client_pwd=None, server_pwd=None):
        """
        Assembles the packet and returns the ready-to-send string.
        Note that the arguments are not used, they are there for
        consistency across all packets.
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
    def assemble(self, mudname=None, client_pwd=None, server_pwd=None):
        """
        This is one of two strange packets, just assemble the packet manually
        and go.
        """
        return 'PW %s %s version=2 autosetup %s\n' %(mudname, client_pwd, server_pwd)

class IMC2PacketKeepAliveRequest(IMC2Packet):
    """
    Description:
    This packet is sent by a MUD to trigger is-alive packets from other MUDs.
    This packet is usually followed by the sending MUD's own is-alive packet.
    It is used in the filling of a client's MUD list, thus any MUD that doesn't
    respond with an is-alive isn't marked as online on the sending MUD's mudlist.

    Data:
    (none)

    Example of a received keepalive-request:
    *@YourMUD 1234567890 YourMUD!Hub1 keepalive-request *@*

    Example of a sent keepalive-request:
    *@YourMUD 1234567890 YourMUD keepalive-request *@*
    """
    def __init__(self):
        super(IMC2PacketKeepAliveRequest, self).__init__()
        self.sender = '*'
        self.packet_type = 'keepalive-request'
        self.target = '*'
        self.destination = '*'

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
        super(IMC2PacketIsAlive, self).__init__()
        self.sender = '*'
        self.packet_type = 'is-alive'
        self.target = '*'
        self.destination = '*'
        self.optional_data = {'versionid': 'Evennia IMC2',
                              'url': '"http://www.evennia.com"',
                              'host': 'test.com',
                              'port': '5555'}

class IMC2PacketIceRefresh(IMC2Packet):
    """
    Description:
    This packet is sent by the MUD to request data about the channels on the
    network. Servers with channels reply with an ice-update packet for each
    channel they control. The usual target for this packet is IMC@$.

    Data:
    (none)

    Example:
    *@YourMUD 1234567890 YourMUD!Hub1 ice-refresh IMC@$
    """
    def __init__(self):
        super(IMC2PacketIceRefresh, self).__init__()
        self.sender = '*'
        self.packet_type = 'ice-refresh'
        self.target = 'IMC'
        self.destination = '$'

class IMC2PacketIceUpdate(IMC2Packet):
    """
    Description:
    A server returns this packet with the data of a channel when prompted with
    an ice-refresh request.

    Data:
    channel=<string>
    The channel's network name in the format of ServerName:ChannelName

    owner=<string>
    The Name@MUD of the channel's owner

    operators=<string>
    A space-seperated list of the Channel's operators, in the format of Person@MUD

    policy=<string>
    The policy is either "open" or "private" with no quotes.

    invited=<string>
    The space-seperated list of invited User@MUDs, only valid for a
    "private" channel.

    excluded=<string>
    The space-seperated list of banned User@MUDs, only valid for "open"
    channels.

    level=<string>      The default level of the channel: Admin, Imp, Imm,
    Mort, or None

    localname=<string>  The suggested local name of the channel.

    Examples:

    Open Policy:
    ICE@Hub1 1234567890 Hub1!Hub2 ice-update *@YourMUD channel=Hub1:ichat owner=Imm@SomeMUD operators=Other@SomeMUD policy=open excluded="Flamer@badMUD Jerk@dirtyMUD" level=Imm localname=ichat

    Private Policy:
    ICE@Hub1 1234567890 Hub1!Hub2 ice-update *@YourMUD channel=Hub1:secretchat owner=Imm@SomeMUD operators=Other@SomeMUD policy=private invited="SpecialDude@OtherMUD CoolDude@WeirdMUD" level=Mort localname=schat
    """
    pass

class IMC2PacketIceMsgRelayed(IMC2Packet):
    """
    Description:
    The -r in this ice-msg packet means it was relayed. This, along with the
    ice-msg-p packet, are used with private policy channels. The 'r' stands
    for 'relay'. All incoming channel messages are from ICE@<server>, where
    <server> is the server hosting the channel.

    Data:
    realfrom=<string>
    The User@MUD the message came from.

    channel=<string>
    The Server:Channel the message is intended to be displayed on.

    text=<string>
    The message text.

    emote=<int>
    An integer value designating emotes. 0 for no emote, 1 for an emote,
    and 2 for a social.

    Examples:
    ICE@Hub1 1234567890 Hub1!Hub2 ice-msg-r *@YourMUD realfrom=You@YourMUD channel=hub1:secret text="Aha! I got it!" emote=0

    ICE@Hub1 1234567890 Hub1!Hub2 ice-msg-r *@YourMUD realfrom=You@YourMUD channel=hub1:secret text=Ahh emote=0

    ICE@Hub1 1234567890 Hub1!Hub2 ice-msg-r *@YourMUD realfrom=You@YourMUD channel=hub1:secret text="grins evilly." emote=1

    ICE@Hub1 1234567890 Hub1!Hub2 ice-msg-r *@YourMUD realfrom=You@YourMUD channel=hub1:secret text="You@YourMUD grins evilly!" emote=2
    """
    pass

class IMC2PacketIceMsgPrivate(IMC2Packet):
    """
    Description:
    This packet is sent when a player sends a message to a private channel.
    This packet should never be seen as incoming to a client. The target of
    this packet should be IMC@<server> of the server hosting the channel.

    Data:
    channel=<string>
    The Server:Channel the message is intended to be displayed on.

    text=<string>
    The message text.

    emote=<int>
    An integer value designating emotes. 0 for no emote, 1 for an emote,
    and 2 for a social.

    echo=<int>
    Tells the server to echo the message back to the sending MUD. This is only
    seen on out-going messages.

    Examples:
    You@YourMUD 1234567890 YourMUD ice-msg-p IMC@Hub1 channel=Hub1:secret text="Ahh! I got it!" emote=0 echo=1
    You@YourMUD 1234567890 YourMUD ice-msg-p IMC@Hub1 channel=Hub1:secret text=Ahh! emote=0 echo=1
    You@YourMUD 1234567890 YourMUD ice-msg-p IMC@Hub1 channel=Hub1:secret text="grins evilly." emote=1 echo=1
    You@YourMUD 1234567890 YourMUD ice-msg-p IMC@Hub1 channel=Hub1:secret text="You@YourMUD grins evilly." emote=2 echo=1
    """
    pass

class IMC2PacketIceMsgBroadcasted(IMC2Packet):
    """
    Description:
    This is the packet used to chat on open policy channels. When sent from a
    MUD, it is broadcasted across the network. Other MUDs receive it in-tact
    as it was sent by the originating MUD. The server that hosts the channel
    sends the packet back to the originating MUD as an 'echo' by removing the
    "echo=1" and attaching the "sender=Person@MUD" data field.

    Data:
    channel=<string>
    The Server:Channel the message is intended to be displayed on.

    text=<string>
    The message text.

    emote=<int>
    An integer value designating emotes. 0 for no emote, 1 for an emote,
    and 2 for a social.

    *echo=<int>
    This stays on broadcasted messages. It tells the channel's server to
    relay an echo back.

    *sender=<string>
    The hosting server replaces "echo=1" with this when sending the echo back
    to the originating MUD.

    Examples:
    (See above for emote/social examples as they are pretty much the same)

    Return Echo Packet:
    You-YourMUD@Hub1 1234567890 Hub1 ice-msg-b *@YourMUD text=Hi! channel=Hub1:ichat sender=You@YourMUD emote=0

    Broadcasted Packet:
    You@YourMUD 1234567890 YourMUD!Hub1 ice-msg-b *@* channel=Hub1:ichat text=Hi! emote=0 echo=1
    """
    def __init__(self, server, channel, pobject, message):
        """
        Args:
          server: (String) Server name the channel resides on (obs - this is e.g. Server01, not the full network name!)
          channel: (String) Name of the IMC2 channel.
          pobject: (Object) Object sending the message.
          message: (String) Message to send.
        """
        super(IMC2PacketIceMsgBroadcasted, self).__init__()
        self.sender = pobject
        self.packet_type = 'ice-msg-b'
        self.target = '*'
        self.destination = '*'
        self.optional_data = {'channel': '%s:%s' % (server, channel),
                              'text': message,
                              'emote': 0,
                              'echo': 1}

class IMC2PacketUserCache(IMC2Packet):
    """
    Description:
    Sent by a MUD with a new IMC2-able player or when a player's gender changes,
    this packet contains only the gender for data. The packet's origination
    should be the Player@MUD.

    Data:
    gender=<int>  0 is male, 1 is female, 2 is anything else such as neuter.
    Will be referred to as "it".

    Example:
    Dude@someMUD 1234567890 SomeMUD!Hub2!Hub1 user-cache *@* gender=0
    """
    pass

class IMC2PacketUserCacheRequest(IMC2Packet):
    """
    Description:
    The MUD sends this packet out when making a request for the user-cache
    information of the user included in the data part of the packet.

    Data:
    user=<string>  The Person@MUD whose data the MUD is seeking.

    Example:
    *@YourMUD 1234567890 YourMUD user-cache-request *@SomeMUD user=Dude@SomeMUD
    """
    pass

class IMC2PacketUserCacheReply(IMC2Packet):
    """
    Description:
    A reply to the user-cache-request packet. It contains the user and gender
    for the user.

    Data:
    user=<string>
    The Person@MUD whose data the MUD requested.

    gender=<int>
    The gender of the Person@MUD in the 'user' field.

    Example:
    *@someMUD 1234567890 SomeMUD!Hub2!Hub1 user-cache-reply *@YourMUD user=Dude@SomeMUD gender=0
    """
    pass

class IMC2PacketTell(IMC2Packet):
    """
    Description:
    This packet is used to communicate private messages between users on MUDs
    across the network.

    Data:
    text=<string>  Message text
    isreply=<int>  Two settings: 1 denotes a reply, 2 denotes a tell social.

    Example:

    Originating:
    You@YourMUD 1234567890 YourMUD tell Dude@SomeMUD text="Having fun?"

    Reply from Dude:
    Dude@SomeMUD 1234567890 SomeMUD!Hub1 tell You@YourMUD text="Yeah, this is cool!" isreply=1
    """
    def __init__(self, pobject, target, destination, message):
        super(IMC2PacketTell, self).__init__()
        self.sender = pobject
        self.packet_type = "tell"
        self.target = target
        self.destination = destination
        self.optional_data = {"text": message,
                              "isreply":None}

    def assemble(self, mudname=None, client_pwd=None, server_pwd=None):
        self.sequence = self.imc2_protocol.sequence
        #self.route = "%s!%s" % (self.origin, self.imc2_protocol.factory.servername.capitalize())
        return '''"%s@%s %s %s tell %s@%s text="%s"''' % (self.sender, self.origin, self.sequence,
                                                          self.route, self.target, self.destination,
                                                          self.optional_data.get("text","NO TEXT GIVEN"))

class IMC2PacketEmote(IMC2Packet):
    """
    Description:
    This packet seems to be sent by servers when notifying the network of a new
    channel or the destruction of a channel.

    Data:
    channel=<int>
    Unsure of what this means. The channel seen in both creation and
    destruction packets is 15.

    level=<int>
    I am assuming this is the permission level of the sender. In both
    creation and destruction messages, this is -1.

    text=<string>
    This is the message to be sent to the users.

    Examples:
    ICE@Hub1 1234567890 Hub1 emote *@* channel=15 level=-1 text="the channel called hub1:test has been destroyed by You@YourMUD."
    """
    pass

class IMC2PacketRemoteAdmin(IMC2Packet):
    """
    Description:
    This packet is used in remote server administration. Please note that
    SHA-256 Support is *required* for a client to use this feature. The command
    can vary, in fact this very packet is highly dependant on the server it's
    being directed to. In most cases, sending the 'list' command will have a
    remote-admin enabled server send you the list of commands it will accept.

    Data:
    command=<string>
    The command being sent to the server for processing.

    data=<string>
    Data associated with the command. This is not always required.

    hash=<string>
    The SHA-256 hash that is verified by the server. This hash is generated in
    the same manner as an authentication packet.

    Example:
    You@YourMUD 1234567890 YourMUD remote-admin IMC@Hub1 command=list hash=<hash goes here>
    """
    pass

class IMC2PacketIceCmd(IMC2Packet):
    """
    Description:
    Used for remote channel administration. In most cases, one must be listed
    as a channel creator on the target server in order to do much with this
    packet. Other cases include channel operators.

    Data:
    channel=<string>
    The target server:channel for the command.

    command=<string>
    The command to be processed.

    data=<string>
    Data associated with the command. This is not always required.

    Example:
    You@YourMUD 1234567890 YourMUD ice-cmd IMC@hub1 channel=hub1:ichat command=list
    """
    pass

class IMC2PacketDestroy(IMC2Packet):
    """
    Description:
    Sent by a server to indicate the destruction of a channel it hosted.
    The mud should remove this channel from its local configuration.

    Data:
    channel=<string>  The server:channel being destroyed.
    """
    pass

class IMC2PacketWho(IMC2Packet):
    """
    Description:
    A seemingly mutli-purpose information-requesting packet. The istats
    packet currently only works on servers, or at least that's the case on
    MUD-Net servers. The 'finger' type takes a player name in addition to the
    type name.

    Example: "finger Dude". The 'who' and 'info' types take no argument.
    The MUD is responsible for building the reply text sent in the who-reply
    packet.

    Data:
    type=<string>  Types: who, info, "finger <name>", istats (server only)

    Example:
    Dude@SomeMUD 1234567890 SomeMUD!Hub1 who *@YourMUD type=who
    """
    pass

class IMC2PacketWhoReply(IMC2Packet):
    """
    Description:
    The multi-purpose reply to the multi-purpose information-requesting 'who'
    packet. The MUD is responsible for building the return data, including the
    format of it. The mud can use the permission level sent in the original who
    packet to filter the output. The example below is the MUD-Net format.

    Data:
    text=<string>  The formatted reply to a 'who' packet.

    Additional Notes:
    The example below is for the who list packet. The same construction would
    go into formatting the other types of who packets.

    Example:
    *@YourMUD 1234567890 YourMUD who-reply Dude@SomeMUD text="\n\r~R-=< ~WPlayers on YourMUD ~R>=-\n\r            ~Y-=< ~Wtelnet://yourmud.domain.com:1234 ~Y>=-\n\r\n\r~B--------------------------------=< ~WPlayers ~B>=---------------------------------\n\r\n\r      ~BPlayer        ~z<--->~G Mortal the Toy\n\r\n\r~R-------------------------------=< ~WImmortals ~R>=--------------------------------\n\r\n\r      ~YStaff        ~z<--->~G You the Immortal\n\r\n\r~Y<~W2 Players~Y> ~Y<~WHomepage: http://www.yourmud.com~Y> <~W  2 Max Since Reboot~Y>\n\r~Y<~W3 logins since last reboot on Tue Feb 24, 2004 6:55:59 PM EST~Y>"
    """
    pass

class IMC2PacketWhois(IMC2Packet):
    """
    Description:
    Sends a request to the network for the location of the specified player.

    Data:
    level=<int>  The permission level of the person making the request.

    Example:
    You@YourMUD 1234567890 YourMUD whois dude@* level=5
    """
    def __init__(self, pobject_id, whois_target):
        super(IMC2PacketWhois, self).__init__()
        self.sender = pobject_id  # Use the dbref, it's easier to trace back for the whois-reply.
        self.packet_type = 'whois'
        self.target = whois_target
        self.destination = '*'
        self.optional_data = {'level': '5'}

class IMC2PacketWhoisReply(IMC2Packet):
    """
    Description:
    The reply to a whois packet. The MUD is responsible for building and formatting
    the text sent back to the requesting player, and can use the permission level
    sent in the original whois packet to filter or block the response.

    Data:
    text=<string>  The whois text.

    Example:
    *@SomeMUD 1234567890 SomeMUD!Hub1 whois-reply You@YourMUD text="~RIMC Locate: ~YDude@SomeMUD: ~cOnline.\n\r"
    """
    pass

class IMC2PacketBeep(IMC2Packet):
    """
    Description:
    Sends out a beep packet to the Player@MUD. The client receiving this should
    then send a bell-character to the target player to 'beep' them.

    Example:
    You@YourMUD 1234567890 YourMUD beep dude@somemud
    """
    pass

class IMC2PacketIceChanWho(IMC2Packet):
    """
    Description:
    Sends a request to the specified MUD or * to list all the users listening
    to the specified channel.

    Data:
    level=<int>
    Sender's permission level.

    channel=<string>
    The server:chan name of the channel.

    lname=<string>
    The localname of the channel.

    Example:
    You@YourMUD 1234567890 YourMUD ice-chan-who somemud level=5 channel=Hub1:ichat lname=ichat
    """
    pass

class IMC2PacketIceChanWhoReply(IMC2Packet):
    """
    Description:
    This is the reply packet for an ice-chan-who. The MUD is responsible for
    creating and formatting the list sent back in the 'list' field. The
    permission level sent in the original ice-chan-who packet can be used to
    filter or block the response.

    Data:
    channel=<string>
    The server:chan of the requested channel.

    list=<string>
    The formatted list of local listeners for that MUD.

    Example:
    *@SomeMUD 1234567890 SomeMUD!Hub1 ice-chan-whoreply You@YourMUD channel=Hub1:ichat list="The following people are listening to ichat on SomeMUD:\n\r\n\rDude\n\r"
    """
    pass

class IMC2PacketLaston(IMC2Packet):
    """
    Description:
    This packet queries the server the mud is connected to to find out when a
    specified user was last seen by the network on a public channel.

    Data:
    username=<string>  The user, user@mud, or "all" being queried. Responses
    to this packet will be sent by the server in the form of a series of tells.

    Example: User@MUD 1234567890 MUD imc-laston SERVER username=somenamehere
    """
    pass

class IMC2PacketCloseNotify(IMC2Packet):
    """
    Description:
    This packet alerts the network when a server or MUD has disconnected. The
    server hosting the server or MUD is responsible for sending this packet
    out across the network. Clients need only process the packet to remove the
    disconnected MUD from their MUD list (or mark it as Disconnected).

    Data:
    host=<string>
    The MUD or server that has disconnected from the network.

    Example:
    *@Hub2 1234567890 Hub2!Hub1 close-notify *@* host=DisconnMUD
    """
    pass

if __name__ == "__main__":
    packstr = "Kayle@MW 1234567 MW!Server02!Server01 ice-msg-b *@* channel=Server01:ichat text=\"*they're going woot\" emote=0 echo=1"
    packstr = "*@Lythelian 1234567 Lythelian!Server01 is-alive *@* versionid=\"Tim's LPC IMC2 client 30-Jan-05 / Dead Souls integrated\" networkname=Mudbytes url=http://dead-souls.net host=70.32.76.142 port=6666 sha256=0"
    print IMC2Packet(packstr)

