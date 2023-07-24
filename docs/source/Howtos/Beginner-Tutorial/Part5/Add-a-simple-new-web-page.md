# Add a simple new web page
Evennia leverages [Django](https://docs.djangoproject.com) which is a web development framework.
Huge professional websites are made in Django and there is extensive documentation (and books) on it.
You are encouraged to at least look at the Django basic tutorials. Here we will just give a brief
introduction for how things hang together, to get you started.

We assume you have installed and set up Evennia to run. A webserver and website comes along with the
default Evennia install out of the box. You can view the default website by pointing your web browser
to `http://localhost:4001`. You will see a generic welcome page with some game statistics and a link
to the Evennia web client. 

In this tutorial, we will add a new page that you can visit at `http://localhost:4001/story`.

### Create the view

A django "view" is a normal Python function that django calls to render the HTML page you will see
in the web browser. Django can do all sorts of cool stuff to a page by using the view function &mdash; like
adding dynamic content or making changes to a page on the fly &mdash; but, here, we will just have it spit
back raw HTML.

Open `mygame/web/website` folder and create a new module file there named `story.py`. (You could also
put it in its own folder if you wanted to be neat but, if you do, don't forget to add an empty 
`__init__.py` file in the new folfder. Adding the `__init__.py` file tells Python that modules can be
imported from the new folder. For this tutorial, here's what the example contents of your new `story.py`
module should look like:

```python
# in mygame/web/website/story.py

from django.shortcuts import render

def storypage(request):
    return render(request, "story.html")
```

The above view takes advantage of a shortcut provided for use by Django: _render_. The render shortcut
gives the template information from the request. For instance, it might provide the game name, and then
renders it.

### The HTML page

Next, we need to find the location where Evennia (and Django) looks for HTML files, which are referred
to as *templates* in Django's parlance. You can specify such locations in your settings (see the
`TEMPLATES` variable in `default_settings.py` for more info) but, here we'll use an existing one. 

Navigate to `mygame/web/templates/website/` and create a new file there called `story.html`. This
is not an HTML tutorial, so this file's content will be simple:

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

As shown above, Django will allow us to extend our base styles easily because we've used the
_render_ shortcut. If you'd prefer to not take advantage of Evennia's base styles, you might
instead do something like this:

```html
<html>
  <body>
    <h1>A story about a tree</h1>
    <p>
    This is a story about a tree, a classic tale ...
  </body>
</html>
```

### The URL

When you enter the address `http://localhost:4001/story` in your web browser, Django will parse the
stub following the port &mdash; here, `/story` &mdash; to find out to which page you would like displayed. How
does Django know what HTML file `/story` should link to? You inform Django about what address stub
patterns correspond to what files in the file `mygame/web/website/urls.py`. Open it in your editor now.

Django looks for the variable `urlpatterns` in this file. You will want to add your new `story` pattern
and corresponding path to `urlpatterns` list &mdash; which is then, in turn, merged with the default
`urlpatterns`. Here's how it could look:

```python
"""
This reroutes from an URL to a python view-function/class.
The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.
"""
from django.urls import path

from web.website import story

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

# add patterns here
urlpatterns = [
    # path("url-pattern", imported_python_view),
    path(r"story", story.storypage, name="Story"),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
```

The above code imports our `story.py` Python view module from where we created it earlier &mdash; in 
`mygame/web/website/` &mdash; and then add the corresponding `path` instance. The first argument to
`path` is the pattern of the URL that we want to find (`"story"`) as a regular expression, and
then the view function from `story.py` that we want to call.

That should be it. Reload Evennia &mdash; `evennia reload` &mdash; and you should now be able to navigate
your browser to the `http://localhost:4001/story` location and view your new story page as
rendered by Python!
