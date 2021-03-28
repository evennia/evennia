# Sessions


An Evennia *Session* represents one single established connection to the server. Depending on the
Evennia session, it is possible for a person to connect multiple times, for example using different
clients in multiple windows. Each such connection is represented by a session object.

A session object has its own [cmdset](./Command-Sets), usually the "unloggedin" cmdset. This is what
is used to show the login screen and to handle commands to create a new account (or
[Account](./Accounts) in evennia lingo) read initial help and to log into the game with an existing
account. A session object can either be "logged in" or not.  Logged in means that the user has
authenticated. When this happens the session is associated with an Account object (which is what
holds account-centric stuff). The account can then in turn puppet any number of objects/characters.

> Warning: A Session is not *persistent* - it is not a [Typeclass](./Typeclasses) and has no
connection to the database. The Session will go away when a user disconnects and you will lose any
custom data on it if the server reloads. The `.db` handler on Sessions is there to present a uniform
API (so you can assume `.db` exists even if you don't know if you receive an Object or a Session),
but this is just an alias to `.ndb`. So don't store any data on Sessions that you can't afford to
lose in a reload. You have been warned.

## Properties on Sessions

Here are some important properties available on (Server-)Sessions

- `sessid` - The unique session-id. This is an integer starting from 1.
- `address` - The connected client's address. Different protocols give different information here.
- `logged_in` - `True` if the user authenticated to this session.
- `account` - The [Account](./Accounts) this Session is attached to. If not logged in yet, this is
`None`.
- `puppet` - The [Character/Object](./Objects) currently puppeted by this Account/Session combo. If
not logged in or in OOC mode, this is `None`.
- `ndb` - The [Non-persistent Attribute](./Attributes) handler.
- `db` - As noted above, Sessions don't have regular Attributes. This is an alias to `ndb`.
- `cmdset` - The Session's [CmdSetHandler](./Command-Sets)

Session statistics are mainly used internally by Evennia.

- `conn_time` - How long this Session has been connected
- `cmd_last` - Last active time stamp. This will be reset by sending `idle` keepalives.
- `cmd_last_visible` - last active time stamp. This ignores `idle` keepalives and representes the
last time this session was truly visibly active.
- `cmd_total` - Total number of Commands passed through this Session.


## Multisession mode

The number of sessions possible to connect to a given account at the same time and how it works is
given by the `MULTISESSION_MODE` setting:

* `MULTISESSION_MODE=0`: One session per account. When connecting with a new session the old one is
disconnected. This is the default mode and emulates many classic mud code bases. In default Evennia,
this mode also changes how the `create account` Command works - it will automatically create a
Character with the *same name* as the Account. When logging in, the login command is also modified
to have the player automatically puppet that Character. This makes the distinction between Account
and Character minimal from the player's perspective.
* `MULTISESSION_MODE=1`: Many sessions per account, input/output from/to each session is treated the
same. For the player this means they can connect to the game from multiple clients and see the same
output in all of them. The result of a command given in one client (that is, through one Session)
will be returned to *all* connected Sessions/clients with no distinction. This mode will have the
Session(s) auto-create and puppet a Character in the same way as mode 0.
* `MULTISESSION_MODE=2`: Many sessions per account, one character per session. In this mode,
puppeting an Object/Character will link the puppet back only to the particular Session doing the
puppeting. That is, input from that Session will make use of the CmdSet of that Object/Character and
outgoing messages (such as the result of a `look`) will be passed back only to that puppeting
Session. If another Session tries to puppet the same Character, the old Session will automatically
un-puppet it. From the player's perspective, this will mean that they can open separate game clients
and play a different Character in each using one game account.
This mode will *not* auto-create a Character and *not* auto-puppet on login like in modes 0 and 1.
Instead it changes how the account-cmdsets's `OOCLook` command works so as to show a simple
'character select' menu.
* `MULTISESSION_MODE=3`: Many sessions per account *and* character. This is the full multi-puppeting
mode, where multiple sessions may not only connect to the player account but multiple sessions may
also puppet a single character at the same time. From the user's perspective it means one can open
multiple client windows, some for controlling different Characters and some that share a Character's
input/output like in mode 1. This mode otherwise works the same as mode 2.

> Note that even if multiple Sessions puppet one Character, there is only ever one instance of that
Character.

## Returning data to the session

When you use `msg()` to return data to a user, the object on which you call the `msg()` matters. The
`MULTISESSION_MODE` also matters, especially if greater than 1.

For example, if you use `account.msg("hello")` there is no way for evennia to know which session it
should send the greeting to. In this case it will send it to all sessions. If you want a specific
session you need to supply its session to the `msg` call (`account.msg("hello",
session=mysession)`).

On the other hand, if you call the `msg()` message on a puppeted object, like
`character.msg("hello")`, the character already knows the session that controls it - it will
cleverly auto-add this for you (you can specify a different session if you specifically want to send
stuff to another session).

Finally, there is a wrapper for `msg()` on all command classes: `command.msg()`. This will
transparently detect which session was triggering the command (if any) and redirects to that session
(this is most often what you want). If you are having trouble redirecting to a given session,
`command.msg()` is often the safest bet.

You can get the `session` in two main ways:
* [Accounts](./Accounts) and [Objects](./Objects) (including Characters) have a `sessions` property.
This is a *handler* that tracks all Sessions attached to or puppeting them. Use e.g.
`accounts.sessions.get()` to get a list of Sessions attached to that entity.
* A Command instance has a `session` property that always points back to the Session that triggered
it (it's always a single one). It will be `None` if no session is involved, like when a mob or
script triggers the Command.

## Customizing the Session object

When would one want to customize the Session object? Consider for example a character creation
system: You might decide to keep this on the out-of-character level. This would mean that you create
the character at the end of some sort of menu choice. The actual char-create cmdset would then
normally be put on the account.  This works fine as long as you are `MULTISESSION_MODE` below 2.
For higher modes, replacing the Account cmdset will affect *all* your connected sessions, also those
not involved in character  creation. In this case you want to instead put the char-create cmdset on
the Session level - then all other sessions will keep working normally despite you creating a new
character in one of them.

By default, the session object gets the `commands.default_cmdsets.UnloggedinCmdSet` when the user
first connects. Once the session is authenticated it has *no* default sets. To add a "logged-in"
cmdset to the Session, give the path to the cmdset class with `settings.CMDSET_SESSION`. This set
will then henceforth always be present as soon as the account logs in.

To customize further you can completely override the Session with your own subclass. To replace the
default Session class, change `settings.SERVER_SESSION_CLASS` to point to your custom class. This is
a dangerous practice and errors can easily make your game unplayable.  Make sure to take heed of the
[original](https://github.com/evennia/evennia/blob/master/evennia/server/session.py) and make your
changes carefully.

## Portal and Server Sessions

*Note: This is considered an advanced topic. You don't need to know this on a first read-through.*

Evennia is split into two parts, the [Portal and the Server](./Portal-And-Server). Each side tracks
its own Sessions, syncing them to each other.

The "Session" we normally refer to is actually the `ServerSession`. Its counter-part on the Portal
side is the `PortalSession`. Whereas the server sessions deal with game states, the portal session
deals with details of the connection-protocol itself. The two are also acting as backups of critical
data such as when the server reboots.

New Account connections are listened for and handled by the Portal using the [protocols](Portal-And-
Server) it understands (such as telnet, ssh, webclient etc). When a new connection is established, a
`PortalSession` is created on the Portal side. This session object looks different depending on
which protocol is used to connect, but all still have a minimum set of attributes that are generic
to all
sessions.

These common properties are piped from the Portal, through the AMP connection, to the Server, which
is now informed a new connection has been established.  On the Server side, a `ServerSession` object
is created to represent this. There is only one type of `ServerSession`; It looks the same
regardless of how the Account connects.

From now on, there is a one-to-one match between the `ServerSession` on one side of the AMP
connection and the `PortalSession` on the other.  Data arriving to the Portal Session is sent on to
its mirror Server session and vice versa.

During certain situations, the portal- and server-side sessions are
"synced" with each other:
- The Player closes their client, killing the Portal Session. The Portal syncs with the Server to
make sure the corresponding Server Session is also deleted.
- The Player quits from inside the game, killing the Server Session.  The Server then syncs with the
Portal to make sure to close the Portal connection cleanly.
- The Server is rebooted/reset/shutdown - The Server Sessions are copied over ("saved") to the
Portal side. When the Server comes back up, this data is returned by the Portal so the two are again
in sync. This way an Account's login status and other connection-critical things can survive a
server reboot (assuming the Portal is not stopped at the same time, obviously).

## Sessionhandlers

Both the Portal and Server each have a *sessionhandler* to manage the connections. These handlers
are global entities contain all methods for relaying data across the AMP bridge. All types of
Sessions hold a reference to their respective Sessionhandler (the property is called
`sessionhandler`) so they can relay data. See [protocols](./Custom-Protocols) for more info
on building new protocols.

To get all Sessions in the game (i.e. all currently connected clients), you access the server-side
Session handler, which you get by
```
from evennia.server.sessionhandler import SESSION_HANDLER
```
> Note: The `SESSION_HANDLER` singleton has an older alias `SESSIONS` that is commonly seen in
various places as well.

See the
[sessionhandler.py](https://github.com/evennia/evennia/blob/master/evennia/server/sessionhandler.py)
module for details on the capabilities of the `ServerSessionHandler`.
