"""
IMC2 user and administrative commands.
"""
from time import time
from django.conf import settings
from src.config.models import ConfigValue
from src.objects.models import Object
from src import defines_global
from src import ansi
from src.util import functions_general
from src.cmdtable import GLOBAL_CMD_TABLE
from src.ansi import parse_ansi
from src.imc2.imc_ansi import IMCANSIParser
from src.imc2 import connection as imc2_conn
from src.imc2.packets import *
from src.imc2.trackers import IMC2_MUDLIST
    
def cmd_imcwhois(command):
    """
    Shows a player's inventory.
    """
    source_object = command.source_object
    if not command.command_argument:    
        source_object.emit_to("Get what?")
        return
    else:
        source_object.emit_to("Sending IMC whois request. If you receive no response, no matches were found.")
        packet = IMC2PacketWhois(source_object, command.command_argument)
        imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
GLOBAL_CMD_TABLE.add_command("imcwhois", cmd_imcwhois)

def cmd_imcansi(command):
    """
    Test IMC ANSI conversion.
    """
    source_object = command.source_object
    if not command.command_argument:    
        source_object.emit_to("You must provide a string to convert.")
        return
    else:
        retval = parse_ansi(command.command_argument, parser=IMCANSIParser())
        source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imcansi", cmd_imcansi)

def cmd_imckeepalive(command):
    """
    Sends an is-alive packet to the network.
    """
    source_object = command.source_object
    source_object.emit_to("Sending")
    packet = IMC2PacketIsAlive()
    imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
    source_object.emit_to("Sent")
GLOBAL_CMD_TABLE.add_command("imckeepalive", cmd_imckeepalive)

def cmd_imckeeprequest(command):
    """
    Sends a keepalive-request packet to the network.
    """
    source_object = command.source_object
    source_object.emit_to("Sending")
    packet = IMC2PacketKeepAliveRequest()
    imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
    source_object.emit_to("Sent")
GLOBAL_CMD_TABLE.add_command("imckeeprequest", cmd_imckeeprequest)

def cmd_imclist(command):
    """
    Shows the list of cached games from the IMC2 Mud list.
    """
    source_object = command.source_object
    
    retval = 'Active MUDs on %s\n\r' % imc2_conn.IMC2_PROTOCOL_INSTANCE.network_name
    
    for mudinfo in IMC2_MUDLIST.get_mud_list():
        mudline = ' %-20s %s' % (mudinfo.name, mudinfo.versionid)
        retval += '%s\n\r' % mudline[:78]
    retval += '%s active MUDs found.' % len(IMC2_MUDLIST.mud_list)
    source_object.emit_to(retval)
GLOBAL_CMD_TABLE.add_command("imclist", cmd_imclist)

def cmd_imcstatus(command):
    """
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
GLOBAL_CMD_TABLE.add_command("imcstatus", cmd_imcstatus)