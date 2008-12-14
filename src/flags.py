"""
Everything related to flags and flag management.
"""
import defines_global

# This is a list of flags that the server actually uses. Anything not in this
# list is a custom flag.
SERVER_FLAGS = ["CONNECTED", "DARK", "FLOATING", "GAGGED", "HAVEN", "OPAQUE", 
                "SAFE", "SLAVE", "SUSPECT", "TRANSPARENT"]

# These flags are not saved.
NOSAVE_FLAGS = ["CONNECTED"]

# These flags can't be modified by players.
NOSET_FLAGS = ["CONNECTED"]

def is_unsavable_flag(flagname):
    """
    Returns TRUE if the flag is an unsavable flag.
    """
    return flagname.upper() in NOSAVE_FLAGS

def is_modifiable_flag(flagname):
    """
    Check to see if a particular flag is modifiable.
    """
    if flagname.upper() not in NOSET_FLAGS:
        return True
    else:
        return False
