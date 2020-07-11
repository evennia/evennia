# Customize channels


# Channel commands in Evennia

By default, Evennia's default channel commands are inspired by MUX. They all
begin with "c" followed by the action to perform (like "ccreate" or "cdesc").
If this default seems strange to you compared to other Evennia commands that
rely on switches, you might want to check this tutorial out.

This tutorial will also give you insight into the workings of the channel system.
So it may be useful even if you don't plan to make the exact changes shown here.

## What we will try to do

Our mission: change the default channel commands to have a different syntax.

This tutorial will do the following changes: 

- Remove all the default commands to handle channels.
- Add a `+` and `-` command to join and leave a channel.  So, assuming there is
a `public` channel on your game (most often the case), you could type `+public`
to join it and `-public` to leave it.
- Group the commands to manipulate channels under the channel name, after a
switch.  For instance, instead of writing `cdesc public = My public channel`,
  you would write `public/desc My public channel`.


> I listed removing the default Evennia commands as a first step in the
> process. Actually, we'll move it at the very bottom of the list, since we
> still want to use them, we might get it wrong and rely on Evennia commands
> for a while longer.

## A command to join, another to leave

We'll do the most simple task at first: create two commands, one to join a
channel, one to leave.

> Why not have them as switches? `public/join` and `public/leave` for instance?

For security reasons, I will hide channels to which the caller is not
connected.  It means that if the caller is not connected to the "public"
channel, he won't be able to use the "public" command.  This is somewhat
standard: if we create an administrator-only channel, we don't want players to
try (or even know) the channel command.  Again, you could design it a different
way should you want to.

First create a file named `comms.py` in your `commands` package.  It's
a rather logical place, since we'll write different commands to handle
communication.

Okay, let's add the first command to join a channel:

```python
# in commands/comms.py
from evennia.utils.search import search_channel
from commands.command import Command

class CmdConnect(Command):
    """
    Connect to a channel.
    """

    key = "+"
    help_category = "Comms"
    locks = "cmd:not pperm(channel_banned)"
    auto_help = False

    def func(self):
        """Implement the command"""
        caller = self.caller
        args = self.args
        if not args:
            self.msg("Which channel do you want to connect to?")
            return

        channelname = self.args
        channel = search_channel(channelname)
        if not channel:
            return

        # Check permissions
        if not channel.access(caller, 'listen'):
            self.msg("%s: You are not allowed to listen to this channel." % channel.key)
            return

        # If not connected to the channel, try to connect
        if not channel.has_connection(caller):
            if not channel.connect(caller):
                self.msg("%s: You are not allowed to join this channel." % channel.key)
                return
            else:
                self.msg("You now are connected to the %s channel. " % channel.key.lower())
        else:
            self.msg("You already are connected to the %s channel. " % channel.key.lower())
```

Okay, let's review this code, but if you're used to Evennia commands, it shouldn't be too strange:

1. We import `search_channel`.  This is a little helper function that we will use to search for
channels by name and aliases, found in `evennia.utils.search`.  It's just more convenient.
2. Our class `CmdConnect` contains the body of our command to join a channel.
3. Notice the key of this command is simply `"+"`.  When you enter `+something` in the game, it will
try to find a command key `+something`.  Failing that, it will look at other potential matches.
Evennia is smart enough to understand that when we type `+something`, `+` is the command key and
`something` is the command argument.  This will, of course, fail if you have a command beginning by
`+` conflicting with the `CmdConnect` key.
4. We have altered some class attributes, like `auto_help`.  If you want to know what they do and
why they have changed here, you can check the [documentation on commands](../Components/Commands).
5. In the command body, we begin by extracting the channel name.  Remember that this name should be
in the command arguments (that is, in `self.args`).  Following the same example, if a player enters
`+something`, `self.args` should contain `"something"`.  We use `search_channel` to see if this
channel exists.
6. We then check the access level of the channel, to see if the caller can listen to it (not
necessarily use it to speak, mind you, just listen to others speak, as these are two different locks
on Evennia).
7. Finally, we connect the caller if he's not already connected to the channel.  We use the
channel's `connect` method to do this.  Pretty straightforward eh?

Now we'll add a command to leave a channel.  It's almost the same, turned upside down:

```python
class CmdDisconnect(Command):
    """
    Disconnect from a channel.
    """

    key = "-"
    help_category = "Comms"
    locks = "cmd:not pperm(channel_banned)"
    auto_help = False

    def func(self):
        """Implement the command"""
        caller = self.caller
        args = self.args
        if not args:
            self.msg("Which channel do you want to disconnect from?")
            return

        channelname = self.args
        channel = search_channel(channelname)
        if not channel:
            return

        # If connected to the channel, try to disconnect
        if channel.has_connection(caller):
            if not channel.disconnect(caller):
                self.msg("%s: You are not allowed to disconnect from this channel." % channel.key)
                return
            else:
                self.msg("You stop listening to the %s channel. " % channel.key.lower())
        else:
            self.msg("You are not connected to the %s channel. " % channel.key.lower())
```

