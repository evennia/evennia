"""
Comsystem command module.

Comm commands are OOC commands and intended to be made available to
the Player at all times (they go into the PlayerCmdSet). So we
make sure to homogenize self.caller to always be the player object
for easy handling.

"""
from django.conf import settings
from src.comms.models import Channel, Msg, PlayerChannelConnection, ExternalChannelConnection
from src.comms import irc, imc2, rss
from src.comms.channelhandler import CHANNELHANDLER
from src.utils import create, utils
from src.commands.default.muxcommand import MuxCommand, MuxCommandOOC

# limit symbol import for API
__all__ = ("CommCommand", "CmdAddCom", "CmdDelCom", "CmdAllCom",
           "CmdChannels", "CmdCdestroy", "CmdCBoot", "CmdCemit",
           "CmdCWho", "CmdChannelCreate", "CmdCset", "CmdCdesc",
           "CmdPage", "CmdIRC2Chan", "CmdIMC2Chan", "CmdIMCInfo",
           "CmdIMCTell", "CmdRSS2Chan")

def find_channel(caller, channelname, silent=False, noaliases=False):
    """
    Helper function for searching for a single channel with
    some error handling.
    """
    channels = Channel.objects.channel_search(channelname)
    if not channels:
        if not noaliases:
            channels = [chan for chan in Channel.objects.all() if channelname in chan.aliases]
        if channels:
            return channels[0]
        if not silent:
            caller.msg("Channel '%s' not found." % channelname)
        return None
    elif len(channels) > 1:
        matches = ", ".join(["%s(%s)" % (chan.key, chan.id) for chan in channels])
        if not silent:
            caller.msg("Multiple channels match (be more specific): \n%s" % matches)
        return None
    return channels[0]

class CommCommand(MuxCommand):
    """
    This is a parent for comm-commands. Since
    These commands are to be available to the
    Player, we make sure to homogenize the caller
    here, so it's always seen as a player to the
    command body.
    """

    def parse(self):
        "overload parts of parse"

        # run parent
        super(CommCommand, self).parse()
        # fix obj->player
        if utils.inherits_from(self.caller, "src.objects.objects.Object"):
            # an object. Convert it to its player.
            self.caller = self.caller.player

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
    locks = "cmd:not pperm(channel_banned)"

    def func(self):
        "Implement the command"

        caller = self.caller
        args = self.args
        player = caller

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
        if not channel.access(player, 'listen'):
            caller.msg("%s: You are not allowed to listen to this channel." % channel.key)
            return

        string = ""
        if not channel.has_connection(player):
            # we want to connect as well.
            if not channel.connect_to(player):
                # if this would have returned True, the player is connected
                caller.msg("%s: You are not allowed to join this channel." % channel.key)
                return
            else:
                string += "You now listen to the channel %s. " % channel.key
        else:
            string += "You are already connected to channel %s." % channel.key

        if alias:
            # create a nick and add it to the caller.
            caller.nicks.add(alias, channel.key, nick_type="channel")
            string += " You can now refer to the channel %s with the alias '%s'."
            caller.msg(string % (channel.key, alias))
        else:
            string += " No alias added."
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
    locks = "cmd:not perm(channel_banned)"

    def func(self):
        "Implementing the command. "

        caller = self.caller
        player = caller

        if not self.args:
            caller.msg("Usage: delcom <alias or channel>")
            return
        ostring = self.args.lower()

        channel = find_channel(caller, ostring, silent=True, noaliases=True)
        if channel:
            # we have given a channel name - unsubscribe
            if not channel.has_connection(player):
                caller.msg("You are not listening to that channel.")
                return
            chkey = channel.key.lower()
            # find all nicks linked to this channel and delete them
            for nick in [nick for nick in caller.nicks.get(nick_type="channel")
                         if nick.db_real.lower() == chkey]:
                nick.delete()
            channel.disconnect_from(player)
            caller.msg("You stop listening to channel '%s'. Eventual aliases were removed." % channel.key)
            return
        else:
            # we are removing a channel nick
            channame = caller.nicks.get(ostring, nick_type="channel")
            channel = find_channel(caller, channame, silent=True)
            if not channel:
                caller.msg("No channel with alias '%s' was found." % ostring)
            else:
                if caller.nicks.has(ostring, nick_type="channel"):
                    caller.nicks.delete(ostring, nick_type="channel")
                    caller.msg("Your alias '%s' for channel %s was cleared." % (ostring, channel.key))
                else:
                    caller.msg("You had no such alias defined for this channel.")

