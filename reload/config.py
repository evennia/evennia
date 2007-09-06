"""
Configuration file for the reload system to add custom
modules to be reloaded at @reload.
"""

# All of these are reloaded after the built-in system modules and default
# model modules are reloaded.

# These are custom modules that have classes requiring state-saving.
# These modules are reloaded before those in no_cache.
cache = {
        #  This should be a dict of lists of tuples
        #  with the module name as a key, a list of tuples
        #  with the class name as the first element of the 
        #  tuple, and True or False if this is a model
        #  for the database, like so:
        #
        #  'modulename' : [ ('ModelA', True), ('ClassA', False) ],
        #  'anothermod' : [ ('ClassB', False), ('ClassC', False) ],
    }

# This is a list of modules that need to be reloaded at @reload.  There
# is no state-saving, and these are reloaded after those cached above.
no_cache = [
        #  'modulename',
        #  'anothermod',
    ]
