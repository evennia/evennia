# Channels 

In a multiplayer game, players often need other means of in-game communication
than just walking from room to room using `say` or `emote`.

_Channels_ are Evennia's system for letting the server act as a fancy chat
program. When a player is connected to a channel, sending a message to it will
automatically distribute it to every other subscriber.

Channels can be used both for chats between [Accounts](./Accounts) and between
[Objects](./Objects) (usually Characters) and (in principle) a mix of the two.
Chats could be both OOC (out-of-character) or IC (in-charcter) in nature.  Some
examples:

- A support channel for contacting staff (OOC)
- A general chat for discussing anything and foster community (OOC)
- Admin channel for private staff discussions (OOC)
- Private guild channels for planning and organization (IC/OOC depending on game)
- Cyberpunk-style retro chat rooms (IC)
- In-game radio channels (IC)
- Group telephathy (IC)
- Walkie talkies (IC)

```versionchanged:: 1.0

  Channel system changed to use a central 'channel' command and nicks instead of
  auto-generated channel-commands and -cmdset. ChannelHandler was removed.

```

## Using channels in-game

In the default command set, channels are all handled via the mighty
[channel command](api:evennia.commands.default.comms.CmdChannel), `channel` (or
`chan`).  By default, this command will assume all entities dealing with
channels are `Accounts`.

### Viewing, joining and creating channels

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

To create/destroy a new channel you can do

    channel/create channelname;alias;alias = description
    channel/destroy channelname

Aliases are optional but can be good for obvious shortcuts everyone may want to
use. The description is used in channel-listings. You will automatically join a
channel you created and will be controlling it.

### Chat on channels

To speak on a channel, do 

    channel public Hello world!

If the channel-name has spaces in it, you need to use a '`=`':

    channel rest room = Hello world!

Now, this is more to type than we'd like, so when you join a channel, the
system automatically sets up an personal alias so you can do this instead:

    public Hello world

```warning::

  This shortcut will not work if the channel-name has spaces in it.
  So channels with long names should make sure to provide a one-word alias as
  well.
```

Any user can make up their own channel aliases:

    channel/alias public = foo;bar

You can now just do 

    foo Hello world!
    bar Hello again!

But you can also use your alias with the `channel` command:
  
    channel foo Hello world!

> What happens when aliasing is that a [nick](./Nicks) is created that maps your
> alias + argument onto calling the `channel` command. So when you enter `foo hello`,
> what the server sees is actually `channel foo = hello`. The system is also 
> clever enough to know that whenever you search for channels, your channel-nicks
> should first be considered.

You can check if you missed something by viewing the channel's scrollback with

    channel/history public 

This retrieves the last 20 lines of text (also from a time when you were
offline). You can step further back by specifying how many lines back to start:

    channel/history public = 30

This again retrieve 20 lines, but starting 30 lines back (so you'll get lines
30-50 counting backwards).


### Channel administration

If you control the channel (because you are an admin or created it) you have the 
ability to control who can access it by use of [locks](./Locks):

    channel/lock buildchannel = listen:all();send:perm(Builders)

Channels use three lock-types by default:

- `listen` - who may listen to the channel. Users without this access will not
  even be able to join the channel and it will not appear in listings for them.
- `send` - who may send to the channel.
- `control` - this is assigned to you automatically when you create the channel. With
  control over the channel you can edit it, boot users and do other management tasks.

If you control a channel you can also kick people off it:

    channel/boot mychannel = annoyinguser123 : stop spamming!
    
The last part is an optional reason to send to the user before they are booted.
You can give a comma-separated list of channels to kick the same user from all
those channels at once. The user will be unsubbed from the channel and all
their aliases will be wiped. But they can still rejoin if they like.

    channel/ban mychannel = annoyinguser123 : spammed too much
    channel/ban      - view bans
    channel/unban mychannel = annoyinguser123

The optional reason at the end shows in the banlist
Banning adds the user to the channels blacklist. This means they will not be
able to rejoin if you boot them. You will need to run `channel/boot` to
actually kick them.

See the [Channel command](api:evennia.commands.default.comms.CmdChannel) api
docs (and in-game help) for more details.


## Allowing Characters to use Channels

The default `channel` command ([evennia.commands.default.comms.CmdChannel](api:evennia.commands.default.comms.CmdChannel))
sits in the `Account` [command set](./Command-Sets). It is set up such that it will
always operate on `Accounts`, even if you were to add it to the
`CharacterCmdSet`.

It's a one-line change to make this command accept non-account callers. But for
convenience we provide a version for Characters/Objects. Just import
[evennia.commands.default.comms.CmdObjectChannel](api:evennia.commands.default.comms.CmdObjectChannel)
and inherit from that instead.

## Customizing channel output and behavior

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

## Channels in code

For most common changes, the default channel, the recipient hooks and possibly
overriding the `channel` command will get you very far. But you can also tweak
channels themselves.

Channels are [Typeclassed](./Typeclasses) entities. This means they are
persistent in the database, can have [attributes](./Attributes) and [Tags](./Tags)
and can be easily extended.

To change which channel typeclass Evennia uses for default commands, change
`settings.BASE_CHANNEL_TYPECLASS`. The base command class is
[`evennia.comms.comms.DefaultChannel`](api:evennia.comms.comms.DefaultChannel).
There is an empty child class in `mygame/typeclasses/channels.py`, same 
as for other typelass-bases.

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

The channel has many more hooks, both hooks shared with all typeclasses as well
as special ones related to muting/banning etc. See the channel class for
details.

## Channel logging

```versionchanged:: 0.7

  Channels changed from using Msg to TmpMsg and optional log files.
```
```versionchanged:: 1.0

  Channels stopped supporting Msg and TmpMsg, using only log files.
```

The channel messages are not stored in the database. A channel is instead
always logged to a regular text log-file
`mygame/server/logs/channel_<channelname>.log`. This is where `channels/history channelname` 
gets its data from. A channel's log will rotate when it grows too big, which
thus also automatically limits the max amount of history a user can view with
`/history`.

### Properties on Channels

Channels have all the standard properties of a Typeclassed entity (`key`,
`aliases`, `attributes`, `tags`, `locks` etc). This is not an exhaustive list;
see the [Channel api docs](api:evennia.comms.comms.DefaultChannel) for details.

- `send_to_online_only` - this class boolean defaults to `True` and is a
  sensible optimization since people offline people will not see the message anyway.
- `log_to_file` - this is a string that determines the name of the channel log file. Default
  is `"channel_{channel_key}.log"`. You should usually not change this.
- `channel_prefix_string` - this property is a string to easily change how 
  the channel is prefixed. It takes the `channel_key` format key. Default is `"[{channel_key}] "`
  and produces output like `[public] ...``.
- `subscriptions` - this is the [SubscriptionHandler](`api:evennia.comms.comms.SubscriptionHandler`), which
  has methods `has`, `add`, `remove`, `all`, `clear` and also `online` (to get
  only actually online channel-members).
- `wholist`, `mutelist`, `banlist` are properties that return a list of subscribers,
  as well as who are currently muted or banned.

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
  this channel
- `mute/unmute(subscriber)` - this mutes the channel for this user.
- `ban/unban(subscriber)` - adds/remove user from banlist.
- `connect/disconnect(subscriber)` - adds/removes a subscriber.
- `pre_join_channel(subscriber)` - if this returns `False`, connection will be refused.
- `post_join_channel(subscriber)` - unused by default.
- `pre_leave_channel(subscriber)` - if this returns `False`, the user is not allowed to leave.
- `post_leave_channel(subscriber)` - unused by default.
  
