# Web Tutorial


Evennia uses the [Django](https://www.djangoproject.com/) web framework as the basis of both its
database configuration and the website it provides. While a full understanding of Django requires
reading the Django documentation, we have provided this tutorial to get you running with the basics
and how they pertain to Evennia. This text details getting everything set up. The 
[Web-based Character view Tutorial](../../Web-Character-View-Tutorial.md) gives a more explicit example of making a
custom web page connected to your game, and you may want to read that after finishing this guide.

## A Basic Overview

Django is a web framework. It gives you a set of development tools for building a website quickly
and easily.

Django projects are split up into *apps* and these apps all contribute to one project. For instance,
you might have an app for conducting polls, or an app for showing news posts or, like us, one for
creating a web client.

Each of these applications has a `urls.py` file, which specifies what
[URL](https://en.wikipedia.org/wiki/Uniform_resource_locator)s are used by the app, a `views.py` file
for the code that the URLs activate, a `templates` directory for displaying the results of that code
in [HTML](https://en.wikipedia.org/wiki/Html) for the user, and a `static` folder that holds assets
like [CSS](https://en.wikipedia.org/wiki/CSS), [Javascript](https://en.wikipedia.org/wiki/Javascript),
and Image files (You may note your mygame/web folder does not have a `static` or `template` folder.
This is intended and explained further below). Django applications may also have a `models.py` file
for storing information in the database. We will not change any models here, take a look at the 
[New Models](../../../Concepts/New-Models.md) page (as well as the [Django docs](https://docs.djangoproject.com/en/1.7/topics/db/models/) on models) if you are interested.

There is also a root `urls.py` that determines the URL structure for the entire project. A starter
`urls.py` is included in the default game template, and automatically imports all of Evennia's
default URLs for you. This is located in `web/urls.py`.

## Changing the logo on the front page

Evennia's default logo is a fun little googly-eyed snake wrapped around a gear globe. As cute as it
is, it probably doesn't represent your game. So one of the first things you may wish to do is
replace it with a logo of your own.

Django web apps all have _static assets_: CSS files, Javascript files, and Image files. In order to
make sure the final project has all the static files it needs, the system collects the files from
every app's `static` folder and places it in the `STATIC_ROOT` defined in `settings.py`. By default,
the Evennia `STATIC_ROOT` is in `web/static`.

Because Django pulls files from all of those separate places and puts them in one folder, it's
possible for one file to overwrite another. We will use this to plug in our own files without having
to change anything in the Evennia itself.

By default, Evennia is configured to pull files you put in the `web/static_overrides` *after* all
other static files. That means that files in `static_overrides` folder will overwrite any previously
loaded files *having the same path under its static folder*. This last part is important to repeat:
To overload the static resource from a standard `static` folder you need to replicate the path of
folders and file names from that `static` folder in exactly the same way inside `static_overrides`.

Let's see how this works for our logo. The default web application is in the Evennia library itself,
in `evennia/web/`. We can see that there is a `static` folder here. If we browse down, we'll
eventually find the full path to the Evennia logo file:
`evennia/web/static/evennia_general/images/evennia_logo.png`.

Inside our `static_overrides` we must replicate the part of the path inside the `static` folder, in
other words, we must replicate `evennia_general/images/evennia_logo.png`.

So, to change the logo, we need to create the folder path `evennia_general/images/` in
`static_overrides`. We then rename our own logo file to `evennia_logo.png` and copy it there. The
final path for this file would thus be:
`web/static_overrides/evennia_general/images/evennia_logo.png` in your local game folder.

To get this file pulled in, just change to your own game directory and reload the server:

```
evennia reload
```

This will reload the configuration and bring in the new static file(s). If you didn't want to reload
the server you could instead use

```
evennia collectstatic
```

to only update the static files without any other changes.

> **Note**: Evennia will collect static files automatically during startup. So if `evennia
collectstatic` reports finding 0 files to collect, make sure you didn't start the engine at some
point - if so the collector has already done its work! To make sure, connect to the website and
check so the logo has actually changed to your own version.

> **Note**: Sometimes the static asset collector can get confused. If no matter what you do, your
overridden files aren't getting copied over the defaults, try removing the target file (or
everything) in the `web/static` directory, and re-running `collectstatic` to gather everything from
scratch.

## Changing the Front Page's Text

The default front page for Evennia contains information about the Evennia project. You'll probably
want to replace this information with information about your own project. Changing the page template
is done in a similar way to changing static resources.

Like static files, Django looks through a series of template folders to find the file it wants. The
difference is that Django does not copy all of the template files into one place, it just searches
through the template folders until it finds a template that matches what it's looking for. This
means that when you edit a template, the changes are instant. You don't have to reload the server or
run any extra commands to see these changes - reloading the web page in your browser is enough.

To replace the index page's text, we'll need to find the template for it. We'll go into more detail
about how to determine which template is used for rendering a page in the 
[Web-based Character view Tutorial](../../Web-Character-View-Tutorial.md). For now, you should know that the template we want to change
is stored in `evennia/web/website/templates/website/index.html`.

To replace this template file, you will put your changed template inside the
`web/template_overrides/website` directory in your game folder. In the same way as with static
resources you must replicate the path inside the default `template` directory exactly. So we must
copy our replacement template named `index.html` there (or create the `website` directory in
web/template_overrides` if it does not exist, first). The final path to the file should thus be:
`web/template_overrides/website/index.html` within your game directory.

Note that it is usually easier to just copy the original template over and edit it in place. The
original file already has all the markup and tags, ready for editing.

## Further reading

For further hints on working with the web presence, you could now continue to the 
[Web-based Character view Tutorial](../../Web-Character-View-Tutorial.md) where you learn to make a web page that
displays in-game character stats. You can also look at [Django's own
tutorial](https://docs.djangoproject.com/en/1.7/intro/tutorial01/) to get more insight in how Django
works and what possibilities exist.