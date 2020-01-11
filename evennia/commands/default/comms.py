"""
Comsystem command module.

Comm commands are OOC commands and intended to be made available to
the Account at all times (they go into the AccountCmdSet). So we
make sure to homogenize self.caller to always be the account object
for easy handling.

"""
import hashlib
import time
from django.conf import settings
from evennia.comms.models import ChannelDB, Msg
from evennia.accounts.models import AccountDB
from evennia.accounts import bots
from evennia.comms.channelhandler import CHANNELHANDLER
from evennia.locks.lockhandler import LockException
from evennia.utils import create, logger, utils, evtable
from evennia.utils.utils import make_iter, class_from_module

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
CHANNEL_DEFAULT_TYPECLASS = class_from_module(settings.BASE_CHANNEL_TYPECLASS)


# limit symbol import for API
__all__ = (
    "CmdAddCom",
    "CmdDelCom",
    "CmdAllCom",
    "CmdChannels",
    "CmdCdestroy",
    "CmdCBoot",
    "CmdCemit",
    "CmdCWho",
    "CmdChannelCreate",
    "CmdClock",
    "CmdCdesc",
    "CmdPage",
    "CmdIRC2Chan",
    "CmdRSS2Chan",
)
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH


def find_channel(caller, channelname, silent=False, noaliases=False):
    """
    Helper function for searching for a single channel with
    some error handling.
    """
    channels = CHANNEL_DEFAULT_TYPECLASS.objects.channel_search(channelname)
    if not channels:
        if not noaliases:
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if channelname in chan.aliases.all()
            ]
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
    account_caller = True

    def func(self):
        """Implement the command"""

        caller = self.caller
        args = self.args
        account = caller

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
        if not channel.access(account, "listen"):
            self.msg("%s: You are not allowed to listen to this channel." % channel.key)
            return

        string = ""
        if not channel.has_connection(account):
            # we want to connect as well.
            if not channel.connect(account):
                # if this would have returned True, the account is connected
                self.msg("%s: You are not allowed to join this channel." % channel.key)
                return
            else:
                string += "You now listen to the channel %s. " % channel.key
        else:
            if channel.unmute(account):
                string += "You unmute channel %s." % channel.key
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
       delcom/all <channel>

    If the full channel name is given, unsubscribe from the
    channel. If an alias is given, remove the alias but don't
    unsubscribe. If the 'all' switch is used, remove all aliases
    for that channel.
    """

    key = "delcom"
    aliases = ["delaliaschan", "delchanalias"]
    help_category = "Comms"
    locks = "cmd:not perm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implementing the command. """

        caller = self.caller
        account = caller

        if not self.args:
            self.msg("Usage: delcom <alias or channel>")
            return
        ostring = self.args.lower()

        channel = find_channel(caller, ostring, silent=True, noaliases=True)
        if channel:
            # we have given a channel name - unsubscribe
            if not channel.has_connection(account):
                self.msg("You are not listening to that channel.")
                return
            chkey = channel.key.lower()
            delnicks = "all" in self.switches
            # find all nicks linked to this channel and delete them
            if delnicks:
                for nick in [
                    nick
                    for nick in make_iter(caller.nicks.get(category="channel", return_obj=True))
                    if nick and nick.pk and nick.value[3].lower() == chkey
                ]:
                    nick.delete()
            disconnect = channel.disconnect(account)
            if disconnect:
                wipednicks = " Eventual aliases were removed." if delnicks else ""
                self.msg("You stop listening to channel '%s'.%s" % (channel.key, wipednicks))
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

    Allows the user to universally turn off or on all channels they are on, as
    well as perform a 'who' for all channels they are on. Destroy deletes all
    channels that you control.

    Without argument, works like comlist.
    """

    key = "allcom"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Runs the function"""

        caller = self.caller
        args = self.args
        if not args:
            self.execute_cmd("channels")
            self.msg("(Usage: allcom on | off | who | destroy)")
            return

        if args == "on":
            # get names of all channels available to listen to
            # and activate them all
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "listen")
            ]
            for channel in channels:
                self.execute_cmd("addcom %s" % channel.key)
        elif args == "off":
            # get names all subscribed channels and disconnect from them all
            channels = CHANNEL_DEFAULT_TYPECLASS.objects.get_subscriptions(caller)
            for channel in channels:
                self.execute_cmd("delcom %s" % channel.key)
        elif args == "destroy":
            # destroy all channels you control
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "control")
            ]
            for channel in channels:
                self.execute_cmd("cdestroy %s" % channel.key)
        elif args == "who":
            # run a who, listing the subscribers on visible channels.
            string = "\n|CChannel subscriptions|n"
            channels = [
                chan
                for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
                if chan.access(caller, "listen")
            ]
            if not channels:
                string += "No channels."
            for channel in channels:
                string += "\n|w%s:|n\n %s" % (channel.key, channel.wholist)
            self.msg(string.strip())
        else:
            # wrong input
            self.msg("Usage: allcom on | off | who | clear")


