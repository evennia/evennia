"""
IMC2 user and administrative commands.
"""
from django.conf import settings
from src import comsys
from src.cmdtable import GLOBAL_CMD_TABLE
from src.ansi import parse_ansi
from src.imc2.imc_ansi import IMCANSIParser
from src.imc2 import connection as imc2_conn
from src.imc2.packets import *
from src.imc2.models import IMC2ChannelMapping    
from src.imc2.trackers import IMC2_MUDLIST, IMC2_CHANLIST
from src.channels.models import CommChannel

def cmd_imcwhois(command):
    """
    imcwhois

    Usage:
      imcwhois
      
    IMC2 command. Shows a player's inventory.
    """
    source_object = command.source_object
    if not command.command_argument:    
        source_object.emit_to("Get what?")
        return
    else:
        source_object.emit_to("Sending IMC whois request. If you receive no response, no matches were found.")
        packet = IMC2PacketWhois(source_object, command.command_argument)
        imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
GLOBAL_CMD_TABLE.add_command("imcwhois", cmd_imcwhois, help_category="Comms")

def cmd_imcansi(command):
    """
    imcansi
    
    Usage:
      imcansi <string>
      
    Test IMC ANSI conversion.
    """
    source_object = command.source_object
    if not command.command_argument:    
        source_object.emit_to("You must provide a string to convert.")
        return
    else:
        retval = parse_ansi(command.command_argument, parser=IMCANSIParser())
        source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imcansi", cmd_imcansi, help_category="Comms")

def cmd_imcicerefresh(command):
    """
    imcicerefresh

    Usage:
      imcicerefresh

    IMC2: Semds an ice-refresh packet.
    """
    source_object = command.source_object
    packet = IMC2PacketIceRefresh()
    imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
    source_object.emit_to("Sent")
GLOBAL_CMD_TABLE.add_command("imcicerefresh", cmd_imcicerefresh, help_category="Comms")

def cmd_imcchanlist(command):
    """
    imcchanlist

    Usage:
      imcchanlist
      
    Shows the list of cached channels from the IMC2 Channel list.
    """
    source_object = command.source_object
    
    retval = 'Channels on %s\n\r' % imc2_conn.IMC2_PROTOCOL_INSTANCE.network_name
    
    retval += ' Full Name          Name       Owner           Perm    Policy\n\r'
    retval += ' ---------          ----       -----           ----    ------\n\r'
    for channel in IMC2_CHANLIST.get_channel_list():
        retval += ' %-18s %-10s %-15s %-7s %s\n\r' % (channel.name, 
                                                      channel.localname,
                                                      channel.owner, 
                                                      channel.level,
                                                      channel.policy)
    retval += '%s channels found.' % len(IMC2_CHANLIST.chan_list)
    source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imcchanlist", cmd_imcchanlist, help_category="Comms")

def cmd_imclist(command):
    """
    imclist

    Usage:
       imclist

    Shows the list of cached games from the IMC2 Mud list.
    """
    source_object = command.source_object
    
    retval = 'Active MUDs on %s\n\r' % imc2_conn.IMC2_PROTOCOL_INSTANCE.network_name
    
    for mudinfo in IMC2_MUDLIST.get_mud_list():
        mudline = ' %-20s %s' % (mudinfo.name, mudinfo.versionid)
        retval += '%s\n\r' % mudline[:78]
    retval += '%s active MUDs found.' % len(IMC2_MUDLIST.mud_list)
    source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imclist", cmd_imclist, help_category="Comms")

def cmd_imcstatus(command):
    """
    imcstatus

    Usage:
      imcstatus
      
    Shows some status information for your IMC2 connection.
    """
    source_object = command.source_object
    # This manages our game's plugged in services.
    collection = command.session.server.service_collection
    # Retrieve the IMC2 service.
    service = collection.getServiceNamed('IMC2')
    
    if service.running == 1:
        status_string = 'Running'
    else:
        status_string = 'Inactive'
    
    # Build the output to emit to the player.
    retval = '-' * 50
    retval += '\n\r'
    retval += 'IMC Status\n\r'
    retval += ' * MUD Name: %s\n\r' % (settings.IMC2_MUDNAME)
    retval += ' * Status: %s\n\r' % (status_string)
    retval += ' * Debugging Mode: %s\n\r' % (settings.IMC2_DEBUG)
    retval += ' * IMC Network Address: %s\n\r' % (settings.IMC2_SERVER_ADDRESS)
    retval += ' * IMC Network Port: %s\n\r' % (settings.IMC2_SERVER_PORT)
    retval += '-' * 50
    
    source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imcstatus", cmd_imcstatus,
                             priv_tuple=('imc2.admin_imc_channels',), help_category="Comms")


def cmd_IMC2chan(command):
    """
    @imc2chan

    Usage:
      @imc2chan <IMCServer> : <IMCchannel> <channel>

    Links an IMC channel to an existing evennia
    channel. You can link as many existing
    evennia channels as you like to the
    IMC channel this way. Running the command with an
    existing mapping will re-map the channels.

    Use 'imcchanlist' to get a list of IMC channels and
    servers. Note that both are case sensitive. 
    """
    source_object = command.source_object
    if not settings.IMC2_ENABLED:
        s = """IMC is not enabled. You need to activate it in game/settings.py."""
        source_object.emit_to(s)
        return
    args = command.command_argument
    if not args or len(args.split()) != 2 :
        source_object.emit_to("Usage: @imc2chan IMCServer:IMCchannel channel")
        return
    #identify the server-channel pair
    imcdata, channel = args.split()
    if not ":" in imcdata:
        source_object.emit_to("You need to supply an IMC Server:Channel pair.")
        return
    imclist = IMC2_CHANLIST.get_channel_list()
    imc_channels = filter(lambda c: c.name == imcdata, imclist)    
    if not imc_channels:
        source_object.emit_to("IMC server and channel '%s' not found." % imcdata)
        return
    else:
        imc_server_name, imc_channel_name = imcdata.split(":")
        
    #find evennia channel
    try:
        chanobj = comsys.get_cobj_from_name(channel)    
    except CommChannel.DoesNotExist:
        source_object.emit_to("Local channel '%s' not found (use real name, not alias)." % channel)
        return
       
    #create the mapping.
    outstring = ""
    mapping = IMC2ChannelMapping.objects.filter(channel__name=channel)
    if mapping:
        mapping = mapping[0]
        outstring = "Replacing %s. New " % mapping
    else:
        mapping = IMC2ChannelMapping()
    
    mapping.imc2_server_name = imc_server_name 
    mapping.imc2_channel_name = imc_channel_name
    mapping.channel = chanobj
    mapping.save()
    outstring += "Mapping set: %s." % mapping    
    source_object.emit_to(outstring)

GLOBAL_CMD_TABLE.add_command("@imc2chan",cmd_IMC2chan,
                             priv_tuple=("imc2.admin_imc_channels",), help_category="Comms")
    
