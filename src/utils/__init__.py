# simple check to determine if we are currently running under pypy.
try:
    import __pypy__ as is_pypy
except ImportError:
    is_pypy = False
