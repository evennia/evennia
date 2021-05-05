"""
Comsystem command module.

Comm commands are OOC commands and intended to be made available to
the Account at all times (they go into the AccountCmdSet). So we
make sure to homogenize self.caller to always be the account object
for easy handling.

"""
from django.conf import settings
from evennia.comms.models import Msg
from evennia.accounts.models import AccountDB
from evennia.accounts import bots
from evennia.locks.lockhandler import LockException
from evennia.utils import create, logger, utils
from evennia.utils.logger import tail_log_file
from evennia.utils.utils import class_from_module
from evennia.utils.evmenu import ask_yes_no

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)
CHANNEL_DEFAULT_TYPECLASS = class_from_module(
    settings.BASE_CHANNEL_TYPECLASS, fallback=settings.FALLBACK_CHANNEL_TYPECLASS)


# limit symbol import for API
__all__ = (
    "CmdChannel",
    "CmdAddCom",
    "CmdDelCom",
    "CmdAllCom",
    "CmdCdestroy",
    "CmdCBoot",
    "CmdCWho",
    "CmdChannelCreate",
    "CmdClock",
    "CmdCdesc",
    "CmdPage",
    "CmdIRC2Chan",
    "CmdIRCStatus",
    "CmdRSS2Chan",
    "CmdGrapevine2Chan",
)
_DEFAULT_WIDTH = settings.CLIENT_DEFAULT_WIDTH

# helper functions to make it easier to override the main CmdChannel
# command and to keep the legacy addcom etc commands around.