class CmdChannels(COMMAND_DEFAULT_CLASS):
    """
    list all channels available to you

    Usage:
      channels
      clist
      comlist

    Lists all channels available to you, whether you listen to them or not.
    Use 'comlist' to only view your current channel subscriptions.
    Use addcom/delcom to join and leave channels
    """

    key = "channels"
    aliases = ["clist", "comlist", "chanlist", "channellist", "all channels"]
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement function"""

        caller = self.caller

        # all channels we have available to listen to
        channels = [
            chan
            for chan in CHANNEL_DEFAULT_TYPECLASS.objects.get_all_channels()
            if chan.access(caller, "listen")
        ]
        if not channels:
            self.msg("No channels available.")
            return
        # all channel we are already subscribed to
        subs = CHANNEL_DEFAULT_TYPECLASS.objects.get_subscriptions(caller)

        if self.cmdstring == "comlist":
            # just display the subscribed channels with no extra info
            comtable = self.styled_table(
                "|wchannel|n",
                "|wmy aliases|n",
                "|wdescription|n",
                align="l",
                maxwidth=_DEFAULT_WIDTH,
            )
            for chan in subs:
                clower = chan.key.lower()
                nicks = caller.nicks.get(category="channel", return_obj=True)
                comtable.add_row(
                    *[
                        "%s%s"
                        % (
                            chan.key,
                            chan.aliases.all() and "(%s)" % ",".join(chan.aliases.all()) or "",
                        ),
                        "%s"
                        % ",".join(
                            nick.db_key
                            for nick in make_iter(nicks)
                            if nick and nick.value[3].lower() == clower
                        ),
                        chan.db.desc,
                    ]
                )
            self.msg(
                "\n|wChannel subscriptions|n (use |wchannels|n to list all,"
                " |waddcom|n/|wdelcom|n to sub/unsub):|n\n%s" % comtable
            )
        else:
            # full listing (of channels caller is able to listen to)
            comtable = self.styled_table(
                "|wsub|n",
                "|wchannel|n",
                "|wmy aliases|n",
                "|wlocks|n",
                "|wdescription|n",
                maxwidth=_DEFAULT_WIDTH,
            )
            for chan in channels:
                clower = chan.key.lower()
                nicks = caller.nicks.get(category="channel", return_obj=True)
                nicks = nicks or []
                if chan not in subs:
                    substatus = "|rNo|n"
                elif caller in chan.mutelist:
                    substatus = "|rMuted|n"
                else:
                    substatus = "|gYes|n"
                comtable.add_row(
                    *[
                        substatus,
                        "%s%s"
                        % (
                            chan.key,
                            chan.aliases.all() and "(%s)" % ",".join(chan.aliases.all()) or "",
                        ),
                        "%s"
                        % ",".join(
                            nick.db_key
                            for nick in make_iter(nicks)
                            if nick.value[3].lower() == clower
                        ),
                        str(chan.locks),
                        chan.db.desc,
                    ]
                )
            comtable.reformat_column(0, width=9)
            comtable.reformat_column(3, width=14)
            self.msg(
                "\n|wAvailable channels|n (use |wcomlist|n,|waddcom|n and |wdelcom|n"
                " to manage subscriptions):\n%s" % comtable
            )


class CmdCdestroy(COMMAND_DEFAULT_CLASS):
    """
    destroy a channel you created

    Usage:
      cdestroy <channel>

    Destroys a channel that you control.
    """

    key = "cdestroy"
    help_category = "Comms"
    locks = "cmd: not pperm(channel_banned)"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Destroy objects cleanly."""
        caller = self.caller

        if not self.args:
            self.msg("Usage: cdestroy <channelname>")
            return
        channel = find_channel(caller, self.args)
        if not channel:
            self.msg("Could not find channel %s." % self.args)
            return
        if not channel.access(caller, "control"):
            self.msg("You are not allowed to do that.")
            return
        channel_key = channel.key
        message = "%s is being destroyed. Make sure to change your aliases." % channel_key
        msgobj = create.create_message(caller, message, channel)
        channel.msg(msgobj)
        channel.delete()
        CHANNELHANDLER.update()
        self.msg("Channel '%s' was destroyed." % channel_key)
        logger.log_sec(
            "Channel Deleted: %s (Caller: %s, IP: %s)."
            % (channel_key, caller, self.session.address)
        )


