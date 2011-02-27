"""
Comsys command module.
"""

from src.comms.models import Channel, Msg, ChannelConnection
from src.comms.channelhandler import CHANNELHANDLER
from src.utils import create, utils
from src.permissions.permissions import has_perm
from src.commands.default.muxcommand import MuxCommand            

def find_channel(caller, channelname, silent=False):
    """
    Helper function for searching for a single channel with
    some error handling.
    """
    channels = Channel.objects.channel_search(channelname)
    if not channels:
        if not silent:
            caller.msg("Channel '%s' not found." % channelname)
        return None
    elif len(channels) > 1:
        matches = ", ".join(["%s(%s)" % (chan.key, chan.id) for chan in channels])
        if not silent:
            caller.msg("Multiple channels match (be more specific): \n%s" % matches)
        return None
    return channels[0]
        
class CmdAddCom(MuxCommand):
    """
    addcom - subscribe to a channel with optional alias

    Usage:
       addcom [alias=] <channel>
       
    Joins a given channel. If alias is given, this will allow you to
    refer to the channel by this alias rather than the full channel
    name. Subsequent calls of this command can be used to add multiple
    aliases to an already joined channel.
    """

    key = "addcom"
    aliases = ["aliaschan","chanalias"]
    help_category = "Comms"

    def func(self):
        "Implement the command"
                
        caller = self.caller
        args = self.args
        player = caller.player

        if not args:
            caller.msg("Usage: addcom [alias =] channelname.")
            return

        if self.rhs:
            # rhs holds the channelname
            channelname = self.rhs            
            alias = self.lhs
        else:
            channelname = self.args
            alias = None

        channel = find_channel(caller, channelname)
        if not channel:
            # we use the custom search method to handle errors.
            return 

        # check permissions
        if not has_perm(player, channel, 'chan_listen'):
            caller.msg("You are not allowed to listen to this channel.")
            return 

        string = ""
        if not channel.has_connection(player):
            # we want to connect as well.
            if not channel.connect_to(player):
                # if this would have returned True, the player is connected
                caller.msg("You are not allowed to join this channel.")
                return 
            else:
                string += "You now listen to the channel %s. " % channel.key
            
        if alias:
            # create a nick and add it to the caller.
            caller.nickhandler(alias, channel.key, nick_type="channel")
            string += "You can now refer to the channel %s with the alias '%s'." 
            caller.msg(string % (channel.key, alias))
        else:
            string += "No alias added."
            caller.msg(string)


class CmdDelCom(MuxCommand):
    """
    delcom - unsubscribe from channel or remove channel alias

    Usage:
       delcom <alias or channel>

    If the full channel name is given, unsubscribe from the
    channel. If an alias is given, remove the alias but don't
    unsubscribe.
    """

    key = "delcom"
    aliases = ["delaliaschan, delchanalias"]
    help_category = "Comms"

    def func(self):
        "Implementing the command. "

        caller = self.caller
        player = caller.player

        if not self.args:
            caller.msg("Usage: delcom <alias or channel>")
            return        
        ostring = self.args.lower()
        
        channel = find_channel(caller, ostring, silent=True)
        if channel:
            # we have given a channel name - unsubscribe
            if not channel.has_connection(player):
                caller.msg("You are listening to that channel.")
                return 
            chkey = channel.key.lower()
            # find all nicks linked to this channel and delete them
            for nick in [nick for nick in caller.nicks 
                         if nick.db_type == "channel" and nick.db_real.lower() == chkey]:                
                nick.delete()
            channel.disconnect_from(player)
            caller.msg("You stop listening to channel '%s'. Eventual aliases were removed." % channel.key)
            return 
        else:
            # we are removing a channel nick
            channame = caller.nickhandler(ostring, nick_type="channel")            
            channel = find_channel(caller, channame, silent=True)
            if not channel:
                caller.msg("No channel with alias '%s' was found." % ostring)
            else:
                caller.nickhandler(ostring, nick_type="channel", delete=True)
                caller.msg("Your alias '%s' for channel %s was cleared." % (ostring, channel.key))
            