class CmdAllCom(MuxCommand):
    """
    allcom - operate on all channels

    Usage:
      allcom [on | off | who | destroy]

    Allows the user to universally turn off or on all channels they are on,
    as well as perform a 'who' for all channels they are on. Destroy deletes
    all channels that you control.

    Without argument, works like comlist.
    """

    key = "allcom"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    def func(self):
        "Runs the function"

        caller = self.caller
        args = self.args
        if not args:
            caller.execute_cmd("@channels")
            caller.msg("(Usage: allcom on | off | who | destroy)")
            return

        if args == "on":
            # get names of all channels available to listen to and activate them all
            channels = [chan for chan in Channel.objects.get_all_channels() if chan.access(caller, 'listen')]
            for channel in channels:
                caller.execute_cmd("addcom %s" % channel.key)
        elif args == "off":
             #get names all subscribed channels and disconnect from them all
            channels = [conn.channel for conn in PlayerChannelConnection.objects.get_all_player_connections(caller)]
            for channel in channels:
                caller.execute_cmd("delcom %s" % channel.key)
        elif args == "destroy":
            # destroy all channels you control
            channels = [chan for chan in Channel.objects.get_all_channels() if chan.access(caller, 'control')]
            for channel in channels:
                caller.execute_cmd("@cdestroy %s" % channel.key)
        elif args == "who":
            # run a who, listing the subscribers on visible channels.
            string = "\n{CChannel subscriptions{n"
            channels = [chan for chan in Channel.objects.get_all_channels() if chan.access(caller, 'listen')]
            if not channels:
                string += "No channels."
            for channel in channels:
                string += "\n{w%s:{n\n" % channel.key
                conns = PlayerChannelConnection.objects.get_all_connections(channel)
                if conns:
                    string += "  " + ", ".join([conn.player.key for conn in conns])
                else:
                    string += "  <None>"
            caller.msg(string.strip())
        else:
            # wrong input
            caller.msg("Usage: allcom on | off | who | clear")

class CmdChannels(MuxCommand):
    """
    @clist

    Usage:
      @channels
      @clist
      comlist

    Lists all channels available to you, wether you listen to them or not.
    Use 'comlist" to only view your current channel subscriptions.
    """
    key = "@channels"
    aliases = ["@clist", "channels", "comlist", "chanlist", "channellist", "all channels"]
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    def func(self):
        "Implement function"

        caller = self.caller

        # all channels we have available to listen to
        channels = [chan for chan in Channel.objects.get_all_channels() if chan.access(caller, 'listen')]
        if not channels:
            caller.msg("No channels available.")
            return
        # all channel we are already subscribed to
        subs = [conn.channel for conn in PlayerChannelConnection.objects.get_all_player_connections(caller)]

        if self.cmdstring != "comlist":

            string = "\nChannels available:"
            cols = [[" "], ["Channel"], ["Aliases"], ["Perms"], ["Description"]]
            for chan in channels:
                if chan in subs:
                    cols[0].append(">")
                else:
                    cols[0].append(" ")
                cols[1].append(chan.key)
                cols[2].append(",".join(chan.aliases))
                cols[3].append(str(chan.locks))
                cols[4].append(chan.desc)
            # put into table
            for ir, row in enumerate(utils.format_table(cols)):
                if ir == 0:
                    string += "\n{w" + "".join(row) + "{n"
                else:
                    string += "\n" + "".join(row)
            self.caller.msg(string)

        string = "\nChannel subscriptions:"
        if not subs:
            string += "(None)"
        else:
            nicks = [nick for nick in caller.nicks.get(nick_type="channel")]
            cols = [[" "], ["Channel"], ["Aliases"], ["Description"]]
            for chan in subs:
                cols[0].append(" ")
                cols[1].append(chan.key)
                cols[2].append(",".join([nick.db_nick for nick in nicks
                                         if nick.db_real.lower() == chan.key.lower()] + chan.aliases))
                cols[3].append(chan.desc)
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
    locks = "cmd: not pperm(channel_banned)"

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
        if not channel.access(caller, 'control'):
            caller.msg("You are not allowed to do that.")
            return

        message = "%s is being destroyed. Make sure to change your aliases." % channel
        msgobj = create.create_message(caller, message, channel)
        channel.msg(msgobj)
        channel.delete()
        CHANNELHANDLER.update()
        caller.msg("%s was destroyed." % channel)

