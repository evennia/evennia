"""
Comsys command module.
"""
import time
from django.conf import settings
from src import comsys
from src.channels.models import CommChannelMembership, CommChannel
from src import defines_global
from src import ansi
from src.util import functions_general
from src.cmdtable import GLOBAL_CMD_TABLE
#from src.imc2.models import IMC2ChannelMapping
#from src.imc2.packets import IMC2PacketIceMsgBroadcasted
#from src.irc.models import IRCChannelMapping
#from src.irc.connection import IRC_CHANNELS

def cmd_addcom(command):
    """
    addcom

    Usage:
       addcom [alias=] <channel>
       
    Joins a channel. Allows adding an alias for it to make it
    easier and faster to use. Subsequent calls of this command
    can be used to add multiple aliases. 
    """
    source_object = command.source_object
    command_argument = command.command_argument

    if not command_argument:
        source_object.emit_to("Usage: addcom [alias=]channelname.")
        return
    
    if '=' in command_argument:        
        chan_alias, chan_name = command.command_argument.split('=', 1)
        chan_alias, chan_name = chan_alias.strip(), chan_name.strip()
    else:
        chan_name = command_argument.strip()
        chan_alias = chan_name
        
    if source_object.channel_membership_set.filter(channel__name__iexact=chan_name):
        source_object.emit_to("You are already on that channel.")
        return 

    try:
        chan = CommChannel.objects.get(name__iexact=chan_name)
        # This adds a CommChannelMembership object and a matching dict entry
        # on the session's cdict.
        comsys.plr_add_channel(source_object, chan_alias, chan)
        
        # Let the player know everything went well.
        source_object.emit_to("You join %s, with an alias of %s." % \
            (chan.get_name(), chan_alias))

        # Announce the user's joining.
        join_msg = "%s has joined the channel." % \
            (source_object.get_name(show_dbref=False),)
        comsys.send_cmessage(chan, join_msg)
    except CommChannel.DoesNotExist:
        # Failed to match iexact on channel's 'name' attribute.
        source_object.emit_to("Could not find channel %s." % chan_name)
GLOBAL_CMD_TABLE.add_command("addcom", cmd_addcom),

