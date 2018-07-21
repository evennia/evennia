# Evennia Code Style

All code submitted or committed to the Evennia project should aim to
follow the guidelines outlined in [Python PEP 8][pep8]. Keeping the code style
uniform makes it much easier for people to collaborate and read the
code.

A good way to check if your code follows PEP8 is to use the [PEP8 tool][pep8tool]
on your sources.

## A quick list of code style points

 * 4-space indendation, NO TABS!
 * Unix line endings.
 * CamelCase is only used for classes, nothing else.
 * All non-global variable names and all function names are to be
   lowercase, words separated by underscores. Variable names should
   always be more than two letters long.
 * Module-level global variables (only) are to be in CAPITAL letters.
 * (Evennia-specific): Imports should normally be done in this order:
   - Python modules (builtins and standard library)
   - Twisted modules
   - Django modules
   - Evennia library modules (`evennia`)
   - Evennia contrib modules (`evennia.contrib`)
 * All modules, classes, functions and modules should have doc
   strings formatted as described below

## Doc strings

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

The root class docstring should describe the over-arcing use of the
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

    Kwargs:
        test (list): A test keyword.

    Returns:
        e (str): The result of the function.

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
    Args/Arg/Kwargs/Kwarg:
        argname (freeform type): text
        or
        freeform text
    Returns/Yields:
        kwargname (freeform type): text
        or
        freeform text
    Raises:
        Exceptiontype: text
        or
        freeform text
    Notes/Note/Examples/Example:
        freeform text
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
Args:
    argname (type, optional): text
```

and

```
Kwargs:
   argname (type): text
```

mean the same thing! Which one is used depends on the function or
method documented, but there are no hard rules; If there is a large
`**kwargs` block in the function, using the `Kwargs:` block may be a
good idea, for a small number of arguments though, just using `Args:`
and marking keywords as `optional` will shorten the docstring and make
it easier to read.

### Default Commands

These represent a special case since Commands in Evennia are using their
class docstrings to represent the in-game help entry for that command. 
So for the default look of Command class docstrings see instead 
[the default command documentation policy][command-docstrings].

### Automatic docstring templating 

The Python IDE [Pycharm][pycharm] will generate Evennia-friendly
docstring stubs automatically for you, but the default format is
reStructuredText. To change it to Evennia's Google-style, follow 
[this guide][pycharm-guide].

## Ask Questions!

If any of the rules outlined in PEP 8 or in the sections above doesn't
make sense, please don't hesitate to ask on the Evennia mailing list
or in the chat.


[pep8]: http://www.python.org/dev/peps/pep-0008
[pep8tool]: https://pypi.python.org/pypi/pep8
[googlestyle]: http://www.sphinx-doc.org/en/stable/ext/example_google.html
[githubmarkdown]: https://help.github.com/articles/github-flavored-markdown/
[markdown-hilight]: https://help.github.com/articles/github-flavored-markdown/#syntax-highlighting
[command-docstrings]: https://github.com/evennia/evennia/wiki/Using%20MUX%20As%20a%20Standard#documentation-policy
[pycharm]: https://www.jetbrains.com/pycharm/
[pycharm-guide]: https://www.jetbrains.com/help/pycharm/2016.3/python-integrated-tools.html