class CmdCBoot(MuxCommand):
    """
    @cboot

    Usage:
       @cboot[/quiet] <channel> = <player> [:reason]

    Switches:
       quiet - don't notify the channel

    Kicks a player or object from a channel you control.

    """

    key = "@cboot"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    def func(self):
        "implement the function"

        if not self.args or not self.rhs:
            string = "Usage: @cboot[/quiet] <channel> = <player> [:reason]"
            self.caller.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        reason = ""
        if ":" in self.rhs:
            playername, reason = self.rhs.rsplit(":", 1)
            searchstring = playername.lstrip('*')
        else:
            searchstring = self.rhs.lstrip('*')
        player = self.caller.search(searchstring, player=True)
        if not player:
            return
        if reason:
            reason = " (reason: %s)" % reason
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.caller.msg(string)
            return
        if not PlayerChannelConnection.objects.has_connection(player, channel):
            string = "Player %s is not connected to channel %s." % (player.key, channel.key)
            self.caller.msg(string)
            return
        if not "quiet" in self.switches:
            string = "%s boots %s from channel.%s" % (self.caller, player.key, reason)
            channel.msg(string)
        # find all player's nicks linked to this channel and delete them
        for nick in [nick for nick in player.character.nicks.get(nick_type="channel")
                     if nick.db_real.lower() == channel.key]:
            nick.delete()
        # disconnect player
        channel.disconnect_from(player)
        CHANNELHANDLER.update()

class CmdCemit(MuxCommand):
    """
    @cemit - send a message to channel

    Usage:
      @cemit[/switches] <channel> = <message>

    Switches:
      noheader - don't show the [channel] header before the message
      sendername - attach the sender's name before the message
      quiet - don't echo the message back to sender

    Allows the user to broadcast a message over a channel as long as
    they control it. It does not show the user's name unless they
    provide the /sendername switch.

    """

    key = "@cemit"
    aliases = ["@cmsg"]
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    def func(self):
        "Implement function"

        if not self.args or not self.rhs:
            string = "Usage: @cemit[/switches] <channel> = <message>"
            self.caller.msg(string)
            return
        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.caller.msg(string)
            return
        message = self.rhs
        if "sendername" in self.switches:
            message = "%s: %s" % (self.caller.key, message)
        if not "noheader" in self.switches:
            message = "[%s] %s" % (channel.key, message)
        channel.msg(message)
        if not "quiet" in self.switches:
            string = "Sent to channel %s: %s" % (channel.key, message)
            self.caller.msg(string)

