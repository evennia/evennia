"""
Comsys command module.
"""
import time
from django.conf import settings
import src.comsys
from src import defines_global
from src import ansi
from src.util import functions_general
from src.cmdtable import GLOBAL_CMD_TABLE
from src.imc2.models import IMC2ChannelMapping
from src.imc2.packets import IMC2PacketIceMsgBroadcasted

def cmd_addcom(command):
    """
    addcom

    Adds an alias for a channel.
    addcom foo=Bar
    """
    source_object = command.source_object
    command_argument = command.command_argument

    if not command_argument:
        source_object.emit_to("Usage: addcom [alias=]channelname.")
        return    
    command_argument

    if '=' in command_argument:        
        chan_alias, chan_name = command.command_argument.split('=', 1)
        chan_alias, chan_name = chan_alias.strip(), chan_name.strip()
    else:
        chan_name = command_argument.strip()
        chan_alias = chan_name
        
    if chan_alias in command.session.channels_subscribed:
        source_object.emit_to("You are already on that channel.")
        return

    name_matches = src.comsys.cname_search(chan_name, exact=True)

    if name_matches:
        chan_name_parsed = name_matches[0].get_name()
        source_object.emit_to("You join %s, with an alias of %s." % \
            (chan_name_parsed, chan_alias))
        src.comsys.plr_set_channel(command.session, chan_alias, 
                                   chan_name_parsed, True)

        # Announce the user's joining.
        join_msg = "%s has joined the channel." % \
            (source_object.get_name(show_dbref=False),)
        src.comsys.send_cmessage(chan_name_parsed, join_msg)
    else:
        source_object.emit_to("Could not find channel %s." % chan_name)
GLOBAL_CMD_TABLE.add_command("addcom", cmd_addcom),

def cmd_delcom(command):
    """
    delcom

    Removes the specified alias to a channel. If this is the last alias,
    the user is effectively removed from the channel.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("You must specify a channel alias.")
        return

    if command.command_argument not in command.session.channels_subscribed:
        source_object.emit_to("You are not on that channel.")
        return

    chan_name = command.session.channels_subscribed[command.command_argument][0]
    source_object.emit_to("You have left %s." % chan_name)
    src.comsys.plr_del_channel(command.session, command.command_argument)

    # Announce the user's leaving.
    leave_msg = "%s has left the channel." % \
        (source_object.get_name(show_dbref=False),)
    src.comsys.send_cmessage(chan_name, leave_msg)
GLOBAL_CMD_TABLE.add_command("delcom", cmd_delcom),

def cmd_comlist(command):
    """
    Lists the channels a user is subscribed to.
    """
    source_object = command.source_object 
    session = command.session

    source_object.emit_to("Alias     Channel             Status")
    for chan in session.channels_subscribed:
        if session.channels_subscribed[chan][1]:
            chan_on = "On"
        else:
            chan_on = "Off"
            
        source_object.emit_to("%-9.9s %-19.19s %s" %
            (chan, session.channels_subscribed[chan][0], chan_on))
    source_object.emit_to("-- End of comlist --")
GLOBAL_CMD_TABLE.add_command("comlist", cmd_comlist),
    
def cmd_allcom(command):
    """
    allcom

    Allows the user to universally turn off or on all channels they are on,
    as well as perform a "who" for all channels they are on.
    """
    # TODO: Implement cmd_allcom
    pass

def cmd_clearcom(command):
    """
    clearcom

    Effectively runs delcom on all channels the user is on.  It will remove their aliases,
    remove them from the channel, and clear any titles they have set.
    """
    # TODO: Implement cmd_clearcom
    pass

def cmd_clist(command):
    """
    @clist

    Lists all available channels on the game.
    """
    session = command.session
    source_object = command.source_object
    
    source_object.emit_to("** Channel        Owner         Description")
    for chan in src.comsys.get_all_channels():
        source_object.emit_to("%s%s %-15.14s%-22.15s%s" %
            ('-', 
             '-', 
             chan.get_name(), 
             chan.get_owner().get_name(show_dbref=False), 
             chan.description))
    source_object.emit_to("** End of Channel List **")
GLOBAL_CMD_TABLE.add_command("@clist", cmd_clist),

def cmd_cdestroy(command):
    """
    @cdestroy

    Destroys a channel.
    """
    source_object = command.source_object
    cname = command.command_argument

    if not cname:
        source_object.emit_to("You must supply a name!")
        return

    name_matches = src.comsys.cname_search(cname, exact=True)

    if not name_matches:
        source_object.emit_to("Could not find channel %s." % (cname,))
    else:
        is_controlled_by_plr = name_matches[0].controlled_by(source_object)
        if is_controlled_by_plr: 
            source_object.emit_to("Channel %s destroyed." % (name_matches[0],))
            name_matches.delete()
        else:
            source_object.emit_to("Permission denied.")
            return
GLOBAL_CMD_TABLE.add_command("@cdestroy", cmd_cdestroy,
                             priv_tuple=("objects.delete_commchannel")),
        
def cmd_cset(command):
    """
    @cset

    Sets various flags on a channel.
    """
    # TODO: Implement cmd_cset
    pass


def cmd_ccharge(command):
    """
    @ccharge

    Sets the cost to transmit over a channel.  Default is free.
    """
    # TODO: Implement cmd_ccharge
    pass

def cmd_cboot(command):
    """
    @cboot

    Kicks a player or object from the channel.
    """
    # TODO: Implement cmd_cboot
    pass

def cmd_cemit(command):
    """
    @cemit <channel>=<message>
    @cemit/noheader <channel>=<message>
    @cemit/sendername <channel>=<message>

    Allows the user to send a message over a channel as long as
    they own or control it. It does not show the user's name unless they
    provide the /sendername switch.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Channel emit what?")
        return

    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) != 2:
        source_object.emit_to("You must provide a channel name and a message to emit.")
        return
    
    cname = eq_args[0]
    cmessage = eq_args[1]
    
    if len(cname) == 0:
        source_object.emit_to("You must provide a channel name to emit to.")
        return
    if len(cmessage) == 0:
        source_object.emit_to("You must provide a message to emit.")
        return

    name_matches = src.comsys.cname_search(cname, exact=True)
    if name_matches:
        cname_parsed = name_matches[0].get_name()
    else:
        source_object.emit_to("Could not find channel %s." % (cname,))
        return

    # If this is False, don't show the channel header before
    # the message. For example: [Public] Woohoo!
    show_channel_header = True
    if "noheader" in command.command_switches:
        if not source_object.has_perm("objects.emit_commchannel"):
            source_object.emit_to(defines_global.NOPERMS_MSG)
            return
        final_cmessage = cmessage
        show_channel_header = False
    else:
        if "sendername" in command.command_switches:
            if not src.comsys.plr_has_channel(command.session, cname_parsed, 
                                              return_muted=False):
                source_object.emit_to("You must be on %s to do that." % (cname_parsed,))
                return
            final_cmessage = "%s: %s" % (source_object.get_name(show_dbref=False), 
                                         cmessage)
        else:
            if not source_object.has_perm("objects.emit_commchannel"):
                source_object.emit_to(defines_global.NOPERMS_MSG)
                return
            final_cmessage = cmessage

    if not "quiet" in command.command_switches:
        source_object.emit_to("Sent - %s" % (name_matches[0],))
    src.comsys.send_cmessage(cname_parsed, final_cmessage,
                             show_header=show_channel_header)
    
    if settings.IMC2_ENABLED:
        # Look for IMC2 channel maps. If one is found, send an ice-msg-b
        # packet to the network.
        try:
            from src.imc2.connection import IMC2_PROTOCOL_INSTANCE
            map = IMC2ChannelMapping.objects.get(channel__name=cname_parsed)
            packet = IMC2PacketIceMsgBroadcasted(map.imc2_server_name,
                                                 map.imc2_channel_name, 
                                                 source_object, 
                                                 cmessage)
            IMC2_PROTOCOL_INSTANCE.send_packet(packet)
        except IMC2ChannelMapping.DoesNotExist:
            # No map found, do nothing.
            pass
