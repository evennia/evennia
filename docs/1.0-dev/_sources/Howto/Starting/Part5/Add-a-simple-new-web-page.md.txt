# Add a simple new web page


Evennia leverages [Django](https://docs.djangoproject.com) which is a web development framework.
Huge professional websites are made in Django and there is extensive documentation (and books) on it
. You are encouraged to at least look at the Django basic tutorials. Here we will just give a brief
introduction for how things hang together, to get you started.

We assume you have installed and set up Evennia to run. A webserver and website comes out of the
box. You can get to that by entering `http://localhost:4001` in your web browser - you should see a
welcome page with some game statistics and a link to the web client. Let us add a new page that you
can get to by going to `http://localhost:4001/story`.

## Create the view

A django "view" is a normal Python function that django calls to render the HTML page you will see
in the web browser. Here we will just have it spit back the raw html, but Django can do all sorts of
cool stuff with the page in the view, like adding dynamic content or change it on the fly. Open
`mygame/web` folder and add a new module there named `story.py` (you could also put it in its own
folder if you wanted to be neat. Don't forget to add an empty `__init__.py` file if you do, to tell
Python you can import from the new folder). Here's how it looks:

```python
# in mygame/web/story.py

from django.shortcuts import render

def storypage(request):
    return render(request, "story.html")
```

This view takes advantage of a shortcut provided to use by Django, _render_. This shortcut gives the
template some information from the request, for instance, the game name, and then renders it.

## The HTML page

We need to find a place where Evennia (and Django) looks for html files (called *templates* in
Django parlance). You can specify such places in your settings (see the `TEMPLATES` variable in
`default_settings.py` for more info), but here we'll use an existing one. Go to
`mygame/template/overrides/website/` and create a page `story.html` there.

This is not a HTML tutorial, so we'll go simple:

```html
{% extends "base.html" %}
{% block content %}
<div class="row">
  <div class="col">
    <h1>A story about a tree</h1>
    <p>
        This is a story about a tree, a classic tale ...
    </p>
  </div>
</div>
{% endblock %}
```

Since we've used the _render_ shortcut, Django will allow us to extend our base styles easily.

If you'd rather not take advantage of Evennia's base styles, you can do something like this instead:

```html
<html>
  <body>
    <h1>A story about a tree</h1>
    <p>
    This is a story about a tree, a classic tale ...
  </body>
</html>
```


## The URL

When you enter the address `http://localhost:4001/story` in your web browser, Django will parse that
field to figure out which page you want to go to. You tell it which patterns are relevant in the
file
[mygame/web/urls.py](https://github.com/evennia/evennia/blob/master/evennia/game_template/web/urls.py).
Open it now.

Django looks for the variable `urlpatterns` in this file. You want to add your new pattern to the
`custom_patterns` list we have prepared - that is then merged with the default `urlpatterns`. Here's
how it could look:

```python
from web import story

# ...

custom_patterns = [
    url(r'story', story.storypage, name='Story'),
]
```

That is, we import our story view module from where we created it earlier and then create an `url`
instance. The first argument to `url` is the pattern of the url we want to find (`"story"`) (this is
a regular expression if you are familiar with those) and then our view function we want to direct
to.

That should be it. Reload Evennia and you should be able to browse to your new story page!
