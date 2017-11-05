"""
This sub-package holds the miscelaneous utilities used by other
modules in Evennia. It also holds the idmapper in-memory caching
functionality.

"""

# simple check to determine if we are currently running under pypy.
try:
    import __pypy__ as is_pypy
except ImportError:
    is_pypy = False

from .utils import *
