# Msg

The `Msg` object is the basic unit of communication in Evennia. A message works a little like an e-mail; it always has a sender (a [Account](../accounts/Accounts)) and one or more recipients. The recipients may be either other Accounts, or a *Channel* (see below). You can mix recipients to send the message to both Channels and Accounts if you like.

Once created, a `Msg` is normally not changed. It is peristently saved in the database. This allows for comprehensive logging of communications. This could be useful for allowing senders/receivers to have 'mailboxes' with the messages they want to keep. 

### Properties defined on `Msg`

- `senders` - this is a reference to one or many [Account](../accounts/Accounts) or [Objects](../objects/Objects) (normally *Characters*) sending the message.  This could also be an *External Connection* such as a message coming in over IRC/IMC2 (see below). There is usually only one sender, but the types can also be mixed in any combination.
- `receivers` - a list of target [Accounts](../accounts/Accounts), [Objects](../objects/Objects) (usually *Characters*) or *Channels* to send the message to. The types of receivers can be mixed in any combination.
- `header` - this is a text field for storing a title or header for the message. 
- `message` - the actual text being sent.
- `date_sent` - when message was sent (auto-created).
- `locks` - a [lock definition](../locks/Locks).
- `hide_from` - this can optionally hold a list of objects, accounts or channels to hide this `Msg` from. This relationship is stored in the database primarily for optimization reasons, allowing for quickly post-filter out messages not intended for a given target.  There is no in-game methods for setting this, it's intended to be done in code.

You create new messages in code using `evennia.create_message` (or `evennia.utils.create.create_message.`) 

## TempMsg

`evennia.comms.models` also has `TempMsg` which mimics the API of `Msg` but is not connected to the database. TempMsgs are used by Evennia for channel messages by default. They can be used for any system expecting a `Msg` but when you don't actually want to save anything. 