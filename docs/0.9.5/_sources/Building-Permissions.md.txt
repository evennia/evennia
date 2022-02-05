# Building Permissions


*OBS: This gives only a brief introduction to the access system. Locks and permissions are fully
detailed* [here](./Locks.md).

## The super user

There are strictly speaking two types of users in Evennia, the *super user* and everyone else. The
superuser is the first user you create, object `#1`. This is the all-powerful server-owner account.
Technically the superuser not only has access to everything, it *bypasses* the permission checks
entirely. This makes the superuser impossible to lock out, but makes it unsuitable to actually play-
test the game's locks and restrictions with (see `@quell` below). Usually there is no need to have
but one superuser.

## Assigning permissions

Whereas permissions can be used for anything, those put in `settings.PERMISSION_HIERARCHY` will have
a ranking relative each other as well. We refer to these types of permissions as *hierarchical
permissions*. When building locks to check these permissions, the `perm()` [lock function](./Locks.md) is
used. By default Evennia creates the following hierarchy (spelled exactly like this):

1. **Developers** basically have the same access as superusers except that they do *not* sidestep
the Permission system. Assign only to really trusted server-admin staff since this level gives
access both to server reload/shutdown functionality as well as (and this may be more critical) gives
access to the all-powerful `@py` command that allows the execution of arbitrary Python code on the
command line.
1. **Admins** can do everything *except* affecting the server functions themselves. So an Admin
couldn't reload or shutdown the server for example. They also cannot execute arbitrary Python code
on the console or import files from the hard drive.
1. **Builders** - have all the build commands, but cannot affect other accounts or mess with the
server.
1. **Helpers** are almost like a normal *Player*, but they can also add help files to the database.
1. **Players** is the default group that new players end up in. A new player have permission to use
tells and to use and create new channels.

A user having a certain level of permission automatically have access to locks specifying access of
a lower level.

To assign a new permission from inside the game, you need to be able to use the `@perm` command.
This is an *Developer*-level command, but it could in principle be made lower-access since it only
allows assignments equal or lower to your current level (so you cannot use it to escalate your own
permission level).  So, assuming you yourself have *Developer* access (or is superuser), you  assign
a new account "Tommy" to your core staff with the command

    @perm/account Tommy = Developer

or

    @perm *Tommy = Developer

We use a switch or the `*name` format to make sure to put the permission on the *Account* and not on
any eventual *Character* that may also be named "Tommy". This is usually what you want since the
Account will then remain an Developer regardless of which Character they are currently controlling.
To limit permission to a per-Character level you should instead use *quelling* (see below). Normally
permissions can be any string, but for these special hierarchical permissions you can also use
plural ("Developer" and "Developers" both grant the same powers).

## Quelling your permissions

When developing it can be useful to check just how things would look had your permission-level been
lower. For this you can use *quelling*.  Normally, when you puppet a Character you are using your
Account-level permission. So even if your Character only has *Accounts* level permissions, your
*Developer*-level Account will take precedence. With the `@quell` command you can change so that the
Character's permission takes precedence instead:

     @quell

This will allow you to test out the game using the current Character's permission level. A developer
or builder can thus in principle maintain several test characters, all using different permission
levels. Note that you cannot escalate your permissions this way; If the Character happens to have a
*higher* permission level than the Account, the *Account's* (lower) permission will still be used.
