# New Models

*Note: This is considered an advanced topic.*

Evennia offers many convenient ways to store object data, such as via Attributes or Scripts. This is
sufficient for most use cases. But if you aim to build a large stand-alone system, trying to squeeze
your storage requirements into those may be more complex than you bargain for. Examples may be to
store guild data for guild members to be able to change, tracking the flow of money across a game-
wide economic system or implement other custom game systems that requires the storage of custom data
in a quickly accessible way. Whereas [Tags](../Components/Tags.md) or [Scripts](../Components/Scripts.md) can handle many situations,
sometimes things may be easier to handle by adding your own database model.

## Overview of database tables

SQL-type databases (which is what Evennia supports) are basically highly optimized systems for
retrieving text stored in tables. A table may look like this

```
     id | db_key    | db_typeclass_path          | db_permissions  ...
    ------------------------------------------------------------------
     1  |  Griatch  | evennia.DefaultCharacter   | Developers       ...
     2  |  Rock     | evennia.DefaultObject      | None            ...
```

Each line is considerably longer in your database. Each column is referred to as a "field" and every
row is a separate object. You can check this out for yourself. If you use the default sqlite3
database, go to your game folder and run

     evennia dbshell

You will drop into the database shell. While there, try:

     sqlite> .help       # view help

     sqlite> .tables     # view all tables

     # show the table field names for objects_objectdb
     sqlite> .schema objects_objectdb

     # show the first row from the objects_objectdb table
     sqlite> select * from objects_objectdb limit 1;

     sqlite> .exit

Evennia uses [Django](https://docs.djangoproject.com), which abstracts away the database SQL
manipulation and allows you to search and manipulate your database entirely in Python. Each database
table is in Django represented by a class commonly called a *model* since it describes the look of
the table. In Evennia, Objects, Scripts, Channels etc are examples of Django models that we then
extend and build on.

## Adding a new database table

Here is how you add your own database table/models:

1. In Django lingo, we will create a new "application" - a subsystem under the main Evennia program.
For this example we'll call it "myapp". Run the following (you need to have a working Evennia
running before you do this, so make sure you have run the steps in [Setup Quickstart](Getting-
Started) first):

        cd mygame/world
        evennia startapp myapp

