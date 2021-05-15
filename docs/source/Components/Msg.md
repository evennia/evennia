# Msg

The [Msg](api:evennia.comms.models.Msg) object represents a database-saved
piece of communication. Think of it as a discrete piece of email - it contains
a message, some metadata and will always have a sender and one or more
recipients.

Once created, a Msg is normally not changed. It is persitently saved in the
database. This allows for comprehensive logging of communications. Here are some
good uses for `Msg` objects:

- page/tells (the `page` command is how Evennia uses them out of the box)
- messages in a bulletin board
- game-wide email stored in 'mailboxes'.


```important::

  A `Msg` does not have any in-game representation. So if you want to use them
  to represent in-game mail/letters, the physical letters would never be
  visible in a room (possible to steal, spy on etc) unless you make your
  spy-system access the Msgs directly (or go to the trouble of spawning an
  actual in-game letter-object based on the Msg)


```

```versionchanged:: 1.0
  Channels dropped Msg-support. Now only used in `page` command by default.
```

## Msg in code

The Msg is intended to be used exclusively in code, to build other game systems. It is _not_
a [Typeclassed](./Typeclasses) entity, which means it cannot (easily) be overridden. It
doesn't support Attributes (but it _does_ support [Tags](./Tags)). It tries to be lean
and small since a new one is created for every message.

You create a new message with `evennia.create_message`:

```python
    from evennia import create_message
    message = create_message(senders, message, receivers,
                             locks=..., tags=..., header=...)
```

You can search for `Msg` objects in various ways:


```python
  from evennia import search_message, Msg

  # args are optional. Only a single sender/receiver should be passed
  messages = search_message(sender=..., receiver=..., freetext=..., dbref=...)

  # get all messages for a given sender/receiver
  messages = Msg.objects.get_msg_by_sender(sender)
  messages = Msg.objects.get_msg_by_receiver(recipient)

```

### Properties on Msg

- `senders` - there must always be at least one sender. This is a set of
- [Account](./Accounts), [Object](./Objects), [Script](./Scripts)
  or `str` in any combination (but usually a message only targets one type).
  Using a `str` for a sender indicates it's an 'external' sender and
  and can be used to point to a sender that is not a typeclassed entity. This is not used by default
  and what this would be depends on the system (it could be a unique id or a
  python-path, for example). While most systems expect a single sender, it's
  possible to have any number of them.
- `receivers` - these are the ones to see the Msg. These are again any combination of
  [Account](./Accounts), [Object](./Objects) or [Script](./Scripts) or `str` (an 'external' receiver).
  It's in principle possible to have zero receivers but most usages of Msg expects one or more.
- `header` - this is an optional text field that can contain meta-information about the message. For
  an email-like system it would be the subject line. This can be independently searched, making
  this a powerful place for quickly finding messages.
- `message` - the actual text being sent.
- `date_sent` - this is auto-set to the time the Msg was created (and thus presumably sent).
- `locks` - the Evennia [lock handler](./Locks). Use with `locks.add()` etc and check locks with `msg.access()`
  like for all other lockable entities. This can be used to limit access to the contents
  of the Msg. The default lock-type to check is `'read'`.
- `hide_from` - this is an optional list of [Accounts](./Accounts) or [Objects](./Objects) that
  will not see this Msg. This relationship is available mainly for optimization
  reasons since it allows quick filtering of messages not intended for a given
  target.


## TempMsg

[evennia.comms.models.TempMsg](api:evennia.comms.models.TempMsg) is an object
that implements the same API as the regular `Msg`, but which has no database
component (and thus cannot be searched). It's meant to plugged into systems
expecting a `Msg` but where you just want to process the message without saving
it.
