# Game website

When Evennia starts it will also start a [Webserver](./Webserver) as part of the
[Server](./Portal-And-Server) process. This uses [Django](https://docs.djangoproject.com) 
to present a simple but functional default game website.  With the default setup,
open your browser to [localhost:4001](http://localhost:4001) or [127.0.0.1:4001](http://127.0.0.1:4001) 
to see it.

The website allows existing players to log in using an account-name and
password they previously used to register with the game. If a user logs in with
the [Webclient](./Webclient) they will also log into the website and vice-versa.
So if you are logged into the website, opening the webclient will automatically
log you into the game as that account.

The default website shows a "Welcome!" page with a few links to useful
resources. It also shows some statistics about how many players are currently
connected.

In the top menu you can find
- _Home_ - Get back to front page.
- _Documentation_ - A link to the latest stable Evennia documentation.
- _Characters_ - This is a demo of connecting in-game characters to the website.
  It will display a list of all entities of the
  _typeclasses.characters.Character` typeclass and allow you to view their
  description with an optional image. The list is only available to logged-in
  users.
- _Channels_ - This is a demo of connecting in-game chats to the website. It will
  show a list of all channels available to you and allow you to view the latest
  discussions. Most channels require logging in, but the `Public` channel can
  also be viewed by non-loggedin users.
- _Help_ - This ties the in-game [Help system](./Help-System) to the website. All
  database-based help entries that are publicly available or accessible to your
  account can be read. This is a good way to present a body of help for people
  to read outside of the game.
- _Play Online_ - This opens the [Webclient](./Webclient) in the browser.
- _Admin_ The [Web admin](Web admin) will only show if you are logged in.
- _Log in/out_ - Allows you to authenticate using the same credentials you use
  in the game.
- _Register_ - Allows you to register a new account. This is the same as 
  creating a new account upon first logging into the game).

## Modifying the default Website

You can modify and override all aspects of the web site from your game dir.
You'll mostly be doing so in your settings file
(`mygame/server/conf/settings.py` and in the gamedir's `web/folder`
(`mygame/web/` if your game folder is `mygame/`).

> When testing your modifications, it's a good idea to add `DEBUG = True` to
> your settings file. This will give you nice informative tracebacks directly
> in your browser instead of generic 404 or 500 error pages. Just remember that
> DEBUG mode leaks memory (for retaining debug info) and is *not* safe to use
> for a production game!

As explained on the [Webserver](./Webserver) page, the process for getting a web
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
        (python files related to website)

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

## Examples of commom web changes

```important::

  Django is a very mature web-design framework. There are endless
  internet-tutorials, courses and books available to explain how to use Django.
  So these examples only serve as a first primer to get you started.

```

### Change Title and blurb

The website's title and blurb are simply changed by tweaking
`settings.SERVERNAME` and `settings.GAME_SLOGAN`. Your settings file is in
`mygame/server/conf/settings.py`, just set/add

    SERVERNAME = "My Awesome Game"
    GAME_SLOGAN = "The best game in the world"

### Change the Logo

The Evennia googly-eyed snake logo is probably not what you want for your game.
The template looks for a file  `web/static/website/images/evennia_logo.png`. Just
plop your own PNG logo (64x64 pixels large) in there and name it the same.


### Change front page HTML

The front page of the website is usually referred to as the 'index' in HTML
parlance.

The frontpage template is found in `evennia/web/templates/website/index.html`.
Just copy this to the equivalent place in `mygame/web/`. Modify it there and
reload the server to see your changes.

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

### Change webpage colors and styling

You can tweak the [CSS](https://en.wikipedia.org/wiki/Cascading_Style_Sheets) of the entire 
website. If you investigate the `evennia/web/templates/website/base.html` file you'll see that we 
use the [Bootstrap
4](https://getbootstrap.com/docs/4.6/getting-started/introduction/) toolkit.

Much structural HTML functionality is actually coming from bootstrap, so you
will often be able to just add bootstrap CSS classes to elements in the HTML
file to get various effects like text-centering or similar.

The website's custom CSS is found in
`evennia/web/static/website/css/website.css` but we also look for a (currently
empty) `custom.css` in the same location. You can override either, but it may
be easier to revert your changes if you only add things to `custom.css`.

Copy the CSS file you want to modify to the corresponding location in `mygame/web`. 
Modify it and reload the server to see your changes. 

You can also apply static files without reloading, but running this in the
terminal:

    evennia collectstatic --no-input

(this is run automatically when reloading the server).

> Note that before you see new CSS files applied you may need to refresh your
> browser without cache (Ctrl-F5 in Firefox, for example).

As an example, add/copy `custom.css` to `mygame/web/static/website/css/` and 
add the following: 


```css

.navbar {
  background-color: #7a3d54;
}

.footer {
  background-color: #7a3d54;
}

```

Reload and your website now has a red theme!

> Hint: Learn to use your web browser's [Developer tools](https://torquemag.io/2020/06/browser-developer-tools-tutorial/).
> These allow you to tweak CSS 'live' to find a look you like and copy it into
> the .css file only when you want to make the changes permanent.


### Change front page functionality

The logic is all in the view. To find where the index-page view is found, we
look in `evennia/web/website/urls.py`. Here we find the following line:

```python
# in evennia/web/website/urls.py

  ...
  # website front page
  path("", index.EvenniaIndexView.as_view(), name="index"),
  ...

```

The first `""` is the empty url - root - what you get if you just enter `localhost:4001/` 
with no extra path. As expected, this leads to the index page. By looking at the imports
we find the view is in in `evennia/web/website/views/index.py`. 

Copy this file to the corresponding location in `mygame/web`. Then tweak your `mygame/web/website/urls.py` 
file to point to the new file:

```python 
# in mygame/web/website/urls.py

# ...

from web.website.views import index

urlpatterns = [
    path("", index.EvenniaIndexView.as_view(), name="index")

]
# ...

```
    
So we just import `index` from the new location and point to it. After a reload 
the front page will now redirect to use your copy rather than the original.

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

### Change other website pages

The other sub pages are handled in the same way - copy the template or static
resource to the right place, or copy the view and repoint your `website/urls.py` to
your copy. Just remember to reload.

## Adding a new web page

### Using Flat Pages

The absolutely simplest way to add a new web page is to use the `Flat Pages`
app available in the [Web Admin](./Web-Admin). The page will appear with the same
styling as the rest of the site.

For the `Flat pages` module to work you must first set up a _Site_ (or
domain) to use. You only need to this once.

- Go to the Web admin and select `Sites`. If your
game is at `mygreatgame.com`, that's the domain you need to add. For local
experimentation, add the domain `localhost:4001`. Note the `id` of the domain
(look at the url when you click on the new domain, if it's for example
`http://localhost:4001/admin/sites/site/2/change/`, then the id is `2`).
- Now add the line `SITE_ID = <id>` to your settings file.

Next you create new pages easily.

- Go the `Flat Pages` web admin and choose to add a new flat page.
- Set the url. If you want the page to appear as e.g. `localhost:4001/test/`, then 
  add `/test/` here. You need to add both leading and trailing slashes.
- Set `Title` to the name of the page.
- The `Content` is the HTML content of the body of the page. Go wild!
- Finally pick the `Site` you made before, and save.
- (in the advanced section you can make it so that you have to login to see the page etc).

You can now go to `localhost:4001/test/` and see your new page!

### Add Custom new page

The `Flat Pages` page doesn't allow for (much) dynamic content and customization. For 
this you need to add the needed components yourself.

Let's see how to make a `/test/` page from scratch.

- Add a new `test.html` file under `mygame/web/templates/website/`. Easiest is to base 
  this off an existing file. Make sure to `{% extend base.html %}` if you want to 
  get the same styling as the rest of your site.
- Add a new view `testview.py` under `mygame/web/website/views/` (don't name it `test.py` or 
  Django/Evennia will think it contains unit tests). Add a view there to process 
  your page. This is a minimal view to start from (read much more [in the Django docs](https://docs.djangoproject.com/en/3.2/topics/class-based-views/)):

    ```python
    # mygame/web/website/views/testview.py

    from django.views.generic import TemplateView

    class MyTestView(TemplateView):
        template_name = "website/test.html"


    ```

- Finally, point to your view from the `mygame/web/website/urls.py`:

    ```python
    # in mygame/web/website/urls.py

    # ...
    from web.website.views import testview

    urlpatterns = [
        # ...
        # we can skip the initial / here
        path("test/", testview.MyTestView.as_view())
    ]

    ``` 
- Reload the server and your new page is available. You can now continue to add
  all sorts of advanced dynamic content through your view and template!


## User forms

All the pages created so far deal with _presenting_ information to the user.
It's also possible for the user to _input_ data on the page through _forms_. An
example would be a page of fields and sliders you fill in to create a
character, with a big 'Submit' button at the bottom. 

Firstly, this must be represented in HTML. The `<form> ... </form>` is a
standard HTML element you need to add to your template. It also has some other
requirements, such as `<input>` and often Javascript components as well (but
usually Django will help with this). If you are unfamiliar with how HTML forms
work, [read about them here](https://docs.djangoproject.com/en/3.2/topics/forms/#html-forms). 

The basic gist of it is that when you click to 'submit' the form, a POST HTML
request will be sent to the server containing the data the user entered. It's
now up to the server to make sure the data makes sense (validation) and then
process the input somehow (like creating a new character).

On the backend side, we need to specify the logic for validating and processing
the form data. This is done by the `Form` [Django class](https://docs.djangoproject.com/en/3.2/topics/forms/#forms-in-django).
This specifies _fields_ on itself that define how to validate that piece of data.

The form is then linked into the view-class by adding `form_class = MyFormClass` to 
the view (next to `template_name`).

There are several example forms in `evennia/web/website/forms.py`. It's also a good 
idea to read [Building a form in Django](https://docs.djangoproject.com/en/3.2/topics/forms/#building-a-form-in-django)
on the Django website - it covers all you need.
