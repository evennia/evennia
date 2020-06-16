# Add a wiki on your website


**Before doing this tutorial you will probably want to read the intro in 
[Basic Web tutorial](Web-Tutorial).**  Reading the three first parts of the 
[Django tutorial](https://docs.djangoproject.com/en/1.9/intro/tutorial01/) might help as well.

This tutorial will provide a step-by-step process to installing a wiki on your website.
Fortunately, you don't have to create the features manually, since it has been done by others, and
we can integrate their work quite easily with Django.  I have decided to focus on
the [Django-wiki](http://django-wiki.readthedocs.io/).

> Note: this article has been updated for Evennia 0.9.  If you're not yet using this version, be
careful, as the django wiki doesn't support Python 2 anymore.  (Remove this note when enough time
has passed.)

The [Django-wiki](http://django-wiki.readthedocs.io/) offers a lot of features associated with
wikis, is
actively maintained (at this time, anyway), and isn't too difficult to install in Evennia.  You can
see a [demonstration of Django-wiki here](https://demo.django.wiki).

## Basic installation

You should begin by shutting down the Evennia server if it is running.  We will run migrations and
alter the virtual environment just a bit.  Open a terminal and activate your Python environment, the
one you use to run the `evennia` command.

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

> Note: this will install the last version of Django wiki. Version >0.4 doesn't support Python 2, so
install wiki 0.3 if you haven't updated to Python 3 yet.

It might take some time, the Django-wiki having some dependencies.

### Adding the wiki in the settings

You will need to add a few settings to have the wiki app on your website.  Open your
`server/conf/settings.py` file and add the following at the bottom (but before importing
`secret_settings`).  Here's what you'll find in my own setting file (add the whole Django-wiki
section):

```python
r"""
Evennia settings file.

...

"""

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

### Adding the new URLs

Next we need to add two URLs in our `web/urls.py` file.  Open it and compare the following output:
you will need to add two URLs in `custom_patterns` and add one import line:

```python
from django.conf.urls import url, include
from django.urls import path # NEW!

# default evenni	a patterns
from evennia.web.urls import urlpatterns

# eventual custom patterns
custom_patterns = [
    # url(r'/desired/url/', view, name='example'),
    url('notifications/', include('django_nyt.urls')), # NEW!
    url('wiki/', include('wiki.urls')), # NEW!
]

# this is required by Django.
urlpatterns = custom_patterns + urlpatterns
```

You will probably need to copy line 2, 10, and 11.  Be sure to place them correctly, as shown in
the example above.

### Running migrations

It's time to run the new migrations.  The wiki app adds a few tables in our database.  We'll need to
run:

    evennia migrate

And that's it, you can start the server.  If you go to http://localhost:4001/wiki , you should see
the wiki.  Use your account's username and password to connect to it.  That's how simple it is.

## Customizing privileges

A wiki can be a great collaborative tool, but who can see it?  Who can modify it?  Django-wiki comes
with a privilege system centered around four values per wiki page.  The owner of an article can
always read and write in it (which is somewhat logical).  The group of the article defines who can
read and who can write, if the user seeing the page belongs to this group.  The topic of groups in
wiki pages will not be discussed here.  A last setting determines which other user (that is, these
who aren't in the groups, and aren't the article's owner) can read and write.  Each article has
these four settings (group read, group write, other read, other write).  Depending on your purpose,
it might not be a good default choice, particularly if you have to remind every builder to keep the
pages private.  Fortunately, Django-wiki gives us additional settings to customize who can read, and
who can write, a specific article.

These settings must be placed, as usual, in your `server/conf/settings.py` file.  They take a
function as argument, said function (or callback) will be called with the article and the user.
Remember, a Django user, for us, is an account.  So we could check lockstrings on them if needed.
Here is a default setting to restrict the wiki: only builders can write in it, but anyone (including
non-logged in users) can read it.  The superuser has some additional privileges.

```python
# In server/conf/settings.py
# ...

def is_superuser(article, user):
    """Return True if user is a superuser, False otherwise."""
    return not user.is_anonymous() and user.is_superuser

def is_builder(article, user):
    """Return True if user is a builder, False otherwise."""
    return not user.is_anonymous() and user.locks.check_lockstring(user, "perm(Builders)")

def is_anyone(article, user):
    """Return True even if the user is anonymous."""
    return True

# Who can create new groups and users from the wiki?
WIKI_CAN_ADMIN = is_superuser
# Who can change owner and group membership?
WIKI_CAN_ASSIGN = is_superuser
# Who can change group membership?
WIKI_CAN_ASSIGN_OWNER = is_superuser
# Who can change read/write access to groups or others?
WIKI_CAN_CHANGE_PERMISSIONS = is_superuser
# Who can soft-delete an article?
WIKI_CAN_DELETE = is_builder
# Who can lock an article and permanently delete it?
WIKI_CAN_MODERATE = is_superuser
# Who can edit articles?
WIKI_CAN_WRITE = is_builder
# Who can read articles?
WIKI_CAN_READ = is_anyone
```

Here, we have created three functions: one to return `True` if the user is the superuser, one to
return `True` if the user is a builder, one to return `True` no matter what (this includes if the
user is anonymous, E.G. if it's not logged-in).  We then change settings to allow either the
superuser or
each builder to moderate, read, write, delete, and more.  You can, of course, add more functions,
adapting them to your need.  This is just a demonstration.

Providing the `WIKI_CAN*...` settings will bypass the original permission system.  The superuser
could change permissions of an article, but still, only builders would be able to write it.  If you
need something more custom, you will have to expand on the functions you use.

### Managing wiki pages from Evennia

Unfortunately, Django wiki doesn't provide a clear and clean entry point to read and write articles
from Evennia and it doesn't seem to be a very high priority.  If you really need to keep Django wiki
and to create and manage wiki pages from your code, you can do so, but this article won't elaborate,
as this is somewhat more technical.

However, it is a good opportunity to present a small project that has been created more recently:
[evennia-wiki](https://github.com/vincent-lg/evennia-wiki) has been created to provide a simple
wiki, more tailored to Evennia and easier to connect.  It doesn't, as yet, provide as many options
as does Django wiki, but it's perfectly usable:

- Pages have an inherent and much-easier to understand hierarchy based on URLs.
- Article permissions are connected to Evennia groups and are much easier to accommodate specific
requirements.
- Articles can easily be created, read or updated from the Evennia code itself.
- Markdown is fully-supported with a default integration to Bootstrap to look good on an Evennia
website. Tables and table of contents are supported as well as wiki links.
- The process to override wiki templates makes full use of the `template_overrides` directory.

However evennia-wiki doesn't yet support:

- Images in markdown and the uploading schema.  If images are important to you, please consider
contributing to this new project.
- Modifying permissions on a per page/setting basis.
- Moving pages to new locations.
- Viewing page history.

Considering the list of features in Django wiki, obviously other things could be added to the list.
However, these features may be the most important and useful.  Additional ones might not be that
necessary.  If you're interested in supporting this little project, you are more than welcome to
[contribute to it](https://github.com/vincent-lg/evennia-wiki).  Thanks!