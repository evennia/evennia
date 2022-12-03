# Channels

In a multiplayer game, players often need other means of in-game communication
than moving to the same room and use `say` or `emote`.

_Channels_ allows Evennia's to act as a fancy chat program. When a player is
connected to a channel, sending a message to it will automatically distribute
it to every other subscriber.

Channels can be used both for chats between [Accounts](./Accounts.md) and between
[Objects](./Objects.md) (usually Characters).  Chats could be both OOC
(out-of-character) or IC (in-charcter) in nature.  Some examples:

- A support channel for contacting staff (OOC)
- A general chat for discussing anything and foster community (OOC)
- Admin channel for private staff discussions (OOC)
- Private guild channels for planning and organization (IC/OOC depending on game)
- Cyberpunk-style retro chat rooms (IC)
- In-game radio channels (IC)
- Group telephathy (IC)
- Walkie talkies (IC)

```{versionchanged} 1.0

  Channel system changed to use a central 'channel' command and nicks instead of
  auto-generated channel-commands and -cmdset. ChannelHandler was removed.

```

## Working with channels

### Viewing and joining channels

In the default command set, channels are all handled via the mighty [channel command](evennia.commands.default.comms.CmdChannel), `channel` (or `chan`).  By default, this command will assume all entities dealing with channels are `Accounts`.

Viewing channels

    channel       - shows your subscriptions
    channel/all   - shows all subs available to you
    channel/who   - shows who subscribes to this channel

To join/unsub a channel do

    channel/sub channelname
    channel/unsub channelname

If you temporarily don't want to hear the channel for a while (without actually
unsubscribing), you can mute it:

    channel/mute channelname
    channel/unmute channelname

### Talk on channels

To speak on a channel, do

    channel public Hello world!

If the channel-name has spaces in it, you need to use a '`=`':

    channel rest room = Hello world!

Now, this is more to type than we'd like, so when you join a channel, the
system automatically sets up an personal alias so you can do this instead:

    public Hello world

```{warning}

  This shortcut will not work if the channel-name has spaces in it.
  So channels with long names should make sure to provide a one-word alias as
  well.
```

Any user can make up their own channel aliases:

    channel/alias public = foo;bar

You can now just do

    foo Hello world!
    bar Hello again!

And even remove the default one if they don't want to use it

    channel/unalias public
    public Hello    (gives a command-not-found error now)

But you can also use your alias with the `channel` command:

    channel foo Hello world!

> What happens when aliasing is that a [nick](./Nicks.md) is created that maps your
> alias + argument onto calling the `channel` command. So when you enter `foo hello`,
> what the server sees is actually `channel foo = hello`. The system is also
> clever enough to know that whenever you search for channels, your channel-nicks
> should also be considered so as to convert your input to an existing channel name.

You can check if you missed channel conversations by viewing the channel's
scrollback with

    channel/history public

This retrieves the last 20 lines of text (also from a time when you were
offline). You can step further back by specifying how many lines back to start:

    channel/history public = 30

This again retrieve 20 lines, but starting 30 lines back (so you'll get lines
30-50 counting backwards).


### Channel administration

To create/destroy a new channel you can do

    channel/create channelname;alias;alias = description
    channel/destroy channelname

Aliases are optional but can be good for obvious shortcuts everyone may want to
use. The description is used in channel-listings. You will automatically join a
channel you created and will be controlling it. You can also use `channel/desc` to
change the description on a channel you wnn later.

If you control a channel you can also kick people off it:

    channel/boot mychannel = annoyinguser123 : stop spamming!

The last part is an optional reason to send to the user before they are booted.
You can give a comma-separated list of channels to kick the same user from all
those channels at once. The user will be unsubbed from the channel and all
their aliases will be wiped. But they can still rejoin if they like.

    channel/ban mychannel = annoyinguser123
    channel/ban      - view bans
    channel/unban mychannel = annoyinguser123

Banning adds the user to the channels blacklist. This means they will not be
able to _rejoin_ if you boot them. You will need to run `channel/boot` to
actually kick them out.

See the [Channel command](evennia.commands.default.comms.CmdChannel) api docs (and in-game help) for more details.

Admin-level users can also modify channel's [locks](./Locks.md):

    channel/lock buildchannel = listen:all();send:perm(Builders)

Channels use three lock-types by default:

- `listen` - who may listen to the channel. Users without this access will not
  even be able to join the channel and it will not appear in listings for them.
- `send` - who may send to the channel.
- `control` - this is assigned to you automatically when you create the channel. With
  control over the channel you can edit it, boot users and do other management tasks.


#### Restricting channel administration

By default everyone can use the channel command ([evennia.commands.default.comms.CmdChannel](evennia.commands.default.comms.CmdChannel)) to create channels and will then control the channels they created (to boot/ban people etc). If you as a developer does not want regular players to do this (perhaps you want only staff to be able to spawn new channels), you can override the `channel` command and change its `locks` property. 