# def cmd_allcom(command):
#     """
#     allcom - operate on all channels

#     Usage:    
#       allcom [on | off | who | clear]

#     Allows the user to universally turn off or on all channels they are on,
#     as well as perform a 'who' for all channels they are on. Clear deletes
#     all channels.

#     Without argument, works like comlist.
#     """
    
#     caller = self.caller
#     arg = self.args
#     if not arg:
#         cmd_comlist(command)
#         caller.msg("(allcom arguments: 'on', 'off', 'who' and 'clear'.)")
#         return
#     arg = arg.strip()
#     if arg == 'clear':
#         cmd_clearcom(command)
#         return 
    
#     #get names and alias of all subscribed channels
#     chandict = comsys.plr_get_cdict(self.session)
#     aliaslist = chandict.keys()
#     aliaslist.sort()
#     if arg == "on":
#         for alias in aliaslist:
#             comsys.plr_chan_on(self.session, alias)
#     elif arg == "off":
#         for alias in aliaslist:
#             comsys.plr_chan_off(self.session, alias)
#     elif arg == "who":
#         s = ""
#         if not aliaslist:
#             s += "  (No channels)  "
#         for alias in aliaslist:
#             s += "-- %s (alias: %s)\n" % (chandict[alias][0],alias)
#             sess_list = comsys.get_cwho_list(chandict[alias][0])
#             objlist = [sess.get_pobject() for sess in sess_list]
#             plist = [p.get_name(show_dbref=caller.sees_dbrefs())
#                       for p in filter(lambda o: o.is_player(), objlist)]
#             olist = [o.get_name(show_dbref=caller.sees_dbrefs())
#                      for o in filter(lambda o: not o.is_player(), objlist)]
#             plist.sort()
#             olist.sort()
#             if plist:
#                 s += "    Players:\n      "
#                 for pname in plist: 
#                     s += "%s, " % pname
#                 s = s[:-2] + "\n"
#             if olist:
#                 s += "   Objects:\n       "
#                 for oname in olist:
#                     s += "%s, " % oname
#                 s = s[:-2] + "\n"
#         s = s[:-1]
#         caller.msg(s)    
# GLOBAL_CMD_TABLE.add_self("allcom", cmd_allcom, help_category="Comms")
            
## def cmd_clearcom(self):
##     """
##     clearcom - removes all channels

##     Usage:
##       clearcom

##     Effectively runs delcom on all channels the user is on.  It will remove
##     their aliases, remove them from the channel, and clear any titles they
##     have set.
##     """    
##     caller = self.caller
##     #get aall subscribed channel memberships
##     memberships = caller.channel_membership_set.all()

##     if not memberships:
##         s = "No channels to delete.  "
##     else:
##         s = "Deleting all channels in your subscriptions ...\n"
##     for membership in memberships:
##         chan_name = membership.channel.get_name()
##         s += "You have left %s.\n" % chan_name
##         comsys.plr_del_channel(caller, membership.user_alias)
##         comsys.send_cmessage(chan_name, "%s has left the channel." % caller.get_name(show_dbref=False))
##     s = s[:-1]
##     caller.msg(s)
## GLOBAL_CMD_TABLE.add_self("clearcom", cmd_clearcom)
        