class CmdCBoot(COMMAND_DEFAULT_CLASS):
    """
    kick an account from a channel you control

    Usage:
       cboot[/quiet] <channel> = <account> [:reason]

    Switch:
       quiet - don't notify the channel

    Kicks an account or object from a channel you control.

    """

    key = "cboot"
    switch_options = ("quiet",)
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """implement the function"""

        if not self.args or not self.rhs:
            string = "Usage: cboot[/quiet] <channel> = <account> [:reason]"
            self.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        reason = ""
        if ":" in self.rhs:
            accountname, reason = self.rhs.rsplit(":", 1)
            searchstring = accountname.lstrip("*")
        else:
            searchstring = self.rhs.lstrip("*")
        account = self.caller.search(searchstring, account=True)
        if not account:
            return
        if reason:
            reason = " (reason: %s)" % reason
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return
        if not channel.subscriptions.has(account):
            string = "Account %s is not connected to channel %s." % (account.key, channel.key)
            self.msg(string)
            return
        if "quiet" not in self.switches:
            string = "%s boots %s from channel.%s" % (self.caller, account.key, reason)
            channel.msg(string)
        # find all account's nicks linked to this channel and delete them
        for nick in [
            nick
            for nick in account.character.nicks.get(category="channel") or []
            if nick.value[3].lower() == channel.key
        ]:
            nick.delete()
        # disconnect account
        channel.disconnect(account)
        CHANNELHANDLER.update()
        logger.log_sec(
            "Channel Boot: %s (Channel: %s, Reason: %s, Caller: %s, IP: %s)."
            % (account, channel, reason, self.caller, self.session.address)
        )


class CmdCemit(COMMAND_DEFAULT_CLASS):
    """
    send an admin message to a channel you control

    Usage:
      cemit[/switches] <channel> = <message>

    Switches:
      sendername - attach the sender's name before the message
      quiet - don't echo the message back to sender

    Allows the user to broadcast a message over a channel as long as
    they control it. It does not show the user's name unless they
    provide the /sendername switch.

    """

    key = "cemit"
    aliases = ["cmsg"]
    switch_options = ("sendername", "quiet")
    locks = "cmd: not pperm(channel_banned) and pperm(Player)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement function"""

        if not self.args or not self.rhs:
            string = "Usage: cemit[/switches] <channel> = <message>"
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
        if "quiet" not in self.switches:
            string = "Sent to channel %s: %s" % (channel.key, message)
            self.msg(string)


