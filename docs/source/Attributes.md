# Attributes


When performing actions in Evennia it is often important that you store data for later. If you write
a menu system, you have to keep track of the current location in the menu tree so that the player
can give correct subsequent commands. If you are writing a combat system, you might have a
combattant's next roll get easier dependent on if their opponent failed. Your characters will
probably need to store roleplaying-attributes like strength and agility. And so on.

[Typeclassed](Typeclasses) game entities ([Accounts](Accounts), [Objects](Objects),
[Scripts](Scripts) and [Channels](Communications)) always have *Attributes* associated with them.
Attributes are used to store any type of data 'on' such entities. This is different from storing
data in properties already defined on entities (such as `key` or `location`) - these have very
specific names and require very specific types of data (for example you couldn't assign a python
*list* to the `key` property no matter how hard you tried).  `Attributes` come into play when you
want to assign arbitrary data to arbitrary names.

**Attributes are _not_ secure by default and any player may be able to change them unless you [prevent this behavior](#locking-and-checking-attributes).**

## The .db and .ndb shortcuts

To save persistent data on a Typeclassed object you normally use the `db` (DataBase) operator. Let's
try to save some data to a *Rose* (an [Object](Objects)):

```python
    # saving
    rose.db.has_thorns = True
    # getting it back
    is_ouch = rose.db.has_thorns

```

This looks like any normal Python assignment, but that `db` makes sure that an *Attribute* is
created behind the scenes and is stored in the database. Your rose will continue to have thorns
throughout the life of the server now, until you deliberately remove them.

To be sure to save **non-persistently**, i.e. to make sure NOT to create a database entry, you use
`ndb` (NonDataBase). It works in the same way:

```python
    # saving
    rose.ndb.has_thorns = True
    # getting it back
    is_ouch = rose.ndb.has_thorns
```

Technically, `ndb` has nothing to do with `Attributes`, despite how similar they look. No
`Attribute` object is created behind the scenes when using `ndb`. In fact the database is not
invoked at all since we are not interested in persistence.  There is however an important reason to
use `ndb` to store data rather than to just store variables direct on entities - `ndb`-stored data
is tracked by the server and will not be purged in various cache-cleanup operations Evennia may do
while it runs. Data stored on `ndb` (as well as `db`) will also be easily listed by example the
`@examine` command.

You can also `del` properties on `db` and `ndb` as normal. This will for example delete an `Attribute`:

```python
    del rose.db.has_thorns
```

Both `db` and `ndb` defaults to offering an `all()` method on themselves. This returns all
associated attributes or non-persistent properties.

```python
     list_of_all_rose_attributes = rose.db.all()
     list_of_all_rose_ndb_attrs = rose.ndb.all()
```

If you use `all` as the name of an attribute, this will be used instead. Later deleting your custom
`all` will return the default behaviour.

## The AttributeHandler

The `.db` and `.ndb` properties are very convenient but if you don't know the name of the Attribute
beforehand they cannot be used.  Behind the scenes `.db` actually accesses the `AttributeHandler`
which sits on typeclassed entities as the `.attributes` property. `.ndb` does the same for the
`.nattributes` property.

The handlers have normal access methods that allow you to manage and retrieve `Attributes` and
`NAttributes`:

- `has('attrname')` - this checks if the object has an Attribute with this key. This is equivalent
  to doing `obj.db.attrname`.
- `get(...)` - this retrieves the given Attribute. Normally the `value` property of the Attribute is
  returned, but the method takes keywords for returning the Attribute object itself. By supplying an
  `accessing_object` to the call one can also make sure to check permissions before modifying
  anything.
- `add(...)` - this adds a new Attribute to the object. An optional [lockstring](Locks) can be
  supplied here to restrict future access and also the call itself may be checked against locks.
- `remove(...)` - Remove the given Attribute. This can optionally be made to check for permission
  before performing the deletion.  - `clear(...)`  - removes all Attributes from object.
- `all(...)` - returns all Attributes (of the given category) attached to this object.

See [this section](https://github.com/evennia/evennia/wiki/Attributes#locking-and-checking-attributes) for more about locking down Attribute
access and editing. The `Nattribute` offers no concept of access control.

Some examples:

```python
    import evennia
    obj = evennia.search_object("MyObject")

    obj.attributes.add("test", "testvalue")
    print(obj.db.test)                 # prints "testvalue"
    print(obj.attributes.get("test"))  #       "
    print(obj.attributes.all())        # prints [<AttributeObject>]
    obj.attributes.remove("test")
```


## Properties of Attributes

An Attribute object is stored in the database. It has the following properties:

- `key` - the name of the Attribute. When doing e.g. `obj.db.attrname = value`, this property is set
  to `attrname`.
- `value` - this is the value of the Attribute. This value can be anything which can be pickled -
  objects, lists, numbers or what have you (see
  [this section](Attributes#What_types_of_data_can_I_save_in_an_Attribute) for more info). In the example
  `obj.db.attrname = value`, the `value` is stored here.
- `category` - this is an optional property that is set to None for most Attributes. Setting this
  allows to use Attributes for different functionality. This is usually not needed unless you want
  to use Attributes for very different functionality ([Nicks](Nicks) is an example of using Attributes
  in this way). To modify this property you need to use the [Attribute Handler](Attributes#The_Attribute_Handler).
- `strvalue` - this is a separate value field that only accepts strings. This severely limits the
  data possible to store, but allows for easier database lookups. This property is usually not used
  except when re-using Attributes for some other purpose ([Nicks](Nicks) use it). It is only
  accessible via the [Attribute Handler](Attributes#The_Attribute_Handler).

There are also two special properties:

- `attrtype` - this is used internally by Evennia to separate [Nicks](Nicks), from Attributes (Nicks
  use Attributes behind the scenes).
- `model` - this is a *natural-key* describing the model this Attribute is attached to. This is on
  the form *appname.modelclass*, like `objects.objectdb`. It is used by the Attribute and
  NickHandler to quickly sort matches in the database.  Neither this nor `attrtype` should normally
  need to be modified.

Non-database attributes have no equivalence to `category` nor `strvalue`, `attrtype` or `model`.

## Persistent vs non-persistent

So *persistent* data means that your data will survive a server reboot, whereas with
*non-persistent* data it will not ...

... So why would you ever want to use non-persistent data? The answer is, you don't have to. Most of
the time you really want to save as much as you possibly can. Non-persistent data is potentially
useful in a few situations though.

- You are worried about database performance. Since Evennia caches Attributes very aggressively,
  this is not an issue unless you are reading *and* writing to your Attribute very often (like many
  times per second). Reading from an already cached Attribute is as fast as reading any Python
  property. But even then this is not likely something to worry about: Apart from Evennia's own
  caching, modern database systems  themselves also cache data very efficiently for speed. Our default
  database even runs completely in RAM if possible, alleviating much of the need to write to disk
  during heavy loads.
- A more valid reason for using non-persistent data is if you *want* to lose your state when logging
  off. Maybe you are storing throw-away data that are re-initialized at server startup. Maybe you
  are implementing some caching of your own. Or maybe you are testing a buggy [Script](Scripts) that
  does potentially harmful stuff to your character object. With non-persistent storage you can be sure
  that whatever is messed up, it's nothing a server reboot can't clear up.
- NAttributes have no restrictions at all on what they can store (see next section), since they
  don't need to worry about being saved to the database - they work very well for temporary storage.
- You want to implement a fully or partly *non-persistent world*. Who are we to argue with your
  grand vision!

## What types of data can I save in an Attribute?

> None of the following affects NAttributes, which does not invoke the database at all. There are no
> restrictions to what can be stored in a NAttribute.

The database doesn't know anything about Python objects, so Evennia must *serialize* Attribute
values into a string representation in order to store it to the database. This is done using the
`pickle` module of Python (the only exception is if you use the `strattr` keyword of the
AttributeHandler to save to the `strvalue` field of the Attribute. In that case you can only save
*strings* which will not be pickled).

It's important to note that when you access the data in an Attribute you are *always* de-serializing
it from the database representation every time. This is because we allow for storing
database-entities in Attributes too. If we cached it as its Python form, we might end up with
situations where the database entity was deleted since we last accessed the Attribute.
De-serializing data with a database-entity in it means querying the database for that object and
making sure it still exists (otherwise it will be set to `None`). Performance-wise this is usually
not a big deal. But if you are accessing the Attribute as part of some big loop or doing a large
amount of reads/writes you should first extract it to a temporary variable, operate on *that* and
then save the result back to the Attribute. If you are storing a more complex structure like a
`dict` or a `list` you should make sure to "disconnect" it from the database before looping over it,
as mentioned in the [Retrieving Mutable Objects](#retrieving-mutable-objects) section below.

### Storing single objects

With a single object, we mean anything that is *not iterable*, like numbers, strings or custom class instances without the `__iter__` method.

* You can generally store any non-iterable Python entity that can be
  [pickled](http://docs.python.org/library/pickle.html).
* Single database objects/typeclasses can be stored as any other in the Attribute. These can
  normally *not* be pickled, but Evennia will behind the scenes convert them to an internal
  representation using their classname, database-id and creation-date with a microsecond precision,
  guaranteeing you get the same object back when you access the Attribute later.
* If you *hide* a database object inside a non-iterable custom class (like stored as a variable
  inside it), Evennia will not know it's there and won't convert it safely. Storing classes with
  such hidden database objects is *not* supported and will lead to errors!

```python
# Examples of valid single-value  attribute data:
obj.db.test1 = 23
obj.db.test1 = False
# a database object (will be stored as an internal representation)
obj.db.test2 = myobj

# example of an invalid, "hidden" dbobject
class Invalid(object):
    def __init__(self, dbobj):
        # no way for Evennia to know this is a dbobj
        self.dbobj = dbobj
invalid = Invalid(myobj)
obj.db.invalid = invalid # will cause error!
```

### Storing multiple objects

This means storing objects in a collection of some kind and are examples of *iterables*, pickle-able
entities you can loop over in a for-loop. Attribute-saving supports the following iterables:

* [Tuples](https://docs.python.org/2/library/functions.html#tuple), like `(1,2,"test", <dbobj>)`.
* [Lists](https://docs.python.org/2/tutorial/datastructures.html#more-on-lists), like `[1,2,"test", <dbobj>]`.
* [Dicts](https://docs.python.org/2/tutorial/datastructures.html#dictionaries), like `{1:2, "test":<dbobj>]`.
* [Sets](https://docs.python.org/2/tutorial/datastructures.html#sets), like `{1,2,"test",<dbobj>}`.
* [collections.OrderedDict](https://docs.python.org/2/library/collections.html#collections.OrderedDict), like `OrderedDict((1,2), ("test", <dbobj>))`.
* [collections.Deque](https://docs.python.org/2/library/collections.html#collections.deque), like `deque((1,2,"test",<dbobj>))`.
* *Nestings* of any combinations of the above, like lists in dicts or an OrderedDict of tuples, each containing dicts, etc.
* All other iterables (i.e. entities with the `__iter__` method) will be converted to a *list*.
  Since you can use any combination of the above iterables, this is generally not much of a
  limitation.

Any entity listed in the [Single object](Attributes#Storing-Single-Objects) section above can be stored in the iterable.

> As mentioned in the previous section, database entities (aka typeclasses) are not possible to
> pickle. So when storing an iterable, Evennia must recursively traverse the iterable *and all its
> nested sub-iterables* in order to find eventual database objects to convert. This is a very fast
> process but for efficiency you may want to avoid too deeply nested structures if you can.

```python
# examples of valid iterables to store
obj.db.test3 = [obj1, 45, obj2, 67]
# a dictionary
obj.db.test4 = {'str':34, 'dex':56, 'agi':22, 'int':77}
# a mixed dictionary/list
obj.db.test5 = {'members': [obj1,obj2,obj3], 'enemies':[obj4,obj5]}
# a tuple with a list in it
obj.db.test6 = (1,3,4,8, ["test", "test2"], 9)
# a set
obj.db.test7 = set([1,2,3,4,5])
# in-situ manipulation
obj.db.test8 = [1,2,{"test":1}]
obj.db.test8[0] = 4
obj.db.test8[2]["test"] = 5
# test8 is now [4,2,{"test":5}]
```

### Retrieving Mutable objects

A side effect of the way Evennia stores Attributes is that *mutable* iterables (iterables that can
be modified in-place after they were created, which is everything except tuples) are handled by
custom objects called `_SaverList`, `_SaverDict` etc. These `_Saver...` classes behave just like the
normal variant except that they are aware of the database and saves to it whenever new data gets
assigned to them. This is what allows you to do things like `self.db.mylist[7] = val` and be sure
that the new version of list is saved. Without this you would have to load the list into a temporary
variable, change it and then re-assign it to the Attribute in order for it to save.

There is however an important thing to remember. If you retrieve your mutable iterable into another
variable, e.g. `mylist2 = obj.db.mylist`, your new variable (`mylist2`) will *still* be a
`_SaverList`. This means it will continue to save itself to the database whenever it is updated!


```python
     obj.db.mylist = [1,2,3,4]
     mylist = obj.db.mylist
     mylist[3] = 5 # this will also update database
     print(mylist) # this is now [1,2,3,5]
     print(obj.db.mylist) # this is also [1,2,3,5]
```

To "disconnect" your extracted mutable variable from the database you simply need to convert the
`_Saver...` iterable to a normal Python structure. So to convert a `_SaverList`, you use the
`list()` function, for a `_SaverDict` you use `dict()` and so on.

```python
     obj.db.mylist = [1,2,3,4]
     mylist = list(obj.db.mylist) # convert to normal list
     mylist[3] = 5
     print(mylist) # this is now [1,2,3,5]
     print(obj.db.mylist) # this is still [1,2,3,4]
```

A further problem comes with *nested mutables*, like a dict containing lists of dicts or something
like that. Each of these nested mutables would be `_Saver*` structures connected to the database and
disconnecting the outermost one of them would not disconnect those nested within. To make really
sure you disonnect a nested structure entirely from the database, Evennia provides a special
function `evennia.utils.dbserialize.deserialize`:

```
from evennia.utils.dbserialize import deserialize

decoupled_mutables = deserialize(nested_mutables)

```

The result of this operation will be a structure only consisting of normal Python mutables (`list`
instead of `_SaverList` and so on).


Remember, this is only valid for *mutable* iterables.
[Immutable](http://en.wikipedia.org/wiki/Immutable) objects (strings, numbers, tuples etc) are
already disconnected from the database from the onset.

```python
     obj.db.mytup = (1,2,[3,4])
     obj.db.mytup[0] = 5 # this fails since tuples are immutable

     # this works but will NOT update database since outermost is a tuple
     obj.db.mytup[2][1] = 5
     print(obj.db.mytup[2][1]) # this still returns 4, not 5

     mytup1 = obj.db.mytup # mytup1 is already disconnected from database since outermost
                           # iterable is a tuple, so we can edit the internal list as we want
                           # without affecting the database.
```

> Attributes will fetch data fresh from the database whenever you read them, so
> if you are performing big operations on a mutable Attribute property (such as looping over a list
> or dict) you should make sure to "disconnect" the Attribute's value first and operate on this
> rather than on the Attribute. You can gain dramatic speed improvements to big loops this
> way.


## Locking and checking Attributes

Attributes are normally not locked down by default, but you can easily change that for individual
Attributes (like those that may be game-sensitive in games with user-level building).

First you need to set a *lock string* on your Attribute. Lock strings are specified [Locks](Locks). The relevant lock types are

- `attrread` - limits who may read the value of the Attribute
- `attredit` - limits who may set/change this Attribute

You cannot use the `db` handler to modify Attribute object (such as setting a lock on them) - The
`db` handler will return the Attribute's *value*, not the Attribute object itself. Instead you use
the AttributeHandler and set it to return the object instead of the value:

```python
     lockstring = "attread:all();attredit:perm(Admins)"
     obj.attributes.get("myattr", return_obj=True).locks.add(lockstring)
```

Note the `return_obj` keyword which makes sure to return the `Attribute` object so its LockHandler
could be accessed.

A lock is no good if nothing checks it -- and by default Evennia does not check locks on Attributes.
You have to add a check to your commands/code wherever it fits (such as before setting an
Attribute).

```python
    # in some command code where we want to limit
    # setting of a given attribute name on an object
    attr = obj.attributes.get(attrname,
                              return_obj=True,
                              accessing_obj=caller,
                              default=None,
                              default_access=False)
    if not attr:
        caller.msg("You cannot edit that Attribute!")
        return
    # edit the Attribute here
```

The same keywords are available to use with `obj.attributes.set()` and `obj.attributes.remove()`,
those will check for the `attredit` lock type.
