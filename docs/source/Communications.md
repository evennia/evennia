# Communications


Apart from moving around in the game world and talking, players might need other forms of communication. This is offered by Evennia's `Comm` system. Stock evennia implements a 'MUX-like' system of channels, but there is nothing stopping you from changing things to better suit your taste. 

Comms rely on two main database objects - `Msg` and `Channel`. There is also the `TempMsg` which mimics the API of a `Msg` but has no connection to the database.

## Msg

The `Msg` object is the basic unit of communication in Evennia. A message works a little like an e-mail; it always has a sender (a [Account](./Accounts)) and one or more recipients. The recipients may be either other Accounts, or a *Channel* (see below). You can mix recipients to send the message to both Channels and Accounts if you like.

Once created, a `Msg` is normally not changed. It is peristently saved in the database. This allows for comprehensive logging of communications. This could be useful for allowing senders/receivers to have 'mailboxes' with the messages they want to keep. 

### Properties defined on `Msg`

- `senders` - this is a reference to one or many [Account](./Accounts) or [Objects](./Objects) (normally *Characters*) sending the message.  This could also be an *External Connection* such as a message coming in over IRC/IMC2 (see below). There is usually only one sender, but the types can also be mixed in any combination.
- `receivers` - a list of target [Accounts](./Accounts), [Objects](./Objects) (usually *Characters*) or *Channels* to send the message to. The types of receivers can be mixed in any combination.
- `header` - this is a text field for storing a title or header for the message. 
- `message` - the actual text being sent.
- `date_sent` - when message was sent (auto-created).
- `locks` - a [lock definition](./Locks).
- `hide_from` - this can optionally hold a list of objects, accounts or channels to hide this `Msg` from. This relationship is stored in the database primarily for optimization reasons, allowing for quickly post-filter out messages not intended for a given target.  There is no in-game methods for setting this, it's intended to be done in code.

You create new messages in code using `evennia.create_message` (or `evennia.utils.create.create_message.`) 

## TempMsg

`evennia.comms.models` also has `TempMsg` which mimics the API of `Msg` but is not connected to the database. TempMsgs are used by Evennia for channel messages by default. They can be used for any system expecting a `Msg` but when you don't actually want to save anything. 

## Channels

Channels are [Typeclassed](./Typeclasses) entities, which mean they can be easily extended and their functionality modified. To change which channel typeclass Evennia uses, change settings.BASE_CHANNEL_TYPECLASS.

Channels act as generic distributors of messages. Think of them as "switch boards" redistributing `Msg` or `TempMsg` objects. Internally they hold a list of "listening" objects and any `Msg` (or `TempMsg`) sent to the channel will be distributed out to all channel listeners. Channels have [Locks](./Locks) to limit who may listen and/or send messages through them. 

The *sending* of text to a channel is handled by a dynamically created [Command](./Commands) that always have the same name as the channel. This is created for each channel by the global `ChannelHandler`. The Channel command is added to the Account's cmdset and normal command locks are used to determine which channels are possible to write to. When subscribing to a channel, you can then just write the channel name and the text to send. 

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
- `locks` - A [lock definition](./Locks). Channels normally use the access_types `send, control` and `listen`.