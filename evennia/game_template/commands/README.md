# commands/

This folder holds modules for implementing one's own commands and
command sets. All the modules' classes are essentially empty and just
imports the default implementations from Evennia; so adding anything
to them will start overloading the defaults. 

You can change the organisation of this directory as you see fit, just
remember that if you change any of the default command set classes'
locations, you need to add the appropriate paths to
`server/conf/settings.py` so that Evennia knows where to find them.
Also remember that if you create new sub directories you must put
(optionally empty) `__init__.py` files in there so that Python can
find your modules.