class CmdChannels(MuxCommand):
    """
    @clist

    Usage:
      @channels
      @clist
      comlist

    Lists all available channels available to you, wether you listen to them or not. 
    Use 'comlist" to only view your current channel subscriptions.
    """
    key = "@channels"
    aliases = ["@clist", "channels", "comlist", "chanlist", "channellist", "all channels"]
    help_category = "Comms"

    def func(self):
        "Implement function"
        
        caller = self.caller
        
        # all channels we have available to listen to
        channels = [chan for chan in Channel.objects.get_all_channels() if has_perm(caller, chan, 'can_listen')]        
        if not channels:
            caller.msg("No channels available")
            return
        # all channel we are already subscribed to
        subs = [conn.channel for conn in ChannelConnection.objects.get_all_player_connections(caller.player)]

        if self.cmdstring != "comlist":

            string = "\nAll available channels:" 
            cols = [[" "], ["Channel"], ["Aliases"], ["Perms"], ["Description"]]
            for chan in channels:
                if chan in subs:
                    cols[0].append(">")
                else:
                    cols[0].append(" ")
                cols[1].append(chan.key)
                cols[2].append(",".join(chan.aliases))
                cols[3].append(",".join(chan.permissions))
                cols[4].append(chan.desc)
            # put into table 
            for ir, row in enumerate(utils.format_table(cols)):
                if ir == 0:
                    string += "\n{w" + "".join(row) + "{n"                    
                else:
                    string += "\n" + "".join(row)
            self.caller.msg(string)

        string = "\nYour channel subscriptions:"
        if not subs:
            string += "(None)"
        else:
            nicks = [nick for nick in caller.nicks if nick.db_type == 'channel']
            print nicks
            cols = [["Channel"], ["Aliases"], ["Description"]]
            for chan in subs:
                cols[0].append(chan.key)
                cols[1].append(",".join([nick.db_nick for nick in nicks 
                                         if nick.db_real.lower() == chan.key.lower()] + chan.aliases))
                cols[2].append(chan.desc)
            # put into table
            for ir, row in enumerate(utils.format_table(cols)):
                if ir == 0:
                    string += "\n{w" + "".join(row) + "{n"                    
                else:
                    string += "\n" + "".join(row)
        caller.msg(string)

class CmdCdestroy(MuxCommand):
    """
    @cdestroy

    Usage:
      @cdestroy <channel>

    Destroys a channel that you control.
    """

    key = "@cdestroy"
    help_category = "Comms"

    def func(self):
        "Destroy objects cleanly."
        caller = self.caller

        if not self.args:
            caller.msg("Usage: @cdestroy <channelname>")
            return
        channel = find_channel(caller, self.args)
        if not channel:
            caller.msg("Could not find channel %s." % self.args)
            return 
        if not has_perm(caller, channel, 'chan_admin', default_deny=True):
            caller.msg("You are not allowed to do that.")
            return 

        message = "%s is being destroyed. Make sure to change your aliases." % channel
        msgobj = create.create_message(caller, message, channel)
        channel.msg(msgobj)
        channel.delete()
        CHANNELHANDLER.update()
        caller.msg("%s was destroyed." % channel)
            
        
## def cmd_cset(self):
##     """
##     @cset

##     Sets various flags on a channel.
##     """
##     # TODO: Implement cmd_cset
##     pass

## def cmd_ccharge(self):
##     """
##     @ccharge

##     Sets the cost to transmit over a channel.  Default is free.
##     """
##     # TODO: Implement cmd_ccharge
##     pass

## def cmd_cboot(self):
##     """
##     @cboot

##     Usage:
##       @cboot[/quiet] <channel> = <player or object>

##     Kicks a player or object from a channel you control.
##     """
##     caller = self.caller
##     args = self.args
##     switches = self.self_switches

##     if not args or not "=" in args:
##         caller.msg("Usage: @cboot[/quiet] <channel> = <object>")
##         return
##     cname, objname = args.split("=",1)
##     cname, objname = cname.strip(), objname.strip()    
##     if not cname or not objname:
##         caller.msg("You must supply both channel and object.")
##         return
##     try:
##         channel = CommChannel.objects.get(name__iexact=cname)
##     except CommChannel.DoesNotExist:
##         caller.msg("Could not find channel %s." % cname)
##         return 

##     #do we have power over this channel?
##     if not channel.controlled_by(caller) or caller.has_perm("channels.channel_admin"):
##         caller.msg("You don't have that power in channel '%s'." % cname)
##         return    

##     #mux specification requires an * before player objects.
##     player_boot = False
##     if objname[0] == '*':        
##         player_boot = True
##         objname = objname[1:]
##     bootobj = Object.objects.player_name_search(objname)
##     if not bootobj:
##         caller.msg("Object '%s' not found." % objname)
##         return
##     if bootobj.is_player() and not player_boot:
##         caller.msg("To boot players you need to start their name with an '*'. ")
##         return    

