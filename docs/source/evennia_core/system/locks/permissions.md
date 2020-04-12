# Permissions

> This section covers the underlying code use of permissions. If you just want to learn how to practically assign permissions in-game, refer to the [Building Permissions](Building-Permissions) page, which details how you use the `perm` command.

A *permission* is simply a list of text strings stored  in the handler `permissions` on `Objects` and `Accounts`. Permissions can be used as a convenient way to structure access levels and hierarchies. It is set by the `perm` command. Permissions are especially handled by the `perm()` and `pperm()` lock functions listed above. 

Let's say we have a `red_key` object. We also have red chests that we want to unlock with this key. 

    perm red_key = unlocks_red_chests

This gives the `red_key` object the permission "unlocks_red_chests".  Next we lock our red chests:

    lock red chest = unlock:perm(unlocks_red_chests)

What this lock will expect is to the fed the actual key object. The `perm()` lock function will check the permissions set on the key and only return true if the permission is the one given. 

Finally we need to actually check this lock somehow. Let's say the chest has an command `open <key>` sitting on itself. Somewhere in its code the command needs to figure out which key you are using and test if this key has the correct permission:

```python
    # self.obj is the chest 
    # and used_key is the key we used as argument to
    # the command. The self.caller is the one trying
    # to unlock the chest
    if not self.obj.access(used_key, "unlock"):
        self.caller.msg("The key does not fit!")
        return 
```

All new accounts are given a default set of permissions defined by `settings.PERMISSION_ACCOUNT_DEFAULT`.

Selected permission strings can be organized in a *permission hierarchy* by editing the tuple `settings.PERMISSION_HIERARCHY`.  Evennia's default permission hierarchy is as follows:

     Developer        # like superuser but affected by locks
     Admin            # can administrate accounts
     Builder          # can edit the world
     Helper           # can edit help files
     Player           # can chat and send tells (default level)

(Also the plural form works, so you could use `Developers` etc too). 

> There is also a `Guest` level below `Player` that is only active if `settings.GUEST_ENABLED` is set. This is never part of `settings.PERMISSION_HIERARCHY`.

The main use of this is that if you use the lock function `perm()` mentioned above, a lock check for a particular permission in the hierarchy will *also* grant access to those with *higher* hierarchy access. So if you have the permission "Admin" you will also pass a lock defined as `perm(Builder)` or any of those levels below "Admin". 

When doing an access check from an [Object](../objects/Objects) or Character, the `perm()` lock function will always first use the permissions of any Account connected to that Object before checking for permissions on the Object. In the case of hierarchical permissions (Admins, Builders etc), the Account permission will always be used (this stops an Account from escalating their permission by puppeting a high-level Character).  If the permission looked for is not in the hierarchy, an exact match is required, first on the Account and if not found there (or if no Account is connected), then on the Object itself. 

Here is how you use `perm` to give an account more permissions: 

     perm/account Tommy = Builders
     perm/account/del Tommy = Builders # remove it again

Note the use of the `/account` switch. It means you assign the permission to the [Accounts](Account) Tommy instead of any [Character](../objects/Objects) that also happens to be named "Tommy". 

Putting permissions on the *Account* guarantees that they are kept, *regardless* of which Character they are currently puppeting. This is especially important to remember when assigning permissions from the *hierarchy tree* - as mentioned above, an Account's permissions will overrule that of its character. So to be sure to avoid confusion you should generally put hierarchy permissions on the Account, not on their Characters (but see also [quelling](../locks/Locks#Quelling)).

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

