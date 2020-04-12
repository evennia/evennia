```python
class Documentation:
    RATING = "Exceptional"
```
# Locks

For most games it is a good idea to restrict what people can do. In Evennia such restrictions are applied and checked by something called *locks*. All Evennia entities ([Commands](../../../evennia_core/system/commands/Commands), [Objects](../../../evennia_core/system/objects/Objects), [Scripts](../../../evennia_core/system/scripts/Scripts), [Accounts](../../../evennia_core/system/accounts/Accounts), [Help System](../../../evennia_core/system/help/help-system), [messages](../../../evennia_core/system/channels/messages) and [channels](../../../evennia_core/system/channels/channels)) are accessed through locks. 

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

- [Commands](../../../evennia_core/system/commands/Commands) 
  - `cmd` - this defines who may call this command at all.
- [Objects](../../../evennia_core/system/objects/Objects):
  - `control` - who is the "owner" of the object. Can set locks, delete it etc. Defaults to the creator of the object.
  - `call` - who may call Object-commands stored on this Object except for the Object itself. By default, Objects share their Commands with anyone in the same location (e.g. so you can 'press' a `Button` object in the room). For Characters and Mobs (who likely only use those Commands for themselves and don't want to share them) this should usually be turned off completely, using something like `call:false()`. 
  - `examine` - who may examine this object's properties.
  - `delete` - who may delete the object.
  - `edit` - who may edit properties and attributes of the object.
  - `view` - if the `look` command will display/list this object
  - `get`- who may pick up the object and carry it around.
  - `puppet` - who may "become" this object and control it as their "character".
  - `attrcreate` - who may create new attributes on the object (default True)
- [Characters](../../../evennia_core/system/objects/Characters): 
  - Same as for Objects
- [Exits](../../../evennia_core/system/objects/Exits): 
  - Same as for Objects 
  - `traverse` - who may pass the exit.
- [Accounts](../../../evennia_core/system/accounts/Accounts):
  - `examine` - who may examine the account's properties.
  - `delete` - who may delete the account.
  - `edit` - who may edit the account's attributes and properties.
  - `msg` - who may send messages to the account.
  - `boot` - who may boot the account.
- [Attributes](../../../evennia_core/system/attributes/Attributes): (only checked by `obj.secure_attr`)
  - `attrread` - see/access attribute
  - `attredit` - change/delete attribute
- [Channels](../../../evennia_core/system/channels/channels)
  - `control` - who is administrating the channel. This means the ability to delete the channel, boot listeners etc.
  - `send` - who may send to the channel.
  - `listen` - who may subscribe and listen to the channel.
- [HelpEntry](../../../evennia_core/system/help/Help-System):
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
- `perm(perm)` - this tries to match a given `permission` property, on an Account firsthand, on a Character second. See [below](../locks/Locks#permissions).
- `perm_above(perm)` - like `perm` but requires a "higher" permission level than the one given.
- `id(num)/dbref(num)` - checks so the access_object has a certain dbref/id.
- `attr(attrname)` - checks if a certain [Attribute](../../../evennia_core/system/attributes/Attributes) exists on accessing_object.
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

Evennia sets up a few basic locks on all new objects and accounts (if we didn't, noone would have any access to anything from the start).  This is all defined in the root [Typeclasses](../../../evennia_core/system/typeclasses/Typeclasses) of the respective entity, in the hook method `basetype_setup()` (which you usually don't want to edit unless you want to change how basic stuff like rooms and exits store their internal variables). This is called once, before `at_object_creation`, so just put them in the latter method on your child object to change the default. Also creation commands like `create` changes the locks of objects you create - for example it sets the `control` lock_type so as to allow you, its creator, to control and delete the object.

## Permissions

[Read more](permissions) about how to access or change available permissions.