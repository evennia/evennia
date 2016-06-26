"""
Comsystem command module.

Comm commands are OOC commands and intended to be made available to
the Player at all times (they go into the PlayerCmdSet). So we
make sure to homogenize self.caller to always be the player object
for easy handling.

"""
from past.builtins import cmp
from django.conf import settings
from evennia.comms.models import ChannelDB, Msg
#from evennia.comms import irc, imc2, rss
from evennia.players.models import PlayerDB
from evennia.players import bots
from evennia.comms.channelhandler import CHANNELHANDLER
from evennia.utils import create, utils, evtable
from evennia.utils.utils import make_iter, class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# limit symbol import for API
__all__ = ("CmdAddCom", "CmdDelCom", "CmdAllCom",
           "CmdChannels", "CmdCdestroy", "CmdCBoot", "CmdCemit",
           "CmdCWho", "CmdChannelCreate", "CmdClock", "CmdCdesc",
           "CmdPage", "CmdIRC2Chan", "CmdRSS2Chan")#, "CmdIMC2Chan", "CmdIMCInfo",
           #"CmdIMCTell")
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH


def find_channel(caller, channelname, silent=False, noaliases=False):
    """
    Helper function for searching for a single channel with
    some error handling.
    """
    channels = ChannelDB.objects.channel_search(channelname)
    if not channels:
        if not noaliases:
            channels = [chan for chan in ChannelDB.objects.get_all_channels()
                        if channelname in chan.aliases.all()]
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


class CmdAddCom(COMMAND_DEFAULT_CLASS):
    """
    add a channel alias and/or subscribe to a channel

    Usage:
       addcom [alias=] <channel>

    Joins a given channel. If alias is given, this will allow you to
    refer to the channel by this alias rather than the full channel
    name. Subsequent calls of this command can be used to add multiple
    aliases to an already joined channel.
    """

    key = "addcom"
    aliases = ["aliaschan", "chanalias"]
    help_category = "Comms"
    locks = "cmd:not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement the command"

        caller = self.caller
        args = self.args
        player = caller

        if not args:
            self.msg("Usage: addcom [alias =] channelname.")
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
            self.msg("%s: You are not allowed to listen to this channel." % channel.key)
            return

        string = ""
        if not channel.has_connection(player):
            # we want to connect as well.
            if not channel.connect(player):
                # if this would have returned True, the player is connected
                self.msg("%s: You are not allowed to join this channel." % channel.key)
                return
            else:
                string += "You now listen to the channel %s. " % channel.key
        else:
            string += "You are already connected to channel %s." % channel.key

        if alias:
            # create a nick and add it to the caller.
            caller.nicks.add(alias, channel.key, category="channel")
            string += " You can now refer to the channel %s with the alias '%s'."
            self.msg(string % (channel.key, alias))
        else:
            string += " No alias added."
            self.msg(string)


class CmdDelCom(COMMAND_DEFAULT_CLASS):
    """
    remove a channel alias and/or unsubscribe from channel

    Usage:
       delcom <alias or channel>

    If the full channel name is given, unsubscribe from the
    channel. If an alias is given, remove the alias but don't
    unsubscribe.
    """

    key = "delcom"
    aliases = ["delaliaschan", "delchanalias"]
    help_category = "Comms"
    locks = "cmd:not perm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implementing the command. "

        caller = self.caller
        player = caller

        if not self.args:
            self.msg("Usage: delcom <alias or channel>")
            return
        ostring = self.args.lower()

        channel = find_channel(caller, ostring, silent=True, noaliases=True)
        if channel:
            # we have given a channel name - unsubscribe
            if not channel.has_connection(player):
                self.msg("You are not listening to that channel.")
                return
            chkey = channel.key.lower()
            # find all nicks linked to this channel and delete them
            for nick in [nick for nick in make_iter(caller.nicks.get(category="channel", return_obj=True))
                         if nick and nick.value[3].lower() == chkey]:
                nick.delete()
            disconnect = channel.disconnect(player)
            if disconnect:
                self.msg("You stop listening to channel '%s'. Eventual aliases were removed." % channel.key)
            return
        else:
            # we are removing a channel nick
            channame = caller.nicks.get(key=ostring, category="channel")
            channel = find_channel(caller, channame, silent=True)
            if not channel:
                self.msg("No channel with alias '%s' was found." % ostring)
            else:
                if caller.nicks.get(ostring, category="channel"):
                    caller.nicks.remove(ostring, category="channel")
                    self.msg("Your alias '%s' for channel %s was cleared." % (ostring, channel.key))
                else:
                    self.msg("You had no such alias defined for this channel.")


