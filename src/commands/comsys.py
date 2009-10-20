"""
Comsys command module.
"""
from src import comsys
from src.channels.models import CommChannelMembership, CommChannel
from src import defines_global
from src.objects.models import Object
from src.cmdtable import GLOBAL_CMD_TABLE

def cmd_addcom(command):
    """
    addcom - join a channel with alias

    Usage:
       addcom [alias=] <channel>
       
    Allows adding an alias for a channel to make is easier and
    faster to use. Subsequent calls of this command can
    be used to add multiple aliases. 
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
    
    membership = source_object.channel_membership_set.filter(channel__name__iexact=chan_name) 
    try:
        chan = CommChannel.objects.get(name__iexact=chan_name)
        s = ""        

        #if we happened to have this alias already defined on another channel, make
        #sure to tell us. 
        aliasmatch = [cmatch.channel.name for cmatch in
                      source_object.channel_membership_set.filter(user_alias=chan_alias)
                      if cmatch.channel.name != chan_name]
        if aliasmatch: 
            s = "The alias '%s' is already in use (for channel '%s')." % (chan_alias, aliasmatch[0])
            source_object.emit_to(s)
            return 

        if membership:
            #we are already members of this channel. Set a different alias.
            # Note: To this without requiring a the user to logout then login again,
            # we need to delete, then rejoin the channel. Is this due to the lazy
            # loading? /Griatch
            prev_alias = membership[0].user_alias
            if chan_alias == prev_alias:
                s += "Alias unchanged."
            else:
                comsys.plr_del_channel(source_object, prev_alias)
                comsys.plr_add_channel(source_object, chan_alias, chan)
                s += "Channel '%s' alias changed from '%s' to '%s'." % (chan_name,prev_alias,
                                                               chan_alias)
        else:
            # This adds a CommChannelMembership object and a matching dict entry
            # on the session's cdict.
            comsys.plr_add_channel(source_object, chan_alias, chan)

            # Let the player know everything went well.
            s += "You join %s, with an alias of %s." % \
                (chan.get_name(), chan_alias)

            # Announce the user's joining.
            join_msg = "%s has joined the channel." % \
                       (source_object.get_name(show_dbref=False),)
            comsys.send_cmessage(chan, join_msg)
        source_object.emit_to(s)
    except CommChannel.DoesNotExist:
        # Failed to match iexact on channel's 'name' attribute.
        source_object.emit_to("Could not find channel %s." % chan_name)
GLOBAL_CMD_TABLE.add_command("addcom", cmd_addcom, help_category="Comms")

def cmd_delcom(command):
    """
    delcom - remove a channel alias

    Usage:
       delcom <alias>

    Removes the specified alias to a channel. If this is the last alias,
    the user is effectively removed from the channel.
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("Usage: delcom <alias>")
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
GLOBAL_CMD_TABLE.add_command("delcom", cmd_delcom,help_category="Comms")

def cmd_comlist(command):
    """
    comlist - list channel memberships

    Usage:
      comlist

    Lists the channels a user is subscribed to.
    """
    source_object = command.source_object 
    session = command.session

    s = "Your subscibed channels (use @clist for full chan list)\n"
    s += "** Alias          Channel               Status\n"
    channels = source_object.channel_membership_set.all()
    if not channels:
        s += "  (No subscriptions)  "
    for membership in channels:
        chan = membership.channel
        if membership.is_listening:
            chan_on = "On"
        else:
            chan_on = "Off"
        s += " %s%s %-15.14s%-22.15s%s\n" %  ('-','-',membership.user_alias, 
                                             chan.get_name(), chan_on)
    s = s[:-1]
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("comlist", cmd_comlist,help_category="Comms")
    
def cmd_allcom(command):
    """
    allcom - operate on all channels

    Usage:    
      allcom [on | off | who | clear]

    Allows the user to universally turn off or on all channels they are on,
    as well as perform a 'who' for all channels they are on. Clear deletes
    all channels.

    Without argument, works like comlist.
    """
    
    source_object = command.source_object
    arg = command.command_argument
    if not arg:
        cmd_comlist(command)
        source_object.emit_to("(allcom arguments: 'on', 'off', 'who' and 'clear'.)")
        return
    arg = arg.strip()
    if arg == 'clear':
        cmd_clearcom(command)
        return 
    
    #get names and alias of all subscribed channels
    chandict = comsys.plr_get_cdict(command.session)
    aliaslist = chandict.keys()
    aliaslist.sort()
    if arg == "on":
        for alias in aliaslist:
            comsys.plr_chan_on(command.session, alias)
    elif arg == "off":
        for alias in aliaslist:
            comsys.plr_chan_off(command.session, alias)
    elif arg == "who":
        s = ""
        if not aliaslist:
            s += "  (No channels)  "
        for alias in aliaslist:
            s += "-- %s (alias: %s)\n" % (chandict[alias][0],alias)
            sess_list = comsys.get_cwho_list(chandict[alias][0])
            objlist = [sess.get_pobject() for sess in sess_list]
            plist = [p.get_name(show_dbref=source_object.sees_dbrefs())
                      for p in filter(lambda o: o.is_player(), objlist)]
            olist = [o.get_name(show_dbref=source_object.sees_dbrefs())
                     for o in filter(lambda o: not o.is_player(), objlist)]
            plist.sort()
            olist.sort()
            if plist:
                s += "    Players:\n      "
                for pname in plist: 
                    s += "%s, " % pname
                s = s[:-2] + "\n"
            if olist:
                s += "   Objects:\n       "
                for oname in olist:
                    s += "%s, " % oname
                s = s[:-2] + "\n"
        s = s[:-1]
        source_object.emit_to(s)    