The default `help` command has the following `locks` property:

```python
    locks = "cmd:not perm(channel_banned); admin:all(); manage:all(); changelocks: perm(Admin)"
```

This is a regular [lockstring](./Locks.md).

- `cmd: pperm(channel_banned)` - The `cmd` locktype is the standard one used for all Commands.
  an accessing object failing this will not even know that the command exists. The `pperm()` lockfunc
  checks an on-account [Permission](Building Permissions) 'channel_banned' - and the `not` means
  that if they _have_ that 'permission' they are cut off from using the `channel` command. You usually
  don't need to change this lock.
- `admin:all()` - this is a lock checked in the `channel` command itself. It controls access to the
  `/boot`, `/ban` and `/unban` switches (by default letting everyone use them).
- `manage:all()` - this controls access to the `/create`, `/destroy`, `/desc` switches.
- `changelocks: perm(Admin)` - this controls access to the `/lock` and `/unlock` switches. By
  default this is something only [Admins](Building Permissions) can change.

> Note - while `admin:all()` and `manage:all()` will let everyone use these switches, users
> will still only be able to admin or destroy channels they actually control!

If you only want (say) Builders and higher to be able to create and admin
channels you could override the `help` command and change the lockstring to:

```python
  # in for example mygame/commands/commands.py

  from evennia import default_cmds

  class MyCustomChannelCmd(default_cmds.CmdChannel):
      locks = "cmd: not pperm(channel_banned);admin:perm(Builder);manage:perm(Builder);changelocks:perm(Admin)"

```

Add this custom command to your default cmdset and regular users wil now get an
access-denied error when trying to use use these switches.

## Using channels in code

For most common changes, the default channel, the recipient hooks and possibly
overriding the `channel` command will get you very far. But you can also tweak
channels themselves.

### Allowing Characters to use Channels

The default `channel` command ([evennia.commands.default.comms.CmdChannel](evennia.commands.default.comms.CmdChannel)) sits in the `Account` [command set](./Command-Sets.md). It is set up such that it will always operate on `Accounts`, even if you were to add it to the `CharacterCmdSet`.

It's a one-line change to make this command accept non-account callers. But for convenience we provide a version for Characters/Objects. Just import [evennia.commands.default.comms.CmdObjectChannel](evennia.commands.default.comms.CmdObjectChannel) and inherit from that instead.

### Customizing channel output and behavior

When distributing a message, the channel will call a series of hooks on itself
and (more importantly) on each recipient. So you can customize things a lot by
just modifying hooks on your normal Object/Account typeclasses.

