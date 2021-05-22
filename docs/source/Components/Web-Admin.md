# The Web Admin

The Evennia _Web admin_ is a customized [Django admin site](https://docs.djangoproject.com/en/3.2/ref/contrib/admin/)
used for manipulating the game database using a graphical interface. You
have to be logged into the site to use it. It then appears as an `Admin` link
the top of your website. You can also go to [http://localhost:4001/admin](http://localhost:4001/admin) when
running locally.

Almost all actions done in the admin can also be done in-game by use of Admin-
or Builder-commands.

## Usage

The admin is pretty self-explanatory - you can see lists of each object type,
create new instances of each type and also add new Attributes/tags them. The
admin frontpage will give a summary of all relevant entities and how they are
used.

There are a few use cases that requires some additional explanation though.

### Adding objects to Attributes

The `value` field of an Attribute is pickled into a special form. This is usually not
something you need to worry about (the admin will pickle/unpickle) the value
for you), _except_ if you want to store a database-object in an attribute. Such
objects are actually stored as a `tuple` with object-unique data.

1. Find the object you want to add to the Attribute. At the bottom of the first section
   you'll find the field _Serialized string_. This string shows a Python tuple like

       ('__packed_dbobj__', ('objects', 'objectdb'), '2021:05:15-08:59:30:624660', 358)
   
   Mark and copy this tuple-string to your clipboard exactly as it stands (parentheses and all).
2. Go to the entity that should have the new Attribute and create the Attribute. In its `value`
   field, paste the tuple-string you copied before. Save!
3. If you want to store multiple objects in, say, a list, you can do so by literally
   typing a python list `[tuple, tuple, tuple, ...]` where you paste in the serialized
   tuple-strings with commas. At some point it's probably easier to do this in code though ...

### Linking Accounts and Characters

In `MULTISESSION_MODE` 0 or 1, each connection can have one Account and one
Character, usually with the same name. Normally this is done by the user
creating a new account and logging in - a matching Character will then be
created for them. You can however also do so manually in the admin:

1. First create the complete Account in the admin.
2. Next, create the Object (usually of `Character` typeclass) and name it the same
   as the Account. It also needs a command-set. The default CharacterCmdset is a good bet.
3. In the `Puppeting Account` field, select the Account.
4. Make sure to save everything.
5. Click the `Link to Account` button (this will only work if you saved first). This will
   add the needed locks and Attributes to the Account to allow them to immediately
   connect to the Character when they next log in. This will (where possible):
   - Set `account.db._last_puppet` to the Character.
   - Add Character to `account.db._playabel_characters` list.
   - Add/extend the `puppet:` lock on the Character to include `puppet:pid(<Character.id>)`

### Building with the Admin

It's possible (if probably not very practical at scale) to build and describe
rooms in the Admin.

1. Create an `Object` of a Room-typeclass with a suitable room-name.
2. Set an Attribute 'desc' on the room - the value of this Attribute is the
   room's description.
3. Add `Tags` of `type` 'alias' to add room-aliases (no type for regular tags)

Exits:

1. Exits are `Objects` of an `Exit` typeclass, so create one.
2. The exit has `Location` of the room you just created.
3. Set `Destination` set to where the exit leads to.
4. Set a 'desc' Attribute, this is shown if someone looks at the exit.
5. `Tags` of `type` 'alias' are alternative names users can use to go through
   this exit.

## Grant others access to the admin

The access to the admin is controlled by the `Staff status` flag on the
Account.  Without this flag set, even superusers will not even see the admin
link on the web page. The staff-status has no in-game equivalence.


Only Superusers can change the `Superuser status` flag, and grant new
permissions to accounts. The superuser is the only permission level that is
also relevant in-game. `User Permissions` and `Groups` found on the `Account`
admin page _only_ affects the admin - they have no connection to the in-game
[Permissions](Permissions) (Player, Builder, Admin etc).

For a staffer with `Staff status` to be able to actually do anything, the
superuser must grant at least some permissions for them on their Account. This
can also be good in order to limit mistakes. It can be a good idea to not allow
the `Can delete Account` permission, for example.

```important::

  If you grant staff-status and permissions to an Account and they still cannot
  access the admin's content, try reloading the server.

```

```warning::

    If a staff member has access to the in-game ``py`` command, they can just as
    well have their admin ``Superuser status`` set too. The reason is that ``py``
    grants them all the power they need to set the ``is_superuser`` flag on their
    account manually. There is a reason access to the ``py`` command must be
    considered carefully ...

```

## Customizing the web admin

Customizing the admin is a big topic and something beyond the scope of this 
documentation. See the [official Django docs](https://docs.djangoproject.com/en/3.2/ref/contrib/admin/) for
the details. This is just a brief summary. 

See the [Website](./Website) page for an overview of the components going into 
generating a web page. The Django admin uses the same principle except that
Django provides a lot of tools to automate the admin-generation for us.

Admin templates are found in `evennia/web/templates/admin/` but you'll find
this is relatively empty. This is because most of the templates are just
inherited directly from their original location in the Django package
(`django/contrib/admin/templates/`). So if you wanted to override one you'd have 
to copy it from _there_ into your `mygame/templates/admin/` folder. Same is true
for CSS files.

The admin site's backend code (the views) is found in `evennia/web/admin/`. It
is organized into `admin`-classes, like `ObjectAdmin`, `AccountAdmin` etc.
These automatically use the underlying database models to generate useful views
for us without us havint go code the forms etc ourselves. 

The top level `AdminSite` (the admin configuration referenced in django docs)
is found in `evennia/web/utils/adminsite.py`.


### Change the title of the admin

By default the admin's title is `Evennia web admin`. To change this, add the 
following to your `mygame/web/urls.py`:

```python
# in mygame/web/urls.py

# ...

from django.conf.admin import site

#...

site.site_header = "My great game admin"


```

Reload the server and the admin's title header will have changed.