GLOBAL_CMD_TABLE.add_command("@cemit", cmd_cemit),

def cmd_cwho(command):
    """
    @cwho

    Displays the name, status and object type for a given channel.
    Adding /all after the channel name will list disconnected players
    as well.
    """
    session = command.session
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("You must specify a channel name.")
        return
    
    channel_name = command.command_argument
    
    if channel_name.strip() == '':
        source_object.emit_to("You must specify a channel name.")
        return

    name_matches = src.comsys.cname_search(channel_name, exact=True)

    if name_matches:
        # Check to make sure the user has permission to use @cwho.
        is_channel_admin = source_object.has_perm("objects.channel_admin")
        is_controlled_by_plr = name_matches[0].controlled_by(source_object)
        
        if is_controlled_by_plr or is_channel_admin:
            src.comsys.msg_cwho(source_object, channel_name)
        else:
            source_object.emit_to("Permission denied.")
            return
    else:
        source_object.emit_to("No channel with that name was found.")
        return
GLOBAL_CMD_TABLE.add_command("@cwho", cmd_cwho),

def cmd_ccreate(command):
    """
    @ccreate

    Creates a new channel with the invoker being the default owner.
    """
    # TODO: Implement cmd_ccreate
    source_object = command.source_object
    cname = command.command_argument

    if not cname:
        source_object.emit_to("You must supply a name!")
        return
    
    if not source_object.has_perm("objects.channel_admin"):
        source_object.emit_to("Permission denied.")
        return

    name_matches = src.comsys.cname_search(cname, exact=True)

    if name_matches:
        source_object.emit_to("A channel with that name already exists.")
    else:
        # Create and set the object up.
        new_chan = src.comsys.create_channel(cname, source_object)
        source_object.emit_to("Channel %s created." % (new_chan.get_name(),))
GLOBAL_CMD_TABLE.add_command("@ccreate", cmd_ccreate,
                             priv_tuple=("objects.add_commchannel")),

def cmd_cchown(command):
    """
    @cchown

    Changes the owner of a channel.
    """
    # TODO: Implement cmd_cchown.
    pass