GLOBAL_CMD_TABLE.add_command("allcom", cmd_allcom, help_category="Comms")
            
def cmd_clearcom(command):
    """
    clearcom - removes all channels

    Usage:
      clearcom

    Effectively runs delcom on all channels the user is on.  It will remove
    their aliases, remove them from the channel, and clear any titles they
    have set.
    """    
    source_object = command.source_object
    #get aall subscribed channel memberships
    memberships = source_object.channel_membership_set.all()

    if not memberships:
        s = "No channels to delete.  "
    else:
        s = "Deleting all channels in your subscriptions ...\n"
    for membership in memberships:
        chan_name = membership.channel.get_name()
        s += "You have left %s.\n" % chan_name
        comsys.plr_del_channel(source_object, membership.user_alias)
        comsys.send_cmessage(chan_name, "%s has left the channel." % source_object.get_name(show_dbref=False))
    s = s[:-1]
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("clearcom", cmd_clearcom)
        
def cmd_clist(command):
    """
    @clist

    Usage:
      @clist

    Lists all available channels in the game.

    [[clist]]

    This is the same as @clist - it shows all
    available channels in game. 
    """
    session = command.session
    source_object = command.source_object

    s = "All channels (use comlist or allcom to see your subscriptions)\n"
    
    s += "** Channel        Owner         Description\n"
    channels = comsys.get_all_channels()
    if not channels:
        s += "(No channels)  "
    for chan in channels:
        s += " %s%s %-15.14s%-22.15s%s\n" % \
            ('-', 
             '-', 
             chan.get_name(), 
             chan.get_owner().get_name(show_dbref=False), 
             chan.description)
    s = s[:-1]
    #s += "** End of Channel List **"
    source_object.emit_to(s)
GLOBAL_CMD_TABLE.add_command("@clist", cmd_clist, help_category="Comms")
GLOBAL_CMD_TABLE.add_command("clist", cmd_clist, help_category="Comms")

def cmd_cdestroy(command):
    """
    @cdestroy

    Usage:
      @cdestroy <channel>

    Destroys a channel that you control.
    """
    source_object = command.source_object
    cname = command.command_argument

    if not cname:
        source_object.emit_to("Usage: @cdestroy <channelname>")
        return

    name_matches = comsys.cname_search(cname, exact=True)

    if not name_matches:
        source_object.emit_to("Could not find channel %s." % (cname,))
    else:
        is_controlled_by_plr = name_matches[0].controlled_by(source_object)
        if is_controlled_by_plr or source_object.has_perm("channels.channel_admin"): 
            source_object.emit_to("Channel %s destroyed." % (name_matches[0],))
            name_matches.delete()
        else:
            source_object.emit_to("Permission denied.")
            return
