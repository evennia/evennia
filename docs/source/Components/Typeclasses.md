# Typeclasses

*Typeclasses* form the core of Evennia's data storage. It allows Evennia to represent any number of
different game entities as Python classes, without having to modify the database schema for every
new type.

In Evennia the most important game entities, [Accounts](./Accounts.md), [Objects](./Objects.md),
[Scripts](./Scripts.md) and [Channels](./Channels.md) are all Python classes inheriting, at
varying distance, from `evennia.typeclasses.models.TypedObject`.  In the documentation we refer to
these objects as being "typeclassed" or even "being a typeclass".

This is how the inheritance looks for the typeclasses in Evennia:

```
                  TypedObject
      _________________|_________________________________
     |                 |                 |               |
1: AccountDB        ObjectDB           ScriptDB         ChannelDB
     |                 |                 |               |
2: DefaultAccount   DefaultObject      DefaultScript    DefaultChannel
     |              DefaultCharacter     |               |
     |              DefaultRoom          |               |
     |              DefaultExit          |               |
     |                 |                 |               |
3: Account          Object              Script           Channel
                   Character
                   Room
                   Exit
```

- **Level 1** above is the "database model" level. This describes the database tables and fields
(this is technically a [Django model](https://docs.djangoproject.com/en/2.2/topics/db/models/)).
- **Level 2** is where we find Evennia's default implementations of the various game entities, on
top of the database. These classes define all the hook methods that Evennia calls in various
situations. `DefaultObject` is a little special since it's the parent for `DefaultCharacter`,
`DefaultRoom` and `DefaultExit`. They are all grouped under level 2 because they all represents
defaults to build from.
- **Level 3**, finally, holds empty template classes created in your game directory. This is the
level you are meant to modify and tweak as you please, overloading the defaults as befits your game.
The templates inherit directly from their defaults, so `Object` inherits from `DefaultObject` and
`Room` inherits from `DefaultRoom`.

The `typeclass/list` command will provide a list of all typeclasses known to
Evennia. This can be useful for getting a feel for what is available. Note
however that if you add a new module with a class in it but do not import that
module from anywhere, the `typeclass/list` will not find it. To make it known
to Evennia you must import that module from somewhere.


## Difference between typeclasses and classes

All Evennia classes inheriting from class in the table above share one important feature and two
important limitations. This is why we don't simply call them "classes" but "typeclasses".

 1. A typeclass can save itself to the database. This means that some properties (actually not that
many) on the class actually represents database fields and can only hold very specific data types.
This is detailed [below](./Typeclasses.md#about-typeclass-properties).
 1. Due to its connection to the database, the typeclass' name must be *unique* across the _entire_
server namespace. That is, there must never be two same-named classes defined anywhere. So the below
code would give an error (since `DefaultObject` is now globally found both in this module and in the
default library):

    ```python
    from evennia import DefaultObject as BaseObject
    class DefaultObject(BaseObject):
         pass
    ```

 1. A typeclass' `__init__` method should normally not be overloaded. This has mostly to do with the
fact that the `__init__` method is not called in a predictable way. Instead Evennia suggest you use
the `at_*_creation` hooks (like `at_object_creation` for Objects) for setting things the very first
time the typeclass is saved to the database or the `at_init` hook which is called every time the
object is cached to memory. If you know what you are doing and want to use `__init__`, it *must*
both accept arbitrary keyword arguments and use `super` to call its parent::

    ```python
    def __init__(self, **kwargs):
        # my content
        super().__init__(**kwargs)
        # my content
    ```

Apart from this, a typeclass works like any normal Python class and you can
treat it as such.


## Creating a new typeclass

It's easy to work with Typeclasses. Either you use an existing typeclass or you  create a new Python
class inheriting from an existing typeclass. Here is an example of creating a new type of Object:

```python
    from evennia import DefaultObject

    class Furniture(DefaultObject):
        # this defines what 'furniture' is, like
        # storing who sits on it or something.
        pass

```

You can now create a new `Furniture` object in two ways.  First (and usually not the most
convenient) way is to create an instance of the class and then save it manually to the database:

```python
chair = Furniture(db_key="Chair")
chair.save()

```

To use this you must give the database field names as keywords to the call. Which are available
depends on the entity you are creating, but all start with `db_*` in Evennia. This is a method you
may be familiar with if you know Django from before.

It is recommended that you instead use the `create_*` functions to create typeclassed entities:


```python
from evennia import create_object

chair = create_object(Furniture, key="Chair")
# or (if your typeclass is in a module furniture.py)
chair = create_object("furniture.Furniture", key="Chair")
```

The `create_object` (`create_account`, `create_script` etc) takes the typeclass as its first
argument; this can both be the actual class or the python path to the typeclass as found under your
game directory. So if your `Furniture` typeclass sits in `mygame/typeclasses/furniture.py`, you
could point to it as `typeclasses.furniture.Furniture`. Since Evennia will itself look in
`mygame/typeclasses`, you can shorten this even further to just `furniture.Furniture`. The create-
functions take a lot of extra keywords allowing you to set things like [Attributes](./Attributes.md) and
[Tags](./Tags.md) all in one go. These keywords don't use the `db_*` prefix. This will also automatically
save the new instance to the database, so you don't need to call `save()` explicitly.

## About typeclass properties

An example of a database field is `db_key`. This stores the "name" of the entity you are modifying
and can thus only hold a string. This is one way of making sure to update the `db_key`:

```python
chair.db_key = "Table"
chair.save()

print(chair.db_key)
<<< Table
```

That is, we change the chair object to have the `db_key` "Table", then save this to the database.
However, you almost never do things this way; Evennia defines property wrappers for all the database
fields. These are named the same as the field, but without the `db_` part:

```python
chair.key = "Table"

print(chair.key)
<<< Table

```

The `key` wrapper is not only shorter to write, it will make sure to save the field for you, and
does so more efficiently by levering sql update mechanics under the hood. So whereas it is good to
be aware that the field is named `db_key` you should use `key` as much as you can.

Each typeclass entity has some unique fields relevant to that type.  But all also share the
following fields (the wrapper name without `db_` is given):

 - `key` (str): The main identifier for the entity, like "Rose", "myscript" or "Paul". `name` is an
alias.
 - `date_created` (datetime): Time stamp when this object was created.
 - `typeclass_path` (str): A python path pointing to the location of this (type)class

There is one special field that doesn't use the `db_` prefix (it's defined by Django):

 - `id` (int): the database id (database ref) of the object. This is an ever-increasing, unique
integer. It can also be accessed as `dbid` (database ID) or `pk` (primary key). The `dbref` property
returns the string form "#id".

The typeclassed entity has several common handlers:

 - `tags` - the [TagHandler](./Tags.md) that handles tagging. Use `tags.add()` , `tags.get()` etc.
 - `locks` - the [LockHandler](./Locks.md) that manages access restrictions. Use `locks.add()`,
`locks.get()` etc.
 - `attributes` - the [AttributeHandler](./Attributes.md) that manages Attributes on the object. Use
`attributes.add()`
etc.
 - `db` (DataBase) - a shortcut property to the AttributeHandler; allowing `obj.db.attrname = value`
 - `nattributes` - the [Non-persistent AttributeHandler](./Attributes.md) for attributes not saved in the
database.
 - `ndb` (NotDataBase) - a shortcut property to the Non-peristent AttributeHandler. Allows
`obj.ndb.attrname = value`


Each of the typeclassed entities then extend this list with their own properties. Go to the
respective pages for [Objects](./Objects.md), [Scripts](./Scripts.md), [Accounts](./Accounts.md) and
[Channels](./Channels.md) for more info. It's also recommended that you explore the available
entities using [Evennia's flat API](../Evennia-API.md) to explore which properties and methods they have
available.

## Overloading hooks

The way to customize typeclasses is usually to overload *hook methods* on them. Hooks are methods
that Evennia call in various situations. An example is the `at_object_creation` hook on `Objects`,
which is only called once, the very first time this object is saved to the database.  Other examples
are the `at_login` hook of Accounts and the `at_repeat` hook of Scripts.

## Querying for typeclasses

Most of the time you search for objects in the database by using convenience methods like the
`caller.search()` of [Commands](./Commands.md) or the search functions like `evennia.search_objects`.

You can however also query for them directly using [Django's query
language](https://docs.djangoproject.com/en/1.7/topics/db/queries/). This makes use of a _database
manager_ that sits on all typeclasses, named `objects`. This manager holds methods that allow
database searches against that particular type of object (this is the way Django normally works
too). When using Django queries, you need to use the full field names (like `db_key`) to search:

```python
matches = Furniture.objects.get(db_key="Chair")

```

It is important that this will *only* find objects inheriting directly from `Furniture` in your
database. If there was a subclass of `Furniture` named `Sitables` you would not find any chairs
derived from `Sitables` with this query (this is not a Django feature but special to Evennia). To
find objects from subclasses Evennia instead makes the `get_family` and `filter_family` query
methods available:

```python
# search for all furnitures and subclasses of furnitures
# whose names starts with "Chair"
matches = Furniture.objects.filter_family(db_key__startswith="Chair")

```

To make sure to search, say, all `Scripts` *regardless* of typeclass, you need to query from the
database model itself. So for Objects, this would be `ObjectDB` in the diagram above. Here's an
example for Scripts:

```python
from evennia import ScriptDB
matches = ScriptDB.objects.filter(db_key__contains="Combat")
```

When querying from the database model parent you don't need to use `filter_family` or `get_family` -
you will always query all children on the database model.

## Updating existing typeclass instances

If you already have created instances of Typeclasses, you can modify the *Python code* at any time -
due to how Python inheritance works your changes will automatically be applied to all children once
you have reloaded the server.

However, database-saved data, like `db_*` fields, [Attributes](./Attributes.md), [Tags](./Tags.md) etc, are
not themselves embedded into the class and will *not* be updated automatically. This you need to
manage yourself, by searching for all relevant objects and updating or adding the data:

```python
# add a worth Attribute to all existing Furniture
for obj in Furniture.objects.all():
    # this will loop over all Furniture instances
    obj.db.worth = 100
```

A common use case is putting all Attributes in the `at_*_creation` hook of the entity, such as
`at_object_creation` for `Objects`. This is called every time an object is created - and only then.
This is usually what you want but it does mean already existing objects won't get updated if you
change the contents of `at_object_creation` later. You can fix this in a similar way as above
(manually setting each Attribute) or with something like this:

```python
# Re-run at_object_creation only on those objects not having the new Attribute
for obj in Furniture.objects.all():
    if not obj.db.worth:
        obj.at_object_creation()
```

The above examples can be run in the command prompt created by `evennia shell`. You could also run
it all in-game using `@py`. That however requires you to put the code (including imports) as one
single line using `;` and [list
comprehensions](http://www.secnetix.de/olli/Python/list_comprehensions.hawk), like this (ignore the
line break, that's only for readability in the wiki):

```
@py from typeclasses.furniture import Furniture;
[obj.at_object_creation() for obj in Furniture.objects.all() if not obj.db.worth]
```

It is recommended that you plan your game properly before starting to build, to avoid having to
retroactively update objects more than necessary.

## Swap typeclass

If you want to swap an already existing typeclass, there are two ways to do so: From in-game and via
code. From inside the game you can use the default `@typeclass` command:

```
@typeclass objname = path.to.new.typeclass
```

There are two important switches to this command:
- `/reset` - This will purge all existing Attributes on the object and re-run the creation hook
(like `at_object_creation` for Objects). This assures you get an object which is purely of this new
class.
- `/force` - This is required if you are changing the class to be *the same* class the object
already has - it's a safety check to avoid user errors. This is usually used together with `/reset`
to re-run the creation hook on an existing class.

In code you instead use the `swap_typeclass` method which you can find on all typeclassed entities:

```python
obj_to_change.swap_typeclass(new_typeclass_path, clean_attributes=False,
                   run_start_hooks="all", no_default=True, clean_cmdsets=False)
```

The arguments to this method are described [in the API docs
here](github:evennia.typeclasses.models#typedobjectswap_typeclass).


## How typeclasses actually work

*This is considered an advanced section.*

Technically, typeclasses are [Django proxy
models](https://docs.djangoproject.com/en/1.7/topics/db/models/#proxy-models).  The only database
models that are "real" in the typeclass system (that is, are represented by actual tables in the
database) are `AccountDB`, `ObjectDB`, `ScriptDB` and `ChannelDB` (there are also
[Attributes](./Attributes.md) and [Tags](./Tags.md) but they are not typeclasses themselves). All the
subclasses of them are "proxies", extending them with Python code without actually modifying the
database layout.

Evennia modifies Django's proxy model in various ways to allow them to work without any boiler plate
(for example you don't need to set the Django "proxy" property in the model `Meta` subclass, Evennia
handles this for you using metaclasses). Evennia also makes sure you can query subclasses as well as
patches django to allow multiple inheritance from the same base class.

## Caveats

Evennia uses the *idmapper* to cache its typeclasses (Django proxy models) in memory. The idmapper
allows things like on-object handlers and properties to be stored on typeclass instances and to not
get lost as long as the server is running (they will only be cleared on a Server reload). Django
does not work like this by default; by default every time you search for an object in the database
you'll get a *different* instance of that object back and anything you stored on it that was not in
the database would be lost. The bottom line is that Evennia's Typeclass instances subside in memory
a lot longer than vanilla Django model instance do.

There is one  caveat to consider with this, and that relates to [making your own models](New-
Models): Foreign relationships to typeclasses are cached by Django and that means that if you were
to change an object in a foreign relationship via some other means than via that relationship, the
object seeing the relationship may not reliably update but will still see its old cached version.
Due to typeclasses staying so long in memory, stale caches of such relationships could be more
visible than common in Django. See the [closed issue #1098 and its
comments](https://github.com/evennia/evennia/issues/1098) for examples and solutions.
