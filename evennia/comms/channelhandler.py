"""
The channel handler, accessed from this module as CHANNEL_HANDLER is a
singleton that handles the stored set of channels and how they are
represented against the cmdhandler.

If there is a channel named 'newbie', we want to be able to just write

    newbie Hello!

For this to work, 'newbie', the name of the channel, must be
identified by the cmdhandler as a command name. The channelhandler
stores all channels as custom 'commands' that the cmdhandler can
import and look through.

> Warning - channel names take precedence over command names, so make
sure to not pick clashing channel names.

Unless deleting a channel you normally don't need to bother about the
channelhandler at all - the create_channel method handles the update.

To delete a channel cleanly, delete the channel object, then call
update() on the channelhandler. Or use Channel.objects.delete() which
does this for you.

"""
from django.conf import settings
from evennia.commands import cmdset, command
from evennia.utils.logger import tail_log_file
from evennia.utils.utils import class_from_module
from django.utils.translation import ugettext as _

_CHANNEL_COMMAND_CLASS = None
_CHANNELDB = None


class ChannelCommand(command.Command):
    """
    {channelkey} channel

    {channeldesc}

    Usage:
       {lower_channelkey}  <message>
       {lower_channelkey}/history [start]
       {lower_channelkey} off - mutes the channel
       {lower_channelkey} on  - unmutes the channel

    Switch:
        history: View 20 previous messages, either from the end or
            from <start> number of messages from the end.

    Example:
        {lower_channelkey} Hello World!
        {lower_channelkey}/history
        {lower_channelkey}/history 30

    """

    # ^note that channeldesc and lower_channelkey will be filled
    # automatically by ChannelHandler

    # this flag is what identifies this cmd as a channel cmd
    # and branches off to the system send-to-channel command
    # (which is customizable by admin)
    is_channel = True
    key = "general"
    help_category = "Channel Names"
    obj = None
    arg_regex = r"\s.*?|/history.*?"

    def parse(self):
        """
        Simple parser
        """
        # cmdhandler sends channame:msg here.
        channelname, msg = self.args.split(":", 1)
        self.history_start = None
        if msg.startswith("/history"):
            arg = msg[8:]
            try:
                self.history_start = int(arg) if arg else 0
            except ValueError:
                # if no valid number was given, ignore it
                pass
        self.args = (channelname.strip(), msg.strip())

    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        global _CHANNELDB
        if not _CHANNELDB:
            from evennia.comms.models import ChannelDB as _CHANNELDB

        channelkey, msg = self.args
        caller = self.caller
        if not msg:
            self.msg(_("Say what?"))
            return
        channel = _CHANNELDB.objects.get_channel(channelkey)

        if not channel:
            self.msg(_("Channel '%s' not found.") % channelkey)
            return
        if not channel.has_connection(caller):
            string = _("You are not connected to channel '%s'.")
            self.msg(string % channelkey)
            return
        if not channel.access(caller, "send"):
            string = _("You are not permitted to send to channel '%s'.")
            self.msg(string % channelkey)
            return
        if msg == "on":
            caller = caller if not hasattr(caller, "account") else caller.account
            unmuted = channel.unmute(caller)
            if unmuted:
                self.msg("You start listening to %s." % channel)
                return
            self.msg("You were already listening to %s." % channel)
            return
        if msg == "off":
            caller = caller if not hasattr(caller, "account") else caller.account
            muted = channel.mute(caller)
            if muted:
                self.msg("You stop listening to %s." % channel)
                return
            self.msg("You were already not listening to %s." % channel)
            return
        if self.history_start is not None:
            # Try to view history
            log_file = channel.attributes.get("log_file", default="channel_%s.log" % channel.key)

            def send_msg(lines):
                return self.msg(
                    "".join(line.split("[-]", 1)[1] if "[-]" in line else line for line in lines)
                )

            tail_log_file(log_file, self.history_start, 20, callback=send_msg)
        else:
            caller = caller if not hasattr(caller, "account") else caller.account
            if caller in channel.mutelist:
                self.msg("You currently have %s muted." % channel)
                return
            channel.msg(msg, senders=self.caller, online=True)

    def get_extra_info(self, caller, **kwargs):
        """
        Let users know that this command is for communicating on a channel.

        Args:
            caller (TypedObject): A Character or Account who has entered an ambiguous command.

        Returns:
            A string with identifying information to disambiguate the object, conventionally with a preceding space.
        """
        return _(" (channel)")


