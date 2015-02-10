# Evennia Code Style

All code submitted or committed to the Evennia project should aim to
follow the guidelines outlined in [Python PEP
8](http://www.python.org/dev/peps/pep-0008). Keeping the code style
uniform makes it much easier for people to collaborate and read the
code.

A good way to check if your code follows PEP8 is to use the [PEP8
tool](https://pypi.python.org/pypi/pep8) on your sources.

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

## Documentation

Remember that Evennia's source code is intended to be read - and will
be read - by game admins trying to implement their game. Evennia
prides itself with being extensively documented. Modules, functions,
classes and class methods should all start with at least one line of
docstring summing up the function's purpose. Ideally also explain
eventual arguments and caveats. Add comments where appropriate.

## Ask Questions!

If any of the rules outlined in PEP 8 or in the sections above doesn't
make sense, please don't hesitate to ask on the Evennia mailing list
or in the chat. 
