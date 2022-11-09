# Attributes

```{code-block}
:caption: In-game
> set obj/myattr = "test"
```
```{code-block} python
:caption: In-code, using the .db wrapper
obj.db.foo = [1, 2, 3, "bar"]
value = obj.db.foo
```
```{code-block} python
:caption: In-code, using the .attributes handler
obj.attributes.add("myattr", 1234, category="bar")
value = attributes.get("myattr", category="bar")
```
```{code-block} python
:caption: In-code, using `AttributeProperty` at class level
from evennia import DefaultObject
from evennia import AttributeProperty

class MyObject(DefaultObject):
    foo = AttributeProperty(default=[1, 2, 3, "bar"])
    myattr = AttributeProperty(100, category='bar')

```

_Attributes_ allow you to to store arbitrary data on objects and make sure the data survives a server reboot. An Attribute can store pretty much any
Python data structure and data type, like numbers, strings, lists, dicts etc. You can also
store (references to) database objects like characters and rooms.

- [What can be stored in an Attribute](#what-types-of-data-can-i-save-in-an-attribute) is a must-read to avoid being surprised, also for experienced developers. Attributes can store _almost_ everything
  but you need to know the quirks.
- [NAttributes](#in-memory-attributes-nattributes) are the in-memory, non-persistent
  siblings of Attributes.
- [Managing Attributes In-game](#managing-attributes-in-game) for in-game builder commands.

## Managing Attributes in Code

Attributes are usually handled in code. All [Typeclassed](./Typeclasses.md) entities
([Accounts](./Accounts.md), [Objects](./Objects.md), [Scripts](./Scripts.md) and
[Channels](./Channels.md)) can (and usually do) have Attributes associated with them. There
are three ways to manage Attributes, all of which can be mixed.

- [Using the `.db` property shortcut](#using-db)
- [Using the `.attributes` manager (`AttributeManager`)](#using-attributes)
- [Using `AttributeProperty` for assigning Attributes in a way similar to Django fields](#using-attributeproperty)

### Using .db

The simplest way to get/set Attributes is to use the `.db` shortcut. This allows for setting and getting Attributes that lack a _category_ (having category `None`)

```python
import evennia

obj = evennia.create_object(key="Foo")

obj.db.foo1 = 1234
obj.db.foo2 = [1, 2, 3, 4]
obj.db.weapon = "sword"
obj.db.self_reference = obj   # stores a reference to the obj

# (let's assume a rose exists in-game)
rose = evennia.search_object(key="rose")[0]  # returns a list, grab 0th element
rose.db.has_thorns = True

# retrieving
val1 = obj.db.foo1
val2 = obj.db.foo2
weap = obj.db.weapon
myself = obj.db.self_reference  # retrieve reference from db, get object back

is_ouch = rose.db.has_thorns

# this will return None, not AttributeError!
not_found = obj.db.jiwjpowiwwerw

# returns all Attributes on the object
obj.db.all

# delete an Attribute
del obj.db.foo2
```
Trying to access a non-existing Attribute will never lead to an `AttributeError`. Instead
you will get `None` back. The special `.db.all` will return a list of all Attributes on
the object. You can replace this with your own Attribute `all` if you want, it will replace the
default `all` functionality until you delete it again.

### Using .attributes

If you want to group your Attribute in a category, or don't know the name of the Attribute beforehand, you can make use of
the [AttributeHandler](evennia.typeclasses.attributes.AttributeHandler), available as `.attributes` on all typeclassed entities. With no extra keywords, this is identical to using the `.db` shortcut (`.db` is actually using the `AttributeHandler` internally):

```python
is_ouch = rose.attributes.get("has_thorns")

obj.attributes.add("helmet", "Knight's helmet")
helmet = obj.attributes.get("helmet")

# you can give space-separated Attribute-names (can't do that with .db)
obj.attributes.add("my game log", "long text about ...")
```

By using a category you can separate same-named Attributes on the same object to help organization.

```python
# store (let's say we have gold_necklace and ringmail_armor from before)
obj.attributes.add("neck", gold_necklace, category="clothing")
obj.attributes.add("neck", ringmail_armor, category="armor")

# retrieve later - we'll get back gold_necklace and ringmail_armor
neck_clothing = obj.attributes.get("neck", category="clothing")
neck_armor = obj.attributes.get("neck", category="armor")
```

If you don't specify a category, the Attribute's `category` will be `None` and can thus also be found via `.db`. `None` is considered a category of its own, so you won't find `None`-category Attributes mixed with Attributes having categories.

Here are the methods of the `AttributeHandler`. See
the [AttributeHandler API](evennia.typeclasses.attributes.AttributeHandler) for more details.

- `has(...)` - this checks if the object has an Attribute with this key. This is equivalent
  to doing `obj.db.attrname` except you can also check for a specific `category.
- `get(...)` - this retrieves the given Attribute. You can also provide a `default` value to return
  if the Attribute is not defined (instead of None). By supplying an
  `accessing_object` to the call one can also make sure to check permissions before modifying
  anything. The `raise_exception` kwarg allows you to raise an `AttributeError` instead of returning
  `None` when you access a non-existing `Attribute`. The `strattr` kwarg tells the system to store
  the Attribute as a raw string rather than to pickle it. While an optimization this should usually
  not be used unless the Attribute is used for some particular, limited purpose.
- `add(...)` - this adds a new Attribute to the object. An optional [lockstring](./Locks.md) can be
  supplied here to restrict future access and also the call itself may be checked against locks.
- `remove(...)` - Remove the given Attribute. This can optionally be made to check for permission
  before performing the deletion.  - `clear(...)`  - removes all Attributes from object.
- `all(category=None)` - returns all Attributes (of the given category) attached to this object.

Examples:

```python
try:
  # raise error if Attribute foo does not exist
  val = obj.attributes.get("foo", raise_exception=True):
except AttributeError:
   # ...

# return default value if foo2 doesn't exist
val2 = obj.attributes.get("foo2", default=[1, 2, 3, "bar"])

# delete foo if it exists (will silently fail if unset, unless
# raise_exception is set)
obj.attributes.remove("foo")

# view all clothes on obj
all_clothes = obj.attributes.all(category="clothes")
```

### Using AttributeProperty

The third way to set up an Attribute is to use an `AttributeProperty`. This
is done on the _class level_ of your typeclass and allows you to treat Attributes a bit like Django database Fields. Unlike using `.db` and `.attributes`, an `AttributeProperty` can't be created on the fly, you must assign it in the class code.

```python
# mygame/typeclasses/characters.py

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

class Character(DefaultCharacter):

    strength = AttributeProperty(10, category='stat')
    constitution = AttributeProperty(11, category='stat')
    agility = AttributeProperty(12, category='stat')
    magic = AttributeProperty(13, category='stat')

    sleepy = AttributeProperty(False, autocreate=False)
    poisoned = AttributeProperty(False, autocreate=False)

    def at_object_creation(self):
      # ...
```

When a new instance of the class is created, new `Attributes` will be created with the value and category given.

With `AttributeProperty`'s set up like this, one can access the underlying `Attribute` like a regular property on the created object:

```python
char = create_object(Character)

char.strength   # returns 10
char.agility = 15  # assign a new value (category remains 'stat')

char.db.magic  # returns None (wrong category)
char.attributes.get("agility", category="stat")  # returns 15

char.db.sleepy # returns None because autocreate=False (see below)

```

```{warning}
Be careful to not assign AttributeProperty's to names of properties and methods already existing on the class, like 'key' or 'at_object_creation'. That could lead to very confusing errors.
```

The `autocreate=False` (default is `True`) used for `sleepy` and `poisoned` is worth a closer explanation. When `False`, _no_ Attribute will be auto-created for these AttributProperties unless they are _explicitly_ set.
The advantage of not creating an Attribute is that the default value given to `AttributeProperty` is returned with no database access unless you change it. This also means that if you want to change the default later, all entities previously create will inherit the new default.
The drawback is that without a database precense you can't find the Attribute via `.db` and `.attributes.get` (or by querying for it in other ways in the database):

```python
char.sleepy   # returns False, no db access

char.db.sleepy   # returns None - no Attribute exists
char.attributes.get("sleepy")  # returns None too

char.sleepy = True  # now an Attribute is created
char.db.sleepy   # now returns True!
char.attributes.get("sleepy")  # now returns True

char.sleepy  # now returns True, involves db access

```

You can e.g. `del char.strength` to set the value back to the default (the value defined
in the `AttributeProperty`).

See the [AttributeProperty API](evennia.typeclasses.attributes.AttributeProperty) for more details on how to create it with special options, like giving access-restrictions.


## Managing Attributes in-game

Attributes are mainly used by code. But one can also allow the builder to use Attributes to
'turn knobs' in-game. For example a builder could want to manually tweak the "level" Attribute of an
enemy NPC to lower its difficuly.

When setting Attributes this way, you are severely limited in what can be stored - this is because
giving players (even builders) the ability to store arbitrary Python would be a severe security
problem.

In game you can set an Attribute like this:

    set myobj/foo = "bar"

To view, do

    set myobj/foo

or see them together with all object-info with

    examine myobj

The first `set`-example will store a new Attribute `foo` on the object `myobj` and give it the
value "bar".
You can store numbers, booleans, strings, tuples, lists and dicts this way. But if
you store a list/tuple/dict they must be proper Python structures and may _only_ contain strings
or numbers. If you try to insert an unsupported structure, the input will be converted to a
string.

    set myobj/mybool = True
    set myobj/mybool = True
    set myobj/mytuple = (1, 2, 3, "foo")
    set myobj/mylist = ["foo", "bar", 2]
    set myobj/mydict = {"a": 1, "b": 2, 3: 4}
    set mypobj/mystring = [1, 2, foo]   # foo is invalid Python (no quotes)

For the last line you'll get a warning and the value instead will be saved as a string `"[1, 2, foo]"`.

## Locking and checking Attributes

While the `set` command is limited to builders, individual Attributes are usually not
locked down. You may want to lock certain sensitive Attributes, in particular for games
where you allow player building. You can add such limitations by adding a [lock string](./Locks.md)
to your Attribute. A NAttribute have no locks.

The relevant lock types are

- `attrread` - limits who may read the value of the Attribute
- `attredit` - limits who may set/change this Attribute

You must use the `AttributeHandler` to assign the lockstring to the Attribute:

```python
lockstring = "attread:all();attredit:perm(Admins)"
obj.attributes.add("myattr", "bar", lockstring=lockstring)"
```

If you already have an Attribute and want to add a lock in-place you can do so
by having the `AttributeHandler` return the `Attribute` object itself (rather than
its value) and then assign the lock to it directly:

```python
     lockstring = "attread:all();attredit:perm(Admins)"
     obj.attributes.get("myattr", return_obj=True).locks.add(lockstring)
```

Note the `return_obj` keyword which makes sure to return the `Attribute` object so its LockHandler
could be accessed.

A lock is no good if nothing checks it -- and by default Evennia does not check locks on Attributes.
To check the `lockstring` you provided, make sure you include `accessing_obj` and set
`default_access=False` as you make a `get` call.

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

## What types of data can I save in an Attribute?

The database doesn't know anything about Python objects, so Evennia must *serialize* Attribute
values into a string representation before storing it to the database. This is done using the
[pickle](https://docs.python.org/library/pickle.html) module of Python.

> The only exception is if you use the `strattr` keyword of the
`AttributeHandler` to save to the `strvalue` field of the Attribute. In that case you can _only_ save
*strings* and those will not be pickled).

### Storing single objects

With a single object, we mean anything that is *not iterable*, like numbers,
strings or custom class instances without the `__iter__` method.

* You can generally store any non-iterable Python entity that can be _pickled_.
* Single database objects/typeclasses can be stored, despite them normally not
  being possible to pickle. Evennia will convert them to an internal
  representation using theihr classname, database-id and creation-date with a
  microsecond precision. When retrieving, the object instance will be re-fetched
  from the database using this information.
* If you 'hide' a db-obj as a property on a custom class, Evennia will not be
  able to find it to serialize it. For that you need to help it out (see below).

```{code-block} python
:caption: Valid assignments

# Examples of valid single-value  attribute data:
obj.db.test1 = 23
obj.db.test1 = False
# a database object (will be stored as an internal representation)
obj.db.test2 = myobj
```

As mentioned, Evennia will not be able to automatically serialize db-objects
'hidden' in arbitrary properties on an object. This will lead to an error
when saving the Attribute.

```{code-block} python
:caption: Invalid, 'hidden' dbobject
# example of storing an invalid, "hidden" dbobject in Attribute
class Container:
    def __init__(self, mydbobj):
        # no way for Evennia to know this is a database object!
        self.mydbobj = mydbobj

# let's assume myobj is a db-object
container = Container(myobj)
obj.db.mydata = container  # will raise error!

```

By adding two methods `__serialize_dbobjs__` and `__deserialize_dbobjs__` to the
object you want to save, you can pre-serialize and post-deserialize all 'hidden'
objects before Evennia's main serializer gets to work. Inside these methods, use Evennia's
[evennia.utils.dbserialize.dbserialize](evennia.utils.dbserialize.dbserialize) and
[dbunserialize](evennia.utils.dbserialize.dbunserialize) functions to safely
serialize the db-objects you want to store.

```{code-block} python
:caption: Fixing an invalid 'hidden' dbobj for storing in Attribute

from evennia.utils import dbserialize  # important

class Container:
    def __init__(self, mydbobj):
        # A 'hidden' db-object
        self.mydbobj = mydbobj

    def __serialize_dbobjs__(self):
        """This is called before serialization and allows
        us to custom-handle those 'hidden' dbobjs"""
        self.mydbobj = dbserialize.dbserialize(self.mydbobj

    def __deserialize_dbobjs__(self):
        """This is called after deserialization and allows you to
        restore the 'hidden' dbobjs you serialized before"""
        if isinstance(self.mydbobj, bytes):
            # make sure to check if it's bytes before trying dbunserialize
            self.mydbobj = dbserialize.dbunserialize(self.mydbobj)

# let's assume myobj is a db-object
container = Container(myobj)
obj.db.mydata = container  # will now work fine!
```

> Note the extra check in `__deserialize_dbobjs__` to make sure the thing you
> are deserializing is a `bytes` object. This is needed because the Attribute's
> cache reruns deserializations in some situations when the data was already
> once deserialized. If you see errors in the log saying
> `Could not unpickle data for storage: ...`, the reason is
> likely that you forgot to add this check.


### Storing multiple objects

This means storing objects in a collection of some kind and are examples of *iterables*, pickle-able
entities you can loop over in a for-loop. Attribute-saving supports the following iterables:

* [Tuples](https://docs.python.org/2/library/functions.html#tuple), like `(1,2,"test", <dbobj>)`.
* [Lists](https://docs.python.org/2/tutorial/datastructures.html#more-on-lists), like `[1,2,"test", <dbobj>]`.
* [Dicts](https://docs.python.org/2/tutorial/datastructures.html#dictionaries), like `{1:2, "test":<dbobj>]`.
* [Sets](https://docs.python.org/2/tutorial/datastructures.html#sets), like `{1,2,"test",<dbobj>}`.
* [collections.OrderedDict](https://docs.python.org/2/library/collections.html#collections.OrderedDict),
like `OrderedDict((1,2), ("test", <dbobj>))`.
* [collections.Deque](https://docs.python.org/2/library/collections.html#collections.deque), like `deque((1,2,"test",<dbobj>))`.
* *Nestings* of any combinations of the above, like lists in dicts or an OrderedDict of tuples, each
containing dicts, etc.
* All other iterables (i.e. entities with the `__iter__` method) will be converted to a *list*.
  Since you can use any combination of the above iterables, this is generally not much of a
  limitation.

Any entity listed in the [Single object](./Attributes.md#storing-single-objects) section above can be
stored in the iterable.

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
obj.db.test6 = (1, 3, 4, 8, ["test", "test2"], 9)
# a set
obj.db.test7 = set([1, 2, 3, 4, 5])
# in-situ manipulation
obj.db.test8 = [1, 2, {"test":1}]
obj.db.test8[0] = 4
obj.db.test8[2]["test"] = 5
# test8 is now [4,2,{"test":5}]
```

Note that if make some advanced iterable object, and store an db-object on it in
a way such that it is _not_ returned by iterating over it, you have created a
'hidden' db-object. See [the previous section](#storing-single-objects) for how
to tell Evennia how to serialize such hidden objects safely.


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
obj.db.mylist = [1, 2, 3, 4]
mylist = obj.db.mylist

mylist[3] = 5  # this will also update database

print(mylist)  # this is now [1, 2, 3, 5]
print(obj.db.mylist)  # now also [1, 2, 3, 5]
```

When you extract your mutable Attribute data into a variable like `mylist`, think of it as getting a _snapshot_
of the variable. If you update the snapshot, it will save to the database, but this change _will not propagate to
any other snapshots you may have done previously_.

```python
obj.db.mylist = [1, 2, 3, 4]
mylist1 = obj.db.mylist
mylist2 = obj.db.mylist
mylist1[3] = 5

print(mylist1)  # this is now [1, 2, 3, 5]
print(obj.db.mylist)  # also updated to [1, 2, 3, 5]

print(mylist2)  # still [1, 2, 3, 4]  !

```

```{sidebar}
Remember, the complexities of this section only relate to *mutable* iterables - things you can update
in-place, like lists and dicts. [Immutable](https://en.wikipedia.org/wiki/Immutable) objects (strings,
numbers, tuples etc) are already disconnected from the database from the onset.
```

To avoid confusion with mutable Attributes, only work with one variable (snapshot) at a time and save
back the results as needed.

You can also choose to "disconnect" the Attribute entirely from the
database with the help of the `.deserialize()` method:

```python
obj.db.mylist = [1, 2, 3, 4, {1: 2}]
mylist = obj.db.mylist.deserialize()
```

The result of this operation will be a structure only consisting of normal Python mutables (`list`
instead of `_SaverList`, `dict` instead of `_SaverDict` and so on). If you update it, you need to
explicitly save it back to the Attribute for it to save.

## Properties of Attributes

An `Attribute` object is stored in the database. It has the following properties:

- `key` - the name of the Attribute. When doing e.g. `obj.db.attrname = value`, this property is set
  to `attrname`.
- `value` - this is the value of the Attribute. This value can be anything which can be pickled -
  objects, lists, numbers or what have you (see
  [this section](./Attributes.md#what-types-of-data-can-i-save-in-an-attribute) for more info). In the
  example
  `obj.db.attrname = value`, the `value` is stored here.
- `category` - this is an optional property that is set to None for most Attributes. Setting this
  allows to use Attributes for different functionality. This is usually not needed unless you want
  to use Attributes for very different functionality ([Nicks](./Nicks.md) is an example of using
  Attributes in this way). To modify this property you need to use the [Attribute Handler](#attributes)
- `strvalue` - this is a separate value field that only accepts strings. This severely limits the
  data possible to store, but allows for easier database lookups. This property is usually not used
  except when re-using Attributes for some other purpose ([Nicks](./Nicks.md) use it). It is only
  accessible via the [Attribute Handler](#attributes).

There are also two special properties:

- `attrtype` - this is used internally by Evennia to separate [Nicks](./Nicks.md), from Attributes (Nicks
  use Attributes behind the scenes).
- `model` - this is a *natural-key* describing the model this Attribute is attached to. This is on
  the form *appname.modelclass*, like `objects.objectdb`. It is used by the Attribute and
  NickHandler to quickly sort matches in the database.  Neither this nor `attrtype` should normally
  need to be modified.

Non-database attributes are not stored in the database and have no equivalence
to `category` nor `strvalue`, `attrtype` or `model`.

## In-memory Attributes (NAttributes)

_NAttributes_ (short of Non-database Attributes) mimic Attributes in most things except they
are **non-persistent** - they will _not_ survive a server reload.

- Instead of `.db` use `.ndb`.
- Instead of `.attributes` use `.nattributes`
- Instead of `AttributeProperty`, use `NAttributeProperty`.

```python
    rose.ndb.has_thorns = True
    is_ouch = rose.ndb.has_thorns

    rose.nattributes.add("has_thorns", True)
    is_ouch = rose.nattributes.get("has_thorns")
```

Differences between `Attributes` and `NAttributes`:

- `NAttribute`s are always wiped on a server reload.
- They only exist in memory and never involve the database at all, making them faster to
  access and edit than `Attribute`s.
- `NAttribute`s can store _any_ Python structure (and database object) without limit.
- They can _not_ be set with the standard `set` command (but they are visible with `examine`)

There are some important reasons we recommend using `ndb` to store temporary data rather than
the simple alternative of just storing a variable directly on an object:

- NAttributes are tracked by Evennia and will not be purged in various cache-cleanup operations
  the server may do. So using them guarantees that they'll remain available at least as long as
  the server lives.
- It's a consistent style - `.db/.attributes` and `.ndb/.nattributes` makes for clean-looking code
  where it's clear how long-lived (or not) your data is to be.

### Persistent vs non-persistent

So *persistent* data means that your data will survive a server reboot, whereas with
*non-persistent* data it will not ...

... So why would you ever want to use non-persistent data? The answer is, you don't have to. Most of
the time you really want to save as much as you possibly can. Non-persistent data is potentially
useful in a few situations though.

- You are worried about database performance. Since Evennia caches Attributes very aggressively,
  this is not an issue unless you are reading *and* writing to your Attribute very often (like many
  times per second). Reading from an already cached Attribute is as fast as reading any Python
  property. But even then this is not likely something to worry about: Apart from Evennia's own
  caching, modern database systems  themselves also cache data very efficiently for speed. Our
  default
  database even runs completely in RAM if possible, alleviating much of the need to write to disk
  during heavy loads.
- A more valid reason for using non-persistent data is if you *want* to lose your state when logging
  off. Maybe you are storing throw-away data that are re-initialized at server startup. Maybe you
  are implementing some caching of your own. Or maybe you are testing a buggy [Script](./Scripts.md) that
  does potentially harmful stuff to your character object. With non-persistent storage you can be
  sure that whatever is messed up, it's nothing a server reboot can't clear up.
- `NAttribute`s have no restrictions at all on what they can store, since they
  don't need to worry about being saved to the database - they work very well for temporary storage.
- You want to implement a fully or partly *non-persistent world*. Who are we to argue with your
  grand vision!
