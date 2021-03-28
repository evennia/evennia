# Quirks


This is a list of various quirks or common stumbling blocks that people often ask about or report
when using (or trying to use) Evennia. They are not bugs.

### Forgetting to use @reload to see changes to your typeclasses

Firstly: Reloading the server is a safe and usually quick operation which will *not* disconnect any
accounts.

New users tend to forget this step. When editing source code (such as when tweaking typeclasses and
commands or adding new commands to command sets) you need to either use the in-game `@reload`
command or, from the command line do `python evennia.py reload` before you see your changes.

### Web admin to create new Account

If you use the default login system and are trying to use the Web admin to create a new Player
account, you need to consider which `MULTIACCOUNT_MODE` you are in. If you are in
`MULTIACCOUNT_MODE` `0` or `1`, the login system expects each Account to also have a Character
object named the same as the Account - there is no character creation screen by default. If using
the normal mud login screen, a Character with the same name is automatically created and connected
to your Account. From the web interface you must do this manually.

So, when creating the Account, make sure to also create the Character *from the same form* as you
create the Account from. This should set everything up for you. Otherwise you need to manually set
the "account" property on the Character and the "character" property on the Account to point to each
other. You must also set the lockstring of the Character to allow the Account to "puppet" this
particular character.

### Mutable attributes and their connection to the database

When storing a mutable object (usually a list or a dictionary) in an Attribute

```python
     object.db.mylist = [1,2,3]
```

you should know that the connection to the database is retained also if you later extract that
Attribute into another variable (what is stored and retrieved is actually a `PackedList` or a
`PackedDict` that works just like their namesakes except they save themselves to the database when
changed). So if you do

```python
     alist = object.db.mylist
     alist.append(4)
```

this updates the database behind the scenes, so both `alist` and `object.db.mylist` are now
`[1,2,3,4]`

If you don't want this, Evennia provides a way to stably disconnect the mutable from the database by
use of `evennia.utils.dbserialize.deserialize`:

```python
     from evennia.utils.dbserialize import deserialize

     blist = deserialize(object.db.mylist)
     blist.append(4)
```

The property `blist` is now `[1,2,3,4]` whereas `object.db.mylist` remains unchanged. If you want to
update the database you'd need to explicitly re-assign the updated data to the `mylist` Attribute.

### Commands are matched by name *or* alias

When merging [command sets](./Commands) it's important to remember that command objects are identified
*both* by key *or* alias. So if you have a command with a key `look` and an alias `ls`, introducing
another command with a key `ls` will be assumed by the system to be *identical* to the first one.
This usually means merging cmdsets will overload one of them depending on priority. Whereas this is
logical once you know how command objects are handled, it may be confusing if you are just looking
at the command strings thinking they are parsed as-is.

### Objects turning to `DefaultObject`

A common confusing error for new developers is finding that one or more objects in-game are suddenly
of the type `DefaultObject` rather than the typeclass you wanted it to be. This happens when you
introduce a critical Syntax error to the module holding your custom class. Since such a module is
not valid Python, Evennia can't load it at all to get to the typeclasses within. To keep on running,
Evennia will solve this by printing the full traceback to the terminal/console and temporarily fall
back to the safe `DefaultObject` until you fix the problem and reload. Most errors of this kind will
be caught by any good text editors. Keep an eye on the terminal/console during a reload to catch
such errors - you may have to scroll up if your window is small.

### Overriding of magic methods

Python implements a system of [magic
methods](https://docs.python.org/3/reference/datamodel.html#emulating-container-types), usually
prefixed and suffixed by double-underscores (`__example__`) that allow object instances to have
certain operations performed on them without needing to do things like turn them into strings or
numbers first-- for example, is `obj1` greater than or equal to `obj2`?

Neither object is a number, but given `obj1.size == "small"` and `obj2.size == "large"`, how might
one compare these two arbitrary English adjective strings to figure out which is greater than the
other? By defining the `__ge__` (greater than or equal to) magic method on the object class in which
you figure out which word has greater significance, perhaps through use of a mapping table
(`{'small':0, 'large':10}`) or other lookup and comparing the numeric values of each.

Evennia extensively makes use of magic methods on typeclasses to do things like initialize objects,
check object existence or iterate over objects in an inventory or container. If you override or
interfere with the return values from the methods Evennia expects to be both present and working, it
can result in very inconsistent and hard-to-diagnose errors.

The moral of the story-- it can be dangerous to tinker with magic methods on typeclassed objects.
Try to avoid doing so.

### Known upstream bugs

- There is currently (Autumn 2017) a bug in the `zope.interface` installer on some Linux Ubuntu
distributions (notably Ubuntu 16.04 LTS). Zope is a dependency of Twisted. The error manifests in
the server not starting with an error that `zope.interface` is not found even though `pip list`
shows it's installed. The reason is a missing empty `__init__.py` file at the root of the zope
package. If the virtualenv is named "evenv" as suggested in the [Getting Started](./Getting-Started)
instructions, use the following command to fix it:

    ```shell
    touch evenv/local/lib/python2.7/site-packages/zope/__init__.py
    ```

    This will create the missing file and things should henceforth work correctly.