##     #check so that this object really is on the channel in the first place
##     membership = bootobj.channel_membership_set.filter(channel__name__iexact=cname)
##     if not membership:
##         caller.msg("'%s' is not on channel '%s'." % (objname,cname)) 
##         return

##     #announce to channel
##     if not 'quiet' in switches:
##         comsys.send_cmessage(cname, "%s boots %s from channel." % \
##                              (caller.get_name(show_dbref=False), objname))

##     #all is set, boot the object by removing all its aliases from the channel. 
##     for mship in membership:
##         comsys.plr_del_channel(bootobj, mship.user_alias)

## GLOBAL_CMD_TABLE.add_self("@cboot", cmd_cboot, help_category="Comms")


## def cmd_cemit(self):
##     """
##     @cemit - send a message to channel

##     Usage:
##       @cemit <channel>=<message>
##       @cemit/noheader <channel>=<message>
##       @cemit/sendername <channel>=<message>

##     Allows the user to send a message over a channel as long as
##     they own or control it. It does not show the user's name unless they
##     provide the /sendername switch.
    
##     [[channel_selfs]]

##     Useful channel selfs
##     (see their help pages for detailed help and options)

##     - Listing channels
##       clist           - show all channels available to you
##       comlist         - show channels you listen to  

##     - Joining/parting channels
##       addcom          - add your alias for a channel 
##       delcom          - remove alias for channel
##                         (leave channel if no more aliases)      
##       allcom          - view, on/off or remove all your channels
##       clearcom        - removes all channels

##     - Other
##       who             - list who's online
##       <chanalias> off - silence channel temporarily
##       <chanalias> on  - turn silenced channel back on
##     """
##     caller = self.caller

##     if not self.args:
##         caller.msg("@cemit[/switches] <channel> = <message>")
##         return

##     eq_args = self.args.split('=', 1)
    
##     if len(eq_args) != 2:
##         caller.msg("You must provide a channel name and a message to emit.")
##         return
    
##     cname = eq_args[0].strip()
##     cmessage = eq_args[1].strip()
##     final_cmessage = cmessage
##     if len(cname) == 0:
##         caller.msg("You must provide a channel name to emit to.")
##         return
##     if len(cmessage) == 0:
##         caller.msg("You must provide a message to emit.")
##         return

##     name_matches = comsys.cname_search(cname, exact=True)
##     if name_matches:
##         cname_parsed = name_matches[0].get_name()
##     else:
##         caller.msg("Could not find channel %s." % (cname,))
##         return
    
##     # If this is False, don't show the channel header before
##     # the message. For example: [Public] Woohoo!
##     show_channel_header = True
##     if "noheader" in self.self_switches:
##         if not caller.has_perm("objects.emit_commchannel"):
##             caller.msg(defines_global.NOPERMS_MSG)
##             return
##         final_cmessage = cmessage
##         show_channel_header = False
##     else:
##         if "sendername" in self.self_switches:
##             if not comsys.plr_has_channel(self.session, cname_parsed, 
##                                           return_muted=False):
##                 caller.msg("You must be on %s to do that." % (cname_parsed,))
##                 return
##             final_cmessage = "%s: %s" % (caller.get_name(show_dbref=False), 
##                                          cmessage)
##         else:
##             if not caller.has_perm("objects.emit_commchannel"):
##                 caller.msg(defines_global.NOPERMS_MSG)
##                 return
##             final_cmessage = cmessage

##     if not "quiet" in self.self_switches:
##         caller.msg("Sent - %s" % (name_matches[0],))
##     comsys.send_cmessage(cname_parsed, final_cmessage,
##                          show_header=show_channel_header)
    
##     #pipe to external channels (IRC, IMC) eventually mapped to this channel
##     comsys.send_cexternal(cname_parsed, cmessage, caller=caller)

## GLOBAL_CMD_TABLE.add_self("@cemit", cmd_cemit,priv_tuple=("channels.emit_commchannel",),
##                              help_category="Comms")

## def cmd_cwho(self):
##     """
##     @cwho
    
##     Usage: 
##        @cwho channel[/all]

##     Displays the name, status and object type for a given channel.
##     Adding /all after the channel name will list disconnected players
##     as well.
##     """
##     session = self.session
##     caller = self.caller