class CmdCWho(COMMAND_DEFAULT_CLASS):
    """
    show who is listening to a channel

    Usage:
      cwho <channel>

    List who is connected to a given channel you have access to.
    """

    key = "cwho"
    locks = "cmd: not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """implement function"""

        if not self.args:
            string = "Usage: cwho <channel>"
            self.msg(string)
            return

        channel = find_channel(self.caller, self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "listen"):
            string = "You can't access this channel."
            self.msg(string)
            return
        string = "\n|CChannel subscriptions|n"
        string += "\n|w%s:|n\n  %s" % (channel.key, channel.wholist)
        self.msg(string.strip())


class CmdChannelCreate(COMMAND_DEFAULT_CLASS):
    """
    create a new channel

    Usage:
     ccreate <new channel>[;alias;alias...] = description

    Creates a new channel owned by you.
    """

    key = "ccreate"
    aliases = "channelcreate"
    locks = "cmd:not pperm(channel_banned) and pperm(Player)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement the command"""

        caller = self.caller

        if not self.args:
            self.msg("Usage ccreate <channelname>[;alias;alias..] = description")
            return

        description = ""

        if self.rhs:
            description = self.rhs
        lhs = self.lhs
        channame = lhs
        aliases = None
        if ";" in lhs:
            channame, aliases = lhs.split(";", 1)
            aliases = [alias.strip().lower() for alias in aliases.split(";")]
        channel = CHANNEL_DEFAULT_TYPECLASS.objects.channel_search(channame)
        if channel:
            self.msg("A channel with that name already exists.")
            return
        # Create and set the channel up
        lockstring = "send:all();listen:all();control:id(%s)" % caller.id
        new_chan = create.create_channel(channame.strip(), aliases, description, locks=lockstring)
        new_chan.connect(caller)
        CHANNELHANDLER.update()
        self.msg("Created channel %s and connected to it." % new_chan.key)


class CmdClock(COMMAND_DEFAULT_CLASS):
    """
    change channel locks of a channel you control

    Usage:
      clock <channel> [= <lockstring>]

    Changes the lock access restrictions of a channel. If no
    lockstring was given, view the current lock definitions.
    """

    key = "clock"
    locks = "cmd:not pperm(channel_banned)"
    aliases = ["clock"]
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """run the function"""

        if not self.args:
            string = "Usage: clock channel [= lockstring]"
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
        try:
            channel.locks.add(self.rhs)
        except LockException as err:
            self.msg(err)
            return
        string = "Lock(s) applied. "
        string += "Current locks on %s:" % channel.key
        string = "%s\n %s" % (string, channel.locks)
        self.msg(string)


class CmdCdesc(COMMAND_DEFAULT_CLASS):
    """
    describe a channel you control

    Usage:
      cdesc <channel> = <description>

    Changes the description of the channel as shown in
    channel lists.
    """

    key = "cdesc"
    locks = "cmd:not pperm(channel_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement command"""

        caller = self.caller

        if not self.rhs:
            self.msg("Usage: cdesc <channel> = <description>")
            return
        channel = find_channel(caller, self.lhs)
        if not channel:
            self.msg("Channel '%s' not found." % self.lhs)
            return
        # check permissions
        if not channel.access(caller, "control"):
            self.msg("You cannot admin this channel.")
            return
        # set the description
        channel.db.desc = self.rhs
        channel.save()
        self.msg("Description of channel '%s' set to '%s'." % (channel.key, self.rhs))