class CmdCWho(MuxCommand):
    """
    @cwho

    Usage:
      @cwho <channel>

    List who is connected to a given channel you have access to.
    """
    key = "@cwho"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    def func(self):
        "implement function"

        if not self.args:
            string = "Usage: @cwho <channel>"
            self.caller.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "listen"):
            string = "You can't access this channel."
            self.caller.msg(string)
        string = "\n{CChannel subscriptions{n"
        string += "\n{w%s:{n\n" % channel.key
        conns = PlayerChannelConnection.objects.get_all_connections(channel)
        if conns:
            string += "  " + ", ".join([conn.player.key for conn in conns])
        else:
            string += "  <None>"
        self.caller.msg(string.strip())

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
    locks = "cmd:not pperm(channel_banned)"
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
        lockstring = "send:all();listen:all();control:id(%s)" % caller.id
        new_chan = create.create_channel(channame, aliases, description, locks=lockstring)
        new_chan.connect_to(caller)
        caller.msg("Created channel %s and connected to it." % new_chan.key)


class CmdCset(MuxCommand):
    """
    @cset - changes channel access restrictions

    Usage:
      @cset <channel> [= <lockstring>]

    Changes the lock access restrictions of a channel. If no
    lockstring was given, view the current lock definitions.
    """

    key = "@cset"
    locks = "cmd:not pperm(channel_banned)"
    aliases = ["@cclock"]
    help_category = "Comms"

    def func(self):
        "run the function"

        if not self.args:
            string = "Usage: @cset channel [= lockstring]"
            self.caller.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not self.rhs:
            # no =, so just view the current locks
            string = "Current locks on %s:" % channel.key
            string = "%s\n %s" % (string, channel.locks)
            self.caller.msg(string)
            return
        # we want to add/change a lock.
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.caller.msg(string)
            return
        # Try to add the lock
        channel.locks.add(self.rhs)
        string = "Lock(s) applied. "
        string += "Current locks on %s:" % channel.key
        string = "%s\n %s" % (string, channel.locks)
        self.caller.msg(string)


class CmdCdesc(MuxCommand):
    """
    @cdesc - set channel description

    Usage:
      @cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists.
    """

    key = "@cdesc"
    locks = "cmd:not pperm(channel_banned)"
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
        if not caller.access(caller, 'control'):
            caller.msg("You cant admin this channel.")
            return
        # set the description
        channel.desc = self.rhs
        channel.save()
        caller.msg("Description of channel '%s' set to '%s'." % (channel.key, self.rhs))

class CmdPage(MuxCommandOOC):
    """
    page - send private message

    Usage:
      page[/switches] [<player>,<player>,... = <message>]
      tell        ''
      page <number>

    Switch:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no
    argument is given, you will get a list of your latest messages.
    """

    key = "page"
    aliases = ['tell']
    locks = "cmd:not pperm(page_banned)"
    help_category = "Comms"

    def func(self):
        "Implement function using the Msg methods"

        # this is a MuxCommandOOC, which means caller will be a Player.
        caller = self.caller

        # get the messages we've sent (not to channels)
        pages_we_sent = Msg.objects.get_messages_by_sender(caller, exclude_channel_messages=True)
        # get last messages we've got
        pages_we_got = Msg.objects.get_messages_by_receiver(caller)


        if 'last' in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[-1].receivers)
                caller.msg("You last paged {c%s{n:%s" % (recv, pages_we_sent[-1].message))
                return
            else:
                caller.msg("You haven't paged anyone yet.")
                return

        if not self.args or not self.rhs:
            pages = pages_we_sent + pages_we_got
            pages.sort(lambda x, y: cmp(x.date_sent, y.date_sent))

            number = 5
            if self.args:
                try:
                    number = int(self.args)
                except ValueError:
                    caller.msg("Usage: tell [<player> = msg]")
                    return

            if len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages

            lastpages = "\n ".join("{w%s{n {c%s{n to {c%s{n: %s" % (utils.datetime_format(page.date_sent),
                                                                    ",".join(obj.key for obj in page.senders),
                                                                    "{n,{c ".join([obj.name for obj in page.receivers]),
                                                                    page.message)
                                                        for page in lastpages)

            if lastpages:
                string = "Your latest pages:\n %s" % lastpages
            else:
                string = "You haven't paged anyone yet."
            caller.msg(string)
            return


        # We are sending. Build a list of targets

        if not self.lhs:
            # If there are no targets, then set the targets
            # to the last person we paged.
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
                pobj = caller.search(receiver)
            elif hasattr(receiver, 'character'):
                pobj = receiver.character
            else:
                caller.msg("Who do you want to page?")
                return
            if pobj:
                recobjs.append(pobj)
        if not recobjs:
            caller.msg("Noone found to page.")
            return

        header = "{wPlayer{n {c%s{n {wpages:{n" % caller.key
        message = self.rhs

        # if message begins with a :, we assume it is a 'page-pose'
        if message.startswith(":"):
            message = "%s %s" % (caller.key, message.strip(':').strip())

        # create the persistent message object
        create.create_message(caller, message,
                              receivers=recobjs)

        # tell the players they got a message.
        received = []
        rstrings = []
        for pobj in recobjs:
            if not pobj.access(caller, 'msg'):
                rstrings.append("You are not allowed to page %s." % pobj)
                continue
            pobj.msg("%s %s" % (header, message))
            if hasattr(pobj, 'has_player') and not pobj.has_player:
                received.append("{C%s{n" % pobj.name)
                rstrings.append("%s is offline. They will see your message if they list their pages later." % received[-1])
            else:
                received.append("{c%s{n" % pobj.name)
        if rstrings:
            caller.msg(rstrings = "\n".join(rstrings))
        caller.msg("You paged %s with: '%s'." % (", ".join(received), message))


