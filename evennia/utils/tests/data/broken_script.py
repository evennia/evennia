"""
Defines a script module with a broken import, to catch the specific error case
in loading global scripts where the module can be parsed but has broken
dependencies.
"""

from evennia import nonexistent_module, DefaultScript

class BrokenScript(DefaultScript):
    pass