class CmdChannel(COMMAND_DEFAULT_CLASS):
    """
    Talk on and manage in-game channels.

    Usage:
      channel
      channel channelname [= <msg>]
      channel/list
      channel/all
      channel/history channelname [= index]
      channel/sub channelname [= alias[;alias...]]
      channel/unsub channelname[,channelname, ...]
      channel/alias channelname = alias[;alias...]
      channel/unalias alias
      channel/mute channelname[,channelname,...]
      channel/unmute channelname[,channelname,...]
      channel/create channelname;alias;alias:typeclass [= description]
      channel/destroy channelname [= reason]
      channel/desc channelname = description
      channel/lock channelname = lockstring
      channel/unlock channelname = lockstring
      channel/boot[/quiet] channelname[,channelname,...] = subscribername [: reason]
      channel/ban channelname   (list bans)
      channe/ban[/quiet] channelname[, channelname, ...] = subscribername [: reason]
      channel/unban[/quiet] channelname[, channelname, ...] = subscribername
      channel/who channelname

    # help-subcategories
    ## channel/list

    This handles all operations on channels. Note that the default operation is to
    assign a nick/alias for sending to a channel. This would mean you can send
    using 'foo Hello world' instead of using 'channel foo = Hello world'. Note that
    aliases set when creating the channel are made available as aliases to subscribers
    automatically.

    """
    key = "channel"
    aliases = ["chan", "channels"]
    locks = "cmd: not pperm(channel_banned)"
    switch_options = (
        "list", "all", "history", "sub", "unsub", "mute", "unmute", "alias", "unalias",
        "create", "destroy", "desc", "lock", "unlock", "boot", "ban", "unban", "who",)
    # disable this in child command classes if wanting on-character channels
    account_caller = True

    # note - changing this will invalidate existing aliases in db
    # channel_msg_nick_alias = r"{alias}\s*?(?P<arg1>.+?){{0,1}}"
    channel_msg_nick_alias = r"{alias}\s*?|{alias}\s+?(?P<arg1>.+?)"
    channel_msg_nick_replacement = "channel {channelname} = $1"

    def search_channel(self, channelname, exact=False, handle_errors=True):
        """
        Helper function for searching for a single channel with some error
        handling.

        Args:
            channelname (str): Name, alias #dbref or partial name/alias to search
                for.
            exact (bool, optional): If an exact or fuzzy-match of the name should be done.
                Note that even for a fuzzy match, an exactly given, unique channel name
                will always be returned.
            handle_errors (bool): If true, use `self.msg` to report errors if
                there are non/multiple matches. If so, the return will always be
                a single match or None.
        Returns:
            object, list or None: If `handle_errors` is `True`, this is either a found Channel
                or `None`. Otherwise it's a list  of zero, one or more channels found.
        Notes:
            The 'listen' and 'control' accesses are checked before returning.

        """
        caller = self.caller
        # first see if this is a personal alias
        channelname = caller.nicks.get(key=channelname, category="channel") or channelname

        # always try the exact match first.
        channels = CHANNEL_DEFAULT_TYPECLASS.objects.channel_search(channelname, exact=True)

        if not channels and not exact:
            # try fuzzy matching as well
            channels = CHANNEL_DEFAULT_TYPECLASS.objects.channel_search(channelname, exact=exact)

        # check permissions
        channels = [channel for channel in channels
                    if channel.access(caller, 'listen') or channel.access(caller, 'control')]

        if handle_errors:
            if not channels:
                self.msk(f"No channel found matching '{channelname}' "
                         "could also be due to missing access).")
                return None
            elif len(channels) > 1:
                self.msg("Multiple possible channel matches/alias for "
                         "'{channelname}':\n" + ", ".join(chan.key for chan in channels))
                return None
            return channels[0]
        else:
            if not channels:
                return []
            elif len(channels) > 1:
                return list(channels)
            return [channels[0]]

    def msg_channel(self, channel, message, **kwargs):
        """
        Send a message to a given channel. At this point
        any permissions should already be done.

        Args:
            channel (Channel): The channel to send to.
            message (str): The message to send.
            **kwargs: Unused by default. These kwargs will be passed into
                all channel messaging hooks for custom overriding.

        """
        channel.msg(message, senders=self.caller, **kwargs)

    def get_channel_history(self, channel, start_index=0):
        """
        View a channel's history.

        Args:
            channel (Channel): The channel to access.
            message (str): The message to send.
            **kwargs: Unused by default. These kwargs will be passed into
                all channel messaging hooks for custom overriding.

        """
        caller = self.caller

        log_file = channel.attributes.get(
            "log_file", default=channel.log_to_file.format(channel_key=channel.key))

        def send_msg(lines):
            return self.msg(
                "".join(line.split("[-]", 1)[1] if "[-]" in line else line for line in lines)
            )
        # asynchronously tail the log file
        tail_log_file(log_file, start_index, 20, callback=send_msg)

    def sub_to_channel(self, channel):
        """
        Subscribe to a channel. Note that all permissions should
        be checked before this step.

        Args:
            channel (Channel): The channel to access.

        Returns:
            bool, str: True, None if connection failed. If False,
                the second part is an error string.

        """
        caller = self.caller

        if channel.has_connection(caller):
            return False, f"Already listening to channel {channel.key}."
        result = channel.connect(caller)

        key_and_aliases = [channel.key.lower()] + [alias.lower() for alias in channel.aliases.all()]
        for key_or_alias in key_and_aliases:
            self.add_alias(channel, key_or_alias)

        return result, "" if result else f"Were not allowed to subscribe to channel {channel.key}"

    def unsub_from_channel(self, channel, **kwargs):
        """
        Un-Subscribe to a channel. Note that all permissions should
        be checked before this step.

        Args:
            channel (Channel): The channel to unsub from.
            **kwargs: Passed on to nick removal.

        Returns:
            bool, str: True, None if un-connection succeeded. If False,
                the second part is an error string.

        """
        caller = self.caller

        if not channel.has_connection(caller):
            return False, f"Not listening to channel {channel.key}."
        # clear aliases
        for key_or_alias in self.get_channel_aliases(channel):
            self.remove_alias(key_or_alias, **kwargs)
        # remove the channel-name alias too
        msg_alias = self.channel_msg_nick_alias.format(alias=channel.key.lower())
        caller.nicks.remove(msg_alias, category="inputline", **kwargs)

        result = channel.disconnect(caller)
        return result, "" if result else f"Could not unsubscribe from channel {channel.key}"

    def add_alias(self, channel, alias, **kwargs):
        """
        Add a new alias (nick) for the user to use with this channel.

        Args:
            channel (Channel): The channel to alias.
            alias (str): The personal alias to use for this channel.
            **kwargs: If given, passed into nicks.add.

        Note:
            We add two nicks - one is a plain `alias -> channel.key` that
            we need to be able to reference this channel easily. The other
            is a templated nick to easily be able to send messages to the
            channel without needing to give the full `channel` command. The
            structure of this nick is given by `self.channel_msg_nick_alias`
            and `self.channel_msg_nick_replacement`. By default it maps
            `alias <msg> -> channel <channelname> = <msg>`, so that you can
            for example just write `pub Hello` to send a message.

            The alias created is `alias $1 -> channel channel = $1`, to allow
            for sending to channel using the main channel command.

        """
        chan_key = channel.key.lower()
        # the message-pattern allows us to type the channel on its own without
        # needing to use the `channel` command explicitly.
        msg_pattern = self.channel_msg_nick_alias.format(alias=alias)
        msg_replacement = self.channel_msg_nick_replacement.format(channelname=chan_key)

        if chan_key != alias:
            self.caller.nicks.add(alias, chan_key, category="channel", **kwargs)
        self.caller.nicks.add(msg_pattern, msg_replacement, category="inputline",
                              pattern_is_regex=True, **kwargs)

    def remove_alias(self, alias, **kwargs):
        """
        Remove an alias from a channel.

        Args:
            alias (str, optional): The alias to remove.
                The channel will be reverse-determined from the
                alias, if it exists.

        Returns:
            bool, str: True, None if removal succeeded. If False,
                the second part is an error string.
            **kwargs: If given, passed into nicks.get/add.

        Note:
            This will remove two nicks - the plain channel alias and the templated
            nick used for easily sending messages to the channel.

        """
        caller = self.caller
        if caller.nicks.get(alias, category="channel", **kwargs):
            caller.nicks.remove(alias, category="chan nel", **kwargs)
            msg_alias = self.channel_msg_nick_alias.format(alias=alias)
            caller.nicks.remove(msg_alias, category="inputline", **kwargs)
            return True, ""

        return False, "No such alias was defined."

    def get_channel_aliases(self, channel):
        """
        Get a user's aliases for a given channel. The user is retrieved
        through self.caller.

        Args:
            channel (Channel): The channel to act on.

        Returns:
            list: A list of zero, one or more alias-strings.

        """
        chan_key = channel.key.lower()
        nicktuples = self.caller.nicks.get(category="channel", return_tuple=True)
        if nicktuples:
            return [tup[2] for tup in nicktuples if tup[3].lower() == chan_key]
        return []

    def mute_channel(self, channel):
        """
        Temporarily mute a channel.

        Args:
            channel (Channel): The channel to alias.

        Returns:
            bool, str: True, None if muting successful. If False,
                the second part is an error string.
        """
        if channel.mute(self.caller):
            return True, ""
        return False, f"Channel {channel.key} was already muted."

    def unmute_channel(self, channel):
        """
        Unmute a channel.

        Args:
            channel (Channel): The channel to alias.

        Returns:
            bool, str: True, None if unmuting successful. If False,
                the second part is an error string.

        """
        if channel.unmute(self.caller):
            return True, ""
        return False, f"Channel {channel.key} was already unmuted."

    def create_channel(self, name, description, typeclass=None, aliases=None):
        """
        Create a new channel. Its name must not previously exist
        (users can alias as needed). Will also connect to the
        new channel.

        Args:
            name (str): The new channel name/key.
            description (str): This is used in listings.
            aliases (list): A list of strings - alternative aliases for the channel
                (not to be confused with per-user aliases; these are available for
                everyone).

        Returns:
            channel, str: new_channel, "" if creation successful. If False,
                the second part is an error string.

        """
        caller = self.caller
        if typeclass:
            typeclass = class_from_module(typeclass)
        else:
            typeclass = CHANNEL_DEFAULT_TYPECLASS

        if typeclass.objects.channel_search(name, exact=True):
            return False, f"Channel {name} already exists."

        # set up the new channel
        lockstring = "send:all();listen:all();control:id(%s)" % caller.id

        new_chan = create.create_channel(
            name, aliases=aliases, desc=description, locks=lockstring, typeclass=typeclass)
        new_chan.connect(caller)
        return new_chan, ""

    def destroy_channel(self, channel, message=None):
        """
        Destroy an existing channel. Access should be checked before
        calling this function.

        Args:
            channel (Channel): The channel to alias.
            message (str, optional): Final message to send onto the channel
                before destroying it. If not given, a default message is
                used. Set to the empty string for no message.

        if typeclass:
           pass

        """
        caller = self.caller

        channel_key = channel.key
        if message is None:
            message = (f"|rChannel {channel_key} is being destroyed. "
                       "Make sure to clean any channel aliases.|n")
        if message:
            channel.msg(message, senders=caller, bypass_mute=True)
        channel.delete()
        logger.log_sec(
            "Channel {} was deleted by {}".format(channel_key, caller)
        )

    def set_lock(self, channel, lockstring):
        """
        Set a lockstring on a channel. Permissions must have been
        checked before this call.

        Args:
            channel (Channel): The channel to operate on.
            lockstring (str): A lockstring on the form 'type:lockfunc();...'

        Returns:
            bool, str: True, None if setting lock was successful. If False,
                the second part is an error string.

        """
        try:
            channel.locks.add(lockstring)
        except LockException as err:
            return False, err
        return True, ""

    def unset_lock(self, channel, lockstring):
        """
        Remove locks in a lockstring on a channel. Permissions must have been
        checked before this call.

        Args:
            channel (Channel): The channel to operate on.
            lockstring (str): A lockstring on the form 'type:lockfunc();...'

        Returns:
            bool, str: True, None if setting lock was successful. If False,
                the second part is an error string.

        """
        try:
            channel.locks.remove(lockstring)
        except LockException as err:
            return False, err
        return True, ""

    def set_desc(self, channel, description):
        """
        Set a channel description. This is shown in listings etc.

        Args:
            caller (Object or Account): The entity performing the action.
            channel (Channel): The channel to operate on.
            description (str): A short description of the channel.

        Returns:
            bool, str: True, None if setting lock was successful. If False,
                the second part is an error string.

        """
        channel.db.desc = description

    def boot_user(self, channel, target, quiet=False, reason=""):
        """
        Boot a user from a channel, with optional reason. This will
        also remove all their aliases for this channel.

        Args:
            channel (Channel): The channel to operate on.
            target (Object or Account): The entity to boot.
            quiet (bool, optional): Whether or not to announce to channel.
            reason (str, optional): A reason for the boot.

        Returns:
            bool, str: True, None if setting lock was successful. If False,
                the second part is an error string.

        """
        if not channel.subscriptions.has(target):
            return False, f"{target} is not connected to channel {channel.key}."
        # find all of target's nicks linked to this channel and delete them
        for nick in [
            nick
            for nick in target.nicks.get(category="channel") or []
            if nick.value[3].lower() == channel.key
        ]:
            nick.delete()
        channel.disconnect(target)
        reason = f" Reason: {reason}" if reason else ""
        target.msg(f"You were booted from channel {channel.key} by {self.caller.key}.{reason}")
        if not quiet:
            channel.msg(f"{target.key} was booted from channel by {self.caller.key}.{reason}")

        logger.log_sec(f"Channel Boot: {target} (Channel: {channel}, "
                       f"Reason: {reason.strip()}, Caller: {self.caller}")
        return True, ""

    def ban_user(self, channel, target, quiet=False, reason=""):
        """
        Ban a user from a channel, by locking them out. This will also
        boot them, if they are currently connected.

        Args:
            channel (Channel): The channel to operate on.
            target (Object or Account): The entity to ban
            quiet (bool, optional): Whether or not to announce to channel.
            reason (str, optional): A reason for the ban

        Returns:
            bool, str: True, None if banning was successful. If False,
                the second part is an error string.

        """
        self.boot_user(channel, target, quiet=quiet, reason=reason)
        if channel.ban(target):
            return True, ""
        return False, f"{target} is already banned from this channel."

    def unban_user(self, channel, target):
        """
        Un-Ban a user from a channel. This will not reconnect them
        to the channel, just allow them to connect again (assuming
        they have the suitable 'listen' lock like everyone else).

        Args:
            channel (Channel): The channel to operate on.
            target (Object or Account): The entity to unban

        Returns:
            bool, str: True, None if unbanning was successful. If False,
                the second part is an error string.

        """
        if channel.unban(target):
            return True, ""
        return False, f"{target} was not previously banned from this channel."

    def channel_list_bans(self, channel):
        """
        Show a channel's bans.

        Args:
            channel (Channel): The channel to operate on.

        Returns:
            list: A list of strings, each the name of a banned user.

        """
        return [banned.key for banned in channel.banlist]

    def channel_list_who(self, channel):
        """
        Show a list of online people is subscribing to a channel. This will check
        the 'control' permission of `caller` to determine if only online users
        should be returned or everyone.

        Args:
            channel (Channel): The channel to operate on.

        Returns:
            list: A list of prepared strings, with name + markers for if they are
                muted or offline.

        """
        caller = self.caller
        mute_list = list(channel.mutelist)
        online_list = channel.subscriptions.online()
        if channel.access(caller, 'control'):
            # for those with channel control, show also offline users
            all_subs = list(channel.subscriptions.all())
        else:
            # for others, only show online users
            all_subs = online_list

        who_list = []
        for subscriber in all_subs:
            name = subscriber.get_display_name(caller)
            conditions = ("muted" if subscriber in mute_list else "",
                          "offline" if subscriber not in online_list else "")
            conditions = (cond for cond in conditions if cond)
            cond_text = "(" + ", ".join(conditions) + ")" if conditions else ""
            who_list.append(f"{name}{cond_text}")

        return who_list

    def list_channels(self, channelcls=CHANNEL_DEFAULT_TYPECLASS):
        """
        Return a available channels.

        Args:
            channelcls (Channel, optional): The channel-class to query on. Defaults
                to the default channel class from settings.

        Returns:
            tuple: A tuple `(subbed_chans, available_chans)` with the channels
                currently subscribed to, and those we have 'listen' access to but
                don't actually sub to yet.

        """
        caller = self.caller
        subscribed_channels = list(channelcls.objects.get_subscriptions(caller))
        unsubscribed_available_channels = [
            chan
            for chan in channelcls.objects.get_all_channels()
            if chan not in subscribed_channels and chan.access(caller, "listen")
        ]
        return subscribed_channels, unsubscribed_available_channels

    def display_subbed_channels(self, subscribed):
        """
        Display channels subscribed to.

        Args:
            subscribed (list): List of subscribed channels

        Returns:
            EvTable: Table to display.

        """
        comtable = self.styled_table(
            "|wchannel|n",
            "|wmy aliases|n",
            "|wdescription|n",
            align="l",
            maxwidth=_DEFAULT_WIDTH
        )

        for chan in subscribed:
            my_aliases = ", ".join(self.get_channel_aliases(chan))
            comtable.add_row(
                *("{}{}".format(
                    chan.key,
                    "({})".format(",".join(chan.aliases.all())) if chan.aliases.all() else ""),
                  my_aliases,
                  chan.db.desc))
        return comtable

    def display_all_channels(self, subscribed, available):
        """
        Display all available channels

        Args:
            subscribed (list): List of subscribed channels

        Returns:
            EvTable: Table to display.

        """
        caller = self.caller

        comtable = self.styled_table(
            "|wsub|n",
            "|wchannel|n",
            "|wmy aliases|n",
            "|wlocks|n",
            "|wdescription|n",
            maxwidth=_DEFAULT_WIDTH,
        )
        channels = subscribed + available

        for chan in channels:
            my_aliases = ", ".join(self.get_channel_aliases(chan))
            if chan not in subscribed:
                substatus = "|rNo|n"
            elif caller in chan.mutelist:
                substatus = "|rMuted|n"
            else:
                substatus = "|gYes|n"
            comtable.add_row(
                *(substatus,
                  "{}{}".format(
                      chan.key,
                      "({})".format(",".join(chan.aliases.all())) if chan.aliases.all() else ""),
                  my_aliases,
                  str(chan.locks),
                  chan.db.desc))
        comtable.reformat_column(0, width=9)
        comtable.reformat_column(3, width=14)

        return comtable

    def func(self):
        """
        Main functionality of command.
        """
        # from evennia import set_trace;set_trace()

        caller = self.caller
        switches = self.switches
        channel_names = [name for name in self.lhslist if name]

        #from evennia import set_trace;set_trace()

        if not channel_names:
            if 'all' in switches:
                # show all available channels
                subscribed, available = self.list_channels()
                table = self.display_all_channels(subscribed, available)

                self.msg(
                    "\n|wAvailable channels|n (use /list to "
                    f"only show subscriptions)\n{table}")
                return
            else:
                # (empty or /list) show only subscribed channels
                subscribed, _ = self.list_channels()
                table = self.display_subbed_channels(subscribed)

                self.msg("\n|wChannel subscriptions|n "
                         f"(use |w/all|n to see all available):\n{table}")
                return

        if not self.switches and not self.args:
            self.msg("Usage[/switches]: channel [= message]")
            return

        if 'create' in switches:
            # create a new channel
            config = self.lhs
            if not config:
                self.msg("To create: channel/create name[;aliases][:typeclass] [= description]")
                return
            name, *typeclass = config.rsplit(":", 1)
            typeclass = typeclass[0] if typeclass else None
            name, *aliases = name.rsplit(";")
            description = self.rhs or ""
            chan, err = self.create_channel(name, description, typeclass=typeclass, aliases=aliases)
            if chan:
                self.msg(f"Created (and joined) new channel '{chan.key}'.")
            else:
                self.msg(err)
            return

        if 'unalias' in switches:
            # remove a personal alias (no channel needed)
            alias = self.rhs
            if not alias:
                self.msg("Specify the alias to remove as channel/unalias <alias>")
                return
            success, err = self.remove_alias(alias)
            if success:
                self.msg(f"Removed your channel alias '{alias}'.")
            else:
                self.msg(err)
            return

        channels = []
        for channel_name in channel_names:
            # find a channel by fuzzy-matching. This also checks
            # 'listen/control' perms.
            channel = self.search_channel(channel_name, exact=False)
            if not channel:
                return
            channels.append(channel)

        # we have at least one channel at this point
        channel = channels[0]

        if not switches:
            if self.rhs:
                # send message to channel
                self.msg_channel(channel, self.rhs.strip())
            else:
                # inspect a given channel
                subscribed, available = self.list_channels()
                if channel in subscribed:
                    table = self.display_subbed_channels([channel])
                    inputname = self.raw_cmdname
                    if inputname.lower() != channel.key.lower():
                        header = f"Channel |w{inputname}|n (alias for {channel.key} channel)"
                    else:
                        header = f"Channel |w{channel.key}|n"
                    self.msg(f"{header}\n(use |w{inputname} <msg>|n to chat and "
                             f"the 'channel' command to customize)\n{table}")
                elif channel in available:
                    table = self.display_all_channels([], [channel])
                    self.msg(
                        "\n|wNot subscribed to this channel|n (use /list to "
                        f"show all subscriptions)\n{table}")
            return

        if 'history' in switches or 'hist' in switches:
            # view channel history

            index = self.rhs or 0
            try:
                index = max(0, int(index))
            except ValueError:
                self.msg("The history index (describing how many lines to go back) "
                         "must be an integer >= 0.")
                return
            self.get_channel_history(channel, start_index=index)
            return

        if 'sub' in switches:
            # subscribe to a channel
            aliases = []
            if self.rhs:
                aliases = set(alias.strip().lower() for alias in self.rhs.split(";"))
            success, err = self.sub_to_channel(channel)
            if success:
                for alias in aliases:
                    self.add_alias(channel, alias)
                alias_txt = ', '.join(aliases)
                alias_txt = f" using alias(es) {alias_txt}" if aliases else ''
                self.msg("You are now subscribed "
                         f"to the channel {channel.key}{alias_txt}. Use /alias to "
                         "add additional aliases for referring to the channel.")
            else:
                self.msg(err)
            return

        if 'unsub' in switches:
            # un-subscribe from a channel
            success, err = self.unsub_from_channel(channel)
            if success:
                self.msg(f"You un-subscribed from channel {channel.key}. "
                         "All aliases were cleared.")
            else:
                self.msg(err)
            return

        if 'alias' in switches:
            # create a new personal alias for a channel
            alias = self.rhs
            if not alias:
                self.msg("Specify the alias as channel/alias channelname = alias")
                return
            self.add_alias(channel, alias)
            self.msg(f"Added/updated your alias '{alias}' for channel {channel.key}.")
            return

        if 'mute' in switches:
            # mute a given channel
            success, err = self.mute_channel(channel)
            if success:
                self.msg(f"Muted channel {channel.key}.")
            else:
                self.msg(err)
            return

        if 'unmute' in switches:
            # unmute a given channel
            success, err = self.unmute_channel(channel)
            if success:
                self.msg(f"Un-muted channel {channel.key}.")
            else:
                self.msg(err)
            return

        if 'destroy' in switches or 'delete' in switches:
            # destroy a channel we control
            reason = self.rhs or None

            if not channel.access(caller, "control"):
                self.msg("You can only delete channels you control.")
                return

            def _perform_delete(caller, *args, **kwargs):
                self.destroy_channel(channel, message=reason)
                self.msg(f"Channel {channel.key} was successfully deleted.")

            ask_yes_no(
                caller,
                f"Are you sure you want to delete channel '{channel.key}'"
                "(make sure name is correct!)? This will disconnect and "
                "remove all users' aliases. {yesno}?",
                _perform_delete,
                "Aborted."
            )

        if 'desc' in switches:
            # set channel description
            desc = self.rhs.strip()

            if not channel.access(caller, "control"):
                self.msg("You can only change description of channels you control.")
                return

            if not desc:
                self.msg("Usage: /desc channel = description")
                return

            self.set_desc(channel, desc)
            self.msg("Updated channel description.")

        if 'lock' in switches:
            # add a lockstring to channel
            lockstring = self.rhs.strip()

            if not channel.access(caller, "control"):
                self.msg("You need 'control'-access to change locks on this channel.")
                return

            if not lockstring:
                self.msg("Usage: channel/lock channelname = lockstring")
                return

            success, err = self.set_lock(channel, self.rhs)
            if success:
                self.msg("Added/updated lock on channel.")
            else:
                self.msg(f"Could not add/update lock: {err}")
            return

        if 'unlock' in switches:
            # remove/update lockstring from channel
            lockstring = self.rhs.strip()

            if not lockstring:
                self.msg("Usage: channel/unlock channelname = lockstring")
                return

            if not channel.access(caller, "control"):
                self.msg("You need 'control'-access to change locks on this channel.")
                return

            success, err = self.unset_lock(channel, self.rhs)
            if success:
                self.msg("Removed lock from channel.")
            else:
                self.msg(f"Could not remove lock: {err}")
            return

        if 'boot' in switches:
            # boot a user from channel(s)

            if not self.rhs:
                self.msg("Usage: channel/boot channel[,channel,...] = username [:reason]")
                return

            target_str, *reason = self.rhs.rsplit(":", 1)
            reason = reason[0].strip() if reason else ""

            for chan in channels:

                if not chan.access(caller, "control"):
                    self.msg(f"You need 'control'-access to boot a user from {chan.key}.")
                    return

                # the target must be a member of all given channels
                target = caller.search(target_str, candidates=chan.subscriptions.all())
                if not target:
                    self.msg(f"Cannot boot '{target_str}' - not in channel {chan.key}.")
                    return

            def _boot_user(caller, *args, **kwargs):
                for chan in channels:
                    success, err = self.boot_user(chan, target, quiet=False, reason=reason)
                    if success:
                        self.msg(f"Booted {target.key} from channel {chan.key}.")
                    else:
                        self.msg(f"Cannot boot {target.key} from channel {chan.key}: {err}")

            channames = ", ".join(chan.key for chan in channels)
            reasonwarn = (". Also note that your reason will be echoed to the channel"
                          if reason else '')
            ask_yes_no(
                caller,
                f"Are you sure you want to boot user {target.key} from "
                f"channel(s) {channames} (make sure name/channels are correct{reasonwarn}). "
                "{yesno}?",
                _boot_user,
                "Aborted.",
                default="Y"
            )
            return

        if 'ban' in switches:
            # ban a user from channel(s)

            if not self.rhs:
                # view bans for channels

                if not channel.access(caller, "control"):
                    self.msg(f"You need 'control'-access to view bans on channel {channel.key}")
                    return

                bans = ["Channel bans "
                        "(to ban, use channel/ban channel[,channel,...] = username [:reason]"]
                bans.expand(self.channel_list_bans(channel))
                self.msg("\n".join(bans))
                return

            target_str, *reason = self.rhs.rsplit(":", 1)
            reason = reason[0].strip() if reason else ""

            for chan in channels:
                # the target must be a member of all given channels
                if not chan.access(caller, "control"):
                    self.msg(f"You don't have access to ban users on channel {chan.key}")
                    return

                target = caller.search(target_str, candidates=chan.subscriptions.all())

                if not target:
                    self.msg(f"Cannot ban '{target_str}' - not in channel {chan.key}.")
                    return

            def _ban_user(caller, *args, **kwargs):
                for chan in channels:
                    success, err = self.ban_user(chan, target, quiet=False, reason=reason)
                    if success:
                        self.msg(f"Banned {target.key} from channel {chan.key}.")
                    else:
                        self.msg(f"Cannot boot {target.key} from channel {chan.key}: {err}")

            channames = ", ".join(chan.key for chan in channels)
            reasonwarn = (". Also note that your reason will be echoed to the channel"
                          if reason else '')
            ask_yes_no(
                caller,
                f"Are you sure you want to ban user {target.key} from "
                f"channel(s) {channames} (make sure name/channels are correct{reasonwarn}) "
                "{yesno}?",
                _ban_user,
                "Aborted.",
            )
            return

        if 'unban' in switches:
            # unban a previously banned user from channel
            target_str = self.rhs.strip()

            if not target_str:
                self.msg("Usage: channel[,channel,...] = user")
                return

            banlists = []
            for chan in channels:
                # the target must be a member of all given channels
                if not chan.access(caller, "control"):
                    self.msg(f"You don't have access to unban users on channel {chan.key}")
                    return
                banlists.extend(chan.banlist)

            target = caller.search(target_str, candidates=banlists)
            if not target:
                self.msg("Could not find a banned user '{target_str}' in given channel(s).")
                return

            for chan in channels:
                success, err = self.unban_user(channel, target)
                if success:
                    self.msg(f"Un-banned {target_str} from channel {chan.key}")
                else:
                    self.msg(err)
            return

        if "who" in switches:
            # view who's a member of a channel

            who_list = [f"Subscribed to {channel.key}:"]
            who_list.extend(self.channel_list_who(channel))
            self.msg("\n".join(who_list))
            return


