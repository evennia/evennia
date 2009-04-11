"""
IMC2 user and administrative commands.
"""
import time
from django.conf import settings
from src.config.models import ConfigValue
from src.objects.models import Object
from src import defines_global
from src import ansi
from src.util import functions_general
from src.cmdtable import GLOBAL_CMD_TABLE
from src.imc2 import connection as imc2_conn
from src.imc2.packets import *
    
def cmd_imctest(command):
    """
    Shows a player's inventory.
    """
    source_object = command.source_object
    source_object.emit_to("Sending")
    packet = IMC2PacketWhois(source_object, 'Cratylus')
    imc2_conn.IMC2_PROTOCOL_INSTANCE.send_packet(packet)
    source_object.emit_to("Sent")
GLOBAL_CMD_TABLE.add_command("imctest", cmd_imctest)