# Web Character View Tutorial


**Before doing this tutorial you will probably want to read the intro in [Basic Web tutorial](Web-Tutorial).**

In this tutorial we will create a web page that displays the stats of a game character. For this, and all other pages we want to make specific to our game, we'll need to create our own Django "app"

We'll call our app `character`, since it will be dealing with character information. From your game dir, run

    evennia startapp character

This will create a directory named `character` in the root of your game dir. It contains all basic files that a Django app needs. To keep `mygame` well ordered, move it to your `mygame/web/` directory instead: 

    mv character web/

Note that we will not edit all files in this new directory, many of the generated files are outside the scope of this tutorial.

In order for Django to find our new web app, we'll need to add it to the `INSTALLED_APPS` setting. Evennia's default installed apps are already set, so in `server/conf/settings.py`, we'll just extend them:

```python
INSTALLED_APPS += ('web.character',)
```

> Note: That end comma is important. It makes sure that Python interprets the addition as a tuple instead of a string.

The first thing we need to do is to create a *view* and an *URL pattern* to point to it. A view is a function that generates the web page that a visitor wants to see, while the URL pattern lets Django know what URL should trigger the view. The pattern may also provide some information of its own as we shall see.

Here is our `character/urls.py` file (**Note**: you may have to create this file if a blank one wasn't generated for you):

```python
# URL patterns for the character app

from django.conf.urls import url
from web.character.views import sheet 

urlpatterns = [
    url(r'^sheet/(?P<object_id>\d+)/$', sheet, name="sheet")
]
```

This file contains all of the URL patterns for the application. The `url` function in the `urlpatterns` list are given three arguments. The first argument is a pattern-string used to identify which URLs are valid. Patterns are specified as *regular expressions*. Regular expressions are used to match strings and are written in a special, very compact, syntax. A detailed description of regular expressions is beyond this tutorial but you can learn more about them [here](https://docs.python.org/2/howto/regex.html). For now, just accept that this regular expression requires that the visitor's URL looks something like this:

````
sheet/123/
````

That is, `sheet/` followed by a number, rather than some other possible URL pattern. We will interpret this number as object ID. Thanks to how the regular expression is formulated, the pattern recognizer stores the number in a variable called `object_id`. This will be passed to the view (see below). We add the imported view function (`sheet`) in the second argument. We also add the `name` keyword to identify the URL pattern itself. You should always name your URL patterns, this makes them easy to refer to in html templates using the `{% url %}` tag (but we won't get more into that in this tutorial).

> Security Note: Normally, users do not have the ability to see object IDs within the game (it's restricted to superusers only). Exposing the game's object IDs to the public like this enables griefers to perform what is known as an [account enumeration attack](http://www.sans.edu/research/security-laboratory/article/attacks-browsing) in the efforts of hijacking your superuser account. Consider this: in every Evennia installation, there are two objects that we can *always* expect to exist and have the same object IDs-- Limbo (#2) and the superuser you create in the beginning (#1). Thus, the griefer can get 50% of the information they need to hijack the admin account (the admin's username) just by navigating to `sheet/1`!

Next we create `views.py`, the view file that `urls.py` refers to.

```python
# Views for our character app

from django.http import Http404
from django.shortcuts import render
from django.conf import settings

from evennia.utils.search import object_search
from evennia.utils.utils import inherits_from

def sheet(request, object_id):
    object_id = '#' + object_id
    try:
        character = object_search(object_id)[0]
    except IndexError:
        raise Http404("I couldn't find a character with that ID.")
    if not inherits_from(character, settings.BASE_CHARACTER_TYPECLASS):
        raise Http404("I couldn't find a character with that ID. "
                      "Found something else instead.")
    return render(request, 'character/sheet.html', {'character': character})
```

As explained earlier, the URL pattern parser in `urls.py` parses the URL and passes `object_id` to our view function `sheet`. We do a database search for the object using this number. We also make sure such an object exists and that it is actually a Character. The view function is also handed a `request` object. This gives us information about the request, such as if a logged-in user viewed it - we won't use that information here but it is good to keep in mind. 

On the last line, we call the `render` function. Apart from the `request` object, the `render` function takes a path to an html template and a dictionary with extra data you want to pass into said template. As extra data we pass the Character object we just found. In the template it will be available as the variable "character". 

The html template is created as `templates/character/sheet.html` under your `character` app folder. You may have to manually create both `template` and its subfolder `character`. Here's the template to create:

````html
{% extends "base.html" %}
{% block content %}

    <h1>{{ character.name }}</h1>

    <p>{{ character.db.desc }}</p>

    <h2>Stats</h2>
    <table>
      <thead>
        <tr>
          <th>Stat</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Strength</td>
          <td>{{ character.db.str }}</td>
        </tr>
        <tr>
          <td>Intelligence</td>
          <td>{{ character.db.int }}</td>
        </tr>
        <tr>
          <td>Speed</td>
          <td>{{ character.db.spd }}</td>
        </tr>
      </tbody>
    </table>

    <h2>Skills</h2>
    <ul>
      {% for skill in character.db.skills %}
        <li>{{ skill }}</li>
      {% empty %}
        <li>This character has no skills yet.</li>
      {% endfor %}
    </ul>

    {% if character.db.approved %}
      <p class="success">This character has been approved!</p>
    {% else %}
      <p class="warning">This character has not yet been approved!</p>
    {% endif %}
{% endblock %}
````

In Django templates, `{% ... %}` denotes special in-template "functions" that Django understands. The `{{ ... }}` blocks work as "slots". They are replaced with whatever value the code inside the block returns.

The first line, `{% extends "base.html" %}`, tells Django that this template extends the base template that Evennia is using. The base template is provided by the theme. Evennia comes with the open-source third-party theme `prosimii`. You can find it and its `base.html` in `evennia/web/templates/prosimii`. Like other templates, these can be overwritten.

The next line is `{% block content %}`. The `base.html` file has `block`s, which are placeholders that templates can extend. The main block, and the one we use, is named `content`.

We can access the `character` variable anywhere in the template because we passed it in the `render` call at the end of `view.py`. That means we also have access to the Character's `db` attributes, much like you would in normal Python code. You don't have the ability to call functions with arguments in the template-- in fact, if you need to do any complicated logic, you should do it in `view.py` and pass the results as more variables to the template. But you still have a great deal of flexibility in how you display the data.

We can do a little bit of logic here as well. We use the `{% for %} ... {% endfor %}` and `{% if %} ... {% else %} ... {% endif %}` structures to change how the template renders depending on how many skills the user has, or if the user is approved (assuming your game has an approval system).

The last file we need to edit is the master URLs file. This is needed in order to smoothly integrate the URLs from your new `character` app with the URLs from Evennia's existing pages. Find the file `web/urls.py` and update its `patterns` list as follows:

```python
# web/urls.py

custom_patterns = [
    url(r'^character/', include('web.character.urls'))
   ]
```

Now reload the server with `evennia reload` and visit the page in your browser. If you haven't changed your defaults, you should be able to find the sheet for character `#1` at `http://localhost:4001/character/sheet/1/`

Try updating the stats in-game and refresh the page in your browser. The results should show immediately.

As an optional final step, you can also change your character typeclass to have a method called 'get_absolute_url'.
```python
# typeclasses/characters.py

    # inside Character
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('character:sheet', kwargs={'object_id':self.id})
```
Doing so will give you a 'view on site' button in the top right of the Django Admin Objects changepage that links to your new character sheet, and allow you to get the link to a character's page by using {{ object.get_absolute_url }} in any template where you have a given object.

*Now that you've made a basic page and app with Django, you may want to read the full Django tutorial to get a better idea of what it can do. [You can find Django's tutorial here](https://docs.djangoproject.com/en/1.8/intro/tutorial01/).*