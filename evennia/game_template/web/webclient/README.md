# Webclient Views

The webclient is mainly controlled by Javascript directly in the browser, so
you usually customize it via `mygame/web/static/webclient/js/` - files instead.

There is very little you can change from here, unless you want to implement
your very own client from scratch.

## On views

A 'view' is python code (a function or callable class) responsible for
producing a HTML page for a user to view in response for going to a given URL
in their browser. In Evennia lingo, it's similar in function to a Command, with
the input/args being the URL/request and the output being a new web-page.

The urls.py file contains regular expressions that are run against the provided
URL - when a match is found, the execution is passed to a view which is then
responsible (usually) for producing the web page by filling in a _template_ - a
HTML document that can have special tags in it that are replaced for dynamic
content. It then returns the finished HTML page for the user to view.

See the [Django docs on Views](https://docs.djangoproject.com/en/4.1/topics/http/views/) for
more information.