So far, you shouldn't have trouble following what this command does: it's
pretty much the same as the `CmdConnect` class in logic, though it accomplishes
the opposite.  If you are connected to the channel `public` you could
disconnect from it using `-public`.  Remember, you can use channel aliases too
(`+pub` and `-pub` will also work, assuming you have the alias `pub` on the
 `public` channel).

It's time to test this code, and to do so, you will need to add these two
commands.  Here is a good time to say it: by default, Evennia connects accounts
to channels.  Some other games (usually with a higher multisession mode)  will
want to connect characters instead of accounts, so that several characters in
the same account can be connected to various channels.  You can definitely add
these commands either in the `AccountCmdSet` or `CharacterCmdSet`, the caller
will be different and the command will add or remove accounts of characters.
If you decide to install these commands on the `CharacterCmdSet`, you might
have to disconnect your superuser account (account #1) from the channel before
joining it with your characters, as Evennia tends to subscribe all accounts
automatically if you don't tell it otherwise.

So here's an example of how to add these commands into your `AccountCmdSet`.
Edit the file `commands/default_cmdsets.py` to change a few things:

```python
# In commands/default_cmdsets.py
from evennia import default_cmds
from commands.comms import CmdConnect, CmdDisconnect


# ... Skip to the AccountCmdSet class ...

class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """
    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()

        # Channel commands
        self.add(CmdConnect())
        self.add(CmdDisconnect())
```

Save, reload your game, and you should be able to use `+public` and `-public`
now!

## A generic channel command with switches

It's time to dive a little deeper into channel processing.  What happens in
Evennia when a player enters `public Hello everybody!`?

Like exits, channels are a particular command that Evennia automatically
creates and attaches to individual channels.  So when you enter `public
message` in your game, Evennia calls the `public` command.

> But I didn't add any public command...

Evennia will just create these commands automatically based on the existing
channels. The base command is the command we'll need to edit.

> Why edit it?  It works just fine to talk.

Unfortunately, if we want to add switches to our channel names, we'll have to
edit this command.  It's not too hard, however, we'll just start writing a
standard command with minor twitches.

### Some additional imports

You'll need to add a line of import in your `commands/comms.py` file.  We'll
see why this import is important when diving in the command itself:

```python
from evennia.comms.models import ChannelDB
```

### The class layout

```python
# In commands/comms.py
class ChannelCommand(Command):
    """
    {channelkey} channel

    {channeldesc}

    Usage:
      {lower_channelkey} <message>
      {lower_channelkey}/history [start]
      {lower_channelkey}/me <message>
      {lower_channelkey}/who

    Switch:
      history: View 20 previous messages, either from the end or
          from <start> number of messages from the end.
      me: Perform an emote on this channel.
      who: View who is connected to this channel.

    Example:
      {lower_channelkey} Hello World!
      {lower_channelkey}/history
      {lower_channelkey}/history 30
      {lower_channelkey}/me grins.
      {lower_channelkey}/who
    """
    # note that channeldesc and lower_channelkey will be filled
    # automatically by ChannelHandler

    # this flag is what identifies this cmd as a channel cmd
    # and branches off to the system send-to-channel command
    # (which is customizable by admin)
    is_channel = True
    key = "general"
    help_category = "Channel Names"
    obj = None
    arg_regex = ""
```

There are some differences here compared to most common commands.

- There is something disconcerting in the class docstring.  Some information is
between curly braces.  This is a format-style which is only used for channel
commands.  `{channelkey}` will be replaced by the actual channel key (like
    public).  `{channeldesc}` will be replaced by the channel description (like
      "public channel").  And `{lower_channelkey}`.
- We have set `is_channel` to `True` in the command class variables.  You
shouldn't worry too much about that: it just tells Evennia this is a special
command just for channels.
- `key` is a bit misleading because it will be replaced eventually.  So we
could set it to virtually anything.
- The `obj` class variable is another one we won't detail right now.
- `arg_regex` is important: the default `arg_regex` in the channel command will
forbid to use switches (a slash just after the channel name is not allowed).
That's why we enforce it here, we allow any syntax.

> What will become of this command?

Well, when we'll be through with it, and once we'll add it as the default
command to handle channels, Evennia will create one per existing channel.  For
instance, the public channel will receive one command of this class, with `key`
set to `public` and `aliases` set to the channel aliases (like `['pub']`).

> Can I see it work?

Not just yet, there's still a lot of code needed.

Okay we have the command structure but it's rather empty.

### The parse method

The `parse` method is called before `func` in every command. Its job is to
parse arguments and in our case, we will analyze switches here.

```python
# ...
    def parse(self):
        """
        Simple parser
        """
        # channel-handler sends channame:msg here.
        channelname, msg = self.args.split(":", 1)
        self.switch = None
        if msg.startswith("/"):
            try:
                switch, msg = msg[1:].split(" ", 1)
            except ValueError:
                switch = msg[1:]
                msg = ""

            self.switch = switch.lower().strip()

        self.args = (channelname.strip(), msg.strip())
```

Reading the comments we see that the channel handler will send the command in a
strange way: a string with the channel name, a colon and the actual message
entered by the player.  So if the player enters "public hello", the command
`args` will contain `"public:hello"`.  You can look at the way the channel name
and message are parsed, this can be used in a lot of different commands.

Next we check if there's any switch, that is, if the message starts with a
slash.  This would be the case if a player entered `public/me jumps up and
down`, for instance.  If there is a switch, we save it in `self.switch`.  We
alter `self.args` at the end to contain a tuple with two values: the channel
name, and the message (if a switch was used, notice that the switch will be
    stored in `self.switch`, not in the second element of `self.args`).

### The command func

Finally, let's see the `func` method in the command class.  It will have to
handle switches and also the raw message to send if no switch was used.


```python
# ...
    def func(self):
        """
        Create a new message and send it to channel, using
        the already formatted input.
        """
        channelkey, msg = self.args
        caller = self.caller
        channel = ChannelDB.objects.get_channel(channelkey)

        # Check that the channel exists
        if not channel:
            self.msg(_("Channel '%s' not found.") % channelkey)
            return

        # Check that the caller is connected
        if not channel.has_connection(caller):
            string = "You are not connected to channel '%s'."
            self.msg(string % channelkey)
            return

        # Check that the caller has send access
        if not channel.access(caller, 'send'):
            string = "You are not permitted to send to channel '%s'."
            self.msg(string % channelkey)
            return

        # Handle the various switches
        if self.switch == "me":
            if not msg:
                self.msg("What do you want to do on this channel?")
            else:
                msg = "{} {}".format(caller.key, msg)
                channel.msg(msg, online=True)
        elif self.switch:
            self.msg("{}: Invalid switch {}.".format(channel.key, self.switch))
        elif not msg:
            self.msg("Say what?")
        else:
            if caller in channel.mutelist:
                self.msg("You currently have %s muted." % channel)
                return
            channel.msg(msg, senders=self.caller, online=True)
```

- First of all, we try to get the channel object from the channel name we have
in the `self.args` tuple.  We use `ChannelDB.objects.get_channel` this time
because we know the channel name isn't an alias (that was part of the deal,
    `channelname` in the `parse` method contains a command key).