class CmdAllCom(COMMAND_DEFAULT_CLASS):
    """
    perform admin operations on all channels

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

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Runs the function"

        caller = self.caller
        args = self.args
        if not args:
            caller.execute_cmd("@channels")
            self.msg("(Usage: allcom on | off | who | destroy)")
            return

        if args == "on":
            # get names of all channels available to listen to
            # and activate them all
            channels = [chan for chan in ChannelDB.objects.get_all_channels()
                        if chan.access(caller, 'listen')]
            for channel in channels:
                caller.execute_cmd("addcom %s" % channel.key)
        elif args == "off":
             #get names all subscribed channels and disconnect from them all
            channels = ChannelDB.objects.get_subscriptions(caller)
            for channel in channels:
                caller.execute_cmd("delcom %s" % channel.key)
        elif args == "destroy":
            # destroy all channels you control
            channels = [chan for chan in ChannelDB.objects.get_all_channels()
                        if chan.access(caller, 'control')]
            for channel in channels:
                caller.execute_cmd("@cdestroy %s" % channel.key)
        elif args == "who":
            # run a who, listing the subscribers on visible channels.
            string = "\n{CChannel subscriptions{n"
            channels = [chan for chan in ChannelDB.objects.get_all_channels()
                        if chan.access(caller, 'listen')]
            if not channels:
                string += "No channels."
            for channel in channels:
                string += "\n{w%s:{n\n" % channel.key
                subs = channel.db_subscriptions.all()
                if subs:
                    string += "  " + ", ".join([player.key for player in subs])
                else:
                    string += "  <None>"
            self.msg(string.strip())
        else:
            # wrong input
            self.msg("Usage: allcom on | off | who | clear")


class CmdChannels(COMMAND_DEFAULT_CLASS):
    """
    list all channels available to you

    Usage:
      @channels
      @clist
      comlist

    Lists all channels available to you, whether you listen to them or not.
    Use 'comlist' to only view your current channel subscriptions.
    Use addcom/delcom to join and leave channels
    """
    key = "@channels"
    aliases = ["@clist", "channels", "comlist", "chanlist", "channellist", "all channels"]
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement function"

        caller = self.caller

        # all channels we have available to listen to
        channels = [chan for chan in ChannelDB.objects.get_all_channels()
                    if chan.access(caller, 'listen')]
        if not channels:
            self.msg("No channels available.")
            return
        # all channel we are already subscribed to
        subs = ChannelDB.objects.get_subscriptions(caller)

        if self.cmdstring == "comlist":
            # just display the subscribed channels with no extra info
            comtable = evtable.EvTable("{wchannel{n", "{wmy aliases{n", "{wdescription{n", align="l", maxwidth=_DEFAULT_WIDTH)
            #comtable = prettytable.PrettyTable(["{wchannel", "{wmy aliases", "{wdescription"])
            for chan in subs:
                clower = chan.key.lower()
                nicks = caller.nicks.get(category="channel", return_obj=True)
                comtable.add_row(*["%s%s" % (chan.key, chan.aliases.all() and
                                  "(%s)" % ",".join(chan.aliases.all()) or ""),
                                  "%s" % ",".join(nick.db_key for nick in make_iter(nicks)
                                  if nick and nick.value[3].lower() == clower),
                                  chan.db.desc])
            caller.msg("\n{wChannel subscriptions{n (use {w@channels{n to list all, {waddcom{n/{wdelcom{n to sub/unsub):{n\n%s" % comtable)
        else:
            # full listing (of channels caller is able to listen to)
            comtable = evtable.EvTable("{wsub{n", "{wchannel{n", "{wmy aliases{n", "{wlocks{n", "{wdescription{n", maxwidth=_DEFAULT_WIDTH)
            #comtable = prettytable.PrettyTable(["{wsub", "{wchannel", "{wmy aliases", "{wlocks", "{wdescription"])
            for chan in channels:
                clower = chan.key.lower()
                nicks = caller.nicks.get(category="channel", return_obj=True)
                nicks = nicks or []
                comtable.add_row(*[chan in subs and "{gYes{n" or "{rNo{n",
                                  "%s%s" % (chan.key, chan.aliases.all() and
                                  "(%s)" % ",".join(chan.aliases.all()) or ""),
                                  "%s" % ",".join(nick.db_key for nick in make_iter(nicks)
                                  if nick.value[3].lower() == clower),
                                  str(chan.locks),
                                  chan.db.desc])
            caller.msg("\n{wAvailable channels{n (use {wcomlist{n,{waddcom{n and {wdelcom{n to manage subscriptions):\n%s" % comtable)


class CmdCdestroy(COMMAND_DEFAULT_CLASS):
    """
    destroy a channel you created

    Usage:
      @cdestroy <channel>

    Destroys a channel that you control.
    """

    key = "@cdestroy"
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Destroy objects cleanly."
        caller = self.caller

        if not self.args:
            self.msg("Usage: @cdestroy <channelname>")
            return
        channel = find_channel(caller, self.args)
        if not channel:
            self.msg("Could not find channel %s." % self.args)
            return
        if not channel.access(caller, 'control'):
            self.msg("You are not allowed to do that.")
            return
        channel_key = channel.key
        message = "%s is being destroyed. Make sure to change your aliases." % channel_key
        msgobj = create.create_message(caller, message, channel)
        channel.msg(msgobj)
        channel.delete()
        CHANNELHANDLER.update()
        self.msg("Channel '%s' was destroyed." % channel_key)


class CmdCBoot(COMMAND_DEFAULT_CLASS):
    """
    kick a player from a channel you control

    Usage:
       @cboot[/quiet] <channel> = <player> [:reason]

    Switches:
       quiet - don't notify the channel

    Kicks a player or object from a channel you control.

    """

    key = "@cboot"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "implement the function"

        if not self.args or not self.rhs:
            string = "Usage: @cboot[/quiet] <channel> = <player> [:reason]"
            self.msg(string)
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
            self.msg(string)
            return
        if not player in channel.db_subscriptions.all():
            string = "Player %s is not connected to channel %s." % (player.key, channel.key)
            self.msg(string)
            return
        if not "quiet" in self.switches:
            string = "%s boots %s from channel.%s" % (self.caller, player.key, reason)
            channel.msg(string)
        # find all player's nicks linked to this channel and delete them
        for nick in [nick for nick in
                     player.character.nicks.get(category="channel") or []
                     if nick.value[3].lower() == channel.key]:
            nick.delete()
        # disconnect player
        channel.disconnect(player)
        CHANNELHANDLER.update()


class CmdCemit(COMMAND_DEFAULT_CLASS):
    """
    send an admin message to a channel you control

    Usage:
      @cemit[/switches] <channel> = <message>

    Switches:
      sendername - attach the sender's name before the message
      quiet - don't echo the message back to sender

    Allows the user to broadcast a message over a channel as long as
    they control it. It does not show the user's name unless they
    provide the /sendername switch.

    """

    key = "@cemit"
    aliases = ["@cmsg"]
    locks = "cmd: not pperm(channel_banned) and pperm(Players)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement function"

        if not self.args or not self.rhs:
            string = "Usage: @cemit[/switches] <channel> = <message>"
            self.msg(string)
            return
        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return
        message = self.rhs
        if "sendername" in self.switches:
            message = "%s: %s" % (self.caller.key, message)
        channel.msg(message)
        if not "quiet" in self.switches:
            string = "Sent to channel %s: %s" % (channel.key, message)
            self.msg(string)


class CmdCWho(COMMAND_DEFAULT_CLASS):
    """
    show who is listening to a channel

    Usage:
      @cwho <channel>

    List who is connected to a given channel you have access to.
    """
    key = "@cwho"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "implement function"

        if not self.args:
            string = "Usage: @cwho <channel>"
            self.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "listen"):
            string = "You can't access this channel."
            self.msg(string)
            return
        string = "\n{CChannel subscriptions{n"
        string += "\n{w%s:{n\n" % channel.key
        subs = channel.db_subscriptions.all()
        if subs:
            string += "  " + ", ".join([player.key for player in subs])
        else:
            string += "  <None>"
        self.msg(string.strip())


class CmdChannelCreate(COMMAND_DEFAULT_CLASS):
    """
    create a new channel

    Usage:
     @ccreate <new channel>[;alias;alias...] = description

    Creates a new channel owned by you.
    """

    key = "@ccreate"
    aliases = "channelcreate"
    locks = "cmd:not pperm(channel_banned) and pperm(Players)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement the command"

        caller = self.caller

        if not self.args:
            self.msg("Usage @ccreate <channelname>[;alias;alias..] = description")
            return

        description = ""

        if self.rhs:
            description = self.rhs
        lhs = self.lhs
        channame = lhs
        aliases = None
        if ';' in lhs:
            channame, aliases = lhs.split(';', 1)
            aliases = [alias.strip().lower() for alias in aliases.split(';')]
        channel = ChannelDB.objects.channel_search(channame)
        if channel:
            self.msg("A channel with that name already exists.")
            return
        # Create and set the channel up
        lockstring = "send:all();listen:all();control:id(%s)" % caller.id
        new_chan = create.create_channel(channame.strip(),
                                         aliases,
                                         description,
                                         locks=lockstring)
        new_chan.connect(caller)
        CHANNELHANDLER.update()
        self.msg("Created channel %s and connected to it." % new_chan.key)


class CmdClock(COMMAND_DEFAULT_CLASS):
    """
    change channel locks of a channel you control

    Usage:
      @clock <channel> [= <lockstring>]

    Changes the lock access restrictions of a channel. If no
    lockstring was given, view the current lock definitions.
    """

    key = "@clock"
    locks = "cmd:not pperm(channel_banned)"
    aliases = ["@clock"]
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "run the function"

        if not self.args:
            string = "Usage: @clock channel [= lockstring]"
            self.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not self.rhs:
            # no =, so just view the current locks
            string = "Current locks on %s:" % channel.key
            string = "%s\n %s" % (string, channel.locks)
            self.msg(string)
            return
        # we want to add/change a lock.
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return
        # Try to add the lock
        channel.locks.add(self.rhs)
        string = "Lock(s) applied. "
        string += "Current locks on %s:" % channel.key
        string = "%s\n %s" % (string, channel.locks)
        self.msg(string)


class CmdCdesc(COMMAND_DEFAULT_CLASS):
    """
    describe a channel you control

    Usage:
      @cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists.
    """

    key = "@cdesc"
    locks = "cmd:not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement command"

        caller = self.caller

        if not self.rhs:
            self.msg("Usage: @cdesc <channel> = <description>")
            return
        channel = find_channel(caller, self.lhs)
        if not channel:
            self.msg("Channel '%s' not found." % self.lhs)
            return
        #check permissions
        if not channel.access(caller, 'control'):
            self.msg("You cannot admin this channel.")
            return
        # set the description
        channel.db.desc = self.rhs
        channel.save()
        self.msg("Description of channel '%s' set to '%s'." % (channel.key,
                                                               self.rhs))


class CmdPage(COMMAND_DEFAULT_CLASS):
    """
    send a private message to another player

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

    # this is used by the COMMAND_DEFAULT_CLASS parent
    player_caller = True

    def func(self):
        "Implement function using the Msg methods"

        # Since player_caller is set above, this will be a Player.
        caller = self.caller

        # get the messages we've sent (not to channels)
        pages_we_sent = Msg.objects.get_messages_by_sender(caller,
                                                 exclude_channel_messages=True)
        # get last messages we've got
        pages_we_got = Msg.objects.get_messages_by_receiver(caller)

        if 'last' in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[-1].receivers)
                self.msg("You last paged {c%s{n:%s" % (recv,
                                                    pages_we_sent[-1].message))
                return
            else:
                self.msg("You haven't paged anyone yet.")
                return

        if not self.args or not self.rhs:
            pages = pages_we_sent + pages_we_got
            pages.sort(lambda x, y: cmp(x.date_sent, y.date_sent))

            number = 5
            if self.args:
                try:
                    number = int(self.args)
                except ValueError:
                    self.msg("Usage: tell [<player> = msg]")
                    return

            if len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages
            template = "{w%s{n {c%s{n to {c%s{n: %s"
            lastpages = "\n ".join(template %
                                   (utils.datetime_format(page.date_sent),
                                    ",".join(obj.key for obj in page.senders),
                                    "{n,{c ".join([obj.name for obj in page.receivers]),
                                    page.message) for page in lastpages)

            if lastpages:
                string = "Your latest pages:\n %s" % lastpages
            else:
                string = "You haven't paged anyone yet."
            self.msg(string)
            return

        # We are sending. Build a list of targets

        if not self.lhs:
            # If there are no targets, then set the targets
            # to the last person we paged.
            if pages_we_sent:
                receivers = pages_we_sent[-1].receivers
            else:
                self.msg("Who do you want to page?")
                return
        else:
            receivers = self.lhslist

        recobjs = []
        for receiver in set(receivers):
            if isinstance(receiver, basestring):
                pobj = caller.search(receiver)
            elif hasattr(receiver, 'character'):
                pobj = receiver
            else:
                self.msg("Who do you want to page?")
                return
            if pobj:
                recobjs.append(pobj)
        if not recobjs:
            self.msg("Noone found to page.")
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
            if hasattr(pobj, 'sessions') and not pobj.sessions.count():
                received.append("{C%s{n" % pobj.name)
                rstrings.append("%s is offline. They will see your message if they list their pages later." % received[-1])
            else:
                received.append("{c%s{n" % pobj.name)
        if rstrings:
            self.msg("\n".join(rstrings))
        self.msg("You paged %s with: '%s'." % (", ".join(received), message))