class ChannelHandler(object):
    """
    The ChannelHandler manages all active in-game channels and
    dynamically creates channel commands for users so that they can
    just give the channel's key or alias to write to it. Whenever a
    new channel is created in the database, the update() method on
    this handler must be called to sync it with the database (this is
    done automatically if creating the channel with
    evennia.create_channel())

    """

    def __init__(self):
        """
        Initializes the channel handler's internal state.

        """
        self._cached_channel_cmds = {}
        self._cached_cmdsets = {}
        self._cached_channels = {}

    def __str__(self):
        """
        Returns the string representation of the handler

        """
        return ", ".join(str(cmd) for cmd in self._cached_channel_cmds)

    def clear(self):
        """
        Reset the cache storage.

        """
        self._cached_channel_cmds = {}
        self._cached_cmdsets = {}
        self._cached_channels = {}

    def add(self, channel):
        """
        Add an individual channel to the handler. This is called
        whenever a new channel is created.

        Args:
            channel (Channel): The channel to add.

        Notes:
            To remove a channel, simply delete the channel object and
            run self.update on the handler. This should usually be
            handled automatically by one of the deletion methos of
            the Channel itself.

        """
        global _CHANNEL_COMMAND_CLASS
        if not _CHANNEL_COMMAND_CLASS:
            _CHANNEL_COMMAND_CLASS = class_from_module(settings.CHANNEL_COMMAND_CLASS)

        # map the channel to a searchable command
        cmd = _CHANNEL_COMMAND_CLASS(
            key=channel.key.strip().lower(),
            aliases=channel.aliases.all(),
            locks="cmd:all();%s" % channel.locks,
            help_category="Channel names",
            obj=channel,
            is_channel=True,
        )
        # format the help entry
        key = channel.key
        cmd.__doc__ = cmd.__doc__.format(
            channelkey=key,
            lower_channelkey=key.strip().lower(),
            channeldesc=channel.attributes.get("desc", default="").strip(),
        )
        self._cached_channel_cmds[channel] = cmd
        self._cached_channels[key] = channel
        self._cached_cmdsets = {}

    add_channel = add  # legacy alias

    def remove(self, channel):
        """
        Remove channel from channelhandler. This will also delete it.

        Args:
            channel (Channel): Channel to remove/delete.

        """
        if channel.pk:
            channel.delete()
        self.update()

    def update(self):
        """
        Updates the handler completely, including removing old removed
        Channel objects. This must be called after deleting a Channel.

        """
        global _CHANNELDB
        if not _CHANNELDB:
            from evennia.comms.models import ChannelDB as _CHANNELDB
        self._cached_channel_cmds = {}
        self._cached_cmdsets = {}
        self._cached_channels = {}
        for channel in _CHANNELDB.objects.get_all_channels():
            self.add(channel)

    def get(self, channelname=None):
        """
        Get a channel from the handler, or all channels

        Args:
            channelame (str, optional): Channel key, case insensitive.
        Returns
            channels (list): The matching channels in a list, or all
                channels in the handler.

        """
        if channelname:
            channel = self._cached_channels.get(channelname.lower(), None)
            return [channel] if channel else []
        return list(self._cached_channels.values())

    def get_cmdset(self, source_object):
        """
        Retrieve cmdset for channels this source_object has
        access to send to.

        Args:
            source_object (Object): An object subscribing to one
                or more channels.

        Returns:
            cmdsets (list): The Channel-Cmdsets `source_object` has
                access to.

        """
        if source_object in self._cached_cmdsets:
            return self._cached_cmdsets[source_object]
        else:
            # create a new cmdset holding all viable channels
            chan_cmdset = None
            chan_cmds = [
                channelcmd
                for channel, channelcmd in self._cached_channel_cmds.items()
                if channel.subscriptions.has(source_object)
                and channelcmd.access(source_object, "send")
            ]
            if chan_cmds:
                chan_cmdset = cmdset.CmdSet()
                chan_cmdset.key = "ChannelCmdSet"
                chan_cmdset.priority = 101
                chan_cmdset.duplicates = True
                for cmd in chan_cmds:
                    chan_cmdset.add(cmd)
            self._cached_cmdsets[source_object] = chan_cmdset
            return chan_cmdset


CHANNEL_HANDLER = ChannelHandler()
CHANNELHANDLER = CHANNEL_HANDLER  # legacy