class CmdPage(COMMAND_DEFAULT_CLASS):
    """
    send a private message to another account

    Usage:
      page[/switches] [<account>,<account>,... = <message>]
      tell        ''
      page <number>

    Switch:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no
    argument is given, you will get a list of your latest messages.
    """

    key = "page"
    aliases = ["tell"]
    switch_options = ("last", "list")
    locks = "cmd:not pperm(page_banned)"
    help_category = "Comms"

    # this is used by the COMMAND_DEFAULT_CLASS parent
    account_caller = True

    def func(self):
        """Implement function using the Msg methods"""

        # Since account_caller is set above, this will be an Account.
        caller = self.caller

        # get the messages we've sent (not to channels)
        pages_we_sent = Msg.objects.get_messages_by_sender(caller, exclude_channel_messages=True)
        # get last messages we've got
        pages_we_got = Msg.objects.get_messages_by_receiver(caller)

        if "last" in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[-1].receivers)
                self.msg("You last paged |c%s|n:%s" % (recv, pages_we_sent[-1].message))
                return
            else:
                self.msg("You haven't paged anyone yet.")
                return

        if not self.args or not self.rhs:
            pages = pages_we_sent + pages_we_got
            pages = sorted(pages, key=lambda page: page.date_created)

            number = 5
            if self.args:
                try:
                    number = int(self.args)
                except ValueError:
                    self.msg("Usage: tell [<account> = msg]")
                    return

            if len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages
            template = "|w%s|n |c%s|n to |c%s|n: %s"
            lastpages = "\n ".join(
                template
                % (
                    utils.datetime_format(page.date_created),
                    ",".join(obj.key for obj in page.senders),
                    "|n,|c ".join([obj.name for obj in page.receivers]),
                    page.message,
                )
                for page in lastpages
            )

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
            if isinstance(receiver, str):
                pobj = caller.search(receiver)
            elif hasattr(receiver, "character"):
                pobj = receiver
            else:
                self.msg("Who do you want to page?")
                return
            if pobj:
                recobjs.append(pobj)
        if not recobjs:
            self.msg("Noone found to page.")
            return

        header = "|wAccount|n |c%s|n |wpages:|n" % caller.key
        message = self.rhs

        # if message begins with a :, we assume it is a 'page-pose'
        if message.startswith(":"):
            message = "%s %s" % (caller.key, message.strip(":").strip())

        # create the persistent message object
        create.create_message(caller, message, receivers=recobjs)

        # tell the accounts they got a message.
        received = []
        rstrings = []
        for pobj in recobjs:
            if not pobj.access(caller, "msg"):
                rstrings.append("You are not allowed to page %s." % pobj)
                continue
            pobj.msg("%s %s" % (header, message))
            if hasattr(pobj, "sessions") and not pobj.sessions.count():
                received.append("|C%s|n" % pobj.name)
                rstrings.append(
                    "%s is offline. They will see your message if they list their pages later."
                    % received[-1]
                )
            else:
                received.append("|c%s|n" % pobj.name)
        if rstrings:
            self.msg("\n".join(rstrings))
        self.msg("You paged %s with: '%s'." % (", ".join(received), message))


def _list_bots(cmd):
    """
    Helper function to produce a list of all IRC bots.

    Args:
        cmd (Command): Instance of the Bot command.
    Returns:
        bots (str): A table of bots or an error message.

    """
    ircbots = [
        bot for bot in AccountDB.objects.filter(db_is_bot=True, username__startswith="ircbot-")
    ]
    if ircbots:
        table = cmd.styled_table(
            "|w#dbref|n",
            "|wbotname|n",
            "|wev-channel|n",
            "|wirc-channel|n",
            "|wSSL|n",
            maxwidth=_DEFAULT_WIDTH,
        )
        for ircbot in ircbots:
            ircinfo = "%s (%s:%s)" % (
                ircbot.db.irc_channel,
                ircbot.db.irc_network,
                ircbot.db.irc_port,
            )
            table.add_row(
                "#%i" % ircbot.id,
                ircbot.db.irc_botname,
                ircbot.db.ev_channel,
                ircinfo,
                ircbot.db.irc_ssl,
            )
        return table
    else:
        return "No irc bots found."