class CmdIRC2Chan(COMMAND_DEFAULT_CLASS):
    """
    link an evennia channel to an external IRC channel

    Usage:
      @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>
      @irc2chan/delete botname|#dbid

    Switches:
      /delete     - this will delete the bot and remove the irc connection
                    to the channel. Requires the botname or #dbid as input.
      /remove     - alias to /delete
      /disconnect - alias to /delete
      /list       - show all irc<->evennia mappings
      /ssl        - use an SSL-encrypted connection

    Example:
      @irc2chan myircchan = irc.dalnet.net 6667 myevennia-channel evennia-bot

    This creates an IRC bot that connects to a given IRC network and channel.
    It will relay everything said in the evennia channel to the IRC channel and
    vice versa. The bot will automatically connect at server start, so this
    comman need only be given once. The /disconnect switch will permanently
    delete the bot. To only temporarily deactivate it, use the  {w@services{n
    command instead.
    """

    key = "@irc2chan"
    locks = "cmd:serversetting(IRC_ENABLED) and pperm(Immortals)"
    help_category = "Comms"

    def func(self):
        "Setup the irc-channel mapping"

        if not settings.IRC_ENABLED:
            string = """IRC is not enabled. You need to activate it in game/settings.py."""
            self.msg(string)
            return

        if 'list' in self.switches:
            # show all connections
            ircbots = [bot for bot in PlayerDB.objects.filter(db_is_bot=True, username__startswith="ircbot-")]
            if ircbots:
                from evennia.utils.evtable import EvTable
                table = EvTable("{wdbid{n", "{wbotname{n", "{wev-channel{n", "{wirc-channel{n", "{wSSL{n", maxwidth=_DEFAULT_WIDTH)
                for ircbot in ircbots:
                    ircinfo = "%s (%s:%s)" % (ircbot.db.irc_channel, ircbot.db.irc_network, ircbot.db.irc_port)
                    table.add_row(ircbot.id, ircbot.db.irc_botname, ircbot.db.ev_channel, ircinfo, ircbot.db.irc_ssl)
                self.caller.msg(table)
            else:
                self.msg("No irc bots found.")
            return


        if('disconnect' in self.switches or 'remove' in self.switches or
                                                    'delete' in self.switches):
            botname = "ircbot-%s" % self.lhs
            matches = PlayerDB.objects.filter(db_is_bot=True, username=botname)
            dbref = utils.dbref(self.lhs)
            if not matches and dbref:
                # try dbref match
                matches = PlayerDB.objects.filter(db_is_bot=True, id=dbref)
            if matches:
                matches[0].delete()
                self.msg("IRC connection destroyed.")
            else:
                self.msg("IRC connection/bot could not be removed, does it exist?")
            return

        if not self.args or not self.rhs:
            string = "Usage: @irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>"
            self.msg(string)
            return

        channel = self.lhs
        self.rhs = self.rhs.replace('#', ' ') # to avoid Python comment issues
        try:
            irc_network, irc_port, irc_channel, irc_botname = \
                       [part.strip() for part in self.rhs.split(None, 3)]
            irc_channel = "#%s" % irc_channel
        except Exception:
            string = "IRC bot definition '%s' is not valid." % self.rhs
            self.msg(string)
            return

        botname = "ircbot-%s" % irc_botname
        irc_ssl = "ssl" in self.switches

        # create a new bot
        bot = PlayerDB.objects.filter(username__iexact=botname)
        if bot:
            # re-use an existing bot
            bot = bot[0]
            if not bot.is_bot:
                self.msg("Player '%s' already exists and is not a bot." % botname)
                return
        else:
            bot = create.create_player(botname, None, None, typeclass=bots.IRCBot)
        bot.start(ev_channel=channel, irc_botname=irc_botname, irc_channel=irc_channel,
                  irc_network=irc_network, irc_port=irc_port, irc_ssl=irc_ssl)
        self.msg("Connection created. Starting IRC bot.")

