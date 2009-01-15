"""
Utility functions for the Object class. These functions should not import
any models or modify the database.
"""
def is_dbref(dbstring):
    """
    Is the input a well-formed dbref number?
    """
    # Strip the leading # sign if it's there.
    if dbstring.startswith("#"):
        dbstring = dbstring[1:]

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
