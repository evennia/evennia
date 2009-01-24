"""
Utility functions for the Object class. These functions should not import
any models or modify the database.
"""
def is_dbref(dbstring, require_pound=True):
    """
    Is the input a well-formed dbref number?
    """
    # Strip the leading # sign if it's there.
    if dbstring.startswith("#"):
        dbstring = dbstring[1:]
    else:
        if require_pound:
            # The pound sign was required and it didn't have it, fail out.
            return False

    try:
        # If this fails, it's probably not valid.
        number = int(dbstring)
    except ValueError:
        return False
    except TypeError:
        return False
          
    # Numbers less than 1 are not valid dbrefs. 
    if number < 1:
        return False
    else:
        return True
