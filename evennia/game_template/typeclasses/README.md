# typeclasses/

This directory holds the modules for overloading all the typeclasses
representing the game entities and many systems of the game. Other
server functionality not covered here is usually modified by the
modules in `server/conf/`.

Each module holds empty classes that just imports Evennia's defaults.
Any modifications done to these classes will overload the defaults.

You can change the structure of this directory (even rename the
directory itself) as you please, but if you do you must add the
appropriate new paths to your settings.py file so Evennia knows where
to look. Also remember that for Python to find your modules, it
requires you to add an empty `__init__.py` file in any new sub
directories you create.
