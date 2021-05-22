# Web resources

This folder holds the functioning code, html, js and css files for use by the
Evennia website and -client. This is a standard Django web application.

1. When a user enters an url (or clicks a link) in their web browser, Django will
   use this incoming request to refer to the `urls.py` file.
2. The `urls.py` file will use regex to match the url to a _view_ - a Python function
   or callable class. The incoming request data will be passed to this code.
3. The view will (usually) refer to a _template_, which is a html document with
   templating slots that allows the system to replace parts of it with dynamic
   content (like how many users are currently in-game).
4. The view will render the template with any context into a final HTML page
   that is returned to the user to view.

I many ways this works like an Evennia Command, with input being the browser's
request and the view being the Command's function body for producing a result.

In the case of the webclient, the html page is rendered once and when doing so
it loads a Javascript application in the browser that opens a websocket to
communicate with the server.