##     if not self.args:
##         cmd_clist(self)
##         caller.msg("Usage: @cwho <channel>[/all]")
##         return
    
##     channel_name = self.args
    
##     if channel_name.strip() == '':
##         caller.msg("You must specify a channel name.")
##         return

##     name_matches = comsys.cname_search(channel_name, exact=True)

##     if name_matches:
##         # Check to make sure the user has permission to use @cwho.
##         is_channel_admin = caller.has_perm("objects.channel_admin")
##         is_controlled_by_plr = name_matches[0].controlled_by(caller)
        
##         if is_controlled_by_plr or is_channel_admin:
##             comsys.msg_cwho(caller, channel_name)
##         else:
##             caller.msg("Permission denied.")
##             return
##     else:
##         caller.msg("No channel with that name was found.")
##         return
## GLOBAL_CMD_TABLE.add_self("@cwho", cmd_cwho, help_category="Comms")

class CmdChannelCreate(MuxCommand):
    """
    @ccreate
    channelcreate 
    Usage:
     @ccreate <new channel>[;alias;alias...] = description

    Creates a new channel owned by you.
    """
    
    key = "@ccreate"
    aliases = "channelcreate"
    permissions = "cmd:ccreate"
    help_category = "Comms"

    def func(self):
        "Implement the command"

        caller = self.caller

        if not self.args:
            caller.msg("Usage @ccreate <channelname>[;alias;alias..] = description")
            return
        
        description = ""

        if self.rhs:
            description = self.rhs
        lhs = self.lhs
        channame = lhs
        aliases = None
        if ';' in lhs:
            channame, aliases = [part.strip().lower() 
                                 for part in lhs.split(';', 1) if part.strip()]
            aliases = [alias.strip().lower() 
                       for alias in aliases.split(';') if alias.strip()]                       
        channel = Channel.objects.channel_search(channame)        
        if channel:
            caller.msg("A channel with that name already exists.")
            return        
        # Create and set the channel up
        permissions = "chan_send:%s,chan_listen:%s,chan_admin:has_id(%s)"  % \
            ("Players","Players",caller.id)
        new_chan = create.create_channel(channame, aliases, description, permissions)
        new_chan.connect_to(caller)
        caller.msg("Created channel %s and connected to it." % new_chan.key)
    

## def cmd_cchown(self):
##     """
##     @cchown

##     Usage:
##       @cchown <channel> = <player>

##     Changes the owner of a channel.
##     """
##     caller = self.caller
##     args = self.args
##     if not args or "=" not in args:
##         caller.msg("Usage: @cchown <channel> = <player>")
##         return
##     cname, pname = args.split("=",1)
##     cname, pname = cname.strip(), pname.strip()
##     #locate channel
##     try:
##         channel = CommChannel.objects.get(name__iexact=cname)
##     except CommChannel.DoesNotExist:
##         caller.msg("Channel '%s' not found." % cname)
##         return
##     #check so we have ownership to give away.
##     if not channel.controlled_by(caller) and not caller.has_perm("channels.channel_admin"):
##         caller.msg("You don't control this channel.")
##         return
##     #find the new owner
##     new_owner = Object.objects.player_name_search(pname)
##     if not new_owner:
##         caller.msg("New owner '%s' not found." % pname)
##         return
##     old_owner = channel.get_owner()
##     old_pname = old_owner.get_name(show_dbref=False)
##     if old_owner == new_owner:
##         caller.msg("Owner unchanged.")
##         return
##     #all is set, change owner
##     channel.set_owner(new_owner)
##     caller.msg("Owner of %s changed from %s to %s." % (cname, old_pname, pname))
##     new_owner.msg("%s transfered ownership of channel '%s' to you." % (old_pname, cname))
## GLOBAL_CMD_TABLE.add_self("@cchown", cmd_cchown, help_category="Comms")


