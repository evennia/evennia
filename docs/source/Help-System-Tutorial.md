# Help System Tutorial


**Before doing this tutorial you will probably want to read the intro in [Basic Web tutorial](./Web-Tutorial).**  Reading the three first parts of the [Django tutorial](https://docs.djangoproject.com/en/1.9/intro/tutorial01/) might help as well.

This tutorial will show you how to access the help system through your website.  Both help commands and regular help entries will be visible, depending on the logged-in user or an anonymous character.

This tutorial will show you how to:

- Create a new page to add to your website.
- Take advantage of a basic view and basic templates.
- Access the help system on your website.
- Identify whether the viewer of this page is logged-in and, if so, to what account.

## Creating our app

The first step is to create our new Django *app*.  An app in Django can contain pages and mechanisms: your website may contain different apps.  Actually, the website provided out-of-the-box by Evennia has already three apps: a "webclient" app, to handle the entire webclient, a "website" app to contain your basic pages, and a third app provided by Django to create a simple admin interface.  So we'll create another app in parallel, giving it a clear name to represent our help system.

From your game directory, use the following command:

    evennia startapp help_system

> Note: calling the app "help" would have been more explicit, but this name is already used by Django.

This will create a directory named `help_system` at the root of your game directory.  It's a good idea to keep things organized and move this directory in the "web" directory of your game.  Your game directory should look like:

    mygame/
        ...
        web/
            help_system/
            ...

The "web/help_system" directory contains files created by Django.  We'll use some of them, but if you want to learn more about them all, you should read [the Django tutorial](https://docs.djangoproject.com/en/1.9/intro/tutorial01/).

There is a last thing to be done: your folder has been added, but Django doesn't know about it, it doesn't know it's a new app.  We need to tell it, and we do so by editing a simple setting.  Open your "server/conf/settings.py" file and add, or edit, these lines:

```python
# Web configuration
INSTALLED_APPS += (
        "web.help_system",
)
```

You can start Evennia if you want, and go to your website, probably at [http://localhost:4001](http://localhost:4001) . You won't see anything different though: we added the app but it's fairly empty.

## Our new page

At this point, our new *app*  contains mostly empty files that you can explore.  In order to create a page for our help system, we need to add:

- A *view*, dealing with the logic of our page.
- A *template* to display our new page.
- A new *URL* pointing to our page.

> We could get away by creating just a view and a new URL, but that's not a recommended way to work with your website.  Building on templates is so much more convenient.

### Create a view

A *view* in Django is a simple Python function placed in the "views.py" file in your app.  It will handle the behavior that is triggered when a user asks for this information by entering a *URL* (the connection between *views* and *URLs* will be discussed later).

So let's create our view.  You can open the "web/help_system/view.py" file and paste the following lines:

```python
from django.shortcuts import render

def index(request):
    """The 'index' view."""
    return render(request, "help_system/index.html")
```

Our view handles all code logic.  This time, there's not much: when this function is called, it will render the template we will now create.  But that's where we will do most of our work afterward.

### Create a template

The `render` function called into our *view* asks the *template* `help_system/index.html`.  The *templates* of our apps are stored in the app directory, "templates" sub-directory.  Django may have created the "templates" folder already.  If not, create it yourself.  In it, create another folder "help_system", and inside of this folder, create a file named "index.html".  Wow, that's some hierarchy.  Your directory structure (starting from `web`) should look like this:

    web/
        help_system/
            ...
            templates/
                help_system/
                    index.html

Open the "index.html" file and paste in the following lines:

```
{% extends "base.html" %}
{% block titleblock %}Help index{% endblock %}
{% block content %}
<h2>Help index</h2>
{% endblock %}
```

Here's a little explanation line by line of what this template does:

1. It loads the "base.html" *template*.  This describes the basic structure of all your pages, with a menu at the top and a footer, and perhaps other information like images and things to be present on each page.  You can create templates that do not inherit from "base.html", but you should have a good reason for doing so.
2. The "base.html" *template* defines all the structure of the page.  What is left is to override some sections of our pages.  These sections are called *blocks*.  On line 2, we override the block named "blocktitle", which contains the title of our page.
3. Same thing here, we override the *block* named "content", which contains the main content of our web page.  This block is bigger, so we define it on several lines.
4. This is perfectly normal HTML code to display a level-2 heading.
5. And finally we close the *block* named "content".

### Create a new URL

Last step to add our page: we need to add a *URL* leading to it... otherwise users won't be able to access it.  The URLs of our apps are stored in the app's directory "urls.py" file.

Open the "web/help_system/urls.py" file (you might have to create it) and write in it:

```python
# URL patterns for the help_system app

from django.conf.urls import url
from web.help_system.views import index

urlpatterns = [
    url(r'^$', index, name="index")
]
```

We also need to add our app as a namespace holder for URLS.  Edit the file "web/urls.py".  In it you will find the `custom_patterns` variable.  Replace it with:

```python
custom_patterns = [
    url(r'^help/', include('web.help_system.urls',
            namespace='help_system', app_name='help_system')),
]
```

When a user will ask for a specific *URL* on your site, Django will:

1. Read the list of custom patterns defined in "web/urls.py".  There's one pattern here, which describes to Django that all URLs beginning by 'help/' should be sent to the 'help_system' app.  The 'help/' part is removed.
2. Then Django will check the "web.help_system/urls.py" file.  It contains only one URL, which is empty (`^$`).

In other words, if the URL is '/help/', then Django will execute our defined view.

### Let's see it work

You can now reload or start Evennia.  Open a tab in your browser and go to [http://localhost:4001/help/](http://localhost:4001/help/) .  If everything goes well, you should see your new page... which isn't empty since Evennia uses our "base.html" *template*.  In the content of our page, there's only a heading that reads "help index".  Notice that the title of our page is "mygame - Help index" ("mygame" is replaced by the name of your game).

From now on, it will be easier to move forward and add features.

### A brief reminder

We'll be trying the following things:

- Have the help of commands and help entries accessed online.
- Have various commands and help entries depending on whether the user is logged in or not.

In terms of pages, we'll have:

- One to display the list of help topics.
- One to display the content of a help topic.

The first one would link to the second.

> Should we create two URLs?

The answer is... maybe.  It depends on what you want to do.  We have our help index accessible through the "/help/" URL.  We could have the detail of a help entry accessible through "/help/desc" (to see the detail of the "desc" command).  The problem is that our commands or help topics may contain special characters that aren't to be present in URLs.  There are different ways around this problem.  I have decided to use a *GET variable* here, which would create URLs like this:

    /help?name=desc

If you use this system, you don't have to add a new URL:  GET and POST variables are accessible through our requests and we'll see how soon enough.

## Handling logged-in users

One of our requirements is to have a help system tailored to our accounts.  If an account with admin access logs in, the page should display a lot of commands that aren't accessible to common users.  And perhaps even some additional help topics.

Fortunately, it's fairly easy to get the logged in account in our view (remember that we'll do most of our coding there).  The *request* object, passed to our function, contains a `user` attribute.  This attribute will always be there: we cannot test whether it's `None` or not, for instance.  But when the request comes from a user that isn't logged in, the `user` attribute will contain an anonymous Django user.  We then can use the `is_anonymous` method to see whether the user is logged-in or not.  Last gift by Evennia, if the user is logged in, `request.user` contains a reference to an account object, which will help us a lot in coupling the game and online system.

So we might end up with something like:

```python
def index(request):
    """The 'index' view."""
    user = request.user
    if not user.is_anonymous() and user.character:
        character = user.character
```

> Note: this code works when your MULTISESSION_MODE is set to 0 or 1.  When it's above, you would have something like:

```python
def index(request):
    """The 'index' view."""
    user = request.user
    if not user.is_anonymous() and user.db._playable_characters:
        character = user.db._playable_characters[0]
```

In this second case, it will select the first character of the account.

But what if the user's not logged in?  Again, we have different solutions.  One of the most simple is to create a character that will behave as our default character for the help system.  You can create it through your game:  connect to it and enter:

    @charcreate anonymous

The system should answer:

    Created new character anonymous. Use @ic anonymous to enter the game as this character.

So in our view, we could have something like this:

```python
from typeclasses.characters import Character

def index(request):
    """The 'index' view."""
    user = request.user
    if not user.is_anonymous() and user.character:
        character = user.character
    else:
        character = Character.objects.get(db_key="anonymous")
```

This time, we have a valid character no matter what:  remember to adapt this code if you're running in multisession mode above 1.

## The full system

What we're going to do is to browse through all commands and help entries, and list all the commands that can be seen by this character (either our 'anonymous' character, or our logged-in character).

The code is longer, but it presents the entire concept in our view.  Edit the "web/help_system/views.py" file and paste into it:

```python
from django.http import Http404
from django.shortcuts import render
from evennia.help.models import HelpEntry

from typeclasses.characters import Character

def index(request):
    """The 'index' view."""
    user = request.user
    if not user.is_anonymous() and user.character:
        character = user.character
    else:
        character = Character.objects.get(db_key="anonymous")

    # Get the categories and topics accessible to this character
    categories, topics = _get_topics(character)

    # If we have the 'name' in our GET variable
    topic = request.GET.get("name")
    if topic:
        if topic not in topics:
            raise Http404("This help topic doesn't exist.")

        topic = topics[topic]
        context = {
                "character": character,
                "topic": topic,
        }
        return render(request, "help_system/detail.html", context)
    else:
        context = {
                "character": character,
                "categories": categories,
        }
        return render(request, "help_system/index.html", context)

def _get_topics(character):
    """Return the categories and topics for this character."""
    cmdset = character.cmdset.all()[0]
    commands = cmdset.commands
    entries = [entry for entry in HelpEntry.objects.all()]
    categories = {}
    topics = {}

    # Browse commands
    for command in commands:
        if not command.auto_help or not command.access(character):
            continue

        # Create the template for a command
        template = {
                "name": command.key,
                "category": command.help_category,
                "content": command.get_help(character, cmdset),
        }

        category = command.help_category
        if category not in categories:
            categories[category] = []
        categories[category].append(template)
        topics[command.key] = template

    # Browse through the help entries
    for entry in entries:
        if not entry.access(character, 'view', default=True):
            continue

        # Create the template for an entry
        template = {
                "name": entry.key,
                "category": entry.help_category,
                "content": entry.entrytext,
        }

        category = entry.help_category
        if category not in categories:
            categories[category] = []
        categories[category].append(template)
        topics[entry.key] = template

    # Sort categories
    for entries in categories.values():
        entries.sort(key=lambda c: c["name"])

    categories = list(sorted(categories.items()))
    return categories, topics
```

That's a bit more complicated here, but all in all, it can be divided in small chunks:

- The `index` function is our view:
  - It begins by getting the character as we saw in the previous section.
  - It gets the help topics (commands and help entries) accessible to this character.  It's another function that handles that part.
  - If there's a *GET variable* "name" in our URL (like "/help?name=drop"), it will retrieve it.  If it's not a valid topic's name, it returns a *404*.  Otherwise, it renders the template called "detail.html", to display the detail of our topic.
  - If there's no *GET variable* "name", render "index.html", to display the list of topics.
- The `_get_topics` is a private function.  Its sole mission is to retrieve the commands a character can execute, and the help entries this same character can see.  This code is more Evennia-specific than Django-specific, it will not be detailed in this tutorial.  Just notice that all help topics are stored in a dictionary.  This is to simplify our job when displaying them in our templates.

Notice that, in both cases when we asked to render a *template*, we passed to `render` a third argument which is the dictionary of variables used in our templates.  We can pass variables this way, and we will use them in our templates.

### The index template

Let's look at our full "index" *template*.  You can open the "web/help_system/templates/help_sstem/index.html" file and paste the following into it:

```
{% extends "base.html" %}
{% block titleblock %}Help index{% endblock %}
{% block content %}
<h2>Help index</h2>
{% if categories %}
    {% for category, topics in categories %}
        <h2>{{ category|capfirst }}</h2>
        <table>
        <tr>
        {% for topic in topics %}
            {% if forloop.counter|divisibleby:"5" %}
                </tr>
                <tr>
            {% endif %}
            <td><a href="{% url 'help_system:index' %}?name={{ topic.name|urlencode }}">
            {{ topic.name }}</td>
        {% endfor %}
        </tr>
        </table>
    {% endfor %}
{% endif %}
{% endblock %}
```

This template is definitely more detailed.  What it does is:

1. Browse through all categories.
2. For all categories, display a level-2 heading with the name of the category.
3. All topics in a category (remember, they can be either commands or help entries) are displayed in a table.  The trickier part may be that, when the loop is above 5, it will create a new line.  The table will have 5 columns at the most per row.
4. For every cell in the table, we create a link redirecting to the detail page (see below).  The URL would look something like "help?name=say".  We use `urlencode` to ensure special characters are properly escaped.

### The detail template

It's now time to show the detail of a topic (command or help entry).  You can create the file "web/help_system/templates/help_system/detail.html".  You can paste into it the following code:

```
{% extends "base.html" %}
{% block titleblock %}Help for {{ topic.name }}{% endblock %}
{% block content %}
<h2>{{ topic.name|capfirst }} help topic</h2>
<p>Category: {{ topic.category|capfirst }}</p>
{{ topic.content|linebreaks }}
{% endblock %}
```

This template is much easier to read.  Some *filters* might be unknown to you, but they are just used to format here.

### Put it all together

Remember to reload or start Evennia, and then go to [http://localhost:4001/help](http://localhost:4001/help/).  You should see the list of commands and topics accessible by all characters.  Try to login (click the "login" link in the menu of your website) and go to the same page again.  You should now see a more detailed list of commands and help entries.  Click on one to see its detail.

## To improve this feature

As always, a tutorial is here to help you feel comfortable adding new features and code by yourself.  Here are some ideas of things to improve this little feature:

- Links at the bottom of the detail template to go back to the index might be useful.
- A link in the main menu to link to this page would be great... for the time being you have to enter the URL, users won't guess it's there.
- Colors aren't handled at this point, which isn't exactly surprising.  You could add it though.
- Linking help entries between one another won't be simple, but it would be great.  For instance, if you see a help entry about how to use several commands, it would be great if these commands were themselves links to display their details.