GLOBAL_CMD_TABLE.add_command("@cdestroy", cmd_cdestroy, help_category="Comms")
        
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

    Usage:
      @cboot[/quiet] <channel> = <player or object>

    Kicks a player or object from a channel you control.
    """
    source_object = command.source_object
    args = command.command_argument
    switches = command.command_switches

    if not args or not "=" in args:
        source_object.emit_to("Usage: @cboot[/quiet] <channel> = <object>")
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
    if not channel.controlled_by(source_object) or source_object.has_perm("channels.channel_admin"):
        source_object.emit_to("You don't have that power in channel '%s'." % cname)
        return    

    #mux specification requires an * before player objects.
    player_boot = False
    if objname[0] == '*':        
        player_boot = True
        objname = objname[1:]
    bootobj = Object.objects.player_name_search(objname)
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
        comsys.plr_del_channel(bootobj, mship.user_alias)

GLOBAL_CMD_TABLE.add_command("@cboot", cmd_cboot, help_category="Comms")


def cmd_cemit(command):
    """
    @cemit - send a message to channel

    Usage:
      @cemit <channel>=<message>
      @cemit/noheader <channel>=<message>
      @cemit/sendername <channel>=<message>

    Allows the user to send a message over a channel as long as
    they own or control it. It does not show the user's name unless they
    provide the /sendername switch.
    
    [[channel_commands]]

    Useful channel commands
    (see their help pages for detailed help and options)

    - Listing channels
      clist           - show all channels available to you
      comlist         - show channels you listen to  

    - Joining/parting channels
      addcom          - add your alias for a channel 
      delcom          - remove alias for channel
                        (leave channel if no more aliases)      
      allcom          - view, on/off or remove all your channels
      clearcom        - removes all channels

    - Other
      who             - list who's online
      <chanalias> off - silence channel temporarily
      <chanalias> on  - turn silenced channel back on
    """
    source_object = command.source_object

    if not command.command_argument:
        source_object.emit_to("@cemit[/switches] <channel> = <message>")
        return

    eq_args = command.command_argument.split('=', 1)
    
    if len(eq_args) != 2:
        source_object.emit_to("You must provide a channel name and a message to emit.")
        return
    
    cname = eq_args[0].strip()
    cmessage = eq_args[1].strip()
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
    comsys.send_cexternal(cname_parsed, cmessage, caller=source_object)

GLOBAL_CMD_TABLE.add_command("@cemit", cmd_cemit,priv_tuple=("channels.emit_commchannel",),
                             help_category="Comms")

def cmd_cwho(command):
    """
    @cwho
    
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
        source_object.emit_to("Usage: @cwho <channel>[/all]")
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
GLOBAL_CMD_TABLE.add_command("@cwho", cmd_cwho, help_category="Comms")

def cmd_ccreate(command):
    """
    @ccreate

    Usage:
     @ccreate <new channel>

    Creates a new channel owned by you.
    """
    source_object = command.source_object
    cname = command.command_argument

    if not cname:
        source_object.emit_to("Usage @ccreate <channelname>")
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
GLOBAL_CMD_TABLE.add_command("@ccreate", cmd_ccreate, help_category="Comms")

def cmd_cchown(command):
    """
    @cchown

    Usage:
      @cchown <channel> = <player>

    Changes the owner of a channel.
    """
    source_object = command.source_object
    args = command.command_argument
    if not args or "=" not in args:
        source_object.emit_to("Usage: @cchown <channel> = <player>")
        return
    cname, pname = args.split("=",1)
    cname, pname = cname.strip(), pname.strip()
    #locate channel
    try:
        channel = CommChannel.objects.get(name__iexact=cname)
    except CommChannel.DoesNotExist:
        source_object.emit_to("Channel '%s' not found." % cname)
        return
    #check so we have ownership to give away.
    if not channel.controlled_by(source_object) and not source_object.has_perm("channels.channel_admin"):
        source_object.emit_to("You don't control this channel.")
        return
    #find the new owner
    new_owner = Object.objects.player_name_search(pname)
    if not new_owner:
        source_object.emit_to("New owner '%s' not found." % pname)
        return
    old_owner = channel.get_owner()
    old_pname = old_owner.get_name(show_dbref=False)
    if old_owner == new_owner:
        source_object.emit_to("Owner unchanged.")
        return
    #all is set, change owner
    channel.set_owner(new_owner)
    source_object.emit_to("Owner of %s changed from %s to %s." % (cname, old_pname, pname))
    new_owner.emit_to("%s transfered ownership of channel '%s' to you." % (old_pname, cname))
GLOBAL_CMD_TABLE.add_command("@cchown", cmd_cchown, help_category="Comms")

def cmd_cdesc(command):
    """
    @cdesc - set channel description

    Usage:
      @cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists. 
    """
    source_object = command.source_object
    args = command.command_argument
    if not args or "=" not in args:
        source_object.emit_to("Usage: @cdesc <channel> = <description>")
        return
    cname, text = args.split("=",1)
    cname, text = cname.strip(), text.strip()
    #locate channel
    try:
        channel = CommChannel.objects.get(name__iexact=cname)
    except CommChannel.DoesNotExist:
        source_object.emit_to("Channel '%s' not found." % cname)
        return
    #check permissions
    if not channel.controlled_by(source_object) \
           and not source_object.has_perm("channels.channel_admin"):
        source_object.emit_to("You don't control this channel.")
        return
    # set the description
    channel.set_description(text)
    source_object.emit_to("Description of channel '%s' set to '%s'." % (cname, text))
GLOBAL_CMD_TABLE.add_command("@cdesc", cmd_cdesc, help_category="Comms")