class CmdIRC2Chan(MuxCommand):
    """
    @irc2chan - link evennia channel to an IRC channel

    Usage:
      @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>

    Switches:
      /disconnect - this will delete the bot and remove the irc connection to the channel.
      /remove     -                                 "
      /list       - show all irc<->evennia mappings

    Example:
      @irc2chan myircchan = irc.dalnet.net 6667 myevennia-channel evennia-bot

    This creates an IRC bot that connects to a given IRC network and channel. It will
    relay everything said in the evennia channel to the IRC channel and vice versa. The
    bot will automatically connect at server start, so this comman need only be given once.
    The /disconnect switch will permanently delete the bot. To only temporarily deactivate it,
    use the @services command instead.
    """

    key = "@irc2chan"
    locks = "cmd:serversetting(IRC_ENABLED) and pperm(Immortals)"
    help_category = "Comms"

    def func(self):
        "Setup the irc-channel mapping"

        if not settings.IRC_ENABLED:
            string = """IRC is not enabled. You need to activate it in game/settings.py."""
            self.caller.msg(string)
            return

        if 'list' in self.switches:
            # show all connections
            connections = ExternalChannelConnection.objects.filter(db_external_key__startswith='irc_')
            if connections:
                cols = [["Evennia channel"], ["IRC channel"]]
                for conn in connections:
                    cols[0].append(conn.channel.key)
                    cols[1].append(" ".join(conn.external_config.split('|')))
                ftable = utils.format_table(cols)
                string = ""
                for ir, row in enumerate(ftable):
                    if ir == 0:
                        string += "{w%s{n" % "".join(row)
                    else:
                        string += "\n" + "".join(row)
                self.caller.msg(string)
            else:
                self.caller.msg("No connections found.")
            return

        if not self.args or not self.rhs:
            string = "Usage: @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>"
            self.caller.msg(string)
            return
        channel = self.lhs
        self.rhs = self.rhs.replace('#', ' ') # to avoid Python comment issues
        try:
            irc_network, irc_port, irc_channel, irc_botname = [part.strip() for part in self.rhs.split(None, 3)]
            irc_channel = "#%s" % irc_channel
        except Exception:
            string = "IRC bot definition '%s' is not valid." % self.rhs
            self.caller.msg(string)
            return

        if 'disconnect' in self.switches or 'remove' in self.switches or 'delete' in self.switches:
            chanmatch = find_channel(self.caller, channel, silent=True)
            if chanmatch:
                channel = chanmatch.key

            ok = irc.delete_connection(channel, irc_network, irc_port, irc_channel, irc_botname)
            if not ok:
                self.caller.msg("IRC connection/bot could not be removed, does it exist?")
            else:
                self.caller.msg("IRC connection destroyed.")
            return

        channel = find_channel(self.caller, channel)
        if not channel:
            return
        ok = irc.create_connection(channel, irc_network, irc_port, irc_channel, irc_botname)
        if not ok:
            self.caller.msg("This IRC connection already exists.")
            return
        self.caller.msg("Connection created. Starting IRC bot.")

