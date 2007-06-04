"""
This module is responsible for managing scripts and their connection to the
Object class model. It is important to keep this as independent from the
codebase as possible in order to allow for drop-in replacements. All
interaction with actual script methods should happen via calls to Objects.
"""

# A dictionary with keys equivalent to the script's name and values that
# contain references to the associated module for each key.
cached_scripts = {}

def scriptlink(scriptname):
   """
   Each Object will refer to this function when trying to execute a function
   contained within a scripted module. For the sake of ease of management,
   modules are cached and compiled as they are requested and stored in
   the cached_scripts dictionary.
   """
   # The module is already cached, just return it rather than re-load.
   retval = cached_scripts.get('scripts.%s' % (scriptname), False)
   if retval:
      return retval

   modname = 'scripts.%s' % (scriptname)
   print 'Caching script module %s.' % (modname)

   try:
      modreference = __import__(modname)
      cached_scripts[modname] = modreference
   except ImportError:
      print 'Error importing %s.' % (modname)
      return

   # The new script module has been cached, return the reference.
   return modreference