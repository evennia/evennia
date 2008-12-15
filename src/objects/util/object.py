"""
Utility functions for the Object class. These functions should not import
any models or modify the database.
"""
def is_dbref(dbstring):
    """
    Is the input a well-formed dbref number?
    """
    try:
        number = int(dbstring[1:])
    except ValueError:
        return False
    except TypeError:
        return False
        
    if not dbstring.startswith("#"):
        return False
    elif number < 1:
        return False
    else:
        return True
