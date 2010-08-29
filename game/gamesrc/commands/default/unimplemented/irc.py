"""
IRC-related commands
"""
from twisted.application import internet
from django.conf import settings
from src.irc.connection import IRC_CHANNELS
from src.irc.models import IRCChannelMapping
from src import comsys
from src.cmdtable import GLOBAL_CMD_TABLE
from src.channels.models import CommChannel

def cmd_IRC2chan(command):
    """
    @irc2chan - link irc to ingame channel

    Usage:    
      @irc2chan <#IRCchannel> <local channel>

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

GLOBAL_CMD_TABLE.add_command("@irc2chan",cmd_IRC2chan,
                             priv_tuple=("irc.admin_irc_channels",),
                             help_category="Comms")
    
def cmd_IRCjoin(command):
    """
    @ircjoin - join a new irc channel

    Usage:
      @ircjoin <#IRCchannel>

    Attempts to connect a bot to a new IRC channel (don't forget that
    IRC channels begin with a #).
    The bot uses the connection details defined in the main settings. 

    Observe that channels added using this command does not survive a reboot. 
    """

    source_object = command.source_object
    arg = command.command_argument
    if not arg:
        source_object.emit_to("Usage: @ircjoin #irc_channel")
        return
    channel = arg.strip()
    if channel[0] != "#": channel = "#%s" % channel

    if not settings.IRC_ENABLED:
        source_object.emit_to("IRC services are not active. You need to turn them on in preferences.")
        return 

    #direct creation of bot (do not add to services)
    from src.irc.connection import connect_to_IRC
    connect_to_IRC(settings.IRC_NETWORK,
                   settings.IRC_PORT,
                   channel, settings.IRC_NICKNAME)

#    ---below should be checked so as to add subequent IRC bots to Services.
#       it adds just fine, but the bot does not connect. /Griatch
#    from src.irc.connection import IRC_BotFactory
#    from src.server import mud_service
#    irc = internet.TCPClient(settings.IRC_NETWORK, 
#                             settings.IRC_PORT, 
#                             IRC_BotFactory(channel,
#                                            settings.IRC_NETWORK,
#                                            settings.IRC_NICKNAME))            
#    irc.setName("%s:%s" % ("IRC",channel))
#    irc.setServiceParent(mud_service.service_collection)

GLOBAL_CMD_TABLE.add_command("@ircjoin",cmd_IRCjoin,
                             priv_tuple=("irc.admin_irc_channels",),
                             help_category="Comms")

def cmd_IRCchanlist(command):
    """
    ircchanlist

    Usage:
      ircchanlist

    Lists all externally available IRC channels.
    """
    source_object = command.source_object
    s = "Available IRC channels:"
    for c in IRC_CHANNELS:
        s += "\n  %s \t(nick '%s') on %s" % (c.factory.channel,
                                             c.factory.nickname,
                                             c.factory.network,)
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("ircchanlist", cmd_IRCchanlist,
                             help_category="Comms")