1. A new folder `myapp` is created. "myapp" will also be the name (the "app label") from now on. We
chose to put it in the `world/` subfolder here, but you could put it in the root of your `mygame` if
that makes more sense.
1. The `myapp` folder contains a few empty default files. What we are
interested in for now is `models.py`. In `models.py` you define your model(s). Each model will be a
table in the database. See the next section and don't continue until you have added the models you
want.
1. You now need to tell Evennia that the models of your app should be a part of your database
scheme. Add this line to your `mygame/server/conf/settings.py`file (make sure to use the path where
you put `myapp` and don't forget the comma at the end of the tuple):

    ```
    INSTALLED_APPS = INSTALLED_APPS + ("world.myapp", )
    ```

1. From `mygame/`, run

        evennia makemigrations myapp
        evennia migrate

This will add your new database table to the database. If you have put your game under version
control (if not, [you should](../Coding/Version-Control.md)), don't forget to `git add myapp/*` to add all items
to version control.

## Defining your models

A Django *model* is the Python representation of a database table. It can be handled like any other
Python class. It defines *fields* on itself, objects of a special type. These become the "columns"
of the database table. Finally, you create new instances of the model to add new rows to the
database.

We won't describe all aspects of Django models here, for that we refer to the vast [Django
documentation](https://docs.djangoproject.com/en/2.2/topics/db/models/) on the subject. Here is a
(very) brief example:

```python
from django.db import models

class MyDataStore(models.Model):
    "A simple model for storing some data"
    db_key = models.CharField(max_length=80, db_index=True)
    db_category = models.CharField(max_length=80, null=True, blank=True)
    db_text = models.TextField(null=True, blank=True)
    # we need this one if we want to be
    # able to store this in an Evennia Attribute!
    db_date_created = models.DateTimeField('date created', editable=False,
                                            auto_now_add=True, db_index=True)
```

We create four fields: two character fields of limited length and one text field which has no
maximum length. Finally we create a field containing the current time of us creating this object.

> The `db_date_created` field, with exactly this name, is *required* if you want to be able to store
instances of your custom model in an Evennia [Attribute](../Components/Attributes.md). It will automatically be set
upon creation and can after that not be changed. Having this field will allow you to do e.g.
`obj.db.myinstance = mydatastore`. If you know you'll never store your model instances in Attributes
the `db_date_created` field is optional.

You don't *have* to start field names with `db_`, this is an Evennia convention. It's nevertheless
recommended that you do use `db_`, partly for clarity and consistency with Evennia (if you ever want
to share your code) and partly for the case of you later deciding to use Evennia's
`SharedMemoryModel` parent down the line.

The field keyword `db_index` creates a *database index* for this field, which allows quicker
lookups, so it's recommended to put it on fields you know you'll often use in queries. The
`null=True` and `blank=True` keywords means that these fields may be left empty or set to the empty
string without the database complaining. There are many other field types and keywords to define
them, see django docs for more info.

Similar to using [django-admin](https://docs.djangoproject.com/en/2.2/howto/legacy-databases/) you
are able to do `evennia inspectdb` to get an automated listing of model information for an existing
database.  As is the case with any model generating tool you should only use this as a starting
point for your models.

## Creating a new model instance

To create a new row in your table, you instantiate the model and then call its `save()` method:

```python
     from evennia.myapp import MyDataStore

     new_datastore = MyDataStore(db_key="LargeSword",
                                 db_category="weapons",
                                 db_text="This is a huge weapon!")
     # this is required to actually create the row in the database!
     new_datastore.save()

```

Note that the `db_date_created` field of the model is not specified. Its flag `at_now_add=True`
makes sure to set it to the current date when the object is created (it can also not be changed
further after creation).

When you update an existing object with some new field value, remember that you have to save the
object afterwards, otherwise the database will not update:

```python
    my_datastore.db_key = "Larger Sword"
    my_datastore.save()
```

Evennia's normal models don't need to explicitly save, since they are based on `SharedMemoryModel`
rather than the raw django model. This is covered in the next section.

## Using the `SharedMemoryModel` parent

Evennia doesn't base most of its models on the raw `django.db.models` but on the Evennia base model
`evennia.utils.idmapper.models.SharedMemoryModel`. There are two main reasons for this:

1. Ease of updating fields without having to explicitly call `save()`
2. On-object memory persistence and database caching

The first (and least important) point means that as long as you named your fields `db_*`, Evennia
will automatically create field wrappers for them. This happens in the model's
[Metaclass](http://en.wikibooks.org/wiki/Python_Programming/Metaclasses) so there is no speed
penalty for this. The name of the wrapper will be the same name as the field, minus the `db_`
prefix. So the `db_key` field will have a wrapper property named `key`. You can then do:

```python
    my_datastore.key = "Larger Sword"
```

and don't have to explicitly call `save()` afterwards. The saving also happens in a more efficient
way under the hood, updating only the field rather than the entire model using django optimizations.
Note that if you were to manually add the property or method `key` to your model, this will be used
instead of the automatic wrapper and allows you to fully customize access as needed.

To explain the second and more important point, consider the following example using the default
Django model parent:

```python
    shield = MyDataStore.objects.get(db_key="SmallShield")
    shield.cracked = True # where cracked is not a database field
```

And then later:

```python
    shield = MyDataStore.objects.get(db_key="SmallShield")
    print(shield.cracked)  # error!
```

The outcome of that last print statement is *undefined*! It could *maybe* randomly work but most
likely you will get an `AttributeError` for not finding the `cracked` property. The reason is that
`cracked` doesn't represent an actual field in the database. It was just added at run-time and thus
Django don't care about it. When you retrieve your shield-match later there is *no* guarantee you
will get back the *same Python instance* of the model where you defined `cracked`, even if you
search for the same database object.

Evennia relies heavily on on-model handlers and other dynamically created properties. So rather than
using the vanilla Django models, Evennia uses `SharedMemoryModel`, which levies something called
*idmapper*. The idmapper caches model instances so that we will always get the *same* instance back
after the first lookup of a given object. Using idmapper, the above example would work fine and you
could retrieve your `cracked` property at any time - until you rebooted when all non-persistent data
goes.

Using the idmapper is both more intuitive and more efficient *per object*; it leads to a lot less
reading from disk. The drawback is that this system tends to be more memory hungry *overall*. So if
you know that you'll *never* need to add new properties to running instances or know that you will
create new objects all the time yet rarely access them again (like for a log system), you are
probably better off making "plain" Django models rather than using `SharedMemoryModel` and its
idmapper.

To use the idmapper and the field-wrapper functionality you just have to have your model classes
inherit from `evennia.utils.idmapper.models.SharedMemoryModel` instead of from the default
`django.db.models.Model`:

```python
from evennia.utils.idmapper.models import SharedMemoryModel

class MyDataStore(SharedMemoryModel):
    # the rest is the same as before, but db_* is important; these will
    # later be settable as .key, .category, .text ...
    db_key = models.CharField(max_length=80, db_index=True)
    db_category = models.CharField(max_length=80, null=True, blank=True)
    db_text = models.TextField(null=True, blank=True)
    db_date_created = models.DateTimeField('date created', editable=False,
                                            auto_now_add=True, db_index=True)
```

## Searching for your models

To search your new custom database table you need to use its database *manager* to build a *query*.
Note that even if you use `SharedMemoryModel` as described in the previous section, you have to use
the actual *field names* in the query, not the wrapper name (so `db_key` and not just `key`).

```python
     from world.myapp import MyDataStore

     # get all datastore objects exactly matching a given key
     matches = MyDataStore.objects.filter(db_key="Larger Sword")
     # get all datastore objects with a key containing "sword"
     # and having the category "weapons" (both ignoring upper/lower case)
     matches2 = MyDataStore.objects.filter(db_key__icontains="sword",
                                           db_category__iequals="weapons")
     # show the matching data (e.g. inside a command)
     for match in matches2:
        self.caller.msg(match.db_text)
```

See the [Django query documentation](https://docs.djangoproject.com/en/2.2/topics/db/queries/) for a
lot more information about querying the database.