# Web Features


Evennia is its own webserver and hosts a default website and browser webclient.

## Web site

The Evennia website is a Django application that ties in with the MUD database. Since the website
shares this database you could, for example, tell website visitors how many accounts are logged into
the game at the moment, how long the server has been up and any other database information you may
want. During development you can access the website by pointing your browser to
`http://localhost:4001`.

> You may also want to set `DEBUG = True` in your settings file for debugging the website. You will
then see proper tracebacks in the browser rather than just error codes. Note however that this will
*leak memory a lot* (it stores everything all the time) and is *not to be used in production*. It's
recommended to only use `DEBUG` for active web development and to turn it off otherwise.

A Django (and thus Evennia) website basically consists of three parts, a
[view](https://docs.djangoproject.com/en/1.9/topics/http/views/) an associated
[template](https://docs.djangoproject.com/en/1.9/topics/templates/) and an `urls.py` file. Think of
the view as the Python back-end and the template as the HTML files you are served, optionally filled
with data from the back-end. The urls file is a sort of mapping that tells Django that if a specific
URL is given in the browser, a particular view should be triggered. You are wise to review the
Django documentation for details on how to use these components.

Evennia's default website is located in
[evennia/web/website](https://github.com/evennia/evennia/tree/master/evennia/web/website). In this
folder you'll find the simple default view as well as subfolders `templates` and `static`. Static
files are things like images, CSS files and Javascript.

### Customizing the Website

You customize your website from your game directory. In the folder `web` you'll find folders
`static`, `templates`, `static_overrides` and `templates_overrides`. The first two of those are
populated automatically by Django and used to serve the website. You should not edit anything in
them - the change will be lost. To customize the website you'll need to copy the file you want to
change from the `web/website/template/` or `web/website/static/` path to the corresponding place
under one of `_overrides` directories.

Example: To override or modify `evennia/web/website/template/website/index.html` you need to
add/modify `mygame/web/template_overrides/website/index.html`.

The detailed description on how to customize the website is best described in tutorial form. See the
[Web Tutorial](./Web-Tutorial.md) for more information.

### Overloading Django views

The Python backend for every HTML page is called a [Django
view](https://docs.djangoproject.com/en/1.9/topics/http/views/). A view can do all sorts of
functions, but the main one is to update variables data that the page can display, like how your
out-of-the-box website will display statistics about number of users and database objects.

To re-point a given page to a `view.py` of your own, you need to modify `mygame/web/urls.py`. An
[URL pattern](https://docs.djangoproject.com/en/1.9/topics/http/urls/) is a [regular
expression](https://en.wikipedia.org/wiki/Regular_expression) that you need to enter in the address
field of your web browser to get to the page in question. If you put your own URL pattern *before*
the default ones, your own view will be used instead. The file `urls.py` even marks where you should
put your change.

Here's an example:

```python
# mygame/web/urls.py

from django.conf.urls import url, include
# default patterns
from evennia.web.urls import urlpatterns

# our own view to use as a replacement
from web.myviews import myview

# custom patterns to add
patterns = [
    # overload the main page view
    url(r'^', myview, name='mycustomview'),
]

urlpatterns = patterns + urlpatterns

```

Django will always look for a list named `urlpatterns` which consists of the results of `url()`
calls. It will use the *first* match it finds in this list. Above, we add a new URL redirect from
the root of the website. It will now our own function `myview` from a new module
`mygame/web/myviews.py`.

> If our game is found on `http://mygame.com`, the regular expression `"^"` means we just entered
`mygame.com` in the address bar. If we had wanted to add a view for `http://mygame.com/awesome`, the
regular expression would have been `^/awesome`.

Look at [evennia/web/website/views.py](https://github.com/evennia/evennia/blob/master/evennia/web/website/views.py#L82) to see the inputs and outputs you must have to define a view. Easiest may be to
copy the default file to `mygame/web` to have something to modify and expand on.

Restart the server and reload the page in the browser - the website will now use your custom view.
If there are errors, consider turning on `settings.DEBUG` to see the full tracebacks - in debug mode
you will also log all requests in `mygame/server/logs/http_requests.log`.

## Web client


Evennia comes with a MUD client accessible from a normal web browser. During
development you can try it at `http://localhost:4001/webclient`.
[See the Webclient page](./Webclient.md) for more details.


## The Django 'Admin' Page

Django comes with a built-in [admin
website](https://docs.djangoproject.com/en/1.10/ref/contrib/admin/). This is accessible by clicking
the 'admin' button from your game website. The admin site allows you to see, edit and create objects
in your database from a graphical interface.

The behavior of default Evennia models are controlled by files `admin.py` in the Evennia package.
New database models you choose to add yourself (such as in the Web Character View Tutorial) can/will
also have `admin.py` files. New models are registered to the admin website by a call of
`admin.site.register(model class, admin class)` inside an admin.py file. It is an error to attempt
to register a model that has already been registered.

To overload Evennia's admin files you don't need to modify Evennia itself. To customize you can call
`admin.site.unregister(model class)`, then follow that with `admin.site.register` in one of your own
admin.py files in a new app that you add.

## More reading

Evennia relies on Django for its web features. For details on expanding your web experience, the
[Django documentation](https://docs.djangoproject.com/en) or the [Django
Book](http://www.djangobook.com/en/2.0/index.html) are the main resources to look into. In Django
lingo, the Evennia is a django "project" that consists of Django "applications". For the sake of web
implementation, the relevant django "applications" in default Evennia are `web/website` or
`web/webclient`.
