# Web 

This folder contains overriding of web assets - the website and webclient
coming with the game.

This is the process for serving a new web site (see also the Django docs for
more details):

1. A user enters an url in their browser (or clicks a button). This leads to
   the browser sending a _HTTP request_ to the server, with a specific type
   (GET,POST etc) and url-path (like for `https://localhost:4001/`, the part of
   the url we need to consider is `/`).
2. Evennia (through Django) will make use of the regular expressions registered
   in the `urls.py` file.  This acts as a rerouter to _views_, which are
   regular Python functions able to process the incoming request (think of
   these as similar to the right Evennia Command being selected to handle your
   input - views are like Commands in this sense). In the case of `/` we
   reroute to a view handling the main index-page of the website.  The view is
   either a function or a callable class (Evennia tends to have them as
   functions).
3. The view-function will prepare all the data needed by the web page. For the default 
   index page, this means gather the game statistics so you can see how many
   are currently connected to the game etc. 
4. The view will next fetch a _template_. A template is a HTML-document with special
   'placeholder' tags (written as `{{...}}` or `{% ... %}` usually). These
   placeholders allow the view to inject dynamic content into the HTML and make
   the page customized to the current situation. For the index page, it means
   injecting the current player-count in the right places of the html page. This
   is called 'rendering' the template. The result is a complete HTML page.
5. (The view can also pull in a _form_ to customize user-input in a similar way.)
6. The finished HTML page is packed in a _HTTP response_ and is returned to the
   web browser, which can now display the page! 

## A note on the webclient

The web browser can also execute code directly without talking to the Server.
This code must be written/loaded into the web page and is written using the
Javascript programming language (there is no way around this, it is what web
browsers understand). Executing Javascript is something the web browser does,
it operates independently from Evennia. Small snippets of javascript can be
used on a page to have buttons react, make small animations etc that doesn't
require the server.

In the case of the Webclient, Evennia will load the Webclient page as above,
but the page then contains Javascript code responsible for actually displaying
the client GUI, allows you to resize windows etc. 

After it starts, the webclient 'calls home' and spins up a websocket link to
the Evennia Portal - this is how all data is then exchanged. So after the
initial loading of the webclient page, the above sequence doesn't happen again
until close the tab and come back or you reload it manually in your browser.