Internally, the message is sent with
`channel.msg(message, senders=sender, bypass_mute=False, **kwargs)`, where
`bypass_mute=True` means the message ignores muting (good for alerts or if you
delete the channel etc) and `**kwargs` are any extra info you may want to pass
to the hooks. The `senders` (it's always only one in the default implementation
but could in principle be multiple) and `bypass_mute` are part of the `kwargs`
below:

  1. `channel.at_pre_msg(message, **kwargs)`
  2. For each recipient:
      - `message = recipient.at_pre_channel_msg(message, channel, **kwargs)` -
         allows for the message to be tweaked per-receiver (for example coloring it depending
         on the users' preferences). If this method returns `False/None`, that
         recipient is skipped.
      - `recipient.channel_msg(message, channel, **kwargs)` - actually sends to recipient.
      - `recipient.at_post_channel_msg(message, channel, **kwargs)` - any post-receive effects.
  3. `channel.at_post_channel_msg(message, **kwargs)`

Note that `Accounts` and `Objects` both have their have separate sets of hooks.
So make sure you modify the set actually used by your subcribers (or both).
Default channels all use `Account` subscribers.

### Channel class

Channels are [Typeclassed](./Typeclasses.md) entities. This means they are persistent in the database, can have [attributes](./Attributes.md) and [Tags](./Tags.md) and can be easily extended. 

To change which channel typeclass Evennia uses for default commands, change `settings.BASE_CHANNEL_TYPECLASS`. The base command class is [`evennia.comms.comms.DefaultChannel`](evennia.comms.comms.DefaultChannel). There is an empty child class in `mygame/typeclasses/channels.py`, same as for other typelass-bases.

In code you create a new channel with `evennia.create_channel` or
`Channel.create`:

```python
  from evennia import create_channel, search_object
  from typeclasses.channels import Channel

  channel = create_channel("my channel", aliases=["mychan"], locks=..., typeclass=...)
  # alternative
  channel = Channel.create("my channel", aliases=["mychan"], locks=...)

  # connect to it
  me = search_object(key="Foo")[0]
  channel.connect(me)

  # send to it (this will trigger the channel_msg hooks described earlier)
  channel.msg("Hello world!", senders=me)

  # view subscriptions (the SubscriptionHandler handles all subs under the hood)
  channel.subscriptions.has(me)    # check we subbed
  channel.subscriptions.all()      # get all subs
  channel.subscriptions.online()   # get only subs currently online
  channel.subscriptions.clear()    # unsub all

  # leave channel
  channel.disconnect(me)

  # permanently delete channel (will unsub everyone)
  channel.delete()

```

The Channel's `.connect` method will accept both `Account` and `Object` subscribers
and will handle them transparently.

The channel has many more hooks, both hooks shared with all typeclasses as well as special ones related to muting/banning etc. See the channel class for
details.

### Channel logging

```{versionchanged} 0.7

  Channels changed from using Msg to TmpMsg and optional log files.
```
```{versionchanged} 1.0

  Channels stopped supporting Msg and TmpMsg, using only log files.
```

The channel messages are not stored in the database. A channel is instead always logged to a regular text log-file `mygame/server/logs/channel_<channelname>.log`. This is where `channels/history channelname` gets its data from. A channel's log will rotate when it grows too big, which thus also automatically limits the max amount of history a user can view with
`/history`.

The log file name is set on the channel class as the `log_file` property. This
is a string that takes the formatting token `{channelname}` to be replaced with
the (lower-case) name of the channel. By default the log is written to in the
channel's `at_post_channel_msg` method.

### Properties on Channels

Channels have all the standard properties of a Typeclassed entity (`key`,
`aliases`, `attributes`, `tags`, `locks` etc). This is not an exhaustive list;
see the [Channel api docs](evennia.comms.comms.DefaultChannel) for details.

- `send_to_online_only` - this class boolean defaults to `True` and is a
  sensible optimization since people offline people will not see the message anyway.
- `log_file` - this is a string that determines the name of the channel log file. Default
  is `"channel_{channelname}.log"`. The log file will appear in `settings.LOG_DIR` (usually
  `mygame/server/logs/`). You should usually not change this.
- `channel_prefix_string` - this property is a string to easily change how
  the channel is prefixed. It takes the `channelname` format key. Default is `"[{channelname}] "`
  and produces output like `[public] ...`.
- `subscriptions` - this is the [SubscriptionHandler](evennia.comms.models.SubscriptionHandler), which
  has methods `has`, `add`, `remove`, `all`, `clear` and also `online` (to get
  only actually online channel-members).
- `wholist`, `mutelist`, `banlist` are properties that return a list of subscribers,
  as well as who are currently muted or banned.
- `channel_msg_nick_pattern` - this is a regex pattern for performing the in-place nick
  replacement (detect that `channelalias <msg` means that you want to send a message to a channel).
  This pattern accepts an `{alias}` formatting marker. Don't mess with this unless you really
  want to change how channels work.
- `channel_msg_nick_replacement` - this is a string on the [nick replacement
- form](./Nicks.md). It accepts the `{channelname}` formatting tag. This is strongly tied to the
  `channel` command and is by default `channel {channelname} = $1`.

Notable `Channel` hooks:

- `at_pre_channel_msg(message, **kwargs)` - called before sending a message, to
  modify it. Not used by default.
- `msg(message, senders=..., bypass_mute=False, **kwargs)` - send the message onto
  the channel. The `**kwargs` are passed on into the other call hooks (also on the recipient).
- `at_post_channel_msg(message, **kwargs)` - by default this is used to store the message
  to the log file.
- `channel_prefix(message)` - this is called to allow the channel to prefix. This is called
  by the object/account when they build the message, so if wanting something else one can
  also just remove that call.
- every channel message. By default it just returns `channel_prefix_string`.
- `has_connection(subscriber)` - shortcut to check if an entity subscribes to
  this channel.
- `mute/unmute(subscriber)` - this mutes the channel for this user.
- `ban/unban(subscriber)` - adds/remove user from banlist.
- `connect/disconnect(subscriber)` - adds/removes a subscriber.
- `add_user_channel_alias(user, alias, **kwargs)` - sets up a user-nick for this channel. This is
  what maps e.g. `alias <msg>` to `channel channelname = <msg>`.
- `remove_user_channel_alias(user, alias, **kwargs)` - remove an alias. Note that this is
  a class-method that will happily remove found channel-aliases from the user linked to _any_
  channel, not only from the channel the method is called on.
- `pre_join_channel(subscriber)` - if this returns `False`, connection will be refused.
- `post_join_channel(subscriber)` - by default this sets up a users's channel-nicks/aliases.
- `pre_leave_channel(subscriber)` - if this returns `False`, the user is not allowed to leave.
- `post_leave_channel(subscriber)` - this will clean up any channel aliases/nicks of the user.
- `delete` the standard typeclass-delete mechanism will also automatically un-subscribe all
  subscribers (and thus wipe all their aliases).