# a channel-command parent for use with Characters/Objects.
class CmdObjectChannel(CmdChannel):
    account_caller = False


class CmdAddCom(CmdChannel):
    """
    Add a channel alias and/or subscribe to a channel

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

        channel = self.search_channel(channelname)
        if not channel:
            return

        string = ""
        if not channel.has_connection(caller):
            # we want to connect as well.
            success, err = self.sub_to_channel(channel)
            if success:
                # if this would have returned True, the account is connected
                self.msg(f"You now listen to the channel {channel.key}")
            else:
                self.msg(f"{channel.key}: You are not allowed to join this channel.")
                return

        if channel.unmute(caller):
            self.msg(f"You unmute channel {channel.key}.")
        else:
            self.msg(f"You are already connected to channel {channel.key}.")

        if alias:
            # create a nick and add it to the caller.
            self.add_alias(channel, alias)
            self.msg(f" You can now refer to the channel {channel} with the alias '{alias}'.")
        else:
            string += " No alias added."
            self.msg(string)


class CmdDelCom(CmdChannel):
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

        if not self.args:
            self.msg("Usage: delcom <alias or channel>")
            return
        ostring = self.args.lower().strip()

        channel = self.search_channel(ostring)
        if not channel:
            return

        if not channel.has_connection(caller):
            self.msg("You are not listening to that channel.")
            return

        if ostring == channel.key.lower():
            # an exact channel name - unsubscribe
            delnicks = "all" in self.switches
            # find all nicks linked to this channel and delete them
            if delnicks:
                aliases = self.get_channel_aliases(channel)
                for alias in aliases:
                    self.remove_alias(alias)
            success, err = self.unsub_from_channel(channel)
            if success:
                wipednicks = " Eventual aliases were removed." if delnicks else ""
                self.msg(f"You stop listening to channel '{channel.key}'.{wipednicks}")
            else:
                self.msg(err)
            return
        else:
            # we are removing a channel nick
            self.remove_alias(ostring)
            self.msg(f"Any alias '{ostring}' for channel {channel.key} was cleared.")


class CmdAllCom(CmdChannel):
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
            subscribed, available = self.list_channels()
            table = self.display_all_channels(subscribed, available)
            self.msg(
                "\n|wAvailable channels:\n{table}")
            return
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

class CmdCdestroy(CmdChannel):
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

        channel = self.search_channel(self.args)

        if not channel:
            self.msg("Could not find channel %s." % self.args)
            return
        if not channel.access(caller, "control"):
            self.msg("You are not allowed to do that.")
            return
        channel_key = channel.key
        message = f"{channel.key} is being destroyed. Make sure to change your aliases."
        self.destroy_channel(channel, message)
        self.msg("Channel '%s' was destroyed." % channel_key)
        logger.log_sec(
            "Channel Deleted: %s (Caller: %s, IP: %s)."
            % (channel_key, caller, self.session.address)
        )


class CmdCBoot(CmdChannel):
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

        channel = self.search_channel(self.lhs)
        if not channel:
            return

        reason = ""
        if ":" in self.rhs:
            target, reason = self.rhs.rsplit(":", 1)
            is_account = target.strip().startswith("*")
            searchstring = target.lstrip("*")
        else:
            is_account = target.strip().startswith("*")
            searchstring = self.rhs.lstrip("*")

        target = self.caller.search(searchstring, account=is_account)
        if not target:
            return
        if reason:
            reason = " (reason: %s)" % reason
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return

        success, err = self.boot_user(target, quiet='quiet' in self.switches)
        if success:
            self.msg(f"Booted {target.key} from {channel.key}")
            logger.log_sec(
                "Channel Boot: %s (Channel: %s, Reason: %s, Caller: %s, IP: %s)."
                % (self.caller, channel, reason, self.caller, self.session.address)
            )
        else:
            self.msg(err)


class CmdCWho(CmdChannel):
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

        channel = self.search_channel(self.lhs)
        if not channel:
            return
        if not channel.access(self.caller, "listen"):
            string = "You can't access this channel."
            self.msg(string)
            return
        string = "\n|CChannel subscriptions|n"
        string += "\n|w%s:|n\n  %s" % (channel.key, channel.wholist)
        self.msg(string.strip())


class CmdChannelCreate(CmdChannel):
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

        new_chan, err = self.create_channel(channame, description, aliases=aliases)
        if new_chan:
            self.msg(f"Created channel {new_chan.key} and connected to it.")
        else:
            self.msg(err)


class CmdClock(CmdChannel):
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

        channel = self.search_channel(self.lhs)
        if not channel:
            return

        if not self.rhs:
            # no =, so just view the current locks
            self.msg(f"Current locks on {channel.key}\n{channel.locks}")
            return
        # we want to add/change a lock.
        if not channel.access(self.caller, "control"):
            string = "You don't control this channel."
            self.msg(string)
            return
        # Try to add the lock
        success, err = self.set_lock(channel, self.rhs)
        if success:
            self.msg(f"Lock(s) applied. Current locks on {channel.key}:\n{channel.locks}")
        else:
            self.msg(err)

class CmdCdesc(CmdChannel):
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
        channel = self.search_channel(self.lhs)
        if not channel:
            return
        # check permissions
        if not channel.access(caller, "control"):
            self.msg("You cannot admin this channel.")
            return
        self.set_desc(channel, self.rhs)
        self.msg(f"Description of channel '{channel.key}' set to '{self.rhs}'.")


class CmdPage(COMMAND_DEFAULT_CLASS):
    """
    send a private message to another account

    Usage:
      page <account> <message>
      page[/switches] [<account>,<account>,... = <message>]
      tell        ''
      page <number>

    Switches:
      last - shows who you last messaged
      list - show your last <number> of tells/pages (default)

    Send a message to target user (if online). If no argument is given, you will
    get a list of your latest messages. The equal sign is needed for multiple
    targets or if sending to target with space in the name.

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
        targets, message, number = [], None, None

        if "last" in self.switches:
            if pages_we_sent:
                recv = ",".join(obj.key for obj in pages_we_sent[-1].receivers)
                self.msg("You last paged |c%s|n:%s" % (recv, pages_we_sent[-1].message))
                return
            else:
                self.msg("You haven't paged anyone yet.")
                return

        if self.args:
            if self.rhs:
                for target in self.lhslist:
                    target_obj = self.caller.search(target)
                    if not target_obj:
                        return
                    targets.append(target_obj)
                message = self.rhs.strip()
            else:
                target, *message = self.args.split(" ", 4)
                if target and target.isnumeric():
                    # a number to specify a historic page
                    number = int(target)
                elif target:
                    target_obj = self.caller.search(target, quiet=True)
                    if target_obj:
                        # a proper target
                        targets = [target_obj[0]]
                    else:
                        # a message with a space in it - put it back together
                        message = target + " " + (message[0] if message else "")
                else:
                    # a single-word message
                    message = message[0].strip()

        pages = pages_we_sent + pages_we_got
        pages = sorted(pages, key=lambda page: page.date_created)

        if message:
            # send a message
            if not targets:
                # no target given - send to last person we paged
                if pages_we_sent:
                    targets = pages_we_sent[-1].receivers
                else:
                    self.msg("Who do you want page?")
                    return

            header = "|wAccount|n |c%s|n |wpages:|n" % caller.key
            if message.startswith(":"):
                message = "%s %s" % (caller.key, message.strip(":").strip())

            # create the persistent message object
            create.create_message(caller, message, receivers=targets)

            # tell the accounts they got a message.
            received = []
            rstrings = []
            for target in targets:
                if not target.access(caller, "msg"):
                    rstrings.append(f"You are not allowed to page {target}.")
                    continue
                target.msg(f"{header} {message}")
                if hasattr(target, "sessions") and not target.sessions.count():
                    received.append(f"|C{target.name}|n")
                    rstrings.append(
                        f"{received[-1]} is offline. They will see your message "
                        "if they list their pages later."
                    )
                else:
                    received.append(f"|c{target.name}|n")
            if rstrings:
                self.msg("\n".join(rstrings))
            self.msg("You paged %s with: '%s'." % (", ".join(received), message))
            return

        else:
            # no message to send
            if number is not None and len(pages) > number:
                lastpages = pages[-number:]
            else:
                lastpages = pages
            to_template = "|w{date}{clr} {sender}|nto{clr}{receiver}|n:> {message}"
            from_template = "|w{date}{clr} {receiver}|nfrom{clr}{sender}|n:< {message}"
            listing = []
            prev_selfsend = False
            for page in lastpages:
                multi_send = len(page.senders) > 1
                multi_recv = len(page.receivers) > 1
                sending = self.caller in page.senders
                # self-messages all look like sends, so we assume they always
                # come in close pairs and treat the second of the pair as the recv.
                selfsend = sending and self.caller in page.receivers
                if selfsend:
                    if prev_selfsend:
                        # this is actually a receive of a self-message
                        sending = False
                        prev_selfsend = False
                    else:
                        prev_selfsend = True

                clr = "|c" if sending else "|g"

                sender = f"|n,{clr}".join(obj.key for obj in page.senders)
                receiver = f"|n,{clr}".join([obj.name for obj in page.receivers])
                if sending:
                    template = to_template
                    sender = f"{sender} " if multi_send else ""
                    receiver = f" {receiver}" if multi_recv else f" {receiver}"
                else:
                    template = from_template
                    receiver = f"{receiver} " if multi_recv else ""
                    sender = f" {sender} " if multi_send else f" {sender}"

                listing.append(
                    template.format(
                        date=utils.datetime_format(page.date_created),
                        clr=clr,
                        sender=sender,
                        receiver=receiver,
                        message=page.message,
                    )

                )
            lastpages = "\n ".join(listing)

            if lastpages:
                string = "Your latest pages:\n %s" % lastpages
            else:
                string = "You haven't paged anyone yet."
            self.msg(string)
            return


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
