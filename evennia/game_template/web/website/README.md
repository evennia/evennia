# Website views and other code 

A 'view' is python code (a function or callable class) responsible for
producing a HTML page for a user to view in response for going to a given URL
in their browser. In Evennia lingo, it's similar in function to a Command, with
the input/args being the URL/request and the output being a new web-page.

The urls.py file contains regular expressions that are run against the provided
URL - when a match is found, the execution is passed to a view which is then
responsible (usually) for producing the web page by filling in a _template_ - a
HTML document that can have special tags in it that are replaced for dynamic
content. It then returns the finished HTML page for the user to view.

See the [Django docs on Views](https://docs.djangoproject.com/en/3.2/topics/http/views/) for 
more information.

## Overriding a view

1. Copy the original code you want to change from `evennia/web/website/views/` into 
`mygame/web/website/views/` and edit it as you like.
2. Look at `evennia/web/website/urls.py` and find the regex pointing to the view. Add this regex 
to your own `mygam/website/urls.pye` but change it to import and point to your
changed version instead.
3. Reload the server and the page now uses your version of the view.