class CmdIRC2Chan(COMMAND_DEFAULT_CLASS):
    """
    Link an evennia channel to an external IRC channel

    Usage:
      irc2chan[/switches] <evennia_channel> = <ircnetwork> <port> <#irchannel> <botname>[:typeclass]
      irc2chan/delete botname|#dbid

    Switches:
      /delete     - this will delete the bot and remove the irc connection
                    to the channel. Requires the botname or #dbid as input.
      /remove     - alias to /delete
      /disconnect - alias to /delete
      /list       - show all irc<->evennia mappings
      /ssl        - use an SSL-encrypted connection

    Example:
      irc2chan myircchan = irc.dalnet.net 6667 #mychannel evennia-bot
      irc2chan public = irc.freenode.net 6667 #evgaming #evbot:accounts.mybot.MyBot

    This creates an IRC bot that connects to a given IRC network and
    channel. If a custom typeclass path is given, this will be used
    instead of the default bot class.
    The bot will relay everything said in the evennia channel to the
    IRC channel and vice versa. The bot will automatically connect at
    server start, so this command need only be given once. The
    /disconnect switch will permanently delete the bot. To only
    temporarily deactivate it, use the  |wservices|n command instead.
    Provide an optional bot class path to use a custom bot.
    """

    key = "irc2chan"
    switch_options = ("delete", "remove", "disconnect", "list", "ssl")
    locks = "cmd:serversetting(IRC_ENABLED) and pperm(Developer)"
    help_category = "Comms"

    def func(self):
        """Setup the irc-channel mapping"""

        if not settings.IRC_ENABLED:
            string = """IRC is not enabled. You need to activate it in game/settings.py."""
            self.msg(string)
            return

        if "list" in self.switches:
            # show all connections
            self.msg(_list_bots(self))
            return

        if "disconnect" in self.switches or "remove" in self.switches or "delete" in self.switches:
            botname = "ircbot-%s" % self.lhs
            matches = AccountDB.objects.filter(db_is_bot=True, username=botname)
            dbref = utils.dbref(self.lhs)
            if not matches and dbref:
                # try dbref match
                matches = AccountDB.objects.filter(db_is_bot=True, id=dbref)
            if matches:
                matches[0].delete()
                self.msg("IRC connection destroyed.")
            else:
                self.msg("IRC connection/bot could not be removed, does it exist?")
            return

        if not self.args or not self.rhs:
            string = (
                "Usage: irc2chan[/switches] <evennia_channel> ="
                " <ircnetwork> <port> <#irchannel> <botname>[:typeclass]"
            )
            self.msg(string)
            return

        channel = self.lhs
        self.rhs = self.rhs.replace("#", " ")  # to avoid Python comment issues
        try:
            irc_network, irc_port, irc_channel, irc_botname = [
                part.strip() for part in self.rhs.split(None, 4)
            ]
            irc_channel = "#%s" % irc_channel
        except Exception:
            string = "IRC bot definition '%s' is not valid." % self.rhs
            self.msg(string)
            return

        botclass = None
        if ":" in irc_botname:
            irc_botname, botclass = [part.strip() for part in irc_botname.split(":", 2)]
        botname = "ircbot-%s" % irc_botname
        # If path given, use custom bot otherwise use default.
        botclass = botclass if botclass else bots.IRCBot
        irc_ssl = "ssl" in self.switches

        # create a new bot
        bot = AccountDB.objects.filter(username__iexact=botname)
        if bot:
            # re-use an existing bot
            bot = bot[0]
            if not bot.is_bot:
                self.msg("Account '%s' already exists and is not a bot." % botname)
                return
        else:
            try:
                bot = create.create_account(botname, None, None, typeclass=botclass)
            except Exception as err:
                self.msg("|rError, could not create the bot:|n '%s'." % err)
                return
        bot.start(
            ev_channel=channel,
            irc_botname=irc_botname,
            irc_channel=irc_channel,
            irc_network=irc_network,
            irc_port=irc_port,
            irc_ssl=irc_ssl,
        )
        self.msg("Connection created. Starting IRC bot.")


