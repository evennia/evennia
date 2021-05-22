# Game Website

When Evennia starts it will also start a [Webserver](Webserver) as part of the
[Server](Portal-And-Server) process. This uses Django to serve a simple but
functional default game website.  With the default setup, open your browser to
`localhost:4001` or `127.0.0.1:4001` to see it.

The website allows existing players to log in using an account-name and
password they previously used to register with the game. If a user logs in with
the [Webclient](Webclient) they will also log into the website and vice-versa.
So if you are logged into the website, opening the webclient will automatically
log you into the game as that account.

The default website shows a "Welcome!" page with a few links to useful
resources. It also shows some statistics about how many players are currently
connected.

In the top menu you can find
- Home - Get back to front page.
- Document - A link to the latest stable Evennia documentation.
- Characters - This is a demo of connecting in-game characters to the website.
  It will display a list of all entities of the
  _typeclasses.characters.Character` typeclass and allow you to view their
  description with an optional image. The list is only available to logged-in
  users.
- Channels - This is a demo of connecting in-game chats to the website. It will
  show a list of all channels available to you and allow you to view the latest
  discussions. Most channels require logging in, but the `Public` channel can
  also be viewed by non-loggedin users.
- Help - This ties the in-game [Help system](Help-System) to the website. All
  database-based help entries that are publicly available or accessible to your
  account can be read. This is a good way to present a body of help for people
  to read outside of the game.
- Play Online - This opens the [Webclient](Webclient) in the browser.


## Modifying the default Website

You can modify and override all aspects of the web site from your game dir.
You'll mostly be doing so in your settings file
(`mygame/server/conf/settings.py` and in the gamedir's `web/folder`
(`mygame/web/` if your game folder is `mygame/`).

As explained on the [Webserver](Webserver) page, the process for getting a web
page is

1. Web browser sends HTTP request to server with an URL
2. `urls.py` uses regex to match that URL to a _view_ (a Python function or callable class).
3. The correct Python view is loaded and executes.
4. The view pulls in a _template_, a HTML document with placeholder markers in it,
   and fills those in as needed (it may also use a _form_ to customize user-input in the same way).
   A HTML page may also in turn point to static resources (usually CSS, sometimes images etc).
5. The rendered HTML page is returned to the browser as a HTTP response.  If
   the HTML page requires static resources are requested, the browser will
   fetch those separately before displaying it to the user.

If you look at the [evennia/web/](github:develop/evennia/web) directory you'll find the following
structure (leaving out stuff not relevant to the website):

```
  evennia/web/
    ...
    static/
        website/
            css/
               (css style files)
            images/
               (images to show)

    templates/
        website/
          (html files)

    website/
      urls.py
      views/
      (all python files related to website)

    urls.py

```

The top-level `web/urls.py` file 'includes' the `web/website/urls.py` file -
that way all the website-related url-handling is kept in the same place.

This is the layout of the `mygame/web/` folder relevant for the website:

```
  mygame/web/
    ...
    static/
      website/
        css/
        images/

    templates/
      website/

      website/
        urls.py
        views/

    urls.py

```

```versionchanged:: 1.0

  Game folders created with older versions of Evennia will lack most of this
  convenient `mygame/web/` layout. If you use a game dir from an older version,
  you should copy over the missing `evennia/game_template/web/` folders from
  there, as well as the main urls.py file.

```

As you can see, the `mygame/web/` folder is a copy of the `evennia/web/` folder
structure except the `mygame` folders are mostly empty.

For static- and template-files, Evennia will _first_
look in `mygame/static` and `mygame/templates` before going to the default
locations in `evennia/web/`.  So override these resources, you just need to put
a file with the same name in the right spot under `mygame/web/` (and then
reload the server). Easiest is often to copy the original over and modify it.

Overridden views (Python modules) also need an additional tweak to the
`website/urls.py` file - you must make sure to repoint the url to the new
version rather than it using the original.

### Title and blurb

The website's title and blurb are simply changed by tweaking
`settings.SERVERNAME` and `settings.GAME_SLOGAN`. Your settings file is in
`mygame/server/conf/settings.py`, just change `SERVERNAME = "My Awesome Game"`
and add `GAME_SLOGAN = "The best game in the world"` or something.

### Logo

The Evennia googly-eyed snake logo is probably not what you want for your game.
The template looks for a file  `web/static/website/images/evennia_logo.png`. Just
plop your own PNG logo (64x64 pixels large) in there and name it the same.

### Index page

This is the front page of the website (the 'index' in HTML parlance).

#### Index HTML template

The frontpage template is found in
`evennia/web/templates/website/index.html`. Just copy this to the equivalent place in
`mygame/web/`. Modify it there and reload the server to see your changes.

Django templates has a few special features that separate them from normal HTML
documents - they contain a special templating language marked with `{% ... %}` and
`{{ ... }}`.

Some important things to know:

- `{% extends "base.html" %}` - This is equivalent to a Python
  `from othermodule import *` statement, but for templates. It allows a given template
  to use everything from the imported (extended) template, but also to override anything
  it wants to change. This makes it easy to keep all pages looking the same and avoids
  a lot of boiler plate.
- `{% block blockname %}...{% endblock %}` - Blocks are inheritable, named pieces of code
  that are modified in one place and then used elsewhere. This works a bit in reverse to
  normal inheritance, because it's commonly in such a way that `base.html` defines an empty
  block, let's say `contents`: `{% block contents %}{% endblock %}` but makes sure to put
  that _in the right place_, say in the main body, next to the sidebar etc. Then each page
  does `{% extends "base.html %"}` and makes their own `{% block contents} <actual content> {% endblock %}`.
  Their `contents` block will now override the empty one in `base.html` and appear in the right
  place in the document, without the extending template having to specifying everything else
  around it!
- `{{ ... }}` are 'slots' usually embedded inside HTML tags or content. They reference a
  _context_ (basically a dict) that the Python _view_ makes available to it.
  Keys on the context are accessed with dot-notation, so if you provide a
  context `{"stats": {"hp": 10, "mp": 5}}` to your template, you could access
  that as  `{{ stats.hp }}` to display `10` at that location to display `10` at
  that location.


This allows for template inheritance (making it easier to make all
pages look the same without rewriting the same thing over and over)

There's a lot more information to be found in the [Django template language documentation](https://docs.djangoproject.com/en/3.2/ref/templates/language/).

#### Index View

To find where the index view is found, we look in `evennia/web/website/urls.py`. Here
we find the following line:

This is found in `evennia/web/website/views/index.py`. If you don't know

The frontpage view is a class `EvenniaIndexView`. This is a [Django class-based view](https://docs.djangoproject.com/en/3.2/topics/class-based-views/).
It's a little less visible what happens in a class-based view than in a function (since
the class implements a lot of functionality as methods), but it's powerful and
much easier to extend/modify.

The class property `template_name` sets the location of the template used under
the `templates/` folder. So `website/index.html` points to
`web/templates/website/index.html` (as we already explored above.

The `get_context_data` is a convenient method for providing the context for the
template. In the index-page's case we want the game stats (number of recent
players etc). These are then made available to use in `{{ ... }}` slots in the
template as described in the previous section.

### Other website pages

The other sub pages are handled in the same way - copy the template or static
resource to the right place