class CmdIMC2Chan(MuxCommand):
    """
    imc2chan - link an evennia channel to imc2

    Usage:
      @imc2chan[/switches] <evennia_channel> = <imc2_channel>

    Switches:
      /disconnect - this clear the imc2 connection to the channel.
      /remove     -                "
      /list       - show all imc2<->evennia mappings

    Example:
      @imc2chan myimcchan = ievennia

    Connect an existing evennia channel to a channel on an IMC2
    network. The network contact information is defined in settings and
    should already be accessed at this point. Use @imcchanlist to see
    available IMC channels.

    """

    key = "@imc2chan"
    locks = "cmd:serversetting(IMC2_ENABLED) and pperm(Immortals)"
    help_category = "Comms"

    def func(self):
        "Setup the imc-channel mapping"

        if not settings.IMC2_ENABLED:
            string = """IMC is not enabled. You need to activate it in game/settings.py."""
            self.caller.msg(string)
            return

        if 'list' in self.switches:
            # show all connections
            connections = ExternalChannelConnection.objects.filter(db_external_key__startswith='imc2_')
            if connections:
                cols = [["Evennia channel"], ["<->"], ["IMC channel"]]
                for conn in connections:
                    cols[0].append(conn.channel.key)
                    cols[1].append("")
                    cols[2].append(conn.external_config)
                ftable = utils.format_table(cols)
                string = ""
                for ir, row in enumerate(ftable):
                    if ir == 0:
                        string += "{w%s{n" % "".join(row)
                    else:
                        string += "\n" + "".join(row)
                self.caller.msg(string)
            else:
                self.caller.msg("No connections found.")
            return

        if not self.args or not self.rhs:
            string = "Usage: @imc2chan[/switches] <evennia_channel> = <imc2_channel>"
            self.caller.msg(string)
            return

        channel = self.lhs
        imc2_channel = self.rhs

        if 'disconnect' in self.switches or 'remove' in self.switches or 'delete' in self.switches:
            # we don't search for channels before this since we want to clear the link
            # also if the channel no longer exists.
            ok = imc2.delete_connection(channel, imc2_channel)
            if not ok:
                self.caller.msg("IMC2 connection could not be removed, does it exist?")
            else:
                self.caller.msg("IMC2 connection destroyed.")
            return

        # actually get the channel object
        channel = find_channel(self.caller, channel)
        if not channel:
            return

        ok = imc2.create_connection(channel, imc2_channel)
        if not ok:
            self.caller.msg("The connection %s <-> %s  already exists." % (channel.key, imc2_channel))
            return
        self.caller.msg("Created connection channel %s <-> IMC channel %s." % (channel.key, imc2_channel))