class CmdIRCStatus(COMMAND_DEFAULT_CLASS):
    """
    Check and reboot IRC bot.

    Usage:
        ircstatus [#dbref ping||nicklist||reconnect]

    If not given arguments, will return a list of all bots (like
    irc2chan/list). The 'ping' argument will ping the IRC network to
    see if the connection is still responsive. The 'nicklist' argument
    (aliases are 'who' and 'users') will return a list of users on the
    remote IRC channel.  Finally, 'reconnect' will force the client to
    disconnect and reconnect again. This may be a last resort if the
    client has silently lost connection (this may happen if the remote
    network experience network issues). During the reconnection
    messages sent to either channel will be lost.

    """

    key = "ircstatus"
    locks = "cmd:serversetting(IRC_ENABLED) and perm(ircstatus) or perm(Builder))"
    help_category = "Comms"

    def func(self):
        """Handles the functioning of the command."""

        if not self.args:
            self.msg(_list_bots(self))
            return
        # should always be on the form botname option
        args = self.args.split()
        if len(args) != 2:
            self.msg("Usage: ircstatus [#dbref ping||nicklist||reconnect]")
            return
        botname, option = args
        if option not in ("ping", "users", "reconnect", "nicklist", "who"):
            self.msg("Not a valid option.")
            return
        matches = None
        if utils.dbref(botname):
            matches = AccountDB.objects.filter(db_is_bot=True, id=utils.dbref(botname))
        if not matches:
            self.msg(
                "No matching IRC-bot found. Use ircstatus without arguments to list active bots."
            )
            return
        ircbot = matches[0]
        channel = ircbot.db.irc_channel
        network = ircbot.db.irc_network
        port = ircbot.db.irc_port
        chtext = "IRC bot '%s' on channel %s (%s:%s)" % (
            ircbot.db.irc_botname,
            channel,
            network,
            port,
        )
        if option == "ping":
            # check connection by sending outself a ping through the server.
            self.caller.msg("Pinging through %s." % chtext)
            ircbot.ping(self.caller)
        elif option in ("users", "nicklist", "who"):
            # retrieve user list. The bot must handles the echo since it's
            # an asynchronous call.
            self.caller.msg("Requesting nicklist from %s (%s:%s)." % (channel, network, port))
            ircbot.get_nicklist(self.caller)
        elif self.caller.locks.check_lockstring(
            self.caller, "dummy:perm(ircstatus) or perm(Developer)"
        ):
            # reboot the client
            self.caller.msg("Forcing a disconnect + reconnect of %s." % chtext)
            ircbot.reconnect()
        else:
            self.caller.msg("You don't have permission to force-reload the IRC bot.")


# RSS connection
class CmdRSS2Chan(COMMAND_DEFAULT_CLASS):
    """
    link an evennia channel to an external RSS feed

    Usage:
      rss2chan[/switches] <evennia_channel> = <rss_url>

    Switches:
      /disconnect - this will stop the feed and remove the connection to the
                    channel.
      /remove     -                                 "
      /list       - show all rss->evennia mappings

    Example:
      rss2chan rsschan = http://code.google.com/feeds/p/evennia/updates/basic

    This creates an RSS reader  that connects to a given RSS feed url. Updates
    will be echoed as a title and news link to the given channel. The rate of
    updating is set with the RSS_UPDATE_INTERVAL variable in settings (default
    is every 10 minutes).

    When disconnecting you need to supply both the channel and url again so as
    to identify the connection uniquely.
    """

    key = "rss2chan"
    switch_options = ("disconnect", "remove", "list")
    locks = "cmd:serversetting(RSS_ENABLED) and pperm(Developer)"
    help_category = "Comms"

    def func(self):
        """Setup the rss-channel mapping"""

        # checking we have all we need
        if not settings.RSS_ENABLED:
            string = """RSS is not enabled. You need to activate it in game/settings.py."""
            self.msg(string)
            return
        try:
            import feedparser

            assert feedparser  # to avoid checker error of not being used
        except ImportError:
            string = (
                "RSS requires python-feedparser (https://pypi.python.org/pypi/feedparser)."
                " Install before continuing."
            )
            self.msg(string)
            return

        if "list" in self.switches:
            # show all connections
            rssbots = [
                bot
                for bot in AccountDB.objects.filter(db_is_bot=True, username__startswith="rssbot-")
            ]
            if rssbots:
                table = self.styled_table(
                    "|wdbid|n",
                    "|wupdate rate|n",
                    "|wev-channel",
                    "|wRSS feed URL|n",
                    border="cells",
                    maxwidth=_DEFAULT_WIDTH,
                )
                for rssbot in rssbots:
                    table.add_row(
                        rssbot.id, rssbot.db.rss_rate, rssbot.db.ev_channel, rssbot.db.rss_url
                    )
                self.msg(table)
            else:
                self.msg("No rss bots found.")
            return

        if "disconnect" in self.switches or "remove" in self.switches or "delete" in self.switches:
            botname = "rssbot-%s" % self.lhs
            matches = AccountDB.objects.filter(db_is_bot=True, db_key=botname)
            if not matches:
                # try dbref match
                matches = AccountDB.objects.filter(db_is_bot=True, id=self.args.lstrip("#"))
            if matches:
                matches[0].delete()
                self.msg("RSS connection destroyed.")
            else:
                self.msg("RSS connection/bot could not be removed, does it exist?")
            return

        if not self.args or not self.rhs:
            string = "Usage: rss2chan[/switches] <evennia_channel> = <rss url>"
            self.msg(string)
            return
        channel = self.lhs
        url = self.rhs

        botname = "rssbot-%s" % url
        bot = AccountDB.objects.filter(username__iexact=botname)
        if bot:
            # re-use existing bot
            bot = bot[0]
            if not bot.is_bot:
                self.msg("Account '%s' already exists and is not a bot." % botname)
                return
        else:
            # create a new bot
            bot = create.create_account(botname, None, None, typeclass=bots.RSSBot)
        bot.start(ev_channel=channel, rss_url=url, rss_rate=10)
        self.msg("RSS reporter created. Fetching RSS.")


