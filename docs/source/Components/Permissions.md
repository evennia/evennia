# Permissions

A *permission* is simply a text string stored in the handler `permissions` on `Objects` and `Accounts`. Think of it as a specialized sort of [Tag](./Tags.md) - one specifically dedicated to access checking. They are thus often tightly coupled to [Locks](./Locks.md). Permission strings are not case-sensitive, so "Builder" is the same as "builder" etc.

Permissions are used as a convenient way to structure access levels and hierarchies. It is set by the `perm` command and checked by the `PermissionHandler.check` method as well as by the specially the `perm()` and `pperm()` [lock functions](./Locks.md).

All new accounts are given a default set of permissions defined by `settings.PERMISSION_ACCOUNT_DEFAULT`.

## The super user

There are strictly speaking two types of users in Evennia, the *super user* and everyone else. The
superuser is the first user you create, object `#1`. This is the all-powerful server-owner account.
Technically the superuser not only has access to everything, it *bypasses* the permission checks
entirely. 

This makes the superuser impossible to lock out, but makes it unsuitable to actually play-
test the game's locks and restrictions with (see `quell` below). Usually there is no need to have
but one superuser.

## Working with Permissions

In-game, you use the `perm` command to add and remove permissions

     > perm/account Tommy = Builders
     > perm/account/del Tommy = Builders

Note the use of the `/account` switch. It means you assign the permission to the [Accounts](./Accounts.md) Tommy instead of any [Character](./Objects.md) that also happens to be named "Tommy". If you don't want to use `/account`, you can also prefix the name with `*` to indicate an Account is sought: 

    > perm *Tommy = Builders
    
There can be reasons for putting permissions on Objects (especially NPCS), but for granting powers to players, you should usually put the permission on the `Account` - this guarantees that they are kept, *regardless* of which Character they are currently puppeting. 

This is especially important to remember when assigning permissions from the *hierarchy tree* (see below), as an Account's permissions will overrule that of its character. So to be sure to avoid confusion you should generally put hierarchy permissions on the Account, not on their Characters/puppets.

If you _do_ want to start using the permissions on your _puppet_, you use `quell`

    > quell 
    > unquell   

This drops to the permissions on the puppeted object, and then back to your Account-permissions again. Quelling is useful if you want to try something "as" someone else. It's also useful for superusers since this makes them susceptible to locks (so they can test things).

In code, you add/remove Permissions via the `PermissionHandler`, which sits on all
typeclassed entities as the property `.permissions`:

```python
    account.permissions.add("Builders")
    account.permissions.add("cool_guy")
    obj.permissions.add("Blacksmith")
    obj.permissions.remove("Blacksmith")
```

### The permission hierarchy

Selected permission strings can be organized in a *permission hierarchy* by editing the tuple
`settings.PERMISSION_HIERARCHY`.  Evennia's default permission hierarchy is as follows
(in increasing order of power):

     Player           # can chat and send tells (default level) (lowest)
     Helper           # can edit help files
     Builder          # can edit the world
     Admin            # can administrate accounts
     Developer        # like superuser but affected by locks (highest)

(Besides being case-insensitive, hierarchical permissions also understand the plural form, so you could use `Developers` and `Developer` interchangeably).

> There is also a `Guest` level below `Player` that is only active if `settings.GUEST_ENABLED` is set. The Guest is is never part of `settings.PERMISSION_HIERARCHY`.

When checking a hierarchical permission (using one of the methods to follow), you will pass checks for your level and all *below* you. That is, even if the check explicitly checks for "Builder" level access, you will actually pass if you have one of "Builder", "Admin" or "Developer". By contrast, if you check for a non-hierarchical permission, like "Blacksmith" you *must* have exactly that permission to pass.

### Checking permissions

It's important to note that you check for the permission of a *puppeted* [Object](./Objects.md) (like a Character), the check will always first use the permissions of any `Account` connected to that Object before checking for permissions on the Object. In the case of hierarchical permissions (Admins, Builders etc), the Account permission will always be used (this stops an Account from escalating their permission by puppeting a high-level Character). If the permission looked for is not in the hierarchy, an exact match is required, first on the Account and if not found there (or if no Account is connected), then on the Object itself.

### Checking with obj.permissions.check()

The simplest way to check if an entity has a permission is to check its _PermissionHandler_, stored as `.permissions`  on all typeclassed entities.

    if obj.permissions.check("Builder"):
        # allow builder to do stuff

    if obj.permissions.check("Blacksmith", "Warrior"):
        # do stuff for blacksmiths OR warriors

    if obj.permissions.check("Blacksmith", "Warrior", require_all=True):
        # only for those that are both blacksmiths AND warriors

Using the `.check` method is the way to go, it will take hierarchical
permissions into account, check accounts/sessions etc.

```{warning}

    Don't confuse `.permissions.check()` with `.permissions.has()`. The .has()
    method checks if a string is defined specifically on that PermissionHandler.
    It will not consider permission-hierarchy, puppeting etc. `.has` can be useful
    if you are manipulating permissions, but use `.check` for access checking.

```

### Lock funcs

While the `PermissionHandler` offers a simple way to check perms, [Lock
strings](./Locks.md) offers a mini-language for describing how something is accessed.
The `perm()` _lock function_ is the main tool for using Permissions in locks.

Let's say we have a `red_key` object. We also have red chests that we want to
unlock with this key.

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
      else:
          who.msg("The key fits! The chest opens.")
          # ...

```

There are several variations to the default `perm` lockfunc:

- `perm_above` - requires a hierarchical permission *higher* than the one
  provided. Example: `"edit: perm_above(Player)"`
- `pperm` - looks *only* for permissions on `Accounts`, never at any puppeted
  objects (regardless of hierarchical perm or not).
- `pperm_above` - like `perm_above`, but for Accounts only.

### Some examples

Adding permissions and checking with locks

```python
    account.permissions.add("Builder")
    account.permissions.add("cool_guy")
    account.locks.add("enter:perm_above(Player) and perm(cool_guy)")
    account.access(obj1, "enter") # this returns True!
```

An example of a puppet with a connected account:

```python
    account.permissions.add("Player")
    puppet.permissions.add("Builders")
    puppet.permissions.add("cool_guy")
    obj2.locks.add("enter:perm_above(Accounts) and perm(cool_guy)")

    obj2.access(puppet, "enter") # this returns False, since puppet permission
                                 # is lower than Account's perm, and perm takes
                                 # precedence.
```


## Quelling

The `quell` command can be used to enforce the `perm()` lockfunc to ignore
permissions on the Account and instead use the permissions on the Character
only. This can be used e.g. by staff to test out things with a lower permission
level. Return to the normal operation with `unquell`.  Note that quelling will
use the smallest of any hierarchical permission on the Account or Character, so
one cannot escalate one's Account permission by quelling to a high-permission
Character. Also the superuser can quell their powers this way, making them
affectable by locks.
