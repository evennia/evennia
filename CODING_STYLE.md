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
   - Evennia src/ modules
   - Evennia game/ modules
   - Evennia 'ev' API imports
 * All modules, classes, functions and modules should have doc 
   strings formatted as described below

## Doc strings

All modules, classes, functions and methods should have docstrings
formatted with [Google style][googlestyle] -inspired indents, using
[Markdown][githubmarkdown] formatting where needed. Evennia's `api2md`
parser will use this to create pretty API documentation. 

> Note that far from all sources are currently formatted using the
> consistent style listed here. This is something that is being
> worked on and any help to convert existing docs are appreciated. 
> We also don't support all forms of the google style syntax, going
> for a limited and more restricted set for consistency.

### Module docstrings

Modules should all start with at least a few lines of docstring at
their top describing the contents and purpose of the module.
Sectioning should not be used - the auto-api will create this
automatically. Otherwise markdown should be used as needed to format
the text. 

Example of module docstring (top of file):

```python
"""
This module handles the creation of `Objects` that 
are useful in the game ...

"""
```

Code examples should use [multi-line syntax highlighting][markdown-hilight] to mark
multi-line code blocks, using the "python" identifier. Just indenting 
code blocks (common in markdown) will not produce the desired look.

### Class docstrings

The root class docstring should describe the over-arcing use of the
class. It should usually not describe the exact call sequence nor list
important methods, this tends to be hard to keep updated as the API
develops. 

Example of class docstring:

```python
class MyClass(object):
    """"
    This class describes the creation of `Objects`. It is useful
    in many situations, such as ...

    """
```

### Function / method docstrings

Example of function or method docstring:

```python

def funcname(a, b, c, d=False):
    """
    This is a brief introduction to the function/class/method

    Args:
        a (str): This is a string argument that we can talk about
            over multiple lines.
        b (int or str): Another argument
        c (list): A list argument
        d (bool, optional): An optional keyword argument

    Returns:
        e (str): The result of the function

    Raises:
        failed (RuntimeException): If there is a critical error,
            this is raised. 
        io error (IOError): This is only raised if there is a 
            problem with the database.

    Notes:
        This is an example function. If `d=True`, something
        amazing will happen.

    """
```

 - If you are describing a class method, the `self` argument should not 
   be included among the documented arguments. 
 - The text before the argument blocks is free-form. It should
   decsribe the function/method briefly. 
 - The argument blocks supported by `api2md` are 
   - `Args:`, `Returns` and `Raises` should be followed by a line break. nted 
     an extra 4 spaces (only). 
     - `argname (type):` is used for positional arguments 
     - `argname (type, optional):` is used for keyword arguments
     - `raise intention (exception type):` is used to describe exceptions
       raised from the function or method. 
     - All the above should appear on a new line with a 4-space indent relative their
       block header (as per PEP8). If extending over more than one line, the 
       subsequent lines should be indented another 4 spaces (only). 
     - The text inside the parenthesis is free-form so you can put
       anything that makes sense in there (such as `Object` or `list
       or str`). 
     - The describing text should start with a capital letter and end
       with a full stop (`.`).
 - `Notes:` starts freeform blocks of text and hsould always appear last. 
   The `Notes:` header should 
   be followed by a line break and a 4-space indent. The rest of the text
   is free-form.


## Ask Questions!

If any of the rules outlined in PEP 8 or in the sections above doesn't
make sense, please don't hesitate to ask on the Evennia mailing list
or in the chat. 


[pep8]: http://www.python.org/dev/peps/pep-0008
[pep8tool]: https://pypi.python.org/pypi/pep8
[googlestyle]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html?showone=Comments#Comments
[githubmarkdown]: https://help.github.com/articles/github-flavored-markdown/
[markdown-hilight]: https://help.github.com/articles/github-flavored-markdown/#syntax-highlighting
