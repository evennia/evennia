Web Features
============

Evennia is its own webserver and hosts a default website and browser
webclient.

Editing the Web site
--------------------

The Evennia website is a Django application that ties in with the MUD
database. It allows you to, for example, tell website visitors how many
players are logged into the game at the moment, how long the server has
been up and any other database information you may want. The dynamic
website application is located in ``src/web/website`` whereas you will
find the html files in ``src/web/templates/prosimii``. Static media such
as images, css and javascript files are served from ``src/web/media``.

You can access the website during development by going to
``http://localhost:8000``.

Since it's not recommended to edit files in ``src/`` directly, we need
to devise a way to allow website customization from ``game/gamesrc``.
This is not really finalized at the current time (it will be easier to
share media directories in Django 1.3) so for now, your easiest course
of action is probably to copy the entire ``src/web`` directory into
``game/gamesrc/`` and modify the copy. Make sure to retain permissions
so the server can access the directory.

You also need to modify the settings file. Set ``ROOT_URLCONF`` to your
new ``game.gamesrc.web.urls`` and add an entry
`` os.path.join(GAME_DIR, "web", "templates", ACTIVE_TEMPLATE)`` to the
``TEMPLATE_DIRS`` tuple. You should now have a separate website setup
you can edit as you like. Be aware that updates we do to ``src/web``
will not transfer automatically to your copy, so you'll need to apply
updates manually.

Web client
----------

Evennia comes with a MUD client accessible from a normal web browser. It
is technically a javascript client polling an asynchronous webserver
through long-polling (this is also known as a *COMET* setup). The
webclient server is defined in ``src/server/webclient`` and is not
something that should normally need to be edited unless you are creating
a custom client. The client javascript, html and css files are located
under the respective folders of ``src/web/``.

The webclient uses the `jQuery <http://jquery.com/>`_ javascript
library. This is imported automatically over the internet when running
the server. If you want to run the client without an internet
connection, you need to download the library from the jQuery homepage
and put it in ``src/web/media/javascript``. Then edit
``src/web/templates/prosimii/webclient.html`` and uncomment the line:

::

    <script src="/media/javascript/jquery-1.4.4.js" type="text/javascript" charset="utf-8"></script>

(edit it to match the name of the ``*.js`` for the jQuery version you
downloaded).

The webclient requires the webserver to be running and is then found on
``http://localhost:8000/webclient``. For now it's best to follow the
procedure suggested in the previous section if you want to customize it.
