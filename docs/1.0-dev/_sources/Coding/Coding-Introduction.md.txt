# Coding Introduction

Evennia allows for a lot of freedom when designing your game - but to code efficiently you still
need to adopt some best practices as well as find a good place to start to learn.

Here are some pointers to get you going.

### Start with the tutorial

It's highly recommended that you jump in on the [Starting Tutorial](../Howto/Starting/Part1/Starting-Part1). Even if 
you only the beginning or some part of it, it covers much of the things needed to get started.

### Python

Evennia is developed using Python. Even if you are more of a designer than a coder, it is wise to
learn how to read and understand basic Python code. If you are new to Python, or need a refresher,
take a look at our [Python introduction](../Howto/Starting/Part1/Python-basic-introduction).

### Explore Evennia interactively

When new to Evennia it can be hard to find things or figure out what is available. Evennia offers a
special interactive python shell that allows you to experiment and try out things. It's recommended
to use [ipython](http://ipython.org/) for this since the vanilla python prompt is very limited. Here
are some simple commands to get started:

    # [open a new console/terminal]
    # [activate your evennia virtualenv in this console/terminal]
    pip install -r requirements_extra.txt  # install ipython etc
    cd mygame
    evennia shell

This will open an Evennia-aware python shell (using ipython). From within this shell, try

    import evennia
    evennia.<TAB>

That is, enter `evennia.` and press the `<TAB>` key. This will show you all the resources made
available at the top level of Evennia's  "flat API". See the [flat API](../Evennia-API) page for more
info on how to explore it efficiently.

#### Jupyter Notebook Support

You can also explore evennia interactively in a [Jupyter notebook](https://jupyter.readthedocs.io/en/latest/index.html#). This offers
an in-browser view of your code similar to Matlab or similar programs. There are 
a few extra steps that must be taken in order for this to work:

    # [open a new console/terminal]
    # [activate your evennia virtualenv in this console/terminal]
    cd evennia
    pip install -r requirements_extra.txt  # if not done already above

Next, `cd` to your game folder. _It's important that you are in the _root_ of this folder for the next command_:

    evennia shell_plus --notebook & 

The `&` at the end starts the process as a background process on Linux/Unix.
Skip it if your OS doesn't support this syntax. Your browser should now open
with the Jupyter interface. If not, open a browser to the link given on the
command line.

In the window, open the `new` menu in the top right and start a `Django Shell-Plus` notebook (or
open an existing one if you had one from before). In the first cell you must initialize 
Evennia like so:

```python
import evennia
evennia._init()
```

_Note that the above initialization must be run every time a new new notebook/kernel is started or restarted._

After this you can import and access all of the Evennia system, same as with `evennia shell`.

#### More exploration

You can complement your exploration by peeking at the sections of the much more detailed 
[Evennia Component overview](../Components/Components-Overview). The [Tutorials](../Howto/Howto-Overview) section also contains a growing collection
of system- or implementation-specific help.

### Use a python syntax checker

Evennia works by importing your own modules and running them as part of the server. Whereas Evennia
should just gracefully tell you what errors it finds, it can nevertheless be a good idea for you to
check your code for simple syntax errors *before* you load it into the running server.  There are
many python syntax checkers out there. A fast and easy one is
[pyflakes](https://pypi.python.org/pypi/pyflakes), a more verbose one is
[pylint](http://www.pylint.org/). You can also check so that your code looks up to snuff using
[pep8](https://pypi.python.org/pypi/pep8). Even with a syntax checker you will not be able to catch
every possible problem - some bugs or problems will only appear when you actually run the code. But
using such a checker can be a good start to weed out the simple problems.

### Plan before you code

Before you start coding away at your dream game, take a look at our [Game Planning](../Howto/Starting/Part2/Game-Planning)
page. It might hopefully help you avoid some common pitfalls and time sinks.

### Code in your game folder, not in the evennia/ repository

As part of the Evennia setup you will create a game folder to host your game code. This is your
home. You should *never* need to modify anything in the `evennia` library (anything you download
from us, really). You import useful functionality from here and if you see code you like, copy&paste
it out into your game folder and edit it there.

If you find that Evennia doesn't support some functionality you need, make a [Feature
Request](github:issue) about it. Same goes for [bugs][bug]. If you add features or fix bugs
yourself, please consider [Contributing](../Contributing) your changes upstream!

### Learn to read tracebacks

Python is very good at reporting when and where things go wrong. A *traceback* shows everything you
need to know about crashing code. The text can be pretty long, but you usually are only interested
in the last bit, where it says what the error is and at which module and line number it happened -
armed with this info you can resolve most problems.

Evennia will usually not show the full traceback in-game though. Instead the server outputs errors
to the terminal/console from which you started Evennia in the first place. If you want more to show
in-game you can add `IN_GAME_ERRORS = True` to your settings file. This will echo most (but not all)
tracebacks both in-game as well as to the terminal/console. This is a potential security problem
though, so don't keep this active when your game goes into production.

> A common confusing error is finding that objects in-game are suddenly of the type `DefaultObject`
rather than your custom typeclass. This happens when you introduce a critical Syntax error to the
module holding your custom class. Since such a module is not valid Python, Evennia can't load it at
all. Instead of crashing, Evennia will then print the full traceback to the terminal/console and
temporarily fall back to the safe `DefaultObject` until you fix the problem and reload.

### Docs are here to help you

Some people find reading documentation extremely dull and shun it out of principle. That's your
call, but reading docs really *does* help you, promise! Evennia's documentation is pretty thorough
and knowing what is possible can often give you a lot of new cool game ideas. That said, if you
can't find the answer in the docs, don't be shy to ask questions! The [discussion
group](https://sites.google.com/site/evenniaserver/discussions) and the [irc
chat](http://webchat.freenode.net/?channels=evennia) are also there for you.

### The most important point

And finally, of course, have fun!

[feature-request]: (https://github.com/evennia/evennia/issues/new?title=Feature+Request%3a+%3Cdescriptive+title+here%3E&body=%23%23%23%23+Description+of+the+suggested+feature+and+how+it+is+supposed+to+work+for+the+admin%2fend+user%3a%0D%0A%0D%0A%0D%0A%23%23%23%23+A+list+of+arguments+for+why+you+think+this+new+feature+should+be+included+in+Evennia%3a%0D%0A%0D%0A1.%0D%0A2.%0D%0A%0D%0A%23%23%23%23+Extra+information%2c+such+as+requirements+or+ideas+on+implementation%3a%0D%0A%0D%0A
[bug](https://github.com/evennia/evennia/issues/new?title=Bug%3a+%3Cdescriptive+title+here%3E&body=%23%23%23%23+Steps+to+reproduce+the+issue%3a%0D%0A%0D%0A1.+%0D%0A2.+%0D%0A3.+%0D%0A%0D%0A%23%23%23%23+What+I+expect+to+see+and+what+I+actually+see+%28tracebacks%2c+error+messages+etc%29%3a%0D%0A%0D%0A%0D%0A%0D%0A%23%23%23%23+Extra+information%2c+such+as+Evennia+revision%2frepo%2fbranch%2c+operating+system+and+ideas+for+how+to+solve%3a%0D%0A%0D%0A)
