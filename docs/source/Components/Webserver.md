# Webserver

When Evennia starts it also spins up its own Twisted-based web server. The
webserver is responsible for serving the html pages of the game's website. It
can also serve static resources like images and music.

The webclient runs as part of the [Server](./Portal-And-Server) process of
Evennia. This means that it can directly access cached objects modified
in-game, and there is no risk of working with objects that are temporarily
out-of-sync in the database.

The webserver runs on Twisted and is meant to be used in a production
environment. It leverages the Django web framework and provides:

- A [Game Website](./Website) - this is what you see when you go to
  `localhost:4001`. The look of the website is meant to be customized to your
  game. Users logged into the website will be auto-logged into the game if they
  do so with the webclient since they share the same login credentials (there
  is no way to safely do auto-login with telnet clients).
- The [Web Admin](./Web-Admin) is based on the Django web admin and allows you to
  edit the game database in a graphical interface.
- The [Webclient](./Webclient) page is served by the webserver, but the actual
  game communication (sending/receiving data) is done by the javascript client
  on the page opening a websocket connection directly to Evennia's Portal.


## Basic Webserver data flow

1. A user enters an url in their browser (or clicks a button). This leads to
   the browser sending a _HTTP request_ to the server containing an url-path
   (like for `https://localhost:4001/`, the part of the url we need to consider
   `/`). Other possibilities would be `/admin/`, `/login/`, `/channels/` etc.
2. evennia (through Django) will make use of the regular expressions registered
   in the `urls.py` file.  This acts as a rerouter to _views_, which are
   regular Python functions or callable classes able to process the incoming
   request (think of these as similar to the right Evennia Command being
   selected to handle your input - views are like Commands in this sense). In
   the case of `/` we reroute to a view handling the main index-page of the
   website.
3. The view code will prepare all the data needed by the web page. For the default
   index page, this means gather the game statistics so you can see how many
   are currently connected to the game etc.
4. The view will next fetch a _template_. A template is a HTML-document with special
   'placeholder' tags (written as `{{...}}` or `{% ... %}` usually). These
   placeholders allow the view to inject dynamic content into the HTML and make
   the page customized to the current situation. For the index page, it means
   injecting the current player-count in the right places of the html page. This
   is called 'rendering' the template. The result is a complete HTML page.
5. (The view can also pull in a _form_ to customize user-input in a similar way.)
6. The finished HTML page is packed into a _HTTP response_ and returned to the
   web browser, which can now display the page!

### A note on the webclient

The web browser can also execute code directly without talking to the Server.
This code must be written/loaded into the web page and is written using the
Javascript programming language (there is no way around this, it is what web
browsers understand). Executing Javascript is something the web browser does,
it operates independently from Evennia. Small snippets of javascript can be
used on a page to have buttons react, make small animations etc that doesn't
require the server.

In the case of the [Webclient](./Webclient), Evennia will load the Webclient page
as above, but the page then initiates Javascript code (a lot of it) responsible
for actually displaying the client GUI, allows you to resize windows etc.

After it starts, the webclient 'calls home' and spins up a
[websocket](https://en.wikipedia.org/wiki/WebSocket) link to the Evennia Portal - this
is how all data is then exchanged. So after the initial loading of the
webclient page, the above sequence doesn't happen again until close the tab and
come back or you reload it manually in your browser.
