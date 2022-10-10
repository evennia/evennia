# Add a wiki on your website

**Before doing this tutorial you will probably want to read the intro in
[Basic Web tutorial](Beginner-Tutorial/Part5/Web-Tutorial.md).**  Reading the three first parts of the
[Django tutorial](https://docs.djangoproject.com/en/1.9/intro/tutorial01/) might help as well.

This tutorial will provide a step-by-step process to installing a wiki on your website.
Fortunately, you don't have to create the features manually, since it has been done by others, and
we can integrate their work quite easily with Django.  I have decided to focus on
the [Django-wiki](https://django-wiki.readthedocs.io/).

The [Django-wiki](https://django-wiki.readthedocs.io/) offers a lot of features associated with
wikis, is actively maintained (at this time, anyway), and isn't too difficult to install in Evennia.  You can
see a [demonstration of Django-wiki here](https://demo.django-wiki.org).

## Basic installation

You should begin by shutting down the Evennia server if it is running.  We will run migrations and
alter the virtual environment just a bit.  Open a terminal and activate your Python environment, the
one you use to run the `evennia` command.

If you used the default location from the Evennia installation instructions, it should be one of the following:

* On Linux:
    ```
    source evenv/bin/activate
    ```
* Or Windows:
    ```
    evenv\bin\activate
    ```

### Installing with pip

Install the wiki using pip:

    pip install wiki

It might take some time, the Django-wiki having some dependencies.

### Adding the wiki in the settings

You will need to add a few settings to have the wiki app on your website.  Open your
`server/conf/settings.py` file and add the following at the bottom (but before importing
`secret_settings`).  Here's an example of a settings file with the Django-wiki added:

```python
# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "demowiki"

######################################################################
# Django-wiki settings
######################################################################
INSTALLED_APPS += (
    'django.contrib.humanize.apps.HumanizeConfig',
    'django_nyt.apps.DjangoNytConfig',
    'mptt',
    'sorl.thumbnail',
    'wiki.apps.WikiConfig',
    'wiki.plugins.attachments.apps.AttachmentsConfig',
    'wiki.plugins.notifications.apps.NotificationsConfig',
    'wiki.plugins.images.apps.ImagesConfig',
    'wiki.plugins.macros.apps.MacrosConfig',
)

# Disable wiki handling of login/signup
WIKI_ACCOUNT_HANDLING = False
WIKI_ACCOUNT_SIGNUP_ALLOWED = False

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
```

Everything in the section "Django-wiki settings" is what you'll need to include.

### Adding the new URLs

Next you will need to add two URLs to the file `web/urls.py`. You'll do that by modifying
`urlpatterns` to look something like this:

```python
# add patterns
urlpatterns = [
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # wiki
    path("wiki/", include("wiki.urls")),
    path("notifications/", include("django_nyt.urls")),
]
```

The last two lines are what you'll need to add.

### Running migrations

Next you'll need to run migrations, since the wiki app adds a few tables in our database:

    evennia migrate


### Initializing the wiki

Last step! Go ahead and start up your server again.

    evennia start

Once that's finished booting, go to your evennia website (e.g. http://localhost:4001 ) and log in
with your superuser account, if you aren't already. Then, go to your new wiki (e.g.
http://localhost:4001/wiki ). It'll prompt you to create a starting page - put whatever you want,
you can change it later.

Congratulations! You're all done!

## Defining wiki permissions

A wiki is usually intended as a collaborative effort - but you probably still want to set
some rules about who is allowed to do what. Who can create new articles? Edit them? Delete
them? Etc.

The two simplest ways to do this are to use Django-wiki's group-based permissions
system - or, since this is an Evennia site, to define your own custom permission rules
tied to Evennia's permissions system in your settings file.

### Group permissions

The wiki itself controls reading/editing permissions per article. The creator of an article will
always have read/write permissions on that article. Additionally, the article will have Group-based
permissions and general permissions.

By default, Evennia's permission groups *won't* be recognized by the wiki, so you'll have to create your own.
Go to the Groups page of your game's Django admin panel (e.g. http://localhost:4001/admin/auth/group )
and add whichever permission groups you want for your wiki here.

***Note:*** *If you want to connect those groups to your game's permission levels, you'll need to modify the game to apply both to accounts.*

Once you've added those groups, they'll be usable in your wiki right away!

### Settings permissions

Django-wiki also allows you to bypass its article-based permissions with custom site-wide permissions
rules in your settings file. If you don't want to use the Group system, or if you want a simple
solution for connecting the Evennia permission levels to wiki access, this is the way to go.

Here's an example of a basic set-up that would go in your `settings.py` file:

```python
# In server/conf/settings.py
# ...

# Custom methods to link wiki permissions to game perms
def is_superuser(article, user):
    """Return True if user is a superuser, False otherwise."""
    return not user.is_anonymous() and user.is_superuser

def is_builder(article, user):
    """Return True if user is a builder, False otherwise."""
    return not user.is_anonymous() and user.locks.check_lockstring(user, "perm(Builders)")

def is_player(article, user):
    """Return True if user is a builder, False otherwise."""
    return not user.is_anonymous() and user.locks.check_lockstring(user, "perm(Players)")

# Create new users
WIKI_CAN_ADMIN = is_superuser

# Change the owner and group for an article
WIKI_CAN_ASSIGN = is_superuser

# Change the GROUP of an article, despite the name
WIKI_CAN_ASSIGN_OWNER = is_superuser

# Change read/write permissions on an article
WIKI_CAN_CHANGE_PERMISSIONS = is_superuser

# Mark an article as deleted
WIKI_CAN_DELETE = is_builder

# Lock or permanently delete an article
WIKI_CAN_MODERATE = is_superuser

# Create or edit any pages
WIKI_CAN_WRITE = is_builder

# Read any pages
WIKI_CAN_READ = is_player

# Completely disallow editing and article creation when not logged in
WIKI_ANONYMOUS_WRITE = False
```

The permission functions can check anything you like on the accessing user, so long as the function
returns either True (they're allowed) or False (they're not).

For a full list of possible settings, you can check out [the django-wiki documentation](https://django-wiki.readthedocs.io/en/latest/settings.html).