class CmdIMCInfo(MuxCommand):
    """
    imcinfo - package of imc info commands

    Usage:
      @imcinfo[/switches]
      @imcchanlist - list imc2 channels
      @imclist -     list connected muds
      @imcwhois <playername> - whois info about a remote player

    Switches for @imcinfo:
      channels - as @imcchanlist (default)
      games or muds - as @imclist
      whois - as @imcwhois (requires an additional argument)
      update - force an update of all lists

    Shows lists of games or channels on the IMC2 network.
    """

    key = "@imcinfo"
    aliases = ["@imcchanlist", "@imclist", "@imcwhois"]
    locks = "cmd: serversetting(IMC2_ENABLED) and pperm(Wizards)"
    help_category = "Comms"

    def func(self):
        "Run the command"

        if not settings.IMC2_ENABLED:
            string = """IMC is not enabled. You need to activate it in game/settings.py."""
            self.caller.msg(string)
            return

        if "update" in self.switches:
            # update the lists
            import time
            from src.comms.imc2lib import imc2_packets as pck
            from src.comms.imc2 import IMC2_MUDLIST, IMC2_CHANLIST, IMC2_CLIENT
            # update connected muds
            IMC2_CLIENT.send_packet(pck.IMC2PacketKeepAliveRequest())
            # prune inactive muds
            for name, mudinfo in IMC2_MUDLIST.mud_list.items():
                if time.time() - mudinfo.last_updated > 3599:
                    del IMC2_MUDLIST.mud_list[name]
            # update channel list
            IMC2_CLIENT.send_packet(pck.IMC2PacketIceRefresh())
            self.caller.msg("IMC2 lists were re-synced.")

        elif "games" in self.switches or "muds" in self.switches or self.cmdstring == "@imclist":
            # list muds
            from src.comms.imc2 import IMC2_MUDLIST

            muds = IMC2_MUDLIST.get_mud_list()
            networks = set(mud.networkname for mud in muds)
            string = ""
            nmuds = 0
            for network in networks:
                string += "\n {GMuds registered on %s:{n" % network
                cols = [["Name"], ["Url"], ["Host"], ["Port"]]
                for mud in (mud for mud in muds if mud.networkname == network):
                    nmuds += 1
                    cols[0].append(mud.name)
                    cols[1].append(mud.url)
                    cols[2].append(mud.host)
                    cols[3].append(mud.port)
                ftable = utils.format_table(cols)
                for ir, row in enumerate(ftable):
                    if ir == 0:
                        string += "\n{w" + "".join(row) + "{n"
                    else:
                        string += "\n" + "".join(row)
            string += "\n %i Muds found." % nmuds
            self.caller.msg(string)

        elif "whois" in self.switches or self.cmdstring == "@imcwhois":
            # find out about a player
            if not self.args:
                self.caller.msg("Usage: @imcwhois <playername>")
                return
            from src.comms.imc2 import IMC2_CLIENT
            self.caller.msg("Sending IMC whois request. If you receive no response, no matches were found.")
            IMC2_CLIENT.msg_imc2(None, from_obj=self.caller, packet_type="imcwhois", data={"target":self.args})

        elif not self.switches or "channels" in self.switches or self.cmdstring == "@imcchanlist":
            # show channels
            from src.comms.imc2 import IMC2_CHANLIST, IMC2_CLIENT

            channels = IMC2_CHANLIST.get_channel_list()
            string = ""
            nchans = 0
            string += "\n {GChannels on %s:{n" % IMC2_CLIENT.factory.network
            cols = [["Full name"], ["Name"], ["Owner"], ["Perm"], ["Policy"]]
            for channel in channels:
                nchans += 1
                cols[0].append(channel.name)
                cols[1].append(channel.localname)
                cols[2].append(channel.owner)
                cols[3].append(channel.level)
                cols[4].append(channel.policy)
            ftable = utils.format_table(cols)
            for ir, row in enumerate(ftable):
                if ir == 0:
                    string += "\n{w" + "".join(row) + "{n"
                else:
                    string += "\n" + "".join(row)
            string += "\n %i Channels found." % nchans
            self.caller.msg(string)

        else:
            # no valid inputs
            string = "Usage: imcinfo|imcchanlist|imclist"
            self.caller.msg(string)

