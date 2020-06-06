# Locks


For most games it is a good idea to restrict what people can do. In Evennia such restrictions are applied and checked by something called *locks*. All Evennia entities ([Commands](Commands), [Objects](Objects), [Scripts](Scripts), [Accounts](Accounts), [Help System](Help-System), [messages](Communications#Msg) and [channels](Communications#Channels)) are accessed through locks. 

A lock can be thought of as an "access rule" restricting a particular use of an Evennia entity.  Whenever another entity wants that kind of access the lock will analyze that entity in different ways to determine if access should be granted or not. Evennia implements a "lockdown" philosophy - all entities are inaccessible unless you explicitly define a lock that allows some or full access. 

Let's take an example: An object has a lock on itself that restricts how people may "delete" that object. Apart from knowing that it restricts deletion, the lock also knows that only players with the specific ID of, say, `34` are allowed to delete it. So whenever a player tries to run `delete` on the object, the `delete` command makes sure to check if this player is really allowed to do so. It calls the lock, which in turn checks if the player's id is `34`. Only then will it allow `delete` to go on with its job.

## Setting and checking a lock

The in-game command for setting locks on objects is `lock`:

     > lock obj = <lockstring>

The `<lockstring>` is a string of a certain form that defines the behaviour of the lock. We will go into more detail on how `<lockstring>` should look in the next section.

Code-wise, Evennia handles locks through what is usually called `locks` on all relevant entities. This is a handler that allows you to add, delete and check locks. 

```python
     myobj.locks.add(<lockstring>)
```

One can call `locks.check()` to perform a lock check, but to hide the underlying implementation all objects also have a convenience function called `access`. This should preferably be used. In the example below, `accessing_obj` is the object requesting the 'delete' access whereas `obj` is the object that might get deleted. This is how it would look (and does look) from inside the `delete` command: 

```python
     if not obj.access(accessing_obj, 'delete'):
         accessing_obj.msg("Sorry, you may not delete that.")
         return 
```

## Defining locks

Defining a lock (i.e. an access restriction) in Evennia is done by adding simple strings of lock definitions to the object's `locks` property using `obj.locks.add()`. 

Here are some examples of lock strings (not including the quotes): 

```python
     delete:id(34)   # only allow obj #34 to delete
     edit:all()      # let everyone edit 
     # only those who are not "very_weak" or are Admins may pick this up
     get: not attr(very_weak) or perm(Admin) 
```

Formally, a lockstring has the following syntax: 

```python
     access_type: [NOT] lockfunc1([arg1,..]) [AND|OR] [NOT] lockfunc2([arg1,...]) [...]
```

where `[]` marks optional parts. `AND`, `OR` and `NOT` are not case sensitive and excess spaces are ignored. `lockfunc1, lockfunc2` etc are special _lock functions_ available to the lock system. 

So, a lockstring consists of the type of restriction (the `access_type`), a colon (`:`) and then an expression involving function calls that determine what is needed to pass the lock. Each function returns either `True` or `False`. `AND`, `OR` and `NOT` work as they do normally in Python. If the total result is `True`, the lock is passed. 

You can create several lock types one after the other by separating them with a semicolon (`;`) in the lockstring. The string below yields the same result as the previous example: 

    delete:id(34);edit:all();get: not attr(very_weak) or perm(Admin) 


### Valid access_types

An `access_type`, the first part of a lockstring, defines what kind of capability a lock controls, such as "delete" or "edit". You may in principle name your `access_type` anything as long as it is unique for the particular object. The name of the access types is not case-sensitive.

If you want to make sure the lock is used however, you should pick `access_type` names that you (or the default command set) actually checks for, as in the example of `delete` above that uses the 'delete' `access_type`.

Below are the access_types checked by the default commandset.

- [Commands](Commands) 
  - `cmd` - this defines who may call this command at all.
- [Objects](Objects):
  - `control` - who is the "owner" of the object. Can set locks, delete it etc. Defaults to the creator of the object.
  - `call` - who may call Object-commands stored on this Object except for the Object itself. By default, Objects share their Commands with anyone in the same location (e.g. so you can 'press' a `Button` object in the room). For Characters and Mobs (who likely only use those Commands for themselves and don't want to share them) this should usually be turned off completely, using something like `call:false()`. 
  - `examine` - who may examine this object's properties.
  - `delete` - who may delete the object.
  - `edit` - who may edit properties and attributes of the object.
  - `view` - if the `look` command will display/list this object
  - `get`- who may pick up the object and carry it around.
  - `puppet` - who may "become" this object and control it as their "character".
  - `attrcreate` - who may create new attributes on the object (default True)
- [Characters](Objects#Characters): 
  - Same as for Objects
- [Exits](Objects#Exits): 
  - Same as for Objects 
  - `traverse` - who may pass the exit.
- [Accounts](Accounts):
  - `examine` - who may examine the account's properties.
  - `delete` - who may delete the account.
  - `edit` - who may edit the account's attributes and properties.
  - `msg` - who may send messages to the account.
  - `boot` - who may boot the account.
- [Attributes](Attributes): (only checked by `obj.secure_attr`)
  - `attrread` - see/access attribute
  - `attredit` - change/delete attribute
- [Channels](Communications#Channels):
  - `control` - who is administrating the channel. This means the ability to delete the channel, boot listeners etc.
  - `send` - who may send to the channel.
  - `listen` - who may subscribe and listen to the channel.
- [HelpEntry](Help-System):
  - `examine` - who may view this help entry (usually everyone)
  - `edit` - who may edit this help entry.

So to take an example, whenever an exit is to be traversed, a lock of the type *traverse* will be checked. Defining a suitable lock type for an exit object would thus involve a lockstring `traverse: <lock functions>`. 

### Custom access_types

As stated above, the `access_type` part of the lock is simply the 'name' or 'type' of the lock. The text is an arbitrary string that must be unique for an object. If adding a lock with the same `access_type` as one that already exists on the object, the new one override the old one.

For example, if you wanted to create a bulletin board system and wanted to restrict who can either read a board or post to a board. You could then define locks such as: 

```python
     obj.locks.add("read:perm(Player);post:perm(Admin)")
``` 

This will create a 'read' access type for Characters having the `Player` permission or above and a 'post' access type for those with `Admin` permissions or above (see below how the `perm()` lock function works).  When it comes time to test these permissions, simply check like this (in this example, the `obj` may be a board on the bulletin board system and `accessing_obj` is the player trying to read the board):

```python
     if not obj.access(accessing_obj, 'read'):
         accessing_obj.msg("Sorry, you may not read that.")
         return 
```

### Lock functions

A lock function is a normal Python function put in a place Evennia looks for such functions. The modules Evennia looks at is the list `settings.LOCK_FUNC_MODULES`. *All functions* in any of those modules will automatically be considered a valid lock function. The default ones are found in `evennia/locks/lockfuncs.py` and you can start adding your own in `mygame/server/conf/lockfuncs.py`. You can append the setting to add more module paths. To replace a default lock function, just add your own with the same name. 

A lock function must always accept at least two arguments - the *accessing object* (this is the object wanting to get access) and the *accessed object* (this is the object with the lock). Those two are fed automatically as the first two arguments to the function when the lock is checked. Any arguments explicitly given in the lock definition will appear as extra arguments.

```python
    # A simple example lock function. Called with e.g. `id(34)`. This is
    # defined in, say mygame/server/conf/lockfuncs.py
    
    def id(accessing_obj, accessed_obj, *args, **kwargs):
        if args:
            wanted_id = args[0]
            return accessing_obj.id == wanted_id
        return False 
```

The above could for example be used in a lock function like this: 

```python
    # we have `obj` and `owner_object` from before
    obj.locks.add("edit: id(%i)" % owner_object.id)
```

We could check if the "edit" lock is passed with something like this:

```python
    # as part of a Command's func() method, for example
    if not obj.access(caller, "edit"):
        caller.msg("You don't have access to edit this!")
        return
```

In this example, everyone except the `caller` with the right `id` will get the error. 

> (Using the `*` and `**` syntax causes Python to magically put all extra arguments into a list `args` and all keyword arguments into a dictionary `kwargs` respectively. If you are unfamiliar with how `*args` and `**kwargs` work, see the Python manuals). 

Some useful default lockfuncs (see `src/locks/lockfuncs.py` for more):

- `true()/all()` - give access to everyone
- `false()/none()/superuser()` - give access to none. Superusers bypass the check entirely and are thus the only ones who will pass this check.
- `perm(perm)` - this tries to match a given `permission` property, on an Account firsthand, on a Character second. See [below](Locks#permissions).
- `perm_above(perm)` - like `perm` but requires a "higher" permission level than the one given.
- `id(num)/dbref(num)` - checks so the access_object has a certain dbref/id.
- `attr(attrname)` - checks if a certain [Attribute](Attributes) exists on accessing_object.
- `attr(attrname, value)` - checks so an attribute exists on accessing_object *and* has the given value.
- `attr_gt(attrname, value)` - checks so accessing_object has a value larger (`>`) than the given value.
- `attr_ge, attr_lt, attr_le, attr_ne` - corresponding for `>=`, `<`, `<=` and `!=`.
- `holds(objid)` - checks so the accessing objects contains an object of given name or dbref.
- `inside()` - checks so the accessing object is inside the accessed object (the inverse of `holds()`).
- `pperm(perm)`, `pid(num)/pdbref(num)` - same as `perm`, `id/dbref` but always looks for permissions and dbrefs of *Accounts*, not on Characters.
- `serversetting(settingname, value)` - Only returns True if Evennia has a given setting or a setting set to a given value. 

## Checking simple strings

Sometimes you don't really need to look up a certain lock, you just want to check a lockstring. A common use is inside Commands, in order to check if a user has a certain permission. The lockhandler has a method `check_lockstring(accessing_obj, lockstring, bypass_superuser=False)` that allows this.

```python
     # inside command definition
     if not self.caller.locks.check_lockstring(self.caller, "dummy:perm(Admin)"):
         self.caller.msg("You must be an Admin or higher to do this!")
         return
```

Note here that the `access_type` can be left to a dummy value since this method does not actually do a Lock lookup.

## Default locks

Evennia sets up a few basic locks on all new objects and accounts (if we didn't, noone would have any access to anything from the start).  This is all defined in the root [Typeclasses](Typeclasses) of the respective entity, in the hook method `basetype_setup()` (which you usually don't want to edit unless you want to change how basic stuff like rooms and exits store their internal variables). This is called once, before `at_object_creation`, so just put them in the latter method on your child object to change the default. Also creation commands like `create` changes the locks of objects you create - for example it sets the `control` lock_type so as to allow you, its creator, to control and delete the object.

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

When doing an access check from an [Object](Objects) or Character, the `perm()` lock function will always first use the permissions of any Account connected to that Object before checking for permissions on the Object. In the case of hierarchical permissions (Admins, Builders etc), the Account permission will always be used (this stops an Account from escalating their permission by puppeting a high-level Character).  If the permission looked for is not in the hierarchy, an exact match is required, first on the Account and if not found there (or if no Account is connected), then on the Object itself. 

Here is how you use `perm` to give an account more permissions: 

     perm/account Tommy = Builders
     perm/account/del Tommy = Builders # remove it again

Note the use of the `/account` switch. It means you assign the permission to the [Accounts]([Accounts](Account)) Tommy instead of any [Character](Objects) that also happens to be named "Tommy". 

Putting permissions on the *Account* guarantees that they are kept, *regardless* of which Character they are currently puppeting. This is especially important to remember when assigning permissions from the *hierarchy tree* - as mentioned above, an Account's permissions will overrule that of its character. So to be sure to avoid confusion you should generally put hierarchy permissions on the Account, not on their Characters (but see also [quelling](Locks#Quelling)).

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

Assume we have two objects - one is ourselves (not superuser) and the other is an [Object](Objects) called `box`. 

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

So the `get` command looks for a lock with the type *get* (not so surprising). It also looks for an [Attribute](Attributes) on the checked object called _get_err_msg_ in order to return a customized error message. Sounds good! Let's start by setting that on the box: 

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