There is normally only one *superuser* account and that is the one first created when starting Evennia (User #1). This is sometimes known as the "Owner" or "God" user.  A superuser has more than full access - it completely *bypasses* all locks so no checks are even run. This allows for the superuser to always have access to everything in an emergency. But it also hides any eventual errors you might have made in your lock definitions. So when trying out game systems you should either use quelling (see below) or make a second Developer-level character so your locks get tested correctly.

## Quelling

The `quell` command can be used to enforce the `perm()` lockfunc to ignore permissions on the Account and instead use the permissions on the Character only. This can be used e.g. by staff to test out things with a lower permission level. Return to the normal operation with `unquell`.  Note that quelling will use the smallest of any hierarchical permission on the Account or Character, so one cannot escalate one's Account permission by quelling to a high-permission Character. Also the superuser can quell their powers this way, making them affectable by locks.

## More Lock definition examples

    examine: attr(eyesight, excellent) or perm(Builders)

You are only allowed to do *examine* on this object if you have 'excellent' eyesight (that is, has an Attribute `eyesight` with the value `excellent` defined on yourself) or if you have the "Builders" permission string assigned to you. 

    open: holds('the green key') or perm(Builder) 

This could be called by the `open` command on a "door" object. The check is passed if you are a Builder or has the right key in your inventory.

    cmd: perm(Builders)

Evennia's command handler looks for a lock of type `cmd` to determine if a user is allowed to even call upon a particular command or not.  When you define a command, this is the kind of lock you must set. See the default command set for lots of examples. If a character/account don't pass the `cmd` lock type the command will not even appear in their `help` list.

    cmd: not perm(no_tell)

"Permissions" can also be used to block users or implement highly specific bans. The above example would be be added as a lock string to the `tell` command. This will allow everyone *not* having the "permission" `no_tell` to use the `tell` command. You could easily give an account the "permission" `no_tell` to disable their use of this particular command henceforth. 


```python
    dbref = caller.id
    lockstring = "control:id(%s);examine:perm(Builders);delete:id(%s) or perm(Admin);get:all()" % (dbref, dbref)
    new_obj.locks.add(lockstring)
```

This is how the `create` command sets up new objects. In sequence, this permission string sets the owner of this object be the creator (the one  running `create`). Builders may examine the object whereas only Admins and the creator may delete it. Everyone can pick it up.

## A complete example of setting locks on an object

Assume we have two objects - one is ourselves (not superuser) and the other is an [Object](../objects/Objects) called `box`. 

     > create/drop box
     > desc box = "This is a very big and heavy box."

We want to limit which objects can pick up this heavy box. Let's say that to do that we require the would-be lifter to to have an attribute *strength* on themselves, with a value greater than 50. We assign it to ourselves to begin with.

     > set self/strength = 45

Ok, so for testing we made ourselves strong, but not strong enough.  Now we need to look at what happens when someone tries to pick up the the box - they use the `get` command (in the default set). This is defined in `evennia/commands/default/general.py`. In its code we find this snippet: 

```python
    if not obj.access(caller, 'get'):
        if obj.db.get_err_msg:
            caller.msg(obj.db.get_err_msg)
        else:
            caller.msg("You can't get that.")
        return
```

So the `get` command looks for a lock with the type *get* (not so surprising). It also looks for an [Attribute](../attributes/Attributes) on the checked object called _get_err_msg_ in order to return a customized error message. Sounds good! Let's start by setting that on the box: 

     > set box/get_err_msg = You are not strong enough to lift this box.

Next we need to craft a Lock of type *get* on our box. We want it to only be passed if the accessing object has the attribute *strength* of the right value. For this we would need to create a lock function that checks if attributes have a value greater than a given value. Luckily there is already such a one included in evennia (see `evennia/locks/lockfuncs.py`), called `attr_gt`. 

So the lock string will look like this: `get:attr_gt(strength, 50)`.  We put this on the box now: 

     lock box = get:attr_gt(strength, 50)

Try to `get` the object and you should get the message that we are not strong enough. Increase your strength above 50 however and you'll pick it up no problem. Done! A very heavy box!

If you wanted to set this up in python code, it would look something like this:

```python
   
 from evennia import create_object
    
    # create, then set the lock
    box = create_object(None, key="box")
    box.locks.add("get:attr_gt(strength, 50)")
    
    # or we can assign locks in one go right away
    box = create_object(None, key="box", locks="get:attr_gt(strength, 50)")
    
    # set the attributes
    box.db.desc = "This is a very big and heavy box."
    box.db.get_err_msg = "You are not strong enough to lift this box."
    
    # one heavy box, ready to withstand all but the strongest...
```

## On Django's permission system

Django also implements a comprehensive permission/security system of its own.  The reason we don't use that is because it is app-centric (app in the Django sense).  Its permission strings are of the form `appname.permstring` and it automatically adds three of them for each database model in the app - for the app evennia/object this would be for example 'object.create', 'object.admin' and 'object.edit'. This makes a lot of sense for a web application, not so much for a MUD, especially when we try to hide away as much of the underlying architecture as possible.  

The django permissions are not completely gone however. We use it for validating passwords during login. It is also used exclusively for managing Evennia's web-based admin site, which is a graphical front-end for the database of Evennia. You edit and assign such permissions directly from the web interface. It's stand-alone from the permissions described above.