# RSS connection
class CmdRSS2Chan(COMMAND_DEFAULT_CLASS):
    """
    link an evennia channel to an external RSS feed

    Usage:
      @rss2chan[/switches] <evennia_channel> = <rss_url>

    Switches:
      /disconnect - this will stop the feed and remove the connection to the
                    channel.
      /remove     -                                 "
      /list       - show all rss->evennia mappings

    Example:
      @rss2chan rsschan = http://code.google.com/feeds/p/evennia/updates/basic

    This creates an RSS reader  that connects to a given RSS feed url. Updates
    will be echoed as a title and news link to the given channel. The rate of
    updating is set with the RSS_UPDATE_INTERVAL variable in settings (default
    is every 10 minutes).

    When disconnecting you need to supply both the channel and url again so as
    to identify the connection uniquely.
    """

    key = "@rss2chan"
    locks = "cmd:serversetting(RSS_ENABLED) and pperm(Immortals)"
    help_category = "Comms"

    def func(self):
        "Setup the rss-channel mapping"

        # checking we have all we need
        if not settings.RSS_ENABLED:
            string = """RSS is not enabled. You need to activate it in game/settings.py."""
            self.msg(string)
            return
        try:
            import feedparser
            feedparser   # to avoid checker error of not being used
        except ImportError:
            string = ("RSS requires python-feedparser (https://pypi.python.org/pypi/feedparser). "
                      "Install before continuing.")
            self.msg(string)
            return

        if 'list' in self.switches:
            # show all connections
            rssbots = [bot for bot in PlayerDB.objects.filter(db_is_bot=True, username__startswith="rssbot-")]
            if rssbots:
                from evennia.utils.evtable import EvTable
                table = EvTable("{wdbid{n", "{wupdate rate{n", "{wev-channel",
                                "{wRSS feed URL{n", border="cells", maxwidth=_DEFAULT_WIDTH)
                for rssbot in rssbots:
                    table.add_row(rssbot.id, rssbot.db.rss_rate, rssbot.db.ev_channel, rssbot.db.rss_url)
                self.caller.msg(table)
            else:
                self.msg("No rss bots found.")
            return

        if('disconnect' in self.switches or 'remove' in self.switches or
                                                    'delete' in self.switches):
            botname = "rssbot-%s" % self.lhs
            matches = PlayerDB.objects.filter(db_is_bot=True, db_key=botname)
            if not matches:
                # try dbref match
                matches = PlayerDB.objects.filter(db_is_bot=True, id=self.args.lstrip("#"))
            if matches:
                matches[0].delete()
                self.msg("RSS connection destroyed.")
            else:
                self.msg("RSS connection/bot could not be removed, does it exist?")
            return

        if not self.args or not self.rhs:
            string = "Usage: @rss2chan[/switches] <evennia_channel> = <rss url>"
            self.msg(string)
            return
        channel = self.lhs
        url = self.rhs

        botname = "rssbot-%s" % url
        # create a new bot
        bot = PlayerDB.objects.filter(username__iexact=botname)
        if bot:
            # re-use existing bot
            bot = bot[0]
            if not bot.is_bot:
                self.msg("Player '%s' already exists and is not a bot." % botname)
                return
        else:
            bot = create.create_player(botname, None, None, typeclass=bots.RSSBot)
        bot.start(ev_channel=channel, rss_url=url, rss_rate=10)
        self.msg("RSS reporter created. Fetching RSS.")


