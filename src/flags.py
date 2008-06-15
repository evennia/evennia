"""
Everything related to flags and flag management.
"""
import defines_global

def is_unsavable_flag(flagname):
    """
    Returns TRUE if the flag is an unsavable flag.
    """
    return flagname.upper() in defines_global.NOSAVE_FLAGS

def is_modifiable_flag(flagname):
    """
    Check to see if a particular flag is modifiable.
    """
    if flagname.upper() not in defines_global.NOSET_FLAGS:
        return True
    else:
        return False
