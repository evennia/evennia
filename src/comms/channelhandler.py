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
from src.comms.models import Channel, Msg
from src.commands import cmdset, command
from src.permissions.permissions import has_perm

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
    key = "general"
    help_category = "Channel Names"
    permissions = "cmd:use_channels"
    is_channel = True 
    obj = None     
    
    def parse(self):
        """
        Simple parser
        """
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
            caller.msg("Say what?")
            return 
        channel = Channel.objects.get_channel(channelkey)

        if not channel:
            caller.msg("Channel '%s' not found." % channelkey)
            return 
        if not channel.has_connection(caller):
            string = "You are not connected to channel '%s'."
            caller.msg(string % channelkey)
            return
        if not has_perm(caller, channel, 'chan_send'):
            string = "You are not permitted to send to channel '%s'."
            caller.msg(string % channelkey)
            return
        msg = "[%s] %s: %s" % (channel.key, caller.name, msg)        
        # we can't use the utils.create function to make the Msg,
        # since that creates an import recursive loop.         
        msgobj = Msg(db_sender=caller.player, db_message=msg)
        msgobj.save()
        msgobj.channels = channel
        # send new message object to channel        
        channel.msg(msgobj)

class ChannelHandler(object):
    """
    Handles the set of commands related to channels.
    """
    def __init__(self):        
        self.cached_channel_cmds = []

    def __str__(self):
        return ", ".join(str(cmd) for cmd in self.cached_channel_cmds)
    
    def clear(self):
        """
        Reset the cache storage.
        """
        self.cached_channel_cmds = []

    def add_channel(self, channel):
        """
        Add an individual channel to the handler. This should be
        called whenever a new channel is created. To
        remove a channel, simply delete the channel object
        and run self.update on the handler. 
        """
        # map the channel to a searchable command
        cmd = ChannelCommand()
        cmd.key = channel.key.strip().lower()
        cmd.obj = channel
        if channel.aliases: 
            cmd.aliases = channel.aliases
        self.cached_channel_cmds.append(cmd)

    def update(self):
        "Updates the handler completely."
        self.cached_channel_cmds = []
        for channel in Channel.objects.all():
            self.add_channel(channel)

    def get_cmdset(self, source_object):
        """
        Retrieve cmdset for channels this source_object has
        access to send to. 
        """
        # create a temporary cmdset holding all channels 
        chan_cmdset = cmdset.CmdSet()
        chan_cmdset.key = '_channelset'
        chan_cmdset.priority = 10
        chan_cmdset.duplicates = True 
        for cmd in [cmd for cmd in self.cached_channel_cmds
                    if has_perm(source_object, cmd, 'chan_send')]:
            chan_cmdset.add(cmd)
        return chan_cmdset

CHANNELHANDLER = ChannelHandler()