# unclear if this is working ...
class CmdIMCTell(MuxCommand):
    """
    imctell - send a page to a remote IMC player

    Usage:
      imctell User@MUD = <msg>
      imcpage      "

    Sends a page to a user on a remote MUD, connected
    over IMC2.
    """

    key = "imctell"
    aliases = ["imcpage", "imc2tell", "imc2page"]
    locks = "cmd: serversetting(IMC2_ENABLED)"
    help_category = "Comms"

    def func(self):
        "Send tell across IMC"

        if not settings.IMC2_ENABLED:
            string = """IMC is not enabled. You need to activate it in game/settings.py."""
            self.caller.msg(string)
            return

        from src.comms.imc2 import IMC2_CLIENT

        if not self.args or not '@' in self.lhs or not self.rhs:
            string = "Usage: imctell User@Mud = <msg>"
            self.caller.msg(string)
            return
        target, destination = self.lhs.split("@", 1)
        message = self.rhs.strip()
        data = {"target":target, "destination":destination}

        # send to imc2
        IMC2_CLIENT.msg_imc2(message, from_obj=self.caller, packet_type="imctell", data=data)

        self.caller.msg("You paged {c%s@%s{n (over IMC): '%s'." % (target, destination, message))


# RSS connection
class CmdRSS2Chan(MuxCommand):
    """
    @rss2chan - link evennia channel to an RSS feed

    Usage:
      @rss2chan[/switches] <evennia_channel> = <rss_url>

    Switches:
      /disconnect - this will stop the feed and remove the connection to the channel.
      /remove     -                                 "
      /list       - show all rss->evennia mappings

    Example:
      @rss2chan rsschan = http://code.google.com/feeds/p/evennia/updates/basic

    This creates an RSS reader  that connects to a given RSS feed url. Updates will be
    echoed as a title and news link to the given channel. The rate of updating is set
    with the RSS_UPDATE_INTERVAL variable in settings (default is every 10 minutes).

    When disconnecting you need to supply both the channel and url again so as to identify
    the connection uniquely.
    """

    key = "@rss2chan"
    locks = "cmd:serversetting(RSS_ENABLED) and pperm(Immortals)"
    help_category = "Comms"

    def func(self):
        "Setup the rss-channel mapping"

        if not settings.RSS_ENABLED:
            string = """RSS is not enabled. You need to activate it in game/settings.py."""
            self.caller.msg(string)
            return

        if 'list' in self.switches:
            # show all connections
            connections = ExternalChannelConnection.objects.filter(db_external_key__startswith='rss_')
            if connections:
                cols = [["Evennia-channel"], ["RSS-url"]]
                for conn in connections:
                    cols[0].append(conn.channel.key)
                    cols[1].append(conn.external_config.split('|')[0])
                ftable = utils.format_table(cols)
                string = ""
                for ir, row in enumerate(ftable):
                    if ir == 0:
                        string += "{w%s{n" % "".join(row)
                    else:
                        string += "\n" + "".join(row)
                self.caller.msg(string)
            else:
                self.caller.msg("No connections found.")
            return

        if not self.args or not self.rhs:
            string = "Usage: @rss2chan[/switches] <evennia_channel> = <rss url>"
            self.caller.msg(string)
            return
        channel = self.lhs
        url = self.rhs

        if 'disconnect' in self.switches or 'remove' in self.switches or 'delete' in self.switches:
            chanmatch = find_channel(self.caller, channel, silent=True)
            if chanmatch:
                channel = chanmatch.key

            ok = rss.delete_connection(channel, url)
            if not ok:
                self.caller.msg("RSS connection/reader could not be removed, does it exist?")
            else:
                self.caller.msg("RSS connection destroyed.")
            return

        channel = find_channel(self.caller, channel)
        if not channel:
            return
        interval = settings.RSS_UPDATE_INTERVAL
        if not interval:
            interval = 10*60
        ok = rss.create_connection(channel, url, interval)
        if not ok:
            self.caller.msg("This RSS connection already exists.")
            return
        self.caller.msg("Connection created. Starting RSS reader.")