def cmd_delcom(command):
    """
    delcom

    Usage:
       delcom <alias>

    Removes the specified alias to a channel. If this is the last alias,
    the user is effectively removed from the channel.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("You must specify a channel alias.")
        return

    try:
        membership = source_object.channel_membership_set.get(user_alias__iexact=command.command_argument)
    except CommChannelMembership.DoesNotExist:
        source_object.emit_to("You are not on that channel.")
        return

    chan_name = membership.channel.get_name()
    source_object.emit_to("You have left %s." % chan_name)
    comsys.plr_del_channel(source_object, command.command_argument)

    # Announce the user's leaving.
    leave_msg = "%s has left the channel." % \
        (source_object.get_name(show_dbref=False),)
    comsys.send_cmessage(chan_name, leave_msg)
GLOBAL_CMD_TABLE.add_command("delcom", cmd_delcom),

def cmd_comlist(command):
    """
    Lists the channels a user is subscribed to.
    """
    source_object = command.source_object 
    session = command.session

    s = "Your subscibed channels (to see all, use @clist)\n"
    s += "Alias     Channel             Status\n"
    for membership in source_object.channel_membership_set.all():
        chan = membership.channel
        if membership.is_listening:
            chan_on = "On"
        else:
            chan_on = "Off"
            
        s += "%-9.9s %-19.19s %s\n" % (membership.user_alias, 
                                     chan.get_name(), 
                                     chan_on)
    s += "-- End of comlist --"
    source_object.emit_to(s)
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

    s = "All channels (use comlist to see your subscriptions)\n"
    
    s += "** Channel        Owner         Description\n"
    for chan in comsys.get_all_channels():
        s += "%s%s %-15.14s%-22.15s%s\n" % \
            ('-', 
             '-', 
             chan.get_name(), 
             chan.get_owner().get_name(show_dbref=False), 
             chan.description)
    s += "** End of Channel List **"
    source_object.emit_to(s)
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

    name_matches = comsys.cname_search(cname, exact=True)

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
    @cboot[/quiet] <channel>=<object>

    Kicks a player or object from the channel
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args or not "=" in args:
        source_object.emit_to("Usage: @cboot[/quiet] <channel>=<object>")
        return
    cname, objname = args.split("=",1)
    cname, objname = cname.strip(), objname.strip()    
    if not cname or not objname:
        source_object.emit_to("You must supply both channel and object.")
        return
    try:
        channel = CommChannel.objects.get(name__iexact=cname)
    except CommChannel.DoesNotExist:
        source_object.emit_to("Could not find channel %s." % cname)
        return 

    #do we have power over this channel?
    if not channel.controlled_by(source_object):
        source_object.emit_to("You don't have that power in channel '%s'." % cname)
        return    

    #mux specification requires an * before player objects.
    player_boot = False
    if objname[0] == '*':        
        player_boot = True
        objname = objname[1:]
    bootobj = source_object.search_for_object(objname)
    if not bootobj:
        source_object.emit_to("Object '%s' not found." % objname)
        return
    if bootobj.is_player() and not player_boot:
        source_object.emit_to("To boot players you need to start their name with an '*'. ")
        return    

    #check so that this object really is on the channel in the first place
    membership = bootobj.channel_membership_set.filter(channel__name__iexact=cname)
    if not membership:
        source_object.emit_to("'%s' is not on channel '%s'." % (objname,cname)) 
        return

    #announce to channel
    if not 'quiet' in switches:
        comsys.send_cmessage(cname, "%s boots %s from channel." % \
                             (source_object.get_name(show_dbref=False), objname))

    #all is set, boot the object by removing all its aliases from the channel. 
    for mship in membership:
        alias = mship.user_alias
        comsys.plr_del_channel(bootobj, alias)

GLOBAL_CMD_TABLE.add_command("@cboot", cmd_cboot)


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
    final_cmessage = cmessage
    if len(cname) == 0:
        source_object.emit_to("You must provide a channel name to emit to.")
        return
    if len(cmessage) == 0:
        source_object.emit_to("You must provide a message to emit.")
        return

    name_matches = comsys.cname_search(cname, exact=True)
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
            if not comsys.plr_has_channel(command.session, cname_parsed, 
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
    comsys.send_cmessage(cname_parsed, final_cmessage,
                         show_header=show_channel_header)
    
    #pipe to external channels (IRC, IMC) eventually mapped to this channel
    comsys.send_cexternal(cname_parsed, "[%s] %s" % (cname_parsed,final_cmessage))

GLOBAL_CMD_TABLE.add_command("@cemit", cmd_cemit),

def cmd_cwho(command):
    """
    @cwho
       list 
    
    Usage: 
       @cwho channel[/all]

    Displays the name, status and object type for a given channel.
    Adding /all after the channel name will list disconnected players
    as well.
    """
    session = command.session
    source_object = command.source_object

    if not command.command_argument:
        cmd_clist(command)
        source_object.emit_to("You must specify a channel name.")
        return
    
    channel_name = command.command_argument
    
    if channel_name.strip() == '':
        source_object.emit_to("You must specify a channel name.")
        return

    name_matches = comsys.cname_search(channel_name, exact=True)

    if name_matches:
        # Check to make sure the user has permission to use @cwho.
        is_channel_admin = source_object.has_perm("objects.channel_admin")
        is_controlled_by_plr = name_matches[0].controlled_by(source_object)
        
        if is_controlled_by_plr or is_channel_admin:
            comsys.msg_cwho(source_object, channel_name)
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

    name_matches = comsys.cname_search(cname, exact=True)

    if name_matches:
        source_object.emit_to("A channel with that name already exists.")
    else:
        # Create and set the object up.
        new_chan = comsys.create_channel(cname, source_object)
        source_object.emit_to("Channel %s created." % (new_chan.get_name(),))
GLOBAL_CMD_TABLE.add_command("@ccreate", cmd_ccreate,
                             priv_tuple=("objects.add_commchannel",))

def cmd_cchown(command):
    """
    @cchown

    Changes the owner of a channel.
    """
    # TODO: Implement cmd_cchown.
    pass