- We check that the channel does exist.
- We then check that the caller is connected to the channel.  Remember, if the
caller isn't connected, we shouldn't allow him to use this command (that
    includes the switches on channels).
- We then check that the caller has access to the channel's `send` lock.  This
time, we make sure the caller can send messages to the channel, no matter what
operation he's trying to perform.
- Finally we handle switches.  We try only one switch: `me`.  This switch would
be used if a player entered `public/me jumps up and down` (to do a channel
    emote).
- We handle the case where the switch is unknown and where there's no switch
(the player simply wants to talk on this channel).

The good news: The code is not too complicated by itself. The bad news is that
this is just an abridged version of the code. If you want to handle all the
switches mentioned in the command help, you will have more code to write. This
is left as an exercise.

### End of class

It's almost done, but we need to add a method in this command class that isn't
often used. I won't detail it's usage too much, just know that Evennia will use
it and will get angry if you don't add it. So at the end of your class, just
add:

```python
# ...
    def get_extra_info(self, caller, **kwargs):
        """
        Let users know that this command is for communicating on a channel.

        Args:
            caller (TypedObject): A Character or Account who has entered an ambiguous command.

        Returns:
            A string with identifying information to disambiguate the object, conventionally with a
preceding space.
        """
        return " (channel)"
```

### Adding this channel command

Contrary to most Evennia commands, we won't add our `ChannelCommand` to a
`CmdSet`. Instead we need to tell Evennia that it should use the command we
just created instead of its default channel-command.

In your `server/conf/settings.py` file, add a new setting:

```python
# Channel options
CHANNEL_COMMAND_CLASS = "commands.comms.ChannelCommand"
```

Then you can reload your game. Try to type `public hello` and `public/me jumps
up and down`.  Don't forget to enter `help public` to see if your command has
truly been added.

## Conclusion and full code

That was some adventure!  And there's still things to do!  But hopefully, this
tutorial will have helped you in designing your own channel system.  Here are a
few things to do:

- Add more switches to handle various actions, like changing the description of
a channel for instance, or listing the connected participants.
- Remove the default Evennia commands to handle channels.
- Alter the behavior of the channel system so it better aligns with what you
want to do.

As a special bonus, you can find a full, working example of a communication
system similar to the one I've shown you: this is a working example, it
integrates all switches and does ever some extra checking, but it's also very
close from the code I've provided here.  Notice, however, that this resource is
external to Evennia and not maintained by anyone but the original author of
this article.

[Read the full example on Github](https://github.com/vincent-
lg/avenew/blob/master/commands/comms.py)