# Signals


_This is feature available from evennia 0.9 and onward_.

There are multiple ways for you to plug in your own functionality into Evennia.
The most common way to do so is through *hooks* - methods on typeclasses that
gets called at particular events. Hooks are great when you want a game entity
to behave a certain way when something happens to it. _Signals_ complements
hooks for cases when you want to easily attach new functionality without
overriding things on the typeclass.

When certain events happen in Evennia, a _Signal_ is fired. The idea is that
you can "attach" any number of event-handlers to these signals. You can attach
any number of handlers and they'll all fire whenever any entity triggers the
signal.

Evennia uses the [Django Signal system](https://docs.djangoproject.com/en/2.2/topics/signals/).


## Attaching a handler to a signal

First you create your handler

```python

def myhandler(sender, **kwargs):
  # do stuff

```

The `**kwargs` is mandatory. Then you attach it to the signal of your choice:

```python
from evennia.server import signals

signals.SIGNAL_OBJECT_POST_CREATE.connect(myhandler)

```

This particular signal fires after (post) an Account has connected to the game.
When that happens, `myhandler` will fire with the `sender` being the Account that just connected.

If you want to respond only to the effects of a specific entity you can do so
like this:

```python
from evennia import search_account
from evennia import signals

account = search_account("foo")[0]
signals.SIGNAL_ACCOUNT_POST_CONNECT.connect(myhandler, account)
```

## Available signals

All signals (including some django-specific defaults) are available in the module
`evennia.server.signals`
(with a shortcut `evennia.signals`). Signals are named by the sender type. So `SIGNAL_ACCOUNT_*`
returns
`Account` instances as senders, `SIGNAL_OBJECT_*` returns `Object`s etc. Extra keywords (kwargs)
should
be extracted from the `**kwargs` dict in the signal handler.

- `SIGNAL_ACCOUNT_POST_CREATE` - this is triggered at the very end of `Account.create()`. Note that
  calling `evennia.create.create_account` (which is called internally by `Account.create`) will
*not*
  trigger this signal. This is because using `Account.create()` is expected to be the most commonly
  used way for users to themselves create accounts during login. It passes and extra kwarg `ip` with
  the client IP of the connecting account.
- `SIGNAL_ACCOUNT_POST_LOGIN` - this will always fire when the account has authenticated.  Sends
  extra kwarg `session` with the new [Session](Sessions) object involved.
- `SIGNAL_ACCCOUNT_POST_FIRST_LOGIN` - this fires just before `SIGNAL_ACCOUNT_POST_LOGIN` but only
if
  this is the *first* connection done (that is, if there are no previous sessions connected). Also
  passes the `session` along as a kwarg.
- `SIGNAL_ACCOUNT_POST_LOGIN_FAIL` - sent when someone tried to log into an account by failed.
Passes
  the `session` as an extra kwarg.
- `SIGNAL_ACCOUNT_POST_LOGOUT` - always fires when an account logs off, no matter if other sessions
  remain or not. Passes the disconnecting `session` along as a kwarg.
- `SIGNAL_ACCOUNT_POST_LAST_LOGOUT` - fires before `SIGNAL_ACCOUNT_POST_LOGOUT`, but only if this is
  the *last* Session to disconnect for that account. Passes the `session` as a kwarg.
- `SIGNAL_OBJECT_POST_PUPPET` - fires when an account puppets this object. Extra kwargs `session`
  and `account` represent the puppeting entities.
  `SIGNAL_OBJECT_POST_UNPUPPET` - fires when the sending object is unpuppeted. Extra kwargs are
  `session` and `account`.
- `SIGNAL_ACCOUNT_POST_RENAME` - triggered by the setting of `Account.username`. Passes extra
  kwargs `old_name`, `new_name`.
- `SIGNAL_TYPED_OBJECT_POST_RENAME` - triggered when any Typeclassed entity's `key` is changed.
Extra
  kwargs passed are `old_key` and `new_key`.
- `SIGNAL_SCRIPT_POST_CREATE` - fires when a script is first created, after any hooks.
- `SIGNAL_CHANNEL_POST_CREATE` - fires when a Channel is first created, after any hooks.
- `SIGNAL_HELPENTRY_POST_CREATE` - fires when a help entry is first created.

The `evennia.signals` module also gives you conveneient access to the default Django signals (these
use a
different naming convention).

- `pre_save` - fired when any database entitiy's `.save` method fires, before any saving has
happened.
- `post_save` - fires after saving a database entity.
- `pre_delete` - fires just before a database entity is deleted.
- `post_delete` - fires after a database entity was deleted.
- `pre_init` - fires before a typeclass' `__init__` method (which in turn
  happens before the `at_init` hook fires).
- `post_init` - triggers at the end of `__init__`  (still before the `at_init` hook).

These are highly specialized Django signals that are unlikely to be useful to most users. But
they are included here for completeness.

- `m2m_changed` - fires after a Many-to-Many field (like `db_attributes`) changes.
- `pre_migrate` - fires before database migration starts with `evennia migrate`.
- `post_migrate` - fires after database migration finished.
- `request_started` - sent when HTTP request begins.
- `request_finished` - sent when HTTP request ends.
- `settings_changed` - sent when changing settings due to `@override_settings`
  decorator (only relevant for unit testing)
- `template_rendered` - sent when test system renders http template (only useful for unit tests).
- `connection_creation` - sent when making initial connection to database.
