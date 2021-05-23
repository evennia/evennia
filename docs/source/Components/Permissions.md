# Permissions

A *permission* is simply a text string stored in the handler `permissions` on `Objects`
and `Accounts`. Think of it as a specialized sort of [Tag](./Tags) - one specifically dedicated
to access checking. They are thus often tightly coupled to [Locks](./Locks).

Permissions are used as a convenient way to structure access levels and
hierarchies. It is set by the `perm` command. Permissions are especially
handled by the `perm()` and `pperm()` [lock functions](./Locks).

Let's say we have a `red_key` object. We also have red chests that we want to unlock with this key.

    perm red_key = unlocks_red_chests

This gives the `red_key` object the permission "unlocks_red_chests". Next we
lock our red chests:

    lock red chest = unlock:perm(unlocks_red_chests)

When trying to unlock the red chest with this key, the chest Typeclass could
then take the key and do an access check:

```python
# in some typeclass file where chest is defined

class TreasureChest(Object):

  # ...

  def open_chest(self, who, tried_key):

      if not chest.access(who, tried_key, "unlock"):
          who.msg("The key does not fit!")
          return

```

All new accounts are given a default set of permissions defined by
`settings.PERMISSION_ACCOUNT_DEFAULT`.

Selected permission strings can be organized in a *permission hierarchy* by editing the tuple
`settings.PERMISSION_HIERARCHY`.  Evennia's default permission hierarchy is as follows:

     Developer        # like superuser but affected by locks
     Admin            # can administrate accounts
     Builder          # can edit the world
     Helper           # can edit help files
     Player           # can chat and send tells (default level)

(Also the plural form works, so you could use `Developers` etc too).

> There is also a `Guest` level below `Player` that is only active if `settings.GUEST_ENABLED` is
set. This is never part of `settings.PERMISSION_HIERARCHY`.

The main use of this is that if you use the lock function `perm()` mentioned above, a lock check for
a particular permission in the hierarchy will *also* grant access to those with *higher* hierarchy
access. So if you have the permission "Admin" you will also pass a lock defined as `perm(Builder)`
or any of those levels below "Admin".

When doing an access check from an [Object](./Objects) or Character, the `perm()` lock function will
always first use the permissions of any Account connected to that Object before checking for
permissions on the Object. In the case of hierarchical permissions (Admins, Builders etc), the
Account permission will always be used (this stops an Account from escalating their permission by
puppeting a high-level Character).  If the permission looked for is not in the hierarchy, an exact
match is required, first on the Account and if not found there (or if no Account is connected), then
on the Object itself.

Here is how you use `perm` to give an account more permissions:

     perm/account Tommy = Builders
     perm/account/del Tommy = Builders # remove it again

Note the use of the `/account` switch. It means you assign the permission to the
[Accounts](./Accounts) Tommy instead of any [Character](./Objects) that also happens to be named
"Tommy".

Putting permissions on the *Account* guarantees that they are kept, *regardless* of which Character
they are currently puppeting. This is especially important to remember when assigning permissions
from the *hierarchy tree* - as mentioned above, an Account's permissions will overrule that of its
character. So to be sure to avoid confusion you should generally put hierarchy permissions on the
Account, not on their Characters (but see also [quelling](./Locks#Quelling)).

Below is an example of an object without any connected account

```python
    obj1.permissions = ["Builders", "cool_guy"]
    obj2.locks.add("enter:perm_above(Accounts) and perm(cool_guy)")

    obj2.access(obj1, "enter") # this returns True!
```

And one example of a puppet with a connected account:

```python
    account.permissions.add("Accounts")
    puppet.permissions.add("Builders", "cool_guy")
    obj2.locks.add("enter:perm_above(Accounts) and perm(cool_guy)")

    obj2.access(puppet, "enter") # this returns False!
```

## Superusers

There is normally only one *superuser* account and that is the one first created when starting
Evennia (User #1). This is sometimes known as the "Owner" or "God" user.  A superuser has more than
full access - it completely *bypasses* all locks so no checks are even run. This allows for the
superuser to always have access to everything in an emergency. But it also hides any eventual errors
you might have made in your lock definitions. So when trying out game systems you should either use
quelling (see below) or make a second Developer-level character so your locks get tested correctly.

## Quelling

The `quell` command can be used to enforce the `perm()` lockfunc to ignore permissions on the
Account and instead use the permissions on the Character only. This can be used e.g. by staff to
test out things with a lower permission level. Return to the normal operation with `unquell`.  Note
that quelling will use the smallest of any hierarchical permission on the Account or Character, so
one cannot escalate one's Account permission by quelling to a high-permission Character. Also the
superuser can quell their powers this way, making them affectable by locks.