class CmdGrapevine2Chan(COMMAND_DEFAULT_CLASS):
    """
    Link an Evennia channel to an exteral Grapevine channel

    Usage:
      grapevine2chan[/switches] <evennia_channel> = <grapevine_channel>
      grapevine2chan/disconnect <connection #id>

    Switches:
        /list     - (or no switch): show existing grapevine <-> Evennia
                    mappings and available grapevine chans
        /remove   - alias to disconnect
        /delete   - alias to disconnect

    Example:
        grapevine2chan mygrapevine = gossip

    This creates a link between an in-game Evennia channel and an external
    Grapevine channel. The game must be registered with the Grapevine network
    (register at https://grapevine.haus) and the GRAPEVINE_* auth information
    must be added to game settings.
    """

    key = "grapevine2chan"
    switch_options = ("disconnect", "remove", "delete", "list")
    locks = "cmd:serversetting(GRAPEVINE_ENABLED) and pperm(Developer)"
    help_category = "Comms"

    def func(self):
        """Setup the Grapevine channel mapping"""

        if not settings.GRAPEVINE_ENABLED:
            self.msg("Set GRAPEVINE_ENABLED=True in settings to enable.")
            return

        if "list" in self.switches:
            # show all connections
            gwbots = [
                bot
                for bot in AccountDB.objects.filter(
                    db_is_bot=True, username__startswith="grapevinebot-"
                )
            ]
            if gwbots:
                table = self.styled_table(
                    "|wdbid|n",
                    "|wev-channel",
                    "|wgw-channel|n",
                    border="cells",
                    maxwidth=_DEFAULT_WIDTH,
                )
                for gwbot in gwbots:
                    table.add_row(gwbot.id, gwbot.db.ev_channel, gwbot.db.grapevine_channel)
                self.msg(table)
            else:
                self.msg("No grapevine bots found.")
            return

        if "disconnect" in self.switches or "remove" in self.switches or "delete" in self.switches:
            botname = "grapevinebot-%s" % self.lhs
            matches = AccountDB.objects.filter(db_is_bot=True, db_key=botname)

            if not matches:
                # try dbref match
                matches = AccountDB.objects.filter(db_is_bot=True, id=self.args.lstrip("#"))
            if matches:
                matches[0].delete()
                self.msg("Grapevine connection destroyed.")
            else:
                self.msg("Grapevine connection/bot could not be removed, does it exist?")
            return

        if not self.args or not self.rhs:
            string = "Usage: grapevine2chan[/switches] <evennia_channel> = <grapevine_channel>"
            self.msg(string)
            return

        channel = self.lhs
        grapevine_channel = self.rhs

        botname = "grapewinebot-%s-%s" % (channel, grapevine_channel)
        bot = AccountDB.objects.filter(username__iexact=botname)
        if bot:
            # re-use existing bot
            bot = bot[0]
            if not bot.is_bot:
                self.msg("Account '%s' already exists and is not a bot." % botname)
                return
            else:
                self.msg("Reusing bot '%s' (%s)" % (botname, bot.dbref))
        else:
            # create a new bot
            bot = create.create_account(botname, None, None, typeclass=bots.GrapevineBot)

        bot.start(ev_channel=channel, grapevine_channel=grapevine_channel)
        self.msg(f"Grapevine connection created {channel} <-> {grapevine_channel}.")