class CmdCdesc(MuxCommand):
    """
    @cdesc - set channel description

    Usage:
      @cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists. 
    """

    key = "@cdesc"
    permissions = "cmd:cdesc"
    help_category = "Comms"

    def func(self):
        "Implement command"
    
        caller = self.caller

        if not self.rhs:
            caller.msg("Usage: @cdesc <channel> = <description>")
            return        
        channel = find_channel(caller, self.lhs)
        if not channel:
            caller.msg("Channel '%s' not found." % self.lhs)
            return
        #check permissions
        if not has_perm(caller, channel, 'channel_admin'):
            caller.msg("You cant admin this channel.")
            return
        # set the description
        channel.desc = self.rhs
        channel.save()
        caller.msg("Description of channel '%s' set to '%s'." % (channel.key, self.rhs))

class CmdPage(MuxCommand):
    """
    page - send private message

    Usage:
      page[/switches] [<player>,<player>,... = <message>]
      tell        ''
      page/list <number>

    Switch:
      list  - show your last <number> of tells/pages. 
      
    Send a message to target user (if online). If no
    argument is given, you will instead see who was the last
    person you paged to. 
    """

    key = "page"
    aliases = ['tell']
    permissions = "cmd:tell"
    help_category = "Comms"
    
    def func(self):
    
        "Implement function using the Msg methods"

        caller = self.caller
        player = caller.player

        # get the messages we've sent
        messages_we_sent = list(Msg.objects.get_messages_by_sender(player))        
        pages_we_sent = [msg for msg in messages_we_sent 
                         if msg.receivers]
        # get last messages we've got
        pages_we_got = list(Msg.objects.get_messages_by_receiver(player))        
        
        if 'list' in self.switches:
            pages = pages_we_sent + pages_we_got
            pages.sort(lambda x, y: cmp(x.date_sent, y.date_sent))

            number = 10
            if self.args:
                try:
                    number = int(self.args)
                except ValueError:
                    pass

            if len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages 
        
            lastpages = "\n ".join(["{w%s{n {c%s{n to {c%s{n: %s" % (utils.datetime_format(page.date_sent), 
                                                                     page.sender.name, 
                            "{n,{c ".join([obj.name for obj in page.receivers]),
                                                              page.message)
                                    for page in lastpages])
            caller.msg("Your latest pages:\n %s" % lastpages )
            return

        if not self.args or not self.rhs:
            if pages_we_sent:
                string = "You last paged {c%s{n." % (", ".join([obj.name 
                                                                for obj in pages_we_sent[-1].receivers]))
                caller.msg(string)
                return
            else:
                string = "You haven't paged anyone yet."
                caller.msg(string)
                return

        # We are sending. Build a list of targets

        if not self.lhs:
            # If there are no targets, then set the targets 
            # to the last person they paged.
            if pages_we_sent:
                receivers = pages_we_sent[-1].receivers
            else:
                caller.msg("Who do you want to page?")
                return 
        else:
            receivers = self.lhslist        
        
        recobjs = []
        for receiver in set(receivers):
            if isinstance(receiver, basestring):
                pobj = caller.search("*%s" % (receiver.lstrip('*')), global_search=True)
                if not pobj:
                    return
            elif hasattr(receiver, 'character'):
                pobj = receiver.character
            else:
                caller.msg("Who do you want to page?")
                return 
            recobjs.append(pobj)
        if not recobjs:
            caller.msg("No players matching your target were found.")
            return 

        header = "{wPlayer{n {c%s{n {wpages:{n" % caller.key
        message = self.rhs

        # if message begins with a :, we assume it is a 'page-pose'
        if message.startswith(":"):            
            message = "%s %s" % (caller.key, message.strip(':').strip())

        # create the persistent message object
        msg = create.create_message(player, message, 
                                    receivers=recobjs)  

        # tell the players they got a message.
        received = []
        for pobj in recobjs:
            pobj.msg("%s %s" % (header, message))
            if hasattr(pobj, 'has_player') and not pobj.has_player:
                received.append("{C%s{n" % pobj.name)
                caller.msg("%s is offline. They will see your message if they list their pages later." % received[-1])
            else:
                received.append("{c%s{n" % pobj.name)
        received = ", ".join(received)
        caller.msg("You paged %s with: '%s'." % (received, message))
