# Channels

Channels are [Typeclassed](../typeclasses/Typeclasses) entities, which mean they can be easily extended and their functionality modified. To change which channel typeclass Evennia uses, change settings.BASE_CHANNEL_TYPECLASS.

Channels act as generic distributors of messages. Think of them as "switch boards" redistributing `Msg` or `TempMsg` objects. Internally they hold a list of "listening" objects and any `Msg` (or `TempMsg`) sent to the channel will be distributed out to all channel listeners. Channels have [Locks](../locks/Locks) to limit who may listen and/or send messages through them. 

The *sending* of text to a channel is handled by a dynamically created [Command](../commands/Commands) that always have the same name as the channel. This is created for each channel by the global `ChannelHandler`. The Channel command is added to the Account's cmdset and normal command locks are used to determine which channels are possible to write to. When subscribing to a channel, you can then just write the channel name and the text to send. 

The default ChannelCommand (which can be customized by pointing `settings.CHANNEL_COMMAND_CLASS` to your own command), implements a few convenient features: 

 - It only sends `TempMsg` objects. Instead of storing individual entries in the database it instead dumps channel output a file log in `server/logs/channel_<channelname>.log`. This is mainly for practical reasons - we find one rarely need to query individual Msg objects at a later date. Just stupidly dumping the log to a file also means a lot less database overhead. 

 - It adds a `/history` switch to view the 20 last messages in the channel. These are read from the end of the log file. One can also supply a line number to start further back in the file (but always 20 entries at a time). It's used like this: 

      > public/history 
      > public/history 35


There are two default channels created in stock Evennia - `MudInfo` and `Public`.  `MudInfo` receives server-related messages meant for Admins whereas `Public`  is open to everyone to chat on (all new accounts are automatically joined to it when logging in, it is useful for asking questions). The default channels are defined by the `DEFAULT_CHANNELS` list (see `evennia/settings_default.py` for more details).

You create new channels with `evennia.create_channel` (or `evennia.utils.create.create_channel`).

In code, messages are sent to a channel using the `msg` or `tempmsg` methods of channels: 

     channel.msg(msgobj, header=None, senders=None, persistent=True)

The argument `msgobj` can be either a string, a previously constructed `Msg` or a `TempMsg` - in the latter cases all the following keywords are ignored since the message objects already contains all this information. If `msgobj` is a string, the other keywords are used for creating a new `Msg` or `TempMsg` on the fly, depending on if `persistent` is set or not. By default, a `TempMsg` is emitted for channel communication (since the default ChannelCommand instead logs to a file). 

```python
    # assume we have a 'sender' object and a channel named 'mychan'

    # manually sending a message to a channel
    mychan.msg("Hello!", senders=[sender])
```

### Properties defined on `Channel`

- `key` - main name for channel
- `aliases` - alternative native names for channels
- `desc` - optional description of channel (seen in listings)
- `keep_log` (bool) - if the channel should store messages (default)
- `locks` - A [lock definition](../locks/Locks). Channels normally use the access_types `send, control` and `listen`.