"""
IRC-related functions
"""

from django.conf import settings
from src.irc.connection import IRC_CHANNELS
from src.irc.connection import connect_to_IRC
from src.irc.models import IRCChannelMapping
from src import comsys
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_IRC2chan(command):
    """
    @irc2chan IRCchannel channel

    Links an IRC channel (including #) to an existing
    evennia channel. You can link as many existing
    evennia channels as you like to the
    IRC channel this way. Running the command with an
    existing mapping will re-map the channels.

    """
    source_object = command.source_object
    if not settings.IRC_ENABLED:
        s = """IRC is not enabled. You need to activate it in game/settings.py."""
        source_object.emit_to(s)
        return
    args = command.command_argument
    if not args or len(args.split()) != 2 :
        source_object.emit_to("Usage: @irc2chan IRCchannel channel")
        return
    irc_channel, channel = args.split()
    if irc_channel not in [o.factory.channel for o in IRC_CHANNELS]:
        source_object.emit_to("IRC channel '%s' not found." % irc_channel)
        return
    try:
        chanobj = comsys.get_cobj_from_name(channel)    
    except CommChannel.DoesNotExist:
        source_object.emit_to("Local channel '%s' not found (use real name, not alias)." % channel)
        return
       
    #create the mapping.
    outstring = ""
    mapping = IRCChannelMapping.objects.filter(channel__name=channel)
    if mapping:
        mapping = mapping[0]
        outstring = "Replacing %s. New " % mapping
    else:
        mapping = IRCChannelMapping()
    
    mapping.irc_server_name = settings.IRC_NETWORK
    mapping.irc_channel_name = irc_channel   
    mapping.channel = chanobj
    mapping.save()
    outstring += "Mapping set: %s." % mapping    
    source_object.emit_to(outstring)

GLOBAL_CMD_TABLE.add_command("@irc2chan",cmd_IRC2chan,auto_help=True,staff_help=True,
                             priv_tuple=("objects.add_commchannel",))
    
def cmd_IRCjoin(command):
    """
    @ircjoin IRCchannel

    Attempts to connect a bot to a new IRC channel (don't forget that
    IRC channels begin with a #).
    The bot uses the connection details defined in the main settings. 

    Observe that channels added using this command does not survive a reboot. 
    """
    source_object = command.source_object
    arg = command.command_argument
    if not arg:
        source_object.emit_to("Usage: @ircjoin irc_channel")
        return
    channel = arg.strip()
    if channel[0] != "#": channel = "#%s" % channel
    
    connect_to_IRC(settings.IRC_NETWORK,
                   settings.IRC_PORT,
                   channel,settings.IRC_NICKNAME)
GLOBAL_CMD_TABLE.add_command("@ircjoin",cmd_IRCjoin,auto_help=True,
                             staff_help=True,
                             priv_tuple=("objects.add_commchannel",))

def cmd_IRCchanlist(command):
    """
    ircchanlist

    Lists all externally available IRC channels.
    """
    source_object = command.source_object
    s = "Available IRC channels:"
    for c in IRC_CHANNELS:
        s += "\n  %s \t(nick '%s') on %s" % (c.factory.channel,c.factory.nickname,c.factory.network,)
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("ircchanlist", cmd_IRCchanlist, auto_help=True)