#class CmdIMC2Chan(COMMAND_DEFAULT_CLASS):
#    """
#    link an evennia channel to an external IMC2 channel
#
#    Usage:
#      @imc2chan[/switches] <evennia_channel> = <imc2_channel>
#
#    Switches:
#      /disconnect - this clear the imc2 connection to the channel.
#      /remove     -                "
#      /list       - show all imc2<->evennia mappings
#
#    Example:
#      @imc2chan myimcchan = ievennia
#
#    Connect an existing evennia channel to a channel on an IMC2
#    network. The network contact information is defined in settings and
#    should already be accessed at this point. Use @imcchanlist to see
#    available IMC channels.
#
#    """
#
#    key = "@imc2chan"
#    locks = "cmd:serversetting(IMC2_ENABLED) and pperm(Immortals)"
#    help_category = "Comms"
#
#    def func(self):
#        "Setup the imc-channel mapping"
#
#        if not settings.IMC2_ENABLED:
#            string = """IMC is not enabled. You need to activate it in game/settings.py."""
#            self.msg(string)
#            return
#
#        if 'list' in self.switches:
#            # show all connections
#            connections = ExternalChannelConnection.objects.filter(db_external_key__startswith='imc2_')
#            if connections:
#                table = prettytable.PrettyTable(["Evennia channel", "IMC channel"])
#                for conn in connections:
#                    table.add_row([conn.channel.key, conn.external_config])
#                string = "{wIMC connections:{n\n%s" % table
#                self.msg(string)
#            else:
#                self.msg("No connections found.")
#            return
#
#        if not self.args or not self.rhs:
#            string = "Usage: @imc2chan[/switches] <evennia_channel> = <imc2_channel>"
#            self.msg(string)
#            return
#
#        channel = self.lhs
#        imc2_channel = self.rhs
#
#        if('disconnect' in self.switches or 'remove' in self.switches or
#                                                    'delete' in self.switches):
#            # we don't search for channels before this since we want
#            # to clear the link also if the channel no longer exists.
#            ok = imc2.delete_connection(channel, imc2_channel)
#            if not ok:
#                self.msg("IMC2 connection could not be removed, does it exist?")
#            else:
#                self.msg("IMC2 connection destroyed.")
#            return
#
#        # actually get the channel object
#        channel = find_channel(self.caller, channel)
#        if not channel:
#            return
#
#        ok = imc2.create_connection(channel, imc2_channel)
#        if not ok:
#            self.msg("The connection %s <-> %s  already exists." % (channel.key, imc2_channel))
#            return
#        self.msg("Created connection channel %s <-> IMC channel %s." % (channel.key, imc2_channel))
#
#
#class CmdIMCInfo(COMMAND_DEFAULT_CLASS):
#    """
#    get various IMC2 information
#
#    Usage:
#      @imcinfo[/switches]
#      @imcchanlist - list imc2 channels
#      @imclist -     list connected muds
#      @imcwhois <playername> - whois info about a remote player
#
#    Switches for @imcinfo:
#      channels - as @imcchanlist (default)
#      games or muds - as @imclist
#      whois - as @imcwhois (requires an additional argument)
#      update - force an update of all lists
#
#    Shows lists of games or channels on the IMC2 network.
#    """
#
#    key = "@imcinfo"
#    aliases = ["@imcchanlist", "@imclist", "@imcwhois"]
#    locks = "cmd: serversetting(IMC2_ENABLED) and pperm(Wizards)"
#    help_category = "Comms"
#
#    def func(self):
#        "Run the command"
#
#        if not settings.IMC2_ENABLED:
#            string = """IMC is not enabled. You need to activate it in game/settings.py."""
#            self.msg(string)
#            return
#
#        if "update" in self.switches:
#            # update the lists
#            import time
#            from evennia.comms.imc2lib import imc2_packets as pck
#            from evennia.comms.imc2 import IMC2_MUDLIST, IMC2_CHANLIST, IMC2_CLIENT
#            # update connected muds
#            IMC2_CLIENT.send_packet(pck.IMC2PacketKeepAliveRequest())
#            # prune inactive muds
#            for name, mudinfo in IMC2_MUDLIST.mud_list.items():
#                if time.time() - mudinfo.last_updated > 3599:
#                    del IMC2_MUDLIST.mud_list[name]
#            # update channel list
#            IMC2_CLIENT.send_packet(pck.IMC2PacketIceRefresh())
#            self.msg("IMC2 lists were re-synced.")
#
#        elif("games" in self.switches or "muds" in self.switches
#                                            or self.cmdstring == "@imclist"):
#            # list muds
#            from evennia.comms.imc2 import IMC2_MUDLIST
#
#            muds = IMC2_MUDLIST.get_mud_list()
#            networks = set(mud.networkname for mud in muds)
#            string = ""
#            nmuds = 0
#            for network in networks:
#                table = prettytable.PrettyTable(["Name", "Url", "Host", "Port"])
#                for mud in (mud for mud in muds if mud.networkname == network):
#                    nmuds += 1
#                    table.add_row([mud.name, mud.url, mud.host, mud.port])
#                string += "\n{wMuds registered on %s:{n\n%s" % (network, table)
#            string += "\n %i Muds found." % nmuds
#            self.msg(string)
#
#        elif "whois" in self.switches or self.cmdstring == "@imcwhois":
#            # find out about a player
#            if not self.args:
#                self.msg("Usage: @imcwhois <playername>")
#                return
#            from evennia.comms.imc2 import IMC2_CLIENT
#            self.msg("Sending IMC whois request. If you receive no response, no matches were found.")
#            IMC2_CLIENT.msg_imc2(None,
#                                 from_obj=self.caller,
#                                 packet_type="imcwhois",
#                                 target=self.args)
#
#        elif(not self.switches or "channels" in self.switches or
#                                              self.cmdstring == "@imcchanlist"):
#            # show channels
#            from evennia.comms.imc2 import IMC2_CHANLIST, IMC2_CLIENT
#
#            channels = IMC2_CHANLIST.get_channel_list()
#            string = ""
#            nchans = 0
#            table = prettytable.PrettyTable(["Full name", "Name", "Owner", "Perm", "Policy"])
#            for chan in channels:
#                nchans += 1
#                table.add_row([chan.name, chan.localname, chan.owner,
#                               chan.level, chan.policy])
#            string += "\n{wChannels on %s:{n\n%s" % (IMC2_CLIENT.factory.network, table)
#            string += "\n%i Channels found." % nchans
#            self.msg(string)
#        else:
#            # no valid inputs
#            string = "Usage: imcinfo|imcchanlist|imclist"
#            self.msg(string)
#
#
## unclear if this is working ...
#class CmdIMCTell(COMMAND_DEFAULT_CLASS):
#    """
#    send a page to a remote IMC player
#
#    Usage:
#      imctell User@MUD = <msg>
#      imcpage      "
#
#    Sends a page to a user on a remote MUD, connected
#    over IMC2.
#    """
#
#    key = "imctell"
#    aliases = ["imcpage", "imc2tell", "imc2page"]
#    locks = "cmd: serversetting(IMC2_ENABLED)"
#    help_category = "Comms"
#
#    def func(self):
#        "Send tell across IMC"
#
#        if not settings.IMC2_ENABLED:
#            string = """IMC is not enabled. You need to activate it in game/settings.py."""
#            self.msg(string)
#            return
#
#        from evennia.comms.imc2 import IMC2_CLIENT
#
#        if not self.args or not '@' in self.lhs or not self.rhs:
#            string = "Usage: imctell User@Mud = <msg>"
#            self.msg(string)
#            return
#        target, destination = self.lhs.split("@", 1)
#        message = self.rhs.strip()
#        data = {"target":target, "destination":destination}
#
#        # send to imc2
#        IMC2_CLIENT.msg_imc2(message, from_obj=self.caller, packet_type="imctell", **data)
#
#        self.msg("You paged {c%s@%s{n (over IMC): '%s'." % (target, destination, message))
#
#
