# Evennia Code Style

All code submitted or committed to the Evennia project should aim to follow the
guidelines outlined in [Python PEP 8][pep8]. Keeping the code style uniform
makes it much easier for people to collaborate and read the code.

A good way to check if your code follows PEP8 is to use the [PEP8 tool][pep8tool]
on your sources.

## Main code style specification

 * 4-space indentation, NO TABS!
 * Unix line endings.
 * 100 character line widths
 * CamelCase is only used for classes, nothing else.
 * All non-global variable names and all function names are to be
   lowercase, words separated by underscores. Variable names should
   always be more than two letters long.
 * Module-level global variables (only) are to be in CAPITAL letters.
 * Imports should be done in this order:
   - Python modules (builtins and standard library)
   - Twisted modules
   - Django modules
   - Evennia library modules (`evennia`)
   - Evennia contrib modules (`evennia.contrib`)
 * All modules, classes, functions and methods should have doc strings formatted
   as outlined below.
 * All default commands should have a consistent docstring formatted as
   outlined below.

## Code Docstrings

All modules, classes, functions and methods should have docstrings
formatted with [Google style][googlestyle] -inspired indents, using
[Markdown][githubmarkdown] formatting where needed. Evennia's `api2md`
parser will use this to create pretty API documentation.


### Module docstrings

Modules should all start with at least a few lines of docstring at
their top describing the contents and purpose of the module.

Example of module docstring (top of file):

```python
"""
This module handles the creation of `Objects` that
are useful in the game ...

"""
```

Sectioning (`# title`,  `## subtile` etc) should not be used in
freeform docstrings - this will confuse the sectioning of the auto
documentation page and the auto-api will create this automatically.
Write just the section name bolded on its own line to mark a section.
Beyond sections markdown should be used as needed to format
the text.

Code examples should use [multi-line syntax highlighting][markdown-hilight]
to mark multi-line code blocks, using the "python" identifier. Just
indenting code blocks (common in markdown) will not produce the
desired look.

When using any code tags (inline or blocks) it's recommended that you
don't let the code extend wider than about 70 characters or it will
need to be scrolled horizontally in the wiki (this does not affect any
other text, only code).

### Class docstrings

The root class docstring should describe the over-arching use of the
class. It should usually not describe the exact call sequence nor list
important methods, this tends to be hard to keep updated as the API
develops. Don't use section markers (`#`, `##` etc).

Example of class docstring:

```python
class MyClass(object):
    """
    This class describes the creation of `Objects`. It is useful
    in many situations, such as ...

    """
```

### Function / method docstrings

Example of function or method docstring:

```python

def funcname(a, b, c, d=False, **kwargs):
    """
    This is a brief introduction to the function/class/method

    Args:
        a (str): This is a string argument that we can talk about
            over multiple lines.
        b (int or str): Another argument.
        c (list): A list argument.
        d (bool, optional): An optional keyword argument.

    Keyword Args:
        test (list): A test keyword.

    Returns:
        str: The result of the function.

    Raises:
        RuntimeException: If there is a critical error,
            this is raised.
        IOError: This is only raised if there is a
            problem with the database.

    Notes:
        This is an example function. If `d=True`, something
        amazing will happen.

    """
```

The syntax is very "loose" but the indentation matters. That is, you
should end the block headers (like `Args:`) with a line break followed by
an indent. When you need to break a line you should start the next line
with another indent. For consistency with the code we recommend all
indents to be 4 spaces wide (no tabs!).

Here are all the supported block headers:

```
    """
    Args
        argname (freeform type): Description endind with period.
    Keyword Args:
        argname (freeform type): Description.
    Returns/Yields:
        type: Description.
    Raises:
        Exceptiontype: Description.
    Notes/Note/Examples/Example:
        Freeform text.
    """
```

Parts marked with "freeform" means that you can in principle put any
text there using any formatting except for sections markers (`#`, `##`
etc). You must also keep indentation to mark which block you are part
of. You should normally use the specified format rather than the
freeform counterpart (this will produce nicer output) but in some
cases the freeform may produce a more compact and readable result
(such as when describing an `*args` or `**kwargs` statement in general
terms). The first `self` argument of class methods should never be
documented.

Note that

```
"""
Args:
    argname (type, optional): Description.
"""
```

and

```
"""
Keyword Args:
   sargname (type): Description.
"""
```

mean the same thing! Which one is used depends on the function or
method documented, but there are no hard rules; If there is a large
`**kwargs` block in the function, using the `Keyword Args:` block may be a
good idea, for a small number of arguments though, just using `Args:`
and marking keywords as `optional` will shorten the docstring and make
it easier to read.

## Default Command Docstrings

These represent a special case since Commands in Evennia use their class
docstrings to represent the in-game help entry for that command.

All the commands in the _default command_ sets should have their doc-strings
formatted on a similar form. For contribs, this is loosened, but if there is
no particular reason to use a different form, one should aim to use the same
style for contrib-command docstrings as well.

```python
      """
      Short header

      Usage:
        key[/switches, if any] <mandatory args> [optional] choice1||choice2||choice3

      Switches:
        switch1    - description
        switch2    - description

      Examples:
        Usage example and output

      Longer documentation detailing the command.

      """
```

- Two spaces are used for *indentation* in all default commands.
- Square brackets `[ ]` surround *optional, skippable arguments*.
- Angled brackets `< >` surround a _description_ of what to write rather than the exact syntax.
- Explicit choices are separated by `|`. To avoid this being parsed as a color code, use `||` (this
will come out as a single `|`) or put spaces around the character ("` | `") if there's plenty of room.
- The `Switches` and `Examples` blocks are optional and based on the Command.

Here is the `nick` command as an example:

```python
      """
      Define a personal alias/nick

      Usage:
        nick[/switches] <nickname> = [<string>]
        alias             ''

      Switches:
        object   - alias an object
        account   - alias an account
        clearall - clear all your aliases
        list     - show all defined aliases (also "nicks" works)

      Examples:
        nick hi = say Hello, I'm Sarah!
        nick/object tom = the tall man

      A 'nick' is a personal shortcut you create for your own use [...]

        """
```

For commands that *require arguments*, the policy is for it to return a `Usage:`
string if the command is entered without any arguments. So for such commands,
the Command body should contain something to the effect of

```python
      if not self.args:
          self.caller.msg("Usage: nick[/switches] <nickname> = [<string>]")
          return
```

## Tools for auto-linting

### black

Automatic pep8 compliant formatting and linting can be performed using the
`black` formatter:

    black --line-length 100

### PyCharm

The Python IDE [Pycharm][pycharm] can auto-generate empty doc-string stubs. The
default is to use `reStructuredText` form, however. To change to Evennia's
Google-style docstrings, follow [this guide][pycharm-guide].



[pep8]: http://www.python.org/dev/peps/pep-0008
[pep8tool]: https://pypi.python.org/pypi/pep8
[googlestyle]: https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html
[githubmarkdown]: https://help.github.com/articles/github-flavored-markdown/
[markdown-hilight]: https://help.github.com/articles/github-flavored-markdown/#syntax-highlighting
[command-docstrings]: https://github.com/evennia/evennia/wiki/Using%20MUX%20As%20a%20Standard#documentation-policy
[pycharm]: https://www.jetbrains.com/pycharm/
[pycharm-guide]: https://www.jetbrains.com/help/pycharm/2016.3/python-integrated-tools.html
