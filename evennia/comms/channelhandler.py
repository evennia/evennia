"""
The channel handler handles the stored set of channels
and how they are represented against the cmdhandler.

If there is a channel named 'newbie', we want to be able
to just write

> newbie Hello!

For this to work, 'newbie', the name of the channel, must
be identified by the cmdhandler as a command name. The
channelhandler stores all channels as custom 'commands'
that the cmdhandler can import and look through.

Warning - channel names take precedence over command names,
so make sure to not pick clashing channel names.

Unless deleting a channel you normally don't need to bother about
the channelhandler at all - the create_channel method handles the update.

To delete a channel cleanly, delete the channel object, then call
update() on the channelhandler. Or use Channel.objects.delete() which
does this for you.

"""
from evennia.comms.models import ChannelDB
from evennia.commands import cmdset, command


class ChannelCommand(command.Command):
    """
    Channel

    Usage:
       <channel name or alias>  <message>

    This is a channel. If you have subscribed to it, you can send to
    it by entering its name or alias, followed by the text you want to
    send.
    """
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
        self.args = (channelname.strip(), msg.strip())

    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        channelkey, msg = self.args
        caller = self.caller
        if not msg:
            self.msg("Say what?")
            return
        channel = ChannelDB.objects.get_channel(channelkey)

        if not channel:
            self.msg("Channel '%s' not found." % channelkey)
            return
        if not channel.has_connection(caller):
            string = "You are not connected to channel '%s'."
            self.msg(string % channelkey)
            return
        if not channel.access(caller, 'send'):
            string = "You are not permitted to send to channel '%s'."
            self.msg(string % channelkey)
            return
        channel.msg(msg, senders=self.caller, online=True)


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
        "Returns the string representation of the handler"
        return ", ".join(str(cmd) for cmd in self.cached_channel_cmds)

    def clear(self):
        """
        Reset the cache storage.
        """
        self.cached_channel_cmds = []

    def _format_help(self, channel):
        "builds a doc string"
        key = channel.key
        aliases = channel.aliases.all()
        ustring = "%s <message>" % key.lower() + "".join(["\n           %s <message>" % alias.lower() for alias in aliases])
        desc = channel.db.desc
        string = \
        """
        Channel '%s'

        Usage (not including your personal aliases):
           %s

        %s
        """ % (key, ustring, desc)
        return string

    def add_channel(self, channel):
        """
        Add an individual channel to the handler. This should be
        called whenever a new channel is created. To
        remove a channel, simply delete the channel object
        and run self.update on the handler.
        """
        # map the channel to a searchable command
        cmd = ChannelCommand(key=channel.key.strip().lower(),
                             aliases=channel.aliases.all(),
                             locks="cmd:all();%s" % channel.locks,
                             help_category="Channel names",
                             obj=channel,
                             arg_regex=r"\s.*?",
                             is_channel=True)
        self.cached_channel_cmds.append(cmd)
        self.cached_cmdsets = {}

    def update(self):
        """
        Updates the handler completely.
        """
        self.cached_channel_cmds = []
        self.cached_cmdsets = {}
        for channel in ChannelDB.objects.get_all_channels():
            self.add_channel(channel)

    def get_cmdset(self, source_object):
        """
        Retrieve cmdset for channels this source_object has
        access to send to.
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
