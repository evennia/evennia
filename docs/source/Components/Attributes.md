# Attributes

```{code-block}
:caption: In-game
> set obj/myattr = "test"
``` 
```{code-block} python
:caption: In-code
obj.db.foo = [1,2,3, "bar"]
value = obj.db.foo

obj.attributes.add("myattr", 1234, category="bar")
value = attributes.get("myattr", category="bar")
```

_Attributes_ allow you to to store arbitrary data on objects and make sure the data survives a 
server reboot. An Attribute can store pretty much any 
Python data structure and data type, like numbers, strings, lists, dicts etc. You can also 
store (references to) database objects like characters and rooms.

- [What can be stored in an Attribute](#what-types-of-data-can-i-save-in-an-attribute) is a must-read
  also for experienced developers, to avoid getting surprised. Attributes can store _almost_ everything
  but you need to know the quirks.
- [NAttributes](#in-memory-attributes-nattributes) are the in-memory, non-persistent 
  siblings of Attributes.
- [Managing Attributes In-game](#managing-attributes-in-game) for in-game builder commands.

## Managing Attributes in Code 

Attributes are usually handled in code. All [Typeclassed](./Typeclasses.md) entities 
([Accounts](./Accounts.md), [Objects](./Objects.md), [Scripts](./Scripts.md) and 
[Channels](./Channels.md)) all can (and usually do) have Attributes associated with them. There
are three ways to manage Attributes, all of which can be mixed.

- [Using the `.db` property shortcut](#using-db)
- [Using the `.attributes` manager (`AttributeManager`)](#using-attributes)
- [Using `AttributeProperty` for assigning Attributes in a way similar to Django fields](#using-attributeproperty)

### Using .db

The simplest way to get/set Attributes is to use the `.db` shortcut: 

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

If you don't know the name of the Attribute beforehand you can also use 
the `AttributeHandler`, available as `.attributes`. With no extra keywords this is identical 
to using the `.db` shortcut (`.db` is actually using the `AttributeHandler` internally): 

```python 
is_ouch = rose.attributes.get("has_thorns") 
 
obj.attributes.add("helmet", "Knight's helmet")
helmet = obj.attributes.get("helmet")

# you can give space-separated Attribute-names (can't do that with .db)
obj.attributes.add("my game log", "long text about ...")
```

With the `AttributeHandler` you can also give Attributes a `category`. By using a category you can 
separate same-named Attributes on the same object which can help organization:

```python 
# store (let's say we have gold_necklace and ringmail_armor from before)
obj.attributes.add("neck", gold_necklace, category="clothing")
obj.attributes.add("neck", ringmail_armor, category="armor")

# retrieve later - we'll get back gold_necklace and ringmail_armor
neck_clothing = obj.attributes.get("neck", category="clothing")
neck_armor = obj.attributes.get("neck", category="armor")
```

If you don't specify a category, the Attribute's `category` will be `None`. Note that 
`None` is also considered a category of its own, so you won't find `None`-category Attributes mixed 
with `Attributes` having categories. 

> When using `.db`, you will always use the `None` category.

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

There is a third way to set up an Attribute, and that is by setting up an `AttributeProperty`. This 
is done on the _class level_ of your typeclass and allows you to treat Attributes a bit like Django 
database Fields. 

```python 
# mygame/typeclasses/characters.py

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

class Character(DefaultCharacter):

    strength = AttributeProperty(default=10, category='stat', autocreate=True)
    constitution = AttributeProperty(default=10, category='stat', autocreate=True)
    agility = AttributeProperty(default=10, category='stat', autocreate=True)
    magic = AttributeProperty(default=10, category='stat', autocreate=True)
    
    sleepy = AttributeProperty(default=False)
    poisoned = AttributeProperty(default=False)
    
    def at_object_creation(self): 
      # ... 
``` 

These "Attribute-properties" will be made available to all instances of the class.

```{important} 
If you change the `default` of an `AttributeProperty` (and reload), it will 
change the default for _all_ instances of that class (it will not override 
explicitly changed values).
```

```python
char = evennia.search_object(Character, key="Bob")[0]  # returns list, get 0th element

# get defaults 
strength = char.strength   # will get the default value 10

# assign new values (this will create/update new Attributes)
char.strength = 12
char.constitution = 16
char.agility = 8
char.magic = 2

# you can also do arithmetic etc 
char.magic += 2   # char.magic is now 4

# check Attributes 
strength = char.strength   # this is now 12
is_sleepy = char.sleepy 
is_poisoned = char.poisoned

del char.strength   # wipes the Attribute
strength  = char.strengh  # back to the default (10) again
```

See the [AttributeProperty](evennia.typeclasses.attributes.AttributeProperty) docs for more 
details on arguments.

An `AttributeProperty` will _not_ create an `Attribute` by default. A new `Attribute` will be created
(or an existing one retrieved/updated) will happen differently depending on how the `autocreate`
keyword: 

- If `autocreate=False` (default), an `Attribute` will be created only if the field is explicitly 
  assigned a value (even if the value is the same as the default, such as `char.strength = 10`).
- If `autocreate=True`, an `Attribute` will be created as soon as the field is _accessed_ in 
  any way (So both `strength = char.strength` and `char.strength = 10` will both make sure that
  an `Attribute` exists. 

Example: 

```python 
# in mygame/typeclasses/objects.py 

from evennia import create_object 
from evennia import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty

class Object(DefaultObject):
  
    value_a = AttributeProperty(default="foo")
    value_b = AttributeProperty(default="bar", autocreate=True)
    
obj = evennia.create_object(key="Dummy")

# these will find NO Attributes! 
obj.db.value_a 
obj.attributes.get("value_a")
obj.db.value_b 
obj.attributes.get("value_b")

# get data from attribute-properties
vala = obj.value_a  # returns "foo"
valb = obj.value_b  # return "bar" AND creates the Attribute (autocreate)

# the autocreate property will now be found 
obj.db.value_a                      # still not found 
obj.attributes.get("value_a")       #       ''
obj.db.value_b                      # now returns "bar" 
obj.attributes.get("value_b")       #       ''

# assign new values 
obj.value_a = 10   # will now create a new Attribute 
obj.value_b = 12   # will update the existing Attribute 

# both are now found as Attributes 
obj.db.value_a                      # now returns 10
obj.attributes.get("value_a")       #       ''
obj.db.value_b                      # now returns 12
obj.attributes.get("value_b")       #       ''
```

If you always access your Attributes via the `AttributeProperty` this does not matter that much
(it's also a bit of an optimization to not create an actual database `Attribute` unless the value changed). 
But until an `Attribute` has been created, `AttributeProperty` fields will _not_ show up with the 
`examine` command or by using the `.db` or `.attributes` handlers - so this is a bit inconsistent. 
If this is important, you need to 'initialize' them by accessing them at least once ... something 
like this: 


```python 
# ... 
class Character(DefaultCharacter):

    strength = AttributeProperty(12, autocreate=True)
    agility = AttributeProperty(12, autocreate=True)


    def at_object_creation(self):
        # initializing 
        self.strength   # by accessing it, the Attribute is auto-created
        self.agility    #             ''
```

```{important}
If you created your `AttributeProperty` with a `category`, you *must* specify the 
category in `.attributes.get()` if you want to find it this way. Remember that 
`.db` always uses a `category` of `None`.
```

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

With a single object, we mean anything that is *not iterable*, like numbers, strings or custom class
instances without the `__iter__` method.

* You can generally store any non-iterable Python entity that can be pickled.
* Single database objects/typeclasses can be stored, despite them normally not being possible 
  to pickle. Evennia wil convert them to an internal representation using their classname, 
  database-id and creation-date with a microsecond precision. When retrieving, the object 
  instance will be re-fetched from the database using this information.
* To convert the database object, Evennia must know it's there. If you *hide* a database object 
  inside a non-iterable class, you will run into errors - this is not supported!

```{code-block} python
:caption: Valid assignments

# Examples of valid single-value  attribute data:
obj.db.test1 = 23
obj.db.test1 = False
# a database object (will be stored as an internal representation)
obj.db.test2 = myobj
```
```{code-block} python
:caption: Invalid, 'hidden' dbobject

# example of an invalid, "hidden" dbobject
class Container:
    def __init__(self, mydbobj):
        # no way for Evennia to know this is a database object!
        self.mydbobj = mydbobj
container = Container(myobj)
obj.db.invalid = container  # will cause error!
```

### Storing multiple objects

This means storing objects in a collection of some kind and are examples of *iterables*, pickle-able
entities you can loop over in a for-loop. Attribute-saving supports the following iterables:

* [Tuples](https://docs.python.org/2/library/functions.html#tuple), like `(1,2,"test", <dbobj>)`.
* [Lists](https://docs.python.org/2/tutorial/datastructures.html#more-on-lists), like `[1,2,"test",
<dbobj>]`.
* [Dicts](https://docs.python.org/2/tutorial/datastructures.html#dictionaries), like `{1:2,
"test":<dbobj>]`.
* [Sets](https://docs.python.org/2/tutorial/datastructures.html#sets), like `{1,2,"test",<dbobj>}`.
* [collections.OrderedDict](https://docs.python.org/2/library/collections.html#collections.OrderedDict),
like `OrderedDict((1,2), ("test", <dbobj>))`.
* [collections.Deque](https://docs.python.org/2/library/collections.html#collections.deque), like
`deque((1,2,"test",<dbobj>))`.
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
[Immutable](https://en.wikipedia.org/wiki/Immutable) objects (strings, numbers, tuples etc) are
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

# In-memory Attributes (NAttributes)

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