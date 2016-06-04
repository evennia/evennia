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
from builtins import object

from django.conf import settings
from evennia.comms.models import ChannelDB
from evennia.commands import cmdset, command
from evennia.utils.logger import tail_log_file
from evennia.utils.utils import class_from_module
from django.utils.translation import ugettext as _

_CHANNEL_COMMAND_CLASS = None

class ChannelCommand(command.Command):
    """
    {channelkey} channel

    {channeldesc}

    Usage:
       {lower_channelkey}  <message>
       {lower_channelkey}/history [start]

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
                pass
        self.args = (channelname.strip(), msg.strip())

    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        channelkey, msg = self.args
        caller = self.caller
        if not msg:
            self.msg(_("Say what?"))
            return
        channel = ChannelDB.objects.get_channel(channelkey)

        if not channel:
            self.msg(_("Channel '%s' not found.") % channelkey)
            return
        if not channel.has_connection(caller):
            string = _("You are not connected to channel '%s'.")
            self.msg(string % channelkey)
            return
        if not channel.access(caller, 'send'):
            string = _("You are not permitted to send to channel '%s'.")
            self.msg(string % channelkey)
            return
        if self.history_start is not None:
            # Try to view history
            log_file = channel.attributes.get("log_file", default="channel_%s.log" % channel.key)
            send_msg = lambda lines: self.msg("".join(line.split("[-]", 1)[1]
                                                    if "[-]" in line else line for line in lines))
            tail_log_file(log_file, self.history_start, 20, callback=send_msg)
        else:
            channel.msg(msg, senders=self.caller, online=True)

    def get_extra_info(self, caller, **kwargs):
        """
        Let users know that this command is for communicating on a channel.

        Args:
            caller (TypedObject): A Character or Player who has entered an ambiguous command.

        Returns:
            A string with identifying information to disambiguate the object, conventionally with a preceding space.
        """
        return _(" (channel)")


class ChannelHandler(object):
    """
    The ChannelHandler manages all active in-game channels and
    dynamically creates channel commands for users so that they can
    just give the channek's key or alias to write to it. Whenever a
    new channel is created in the database, the update() method on
    this handler must be called to sync it with the database (this is
    done automatically if creating the channel with
    evennia.create_channel())

    """
    def __init__(self):
        """
        Initializes the channel handler's internal state.

        """
        self.cached_channel_cmds = []
        self.cached_cmdsets = {}

    def __str__(self):
        """
        Returns the string representation of the handler

        """
        return ", ".join(str(cmd) for cmd in self.cached_channel_cmds)

    def clear(self):
        """
        Reset the cache storage.

        """
        self.cached_channel_cmds = []

    def add_channel(self, channel):
        """
        Add an individual channel to the handler. This should be
        called whenever a new channel is created.

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
                             arg_regex=r"\s.*?|/history.*?",
                             is_channel=True)
        # format the help entry
        key = channel.key
        cmd.__doc__ = cmd.__doc__.format(channelkey=key,
                                         lower_channelkey=key.strip().lower(),
                                         channeldesc=channel.attributes.get("desc", default="").strip())
        self.cached_channel_cmds.append(cmd)
        self.cached_cmdsets = {}

    def update(self):
        """
        Updates the handler completely, including removing old removed
        Channel objects. This must be called after deleting a Channel.

        """
        self.cached_channel_cmds = []
        self.cached_cmdsets = {}
        for channel in ChannelDB.objects.get_all_channels():
            self.add_channel(channel)

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
        if source_object in self.cached_cmdsets:
            return self.cached_cmdsets[source_object]
        else:
            # create a new cmdset holding all channels
            chan_cmdset = cmdset.CmdSet()
            chan_cmdset.key = '_channelset'
            chan_cmdset.priority = 120
            chan_cmdset.duplicates = True
            for cmd in [cmd for cmd in self.cached_channel_cmds
                        if cmd.access(source_object, 'send')]:
                chan_cmdset.add(cmd)
            self.cached_cmdsets[source_object] = chan_cmdset
            return chan_cmdset

CHANNEL_HANDLER = ChannelHandler()
CHANNELHANDLER = CHANNEL_HANDLER # legacy
